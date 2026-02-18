from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from psycopg import Connection

from app.modules.asset_registry.loader import load_policy_asset, load_source_asset
from app.modules.ops.services.connections import ConnectionFactory

# System-required policy asset name (hardcoded - not configurable)
DISCOVERY_POLICY_NAME = "discovery_config"

CATALOG_DIR = Path(__file__).resolve().parents[1] / "catalog"
OUTPUT_PATH = CATALOG_DIR / "postgres_catalog.json"

# Default configuration (overridden by policy asset)
_DEFAULT_TARGET_TABLES = ["ci", "ci_ext"]
_DEFAULT_AGG_COLUMNS = [
    "ci_type",
    "ci_subtype",
    "ci_category",
    "status",
    "location",
    "owner",
]

# Cache for discovery config
_DISCOVERY_CONFIG_CACHE: Dict[str, Any] | None = None


def _get_discovery_config() -> Dict[str, Any]:
    """Load PostgreSQL discovery configuration from policy asset."""
    global _DISCOVERY_CONFIG_CACHE
    if _DISCOVERY_CONFIG_CACHE is not None:
        return _DISCOVERY_CONFIG_CACHE

    try:
        policy = load_policy_asset(DISCOVERY_POLICY_NAME)
        if policy:
            content = policy.get("content", {})
            pg_config = content.get("postgres", {})
            if pg_config:
                _DISCOVERY_CONFIG_CACHE = {
                    "target_tables": pg_config.get("target_tables", _DEFAULT_TARGET_TABLES),
                    "agg_columns": pg_config.get("agg_columns", _DEFAULT_AGG_COLUMNS),
                    "queries": pg_config.get("queries", {}),
                }
                return _DISCOVERY_CONFIG_CACHE
    except Exception as e:
        pass  # Fall through to defaults

    _DISCOVERY_CONFIG_CACHE = {
        "target_tables": _DEFAULT_TARGET_TABLES,
        "agg_columns": _DEFAULT_AGG_COLUMNS,
        "queries": {},
    }
    return _DISCOVERY_CONFIG_CACHE


def _get_connection():
    """Get connection using an explicitly provided source asset."""
    source_ref = os.environ.get("OPS_SOURCE_ASSET")
    if not source_ref:
        raise ValueError("OPS_SOURCE_ASSET is required")
    source_asset = load_source_asset(source_ref)
    if not source_asset:
        raise ValueError(f"Source asset not found: {source_ref}")
    return ConnectionFactory.create(source_asset)


def _load_query(name: str) -> str:
    """Load discovery query from Policy Asset.

    Discovery queries are stored in Policy Assets with policy_type from DISCOVERY_POLICY_NAME.
    The policy content should have a 'postgres.queries' dict mapping query names to query strings.
    """
    query_name = Path(name).stem
    config = _get_discovery_config()
    queries = config.get("queries", {})
    query = queries.get(query_name) or queries.get(name)
    if query:
        return query

    raise ValueError(
        f"Discovery query '{query_name}' not found. "
        f"Please add it to policy asset '{DISCOVERY_POLICY_NAME}' "
        f"under content.postgres.queries.{query_name}"
    )


def _mask_sensitive(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _exit_error(message: str) -> None:
    print(f"[postgres_catalog] ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _build_environment_context() -> dict[str, str | None]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "pg_host": _mask_sensitive(os.environ.get("PG_HOST")),
        "pg_db": _mask_sensitive(os.environ.get("PG_DB")),
        "pg_user": _mask_sensitive(os.environ.get("PG_USER")),
    }


def _fetch_columns(conn: Connection) -> list[dict[str, str]]:
    with conn.cursor() as cur:
        columns_query = _load_query("postgres_catalog_columns.sql")
        cur.execute(columns_query)
        return [
            {
                "table_name": table_name,
                "column_name": column_name,
                "data_type": data_type,
                "is_nullable": is_nullable,
            }
            for table_name, column_name, data_type, is_nullable in cur.fetchall()
        ]


def _fetch_table_row_count(conn: Connection, table: str) -> int:
    with conn.cursor() as cur:
        count_query = _load_query("postgres_catalog_table_count.sql").format(
            table=table
        )
        cur.execute(count_query)
        return cur.fetchone()[0]


def _fetch_aggregation(
    conn: Connection, column: str, limit: int = 50
) -> list[dict[str, int | str | None]]:
    with conn.cursor() as cur:
        agg_query = _load_query("postgres_catalog_aggregation.sql").format(
            column=column
        )
        cur.execute(agg_query, (limit,))
        return [{"value": value, "count": cnt} for value, cnt in cur.fetchall()]


def _format_sample_value(value: str | None) -> str:
    if value is None:
        return "<null>"
    text = str(value)
    if text == "":
        return "<empty>"
    if len(text) > 200:
        return f"{text[:200]}...(truncated)"
    return text


def _sample_jsonb_values(
    conn: Connection, column: str, key: str, limit: int = 5
) -> list[str]:
    with conn.cursor() as cur:
        sample_query = _load_query("postgres_catalog_jsonb_sample.sql").format(
            column=column
        )
        cur.execute(sample_query, (key, key, limit))
        return [_format_sample_value(row[0]) for row in cur.fetchall()]


def _collect_jsonb_key_stats(conn: Connection, column: str) -> list[dict[str, object]]:
    with conn.cursor() as cur:
        stats_query = _load_query("postgres_catalog_jsonb_key_stats.sql").format(
            column=column
        )
        cur.execute(stats_query)
        results: list[dict[str, object]] = []
        for key, cnt in cur.fetchall():
            samples = _sample_jsonb_values(conn, column, key)
            results.append(
                {
                    "key": key,
                    "count": cnt,
                    "sample_values": samples,
                }
            )
        return results


def _build_catalog(conn: Connection) -> dict[str, object]:
    config = _get_discovery_config()
    target_tables = config.get("target_tables", _DEFAULT_TARGET_TABLES)
    agg_columns = config.get("agg_columns", _DEFAULT_AGG_COLUMNS)

    columns = _fetch_columns(conn)
    available_columns = {
        col["column_name"] for col in columns if col["table_name"] == "ci"
    }
    stats: dict[str, object] = {}
    tenant_counts: list[dict[str, int | str | None]] = []
    if "tenant_id" in available_columns:
        tenant_counts = _fetch_aggregation(conn, "tenant_id")
    try:
        total = _fetch_table_row_count(conn, "ci")
    except Exception:  # pragma: no cover - best effort
        raise
    stats["ci_counts"] = {
        "total": total,
        "tenant_counts": tenant_counts,
        "breakdowns": {},
    }
    for column in agg_columns:
        if column in available_columns:
            stats["ci_counts"]["breakdowns"][column] = _fetch_aggregation(conn, column)
    jsonb_catalog = {
        "tags_keys": _collect_jsonb_key_stats(conn, "tags"),
        "attributes_keys": _collect_jsonb_key_stats(conn, "attributes"),
    }
    table_row_counts = {
        table: _fetch_table_row_count(conn, table) for table in target_tables
    }
    return {
        "schema": {"columns": columns},
        "stats": stats,
        "jsonb_catalog": jsonb_catalog,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "table_row_counts": table_row_counts,
            "environment": _build_environment_context(),
        },
    }


def _write_catalog(payload: dict[str, object]) -> None:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def main() -> None:
    try:
        connection = _get_connection()
        try:
            conn = connection.connection if hasattr(connection, 'connection') else connection
            catalog = _build_catalog(conn)
            _write_catalog(catalog)
            print(f"Wrote Postgres catalog to {OUTPUT_PATH}")
        finally:
            connection.close()

    except Exception as exc:
        _exit_error(str(exc))


if __name__ == "__main__":
    main()
