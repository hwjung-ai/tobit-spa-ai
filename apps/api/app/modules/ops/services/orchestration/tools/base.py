"""
Base classes and interfaces for OPS tools.

This module defines the abstract tool interface and context objects that allow
all tools (CI, Graph, Metric, History, CEP, etc.) to be executed uniformly
through a registry-based pattern.

Tool types are now dynamically registered instead of hardcoded enums,
enabling domain-generic extension.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Type, Union

from core.logging import get_logger

logger = get_logger(__name__)


# Tool type is now a string literal type instead of enum
# This enables dynamic registration of new tool types
ToolType = Union[str, Literal["ci", "graph", "metric", "history", "cep", "mcp"]]

# Common tool types for backward compatibility
class CommonToolTypes:
    """Common tool type constants for backward compatibility."""

    CI = "ci"  # CI configuration search and retrieval
    GRAPH = "graph"  # Relationship graph expansion and path finding
    METRIC = "metric"  # Metrics aggregation and time series
    HISTORY = "history"  # Event logs and historical data
    CEP = "cep"  # Complex event processing
    MCP = "mcp"  # MCP (Model Context Protocol) server tools


@dataclass
class ToolContext:
    """
    Context for tool execution.

    Provides access to request-scoped information like tenant_id, user_id,
    request tracing IDs, and other execution context.
    """

    tenant_id: str
    """Tenant identifier for multi-tenancy isolation"""

    user_id: Optional[str] = None
    """User identifier for audit and authorization"""

    request_id: Optional[str] = None
    """Request ID for tracing across distributed systems"""

    trace_id: Optional[str] = None
    """Trace ID for linking related operations"""

    parent_trace_id: Optional[str] = None
    """Parent trace ID for call hierarchy tracking"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional context metadata for tool-specific use"""

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Safely retrieve metadata by key."""
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata by key."""
        self.metadata[key] = value


@dataclass
class ToolResult:
    """
    Result returned by tool execution.

    Provides a standardized format for tool outputs including success status,
    data payload, error information, and execution metadata.
    """

    success: bool
    """Whether the tool executed successfully"""

    data: Any = None
    """The primary result data from the tool"""

    error: Optional[str] = None
    """Error message if execution failed"""

    error_details: Optional[Dict[str, Any]] = None
    """Additional error details for debugging"""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings from execution"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Execution metadata (timing, truncation status, etc.)"""

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata by key."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Safely retrieve metadata by key."""
        return self.metadata.get(key, default)


class BaseTool(ABC):
    """
    Abstract base class for all OPS tools.

    Defines the interface that all tool implementations must follow, including
    execution, validation, and error handling. This allows tools to be
    uniformly registered and invoked through a ToolRegistry.
    """

    def __init__(self):
        """Initialize the tool."""
        self.logger = logger

    @property
    @abstractmethod
    def tool_type(self) -> str:
        """
        Return the type of this tool.

        Returns:
            Tool type string (e.g., 'ci', 'metric', 'audit')
        """
        pass

    @property
    def tool_name(self) -> str:
        """Return a human-readable name for this tool."""
        return self.tool_type

    @property
    def input_schema(self) -> Optional[Dict[str, Any]]:
        """
        Return the input schema for this tool.

        Returns:
            JSON schema describing the expected input parameters, or None if not defined
        """
        return None

    @property
    def output_schema(self) -> Optional[Dict[str, Any]]:
        """
        Return the output schema for this tool.

        Returns:
            JSON schema describing the output format, or None if not defined
        """
        return None

    @abstractmethod
    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute given the parameters.

        Used by the registry to select the right tool for a given operation.
        Allows tools to validate input parameters before execution.

        Args:
            context: Execution context
            params: Tool-specific parameters

        Returns:
            True if this tool can handle the operation, False otherwise
        """
        pass

    @abstractmethod
    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool operation.

        Subclasses must implement this to perform the actual tool operation
        and return a ToolResult with the outcome.

        Args:
            context: Execution context
            params: Tool-specific parameters

        Returns:
            ToolResult with success status and data/error information
        """
        pass

    async def format_error(
        self, context: ToolContext, error: Exception, params: Dict[str, Any]
    ) -> ToolResult:
        """
        Format an exception into a ToolResult.

        Can be overridden by subclasses to provide tool-specific error handling.

        Args:
            context: Execution context
            error: The exception that occurred
            params: Tool-specific parameters

        Returns:
            ToolResult with failure status and error information
        """
        error_msg = str(error)
        # Handle both enum and string tool_type
        tool_type_str = self.tool_type.value if hasattr(self.tool_type, 'value') else str(self.tool_type)

        self.logger.error(
            f"Tool {self.tool_name} failed",
            extra={
                "tool_type": tool_type_str,
                "error": error_msg,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
            },
        )

        return ToolResult(
            success=False,
            error=error_msg,
            error_details={
                "exception_type": type(error).__name__,
                "tool_type": tool_type_str,
            },
        )

    async def safe_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute the tool with automatic error handling.

        Wraps execute() to catch exceptions and format them appropriately.
        This is the recommended entry point for tool execution.

        Args:
            context: Execution context
            params: Tool-specific parameters

        Returns:
            ToolResult with success status and data/error information
        """
        try:
            return await self.execute(context, params)
        except Exception as e:
            return await self.format_error(context, e, params)


class ToolRegistry:
    """
    Registry for managing and selecting tools dynamically.

    Allows tools to be registered by type and selected at runtime based on
    parameters, enabling the orchestrator to dynamically choose the right
    tool without hard-coded dependencies.

    Tool types are now string-based, enabling dynamic registration of
    new tool types for different domains.
    """

    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}

    def register(self, tool_type: str, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class with the registry.

        Args:
            tool_type: The tool type string (e.g., 'ci', 'metric', 'audit')
            tool_class: The tool class to register

        Raises:
            ValueError: If a tool is already registered for this type
        """
        if tool_type in self._tools:
            logger.warning(
                f"Tool type '{tool_type}' already registered; skipping re-registration"
            )
            return

        self._tools[tool_type] = tool_class
        # Instantiate immediately for singleton access
        self._instances[tool_type] = tool_class()
        logger.info(f"Registered tool: {tool_type}")

    def register_dynamic(self, tool_instance: BaseTool) -> None:
        """
        Register a tool instance directly with the registry.

        This method supports registering tool instances (e.g., DynamicTool)
        that are already instantiated, rather than registering classes.

        Tools are registered by their NAME (not by type) to allow multiple
        tools of the same type (e.g., multiple database_query tools).

        Args:
            tool_instance: An instance of BaseTool to register

        Raises:
            ValueError: If tool_instance doesn't have tool_name
        """
        if not hasattr(tool_instance, 'tool_name'):
            raise ValueError("Tool instance must have a 'tool_name' attribute")

        tool_name = tool_instance.tool_name
        tool_type = getattr(tool_instance, 'tool_type', 'unknown')

        if tool_name in self._instances:
            logger.warning(
                f"Tool '{tool_name}' already registered; skipping re-registration"
            )
            return

        # Register the instance by NAME, not by type
        # This allows multiple tools of the same type
        self._instances[tool_name] = tool_instance
        logger.info(f"Registered dynamic tool: {tool_name} (type={tool_type})")

    def get_tool(self, tool_type: str) -> BaseTool:
        """
        Get an instance of a registered tool.

        Args:
            tool_type: The type of tool to retrieve (string)

        Returns:
            An instance of the requested tool

        Raises:
            ValueError: If the tool type is not registered
        """
        # Check both _instances and _tools for compatibility
        if tool_type in self._instances:
            return self._instances[tool_type]
        if tool_type in self._tools:
            return self._tools[tool_type]
        raise ValueError(f"Tool type '{tool_type}' is not registered")

    def get_available_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return self._instances.copy()

    def is_registered(self, tool_type: str) -> bool:
        """Check if a tool type is registered."""
        # Check both _instances and _tools for compatibility
        return tool_type in self._instances or tool_type in self._tools

    def list_tool_types(self) -> list[str]:
        """List all registered tool type strings."""
        return list(self._instances.keys())

    def get_tool_info(self, tool_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered tool.

        Args:
            tool_type: The tool type to retrieve information for

        Returns:
            Dictionary with tool name, description, input_schema, and output_schema,
            or None if tool is not registered
        """
        if tool_type not in self._instances:
            return None

        tool = self._instances[tool_type]
        return {
            "name": tool.tool_name,
            "type": tool.tool_type,
            "input_schema": tool.input_schema,
            "output_schema": tool.output_schema,
        }

    def get_all_tools_info(self) -> list[Dict[str, Any]]:
        """
        Get information about all registered tools.

        Returns:
            List of dictionaries, each containing tool information
        """
        tools_info = []
        for tool_type in self._instances.keys():
            info = self.get_tool_info(tool_type)
            if info:
                tools_info.append(info)
        return tools_info

    def validate_tool_type(self, tool_type: str) -> bool:
        """
        Validate if a tool_type is registered.

        Args:
            tool_type: The tool type to validate

        Returns:
            True if tool_type is registered, False otherwise
        """
        return tool_type in self._instances

    def __repr__(self) -> str:
        tools_str = ", ".join(self._instances.keys())
        return f"ToolRegistry([{tools_str}])"


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry, creating it if necessary."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool_type: ToolType, tool_class: Type[BaseTool]) -> None:
    """
    Register a tool with the global registry.

    This is a convenience function for registering tools at module import time.
    """
    get_tool_registry().register(tool_type, tool_class)
