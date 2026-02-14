"""Observability metrics for the admin dashboard (KPI-focused)"""

from __future__ import annotations

from typing import Any, Dict

from sqlmodel import Session

from app.modules.inspector.observability_crud import (
    collect_observability_metrics as _collect_observability_metrics_crud,
)
from app.modules.inspector.observability_crud import (
    collect_ops_summary_stats as _collect_ops_summary_stats_crud,
)


def collect_observability_metrics(session: Session) -> Dict[str, Any]:
    """
    Collect all observability metrics for admin dashboard.

    Args:
        session: Database session

    Returns:
        Dict with success_rate, failure_rate, latency, regression_trend,
             top_causes, no_data_ratio
    """
    return _collect_observability_metrics_crud(session)


def collect_ops_summary_stats(session: Session) -> Dict[str, Any]:
    """
    Collect OPS summary stats for frontend summary strip.

    Args:
        session: Database session

    Returns:
        Dict with totalQueries, successfulQueries, failedQueries,
             avgResponseTime, recentActivity, health
    """
    return _collect_ops_summary_stats_crud(session)
