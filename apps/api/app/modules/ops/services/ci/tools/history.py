from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Literal, List, Tuple

from scripts.seed.utils import get_postgres_conn
from schemas.tool_contracts import HistoryRecord, HistoryResult
from app.shared.config_loader import load_text
from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
    ToolType,
)

TIME_RANGES = {
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
    "last_30d": timedelta(days=30),
}

MAX_LIMIT = 200
MAX_CI_IDS = 300

_QUERY_BASE = "queries/postgres/history"


def _load_query(name: str) -> str:
    query = load_text(f"{_QUERY_BASE}/{name}")
    if not query:
        raise ValueError(f"History query '{name}' not found")
    return query


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
            table_exists_query = _load_query("event_log_table_exists.sql")
            cur.execute(table_exists_query)
            table_exists = bool(cur.fetchone())
            if not table_exists:
                warnings.append("event_log table not found")
                return {"available": False, "warnings": warnings}
            columns_query = _load_query("event_log_columns.sql")
            cur.execute(columns_query)
            columns = [row[0] for row in cur.fetchall()]
    ci_candidates = ["ci_id", "ci_code", "target_ci_id", "resource_id"]
    time_candidates = ["created_at", "occurred_at", "timestamp", "ts"]
    ci_col = next((col for col in ci_candidates if col in columns), None)
    time_col = next((col for col in time_candidates if col in columns), None)
    tenant_col = "tenant_id" if "tenant_id" in columns else None
    available = bool(ci_col and time_col)
    if not ci_col:
        warnings.append("No CI reference column found in event_log")
    if not time_col:
        warnings.append("No timestamp column found in event_log")
        available = False
    return {
        "available": available,
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
    ci: dict[str, object] | None,
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
    for col in [ci_ref, time_col, "ci.ci_code", "ci.ci_name"]:
        if col and col not in selected_columns:
            selected_columns.append(col)
    for col in metadata["columns"]:
        if len(selected_columns) >= 12:
            break
        if col not in selected_columns:
            selected_columns.append(col)
    ci_values: List[str] = []
    ci_ids_truncated = False
    ci_requested = 0
    if ci_ids:
        prepared_ids, ci_ids_truncated, ci_requested = _prepare_ci_ids(ci_ids)
        ci_values = prepared_ids
        where_clauses = [f"{ci_ref} = ANY(%s)", f"{time_col} >= %s", f"{time_col} < %s"]
        params = [prepared_ids, time_from, time_to]
    else:
        ci_value = None
        if ci:
            ci_value = ci.get("ci_id") or ci.get("ci_code")
        if ci_value:
            ci_values = [ci_value]
            ci_requested = 1
            where_clauses = [f"{ci_ref} = %s", f"{time_col} >= %s", f"{time_col} < %s"]
            params = [ci_value, time_from, time_to]
        else:
            where_clauses = [f"{time_col} >= %s", f"{time_col} < %s"]
            params = [time_from, time_to]
    if tenant_col:
        where_clauses.insert(0, f"{tenant_col} = %s")
        params.insert(0, tenant_id)
    else:
        warnings.append("tenant_id column missing in event_log; tenant scope not enforced")
    columns_sql = ", ".join(selected_columns)
    query_template = _load_query("event_log_recent.sql")
    query = query_template.format(
        columns=columns_sql,
        where_clause=" AND ".join(where_clauses),
        time_col=time_col,
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


def recent_work_and_maintenance(
    tenant_id: str,
    time_range: Literal["last_24h", "last_7d", "last_30d"],
    limit: int | None = 50,
) -> HistoryResult:
    time_from, time_to = _calculate_time_range(time_range)
    work_query = _load_query("work_history_recent.sql")
    work_rows = _fetch_sql_rows(
        work_query,
        (tenant_id, time_from, time_to, limit or 50),
    )
    maint_query = _load_query("maintenance_history_recent.sql")
    maint_rows = _fetch_sql_rows(
        maint_query,
        (tenant_id, time_from, time_to, limit or 50),
    )
    # Convert rows to HistoryRecord format
    records: List[HistoryRecord] = []
    for row in list(work_rows) + list(maint_rows):
        # Assuming row format: (timestamp, event_type, ci_id, ci_code, description)
        if len(row) >= 5:
            records.append(
                HistoryRecord(
                    timestamp=row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                    event_type=row[1] or "work",
                    ci_id=str(row[2]) if row[2] else "",
                    ci_code=str(row[3]) if row[3] else "",
                    description=str(row[4]) if row[4] else "",
                )
            )
    return HistoryResult(
        records=records,
        total=len(records),
        time_range=time_range,
    )


HISTORY_WORK_KEYWORDS = {"작업", "work", "deployment", "integration", "audit", "upgrade", "change"}
HISTORY_MAINT_KEYWORDS = {"유지보수", "maintenance", "maint", "점검", "inspection", "routine"}


def detect_history_sections(question: str) -> set[str]:
    text = (question or "").lower()
    types: set[str] = set()
    if any(keyword in text for keyword in HISTORY_WORK_KEYWORDS):
        types.add("work")
    if any(keyword in text for keyword in HISTORY_MAINT_KEYWORDS):
        types.add("maintenance")
    return types


def _fetch_sql_rows(query: str, params: Iterable) -> list[tuple]:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()


# ==============================================================================
# Tool Interface Implementation
# ==============================================================================


class HistoryTool(BaseTool):
    """
    Tool for History and Event Log operations.

    Provides methods to query event logs and historical data from the system,
    including work history, maintenance records, and general event logs.
    """

    @property
    def tool_type(self) -> ToolType:
        """Return the History tool type."""
        return ToolType.HISTORY

    async def should_execute(self, context: ToolContext, params: Dict[str, Any]) -> bool:
        """
        Determine if this tool should execute for the given operation.

        History tool handles operations with these parameter keys:
        - operation: 'event_log', 'work_and_maintenance', 'detect_sections'

        Args:
            context: Execution context
            params: Tool parameters

        Returns:
            True if this is a History operation, False otherwise
        """
        operation = params.get("operation", "")
        valid_operations = {"event_log", "work_and_maintenance", "detect_sections"}
        return operation in valid_operations

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a History operation.

        Dispatches to the appropriate function based on the 'operation' parameter.

        Parameters:
            operation (str): The operation to perform
            time_range (str): Time range ('last_24h', 'last_7d', 'last_30d')
            limit (int, optional): Result limit
            ci (dict, optional): CI reference for filtering
            ci_ids (list[str], optional): Multiple CI IDs for filtering
            question (str, optional): Question text for detecting history sections

        Returns:
            ToolResult with success status and history data
        """
        try:
            operation = params.get("operation", "")
            tenant_id = context.tenant_id

            if operation == "event_log":
                result = event_log_recent(
                    tenant_id=tenant_id,
                    ci=params.get("ci"),
                    time_range=params.get("time_range", "last_24h"),
                    limit=params.get("limit", 50),
                    ci_ids=params.get("ci_ids"),
                )
            elif operation == "work_and_maintenance":
                result = recent_work_and_maintenance(
                    tenant_id=tenant_id,
                    time_range=params.get("time_range", "last_24h"),
                    limit=params.get("limit", 50),
                )
            elif operation == "detect_sections":
                sections = detect_history_sections(params.get("question", ""))
                result = {
                    "sections": list(sections),
                    "question": params.get("question", ""),
                }
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown History operation: {operation}",
                )

            return ToolResult(success=True, data=result)

        except ValueError as e:
            return await self.format_error(context, e, params)
        except Exception as e:
            return await self.format_error(context, e, params)


# Create and register the History tool
_history_tool = HistoryTool()
