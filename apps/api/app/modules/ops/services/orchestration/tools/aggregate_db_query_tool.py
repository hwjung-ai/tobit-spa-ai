"""
Aggregate DB Query Tool - Execute aggregate SQL queries on operational data tables.

This tool handles aggregate queries (count, group_by, distribution) for:
- event_log: events, severity, event types
- work_history: work activities, types, results
- maintenance_history: maintenance activities, types, results
- ci: CI configuration items
- metric_value: metric data points
- document: document management
- tb_audit_log: audit log entries

Replaces the Query Asset system for aggregate/count queries.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from core.db import get_session_context

from .base import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


# Scope → table mapping
SCOPE_TABLE_MAP = {
    "event": "event_log",
    "event_log": "event_log",
    "work": "work_history",
    "work_history": "work_history",
    "maintenance": "maintenance_history",
    "maintenance_history": "maintenance_history",
    "work_and_maintenance": "work_history",  # handled specially
    "ci": "ci",
    "s1": "ci",  # default CI scope
    "metric": "metric_value",
    "metric_value": "metric_value",
    "document": "documents",   # actual table name is 'documents'
    "audit": "tb_audit_log",
    "audit_log": "tb_audit_log",
    "graph": "ci",  # graph scope falls back to CI
}

# Valid column names per table (whitelist for security)
VALID_COLUMNS = {
    "event_log": {
        "event_type", "severity", "source", "title", "message", "time",
        "tenant_id", "ci_id",
    },
    "work_history": {
        "work_type", "result", "impact_level", "requested_by", "approved_by",
        "start_time", "end_time", "tenant_id", "ci_id", "summary",
    },
    "maintenance_history": {
        "maint_type", "result", "performer", "start_time", "end_time",
        "tenant_id", "ci_id", "summary",
    },
    "ci": {
        "ci_type", "ci_subtype", "ci_category", "status", "location",
        "owner", "tenant_id", "ci_id", "ci_name", "ci_code",
    },
    "metric_value": {
        "metric_name", "ci_id", "tenant_id", "time", "value",
    },
    "documents": {
        "content_type", "status", "format", "category", "tenant_id",
        "filename", "size", "created_by", "user_id",
    },
    "tb_audit_log": {
        "action", "resource_type", "tenant_id", "user_id", "created_at",
    },
}

# Column alias normalization: LLM may generate abbreviated column names
# Map these to actual column names per table
COLUMN_ALIASES: Dict[str, Dict[str, str]] = {
    "ci": {
        "type": "ci_type",
        "subtype": "ci_subtype",
        "category": "ci_category",
        "name": "ci_name",
        "code": "ci_code",
        "id": "ci_id",
    },
    "event_log": {
        "type": "event_type",
        "id": "ci_id",
    },
    "work_history": {
        "type": "work_type",
        "id": "ci_id",
    },
    "maintenance_history": {
        "type": "maint_type",
        "id": "ci_id",
    },
    "documents": {
        "type": "content_type",
    },
    "tb_audit_log": {
        "type": "action",
    },
}

# PostgreSQL reserved words that need quoting
PG_RESERVED_WORDS = {
    "type", "value", "time", "status", "source", "format", "action",
    "result", "size", "owner", "location", "summary", "message",
}


def _normalize_column(table: str, column: str) -> str:
    """Normalize column name using alias mapping."""
    aliases = COLUMN_ALIASES.get(table, {})
    return aliases.get(column, column)


def _validate_column(table: str, column: str) -> bool:
    """Validate column name against whitelist (after normalization)."""
    normalized = _normalize_column(table, column)
    valid = VALID_COLUMNS.get(table, set())
    return normalized in valid


def _safe_column(table: str, column: str, default: str = "ci_type") -> str:
    """Return normalized column if valid, else default."""
    normalized = _normalize_column(table, column)
    if normalized in VALID_COLUMNS.get(table, set()):
        return normalized
    logger.warning(f"Invalid column '{column}' for table '{table}', using default '{default}'")
    return default


def _quote_column(column: str) -> str:
    """Quote column name if it's a PostgreSQL reserved word."""
    if column.lower() in PG_RESERVED_WORDS:
        return f'"{column}"'
    return column


class AggregateDbQueryTool(BaseTool):
    """
    Tool that executes aggregate SQL queries on operational data tables.

    Handles count, group_by, distribution queries for:
    - event_log, work_history, maintenance_history, ci, metric_value, document, tb_audit_log
    """

    @property
    def tool_type(self) -> str:
        return "aggregate_db_query"

    @property
    def tool_name(self) -> str:
        return "AggregateDbQueryTool"

    async def should_execute(self, context: ToolContext, params: Dict[str, Any]) -> bool:
        """Execute if scope maps to a known table."""
        scope = params.get("scope", "s1")
        group_by = params.get("group_by", [])
        metrics = params.get("metrics", [])

        # Always execute for any known scope (including ci/s1 for status distribution)
        if scope in SCOPE_TABLE_MAP:
            return True

        # Execute if group_by contains any known fields
        all_known_fields = set()
        for cols in VALID_COLUMNS.values():
            all_known_fields.update(cols)
        # Also include alias source names
        for aliases in COLUMN_ALIASES.values():
            all_known_fields.update(aliases.keys())

        if any(f in all_known_fields for f in (group_by or [])):
            return True

        # Execute if metrics contain count/aggregate operations
        if any("event" in m or "work" in m or "maint" in m or "document" in m or "ci" in m
               for m in (metrics or [])):
            return True

        return False

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """Execute aggregate query based on scope and group_by parameters."""
        scope = params.get("scope", "s1")
        group_by = params.get("group_by", [])
        metrics = params.get("metrics", [])
        filters = params.get("filters", [])
        top_n = params.get("top_n", 10) or 10
        tenant_id = params.get("tenant_id") or context.tenant_id

        try:
            top_n = max(1, min(int(top_n), 1000))
        except (ValueError, TypeError):
            top_n = 10

        # Determine target table from scope
        table = SCOPE_TABLE_MAP.get(scope, "ci")

        # Special handling for work_and_maintenance
        if scope == "work_and_maintenance":
            return await self._execute_work_and_maintenance(
                context, params, tenant_id, group_by, filters, top_n
            )

        # Special handling for work scope with result group_by → success rate
        if table == "work_history" and not group_by and not filters:
            # Simple count of work_history
            pass  # fall through to normal query

        # Special handling for metric_value: use pg_class for simple COUNT (no group_by)
        # metric_value has 10M+ rows - full COUNT(*) crashes the server
        if table == "metric_value" and not group_by and not filters:
            approx_count = self._get_approx_count(table, tenant_id)
            if approx_count is not None:
                logger.info(f"Using pg_class approx count for metric_value: {approx_count}")
                return ToolResult(
                    success=True,
                    data={
                        "rows": [{"count": approx_count}],
                        "count": 1,
                        "table": table,
                        "scope": scope,
                        "group_by": group_by,
                        "approximate": True,
                    },
                    metadata={
                        "query_type": "aggregate_db_query",
                        "table": table,
                        "row_count": 1,
                        "approximate": True,
                    },
                )

        # Check if metrics contain MAX/MIN/SUM operations (e.g. "MAX(size)", "MIN(size)")
        agg_metric = self._parse_agg_metric(metrics, table)
        if agg_metric:
            return self._execute_agg_metric(table, scope, agg_metric, filters, tenant_id)

        # Build and execute query
        try:
            sql, sql_params = self._build_aggregate_sql(
                table=table,
                group_by=group_by,
                metrics=metrics,
                filters=filters,
                top_n=top_n,
                tenant_id=tenant_id,
            )

            logger.info(
                f"AggregateDbQueryTool executing: table={table}, scope={scope}, "
                f"group_by={group_by}, sql={sql[:200]}"
            )

            rows = self._execute_sql(sql, sql_params)

            return ToolResult(
                success=True,
                data={
                    "rows": rows,
                    "count": len(rows),
                    "table": table,
                    "scope": scope,
                    "group_by": group_by,
                },
                metadata={
                    "query_type": "aggregate_db_query",
                    "table": table,
                    "row_count": len(rows),
                },
            )

        except Exception as e:
            logger.error(f"AggregateDbQueryTool failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                error_details={
                    "table": table,
                    "scope": scope,
                    "group_by": group_by,
                },
            )

    def _build_aggregate_sql(
        self,
        table: str,
        group_by: List[str],
        metrics: List[str],
        filters: List[Any],
        top_n: int,
        tenant_id: str,
    ) -> tuple[str, list]:
        """Build parameterized aggregate SQL query."""
        params = []

        # Validate, normalize, and sanitize group_by columns
        valid_group_by = []
        for col in (group_by or []):
            # Normalize alias (e.g. "type" → "ci_type" for ci table)
            normalized = _normalize_column(table, col)
            if normalized in VALID_COLUMNS.get(table, set()):
                valid_group_by.append(normalized)
            else:
                logger.warning(f"Skipping invalid column '{col}' (normalized: '{normalized}') for table '{table}'")

        # Build SELECT clause with proper quoting for reserved words
        if valid_group_by:
            quoted_cols = [_quote_column(c) for c in valid_group_by]
            select_cols = ", ".join(quoted_cols)
            select_clause = f"{select_cols}, COUNT(*) AS count"
            group_clause = f"GROUP BY {select_cols}"
            order_clause = "ORDER BY count DESC"
        else:
            # No group_by → simple count
            select_clause = "COUNT(*) AS count"
            group_clause = ""
            order_clause = ""

        # Build WHERE clause
        where_conditions = ["tenant_id = %s"]
        params.append(tenant_id)

        # Add deleted_at filter for CI table
        if table == "ci":
            where_conditions.append("deleted_at IS NULL")

        # Add user-specified filters
        for f in (filters or []):
            if isinstance(f, dict):
                field = f.get("field", "")
                op = f.get("op", "=")
                value = f.get("value")
                # Normalize alias first
                normalized_field = _normalize_column(table, field)
                # Validate field
                if normalized_field and _validate_column(table, normalized_field) and value is not None:
                    quoted_field = _quote_column(normalized_field)
                    if op == "ILIKE":
                        where_conditions.append(f"{quoted_field} ILIKE %s")
                        params.append(f"%{value}%")
                    elif op in ("=", "!=", "<", ">", "<=", ">="):
                        where_conditions.append(f"{quoted_field} {op} %s")
                        params.append(value)

        where_clause = "WHERE " + " AND ".join(where_conditions)

        # Build LIMIT clause (only for group_by queries, not simple COUNT)
        if valid_group_by:
            limit_clause = "LIMIT %s"
            params.append(top_n)
        else:
            limit_clause = ""

        sql = f"""
SELECT {select_clause}
FROM {table}
{where_clause}
{group_clause}
{order_clause}
{limit_clause}
""".strip()

        return sql, params

    async def _execute_work_and_maintenance(
        self,
        context: ToolContext,
        params: Dict[str, Any],
        tenant_id: str,
        group_by: List[str],
        filters: List[Any],
        top_n: int,
    ) -> ToolResult:
        """Execute combined work_history + maintenance_history query."""
        try:
            # Determine what to group by
            wh_group = []
            mh_group = []

            for col in (group_by or []):
                if col == "work_type" or _validate_column("work_history", col):
                    wh_group.append(col)
                if col == "maint_type" or _validate_column("maintenance_history", col):
                    mh_group.append(col)

            # If no specific group_by, just count both tables
            if not group_by:
                sql = """
SELECT 'work_history' AS source, COUNT(*) AS count
FROM work_history
WHERE tenant_id = %s
UNION ALL
SELECT 'maintenance_history' AS source, COUNT(*) AS count
FROM maintenance_history
WHERE tenant_id = %s
"""
                rows = self._execute_sql(sql, [tenant_id, tenant_id])
            elif "result" in group_by:
                # Group by result for both tables
                sql = """
SELECT result, COUNT(*) AS count
FROM (
    SELECT result FROM work_history WHERE tenant_id = %s
    UNION ALL
    SELECT result FROM maintenance_history WHERE tenant_id = %s
) combined
GROUP BY result
ORDER BY count DESC
LIMIT %s
"""
                rows = self._execute_sql(sql, [tenant_id, tenant_id, top_n])
            else:
                # Default: count both
                sql = """
SELECT 'work_history' AS source, COUNT(*) AS count
FROM work_history
WHERE tenant_id = %s
UNION ALL
SELECT 'maintenance_history' AS source, COUNT(*) AS count
FROM maintenance_history
WHERE tenant_id = %s
"""
                rows = self._execute_sql(sql, [tenant_id, tenant_id])

            return ToolResult(
                success=True,
                data={
                    "rows": rows,
                    "count": len(rows),
                    "scope": "work_and_maintenance",
                },
                metadata={"query_type": "aggregate_db_query", "row_count": len(rows)},
            )

        except Exception as e:
            logger.error(f"work_and_maintenance aggregate failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                error_details={"scope": "work_and_maintenance"},
            )

    def _parse_agg_metric(self, metrics: List[str], table: str) -> Optional[Dict[str, str]]:
        """Parse metrics list for MAX/MIN/SUM/AVG operations.
        
        Supports formats like: "MAX(size)", "MIN(size)", "SUM(value)", "AVG(value)"
        Returns dict with {func, column} or None if no agg metric found.
        """
        if not metrics:
            return None
        for m in metrics:
            if not isinstance(m, str):
                continue
            m_upper = m.upper().strip()
            # Match patterns like MAX(size), MIN(size), SUM(value), AVG(value)
            match = re.match(r'^(MAX|MIN|SUM|AVG)\((\w+)\)$', m_upper)
            if match:
                func = match.group(1)
                col = match.group(2).lower()
                # Normalize column alias
                normalized = _normalize_column(table, col)
                if normalized in VALID_COLUMNS.get(table, set()):
                    return {"func": func, "column": normalized}
                # Try original column name
                if col in VALID_COLUMNS.get(table, set()):
                    return {"func": func, "column": col}
        return None

    def _execute_agg_metric(
        self,
        table: str,
        scope: str,
        agg_metric: Dict[str, str],
        filters: List[Any],
        tenant_id: str,
    ) -> ToolResult:
        """Execute MAX/MIN/SUM/AVG aggregate query."""
        func = agg_metric["func"]
        column = agg_metric["column"]
        quoted_col = _quote_column(column)

        params = [tenant_id]
        where_conditions = ["tenant_id = %s"]

        if table == "ci":
            where_conditions.append("deleted_at IS NULL")

        for f in (filters or []):
            if isinstance(f, dict):
                field = f.get("field", "")
                op = f.get("op", "=")
                value = f.get("value")
                normalized_field = _normalize_column(table, field)
                if normalized_field and _validate_column(table, normalized_field) and value is not None:
                    quoted_field = _quote_column(normalized_field)
                    if op == "ILIKE":
                        where_conditions.append(f"{quoted_field} ILIKE %s")
                        params.append(f"%{value}%")
                    elif op in ("=", "!=", "<", ">", "<=", ">="):
                        where_conditions.append(f"{quoted_field} {op} %s")
                        params.append(value)

        where_clause = "WHERE " + " AND ".join(where_conditions)
        sql = f"SELECT {func}({quoted_col}) AS {func.lower()}_{column} FROM {table} {where_clause}"

        try:
            logger.info(f"AggregateDbQueryTool agg_metric: {sql[:200]}")
            rows = self._execute_sql(sql, params)
            return ToolResult(
                success=True,
                data={
                    "rows": rows,
                    "count": len(rows),
                    "table": table,
                    "scope": scope,
                    "agg_func": func,
                    "agg_column": column,
                },
                metadata={
                    "query_type": "aggregate_db_query",
                    "table": table,
                    "row_count": len(rows),
                    "agg_func": func,
                },
            )
        except Exception as e:
            logger.error(f"AggregateDbQueryTool agg_metric failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                error_details={"table": table, "func": func, "column": column},
            )

    def _get_approx_count(self, table: str, tenant_id: str) -> Optional[int]:
        """Get approximate row count from pg_class statistics for large tables.
        
        Used for metric_value table which has 10M+ rows to avoid full table scan.
        Falls back to exact COUNT if statistics not available.
        """
        from sqlalchemy import text
        try:
            with get_session_context() as session:
                # Use pg_class reltuples for fast approximate count
                result = session.execute(
                    text("SELECT reltuples::bigint FROM pg_class WHERE relname = :table_name"),
                    {"table_name": table}
                )
                row = result.fetchone()
                if row and row[0] and row[0] > 0:
                    return int(row[0])
        except Exception as e:
            logger.warning(f"pg_class count failed for {table}: {e}")
        return None

    def _execute_sql(self, sql: str, params: list) -> List[Dict[str, Any]]:
        """Execute SQL and return list of dicts."""
        from sqlalchemy import text

        with get_session_context() as session:
            # Set statement timeout to prevent long-running queries from crashing server
            session.execute(text("SET LOCAL statement_timeout = '30s'"))
            # Use SQLAlchemy text() with named params
            # Convert %s to :param_N for SQLAlchemy compatibility
            sa_sql, sa_params = self._convert_to_sqlalchemy_params(sql, params)
            # Use session.execute() (not session.exec()) for raw SQL with text()
            result = session.execute(text(sa_sql), sa_params)
            rows = result.fetchall()

        formatted_rows = []
        for row in rows:
            if hasattr(row, "_mapping"):
                formatted_rows.append(dict(row._mapping))
            elif isinstance(row, dict):
                formatted_rows.append(row)
            elif hasattr(row, "__iter__") and not isinstance(row, str):
                formatted_rows.append({"value": list(row)[0] if list(row) else None})
            else:
                formatted_rows.append({"value": row})

        return formatted_rows

    def _convert_to_sqlalchemy_params(self, sql: str, params: list) -> tuple[str, dict]:
        """Convert %s placeholders to SQLAlchemy :param_N named params."""
        sa_params = {}
        counter = [0]

        def replace_placeholder(match: re.Match) -> str:
            idx = counter[0]
            key = f"p{idx}"
            sa_params[key] = params[idx] if idx < len(params) else None
            counter[0] += 1
            return f":{key}"

        sa_sql = re.sub(r"(?<!%)%s", replace_placeholder, sql)
        return sa_sql, sa_params
