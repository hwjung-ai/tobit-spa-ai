"""
UI Actions Service: Execute deterministic UI actions with binding engine

Responsibilities:
1. Render action payload with binding engine
2. Route to action handler registry
3. Execute action deterministically
4. Return blocks + metadata
"""

from __future__ import annotations

from typing import Any, Dict
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError

from core.logging import get_logger
from .binding_engine import BindingEngine, mask_sensitive_inputs as mask_fn
from .action_registry import execute_action, ExecutorResult

logger = get_logger(__name__)


# Action-specific input validators (legacy, for backward compatibility)
class HistoryQueryInputs(BaseModel):
    """Input schema for run_history_query action"""
    device_id: str
    date_from: str  # ISO date (YYYY-MM-DD)
    date_to: str    # ISO date (YYYY-MM-DD)


# Legacy action registry (kept for backward compatibility)
ACTION_REGISTRY = {
    "run_history_query": {
        "validator": HistoryQueryInputs,
        "executor": "history",  # Maps to existing hist_executor
        "params_builder": lambda inputs: {
            "question": f"Show history for {inputs['device_id']} from {inputs['date_from']} to {inputs['date_to']}",
            "device_id": inputs["device_id"],
            "date_range": {"from": inputs["date_from"], "to": inputs["date_to"]},
        },
    },
    # More actions can be added here as needed
}

SENSITIVE_INPUT_KEYS = ["password", "token", "secret", "api_key", "auth", "credential"]


def mask_sensitive_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive input values before storing in trace.

    Uses BindingEngine's mask_sensitive_inputs function.

    Args:
        inputs: User input values

    Returns:
        Masked input dictionary with sensitive values replaced
    """
    return mask_fn(inputs)


async def execute_action_deterministic(
    action_id: str,
    inputs: Dict[str, Any],
    context: Dict[str, Any],
    session: Session,
) -> Dict[str, Any]:
    """
    Execute a deterministic UI action without LLM involvement.

    This function:
    1. Validates the action_id exists (from registry)
    2. Routes to the appropriate action handler
    3. Executes using action registry handlers
    4. Returns standardized result with blocks, references, tool_calls

    Args:
        action_id: Action identifier for routing
        inputs: User input values
        context: Execution context (mode, origin, etc.)
        session: Database session

    Returns:
        Dict with keys: blocks, references, tool_calls, summary

    Raises:
        ValueError: If action_id is unknown or execution fails
    """

    logger.info(
        "execute_action_deterministic.start",
        extra={"action_id": action_id, "inputs_keys": list(inputs.keys())},
    )

    try:
        # Use new action registry (from action_registry module)
        result: ExecutorResult = await execute_action(
            action_id=action_id,
            inputs=inputs,
            context=context,
            session=session,
        )

        logger.info(
            "execute_action_deterministic.success",
            extra={
                "action_id": action_id,
                "blocks_count": len(result.blocks),
            },
        )

        # Return standardized result
        return {
            "blocks": result.blocks,
            "references": result.references,
            "tool_calls": result.tool_calls,
            "summary": result.summary,
        }

    except Exception as e:
        logger.error(
            "execute_action_deterministic.error",
            extra={"action_id": action_id, "error": str(e)},
        )
        raise


def render_action_payload(
    payload_template: Dict[str, Any],
    inputs: Dict[str, Any],
    state: Dict[str, Any],
    context_extra: Dict[str, Any],
    trace_id: str,
) -> Dict[str, Any]:
    """
    Render action payload template with bindings.

    Creates binding context and renders template using BindingEngine.

    Args:
        payload_template: Template with {{expr}} patterns
        inputs: User inputs
        state: Current screen state
        context_extra: Additional context (mode, user_id, etc.)
        trace_id: Current trace ID

    Returns:
        Rendered payload dict

    Raises:
        BindingError: If binding fails
    """
    binding_context = {
        "inputs": inputs,
        "state": state,
        "context": context_extra,
        "trace_id": trace_id,
    }

    logger.info(
        "render_action_payload",
        extra={
            "template_keys": list(payload_template.keys()) if isinstance(payload_template, dict) else "N/A",
        },
    )

    rendered = BindingEngine.render_template(payload_template, binding_context)

    logger.debug("render_action_payload.result", extra={"rendered_keys": list(rendered.keys()) if isinstance(rendered, dict) else "N/A"})

    return rendered
