"""
Performance utilities for CEP Builder

Provides performance monitoring, metrics collection, and optimization helpers.
"""

import time
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
import json

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Collects and manages performance metrics"""

    def __init__(self):
        self.metrics: Dict[str, list] = {}

    def record(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        entry = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            entry.update(metadata)

        self.metrics[metric_name].append(entry)

    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}

        values = [entry["value"] for entry in self.metrics[metric_name]]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values),
        }

    def clear(self, metric_name: Optional[str] = None):
        """Clear metrics"""
        if metric_name:
            self.metrics.pop(metric_name, None)
        else:
            self.metrics.clear()


# Global metrics instance
performance_metrics = PerformanceMetrics()


@contextmanager
def measure_time(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager to measure operation time"""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        performance_metrics.record(f"operation:{operation_name}", elapsed_ms, metadata)
        logger.debug(f"{operation_name} took {elapsed_ms:.2f}ms")


@asynccontextmanager
async def async_measure_time(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Async context manager to measure operation time"""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        performance_metrics.record(f"operation:{operation_name}", elapsed_ms, metadata)
        logger.debug(f"{operation_name} took {elapsed_ms:.2f}ms")


def measure_query_time(func: Callable) -> Callable:
    """Decorator to measure database query time"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metadata = {
                "query": func.__name__,
                "args_count": len(args) - 1,  # Exclude 'self' or 'session'
            }
            performance_metrics.record("query", elapsed_ms, metadata)

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metadata = {
                "query": func.__name__,
                "args_count": len(args) - 1,  # Exclude 'self' or 'session'
            }
            performance_metrics.record("query", elapsed_ms, metadata)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


class IndexHelper:
    """Helper class for understanding index usage and optimization"""

    # Index recommendations for each table
    RECOMMENDED_INDEXES = {
        "tb_cep_rule": [
            {"columns": ["rule_id"], "type": "btree", "reason": "Primary key lookup"},
            {"columns": ["is_active"], "type": "btree", "reason": "Filter by active status"},
            {"columns": ["created_at"], "type": "btree", "reason": "Time-based sorting"},
            {"columns": ["updated_at"], "type": "btree", "reason": "Time-based sorting"},
            {
                "columns": ["is_active", "updated_at"],
                "type": "btree",
                "reason": "Combined filter and sort",
            },
            {"columns": ["trigger_type"], "type": "btree", "reason": "Filter by trigger type"},
        ],
        "tb_cep_exec_log": [
            {"columns": ["rule_id"], "type": "btree", "reason": "Foreign key lookup"},
            {"columns": ["triggered_at"], "type": "btree", "reason": "Time-based sorting"},
            {"columns": ["status"], "type": "btree", "reason": "Status filtering"},
            {
                "columns": ["rule_id", "triggered_at"],
                "type": "btree",
                "reason": "Combined filter for rule logs",
            },
        ],
        "tb_cep_notification_log": [
            {"columns": ["notification_id"], "type": "btree", "reason": "Foreign key lookup"},
            {"columns": ["fired_at"], "type": "btree", "reason": "Time-based sorting"},
            {"columns": ["status"], "type": "btree", "reason": "Status filtering"},
            {"columns": ["ack"], "type": "btree", "reason": "Filter by acknowledgment"},
            {
                "columns": ["notification_id", "ack"],
                "type": "btree",
                "reason": "Combined filter for unacked logs",
            },
        ],
        "tb_cep_metric_poll_snapshot": [
            {"columns": ["tick_at"], "type": "btree", "reason": "Time-based sorting"},
            {"columns": ["instance_id"], "type": "btree", "reason": "Filter by instance"},
            {"columns": ["is_leader"], "type": "btree", "reason": "Filter by leader status"},
        ],
        "tb_cep_notification": [
            {"columns": ["is_active"], "type": "btree", "reason": "Filter by active status"},
            {"columns": ["channel"], "type": "btree", "reason": "Filter by channel"},
            {"columns": ["rule_id"], "type": "btree", "reason": "Foreign key lookup"},
            {
                "columns": ["is_active", "created_at"],
                "type": "btree",
                "reason": "Combined filter and sort",
            },
        ],
    }

    @staticmethod
    def get_index_recommendations(table_name: str) -> list[Dict[str, Any]]:
        """Get recommended indexes for a table"""
        return IndexHelper.RECOMMENDED_INDEXES.get(table_name, [])

    @staticmethod
    def get_all_recommendations() -> Dict[str, list[Dict[str, Any]]]:
        """Get all index recommendations"""
        return IndexHelper.RECOMMENDED_INDEXES


class CacheStrategy:
    """Cache strategy recommendations"""

    STRATEGIES = {
        "rules_list": {
            "ttl": 300,  # 5 minutes
            "reason": "Rules change infrequently, list operations are common",
            "invalidation": ["on_rule_create", "on_rule_update", "on_rule_delete"],
        },
        "rule_detail": {
            "ttl": 600,  # 10 minutes
            "reason": "Individual rule details are stable",
            "invalidation": ["on_rule_update"],
        },
        "notifications_list": {
            "ttl": 180,  # 3 minutes
            "reason": "Notification configs change occasionally",
            "invalidation": [
                "on_notification_create",
                "on_notification_update",
                "on_notification_delete",
            ],
        },
        "notification_detail": {
            "ttl": 600,  # 10 minutes
            "reason": "Individual notification details are stable",
            "invalidation": ["on_notification_update"],
        },
        "channel_status": {
            "ttl": 30,  # 30 seconds
            "reason": "Channel status changes frequently",
            "invalidation": ["on_notification_status_change"],
        },
        "system_health": {
            "ttl": 30,  # 30 seconds
            "reason": "Health metrics are real-time critical",
            "invalidation": ["periodic_refresh"],
        },
        "rule_stats": {
            "ttl": 60,  # 1 minute
            "reason": "Statistics are updated frequently but don't need real-time updates",
            "invalidation": ["on_rule_execution"],
        },
    }

    @staticmethod
    def get_strategy(cache_name: str) -> Dict[str, Any]:
        """Get cache strategy for a cache type"""
        return CacheStrategy.STRATEGIES.get(cache_name, {})

    @staticmethod
    def get_all_strategies() -> Dict[str, Dict[str, Any]]:
        """Get all cache strategies"""
        return CacheStrategy.STRATEGIES


class QueryOptimizationTips:
    """Query optimization recommendations"""

    TIPS = [
        {
            "title": "Use LIMIT for large result sets",
            "description": "Always paginate large queries to reduce memory and network overhead",
            "example": "SELECT * FROM tb_cep_rule LIMIT 100 OFFSET 0",
        },
        {
            "title": "Use indexes for filtering",
            "description": "Ensure WHERE conditions use indexed columns",
            "example": "SELECT * FROM tb_cep_rule WHERE is_active = true AND trigger_type = 'metric'",
        },
        {
            "title": "Use composite indexes for combined conditions",
            "description": "Create indexes on multiple columns for common filter combinations",
            "example": "CREATE INDEX idx_rule_active_updated ON tb_cep_rule(is_active, updated_at DESC)",
        },
        {
            "title": "Avoid SELECT * for large tables",
            "description": "Specify only needed columns to reduce data transfer",
            "example": "SELECT rule_id, rule_name FROM tb_cep_rule",
        },
        {
            "title": "Use JOIN instead of loading related records separately",
            "description": "Avoid N+1 queries by joining related tables",
            "example": "SELECT * FROM tb_cep_notification_log JOIN tb_cep_notification ON ...",
        },
        {
            "title": "Use indexes on foreign keys",
            "description": "Ensure foreign key columns are indexed for JOIN performance",
            "example": "CREATE INDEX idx_notification_log_notification_id ON tb_cep_notification_log(notification_id)",
        },
        {
            "title": "Use Redis caching for frequently accessed data",
            "description": "Cache rules list, notifications list, and health metrics",
            "example": "Cache invalidation on updates, refresh on miss",
        },
        {
            "title": "Use database views for complex aggregations",
            "description": "Pre-compute aggregations instead of calculating on demand",
            "example": "CREATE VIEW vw_notification_summary AS SELECT ...",
        },
    ]

    @staticmethod
    def get_tips() -> list[Dict[str, str]]:
        """Get all optimization tips"""
        return QueryOptimizationTips.TIPS


import asyncio
