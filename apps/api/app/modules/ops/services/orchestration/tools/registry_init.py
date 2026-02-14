"""
Tool registry initialization module.

This module initializes the tool registry from Asset Registry (database).
All tools are now defined as Tool Assets and dynamically loaded at runtime.
Call ``initialize_tools()`` explicitly during application startup.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def initialize_tools() -> None:
    """
    Initialize and register all tools from Asset Registry.

    This function loads all published Tool Assets from the database and
    registers them as DynamicTools with the global ToolRegistry.

    Also registers DirectQueryTool for direct SQL execution.

    Should be called once during application startup.
    """
    try:
        from app.modules.asset_registry.loader import load_all_published_tools
        from app.modules.ops.services.orchestration.tools.base import get_tool_registry
        from app.modules.ops.services.orchestration.tools.direct_query_tool import DirectQueryTool
        from app.modules.ops.services.orchestration.tools.dynamic_tool import DynamicTool

        registry = get_tool_registry()

        # Register DirectQueryTool first
        try:
            direct_query_tool = DirectQueryTool()
            registry.register_dynamic(direct_query_tool)
            logger.info("Registered DirectQueryTool for direct SQL execution")
        except Exception as e:
            logger.warning(f"Failed to register DirectQueryTool: {e}")

        try:
            tool_assets = load_all_published_tools()
        except Exception as e:
            logger.warning(f"Could not load tools from Asset Registry: {e}")
            logger.info("Continuing with DirectQueryTool only")
            return

        loaded_count = 0
        for tool_asset in tool_assets:
            try:
                tool = DynamicTool(tool_asset)
                registry.register_dynamic(tool)
                logger.info(f"Loaded tool from Asset Registry: {tool_asset['name']}")
                loaded_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to load tool '{tool_asset.get('name', 'unknown')}' from Asset Registry: {e}"
                )

        logger.info(f"Successfully loaded {loaded_count} tools from Asset Registry")

    except Exception as e:
        logger.error(f"Failed to initialize tools from Asset Registry: {e}")
