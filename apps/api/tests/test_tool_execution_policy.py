"""
P0-2: Tool Execution Policy Tests

Tests for tool execution policies, circuit breaker, and rate limiting.
"""

import pytest
import time
from datetime import datetime, timedelta
from app.modules.ops.services.orchestration.tools.policy import (
    ToolExecutionPolicy,
    CircuitBreaker,
    RateLimiter,
    CircuitBreakerState,
    PolicyViolation,
    get_policy_for_tool_type,
    DEFAULT_POLICY,
    SQL_TOOL_POLICY,
    HTTP_API_POLICY,
    GRAPH_QUERY_POLICY,
)


class TestToolExecutionPolicy:
    """Test ToolExecutionPolicy configuration."""

    def test_default_policy_values(self):
        """Default policy should have reasonable values."""
        assert DEFAULT_POLICY.timeout_ms == 30000
        assert DEFAULT_POLICY.max_retries == 2
        assert DEFAULT_POLICY.fail_closed is True
        assert DEFAULT_POLICY.breaker_enabled is True

    def test_sql_tool_policy_strict(self):
        """SQL tool policy should be strict."""
        assert SQL_TOOL_POLICY.enforce_readonly is True
        assert SQL_TOOL_POLICY.block_ddl is True
        assert SQL_TOOL_POLICY.block_dcl is True
        assert SQL_TOOL_POLICY.max_rows == 5000

    def test_http_api_policy_config(self):
        """HTTP API policy should allow redirects."""
        assert HTTP_API_POLICY.follow_redirects is True
        assert HTTP_API_POLICY.max_redirect_hops == 5

    def test_graph_query_policy_config(self):
        """Graph query policy should have appropriate limits."""
        assert GRAPH_QUERY_POLICY.max_rows == 10000
        assert GRAPH_QUERY_POLICY.timeout_ms == 45000

    def test_policy_validation_timeout(self):
        """Invalid timeout should raise error."""
        with pytest.raises(ValueError, match="timeout_ms must be positive"):
            ToolExecutionPolicy(timeout_ms=-1)

    def test_policy_validation_retries(self):
        """Invalid retries should raise error."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            ToolExecutionPolicy(max_retries=-1)

    def test_policy_validation_breaker_threshold(self):
        """Invalid breaker threshold should raise error."""
        with pytest.raises(ValueError, match="breaker_threshold must be positive"):
            ToolExecutionPolicy(breaker_threshold=0)

    def test_policy_to_dict(self):
        """Policy should serialize to dict."""
        policy = DEFAULT_POLICY
        policy_dict = policy.to_dict()

        assert "timeout_ms" in policy_dict
        assert "max_retries" in policy_dict
        assert "fail_closed" in policy_dict
        assert policy_dict["timeout_ms"] == 30000

    def test_custom_policy_creation(self):
        """Should be able to create custom policies."""
        custom_policy = ToolExecutionPolicy(
            timeout_ms=60000,
            max_retries=3,
            max_rows=50000,
        )

        assert custom_policy.timeout_ms == 60000
        assert custom_policy.max_retries == 3
        assert custom_policy.max_rows == 50000

    def test_get_policy_for_tool_type_database_query(self):
        """Should return SQL policy for database_query."""
        policy = get_policy_for_tool_type("database_query")
        assert policy is SQL_TOOL_POLICY

    def test_get_policy_for_tool_type_http_api(self):
        """Should return HTTP policy for http_api."""
        policy = get_policy_for_tool_type("http_api")
        assert policy is HTTP_API_POLICY

    def test_get_policy_for_tool_type_graph_query(self):
        """Should return graph policy for graph_query."""
        policy = get_policy_for_tool_type("graph_query")
        assert policy is GRAPH_QUERY_POLICY

    def test_get_policy_for_tool_type_default(self):
        """Should return default policy for unknown types."""
        policy = get_policy_for_tool_type("unknown")
        assert policy is DEFAULT_POLICY

    def test_get_policy_case_insensitive(self):
        """Policy lookup should be case-insensitive."""
        policy1 = get_policy_for_tool_type("DATABASE_QUERY")
        policy2 = get_policy_for_tool_type("database_query")
        assert policy1 is policy2


class TestCircuitBreaker:
    """Test CircuitBreaker implementation."""

    def test_initial_state_closed(self):
        """Circuit breaker should start closed."""
        breaker = CircuitBreaker(threshold=3)
        assert breaker.get_state() == CircuitBreakerState.CLOSED.value
        assert breaker.is_closed() is True

    def test_success_keeps_closed(self):
        """Success should keep circuit closed."""
        breaker = CircuitBreaker(threshold=3)
        breaker.record_success()
        assert breaker.is_closed() is True

    def test_failures_open_circuit(self):
        """Circuit opens after threshold failures."""
        breaker = CircuitBreaker(threshold=3)

        breaker.record_failure()
        assert breaker.is_closed() is True

        breaker.record_failure()
        assert breaker.is_closed() is True

        breaker.record_failure()
        assert breaker.is_open() is True
        assert breaker.is_closed() is False

    def test_success_resets_failures(self):
        """Success should reset failure count."""
        breaker = CircuitBreaker(threshold=3)

        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()

        assert breaker.failure_count == 0
        assert breaker.is_closed() is True

    def test_half_open_state_recovery(self):
        """Should enter HALF_OPEN state after reset time."""
        breaker = CircuitBreaker(threshold=2, reset_ms=100)

        # Trigger open
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open() is True

        # Wait for reset time
        time.sleep(0.15)  # 150ms
        assert breaker.is_closed() is True  # HALF_OPEN allows requests

    def test_custom_threshold(self):
        """Should respect custom threshold."""
        breaker = CircuitBreaker(threshold=5)

        for _ in range(4):
            breaker.record_failure()
            assert breaker.is_closed() is True

        breaker.record_failure()
        assert breaker.is_open() is True


class TestRateLimiter:
    """Test RateLimiter implementation."""

    def test_initial_quota_allowed(self):
        """Initial request should be allowed."""
        limiter = RateLimiter(rate_per_minute=60, rate_per_second=1)
        assert limiter.is_allowed() is True

    def test_per_minute_limit(self):
        """Should enforce per-minute limit."""
        limiter = RateLimiter(rate_per_minute=2, rate_per_second=10)

        assert limiter.is_allowed() is True
        limiter.record_request()

        assert limiter.is_allowed() is True
        limiter.record_request()

        assert limiter.is_allowed() is False  # Exceeded per-minute limit

    def test_per_second_limit(self):
        """Should enforce per-second limit."""
        limiter = RateLimiter(rate_per_minute=100, rate_per_second=2)

        assert limiter.is_allowed() is True
        limiter.record_request()

        assert limiter.is_allowed() is True
        limiter.record_request()

        assert limiter.is_allowed() is False  # Exceeded per-second limit

    def test_quota_resets_after_period(self):
        """Quota should reset after time period."""
        # Use higher per-minute limit so it doesn't block
        limiter = RateLimiter(rate_per_minute=60, rate_per_second=1)

        assert limiter.is_allowed() is True
        limiter.record_request()
        assert limiter.is_allowed() is False  # Per-second limit reached

        # Wait for per-second quota to reset
        time.sleep(1.5)  # Over 1 second
        # Per-second quota should reset, per-minute quota still has budget
        assert limiter.is_allowed() is True  # Should be allowed now

    def test_remaining_quota_minute(self):
        """Should report remaining minute quota."""
        limiter = RateLimiter(rate_per_minute=5, rate_per_second=10)

        assert limiter.get_remaining_quota_minute() == 5
        limiter.record_request()
        assert limiter.get_remaining_quota_minute() == 4

    def test_remaining_quota_second(self):
        """Should report remaining second quota."""
        limiter = RateLimiter(rate_per_minute=100, rate_per_second=3)

        assert limiter.get_remaining_quota_second() == 3
        limiter.record_request()
        assert limiter.get_remaining_quota_second() == 2

    def test_cleanup_old_entries(self):
        """Should remove old entries from tracking."""
        limiter = RateLimiter(rate_per_minute=100, rate_per_second=10)

        # Add requests
        now = datetime.now()
        for _ in range(5):
            limiter.record_request()

        # Manually set old timestamps
        old_time = now - timedelta(minutes=2)
        limiter.requests_minute = [old_time] * 5

        # Check quota - old entries should be ignored
        remaining = limiter.get_remaining_quota_minute()
        assert remaining == 100  # All old requests cleaned up


class TestPolicyViolation:
    """Test PolicyViolation exception."""

    def test_policy_violation_creation(self):
        """Should create policy violation with details."""
        violation = PolicyViolation("timeout", "Exceeded 30000ms")

        assert violation.policy_name == "timeout"
        assert violation.reason == "Exceeded 30000ms"

    def test_policy_violation_message(self):
        """Exception should have descriptive message."""
        violation = PolicyViolation("max_retries", "Exceeded max retries")

        assert "Policy violation" in str(violation)
        assert "max_retries" in str(violation)


class TestPolicyIntegration:
    """Integration tests for policies."""

    def test_sql_policy_prevents_writes(self):
        """SQL policy should enforce read-only."""
        assert SQL_TOOL_POLICY.enforce_readonly is True
        assert SQL_TOOL_POLICY.block_ddl is True
        assert SQL_TOOL_POLICY.block_dml_delete is True

    def test_http_policy_redirect_safety(self):
        """HTTP policy should limit redirects."""
        assert HTTP_API_POLICY.follow_redirects is True
        assert HTTP_API_POLICY.max_redirect_hops == 5

    def test_all_policies_fail_closed(self):
        """All policies should fail closed by default."""
        policies = [DEFAULT_POLICY, SQL_TOOL_POLICY, HTTP_API_POLICY, GRAPH_QUERY_POLICY]
        for policy in policies:
            assert policy.fail_closed is True

    def test_timeout_hierarchy(self):
        """Different tools should have appropriate timeouts."""
        assert DEFAULT_POLICY.timeout_ms == 30000  # 30s
        assert SQL_TOOL_POLICY.timeout_ms == 60000  # 60s (longer for queries)
        assert GRAPH_QUERY_POLICY.timeout_ms == 45000  # 45s

    def test_policy_completeness(self):
        """All policies should be properly configured."""
        policies = [DEFAULT_POLICY, SQL_TOOL_POLICY, HTTP_API_POLICY, GRAPH_QUERY_POLICY]

        for policy in policies:
            # All policies should have these critical fields set
            assert policy.timeout_ms > 0
            assert policy.fail_closed is True
            assert isinstance(policy.max_retries, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
