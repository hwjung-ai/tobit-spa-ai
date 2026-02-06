"""Observability metrics for the admin dashboard (KPI-focused)"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable

from sqlalchemy import func, select
from sqlmodel import Session

from app.modules.inspector.models import TbExecutionTrace, TbRegressionRun


def _percentile(values: Iterable[int], percentile: float) -> int | None:
    values_list = sorted(values)
    if not values_list:
        return None
    index = int((len(values_list) - 1) * percentile)
    return values_list[max(0, min(index, len(values_list) - 1))]


def _extract_summary(answer: dict[str, Any] | None) -> str:
    if not answer:
        return ""
    meta = answer.get("meta")
    if isinstance(meta, dict):
        summary = meta.get("summary") or ""
        return str(summary).lower()
    return ""


def collect_observability_metrics(session: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    since_day = now - timedelta(hours=24)
    since_week = now - timedelta(days=7)

    recent_total = session.exec(
        select(func.count()).where(TbExecutionTrace.created_at >= since_day)
    ).scalar_one()
    recent_success = session.exec(
        select(func.count()).where(
            TbExecutionTrace.created_at >= since_day,
            TbExecutionTrace.status == "success",
        )
    ).scalar_one()
    success_rate = (recent_success / recent_total) if recent_total else 0.0
    failure_rate = 1.0 - success_rate if recent_total else 0.0

    durations = session.exec(
        select(TbExecutionTrace.duration_ms)
        .where(TbExecutionTrace.created_at >= since_day)
        .order_by(TbExecutionTrace.duration_ms)
    ).all()
    durations_list = [row[0] for row in durations if row[0] is not None]
    latency_p50 = _percentile(durations_list, 0.5)
    latency_p95 = _percentile(durations_list, 0.95)

    day_expr = func.date_trunc("day", TbRegressionRun.created_at)
    regression_trend_query = select(
        day_expr.label("day"),
        TbRegressionRun.judgment,
        func.count().label("count"),
    ).where(TbRegressionRun.created_at >= since_week)
    regression_trend_query = regression_trend_query.group_by(
        day_expr, TbRegressionRun.judgment
    )
    regression_trend_query = regression_trend_query.order_by(day_expr)
    trend_result = session.exec(regression_trend_query).all()
    trend_map: dict[str, dict[str, int]] = defaultdict(
        lambda: {"PASS": 0, "WARN": 0, "FAIL": 0}
    )
    regression_totals: Counter[str] = Counter()
    for day, judgment, count in trend_result:
        normalized_date = day.date().isoformat()
        trend_map[normalized_date][judgment] = int(count)
        regression_totals[judgment] += int(count)

    trend_list = [{"date": day, **trend_map[day]} for day in sorted(trend_map.keys())]

    overall_reasons = Counter()
    reason_rows = session.exec(
        select(TbRegressionRun.verdict_reason)
        .where(TbRegressionRun.verdict_reason.is_not(None))
        .order_by(TbRegressionRun.created_at.desc())
        .limit(100)
    ).all()
    for (reason,) in reason_rows:
        safe_reason = (reason or "").strip()
        if safe_reason:
            overall_reasons[safe_reason] += 1

    traces_samples = session.exec(
        select(TbExecutionTrace.answer)
        .order_by(TbExecutionTrace.created_at.desc())
        .limit(500)
    ).all()
    sample_summaries = [
        _extract_summary(answer) for (answer,) in traces_samples if answer is not None
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
    """Collect specific metrics for the OPS summary strip in the frontend."""
    # Total counts (lifetime for now, or we could limit to recent)
    total_queries = session.exec(select(func.count(TbExecutionTrace.trace_id))).scalar_one()
    successful_queries = session.exec(
        select(func.count(TbExecutionTrace.trace_id)).where(TbExecutionTrace.status == "success")
    ).scalar_one()
    failed_queries = total_queries - successful_queries

    # Average response time
    avg_latency = session.exec(select(func.avg(TbExecutionTrace.duration_ms))).scalar() or 0

    # Recent activity (last 5)
    recent_traces = session.exec(
        select(TbExecutionTrace.created_at, TbExecutionTrace.ops_mode, TbExecutionTrace.status)
        .order_by(TbExecutionTrace.created_at.desc())
        .limit(5)
    ).all()

    recent_activity = []
    for created_at, ops_mode, status in recent_traces:
        # Map ops_mode to frontend types
        mode_map = {
            "config": "ci",
            "metric": "metric",
            "hist": "history",
            "graph": "relation",
            "all": "all"
        }
        recent_activity.append({
            "timestamp": created_at.isoformat(),
            "type": mode_map.get(ops_mode, "all"),
            "status": "ok" if status == "success" else "error"
        })

    # Reverse to match frontend expectation (reverse internally or just send)
    # The frontend does .reverse() so we send in DESC order.

    return {
        "totalQueries": int(total_queries),
        "successfulQueries": int(successful_queries),
        "failedQueries": int(failed_queries),
        "avgResponseTime": int(avg_latency),
        "recentActivity": recent_activity,
        "health": {
            "service": "ok",
            "database": "ok",
            "network": "ok"
        }
    }
