"""
LLM Call Logs API Router

Provides endpoints for viewing and analyzing LLM API calls.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, Query
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.auth.models import TbUser

from .crud import (
    list_llm_call_logs,
    get_llm_call_log,
    get_llm_call_logs_by_trace,
    get_llm_analytics,
    get_llm_call_pairs,
    to_read_model,
)
from .models import LlmCallLogRead, LlmCallAnalytics

router = APIRouter(prefix="/llm-logs", tags=["llm-logs"])


@router.get("", response_model=ResponseEnvelope)
def list_llm_logs(
    trace_id: str | None = Query(None, description="Filter by trace ID"),
    call_type: str | None = Query(None, description="Filter by call type (planner, output_parser, tool)"),
    model_name: str | None = Query(None, description="Filter by model name"),
    feature: str | None = Query(None, description="Filter by feature (ops, docs, cep)"),
    status: str | None = Query(None, description="Filter by status (success, error)"),
    from_date: datetime | None = Query(None, alias="from", description="Filter by start date"),
    to_date: datetime | None = Query(None, alias="to", description="Filter by end date"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    List LLM call logs with filters

    Returns paginated list of LLM calls with total count
    """
    # Parse trace_id if provided
    logs, total = list_llm_call_logs(
        session=session,
        trace_id=trace_id,
        call_type=call_type,
        model_name=model_name,
        feature=feature,
        status=status,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope.success(
        data={
            "logs": [to_read_model(log).model_dump() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/pairs", response_model=ResponseEnvelope)
def list_llm_log_pairs(
    trace_id: str | None = Query(None, description="Filter by trace ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get LLM call logs grouped as query-response pairs

    Returns logs grouped by trace_id for easier viewing of conversation flow
    """
    logs, total = get_llm_call_pairs(
        session=session,
        trace_id=trace_id,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope.success(
        data={
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/analytics", response_model=ResponseEnvelope)
def get_analytics(
    from_date: datetime | None = Query(None, alias="from", description="Start date (default: 24h ago)"),
    to_date: datetime | None = Query(None, alias="to", description="End date (default: now)"),
    feature: str | None = Query(None, description="Filter by feature"),
    model_name: str | None = Query(None, description="Filter by model name"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get LLM call analytics summary

    Returns aggregated statistics for LLM usage including:
    - Total calls, success/failure counts
    - Token usage (input, output, total)
    - Average latency
    - Breakdown by model, feature, call type
    """
    analytics = get_llm_analytics(
        session=session,
        from_date=from_date,
        to_date=to_date,
        feature=feature,
        model_name=model_name,
    )

    return ResponseEnvelope.success(data=analytics.model_dump())


@router.get("/{log_id}", response_model=ResponseEnvelope)
def get_log_detail(
    log_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get detailed information about a single LLM call

    Includes full prompts and responses
    """
    try:
        log_uuid = UUID(log_id)
    except ValueError:
        return ResponseEnvelope.error("Invalid log ID", error_code="INVALID_ID")

    log = get_llm_call_log(session=session, log_id=log_uuid)
    if not log:
        return ResponseEnvelope.error("LLM call log not found", error_code="NOT_FOUND")

    return ResponseEnvelope.success(data=to_read_model(log).model_dump())


@router.get("/trace/{trace_id}", response_model=ResponseEnvelope)
def get_logs_by_trace(
    trace_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get all LLM calls for a specific trace

    Returns all LLM calls made during a single request trace,
    ordered by call index to show the conversation flow
    """
    logs = get_llm_call_logs_by_trace(session=session, trace_id=trace_id)

    return ResponseEnvelope.success(
        data={
            "trace_id": trace_id,
            "logs": [to_read_model(log).model_dump() for log in logs],
            "total": len(logs),
        }
    )
