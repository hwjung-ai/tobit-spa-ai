"""
Base Runner Module for OPS Orchestration
Provides the base class and context for running orchestrated operations.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RunnerStatus(str, Enum):
    """Status of runner execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class RunnerContext:
    """Context for runner execution."""
    tenant_id: str
    user_id: str
    query: str
    mode: str = "all"
    trace_id: Optional[str] = None
    timeout_seconds: float = 30.0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.trace_id is None:
            import uuid
            self.trace_id = str(uuid.uuid4())


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    tool_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_details": self.error_details,
            "warnings": self.warnings,
            "execution_time_ms": self.execution_time_ms,
            "tool_name": self.tool_name,
            "metadata": self.metadata,
        }


@dataclass
class OrchestrationResult:
    """Result from orchestration execution."""
    success: bool
    status: RunnerStatus
    results: List[ToolResult] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    total_time_ms: float = 0.0
    context: Optional[RunnerContext] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "results": [r.to_dict() for r in self.results],
            "blocks": self.blocks,
            "actions": self.actions,
            "explanation": self.explanation,
            "total_time_ms": self.total_time_ms,
            "error": self.error,
        }


class BaseRunner(ABC):
    """Abstract base class for runners."""

    def __init__(self, context: RunnerContext):
        self.context = context
        self.status = RunnerStatus.PENDING
        self.results: List[ToolResult] = []
        self.start_time: float = 0.0

    @abstractmethod
    async def execute(self) -> OrchestrationResult:
        """Execute the orchestration."""
        pass

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> ToolResult:
        """Execute a single tool."""
        pass

    def record_result(self, result: ToolResult) -> None:
        """Record a tool execution result."""
        self.results.append(result)
        logger.info(
            f"[{self.context.trace_id}] Tool {result.tool_name} "
            f"{'succeeded' if result.success else 'failed'} "
            f"in {result.execution_time_ms:.2f}ms"
        )

    def start(self) -> None:
        """Mark execution as started."""
        self.status = RunnerStatus.RUNNING
        self.start_time = time.time()
        logger.info(f"[{self.context.trace_id}] Runner started for query: {self.context.query[:100]}...")

    def complete(self, success: bool = True, error: Optional[str] = None) -> OrchestrationResult:
        """Mark execution as completed and return result."""
        self.status = RunnerStatus.COMPLETED if success else RunnerStatus.FAILED
        total_time = (time.time() - self.start_time) * 1000 if self.start_time else 0

        logger.info(
            f"[{self.context.trace_id}] Runner {'completed' if success else 'failed'} "
            f"in {total_time:.2f}ms with {len(self.results)} tool executions"
        )

        return OrchestrationResult(
            success=success,
            status=self.status,
            results=self.results,
            total_time_ms=total_time,
            context=self.context,
            error=error,
        )

    def timeout(self) -> OrchestrationResult:
        """Mark execution as timed out."""
        self.status = RunnerStatus.TIMEOUT
        logger.warning(f"[{self.context.trace_id}] Runner timed out after {self.context.timeout_seconds}s")
        return OrchestrationResult(
            success=False,
            status=self.status,
            results=self.results,
            error=f"Execution timed out after {self.context.timeout_seconds} seconds",
            context=self.context,
        )


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    def __init__(self, tool_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.tool_name = tool_name
        self.message = message
        self.details = details or {}
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class RunnerTimeoutError(Exception):
    """Exception raised when runner execution times out."""
    pass


class RunnerContextManager:
    """Context manager for runner execution with automatic cleanup."""

    def __init__(self, context: RunnerContext):
        self.context = context
        self.runner: Optional[BaseRunner] = None

    async def __aenter__(self) -> "RunnerContextManager":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Cleanup resources
        if self.runner:
            # Log final status
            logger.info(f"[{self.context.trace_id}] Runner context cleaned up, status: {self.runner.status}")


def create_runner_context(
    tenant_id: str,
    user_id: str,
    query: str,
    mode: str = "all",
    **kwargs
) -> RunnerContext:
    """Factory function to create a runner context."""
    return RunnerContext(
        tenant_id=tenant_id,
        user_id=user_id,
        query=query,
        mode=mode,
        **kwargs
    )
