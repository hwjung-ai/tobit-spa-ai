"""
Deterministic UI Action executor for handling interactive UI panel actions.

Routes action_id to specific executors without LLM involvement.
"""

from typing import Any, Dict
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError


# Action-specific input validators
class HistoryQueryInputs(BaseModel):
    """Input schema for run_history_query action"""
    device_id: str
    date_from: str  # ISO date (YYYY-MM-DD)
    date_to: str    # ISO date (YYYY-MM-DD)


# Action registry mapping action_id to executor configuration
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

    Args:
        inputs: User input values

    Returns:
        Masked input dictionary with sensitive values replaced with "[MASKED]"
    """
    masked = {}
    for key, value in inputs.items():
        if any(sk in key.lower() for sk in SENSITIVE_INPUT_KEYS):
            masked[key] = "[MASKED]"
        else:
            masked[key] = value
    return masked


async def execute_action_deterministic(
    action_id: str,
    inputs: Dict[str, Any],
    context: Dict[str, Any],
    session: Session,
) -> Dict[str, Any]:
    """
    Execute a deterministic UI action without LLM involvement.

    This function:
    1. Validates the action_id exists
    2. Validates inputs against the action's input schema
    3. Routes to the appropriate executor
    4. Executes using existing OPS executors (config, history, metric, etc.)
    5. Returns standardized result with blocks, references, tool_calls

    Args:
        action_id: Action identifier for routing
        inputs: User input values (validated before calling)
        context: Execution context (mode, origin, etc.)
        session: Database session

    Returns:
        Dict with keys: blocks, references, tool_calls

    Raises:
        ValueError: If action_id is unknown or input validation fails
    """

    # Validate action exists
    if action_id not in ACTION_REGISTRY:
        raise ValueError(f"Unknown action_id: {action_id}")

    action_config = ACTION_REGISTRY[action_id]

    # Validate inputs against schema
    validator = action_config["validator"]
    try:
        validated_inputs = validator(**inputs)
    except ValidationError as e:
        raise ValueError(f"Input validation failed: {e}")

    # Build executor params
    params_builder = action_config["params_builder"]
    executor_params = params_builder(dict(validated_inputs))

    # Route to existing executor
    executor_name = action_config["executor"]

    # Import and call executor (reuse existing OPS executors)
    if executor_name == "history":
        from app.modules.ops.services.executors.hist_executor import run_hist
        result = await run_hist(
            question=executor_params["question"],
            mode=context.get("mode", "real"),
            session=session,
        )
    elif executor_name == "metric":
        from app.modules.ops.services.executors.metric_executor import run_metric
        result = await run_metric(
            question=executor_params["question"],
            mode=context.get("mode", "real"),
            session=session,
        )
    elif executor_name == "config":
        from app.modules.ops.services.executors.config_executor import run_config
        result = await run_config(
            question=executor_params["question"],
            mode=context.get("mode", "real"),
            session=session,
        )
    elif executor_name == "graph":
        from app.modules.ops.services.executors.graph_executor import run_graph
        result = await run_graph(
            question=executor_params["question"],
            mode=context.get("mode", "real"),
            session=session,
        )
    else:
        raise ValueError(f"Unknown executor: {executor_name}")

    # Return standardized result
    return {
        "blocks": result.get("blocks", []),
        "references": result.get("references", []),
        "tool_calls": result.get("tool_calls", []),
    }
