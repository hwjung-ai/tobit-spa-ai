"""Orchestrates Python script execution and CEP rule triggers."""

from __future__ import annotations

import hashlib
import json
import time
from time import perf_counter
from typing import Any, Dict, Tuple
from uuid import UUID

import httpx
from core.config import get_settings
from core.db import engine, get_session_context
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlmodel import Session

from app.modules.api_manager.schemas import ApiExecuteResponse

from .crud import record_exec_log
from .models import TbCepRule

DEFAULT_SCRIPT_TIMEOUT_MS = 5000
DEFAULT_OUTPUT_BYTES = 1_048_576
RULE_LOCK_BASE = 424_200_000
RULE_LOCK_MOD = 100_000


def _runtime_base_url() -> str:
    settings = get_settings()
    port = settings.api_port or 8000
    return f"http://127.0.0.1:{port}"


def get_path_value(target: Any, path: str | None) -> Any | None:
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


def _resolve_metric_request(
    trigger_spec: Dict[str, Any],
) -> Tuple[str, str, Dict[str, Any]]:
    endpoint = trigger_spec.get("endpoint")
    if not endpoint:
        raise HTTPException(
            status_code=400, detail="Metric trigger endpoint is required"
        )
    method = str(trigger_spec.get("method", "GET")).upper()
    if method not in {"GET", "POST"}:
        raise HTTPException(
            status_code=400, detail="Metric trigger method must be GET or POST"
        )
    params = trigger_spec.get("params") or {}
    if not isinstance(params, dict):
        raise HTTPException(
            status_code=400, detail="Metric trigger params must be an object"
        )
    url = (
        endpoint if endpoint.startswith("http") else f"{_runtime_base_url()}{endpoint}"
    )
    return url, method, params.copy()


def fetch_runtime_value(
    trigger_spec: Dict[str, Any],
) -> Tuple[Dict[str, Any], Any | None]:
    settings = get_settings()
    timeout = settings.cep_metric_http_timeout_seconds
    url, method, params = _resolve_metric_request(trigger_spec)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = (
                client.get(url, params=params)
                if method == "GET"
                else client.post(url, json=params)
            )
            response.raise_for_status()
            raw_payload = response.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"Runtime request failed: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Runtime response error: {exc.response.status_code}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="Runtime response is not valid JSON"
        ) from exc
    value_path = trigger_spec.get("value_path")
    extracted_value = get_path_value(raw_payload, value_path)
    return raw_payload, extracted_value


def evaluate_trigger(
    trigger_type: str,
    trigger_spec: Dict[str, Any] | None,
    payload: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    spec = trigger_spec or {}
    if trigger_type == "schedule":
        return True, {"trigger_spec": spec}
    if trigger_type == "metric":
        return _evaluate_metric_trigger(spec, payload)
    if trigger_type == "event":
        return _evaluate_event_trigger(spec, payload)
    raise HTTPException(
        status_code=400, detail=f"Unsupported trigger type: {trigger_type}"
    )


def _evaluate_single_condition(
    condition: Dict[str, Any],
    payload: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """평가 단일 조건과 상세 정보 반환"""
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
    """복합 조건 평가 (AND/OR/NOT)"""
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
    """이벤트 트리거 평가 (단일 또는 복합 조건)"""
    spec = trigger_spec
    payload = payload or {}
    references: Dict[str, Any] = {"trigger_spec": spec}

    # 새로운 복합 조건 형식 지원
    if "conditions" in spec and isinstance(spec.get("conditions"), list):
        conditions = spec.get("conditions", [])
        logic = spec.get("logic", "AND")
        matched, composite_refs = _evaluate_composite_conditions(
            conditions, logic, payload
        )
        references.update(composite_refs)
        return matched, references

    # 기존 단일 조건 형식 (하위 호환성)
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


METRIC_OPERATORS = {">", "<", ">=", "<=", "=="}


def _evaluate_metric_trigger(
    trigger_spec: Dict[str, Any],
    payload: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    spec = trigger_spec
    references: Dict[str, Any] = {"trigger_spec": spec}
    source = spec.get("source", "runtime")
    if source != "runtime":
        raise HTTPException(
            status_code=400, detail=f"Unsupported metric source: {source}"
        )

    value_path = spec.get("value_path")
    if not value_path or not isinstance(value_path, str):
        raise HTTPException(
            status_code=400, detail="Metric trigger value_path is required"
        )
    op = str(spec.get("op", "==")).strip()
    if op not in METRIC_OPERATORS:
        raise HTTPException(status_code=400, detail=f"Unsupported operator: {op}")

    threshold_raw = spec.get("threshold")
    if threshold_raw is None:
        raise HTTPException(
            status_code=400, detail="Metric trigger threshold is required"
        )
    try:
        threshold_value = float(threshold_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400, detail="Metric trigger threshold must be numeric"
        )

    url, method, params = _resolve_metric_request(spec)
    references.update(
        {
            "runtime_endpoint": url,
            "method": method,
            "params": params,
            "value_path": value_path,
            "op": op,
            "threshold": threshold_value,
            "used_test_payload": payload is not None,
        }
    )

    if payload is None:
        _, extracted_value = fetch_runtime_value(spec)
    else:
        extracted_value = get_path_value(payload, value_path)
    references["extracted_value"] = extracted_value

    if extracted_value is None:
        references["condition_evaluated"] = False
        references["error_reason"] = "value_path did not resolve"
        return False, references

    try:
        actual_value = float(extracted_value)
    except (TypeError, ValueError):
        references["condition_evaluated"] = False
        references["error_reason"] = "extracted value is not numeric"
        return False, references

    comparisons = {
        ">": actual_value > threshold_value,
        "<": actual_value < threshold_value,
        ">=": actual_value >= threshold_value,
        "<=": actual_value <= threshold_value,
        "==": actual_value == threshold_value,
    }
    matched = comparisons.get(op)
    references["condition_evaluated"] = True
    references["actual_value"] = actual_value

    # Aggregation support: If aggregation spec exists, apply it
    aggregation_spec = spec.get("aggregation")
    if aggregation_spec:
        # For metric triggers, we can apply aggregation to historic data
        # This would require windowing support (not fully implemented yet)
        # For now, we just document the aggregation intent
        references["aggregation_spec"] = aggregation_spec
        references["note"] = "Aggregation spec present; full windowing support requires Redis or state storage"

    return matched, references


def execute_action(
    action_spec: Dict[str, Any],
    session: Session | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Execute action based on action_type.

    Supported action types:
    - "webhook": HTTP webhook call (existing behavior)
    - "api_script": Execute API Manager script
    - "trigger_rule": Trigger another CEP rule

    Args:
        action_spec: Action specification with type, endpoint, params, etc.
        session: Database session (required for api_script and trigger_rule)

    Returns:
        Tuple of (result_payload, references)
    """
    action_type = str(action_spec.get("type", "webhook")).lower()

    if action_type == "webhook":
        return _execute_webhook_action(action_spec)
    elif action_type == "api_script":
        if not session:
            raise HTTPException(
                status_code=400,
                detail="Database session required for api_script action"
            )
        return _execute_api_script_action(action_spec, session)
    elif action_type == "trigger_rule":
        if not session:
            raise HTTPException(
                status_code=400,
                detail="Database session required for trigger_rule action"
            )
        return _execute_trigger_rule_action(action_spec, session)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported action type: {action_type}"
        )


def _execute_webhook_action(
    action_spec: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute HTTP webhook action (backward compatible)."""
    endpoint = action_spec.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Action endpoint is required")
    method = str(action_spec.get("method", "GET")).upper()
    params = action_spec.get("params") or {}
    body = action_spec.get("body")
    url = (
        endpoint if endpoint.startswith("http") else f"{_runtime_base_url()}{endpoint}"
    )
    try:
        with httpx.Client(timeout=5.0) as client:
            if method == "GET":
                response = client.get(url, params=params)
            else:
                response = client.request(method, url, json=body or params)
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"Action request failed: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Action response error: {exc.response.status_code}"
        ) from exc
    references = {
        "action_type": "webhook",
        "endpoint": endpoint,
        "method": method,
        "params": params,
        "status_code": response.status_code,
    }
    try:
        payload = response.json()
    except ValueError:
        payload = {"text": response.text}
    return payload, references


def _execute_api_script_action(
    action_spec: Dict[str, Any],
    session: Session,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Execute API Manager script action.

    Action spec should contain:
    {
        "type": "api_script",
        "api_id": "api-uuid",
        "params": {...},
        "input": {...}  # optional
    }
    """
    from app.modules.api_manager.crud import get_api_definition
    from app.modules.api_manager.script_executor import execute_script_api

    api_id = action_spec.get("api_id")
    if not api_id:
        raise HTTPException(
            status_code=400,
            detail="api_id is required for api_script action"
        )

    # Fetch API definition
    api_def = get_api_definition(session, api_id)
    if not api_def:
        raise HTTPException(
            status_code=404,
            detail=f"API definition not found: {api_id}"
        )

    if api_def.logic_type != "script":
        raise HTTPException(
            status_code=400,
            detail=f"API {api_id} is not a script type API"
        )

    # Prepare execution params
    params = action_spec.get("params") or {}
    input_payload = action_spec.get("input")
    runtime_policy = api_def.runtime_policy or {}

    # Execute script
    result = execute_script_api(
        session=session,
        api_id=api_id,
        logic_body=api_def.logic_body,
        params=params,
        input_payload=input_payload,
        executed_by="cep-action",
        runtime_policy=runtime_policy,
    )

    references = {
        "action_type": "api_script",
        "api_id": api_id,
        "api_name": api_def.api_name,
        "duration_ms": result.duration_ms,
        "params_passed": list(params.keys()),
        "references": result.references,
        "logs_count": len(result.logs),
    }

    # Return output with result details
    payload = {
        "output": result.output,
        "logs": result.logs,
        "references": result.references,
    }

    return payload, references


def _execute_trigger_rule_action(
    action_spec: Dict[str, Any],
    session: Session,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Trigger another CEP rule.

    Action spec should contain:
    {
        "type": "trigger_rule",
        "rule_id": "target-rule-id",
        "payload": {...}  # event payload to pass to target rule
    }
    """
    from .models import TbCepRule

    target_rule_id = action_spec.get("rule_id")
    if not target_rule_id:
        raise HTTPException(
            status_code=400,
            detail="rule_id is required for trigger_rule action"
        )

    # Fetch target rule
    target_rule = session.query(TbCepRule).filter(
        TbCepRule.rule_id == UUID(target_rule_id)
    ).first()

    if not target_rule:
        raise HTTPException(
            status_code=404,
            detail=f"Target rule not found: {target_rule_id}"
        )

    if not target_rule.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Target rule is not active: {target_rule_id}"
        )

    # Trigger the target rule
    trigger_payload = action_spec.get("payload")

    # Call manual_trigger recursively (with same session)
    result = manual_trigger(
        rule=target_rule,
        payload=trigger_payload,
        executed_by="cep-trigger"
    )

    references = {
        "action_type": "trigger_rule",
        "target_rule_id": target_rule_id,
        "target_rule_name": target_rule.rule_name,
        "trigger_status": result.get("status"),
        "trigger_condition_met": result.get("condition_met"),
        "trigger_duration_ms": result.get("duration_ms"),
    }

    payload = {
        "trigger_result": result,
    }

    return payload, references


def _rule_lock_key(rule_id: UUID) -> int:
    digest = hashlib.md5(rule_id.bytes).digest()
    value = int.from_bytes(digest[:4], "big")
    return RULE_LOCK_BASE + (value % RULE_LOCK_MOD)


def _try_acquire_rule_lock(rule_id: UUID) -> Connection | None:
    conn = engine.connect()
    result = conn.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": _rule_lock_key(rule_id)}
    )
    if result.scalar():
        return conn
    conn.close()
    return None


def _release_rule_lock(conn: Connection, rule_id: UUID) -> None:
    try:
        conn.execute(
            text("SELECT pg_advisory_unlock(:key)"), {"key": _rule_lock_key(rule_id)}
        )
    finally:
        conn.close()


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


HTTP_TIMEOUT = 5.0


def execute_http_api(
    session: Session,
    api_id: str,
    logic_body: str,
    params: dict[str, Any] | None,
    executed_by: str,
) -> ApiExecuteResponse:
    try:
        spec = json.loads(logic_body) if logic_body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid HTTP logic body") from exc
    method = spec.get("method", "GET").upper()
    url = spec.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="HTTP logic must specify url")
    headers = spec.get("headers") or {}
    data = spec.get("body")
    query_params = spec.get("params") or {}
    start = perf_counter()
    status = "success"
    error_message: str | None = None
    try:
        response = httpx.request(
            method,
            url,
            params=query_params,
            headers=headers,
            json=data,
            timeout=HTTP_TIMEOUT,
        )
    except Exception as exc:
        status = "fail"
        error_message = str(exc)
        raise HTTPException(
            status_code=502, detail="External HTTP request failed"
        ) from exc
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        record_exec_log(
            session=session,
            api_id=api_id,
            status=status,
            duration_ms=duration_ms,
            row_count=0,
            params=params or {},
            executed_by=executed_by,
            error_message=error_message,
        )
    try:
        body = response.json()
    except ValueError:
        body = response.text
    if isinstance(body, list):
        rows = [row if isinstance(row, dict) else {"value": row} for row in body]
        columns = sorted({key for row in rows for key in row.keys()})
    elif isinstance(body, dict):
        rows = [body]
        columns = sorted(body.keys())
    else:
        rows = [{"value": body}]
        columns = ["value"]
    duration_ms = int((perf_counter() - start) * 1000)
    return ApiExecuteResponse(
        executed_sql=f"HTTP {method} {url}",
        params=params or {},
        columns=columns,
        rows=rows,
        row_count=len(rows),
        duration_ms=duration_ms,
    )


# ============================================================================
# Aggregation Functions for Windowing/Aggregation Support
# ============================================================================


def _apply_aggregation(
    values: list[Any],
    agg_type: str,
    percentile_value: float | None = None,
) -> float | None:
    """
    Apply aggregation function to a list of values

    Args:
        values: List of numeric values
        agg_type: Aggregation type (count, sum, avg, min, max, std, percentile)
        percentile_value: Value for percentile calculation (0-100)

    Returns:
        Aggregated value or None if cannot compute
    """
    if not values:
        return None

    # Filter out None values
    numeric_values = [v for v in values if isinstance(v, (int, float)) and v is not None]

    if not numeric_values:
        return None

    agg_type = agg_type.lower() if agg_type else "count"

    try:
        if agg_type == "count":
            return float(len(numeric_values))
        elif agg_type == "sum":
            return float(sum(numeric_values))
        elif agg_type == "avg" or agg_type == "average":
            return float(sum(numeric_values)) / len(numeric_values)
        elif agg_type == "min":
            return float(min(numeric_values))
        elif agg_type == "max":
            return float(max(numeric_values))
        elif agg_type == "std" or agg_type == "stddev":
            if len(numeric_values) < 2:
                return 0.0
            mean = sum(numeric_values) / len(numeric_values)
            variance = sum((x - mean) ** 2 for x in numeric_values) / (
                len(numeric_values) - 1
            )
            return float(variance**0.5)
        elif agg_type == "percentile":
            if percentile_value is None or not (0 <= percentile_value <= 100):
                return None
            sorted_values = sorted(numeric_values)
            index = (percentile_value / 100.0) * (len(sorted_values) - 1)
            lower = int(index)
            upper = lower + 1
            if upper >= len(sorted_values):
                return float(sorted_values[lower])
            weight = index - lower
            return float(
                sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
            )
        else:
            return None
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def evaluate_aggregation(
    window_events: list[Dict[str, Any]],
    aggregation_spec: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluate aggregation over a window of events

    Args:
        window_events: List of events in the current window
        aggregation_spec: Aggregation specification with type, field, threshold

    Returns:
        Tuple of (matched: bool, details: dict)
    """
    if not window_events or not aggregation_spec:
        return False, {"reason": "No events or aggregation spec"}

    agg_type = aggregation_spec.get("type", "count")
    field = aggregation_spec.get("field")
    threshold = aggregation_spec.get("threshold")

    # Extract field values from window events
    if field:
        values = []
        for event in window_events:
            # event can be {"timestamp": ..., "data": {...}} or just payload
            payload = event.get("data", event)
            value = get_path_value(payload, field)
            if value is not None:
                values.append(value)
    else:
        # If no field specified, count events
        values = [1] * len(window_events)
        agg_type = "count"

    # Apply aggregation
    percentile_value = aggregation_spec.get("percentile_value")
    aggregated_value = _apply_aggregation(values, agg_type, percentile_value)

    if aggregated_value is None:
        return False, {"reason": f"Cannot compute {agg_type} aggregation"}

    # Evaluate condition if threshold provided
    if threshold is not None:
        op = aggregation_spec.get("op", ">")
        matched = False

        if op == ">":
            matched = aggregated_value > threshold
        elif op == ">=":
            matched = aggregated_value >= threshold
        elif op == "<":
            matched = aggregated_value < threshold
        elif op == "<=":
            matched = aggregated_value <= threshold
        elif op == "==":
            matched = aggregated_value == threshold
        elif op == "!=":
            matched = aggregated_value != threshold

        return matched, {
            "aggregation_type": agg_type,
            "field": field,
            "aggregated_value": aggregated_value,
            "threshold": threshold,
            "operator": op,
            "matched": matched,
            "event_count": len(window_events),
        }
    else:
        # No threshold, just return aggregated value
        return True, {
            "aggregation_type": agg_type,
            "field": field,
            "aggregated_value": aggregated_value,
            "event_count": len(window_events),
        }


def apply_window_aggregation(
    trigger_spec: Dict[str, Any],
    window_events: list[Dict[str, Any]],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Apply windowing and aggregation to a set of events

    Args:
        trigger_spec: Trigger specification with window and aggregation config
        window_events: List of events in the current window

    Returns:
        Tuple of (matched: bool, details: dict)
    """
    aggregation_spec = trigger_spec.get("aggregation")

    if not aggregation_spec:
        return False, {"reason": "No aggregation spec provided"}

    # Apply aggregation
    matched, details = evaluate_aggregation(window_events, aggregation_spec)

    # Add window info
    details["window_size"] = len(window_events)
    details["window_config"] = trigger_spec.get("window_config", {})

    return matched, details
