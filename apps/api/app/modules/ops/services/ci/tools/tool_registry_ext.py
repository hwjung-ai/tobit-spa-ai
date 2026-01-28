"""
Tool Registry Extensions for Generic Orchestration System.

This module extends ToolRegistry to support loading tools from database assets.
"""

from __future__ import annotations

from typing import Set

from sqlmodel import Session, select

from core.logging import get_logger

from .base import BaseTool, ToolResult

from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.asset_registry.schemas import ToolAssetRead
from app.modules.asset_registry.crud import list_assets

logger = get_logger(__name__)


class ToolRegistryExt:
    """Extension to ToolRegistry for DB-based tool loading."""

    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
        self.tool_types: Set[str] = set()

    def register(self, tool: BaseTool):
        """Register a tool in the registry."""
        self.tools[tool.tool_type] = tool
        self.tool_types.add(tool.tool_type)
        logger.info(f"Registered tool: {tool.tool_name} (type={tool.tool_type})")

    def get(self, tool_type: str) -> BaseTool | None:
        """Get a tool by type."""
        return self.tools.get(tool_type)

    def list_all(self):
        """List all registered tools."""
        return list(self.tools.values())

    def get_tool_types(self) -> Set[str]:
        """Get all registered tool types."""
        return self.tool_types.copy()

    def register_from_asset(self, asset_data: ToolAssetRead) -> BaseTool:
        """Register a tool from Tool Asset data."""
        from .dynamic_tool import DynamicTool

        tool = DynamicTool(
            asset_id=str(asset_data.asset_id),
            asset_data=asset_data,
        )
        self.register(tool)
        logger.info(
            f"Registered tool from asset: {asset_data.name} (type={asset_data.tool_type})"
        )
        return tool

    def load_from_db(
        self, session: Session, asset_type_filter: str | None = None
    ) -> None:
        """Load published tool assets from database and register them."""
        from app.modules.asset_registry.crud import list_assets

        query = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")
        if asset_type_filter:
            query = query.where(TbAssetRegistry.tool_type == asset_type_filter)
        query = query.where(TbAssetRegistry.status == "published")

        assets = session.exec(query).all()

        if not assets:
            logger.warning(f"No published tool assets found in database")
            return

        logger.info(f"Loading {len(assets)} tool assets from database")

        for asset in assets:
            asset_data = ToolAssetRead(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                tool_type=asset.tool_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                tool_config=asset.tool_config,
                tool_input_schema=asset.tool_input_schema,
                tool_output_schema=asset.tool_output_schema,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
            self.register_from_asset(asset_data)

        logger.info(
            f"Successfully loaded and registered {len(assets)} tool assets from database"
        )
