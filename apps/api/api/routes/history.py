from __future__ import annotations

import uuid

from app.modules.auth.models import TbUser
from core.auth import get_current_user
from core.config import get_settings
from core.db import get_session
from core.tenant import get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.history import QueryHistory
from schemas.common import ResponseEnvelope
from schemas.history import HistoryCreate, HistoryRead
from sqlalchemy import select
from sqlmodel import Session

from apps.api.core.logging import get_logger

router = APIRouter(prefix="/history", tags=["history"])
logger = get_logger(__name__)


def _resolve_identity(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> tuple[str, str]:
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return tenant_id, str(current_user.id)


@router.post("/", response_model=ResponseEnvelope, status_code=status.HTTP_201_CREATED)
def create_history(
    payload: HistoryCreate,
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    entry = QueryHistory(
        tenant_id=tenant_id,
        user_id=user_id,
        feature=payload.feature,
        question=payload.question,
        summary=payload.summary,
        status=payload.status,
        response=payload.response,
        metadata_info=payload.metadata,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return ResponseEnvelope.success(
        data={"history": HistoryRead.model_validate(entry.model_dump(by_alias=True))}
    )


@router.get("/", response_model=ResponseEnvelope)
def list_history(
    feature: str | None = Query(None),
    limit: int = Query(40, ge=1, le=200),
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    statement = select(QueryHistory)

    # Always filter by authenticated identity for tenant/user isolation.
    statement = statement.where(
        QueryHistory.tenant_id == tenant_id,
        QueryHistory.user_id == user_id,
    )

    if feature:
        statement = statement.where(QueryHistory.feature == feature)
    statement = statement.order_by(QueryHistory.created_at.desc()).limit(limit)
    entries = session.exec(statement).scalars().all()
    result = [
        HistoryRead.model_validate(entry.model_dump(by_alias=True)) for entry in entries
    ]
    return ResponseEnvelope.success(data={"history": result})


@router.delete("/{history_id}", response_model=ResponseEnvelope)
def delete_history(
    history_id: uuid.UUID,
    session: Session = Depends(get_session),
    identity: tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    entry = session.get(QueryHistory, history_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found"
        )
    if entry.tenant_id != tenant_id or entry.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History entry not found",
        )
    session.delete(entry)
    session.commit()
    return ResponseEnvelope.success()
