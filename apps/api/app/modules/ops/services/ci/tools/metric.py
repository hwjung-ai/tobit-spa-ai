from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import List, Literal, Tuple

from apps.api.scripts.seed.utils import get_postgres_conn

TIME_RANGES = {
    "last_1h": timedelta(hours=1),
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

AGG_FUNCTIONS = {"count", "max", "min", "avg"}
MAX_CI_IDS = 300


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


def _metric_base_query() -> str:
    return (
        "FROM metric_value mv "
        "JOIN metric_def md ON mv.metric_id = md.metric_id "
        "WHERE mv.tenant_id = %s AND md.metric_name = %s "
    )


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
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM metric_def WHERE metric_name = %s LIMIT 1",
                (metric_name,),
            )
            return bool(cur.fetchone())


def list_metric_names(tenant_id: str, limit: int = 200) -> List[str]:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT metric_name FROM metric_def ORDER BY metric_name LIMIT %s",
                (limit,),
            )
            return [row[0] for row in cur.fetchall()]


def metric_aggregate(
    tenant_id: str,
    metric_name: str,
    time_range: Literal["last_1h", "last_24h", "last_7d"],
    agg: Literal["count", "max", "min", "avg"],
    ci_id: str | None = None,
    ci_ids: list[str] | None = None,
) -> dict[str, object]:
    if agg not in AGG_FUNCTIONS:
        raise ValueError(f"Unsupported aggregate '{agg}'")
    ci_list, truncated, requested_count = _prepare_ci_ids(ci_id, ci_ids)
    time_from, time_to = _calculate_time_range(time_range)
    function = "COUNT(*)" if agg == "count" else f"{agg.upper()}(mv.value)"
    query = (
        f"SELECT {function} AS value "
        f"{_metric_base_query()}"
        "AND mv.ci_id = ANY(%s) "
        "AND mv.time >= %s AND mv.time < %s"
    )
    params = [tenant_id, metric_name, ci_list, time_from, time_to]
    value = None
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            value = row[0] if row else None
    meta = {
        "metric_name": metric_name,
        "agg": agg,
        "time_range": time_range,
        "time_from": time_from.isoformat(),
        "time_to": time_to.isoformat(),
        "ci_count_used": len(ci_list),
        "ci_ids_truncated": truncated,
        "ci_requested": requested_count,
    }
    return {**meta, "value": value, "ci_ids": ci_list}


def metric_series_table(
    tenant_id: str,
    ci_id: str,
    metric_name: str,
    time_range: Literal["last_1h", "last_24h", "last_7d"],
    limit: int | None = 200,
) -> dict[str, object]:
    time_from, time_to = _calculate_time_range(time_range)
    sanitized_limit = max(1, min(1000, limit or 200))
    query = (
        "SELECT mv.time, mv.value "
        f"{_metric_base_query()}"
        "AND mv.ci_id = %s "
        "AND mv.time >= %s AND mv.time < %s "
        "ORDER BY mv.time DESC LIMIT %s"
    )
    params = [tenant_id, metric_name, ci_id, time_from, time_to, sanitized_limit]
    rows: List[tuple[str, str]] = []
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            for time_val, value in cur.fetchall():
                rows.append((time_val.isoformat(), str(value)))
    return {"metric_name": metric_name, "time_range": time_range, "rows": rows}
