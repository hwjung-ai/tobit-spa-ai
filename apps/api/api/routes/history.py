from __future__ import annotations

import uuid
from typing import Tuple

from core.db import get_session
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from models.history import QueryHistory
from schemas.common import ResponseEnvelope
from schemas.history import HistoryCreate, HistoryRead
from sqlalchemy import select
from sqlmodel import Session

from apps.api.core.logging import get_logger

router = APIRouter(prefix="/history", tags=["history"])
logger = get_logger(__name__)


def _resolve_identity(
    tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
    user_id: str | None = Header(None, alias="X-User-Id"),
) -> Tuple[str, str]:
    return tenant_id or "default", user_id or "default"


@router.post("/", response_model=ResponseEnvelope, status_code=status.HTTP_201_CREATED)
def create_history(
    payload: HistoryCreate,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
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
    return ResponseEnvelope.success(data={"history": HistoryRead.model_validate(entry.model_dump(by_alias=True))})


@router.get("/", response_model=ResponseEnvelope)
def list_history(
    feature: str | None = Query(None),
    limit: int = Query(40, ge=1, le=200),
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    statement = select(QueryHistory).where(
        QueryHistory.tenant_id == tenant_id,
        QueryHistory.user_id == user_id,
    )
    if feature:
        statement = statement.where(QueryHistory.feature == feature)
    statement = statement.order_by(QueryHistory.created_at.desc()).limit(limit)
    entries = session.exec(statement).scalars().all()
    result = [HistoryRead.model_validate(entry.model_dump(by_alias=True)) for entry in entries]
    return ResponseEnvelope.success(data={"history": result})


@router.delete("/{history_id}", response_model=ResponseEnvelope)
def delete_history(
    history_id: uuid.UUID,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    entry = session.get(QueryHistory, history_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found")
    if entry.tenant_id != tenant_id or entry.user_id != user_id:
        logger.warning(
            "history.delete.identity_mismatch",
            extra={
                "requested_tenant_id": tenant_id,
                "requested_user_id": user_id,
                "entry_tenant_id": entry.tenant_id,
                "entry_user_id": entry.user_id,
                "history_id": str(history_id),
            },
        )
    session.delete(entry)
    session.commit()
    return ResponseEnvelope.success()
