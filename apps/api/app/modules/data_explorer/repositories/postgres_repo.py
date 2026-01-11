from __future__ import annotations

from typing import Any, Iterable

import psycopg
from psycopg import sql

from core.config import AppSettings
from core.db_pg import get_pg_connection


def list_tables(settings: AppSettings, schemas: Iterable[str]) -> list[tuple[str, str]]:
    query = """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema = ANY(%s)
        ORDER BY table_schema, table_name
    """
    with get_pg_connection(settings) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (list(schemas),))
            return cursor.fetchall()


def preview_table(
    settings: AppSettings,
    schema: str,
    table: str,
    limit: int,
    timeout_ms: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    statement = sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
        sql.Identifier(schema),
        sql.Identifier(table),
    )
    with get_pg_connection(settings) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
            cursor.execute(statement, (limit,))
            columns = [col.name for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return columns, rows


def execute_query(
    settings: AppSettings,
    sql_text: str,
    timeout_ms: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        with get_pg_connection(settings) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                cursor.execute(sql_text)
                columns = [col.name for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return columns, rows
    except psycopg.Error as exc:
        raise ValueError(str(exc))
