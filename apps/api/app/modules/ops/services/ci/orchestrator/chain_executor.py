"""
Tool Chain Executor for Generic Orchestration System.

This module implements sequential, parallel, and DAG-based tool chain execution
with data piping between tools.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from core.logging import get_logger
from app.modules.ops.services.ci.tools.base import (
    get_tool_registry,
    ToolContext,
    ToolResult,
)

logger = get_logger(__name__)


class ToolChainStep(BaseModel):
    """Single step in a tool chain."""

    step_id: str = Field(..., description="Unique step identifier")
    tool_name: str = Field(..., description="Tool to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Dependencies (step_ids)"
    )
    output_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map previous results to parameters (e.g., {'ci_id': 'step1.data.records[0].ci_id'})",
    )
    timeout_ms: int = Field(default=30000, description="Timeout in milliseconds")
    retry_count: int = Field(default=0, description="Number of retries")


class ToolChain(BaseModel):
    """Tool execution chain."""

    chain_id: str = Field(..., description="Unique chain identifier")
    steps: list[ToolChainStep] = Field(..., description="Chain steps")
    execution_mode: str = Field(
        default="sequential", description="sequential, parallel, or dag"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Result of a single step execution."""

    step_id: str
    success: bool
    data: Any = None
    error: str | None = None
    execution_time_ms: int = 0


class ChainExecutionResult(BaseModel):
    """Result of chain execution."""

    chain_id: str
    success: bool
    step_results: dict[str, StepResult] = Field(default_factory=dict)
    final_output: Any = None
    total_execution_time_ms: int = 0
    failed_steps: list[str] = Field(default_factory=list)


class ToolChainExecutor:
    """
    Executes tool chains in sequential, parallel, or DAG mode.

    Supports:
    - Sequential execution with data piping
    - Parallel execution for independent tools
    - DAG-based execution with dependencies
    """

    def __init__(self):
        """Initialize the chain executor."""
        # Don't cache registry in __init__ - get it fresh each time to handle lazy initialization
        self._registry = None

    def _get_registry(self):
        """Get the tool registry, creating it if necessary."""
        if self._registry is None:
            self._registry = get_tool_registry()
        return self._registry

    async def execute_chain(
        self, chain: ToolChain, context: ToolContext, execution_plan_trace: dict[str, Any] | None = None
    ) -> ChainExecutionResult:
        """
        Execute a tool chain.

        Args:
            chain: Chain to execute
            context: Execution context
            execution_plan_trace: Optional execution plan metadata for trace integration

        Returns:
            ChainExecutionResult
        """
        start_time = time.time()
        logger.info(f"Executing chain {chain.chain_id} with {len(chain.steps)} steps")

        if chain.execution_mode == "parallel":
            result = await self._execute_parallel(chain, context, execution_plan_trace)
        elif chain.execution_mode == "dag":
            result = await self._execute_dag(chain, context, execution_plan_trace)
        else:  # sequential
            result = await self._execute_sequential(chain, context, execution_plan_trace)

        result.total_execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Chain {chain.chain_id} completed: success={result.success}, "
            f"time={result.total_execution_time_ms}ms"
        )

        return result

    async def _execute_sequential(
        self, chain: ToolChain, context: ToolContext, execution_plan_trace: dict[str, Any] | None = None
    ) -> ChainExecutionResult:
        """Execute steps sequentially."""
        step_results: dict[str, StepResult] = {}
        failed_steps: list[str] = []

        for group_index, step in enumerate(chain.steps):
            # Merge parameters with previous results
            params = self._merge_params(step, step_results)

            # Execute step with orchestration metadata
            step_result = await self._execute_step(
                step, params, context,
                execution_plan_trace=execution_plan_trace,
                group_index=group_index,
                execution_order=group_index
            )
            step_results[step.step_id] = step_result

            if not step_result.success:
                failed_steps.append(step.step_id)
                # Stop on failure in sequential mode
                break

        # Get final output from last successful step
        final_output = None
        for step in reversed(chain.steps):
            if step.step_id in step_results and step_results[step.step_id].success:
                final_output = step_results[step.step_id].data
                break

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_output=final_output,
            failed_steps=failed_steps,
        )

    async def _execute_parallel(
        self, chain: ToolChain, context: ToolContext, execution_plan_trace: dict[str, Any] | None = None
    ) -> ChainExecutionResult:
        """Execute steps in parallel."""
        tasks = []
        for group_index, step in enumerate(chain.steps):
            params = self._merge_params(step, {})  # No previous results in parallel
            task = self._execute_step(
                step, params, context,
                execution_plan_trace=execution_plan_trace,
                group_index=0,  # All in same group for parallel
                execution_order=group_index
            )
            tasks.append((step.step_id, task))

        # Run all tasks in parallel
        results = await asyncio.gather(
            *[t[1] for t in tasks], return_exceptions=True
        )

        step_results: dict[str, StepResult] = {}
        failed_steps: list[str] = []

        for i, (step_id, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                step_results[step_id] = StepResult(
                    step_id=step_id,
                    success=False,
                    error=str(result),
                )
                failed_steps.append(step_id)
            else:
                step_results[step_id] = result
                if not result.success:
                    failed_steps.append(step_id)

        # Merge all successful results as final output
        final_output = [
            step_results[step.step_id].data
            for step in chain.steps
            if step_results.get(step.step_id) and step_results[step.step_id].success
        ]

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_output=final_output,
            failed_steps=failed_steps,
        )

    async def _execute_dag(
        self, chain: ToolChain, context: ToolContext, execution_plan_trace: dict[str, Any] | None = None
    ) -> ChainExecutionResult:
        """Execute steps based on DAG dependencies."""
        step_results: dict[str, StepResult] = {}
        failed_steps: list[str] = []
        completed: set[str] = set()

        # Build step map
        step_map = {s.step_id: s for s in chain.steps}
        group_index = 0

        while len(completed) < len(chain.steps):
            # Find ready steps (all dependencies completed)
            ready_steps = []
            for step in chain.steps:
                if step.step_id in completed:
                    continue
                if all(dep in completed for dep in step.depends_on):
                    ready_steps.append(step)

            if not ready_steps:
                # Deadlock or all done
                if len(completed) < len(chain.steps):
                    logger.error("DAG deadlock detected")
                break

            # Execute ready steps in parallel
            tasks = []
            for execution_order, step in enumerate(ready_steps):
                params = self._merge_params(step, step_results)
                task = self._execute_step(
                    step, params, context,
                    execution_plan_trace=execution_plan_trace,
                    group_index=group_index,
                    execution_order=execution_order
                )
                tasks.append((step.step_id, task))

            results = await asyncio.gather(
                *[t[1] for t in tasks], return_exceptions=True
            )

            for i, (step_id, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=str(result),
                    )
                    failed_steps.append(step_id)
                else:
                    step_results[step_id] = result
                    if not result.success:
                        failed_steps.append(step_id)
                completed.add(step_id)

            group_index += 1

        # Final output from last step
        final_output = None
        if chain.steps:
            last_step = chain.steps[-1]
            if last_step.step_id in step_results:
                final_output = step_results[last_step.step_id].data

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_output=final_output,
            failed_steps=failed_steps,
        )

    async def _execute_step(
        self, step: ToolChainStep, params: dict[str, Any], context: ToolContext,
        execution_plan_trace: dict[str, Any] | None = None,
        group_index: int = 0,
        execution_order: int = 0
    ) -> StepResult:
        """Execute a single step.

        Args:
            step: Tool chain step to execute
            params: Merged parameters for the step
            context: Execution context
            execution_plan_trace: Optional execution plan metadata for trace integration
            group_index: Index of execution group (for DAG execution)
            execution_order: Order within execution group
        """
        start_time = time.time()

        # Get tool from registry
        try:
            tool = self._get_registry().get_tool(step.tool_name)
        except ValueError:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=f"Tool not found: {step.tool_name}",
            )

        # Execute with timeout
        try:
            result: ToolResult = await asyncio.wait_for(
                tool.safe_execute(context, params),
                timeout=step.timeout_ms / 1000,
            )

            # Add orchestration metadata to result if available
            if execution_plan_trace and isinstance(result.data, dict):
                orchestration_metadata = {
                    "group_index": group_index,
                    "execution_order": execution_order,
                    "tool_id": step.step_id,
                    "depends_on": step.depends_on,
                    "output_mapping": step.output_mapping,
                }
                if "orchestration" not in result.data:
                    result.data["orchestration"] = orchestration_metadata

            return StepResult(
                step_id=step.step_id,
                success=result.success,
                data=result.data,
                error=result.error,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except asyncio.TimeoutError:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=f"Timeout after {step.timeout_ms}ms",
                execution_time_ms=step.timeout_ms,
            )
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _merge_params(
        self, step: ToolChainStep, prev_results: dict[str, StepResult]
    ) -> dict[str, Any]:
        """
        Merge step parameters with mapped values from previous results.

        Example output_mapping:
        - {"ci_id": "step1.data.records[0].ci_id"}
        - {"keywords": "step1.data.keywords"}
        """
        params = dict(step.parameters)

        for param_name, path in step.output_mapping.items():
            value = self._resolve_path(path, prev_results)
            if value is not None:
                params[param_name] = value

        return params

    def _resolve_path(
        self, path: str, results: dict[str, StepResult]
    ) -> Any:
        """
        Resolve a path expression to a value.

        Example: "step1.data.records[0].ci_id"
        Special syntax: "step1.data.rows.*.ci_id" extracts ci_id from all rows

        Note: path format is "step_id.field.subfield" where step_id is the key in results dict
        If results[step_id] is a StepResult, we automatically access its .data attribute.
        """
        parts = path.split(".")
        if not parts:
            return None

        step_id = parts[0]
        if step_id not in results:
            return None

        # Get the step result
        step_result = results[step_id]

        # If it's a StepResult, extract the data field first
        # The path should be "step_id.data.xxx" or just "step_id" for the whole data
        if hasattr(step_result, 'data'):
            current = step_result.data
            # If path has more than just step_id, process remaining parts
            # (skipping 'data' if it's the next part since we already extracted it)
            start_idx = 1
            if len(parts) > 1 and parts[1] == 'data':
                start_idx = 2  # Skip 'data' since we already extracted .data
            elif len(parts) == 1:
                return current  # Just return the whole data
        else:
            current = step_result
            start_idx = 1

        for i, part in enumerate(parts[start_idx:], start_idx):
            if current is None:
                return None

            # Handle wildcard (e.g., rows.*.ci_id) to extract from all array elements
            if part == "*":
                # Get remaining path after wildcard
                remaining_path = ".".join(parts[i+1:]) if i < len(parts) - 1 else None

                if isinstance(current, list):
                    result_list = []
                    for item in current:
                        if remaining_path:
                            # Recursively resolve remaining path for each item
                            value = self._resolve_value_from_object(item, remaining_path)
                            if value is not None:
                                result_list.append(value)
                        else:
                            result_list.append(item)
                    return result_list if result_list else None
                else:
                    return None

            # Handle array index (e.g., records[0])
            match = re.match(r"(\w+)\[(\d+)\]", part)
            if match:
                attr, index = match.groups()
                if hasattr(current, attr):
                    current = getattr(current, attr)
                elif isinstance(current, dict):
                    current = current.get(attr)
                else:
                    return None

                if isinstance(current, list) and int(index) < len(current):
                    current = current[int(index)]
                else:
                    return None
            else:
                # Regular attribute access
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

        return current

    def _resolve_value_from_object(self, obj: Any, path: str) -> Any:
        """
        Resolve a path within a single object.
        Used internally for wildcard path resolution.
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if current is None:
                return None

            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current


# Global executor instance
_global_chain_executor: ToolChainExecutor | None = None


def get_chain_executor() -> ToolChainExecutor:
    """Get the global chain executor instance."""
    global _global_chain_executor
    if _global_chain_executor is None:
        _global_chain_executor = ToolChainExecutor()
    return _global_chain_executor


async def execute_tool_chain(
    chain: ToolChain, context: ToolContext
) -> ChainExecutionResult:
    """
    Execute a tool chain using the global executor.

    Convenience function for chain execution.
    """
    executor = get_chain_executor()
    return await executor.execute_chain(chain, context)
