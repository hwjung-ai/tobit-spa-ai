from __future__ import annotations

from core.config import get_settings

from app.modules.asset_registry.loader import load_query_asset, load_source_asset
from app.modules.ops.services.connections import ConnectionFactory

from .types import MetricHit

METRIC_KEYWORDS = [
    ("temperature", {"온도", "temperature", "temp"}),
    ("cpu_usage", {"cpu", "cpu 사용", "사용률"}),
    ("memory_usage", {"메모리", "ram", "memory"}),
    ("disk_io", {"disk", "iops", "io"}),
    ("network_in", {"network", "트래픽", "bandwidth", "inbound"}),
]


def _get_connection():
    """Get connection using source asset."""
    settings = get_settings()
    source_asset = load_source_asset(settings.ops_default_source_asset)
    return ConnectionFactory.create(source_asset)


def resolve_metric(question: str) -> MetricHit | None:
    normalized = question.lower()
    for metric_name, keywords in METRIC_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            hit = _fetch_metric(metric_name)
            if hit:
                return hit
    return None


def _fetch_metric(metric_name: str) -> MetricHit | None:
    # Query assets must be managed in Asset Registry (DB).
    asset, _ = load_query_asset("metric", "metric_resolver")
    query = asset.get("sql") if asset else None
    if not query:
        raise ValueError(
            "Metric resolver query not found in Asset Registry: metric/metric_resolver"
        )
    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        with conn.cursor() as cur:
            cur.execute(query, (metric_name,))
            row = cur.fetchone()
            if not row:
                return None
            metric_id, name = row
            return MetricHit(metric_id=str(metric_id), metric_name=name)
    finally:
        connection.close()
