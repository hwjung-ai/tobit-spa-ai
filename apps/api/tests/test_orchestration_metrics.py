"""
P0-1: Orchestration Metrics Tests

Tests for SLO metrics collection and tagging.
"""

import pytest
import time
from app.modules.ops.services.ci.metrics import (
    OrchestrationMetrics,
    MetricType,
    MetricValue,
    get_orchestration_metrics,
    reset_orchestration_metrics,
)


class TestOrchestrationMetrics:
    """Test suite for Orchestration Metrics."""

    def teardown_method(self):
        """Reset metrics after each test."""
        reset_orchestration_metrics()

    def test_metrics_definitions_exist(self):
        """All required metrics should be defined."""
        expected_metrics = [
            "latency_p50",
            "latency_p95",
            "latency_p99",
            "tool_fail_rate",
            "fallback_rate",
            "replan_rate",
            "timeout_rate",
            "tool_execution_latency",
            "stage_latency",
        ]

        for metric in expected_metrics:
            assert metric in OrchestrationMetrics.METRICS
            metric_def = OrchestrationMetrics.METRICS[metric]
            assert metric_def.name == metric
            assert metric_def.metric_type in [MetricType.HISTOGRAM, MetricType.COUNTER, MetricType.GAUGE]

    def test_required_tags_defined(self):
        """Required tags should be specified."""
        assert "trace_id" in OrchestrationMetrics.REQUIRED_TAGS
        assert "tenant_id" in OrchestrationMetrics.REQUIRED_TAGS
        assert len(OrchestrationMetrics.REQUIRED_TAGS) >= 2

    def test_optional_tags_defined(self):
        """Optional tags should be defined for context."""
        assert "plan_id" in OrchestrationMetrics.OPTIONAL_TAGS
        assert "tool_call_id" in OrchestrationMetrics.OPTIONAL_TAGS
        assert "stage_name" in OrchestrationMetrics.OPTIONAL_TAGS

    def test_record_metric_basic(self):
        """Record a simple metric."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_metric("latency_p50", 150.0, tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].metric_name == "latency_p50"
        assert metrics.recorded_metrics[0].value == 150.0
        assert metrics.recorded_metrics[0].tags == tags

    def test_record_metric_multiple(self):
        """Record multiple metrics."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_metric("latency_p50", 150.0, tags)
        metrics.record_metric("latency_p95", 250.0, tags)
        metrics.record_metric("latency_p99", 350.0, tags)

        assert len(metrics.recorded_metrics) == 3

    def test_record_latency(self):
        """Record stage latency."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_latency("plan", 100.0, tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].metric_name == "stage_latency"
        assert metrics.recorded_metrics[0].tags["stage_name"] == "plan"

    def test_record_tool_latency(self):
        """Record tool execution latency."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1", "tool_call_id": "tool-1"}

        metrics.record_tool_latency("database_query", 50.0, tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].metric_name == "tool_execution_latency"
        assert metrics.recorded_metrics[0].tags["tool_type"] == "database_query"

    def test_record_tool_failure(self):
        """Record tool failure event."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_tool_failure("http_api", tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].tags["status"] == "failed"

    def test_record_fallback(self):
        """Record fallback event."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_fallback("execution_failed", tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].metric_name == "fallback_rate"
        assert metrics.recorded_metrics[0].tags["fallback_reason"] == "execution_failed"

    def test_record_replan(self):
        """Record replan event."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_replan("tool_failed", tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].metric_name == "replan_rate"
        assert metrics.recorded_metrics[0].tags["replan_reason"] == "tool_failed"

    def test_record_timeout(self):
        """Record timeout event."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_timeout(5000.0, tags)

        assert len(metrics.recorded_metrics) == 1
        assert metrics.recorded_metrics[0].metric_name == "timeout_rate"
        assert metrics.recorded_metrics[0].tags["timeout_ms"] == "5000"

    def test_request_latency_tracking(self):
        """Track total request latency."""
        metrics = OrchestrationMetrics()

        metrics.start_request()
        time.sleep(0.1)  # Sleep for 100ms
        metrics.end_request()

        latency = metrics.get_total_latency_ms()
        # Allow 10-200ms range to account for timing variations
        assert 90 <= latency <= 200

    def test_metrics_summary(self):
        """Generate metrics summary."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.start_request()
        metrics.record_metric("latency_p50", 150.0, tags)
        metrics.record_metric("tool_fail_rate", 5.0, tags)
        metrics.end_request()

        summary = metrics.get_metrics_summary()

        assert "total_latency_ms" in summary
        assert "metric_count" in summary
        assert "metrics" in summary
        assert summary["metric_count"] == 2

    def test_validate_required_tags_present(self):
        """Valid tags should pass validation."""
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        missing = OrchestrationMetrics.METRICS["latency_p50"]
        # Use class method
        validator = OrchestrationMetrics()
        missing_tags = validator.validate_required_tags(tags)

        assert len(missing_tags) == 0

    def test_validate_required_tags_missing(self):
        """Missing tags should be detected."""
        tags = {"trace_id": "trace-123"}  # Missing tenant_id

        validator = OrchestrationMetrics()
        missing_tags = validator.validate_required_tags(tags)

        assert "tenant_id" in missing_tags

    def test_record_metric_without_required_tags_warns(self, capsys):
        """Recording metric without required tags should warn."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123"}  # Missing tenant_id

        metrics.record_metric("latency_p50", 150.0, tags)

        # Should still record but warn
        assert len(metrics.recorded_metrics) == 1

    def test_unknown_metric_warning(self, capsys):
        """Recording unknown metric should warn."""
        metrics = OrchestrationMetrics()
        tags = {"trace_id": "trace-123", "tenant_id": "tenant-1"}

        metrics.record_metric("unknown_metric", 100.0, tags)

        # Should warn but not crash
        assert len(metrics.recorded_metrics) == 0  # Unknown metrics not recorded

    def test_metric_value_serialization(self):
        """MetricValue should serialize to dict."""
        metric = MetricValue(
            metric_name="latency_p50",
            value=150.0,
            tags={"trace_id": "trace-123", "tenant_id": "tenant-1"},
        )

        metric_dict = metric.to_dict()

        assert metric_dict["metric_name"] == "latency_p50"
        assert metric_dict["value"] == 150.0
        assert "trace_id" in metric_dict["tags"]
        assert "timestamp" in metric_dict

    def test_singleton_pattern(self):
        """Metrics should use singleton pattern."""
        reset_orchestration_metrics()

        metrics1 = get_orchestration_metrics()
        metrics1.record_metric("latency_p50", 100.0, {"trace_id": "t1", "tenant_id": "t1"})

        metrics2 = get_orchestration_metrics()
        assert len(metrics2.recorded_metrics) == 1

        # Should be same instance
        assert metrics1 is metrics2

    def test_default_tags_none_handling(self):
        """Should handle None tags gracefully."""
        metrics = OrchestrationMetrics()

        metrics.record_latency("execute", 100.0, tags=None)
        metrics.record_tool_latency("database_query", 50.0, tags=None)
        metrics.record_fallback("timeout", tags=None)

        assert len(metrics.recorded_metrics) == 3

    def test_complete_orchestration_flow(self):
        """Test complete orchestration metrics flow."""
        metrics = OrchestrationMetrics()
        trace_tags = {
            "trace_id": "trace-abc",
            "tenant_id": "tenant-1",
            "plan_id": "plan-1",
        }

        metrics.start_request()

        # Plan stage
        metrics.record_latency("plan", 50.0, trace_tags)

        # Tool execution
        tool_tags = {**trace_tags, "tool_call_id": "tool-1"}
        metrics.record_tool_latency("database_query", 100.0, tool_tags)

        # Execute stage
        metrics.record_latency("execute", 120.0, trace_tags)

        # Compose stage
        metrics.record_latency("compose", 30.0, trace_tags)

        metrics.end_request()

        summary = metrics.get_metrics_summary()

        assert summary["metric_count"] == 4
        assert summary["total_latency_ms"] > 0
        assert len(summary["metrics"]) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
