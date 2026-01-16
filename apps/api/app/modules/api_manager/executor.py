"""Safe SQL executor used by API Manager MVP-2/MVP-3."""

from __future__ import annotations

from time import perf_counter
from typing import Any
import re
import httpx
import json

from fastapi import HTTPException
from sqlalchemy import text as sa_text
from sqlmodel import Session

from .crud import record_exec_log
from .schemas import ApiExecuteResponse

STATEMENT_TIMEOUT_MS = 3000
BANNED_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "CALL",
    "DO",
}
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

BANNED_PATTERN = re.compile(r"\b(" + "|".join(BANNED_KEYWORDS) + r")\b")

HTTP_TIMEOUT = 5.0

# Template pattern: {{params.field}} or {{params.nested.field}}
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([^}\s]+)\s*}}")

def _resolve_path(source: Any, keys: list[str], error_message: str) -> Any:
    """Resolve nested dictionary/list path for template expressions."""
    current = source
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            raise HTTPException(status_code=400, detail=error_message)
    return current


def _evaluate_http_expression(expression: str, params: dict[str, Any]) -> Any:
    """
    Evaluate HTTP template expressions like {{params.field.nested}}.
    Only 'params' root is supported for HTTP templates.
    """
    parts = expression.split(".")
    if not parts or parts[0] != "params":
        raise HTTPException(
            status_code=400,
            detail=f"HTTP template expression '{expression}' must start with 'params'"
        )

    try:
        return _resolve_path(params, parts[1:], f"missing param for '{expression}'")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Template expression '{expression}' resolution failed: {str(exc)}"
        ) from exc


def _render_http_templates(spec: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """
    Apply {{params.xxx}} template substitution to all string fields in HTTP spec.
    Supports recursive substitution in nested dicts and lists.
    Compatible with workflow_executor template patterns.
    """
    if not spec:
        return spec

    def render_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: render_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [render_value(item) for item in value]
        if isinstance(value, str):
            # Find {{params.xxx}} placeholders
            matches = list(PLACEHOLDER_PATTERN.finditer(value))
            if not matches:
                return value
            # Full expression match: preserve type (e.g., {{params.count}} → 10)
            if len(matches) == 1 and matches[0].group(0).strip() == value.strip():
                return _evaluate_http_expression(matches[0].group(1), params)
            # Partial substitution: convert to string
            def _replace(match: re.Match[str]) -> str:
                resolved = _evaluate_http_expression(match.group(1), params)
                return str(resolved)
            return PLACEHOLDER_PATTERN.sub(_replace, value)
        return value

    return render_value(spec)


def normalize_limit(value: int | None) -> int:
    if value is None:
        return DEFAULT_LIMIT
    if value <= 0:
        return 1
    return min(value, MAX_LIMIT)


def validate_select_sql(sql: str) -> None:
    normalized = sql.strip()
    upper = normalized.upper()
    if ";" in sql:
        raise HTTPException(status_code=400, detail="Semicolons are not allowed")
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise HTTPException(status_code=400, detail="Only SELECT/WITH statements are allowed")
    match = BANNED_PATTERN.search(upper)
    if match:
        raise HTTPException(
            status_code=400,
            detail=f"Forbidden keyword detected: {match.group(0)}",
        )


def execute_sql_api(
    session: Session,
    api_id: str,
    logic_body: str,
    params: dict[str, Any] | None,
    limit: int | None,
    executed_by: str,
) -> ApiExecuteResponse:
    validate_select_sql(logic_body)
    final_limit = normalize_limit(limit)
    bind_params = {**(params or {}), "_limit": final_limit}
    wrapped_sql = f"SELECT * FROM ({logic_body}) AS api_exec_limit LIMIT :_limit"
    start = perf_counter()
    status = "success"
    error_message: str | None = None
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    row_count = 0
    try:
        session.exec(sa_text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT_MS}ms'"))
        result = session.exec(sa_text(wrapped_sql), params=bind_params)
        columns = list(result.keys())
        for record in result:
            row = dict(record._mapping)
            row_count += 1
            rows.append(row)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover (DB errors)
        status = "fail"
        error_message = str(exc)
        raise HTTPException(status_code=500, detail="SQL execution failed") from exc
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        record_exec_log(
            session=session,
            api_id=api_id,
            status=status,
            duration_ms=duration_ms,
            row_count=row_count,
            params=params or {},
            executed_by=executed_by,
            error_message=error_message,
        )
    return ApiExecuteResponse(
        executed_sql=logic_body,
        params=params or {},
        columns=columns,
        rows=rows,
        row_count=row_count,
        duration_ms=duration_ms,
    )


def execute_http_api(session: Session, api_id: str, logic_body: str, params: dict[str, Any] | None, executed_by: str) -> ApiExecuteResponse:
    try:
        spec = json.loads(logic_body) if logic_body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid HTTP logic body") from exc

    # Apply template substitution to spec using runtime params
    final_params = params or {}
    spec = _render_http_templates(spec, final_params)

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
