"""
Dynamic Tool implementation for Generic Orchestration System.

This module implements dynamic tool execution based on Tool Asset configuration.
"""

from __future__ import annotations

import re
from typing import Any

from core.logging import get_logger

from .base import BaseTool, ToolContext, ToolResult
from app.modules.asset_registry.loader import load_source_asset

logger = get_logger(__name__)


class DynamicTool(BaseTool):
    """Tool that executes based on Tool Asset configuration."""

    def __init__(self, tool_asset: dict[str, Any]):
        """
        Initialize DynamicTool from a tool asset dictionary.

        Args:
            tool_asset: Dictionary containing tool configuration with keys:
                - name: Tool name
                - asset_id: Asset ID (optional)
                - tool_type: Type of tool (database_query, http_api, graph_query, custom)
                - tool_config: Tool configuration dict
                - tool_input_schema: Input schema dict
                - tool_output_schema: Output schema dict (optional)
                - description: Tool description (optional)
        """
        super().__init__()
        self.asset_id = tool_asset.get("asset_id")
        self.asset_data = tool_asset
        self.name = tool_asset.get("name", "unknown")
        self.description = tool_asset.get("description", "")
        self._tool_type = tool_asset.get("tool_type", "custom")
        self.tool_config = tool_asset.get("tool_config", {})
        self._input_schema = tool_asset.get("tool_input_schema", {})
        self._output_schema = tool_asset.get("tool_output_schema", {})

    @property
    def tool_type(self) -> str:
        """Return the type of this tool."""
        return self._tool_type

    @property
    def tool_name(self) -> str:
        """Return the name of this tool."""
        return self.name

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the input schema for this tool."""
        return self._input_schema

    @property
    def output_schema(self) -> dict[str, Any]:
        """Return the output schema for this tool."""
        return self._output_schema

    async def should_execute(
        self, context: ToolContext, params: dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute given the parameters.

        For DynamicTools, we accept all parameters since configuration
        determines behavior.

        Args:
            context: Execution context
            params: Tool-specific parameters

        Returns:
            True (always execute for DynamicTools)
        """
        return True

    async def execute(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute tool based on tool_config."""
        tool_type = self.tool_type

        if tool_type == "database_query":
            return await self._execute_database_query(context, input_data)
        elif tool_type == "http_api":
            return await self._execute_http_api(context, input_data)
        elif tool_type == "graph_query":
            return await self._execute_graph_query(context, input_data)
        elif tool_type == "custom":
            return await self._execute_custom(context, input_data)
        else:
            return ToolResult(
                success=False,
                error=f"Unsupported tool type: {tool_type}",
                error_details={"tool_type": tool_type},
            )

    def _process_query_template(self, query_template: str, input_data: dict[str, Any]) -> str:
        """Process query template to replace placeholders with actual values.

        Supports two modes:
        1. CI lookup mode (legacy): {where_clause}, {order_by}, {direction}, %s
        2. Generic mode: Direct placeholder replacement from input_data

        Args:
            query_template: SQL query template with placeholders
            input_data: Input parameters containing keywords, filters, etc.

        Returns:
            Processed SQL query with actual values
        """
        if not query_template:
            return ""

        processed_query = query_template

        # Check if this is CI lookup mode (has where_clause placeholder)
        if "{where_clause}" in query_template:
            # Legacy CI lookup mode - build complex WHERE clause
            where_conditions = []
            order_by = "ci.ci_id"  # Default order
            direction = "ASC"     # Default direction
            limit_value = 10      # Default limit

            # Process keywords
            keywords = input_data.get("keywords", [])
            if keywords and len(keywords) > 0:
                keyword_conditions = []
                for keyword in keywords:
                    if keyword:
                        keyword_conditions.append(f"(ci.ci_name ILIKE '%{keyword}%' OR ci.ci_code ILIKE '%{keyword}%')")
                if keyword_conditions:
                    where_conditions.append(" OR ".join(keyword_conditions))

            # Process filters
            filters = input_data.get("filters", [])
            if filters:
                for filter_item in filters:
                    if isinstance(filter_item, dict):
                        field = filter_item.get("field")
                        operator = filter_item.get("operator", "=")
                        value = filter_item.get("value")

                        if field and value:
                            if operator.upper() == "ILIKE":
                                where_conditions.append(f"{field} ILIKE '%{value}%'")
                            elif operator.upper() == "IN":
                                values_str = ", ".join([f"'{v}'" for v in value])
                                where_conditions.append(f"{field} IN ({values_str})")
                            else:
                                where_conditions.append(f"{field} {operator} '{value}'")

            # Add tenant_id filter
            tenant_id = input_data.get("tenant_id", "default")
            where_conditions.append(f"ci.tenant_id = '{tenant_id}'")
            where_conditions.append("ci.deleted_at IS NULL")

            # Build WHERE clause
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Process sorting
            sort = input_data.get("sort")
            if sort:
                if isinstance(sort, tuple) and len(sort) == 2:
                    order_by = sort[0]
                    direction = sort[1].upper()
                else:
                    order_by = str(sort)

            # Process limit
            limit = input_data.get("limit", limit_value)

            # Replace placeholders in template
            processed_query = processed_query.replace("{where_clause}", where_clause)
            processed_query = processed_query.replace("{order_by}", order_by)
            processed_query = processed_query.replace("{direction}", direction)
            processed_query = processed_query.replace("%s", str(limit))
            processed_query = processed_query.replace("{limit}", str(limit))

        else:
            # Generic mode - direct placeholder replacement

            # Handle metric tool specific mappings
            if "{function}" in processed_query:
                # Map 'agg' to 'function' for metric aggregation
                agg = input_data.get("agg", "AVG")
                if isinstance(agg, str):
                    agg = agg.upper()
                processed_query = processed_query.replace("{function}", agg)

            # Handle ci_ids array placeholder
            if "{ci_ids}" in processed_query:
                ci_ids = input_data.get("ci_ids", [])
                if ci_ids and isinstance(ci_ids, list):
                    # Format as PostgreSQL array values: ['id1', 'id2']
                    # Template should have ARRAY{ci_ids}, so we just provide the bracket part
                    escaped_ids = [str(cid).replace("'", "''") for cid in ci_ids]
                    array_str = "['" + "', '".join(escaped_ids) + "']::uuid[]"
                    processed_query = processed_query.replace("{ci_ids}", array_str)
                else:
                    # Empty array - remove the ci_id filter entirely to query all CIs
                    # Find and remove the "AND mv.ci_id = ANY(ARRAY{ci_ids})" clause
                    processed_query = re.sub(
                        r"\s+AND\s+mv\.ci_id\s*=\s*ANY\s*\(\s*ARRAY\{ci_ids\}\s*\)",
                        "",
                        processed_query
                    )

            # First handle special aggregate-specific placeholders
            group_by = input_data.get("group_by", [])
            if group_by and isinstance(group_by, list):
                # Handle {select_field} for single field GROUP BY
                if "{select_field}" in processed_query:
                    select_field = group_by[0] if group_by else "ci_type"
                    processed_query = processed_query.replace("{select_field}", select_field)
                # Handle {group_clause} for multi-field GROUP BY
                if "{group_clause}" in processed_query:
                    group_clause = ", ".join(group_by) if group_by else "ci_type"
                    processed_query = processed_query.replace("{group_clause}", group_clause)
                # Handle {group_field} for single field
                if "{group_field}" in processed_query:
                    group_field = group_by[0] if group_by else "event_type"
                    processed_query = processed_query.replace("{group_field}", group_field)

            # Handle time_filter for event queries
            if "{time_filter}" in processed_query:
                time_range = input_data.get("time_range", "")
                if time_range:
                    # Simple time range placeholder - could be enhanced
                    processed_query = processed_query.replace("{time_filter}", f"AND time > NOW() - INTERVAL '{time_range}'")
                else:
                    processed_query = processed_query.replace("{time_filter}", "")

            # Replace all other {key} placeholders with values from input_data
            # Skip keys that were already processed above
            skip_keys = {"group_by", "ci_ids", "agg"}

            for key, value in input_data.items():
                if key in skip_keys:
                    continue

                placeholder = f"{{{key}}}"
                if placeholder in processed_query:
                    if value is None:
                        processed_query = processed_query.replace(placeholder, "NULL")
                    elif isinstance(value, list):
                        # Convert list to SQL array format
                        escaped_values = [str(v).replace("'", "''") for v in value]
                        array_values = "', '".join(escaped_values)
                        array_str = f"ARRAY['{array_values}']"
                        processed_query = processed_query.replace(placeholder, array_str)
                    elif isinstance(value, dict):
                        processed_query = processed_query.replace(placeholder, str(value))
                    else:
                        # Replace placeholder with value directly
                        # Query templates should include quotes if needed (e.g., '{metric_name}' not {metric_name})
                        escaped_value = str(value).replace("'", "''")
                        processed_query = processed_query.replace(placeholder, escaped_value)

        return processed_query

    async def _execute_database_query(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute database query tool."""
        source_ref = self.tool_config.get("source_ref")
        query_template = self.tool_config.get("query_template")

        if not source_ref:
            return ToolResult(
                success=False,
                error="source_ref not provided in tool_config",
                error_details=self.tool_config,
            )

        source_asset = load_source_asset(name=source_ref)
        if not source_asset:
            return ToolResult(
                success=False,
                error=f"Source asset not found: {source_ref}",
                error_details={"source_ref": source_ref},
            )

        # Process query template to replace placeholders
        query = self._process_query_template(query_template, input_data)

        # source_asset is a dict, not an object
        connection_params = source_asset.get("connection", {})
        source_type = source_asset.get("source_type")

        if source_type == "postgres":
            from core.db import engine
            from sqlalchemy import text

            # Use synchronous execution (engine is not async)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                columns = result.keys()
                output = [dict(zip(columns, row)) for row in rows]
                return ToolResult(success=True, data={"rows": output})
        else:
            return ToolResult(
                success=False,
                error=f"Unsupported database type: {source_type}",
                error_details={"source_type": source_type},
            )

    async def _execute_http_api(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute HTTP API tool."""
        url = self.tool_config.get("url")
        method = self.tool_config.get("method", "GET")
        headers = self.tool_config.get("headers", {})
        body_template = self.tool_config.get("body_template")

        if not url:
            return ToolResult(
                success=False,
                error="url not provided in tool_config",
                error_details=self.tool_config,
            )

        import httpx

        body = None
        if body_template and method in ["POST", "PUT", "PATCH"]:
            body = {k: input_data.get(v, "") for k, v in body_template.items()}

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = await client.post(
                    url, headers=headers, json=body, timeout=30
                )
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=body, timeout=30)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, timeout=30)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unsupported HTTP method: {method}",
                    error_details=self.tool_config,
                )

            try:
                response.raise_for_status()
                output = response.json() if response.text else {}
                return ToolResult(success=True, data=output)
            except httpx.HTTPStatusError as exc:
                return ToolResult(
                    success=False,
                    error=f"HTTP {exc.response.status_code}: {exc.response.text}",
                    error_details={"status_code": exc.response.status_code},
                )
            except Exception as exc:
                return ToolResult(
                    success=False,
                    error=f"HTTP request failed: {str(exc)}",
                    error_details={"exception": str(exc)},
                )

    async def _execute_graph_query(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute graph query tool."""
        # Placeholder implementation
        return ToolResult(
            success=False,
            error="Graph query not yet implemented",
            error_details={"tool_type": "graph_query"},
        )

    async def _execute_custom(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute custom tool."""
        # Placeholder implementation
        return ToolResult(
            success=False,
            error="Custom tool not yet implemented",
            error_details={"tool_type": "custom"},
        )