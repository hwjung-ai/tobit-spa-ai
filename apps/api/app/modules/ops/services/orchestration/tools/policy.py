"""
Tool Execution Policy

This module defines execution policies for tools including timeout,
retry, rate limiting, and security constraints.

P0-2: Tool 실행 정책 가드레일 추가
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ToolExecutionPolicy:
    """
    Tool execution policy for fail-closed behavior.

    Defines timeouts, retries, rate limits, and security constraints
    for tool execution.
    """

    # Timeout & Retry
    timeout_ms: int = 30000  # 30 seconds
    max_retries: int = 2  # Exponential backoff
    retry_backoff_ms: int = 100  # Initial backoff (doubles each retry)

    # Circuit Breaker
    breaker_enabled: bool = True
    breaker_threshold: int = 5  # Open breaker after N failures
    breaker_reset_ms: int = 60000  # Reset to HALF_OPEN after 60s

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_per_second: int = 10

    # SQL-specific security policies
    enforce_readonly: bool = False  # Prevent writes (default off, enable per-tool)
    block_ddl: bool = False  # Block DDL (default off, enable per-tool)
    block_dcl: bool = False  # Block DCL (default off, enable per-tool)
    block_dml_delete: bool = False  # Block DELETE (default off, enable per-tool)
    max_rows: int = 100000  # Maximum rows to return

    # HTTP-specific policies
    follow_redirects: bool = True
    max_redirect_hops: int = 5
    connect_timeout_ms: int = 5000

    # General behavior
    fail_closed: bool = True  # Reject request if policy violated
    log_violations: bool = True  # Log policy violations

    def __post_init__(self):
        """Validate policy configuration."""
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.breaker_threshold <= 0:
            raise ValueError("breaker_threshold must be positive")
        if self.rate_limit_per_minute <= 0:
            raise ValueError("rate_limit_per_minute must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Convert policy to dict."""
        return {
            "timeout_ms": self.timeout_ms,
            "max_retries": self.max_retries,
            "retry_backoff_ms": self.retry_backoff_ms,
            "breaker_enabled": self.breaker_enabled,
            "breaker_threshold": self.breaker_threshold,
            "breaker_reset_ms": self.breaker_reset_ms,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_second": self.rate_limit_per_second,
            "enforce_readonly": self.enforce_readonly,
            "block_ddl": self.block_ddl,
            "block_dcl": self.block_dcl,
            "block_dml_delete": self.block_dml_delete,
            "max_rows": self.max_rows,
            "follow_redirects": self.follow_redirects,
            "max_redirect_hops": self.max_redirect_hops,
            "connect_timeout_ms": self.connect_timeout_ms,
            "fail_closed": self.fail_closed,
            "log_violations": self.log_violations,
        }


# Default execution policy (conservative)
DEFAULT_POLICY = ToolExecutionPolicy(
    timeout_ms=30000,
    max_retries=2,
    breaker_enabled=True,
    rate_limit_enabled=True,
    rate_limit_per_minute=100,
    fail_closed=True,
)

# SQL tool policy (strict for security)
SQL_TOOL_POLICY = ToolExecutionPolicy(
    timeout_ms=60000,  # Longer timeout for complex queries
    max_retries=1,  # No retry for SQL queries
    enforce_readonly=True,  # Enforce read-only
    block_ddl=True,  # Block DDL keywords
    block_dcl=True,  # Block DCL keywords
    block_dml_delete=True,  # Block DELETE
    max_rows=5000,  # Limit result set
    fail_closed=True,
)

# HTTP API policy
HTTP_API_POLICY = ToolExecutionPolicy(
    timeout_ms=30000,
    max_retries=2,
    follow_redirects=True,
    max_redirect_hops=5,
    connect_timeout_ms=5000,
    rate_limit_per_minute=50,
)

# Graph query policy
GRAPH_QUERY_POLICY = ToolExecutionPolicy(
    timeout_ms=45000,
    max_retries=1,
    max_rows=10000,
)


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    Tracks failure count and switches between CLOSED, OPEN, and HALF_OPEN states.
    """

    def __init__(self, threshold: int = 5, reset_ms: int = 60000):
        """
        Initialize circuit breaker.

        Args:
            threshold: Number of failures before opening circuit
            reset_ms: Time in milliseconds before attempting to recover
        """
        self.threshold = threshold
        self.reset_ms = reset_ms
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitBreakerState.CLOSED

    def record_success(self) -> None:
        """Record successful execution."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            # Check if enough time has passed to try recovery
            if self.last_failure_time:
                reset_time = self.last_failure_time + timedelta(milliseconds=self.reset_ms)
                if datetime.now() >= reset_time:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker half-open, testing recovery")
                    return True
            return False

        # HALF_OPEN - allow single request for testing
        return True

    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == CircuitBreakerState.OPEN

    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state.value


class RateLimiter:
    """Simple rate limiter using sliding window counter."""

    def __init__(self, rate_per_minute: int, rate_per_second: int | None = None):
        """
        Initialize rate limiter.

        Args:
            rate_per_minute: Requests allowed per minute
            rate_per_second: Requests allowed per second (optional)
        """
        self.rate_per_minute = rate_per_minute
        self.rate_per_second = rate_per_second or (rate_per_minute // 60)
        self.requests_minute: list[datetime] = []
        self.requests_second: list[datetime] = []

    def is_allowed(self) -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.now()

        # Check per-second limit
        minute_ago = now - timedelta(minutes=1)
        self.requests_minute = [t for t in self.requests_minute if t > minute_ago]

        if len(self.requests_minute) >= self.rate_per_minute:
            return False

        # Check per-second limit
        second_ago = now - timedelta(seconds=1)
        self.requests_second = [t for t in self.requests_second if t > second_ago]

        if len(self.requests_second) >= self.rate_per_second:
            return False

        return True

    def record_request(self) -> None:
        """Record a request."""
        now = datetime.now()
        self.requests_minute.append(now)
        self.requests_second.append(now)

    def get_remaining_quota_minute(self) -> int:
        """Get remaining quota for this minute."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        self.requests_minute = [t for t in self.requests_minute if t > minute_ago]
        return max(0, self.rate_per_minute - len(self.requests_minute))

    def get_remaining_quota_second(self) -> int:
        """Get remaining quota for this second."""
        now = datetime.now()
        second_ago = now - timedelta(seconds=1)
        self.requests_second = [t for t in self.requests_second if t > second_ago]
        return max(0, self.rate_per_second - len(self.requests_second))


class PolicyViolation(Exception):
    """Raised when tool execution policy is violated."""

    def __init__(self, policy_name: str, reason: str):
        """
        Initialize policy violation.

        Args:
            policy_name: Name of the violated policy
            reason: Reason for violation
        """
        self.policy_name = policy_name
        self.reason = reason
        super().__init__(f"Policy violation: {policy_name} - {reason}")


def get_policy_for_tool_type(tool_type: str) -> ToolExecutionPolicy:
    """
    Get default execution policy for tool type.

    Args:
        tool_type: Type of tool (database_query, http_api, graph_query, etc.)

    Returns:
        Appropriate execution policy for the tool type
    """
    tool_type_lower = tool_type.lower()

    if tool_type_lower == "database_query":
        return SQL_TOOL_POLICY
    elif tool_type_lower == "http_api":
        return HTTP_API_POLICY
    elif tool_type_lower == "graph_query":
        return GRAPH_QUERY_POLICY
    else:
        return DEFAULT_POLICY
