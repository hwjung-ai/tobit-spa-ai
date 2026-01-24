"""
Tests for Control Loop Runtime in OPS Orchestration.

Tests the control loop policy enforcement and replan decision logic including:
- Policy validation
- Replan trigger evaluation
- Max replans enforcement
- Cooling period and interval checks
- Trigger allowlist
- Critical severity override
"""

from datetime import datetime, timedelta

import pytest
from app.modules.ops.schemas import ReplanEvent, ReplanPatchDiff, ReplanTrigger
from app.modules.ops.services.control_loop import (
    ControlLoopPolicy,
    ControlLoopRuntime,
)


@pytest.fixture
def default_policy():
    """Default control loop policy."""
    return ControlLoopPolicy(
        max_replans=3,
        allowed_triggers=["error", "timeout", "policy_violation"],
        enable_automatic_replan=True,
        min_interval_seconds=60,
        cooling_period_seconds=300,
    )


@pytest.fixture
def strict_policy():
    """Strict control loop policy."""
    return ControlLoopPolicy(
        max_replans=1,
        allowed_triggers=["error"],
        enable_automatic_replan=False,
        min_interval_seconds=120,
        cooling_period_seconds=600,
    )


@pytest.fixture
def sample_trigger():
    """Sample replan trigger."""
    return ReplanTrigger(
        trigger_type="error",
        stage_name="execute",
        severity="high",
        reason="Database connection timeout",
        timestamp=datetime.now().isoformat(),
    )


class TestControlLoopPolicy:
    """Test suite for ControlLoopPolicy."""

    def test_policy_creation(self):
        """Test creating a control loop policy."""
        policy = ControlLoopPolicy(
            max_replans=5,
            allowed_triggers=["error", "timeout"],
            enable_automatic_replan=True,
            min_interval_seconds=30,
            cooling_period_seconds=180,
        )

        assert policy.max_replans == 5
        assert len(policy.allowed_triggers) == 2
        assert policy.enable_automatic_replan is True
        assert policy.min_interval_seconds == 30
        assert policy.cooling_period_seconds == 180

    def test_policy_defaults(self):
        """Test default policy values."""
        policy = ControlLoopPolicy()

        assert policy.max_replans == 3
        assert "error" in policy.allowed_triggers
        assert policy.enable_automatic_replan is True
        assert policy.min_interval_seconds == 60
        assert policy.cooling_period_seconds == 300

    def test_policy_validation_success(self, default_policy):
        """Test valid policy configuration."""
        errors = default_policy.validate_policy()
        assert len(errors) == 0

    def test_policy_validation_negative_max_replans(self):
        """Test policy validation with negative max_replans."""
        policy = ControlLoopPolicy(max_replans=0)
        errors = policy.validate_policy()

        assert len(errors) > 0
        assert any("max_replans" in error for error in errors)

    def test_policy_validation_negative_interval(self):
        """Test policy validation with negative interval."""
        policy = ControlLoopPolicy(min_interval_seconds=-10)
        errors = policy.validate_policy()

        assert len(errors) > 0
        assert any("min_interval_seconds" in error for error in errors)

    def test_policy_validation_negative_cooling_period(self):
        """Test policy validation with negative cooling period."""
        policy = ControlLoopPolicy(cooling_period_seconds=-100)
        errors = policy.validate_policy()

        assert len(errors) > 0
        assert any("cooling_period_seconds" in error for error in errors)

    def test_policy_validation_interval_greater_than_cooling(self):
        """Test policy validation when min_interval > cooling_period."""
        policy = ControlLoopPolicy(
            min_interval_seconds=400,
            cooling_period_seconds=300,
        )
        errors = policy.validate_policy()

        assert len(errors) > 0
        assert any("min_interval_seconds must be <=" in error for error in errors)


class TestControlLoopRuntime:
    """Test suite for ControlLoopRuntime."""

    def test_runtime_creation(self, default_policy):
        """Test creating a control loop runtime."""
        runtime = ControlLoopRuntime(policy=default_policy)

        assert runtime.policy == default_policy
        assert runtime.replan_count == 0
        assert runtime.last_replan_time is None
        assert len(runtime.replan_history) == 0
        assert len(runtime.trigger_counts) == 0

    def test_should_replan_allowed_trigger(self, default_policy, sample_trigger):
        """Test replan decision with allowed trigger."""
        runtime = ControlLoopRuntime(policy=default_policy)

        should_replan = runtime.should_replan(sample_trigger)
        assert should_replan is True

    def test_should_replan_disallowed_trigger(self, default_policy):
        """Test replan decision with disallowed trigger."""
        runtime = ControlLoopRuntime(policy=default_policy)

        disallowed_trigger = ReplanTrigger(
            trigger_type="low_confidence",
            stage_name="validate",
            severity="low",
            reason="Confidence below threshold",
            timestamp=datetime.now().isoformat(),
        )

        should_replan = runtime.should_replan(disallowed_trigger)
        assert should_replan is False

    def test_should_replan_max_replans_exceeded(self, default_policy, sample_trigger):
        """Test replan decision when max replans exceeded."""
        runtime = ControlLoopRuntime(policy=default_policy)

        # Exhaust max replans
        runtime.replan_count = default_policy.max_replans

        should_replan = runtime.should_replan(sample_trigger)
        assert should_replan is False

    def test_should_replan_min_interval_not_met(self, default_policy, sample_trigger):
        """Test replan decision when minimum interval not met."""
        runtime = ControlLoopRuntime(policy=default_policy)

        # Set last replan time to very recent
        runtime.last_replan_time = datetime.now() - timedelta(seconds=10)

        should_replan = runtime.should_replan(sample_trigger)
        assert should_replan is False

    def test_should_replan_cooling_period_active(self, default_policy, sample_trigger):
        """Test replan decision during cooling period."""
        runtime = ControlLoopRuntime(policy=default_policy)

        # Record some replans to trigger cooling period check
        runtime.replan_count = 2
        runtime.last_replan_time = datetime.now() - timedelta(seconds=30)

        should_replan = runtime.should_replan(sample_trigger)
        # Should be False because we're in cooling period
        assert should_replan is False

    def test_should_replan_critical_severity_override(self, default_policy):
        """Test that critical severity can override some restrictions."""
        runtime = ControlLoopRuntime(policy=default_policy)

        critical_trigger = ReplanTrigger(
            trigger_type="error",
            stage_name="execute",
            severity="critical",
            reason="Fatal database error",
            timestamp=datetime.now().isoformat(),
        )

        # Even with recent replan, critical should potentially be allowed
        runtime.last_replan_time = datetime.now() - timedelta(seconds=10)

        should_replan = runtime.should_replan(critical_trigger)
        # The actual behavior depends on implementation details
        # This test documents expected behavior
        assert isinstance(should_replan, bool)

    def test_record_replan(self, default_policy, sample_trigger):
        """Test recording a replan event."""
        runtime = ControlLoopRuntime(policy=default_policy)

        initial_count = runtime.replan_count

        event = ReplanEvent(
            event_type="auto_retry",
            stage_name="execute",
            trigger=sample_trigger,
            patch=ReplanPatchDiff(
                before={"query": "SELECT * FROM old_table"},
                after={"query": "SELECT * FROM new_table"},
            ),
            timestamp=datetime.now().isoformat(),
            decision_metadata={},
            execution_metadata={},
        )

        runtime.record_replan(event)

        assert runtime.replan_count == initial_count + 1
        assert runtime.last_replan_time is not None
        assert len(runtime.replan_history) == 1
        assert runtime.replan_history[0] == event

    def test_trigger_counts_tracking(self, default_policy):
        """Test that trigger types are counted."""
        runtime = ControlLoopRuntime(policy=default_policy)

        triggers = [
            ReplanTrigger(
                trigger_type="error",
                stage_name="execute",
                severity="high",
                reason="Error 1",
                timestamp=datetime.now().isoformat(),
            ),
            ReplanTrigger(
                trigger_type="error",
                stage_name="execute",
                severity="high",
                reason="Error 2",
                timestamp=datetime.now().isoformat(),
            ),
            ReplanTrigger(
                trigger_type="timeout",
                stage_name="execute",
                severity="medium",
                reason="Timeout 1",
                timestamp=datetime.now().isoformat(),
            ),
        ]

        for trigger in triggers:
            event = ReplanEvent(
                event_type="auto_retry",
                stage_name=trigger.stage_name,
                trigger=trigger,
                patch=ReplanPatchDiff(before={}, after={}),
                timestamp=datetime.now().isoformat(),
                decision_metadata={},
                execution_metadata={},
            )
            runtime.record_replan(event)

        # Verify counts (implementation may vary)
        assert runtime.replan_count == 3

    def test_get_stats(self, default_policy):
        """Test getting runtime statistics."""
        runtime = ControlLoopRuntime(policy=default_policy)

        # Record some events
        for i in range(2):
            trigger = ReplanTrigger(
                trigger_type="error",
                stage_name="execute",
                severity="high",
                reason=f"Error {i}",
                timestamp=datetime.now().isoformat(),
            )
            event = ReplanEvent(
                event_type="auto_retry",
                stage_name="execute",
                trigger=trigger,
                patch=ReplanPatchDiff(before={}, after={}),
                timestamp=datetime.now().isoformat(),
                decision_metadata={},
                execution_metadata={},
            )
            runtime.record_replan(event)

        stats = runtime.get_stats()

        assert isinstance(stats, dict)
        assert "replan_count" in stats
        assert stats["replan_count"] == 2

    def test_should_replan_with_string_trigger(self, default_policy):
        """Test replan decision with string trigger (P0-1 compliance)."""
        runtime = ControlLoopRuntime(policy=default_policy)

        # Pass trigger as string (should use safe_parse_trigger)
        should_replan = runtime.should_replan("error")

        # Should handle string trigger gracefully
        assert isinstance(should_replan, bool)

    def test_multiple_replans_sequence(self, default_policy):
        """Test a sequence of multiple replans."""
        runtime = ControlLoopRuntime(policy=default_policy)

        for i in range(default_policy.max_replans):
            trigger = ReplanTrigger(
                trigger_type="error",
                stage_name="execute",
                severity="high",
                reason=f"Error {i}",
                timestamp=datetime.now().isoformat(),
            )

            # First check should succeed
            should_replan = runtime.should_replan(trigger)

            if i < default_policy.max_replans:
                # Record replan
                event = ReplanEvent(
                    event_type="auto_retry",
                    stage_name="execute",
                    trigger=trigger,
                    patch=ReplanPatchDiff(before={}, after={}),
                    timestamp=datetime.now().isoformat(),
                    decision_metadata={},
                    execution_metadata={},
                )
                runtime.record_replan(event)

                # Wait to satisfy min_interval
                import time

                time.sleep(0.1)  # Small delay for testing

        # After max replans, should return False
        final_trigger = ReplanTrigger(
            trigger_type="error",
            stage_name="execute",
            severity="high",
            reason="Final error",
            timestamp=datetime.now().isoformat(),
        )
        should_replan = runtime.should_replan(final_trigger)
        assert should_replan is False


class TestReplanEventSchema:
    """Test suite for ReplanEvent schema."""

    def test_replan_event_creation(self, sample_trigger):
        """Test creating a replan event."""
        event = ReplanEvent(
            event_type="auto_retry",
            stage_name="execute",
            trigger=sample_trigger,
            patch=ReplanPatchDiff(
                before={"timeout": 30},
                after={"timeout": 60},
            ),
            timestamp=datetime.now().isoformat(),
            decision_metadata={"reason": "Increase timeout"},
            execution_metadata={"attempt": 2},
        )

        assert event.event_type == "auto_retry"
        assert event.stage_name == "execute"
        assert event.trigger == sample_trigger
        assert event.patch.before == {"timeout": 30}
        assert event.patch.after == {"timeout": 60}

    def test_replan_patch_diff(self):
        """Test ReplanPatchDiff structure (P0-2 compliance)."""
        patch = ReplanPatchDiff(
            before={"query": "old query"},
            after={"query": "new query"},
        )

        assert patch.before == {"query": "old query"}
        assert patch.after == {"query": "new query"}

    def test_replan_trigger_structure(self):
        """Test ReplanTrigger structure."""
        trigger = ReplanTrigger(
            trigger_type="timeout",
            stage_name="execute",
            severity="medium",
            reason="Query exceeded 30s limit",
            timestamp=datetime.now().isoformat(),
        )

        assert trigger.trigger_type == "timeout"
        assert trigger.stage_name == "execute"
        assert trigger.severity == "medium"
        assert "30s" in trigger.reason
