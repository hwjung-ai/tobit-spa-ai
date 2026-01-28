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
        self._registry = get_tool_registry()

    async def execute_chain(
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """
        Execute a tool chain.

        Args:
            chain: Chain to execute
            context: Execution context

        Returns:
            ChainExecutionResult
        """
        start_time = time.time()
        logger.info(f"Executing chain {chain.chain_id} with {len(chain.steps)} steps")

        if chain.execution_mode == "parallel":
            result = await self._execute_parallel(chain, context)
        elif chain.execution_mode == "dag":
            result = await self._execute_dag(chain, context)
        else:  # sequential
            result = await self._execute_sequential(chain, context)

        result.total_execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Chain {chain.chain_id} completed: success={result.success}, "
            f"time={result.total_execution_time_ms}ms"
        )

        return result

    async def _execute_sequential(
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """Execute steps sequentially."""
        step_results: dict[str, StepResult] = {}
        failed_steps: list[str] = []

        for step in chain.steps:
            # Merge parameters with previous results
            params = self._merge_params(step, step_results)

            # Execute step
            step_result = await self._execute_step(step, params, context)
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
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """Execute steps in parallel."""
        tasks = []
        for step in chain.steps:
            params = self._merge_params(step, {})  # No previous results in parallel
            task = self._execute_step(step, params, context)
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
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """Execute steps based on DAG dependencies."""
        step_results: dict[str, StepResult] = {}
        failed_steps: list[str] = []
        completed: set[str] = set()

        # Build step map
        step_map = {s.step_id: s for s in chain.steps}

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
            for step in ready_steps:
                params = self._merge_params(step, step_results)
                task = self._execute_step(step, params, context)
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
        self, step: ToolChainStep, params: dict[str, Any], context: ToolContext
    ) -> StepResult:
        """Execute a single step."""
        start_time = time.time()

        # Get tool from registry
        try:
            tool = self._registry.get_tool(step.tool_name)
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
        """
        parts = path.split(".")
        if not parts:
            return None

        step_id = parts[0]
        if step_id not in results:
            return None

        current: Any = results[step_id]

        for part in parts[1:]:
            if current is None:
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
