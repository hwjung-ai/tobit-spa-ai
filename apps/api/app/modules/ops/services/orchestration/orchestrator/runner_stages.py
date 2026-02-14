"""
Stage Orchestration Module - Phase 8

Extracts stage-based orchestration logic from runner.py including:
- Stage-based execution orchestration (_run_async_with_stages)
- Stage input building (_build_stage_input)
- Stage asset distribution (_distribute_stage_assets)
- Orchestration trace building (_build_orchestration_trace)
- Individual stage execution methods
"""

from __future__ import annotations

import uuid
from time import perf_counter
from typing import Any, Dict, List

from core.logging import get_logger, get_request_context

from app.modules.ops.schemas import (
    StageDiagnostics,
    StageInput,
    StageOutput,
)
from app.modules.ops.services.orchestration.blocks import Block, text_block
from app.modules.ops.services.orchestration.planner.plan_schema import (
    PlanOutput,
    PlanOutputKind,
)

MODULE_LOGGER = get_logger(__name__)


class StageOrchestrator:
    """
    Manages stage-based orchestration of the runner pipeline.

    Responsible for:
    - Coordinating 5-stage execution (route, validate, execute, compose, present)
    - Building stage inputs with proper asset context
    - Recording stage diagnostics and references
    - Building orchestration trace for Inspector
    - Distributing assets to stages
    """

    def __init__(self, tenant_id: str, logger: Any = None):
        """
        Initialize StageOrchestrator.

        Args:
            tenant_id: Current tenant ID
            logger: Logger instance
        """
        self.tenant_id = tenant_id
        self.logger = logger or MODULE_LOGGER

    async def run_with_stages(
        self,
        plan_output: PlanOutput,
        execution_fn,
        present_fn,
    ) -> tuple[List[Block], str, Dict[str, Any]]:
        """
        Run orchestration with explicit stages.

        Args:
            plan_output: Plan output from planner
            execution_fn: Async function to execute main logic
            present_fn: Async function to present results

        Returns:
            Tuple of (blocks, answer, full_result)
        """
        stage_inputs: List[Dict[str, Any]] = []
        stage_outputs: List[Dict[str, Any]] = []
        stages: List[Dict[str, Any]] = []

        # Initialize trace_id early
        context = get_request_context()
        trace_id = context.get("trace_id")
        if not trace_id or trace_id == "-":
            trace_id = context.get("request_id") or str(uuid.uuid4())
        parent_trace_id = context.get("parent_trace_id")
        if parent_trace_id == "-":
            parent_trace_id = None

        self.logger.info(
            "ci.runner.stages.start",
            extra={
                "plan_kind": plan_output.kind.value,
                "stages": ["route_plan", "validate", "execute", "compose", "present"],
            },
        )

        def record_stage(
            stage_name: str, stage_input: StageInput, stage_output: StageOutput
        ) -> None:
            """Record stage execution with diagnostics."""
            stage_input_payload = stage_input.model_dump()
            stage_output_payload = stage_output.model_dump()
            stage_inputs.append(stage_input_payload)
            stage_outputs.append(stage_output_payload)
            stages.append(
                {
                    "name": stage_name,
                    "input": stage_input_payload,
                    "output": stage_output_payload.get("result"),
                    "duration_ms": stage_output_payload.get("duration_ms", 0),
                    "status": stage_output_payload.get("diagnostics", {}).get(
                        "status", "ok"
                    ),
                }
            )
            self.logger.info(
                f"Stage recorded: {stage_name}, status={stage_output_payload.get('diagnostics', {}).get('status', 'ok')}, duration={stage_output_payload.get('duration_ms', 0)}ms"
            )

        try:
            # route_plan stage
            route_start = perf_counter()
            route_result = {
                "route": plan_output.kind.value,
                "plan_output": plan_output.model_dump(),
            }
            route_output = StageOutput(
                stage="route_plan",
                result=route_result,
                diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
                references=[],
                duration_ms=int((perf_counter() - route_start) * 1000),
            )
            route_input = self._build_stage_input(
                "route_plan", plan_output, stage_assets={}
            )
            record_stage("route_plan", route_input, route_output)

            # Route to appropriate path (DIRECT, REJECT, or PLAN)
            if plan_output.kind == PlanOutputKind.DIRECT:
                return await self._execute_direct_path(
                    plan_output, present_fn, stages, stage_inputs, stage_outputs,
                    record_stage, route_output
                )
            elif plan_output.kind == PlanOutputKind.REJECT:
                return await self._execute_reject_path(
                    plan_output, stages, stage_inputs, stage_outputs,
                    record_stage, route_output
                )
            else:
                return await self._execute_plan_path(
                    plan_output, execution_fn, present_fn, stages,
                    stage_inputs, stage_outputs, record_stage, route_output, trace_id
                )

        except Exception as e:
            self.logger.error(f"Stage orchestration error: {e}", exc_info=True)
            raise

    async def _execute_direct_path(
        self, plan_output, present_fn, stages, stage_inputs, stage_outputs,
        record_stage, route_output
    ):
        """Execute DIRECT path (direct answer)."""
        # Validate, execute, compose stages are skipped
        validate_output = StageOutput(
            stage="validate",
            result={"skipped": True, "reason": "direct_answer"},
            diagnostics=StageDiagnostics(
                status="warning", warnings=["skipped"], errors=[]
            ),
            references=[],
            duration_ms=0,
        )
        validate_input = self._build_stage_input("validate", plan_output)
        record_stage("validate", validate_input, validate_output)

        execute_output = StageOutput(
            stage="execute",
            result={"skipped": True, "reason": "direct_answer"},
            diagnostics=StageDiagnostics(
                status="warning", warnings=["skipped"], errors=[]
            ),
            references=[],
            duration_ms=0,
        )
        execute_input = self._build_stage_input("execute", plan_output)
        record_stage("execute", execute_input, execute_output)

        compose_output = StageOutput(
            stage="compose",
            result={"skipped": True, "reason": "direct_answer"},
            diagnostics=StageDiagnostics(
                status="warning", warnings=["skipped"], errors=[]
            ),
            references=[],
            duration_ms=0,
        )
        compose_input = self._build_stage_input("compose", plan_output)
        record_stage("compose", compose_input, compose_output)

        # Present stage executes
        present_start = perf_counter()
        present_result = await present_fn(plan_output)
        blocks = present_result.get("blocks", [])
        answer = present_result.get("summary", "Direct answer")

        present_output = StageOutput(
            stage="present",
            result={"summary": answer, "blocks": blocks},
            diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
            references=present_result.get("references", []),
            duration_ms=int((perf_counter() - present_start) * 1000),
        )
        present_input = self._build_stage_input("present", plan_output)
        record_stage("present", present_input, present_output)

        return blocks, answer, {
            "stages": stages,
            "stage_inputs": stage_inputs,
            "stage_outputs": stage_outputs,
        }

    async def _execute_reject_path(
        self, plan_output, stages, stage_inputs, stage_outputs,
        record_stage, route_output
    ):
        """Execute REJECT path (query rejected)."""
        # All stages are skipped
        for stage_name in ["validate", "execute", "compose"]:
            output = StageOutput(
                stage=stage_name,
                result={"skipped": True, "reason": "rejected"},
                diagnostics=StageDiagnostics(
                    status="warning", warnings=["skipped"], errors=[]
                ),
                references=[],
                duration_ms=0,
            )
            input_stage = self._build_stage_input(stage_name, plan_output)
            record_stage(stage_name, input_stage, output)

        # Present stage with rejection message
        reject_reason = (
            plan_output.reject_payload.reason
            if plan_output.reject_payload
            else "Query rejected"
        )
        blocks = [text_block(f"Query rejected: {reject_reason}")]
        answer = f"Query rejected: {reject_reason}"

        present_output = StageOutput(
            stage="present",
            result={"summary": answer, "blocks": blocks},
            diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
            references=[],
            duration_ms=0,
        )
        present_input = self._build_stage_input("present", plan_output)
        record_stage("present", present_input, present_output)

        return blocks, answer, {
            "stages": stages,
            "stage_inputs": stage_inputs,
            "stage_outputs": stage_outputs,
        }

    async def _execute_plan_path(
        self, plan_output, execution_fn, present_fn, stages,
        stage_inputs, stage_outputs, record_stage, route_output, trace_id
    ):
        """Execute PLAN path (full orchestration)."""
        # Validate stage
        validate_start = perf_counter()
        validate_result = {
            "is_valid": True,
        }
        validate_output = StageOutput(
            stage="validate",
            result=validate_result,
            diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
            references=[],
            duration_ms=int((perf_counter() - validate_start) * 1000),
        )
        validate_input = self._build_stage_input("validate", plan_output)
        record_stage("validate", validate_input, validate_output)

        # Execute stage
        execute_start = perf_counter()
        execute_result = await execution_fn(plan_output)
        execute_output = StageOutput(
            stage="execute",
            result=execute_result,
            diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
            references=[],
            duration_ms=int((perf_counter() - execute_start) * 1000),
        )
        execute_input = self._build_stage_input("execute", plan_output)
        record_stage("execute", execute_input, execute_output)

        # Compose stage
        compose_start = perf_counter()
        compose_result = {
            "execution_result": execute_result,
        }
        compose_output = StageOutput(
            stage="compose",
            result=compose_result,
            diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
            references=[],
            duration_ms=int((perf_counter() - compose_start) * 1000),
        )
        compose_input = self._build_stage_input("compose", plan_output)
        record_stage("compose", compose_input, compose_output)

        # Present stage
        present_start = perf_counter()
        present_result = await present_fn(plan_output, execute_result)
        blocks = present_result.get("blocks", [])
        answer = present_result.get("summary", "CI insight ready")

        present_output = StageOutput(
            stage="present",
            result={"summary": answer, "blocks": blocks},
            diagnostics=StageDiagnostics(status="ok", warnings=[], errors=[]),
            references=present_result.get("references", []),
            duration_ms=int((perf_counter() - present_start) * 1000),
        )
        present_input = self._build_stage_input("present", plan_output)
        record_stage("present", present_input, present_output)

        return blocks, answer, {
            "stages": stages,
            "stage_inputs": stage_inputs,
            "stage_outputs": stage_outputs,
        }

    def _build_stage_input(
        self,
        stage_name: str,
        plan_output: PlanOutput,
        prev_output: Dict[str, Any] | None = None,
        stage_assets: Dict[str, str] | None = None,
    ) -> StageInput:
        """Build stage input with proper asset context."""
        context = get_request_context()
        trace_id = context.get("trace_id")
        if not trace_id or trace_id == "-":
            trace_id = context.get("request_id") or str(uuid.uuid4())

        applied_assets = stage_assets or {}

        return StageInput(
            stage=stage_name,
            applied_assets=applied_assets,
            params={
                "plan_output": plan_output.model_dump(),
                "stage_name": stage_name,
            },
            prev_output=prev_output or {},
            trace_id=trace_id,
        )

    def _distribute_stage_assets(
        self, stage: str, all_assets: Dict[str, str]
    ) -> Dict[str, str]:
        """Distribute assets to specific stage."""
        # Filter assets by stage prefix
        stage_prefix = f"{stage}:"
        return {
            k.replace(stage_prefix, ""): v
            for k, v in all_assets.items()
            if k.startswith(stage_prefix)
        }

    def build_orchestration_trace(
        self,
        plan_output: PlanOutput,
        stage_outputs: List[Dict[str, Any]],
        references: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build orchestration trace for Inspector."""
        return {
            "plan_output": plan_output.model_dump(),
            "stages": stage_outputs,
            "references": references,
            "trace_id": get_request_context().get("trace_id"),
            "timestamp": str(perf_counter()),
        }
