"""Runtime router that exposes stored SQL endpoints under /runtime/.*."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Request
from models.api_definition import ApiDefinition
from schemas.common import ResponseEnvelope
from sqlalchemy import select
from sqlmodel import Session

from .executor import execute_http_api, execute_sql_api, normalize_limit, is_http_logic_body
from .script_executor import execute_script_api
from .workflow_executor import execute_workflow_api

runtime_router = APIRouter(tags=["runtime"])

# ---------------------------------------------------------------------------
# In-memory sliding-window rate limiter
# ---------------------------------------------------------------------------
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_REQUESTS = 120  # max per IP per window

_rate_buckets: dict[str, list[float]] = defaultdict(list)
_last_cleanup = time.monotonic()
_CLEANUP_INTERVAL = 300  # prune stale entries every 5 min


def _check_rate_limit(client_ip: str) -> None:
    global _last_cleanup
    now = time.monotonic()

    # Periodic cleanup of stale buckets
    if now - _last_cleanup > _CLEANUP_INTERVAL:
        cutoff = now - RATE_LIMIT_WINDOW_SEC
        stale_keys = [k for k, v in _rate_buckets.items() if not v or v[-1] < cutoff]
        for k in stale_keys:
            del _rate_buckets[k]
        _last_cleanup = now

    bucket = _rate_buckets[client_ip]
    window_start = now - RATE_LIMIT_WINDOW_SEC
    # Remove timestamps outside the window
    while bucket and bucket[0] < window_start:
        bucket.pop(0)

    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SEC}s",
        )
    bucket.append(now)


@runtime_router.api_route("/runtime/{path:path}", methods=["GET", "POST"])
async def handle_runtime_request(
    path: str,
    request: Request,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    normalized_path = _normalize_runtime_path(path)
    api = _find_runtime_api(session, normalized_path, request.method)
    if not api:
        raise HTTPException(status_code=404, detail="Runtime API not found")
    params, raw_limit, input_payload = await _extract_runtime_params(request)
    executed_by = request.headers.get("X-Executed-By") or "anonymous"

    if api.mode == "sql":
        if is_http_logic_body(api.logic):
            result = execute_http_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params=params,
                executed_by=executed_by,
                internal_app=request.app,
            )
            return ResponseEnvelope.success(
                data={
                    "api": {
                        "api_id": str(api.id),
                        "api_name": api.name,
                        "endpoint": api.path,
                        "method": api.method,
                    },
                    "result": {
                        "columns": result.columns,
                        "rows": result.rows,
                        "row_count": result.row_count,
                        "duration_ms": result.duration_ms,
                    },
                    "references": {
                        "http_spec": api.logic,
                        "params": result.params,
                    },
                }
            )
        result = execute_sql_api(
            session=session,
            api_id=str(api.id),
            logic_body=api.logic,
            params=params,
            limit=raw_limit,
            executed_by=executed_by,
        )
        runtime_limit = normalize_limit(raw_limit)
        return ResponseEnvelope.success(
            data={
                "api": {
                    "api_id": str(api.id),
                    "api_name": api.name,
                    "endpoint": api.path,
                    "method": api.method,
                },
                "result": {
                    "columns": result.columns,
                    "rows": result.rows,
                    "row_count": result.row_count,
                    "duration_ms": result.duration_ms,
                },
                "references": {
                    "sql_template": api.logic,
                    "params": result.params,
                    "limit": runtime_limit,
                },
            }
        )
    if api.mode == "workflow":
        workflow_result = execute_workflow_api(
            session=session,
            workflow_api=api,
            params=params,
            input_payload=input_payload,
            executed_by=executed_by,
            limit=raw_limit,
        )
        return ResponseEnvelope.success(
            data={
                "api": {
                    "api_id": str(api.id),
                    "api_name": api.name,
                    "endpoint": api.path,
                    "method": api.method,
                },
                "result": workflow_result.model_dump(),
                "references": workflow_result.references,
            }
        )
    if api.mode in {"script", "python"}:
        script_result = execute_script_api(
            session=session,
            api_id=str(api.id),
            logic_body=api.logic,
            params=params,
            input_payload=input_payload,
            executed_by=executed_by,
            runtime_policy=getattr(api, "runtime_policy", None),
        )
        return ResponseEnvelope.success(
            data={
                "api": {
                    "api_id": str(api.id),
                    "api_name": api.name,
                    "endpoint": api.path,
                    "method": api.method,
                },
                "result": script_result.model_dump(),
                "references": script_result.references,
            }
        )
    if api.mode == "http":
        result = execute_http_api(
            session=session,
            api_id=str(api.id),
            logic_body=api.logic,
            params=params,
            executed_by=executed_by,
            internal_app=request.app,
        )
        return ResponseEnvelope.success(
            data={
                "api": {
                    "api_id": str(api.id),
                    "api_name": api.name,
                    "endpoint": api.path,
                    "method": api.method,
                },
                "result": {
                    "columns": result.columns,
                    "rows": result.rows,
                    "row_count": result.row_count,
                    "duration_ms": result.duration_ms,
                },
                "references": {
                    "http_spec": api.logic,
                    "params": result.params,
                },
            }
        )
    raise HTTPException(status_code=400, detail="Runtime API cannot be executed")


def _normalize_runtime_path(path: str) -> str:
    cleaned = f"/{path.lstrip('/')}"
    if cleaned.startswith("/runtime/"):
        return cleaned
    return f"/runtime{cleaned}"


def _find_runtime_api(
    session: Session, endpoint: str, method: str
) -> ApiDefinition | None:
    cleaned = _normalize_endpoint(endpoint)
    statement = (
        select(ApiDefinition)
        .where(
            ApiDefinition.path.in_(
                [
                    cleaned,
                    f"/runtime{cleaned}",
                    f"/{cleaned.lstrip('/')}",
                ]
            )
        )
        .where(ApiDefinition.method == method)
        .where(ApiDefinition.is_enabled)
        .limit(1)
    )
    api = session.exec(statement).scalars().first()
    if api:
        return api
    return (
        session.exec(
            select(ApiDefinition)
            .where(ApiDefinition.path == cleaned.rstrip("/"))
            .where(ApiDefinition.method == method)
            .where(ApiDefinition.is_enabled)
            .limit(1)
        )
        .scalars()
        .first()
    )


def _normalize_endpoint(endpoint: str) -> str:
    normalized = f"/{endpoint.lstrip('/')}"
    if normalized.startswith("/runtime/"):
        normalized = normalized[len("/runtime") :]
        normalized = f"/{normalized.lstrip('/')}"
    return normalized


async def _extract_runtime_params(
    request: Request,
) -> tuple[dict[str, Any], int | None, Any | None]:
    if request.method == "GET":
        params = {
            key: value for key, value in request.query_params.items() if key != "limit"
        }
        limit_raw = request.query_params.get("limit")
        return params, _parse_limit(limit_raw), None
    else:
        body = await request.json()
        params = body.get("params") or {}
        limit_raw = body.get("limit")
        return params, _parse_limit(limit_raw), body.get("input")


def _parse_limit(limit_raw: Any) -> int | None:
    if limit_raw is None:
        return None
    try:
        return int(limit_raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Limit must be an integer")
