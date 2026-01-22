"""Rule performance monitoring and metrics collection for CEP rules"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RuleExecutionMetric:
    """Represents a single rule execution metric"""

    def __init__(
        self,
        rule_id: str,
        execution_time_ms: int,
        events_processed: int,
        events_matched: int,
        errors: Optional[List[str]] = None,
    ):
        self.rule_id = rule_id
        self.execution_time_ms = execution_time_ms
        self.events_processed = events_processed
        self.events_matched = events_matched
        self.errors = errors or []
        self.error_count = len(self.errors)
        self.created_at = datetime.utcnow()
        self.success = len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            "rule_id": self.rule_id,
            "execution_time_ms": self.execution_time_ms,
            "events_processed": self.events_processed,
            "events_matched": self.events_matched,
            "error_count": self.error_count,
            "success": self.success,
            "created_at": self.created_at.isoformat(),
        }


class RulePerformanceStats:
    """Performance statistics for a rule"""

    def __init__(
        self,
        rule_id: str,
        total_executions: int = 0,
        avg_execution_time_ms: float = 0,
        min_execution_time_ms: int = 0,
        max_execution_time_ms: int = 0,
        p50_execution_time_ms: float = 0,
        p95_execution_time_ms: float = 0,
        p99_execution_time_ms: float = 0,
        total_events_processed: int = 0,
        total_events_matched: int = 0,
        total_errors: int = 0,
        success_rate: float = 0.0,
    ):
        self.rule_id = rule_id
        self.total_executions = total_executions
        self.avg_execution_time_ms = avg_execution_time_ms
        self.min_execution_time_ms = min_execution_time_ms
        self.max_execution_time_ms = max_execution_time_ms
        self.p50_execution_time_ms = p50_execution_time_ms
        self.p95_execution_time_ms = p95_execution_time_ms
        self.p99_execution_time_ms = p99_execution_time_ms
        self.total_events_processed = total_events_processed
        self.total_events_matched = total_events_matched
        self.total_errors = total_errors
        self.success_rate = success_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "rule_id": self.rule_id,
            "total_executions": self.total_executions,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "min_execution_time_ms": self.min_execution_time_ms,
            "max_execution_time_ms": self.max_execution_time_ms,
            "p50_execution_time_ms": self.p50_execution_time_ms,
            "p95_execution_time_ms": self.p95_execution_time_ms,
            "p99_execution_time_ms": self.p99_execution_time_ms,
            "total_events_processed": self.total_events_processed,
            "total_events_matched": self.total_events_matched,
            "total_errors": self.total_errors,
            "success_rate": self.success_rate,
        }


class RulePerformanceMonitor:
    """Monitor CEP rule execution performance"""

    def __init__(self):
        self.metrics: Dict[str, List[RuleExecutionMetric]] = {}
        self.stats_cache: Dict[str, RulePerformanceStats] = {}
        self.cache_ttl_seconds = 300  # 5 minutes

    def record_execution(
        self,
        rule_id: str,
        execution_time_ms: int,
        events_processed: int,
        events_matched: int,
        errors: Optional[List[str]] = None,
    ) -> RuleExecutionMetric:
        """Record a rule execution metric"""

        metric = RuleExecutionMetric(
            rule_id=rule_id,
            execution_time_ms=execution_time_ms,
            events_processed=events_processed,
            events_matched=events_matched,
            errors=errors,
        )

        # Add to metrics storage
        if rule_id not in self.metrics:
            self.metrics[rule_id] = []

        self.metrics[rule_id].append(metric)

        # Keep only last 1000 metrics per rule to avoid memory bloat
        if len(self.metrics[rule_id]) > 1000:
            self.metrics[rule_id] = self.metrics[rule_id][-1000:]

        # Invalidate cache for this rule
        if rule_id in self.stats_cache:
            del self.stats_cache[rule_id]

        logger.debug(
            f"Recorded execution for rule {rule_id}: "
            f"{execution_time_ms}ms, {events_processed} events, {events_matched} matches"
        )

        return metric

    def get_rule_performance(
        self,
        rule_id: str,
        time_range_minutes: Optional[int] = None,
    ) -> RulePerformanceStats:
        """Get aggregated performance statistics for a rule"""

        # Return cached stats if available and not expired
        if rule_id in self.stats_cache:
            return self.stats_cache[rule_id]

        # Get metrics for the rule
        metrics = self.metrics.get(rule_id, [])

        if not metrics:
            return RulePerformanceStats(rule_id=rule_id)

        # Filter by time range if specified
        if time_range_minutes:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_range_minutes)
            metrics = [m for m in metrics if m.created_at > cutoff_time]

        if not metrics:
            return RulePerformanceStats(rule_id=rule_id)

        # Calculate statistics
        execution_times = [m.execution_time_ms for m in metrics]
        successful_executions = sum(1 for m in metrics if m.success)

        try:
            p50 = statistics.median(execution_times)
            p95 = statistics.quantiles(execution_times, n=20)[18] if len(execution_times) > 20 else max(execution_times)
            p99 = statistics.quantiles(execution_times, n=100)[98] if len(execution_times) > 100 else max(execution_times)
        except (statistics.StatisticsError, IndexError):
            p50 = p95 = p99 = statistics.mean(execution_times)

        stats = RulePerformanceStats(
            rule_id=rule_id,
            total_executions=len(metrics),
            avg_execution_time_ms=statistics.mean(execution_times),
            min_execution_time_ms=min(execution_times),
            max_execution_time_ms=max(execution_times),
            p50_execution_time_ms=p50,
            p95_execution_time_ms=p95,
            p99_execution_time_ms=p99,
            total_events_processed=sum(m.events_processed for m in metrics),
            total_events_matched=sum(m.events_matched for m in metrics),
            total_errors=sum(m.error_count for m in metrics),
            success_rate=successful_executions / len(metrics) if metrics else 0.0,
        )

        # Cache the stats
        self.stats_cache[rule_id] = stats

        return stats

    def get_all_performance_stats(self) -> List[RulePerformanceStats]:
        """Get performance statistics for all rules"""
        return [self.get_rule_performance(rule_id) for rule_id in self.metrics.keys()]

    def get_rule_errors(
        self,
        rule_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent errors for a rule"""
        metrics = self.metrics.get(rule_id, [])

        # Filter metrics with errors and sort by creation time (newest first)
        error_metrics = [m for m in metrics if m.errors]
        error_metrics.sort(key=lambda m: m.created_at, reverse=True)

        # Extract error information
        errors = []
        for metric in error_metrics[:limit]:
            for error in metric.errors:
                errors.append({
                    "rule_id": rule_id,
                    "error": error,
                    "timestamp": metric.created_at.isoformat(),
                    "execution_time_ms": metric.execution_time_ms,
                })

        return errors

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        if not self.metrics:
            return {
                "status": "healthy",
                "total_rules": 0,
                "total_executions": 0,
                "avg_success_rate": 0.0,
                "critical_rules": [],
            }

        all_stats = self.get_all_performance_stats()

        total_executions = sum(s.total_executions for s in all_stats)
        avg_success_rate = (
            statistics.mean(s.success_rate for s in all_stats)
            if all_stats
            else 0.0
        )

        # Identify critical rules (low success rate or high error count)
        critical_rules = [
            {
                "rule_id": s.rule_id,
                "success_rate": s.success_rate,
                "error_count": s.total_errors,
                "avg_execution_time_ms": s.avg_execution_time_ms,
            }
            for s in all_stats
            if s.success_rate < 0.95 or s.total_errors > 10
        ]

        # Determine overall health status
        if not critical_rules and avg_success_rate >= 0.99:
            status = "healthy"
        elif len(critical_rules) <= 2 and avg_success_rate >= 0.95:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "total_rules": len(self.metrics),
            "total_executions": total_executions,
            "avg_success_rate": avg_success_rate,
            "critical_rules": critical_rules,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def clear_old_metrics(self, days: int = 7) -> int:
        """Clear metrics older than specified days"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        total_removed = 0

        for rule_id in self.metrics:
            original_count = len(self.metrics[rule_id])
            self.metrics[rule_id] = [
                m for m in self.metrics[rule_id]
                if m.created_at > cutoff_time
            ]
            total_removed += original_count - len(self.metrics[rule_id])

        logger.info(f"Cleared {total_removed} old metrics (older than {days} days)")

        return total_removed
