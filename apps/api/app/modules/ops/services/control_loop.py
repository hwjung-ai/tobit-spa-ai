from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.logging import get_request_context

from app.modules.ops.schemas import (
    ReplanEvent,
    ReplanPatchDiff,
    ReplanTrigger,
    safe_parse_trigger,
)

logger = logging.getLogger(__name__)


class ControlLoopPolicy:
    """Policy configuration for the control loop"""
    def __init__(
        self,
        max_replans: int = 3,
        allowed_triggers: List[str] = None,
        enable_automatic_replan: bool = True,
        min_interval_seconds: int = 60,
        cooling_period_seconds: int = 300,
    ):
        self.max_replans = max_replans
        self.allowed_triggers = allowed_triggers or ["error", "timeout", "policy_violation"]
        self.enable_automatic_replan = enable_automatic_replan
        self.min_interval_seconds = min_interval_seconds
        self.cooling_period_seconds = cooling_period_seconds

    def validate_policy(self) -> List[str]:
        """Validate policy configuration and return list of errors"""
        errors = []

        if self.max_replans <= 0:
            errors.append("max_replans must be positive")

        if self.min_interval_seconds <= 0:
            errors.append("min_interval_seconds must be positive")

        if self.cooling_period_seconds <= 0:
            errors.append("cooling_period_seconds must be positive")

        if self.min_interval_seconds > self.cooling_period_seconds:
            errors.append("min_interval_seconds must be <= cooling_period_seconds")

        return errors


class ControlLoopRuntime:
    """Runtime state for the control loop"""
    def __init__(self, policy: ControlLoopPolicy):
        self.policy = policy
        self.replan_count = 0
        self.last_replan_time: Optional[datetime] = None
        self.replan_history: List[ReplanEvent] = []
        self.trigger_counts: Dict[str, int] = {}

    def should_replan(self, trigger: ReplanTrigger | str) -> bool:
        """
        Check if a replan should be triggered (P0-3: Trigger normalization)
        """
        # Normalize trigger if string
        if isinstance(trigger, str):
            try:
                trigger = safe_parse_trigger(trigger)
            except ValueError:
                logger.warning(f"Failed to parse trigger: {trigger}")
                return False

        # Check if trigger type is allowed
        if trigger.trigger_type not in self.policy.allowed_triggers:
            logger.info(f"Trigger type {trigger.trigger_type} not allowed by policy")
            return False

        # Check max replans limit
        if self.replan_count >= self.policy.max_replans:
            logger.info(f"Maximum replan count ({self.policy.max_replans}) reached")
            return False

        # Check minimum interval
        if self.last_replan_time:
            time_since_last = (datetime.now() - self.last_replan_time).total_seconds()
            if time_since_last < self.policy.min_interval_seconds:
                logger.info(f"Minimum interval not met: {time_since_last:.1f}s < {self.policy.min_interval_seconds}s")
                return False

        # Check cooling period
        if self.last_replan_time:
            time_since_last = (datetime.now() - self.last_replan_time).total_seconds()
            if time_since_last < self.policy.cooling_period_seconds:
                logger.warning(f"Replan within cooling period: {time_since_last:.1f}s < {self.policy.cooling_period_seconds}s")
                # Allow if critical severity
                if trigger.severity == "critical":
                    logger.info("Critical severity override: allowing replan during cooling period")
                    return True
                else:
                    return False

        return True

    def record_replan(self, event: ReplanEvent) -> None:
        """Record a replan event"""
        self.replan_count += 1
        self.last_replan_time = datetime.now()
        self.replan_history.append(event)

        # Update trigger counts
        trigger_type = event.trigger.trigger_type
        self.trigger_counts[trigger_type] = self.trigger_counts.get(trigger_type, 0) + 1

        logger.info(f"Recorded replan #{self.replan_count}: {trigger_type} - {event.trigger.reason}")

    def get_stats(self) -> Dict[str, Any]:
        """Get control loop statistics"""
        return {
            "replan_count": self.replan_count,
            "max_replans": self.policy.max_replans,
            "last_replan_time": self.last_replan_time.isoformat() if self.last_replan_time else None,
            "replan_history_count": len(self.replan_history),
            "trigger_counts": self.trigger_counts.copy(),
            "policy": {
                "max_replans": self.policy.max_replans,
                "allowed_triggers": self.policy.allowed_triggers,
                "enable_automatic_replan": self.policy.enable_automatic_replan,
                "min_interval_seconds": self.policy.min_interval_seconds,
                "cooling_period_seconds": self.policy.cooling_period_seconds,
            }
        }


class ControlLoopManager:
    """Main control loop manager"""
    def __init__(self, policy: ControlLoopPolicy = None):
        self.policy = policy or ControlLoopPolicy()
        self.runtime = ControlLoopRuntime(self.policy)
        self._validate_policy()

    def _validate_policy(self) -> None:
        """Validate the policy on initialization"""
        errors = self.policy.validate_policy()
        if errors:
            raise ValueError(f"Invalid control loop policy: {', '.join(errors)}")

    def evaluate_replan_request(self, trigger: ReplanTrigger | str, patch_diff: ReplanPatchDiff) -> bool:
        """
        Evaluate a replan request and return decision
        """
        # Get trace info for logging
        context = get_request_context()
        trace_id = context.get("trace_id")

        if isinstance(trigger, str):
            trigger = safe_parse_trigger(trigger)

        # Log the evaluation
        logger.info(f"Evaluating replan request for {trigger.trigger_type} at stage {trigger.stage_name}")
        logger.info(f"Trigger reason: {trigger.reason}")
        logger.info(f"Current replan count: {self.runtime.replan_count}/{self.policy.max_replans}")

        # Check if we should replan
        should_replan = self.runtime.should_replan(trigger)

        # Create event
        event = ReplanEvent(
            event_type="replan_decision",
            stage_name=trigger.stage_name,  # snake_case (P0-3)
            trigger=trigger,
            patch=patch_diff,
            timestamp=datetime.now().isoformat(),
            decision_metadata={
                "trace_id": trace_id,
                "should_replan": should_replan,
                "evaluation_time": time.time(),
            }
        )

        # Record decision
        if should_replan:
            self.runtime.record_replan(event)
            logger.info("Replan request approved")
            return True
        else:
            logger.info("Replan request denied")
            return False

    def get_replan_history(self) -> List[ReplanEvent]:
        """Get the history of replan events"""
        return self.runtime.replan_history.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get control loop statistics"""
        return self.runtime.get_stats()

    def reset(self) -> None:
        """Reset the control loop state"""
        self.runtime = ControlLoopRuntime(self.policy)
        logger.info("Control loop state reset")

    def check_and_handle_cooling_period(self, trigger_type: str) -> bool:
        """Check if cooling period allows the trigger"""
        if not self.runtime.last_replan_time:
            return True

        time_since_last = (datetime.now() - self.runtime.last_replan_time).total_seconds()
        if time_since_last < self.policy.cooling_period_seconds:
            logger.warning(f"Trigger {trigger_type} within cooling period: {time_since_last:.1f}s")
            return False
        return True


# Factory function for creating control loop instances
def create_control_loop(policy: Dict[str, Any] = None) -> ControlLoopManager:
    """Create a control loop manager with optional custom policy"""
    if policy:
        return ControlLoopManager(policy=ControlLoopPolicy(**policy))
    return ControlLoopManager()


# Default control loop instance
default_control_loop = create_control_loop()


# Convenience functions
def evaluate_replan(trigger: ReplanTrigger | str, patch_diff: ReplanPatchDiff) -> bool:
    """Evaluate a replan request using the default control loop"""
    return default_control_loop.evaluate_replan_request(trigger, patch_diff)


def get_replan_stats() -> Dict[str, Any]:
    """Get stats from the default control loop"""
    return default_control_loop.get_stats()


def reset_control_loop() -> None:
    """Reset the default control loop"""
    default_control_loop.reset()