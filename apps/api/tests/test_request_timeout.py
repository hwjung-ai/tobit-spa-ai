"""
P0-5: Request-wide Timeout Tests

Tests for request-level timeout enforcement and budget management.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from app.modules.ops.services.orchestration.tools.request_timeout import (
    TimeoutBudget,
    TimeoutPhase,
    RequestTimeoutManager,
    RequestTimeoutError,
    get_request_timeout_manager,
    reset_request_timeout_manager,
)


class TestTimeoutBudget:
    """Test TimeoutBudget configuration and tracking."""

    def test_budget_creation(self):
        """Should create timeout budget with default values."""
        budget = TimeoutBudget(total_timeout_ms=120000)

        assert budget.total_timeout_ms == 120000
        assert budget.plan_timeout_ms == 30000
        assert budget.execute_timeout_ms == 60000
        assert budget.compose_timeout_ms == 20000

    def test_budget_custom_phase_timeouts(self):
        """Should accept custom phase timeouts."""
        budget = TimeoutBudget(
            total_timeout_ms=180000,
            plan_timeout_ms=45000,
            execute_timeout_ms=90000,
            compose_timeout_ms=30000,
        )

        assert budget.plan_timeout_ms == 45000
        assert budget.execute_timeout_ms == 90000
        assert budget.compose_timeout_ms == 30000

    def test_elapsed_ms_calculation(self):
        """Should track elapsed time correctly."""
        budget = TimeoutBudget(total_timeout_ms=120000)
        start = budget.start_time

        # Manually set start time to 1 second ago
        budget.start_time = datetime.now() - timedelta(seconds=1)

        elapsed = budget.get_elapsed_ms()
        assert 900 <= elapsed <= 1100  # 1000ms ± 100ms tolerance

    def test_remaining_ms_calculation(self):
        """Should calculate remaining time correctly."""
        budget = TimeoutBudget(total_timeout_ms=120000)
        budget.start_time = datetime.now() - timedelta(seconds=1)

        remaining = budget.get_remaining_ms()
        assert 118900 <= remaining <= 119100  # ~119000ms ± 100ms

    def test_is_exhausted_false(self):
        """Should report not exhausted when time remains."""
        budget = TimeoutBudget(total_timeout_ms=120000)
        assert budget.is_exhausted() is False

    def test_is_exhausted_true(self):
        """Should report exhausted when timeout exceeded."""
        budget = TimeoutBudget(total_timeout_ms=100)  # 100ms
        budget.start_time = datetime.now() - timedelta(seconds=2)  # 2 seconds ago

        assert budget.is_exhausted() is True

    def test_check_phase_timeout_valid(self):
        """Valid phase execution should not raise."""
        budget = TimeoutBudget(total_timeout_ms=120000, plan_timeout_ms=30000)

        # 10s is less than 30s phase timeout
        budget.check_phase_timeout(TimeoutPhase.PLAN, 10000)  # Should not raise

    def test_check_phase_timeout_exceeded(self):
        """Exceeded phase timeout should raise."""
        budget = TimeoutBudget(total_timeout_ms=120000, plan_timeout_ms=30000)

        with pytest.raises(RequestTimeoutError) as exc_info:
            budget.check_phase_timeout(TimeoutPhase.PLAN, 35000)  # 35s > 30s

        assert exc_info.value.phase == "plan"
        assert exc_info.value.elapsed_ms == 35000
        assert exc_info.value.timeout_ms == 30000

    def test_check_total_timeout_valid(self):
        """Valid total time should not raise."""
        budget = TimeoutBudget(total_timeout_ms=120000)
        budget.start_time = datetime.now() - timedelta(seconds=1)

        budget.check_total_timeout()  # Should not raise

    def test_check_total_timeout_exceeded(self):
        """Exceeded total timeout should raise."""
        budget = TimeoutBudget(total_timeout_ms=100)  # 100ms
        budget.start_time = datetime.now() - timedelta(seconds=2)  # 2 seconds ago

        with pytest.raises(RequestTimeoutError) as exc_info:
            budget.check_total_timeout()

        assert exc_info.value.phase == "total"
        assert exc_info.value.elapsed_ms > 100

    def test_record_phase_time(self):
        """Should record phase execution times."""
        budget = TimeoutBudget(total_timeout_ms=120000)

        budget.record_phase_time(TimeoutPhase.PLAN, 15000)
        budget.record_phase_time(TimeoutPhase.EXECUTE, 45000)

        assert budget.phase_times["plan"] == 15000
        assert budget.phase_times["execute"] == 45000

    def test_get_remaining_for_phase(self):
        """Should calculate remaining time for phase."""
        budget = TimeoutBudget(
            total_timeout_ms=120000,
            plan_timeout_ms=30000,
            execute_timeout_ms=60000,
        )

        remaining = budget.get_remaining_for_phase(TimeoutPhase.PLAN)
        # Should be close to 30000ms (phase timeout)
        assert 29900 <= remaining <= 30100

    def test_get_remaining_for_phase_respects_total(self):
        """Phase timeout should be limited by total timeout."""
        budget = TimeoutBudget(
            total_timeout_ms=10000,  # Very short total
            plan_timeout_ms=30000,  # Longer than total
        )

        remaining = budget.get_remaining_for_phase(TimeoutPhase.PLAN)
        # Should be limited to total remaining time
        assert remaining <= 10000

    def test_budget_to_dict(self):
        """Should serialize budget to dict."""
        budget = TimeoutBudget(total_timeout_ms=120000)
        budget.record_phase_time(TimeoutPhase.PLAN, 15000)

        budget_dict = budget.to_dict()

        assert budget_dict["total_timeout_ms"] == 120000
        assert budget_dict["plan_timeout_ms"] == 30000
        assert "elapsed_ms" in budget_dict
        assert "remaining_ms" in budget_dict
        assert budget_dict["phase_times"]["plan"] == 15000


class TestRequestTimeoutManager:
    """Test RequestTimeoutManager."""

    def test_manager_creation(self):
        """Should create manager with default timeout."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        assert manager.budget.total_timeout_ms == 120000
        assert manager.budget.get_elapsed_ms() >= 0

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self):
        """Successful execution within timeout should complete."""
        manager = RequestTimeoutManager(timeout_ms=60000)

        async def quick_task():
            await asyncio.sleep(0.01)  # 10ms
            return "success"

        result = await manager.execute_with_timeout(TimeoutPhase.EXECUTE, quick_task())
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_exceeds(self):
        """Execution exceeding timeout should raise."""
        manager = RequestTimeoutManager(timeout_ms=100)  # 100ms
        manager.budget.execute_timeout_ms = 50  # 50ms phase timeout

        async def slow_task():
            await asyncio.sleep(1)  # 1 second
            return "done"

        with pytest.raises(RequestTimeoutError):
            await manager.execute_with_timeout(TimeoutPhase.EXECUTE, slow_task())

    @pytest.mark.asyncio
    async def test_execute_with_timeout_tracks_time(self):
        """Should record phase execution time."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        async def task():
            await asyncio.sleep(0.05)  # 50ms
            return "done"

        await manager.execute_with_timeout(TimeoutPhase.PLAN, task())

        assert "plan" in manager.budget.phase_times
        assert manager.budget.phase_times["plan"] >= 50

    def test_execute_sync_with_timeout_success(self):
        """Synchronous execution should complete successfully."""
        manager = RequestTimeoutManager(timeout_ms=60000)

        def sync_task(x, y):
            time.sleep(0.01)
            return x + y

        result = manager.execute_sync_with_timeout(TimeoutPhase.PLAN, sync_task, 5, 3)
        assert result == 8

    def test_execute_sync_with_timeout_tracks_time(self):
        """Should record sync execution time."""
        manager = RequestTimeoutManager(timeout_ms=60000)

        def sync_task():
            time.sleep(0.05)  # 50ms
            return "done"

        manager.execute_sync_with_timeout(TimeoutPhase.PLAN, sync_task)

        assert "plan" in manager.budget.phase_times
        assert manager.budget.phase_times["plan"] >= 50

    @pytest.mark.asyncio
    async def test_phase_timeout_context_manager(self):
        """Context manager should track phase time."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        async with manager.phase_timeout(TimeoutPhase.PLAN):
            await asyncio.sleep(0.01)

        assert "plan" in manager.budget.phase_times
        assert manager.budget.phase_times["plan"] >= 10

    @pytest.mark.asyncio
    async def test_multiple_phases_in_sequence(self):
        """Should track multiple phases sequentially."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        # Plan phase
        async with manager.phase_timeout(TimeoutPhase.PLAN):
            await asyncio.sleep(0.01)

        # Execute phase
        async with manager.phase_timeout(TimeoutPhase.EXECUTE):
            await asyncio.sleep(0.02)

        # Compose phase
        async with manager.phase_timeout(TimeoutPhase.COMPOSE):
            await asyncio.sleep(0.01)

        assert "plan" in manager.budget.phase_times
        assert "execute" in manager.budget.phase_times
        assert "compose" in manager.budget.phase_times

    def test_get_timeout_summary(self):
        """Should provide timeout status summary."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        summary = manager.get_timeout_summary()

        assert "elapsed_ms" in summary
        assert "remaining_ms" in summary
        assert "is_exhausted" in summary
        assert "phase_times" in summary
        assert "budget" in summary

    @pytest.mark.asyncio
    async def test_request_timeout_error_message(self):
        """RequestTimeoutError should provide useful message."""
        manager = RequestTimeoutManager(timeout_ms=100)
        manager.budget.execute_timeout_ms = 50

        async def slow_task():
            await asyncio.sleep(1)

        try:
            await manager.execute_with_timeout(TimeoutPhase.EXECUTE, slow_task())
        except RequestTimeoutError as e:
            assert "execute" in str(e)
            assert "50" in str(e)  # Timeout value
            assert "Request timeout" in str(e)

    @pytest.mark.asyncio
    async def test_execute_after_budget_exhausted(self):
        """Should reject execution after total budget exhausted."""
        manager = RequestTimeoutManager(timeout_ms=100)  # 100ms total
        manager.budget.start_time = datetime.now() - timedelta(seconds=2)

        async def task():
            await asyncio.sleep(0.01)

        with pytest.raises(RequestTimeoutError) as exc_info:
            await manager.execute_with_timeout(TimeoutPhase.PLAN, task())

        # Should fail due to total timeout (checked before execution)
        assert exc_info.value.phase == "total"
        assert exc_info.value.elapsed_ms > 100

    def test_global_timeout_manager_singleton(self):
        """Global manager should be singleton."""
        reset_request_timeout_manager()

        manager1 = get_request_timeout_manager(120000)
        manager2 = get_request_timeout_manager(120000)

        assert manager1 is manager2

    def test_reset_global_timeout_manager(self):
        """Should reset global manager."""
        reset_request_timeout_manager()

        manager1 = get_request_timeout_manager(120000)
        reset_request_timeout_manager()
        manager2 = get_request_timeout_manager(60000)

        assert manager1 is not manager2
        assert manager2.budget.total_timeout_ms == 60000


class TestTimeoutIntegration:
    """Integration tests for timeout management."""

    @pytest.mark.asyncio
    async def test_full_orchestration_timeout_flow(self):
        """Test complete orchestration timeout flow."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        # Plan phase
        async with manager.phase_timeout(TimeoutPhase.PLAN):
            await asyncio.sleep(0.01)

        # Execute phase with multiple tool calls
        async def tool_call():
            await asyncio.sleep(0.02)
            return {"result": "data"}

        async with manager.phase_timeout(TimeoutPhase.EXECUTE):
            result = await manager.execute_with_timeout(
                TimeoutPhase.EXECUTE, tool_call()
            )
            assert result == {"result": "data"}

        # Compose phase
        async with manager.phase_timeout(TimeoutPhase.COMPOSE):
            await asyncio.sleep(0.01)

        summary = manager.get_timeout_summary()
        assert not summary["is_exhausted"]
        assert len(summary["phase_times"]) == 3

    @pytest.mark.asyncio
    async def test_timeout_with_parallel_tasks(self):
        """Should handle parallel task execution."""
        manager = RequestTimeoutManager(timeout_ms=120000)

        async def task(duration_ms):
            await asyncio.sleep(duration_ms / 1000)
            return f"task_{duration_ms}"

        async with manager.phase_timeout(TimeoutPhase.EXECUTE):
            # Run parallel tasks within phase timeout
            results = await asyncio.gather(
                manager.execute_with_timeout(
                    TimeoutPhase.EXECUTE, task(10)
                ),
                manager.execute_with_timeout(
                    TimeoutPhase.EXECUTE, task(20)
                ),
                manager.execute_with_timeout(
                    TimeoutPhase.EXECUTE, task(15)
                ),
            )

            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_timeout_with_fallback_strategy(self):
        """Should support fallback execution on timeout."""
        manager = RequestTimeoutManager(timeout_ms=100)
        manager.budget.execute_timeout_ms = 50

        async def main_task():
            await asyncio.sleep(0.5)  # Will timeout
            return "main"

        async def fallback_task():
            return "fallback"

        try:
            result = await manager.execute_with_timeout(
                TimeoutPhase.EXECUTE, main_task()
            )
            assert False, "Should have timed out"
        except RequestTimeoutError:
            # Fallback
            result = await manager.execute_with_timeout(
                TimeoutPhase.COMPOSE, fallback_task()
            )
            assert result == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
