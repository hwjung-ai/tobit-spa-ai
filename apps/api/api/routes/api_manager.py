from __future__ import annotations

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from models import ApiDefinition, ApiMode, ApiScope
from schemas import (
    ApiDefinitionCreate,
    ApiDefinitionRead,
    ApiDefinitionUpdate,
    ResponseEnvelope,
)
from services.api_manager import (
    build_test_response,
    create_custom_definition,
    list_api_definitions,
    run_sql_logic,
    soft_delete_definition,
    sync_system_definitions,
    update_definition,
)
from sqlmodel import Session

router = APIRouter(prefix="/api-manager", tags=["api-manager"])


def to_read(definition: ApiDefinition) -> ApiDefinitionRead:
    return ApiDefinitionRead(
        id=str(definition.id),
        scope=definition.scope,
        name=definition.name,
        method=definition.method,
        path=definition.path,
        description=definition.description,
        tags=definition.tags,
        mode=definition.mode,
        logic=definition.logic,
        is_enabled=definition.is_enabled,
    )


@router.get("/apis", response_model=ResponseEnvelope)
def list_definitions(
    session: Session = Depends(get_session),
    scope: ApiScope | None = Query(None),
) -> ResponseEnvelope:
    items = list_api_definitions(session, scope)
    data = [to_read(item).model_dump() for item in items]
    return ResponseEnvelope.success(data={"apis": data})


@router.get("/apis/{api_id}", response_model=ResponseEnvelope)
def get_definition(
    api_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    definition = session.get(ApiDefinition, api_id)
    if not definition or definition.deleted_at:
        raise HTTPException(status_code=404, detail="API not found")
    return ResponseEnvelope.success(data={"api": to_read(definition).model_dump()})


@router.post("/apis", response_model=ResponseEnvelope)
def create_definition(
    payload: ApiDefinitionCreate, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    data = payload.model_dump()
    created = create_custom_definition(session, data)
    return ResponseEnvelope.success(data={"api": to_read(created).model_dump()})


@router.put("/apis/{api_id}", response_model=ResponseEnvelope)
def update_definition_endpoint(
    api_id: str,
    payload: ApiDefinitionUpdate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    definition = session.get(ApiDefinition, api_id)
    if not definition or definition.deleted_at:
        raise HTTPException(status_code=404, detail="API not found")
    if definition.scope == ApiScope.system:
        updates = {
            "description": payload.description,
            "tags": payload.tags,
        }
    else:
        updates = payload.model_dump(
            exclude_unset=True, exclude={"tags"} if payload.tags is None else {}
        )
        if payload.tags is not None:
            updates["tags"] = payload.tags
    updated = update_definition(session, definition, updates)
    return ResponseEnvelope.success(data={"api": to_read(updated).model_dump()})


@router.delete("/apis/{api_id}", response_model=ResponseEnvelope)
def delete_definition(
    api_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    definition = session.get(ApiDefinition, api_id)
    if not definition or definition.deleted_at:
        raise HTTPException(status_code=404, detail="API not found")
    soft_delete_definition(session, definition)
    return ResponseEnvelope.success(data={"deleted": api_id})


@router.post("/apis/{api_id}/test", response_model=ResponseEnvelope)
def test_definition(
    api_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    definition = session.get(ApiDefinition, api_id)
    if not definition or definition.deleted_at:
        raise HTTPException(status_code=404, detail="API not found")
    if definition.scope == ApiScope.system:
        md = f"System API {definition.method} {definition.path} 테스트"
        envelope = build_test_response([], md, "system")
        return ResponseEnvelope.success(data={"answer": envelope.model_dump()})
    if definition.mode == ApiMode.sql and definition.logic:
        try:
            rows = run_sql_logic(session, definition.logic)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        envelope = build_test_response(rows, "Custom SQL test", "custom")
        return ResponseEnvelope.success(data={"answer": envelope.model_dump()})
    raise HTTPException(
        status_code=501, detail="Logic test not implemented for this mode"
    )


@router.post("/sync/system", response_model=ResponseEnvelope)
def sync_system(
    request: Request, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    schema = request.app.openapi()
    synced, skipped = sync_system_definitions(session, schema)
    return ResponseEnvelope.success(
        data={
            "sync": {"synced": synced, "skipped": skipped},
            "message": "System sync completed",
        }
    )
