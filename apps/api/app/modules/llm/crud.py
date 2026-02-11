"""
LLM Call Log CRUD Operations
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func as sql_func
from sqlmodel import Session, select, col

from .models import (
    LlmCallLogCreate,
    LlmCallLogRead,
    LlmCallLogSummary,
    LlmCallAnalytics,
    LlmCallLogUpdate,
    TbLlmCallLog,
)


def create_llm_call_log(
    session: Session,
    log: LlmCallLogCreate,
) -> TbLlmCallLog:
    """Create a new LLM call log entry"""
    db_log = TbLlmCallLog(
        **log.model_dump(exclude_none=True),
        id=uuid4(),
    )
    session.add(db_log)
    session.commit()
    session.refresh(db_log)
    return db_log


def get_llm_call_log(session: Session, log_id: UUID) -> TbLlmCallLog | None:
    """Get LLM call log by ID"""
    return session.get(TbLlmCallLog, log_id)


def list_llm_call_logs(
    session: Session,
    trace_id: str | None = None,
    call_type: str | None = None,
    model_name: str | None = None,
    feature: str | None = None,
    status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TbLlmCallLog], int]:
    """
    List LLM call logs with filters

    Returns:
        tuple: (logs, total_count)
    """
    query = select(TbLlmCallLog)

    # Apply filters
    if trace_id:
        query = query.where(TbLlmCallLog.trace_id == trace_id)
    if call_type:
        query = query.where(TbLlmCallLog.call_type == call_type)
    if model_name:
        query = query.where(TbLlmCallLog.model_name == model_name)
    if feature:
        query = query.where(TbLlmCallLog.feature == feature)
    if status:
        query = query.where(TbLlmCallLog.status == status)
    if from_date:
        query = query.where(TbLlmCallLog.created_at >= from_date)
    if to_date:
        query = query.where(TbLlmCallLog.created_at <= to_date)

    # Get total count
    count_query = select(sql_func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # Apply pagination and ordering
    query = query.order_by(TbLlmCallLog.created_at.desc())
    query = query.offset(offset).limit(limit)

    logs = session.exec(query).all()
    return logs, total


def get_llm_call_logs_by_trace(
    session: Session,
    trace_id: str,
) -> list[TbLlmCallLog]:
    """Get all LLM call logs for a specific trace"""
    query = select(TbLlmCallLog).where(
        TbLlmCallLog.trace_id == trace_id
    ).order_by(TbLlmCallLog.call_index.asc())
    return session.exec(query).all()


def update_llm_call_log(
    session: Session,
    log: TbLlmCallLog,
    update: LlmCallLogUpdate,
) -> TbLlmCallLog:
    """Update LLM call log"""
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(log, key, value)
    log.updated_at = datetime.utcnow()
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def get_llm_analytics(
    session: Session,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    feature: str | None = None,
    model_name: str | None = None,
) -> LlmCallAnalytics:
    """
    Get analytics summary for LLM calls

    Args:
        session: Database session
        from_date: Start date filter (default: 24 hours ago)
        to_date: End date filter (default: now)
        feature: Filter by feature
        model_name: Filter by model name

    Returns:
        LlmCallAnalytics: Analytics summary
    """
    if not from_date:
        from_date = datetime.utcnow() - timedelta(hours=24)
    if not to_date:
        to_date = datetime.utcnow()

    # Base query
    query = select(TbLlmCallLog).where(
        TbLlmCallLog.created_at >= from_date,
        TbLlmCallLog.created_at <= to_date,
    )

    if feature:
        query = query.where(TbLlmCallLog.feature == feature)
    if model_name:
        query = query.where(TbLlmCallLog.model_name == model_name)

    # Get all matching logs
    logs = session.exec(query).all()

    # Calculate analytics
    total_calls = len(logs)
    successful_calls = len([log for log in logs if log.status == "success"])
    failed_calls = len([log for log in logs if log.status == "error"])

    total_input_tokens = sum(log.input_tokens or 0 for log in logs)
    total_output_tokens = sum(log.output_tokens or 0 for log in logs)
    total_tokens_sum = sum(log.total_tokens or 0 for log in logs)

    total_duration = sum(log.duration_ms or 0 for log in logs)
    avg_latency = total_duration / total_calls if total_calls > 0 else 0

    # Breakdown by model
    model_breakdown: dict[str, int] = {}
    for log in logs:
        model = log.model_name or "unknown"
        model_breakdown[model] = model_breakdown.get(model, 0) + 1

    # Breakdown by feature
    feature_breakdown: dict[str, int] = {}
    for log in logs:
        feat = log.feature or "unknown"
        feature_breakdown[feat] = feature_breakdown.get(feat, 0) + 1

    # Breakdown by call type
    call_type_breakdown: dict[str, int] = {}
    for log in logs:
        call_type = log.call_type or "unknown"
        call_type_breakdown[call_type] = call_type_breakdown.get(call_type, 0) + 1

    return LlmCallAnalytics(
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_tokens_sum,
        avg_latency_ms=avg_latency,
        total_duration_ms=total_duration,
        model_breakdown=model_breakdown,
        feature_breakdown=feature_breakdown,
        call_type_breakdown=call_type_breakdown,
    )


def get_llm_call_pairs(
    session: Session,
    trace_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    Get LLM call logs paired as query-response for display

    Returns logs grouped by trace_id and ordered by call_index
    """
    # Get logs
    logs, total = list_llm_call_logs(
        session=session,
        trace_id=trace_id,
        limit=limit,
        offset=offset,
    )

    # Group by trace_id and create pairs
    pairs_by_trace: dict[str, list[dict]] = {}

    for log in logs:
        trace_key = str(log.trace_id) if log.trace_id else "unlinked"

        if trace_key not in pairs_by_trace:
            pairs_by_trace[trace_key] = []

        log_dict = {
            "id": str(log.id),
            "trace_id": trace_key,
            "call_type": log.call_type,
            "call_index": log.call_index,
            "model_name": log.model_name,
            "provider": log.provider,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "total_tokens": log.total_tokens,
            "duration_ms": log.duration_ms,
            "status": log.status,
            "feature": log.feature,
            "ui_endpoint": log.ui_endpoint,
            "request_time": log.request_time.isoformat() if log.request_time else None,
            "response_time": log.response_time.isoformat() if log.response_time else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }

        # Add prompt snippets (first 500 chars)
        if log.user_prompt:
            log_dict["user_prompt_preview"] = log.user_prompt[:500] + "..." if len(log.user_prompt) > 500 else log.user_prompt
        if log.raw_response:
            log_dict["response_preview"] = log.raw_response[:500] + "..." if len(log.raw_response) > 500 else log.raw_response

        pairs_by_trace[trace_key].append(log_dict)

    # Sort each pair group by call_index and flatten
    result = []
    for trace_key in sorted(pairs_by_trace.keys(), reverse=True):
        trace_logs = sorted(pairs_by_trace[trace_key], key=lambda x: x["call_index"])
        result.extend(trace_logs)

    return result, total


def to_read_model(log: TbLlmCallLog) -> LlmCallLogRead:
    """Convert TbLlmCallLog to LlmCallLogRead"""
    return LlmCallLogRead.model_validate(log)


def to_summary_model(log: TbLlmCallLog) -> LlmCallLogSummary:
    """Convert TbLlmCallLog to LlmCallLogSummary"""
    return LlmCallLogSummary.model_validate(log)
