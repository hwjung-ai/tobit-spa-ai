"""
OPS UI Actions Route

Handles UI action execution for deterministic operations triggered from the frontend.

Endpoints:
    POST /ops/ui-actions - Execute a deterministic UI action
"""

from __future__ import annotations

import time
import uuid

from core.config import get_settings
from core.db import get_session_context
from core.logging import get_logger
from fastapi import APIRouter, Header
from schemas import ResponseEnvelope

from app.modules.inspector.service import persist_execution_trace
from app.modules.inspector.span_tracker import (
    clear_spans,
    end_span,
    get_all_spans,
    start_span,
)
from app.modules.ops.schemas import UIActionRequest

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.post("/ui-actions", response_model=ResponseEnvelope)
async def execute_ui_action(
    payload: UIActionRequest,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
) -> ResponseEnvelope:
    """Execute a deterministic UI action based on action_id.

    Executes deterministic operations triggered from the frontend without LLM,
    including action routing, execution, trace persistence, and error handling.

    Flow:
        1. Validate action_id and inputs
        2. Generate new trace_id with parent_trace_id = payload.trace_id
        3. Route to deterministic executor based on action_id
        4. Execute using existing OPS executors (no LLM)
        5. Persist execution trace
        6. Return blocks as response

    Args:
        payload: UI action request with action_id, inputs, context
        x_tenant_id: Tenant ID from header

    Returns:
        ResponseEnvelope with execution result including blocks, state_patch, etc.
    """
    from app.modules.ops.services.ui_actions import (
        execute_action_deterministic,
        mask_sensitive_inputs,
    )

    # Setup
    trace_id = str(uuid.uuid4())
    parent_trace_id = payload.trace_id
    settings = get_settings()

    ts_start = time.time()

    # Start span tracking
    clear_spans()
    action_span = start_span(f"ui_action:{payload.action_id}", "ui_action")

    try:
        # Validate OPS_MODE (no mock in real mode)
        mode = payload.context.get("mode", "real")
        if mode == "mock" and settings.OPS_MODE == "real":
            raise ValueError("Mock mode not allowed in OPS_MODE=real")

        # Execute action deterministically
        with get_session_context() as session:
            executor_result = await execute_action_deterministic(
                action_id=payload.action_id,
                inputs=payload.inputs,
                context=payload.context,
                session=session,
            )

        # End span
        end_span(action_span, status="ok")

        # Persist trace
        duration_ms = int((time.time() - ts_start) * 1000)
        all_spans = get_all_spans()

        with get_session_context() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature="ui_action",
                endpoint="/ops/ui-actions",
                method="POST",
                ops_mode=mode,
                question=f"UI Action: {payload.action_id}",
                status="success",
                duration_ms=duration_ms,
                request_payload={
                    "trace_id": payload.trace_id,
                    "action_id": payload.action_id,
                    "inputs": mask_sensitive_inputs(payload.inputs),
                    "context": payload.context,
                },
                plan_raw=None,
                plan_validated=None,
                trace_payload={
                    "route": payload.action_id,
                    "tool_calls": executor_result.get("tool_calls", []),
                    "references": executor_result.get("references", []),
                },
                answer_meta={
                    "route": payload.action_id,
                    "route_reason": "UI action execution",
                    "timing_ms": duration_ms,
                    "trace_id": trace_id,
                    "parent_trace_id": parent_trace_id,
                },
                blocks=executor_result["blocks"],
                flow_spans=all_spans,
            )

        logger.info(
            "ui_action.success",
            extra={
                "action_id": payload.action_id,
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "duration_ms": duration_ms,
                "blocks_count": len(executor_result.get("blocks", [])),
            },
        )

        return ResponseEnvelope.success(
            data={
                "trace_id": trace_id,
                "status": "ok",
                "blocks": executor_result["blocks"],
                "references": executor_result.get("references", []),
                "state_patch": executor_result.get("state_patch", {}),
            }
        )

    except Exception as exc:
        # Error handling
        end_span(
            action_span,
            status="error",
            summary={"error_type": type(exc).__name__, "error_message": str(exc)},
        )

        duration_ms = int((time.time() - ts_start) * 1000)
        all_spans = get_all_spans()

        # Error blocks
        error_blocks = [
            {
                "type": "markdown",
                "content": f"## ❌ UI Action 실행 실패\n\n**Action**: {payload.action_id}\n\n**Error**: {str(exc)}",
            }
        ]

        with get_session_context() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature="ui_action",
                endpoint="/ops/ui-actions",
                method="POST",
                ops_mode=payload.context.get("mode", "real"),
                question=f"UI Action: {payload.action_id}",
                status="error",
                duration_ms=duration_ms,
                request_payload={
                    "trace_id": payload.trace_id,
                    "action_id": payload.action_id,
                    "inputs": mask_sensitive_inputs(payload.inputs),
                    "context": payload.context,
                },
                plan_raw=None,
                plan_validated=None,
                trace_payload={
                    "route": payload.action_id,
                    "tool_calls": [],
                    "references": [],
                },
                answer_meta={
                    "route": payload.action_id,
                    "route_reason": "UI action execution",
                    "timing_ms": duration_ms,
                    "trace_id": trace_id,
                    "parent_trace_id": parent_trace_id,
                    "error": str(exc),
                },
                blocks=error_blocks,
                flow_spans=all_spans,
            )

        logger.error(
            "ui_action.error",
            extra={
                "action_id": payload.action_id,
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "error": str(exc),
                "duration_ms": duration_ms,
            },
        )

        return ResponseEnvelope.success(
            data={
                "trace_id": trace_id,
                "status": "error",
                "blocks": error_blocks,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        )
