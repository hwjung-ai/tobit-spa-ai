from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from core.logging import get_logger

from app.modules.ops.services.ci.tools.base import ToolType
from app.modules.ops.services.ci.tools.executor import ToolExecutor

logger = get_logger(__name__)


@dataclass
class CompositionStep:
    tool_type: ToolType
    operation: str
    params_transform: Callable[[Dict[str, Any]], Dict[str, Any]]
    error_handling: str = "fail_fast"


class CompositionPipeline:
    def __init__(self, steps: List[CompositionStep]):
        self.steps = steps
        self.results: List[Dict[str, Any]] = []
        self.logger = logger

    async def execute(self, executor: ToolExecutor, initial_params: Dict[str, Any]) -> Dict[str, Any]:
        current_result = initial_params
        for step in self.steps:
            try:
                params = step.params_transform(current_result)
                result = await executor.execute_async(step.tool_type, step.operation, **params)
                self.results.append({"step": step.tool_type.value, "result": result})
                current_result = result
            except Exception as exc:
                self._handle_step_error(step, exc)
                if step.error_handling == "fail_fast":
                    raise
        return self._aggregate_results()

    def _handle_step_error(self, step: CompositionStep, error: Exception):
        if step.error_handling == "fail_fast":
            self.logger.error(f"Composition step failed: {step.tool_type.value}/{step.operation}", extra={"error": str(error)})
        elif step.error_handling == "skip":
            self.logger.warning(f"Skipping {step.tool_type.value}/{step.operation}: {error}")
        elif step.error_handling == "fallback":
            self.logger.info(f"Fallback mode for {step.tool_type.value}/{step.operation}: {error}")

    def _aggregate_results(self) -> Dict[str, Any]:
        return {
            "primary": self.results[0]["result"] if self.results else None,
            "enriched": {r["step"]: r["result"] for r in self.results[1:]},
            "execution_trace": [r["step"] for r in self.results],
        }
