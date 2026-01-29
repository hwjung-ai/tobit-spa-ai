"""
Direct Query Tool - Execute SQL queries directly on the database.

This tool bypasses the graph-based CI system and executes actual SQL queries
to return real data from the database.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.db import get_session_context
from sqlalchemy import text

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

        try:
            logger.info(f"Executing direct query: {sql_query[:100]}...")

            # Execute query using session context
            with get_session_context() as session:
                result = session.exec(text(sql_query))
                rows = result.fetchall()

            # Format results
            data = {
                "rows": rows,
                "count": len(rows),
                "sql": sql_query
            }

            logger.info(f"Query executed successfully, {len(rows)} rows returned")

            return ToolResult(
                success=True,
                data=data,
                metadata={
                    "references": [],
                    "row_count": len(rows),
                    "query_type": "direct_sql"
                }
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")

            return ToolResult(
                success=False,
                error=error_msg,
                error_details={
                    "exception_type": type(e).__name__,
                    "sql": sql_query[:100]
                }
            )
