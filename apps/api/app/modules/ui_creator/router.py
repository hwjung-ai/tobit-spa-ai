from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.db import get_session
from schemas.common import ResponseEnvelope
from .crud import create_ui_definition, get_ui_definition, list_ui_definitions, update_ui_definition
from .schemas import UiDefinitionCreate, UiDefinitionList, UiDefinitionRead, UiDefinitionUpdate

router = APIRouter(prefix="/ui-defs", tags=["ui-creator"])


@router.get("", response_model=ResponseEnvelope)
def list_defs(session: Session = Depends(get_session)) -> ResponseEnvelope:
    items = list_ui_definitions(session)
    payload = [UiDefinitionList.from_orm(item).model_dump() for item in items]
    return ResponseEnvelope.success(data={"ui_defs": payload})


@router.get("/{ui_id}", response_model=ResponseEnvelope)
def get_def(ui_id: str, session: Session = Depends(get_session)) -> ResponseEnvelope:
    item = get_ui_definition(session, ui_id)
    if not item:
        raise HTTPException(status_code=404, detail="UI definition not found")
    payload = UiDefinitionRead.from_orm(item).model_dump(by_alias=True)
    return ResponseEnvelope.success(data={"ui": payload})


@router.post("", response_model=ResponseEnvelope)
def create_def(payload: UiDefinitionCreate, session: Session = Depends(get_session)) -> ResponseEnvelope:
    created = create_ui_definition(session, payload)
    return ResponseEnvelope.success(data={"ui": UiDefinitionRead.from_orm(created).model_dump(by_alias=True)})


@router.put("/{ui_id}", response_model=ResponseEnvelope)
def update_def(ui_id: str, payload: UiDefinitionUpdate, session: Session = Depends(get_session)) -> ResponseEnvelope:
    item = get_ui_definition(session, ui_id)
    if not item:
        raise HTTPException(status_code=404, detail="UI definition not found")
    updated = update_ui_definition(session, item, payload)
    return ResponseEnvelope.success(data={"ui": UiDefinitionRead.from_orm(updated).model_dump(by_alias=True)})
