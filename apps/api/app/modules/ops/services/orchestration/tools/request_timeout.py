"""
Request-wide Timeout Management

This module provides request-level timeout enforcement for orchestration execution.
Prevents circular execution, infinite waits, and runaway processes.

P0-5: 요청 전체 Timeout 관리
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from core.logging import get_logger

logger = get_logger(__name__)


class RequestTimeoutError(Exception):
    """Raised when request-wide timeout is exceeded."""

    def __init__(self, phase: str, elapsed_ms: float, timeout_ms: float):
        """
        Initialize timeout error.

        Args:
            phase: Which phase exceeded timeout (plan, execute, compose)
            elapsed_ms: Elapsed time in milliseconds
            timeout_ms: Configured timeout in milliseconds
        """
        self.phase = phase
        self.elapsed_ms = elapsed_ms
        self.timeout_ms = timeout_ms
        super().__init__(
            f"Request timeout in {phase} phase: {elapsed_ms:.0f}ms exceeded {timeout_ms:.0f}ms"
        )


class TimeoutPhase(str, Enum):
    """Execution phases with timeout tracking."""

    PLAN = "plan"
    EXECUTE = "execute"
    COMPOSE = "compose"


@dataclass
class TimeoutBudget:
    """
    Timeout budget for a request.

    Allocates total timeout across different phases.
    """

    total_timeout_ms: float  # Total request timeout (e.g., 120000 = 120s)
    plan_timeout_ms: float = 30000  # Planning phase timeout (30s)
    execute_timeout_ms: float = 60000  # Execution phase timeout (60s)
    compose_timeout_ms: float = 20000  # Composition phase timeout (20s)

    # Internal tracking
    start_time: datetime = field(default_factory=datetime.now)
    phase_times: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Validate budget configuration."""
        total = self.plan_timeout_ms + self.execute_timeout_ms + self.compose_timeout_ms
        if total > self.total_timeout_ms:
            logger.warning(
                f"Phase timeouts sum to {total}ms but total budget is {self.total_timeout_ms}ms. "
                f"May need reallocation."
            )

    def get_elapsed_ms(self) -> float:
        """Get elapsed time since request start."""
        return (datetime.now() - self.start_time).total_seconds() * 1000

    def get_remaining_ms(self) -> float:
        """Get remaining time in request."""
        return self.total_timeout_ms - self.get_elapsed_ms()

    def is_exhausted(self) -> bool:
        """Check if request timeout is exhausted."""
        return self.get_remaining_ms() <= 0

    def check_phase_timeout(self, phase: TimeoutPhase, elapsed_ms: float) -> None:
        """
        Check if phase has exceeded timeout.

        Args:
            phase: Phase being checked
            elapsed_ms: Time spent in phase

        Raises:
            RequestTimeoutError: If phase timeout exceeded
        """
        phase_timeout = self._get_phase_timeout(phase)
        if elapsed_ms > phase_timeout:
            logger.error(f"Phase timeout exceeded: {phase.value} {elapsed_ms}ms > {phase_timeout}ms")
            raise RequestTimeoutError(phase.value, elapsed_ms, phase_timeout)

    def check_total_timeout(self) -> None:
        """
        Check if total request timeout is exhausted.

        Raises:
            RequestTimeoutError: If total timeout exceeded
        """
        elapsed = self.get_elapsed_ms()
        if elapsed > self.total_timeout_ms:
            raise RequestTimeoutError("total", elapsed, self.total_timeout_ms)

    def record_phase_time(self, phase: TimeoutPhase, elapsed_ms: float) -> None:
        """Record phase execution time."""
        self.phase_times[phase.value] = elapsed_ms
        logger.debug(f"Phase {phase.value} executed in {elapsed_ms:.0f}ms")

    def get_remaining_for_phase(self, phase: TimeoutPhase) -> float:
        """
        Get remaining timeout for a specific phase.

        Reduces phase timeout if total timeout would be exceeded.

        Args:
            phase: Phase to check

        Returns:
            Remaining timeout for phase in milliseconds
        """
        phase_timeout = self._get_phase_timeout(phase)
        remaining = self.get_remaining_ms()

        # Return minimum of phase timeout and total remaining
        return min(phase_timeout, max(0, remaining))

    def _get_phase_timeout(self, phase: TimeoutPhase) -> float:
        """Get timeout for specific phase."""
        timeout_map = {
            TimeoutPhase.PLAN: self.plan_timeout_ms,
            TimeoutPhase.EXECUTE: self.execute_timeout_ms,
            TimeoutPhase.COMPOSE: self.compose_timeout_ms,
        }
        return timeout_map.get(phase, self.total_timeout_ms)

    def to_dict(self) -> dict[str, Any]:
        """Convert budget to dict."""
        return {
            "total_timeout_ms": self.total_timeout_ms,
            "plan_timeout_ms": self.plan_timeout_ms,
            "execute_timeout_ms": self.execute_timeout_ms,
            "compose_timeout_ms": self.compose_timeout_ms,
            "elapsed_ms": self.get_elapsed_ms(),
            "remaining_ms": self.get_remaining_ms(),
            "phase_times": self.phase_times,
        }


class RequestTimeoutManager:
    """
    Manages request-wide timeout enforcement.

    Provides context managers and decorators for timeout tracking.
    """

    def __init__(self, timeout_ms: float = 120000):
        """
        Initialize timeout manager.

        Args:
            timeout_ms: Total request timeout in milliseconds (default 120s)
        """
        self.budget = TimeoutBudget(total_timeout_ms=timeout_ms)

    async def execute_with_timeout(
        self,
        phase: TimeoutPhase,
        coro: Any,
    ) -> Any:
        """
        Execute coroutine with phase timeout enforcement.

        Args:
            phase: Execution phase
            coro: Async coroutine to execute

        Returns:
            Coroutine result

        Raises:
            asyncio.TimeoutError: If timeout exceeded
            RequestTimeoutError: If request timeout exceeded
        """
        # Check total timeout before starting
        self.budget.check_total_timeout()

        phase_timeout = self.budget.get_remaining_for_phase(phase)
        if phase_timeout <= 0:
            raise RequestTimeoutError(
                phase.value, self.budget.get_elapsed_ms(), self.budget.total_timeout_ms
            )

        try:
            start = time.time()
            result = await asyncio.wait_for(coro, timeout=phase_timeout / 1000)  # Convert to seconds
            elapsed = (time.time() - start) * 1000
            self.budget.record_phase_time(phase, elapsed)
            return result
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            self.budget.record_phase_time(phase, elapsed)
            raise RequestTimeoutError(phase.value, elapsed, phase_timeout)

    def execute_sync_with_timeout(
        self,
        phase: TimeoutPhase,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute synchronous function with phase timeout enforcement.

        Args:
            phase: Execution phase
            func: Synchronous function to execute
            args: Function args
            kwargs: Function kwargs

        Returns:
            Function result

        Raises:
            RequestTimeoutError: If timeout exceeded
        """
        # Check total timeout before starting
        self.budget.check_total_timeout()

        phase_timeout = self.budget.get_remaining_for_phase(phase)
        if phase_timeout <= 0:
            raise RequestTimeoutError(
                phase.value, self.budget.get_elapsed_ms(), self.budget.total_timeout_ms
            )

        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start) * 1000
            self.budget.record_phase_time(phase, elapsed)
            return result
        except Exception:
            elapsed = (time.time() - start) * 1000
            self.budget.record_phase_time(phase, elapsed)
            raise

    @asynccontextmanager
    async def phase_timeout(self, phase: TimeoutPhase):
        """
        Context manager for phase timeout enforcement.

        Usage:
            async with manager.phase_timeout(TimeoutPhase.PLAN):
                result = await plan()

        Raises:
            RequestTimeoutError: If timeout exceeded
        """
        # Check total timeout before starting
        self.budget.check_total_timeout()

        phase_timeout = self.budget.get_remaining_for_phase(phase)
        if phase_timeout <= 0:
            raise RequestTimeoutError(
                phase.value, self.budget.get_elapsed_ms(), self.budget.total_timeout_ms
            )

        start = time.time()
        try:
            yield self
        finally:
            elapsed = (time.time() - start) * 1000
            self.budget.record_phase_time(phase, elapsed)

    def get_timeout_summary(self) -> dict[str, Any]:
        """Get summary of timeout status."""
        return {
            "elapsed_ms": self.budget.get_elapsed_ms(),
            "remaining_ms": self.budget.get_remaining_ms(),
            "is_exhausted": self.budget.is_exhausted(),
            "phase_times": self.budget.phase_times,
            "budget": self.budget.to_dict(),
        }


# Default global timeout manager
_global_timeout_manager: RequestTimeoutManager | None = None


def get_request_timeout_manager(timeout_ms: float = 120000) -> RequestTimeoutManager:
    """
    Get or create global request timeout manager.

    Args:
        timeout_ms: Request timeout in milliseconds

    Returns:
        Timeout manager instance
    """
    global _global_timeout_manager
    if _global_timeout_manager is None:
        _global_timeout_manager = RequestTimeoutManager(timeout_ms=timeout_ms)
    return _global_timeout_manager


def reset_request_timeout_manager() -> None:
    """Reset global timeout manager."""
    global _global_timeout_manager
    _global_timeout_manager = None
