from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import List, Literal, Tuple

from apps.api.scripts.seed.utils import get_postgres_conn
from schemas.tool_contracts import MetricAggregateResult, MetricSeriesResult

from app.shared.config_loader import load_text

TIME_RANGES = {
    "last_1h": timedelta(hours=1),
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

AGG_FUNCTIONS = {"count", "max", "min", "avg"}
MAX_CI_IDS = 300

_QUERY_BASE = "queries/postgres/metric"


def _load_query(name: str) -> str:
    query = load_text(f"{_QUERY_BASE}/{name}")
    if not query:
        raise ValueError(f"Metric query '{name}' not found")
    return query


def _calculate_time_range(time_range: str) -> Tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if DATE_PATTERN.match(time_range):
        start = datetime.fromisoformat(time_range).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return start, end
    delta = TIME_RANGES.get(time_range)
    if not delta:
        raise ValueError(f"Unsupported time range '{time_range}'")
    return now - delta, now


def _prepare_ci_ids(ci_id: str | None, ci_ids: list[str] | None) -> tuple[list[str], bool, int]:
    candidates: list[str] = []
    if ci_ids:
        candidates = list(dict.fromkeys(ci_ids))
    elif ci_id:
        candidates = [ci_id]
    if not candidates:
        raise ValueError("Either ci_id or ci_ids must be provided")
    requested = len(candidates)
    truncated = requested > MAX_CI_IDS
    if truncated:
        candidates = candidates[:MAX_CI_IDS]
    return candidates, truncated, requested


def metric_exists(tenant_id: str, metric_name: str) -> bool:
    query = _load_query("metric_exists.sql")
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (metric_name,))
            return bool(cur.fetchone())


def list_metric_names(tenant_id: str, limit: int = 200) -> List[str]:
    query = _load_query("metric_list.sql")
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            return [row[0] for row in cur.fetchall()]


def metric_aggregate(
    tenant_id: str,
    metric_name: str,
    time_range: Literal["last_1h", "last_24h", "last_7d"],
    agg: Literal["count", "max", "min", "avg"],
    ci_id: str | None = None,
    ci_ids: list[str] | None = None,
) -> MetricAggregateResult:
    if agg not in AGG_FUNCTIONS:
        raise ValueError(f"Unsupported aggregate '{agg}'")
    ci_list, truncated, requested_count = _prepare_ci_ids(ci_id, ci_ids)
    time_from, time_to = _calculate_time_range(time_range)
    function = "COUNT(*)" if agg == "count" else f"{agg.upper()}(mv.value)"
    query_template = _load_query("metric_aggregate.sql")
    query = query_template.format(function=function)
    params = [tenant_id, metric_name, ci_list, time_from, time_to]
    value = None
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            value = row[0] if row else None
    return MetricAggregateResult(
        metric_name=metric_name,
        agg=agg,
        time_range=time_range,
        time_from=time_from.isoformat(),
        time_to=time_to.isoformat(),
        ci_count_used=len(ci_list),
        ci_ids_truncated=truncated,
        ci_requested=requested_count,
        value=value,
        ci_ids=ci_list,
    )


def metric_series_table(
    tenant_id: str,
    ci_id: str,
    metric_name: str,
    time_range: Literal["last_1h", "last_24h", "last_7d"],
    limit: int | None = 200,
) -> MetricSeriesResult:
    time_from, time_to = _calculate_time_range(time_range)
    sanitized_limit = max(1, min(1000, limit or 200))
    query = _load_query("metric_series.sql")
    params = [tenant_id, metric_name, ci_id, time_from, time_to, sanitized_limit]
    rows: List[tuple[str, str]] = []
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            for time_val, value in cur.fetchall():
                rows.append((time_val.isoformat(), str(value)))
    return MetricSeriesResult(
        metric_name=metric_name,
        time_range=time_range,
        rows=rows,
    )
