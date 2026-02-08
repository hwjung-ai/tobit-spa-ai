"""API Manager routes for dynamic API management"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.routing import APIRoute
from models.api_definition import (
    ApiDefinition,
    ApiDefinitionVersion,
    ApiMode,
    ApiScope,
)
from pydantic import BaseModel
from schemas import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.auth.models import TbUser

from .crud import DRY_RUN_API_ID, list_exec_logs
from .executor import execute_http_api, execute_sql_api
from .script_executor import execute_script_api
from .services.sql_validator import SQLValidator
from .workflow_executor import execute_workflow_api

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])

sql_validator = SQLValidator()


def _api_snapshot(api: ApiDefinition) -> dict:
    return {
        "id": str(api.id),
        "scope": api.scope.value if hasattr(api.scope, "value") else str(api.scope),
        "name": api.name,
        "method": api.method,
        "path": api.path,
        "description": api.description,
        "tags": api.tags or [],
        "mode": api.mode.value if api.mode else None,
        "logic": api.logic,
        "runtime_policy": api.runtime_policy or {},
        "is_enabled": api.is_enabled,
        "created_at": api.created_at.isoformat() if api.created_at else None,
        "updated_at": api.updated_at.isoformat() if api.updated_at else None,
    }


def _next_version(session: Session, api_id: uuid.UUID) -> int:
    statement = (
        select(ApiDefinitionVersion)
        .where(ApiDefinitionVersion.api_id == api_id)
        .order_by(ApiDefinitionVersion.version.desc())
        .limit(1)
    )
    latest = session.exec(statement).first()
    return (latest.version + 1) if latest else 1


def _record_api_version(
    session: Session,
    api: ApiDefinition,
    *,
    change_type: str,
    created_by: str | None,
    change_summary: str | None = None,
) -> ApiDefinitionVersion:
    version_row = ApiDefinitionVersion(
        api_id=api.id,
        version=_next_version(session, api.id),
        change_type=change_type,
        change_summary=change_summary,
        snapshot=_api_snapshot(api),
        created_by=created_by,
    )
    session.add(version_row)
    session.commit()
    session.refresh(version_row)
    return version_row


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


@router.get("/apis", response_model=ResponseEnvelope)
async def list_apis(
    scope: Optional[str] = Query(None), session: Session = Depends(get_session)
):
    """List all available APIs (public endpoint - no authentication required)"""

    try:
        statement = select(ApiDefinition).where(ApiDefinition.deleted_at.is_(None))

        if scope:
            try:
                scope_enum = ApiScope(scope)
                statement = statement.where(ApiDefinition.scope == scope_enum)
            except ValueError:
                pass

        apis = session.exec(statement).all()

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

        return ResponseEnvelope.success(data={"apis": api_list})

    except Exception as e:
        logger.error(f"List APIs failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/system/endpoints", response_model=ResponseEnvelope)
async def list_discovered_endpoints(request: Request):
    """Discover all API endpoints from the current FastAPI app."""
    try:
        openapi = request.app.openapi() or {}
        paths = openapi.get("paths") or {}
        if not isinstance(paths, dict):
            paths = {}

        discovered: dict[tuple[str, str], dict] = {}
        for path, operations in paths.items():
            if not isinstance(operations, dict):
                continue
            for method, operation in operations.items():
                method_upper = str(method).upper()
                if method_upper in {"HEAD", "OPTIONS"}:
                    continue
                if not isinstance(operation, dict):
                    continue
                discovered[(method_upper, path)] = {
                    "method": method_upper,
                    "path": path,
                    "operationId": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "description": operation.get("description"),
                    "tags": operation.get("tags") or [],
                    "parameters": operation.get("parameters") or [],
                    "requestBody": operation.get("requestBody"),
                    "responses": operation.get("responses") or {},
                    "source": "openapi",
                }

        if not discovered:
            for route in request.app.routes:
                if not isinstance(route, APIRoute):
                    continue
                methods = sorted((route.methods or set()) - {"HEAD", "OPTIONS"})
                for method in methods:
                    discovered[(method, route.path)] = {
                        "method": method,
                        "path": route.path,
                        "operationId": route.operation_id,
                        "summary": route.summary,
                        "description": route.description,
                        "tags": route.tags or [],
                        "parameters": [],
                        "requestBody": None,
                        "responses": {},
                        "source": "router",
                    }

        endpoints = [
            discovered[key]
            for key in sorted(discovered.keys(), key=lambda item: (item[1], item[0]))
        ]
        return ResponseEnvelope.success(
            data={"endpoints": endpoints, "count": len(endpoints)}
        )
    except Exception as e:
        logger.error(f"Discover endpoints failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/system/endpoints/register", response_model=ResponseEnvelope)
async def register_discovered_endpoints(
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Discover FastAPI endpoints and upsert them as system APIs."""
    try:
        discovery_response = await list_discovered_endpoints(request)
        discovered = (
            (discovery_response.data or {}).get("endpoints", [])
            if hasattr(discovery_response, "data")
            else []
        )
        created = 0
        updated = 0
        skipped = 0
        for endpoint in discovered:
            path = endpoint.get("path")
            method = str(endpoint.get("method") or "").upper()
            if not path or not method:
                skipped += 1
                continue
            existing = session.exec(
                select(ApiDefinition)
                .where(ApiDefinition.path == path)
                .where(ApiDefinition.method == method)
                .where(ApiDefinition.deleted_at.is_(None))
                .limit(1)
            ).first()
            if existing:
                existing.scope = ApiScope.system
                existing.name = existing.name or endpoint.get("operationId") or f"{method} {path}"
                existing.description = existing.description or endpoint.get("summary")
                existing.tags = endpoint.get("tags") or existing.tags or []
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                updated += 1
                continue
            api = ApiDefinition(
                scope=ApiScope.system,
                name=endpoint.get("operationId") or endpoint.get("summary") or f"{method} {path}",
                method=method,
                path=path,
                description=endpoint.get("summary") or endpoint.get("description"),
                tags=endpoint.get("tags") or [],
                mode=ApiMode.http,
                logic='{"method":"GET","url":"http://127.0.0.1:8000/health"}',
                is_enabled=True,
            )
            session.add(api)
            session.flush()
            _record_api_version(
                session,
                api,
                change_type="create",
                created_by=getattr(current_user, "id", None),
                change_summary="Auto-registered from OpenAPI discovery",
            )
            created += 1
        session.commit()
        return ResponseEnvelope.success(
            data={
                "discovered": len(discovered),
                "created": created,
                "updated": updated,
                "skipped": skipped,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register discovered endpoints failed: {str(e)}")
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


@router.post("/apis", response_model=ResponseEnvelope)
async def create_or_update_api(
    request: SaveApiRequest,
    api_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
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
        _record_api_version(
            session,
            api,
            change_type="update" if api_id else "create",
            created_by=getattr(current_user, "id", None),
            change_summary="Saved from /api-manager/apis",
        )

        return ResponseEnvelope.success(data={
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
        })
    except Exception as e:
        logger.error(f"Create/update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/create", response_model=ResponseEnvelope)
async def create_api(
    request: CreateApiRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Create new dynamic API (legacy endpoint).
    Prefer POST /apis for new integrations.
    """
    try:
        api_scope = (
            ApiScope(request.scope)
            if request.scope in [s.value for s in ApiScope]
            else ApiScope.custom
        )
        api_mode = (
            ApiMode(request.mode)
            if request.mode in [m.value for m in ApiMode]
            else ApiMode.sql
        )

        api = ApiDefinition(
            scope=api_scope,
            name=request.name,
            method=request.method.upper(),
            path=request.path,
            description=request.description,
            mode=api_mode,
            logic=request.logic,
            is_enabled=True,
        )
        session.add(api)
        session.commit()
        session.refresh(api)
        _record_api_version(
            session,
            api,
            change_type="create",
            created_by=getattr(current_user, "id", None),
            change_summary="Created from legacy /api-manager/create",
        )

        return ResponseEnvelope.success(data={
            "id": str(api.id),
            "scope": api.scope.value,
            "name": api.name,
            "method": api.method,
            "path": api.path,
            "mode": api.mode.value if api.mode else None,
            "logic": api.logic,
            "is_enabled": api.is_enabled,
            "version": 1,
        })

    except Exception as e:
        logger.error(f"Create API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{api_id}", response_model=ResponseEnvelope)
async def get_api(
    api_id: str,
    session: Session = Depends(get_session),
):
    """Get API definition by ID"""
    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        return ResponseEnvelope.success(data={
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
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.put("/apis/{api_id}", response_model=ResponseEnvelope)
async def update_api(
    api_id: str,
    request: SaveApiRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Update API definition
    """

    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Map frontend field names to backend field names
        api_mode = (
            ApiMode(request.logic_type)
            if request.logic_type in [m.value for m in ApiMode]
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
        _record_api_version(
            session,
            api,
            change_type="update",
            created_by=getattr(current_user, "id", None),
            change_summary="Updated from PUT /api-manager/apis/{api_id}",
        )

        return ResponseEnvelope.success(data={
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
        })

    except Exception as e:
        logger.error(f"Update API failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/rollback", response_model=ResponseEnvelope)
async def rollback_api(
    api_id: str,
    version: Optional[int] = Query(None, description="Target version to rollback to"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """Rollback API to a previous version snapshot."""
    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        version_statement = (
            select(ApiDefinitionVersion)
            .where(ApiDefinitionVersion.api_id == api.id)
            .order_by(ApiDefinitionVersion.version.desc())
        )
        rows = session.exec(version_statement).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No version history found")

        current_version = rows[0]
        target = None
        if version is not None:
            target = next((row for row in rows if row.version == version), None)
            if not target:
                raise HTTPException(status_code=404, detail=f"Version {version} not found")
        else:
            target = rows[1] if len(rows) > 1 else rows[0]

        snapshot = target.snapshot or {}
        try:
            api.scope = ApiScope(snapshot.get("scope", api.scope.value if hasattr(api.scope, "value") else str(api.scope)))
        except ValueError:
            pass
        api.name = snapshot.get("name", api.name)
        api.method = snapshot.get("method", api.method)
        api.path = snapshot.get("path", api.path)
        api.description = snapshot.get("description")
        api.tags = snapshot.get("tags", api.tags)
        mode_value = snapshot.get("mode")
        if mode_value:
            try:
                api.mode = ApiMode(mode_value)
            except ValueError:
                pass
        api.logic = snapshot.get("logic", api.logic)
        api.runtime_policy = snapshot.get("runtime_policy", api.runtime_policy)
        api.is_enabled = bool(snapshot.get("is_enabled", api.is_enabled))
        api.updated_at = datetime.utcnow()

        session.add(api)
        session.commit()
        session.refresh(api)

        new_version = _record_api_version(
            session,
            api,
            change_type="rollback",
            created_by=getattr(current_user, "id", None),
            change_summary=f"Rolled back from v{current_version.version} to v{target.version}",
        )

        return ResponseEnvelope.success(
            data={
                "api_id": api_id,
                "rolled_back_to_version": target.version,
                "new_version": new_version.version,
                "snapshot": _api_snapshot(api),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{api_id}/versions", response_model=ResponseEnvelope)
async def get_versions(
    api_id: str,
    session: Session = Depends(get_session),
):
    """Get API version history."""
    try:
        api = session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        statement = (
            select(ApiDefinitionVersion)
            .where(ApiDefinitionVersion.api_id == api.id)
            .order_by(ApiDefinitionVersion.version.desc())
        )
        rows = session.exec(statement).all()
        current = rows[0].version if rows else None
        versions = [
            {
                "version": row.version,
                "change_type": row.change_type,
                "change_summary": row.change_summary,
                "created_by": row.created_by,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "is_current": row.version == current,
                "snapshot": row.snapshot,
            }
            for row in rows
        ]

        return ResponseEnvelope.success(data={"api_id": api_id, "versions": versions})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get versions failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{api_id}/validate-sql", response_model=ResponseEnvelope)
async def validate_sql(
    api_id: str, sql: str = Query(...), current_user: TbUser = Depends(get_current_user)
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
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
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
            result = execute_http_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=request.params or None,
                executed_by=executed_by,
            )
            return ResponseEnvelope.success(data={"result": _result_dict(result)})

        if mode == "workflow":
            import json as _json

            class _WfAdapter:
                def __init__(self, ad: ApiDefinition):
                    self.api_id = ad.id
                    self.logic_spec = {}
                    self.logic = ad.logic
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
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
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
                import json as _json

                class _WfAdapter:
                    def __init__(self, ad: ApiDefinition):
                        self.id = ad.id
                        self.api_id = ad.id
                        self.logic_spec = {}
                        self.logic = ad.logic
                        try:
                            self.logic_spec = _json.loads(ad.logic or "{}")
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


@router.get("/apis/{api_id}/execution-logs", response_model=ResponseEnvelope)
async def get_logs(
    api_id: str,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """Get API execution history from available execution log table(s)."""
    try:
        logs = list_exec_logs(session, api_id, limit)
        log_list = []
        for log in logs:
            exec_id = getattr(log, "exec_id", None) or getattr(log, "id", None)
            executed_at = getattr(log, "executed_at", None) or getattr(
                log, "execution_time", None
            )
            status = getattr(log, "status", None) or getattr(log, "response_status", None)
            row_count = getattr(log, "row_count", None)
            if row_count is None:
                row_count = getattr(log, "rows_affected", 0)
            log_list.append(
                {
                    "exec_id": str(exec_id) if exec_id else None,
                    "api_id": str(log.api_id),
                    "executed_at": executed_at.isoformat() if executed_at else None,
                    "executed_by": log.executed_by,
                    "status": status,
                    "duration_ms": log.duration_ms,
                    "row_count": row_count,
                    "request_params": log.request_params,
                    "error_message": log.error_message,
                }
            )
        return ResponseEnvelope.success(data={"api_id": api_id, "logs": log_list})
    except Exception as e:
        logger.error(f"Get logs failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/apis/{api_id}", response_model=ResponseEnvelope)
async def delete_api(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
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

        return ResponseEnvelope.success(message=f"API {api_id} deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/dry-run", response_model=ResponseEnvelope)
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
            result = execute_http_api(
                session=session,
                api_id=DRY_RUN_API_ID,
                logic_body=logic_body,
                params=params or None,
                executed_by="dry-run",
            )
            return ResponseEnvelope.success(data={"result": _result_dict(result)})

        raise HTTPException(400, f"Dry-run not supported for logic_type: {logic_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dry-run failed: {str(e)}")
        raise HTTPException(500, str(e))
