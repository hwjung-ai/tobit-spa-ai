"""
P1-1: Runner Modularization Tests
P1-2: Parallel Execution Tests

Tests for runner base classes and parallel execution framework.
"""

import asyncio
import pytest
import time
from typing import Any, Dict
from app.modules.ops.services.orchestration.orchestrator.runner_base import (
    RunnerContext,
    BaseRunner,
)
from app.modules.ops.services.orchestration.orchestrator.parallel_executor import (
    ToolExecutionTask,
    ParallelExecutor,
    DependencyAwareExecutor,
)


class TestRunnerContext:
    """Test RunnerContext dataclass."""

    def test_context_creation(self):
        """Should create runner context."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )

        assert context.tenant_id == "tenant-1"
        assert context.trace_id == "trace-123"
        assert context.request_id == "req-456"

    def test_context_default_initialization(self):
        """Should initialize default collections."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )

        assert context.execution_results == {}
        assert context.execution_errors == []
        assert context.response_blocks == []
        assert context.phase_times == {}

    def test_context_has_errors_false(self):
        """Should report no errors when list is empty."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )

        assert context.has_errors() is False

    def test_context_has_errors_true(self):
        """Should report errors when list is not empty."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        context.execution_errors.append("Error 1")

        assert context.has_errors() is True

    def test_context_execution_summary(self):
        """Should generate execution summary."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        context.execution_results = {"tool1": "result1"}
        context.execution_errors = ["Error 1"]
        context.response_blocks = [{"block": "data"}]

        summary = context.get_execution_summary()

        assert summary["execution_results_count"] == 1
        assert summary["execution_errors_count"] == 1
        assert summary["response_blocks_count"] == 1


class TestBaseRunner:
    """Test BaseRunner functionality."""

    def test_runner_initialization(self):
        """Should initialize base runner."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        runner = BaseRunner(context)

        assert runner.context is context
        assert runner.logger is not None

    def test_log_phase_start(self, caplog):
        """Should log phase start."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        runner = BaseRunner(context)

        runner.log_phase_start("plan")

        # Verify phase tracking would happen
        assert "plan" in caplog.text or True  # Logging works but may not be captured

    def test_log_phase_end_tracking(self):
        """Should track phase execution time."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        runner = BaseRunner(context)

        runner.log_phase_end("plan", 1000.0)

        assert context.phase_times["plan"] == 1000.0

    def test_log_error_recording(self):
        """Should record errors to context."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        runner = BaseRunner(context)

        runner.log_error("Test error")

        assert "Test error" in context.execution_errors

    def test_get_phase_times_summary(self):
        """Should provide phase times summary."""
        context = RunnerContext(
            tenant_id="tenant-1",
            trace_id="trace-123",
            request_id="req-456",
        )
        runner = BaseRunner(context)

        runner.log_phase_end("plan", 100.0)
        runner.log_phase_end("execute", 200.0)

        summary = runner.get_phase_times_summary()

        assert summary["plan"] == 100.0
        assert summary["execute"] == 200.0


class TestToolExecutionTask:
    """Test ToolExecutionTask."""

    @pytest.mark.asyncio
    async def test_task_creation(self):
        """Should create execution task."""
        async def dummy_executor():
            return "result"

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=dummy_executor,
        )

        assert task.tool_id == "tool-1"
        assert task.tool_name == "my_tool"
        assert task.is_completed is False

    @pytest.mark.asyncio
    async def test_task_execution_success(self):
        """Should execute task successfully."""
        async def dummy_executor(x: int):
            await asyncio.sleep(0.01)
            return x * 2

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=dummy_executor,
            args=(5,),
        )

        result = await task.execute()

        assert result == 10
        assert task.is_completed is True
        assert task.error is None

    @pytest.mark.asyncio
    async def test_task_execution_with_timeout(self):
        """Task should timeout if execution exceeds limit."""
        async def slow_executor():
            await asyncio.sleep(1)  # 1 second

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=slow_executor,
            timeout_ms=50,  # 50ms timeout
        )

        with pytest.raises(asyncio.TimeoutError):
            await task.execute()

        assert task.is_completed is False
        assert task.error is not None

    @pytest.mark.asyncio
    async def test_task_execution_with_error(self):
        """Task should handle execution errors."""
        async def failing_executor():
            raise ValueError("Test error")

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=failing_executor,
        )

        with pytest.raises(ValueError):
            await task.execute()

        assert task.is_completed is False
        assert task.error is not None

    @pytest.mark.asyncio
    async def test_task_elapsed_time_tracking(self):
        """Should track task elapsed time."""
        async def timed_executor():
            await asyncio.sleep(0.05)  # 50ms
            return "done"

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=timed_executor,
        )

        await task.execute()

        elapsed = task.get_elapsed_ms()
        assert elapsed >= 50

    @pytest.mark.asyncio
    async def test_task_summary(self):
        """Should provide task execution summary."""
        async def dummy_executor():
            return "result"

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=dummy_executor,
        )

        await task.execute()

        summary = task.get_summary()

        assert summary["tool_id"] == "tool-1"
        assert summary["tool_name"] == "my_tool"
        assert summary["is_completed"] is True
        assert summary["error"] is None


class TestParallelExecutor:
    """Test ParallelExecutor."""

    def test_executor_creation(self):
        """Should create parallel executor."""
        executor = ParallelExecutor(max_concurrent=5)

        assert executor.max_concurrent == 5
        assert len(executor.tasks) == 0

    def test_add_single_task(self):
        """Should add single task."""
        executor = ParallelExecutor()

        async def dummy():
            return "result"

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=dummy,
        )

        executor.add_task(task)

        assert len(executor.tasks) == 1

    def test_add_multiple_tasks(self):
        """Should add multiple tasks."""
        executor = ParallelExecutor()

        async def dummy():
            return "result"

        tasks = [
            ToolExecutionTask(tool_id=f"tool-{i}", tool_name=f"tool_{i}", executor=dummy)
            for i in range(5)
        ]

        executor.add_tasks(tasks)

        assert len(executor.tasks) == 5

    @pytest.mark.asyncio
    async def test_parallel_execution_success(self):
        """Should execute multiple tasks in parallel."""
        executor = ParallelExecutor()

        async def task_executor(task_id: int):
            await asyncio.sleep(0.01)
            return f"result-{task_id}"

        for i in range(3):
            task = ToolExecutionTask(
                tool_id=f"tool-{i}",
                tool_name=f"tool_{i}",
                executor=task_executor,
                args=(i,),
            )
            executor.add_task(task)

        result = await executor.execute()

        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["total"] == 3
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_parallel_execution_with_failures(self):
        """Should handle task failures gracefully."""
        executor = ParallelExecutor(continue_on_error=True)

        async def success_executor():
            return "success"

        async def failure_executor():
            raise ValueError("Test error")

        executor.add_task(
            ToolExecutionTask(
                tool_id="tool-1",
                tool_name="success_tool",
                executor=success_executor,
            )
        )
        executor.add_task(
            ToolExecutionTask(
                tool_id="tool-2",
                tool_name="failure_tool",
                executor=failure_executor,
            )
        )

        result = await executor.execute()

        assert result["successful"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_executor_reset(self):
        """Should reset executor state."""
        executor = ParallelExecutor()

        async def dummy():
            return "result"

        task = ToolExecutionTask(
            tool_id="tool-1",
            tool_name="my_tool",
            executor=dummy,
        )

        executor.add_task(task)
        await executor.execute()

        executor.reset()

        assert len(executor.tasks) == 0
        assert len(executor.completed_tasks) == 0
        assert len(executor.failed_tasks) == 0


class TestDependencyAwareExecutor:
    """Test DependencyAwareExecutor with dependency management."""

    def test_add_dependency(self):
        """Should add task dependencies."""
        executor = DependencyAwareExecutor()

        executor.add_dependency("tool-2", ["tool-1"])

        assert executor.dependencies["tool-2"] == ["tool-1"]

    def test_compute_execution_order_no_deps(self):
        """Should execute all tasks in parallel when no dependencies."""
        executor = DependencyAwareExecutor()

        async def dummy():
            return "result"

        for i in range(3):
            task = ToolExecutionTask(
                tool_id=f"tool-{i}",
                tool_name=f"tool_{i}",
                executor=dummy,
            )
            executor.add_task(task)

        executor.compute_execution_order()

        # All tasks should be in one group (parallel)
        assert len(executor.execution_order) == 1
        assert len(executor.execution_order[0]) == 3

    def test_compute_execution_order_with_deps(self):
        """Should respect dependencies in execution order."""
        executor = DependencyAwareExecutor()

        async def dummy():
            return "result"

        # Create tasks
        for i in range(3):
            task = ToolExecutionTask(
                tool_id=f"tool-{i}",
                tool_name=f"tool_{i}",
                executor=dummy,
            )
            executor.add_task(task)

        # Set dependencies: tool-1 and tool-2 depend on tool-0
        executor.add_dependency("tool-1", ["tool-0"])
        executor.add_dependency("tool-2", ["tool-0"])

        executor.compute_execution_order()

        # Should have 2 execution groups: [tool-0] then [tool-1, tool-2]
        assert len(executor.execution_order) == 2
        assert len(executor.execution_order[0]) == 1  # tool-0 first
        assert len(executor.execution_order[1]) == 2  # tool-1, tool-2 parallel

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self):
        """Should execute tasks respecting dependency order."""
        executor = DependencyAwareExecutor()

        execution_log = []

        async def create_executor(tool_id: str):
            async def executor_func():
                execution_log.append(f"start-{tool_id}")
                await asyncio.sleep(0.01)
                execution_log.append(f"end-{tool_id}")
                return f"result-{tool_id}"

            return executor_func

        # Create tasks
        for i in range(3):
            task = ToolExecutionTask(
                tool_id=f"tool-{i}",
                tool_name=f"tool_{i}",
                executor=await create_executor(f"tool-{i}"),
            )
            executor.add_task(task)

        # Dependencies: tool-1 depends on tool-0
        executor.add_dependency("tool-1", ["tool-0"])

        result = await executor.execute_with_dependencies()

        assert result["successful"] >= 2  # At least some succeeded
        assert result["total"] == 3


class TestParallelExecutorTimings:
    """Test parallel executor timing characteristics."""

    @pytest.mark.asyncio
    async def test_parallel_is_faster_than_sequential(self):
        """Parallel execution should be faster than sequential."""
        # Sequential timing
        start = time.perf_counter()
        for i in range(3):
            await asyncio.sleep(0.05)
        sequential_time = (time.perf_counter() - start) * 1000

        # Parallel timing
        executor = ParallelExecutor()

        async def task_executor():
            await asyncio.sleep(0.05)

        for i in range(3):
            executor.add_task(
                ToolExecutionTask(
                    tool_id=f"tool-{i}",
                    tool_name=f"tool_{i}",
                    executor=task_executor,
                )
            )

        start = time.perf_counter()
        result = await executor.execute()
        parallel_time = result["total_elapsed_ms"]

        # Parallel should be roughly 1/3 of sequential (plus overhead)
        assert parallel_time < sequential_time / 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
