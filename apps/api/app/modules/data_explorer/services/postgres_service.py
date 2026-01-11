from __future__ import annotations

import fnmatch
import re
from typing import Any

from core.config import AppSettings
from app.modules.data_explorer.repositories import postgres_repo


_FORBIDDEN_SQL = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "copy",
)


def _normalize_patterns(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_table_allowed(schema: str, table: str, settings: AppSettings) -> bool:
    schema_allowed = _normalize_patterns(settings.data_pg_allow_schemas)
    table_allowed = _normalize_patterns(settings.data_pg_allow_tables)
    if schema_allowed and not any(fnmatch.fnmatch(schema, pattern) for pattern in schema_allowed):
        return False
    if table_allowed and not any(fnmatch.fnmatch(table, pattern) for pattern in table_allowed):
        return False
    return True


def list_tables(settings: AppSettings) -> list[dict[str, str]]:
    schemas = _normalize_patterns(settings.data_pg_allow_schemas) or ["public"]
    rows = postgres_repo.list_tables(settings, schemas)
    return [
        {"schema": schema, "table": table}
        for schema, table in rows
        if _is_table_allowed(schema, table, settings)
    ]


def preview_table(
    settings: AppSettings,
    table: str,
    limit: int | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    schema, name = _split_table(table, settings)
    if not _is_table_allowed(schema, name, settings):
        raise ValueError("Table is not in allowlist")
    limit_value = _bounded_limit(limit, settings)
    return postgres_repo.preview_table(
        settings,
        schema,
        name,
        limit_value,
        settings.data_query_timeout_ms,
    )


def run_query(
    settings: AppSettings,
    sql_text: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    normalized = _sanitize_sql(sql_text)
    _ensure_allowed_tables(normalized, settings)
    sql_text = _ensure_limit(normalized, settings.data_max_rows)
    return postgres_repo.execute_query(
        settings,
        sql_text,
        settings.data_query_timeout_ms,
    )


def _split_table(table: str, settings: AppSettings) -> tuple[str, str]:
    parts = [part.strip() for part in table.split(".") if part.strip()]
    if len(parts) == 1:
        default_schema = _normalize_patterns(settings.data_pg_allow_schemas) or ["public"]
        return default_schema, parts[0]
    if len(parts) == 2:
        return parts[0], parts[1]
    raise ValueError("Invalid table name")


def _sanitize_sql(value: str) -> str:
    sql_text = value.strip().rstrip(";")
    lowered = sql_text.lower()
    if not lowered.startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed")
    if ";" in sql_text:
        raise ValueError("Multiple SQL statements are not allowed")
    if any(re.search(rf"\\b{keyword}\\b", lowered) for keyword in _FORBIDDEN_SQL):
        raise ValueError("Forbidden SQL keyword detected")
    return sql_text


def _ensure_allowed_tables(sql_text: str, settings: AppSettings) -> None:
    if not settings.data_pg_allow_tables:
        return
    pattern = re.compile(r"\b(from|join)\s+([a-zA-Z0-9_\".]+)", re.IGNORECASE)
    matches = pattern.findall(sql_text)
    for _, table_expr in matches:
        table_name = table_expr.strip().strip('"')
        if table_name.startswith("("):
            continue
        parts = table_name.split(".")
        if len(parts) == 1:
            schema = (_normalize_patterns(settings.data_pg_allow_schemas) or ["public"])[0]
            table = parts[0]
        else:
            schema, table = parts[0], parts[1]
        if not _is_table_allowed(schema, table, settings):
            raise ValueError(f"Table not allowed: {schema}.{table}")


def _ensure_limit(sql_text: str, limit: int) -> str:
    if re.search(r"\blimit\b", sql_text, re.IGNORECASE):
        return sql_text
    return f"{sql_text} LIMIT {limit}"


def _bounded_limit(limit: int | None, settings: AppSettings) -> int:
    if limit is None:
        return settings.data_max_rows
    return max(1, min(limit, settings.data_max_rows))
