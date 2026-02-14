"""Notification and action dispatch logic for CEP Builder."""

from __future__ import annotations

import hashlib
from time import perf_counter
from typing import Any, Dict, Tuple
from uuid import UUID

import httpx
from core.config import get_settings
from core.db import engine, get_session_context
from fastapi import HTTPException
from models.api_definition import ApiDefinition, ApiMode
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlmodel import Session

from ..crud import record_exec_log
from ..models import TbCepRule
from .metric_executor import _runtime_base_url

DEFAULT_SCRIPT_TIMEOUT_MS = 5000
DEFAULT_OUTPUT_BYTES = 1_048_576
RULE_LOCK_BASE = 424_200_000
RULE_LOCK_MOD = 100_000

_api_cache = None


def _get_api_cache():
    """Get API cache service singleton."""
    global _api_cache
    if _api_cache is None:
        from app.modules.api_manager.cache_service import APICacheService
        _api_cache = APICacheService()
    return _api_cache


def _rule_lock_key(rule_id: UUID) -> int:
    """Generate database lock key for rule."""
    digest = hashlib.md5(rule_id.bytes).digest()
    value = int.from_bytes(digest[:4], "big")
    return RULE_LOCK_BASE + (value % RULE_LOCK_MOD)


def _try_acquire_rule_lock(rule_id: UUID) -> Connection | None:
    """Attempt to acquire distributed lock for rule."""
    conn = engine.connect()
    result = conn.execute(
        text("SELECT pg_try_advisory_lock(:key)"), {"key": _rule_lock_key(rule_id)}
    )
    if result.scalar():
        return conn
    conn.close()
    return None


def _release_rule_lock(conn: Connection, rule_id: UUID) -> None:
    """Release distributed lock for rule."""
    try:
        conn.execute(
            text("SELECT pg_advisory_unlock(:key)"), {"key": _rule_lock_key(rule_id)}
        )
    finally:
        conn.close()


def _execute_webhook_action(
    action_spec: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute HTTP webhook action."""
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


def _execute_api_action(
    action_spec: Dict[str, Any],
    session: Session,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute API Manager action."""
    from app.modules.api_manager.executor import execute_http_api, execute_sql_api
    from app.modules.api_manager.schemas import ApiExecuteResponse
    from app.modules.api_manager.script_executor import execute_script_api
    from app.modules.api_manager.workflow_executor import execute_workflow_api

    api_id = action_spec.get("api_id")
    if not api_id:
        raise HTTPException(status_code=400, detail="api_id is required for api_call action")

    api_def = session.get(ApiDefinition, api_id)
    if not api_def or api_def.deleted_at:
        raise HTTPException(status_code=404, detail=f"API not found: {api_id}")

    params = action_spec.get("params") or {}
    input_payload = action_spec.get("input")
    use_cache = bool(action_spec.get("cache", False))
    cache_ttl = int(action_spec.get("cache_ttl_seconds", 300))

    cache_service = _get_api_cache()
    if use_cache:
        cached = cache_service.get(str(api_id), params)
        if cached is not None:
            refs = {
                "action_type": "api_call",
                "api_id": str(api_id),
                "api_name": api_def.name,
                "mode": api_def.mode.value if api_def.mode else "sql",
                "cache": "hit",
            }
            return cached, refs

    mode = api_def.mode.value if api_def.mode else "sql"
    payload: Dict[str, Any]
    refs: Dict[str, Any] = {
        "action_type": "api_call",
        "api_id": str(api_id),
        "api_name": api_def.name,
        "mode": mode,
        "cache": "miss" if use_cache else "disabled",
    }

    if mode == ApiMode.sql.value:
        result = execute_sql_api(
            session=session,
            api_id=str(api_def.id),
            logic_body=api_def.logic or "",
            params=params,
            limit=params.get("limit") if isinstance(params, dict) else None,
            executed_by="cep-action",
        )
        payload = {"result": ApiExecuteResponse(**result.model_dump()).model_dump()}
    elif mode == ApiMode.http.value:
        result = execute_http_api(
            session=session,
            api_id=str(api_def.id),
            logic_body=api_def.logic or "",
            params=params,
            executed_by="cep-action",
        )
        payload = {"result": ApiExecuteResponse(**result.model_dump()).model_dump()}
    elif mode == ApiMode.workflow.value:
        wf = execute_workflow_api(
            session=session,
            workflow_api=api_def,
            params=params,
            input_payload=input_payload,
            executed_by="cep-action",
            limit=params.get("limit") if isinstance(params, dict) else None,
        )
        payload = {"result": wf.model_dump()}
    elif mode in (ApiMode.script.value, ApiMode.python.value):
        sc = execute_script_api(
            session=session,
            api_id=str(api_def.id),
            logic_body=api_def.logic or "",
            params=params,
            input_payload=input_payload,
            executed_by="cep-action",
            runtime_policy=getattr(api_def, "runtime_policy", None),
        )
        payload = {"result": sc.model_dump()}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported API mode: {mode}")

    if use_cache:
        cache_service.set(str(api_id), params, payload, ttl_seconds=cache_ttl)
    return payload, refs


def _execute_api_script_action(
    action_spec: Dict[str, Any],
    session: Session,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute API Manager script action."""
    from app.modules.api_manager.crud import get_api_definition
    from app.modules.api_manager.script_executor import execute_script_api

    api_id = action_spec.get("api_id")
    if not api_id:
        raise HTTPException(
            status_code=400,
            detail="api_id is required for api_script action"
        )

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

    params = action_spec.get("params") or {}
    input_payload = action_spec.get("input")
    runtime_policy = api_def.runtime_policy or {}

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
    """Trigger another CEP rule."""
    from . import manual_trigger

    target_rule_id = action_spec.get("rule_id")
    if not target_rule_id:
        raise HTTPException(
            status_code=400,
            detail="rule_id is required for trigger_rule action"
        )

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

    trigger_payload = action_spec.get("payload")

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


def execute_action(
    action_spec: Dict[str, Any],
    session: Session | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute action based on type."""
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
    elif action_type == "api_call":
        if not session:
            raise HTTPException(
                status_code=400,
                detail="Database session required for api_call action"
            )
        return _execute_api_action(action_spec, session)
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
