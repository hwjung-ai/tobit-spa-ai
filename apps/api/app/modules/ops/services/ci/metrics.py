"""
Orchestration Metrics and SLO Collection

This module provides metrics collection for OPS orchestration requests,
tracking key performance indicators and SLO compliance.

P0-1: 오케스트레이션 SLO 정의 및 강제 계측
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Metric type enumeration."""

    HISTOGRAM = "histogram"  # Latency, durations
    COUNTER = "counter"  # Event counts
    GAUGE = "gauge"  # Point-in-time measurements


@dataclass
class MetricDefinition:
    """Definition of a metric."""

    name: str
    metric_type: MetricType
    unit: str = ""
    description: str = ""


@dataclass
class MetricValue:
    """A recorded metric value."""

    metric_name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dict for serialization."""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
        }


class OrchestrationMetrics:
    """
    Orchestration SLO metrics collector.

    Tracks latency, failure rates, fallback events, and other key indicators
    for OPS orchestration pipeline performance.
    """

    # Metric definitions
    METRICS = {
        "latency_p50": MetricDefinition(
            name="latency_p50",
            metric_type=MetricType.HISTOGRAM,
            unit="ms",
            description="P50 orchestration latency",
        ),
        "latency_p95": MetricDefinition(
            name="latency_p95",
            metric_type=MetricType.HISTOGRAM,
            unit="ms",
            description="P95 orchestration latency",
        ),
        "latency_p99": MetricDefinition(
            name="latency_p99",
            metric_type=MetricType.HISTOGRAM,
            unit="ms",
            description="P99 orchestration latency",
        ),
        "tool_fail_rate": MetricDefinition(
            name="tool_fail_rate",
            metric_type=MetricType.GAUGE,
            unit="%",
            description="Percentage of tool executions that failed",
        ),
        "fallback_rate": MetricDefinition(
            name="fallback_rate",
            metric_type=MetricType.GAUGE,
            unit="%",
            description="Percentage of orchestrations using fallback flow",
        ),
        "replan_rate": MetricDefinition(
            name="replan_rate",
            metric_type=MetricType.GAUGE,
            unit="%",
            description="Percentage of orchestrations requiring replan",
        ),
        "timeout_rate": MetricDefinition(
            name="timeout_rate",
            metric_type=MetricType.GAUGE,
            unit="%",
            description="Percentage of requests exceeding timeout",
        ),
        "tool_execution_latency": MetricDefinition(
            name="tool_execution_latency",
            metric_type=MetricType.HISTOGRAM,
            unit="ms",
            description="Individual tool execution latency",
        ),
        "stage_latency": MetricDefinition(
            name="stage_latency",
            metric_type=MetricType.HISTOGRAM,
            unit="ms",
            description="Orchestration pipeline stage latency",
        ),
    }

    # Required tags for all metrics
    REQUIRED_TAGS = ["trace_id", "tenant_id"]

    # Optional tags for additional context
    OPTIONAL_TAGS = ["plan_id", "tool_call_id", "stage_name", "tool_type", "status"]

    def __init__(self):
        """Initialize metrics collector."""
        self.recorded_metrics: list[MetricValue] = []
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start_request(self) -> None:
        """Record request start time."""
        self.start_time = time.time()

    def end_request(self) -> None:
        """Record request end time."""
        self.end_time = time.time()

    def get_total_latency_ms(self) -> float:
        """Get total request latency in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def record_metric(
        self, metric_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of the metric
            value: Numeric value
            tags: Optional tags for categorization
        """
        if metric_name not in self.METRICS:
            logger.warning(f"Unknown metric: {metric_name}")
            return

        if tags is None:
            tags = {}

        # Validate required tags
        missing_tags = set(self.REQUIRED_TAGS) - set(tags.keys())
        if missing_tags:
            logger.warning(
                f"Missing required tags for {metric_name}: {missing_tags}. "
                f"Metrics may not be properly tracked."
            )

        metric = MetricValue(metric_name=metric_name, value=value, tags=tags)
        self.recorded_metrics.append(metric)

    def record_latency(self, stage_name: str, latency_ms: float, tags: dict[str, str] | None = None) -> None:
        """
        Record latency for a specific stage.

        Args:
            stage_name: Name of the stage (e.g., 'plan', 'execute', 'compose')
            latency_ms: Latency in milliseconds
            tags: Optional additional tags
        """
        if tags is None:
            tags = {}

        tags["stage_name"] = stage_name
        self.record_metric("stage_latency", latency_ms, tags)

    def record_tool_latency(
        self, tool_name: str, latency_ms: float, tags: dict[str, str] | None = None
    ) -> None:
        """
        Record latency for tool execution.

        Args:
            tool_name: Name of the tool
            latency_ms: Latency in milliseconds
            tags: Optional additional tags
        """
        if tags is None:
            tags = {}

        tags["tool_type"] = tool_name
        self.record_metric("tool_execution_latency", latency_ms, tags)

    def record_tool_failure(self, tool_name: str, tags: dict[str, str] | None = None) -> None:
        """
        Record a tool execution failure.

        Args:
            tool_name: Name of the tool
            tags: Optional additional tags
        """
        if tags is None:
            tags = {}

        tags["tool_type"] = tool_name
        tags["status"] = "failed"
        # Increment failure counter (use metric_name with _count suffix)
        self.record_metric("tool_execution_latency", 0, tags)  # Mark with status tag

    def record_fallback(self, reason: str, tags: dict[str, str] | None = None) -> None:
        """
        Record a fallback event.

        Args:
            reason: Reason for fallback (e.g., 'execution_failed', 'timeout')
            tags: Optional additional tags
        """
        if tags is None:
            tags = {}

        tags["fallback_reason"] = reason
        self.record_metric("fallback_rate", 1.0, tags)

    def record_replan(self, reason: str, tags: dict[str, str] | None = None) -> None:
        """
        Record a replan event.

        Args:
            reason: Reason for replan
            tags: Optional additional tags
        """
        if tags is None:
            tags = {}

        tags["replan_reason"] = reason
        self.record_metric("replan_rate", 1.0, tags)

    def record_timeout(self, timeout_ms: float, tags: dict[str, str] | None = None) -> None:
        """
        Record a timeout event.

        Args:
            timeout_ms: Configured timeout in milliseconds
            tags: Optional additional tags
        """
        if tags is None:
            tags = {}

        tags["timeout_ms"] = str(int(timeout_ms))
        self.record_metric("timeout_rate", 1.0, tags)

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get summary of recorded metrics.

        Returns:
            Dictionary with metric summary
        """
        total_latency = self.get_total_latency_ms()

        return {
            "total_latency_ms": total_latency,
            "metric_count": len(self.recorded_metrics),
            "metrics": [m.to_dict() for m in self.recorded_metrics],
            "collection_start": datetime.fromtimestamp(self.start_time).isoformat()
            if self.start_time
            else None,
            "collection_end": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
        }

    def validate_required_tags(self, tags: dict[str, str]) -> list[str]:
        """
        Validate that all required tags are present.

        Args:
            tags: Tags to validate

        Returns:
            List of missing tag names (empty if all present)
        """
        return list(set(self.REQUIRED_TAGS) - set(tags.keys()))


# Singleton-like instance for global metrics tracking
_metrics_instance: OrchestrationMetrics | None = None


def get_orchestration_metrics() -> OrchestrationMetrics:
    """Get or create the global orchestration metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = OrchestrationMetrics()
    return _metrics_instance


def reset_orchestration_metrics() -> None:
    """Reset the global metrics instance (for testing)."""
    global _metrics_instance
    _metrics_instance = None
