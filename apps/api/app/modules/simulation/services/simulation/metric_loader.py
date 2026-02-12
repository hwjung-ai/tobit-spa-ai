"""
Metric Data Loader for Simulation

Loads actual metric timeseries data from PostgreSQL for simulation baseline and backtesting.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.config import get_settings
from core.db import get_session_context
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.modules.asset_registry.loader import load_catalog_for_source


def _get_metric_timeseries(
    session: Session,
    tenant_id: str,
    service: str,
    metric_names: list[str] | None = None,
    hours_back: int = 24
) -> dict[str, list[dict[str, Any]]]:
    """
    Load metric timeseries from PostgreSQL.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        service: Service name
        metric_names: List of metric names to load (latency_ms, throughput_rps, error_rate_pct, cost_usd_hour)
        hours_back: How many hours of historical data to load

    Returns:
        Dictionary mapping metric_name -> list of {timestamp, value} records
    """
    if metric_names is None:
        metric_names = ["latency_ms", "throughput_rps", "error_rate_pct", "cost_usd_hour"]

    since = datetime.utcnow() - timedelta(hours=hours_back)

    # Build query to load timeseries data
    # Check if tb_metric_timeseries exists
    from app.modules.simulation.services.simulation.metric_models import TbMetricTimeseries

    query = (
        select(TbMetricTimeseries)
        .where(TbMetricTimeseries.tenant_id == tenant_id)
        .where(TbMetricTimeseries.service == service)
        .where(TbMetricTimeseries.metric_name.in_(metric_names))
        .where(TbMetricTimeseries.timestamp >= since)
        .order_by(TbMetricTimeseries.timestamp.asc())
    )

    results = session.exec(query).all()

    # Group by metric_name
    metric_data: dict[str, list[dict[str, Any]]] = {name: [] for name in metric_names}
    for row in results:
        if row.metric_name not in metric_data:
            metric_data[row.metric_name] = []
        metric_data[row.metric_name].append({
            "timestamp": row.timestamp,
            "value": float(row.value),
            "unit": row.unit,
        })

    return metric_data


def calculate_baseline_statistics(
    metric_data: list[dict[str, Any]],
    aggregation: str = "mean"
) -> float:
    """
    Calculate baseline statistics from metric data.

    Args:
        metric_data: List of {timestamp, value} records
        aggregation: Aggregation method (mean, median, p50, p95, max, min)

    Returns:
        Baseline value as float
    """
    if not metric_data:
        return 0.0

    values = [row["value"] for row in metric_data]

    if aggregation == "mean":
        return sum(values) / len(values)
    elif aggregation == "median":
        sorted_values = sorted(values)
        n = len(sorted_values)
        return sorted_values[n // 2]
    elif aggregation == "p50":
        sorted_values = sorted(values)
        n = len(sorted_values)
        return sorted_values[n // 2]
    elif aggregation == "p95":
        sorted_values = sorted(values)
        n = len(sorted_values)
        idx = int(n * 0.95)
        return sorted_values[min(idx, n - 1)]
    elif aggregation == "max":
        return max(values)
    elif aggregation == "min":
        return min(values)
    else:
        return sum(values) / len(values)


def load_baseline_kpis(
    *, tenant_id: str, service: str, hours_back: int = 168
) -> dict[str, float]:
    """
    Load baseline KPIs from actual metric timeseries data.

    Args:
        tenant_id: Tenant identifier
        service: Service name
        hours_back: Hours of historical data to use for baseline (default: 168 = 7 days)

    Returns:
        Dictionary with baseline KPIs:
        - latency_ms: Mean latency
        - throughput_rps: Mean throughput
        - error_rate_pct: Mean error rate
        - cost_usd_hour: Mean cost
    """
    with get_session_context() as session:
        metric_data = _get_metric_timeseries(
            session=session,
            tenant_id=tenant_id,
            service=service,
            hours_back=hours_back
        )

        baseline = {}

        # Calculate baseline for each metric
        for metric_name, records in metric_data.items():
            if records:
                baseline[metric_name] = calculate_baseline_statistics(records, aggregation="mean")
            else:
                # Fallback to defaults if no data
                baseline[metric_name] = {
                    "latency_ms": 45.0,
                    "throughput_rps": 100.0,
                    "error_rate_pct": 0.5,
                    "cost_usd_hour": 10.0,
                }.get(metric_name, 0.0)

        return baseline


def get_available_services_from_metrics(tenant_id: str) -> list[str]:
    """
    Get list of services that have metric data available.

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of service names with metric data
    """
    with get_session_context() as session:
        from app.modules.simulation.services.simulation.metric_models import TbMetricTimeseries

        # Check if timeseries table exists and has data
        query = (
            select(TbMetricTimeseries.service)
            .where(TbMetricTimeseries.tenant_id == tenant_id)
            .where(TbMetricTimeseries.timestamp >= datetime.utcnow() - timedelta(hours=24))
            .distinct()
        )

        results = session.exec(query).all()
        return [row.service for row in results if row.service]
