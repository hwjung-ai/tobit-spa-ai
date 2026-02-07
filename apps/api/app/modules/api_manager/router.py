"""API Manager routes for dynamic API management"""

import logging
from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from models.api_definition import ApiDefinition, ApiMode, ApiScope
from pydantic import BaseModel
from sqlmodel import Session, select

from .crud import DRY_RUN_API_ID, list_exec_logs
from .executor import execute_http_api, execute_sql_api
from .script_executor import execute_script_api
from .services.api_service import ApiManagerService
from .services.sql_validator import SQLValidator
from .services.test_runner import ApiTestRunner
from .workflow_executor import execute_workflow_api

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])

# Initialize services
sql_validator = SQLValidator()
api_service = ApiManagerService(sql_validator=sql_validator)
test_runner = ApiTestRunner(api_service=api_service)


class CreateApiRequest(BaseModel):
    """Request to create new API"""

    name: str
    method: str
    path: str
    mode: str  # sql, python, workflow
    logic: str
    scope: str = "custom"
    input_schema: dict = {}
    output_schema: dict = {}
    description: Optional[str] = None


class UpdateApiRequest(BaseModel):
    """Request to update API"""

    name: Optional[str] = None
    logic: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    description: Optional[str] = None


class ExecuteApiRequest(BaseModel):
    """Request to execute API"""

    params: dict = {}


@router.get("/apis", response_model=dict)
async def list_apis(
    scope: Optional[str] = Query(None), session: Session = Depends(get_session)
):
    """List all available APIs (public endpoint - no authentication required)"""

    try:
        # Build query
        statement = select(ApiDefinition).where(ApiDefinition.deleted_at.is_(None))

        # Filter by scope if provided
        if scope:
            try:
                scope_enum = ApiScope(scope)
                statement = statement.where(ApiDefinition.scope == scope_enum)
            except ValueError:
                # Invalid scope, just return empty
                pass

        # Execute query
        apis = session.exec(statement).all()

        # Convert to dict format
        api_list = [
            {
                "id": str(api.id),
                "scope": api.scope.value,
                "name": api.name,
                "method": api.method,
                "path": api.path,
                "description": api.description,
                "tags": api.tags or [],
                "mode": api.mode.value if api.mode else None,
                "logic": api.logic,
                "is_enabled": api.is_enabled,
                "created_at": api.created_at.isoformat() if api.created_at else None,
                "updated_at": api.updated_at.isoformat() if api.updated_at else None,
            }
            for api in apis
        ]

        return {"status": "ok", "data": {"apis": api_list}}

    except Exception as e:
        logger.error(f"List APIs failed: {str(e)}")
        raise HTTPException(500, str(e))


class SaveApiRequest(BaseModel):
    """Request to save/create API from frontend"""

    api_name: str
    api_type: str  # "system" or "custom"
    method: str
    endpoint: str
    description: Optional[str] = None
    tags: list[str] = []
    logic_type: str  # "sql", "python", "workflow", "script", "http"
    logic_body: str
    param_schema: dict = {}
    runtime_policy: dict = {}
    logic_spec: dict = {}
    is_active: bool = True
    created_by: Optional[str] = None


@router.post("/apis", response_model=dict)
async def create_or_update_api(
    request: SaveApiRequest,
    api_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Create or update API definition"""
    try:
        # Map frontend field names to backend field names
        api_scope = (
            ApiScope(request.api_type)
            if request.api_type in ["system", "custom"]
            else ApiScope.custom
        )
        api_mode = (
            ApiMode(request.logic_type)
            if request.logic_type in [m.value for m in ApiMode]
            else ApiMode.sql
        )

        if api_id:
            # Update existing API
            api = session.get(ApiDefinition, api_id)
            if not api or api.deleted_at:
                raise HTTPException(status_code=404, detail="API not found")

            api.name = request.api_name
            api.method = request.method.upper()
            api.path = request.endpoint
            api.description = request.description
            api.tags = request.tags
            api.mode = api_mode
            api.logic = (
                request.logic_body
                if request.logic_type == "sql"
                else request.logic_body
            )
            api.updated_at = datetime.utcnow()
        else:
            # Create new API
            api = ApiDefinition(
                scope=api_scope,
                name=request.api_name,
                method=request.method.upper(),
                path=request.endpoint,
                description=request.description,
                tags=request.tags,
                mode=api_mode,
                logic=request.logic_body,
                is_enabled=request.is_active,
            )
            session.add(api)

        session.commit()
        session.refresh(api)

        # Return response in expected format
        return {
            "status": "ok",
            "data": {
                "api": {
                    "id": str(api.id),
                    "scope": api.scope.value,
                    "name": api.name,
                    "method": api.method,
                    "path": api.path,
                    "description": api.description,
                    "tags": api.tags or [],
                    "mode": api.mode.value if api.mode else None,
                    "logic": api.logic,
                    "is_enabled": api.is_enabled,
                    "created_at": api.created_at.isoformat()
                    if api.created_at
                    else None,
                    "updated_at": api.updated_at.isoformat()
                    if api.updated_at
                    else None,
                }
            },
        }
    except Exception as e:
        logger.error(f"Create/update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/create", response_model=dict)
async def create_api(
    request: CreateApiRequest, current_user: dict = Depends(get_current_user)
):
    """
    Create new dynamic API

    Modes:
    - sql: Execute SQL queries
    - python: Execute Python code
    - workflow: Compose tools

    Returns created API definition with version 1
    """

    try:
        api = await api_service.create_api(request.dict(), current_user)

        return {"status": "ok", "data": api}

    except Exception as e:
        logger.error(f"Create API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}", response_model=dict)
async def get_api(api_id: str, current_user: dict = Depends(get_current_user)):
    """Get API definition"""

    try:
        # In real implementation: db.get(ApiDefinition, api_id)
        api = {"id": api_id, "name": "Example API", "version": 1, "status": "active"}

        return {"status": "ok", "data": api}

    except Exception as e:
        logger.error(f"Get API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.put("/apis/{api_id}", response_model=dict)
async def update_api(
    api_id: str,
    request: SaveApiRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Update API definition
    """

    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Map frontend field names to backend field names
        ApiScope(request.api_type) if request.api_type in [
            "system",
            "custom",
        ] else ApiScope.custom
        api_mode = (
            ApiMode(request.logic_type)
            if request.logic_type in ["sql", "python", "workflow"]
            else ApiMode.sql
        )

        # Update fields
        api.name = request.api_name
        api.method = request.method.upper()
        api.path = request.endpoint
        api.description = request.description
        api.tags = request.tags
        api.mode = api_mode
        api.logic = request.logic_body
        api.is_enabled = request.is_active
        api.updated_at = datetime.utcnow()

        session.add(api)
        session.commit()
        session.refresh(api)

        # Return response in expected format
        return {
            "status": "ok",
            "data": {
                "api": {
                    "id": str(api.id),
                    "scope": api.scope.value,
                    "name": api.name,
                    "method": api.method,
                    "path": api.path,
                    "description": api.description,
                    "tags": api.tags or [],
                    "mode": api.mode.value if api.mode else None,
                    "logic": api.logic,
                    "is_enabled": api.is_enabled,
                    "created_at": api.created_at.isoformat()
                    if api.created_at
                    else None,
                    "updated_at": api.updated_at.isoformat()
                    if api.updated_at
                    else None,
                }
            },
        }

    except Exception as e:
        logger.error(f"Update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/rollback", response_model=dict)
async def rollback_api(
    api_id: str,
    target_version: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Rollback API to previous version

    Args:
        api_id: API ID
        target_version: Version to rollback to
    """

    try:
        api = await api_service.rollback_api(api_id, target_version, current_user)

        return {
            "status": "ok",
            "message": f"Rolled back to version {target_version}",
            "data": api,
        }

    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}/versions", response_model=dict)
async def get_versions(api_id: str, current_user: dict = Depends(get_current_user)):
    """Get version history"""

    try:
        versions = await api_service.get_api_versions(api_id)

        return {"status": "ok", "api_id": api_id, "versions": versions}

    except Exception as e:
        logger.error(f"Get versions failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/validate-sql", response_model=dict)
async def validate_sql(
    api_id: str, sql: str = Query(...), current_user: dict = Depends(get_current_user)
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

        return {
            "status": "ok",
            "is_safe": validation.is_safe,
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "metadata": validation.metadata,
        }

    except Exception as e:
        logger.error(f"SQL validation failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/apis/{api_id}/execute", response_model=dict)
async def execute_api(
    api_id: str,
    request: ExecuteApiRequest,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Execute API with parameters using real executors.
    Dispatches to sql/http/workflow/script based on API mode.
    """
    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")
        if not api.logic:
            raise HTTPException(status_code=400, detail="API has no logic defined")

        executed_by = current_user.get("id", "anonymous") if current_user else "anonymous"
        mode = api.mode.value if api.mode else "sql"

        if mode == "sql":
            result = execute_sql_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=request.params or None,
                limit=request.params.get("limit") if request.params else None,
                executed_by=executed_by,
            )
            return {
                "status": "ok",
                "data": {
                    "columns": result.columns,
                    "rows": result.rows,
                    "row_count": result.row_count,
                    "duration_ms": result.duration_ms,
                },
            }

        if mode == "http":
            result = execute_http_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=request.params or None,
                executed_by=executed_by,
            )
            return {
                "status": "ok",
                "data": {
                    "columns": result.columns,
                    "rows": result.rows,
                    "row_count": result.row_count,
                    "duration_ms": result.duration_ms,
                },
            }

        if mode == "workflow":
            # workflow_executor expects TbApiDef with logic_spec/api_id attrs.
            # Build a simple namespace adapter for ApiDefinition.
            class _WfAdapter:
                def __init__(self, ad: ApiDefinition):
                    self.api_id = ad.id
                    self.logic_spec = {}
                    self.logic = ad.logic
                    # Try to parse logic as JSON for workflow spec
                    import json as _json
                    try:
                        self.logic_spec = _json.loads(ad.logic or "{}")
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
            return {
                "status": "ok",
                "data": wf_result.model_dump(),
            }

        if mode in ("script", "python"):
            sc_result = execute_script_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=request.params or None,
                input_payload=None,
                executed_by=executed_by,
                runtime_policy=None,
            )
            return {
                "status": "ok",
                "data": sc_result.model_dump(),
            }

        raise HTTPException(400, f"Unsupported API mode: {mode}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/test", response_model=dict)
async def run_tests(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """
    Run test for API by executing it with sample/empty params.
    Validates that the API logic is executable without errors.
    """
    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")
        if not api.logic:
            raise HTTPException(status_code=400, detail="API has no logic defined")

        mode = api.mode.value if api.mode else "sql"
        executed_by = current_user.get("id", "anonymous") if current_user else "anonymous"

        # Extract test params from param_schema if available
        test_params = {}
        if api.mode == ApiMode.sql:
            # For SQL, try to extract sample values from param_schema
            # param_schema can contain {"test_cases": [{"params": {...}, "description": "..."}]}
            pass

        import time
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
                result = execute_http_api(
                    session=session,
                    api_id=DRY_RUN_API_ID,
                    logic_body=api.logic,
                    params=test_params or None,
                    executed_by="test-runner",
                )
                test_results.append({
                    "test_id": "execution",
                    "status": "pass",
                    "error": "",
                    "duration_ms": result.duration_ms,
                    "row_count": result.row_count,
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

        return {
            "status": "ok",
            "api_id": api_id,
            "total": len(test_results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": test_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/apis/{api_id}/execution-logs", response_model=dict)
async def get_logs(
    api_id: str,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """Get API execution history from tb_api_exec_log table"""
    try:
        logs = list_exec_logs(session, api_id, limit)
        log_list = [
            {
                "exec_id": str(log.exec_id),
                "api_id": str(log.api_id),
                "executed_at": log.executed_at.isoformat() if log.executed_at else None,
                "executed_by": log.executed_by,
                "status": log.status,
                "duration_ms": log.duration_ms,
                "row_count": log.row_count,
                "request_params": log.request_params,
                "error_message": log.error_message,
            }
            for log in logs
        ]
        return {"status": "ok", "data": {"api_id": api_id, "logs": log_list}}
    except Exception as e:
        logger.error(f"Get logs failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/apis/{api_id}", response_model=dict)
async def delete_api(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Delete API (soft delete)"""

    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Soft delete - mark deleted_at timestamp
        api.deleted_at = datetime.utcnow()
        session.add(api)
        session.commit()

        return {"status": "ok", "message": f"API {api_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/dry-run", response_model=dict)
async def dry_run(request: dict, session: Session = Depends(get_session)):
    """
    Execute query without saving to execution logs (dry-run/test).
    Uses DRY_RUN_API_ID so that record_exec_log() skips logging.

    Supports: sql, http
    """
    try:
        logic_type = request.get("logic_type", "sql")
        logic_body = request.get("logic_body", "")
        params = request.get("params", {})

        if not logic_body:
            raise HTTPException(400, "logic_body is required")

        if logic_type == "sql":
            result = execute_sql_api(
                session=session,
                api_id=DRY_RUN_API_ID,
                logic_body=logic_body,
                params=params or None,
                limit=request.get("limit"),
                executed_by="dry-run",
            )
            return {
                "status": "ok",
                "data": {
                    "result": {
                        "executed_sql": result.executed_sql,
                        "params": result.params,
                        "columns": result.columns,
                        "rows": result.rows,
                        "row_count": result.row_count,
                        "duration_ms": result.duration_ms,
                    }
                },
            }

        if logic_type == "http":
            result = execute_http_api(
                session=session,
                api_id=DRY_RUN_API_ID,
                logic_body=logic_body,
                params=params or None,
                executed_by="dry-run",
            )
            return {
                "status": "ok",
                "data": {
                    "result": {
                        "executed_sql": result.executed_sql,
                        "params": result.params,
                        "columns": result.columns,
                        "rows": result.rows,
                        "row_count": result.row_count,
                        "duration_ms": result.duration_ms,
                    }
                },
            }

        raise HTTPException(400, f"Dry-run not supported for logic_type: {logic_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dry-run failed: {str(e)}")
        raise HTTPException(500, str(e))
