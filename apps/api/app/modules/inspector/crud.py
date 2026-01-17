from __future__ import annotations

from datetime import datetime
from typing import Iterable, Tuple
from uuid import uuid4

from sqlalchemy import func, or_, desc
from sqlmodel import Session, select

from app.modules.inspector.models import (
    TbExecutionTrace,
    TbGoldenQuery,
    TbRegressionBaseline,
    TbRegressionRun,
)


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
    total = session.exec(total_stmt).one()
    return traces, total


# Golden Query CRUD


def create_golden_query(
    session: Session,
    name: str,
    query_text: str,
    ops_type: str,
    options: dict | None = None,
) -> TbGoldenQuery:
    """Create a new golden query"""
    golden_query = TbGoldenQuery(
        id=str(uuid4()),
        name=name,
        query_text=query_text,
        ops_type=ops_type,
        options=options,
    )
    session.add(golden_query)
    session.commit()
    session.refresh(golden_query)
    return golden_query


def get_golden_query(session: Session, golden_query_id: str) -> TbGoldenQuery | None:
    """Get golden query by ID"""
    return session.get(TbGoldenQuery, golden_query_id)


def list_golden_queries(session: Session, enabled_only: bool = False) -> list[TbGoldenQuery]:
    """List all golden queries"""
    statement = select(TbGoldenQuery)
    if enabled_only:
        statement = statement.where(TbGoldenQuery.enabled == True)
    statement = statement.order_by(TbGoldenQuery.created_at.desc())
    return session.exec(statement).all()


def update_golden_query(
    session: Session,
    golden_query_id: str,
    name: str | None = None,
    query_text: str | None = None,
    enabled: bool | None = None,
    options: dict | None = None,
) -> TbGoldenQuery | None:
    """Update golden query"""
    golden_query = get_golden_query(session, golden_query_id)
    if not golden_query:
        return None

    if name is not None:
        golden_query.name = name
    if query_text is not None:
        golden_query.query_text = query_text
    if enabled is not None:
        golden_query.enabled = enabled
    if options is not None:
        golden_query.options = options

    session.add(golden_query)
    session.commit()
    session.refresh(golden_query)
    return golden_query


def delete_golden_query(session: Session, golden_query_id: str) -> bool:
    """Delete golden query"""
    golden_query = get_golden_query(session, golden_query_id)
    if not golden_query:
        return False

    session.delete(golden_query)
    session.commit()
    return True


# Regression Baseline CRUD


def create_regression_baseline(
    session: Session,
    golden_query_id: str,
    baseline_trace_id: str,
    baseline_status: str,
    asset_versions: list[str] | None = None,
    created_by: str | None = None,
) -> TbRegressionBaseline:
    """Create regression baseline"""
    baseline = TbRegressionBaseline(
        id=str(uuid4()),
        golden_query_id=golden_query_id,
        baseline_trace_id=baseline_trace_id,
        baseline_status=baseline_status,
        asset_versions=asset_versions,
        created_by=created_by,
    )
    session.add(baseline)
    session.commit()
    session.refresh(baseline)
    return baseline


def get_latest_regression_baseline(
    session: Session, golden_query_id: str
) -> TbRegressionBaseline | None:
    """Get the latest baseline for a golden query"""
    statement = (
        select(TbRegressionBaseline)
        .where(TbRegressionBaseline.golden_query_id == golden_query_id)
        .order_by(TbRegressionBaseline.created_at.desc())
        .limit(1)
    )
    return session.exec(statement).first()


def get_regression_baseline(
    session: Session, baseline_id: str
) -> TbRegressionBaseline | None:
    """Get regression baseline by ID"""
    return session.get(TbRegressionBaseline, baseline_id)


# Regression Run CRUD


def create_regression_run(
    session: Session,
    golden_query_id: str,
    baseline_id: str,
    candidate_trace_id: str,
    baseline_trace_id: str,
    judgment: str,
    triggered_by: str,
    verdict_reason: str | None = None,
    diff_summary: dict | None = None,
    trigger_info: dict | None = None,
    execution_duration_ms: int | None = None,
) -> TbRegressionRun:
    """Create regression run result"""
    run = TbRegressionRun(
        id=str(uuid4()),
        golden_query_id=golden_query_id,
        baseline_id=baseline_id,
        candidate_trace_id=candidate_trace_id,
        baseline_trace_id=baseline_trace_id,
        judgment=judgment,
        verdict_reason=verdict_reason,
        diff_summary=diff_summary,
        triggered_by=triggered_by,
        trigger_info=trigger_info,
        execution_duration_ms=execution_duration_ms,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def list_regression_runs(
    session: Session,
    golden_query_id: str | None = None,
    limit: int = 50,
) -> list[TbRegressionRun]:
    """List regression runs"""
    statement = select(TbRegressionRun)
    if golden_query_id:
        statement = statement.where(TbRegressionRun.golden_query_id == golden_query_id)
    statement = statement.order_by(TbRegressionRun.created_at.desc()).limit(limit)
    return session.exec(statement).all()


def get_regression_run(session: Session, run_id: str) -> TbRegressionRun | None:
    """Get regression run by ID"""
    return session.get(TbRegressionRun, run_id)
