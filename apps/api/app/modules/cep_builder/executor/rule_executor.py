"""Rule evaluation and trigger logic for CEP Builder."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from fastapi import HTTPException


def get_path_value(target: Any, path: str | None) -> Any | None:
    """Extract value from object using dot notation path."""
    if path is None or path == "":
        return target
    current: Any = target
    for token in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(token)
            continue
        if isinstance(current, list) and token.isdigit():
            index = int(token)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def _evaluate_single_condition(
    condition: Dict[str, Any],
    payload: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Evaluate a single condition."""
    field = condition.get("field")
    op = str(condition.get("op", "==")).strip()
    target_value = condition.get("value")

    raw_value = payload.get(field)
    if raw_value is None:
        metrics_block = payload.get("metrics") or {}
        if isinstance(metrics_block, dict):
            raw_value = metrics_block.get(field)

    condition_ref: Dict[str, Any] = {
        "field": field,
        "operator": op,
        "expected": target_value,
    }

    if raw_value is None:
        condition_ref["condition_evaluated"] = False
        condition_ref["reason"] = "field missing"
        return False, condition_ref

    try:
        actual = float(raw_value)
        expected = float(target_value)
    except (TypeError, ValueError):
        actual = raw_value
        expected = target_value

    operators = {
        ">": actual > expected,
        "<": actual < expected,
        ">=": actual >= expected,
        "<=": actual <= expected,
        "==": actual == expected,
        "=": actual == expected,
        "!=": actual != expected,
    }
    result = operators.get(op)
    if result is None:
        raise HTTPException(status_code=400, detail=f"Unsupported operator: {op}")

    condition_ref["actual"] = actual
    condition_ref["condition_evaluated"] = True
    return result, condition_ref


def _evaluate_composite_conditions(
    conditions: list[Dict[str, Any]],
    logic: str,
    payload: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Evaluate composite conditions (AND/OR/NOT logic)."""
    if not conditions or len(conditions) == 0:
        return True, {"composite_logic": logic, "conditions_evaluated": []}

    logic = logic.upper()
    if logic not in {"AND", "OR", "NOT"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported composite logic: {logic}. Must be AND, OR, or NOT"
        )

    results: list[bool] = []
    condition_refs: list[Dict[str, Any]] = []

    for condition in conditions:
        matched, cond_ref = _evaluate_single_condition(condition, payload)
        results.append(matched)
        condition_refs.append(cond_ref)

    if logic == "AND":
        final_result = all(results)
    elif logic == "OR":
        final_result = any(results)
    else:  # NOT
        final_result = not any(results)

    return final_result, {
        "composite_logic": logic,
        "conditions_evaluated": condition_refs,
        "final_result": final_result,
    }


def _evaluate_event_trigger(
    trigger_spec: Dict[str, Any],
    payload: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    """Evaluate event trigger (single or composite conditions)."""
    spec = trigger_spec
    payload = payload or {}
    references: Dict[str, Any] = {"trigger_spec": spec}

    # Support composite conditions
    if "conditions" in spec and isinstance(spec.get("conditions"), list):
        conditions = spec.get("conditions", [])
        logic = spec.get("logic", "AND")
        matched, composite_refs = _evaluate_composite_conditions(
            conditions, logic, payload
        )
        references.update(composite_refs)
        return matched, references

    # Legacy single condition format
    field = spec.get("field")
    op = str(spec.get("op", "==")).strip()
    target_value = spec.get("value")

    raw_value = payload.get(field)
    if raw_value is None:
        metrics_block = payload.get("metrics") or {}
        if isinstance(metrics_block, dict):
            raw_value = metrics_block.get(field)
    if raw_value is None:
        references["reason"] = "field missing"
        references["condition_evaluated"] = False
        return False, references

    try:
        actual = float(raw_value)
        expected = float(target_value)
    except (TypeError, ValueError):
        actual = raw_value
        expected = target_value

    operators = {
        ">": actual > expected,
        "<": actual < expected,
        ">=": actual >= expected,
        "<=": actual <= expected,
        "==": actual == expected,
        "=": actual == expected,
        "!=": actual != expected,
    }
    result = operators.get(op)
    if result is None:
        raise HTTPException(status_code=400, detail=f"Unsupported operator: {op}")

    references["actual"] = actual
    references["expected"] = expected
    references["operator"] = op
    references["condition_evaluated"] = True
    return result, references
