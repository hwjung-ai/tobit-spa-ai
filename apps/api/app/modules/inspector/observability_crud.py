"""
CRUD operations for Observability module.

Centralizes database access for execution traces and regression runs.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import func, select
from sqlmodel import Session

from app.modules.inspector.models import TbExecutionTrace, TbRegressionRun

logger = logging.getLogger(__name__)


def _percentile(values: Iterable[int], percentile: float) -> int | None:
    """Calculate percentile from values."""
    values_list = sorted(values)
    if not values_list:
        return None
    index = int((len(values_list) - 1) * percentile)
    return values_list[max(0, min(index, len(values_list) - 1))]


# ============================================================================
# Execution Trace CRUD
# ============================================================================


def get_trace_count(
    session: Session, since: datetime, status: Optional[str] = None
) -> int:
    """
    Get count of execution traces.

    Args:
        session: Database session
        since: Start datetime filter
        status: Optional status filter

    Returns:
        Count of traces
    """
    query = select(func.count()).where(TbExecutionTrace.created_at >= since)
    if status:
        query = query.where(TbExecutionTrace.status == status)
    return session.exec(query).scalar_one() or 0


def get_trace_durations(session: Session, since: datetime) -> List[int]:
    """
    Get all trace durations since given time.

    Args:
        session: Database session
        since: Start datetime filter

    Returns:
        List of duration_ms values
    """
    durations = session.exec(
        select(TbExecutionTrace.duration_ms)
        .where(TbExecutionTrace.created_at >= since)
        .order_by(TbExecutionTrace.duration_ms)
    ).all()
    return [row[0] for row in durations if row[0] is not None]


def get_recent_traces(
    session: Session, limit: int = 5
) -> List[tuple[datetime, str, str]]:
    """
    Get most recent traces with timestamp, ops_mode, and status.

    Args:
        session: Database session
        limit: Number of traces to return

    Returns:
        List of (created_at, ops_mode, status) tuples
    """
    traces = session.exec(
        select(
            TbExecutionTrace.created_at,
            TbExecutionTrace.ops_mode,
            TbExecutionTrace.status,
        )
        .order_by(TbExecutionTrace.created_at.desc())
        .limit(limit)
    ).all()
    return list(traces)


def get_recent_trace_answers(
    session: Session, limit: int = 500
) -> List[Dict[str, Any] | None]:
    """
    Get recent trace answers for analysis.

    Args:
        session: Database session
        limit: Number of answers to return

    Returns:
        List of answer dicts
    """
    traces = session.exec(
        select(TbExecutionTrace.answer)
        .order_by(TbExecutionTrace.created_at.desc())
        .limit(limit)
    ).all()
    return [answer for (answer,) in traces]


def get_average_latency(session: Session, since: datetime) -> float:
    """
    Get average trace duration since given time.

    Args:
        session: Database session
        since: Start datetime filter

    Returns:
        Average duration in ms
    """
    avg = session.exec(
        select(func.avg(TbExecutionTrace.duration_ms)).where(
            TbExecutionTrace.created_at >= since
        )
    ).scalar()
    return float(avg) if avg else 0.0


# ============================================================================
# Regression Run CRUD
# ============================================================================


def get_regression_trend(
    session: Session, since: datetime
) -> List[tuple[datetime, str, int]]:
    """
    Get daily regression trend.

    Args:
        session: Database session
        since: Start datetime filter

    Returns:
        List of (day, judgment, count) tuples
    """
    day_expr = func.date_trunc("day", TbRegressionRun.created_at)
    query = (
        select(
            day_expr.label("day"),
            TbRegressionRun.judgment,
            func.count().label("count"),
        )
        .where(TbRegressionRun.created_at >= since)
        .group_by(day_expr, TbRegressionRun.judgment)
        .order_by(day_expr)
    )
    return session.exec(query).all()


def get_recent_verdict_reasons(session: Session, limit: int = 100) -> List[str]:
    """
    Get recent verdict reasons.

    Args:
        session: Database session
        limit: Number of reasons to return

    Returns:
        List of reason strings
    """
    reasons = session.exec(
        select(TbRegressionRun.verdict_reason)
        .where(TbRegressionRun.verdict_reason.is_not(None))
        .order_by(TbRegressionRun.created_at.desc())
        .limit(limit)
    ).all()
    return [reason or "" for (reason,) in reasons if reason]


# ============================================================================
# High-Level Observability Functions
# ============================================================================


def collect_observability_metrics(session: Session) -> Dict[str, Any]:
    """
    Collect all observability metrics for admin dashboard.

    Args:
        session: Database session

    Returns:
        Dict with success_rate, failure_rate, latency, regression_trend,
             top_causes, no_data_ratio
    """
    now = datetime.utcnow()
    since_day = now - timedelta(hours=24)
    since_week = now - timedelta(days=7)

    # Success/Failure rates
    recent_total = get_trace_count(session, since_day)
    recent_success = get_trace_count(session, since_day, status="success")
    success_rate = (recent_success / recent_total) if recent_total else 0.0
    failure_rate = 1.0 - success_rate if recent_total else 0.0

    # Latency percentiles
    durations_list = get_trace_durations(session, since_day)
    latency_p50 = _percentile(durations_list, 0.5)
    latency_p95 = _percentile(durations_list, 0.95)

    # Regression trend
    trend_result = get_regression_trend(session, since_week)
    trend_map: dict[str, dict[str, int]] = defaultdict(
        lambda: {"PASS": 0, "WARN": 0, "FAIL": 0}
    )
    regression_totals: Counter[str] = Counter()
    for day, judgment, count in trend_result:
        normalized_date = day.date().isoformat()
        trend_map[normalized_date][judgment] = int(count)
        regression_totals[judgment] += int(count)

    trend_list = [{"date": day, **trend_map[day]} for day in sorted(trend_map.keys())]

    # Top failure reasons
    reason_rows = get_recent_verdict_reasons(session, limit=100)
    overall_reasons = Counter()
    for reason in reason_rows:
        safe_reason = reason.strip()
        if safe_reason:
            overall_reasons[safe_reason] += 1

    # No data ratio
    traces_samples = get_recent_trace_answers(session, limit=500)

    def _extract_summary(answer: dict[str, Any] | None) -> str:
        if not answer:
            return ""
        meta = answer.get("meta")
        if isinstance(meta, dict):
            summary = meta.get("summary") or ""
            return str(summary).lower()
        return ""

    sample_summaries = [
        _extract_summary(answer) for answer in traces_samples if answer is not None
    ]
    no_data_hits = sum(1 for summary in sample_summaries if "no data" in summary)
    sample_count = len(sample_summaries)
    no_data_ratio = (no_data_hits / sample_count) if sample_count else 0.0

    return {
        "success_rate": round(success_rate, 3),
        "failure_rate": round(failure_rate, 3),
        "total_recent_requests": int(recent_total),
        "latency": {
            "p50": latency_p50,
            "p95": latency_p95,
        },
        "regression_trend": trend_list,
        "regression_totals": {
            "PASS": regression_totals.get("PASS", 0),
            "WARN": regression_totals.get("WARN", 0),
            "FAIL": regression_totals.get("FAIL", 0),
        },
        "top_causes": [
            {"reason": reason, "count": count}
            for reason, count in overall_reasons.most_common(5)
        ],
        "no_data_ratio": round(no_data_ratio, 3),
    }


def collect_ops_summary_stats(session: Session) -> Dict[str, Any]:
    """
    Collect OPS summary stats for frontend summary strip.

    Args:
        session: Database session

    Returns:
        Dict with totalQueries, successfulQueries, failedQueries,
             avgResponseTime, recentActivity, health
    """
    now = datetime.utcnow()
    since_day = now - timedelta(hours=24)

    # Query counts
    total_queries = get_trace_count(session, since_day)
    successful_queries = get_trace_count(session, since_day, status="success")
    failed_queries = total_queries - successful_queries

    # Average latency
    avg_latency = get_average_latency(session, since_day)

    # Recent activity
    recent_traces = get_recent_traces(session, limit=5)

    mode_map = {
        "config": "ci",
        "metric": "metric",
        "hist": "history",
        "graph": "relation",
        "all": "all",
    }

    recent_activity = []
    for created_at, ops_mode, status in recent_traces:
        recent_activity.append({
            "timestamp": created_at.isoformat(),
            "type": mode_map.get(ops_mode, "all"),
            "status": "ok" if status == "success" else "error"
        })

    # Health check
    try:
        from app.modules.admin_dashboard.system_monitor import SystemMonitor

        monitor = SystemMonitor()
        health = monitor.check_health()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health = {
            "service": {"status": "error", "detail": f"Monitor unavailable: {e}"},
            "database": {"status": "error", "detail": f"Monitor unavailable: {e}"},
            "network": {"status": "error", "detail": f"Monitor unavailable: {e}"},
        }

    return {
        "totalQueries": int(total_queries),
        "successfulQueries": int(successful_queries),
        "failedQueries": int(failed_queries),
        "avgResponseTime": int(avg_latency),
        "recentActivity": recent_activity,
        "health": health,
    }
