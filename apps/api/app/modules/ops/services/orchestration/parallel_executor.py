"""
Parallel Executor for OPS Orchestration
Provides parallel tool execution with dependency resolution and error handling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Set

from .runner_base import (
    BaseRunner,
    OrchestrationResult,
    RunnerContext,
    RunnerStatus,
    ToolResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolTask:
    """Represents a tool execution task."""

    name: str
    params: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    timeout_seconds: float = 10.0
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ExecutionPlan:
    """Represents an execution plan with phases."""

    phases: List[List[ToolTask]]
    total_tasks: int
    estimated_time_ms: float = 0.0


class DependencyResolver:
    """Resolves dependencies between tasks."""

    @staticmethod
    def resolve(tasks: List[ToolTask]) -> ExecutionPlan:
        """
        Resolve task dependencies and create execution phases.
        Tasks in the same phase can be executed in parallel.
        """
        if not tasks:
            return ExecutionPlan(phases=[], total_tasks=0)

        # Build dependency graph
        task_map = {t.name: t for t in tasks}
        in_degree = {t.name: 0 for t in tasks}
        dependents = {t.name: [] for t in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_map:
                    in_degree[task.name] += 1
                    dependents[dep].append(task.name)

        # Topological sort with phases
        phases = []
        remaining = set(in_degree.keys())
        current_in_degree = in_degree.copy()

        while remaining:
            # Find tasks with no remaining dependencies
            phase = [
                task_map[name] for name in remaining if current_in_degree[name] == 0
            ]

            if not phase:
                # Circular dependency detected
                remaining_tasks = [task_map[name] for name in remaining]
                logger.warning(
                    f"Circular dependency detected among tasks: "
                    f"{[t.name for t in remaining_tasks]}"
                )
                # Add remaining tasks to last phase as fallback
                if phases:
                    phases[-1].extend(remaining_tasks)
                else:
                    phases.append(remaining_tasks)
                break

            # Sort by priority (higher priority first)
            phase.sort(key=lambda t: -t.priority)
            phases.append(phase)

            # Update in-degrees for next phase
            phase_names = {t.name for t in phase}
            remaining -= phase_names
            for name in phase_names:
                for dependent in dependents[name]:
                    current_in_degree[dependent] -= 1

        return ExecutionPlan(
            phases=phases,
            total_tasks=len(tasks),
            estimated_time_ms=sum(
                max(t.timeout_seconds for t in phase) * 1000 for phase in phases
            ),
        )


class ParallelExecutor(BaseRunner):
    """
    Executes tools in parallel with dependency resolution.
    """

    def __init__(
        self,
        context: RunnerContext,
        tool_executor: Callable[[str, Dict[str, Any]], Awaitable[ToolResult]],
        max_concurrent: int = 5,
    ):
        super().__init__(context)
        self.tool_executor = tool_executor
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self) -> OrchestrationResult:
        """Execute tools based on the plan."""
        self.start()

        try:
            # Build execution plan from context
            tasks = self._build_tasks()
            plan = DependencyResolver.resolve(tasks)

            logger.info(
                f"[{self.context.trace_id}] Execution plan: "
                f"{plan.total_tasks} tasks in {len(plan.phases)} phases"
            )

            # Execute phases
            for phase_idx, phase in enumerate(plan.phases):
                if self.status != RunnerStatus.RUNNING:
                    break

                logger.debug(
                    f"[{self.context.trace_id}] Executing phase {phase_idx + 1}/{len(plan.phases)} "
                    f"with {len(phase)} tasks"
                )

                # Execute phase tasks in parallel
                phase_results = await self._execute_phase(phase)

                # Check for critical failures
                if self._has_critical_failure(phase_results):
                    return self.complete(
                        success=False, error="Critical tool execution failed"
                    )

            return self.complete(success=True)

        except asyncio.TimeoutError:
            return self.timeout()
        except Exception as e:
            logger.exception(f"[{self.context.trace_id}] Runner error: {e}")
            return self.complete(success=False, error=str(e))

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a single tool with timeout and retry."""
        start_time = time.time()

        async with self._semaphore:
            for attempt in range(3):  # Max 3 retries
                try:
                    result = await asyncio.wait_for(
                        self.tool_executor(tool_name, params), timeout=10.0
                    )
                    result.execution_time_ms = (time.time() - start_time) * 1000
                    result.tool_name = tool_name
                    return result

                except asyncio.TimeoutError:
                    logger.warning(
                        f"[{self.context.trace_id}] Tool {tool_name} timeout "
                        f"(attempt {attempt + 1}/3)"
                    )
                    if attempt == 2:
                        return ToolResult(
                            success=False,
                            tool_name=tool_name,
                            error="Tool timeout after 10s",
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    await asyncio.sleep(0.5 * (attempt + 1))

                except Exception as e:
                    logger.error(
                        f"[{self.context.trace_id}] Tool {tool_name} error: {e}"
                    )
                    return ToolResult(
                        success=False,
                        tool_name=tool_name,
                        error=str(e),
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )

        return ToolResult(
            success=False,
            tool_name=tool_name,
            error="Unknown error",
        )

    def _build_tasks(self) -> List[ToolTask]:
        """Build task list from context."""
        # Default tasks based on mode
        mode = self.context.mode
        tasks = []

        if mode in ["all", "config"]:
            tasks.append(
                ToolTask(
                    name="ci_lookup",
                    params={"query": self.context.query},
                    priority=10,
                )
            )

        if mode in ["all", "metric"]:
            tasks.append(
                ToolTask(
                    name="metric_query",
                    params={"query": self.context.query},
                    priority=5,
                    dependencies=["ci_lookup"]
                    if "config" in mode or mode == "all"
                    else [],
                )
            )

        if mode in ["all", "hist"]:
            tasks.append(
                ToolTask(
                    name="history_query",
                    params={"query": self.context.query},
                    priority=5,
                    dependencies=["ci_lookup"]
                    if "config" in mode or mode == "all"
                    else [],
                )
            )

        if mode in ["all", "graph"]:
            tasks.append(
                ToolTask(
                    name="graph_query",
                    params={"query": self.context.query},
                    priority=3,
                    dependencies=["ci_lookup"]
                    if "config" in mode or mode == "all"
                    else [],
                )
            )

        return tasks

    async def _execute_phase(self, phase: List[ToolTask]) -> List[ToolResult]:
        """Execute a phase of tasks in parallel."""
        tasks = [self.execute_tool(task.name, task.params) for task in phase]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to ToolResult
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(
                    ToolResult(
                        success=False,
                        tool_name=phase[i].name,
                        error=str(result),
                    )
                )
                self.record_result(processed[-1])
            else:
                self.record_result(result)
                processed.append(result)

        return processed

    def _has_critical_failure(self, results: List[ToolResult]) -> bool:
        """Check if any critical tool failed."""
        critical_tools = {"ci_lookup", "document_search"}
        for result in results:
            if result.tool_name in critical_tools and not result.success:
                return True
        return False


class DependencyAwareExecutor(ParallelExecutor):
    """
    Enhanced parallel executor with advanced dependency handling.
    """

    def __init__(
        self,
        context: RunnerContext,
        tool_executor: Callable[[str, Dict[str, Any]], Awaitable[ToolResult]],
        max_concurrent: int = 5,
        fail_fast: bool = False,
    ):
        super().__init__(context, tool_executor, max_concurrent)
        self.fail_fast = fail_fast
        self._completed_tasks: Set[str] = set()
        self._failed_tasks: Set[str] = set()

    async def execute(self) -> OrchestrationResult:
        """Execute with dependency awareness."""
        self.start()

        try:
            tasks = self._build_tasks()
            plan = DependencyResolver.resolve(tasks)

            for phase_idx, phase in enumerate(plan.phases):
                # Skip tasks that depend on failed tasks
                executable = [
                    t
                    for t in phase
                    if not any(d in self._failed_tasks for d in t.dependencies)
                ]

                if not executable:
                    logger.warning(
                        f"[{self.context.trace_id}] Phase {phase_idx + 1} "
                        f"skipped: all tasks depend on failed tasks"
                    )
                    continue

                results = await self._execute_phase(executable)

                # Update task status
                for task, result in zip(executable, results):
                    if result.success:
                        self._completed_tasks.add(task.name)
                    else:
                        self._failed_tasks.add(task.name)

                # Check fail-fast condition
                if self.fail_fast and self._failed_tasks:
                    return self.complete(
                        success=False,
                        error=f"Fail-fast triggered: {self._failed_tasks}",
                    )

            return self.complete(success=len(self._failed_tasks) == 0)

        except asyncio.TimeoutError:
            return self.timeout()
        except Exception as e:
            logger.exception(f"[{self.context.trace_id}] Runner error: {e}")
            return self.complete(success=False, error=str(e))


def create_parallel_executor(
    context: RunnerContext,
    tool_executor: Callable[[str, Dict[str, Any]], Awaitable[ToolResult]],
    **kwargs,
) -> ParallelExecutor:
    """Factory function to create a parallel executor."""
    return ParallelExecutor(context, tool_executor, **kwargs)


def create_dependency_aware_executor(
    context: RunnerContext,
    tool_executor: Callable[[str, Dict[str, Any]], Awaitable[ToolResult]],
    **kwargs,
) -> DependencyAwareExecutor:
    """Factory function to create a dependency-aware executor."""
    return DependencyAwareExecutor(context, tool_executor, **kwargs)
