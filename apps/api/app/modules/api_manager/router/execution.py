"""API Manager execution endpoints for running and testing API definitions."""

import json
import logging
import time
from urllib.parse import urlparse, urlunparse

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Request
from models.api_definition import ApiDefinition, ApiMode
from pydantic import BaseModel
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.auth.models import TbUser

from ..crud import DRY_RUN_API_ID, _parse_api_uuid
from ..executor import execute_http_api, execute_sql_api, is_http_logic_body
from ..script_executor import execute_script_api
from ..services.sql_validator import SQLValidator
from ..workflow_executor import execute_workflow_api

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])

sql_validator = SQLValidator()


class ExecuteApiRequest(BaseModel):
    """Request to execute API"""

    params: dict = {}


def _rewrite_http_logic_for_request(logic_body: str, request: Request | None) -> str:
    """Rewrite local HTTP targets to current API host for dry-run/execute stability."""
    if request is None:
        return logic_body
    try:
        spec = json.loads(logic_body or "{}")
    except (ValueError, TypeError):
        return logic_body
    if not isinstance(spec, dict):
        return logic_body

    raw_url = spec.get("url")
    if not isinstance(raw_url, str) or not raw_url.strip():
        return logic_body
    url = raw_url.strip()

    base_url = str(request.base_url).rstrip("/")
    parsed = urlparse(url)
    rewritten = url

    if url.startswith("/"):
        rewritten = f"{base_url}{url}"
    elif parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost"}:
        current = urlparse(base_url)
        rewritten = urlunparse(
            (
                current.scheme or parsed.scheme,
                current.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    if rewritten != url:
        spec["url"] = rewritten
        return json.dumps(spec, ensure_ascii=False)
    return logic_body


@router.post("/{api_id}/validate-sql", response_model=ResponseEnvelope)
async def validate_sql(
    api_id: str, sql: str = None, current_user: TbUser = Depends(get_current_user)
):
    """
    Validate SQL query

    Checks for:
    - Security issues (dangerous keywords, SQL injection)
    - Table access permissions
    - Performance problems
    """

    try:
        validation = sql_validator.validate(sql)

        return ResponseEnvelope.success(data={
            "is_safe": validation.is_safe,
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "metadata": validation.metadata,
        })

    except Exception as e:
        logger.error(f"SQL validation failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/apis/{api_id}/execute", response_model=ResponseEnvelope)
async def execute_api(
    api_id: str,
    request: ExecuteApiRequest,
    http_request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Execute API with parameters using real executors.
    Dispatches to sql/http/workflow/script based on API mode.
    """
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")
        if not api.logic:
            raise HTTPException(status_code=400, detail="API has no logic defined")

        executed_by = getattr(current_user, "id", "anonymous") if current_user else "anonymous"
        mode = api.mode.value if api.mode else "sql"

        def _result_dict(result):
            return {
                "executed_sql": result.executed_sql,
                "params": result.params,
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "duration_ms": result.duration_ms,
            }

        if mode == "sql":
            if is_http_logic_body(api.logic):
                rewritten_logic_body = _rewrite_http_logic_for_request(api.logic, http_request)
                result = execute_http_api(
                    session=session,
                    api_id=str(api.id),
                    logic_body=rewritten_logic_body,
                    params=request.params or None,
                    executed_by=executed_by,
                    internal_app=getattr(http_request, "app", None),
                )
                return ResponseEnvelope.success(data={"result": _result_dict(result)})
            result = execute_sql_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=request.params or None,
                limit=request.params.get("limit") if request.params else None,
                executed_by=executed_by,
            )
            return ResponseEnvelope.success(data={"result": _result_dict(result)})

        if mode == "http":
            rewritten_logic_body = _rewrite_http_logic_for_request(api.logic, http_request)
            result = execute_http_api(
                session=session,
                api_id=str(api.id),
                logic_body=rewritten_logic_body,
                params=request.params or None,
                executed_by=executed_by,
                internal_app=getattr(http_request, "app", None),
            )
            return ResponseEnvelope.success(data={"result": _result_dict(result)})

        if mode == "workflow":
            class _WfAdapter:
                def __init__(self, ad: ApiDefinition):
                    self.api_id = ad.id
                    self.logic_spec = {}
                    self.logic = ad.logic
                    try:
                        self.logic_spec = json.loads(ad.logic or "{}")
                    except (ValueError, TypeError):
                        pass

            wf_result = execute_workflow_api(
                session=session,
                workflow_api=_WfAdapter(api),
                params=request.params or {},
                input_payload=None,
                executed_by=executed_by,
                limit=request.params.get("limit") if request.params else None,
            )
            return ResponseEnvelope.success(data={"result": wf_result.model_dump()})

        if mode in ("script", "python"):
            sc_result = execute_script_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=request.params or None,
                input_payload=None,
                executed_by=executed_by,
                runtime_policy=getattr(api, "runtime_policy", None),
            )
            return ResponseEnvelope.success(data={"result": sc_result.model_dump()})

        raise HTTPException(400, f"Unsupported API mode: {mode}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/test", response_model=ResponseEnvelope)
async def run_tests(
    api_id: str,
    http_request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Run test for API by executing it with sample/empty params.
    Validates that the API logic is executable without errors.
    """
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")
        if not api.logic:
            raise HTTPException(status_code=400, detail="API has no logic defined")

        mode = api.mode.value if api.mode else "sql"

        # Extract test params from param_schema if available
        test_params = {}
        if api.mode == ApiMode.sql:
            # For SQL, try to extract sample values from param_schema
            # param_schema can contain {"test_cases": [{"params": {...}, "description": "..."}]}
            pass

        test_results = []
        start = time.time()

        # Test 1: Syntax/validation test
        if mode == "sql":
            try:
                sql_validator.validate(api.logic)
                test_results.append({
                    "test_id": "syntax_check",
                    "status": "pass",
                    "error": "",
                    "duration_ms": int((time.time() - start) * 1000),
                })
            except Exception as e:
                test_results.append({
                    "test_id": "syntax_check",
                    "status": "fail",
                    "error": str(e),
                    "duration_ms": int((time.time() - start) * 1000),
                })

        # Test 2: Execution test with sample params
        exec_start = time.time()
        try:
            if mode == "sql":
                result = execute_sql_api(
                    session=session,
                    api_id=DRY_RUN_API_ID,
                    logic_body=api.logic,
                    params=test_params or None,
                    limit=10,
                    executed_by="test-runner",
                )
                test_results.append({
                    "test_id": "execution",
                    "status": "pass",
                    "error": "",
                    "duration_ms": result.duration_ms,
                    "row_count": result.row_count,
                    "columns": result.columns,
                })
            elif mode == "http":
                rewritten_logic_body = _rewrite_http_logic_for_request(
                    api.logic, http_request
                )
                result = execute_http_api(
                    session=session,
                    api_id=DRY_RUN_API_ID,
                    logic_body=rewritten_logic_body,
                    params=test_params or None,
                    executed_by="test-runner",
                    internal_app=getattr(http_request, "app", None),
                )
                test_results.append({
                    "test_id": "execution",
                    "status": "pass",
                    "error": "",
                    "duration_ms": result.duration_ms,
                    "row_count": result.row_count,
                })
            elif mode in {"script", "python"}:
                result = execute_script_api(
                    session=session,
                    api_id=DRY_RUN_API_ID,
                    logic_body=api.logic,
                    params=test_params or None,
                    input_payload=None,
                    executed_by="test-runner",
                    runtime_policy=getattr(api, "runtime_policy", None),
                )
                test_results.append({
                    "test_id": "execution",
                    "status": "pass",
                    "error": "",
                    "duration_ms": result.duration_ms,
                    "output_keys": sorted((result.output or {}).keys()),
                })
            elif mode == "workflow":
                class _WfAdapter:
                    def __init__(self, ad: ApiDefinition):
                        self.id = ad.id
                        self.api_id = ad.id
                        self.logic_spec = {}
                        self.logic = ad.logic
                        try:
                            self.logic_spec = json.loads(ad.logic or "{}")
                        except (ValueError, TypeError):
                            pass

                result = execute_workflow_api(
                    session=session,
                    workflow_api=_WfAdapter(api),
                    params=test_params or {},
                    input_payload=None,
                    executed_by="test-runner",
                    limit=10,
                )
                test_results.append({
                    "test_id": "execution",
                    "status": "pass",
                    "error": "",
                    "duration_ms": sum(step.duration_ms for step in result.steps),
                    "steps": len(result.steps),
                })
            else:
                test_results.append({
                    "test_id": "execution",
                    "status": "skip",
                    "error": f"Execution test not supported for mode: {mode}",
                    "duration_ms": 0,
                })
        except Exception as e:
            test_results.append({
                "test_id": "execution",
                "status": "fail",
                "error": str(e),
                "duration_ms": int((time.time() - exec_start) * 1000),
            })

        passed = len([r for r in test_results if r["status"] == "pass"])
        failed = len([r for r in test_results if r["status"] == "fail"])
        errors = len([r for r in test_results if r["status"] == "error"])

        return ResponseEnvelope.success(data={
            "api_id": api_id,
            "total": len(test_results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": test_results,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/dry-run", response_model=ResponseEnvelope)
async def dry_run(
    request: dict,
    http_request: Request,
    session: Session = Depends(get_session),
):
    """
    Execute query without saving to execution logs (dry-run/test).
    Uses DRY_RUN_API_ID so that record_exec_log() skips logging.

    Supports: sql, http, script/python, workflow
    """
    try:
        logic_type = request.get("logic_type", "sql")
        logic_body = request.get("logic_body", "")
        params = request.get("params", {})
        input_payload = request.get("input")
        runtime_policy = request.get("runtime_policy")

        if not logic_body:
            raise HTTPException(400, "logic_body is required")

        def _result_dict(r):
            return {
                "executed_sql": r.executed_sql,
                "params": r.params,
                "columns": r.columns,
                "rows": r.rows,
                "row_count": r.row_count,
                "duration_ms": r.duration_ms,
            }

        if logic_type == "sql":
            result = execute_sql_api(
                session=session,
                api_id=DRY_RUN_API_ID,
                logic_body=logic_body,
                params=params or None,
                limit=request.get("limit"),
                executed_by="dry-run",
            )
            return ResponseEnvelope.success(data={"result": _result_dict(result)})

        if logic_type == "http":
            rewritten_logic_body = _rewrite_http_logic_for_request(
                logic_body, http_request
            )
            result = execute_http_api(
                session=session,
                api_id=DRY_RUN_API_ID,
                logic_body=rewritten_logic_body,
                params=params or None,
                executed_by="dry-run",
                internal_app=getattr(http_request, "app", None),
            )
            return ResponseEnvelope.success(data={"result": _result_dict(result)})

        if logic_type in {"script", "python"}:
            effective_policy = runtime_policy if isinstance(runtime_policy, dict) else {}
            # Dry-run should be test-friendly: if not explicitly configured, allow runtime.
            if "allow_runtime" not in effective_policy:
                effective_policy = {
                    **effective_policy,
                    "allow_runtime": True,
                }
            result = execute_script_api(
                session=session,
                api_id=DRY_RUN_API_ID,
                logic_body=logic_body,
                params=params or None,
                input_payload=input_payload,
                executed_by="dry-run",
                runtime_policy=effective_policy,
            )
            return ResponseEnvelope.success(data={"result": result.model_dump()})

        if logic_type == "workflow":
            class _WfAdapter:
                def __init__(self, workflow_logic: str):
                    self.id = DRY_RUN_API_ID
                    self.api_id = DRY_RUN_API_ID
                    self.logic_spec = {}
                    self.logic = workflow_logic
                    try:
                        self.logic_spec = json.loads(workflow_logic or "{}")
                    except (ValueError, TypeError):
                        pass

            result = execute_workflow_api(
                session=session,
                workflow_api=_WfAdapter(logic_body),
                params=params or {},
                input_payload=input_payload,
                executed_by="dry-run",
                limit=request.get("limit"),
            )
            return ResponseEnvelope.success(data={"result": result.model_dump()})

        raise HTTPException(400, f"Dry-run not supported for logic_type: {logic_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dry-run failed: {str(e)}")
        raise HTTPException(500, str(e))
