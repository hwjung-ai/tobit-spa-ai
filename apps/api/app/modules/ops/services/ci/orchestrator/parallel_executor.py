"""
Parallel Tool Execution

P1-2: 병렬 실행 실제 구현 - 독립 도구의 동시 실행
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolExecutionTask:
    """
    Represents a single tool execution task.

    Can be executed independently or as part of parallel execution.
    """

    tool_id: str
    tool_name: str
    executor: Callable[..., Coroutine[Any, Any, Any]]
    args: tuple = ()
    kwargs: dict = None  # type: ignore
    timeout_ms: float | None = None

    # Execution tracking
    start_time: float | None = None
    end_time: float | None = None
    result: Any = None
    error: Exception | None = None
    is_completed: bool = False

    def __post_init__(self):
        """Initialize defaults."""
        if self.kwargs is None:
            self.kwargs = {}

    async def execute(self) -> Any:
        """
        Execute the task.

        Returns:
            Task result

        Raises:
            Exception: If execution fails
        """
        self.start_time = time.perf_counter()
        try:
            coro = self.executor(*self.args, **self.kwargs)
            if self.timeout_ms:
                # Convert to seconds for asyncio.wait_for
                timeout_sec = self.timeout_ms / 1000
                self.result = await asyncio.wait_for(coro, timeout=timeout_sec)
            else:
                self.result = await coro
            self.is_completed = True
            return self.result
        except asyncio.TimeoutError as e:
            self.error = e
            self.is_completed = False
            raise
        except Exception as e:
            self.error = e
            self.is_completed = False
            raise
        finally:
            self.end_time = time.perf_counter()

    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None or self.end_time is None:
            return 0
        return (self.end_time - self.start_time) * 1000

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "is_completed": self.is_completed,
            "elapsed_ms": self.get_elapsed_ms(),
            "error": str(self.error) if self.error else None,
            "has_result": self.result is not None,
        }


class ParallelExecutor:
    """
    Execute multiple independent tools in parallel.

    Uses asyncio.gather for concurrent execution with optional
    dependency management and failure handling strategies.
    """

    def __init__(
        self,
        max_concurrent: int | None = None,
        fail_fast: bool = False,
        continue_on_error: bool = True,
    ):
        """
        Initialize parallel executor.

        Args:
            max_concurrent: Maximum concurrent tasks (None = unlimited)
            fail_fast: Stop on first error
            continue_on_error: Continue execution even if some tasks fail
        """
        self.max_concurrent = max_concurrent or 10  # Default to 10
        self.fail_fast = fail_fast
        self.continue_on_error = continue_on_error
        self.tasks: list[ToolExecutionTask] = []
        self.completed_tasks: list[ToolExecutionTask] = []
        self.failed_tasks: list[ToolExecutionTask] = []

    def add_task(self, task: ToolExecutionTask) -> None:
        """Add a task to the execution queue."""
        self.tasks.append(task)

    def add_tasks(self, tasks: list[ToolExecutionTask]) -> None:
        """Add multiple tasks to the execution queue."""
        self.tasks.extend(tasks)

    async def execute(self) -> dict[str, Any]:
        """
        Execute all tasks in parallel.

        Returns:
            Dict with execution results and metadata
        """
        if not self.tasks:
            return {
                "successful": 0,
                "failed": 0,
                "total": 0,
                "results": {},
                "errors": [],
            }

        logger.info(f"Starting parallel execution of {len(self.tasks)} tasks")

        # Create coroutines for all tasks
        coroutines = [self._execute_task_with_error_handling(task) for task in self.tasks]

        # Execute with gather
        start_time = time.perf_counter()
        try:
            await asyncio.gather(*coroutines, return_exceptions=self.continue_on_error)
        except Exception as e:
            if self.fail_fast:
                logger.error(f"Parallel execution failed: {e}")
                raise
            logger.warning(f"Some parallel tasks failed: {e}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Categorize results
        for task in self.tasks:
            if task.is_completed and task.error is None:
                self.completed_tasks.append(task)
            else:
                self.failed_tasks.append(task)

        logger.info(
            f"Parallel execution completed: {len(self.completed_tasks)} succeeded, "
            f"{len(self.failed_tasks)} failed in {elapsed_ms:.0f}ms"
        )

        return self._build_execution_summary(elapsed_ms)

    async def _execute_task_with_error_handling(self, task: ToolExecutionTask) -> None:
        """
        Execute a single task with error handling.

        Args:
            task: Task to execute
        """
        try:
            await task.execute()
            logger.debug(f"Task {task.tool_id} completed successfully in {task.get_elapsed_ms():.0f}ms")
        except asyncio.TimeoutError:
            logger.warning(f"Task {task.tool_id} timeout after {task.get_elapsed_ms():.0f}ms")
        except Exception as e:
            logger.warning(f"Task {task.tool_id} failed: {e}")
            if self.fail_fast:
                raise

    def _build_execution_summary(self, total_elapsed_ms: float) -> dict[str, Any]:
        """Build execution summary."""
        results = {}
        errors = []

        for task in self.completed_tasks:
            results[task.tool_id] = {
                "result": task.result,
                "elapsed_ms": task.get_elapsed_ms(),
            }

        for task in self.failed_tasks:
            errors.append({
                "tool_id": task.tool_id,
                "tool_name": task.tool_name,
                "error": str(task.error),
                "elapsed_ms": task.get_elapsed_ms(),
            })

        return {
            "successful": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "total": len(self.tasks),
            "total_elapsed_ms": total_elapsed_ms,
            "results": results,
            "errors": errors,
        }

    def get_task_summaries(self) -> list[dict[str, Any]]:
        """Get summary of all tasks."""
        return [task.get_summary() for task in self.tasks]

    def reset(self) -> None:
        """Reset executor for reuse."""
        self.tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()


class DependencyAwareExecutor(ParallelExecutor):
    """
    Execute tools with dependency awareness.

    Schedules independent tools in parallel and dependent tools
    sequentially based on dependency graph.
    """

    def __init__(self, *args, **kwargs):
        """Initialize dependency-aware executor."""
        super().__init__(*args, **kwargs)
        self.dependencies: dict[str, list[str]] = {}  # tool_id -> [dependent_tool_ids]
        self.execution_order: list[list[ToolExecutionTask]] = []  # Groups of parallel tasks

    def add_dependency(self, tool_id: str, depends_on: list[str]) -> None:
        """
        Add dependency: tool_id depends on depends_on tools.

        Args:
            tool_id: Task that depends on others
            depends_on: List of task IDs it depends on
        """
        self.dependencies[tool_id] = depends_on

    def compute_execution_order(self) -> None:
        """
        Compute execution order respecting dependencies.

        Groups independent tasks for parallel execution.
        """
        self.execution_order = []
        executed = set()
        remaining = {task.tool_id: task for task in self.tasks}

        while remaining:
            # Find tasks with no unexecuted dependencies
            parallel_group = []
            for tool_id, task in remaining.items():
                deps = self.dependencies.get(tool_id, [])
                if all(dep in executed for dep in deps):
                    parallel_group.append(task)

            if not parallel_group:
                logger.warning("Circular dependency detected in task graph")
                # Add remaining tasks to break deadlock
                parallel_group = list(remaining.values())

            self.execution_order.append(parallel_group)
            for task in parallel_group:
                executed.add(task.tool_id)
                del remaining[task.tool_id]

    async def execute_with_dependencies(self) -> dict[str, Any]:
        """
        Execute tasks respecting dependency order.

        Returns:
            Execution results
        """
        self.compute_execution_order()

        all_results = {}
        all_errors = []
        total_start = time.perf_counter()

        for phase_num, parallel_group in enumerate(self.execution_order):
            logger.info(f"Executing parallel group {phase_num + 1}/{len(self.execution_order)} ({len(parallel_group)} tasks)")

            executor = ParallelExecutor(
                max_concurrent=self.max_concurrent,
                fail_fast=self.fail_fast,
                continue_on_error=self.continue_on_error,
            )
            executor.add_tasks(parallel_group)

            result = await executor.execute()
            all_results.update(result.get("results", {}))
            all_errors.extend(result.get("errors", []))

        total_elapsed = (time.perf_counter() - total_start) * 1000

        return {
            "successful": len(self.tasks) - len(all_errors),
            "failed": len(all_errors),
            "total": len(self.tasks),
            "total_elapsed_ms": total_elapsed,
            "results": all_results,
            "errors": all_errors,
        }
