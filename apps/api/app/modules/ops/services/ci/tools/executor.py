"""
Tool Executor for OPS Orchestration.

This module provides a unified executor for all OPS tools, enabling the orchestrator
to dynamically select and execute tools through the ToolRegistry without hard-coded
tool imports or dependencies.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from core.logging import get_logger

from app.modules.ops.services.ci.tools.base import (
    ToolContext,
    ToolRegistry,
    ToolResult,
    ToolType,
    get_tool_registry,
)
from app.modules.ops.services.ci.tools.cache import ToolResultCache

logger = get_logger(__name__)


class ToolExecutor:
    """
    Unified executor for all OPS tools.

    Provides a single interface for executing any registered tool without needing
    to know about specific tool implementations. This enables the orchestrator to
    work with tools dynamically.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        cache: Optional[ToolResultCache] = None,
    ):
        """
        Initialize the executor.

        Args:
            registry: ToolRegistry to use. If None, uses global registry.
        """
        self.registry = registry or get_tool_registry()
        self.logger = logger
        self._cache = cache

    def can_execute(self, tool_type: ToolType, params: Dict[str, Any]) -> bool:
        """
        Check if a tool can execute the given operation.

        Args:
            tool_type: Type of tool to check
            params: Operation parameters

        Returns:
            True if tool is registered and can handle operation, False otherwise
        """
        if not self.registry.is_registered(tool_type):
            return False

        try:
            tool = self.registry.get_tool(tool_type)
            # Run async check synchronously
            return asyncio.run(tool.should_execute(ToolContext(tenant_id=""), params))
        except Exception as e:
            self.logger.debug(
                f"Tool capability check failed for {tool_type.value}",
                extra={"error": str(e)},
            )
            return False

    def execute(
        self,
        tool_type: ToolType,
        context: ToolContext,
        params: Dict[str, Any],
    ) -> ToolResult:
        """
        Execute a tool operation.

        Synchronous wrapper around async tool execution.

        Args:
            tool_type: Type of tool to execute
            context: Execution context
            params: Operation parameters

        Returns:
            ToolResult with execution outcome

        Raises:
            ValueError: If tool type is not registered
        """
        if not self.registry.is_registered(tool_type):
            return ToolResult(
                success=False,
                error=f"Tool type '{tool_type.value}' is not registered",
                error_details={"tool_type": tool_type.value},
            )

        tool = self.registry.get_tool(tool_type)

        # Run async execution synchronously
        try:
            result = asyncio.run(tool.safe_execute(context, params))
            return result
        except Exception as e:
            # Fallback error handling if async execution fails
            self.logger.error(
                f"Tool execution failed for {tool_type.value}",
                extra={
                    "error": str(e),
                    "tool_type": tool_type.value,
                    "tenant_id": context.tenant_id,
                },
            )
            return ToolResult(
                success=False,
                error=str(e),
                error_details={
                    "exception_type": type(e).__name__,
                    "tool_type": tool_type.value,
                },
            )

    async def execute_async(
        self,
        tool_type: ToolType,
        context: ToolContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a tool operation asynchronously without asyncio.run overhead.

        Args:
            tool_type: Type of tool to execute
            context: Execution context
            params: Operation parameters

        Returns:
            ToolResult data dictionary

        Raises:
            ValueError: If tool type is not registered or execution fails
        """
        if not self.registry.is_registered(tool_type):
            raise ValueError(f"Tool type '{tool_type.value}' is not registered")

        tool = self.registry.get_tool(tool_type)
        operation = params.get("operation")
        if not operation:
            raise ValueError("operation parameter required")

        cache_key: str | None = None
        if self._cache:
            cache_key = self._cache.generate_key(tool_type.value, operation, params)
            cached = await self._cache.get(cache_key)
            if cached:
                context.set_metadata("cache_hit", True)
                return cached

        try:
            result = await tool.safe_execute(context, params)
        except Exception as exc:
            self.logger.error(
                f"Async tool execution failed for {tool_type.value}",
                extra={
                    "error": str(exc),
                    "tool_type": tool_type.value,
                    "tenant_id": context.tenant_id,
                },
            )
            raise

        if not result.success:
            raise ValueError(result.error or "Unknown tool error")

        if self._cache and cache_key:
            await self._cache.set(
                cache_key,
                result.data,
                tool_type=tool_type.value,
                operation=operation,
            )

        return result.data

    def set_cache(self, cache: ToolResultCache) -> None:
        """Attach or replace the cache instance used by this executor."""
        self._cache = cache

    def get_available_tools(self) -> Dict[str, ToolType]:
        """
        Get list of available tool types.

        Returns:
            Dictionary mapping tool names to ToolType values
        """
        tools = self.registry.get_available_tools()
        return {tool.tool_name: tool.tool_type for tool in tools.values()}

    def is_available(self, tool_type: ToolType) -> bool:
        """Check if a tool is registered and available."""
        return self.registry.is_registered(tool_type)


# Global executor instance
_global_executor: Optional[ToolExecutor] = None


def get_tool_executor(cache: Optional[ToolResultCache] = None) -> ToolExecutor:
    """Get the global tool executor, creating it if necessary."""
    global _global_executor
    if _global_executor is None:
        _global_executor = ToolExecutor(cache=cache)
    elif cache:
        _global_executor.set_cache(cache)
    return _global_executor
