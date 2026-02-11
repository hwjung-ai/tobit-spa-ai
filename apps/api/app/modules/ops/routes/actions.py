"""
OPS Actions Route

Handles action execution endpoints for orchestration, including rerun, replan,
debug, skip, and rollback operations.

Endpoints:
    POST /ops/actions - Execute recovery or orchestration action
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from core.db import get_session
from core.logging import get_logger
from fastapi import APIRouter, Depends
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.ops.schemas import ReplanTrigger
from app.modules.ops.security import SecurityUtils

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Debug diagnostics helper
# ---------------------------------------------------------------------------

def _run_debug_diagnostics(
    session: Session,
    execution_id: str | None,
    stage: str | None,
) -> Dict[str, Any]:
    """Analyse an execution trace and return diagnostics."""
    from app.modules.inspector.crud import get_execution_trace

    debug_id = str(uuid.uuid4())

    if not execution_id:
        return {
            "debug_id": debug_id,
            "status": "error",
            "error": "execution_id (or trace_id) is required in params",
            "logs": [],
            "recommendations": ["Provide params.execution_id to debug a specific run"],
        }

    trace = get_execution_trace(session, execution_id)
    if not trace:
        return {
            "debug_id": debug_id,
            "status": "not_found",
            "error": f"Execution trace {execution_id} not found",
            "logs": [],
            "recommendations": ["Verify the execution_id exists in the inspector"],
        }

    # Collect logs from execution_steps
    logs: List[str] = []
    error_steps: List[Dict[str, Any]] = []
    slow_steps: List[Dict[str, Any]] = []

    for step in (trace.execution_steps or []):
        step_id = step.get("step_id", "unknown")
        status = step.get("status", "unknown")
        duration = step.get("duration_ms", 0)
        logs.append(f"[{status}] {step_id} ({duration}ms)")

        if status == "error":
            error_steps.append(step)
        if duration > 3000:
            slow_steps.append(step)

    # Build recommendations
    recommendations: List[str] = []
    if trace.status == "error":
        recommendations.append("Execution ended with error status – check error_steps for details")
    if error_steps:
        for es in error_steps:
            err_msg = (es.get("error") or {}).get("message", "unknown error")
            recommendations.append(f"Step '{es.get('step_id')}' failed: {err_msg}")
    if slow_steps:
        for ss in slow_steps:
            recommendations.append(
                f"Step '{ss.get('step_id')}' is slow ({ss.get('duration_ms')}ms) – consider optimisation"
            )
    if trace.fallbacks:
        fallback_keys = [k for k, v in trace.fallbacks.items() if v]
        if fallback_keys:
            recommendations.append(
                f"Fallbacks used for: {', '.join(fallback_keys)} – consider registering assets"
            )
    if trace.replan_events:
        recommendations.append(
            f"{len(trace.replan_events)} replan event(s) occurred – review replan triggers"
        )
    if not recommendations:
        recommendations.append("No issues detected – execution looks healthy")

    return {
        "debug_id": debug_id,
        "status": "completed",
        "trace_id": execution_id,
        "execution_status": trace.status,
        "ops_mode": trace.ops_mode,
        "duration_ms": trace.duration_ms,
        "question": trace.question,
        "total_steps": len(trace.execution_steps or []),
        "error_steps": len(error_steps),
        "slow_steps": len(slow_steps),
        "replan_count": len(trace.replan_events or []),
        "fallbacks": trace.fallbacks,
        "logs": logs,
        "error_details": [
            {
                "step_id": s.get("step_id"),
                "tool_name": s.get("tool_name"),
                "error": s.get("error"),
            }
            for s in error_steps
        ],
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Rollback helper
# ---------------------------------------------------------------------------

def _run_rollback(
    session: Session,
    execution_id: str | None,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Rollback to a previous execution state by re-running with the original params."""
    from app.modules.inspector.crud import get_execution_trace
    from app.modules.ops.services.ci.orchestrator.runner import OpsOrchestratorRunner

    rollback_id = str(uuid.uuid4())

    if not execution_id:
        return {
            "rollback_id": rollback_id,
            "status": "error",
            "error": "execution_id (or trace_id) is required in params",
        }

    trace = get_execution_trace(session, execution_id)
    if not trace:
        return {
            "rollback_id": rollback_id,
            "status": "error",
            "error": f"Execution trace {execution_id} not found",
        }

    # Extract the original request to replay
    original_payload = trace.request_payload or {}
    original_question = trace.question
    original_mode = trace.ops_mode

    # If caller provides explicit replay params, merge them
    replay_params = {**original_payload, **params.get("override", {})}

    # Attempt re-execution via orchestrator
    try:
        orchestrator = OpsOrchestratorRunner()
        ci_code = replay_params.get("ci_code") or original_question
        rerun_result = orchestrator.rerun_ci(ci_code, replay_params)

        return {
            "rollback_id": rollback_id,
            "status": "rollback_completed",
            "original_trace_id": execution_id,
            "original_mode": original_mode,
            "original_question": original_question,
            "rerun_result": rerun_result,
        }
    except Exception as e:
        logger.error(f"Rollback re-execution failed: {e}", exc_info=True)
        return {
            "rollback_id": rollback_id,
            "status": "rollback_failed",
            "original_trace_id": execution_id,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Main action endpoint
# ---------------------------------------------------------------------------

@router.post("/actions")
def execute_action(
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Execute recovery or orchestration action for OPS workflow.

    Supports various action types including rerun, replan, debug, skip, and rollback.
    Each action type has its own execution logic and parameters.

    Payload structure:
        {
            "action": "rerun|replan|debug|skip|rollback",
            "trigger": { ...ReplanTrigger... },
            "stage": "stage_name",
            "params": { ...action-specific parameters... }
        }

    Args:
        payload: Request payload with action type and parameters
        session: Database session dependency

    Returns:
        ResponseEnvelope with action result and metadata
    """
    from app.modules.ops.services.ci.orchestrator.runner import OpsOrchestratorRunner
    from app.modules.ops.services.control_loop import ControlLoop

    try:
        action = payload.get("action")
        trigger = payload.get("trigger")
        stage = payload.get("stage")
        params = payload.get("params", {})

        if not action:
            return ResponseEnvelope.error(message="action is required")

        # Validate trigger if provided
        if trigger:
            try:
                from app.modules.ops.schemas import safe_parse_trigger

                trigger = safe_parse_trigger(trigger)
            except Exception:
                return ResponseEnvelope.error(message="invalid trigger format")

        action_id = str(uuid.uuid4())

        # 로깅을 위해 요청 데이터 마스킹
        masked_payload = SecurityUtils.mask_dict(payload)
        logger.info(
            f"Executing action: {action} for stage: {stage}",
            extra={"action_id": action_id, "masked_payload": masked_payload},
        )

        # Execute action based on type
        result = None
        message = f"Action {action} executed successfully"

        if action == "rerun":
            # Re-run CI with provided parameters
            ci_code = params.get("ci_code")
            if not ci_code:
                return ResponseEnvelope.error(message="ci_code is required for rerun")

            orchestrator = OpsOrchestratorRunner()
            result = orchestrator.rerun_ci(ci_code, params)

        elif action == "replan":
            # Trigger replanning
            control_loop = ControlLoop()
            result = control_loop.trigger_replan(
                trigger
                or ReplanTrigger(
                    trigger_type="manual",
                    stage_name=stage or "unknown",
                    reason="Manual replan triggered",
                    timestamp="now",
                )
            )

        elif action == "debug":
            # Run diagnostics on a specific execution trace
            execution_id = params.get("execution_id") or params.get("trace_id")
            result = _run_debug_diagnostics(session, execution_id, stage)

        elif action == "skip":
            # Skip stage
            control_loop = ControlLoop()
            result = control_loop.skip_stage(
                stage or "unknown", params.get("skip_reason", "")
            )

        elif action == "rollback":
            # Rollback to a previous execution by re-running with original params
            execution_id = params.get("execution_id") or params.get("trace_id")
            result = _run_rollback(session, execution_id, params)

        else:
            return ResponseEnvelope.error(message=f"Unknown action: {action}")

        # Log the action execution
        logger.info(f"Action {action} completed: {result}")

        return ResponseEnvelope.success(
            data={
                "action_id": action_id,
                "action": action,
                "stage": stage,
                "result": result,
                "message": message,
            }
        )

    except Exception as e:
        logger.error(f"Action execution failed: {e}", exc_info=True)
        return ResponseEnvelope.error(message=f"Action failed: {str(e)}")
