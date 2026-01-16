from __future__ import annotations

from typing import Any, Iterable, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.engine.row import Row
from sqlmodel import Session

from app.modules.audit_log.crud import (
    get_audit_logs_by_parent_trace,
    get_audit_logs_by_trace,
)
from app.modules.audit_log.models import TbAuditLog
from core.db import get_session
from core.logging import get_logger
from schemas import ResponseEnvelope

router = APIRouter(prefix="/audit-log", tags=["audit_log"])
logger = get_logger(__name__)


def _serialize_audit_log(entry: TbAuditLog) -> dict[str, Any]:
    return entry.model_dump()


def _normalize_rows(rows: Sequence[Row | TbAuditLog | tuple[object, ...]]) -> list[TbAuditLog]:
    def _extract(row: Row | TbAuditLog | tuple[object, ...]) -> TbAuditLog:
        if isinstance(row, TbAuditLog):
            return row
        if isinstance(row, Row) or isinstance(row, tuple):
            return row[0]  # type: ignore[index]
        if isinstance(row, Iterable):
            return next(iter(row))  # type: ignore[return-value]
        return row  # type: ignore[return-value]

    return [_extract(row) for row in rows]


@router.get("")
def list_audit_logs(
    resource_type: str | None = Query(None, description="Filter by the audited resource type"),
    resource_id: str | None = Query(None, description="Filter by the audited resource identifier"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    statement = select(TbAuditLog)
    if resource_type:
        statement = statement.where(TbAuditLog.resource_type == resource_type)
    if resource_id:
        statement = statement.where(TbAuditLog.resource_id == resource_id)

    statement = (
        statement.order_by(TbAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    audit_logs = _normalize_rows(session.exec(statement).all())
    logger.info(
        "audit_log.list",
        extra={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "limit": limit,
            "offset": offset,
            "returned": len(audit_logs),
        },
    )

    return ResponseEnvelope.success(
        data={
            "audit_logs": [_serialize_audit_log(entry) for entry in audit_logs],
            "paging": {"limit": limit, "offset": offset, "returned": len(audit_logs)},
        }
    )


@router.get("/by-trace/{trace_id}")
def get_audit_logs_by_trace_endpoint(
    trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    logs = get_audit_logs_by_trace(session, trace_id)
    if not logs:
        raise HTTPException(status_code=404, detail=f"No audit logs found for trace_id {trace_id}")

    return ResponseEnvelope.success(
        data={
            "trace_id": trace_id,
            "audit_logs": [_serialize_audit_log(entry) for entry in logs],
            "count": len(logs),
        }
    )


@router.get("/by-parent-trace/{parent_trace_id}")
def get_audit_logs_by_parent_trace_endpoint(
    parent_trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    logs = get_audit_logs_by_parent_trace(session, parent_trace_id)
    if not logs:
        raise HTTPException(
            status_code=404,
            detail=f"No audit logs found for parent_trace_id {parent_trace_id}",
        )

    return ResponseEnvelope.success(
        data={
            "parent_trace_id": parent_trace_id,
            "audit_logs": [_serialize_audit_log(entry) for entry in logs],
            "count": len(logs),
        }
    )
