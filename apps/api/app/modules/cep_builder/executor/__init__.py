"""Executor modules for CEP Builder - combines all execution logic."""

from __future__ import annotations

import time
from time import perf_counter
from typing import Any, Dict

from core.db import get_session_context
from fastapi import HTTPException
from sqlmodel import Session

from ..crud import record_exec_log
from ..models import TbCepRule
from .baseline_executor import _evaluate_anomaly_trigger
from .metric_executor import (
    _evaluate_metric_trigger,
    apply_window_aggregation,
    evaluate_aggregation,
    fetch_runtime_value,
    get_path_value,
)
from .notification_executor import (
    _release_rule_lock,
    _try_acquire_rule_lock,
    execute_action,
)
from .rule_executor import (
    _evaluate_composite_conditions,
    _evaluate_event_trigger,
    _evaluate_single_condition,
)


def evaluate_trigger(
    trigger_type: str,
    trigger_spec: Dict[str, Any] | None,
    payload: Dict[str, Any] | None,
) -> tuple[bool, Dict[str, Any]]:
    """Evaluate trigger based on type."""
    spec = trigger_spec or {}
    if trigger_type == "schedule":
        return True, {"trigger_spec": spec}
    if trigger_type == "metric":
        return _evaluate_metric_trigger(spec, payload)
    if trigger_type == "event":
        return _evaluate_event_trigger(spec, payload)
    if trigger_type == "anomaly":
        return _evaluate_anomaly_trigger(spec, payload)
    raise HTTPException(
        status_code=400, detail=f"Unsupported trigger type: {trigger_type}"
    )


def manual_trigger(
    rule: TbCepRule,
    payload: Dict[str, Any] | None = None,
    executed_by: str = "cep-builder",
    session: Session | None = None,
) -> Dict[str, Any]:
    """
    Manually trigger a CEP rule execution.

    Args:
        rule: The CEP rule to execute
        payload: Event payload to evaluate against the rule
        executed_by: Who triggered this execution
        session: Optional database session (created if not provided)

    Returns:
        Execution result with status, condition_met, result, references, etc.
    """
    start = time.perf_counter()
    condition, trigger_refs = evaluate_trigger(
        rule.trigger_type, rule.trigger_spec, payload
    )
    lock_conn = _try_acquire_rule_lock(rule.rule_id)
    references: Dict[str, Any] = {"trigger": trigger_refs}
    status = "dry_run"
    result: Dict[str, Any] | None = None
    error_message: str | None = None
    local_session = False

    if not lock_conn:
        skipped_refs = {
            "skipped_reason": "rule already running",
            "trigger": trigger_refs,
        }
        duration_ms = int((time.perf_counter() - start) * 1000)
        with get_session_context() as db_session:
            record_exec_log(
                session=db_session,
                rule_id=str(rule.rule_id),
                status="skipped",
                duration_ms=duration_ms,
                references=skipped_refs,
                executed_by=executed_by,
                error_message="rule already running",
            )
        return {
            "status": "skipped",
            "condition_met": False,
            "result": None,
            "references": skipped_refs,
            "error_message": "rule already running",
            "duration_ms": duration_ms,
        }

    # Create session if not provided
    if session is None:
        session = get_session_context().__enter__()
        local_session = True

    try:
        if condition:
            status = "success"
            action_result, action_refs = execute_action(rule.action_spec, session)
            result = action_result
            references["action"] = action_refs
    except HTTPException as exc:
        status = "fail"
        error_message = exc.detail if isinstance(exc.detail, str) else None
        references["action"] = {"error": error_message or "Action failure"}
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        if payload is None:
            payload = {}
        try:
            record_exec_log(
                session=session,
                rule_id=str(rule.rule_id),
                status=status,
                duration_ms=duration_ms,
                references=references,
                executed_by=executed_by,
                error_message=error_message,
            )
        finally:
            _release_rule_lock(lock_conn, rule.rule_id)
            if local_session:
                session.close()

    return {
        "status": status,
        "condition_met": condition,
        "result": result,
        "references": references,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }


# Re-export key functions for backward compatibility and direct access
__all__ = [
    "evaluate_trigger",
    "manual_trigger",
    "execute_action",
    "fetch_runtime_value",
    "get_path_value",
    "evaluate_aggregation",
    "apply_window_aggregation",
    # Internal evaluation functions
    "_evaluate_single_condition",
    "_evaluate_composite_conditions",
    "_evaluate_event_trigger",
    "_evaluate_metric_trigger",
    "_evaluate_anomaly_trigger",
]
