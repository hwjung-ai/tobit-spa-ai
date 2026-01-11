from __future__ import annotations

from sqlmodel import Session, select

from .models import TbUiDef
from .schemas import UiDefinitionCreate, UiDefinitionUpdate


def list_ui_definitions(session: Session) -> list[TbUiDef]:
    statement = select(TbUiDef).where(TbUiDef.is_active == True).order_by(TbUiDef.updated_at.desc())
    return session.exec(statement).all()


def get_ui_definition(session: Session, ui_id: str) -> TbUiDef | None:
    return session.get(TbUiDef, ui_id)


def create_ui_definition(session: Session, payload: UiDefinitionCreate) -> TbUiDef:
    record = TbUiDef(
        ui_name=payload.ui_name,
        ui_type=payload.ui_type,
        schema=payload.ui_schema,
        description=payload.description,
        tags=payload.tags,
        is_active=payload.is_active,
        created_by=payload.created_by,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update_ui_definition(session: Session, record: TbUiDef, payload: UiDefinitionUpdate) -> TbUiDef:
    data = payload.model_dump(exclude_unset=True, by_alias=True)
    for key, value in data.items():
        setattr(record, key, value)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
