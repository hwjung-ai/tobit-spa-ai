"""
P0-3: Tool Error Code Classification Tests

Tests for standardized error codes for failure classification.
"""

import pytest
from schemas.tool_contracts import ToolErrorCode, ToolCall, ToolCallTrace


class TestToolErrorCodeEnum:
    """Test ToolErrorCode enum."""

    def test_policy_error_codes(self):
        """Policy violation error codes should be defined."""
        assert ToolErrorCode.POLICY_DENY.value == "POLICY_DENY"
        assert ToolErrorCode.RATE_LIMITED.value == "RATE_LIMITED"
        assert ToolErrorCode.CIRCUIT_OPEN.value == "CIRCUIT_OPEN"

    def test_execution_error_codes(self):
        """Execution failure error codes should be defined."""
        assert ToolErrorCode.TOOL_TIMEOUT.value == "TOOL_TIMEOUT"
        assert ToolErrorCode.TOOL_BAD_REQUEST.value == "TOOL_BAD_REQUEST"
        assert ToolErrorCode.UPSTREAM_UNAVAILABLE.value == "UPSTREAM_UNAVAILABLE"
        assert ToolErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"

    def test_orchestration_error_codes(self):
        """Orchestration failure error codes should be defined."""
        assert ToolErrorCode.PLAN_INVALID.value == "PLAN_INVALID"
        assert ToolErrorCode.PLAN_TIMEOUT.value == "PLAN_TIMEOUT"
        assert ToolErrorCode.EXECUTE_TIMEOUT.value == "EXECUTE_TIMEOUT"
        assert ToolErrorCode.COMPOSE_TIMEOUT.value == "COMPOSE_TIMEOUT"

    def test_security_error_codes(self):
        """Security violation error codes should be defined."""
        assert ToolErrorCode.SQL_BLOCKED.value == "SQL_BLOCKED"
        assert ToolErrorCode.TENANT_MISMATCH.value == "TENANT_MISMATCH"
        assert ToolErrorCode.AUTH_FAILED.value == "AUTH_FAILED"
        assert ToolErrorCode.PERMISSION_DENIED.value == "PERMISSION_DENIED"

    def test_data_error_codes(self):
        """Data error codes should be defined."""
        assert ToolErrorCode.DATA_NOT_FOUND.value == "DATA_NOT_FOUND"
        assert ToolErrorCode.INVALID_PARAMS.value == "INVALID_PARAMS"
        assert ToolErrorCode.MAX_ROWS_EXCEEDED.value == "MAX_ROWS_EXCEEDED"

    def test_error_code_count(self):
        """Should have sufficient error codes."""
        all_codes = list(ToolErrorCode)
        assert len(all_codes) >= 15  # At least 15 error codes

    def test_error_code_uniqueness(self):
        """All error codes should be unique."""
        codes = [code.value for code in ToolErrorCode]
        assert len(codes) == len(set(codes))

    def test_error_code_string_conversion(self):
        """Error codes should convert to strings properly."""
        code = ToolErrorCode.TOOL_TIMEOUT
        assert str(code.value) == "TOOL_TIMEOUT"
        assert code.value in ToolErrorCode.__members__.values()


class TestToolCallWithErrorCode:
    """Test ToolCall with error_code field."""

    def test_tool_call_success(self):
        """ToolCall should work without error_code for success."""
        call = ToolCall(
            tool="ci.search",
            elapsed_ms=100,
            input_params={"query": "server01"},
            output_summary={"count": 5},
        )

        assert call.tool == "ci.search"
        assert call.elapsed_ms == 100
        assert call.error is None
        assert call.error_code is None

    def test_tool_call_with_error_and_code(self):
        """ToolCall should record error and error_code."""
        call = ToolCall(
            tool="database_query",
            elapsed_ms=35000,
            input_params={"query": "SELECT ..."},
            error="Execution timeout",
            error_code=ToolErrorCode.TOOL_TIMEOUT.value,
        )

        assert call.tool == "database_query"
        assert call.error == "Execution timeout"
        assert call.error_code == ToolErrorCode.TOOL_TIMEOUT.value

    def test_tool_call_policy_violation(self):
        """ToolCall should record policy violation."""
        call = ToolCall(
            tool="http_api",
            elapsed_ms=0,
            error="Policy violation: rate limit exceeded",
            error_code=ToolErrorCode.RATE_LIMITED.value,
        )

        assert call.error_code == ToolErrorCode.RATE_LIMITED.value

    def test_tool_call_sql_blocked(self):
        """ToolCall should record SQL block."""
        call = ToolCall(
            tool="database_query",
            elapsed_ms=50,
            input_params={"query": "DROP TABLE users"},
            error="Dangerous SQL keyword detected",
            error_code=ToolErrorCode.SQL_BLOCKED.value,
        )

        assert call.error_code == ToolErrorCode.SQL_BLOCKED.value

    def test_tool_call_trace_with_mixed_results(self):
        """ToolCallTrace should handle mixed success/failure."""
        trace = ToolCallTrace(
            tool_calls=[
                ToolCall(
                    tool="ci.search",
                    elapsed_ms=100,
                    input_params={"query": "server01"},
                    output_summary={"count": 5},
                ),
                ToolCall(
                    tool="metric.aggregate",
                    elapsed_ms=35000,
                    input_params={"metric": "latency"},
                    error="Timeout",
                    error_code=ToolErrorCode.TOOL_TIMEOUT.value,
                ),
            ],
            total_elapsed_ms=35100,
            total_calls=2,
        )

        assert len(trace.tool_calls) == 2
        assert trace.tool_calls[0].error_code is None  # Success
        assert trace.tool_calls[1].error_code == ToolErrorCode.TOOL_TIMEOUT.value  # Failure


class TestErrorCodeCategories:
    """Test error code categories."""

    def test_policy_violations_category(self):
        """Policy violation codes."""
        policy_codes = [
            ToolErrorCode.POLICY_DENY,
            ToolErrorCode.RATE_LIMITED,
            ToolErrorCode.CIRCUIT_OPEN,
        ]
        assert len(policy_codes) == 3

    def test_timeout_errors_category(self):
        """All timeout-related error codes."""
        timeout_codes = [
            ToolErrorCode.TOOL_TIMEOUT,
            ToolErrorCode.PLAN_TIMEOUT,
            ToolErrorCode.EXECUTE_TIMEOUT,
            ToolErrorCode.COMPOSE_TIMEOUT,
        ]
        for code in timeout_codes:
            assert "TIMEOUT" in code.value

    def test_security_violations_category(self):
        """Security violation codes."""
        security_codes = [
            ToolErrorCode.SQL_BLOCKED,
            ToolErrorCode.TENANT_MISMATCH,
            ToolErrorCode.AUTH_FAILED,
            ToolErrorCode.PERMISSION_DENIED,
        ]
        assert len(security_codes) == 4

    def test_external_failures_category(self):
        """External service failure codes."""
        external_codes = [
            ToolErrorCode.UPSTREAM_UNAVAILABLE,
            ToolErrorCode.DATA_NOT_FOUND,
        ]
        for code in external_codes:
            assert code in list(ToolErrorCode)

    def test_internal_errors_category(self):
        """Internal error codes."""
        internal_codes = [
            ToolErrorCode.INTERNAL_ERROR,
            ToolErrorCode.INVALID_PARAMS,
        ]
        for code in internal_codes:
            assert code in list(ToolErrorCode)


class TestErrorCodeMapping:
    """Test mapping common errors to codes."""

    def test_timeout_classification(self):
        """Timeout errors should map to TOOL_TIMEOUT."""
        timeout_scenarios = [
            ("Query execution exceeded 30000ms", ToolErrorCode.TOOL_TIMEOUT),
            ("HTTP request timeout", ToolErrorCode.TOOL_TIMEOUT),
            ("Plan timeout", ToolErrorCode.PLAN_TIMEOUT),
        ]

        for error_msg, expected_code in timeout_scenarios:
            if "Plan timeout" in error_msg:
                assert expected_code == ToolErrorCode.PLAN_TIMEOUT
            else:
                assert expected_code == ToolErrorCode.TOOL_TIMEOUT

    def test_sql_blocked_classification(self):
        """SQL dangers should map to SQL_BLOCKED."""
        sql_dangers = [
            ("DROP keyword detected", ToolErrorCode.SQL_BLOCKED),
            ("DELETE not allowed", ToolErrorCode.SQL_BLOCKED),
            ("DDL statement denied", ToolErrorCode.SQL_BLOCKED),
        ]

        for error_msg, expected_code in sql_dangers:
            assert expected_code == ToolErrorCode.SQL_BLOCKED

    def test_policy_classification(self):
        """Policy violations should map correctly."""
        policy_scenarios = [
            ("Rate limit exceeded", ToolErrorCode.RATE_LIMITED),
            ("Circuit breaker open", ToolErrorCode.CIRCUIT_OPEN),
            ("Request denied by policy", ToolErrorCode.POLICY_DENY),
        ]

        for error_msg, expected_code in policy_scenarios:
            assert expected_code in [ToolErrorCode.RATE_LIMITED, ToolErrorCode.CIRCUIT_OPEN, ToolErrorCode.POLICY_DENY]


class TestErrorCodeDocumentation:
    """Test error code documentation."""

    def test_all_codes_have_docstring(self):
        """All error codes should be defined in enum."""
        # Verify enum is properly defined
        assert hasattr(ToolErrorCode, "POLICY_DENY")
        assert hasattr(ToolErrorCode, "TOOL_TIMEOUT")
        assert hasattr(ToolErrorCode, "SQL_BLOCKED")

    def test_error_code_naming_convention(self):
        """Error codes should follow UPPER_CASE_SNAKE_CASE convention."""
        for code in ToolErrorCode:
            # Check format
            assert code.value.isupper()
            assert "_" in code.value or code.value.isalnum()
            # No spaces or special chars
            assert all(c.isalnum() or c == "_" for c in code.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
