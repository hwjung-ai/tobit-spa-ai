from __future__ import annotations

from typing import Any, Iterable, Sequence

from sqlalchemy.engine.row import Row
from sqlmodel import Session, select

from app.modules.audit_log.models import TbAuditLog


def create_audit_log(
    session: Session,
    trace_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    actor: str,
    changes: dict[str, Any],
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    parent_trace_id: str | None = None,
) -> TbAuditLog:
    """Create a new audit log entry."""
    audit_log = TbAuditLog(
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        actor=actor,
        changes=changes,
        old_values=old_values,
        new_values=new_values,
        audit_metadata=metadata,
    )
    session.add(audit_log)
    session.commit()
    session.refresh(audit_log)
    return audit_log


def get_audit_logs_by_resource(
    session: Session,
    resource_type: str,
    resource_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[TbAuditLog]:
    """Get audit logs for a specific resource."""
    statement = (
        select(TbAuditLog)
        .where(TbAuditLog.resource_type == resource_type)
        .where(TbAuditLog.resource_id == resource_id)
        .order_by(TbAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return _unwrap_result(session.exec(statement).all())


def get_audit_logs_by_trace(
    session: Session,
    trace_id: str,
) -> list[TbAuditLog]:
    """Get all audit logs for a specific trace."""
    statement = (
        select(TbAuditLog)
        .where(TbAuditLog.trace_id == trace_id)
        .order_by(TbAuditLog.created_at.desc())
    )
    return _unwrap_result(session.exec(statement).all())


def get_audit_logs_by_parent_trace(
    session: Session,
    parent_trace_id: str,
) -> list[TbAuditLog]:
    """Get all audit logs for a specific parent trace."""
    statement = (
        select(TbAuditLog)
        .where(TbAuditLog.parent_trace_id == parent_trace_id)
        .order_by(TbAuditLog.created_at.desc())
    )
    return _unwrap_result(session.exec(statement).all())


def _unwrap_result(
    rows: Sequence[Row | TbAuditLog | tuple[object, ...]],
) -> list[TbAuditLog]:
    def _normalize(row: Row | TbAuditLog | tuple[object, ...]) -> TbAuditLog:
        if isinstance(row, TbAuditLog):
            return row
        if isinstance(row, Row) or isinstance(row, tuple):
            return row[0]  # type: ignore[index]
        if isinstance(row, Iterable):
            # fallback: pick first element
            return next(iter(row))  # type: ignore[return-value]
        return row  # pragma: no cover

    return [_normalize(row) for row in rows]
