from __future__ import annotations

import os
from typing import Any

import psycopg
from app.modules.asset_registry.loader import load_source_asset

from .config import AppSettings


def _resolve_secret(secret_ref: str | None) -> str | None:
    if not secret_ref:
        return None
    if secret_ref.startswith("env:"):
        key = secret_ref.split(":", 1)[1]
        return os.environ.get(key)
    return None


def _build_dsn_from_source(source_payload: dict[str, Any]) -> str | None:
    connection = source_payload.get("connection") or {}
    host = connection.get("host")
    port = connection.get("port") or 5432
    user = connection.get("username")
    database = connection.get("database")

    # Resolve password using multiple methods (same order as ConnectionFactory)
    # 1. secret_key_ref (env:VARIABLE_NAME)
    # 2. password_encrypted
    # 3. direct password (for testing/dev)
    password = (
        _resolve_secret(connection.get("secret_key_ref"))
        or connection.get("password_encrypted")
        or connection.get("password")
    )

    if not host or not user or not database:
        return None

    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return f"postgresql://{user}@{host}:{port}/{database}"


def get_pg_connection(
    settings: AppSettings | None = None,
    use_source_asset: bool = False,
    source_ref: str | None = None,
) -> psycopg.Connection:
    """
    Get PostgreSQL connection.

    Args:
        settings: Application settings
        use_source_asset: If True, use source asset from DB (for OPS operations).
                         If False (default), use direct env vars (for system operations).
    """
    settings = settings or AppSettings.cached_settings()
    if use_source_asset:
        if not source_ref:
            raise ValueError("source_ref is required when use_source_asset=True")
        source_payload = load_source_asset(source_ref)
        if not source_payload:
            raise ValueError(f"Source asset not found: {source_ref}")
        dsn = _build_dsn_from_source(source_payload)
        if not dsn:
            raise ValueError(
                f"Invalid source asset connection configuration: {source_ref}"
            )
        return psycopg.connect(dsn, options="-c timezone=UTC")
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
