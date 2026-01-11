from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, List, Tuple

from apps.api.scripts.seed.utils import get_postgres_conn

TIME_RANGES = {
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
    "last_30d": timedelta(days=30),
}

MAX_LIMIT = 200
MAX_CI_IDS = 300


def _prepare_ci_ids(ci_ids: List[str]) -> Tuple[List[str], bool, int]:
    requested = len(ci_ids)
    unique_ids = list(dict.fromkeys(ci_ids))
    truncated = len(unique_ids) > MAX_CI_IDS
    if truncated:
        unique_ids = unique_ids[:MAX_CI_IDS]
    return unique_ids, truncated, requested


def _load_event_log_metadata() -> dict[str, object]:
    warnings: List[str] = []
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'event_log' LIMIT 1"
            )
            table_exists = bool(cur.fetchone())
            if not table_exists:
                warnings.append("event_log table not found")
                return {"available": False, "warnings": warnings}
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'event_log' ORDER BY ordinal_position"
            )
            columns = [row[0] for row in cur.fetchall()]
    ci_candidates = ["ci_id", "ci_code", "target_ci_id", "resource_id"]
    time_candidates = ["created_at", "occurred_at", "timestamp", "ts"]
    ci_col = next((col for col in ci_candidates if col in columns), None)
    time_col = next((col for col in time_candidates if col in columns), None)
    tenant_col = "tenant_id" if "tenant_id" in columns else None
    if not ci_col:
        warnings.append("No CI reference column found in event_log")
    if not time_col:
        warnings.append("No timestamp column found in event_log")
    return {
        "available": bool(ci_col and time_col),
        "warnings": warnings,
        "columns": columns,
        "ci_col": ci_col,
        "time_col": time_col,
        "tenant_col": tenant_col,
    }


def _calculate_time_range(time_range: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    span = TIME_RANGES.get(time_range)
    if not span:
        raise ValueError(f"Unsupported time range '{time_range}'")
    return now - span, now


def event_log_recent(
    tenant_id: str,
    ci: dict[str, object],
    time_range: Literal["last_24h", "last_7d", "last_30d"],
    limit: int | None = 50,
    ci_ids: List[str] | None = None,
) -> dict[str, object]:
    metadata = _load_event_log_metadata()
    if not metadata.get("available"):
        return {"available": False, "warnings": metadata.get("warnings", []), "meta": {"source": "event_log"}}
    ci_ref = metadata["ci_col"]
    time_col = metadata["time_col"]
    tenant_col = metadata.get("tenant_col")
    warnings = metadata.get("warnings", []).copy()
    if not ci_ref or not time_col:
        return {"available": False, "warnings": warnings, "meta": {"source": "event_log"}}
    time_from, time_to = _calculate_time_range(time_range)
    sanitized_limit = max(1, min(MAX_LIMIT, limit or 50))
    selected_columns: List[str] = []
    for col in [ci_ref, time_col]:
        if col and col not in selected_columns:
            selected_columns.append(col)
    for col in metadata["columns"]:
        if len(selected_columns) >= 12:
            break
        if col not in selected_columns:
            selected_columns.append(col)
    ci_values = []
    ci_ids_truncated = False
    ci_requested = 0
    if ci_ids:
        prepared_ids, ci_ids_truncated, ci_requested = _prepare_ci_ids(ci_ids)
        ci_values = prepared_ids
        where_clauses = [f"{ci_ref} = ANY(%s)", f"{time_col} >= %s", f"{time_col} < %s"]
        params = [prepared_ids, time_from, time_to]
    else:
        ci_value = ci.get("ci_id") or ci.get("ci_code")
        if not ci_value:
            raise ValueError("CI identifier is required for history queries")
        ci_values = [ci_value]
        where_clauses = [f"{ci_ref} = %s", f"{time_col} >= %s", f"{time_col} < %s"]
        params = [ci_value, time_from, time_to]
    if tenant_col:
        where_clauses.insert(0, f"{tenant_col} = %s")
        params.insert(0, tenant_id)
    else:
        warnings.append("tenant_id column missing in event_log; tenant scope not enforced")
    columns_sql = ", ".join(selected_columns)
    query = (
        f"SELECT {columns_sql} FROM event_log WHERE {' AND '.join(where_clauses)} "
        f"ORDER BY {time_col} DESC LIMIT %s"
    )
    params.append(sanitized_limit)
    rows: List[List[str]] = []
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            for row in cur.fetchall():
                rows.append([str(item) if item is not None else "<null>" for item in row])
    meta = {
        "source": "event_log",
        "ci_col": ci_ref,
        "time_col": time_col,
        "time_from": time_from.isoformat(),
        "time_to": time_to.isoformat(),
        "limit": sanitized_limit,
        "ci_count_used": len(ci_values),
        "ci_ids_truncated": ci_ids_truncated,
        "ci_requested": ci_requested or len(ci_values),
        "warnings": warnings,
    }
    return {"available": True, "columns": selected_columns, "rows": rows, "meta": meta}
