from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.db import get_session
from schemas.common import ResponseEnvelope
from .crud import get_ui_definition, list_ui_definitions
from .schemas import UiDefinitionCreate, UiDefinitionList, UiDefinitionRead, UiDefinitionUpdate

router = APIRouter(prefix="/ui-defs", tags=["ui-creator"])

DEPRECATION_STATUS_CODE = 410
DEPRECATION_DETAIL = {
    "error": "deprecated",
    "message": "ui-defs write access is removed; use asset-registry screens instead.",
}


def _raise_ui_defs_read_only() -> None:
    raise HTTPException(status_code=DEPRECATION_STATUS_CODE, detail=DEPRECATION_DETAIL)


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
def create_def(_payload: UiDefinitionCreate, _session: Session = Depends(get_session)) -> ResponseEnvelope:
    _raise_ui_defs_read_only()


@router.put("/{ui_id}", response_model=ResponseEnvelope)
def update_def(ui_id: str, _payload: UiDefinitionUpdate, _session: Session = Depends(get_session)) -> ResponseEnvelope:
    _raise_ui_defs_read_only()


@router.patch("/{ui_id}", response_model=ResponseEnvelope)
def patch_def(ui_id: str, _payload: UiDefinitionUpdate, _session: Session = Depends(get_session)) -> ResponseEnvelope:
    _raise_ui_defs_read_only()


@router.delete("/{ui_id}", response_model=ResponseEnvelope)
def delete_def(ui_id: str, _session: Session = Depends(get_session)) -> ResponseEnvelope:
    _raise_ui_defs_read_only()


