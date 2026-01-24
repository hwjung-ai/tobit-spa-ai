from __future__ import annotations

from typing import Any

from core.config import AppSettings, get_settings
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.common import ResponseEnvelope

from app.modules.data_explorer.schemas import (
    Neo4jQueryRequest,
    PostgresQueryRequest,
    RedisCommandRequest,
)
from app.modules.data_explorer.services import (
    neo4j_service,
    postgres_service,
    redis_service,
)

router = APIRouter(prefix="/data", tags=["data"])


def _require_enabled(settings: AppSettings) -> None:
    if not settings.enable_data_explorer:
        raise HTTPException(status_code=404, detail="Data explorer disabled")


@router.get(
    "/postgres/tables",
    summary="List Postgres tables",
    description=(
        "Read-only table/catalog browse for allowlisted schemas (tb_cep_*, ci, event_log). "
        "No data rows returned; only names/types are exposed."
    ),
)
def list_postgres_tables(
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        tables = postgres_service.list_tables(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"tables": tables})


@router.get(
    "/postgres/preview",
    summary="Preview Postgres rows",
    description=(
        "SELECT * FROM the allowlisted table with LIMIT 200 and timeout enforced (default 3s). "
        "Read-only preview; any non-SELECT or large tables are blocked."
    ),
)
def preview_postgres_table(
    table: str = Query(..., min_length=1),
    limit: int | None = Query(None, ge=1),
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        columns, rows = postgres_service.preview_table(settings, table, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"columns": columns, "rows": rows})


@router.post(
    "/postgres/query",
    summary="Run Postgres read-only query",
    description=(
        "Read-only SQL execution (SELECT-only, no DDL/DML). "
        "LIMIT 200 is enforced and the allowlist restricts schemas to tb_cep_*, event_log, ci. "
        "Statement timeout defaults to 3 seconds."
    ),
)
def query_postgres(
    payload: PostgresQueryRequest,
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        columns, rows = postgres_service.run_query(settings, payload.sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"columns": columns, "rows": rows})


@router.get(
    "/neo4j/labels",
    summary="List Neo4j labels",
    description="Read-only label list for Neo4j. Used to seed the Browse tab.",
)
def list_neo4j_labels(
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        labels = neo4j_service.list_labels(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"labels": labels})


@router.post(
    "/neo4j/query",
    summary="Run Neo4j read-only query",
    description=(
        "Cypher read-only execution. Only MATCH/RETURN clauses are allowed, LIMIT 200 enforced, "
        "write keywords such as CREATE/MERGE/DELETE/SET/CALL are forbidden."
    ),
)
def query_neo4j(
    payload: Neo4jQueryRequest,
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        columns, rows = neo4j_service.run_query(
            settings, payload.cypher, payload.params
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"columns": columns, "rows": rows})


@router.get(
    "/redis/scan",
    summary="Scan Redis keys",
    description=(
        "Read-only SCAN from allowlisted prefixes (cep:, etc.). "
        "Cursor/count controls pagination with TTL and type metadata."
    ),
)
def scan_redis_keys(
    prefix: str = Query(..., min_length=1),
    pattern: str | None = Query(None),
    cursor: int = Query(0, ge=0),
    count: int = Query(50, ge=1, le=500),
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        payload = redis_service.scan(settings, prefix, pattern or "", cursor, count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data=payload)


@router.get(
    "/redis/key",
    summary="Inspect Redis key",
    description="Returns key type, TTL, and entries (GET/HGETALL/SCAN depending on type). Read-only.",
)
def get_redis_key(
    key: str = Query(..., min_length=1),
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        payload = redis_service.get_key(settings, key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data=payload)


@router.post(
    "/redis/command",
    summary="Run Redis read-only command",
    description=(
        "Executes a safe Redis command (GET/HGETALL/SCAN/ZRANGE/etc.) confined to allowlisted prefixes. "
        "Writes, DEL, FLUSH, CONFIG, EVAL are forbidden."
    ),
)
def command_redis(
    payload: RedisCommandRequest,
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    _require_enabled(settings)
    try:
        result: Any = redis_service.run_command(settings, payload.command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ResponseEnvelope.success(data={"result": result})
