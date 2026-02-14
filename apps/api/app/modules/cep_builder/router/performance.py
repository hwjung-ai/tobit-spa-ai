"""Performance monitoring and statistics endpoints for CEP Builder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core.db import get_session
from fastapi import APIRouter, Depends, Query
from schemas.common import ResponseEnvelope
from sqlalchemy import select
from sqlmodel import Session

from ..crud import get_rule, list_rules
from ..models import TbCepExecLog

router = APIRouter(prefix="/cep", tags=["cep-performance"])


@router.get("/stats/summary")
def get_stats_summary(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """
    Get overall CEP statistics summary.

    Returns:
        - Total rule count
        - Today's execution count
        - Average execution time
        - Error rate
    """
    all_rules = list_rules(session)
    total_rules = len(all_rules)
    active_rules = sum(1 for rule in all_rules if rule.is_active)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_logs_query = select(TbCepExecLog).where(
        TbCepExecLog.triggered_at >= today_start
    )
    today_logs = session.exec(today_logs_query).scalars().all()

    today_execution_count = len(today_logs)
    today_errors = sum(1 for log in today_logs if log.status == "fail")

    if today_logs:
        avg_duration = sum(log.duration_ms for log in today_logs) / len(today_logs)
        error_rate = today_errors / len(today_logs)
    else:
        avg_duration = 0
        error_rate = 0

    last_24h = now - timedelta(hours=24)
    logs_24h_query = select(TbCepExecLog).where(
        TbCepExecLog.triggered_at >= last_24h
    )
    logs_24h = session.exec(logs_24h_query).scalars().all()

    return ResponseEnvelope.success(
        data={
            "stats": {
                "total_rules": total_rules,
                "active_rules": active_rules,
                "inactive_rules": total_rules - active_rules,
                "today_execution_count": today_execution_count,
                "today_error_count": today_errors,
                "today_error_rate": error_rate,
                "today_avg_duration_ms": round(avg_duration, 2),
                "last_24h_execution_count": len(logs_24h),
                "timestamp": now.isoformat(),
            }
        }
    )


@router.get("/errors/timeline")
def get_errors_timeline(
    period: str = Query("24h"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get error timeline with hourly distribution.

    Args:
        period: Time period to look back (1h, 6h, 24h, 7d)

    Returns:
        - Hourly error counts
        - Error type distribution
        - Recent error list
    """
    period_mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }

    lookback = period_mapping.get(period, timedelta(hours=24))
    now = datetime.now(timezone.utc)
    cutoff_time = now - lookback

    error_logs_query = select(TbCepExecLog).where(
        (TbCepExecLog.triggered_at >= cutoff_time) &
        (TbCepExecLog.status == "fail")
    ).order_by(TbCepExecLog.triggered_at.desc())

    error_logs = session.exec(error_logs_query).scalars().all()

    # Create hourly timeline
    timeline = {}
    current = cutoff_time.replace(minute=0, second=0, microsecond=0)
    while current <= now:
        timeline[current.isoformat()] = 0
        current += timedelta(hours=1)

    # Count errors by hour
    error_types = {}
    for log in error_logs:
        hour_key = log.triggered_at.replace(minute=0, second=0, microsecond=0).isoformat()
        if hour_key in timeline:
            timeline[hour_key] += 1

        # Categorize error type
        error_type = "unknown"
        if log.error_message:
            if "timeout" in log.error_message.lower():
                error_type = "timeout"
            elif "connection" in log.error_message.lower():
                error_type = "connection"
            elif "validation" in log.error_message.lower():
                error_type = "validation"
            elif "authentication" in log.error_message.lower():
                error_type = "authentication"
            else:
                error_type = "other"

        error_types[error_type] = error_types.get(error_type, 0) + 1

    # Get recent errors (last 10)
    recent_errors = []
    for log in error_logs[:10]:
        rule = get_rule(session, str(log.rule_id))
        recent_errors.append({
            "exec_id": str(log.exec_id),
            "rule_id": str(log.rule_id),
            "rule_name": rule.rule_name if rule else "Unknown",
            "triggered_at": log.triggered_at.isoformat(),
            "error_message": log.error_message,
            "duration_ms": log.duration_ms,
        })

    return ResponseEnvelope.success(
        data={
            "timeline": [
                {"timestamp": k, "error_count": v}
                for k, v in sorted(timeline.items())
            ],
            "error_distribution": error_types,
            "recent_errors": recent_errors,
            "period": period,
            "total_errors": len(error_logs),
        }
    )
