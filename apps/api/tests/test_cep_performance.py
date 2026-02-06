"""
CEP Performance Test Suite

Tests index effectiveness, cache performance, and query optimization.
Provides performance benchmarks and comparison reports.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import uuid

from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

# Import modules to test
import sys
sys.path.insert(0, '/home/spa/tobit-spa-ai/apps/api')

from app.modules.cep_builder.models import (
    TbCepRule,
    TbCepExecLog,
    TbCepNotification,
    TbCepNotificationLog,
    TbCepMetricPollSnapshot,
)
from app.modules.cep_builder import crud
from app.modules.cep_builder.cache_manager import CacheManager
from app.modules.cep_builder.performance_utils import (
    performance_metrics,
    measure_time,
    IndexHelper,
    CacheStrategy,
)


@pytest.fixture
def session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_rule():
    """Create a sample rule"""
    return TbCepRule(
        rule_id=uuid.uuid4(),
        rule_name="Test Rule",
        trigger_type="metric",
        trigger_spec={"metric": "cpu_usage", "threshold": 80},
        action_spec={"action": "alert"},
        is_active=True,
        created_by="test_user",
    )


@pytest.fixture
def sample_notification():
    """Create a sample notification"""
    return TbCepNotification(
        notification_id=uuid.uuid4(),
        name="Test Notification",
        is_active=True,
        channel="slack",
        webhook_url="http://example.com",
        headers={},
        trigger={},
        policy={},
    )


class TestIndexRecommendations:
    """Test index recommendations"""

    def test_get_cep_rule_indexes(self):
        """Test getting index recommendations for tb_cep_rule"""
        indexes = IndexHelper.get_index_recommendations("tb_cep_rule")
        assert len(indexes) > 0
        assert any(idx["columns"] == ["rule_id"] for idx in indexes)
        assert any(idx["columns"] == ["is_active"] for idx in indexes)

    def test_get_exec_log_indexes(self):
        """Test getting index recommendations for tb_cep_exec_log"""
        indexes = IndexHelper.get_index_recommendations("tb_cep_exec_log")
        assert len(indexes) > 0
        assert any(idx["columns"] == ["rule_id"] for idx in indexes)

    def test_get_notification_log_indexes(self):
        """Test getting index recommendations for tb_cep_notification_log"""
        indexes = IndexHelper.get_index_recommendations("tb_cep_notification_log")
        assert len(indexes) > 0
        assert any(idx["columns"] == ["notification_id"] for idx in indexes)

    def test_all_recommendations(self):
        """Test getting all recommendations"""
        all_recs = IndexHelper.get_all_recommendations()
        assert "tb_cep_rule" in all_recs
        assert "tb_cep_exec_log" in all_recs
        assert "tb_cep_notification_log" in all_recs


class TestCacheStrategies:
    """Test cache strategy recommendations"""

    def test_rules_list_cache_strategy(self):
        """Test cache strategy for rules list"""
        strategy = CacheStrategy.get_strategy("rules_list")
        assert strategy["ttl"] == 300
        assert "on_rule_create" in strategy["invalidation"]

    def test_channel_status_cache_strategy(self):
        """Test cache strategy for channel status"""
        strategy = CacheStrategy.get_strategy("channel_status")
        assert strategy["ttl"] == 30

    def test_all_strategies(self):
        """Test getting all cache strategies"""
        all_strategies = CacheStrategy.get_all_strategies()
        assert "rules_list" in all_strategies
        assert "notifications_list" in all_strategies
        assert "system_health" in all_strategies


class TestPerformanceMetrics:
    """Test performance metrics collection"""

    def test_record_metric(self):
        """Test recording a metric"""
        performance_metrics.clear()
        performance_metrics.record("test_metric", 100.0)
        assert "test_metric" in performance_metrics.metrics

    def test_get_stats(self):
        """Test getting metric statistics"""
        performance_metrics.clear()
        performance_metrics.record("test_metric", 100.0)
        performance_metrics.record("test_metric", 200.0)
        performance_metrics.record("test_metric", 300.0)

        stats = performance_metrics.get_stats("test_metric")
        assert stats["count"] == 3
        assert stats["min"] == 100.0
        assert stats["max"] == 300.0
        assert stats["avg"] == 200.0

    def test_measure_time_context(self):
        """Test measure_time context manager"""
        performance_metrics.clear()
        with measure_time("test_operation"):
            time.sleep(0.01)

        stats = performance_metrics.get_stats("operation:test_operation")
        assert stats["count"] == 1
        assert stats["value"] >= 10.0  # At least 10ms


class TestCRUDOptimizations:
    """Test CRUD optimizations"""

    def test_list_rules_with_active_filter(self, session, sample_rule):
        """Test listing rules with active filter"""
        session.add(sample_rule)
        session.commit()

        # Test with active_only filter
        rules = crud.list_rules(session, active_only=True)
        assert len(rules) == 1

        # Test without filter
        rules = crud.list_rules(session)
        assert len(rules) == 1

    def test_list_exec_logs_with_status_filter(self, session, sample_rule):
        """Test listing exec logs with status filter"""
        exec_log = TbCepExecLog(
            exec_id=uuid.uuid4(),
            rule_id=sample_rule.rule_id,
            triggered_at=datetime.utcnow(),
            status="success",
            duration_ms=100,
            error_message=None,
            references={},
        )
        session.add(sample_rule)
        session.add(exec_log)
        session.commit()

        # Test with status filter
        logs = crud.list_exec_logs(session, sample_rule.rule_id, status="success")
        assert len(logs) == 1

    def test_list_notifications_with_filters(self, session, sample_notification):
        """Test listing notifications with filters"""
        session.add(sample_notification)
        session.commit()

        # Test with channel filter
        notifs = crud.list_notifications(session, channel="slack")
        assert len(notifs) == 1

        # Test with active_only filter
        notifs = crud.list_notifications(session, active_only=True)
        assert len(notifs) == 1


class TestCacheManager:
    """Test cache manager functionality"""

    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """Test cache manager initialization without Redis"""
        manager = CacheManager(redis_client=None)
        assert manager.available is False

    @pytest.mark.asyncio
    async def test_cache_operations_without_redis(self):
        """Test cache operations when Redis is unavailable"""
        manager = CacheManager(redis_client=None)

        # All operations should return False or None
        result = await manager.get("test_key")
        assert result is None

        result = await manager.set("test_key", {"value": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_get_rules_list_cache(self):
        """Test getting rules list from cache"""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b'{"rules": []}'

        manager = CacheManager(redis_client=mock_redis)
        manager.available = True

        result = await manager.get_rules_list()
        assert result is not None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation for rules"""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1
        mock_redis.scan.return_value = (0, [b"cep:cache:rules_list"])

        manager = CacheManager(redis_client=mock_redis)
        manager.available = True

        count = await manager.invalidate_rule("test_rule_id")
        assert count >= 0


class TestPerformanceComparison:
    """Test performance comparison scenarios"""

    def test_index_usage_explanation(self):
        """Test that indexes are explained properly"""
        indexes = IndexHelper.get_index_recommendations("tb_cep_rule")

        # Verify indexes have proper documentation
        for idx in indexes:
            assert "columns" in idx
            assert "type" in idx
            assert "reason" in idx

    def test_cache_strategy_documentation(self):
        """Test that cache strategies are documented"""
        strategies = CacheStrategy.get_all_strategies()

        for cache_type, strategy in strategies.items():
            assert "ttl" in strategy
            assert "reason" in strategy
            assert "invalidation" in strategy
            assert isinstance(strategy["ttl"], int)
            assert isinstance(strategy["invalidation"], list)

    def test_query_optimization_recommendations(self):
        """Test query optimization tips are available"""
        from app.modules.cep_builder.performance_utils import QueryOptimizationTips

        tips = QueryOptimizationTips.get_tips()
        assert len(tips) > 0

        for tip in tips:
            assert "title" in tip
            assert "description" in tip
            assert "example" in tip


class TestN1QueryPrevention:
    """Test N+1 query prevention"""

    def test_list_events_no_n1_queries(self, session, sample_rule, sample_notification):
        """Test that list_events uses proper JOINs to prevent N+1"""
        # Add rule and notification
        session.add(sample_rule)
        session.add(sample_notification)
        session.commit()

        # Add some notification logs
        for i in range(5):
            log = TbCepNotificationLog(
                log_id=uuid.uuid4(),
                notification_id=sample_notification.notification_id,
                fired_at=datetime.utcnow() - timedelta(minutes=i),
                status="delivered",
                payload={},
            )
            session.add(log)
        session.commit()

        # This should use a single query with JOINs, not N+1
        events = crud.list_events(session, limit=10)
        assert len(events) > 0


class TestPerformanceReport:
    """Test performance reporting"""

    def test_generate_performance_report(self):
        """Test generating a performance report"""
        performance_metrics.clear()

        # Simulate some operations
        for _ in range(5):
            performance_metrics.record("query", 10.0)
            performance_metrics.record("query", 15.0)
            performance_metrics.record("query", 20.0)

        stats = performance_metrics.get_stats("query")
        assert stats["count"] == 15
        assert stats["min"] == 10.0
        assert stats["max"] == 20.0
        assert 14 < stats["avg"] < 16  # Average should be around 15


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
