"""
Compatibility layer for tool execution.

Provides adapters between ToolResult and legacy tool return formats to enable
gradual migration from direct tool calls to ToolRegistry-based execution.

This module allows mixing legacy tool function calls with new ToolRegistry calls
without changing existing code.
"""

from __future__ import annotations

from typing import Any, Dict

from app.modules.ops.services.ci.tools.base import ToolResult


class ToolResultAdapter:
    """
    Adapts ToolResult to various tool return formats.

    Handles conversion between standardized ToolResult format and legacy
    tool-specific return formats to maintain backward compatibility.
    """

    @staticmethod
    def to_ci_record(result: ToolResult) -> Any:
        """
        Convert ToolResult to CI record format.

        Args:
            result: Tool execution result

        Returns:
            CI record object or None if failed

        Raises:
            ValueError: If result data is not valid
        """
        if not result.success:
            raise ValueError(result.error or "Unknown error")

        data = result.data
        if data is None:
            return None

        # If data is already a dict/object, assume it's the CI record
        return data

    @staticmethod
    def to_ci_search_result(result: ToolResult) -> Any:
        """
        Convert ToolResult to CISearchResult format.

        Args:
            result: Tool execution result

        Returns:
            CISearchResult-compatible object

        Raises:
            ValueError: If result data is not valid
        """
        if not result.success:
            raise ValueError(result.error or "Unknown error")

        # Return the result data as-is (should already be CISearchResult)
        return result.data

    @staticmethod
    def to_metric_result(result: ToolResult) -> Any:
        """
        Convert ToolResult to Metric result format.

        Args:
            result: Tool execution result

        Returns:
            Metric result object

        Raises:
            ValueError: If result data is not valid
        """
        if not result.success:
            raise ValueError(result.error or "Unknown error")

        return result.data

    @staticmethod
    def to_graph_result(result: ToolResult) -> Any:
        """
        Convert ToolResult to Graph result format.

        Args:
            result: Tool execution result

        Returns:
            Graph result object

        Raises:
            ValueError: If result data is not valid
        """
        if not result.success:
            raise ValueError(result.error or "Unknown error")

        return result.data

    @staticmethod
    def to_history_result(result: ToolResult) -> Any:
        """
        Convert ToolResult to History result format.

        Args:
            result: Tool execution result

        Returns:
            History result dict

        Raises:
            ValueError: If result data is not valid
        """
        if not result.success:
            raise ValueError(result.error or "Unknown error")

        return result.data

    @staticmethod
    def to_cep_result(result: ToolResult) -> Any:
        """
        Convert ToolResult to CEP result format.

        Args:
            result: Tool execution result

        Returns:
            CEP simulation result dict

        Raises:
            ValueError: If result data is not valid
        """
        if not result.success:
            raise ValueError(result.error or "Unknown error")

        return result.data

    @staticmethod
    def from_error(error: Exception, tool_type: str) -> ToolResult:
        """
        Create ToolResult from an exception.

        Args:
            error: The exception that occurred
            tool_type: Type of tool that failed

        Returns:
            ToolResult with error status
        """
        return ToolResult(
            success=False,
            error=str(error),
            error_details={
                "exception_type": type(error).__name__,
                "tool_type": tool_type,
            },
        )


def extract_dict_from_result(data: Any) -> Dict[str, Any]:
    """
    Extract dict from tool result data.

    Handles various return types and converts to dict format.

    Args:
        data: Tool result data

    Returns:
        Dictionary representation of data

    Raises:
        TypeError: If data cannot be converted to dict
    """
    if isinstance(data, dict):
        return data

    if hasattr(data, "dict"):
        return data.dict()

    if hasattr(data, "__dict__"):
        return data.__dict__

    raise TypeError(f"Cannot convert {type(data)} to dict")
