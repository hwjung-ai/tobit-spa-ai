"""
Dynamic Tool implementation for Generic Orchestration System.

This module implements dynamic tool execution based on Tool Asset configuration.
"""

from __future__ import annotations

from typing import Any

from core.logging import get_logger

from .base import BaseTool, ToolContext, ToolResult
from ...asset_registry.loader import load_source_asset
from ...asset_registry.schemas import ToolAssetRead

logger = get_logger(__name__)


class DynamicTool(BaseTool):
    """Tool that executes based on Tool Asset configuration."""

    def __init__(
        self,
        asset_id: str,
        asset_data: ToolAssetRead,
    ):
        self.asset_id = asset_id
        self.asset_data = asset_data
        self.tool_type = asset_data.tool_type
        self.tool_config = asset_data.tool_config
        self.input_schema = asset_data.tool_input_schema
        self.output_schema = asset_data.tool_output_schema

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

        query = query_template

        connection_params = source_asset.connection_params or {}
        if source_asset.source_type == "postgres":
            from core.db import get_engine

            engine = get_engine()
            async with engine.begin() as conn:
                result = await conn.execute(query, connection_params)
                rows = result.fetchall()
                columns = result.keys()
                output = [dict(zip(columns, row)) for row in rows]
                return ToolResult(success=True, data={"rows": output})
        else:
            return ToolResult(
                success=False,
                error=f"Unsupported database type: {source_asset.source_type}",
                error_details={"source_type": source_asset.source_type},
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
            except httpx.HTTPStatusError as e:
                return ToolResult(
                    success=False,
                    error=f"HTTP error: {e.response.status_code}",
                    error_details={
                        "status_code": e.response.status_code,
                        "response": e.response.text,
                    },
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"HTTP request failed: {str(e)}",
                    error_details={"exception": str(e)},
                )

    async def _execute_graph_query(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute Neo4j graph query tool."""
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

        if source_asset.source_type != "neo4j":
            return ToolResult(
                success=False,
                error=f"Graph queries only support neo4j source type",
                error_details={"source_type": source_asset.source_type},
            )

        query = query_template

        from neo4j import GraphDatabase

        connection_params = source_asset.connection_params or {}
        driver = GraphDatabase.driver(**connection_params)
        session = driver.session()

        try:
            result = session.run(query)
            data = [dict(record.data()) for record in result]
            return ToolResult(success=True, data={"nodes": data})
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Graph query failed: {str(e)}",
                error_details={"exception": str(e)},
            )
        finally:
            session.close()
            driver.close()

    async def _execute_custom(
        self, context: ToolContext, input_data: dict[str, Any]
    ) -> ToolResult:
        """Execute custom handler tool."""
        handler_name = self.tool_config.get("handler_name")

        if not handler_name:
            return ToolResult(
                success=False,
                error="handler_name not provided in tool_config",
                error_details=self.tool_config,
            )

        try:
            from app.modules.ops.services.executors.custom_executor import (
                execute_custom_handler,
            )

            data = await execute_custom_handler(handler_name, input_data)
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Custom handler failed: {str(e)}",
                error_details={"handler_name": handler_name, "exception": str(e)},
            )
