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

    def _process_query_template(self, query_template: str, input_data: dict[str, Any]) -> tuple[str, list]:
        """Process query template to replace placeholders with actual values using parameterized queries.

        Returns tuple of (query, params) for safe parameterized execution.

        Args:
            query_template: SQL query template with {placeholders}
            input_data: Input parameters containing keywords, filters, etc.

        Returns:
            Tuple of (processed_query, params_list) for parameterized execution
        """
        if not query_template:
            return "", []

        processed_query = query_template
        params = []

        # Check if this is CI lookup mode (has where_clause placeholder)
        if "{where_clause}" in query_template:
            # CI lookup mode - build safe WHERE clause with params
            where_conditions = []
            order_by = "ci.ci_id"
            direction = "ASC"
            limit_value = 10

            # Process keywords - safe parameterization
            keywords = input_data.get("keywords", [])
            if keywords and len(keywords) > 0:
                keyword_conditions = []
                for keyword in keywords:
                    if keyword:
                        # Use parameterized ILIKE instead of string interpolation
                        keyword_conditions.append("(ci.ci_name ILIKE %s OR ci.ci_code ILIKE %s)")
                        params.extend([f"%{keyword}%", f"%{keyword}%"])
                if keyword_conditions:
                    where_conditions.append(" OR ".join(keyword_conditions))

            # Process filters - safe parameterization
            filters = input_data.get("filters", [])
            if filters:
                for filter_item in filters:
                    if isinstance(filter_item, dict):
                        field = filter_item.get("field")
                        operator = filter_item.get("operator", "=")
                        value = filter_item.get("value")

                        if field and value is not None:
                            # Validate field name (whitelist approach)
                            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", field):
                                logger.warning(f"Invalid field name: {field}")
                                continue

                            if operator.upper() == "ILIKE":
                                where_conditions.append(f"{field} ILIKE %s")
                                params.append(f"%{value}%")
                            elif operator.upper() == "IN" and isinstance(value, list):
                                placeholders = ", ".join(["%s"] * len(value))
                                where_conditions.append(f"{field} IN ({placeholders})")
                                params.extend(value)
                            else:
                                where_conditions.append(f"{field} {operator} %s")
                                params.append(value)

            # Add tenant_id filter - parameterized
            tenant_id = input_data.get("tenant_id", "default")
            where_conditions.append("ci.tenant_id = %s")
            params.append(tenant_id)
            where_conditions.append("ci.deleted_at IS NULL")

            # Build WHERE clause
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Process sorting (column names only, no parameterization needed)
            sort = input_data.get("sort")
            if sort:
                if isinstance(sort, tuple) and len(sort) == 2:
                    order_by = sort[0]
                    direction = sort[1].upper()
                else:
                    order_by = str(sort)

            # Validate order_by and direction
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", order_by):
                order_by = "ci.ci_id"
            if direction not in ("ASC", "DESC"):
                direction = "ASC"

            # Process limit - parameterized
            limit = input_data.get("limit", limit_value)
            try:
                limit = max(1, min(int(limit), 1000))  # Clamp between 1 and 1000
            except (ValueError, TypeError):
                limit = limit_value

            # Replace placeholders in template
            processed_query = processed_query.replace("{where_clause}", where_clause)
            processed_query = processed_query.replace("{order_by}", order_by)
            processed_query = processed_query.replace("{direction}", direction)
            processed_query = processed_query.replace("{limit}", "%s")
            params.append(limit)

        else:
            # Generic mode - safe placeholder replacement

            # Handle metric tool specific mappings
            if "{function}" in processed_query:
                agg = input_data.get("agg", "AVG")
                if isinstance(agg, str):
                    agg = agg.upper()
                # Validate agg function (whitelist approach)
                if agg not in ("AVG", "MIN", "MAX", "SUM", "COUNT", "STDDEV"):
                    agg = "AVG"
                processed_query = processed_query.replace("{function}", agg)

            # Handle ci_ids array placeholder - parameterized
            if "{ci_ids}" in processed_query:
                ci_ids = input_data.get("ci_ids", [])
                if ci_ids and isinstance(ci_ids, list):
                    placeholders = ", ".join(["%s"] * len(ci_ids))
                    processed_query = processed_query.replace("ARRAY{ci_ids}", f"ARRAY[{placeholders}]::uuid[]")
                    params.extend(ci_ids)
                else:
                    # Empty array - remove the ci_id filter
                    processed_query = re.sub(
                        r"\s+AND\s+mv\.ci_id\s*=\s*ANY\s*\(\s*ARRAY\[.*?\]::uuid\[\]\s*\)",
                        "",
                        processed_query
                    )

            # Handle group_by (column names only)
            raw_group_by = input_data.get("group_by")
            group_by = raw_group_by if isinstance(raw_group_by, list) else []
            if not group_by:
                group_by = ["ci_type"]

            if isinstance(group_by, list):
                # Validate all group_by fields
                validated_group_by = []
                for field in group_by:
                    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", field):
                        validated_group_by.append(field)
                group_by = validated_group_by if validated_group_by else ["ci_type"]

                if "{select_field}" in processed_query:
                    processed_query = processed_query.replace("{select_field}", group_by[0])
                if "{group_clause}" in processed_query:
                    processed_query = processed_query.replace("{group_clause}", ", ".join(group_by))
                if "{group_field}" in processed_query:
                    processed_query = processed_query.replace("{group_field}", group_by[0])

            # Handle time_filter
            if "{time_filter}" in processed_query:
                time_range = input_data.get("time_range", "")
                if time_range:
                    processed_query = processed_query.replace("{time_filter}", f"AND time > NOW() - INTERVAL %s")
                    params.append(time_range)
                else:
                    processed_query = processed_query.replace("{time_filter}", "")

            # Replace all other {key} placeholders - parameterized
            skip_keys = {"group_by", "ci_ids", "agg"}

            for key, value in input_data.items():
                if key in skip_keys:
                    continue

                placeholder = f"{{{key}}}"
                if placeholder in processed_query:
                    if value is None:
                        # Handle NULL - remove AND clause
                        null_pattern = rf"\s+AND\s+\w+(?:\.\w+)?\s*=\s*'{placeholder}'"
                        processed_query = re.sub(null_pattern, "", processed_query)
                    elif isinstance(value, list):
                        # Convert list to parameterized IN clause
                        placeholders = ", ".join(["%s"] * len(value))
                        processed_query = processed_query.replace(placeholder, f"({placeholders})")
                        params.extend(value)
                    elif isinstance(value, dict):
                        # Skip dict values
                        continue
                    else:
                        # Replace with parameterized placeholder
                        processed_query = processed_query.replace(placeholder, "%s")
                        params.append(value)

        return processed_query, params

    async def _execute_database_query(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute database query tool with parameterized queries."""
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
            query, params = self._build_history_query_by_source(source_param, input_data)
        else:
            # Process query template to replace placeholders - now returns (query, params) tuple
            query, params = self._process_query_template(query_template, input_data)

        # source_asset is a dict, not an object
        source_type = source_asset.get("source_type")

        if source_type == "postgres":
            from core.db import engine
            from sqlalchemy import text

            try:
                # Use parameterized query with bound parameters
                with engine.connect() as conn:
                    result = conn.execute(text(query), params)
                    rows = result.fetchall()
                    columns = result.keys()
                    output = [dict(zip(columns, row)) for row in rows]
                    return ToolResult(success=True, data={"rows": output})
            except Exception as exc:
                logger.error(f"Database query failed: {str(exc)}", extra={"query": query[:200]})
                return ToolResult(
                    success=False,
                    error=f"Database query failed: {str(exc)}",
                    error_details={"exception": str(exc)},
                )
        else:
            return ToolResult(
                success=False,
                error=f"Unsupported database type: {source_type}",
                error_details={"source_type": source_type},
            )

    def _build_history_query_by_source(self, source: str, input_data: dict[str, Any]) -> tuple[str, list]:
        """Build history query based on source parameter with parameterized queries.

        Supports work_history, maintenance_history, and work_and_maintenance (UNION).

        Returns:
            Tuple of (query, params) for parameterized execution
        """
        params = []
        tenant_id = input_data.get("tenant_id", "default")
        ci_id = input_data.get("ci_id")
        start_time = input_data.get("start_time")
        end_time = input_data.get("end_time")
        limit = input_data.get("limit", 30)

        try:
            limit = max(1, min(int(limit), 1000))
        except (ValueError, TypeError):
            limit = 30

        if source == "work_and_maintenance":
            query = """
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
                WHERE wh.tenant_id = %s
                    {wh_time_filter}
                    {wh_ci_filter}
                ORDER BY wh.start_time DESC
                LIMIT %s
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
                WHERE mh.tenant_id = %s
                    {mh_time_filter}
                    {mh_ci_filter}
                ORDER BY mh.start_time DESC
                LIMIT %s
            )
            ORDER BY start_time DESC
            LIMIT %s
            """

            # Build parameterized filters
            wh_time_filter = ""
            mh_time_filter = ""
            wh_ci_filter = ""
            mh_ci_filter = ""

            if start_time:
                wh_time_filter = "AND wh.start_time >= %s"
                mh_time_filter = "AND mh.start_time >= %s"
            if end_time:
                if start_time:
                    wh_time_filter += " AND wh.start_time < %s"
                    mh_time_filter += " AND mh.start_time < %s"
                else:
                    wh_time_filter = "AND wh.start_time < %s"
                    mh_time_filter = "AND mh.start_time < %s"

            if ci_id and ci_id not in ("None", "null"):
                wh_ci_filter = "AND wh.ci_id = %s::uuid"
                mh_ci_filter = "AND mh.ci_id = %s::uuid"

            query = query.format(
                wh_time_filter=wh_time_filter,
                wh_ci_filter=wh_ci_filter,
                mh_time_filter=mh_time_filter,
                mh_ci_filter=mh_ci_filter
            )

            # Build params list
            params = [tenant_id]
            if start_time:
                params.append(start_time)
            if end_time:
                params.append(end_time)
            if ci_id and ci_id not in ("None", "null"):
                params.append(ci_id)
            params.append(limit)

            # Second part (maintenance_history)
            params.append(tenant_id)
            if start_time:
                params.append(start_time)
            if end_time:
                params.append(end_time)
            if ci_id and ci_id not in ("None", "null"):
                params.append(ci_id)
            params.append(limit)

            # Final LIMIT
            params.append(limit * 2)

        elif source == "work_history":
            query = """
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
            WHERE wh.tenant_id = %s
                {time_filter}
                {ci_filter}
            ORDER BY wh.start_time DESC
            LIMIT %s
            """

            time_filter = ""
            ci_filter = ""

            if start_time:
                time_filter += "AND wh.start_time >= %s"
            if end_time:
                if time_filter:
                    time_filter += " AND wh.start_time < %s"
                else:
                    time_filter = "AND wh.start_time < %s"

            if ci_id and ci_id not in ("None", "null"):
                ci_filter = "AND wh.ci_id = %s::uuid"

            query = query.format(time_filter=time_filter, ci_filter=ci_filter)

            params = [tenant_id]
            if start_time:
                params.append(start_time)
            if end_time:
                params.append(end_time)
            if ci_id and ci_id not in ("None", "null"):
                params.append(ci_id)
            params.append(limit)

        elif source == "maintenance_history":
            query = """
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
            WHERE mh.tenant_id = %s
                {time_filter}
                {ci_filter}
            ORDER BY mh.start_time DESC
            LIMIT %s
            """

            time_filter = ""
            ci_filter = ""

            if start_time:
                time_filter += "AND mh.start_time >= %s"
            if end_time:
                if time_filter:
                    time_filter += " AND mh.start_time < %s"
                else:
                    time_filter = "AND mh.start_time < %s"

            if ci_id and ci_id not in ("None", "null"):
                ci_filter = "AND mh.ci_id = %s::uuid"

            query = query.format(time_filter=time_filter, ci_filter=ci_filter)

            params = [tenant_id]
            if start_time:
                params.append(start_time)
            if end_time:
                params.append(end_time)
            if ci_id and ci_id not in ("None", "null"):
                params.append(ci_id)
            params.append(limit)
        else:
            # Fallback to event_log
            return self._process_query_template(
                self.tool_config.get("query_template", ""), input_data
            )

        return query, params

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
                # Query PostgreSQL for authoritative CI info - use parameterized query
                placeholders = ", ".join(["%s"] * len(node_ids_list))
                pg_query = f"""
                SELECT ci_id::text, ci_code, ci_name, ci_type::text,
                       ci_subtype::text, status
                FROM ci
                WHERE tenant_id = %s
                  AND ci_id::text IN ({placeholders})
                  AND deleted_at IS NULL
                """
                with engine.connect() as conn:
                    params = [tenant_id] + node_ids_list
                    result = conn.execute(text(pg_query), params)
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
