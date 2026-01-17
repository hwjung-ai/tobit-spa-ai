from __future__ import annotations

from datetime import datetime
from typing import Iterable, Tuple

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.modules.inspector.models import TbExecutionTrace


def create_execution_trace(session: Session, trace: TbExecutionTrace) -> TbExecutionTrace:
    session.add(trace)
    session.commit()
    session.refresh(trace)
    return trace


def get_execution_trace(session: Session, trace_id: str) -> TbExecutionTrace | None:
    return session.get(TbExecutionTrace, trace_id)


def list_execution_traces(
    session: Session,
    q: str | None = None,
    feature: str | None = None,
    status: str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    asset_id: str | None = None,
    parent_trace_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[list[TbExecutionTrace], int]:
    filters: list[object] = []
    if feature:
        filters.append(TbExecutionTrace.feature == feature)
    if status:
        filters.append(TbExecutionTrace.status == status)
    if parent_trace_id:
        filters.append(TbExecutionTrace.parent_trace_id == parent_trace_id)
    if from_ts:
        filters.append(TbExecutionTrace.created_at >= from_ts)
    if to_ts:
        filters.append(TbExecutionTrace.created_at <= to_ts)
    if q:
        term = f"%{q}%"
        filters.append(
            or_(
                TbExecutionTrace.question.ilike(term),
                TbExecutionTrace.endpoint.ilike(term),
                TbExecutionTrace.feature.ilike(term),
            )
        )
    if asset_id:
        filters.append(TbExecutionTrace.asset_versions.contains([asset_id]))

    statement = select(TbExecutionTrace)
    if filters:
        statement = statement.where(*filters)

    statement = statement.order_by(TbExecutionTrace.created_at.desc()).offset(offset).limit(limit)

    total_stmt = select(func.count()).select_from(TbExecutionTrace)
    if filters:
        total_stmt = total_stmt.where(*filters)

    traces = session.exec(statement).all()
    total = session.exec(total_stmt).scalar_one()
    return traces, total
