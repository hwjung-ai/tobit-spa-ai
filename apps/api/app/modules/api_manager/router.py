from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session

from core.config import get_settings
from core.db import get_session
from schemas.common import ResponseEnvelope
from .crud import (
    create_api_definition,
    get_api_definition,
    list_api_definitions,
    list_exec_logs,
    update_api_definition,
)
from .executor import execute_sql_api, execute_http_api
from .script_executor import execute_script_api
from .workflow_executor import execute_workflow_api
from .schemas import (
    ApiDefinitionCreate,
    ApiDefinitionRead,
    ApiDefinitionUpdate,
    ApiExecuteRequest,
    ApiDryRunRequest,
    ApiExecLogRead,
    ApiType,
)

router = APIRouter(prefix="/api-manager", tags=["api-manager"])

@router.get("/apis")
def list_defs(
    api_type: ApiType | None = Query(None),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    items = list_api_definitions(session, api_type)
    payload = [ApiDefinitionRead.from_orm(item).model_dump() for item in items]
    return ResponseEnvelope.success(data={"apis": payload})


@router.get("/system/endpoints")
def list_system_endpoints(request: Request) -> ResponseEnvelope:
    settings = get_settings()
    if not settings.enable_system_apis:
        raise HTTPException(status_code=404, detail="System endpoints are disabled")
    openapi = request.app.openapi()
    endpoints: list[dict[str, object]] = []
    paths = openapi.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, meta in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            if not isinstance(meta, dict):
                continue
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operationId": meta.get("operationId"),
                    "summary": meta.get("summary"),
                    "description": meta.get("description"),
                    "tags": meta.get("tags", []),
                    "parameters": meta.get("parameters", []),
                    "requestBody": meta.get("requestBody"),
                    "responses": meta.get("responses"),
                    "source": "openapi",
                }
            )
    return ResponseEnvelope.success(data={"endpoints": endpoints})


@router.get("/apis/{api_id}")
def get_def(api_id: str, session: Session = Depends(get_session)) -> ResponseEnvelope:
    item = get_api_definition(session, api_id)
    if not item:
        raise HTTPException(status_code=404, detail="API not found")
    payload = ApiDefinitionRead.from_orm(item).model_dump()
    return ResponseEnvelope.success(data={"api": payload})


@router.post("/apis")
def create_def(payload: ApiDefinitionCreate, session: Session = Depends(get_session)) -> ResponseEnvelope:
    if payload.api_type != "custom":
        raise HTTPException(status_code=400, detail="Only custom APIs can be created via this endpoint")
    try:
        created = create_api_definition(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"api": ApiDefinitionRead.from_orm(created).model_dump()})


@router.put("/apis/{api_id}")
def update_def(
    api_id: str,
    payload: ApiDefinitionUpdate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    item = get_api_definition(session, api_id)
    if not item:
        raise HTTPException(status_code=404, detail="API not found")
    try:
        updated = update_api_definition(session, item, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"api": ApiDefinitionRead.from_orm(updated).model_dump()})


@router.post("/apis/{api_id}/execute")
def execute_api(
    api_id: str,
    payload: ApiExecuteRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    api = get_api_definition(session, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    if not api.logic_body:
        raise HTTPException(status_code=400, detail="Logic body is required for execution")
    executed_by = payload.executed_by or "ops-builder"
    if api.logic_type == "sql":
        result = execute_sql_api(
            session=session,
            api_id=api_id,
            logic_body=api.logic_body,
            params=payload.params,
            limit=payload.limit,
            executed_by=executed_by,
        )
        payload_result = result.model_dump()
    elif api.logic_type in ("script", "python"):
        script_result = execute_script_api(
            session=session,
            api_id=api_id,
            logic_body=api.logic_body,
            params=payload.params,
            input_payload=payload.input,
            executed_by=executed_by,
            runtime_policy=api.runtime_policy,
        )
        payload_result = script_result.model_dump()
    elif api.logic_type == "workflow":
        workflow_result = execute_workflow_api(
            session=session,
            workflow_api=api,
            params=payload.params,
            input_payload=payload.input,
            executed_by=executed_by,
            limit=payload.limit,
        )
        payload_result = workflow_result.model_dump()
    elif api.logic_type == "http":
        http_result = execute_http_api(
            session=session,
            api_id=api_id,
            logic_body=api.logic_body,
            params=payload.params,
            executed_by=executed_by,
        )
        payload_result = http_result.model_dump()
    else:
        raise HTTPException(status_code=400, detail="Logic type cannot be executed")
    return ResponseEnvelope.success(data={"result": payload_result})


@router.post("/dry-run")
def dry_run_api(
    payload: ApiDryRunRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    dummy_api_id = "00000000-0000-0000-0000-000000000000"
    executed_by = "dry-run-user"
    if payload.logic_type == "sql":
        result = execute_sql_api(
            session=session,
            api_id=dummy_api_id,
            logic_body=payload.logic_body,
            params=payload.params,
            limit=200,
            executed_by=executed_by,
        )
        payload_result = result.model_dump()
    elif payload.logic_type in ("script", "python"):
        script_result = execute_script_api(
            session=session,
            api_id=dummy_api_id,
            logic_body=payload.logic_body,
            params=payload.params,
            input_payload=payload.input,
            executed_by=executed_by,
            runtime_policy=payload.runtime_policy,
        )
        payload_result = script_result.model_dump()
    elif payload.logic_type == "http":
        http_result = execute_http_api(
            session=session,
            api_id=dummy_api_id,
            logic_body=payload.logic_body,
            params=payload.params,
            executed_by=executed_by,
        )
        payload_result = http_result.model_dump()
    else:
        raise HTTPException(status_code=400, detail="Dry run not supported for this logic type")
    return ResponseEnvelope.success(data={"result": payload_result})


@router.get("/apis/{api_id}/exec-logs")
def list_exec_logs_endpoint(
    api_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    api = get_api_definition(session, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    logs = list_exec_logs(session, api_id, limit=limit)
    payload = [ApiExecLogRead.from_orm(item).model_dump() for item in logs]
    return ResponseEnvelope.success(data={"logs": payload})
