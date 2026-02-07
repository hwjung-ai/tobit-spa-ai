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

            # DEBUG LOG (forced to stderr)
            import sys
            print(f"[DEBUG FORCED {self.name}] Input data keys: {list(input_data.keys())}", file=sys.stderr, flush=True)
            print(f"[DEBUG FORCED {self.name}] Query template (first 200 chars): {processed_query[:200]}", file=sys.stderr, flush=True)

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
            raw_group_by = input_data.get("group_by")
            group_by = raw_group_by if isinstance(raw_group_by, list) else []
            if not group_by:
                group_by = ["ci_type"]
                print(f"[DEBUG {self.name}] group_by was empty or missing, using default: {group_by}", file=sys.stderr, flush=True)

            if isinstance(group_by, list):
                if "{select_field}" in processed_query:
                    select_field = group_by[0] if group_by else "ci_type"
                    processed_query = processed_query.replace("{select_field}", select_field)
                if "{group_clause}" in processed_query:
                    group_clause = ", ".join(group_by) if group_by else "ci_type"
                    processed_query = processed_query.replace("{group_clause}", group_clause)
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
                        # Handle NULL: remove the entire AND clause containing this placeholder
                        # to avoid comparing UUID columns against string 'NULL'
                        null_pattern = rf"\s+AND\s+\w+(?:\.\w+)?\s*=\s*'{placeholder}'"
                        cleaned = re.sub(null_pattern, "", processed_query)
                        if cleaned != processed_query:
                            processed_query = cleaned
                        else:
                            # Fallback: replace with SQL NULL (no quotes)
                            processed_query = processed_query.replace(f"'{placeholder}'", "NULL")
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

            # DEBUG LOG - Final check (forced to stderr)
            if self.name in ["ci_aggregate", "metric"]:
                import sys
                print(f"[DEBUG FORCED {self.name}] Processed query (first 300 chars): {processed_query[:300]}", file=sys.stderr, flush=True)
                # Check for remaining placeholders (re already imported at module level)
                remaining = re.findall(r'\{[^}]+\}', processed_query)
                if remaining:
                    print(f"[DEBUG FORCED {self.name}] WARNING: Remaining placeholders: {set(remaining)}", file=sys.stderr, flush=True)

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

        # For history tool: override query_template based on source parameter
        source_param = input_data.get("source")
        if self.name == "history" and source_param and source_param != "event_log":
            query = self._build_history_query_by_source(source_param, input_data)
        else:
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

    def _build_history_query_by_source(self, source: str, input_data: dict[str, Any]) -> str:
        """Build history query based on source parameter.

        Supports work_history, maintenance_history, and work_and_maintenance (UNION).
        """
        tenant_id = input_data.get("tenant_id", "default")
        ci_id = input_data.get("ci_id")
        start_time = input_data.get("start_time")
        end_time = input_data.get("end_time")
        limit = input_data.get("limit", 30)

        # Build filter clauses
        time_filter = ""
        if start_time:
            time_filter += f" AND start_time >= '{start_time}'"
        if end_time:
            time_filter += f" AND start_time < '{end_time}'"

        ci_filter = ""
        if ci_id and ci_id != "None" and ci_id != "null":
            ci_filter = f" AND ci_id = '{ci_id}'"

        if source == "work_and_maintenance":
            return f"""
            (
                SELECT
                    '작업' AS history_type,
                    wh.work_type AS type,
                    wh.summary,
                    wh.detail,
                    wh.start_time,
                    wh.end_time,
                    wh.duration_min,
                    wh.result,
                    c.ci_name,
                    c.ci_code
                FROM work_history wh
                LEFT JOIN ci c ON c.ci_id = wh.ci_id
                WHERE wh.tenant_id = '{tenant_id}'
                    {time_filter.replace('start_time', 'wh.start_time')}
                    {ci_filter.replace('ci_id', 'wh.ci_id')}
                ORDER BY wh.start_time DESC
                LIMIT {limit}
            )
            UNION ALL
            (
                SELECT
                    '점검' AS history_type,
                    mh.maint_type AS type,
                    mh.summary,
                    mh.detail,
                    mh.start_time,
                    mh.end_time,
                    mh.duration_min,
                    mh.result,
                    c.ci_name,
                    c.ci_code
                FROM maintenance_history mh
                LEFT JOIN ci c ON c.ci_id = mh.ci_id
                WHERE mh.tenant_id = '{tenant_id}'
                    {time_filter.replace('start_time', 'mh.start_time')}
                    {ci_filter.replace('ci_id', 'mh.ci_id')}
                ORDER BY mh.start_time DESC
                LIMIT {limit}
            )
            ORDER BY start_time DESC
            LIMIT {limit * 2}
            """
        elif source == "work_history":
            return f"""
            SELECT
                wh.start_time,
                wh.work_type,
                wh.summary,
                wh.detail,
                wh.duration_min,
                wh.result,
                wh.requested_by,
                wh.approved_by,
                wh.impact_level,
                c.ci_name,
                c.ci_code
            FROM work_history wh
            LEFT JOIN ci c ON c.ci_id = wh.ci_id
            WHERE wh.tenant_id = '{tenant_id}'
                {time_filter.replace('start_time', 'wh.start_time')}
                {ci_filter.replace('ci_id', 'wh.ci_id')}
            ORDER BY wh.start_time DESC
            LIMIT {limit}
            """
        elif source == "maintenance_history":
            return f"""
            SELECT
                mh.start_time,
                mh.maint_type,
                mh.summary,
                mh.detail,
                mh.duration_min,
                mh.performer,
                mh.result,
                c.ci_name,
                c.ci_code
            FROM maintenance_history mh
            LEFT JOIN ci c ON c.ci_id = mh.ci_id
            WHERE mh.tenant_id = '{tenant_id}'
                {time_filter.replace('start_time', 'mh.start_time')}
                {ci_filter.replace('ci_id', 'mh.ci_id')}
            ORDER BY mh.start_time DESC
            LIMIT {limit}
            """
        else:
            # Fallback to event_log
            return self._process_query_template(
                self.tool_config.get("query_template", ""), input_data
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
        """Execute graph query using Neo4j for relationships + PostgreSQL for CI node info.

        - Relationships (edges): from Neo4j (COMPOSED_OF, DEPLOYED_ON, RUNS_ON, etc.)
        - CI node basic info (label, type, status): from PostgreSQL ci table
        """
        from core.db import engine
        from core.db_neo4j import get_neo4j_driver
        from sqlalchemy import text

        tenant_id = input_data.get("tenant_id", "default")
        depth = input_data.get("depth", 2)
        limit = input_data.get("limit", 50)
        ci_ids = input_data.get("ci_ids", [])

        # Relationship type → Korean label mapping
        rel_label_map = {
            "COMPOSED_OF": "구성",
            "DEPLOYED_ON": "배포",
            "RUNS_ON": "실행",
            "USES": "사용",
            "PROTECTED_BY": "보호",
            "DEPENDS_ON": "의존",
            "CONNECTED_TO": "연결",
        }

        try:
            # --- Step 1: Query Neo4j for relationships ---
            driver = get_neo4j_driver()
            neo4j_nodes = {}  # ci_id -> node properties from Neo4j
            edges = []

            with driver.session() as session:
                if ci_ids and isinstance(ci_ids, list) and len(ci_ids) > 0:
                    # Expand from specific CI nodes
                    cypher = (
                        "MATCH (a:CI)-[r]-(b:CI) "
                        "WHERE a.tenant_id = $tenant_id "
                        "  AND a.ci_id IN $ci_ids "
                        "  AND b.tenant_id = $tenant_id "
                        "RETURN a.ci_id AS src_id, a.ci_name AS src_name, "
                        "       a.ci_type AS src_type, a.ci_code AS src_code, "
                        "       a.status AS src_status, "
                        "       type(r) AS rel_type, "
                        "       b.ci_id AS tgt_id, b.ci_name AS tgt_name, "
                        "       b.ci_type AS tgt_type, b.ci_code AS tgt_code, "
                        "       b.status AS tgt_status "
                        "LIMIT $limit"
                    )
                    result = session.run(
                        cypher,
                        tenant_id=tenant_id,
                        ci_ids=ci_ids,
                        limit=limit * 5,
                    )
                else:
                    # Get all relationships for the tenant
                    cypher = (
                        "MATCH (a:CI)-[r]->(b:CI) "
                        "WHERE a.tenant_id = $tenant_id "
                        "  AND b.tenant_id = $tenant_id "
                        "RETURN a.ci_id AS src_id, a.ci_name AS src_name, "
                        "       a.ci_type AS src_type, a.ci_code AS src_code, "
                        "       a.status AS src_status, "
                        "       type(r) AS rel_type, "
                        "       b.ci_id AS tgt_id, b.ci_name AS tgt_name, "
                        "       b.ci_type AS tgt_type, b.ci_code AS tgt_code, "
                        "       b.status AS tgt_status "
                        "LIMIT $limit"
                    )
                    result = session.run(
                        cypher,
                        tenant_id=tenant_id,
                        limit=limit * 5,
                    )

                for record in result:
                    src_id = record["src_id"]
                    tgt_id = record["tgt_id"]
                    rel_type = record["rel_type"]

                    # Collect node info from Neo4j
                    if src_id and src_id not in neo4j_nodes:
                        neo4j_nodes[src_id] = {
                            "ci_name": record["src_name"] or "",
                            "ci_type": record["src_type"] or "",
                            "ci_code": record["src_code"] or "",
                            "status": record["src_status"] or "",
                        }
                    if tgt_id and tgt_id not in neo4j_nodes:
                        neo4j_nodes[tgt_id] = {
                            "ci_name": record["tgt_name"] or "",
                            "ci_type": record["tgt_type"] or "",
                            "ci_code": record["tgt_code"] or "",
                            "status": record["tgt_status"] or "",
                        }

                    # Build edge
                    if src_id and tgt_id:
                        edges.append({
                            "source": src_id,
                            "target": tgt_id,
                            "relation": rel_type,
                            "label": rel_label_map.get(rel_type, rel_type),
                        })

            driver.close()

            # --- Step 2: Enrich node info from PostgreSQL ---
            node_ids_list = list(neo4j_nodes.keys())
            pg_node_info = {}

            if node_ids_list:
                # Query PostgreSQL for authoritative CI info
                placeholders = ", ".join(f"'{nid}'" for nid in node_ids_list)
                pg_query = f"""
                SELECT ci_id::text, ci_code, ci_name, ci_type::text,
                       ci_subtype::text, status
                FROM ci
                WHERE tenant_id = '{tenant_id}'
                  AND ci_id::text IN ({placeholders})
                  AND deleted_at IS NULL
                """
                with engine.connect() as conn:
                    result = conn.execute(text(pg_query))
                    for row in result:
                        row_dict = dict(row._mapping)
                        pg_node_info[row_dict["ci_id"]] = row_dict

            # --- Step 3: Build final nodes (PostgreSQL preferred, Neo4j fallback) ---
            nodes = []
            for ci_id, neo4j_info in neo4j_nodes.items():
                pg_info = pg_node_info.get(ci_id)
                if pg_info:
                    nodes.append({
                        "id": ci_id,
                        "label": pg_info.get("ci_name", neo4j_info["ci_name"]),
                        "code": pg_info.get("ci_code", neo4j_info["ci_code"]),
                        "type": pg_info.get("ci_type", neo4j_info["ci_type"]),
                        "subtype": pg_info.get("ci_subtype", ""),
                        "status": pg_info.get("status", neo4j_info["status"]),
                    })
                else:
                    # Fallback to Neo4j properties
                    nodes.append({
                        "id": ci_id,
                        "label": neo4j_info["ci_name"],
                        "code": neo4j_info["ci_code"],
                        "type": neo4j_info["ci_type"],
                        "subtype": "",
                        "status": neo4j_info["status"],
                    })

            return ToolResult(
                success=True,
                data={
                    "nodes": nodes[:limit],
                    "edges": edges,
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                }
            )

        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Graph query failed: {str(exc)}",
                error_details={"exception": str(exc)},
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
