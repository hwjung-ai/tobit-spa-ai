"""
Tests for monitoring dashboard API endpoints
"""

import pytest
from app.modules.cep_builder.models import (
    TbCepExecLog,
    TbCepNotification,
    TbCepNotificationLog,
    TbCepRule,
)
from sqlmodel import Session


@pytest.fixture
def sample_rule(session: Session):
    """Create a sample rule for testing"""
    rule = TbCepRule(
        rule_name="Test Rule",
        trigger_type="metric",
        trigger_spec={"field": "cpu", "threshold": 80},
        action_spec={"endpoint": "/notify"},
        is_active=True,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


@pytest.fixture
def sample_notification(session: Session, sample_rule):
    """Create a sample notification"""
    notification = TbCepNotification(
        name="Test Notification",
        is_active=True,
        channel="slack",
        webhook_url="https://hooks.slack.com/test",
        rule_id=sample_rule.rule_id,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


@pytest.fixture
def sample_exec_log(session: Session, sample_rule):
    """Create a sample execution log"""
    log = TbCepExecLog(
        rule_id=sample_rule.rule_id,
        status="success",
        duration_ms=50,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@pytest.fixture
def sample_notification_log(session: Session, sample_notification):
    """Create a sample notification log"""
    log = TbCepNotificationLog(
        notification_id=sample_notification.notification_id,
        status="success",
        payload={"severity": "high"},
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


class TestChannelsStatusEndpoint:
    """Tests for /cep/channels/status endpoint"""

    def test_get_channels_status_returns_data(
        self, client, sample_notification, sample_notification_log
    ):
        """Test that channels status endpoint returns structured data"""
        response = client.get("/cep/channels/status")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "channels" in data["data"]

    def test_channels_status_structure(
        self, client, sample_notification, sample_notification_log
    ):
        """Test that channels status has correct structure"""
        response = client.get("/cep/channels/status")
        data = response.json()

        channels = data["data"]["channels"]
        if channels:
            channel = channels[0]
            assert "type" in channel
            assert "display_name" in channel
            assert "active" in channel
            assert "inactive" in channel
            assert "total_sent" in channel
            assert "total_failed" in channel
            assert "failure_rate" in channel

    def test_channels_status_includes_period(self, client):
        """Test that response includes period information"""
        response = client.get("/cep/channels/status")
        data = response.json()

        assert "period_hours" in data["data"]


class TestStatsSummaryEndpoint:
    """Tests for /cep/stats/summary endpoint"""

    def test_get_stats_summary_returns_data(self, client, sample_rule):
        """Test that stats summary endpoint returns data"""
        response = client.get("/cep/stats/summary")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "stats" in data["data"]

    def test_stats_summary_structure(self, client, sample_rule):
        """Test that stats summary has correct structure"""
        response = client.get("/cep/stats/summary")
        data = response.json()

        stats = data["data"]["stats"]
        assert "total_rules" in stats
        assert "active_rules" in stats
        assert "inactive_rules" in stats
        assert "today_execution_count" in stats
        assert "today_error_count" in stats
        assert "today_error_rate" in stats
        assert "today_avg_duration_ms" in stats
        assert "last_24h_execution_count" in stats

    def test_stats_summary_counts_active_rules(self, client, sample_rule):
        """Test that stats correctly count active rules"""
        response = client.get("/cep/stats/summary")
        data = response.json()

        stats = data["data"]["stats"]
        assert stats["total_rules"] >= 1
        assert stats["active_rules"] >= 1

    def test_stats_summary_calculates_error_rate(self, client, sample_rule, sample_exec_log):
        """Test that error rate is calculated correctly"""
        response = client.get("/cep/stats/summary")
        data = response.json()

        stats = data["data"]["stats"]
        # Sample exec log is successful, so error rate should be 0
        if stats["today_execution_count"] > 0:
            assert 0 <= stats["today_error_rate"] <= 1


class TestErrorsTimelineEndpoint:
    """Tests for /cep/errors/timeline endpoint"""

    def test_get_errors_timeline_returns_data(self, client):
        """Test that errors timeline endpoint returns data"""
        response = client.get("/cep/errors/timeline?period=24h")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "timeline" in data["data"]

    def test_errors_timeline_structure(self, client):
        """Test that errors timeline has correct structure"""
        response = client.get("/cep/errors/timeline?period=24h")
        data = response.json()

        timeline_data = data["data"]
        assert "timeline" in timeline_data
        assert "error_distribution" in timeline_data
        assert "recent_errors" in timeline_data
        assert "period" in timeline_data
        assert "total_errors" in timeline_data

    def test_errors_timeline_periods(self, client):
        """Test that different periods are supported"""
        for period in ["1h", "6h", "24h", "7d"]:
            response = client.get(f"/cep/errors/timeline?period={period}")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["period"] == period

    def test_timeline_entries_have_timestamps(self, client):
        """Test that timeline entries have timestamps"""
        response = client.get("/cep/errors/timeline?period=24h")
        data = response.json()

        timeline = data["data"]["timeline"]
        for entry in timeline:
            assert "timestamp" in entry
            assert "error_count" in entry


class TestRulesPerformanceEndpoint:
    """Tests for /cep/rules/performance endpoint"""

    def test_get_rules_performance_returns_data(self, client, sample_rule):
        """Test that rules performance endpoint returns data"""
        response = client.get("/cep/rules/performance?limit=10")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "rules" in data["data"]

    def test_rules_performance_structure(self, client, sample_rule, sample_exec_log):
        """Test that rules performance has correct structure"""
        response = client.get("/cep/rules/performance?limit=10")
        data = response.json()

        rules_data = data["data"]
        assert "rules" in rules_data
        assert "total_rules" in rules_data
        assert "period_days" in rules_data

        if rules_data["rules"]:
            rule = rules_data["rules"][0]
            assert "rule_id" in rule
            assert "rule_name" in rule
            assert "is_active" in rule
            assert "execution_count" in rule
            assert "error_count" in rule
            assert "error_rate" in rule
            assert "avg_duration_ms" in rule

    def test_rules_sorted_by_execution_count(self, client, sample_rule):
        """Test that rules are sorted by execution count descending"""
        response = client.get("/cep/rules/performance?limit=10")
        data = response.json()

        rules = data["data"]["rules"]
        if len(rules) > 1:
            # Check that first rule has higher or equal execution count than next
            for i in range(len(rules) - 1):
                assert rules[i]["execution_count"] >= rules[i + 1]["execution_count"]

    def test_rules_performance_limit_respected(self, client):
        """Test that limit parameter is respected"""
        for limit in [1, 5, 10]:
            response = client.get(f"/cep/rules/performance?limit={limit}")
            data = response.json()

            rules = data["data"]["rules"]
            assert len(rules) <= limit


class TestDashboardIntegration:
    """Integration tests for the entire dashboard"""

    def test_all_endpoints_accessible(self, client):
        """Test that all dashboard endpoints are accessible"""
        endpoints = [
            "/cep/channels/status",
            "/cep/stats/summary",
            "/cep/errors/timeline?period=24h",
            "/cep/rules/performance",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200

    def test_dashboard_data_consistency(self, client, sample_rule, sample_exec_log):
        """Test that data from different endpoints is consistent"""
        # Get stats
        stats_response = client.get("/cep/stats/summary")
        stats = stats_response.json()["data"]["stats"]

        # Get rules performance
        perf_response = client.get("/cep/rules/performance?limit=10")
        perf = perf_response.json()["data"]

        # Total rules should match
        assert stats["total_rules"] == perf["total_rules"]

    def test_error_handling_for_invalid_period(self, client):
        """Test that invalid period parameters are handled"""
        response = client.get("/cep/errors/timeline?period=invalid")
        # Should default to 24h, not fail
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
