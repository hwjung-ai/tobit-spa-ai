"""
Direct Query Tool - Execute SQL queries directly on the database.

This tool bypasses the graph-based CI system and executes actual SQL queries
to return real data from the database.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.config import get_settings

from app.modules.asset_registry.loader import load_source_asset
from app.modules.ops.services.connections import ConnectionFactory

from .base import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)


class DirectQueryTool(BaseTool):
    """
    Tool that executes SQL queries directly on the database.

    This is used as a fallback when Query Assets need to be executed
    to get actual data instead of graph-based results.
    """

    @property
    def tool_type(self) -> str:
        """Return the tool type."""
        return "direct_query"

    @property
    def tool_name(self) -> str:
        """Return the tool name."""
        return "DirectQueryTool"

    async def should_execute(self, context: ToolContext, params: Dict[str, Any]) -> bool:
        """
        Check if this tool should execute.

        Args:
            context: Execution context
            params: Parameters including 'sql' key

        Returns:
            True if sql parameter exists
        """
        return "sql" in params and params["sql"]

    async def execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a SQL query and return results.

        Args:
            context: Execution context
            params: Parameters including 'sql' (SQL query string)

        Returns:
            ToolResult with query results
        """
        sql_query = params.get("sql", "")

        if not sql_query:
            return ToolResult(
                success=False,
                error="No SQL query provided",
                error_details={"param": "sql"}
            )

        source_ref = params.get("source_ref")
        if not source_ref:
            source_ref = get_settings().ops_default_source_asset
        if not source_ref:
            return ToolResult(
                success=False,
                error="source_ref is required or ops_default_source_asset must be configured",
                error_details={"param": "source_ref"},
            )

        source_asset = load_source_asset(source_ref)
        if not source_asset:
            return ToolResult(
                success=False,
                error=f"Source asset not found: {source_ref}",
                error_details={"source_ref": source_ref},
            )

        connection = None
        try:
            logger.info(
                f"Executing direct query via source '{source_ref}': {sql_query[:100]}..."
            )
            connection = ConnectionFactory.create(source_asset)
            query_params = params.get("query_params")
            rows = connection.execute(sql_query, query_params)
            count = len(rows) if isinstance(rows, list) else 0
            data = {
                "rows": rows,
                "count": count,
                "sql": sql_query,
                "source_ref": source_ref,
            }
            return ToolResult(
                success=True,
                data=data,
                metadata={
                    "references": [],
                    "row_count": count,
                    "query_type": "direct_sql",
                    "source_ref": source_ref,
                },
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")
            return ToolResult(
                success=False,
                error=error_msg,
                error_details={
                    "exception_type": type(e).__name__,
                    "sql": sql_query[:100],
                    "source_ref": source_ref,
                },
            )
        finally:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass
