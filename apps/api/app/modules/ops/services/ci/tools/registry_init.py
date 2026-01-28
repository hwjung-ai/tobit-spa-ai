"""
Tool registry initialization module.

This module initializes the tool registry from Asset Registry (database).
All tools are now defined as Tool Assets and dynamically loaded at runtime.

Import this module early in your application startup to initialize tools.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def initialize_tools() -> None:
    """
    Initialize and register all tools from Asset Registry.

    This function loads all published Tool Assets from the database and
    registers them as DynamicTools with the global ToolRegistry.

    Should be called once during application startup.
    """
    try:
        from app.modules.asset_registry.loader import load_all_published_tools
        from app.modules.ops.services.ci.tools.base import get_tool_registry
        from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

        registry = get_tool_registry()

        try:
            tool_assets = load_all_published_tools()
        except Exception as e:
            logger.warning(f"Could not load tools from Asset Registry: {e}")
            logger.info("Continuing with empty tool registry (tools can be added via Admin UI)")
            return

        for tool_asset in tool_assets:
            try:
                tool = DynamicTool(tool_asset)
                registry.register_dynamic(tool)
                logger.info(f"Loaded tool from Asset Registry: {tool_asset['name']}")
            except Exception as e:
                logger.warning(
                    f"Failed to load tool '{tool_asset.get('name', 'unknown')}' from Asset Registry: {e}"
                )

        logger.info(f"Successfully loaded {len(tool_assets)} tools from Asset Registry")

    except Exception as e:
        logger.error(f"Failed to initialize tools from Asset Registry: {e}")


# Auto-initialize tools when this module is imported
initialize_tools()
