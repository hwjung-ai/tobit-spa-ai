"""
Tool registry initialization module.

This module automatically registers all tools when imported, ensuring they are
available through the global ToolRegistry for use by the orchestrator.

Import this module early in your application startup to initialize all tools.
"""

from __future__ import annotations

from app.modules.ops.services.ci.tools.base import (
    ToolType,
    register_tool,
)

# Import tool classes to trigger their instantiation and registration
from app.modules.ops.services.ci.tools.ci import CITool
from app.modules.ops.services.ci.tools.graph import GraphTool
from app.modules.ops.services.ci.tools.metric import MetricTool
from app.modules.ops.services.ci.tools.history import HistoryTool
from app.modules.ops.services.ci.tools.cep import CEPTool


def initialize_tools() -> None:
    """
    Initialize and register all available tools.

    This function registers all tool classes with the global ToolRegistry,
    making them available for dynamic selection and execution by the orchestrator.

    Should be called once during application startup.
    """
    # Register each tool type with its implementation class
    register_tool(ToolType.CI, CITool)
    register_tool(ToolType.GRAPH, GraphTool)
    register_tool(ToolType.METRIC, MetricTool)
    register_tool(ToolType.HISTORY, HistoryTool)
    register_tool(ToolType.CEP, CEPTool)


# Auto-initialize tools when this module is imported
initialize_tools()
