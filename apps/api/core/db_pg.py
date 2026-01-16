from __future__ import annotations

import psycopg

from .config import AppSettings


def get_pg_connection(settings: AppSettings | None = None) -> psycopg.Connection:
    settings = settings or AppSettings.cached_settings()
    return psycopg.connect(settings.psycopg_dsn)


def test_postgres_connection(settings: AppSettings) -> bool:
    """
    Run a lightweight query to prove that the credentials from settings are valid.
    """
    try:
        with get_pg_connection(settings) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as exc:
        raise RuntimeError("Postgres connection failed") from exc
