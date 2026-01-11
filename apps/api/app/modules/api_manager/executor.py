"""Safe SQL executor used by API Manager MVP-2/MVP-3."""

from __future__ import annotations

from time import perf_counter
from typing import Any

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
    for keyword in BANNED_KEYWORDS:
        if keyword in upper:
            raise HTTPException(status_code=400, detail=f"Forbidden keyword detected: {keyword}")


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
        session.exec(sa_text("SET LOCAL statement_timeout = :timeout"), {"timeout": STATEMENT_TIMEOUT_MS})
        result = session.exec(sa_text(wrapped_sql), bind_params)
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
