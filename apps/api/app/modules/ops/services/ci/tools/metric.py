from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Literal, Tuple

from core.config import get_settings
from core.logging import get_logger
from schemas.tool_contracts import MetricAggregateResult, MetricSeriesResult

from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
)
from app.modules.ops.services.ci.tools.ci import ci_search, FilterSpec
from app.modules.ops.services.ci.tools.query_registry import (
    execute_query,
    create_connection_for_query,
    load_query_asset_simple,
)
from app.modules.asset_registry.loader import load_policy_asset

logger = get_logger(__name__)

# Hardcoded fallback (used if policy asset not found)
TIME_RANGES = {
    "last_1h": timedelta(hours=1),
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

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

AGG_FUNCTIONS = {"count", "max", "min", "avg"}
# Hardcoded fallback limits - will be loaded from DB via _get_limits()
MAX_CI_IDS = 300

# Cache for tool limits loaded from DB
_LIMITS_CACHE: Dict[str, Any] | None = None


def _get_limits() -> Dict[str, Any]:
    """
    Load Metric tool limits from policy asset.
    Falls back to hardcoded constants if asset not found.

    Returns:
        Dictionary with limit configuration:
        {
            "max_ci_ids": 300,
            "default_top_n": 10
        }
    """
    global _LIMITS_CACHE
    if _LIMITS_CACHE is not None:
        return _LIMITS_CACHE

    try:
        policy = load_policy_asset("tool_limits")
        if policy:
            content = policy.get("content", {})
            metric_limits = content.get("metric", {})
            if metric_limits:
                _LIMITS_CACHE = metric_limits
                logger.info(f"Loaded Metric tool limits from DB: {metric_limits}")
                return _LIMITS_CACHE
    except Exception as e:
        logger.warning(f"Failed to load tool_limits policy for Metric: {e}")

    # Fallback to hardcoded limits
    _LIMITS_CACHE = {
        "max_ci_ids": MAX_CI_IDS,
        "default_top_n": 10,
    }
    logger.info("Using hardcoded Metric tool limits (fallback)")
    return _LIMITS_CACHE


def _load_query(name: str) -> str:
    """
    Load a query by operation name using QueryAssetRegistry.

    This function provides backward compatibility with the old signature
    while using the new QueryAssetRegistry for dynamic discovery.

    Args:
        name: Operation name (maps to query asset operation)

    Returns:
        SQL query string
    """
    # Map old query filenames to operation names
    operation_map = {
        "metric_exists.sql": "exists",
        "metric_list.sql": "list",
        "metric_aggregate.sql": "aggregate",
        "metric_series.sql": "series",
        "metric_aggregate_by_ci.sql": "aggregate_by_ci",
    }

    operation = operation_map.get(name, name.replace(".sql", ""))
    return load_query_asset_simple("metric", operation)


def _calculate_time_range(time_range: str) -> Tuple[datetime, datetime]:
    kst_timezone = get_settings().timezone_offset
    now = datetime.now(kst_timezone)
    if DATE_PATTERN.match(time_range):
        start = datetime.fromisoformat(time_range).replace(tzinfo=kst_timezone)
        end = start + timedelta(days=1)
        return start, end
    time_ranges = _get_time_ranges()
    delta = time_ranges.get(time_range)
    if not delta:
        raise ValueError(f"Unsupported time range '{time_range}'")
    return now - delta, now


def _prepare_ci_ids(
    ci_id: str | None, ci_ids: list[str] | None
) -> tuple[list[str], bool, int]:
    candidates: list[str] = []
    if ci_ids:
        candidates = list(dict.fromkeys(ci_ids))
    elif ci_id:
        candidates = [ci_id]
    if not candidates:
        raise ValueError("Either ci_id or ci_ids must be provided")
    requested = len(candidates)
    limits = _get_limits()
    max_ci_ids = limits.get("max_ci_ids", 300)
    truncated = requested > max_ci_ids
    if truncated:
        candidates = candidates[:max_ci_ids]
    return candidates, truncated, requested


def metric_exists(tenant_id: str, metric_name: str) -> bool:
    """Check if a metric exists using the query registry."""
    result = execute_query("metric", "exists", {"metric_name": metric_name})
    # Result is a list of dicts like [{'?column?': 1}]
    if result and len(result) > 0:
        # Get the first value from the first row
        value = list(result[0].values())[0]
        return bool(value)
    return False


def list_metric_names(tenant_id: str, limit: int = 200) -> List[str]:
    """List metric names using the query registry."""
    result = execute_query("metric", "list", {"limit": limit})
    # Result is a list of dicts like [{'metric_name': 'cpu_usage'}, ...]
    if result:
        return [list(row.values())[0] for row in result]
    return []


def metric_aggregate(
    tenant_id: str,
    metric_name: str,
    time_range: Literal["last_1h", "last_24h", "last_7d"],
    agg: Literal["count", "max", "min", "avg"],
    ci_id: str | None = None,
    ci_ids: list[str] | None = None,
) -> MetricAggregateResult:
    """Aggregate metric values using the query registry with template substitution."""
    if agg not in AGG_FUNCTIONS:
        raise ValueError(f"Unsupported aggregate '{agg}'")
    ci_list, truncated, requested_count = _prepare_ci_ids(ci_id, ci_ids)
    time_from, time_to = _calculate_time_range(time_range)
    function = "COUNT(*)" if agg == "count" else f"{agg.upper()}(mv.value)"

    # Load query template and format it
    query_template = _load_query("metric_aggregate.sql")
    query = query_template.format(function=function)

    # Create connection and execute
    conn = create_connection_for_query("metric", "aggregate")
    try:
        params = {
            "tenant_id": tenant_id,
            "metric_name": metric_name,
            "ci_ids": ci_list,
            "time_from": time_from,
            "time_to": time_to,
        }
        result = conn.execute(query, params)
        value = None
        if result and len(result) > 0:
            value = list(result[0].values())[0]
    finally:
        conn.close()

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
    """Get metric time series data using the query registry."""
    time_from, time_to = _calculate_time_range(time_range)
    sanitized_limit = max(1, min(1000, limit or 200))

    result = execute_query("metric", "series", {
        "tenant_id": tenant_id,
        "metric_name": metric_name,
        "ci_id": ci_id,
        "time_from": time_from,
        "time_to": time_to,
        "limit": sanitized_limit,
    })

    rows: List[tuple[str, str]] = []
    if result:
        for row in result:
            values = list(row.values())
            rows.append((values[0].isoformat() if hasattr(values[0], 'isoformat') else str(values[0]), str(values[1])))

    return MetricSeriesResult(
        metric_name=metric_name,
        time_range=time_range,
        rows=rows,
    )


def metric_aggregate_by_ci(
    tenant_id: str,
    metric_name: str,
    agg: Literal["count", "max", "min", "avg"],
    time_range: Literal["last_1h", "last_24h", "last_7d"] | str,
    filters: Iterable[FilterSpec] | None = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Aggregate metric values per CI, returning top N CIs sorted by metric value.

    Generalized solution for queries like:
    - "CPU 사용량이 높은 상위 5개 서버는?"
    - "메모리 사용량이 낮은 하위 10개 서버는?"

    Args:
        tenant_id: Tenant ID
        metric_name: Metric name (e.g., "cpu_usage", "memory_usage")
        agg: Aggregation function ("max", "min", "avg", "count")
        time_range: Time range ("last_1h", "last_24h", "last_7d", or YYYY-MM-DD)
        filters: CI filters to limit the search space
        top_n: Number of top results to return

    Returns:
        Dict with columns, rows, query, params
    """
    # Step 1: Find all matching CIs based on filters
    filters_list = list(filters or [])
    search_result = ci_search(
        tenant_id=tenant_id,
        keywords=[],  # No keywords, just filters
        filters=filters_list if filters_list else None,
        limit=None,  # Get all matching CIs
    )

    if not search_result.records:
        return {
            "columns": ["ci_code", "ci_name", "ci_type", "ci_subtype", f"{agg}_{metric_name}"],
            "rows": [],
            "total": 0,
            "query": None,
            "params": [],
        }

    ci_ids = [r.ci_id for r in search_result.records]
    ci_id_to_record = {r.ci_id: r for r in search_result.records}

    # Step 2: Parse time_range
    kst_timezone = get_settings().timezone_offset
    if DATE_PATTERN.match(time_range):
        time_from = datetime.fromisoformat(time_range).replace(tzinfo=kst_timezone)
        time_to = time_from + timedelta(days=1)
    else:
        time_ranges = _get_time_ranges()
        delta = time_ranges.get(time_range, timedelta(hours=24))
        now = datetime.now(kst_timezone)
        time_from = now - delta
        time_to = now

    # Step 3: Build aggregation function
    agg_func_upper = agg.upper()
    function = (
        f"MAX(mv.value)"
        if agg == "max"
        else f"MIN(mv.value)"
        if agg == "min"
        else f"AVG(mv.value)"
        if agg == "avg"
        else "COUNT(*)"
    )

    # Step 4: Load and execute query using ConnectionFactory
    query_template = _load_query("metric_aggregate_by_ci.sql")
    query = query_template.format(function=function)

    conn = create_connection_for_query("metric", "aggregate_by_ci")
    try:
        params = {
            "tenant_id": tenant_id,
            "metric_name": metric_name,
            "ci_ids": ci_ids,
            "time_from": time_from,
            "time_to": time_to,
            "top_n": top_n,
        }
        metric_rows = conn.execute(query, params)
    finally:
        conn.close()

    # Step 5: Build result with CI details
    columns = ["ci_code", "ci_name", "ci_type", "ci_subtype", f"{agg}_{metric_name}"]
    rows = []
    if metric_rows:
        for row in metric_rows:
            values = list(row.values())
            ci_id = values[0]
            value = values[1]
            ci_record = ci_id_to_record.get(str(ci_id))
            if ci_record:
                rows.append([
                    ci_record.ci_code,
                    ci_record.ci_name,
                    ci_record.ci_type,
                    ci_record.ci_subtype,
                    str(value),
                ])

    return {
        "columns": columns,
        "rows": rows,
        "total": len(rows),
        "query": query.strip(),
        "params": params,
    }


# ==============================================================================
# Tool Interface Implementation
# ==============================================================================


class MetricTool(BaseTool):
    """
    Tool for Metric operations.

    Provides methods to query metrics data including aggregation and time series
    analysis. Supports multiple time ranges and aggregation functions.
    """

    @property
    def tool_type(self) -> str:
        """Return the Metric tool type."""
        return "metric"

    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute for the given operation.

        Metric tool handles:
        - Built-in operations: 'aggregate', 'aggregate_by_ci', 'series', 'exists', 'list'
        - Any operation registered in QueryAssetRegistry with tool_type='metric'

        This allows new operations to be added just by creating Query Assets,
        without any Python code changes.

        Args:
            context: Execution context
            params: Tool parameters

        Returns:
            True if this is a Metric operation, False otherwise
        """
        operation = params.get("operation", "")

        # Built-in operations with custom logic
        builtin_operations = {"aggregate", "aggregate_by_ci", "series", "exists", "list"}
        if operation in builtin_operations:
            return True

        # Check if operation exists in QueryAssetRegistry for metric tool
        try:
            from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry
            registry = get_query_asset_registry()
            query_asset = registry.get_query_asset("metric", operation)
            return query_asset is not None
        except Exception:
            return False

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a Metric operation.

        Dispatches to the appropriate function based on the 'operation' parameter.

        Parameters:
            operation (str): The operation to perform
            metric_name (str): Name of the metric
            time_range (str): Time range ('last_1h', 'last_24h', 'last_7d', or YYYY-MM-DD)
            agg (str, optional): Aggregation function ('count', 'max', 'min', 'avg')
            ci_id (str, optional): Single CI ID
            ci_ids (list[str], optional): Multiple CI IDs
            filters (list[dict], optional): CI filters for aggregate_by_ci
            top_n (int, optional): Top N results for aggregate_by_ci
            limit (int, optional): Result limit for series

        Returns:
            ToolResult with success status and operation result
        """
        try:
            operation = params.get("operation", "")
            tenant_id = context.tenant_id

            if operation == "aggregate":
                result = metric_aggregate(
                    tenant_id=tenant_id,
                    metric_name=params["metric_name"],
                    time_range=params["time_range"],
                    agg=params.get("agg", "count"),
                    ci_id=params.get("ci_id"),
                    ci_ids=params.get("ci_ids"),
                )
            elif operation == "aggregate_by_ci":
                result = metric_aggregate_by_ci(
                    tenant_id=tenant_id,
                    metric_name=params["metric_name"],
                    agg=params.get("agg", "max"),
                    time_range=params["time_range"],
                    filters=params.get("filters"),
                    top_n=params.get("top_n", 10),
                )
            elif operation == "series":
                result = metric_series_table(
                    tenant_id=tenant_id,
                    ci_id=params["ci_id"],
                    metric_name=params["metric_name"],
                    time_range=params["time_range"],
                    limit=params.get("limit", 200),
                )
            elif operation == "exists":
                exists = metric_exists(
                    tenant_id=tenant_id,
                    metric_name=params["metric_name"],
                )
                result = {"exists": exists, "metric_name": params["metric_name"]}
            elif operation == "list":
                result = {
                    "metrics": list_metric_names(
                        tenant_id=tenant_id,
                        limit=params.get("limit", 200),
                    )
                }
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

        Raises:
            ValueError: If operation not found in QueryAssetRegistry
        """
        from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry

        # Get the Query Asset
        registry = get_query_asset_registry()
        query_asset = registry.get_query_asset("metric", operation)

        if not query_asset:
            raise ValueError(f"Unknown Metric operation: {operation}")

        # Execute using ConnectionFactory
        source_type = query_asset.get("query_metadata", {}).get("source_type", "")
        conn = create_connection_for_query("metric", operation)
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


# Create and register the Metric tool
_metric_tool = MetricTool()
