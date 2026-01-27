from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Literal, Tuple

from core.config import get_settings
from core.logging import get_logger
from schemas.tool_contracts import HistoryRecord, HistoryResult

from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
)
from app.modules.ops.services.ci.tools.query_registry import (
    create_connection_for_query,
    load_query_asset_simple,
)
from app.shared.config_loader import load_text
from app.modules.asset_registry.loader import load_policy_asset

logger = get_logger(__name__)

# Hardcoded fallback (used if policy asset not found)
TIME_RANGES = {
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
    "last_30d": timedelta(days=30),
}

# Cache for time ranges
_TIME_RANGES_CACHE = None


def _get_time_ranges() -> dict[str, timedelta]:
    """
    Load time ranges from policy asset.
    Falls back to hardcoded TIME_RANGES if asset not found.
    """
    global _TIME_RANGES_CACHE
    if _TIME_RANGES_CACHE is not None:
        return _TIME_RANGES_CACHE

    try:
        policy = load_policy_asset("time_ranges")
        if policy:
            content = policy.get("content", {})
            time_ranges_config = content.get("time_ranges", {})

            if time_ranges_config:
                # Convert config to timedelta objects
                ranges = {}
                for key, config in time_ranges_config.items():
                    if "hours" in config:
                        ranges[key] = timedelta(hours=config["hours"])
                    elif "days" in config:
                        ranges[key] = timedelta(days=config["days"])
                    elif "minutes" in config:
                        ranges[key] = timedelta(minutes=config["minutes"])

                if ranges:
                    _TIME_RANGES_CACHE = ranges
                    logger.info(f"Loaded {len(ranges)} time ranges from policy asset")
                    return _TIME_RANGES_CACHE
    except Exception as e:
        logger.warning(f"Failed to load time_ranges policy: {e}")

    # Fallback to hardcoded
    logger.warning("Using hardcoded TIME_RANGES")
    _TIME_RANGES_CACHE = TIME_RANGES
    return _TIME_RANGES_CACHE

# Hardcoded fallback limits - will be loaded from DB via _get_limits()
MAX_LIMIT = 200
MAX_CI_IDS = 300

# Cache for tool limits loaded from DB
_LIMITS_CACHE: Dict[str, Any] | None = None

_QUERY_BASE = "queries/postgres/history"


def _get_limits() -> Dict[str, Any]:
    """
    Load History tool limits from policy asset.
    Falls back to hardcoded constants if asset not found.

    Returns:
        Dictionary with limit configuration:
        {
            "max_limit": 200,
            "default_limit": 50
        }
    """
    global _LIMITS_CACHE
    if _LIMITS_CACHE is not None:
        return _LIMITS_CACHE

    try:
        policy = load_policy_asset("tool_limits")
        if policy:
            content = policy.get("content", {})
            history_limits = content.get("history", {})
            if history_limits:
                _LIMITS_CACHE = history_limits
                logger.info(f"Loaded History tool limits from DB: {history_limits}")
                return _LIMITS_CACHE
    except Exception as e:
        logger.warning(f"Failed to load tool_limits policy for History: {e}")

    # Fallback to hardcoded limits
    _LIMITS_CACHE = {
        "max_limit": MAX_LIMIT,
        "default_limit": 50,
    }
    logger.info("Using hardcoded History tool limits (fallback)")
    return _LIMITS_CACHE


def _load_query(name: str) -> str:
    """
    Load a history query by operation name using QueryAssetRegistry.

    Tries to load from QueryAssetRegistry first, then falls back to file-based loading.
    """
    # Map filenames to operation names
    operation_map = {
        "event_log_table_exists.sql": "event_log_table_exists",
        "event_log_columns.sql": "event_log_columns",
        "event_log_recent.sql": "event_log_recent",
        "work_history_recent.sql": "work_history_recent",
        "maintenance_history_recent.sql": "maintenance_history_recent",
        "inspection_history.sql": "inspection_history",
        "work_history.sql": "work_history",
        "maintenance_history.sql": "maintenance_history",
        "event_log.sql": "event_log",
        "event_log_table_exists": "event_log_table_exists",
        "event_log_columns": "event_log_columns",
        "event_log_recent": "event_log_recent",
        "work_history_recent": "work_history_recent",
        "maintenance_history_recent": "maintenance_history_recent",
        "inspection_history": "inspection_history",
        "work_history": "work_history",
        "maintenance_history": "maintenance_history",
        "event_log": "event_log",
    }

    operation = operation_map.get(name, name.replace(".sql", ""))

    try:
        from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry

        registry = get_query_asset_registry()
        query_asset = registry.get_query_asset("history", operation)
        if query_asset and query_asset.get("sql"):
            return query_asset["sql"]
    except Exception:
        # Fallback to file-based loading
        pass

    # File-based fallback
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
    """Load event_log table metadata using the query registry."""
    warnings: List[str] = []

    # Use execute_query for simple queries
    from app.modules.ops.services.ci.tools.query_registry import execute_query

    # Check if table exists
    table_exists_query = _load_query("event_log_table_exists.sql")
    try:
        result = execute_query("history", "event_log_table_exists")
        table_exists = bool(result and len(result) > 0)
    except Exception:
        table_exists = False

    if not table_exists:
        warnings.append("event_log table not found")
        return {"available": False, "warnings": warnings}

    # Get table columns
    try:
        result = execute_query("history", "event_log_columns")
        columns = [list(row.values())[0] for row in result] if result else []
    except Exception:
        columns = []

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
    kst_timezone = get_settings().timezone_offset
    now = datetime.now(kst_timezone)
    time_ranges = _get_time_ranges()
    span = time_ranges.get(time_range)
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
        return {
            "available": False,
            "warnings": metadata.get("warnings", []),
            "meta": {"source": "event_log"},
        }
    ci_ref = metadata["ci_col"]
    time_col = metadata["time_col"]
    tenant_col = metadata.get("tenant_col")
    warnings = metadata.get("warnings", []).copy()
    if not ci_ref or not time_col:
        return {
            "available": False,
            "warnings": warnings,
            "meta": {"source": "event_log"},
        }
    time_from, time_to = _calculate_time_range(time_range)
    limits = _get_limits()
    sanitized_limit = max(1, min(limits.get("max_limit", 200), limit or limits.get("default_limit", 50)))
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
        warnings.append(
            "tenant_id column missing in event_log; tenant scope not enforced"
        )
    columns_sql = ", ".join(selected_columns)
    query_template = _load_query("event_log_recent.sql")
    query = query_template.format(
        columns=columns_sql,
        where_clause=" AND ".join(where_clauses),
        time_col=time_col,
    )
    params.append(sanitized_limit)

    # Use ConnectionFactory for dynamic query execution
    conn = create_connection_for_query("history", "event_log_recent")
    try:
        result = conn.execute(query, params)
        rows: List[List[str]] = []
        if result:
            for row in result:
                rows.append(
                    [str(item) if item is not None else "<null>" for item in row.values()]
                )
    finally:
        conn.close()

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
                    timestamp=row[0].isoformat()
                    if hasattr(row[0], "isoformat")
                    else str(row[0]),
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


HISTORY_WORK_KEYWORDS = {
    "작업",
    "work",
    "deployment",
    "integration",
    "audit",
    "upgrade",
    "change",
}
HISTORY_MAINT_KEYWORDS = {
    "유지보수",
    "maintenance",
    "maint",
    "점검",
    "inspection",
    "routine",
}


def detect_history_sections(question: str) -> set[str]:
    text = (question or "").lower()
    types: set[str] = set()
    if any(keyword in text for keyword in HISTORY_WORK_KEYWORDS):
        types.add("work")
    if any(keyword in text for keyword in HISTORY_MAINT_KEYWORDS):
        types.add("maintenance")
    return types


def _fetch_sql_rows(query: str, params: Iterable) -> list[tuple]:
    """
    Execute SQL query using ConnectionFactory.

    This is a convenience function for executing queries that need
    template substitution but don't fit into the standard query registry pattern.
    """
    # Use history tool's default connection
    conn = create_connection_for_query("history", "work_history")
    try:
        result = conn.execute(query, list(params))
        # Convert list of dicts to list of tuples
        return [tuple(row.values()) for row in result]
    finally:
        conn.close()


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
    def tool_type(self) -> str:
        """Return the History tool type."""
        return "history"

    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute for the given operation.

        History tool handles:
        - Special operations: 'event_log', 'work_and_maintenance', 'detect_sections'
        - Any operation registered in QueryAssetRegistry with tool_type='history'

        Args:
            context: Execution context
            params: Tool parameters

        Returns:
            True if this is a History operation, False otherwise
        """
        operation = params.get("operation", "")

        # Special built-in operations
        builtin_operations = {"event_log", "work_and_maintenance", "detect_sections"}
        if operation in builtin_operations:
            return True

        # Check if operation exists in QueryAssetRegistry for history tool
        try:
            from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry
            registry = get_query_asset_registry()
            query_asset = registry.get_query_asset("history", operation)
            return query_asset is not None
        except Exception:
            return False

        return False

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a History operation.

        Dispatches to the appropriate function based on the 'operation' parameter.
        Special operations are handled by built-in functions.
        All other operations are executed dynamically via QueryAssetRegistry.

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

            # Special built-in operations with custom logic
            if operation == "detect_sections":
                sections = detect_history_sections(params.get("question", ""))
                result = {
                    "sections": list(sections),
                    "question": params.get("question", ""),
                }
                return ToolResult(success=True, data=result)

            # Built-in operations with their own functions
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
            else:
                # Generic execution via QueryAssetRegistry
                # This allows any operation to be added just by creating a Query Asset!
                result = await self._execute_generic(operation, params)

            return ToolResult(success=True, data=result)

        except ValueError as e:
            return await self.format_error(context, e, params)
        except Exception as e:
            return await self.format_error(context, e, params)

    async def _execute_generic(self, operation: str, params: Dict[str, Any]) -> dict:
        """
        Execute a generic operation dynamically via QueryAssetRegistry.

        This allows new operations to be added just by creating Query Assets,
        without any Python code changes.

        Args:
            operation: The operation name (must exist in QueryAssetRegistry)
            params: Parameters to pass to the query

        Returns:
            The query result
        """
        from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry

        # Get the Query Asset
        registry = get_query_asset_registry()
        query_asset = registry.get_query_asset("history", operation)

        if not query_asset:
            raise ValueError(f"Unknown History operation: {operation}")

        # Execute using ConnectionFactory
        source_type = query_asset.get("query_metadata", {}).get("source_type", "")
        conn = create_connection_for_query("history", operation)
        try:
            # Determine query type and execute
            if source_type == "postgresql" and query_asset.get("sql"):
                # SQL query - may need parameter substitution
                sql = query_asset["sql"]
                # Extract params or use defaults
                # Merge query_params and filters for SQL template processor
                execute_params = {
                    "query_params": params.get("query_params", {}),
                    "filters": params.get("filters", []),
                    "limit": params.get("limit"),
                    "offset": params.get("offset"),
                    "order_by": params.get("order_by"),
                    "order_dir": params.get("order_dir"),
                }
                result = conn.execute(sql, execute_params)
            elif source_type == "neo4j" and query_asset.get("cypher"):
                # Cypher query
                cypher = query_asset["cypher"]
                query_params = params.get("query_params", {})
                result = conn.execute(cypher, query_params)
            elif source_type == "rest_api" and query_asset.get("query_http"):
                # REST API query
                http_config = query_asset["query_http"]
                # Build request from params
                request_params = self._build_http_params(http_config, params)
                result = conn.execute(request_params)
            else:
                raise ValueError(f"Unsupported query configuration for operation: {operation}")

            # Normalize result
            if isinstance(result, list):
                return {"data": result, "count": len(result)}
            elif isinstance(result, dict):
                return result
            else:
                return {"data": result}
        finally:
            conn.close()

    def _build_http_params(self, http_config: dict, params: Dict[str, Any]) -> dict:
        """Build HTTP request parameters from config and input params."""
        method = http_config.get("method", "GET")
        path_template = http_config.get("path", "")
        headers = http_config.get("headers", {})

        # Replace path parameters
        path = path_template
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in path:
                path = path.replace(placeholder, str(value))

        return {
            "method": method,
            "path": path,
            "headers": headers,
            "params": params.get("query_params", {}),
        }


# Create and register the History tool
_history_tool = HistoryTool()
