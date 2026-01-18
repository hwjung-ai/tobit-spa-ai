"""
Base classes and interfaces for OPS tools.

This module defines the abstract tool interface and context objects that allow
all tools (CI, Graph, Metric, History, CEP, etc.) to be executed uniformly
through a registry-based pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)


class ToolType(str, Enum):
    """Enumeration of available tool types in the OPS system."""

    CI = "ci"  # CI configuration search and retrieval
    GRAPH = "graph"  # Relationship graph expansion and path finding
    METRIC = "metric"  # Metrics aggregation and time series
    HISTORY = "history"  # Event logs and historical data
    CEP = "cep"  # Complex event processing
    # Future tool types
    # DOCUMENT = "document"  # Document search
    # TRACE = "trace"  # Distributed tracing
    # ALERT = "alert"  # Alert rules and patterns


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
    def tool_type(self) -> ToolType:
        """Return the type of this tool."""
        pass

    @property
    def tool_name(self) -> str:
        """Return a human-readable name for this tool."""
        return self.tool_type.value

    @abstractmethod
    async def should_execute(self, context: ToolContext, params: Dict[str, Any]) -> bool:
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
        self.logger.error(
            f"Tool {self.tool_name} failed",
            extra={
                "tool_type": self.tool_type.value,
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
                "tool_type": self.tool_type.value,
            },
        )

    async def safe_execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
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
    """

    def __init__(self):
        """Initialize an empty tool registry."""
        self._tools: Dict[ToolType, Type[BaseTool]] = {}
        self._instances: Dict[ToolType, BaseTool] = {}

    def register(self, tool_type: ToolType, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool class with the registry.

        Args:
            tool_type: The ToolType this class implements
            tool_class: The tool class to register

        Raises:
            ValueError: If a tool is already registered for this type
        """
        if tool_type in self._tools:
            logger.warning(f"Tool type {tool_type.value} already registered; skipping re-registration")
            return

        self._tools[tool_type] = tool_class
        # Instantiate immediately for singleton access
        self._instances[tool_type] = tool_class()
        logger.info(f"Registered tool: {tool_type.value}")

    def get_tool(self, tool_type: ToolType) -> BaseTool:
        """
        Get an instance of a registered tool.

        Args:
            tool_type: The type of tool to retrieve

        Returns:
            An instance of the requested tool

        Raises:
            ValueError: If the tool type is not registered
        """
        if tool_type not in self._instances:
            raise ValueError(f"Tool type {tool_type.value} is not registered")
        return self._instances[tool_type]

    def get_available_tools(self) -> Dict[ToolType, BaseTool]:
        """Get all registered tools."""
        return self._instances.copy()

    def is_registered(self, tool_type: ToolType) -> bool:
        """Check if a tool type is registered."""
        return tool_type in self._instances

    def __repr__(self) -> str:
        tools_str = ", ".join(t.value for t in self._instances.keys())
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
