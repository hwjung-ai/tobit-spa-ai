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


def _resolve_metric_request(trigger_spec: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    endpoint = trigger_spec.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Metric trigger endpoint is required")
    method = str(trigger_spec.get("method", "GET")).upper()
    if method not in {"GET", "POST"}:
        raise HTTPException(status_code=400, detail="Metric trigger method must be GET or POST")
    params = trigger_spec.get("params") or {}
    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail="Metric trigger params must be an object")
    url = endpoint if endpoint.startswith("http") else f"{_runtime_base_url()}{endpoint}"
    return url, method, params.copy()


def fetch_runtime_value(trigger_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], Any | None]:
    settings = get_settings()
    timeout = settings.cep_metric_http_timeout_seconds
    url, method, params = _resolve_metric_request(trigger_spec)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params) if method == "GET" else client.post(url, json=params)
            response.raise_for_status()
            raw_payload = response.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Runtime request failed: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Runtime response error: {exc.response.status_code}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Runtime response is not valid JSON") from exc
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
    raise HTTPException(status_code=400, detail=f"Unsupported trigger type: {trigger_type}")


def _evaluate_event_trigger(
    trigger_spec: Dict[str, Any],
    payload: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    spec = trigger_spec
    references: Dict[str, Any] = {"trigger_spec": spec}
    field = spec.get("field")
    op = str(spec.get("op", "==")).strip()
    target_value = spec.get("value")
    payload = payload or {}
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
        raise HTTPException(status_code=400, detail=f"Unsupported metric source: {source}")

    value_path = spec.get("value_path")
    if not value_path or not isinstance(value_path, str):
        raise HTTPException(status_code=400, detail="Metric trigger value_path is required")
    op = str(spec.get("op", "==")).strip()
    if op not in METRIC_OPERATORS:
        raise HTTPException(status_code=400, detail=f"Unsupported operator: {op}")

    threshold_raw = spec.get("threshold")
    if threshold_raw is None:
        raise HTTPException(status_code=400, detail="Metric trigger threshold is required")
    try:
        threshold_value = float(threshold_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Metric trigger threshold must be numeric")

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
    return matched, references


def execute_action(action_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    endpoint = action_spec.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Action endpoint is required")
    method = str(action_spec.get("method", "GET")).upper()
    params = action_spec.get("params") or {}
    body = action_spec.get("body")
    url = endpoint if endpoint.startswith("http") else f"{_runtime_base_url()}{endpoint}"
    try:
        with httpx.Client(timeout=5.0) as client:
            if method == "GET":
                response = client.get(url, params=params)
            else:
                response = client.request(method, url, json=body or params)
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Action request failed: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Action response error: {exc.response.status_code}") from exc
    references = {
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


def _rule_lock_key(rule_id: UUID) -> int:
    digest = hashlib.md5(rule_id.bytes).digest()
    value = int.from_bytes(digest[:4], "big")
    return RULE_LOCK_BASE + (value % RULE_LOCK_MOD)


def _try_acquire_rule_lock(rule_id: UUID) -> Connection | None:
    conn = engine.connect()
    result = conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": _rule_lock_key(rule_id)})
    if result.scalar():
        return conn
    conn.close()
    return None


def _release_rule_lock(conn: Connection, rule_id: UUID) -> None:
    try:
        conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _rule_lock_key(rule_id)})
    finally:
        conn.close()


def manual_trigger(
    rule: TbCepRule,
    payload: Dict[str, Any] | None = None,
    executed_by: str = "cep-builder",
) -> Dict[str, Any]:
    start = time.perf_counter()
    condition, trigger_refs = evaluate_trigger(rule.trigger_type, rule.trigger_spec, payload)
    lock_conn = _try_acquire_rule_lock(rule.rule_id)
    references: Dict[str, Any] = {"trigger": trigger_refs}
    status = "dry_run"
    result: Dict[str, Any] | None = None
    error_message: str | None = None
    if not lock_conn:
        skipped_refs = {"skipped_reason": "rule already running", "trigger": trigger_refs}
        duration_ms = int((time.perf_counter() - start) * 1000)
        with get_session_context() as session:
            record_exec_log(
                session=session,
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
    try:
        if condition:
            status = "success"
            action_result, action_refs = execute_action(rule.action_spec)
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
        with get_session_context() as session:
            record_exec_log(
                session=session,
                rule_id=str(rule.rule_id),
                status=status,
                duration_ms=duration_ms,
                references=references,
                executed_by=executed_by,
                error_message=error_message,
            )
        _release_rule_lock(lock_conn, rule.rule_id)
    return {
        "status": status,
        "condition_met": condition,
        "result": result,
        "references": references,
        "error_message": error_message,
        "duration_ms": duration_ms,
    }

HTTP_TIMEOUT = 5.0

def execute_http_api(session: Session, api_id: str, logic_body: str, params: dict[str, Any] | None, executed_by: str) -> ApiExecuteResponse:
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
        raise HTTPException(status_code=502, detail="External HTTP request failed") from exc
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
