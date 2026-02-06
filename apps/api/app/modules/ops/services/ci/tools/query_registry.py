"""
Query Asset Registry for dynamic query discovery.

This module provides a registry that indexes Query Assets by tool_type and operation,
enabling tools to dynamically discover and use queries without hardcoding filenames.

NOW SCHEMA-AWARE: Uses schema assets to build queries dynamically instead of hardcoded SQL.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.db import get_session_context
from sqlmodel import select

from app.modules.asset_registry.loader import load_query_asset, load_source_asset
from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.asset_registry.query_builder import SchemaQueryBuilder, get_query_builder
from app.modules.ops.services.connections import ConnectionFactory

logger = logging.getLogger(__name__)


class QueryAssetRegistry:
    """
    Registry for Query Assets indexed by tool_type and operation.

    This registry enables tools to dynamically discover queries based on their
    tool_type and operation metadata, rather than hardcoding query filenames.

    The index is built from query_metadata in TbAssetRegistry:
    - tool_type: Which tool uses this query (e.g., "metric", "ci")
    - operation: Which operation this query supports (e.g., "aggregate_by_ci", "search")
    """

    def __init__(self):
        """Initialize an empty query asset registry."""
        self._index: Dict[str, Dict[str, str]] = {}  # {tool_type: {operation: asset_name}}
        self._initialized = False

    def initialize(self, force_refresh: bool = False) -> None:
        """
        Load and index all Query Assets from the database.

        Args:
            force_refresh: Force re-indexing even if already initialized
        """
        if self._initialized and not force_refresh:
            return

        with get_session_context() as session:
            query = (
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "query")
                .where(TbAssetRegistry.status == "published")
            )

            assets = session.exec(query).all()

            # Clear existing index
            self._index = {}

            # Build index from query_metadata
            indexed_count = 0
            for asset in assets:
                metadata = asset.query_metadata or {}
                tool_type = metadata.get("tool_type")
                operation = metadata.get("operation")
                name = asset.name

                if tool_type and operation:
                    if tool_type not in self._index:
                        self._index[tool_type] = {}
                    self._index[tool_type][operation] = name
                    indexed_count += 1
                    logger.debug(
                        f"Indexed query asset: {tool_type}.{operation} -> {name}"
                    )

        self._initialized = True
        logger.info(
            f"QueryAssetRegistry initialized: {indexed_count} query assets indexed"
        )

    def get_query_asset(
        self, tool_type: str, operation: str
    ) -> Dict[str, Any] | None:
        """
        Get a query asset by tool_type and operation.

        Args:
            tool_type: Tool type (e.g., "metric", "ci")
            operation: Operation name (e.g., "aggregate_by_ci", "search")

        Returns:
            Dictionary with sql, cypher, http, params, metadata, or None if not found
        """
        if not self._initialized:
            self.initialize()

        if tool_type not in self._index:
            logger.debug(f"No queries indexed for tool_type: {tool_type}")
            return None

        asset_name = self._index[tool_type].get(operation)
        if not asset_name:
            logger.debug(f"No query indexed for {tool_type}.{operation}")
            return None

        # Load the asset directly from database to get all fields
        with get_session_context() as session:
            query = (
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "query")
                .where(TbAssetRegistry.status == "published")
                .where(TbAssetRegistry.name == asset_name)
            )
            asset = session.exec(query).first()

            if asset:
                return {
                    "sql": asset.query_sql,
                    "cypher": asset.query_cypher,
                    "http": asset.query_http,
                    "params": asset.query_params or {},
                    "metadata": asset.query_metadata or {},
                    "source": "asset_registry",
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                }

        # Fallback to file-based loading
        scope = f"postgres/{tool_type}"
        result, _ = load_query_asset(scope, asset_name)
        return result

    def list_operations(self, tool_type: str) -> List[str]:
        """
        List all available operations for a tool type.

        Args:
            tool_type: Tool type to list operations for

        Returns:
            List of operation names
        """
        if not self._initialized:
            self.initialize()

        return list(self._index.get(tool_type, {}).keys())

    def list_tool_types(self) -> List[str]:
        """
        List all available tool types.

        Returns:
            List of tool type strings
        """
        if not self._initialized:
            self.initialize()

        return list(self._index.keys())

    def is_available(self, tool_type: str, operation: str) -> bool:
        """
        Check if a query is available for a given tool_type and operation.

        Args:
            tool_type: Tool type
            operation: Operation name

        Returns:
            True if query is available
        """
        if not self._initialized:
            self.initialize()

        return (
            tool_type in self._index
            and operation in self._index[tool_type]
        )

    def get_index_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get the current index for debugging/inspection.

        Returns:
            Copy of the internal index {tool_type: {operation: asset_name}}
        """
        if not self._initialized:
            self.initialize()

        return self._index.copy()


# Global registry instance
_global_query_asset_registry: Optional[QueryAssetRegistry] = None


def get_query_asset_registry() -> QueryAssetRegistry:
    """Get the global query asset registry, creating it if necessary."""
    global _global_query_asset_registry
    if _global_query_asset_registry is None:
        _global_query_asset_registry = QueryAssetRegistry()
    return _global_query_asset_registry


def load_query_asset_simple(
    tool_type: str, operation: str
) -> str:
    """
    Simple wrapper to load SQL query for a tool operation.

    This is a convenience function for tools to load SQL queries
    without directly accessing the registry.

    Args:
        tool_type: Tool type (e.g., "metric", "ci")
        operation: Operation name (e.g., "aggregate_by_ci", "search")

    Returns:
        SQL query string

    Raises:
        ValueError: If query asset not found
    """
    registry = get_query_asset_registry()
    query_asset = registry.get_query_asset(tool_type, operation)

    if not query_asset:
        raise ValueError(
            f"Query asset not found for {tool_type}.{operation}. "
            f"Ensure a query asset exists with tool_type={tool_type} "
            f"and operation={operation} in query_metadata."
        )

    sql = query_asset.get("sql")
    if not sql:
        raise ValueError(
            f"Query asset for {tool_type}.{operation} has no SQL content"
        )

    return sql


def load_query_asset_with_source(
    tool_type: str, operation: str
) -> Dict[str, Any]:
    """
    Load a query asset with its associated source asset.

    This function loads both the Query Asset and the Source Asset referenced
    in query_metadata.source_ref, enabling tools to dynamically connect to
    the appropriate data source.

    Args:
        tool_type: Tool type (e.g., "metric", "ci")
        operation: Operation name (e.g., "aggregate_by_ci", "search")

    Returns:
        Dictionary with:
        - query: SQL/Cypher/HTTP query string or config
        - query_type: "sql", "cypher", or "http"
        - source_asset: Source asset dict with source_type and connection
        - metadata: Full query_metadata

    Raises:
        ValueError: If query asset or source asset not found
    """
    registry = get_query_asset_registry()
    query_asset = registry.get_query_asset(tool_type, operation)

    if not query_asset:
        raise ValueError(
            f"Query asset not found for {tool_type}.{operation}. "
            f"Ensure a query asset exists with tool_type={tool_type} "
            f"and operation={operation} in query_metadata."
        )

    metadata = query_asset.get("metadata", {})
    source_ref = metadata.get("source_ref")

    if not source_ref:
        raise ValueError(
            f"Query asset for {tool_type}.{operation} has no source_ref in metadata. "
            f"Add source_ref to query_metadata to specify which source to use."
        )

    # Load the Source Asset
    source_asset = load_source_asset(source_ref)
    if not source_asset:
        raise ValueError(
            f"Source asset '{source_ref}' not found. "
            f"Ensure a source asset exists with name={source_ref}."
        )

    # Determine query type and get the appropriate query
    # Try in order: sql, cypher, http
    query_sql = query_asset.get("sql")
    query_cypher = query_asset.get("cypher")
    query_http = query_asset.get("http")

    if query_sql:
        query_type = "sql"
        query = query_sql
    elif query_cypher:
        query_type = "cypher"
        query = query_cypher
    elif query_http:
        query_type = "http"
        query = query_http
    else:
        # Fallback: check the source_type to determine default query type
        source_type = source_asset.get("source_type", "postgresql")
        if source_type in ("postgresql", "mysql", "bigquery", "snowflake"):
            query_type = "sql"
            query = query_sql or ""
        elif source_type == "neo4j":
            query_type = "cypher"
            query = query_cypher or ""
        elif source_type in ("rest_api", "graphql_api"):
            query_type = "http"
            query = query_http or {}
        else:
            raise ValueError(
                f"Query asset for {tool_type}.{operation} has no query content. "
                f"Ensure query_sql, query_cypher, or query_http is set."
            )

    return {
        "query": query,
        "query_type": query_type,
        "source_asset": source_asset,
        "metadata": metadata,
    }


def create_connection_for_query(
    tool_type: str, operation: str
):
    """
    Create a connection for executing a query.

    This function loads the Query Asset and Source Asset, then creates
    a connection using ConnectionFactory based on the source type.

    Args:
        tool_type: Tool type (e.g., "metric", "ci")
        operation: Operation name (e.g., "aggregate_by_ci", "search")

    Returns:
        SourceConnection instance (connected and ready to use)

    Raises:
        ValueError: If query asset or source asset not found
    """
    query_data = load_query_asset_with_source(tool_type, operation)
    source_asset = query_data["source_asset"]

    # Create connection using ConnectionFactory
    connection = ConnectionFactory.create(source_asset)
    return connection


def execute_query(
    tool_type: str, operation: str, params: Dict[str, Any] | None = None
) -> Any:
    """
    Execute a query using the appropriate connection.

    This function loads the Query Asset, creates a connection, and executes
    the query with the given parameters.

    Args:
        tool_type: Tool type (e.g., "metric", "ci")
        operation: Operation name (e.g., "aggregate_by_ci", "search")
        params: Query parameters (optional)

    Returns:
        Query result (format varies by source type)

    Raises:
        ValueError: If query asset or source asset not found
        RuntimeError: If query execution fails
    """
    query_data = load_query_asset_with_source(tool_type, operation)
    source_asset = query_data["source_asset"]
    query = query_data["query"]
    query_type = query_data["query_type"]

    # Create and execute using ConnectionFactory
    connection = ConnectionFactory.create(source_asset)

    try:
        if query_type in ("sql", "cypher"):
            result = connection.execute(query, params)
        elif query_type == "http":
            result = connection.execute(query, params)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
        return result
    finally:
        connection.close()


# =============================================================================
# SCHEMA-BASED QUERY BUILDER FUNCTIONS
# =============================================================================

def _get_required_tenant_id(params: Dict[str, Any]) -> str:
    """Get tenant_id from params, raise error if missing."""
    tenant_id = params.get("tenant_id")
    if not tenant_id:
        raise ValueError(
            "tenant_id is required parameter. "
            "Please provide tenant_id in params."
        )
    return tenant_id


def build_query_from_schema(
    tool_type: str,
    operation: str,
    params: Dict[str, Any] | None = None,
    schema_asset_name: str = "primary_postgres_schema",
) -> str:
    """
    Build a SQL query dynamically using schema instead of hardcoded SQL.

    This replaces the need for hardcoded query_sql in query assets.
    The query is built based on:
    1. Schema asset (table/column definitions)
    2. Tool type and operation (determines query pattern)
    3. Parameters (filters, columns, aggregations, etc.)

    Args:
        tool_type: Tool type (e.g., "ci", "metric", "history")
        operation: Operation (e.g., "search", "aggregate_by_ci", "series")
        params: Query parameters (filters, columns, aggregations, etc.)
            - tenant_id: REQUIRED - tenant identifier
        schema_asset_name: Name of schema asset to use

    Returns:
        Complete SQL query string

    Raises:
        ValueError: If schema not found, operation not supported, or tenant_id missing
    """
    params = params or {}
    builder = get_query_builder(schema_asset_name)

    # CI operations
    if tool_type == "ci":
        return _build_ci_query(operation, builder, params)

    # Metric operations
    elif tool_type == "metric":
        return _build_metric_query(operation, builder, params)

    # History operations
    elif tool_type == "history":
        return _build_history_query(operation, builder, params)

    # Graph operations
    elif tool_type == "graph":
        return _build_graph_query(operation, builder, params)

    else:
        raise ValueError(
            f"Unsupported tool_type for schema-based query: {tool_type}"
        )


def _build_ci_query(operation: str, builder: SchemaQueryBuilder, params: Dict[str, Any]) -> str:
    """Build CI query using schema"""

    # CI search with filters
    if operation == "search":
        table_name = "ci"
        columns = params.get("columns") or ["ci_id", "ci_code", "ci_name", "ci_type", "ci_subtype", "status", "location", "owner"]

        # Build WHERE clause from filters
        filters = params.get("filters", [])
        where_conditions = []
        where_params = []

        for f in filters:
            field = f.get("field")
            op = f.get("op", "=")
            value = f.get("value")

            if field and value is not None:
                # Handle qualified column names
                col_expr = f"{table_name}.{field}" if "." not in field else field

                # Validate column exists
                col_name = field.split(".")[-1]
                if not builder.has_column(table_name, col_name):
                    logger.warning(f"Column {col_name} not in {table_name} schema")
                    continue

                if op == "=":
                    where_conditions.append(f"{col_expr} = %s")
                    where_params.append(value)
                elif op == "!=":
                    where_conditions.append(f"{col_expr} != %s")
                    where_params.append(value)
                elif op == "like":
                    where_conditions.append(f"{col_expr} ILIKE %s")
                    where_params.append(f"%{value}%")
                elif op == "in":
                    where_conditions.append(f"{col_expr} = ANY(%s)")
                    where_params.append(value if isinstance(value, list) else [value])

        # Add tenant_id filter (REQUIRED)
        tenant_id = _get_required_tenant_id(params)
        where_conditions.append(f"{table_name}.tenant_id = %s")
        where_params.append(tenant_id)

        # Add deleted_at filter
        where_conditions.append(f"{table_name}.deleted_at IS NULL")

        where_clause = " AND ".join(where_conditions) if where_conditions else None

        # Handle JOIN with ci_ext if attributes/tags needed
        joins = []
        if any(c in columns for c in ["attributes", "tags"]):
            joins.append({
                "table": "ci_ext",
                "on": f"{table_name}.ci_id = ci_ext.ci_id",
                "type": "LEFT"
            })

        # Build query
        limit = params.get("limit", 50)
        offset = params.get("offset", 0)
        order_by = params.get("order_by") or f"{table_name}.created_at DESC"

        query = builder.build_select(
            table_name=table_name,
            columns=columns,
            where_clause=where_clause,
            joins=joins if joins else None,
            order_by=order_by,
            limit=limit,
            offset=offset if offset > 0 else None,
        )

        # Store params for execution
        query += f" -- PARAMS: {where_params}"
        return query

    # CI aggregate (group by)
    elif operation == "aggregate":
        table_name = "ci"
        group_by = params.get("group_by", [])
        metrics = params.get("metrics", [{"column": "*", "agg": "count", "alias": "count"}])

        tenant_id = _get_required_tenant_id(params)
        filters = params.get("filters", [])
        where_conditions = [f"{table_name}.tenant_id = %s", f"{table_name}.deleted_at IS NULL"]
        where_params = [tenant_id]

        for f in filters:
            field = f.get("field")
            op = f.get("op", "=")
            value = f.get("value")
            if field and value is not None:
                col_expr = f"{table_name}.{field}" if "." not in field else field
                if op == "=":
                    where_conditions.append(f"{col_expr} = %s")
                    where_params.append(value)

        where_clause = " AND ".join(where_conditions)

        query = builder.build_aggregate(
            table_name=table_name,
            group_by=group_by,
            metrics=metrics,
            where_clause=where_clause,
            order_by=params.get("order_by") or "count DESC",
            limit=params.get("limit", 10),
        )
        query += f" -- PARAMS: {where_params}"
        return query

    # CI get (single by ID)
    elif operation == "get":
        table_name = "ci"
        ci_id = params.get("ci_id")
        if not ci_id:
            raise ValueError("ci_id required for get operation")

        tenant_id = _get_required_tenant_id(params)
        columns = params.get("columns") or ["*"]
        where_clause = f"{table_name}.ci_id = %s AND {table_name}.tenant_id = %s AND {table_name}.deleted_at IS NULL"

        query = builder.build_select(
            table_name=table_name,
            columns=columns if columns != ["*"] else None,
            where_clause=where_clause,
            limit=1,
        )
        query += f" -- PARAMS: ['{ci_id}', '{tenant_id}']"
        return query

    # CI count
    elif operation == "count":
        table_name = "ci"
        tenant_id = _get_required_tenant_id(params)
        filters = params.get("filters", [])
        where_conditions = [f"{table_name}.tenant_id = %s", f"{table_name}.deleted_at IS NULL"]
        where_params = [tenant_id]

        for f in filters:
            field = f.get("field")
            value = f.get("value")
            if field and value is not None:
                col_expr = f"{table_name}.{field}" if "." not in field else field
                where_conditions.append(f"{col_expr} = %s")
                where_params.append(value)

        where_clause = " AND ".join(where_conditions) if where_conditions else None
        query = builder.build_count(table_name, where_clause)
        query += f" -- PARAMS: {where_params}"
        return query

    else:
        raise ValueError(f"Unsupported CI operation: {operation}")


def _build_metric_query(operation: str, builder: SchemaQueryBuilder, params: Dict[str, Any]) -> str:
    """Build metric query using schema"""

    def _build_time_filter(column: str) -> tuple[str, list[str]]:
        time_range = params.get("time_range")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        full_time = params.get("full_time_range") or time_range in {"all_time", "all"}

        if full_time:
            return "", []

        if start_time and end_time:
            return f" AND {column} >= '{start_time}' AND {column} < '{end_time}'", []

        interval_map = {
            "last_1h": "1 hour",
            "last_24h": "24 hours",
            "last_7d": "7 days",
            "last_30d": "30 days",
        }
        interval = interval_map.get(time_range, "1 hour")
        return f" AND {column} >= NOW() - INTERVAL '{interval}'", []

    if operation == "aggregate_by_ci":
        # Aggregate metric values grouped by CI
        metric_name = params.get("metric_name")
        if not metric_name:
            raise ValueError("metric_name required for aggregate_by_ci")

        agg = params.get("agg", "avg")
        time_filter, _ = _build_time_filter("metric_value.time")

        ci_ids = params.get("ci_ids") or []
        ci_filter = ""
        if isinstance(ci_ids, list) and ci_ids:
            escaped = [str(cid).replace("'", "''") for cid in ci_ids]
            ci_list = ", ".join(f"'{cid}'" for cid in escaped)
            ci_filter = f" AND metric_value.ci_id IN ({ci_list})"

        query = f"""
        SELECT
            ci.ci_id,
            ci.ci_code,
            ci.ci_name,
            {agg.upper()}(metric_value.value) AS metric_value
        FROM metric_value
        JOIN metric_def ON metric_value.metric_id = metric_def.metric_id
        JOIN ci ON metric_value.ci_id = ci.ci_id
        WHERE metric_def.metric_name = %s
            {time_filter}
            AND ci.tenant_id = %s
            AND ci.deleted_at IS NULL
            {ci_filter}
        GROUP BY ci.ci_id, ci.ci_code, ci.ci_name
        ORDER BY metric_value {('DESC' if agg in ['max', 'avg'] else 'ASC')}
        LIMIT %s
        """
        tenant_id = _get_required_tenant_id(params)
        query += f" -- PARAMS: ['{metric_name}', '{tenant_id}', {params.get('top_n', 10)}]"
        return query

    elif operation == "series":
        # Time series for a metric
        metric_name = params.get("metric_name")
        ci_id = params.get("ci_id")
        time_filter, _ = _build_time_filter("metric_value.time")

        query = f"""
        SELECT
            time_bucket('1 hour', metric_value.time) AS bucket,
            AVG(metric_value.value) AS avg_value,
            MAX(metric_value.value) AS max_value,
            MIN(metric_value.value) AS min_value
        FROM metric_value
        JOIN metric_def ON metric_value.metric_id = metric_def.metric_id
        WHERE metric_def.metric_name = %s
            {time_filter}
        """

        if ci_id:
            query += f"    AND metric_value.ci_id = %s\n"
            query += f" -- PARAMS: ['{metric_name}', '{ci_id}']"
        else:
            query += f" -- PARAMS: ['{metric_name}']"

        query += " GROUP BY bucket ORDER BY bucket ASC"
        return query

    elif operation == "aggregate":
        # Single aggregate value
        metric_name = params.get("metric_name")
        agg = params.get("agg", "avg")
        time_filter, _ = _build_time_filter("metric_value.time")

        query = f"""
        SELECT {agg.upper()}(metric_value.value) AS value
        FROM metric_value
        JOIN metric_def ON metric_value.metric_id = metric_def.metric_id
        WHERE metric_def.metric_name = %s
            {time_filter}
        """
        query += f" -- PARAMS: ['{metric_name}']"
        return query

    else:
        raise ValueError(f"Unsupported metric operation: {operation}")


def _build_history_query(operation: str, builder: SchemaQueryBuilder, params: Dict[str, Any]) -> str:
    """Build history query using schema"""

    def _build_time_filter(column: str) -> str:
        time_range = params.get("time_range")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        full_time = params.get("full_time_range") or time_range in {"all_time", "all"}

        if full_time:
            return ""

        if start_time and end_time:
            return f" AND {column} >= '{start_time}' AND {column} < '{end_time}'"

        interval_map = {
            "last_24h": "24 hours",
            "last_7d": "7 days",
            "last_30d": "30 days",
        }
        interval = interval_map.get(time_range, "7 days")
        return f" AND {column} >= NOW() - INTERVAL '{interval}'"

    def _build_ci_filter(column: str) -> str:
        ci_id = params.get("ci_id")
        ci_ids = params.get("ci_ids")
        if ci_id:
            return f" AND {column} = '{str(ci_id).replace(\"'\", \"''\")}'"
        if isinstance(ci_ids, list) and ci_ids:
            escaped = [str(cid).replace(\"'\", \"''\") for cid in ci_ids]
            ci_list = \", \".join(f\"'{cid}'\" for cid in escaped)
            return f\" AND {column} IN ({ci_list})\"
        return ""

    if operation == "work_and_maintenance":
        # Combine work_history and maintenance_history
        limit = params.get("limit", 50)
        work_time_filter = _build_time_filter("start_time")
        maint_time_filter = _build_time_filter("start_time")
        work_ci_filter = _build_ci_filter("ci_id")
        maint_ci_filter = _build_ci_filter("ci_id")

        query = f"""
        (
            SELECT
                'work' AS history_type,
                work_type,
                summary,
                start_time,
                end_time,
                duration_min,
                performer,
                result
            FROM work_history
            WHERE 1=1
                {work_time_filter}
                {work_ci_filter}
                AND tenant_id = %s
            ORDER BY start_time DESC
            LIMIT {limit}
        )
        UNION ALL
        (
            SELECT
                'maintenance' AS history_type,
                maint_type AS work_type,
                summary,
                start_time,
                end_time,
                duration_min,
                performer,
                result
            FROM maintenance_history
            WHERE 1=1
                {maint_time_filter}
                {maint_ci_filter}
                AND tenant_id = %s
            ORDER BY start_time DESC
            LIMIT {limit}
        )
        ORDER BY start_time DESC
        LIMIT {limit * 2}
        """
        tenant_id = _get_required_tenant_id(params)
        query += f" -- PARAMS: ['{tenant_id}', '{tenant_id}']"
        return query

    elif operation == "work_history":
        limit = params.get("limit", 50)
        time_filter = _build_time_filter("start_time")
        ci_filter = _build_ci_filter("ci_id")
        query = f"""
        SELECT
            start_time,
            work_type,
            summary,
            result,
            performer
        FROM work_history
        WHERE 1=1
            {time_filter}
            {ci_filter}
            AND tenant_id = %s
        ORDER BY created_at DESC
        LIMIT {limit}
        """
        tenant_id = _get_required_tenant_id(params)
        query += f" -- PARAMS: ['{tenant_id}']"
        return query

    elif operation == "maintenance_history":
        limit = params.get("limit", 50)
        time_filter = _build_time_filter("start_time")
        ci_filter = _build_ci_filter("ci_id")
        query = f"""
        SELECT
            start_time,
            maint_type,
            summary,
            result,
            performer
        FROM maintenance_history
        WHERE 1=1
            {time_filter}
            {ci_filter}
            AND tenant_id = %s
        ORDER BY start_time DESC
        LIMIT {limit}
        """
        tenant_id = _get_required_tenant_id(params)
        query += f" -- PARAMS: ['{tenant_id}']"
        return query

    elif operation == "event_log":
        limit = params.get("limit", 50)
        time_filter = _build_time_filter("time")
        ci_filter = _build_ci_filter("ci_id")
        query = f"""
        SELECT
            time,
            event_type,
            severity,
            title,
            message
        FROM event_log
        WHERE 1=1
            {time_filter}
            {ci_filter}
            AND tenant_id = %s
        ORDER BY time DESC
        LIMIT {limit}
        """
        tenant_id = _get_required_tenant_id(params)
        query += f" -- PARAMS: ['{tenant_id}']"
        return query

    else:
        raise ValueError(f"Unsupported history operation: {operation}")


def _build_graph_query(operation: str, builder: SchemaQueryBuilder, params: Dict[str, Any]) -> str:
    """Build graph query using schema (for Neo4j)"""
    # Graph queries use Neo4j, not SQL
    # Return a placeholder that indicates this should use Cypher
    return "-- GRAPH QUERY: Use Neo4j Cypher query instead of SQL"
