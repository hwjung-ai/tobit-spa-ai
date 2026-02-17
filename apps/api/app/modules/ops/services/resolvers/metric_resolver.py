from __future__ import annotations

from app.modules.asset_registry.loader import load_query_asset, load_source_asset
from app.modules.inspector.asset_context import get_stage_assets, get_tracked_assets
from app.modules.ops.services.connections import ConnectionFactory

from .types import MetricHit

METRIC_KEYWORDS = [
    ("temperature", {"온도", "temperature", "temp"}),
    ("cpu_usage", {"cpu", "cpu 사용", "사용률"}),
    ("memory_usage", {"메모리", "ram", "memory"}),
    ("disk_io", {"disk", "iops", "io"}),
    ("network_in", {"network", "트래픽", "bandwidth", "inbound"}),
]


def _resolve_source_ref(source_ref: str | None = None) -> str | None:
    if source_ref:
        return source_ref
    stage_assets = get_stage_assets()
    stage_source = stage_assets.get("source") if isinstance(stage_assets, dict) else None
    if isinstance(stage_source, dict) and stage_source.get("name"):
        return str(stage_source["name"])
    tracked_assets = get_tracked_assets()
    tracked_source = tracked_assets.get("source") if isinstance(tracked_assets, dict) else None
    if isinstance(tracked_source, dict) and tracked_source.get("name"):
        return str(tracked_source["name"])
    return None


def _get_connection(source_ref: str | None = None):
    """Get connection using explicitly selected source asset."""
    resolved_source_ref = _resolve_source_ref(source_ref)
    if not resolved_source_ref:
        raise ValueError("source_ref is required for metric resolver")
    source_asset = load_source_asset(resolved_source_ref)
    if not source_asset:
        raise ValueError(f"Source asset not found: {resolved_source_ref}")
    return ConnectionFactory.create(source_asset)


def resolve_metric(question: str, source_ref: str | None = None) -> MetricHit | None:
    normalized = question.lower()
    for metric_name, keywords in METRIC_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            hit = _fetch_metric(metric_name, source_ref=source_ref)
            if hit:
                return hit
    return None


def _fetch_metric(metric_name: str, source_ref: str | None = None) -> MetricHit | None:
    # Query assets must be managed in Asset Registry (DB).
    asset, _ = load_query_asset("metric", "metric_resolver")
    query = asset.get("sql") if asset else None
    if not query:
        raise ValueError(
            "Metric resolver query not found in Asset Registry: metric/metric_resolver"
        )
    connection = _get_connection(source_ref)
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
