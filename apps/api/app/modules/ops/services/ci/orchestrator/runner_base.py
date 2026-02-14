"""
Runner Base Classes and Shared Utilities

P1-1: Runner 모듈화 - 공통 기본 클래스
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RunnerContext:
    """
    Shared context for all runner phases.

    Contains data that needs to be passed between planning, execution,
    and composition phases.
    """

    # Request context
    tenant_id: str
    trace_id: str
    request_id: str

    # Planning phase outputs
    plan: Optional[Any] = None
    plan_diagnostics: Optional[Dict[str, Any]] = None

    # Execution phase outputs
    execution_results: Dict[str, Any] = None  # type: ignore
    execution_errors: list[str] = None  # type: ignore

    # Composition phase outputs
    response_blocks: list[Any] = None  # type: ignore
    composition_metadata: Optional[Dict[str, Any]] = None

    # Tracking
    phase_times: Dict[str, float] = None  # type: ignore
    metrics_summary: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.execution_results is None:
            self.execution_results = {}
        if self.execution_errors is None:
            self.execution_errors = []
        if self.response_blocks is None:
            self.response_blocks = []
        if self.phase_times is None:
            self.phase_times = {}

    def has_errors(self) -> bool:
        """Check if execution phase had errors."""
        return len(self.execution_errors) > 0

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution phase."""
        return {
            "execution_results_count": len(self.execution_results),
            "execution_errors_count": len(self.execution_errors),
            "response_blocks_count": len(self.response_blocks),
        }


class BaseRunner:
    """
    Base class for orchestration runners.

    Provides common initialization, logging, and context management
    for planning, execution, and composition runners.
    """

    def __init__(self, context: RunnerContext):
        """
        Initialize base runner.

        Args:
            context: Shared runner context
        """
        self.context = context
        self.logger = logger

    def log_phase_start(self, phase_name: str) -> None:
        """Log start of a phase."""
        self.logger.info(
            f"[{self.context.trace_id}] {phase_name} phase starting",
            extra={"tenant_id": self.context.tenant_id},
        )

    def log_phase_end(self, phase_name: str, elapsed_ms: float) -> None:
        """Log end of a phase."""
        self.context.phase_times[phase_name] = elapsed_ms
        self.logger.info(
            f"[{self.context.trace_id}] {phase_name} phase completed in {elapsed_ms:.0f}ms",
            extra={"tenant_id": self.context.tenant_id},
        )

    def log_error(self, error_msg: str, error_detail: Optional[str] = None) -> None:
        """Log error."""
        if error_detail:
            self.logger.error(
                f"[{self.context.trace_id}] {error_msg}: {error_detail}",
                extra={"tenant_id": self.context.tenant_id},
            )
        else:
            self.logger.error(
                f"[{self.context.trace_id}] {error_msg}",
                extra={"tenant_id": self.context.tenant_id},
            )
        self.context.execution_errors.append(error_msg)

    def get_phase_times_summary(self) -> Dict[str, float]:
        """Get summary of all phase execution times."""
        return self.context.phase_times.copy()
