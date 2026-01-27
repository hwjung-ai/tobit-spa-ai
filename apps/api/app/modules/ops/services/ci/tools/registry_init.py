"""
Tool registry initialization module.

This module automatically registers all tools when imported, ensuring they are
available through the global ToolRegistry for use by the orchestrator.

Import this module early in your application startup to initialize all tools.
"""

from __future__ import annotations

from app.modules.ops.services.ci.tools.base import (
    CommonToolTypes,
    register_tool,
)
from app.modules.ops.services.ci.tools.cep import CEPTool

# Import tool classes to trigger their instantiation and registration
from app.modules.ops.services.ci.tools.ci import CITool
from app.modules.ops.services.ci.tools.graph import GraphTool
from app.modules.ops.services.ci.tools.history import HistoryTool
from app.modules.ops.services.ci.tools.metric import MetricTool


def initialize_tools() -> None:
    """
    Initialize and register all available tools.

    This function registers all tool classes with the global ToolRegistry,
    making them available for dynamic selection and execution by the orchestrator.

    Should be called once during application startup.
    """
    # Register each tool type with its implementation class
    register_tool(CommonToolTypes.CI, CITool)
    register_tool(CommonToolTypes.GRAPH, GraphTool)
    register_tool(CommonToolTypes.METRIC, MetricTool)
    register_tool(CommonToolTypes.HISTORY, HistoryTool)
    register_tool(CommonToolTypes.CEP, CEPTool)


# Auto-initialize tools when this module is imported
initialize_tools()
