from __future__ import annotations

from .base import (
    BaseTool,
    ToolContext,
    ToolRegistry,
    ToolResult,
    get_tool_registry,
    register_tool,
)
from .compat import (
    ToolResultAdapter,
    extract_dict_from_result,
)
from .executor import (
    ToolExecutor,
    get_tool_executor,
)
from .dynamic_tool import DynamicTool

# Type alias for backward compatibility
ToolType = str

__all__ = [
    "BaseTool",
    "ToolContext",
    "ToolResult",
    "ToolType",
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "ToolExecutor",
    "get_tool_executor",
    "DynamicTool",
    "ToolResultAdapter",
    "extract_dict_from_result",
]
