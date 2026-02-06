"""
OPS Actions Route

Handles action execution endpoints for orchestration, including rerun, replan,
debug, skip, and rollback operations.

Endpoints:
    POST /ops/actions - Execute recovery or orchestration action
"""

from __future__ import annotations

import uuid
from typing import Any

from core.logging import get_logger
from fastapi import APIRouter, Depends
from schemas import ResponseEnvelope
from sqlmodel import Session
from core.db import get_session

from app.modules.ops.schemas import ReplanTrigger
from app.modules.ops.security import SecurityUtils

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


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
    from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner
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

            orchestrator = CIOrchestratorRunner()
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
            # Run diagnostics
            # TODO: Implement debug service
            result = {
                "debug_id": str(uuid.uuid4()),
                "status": "debugging",
                "logs": [],
                "recommendations": [],
            }

        elif action == "skip":
            # Skip stage
            control_loop = ControlLoop()
            result = control_loop.skip_stage(
                stage or "unknown", params.get("skip_reason", "")
            )

        elif action == "rollback":
            # Rollback to previous version
            # TODO: Implement rollback service
            result = {"rollback_id": str(uuid.uuid4()), "status": "rollback_initiated"}

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
