#!/usr/bin/env python3
"""
Register Query Assets directly via SQL.

This script reads SQL query files and registers them in the Asset Registry
with tool_type and operation metadata for dynamic discovery.
Uses direct SQL without importing app modules.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
import yaml

# Get database URL from environment or use default
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/tobit"
)

RESOURCES = Path(__file__).resolve().parent.parent / "resources"


def _load_text(path: Path) -> str:
    """Load text file content."""
    return path.read_text(encoding="utf-8")


def register_query_assets(actor: str = "system") -> None:
    """Register query assets from SQL files."""
    query_root = RESOURCES / "queries"
    if not query_root.exists():
        print(f"Query directory not found: {query_root}")
        return

    # Query asset definitions with metadata
    query_assets = [
        # Metric queries
        {
            "name": "metric_exists",
            "scope": "postgres/metric",
            "description": "Check if a metric exists in metric_def table",
            "tool_type": "metric",
            "operation": "exists",
            "file": "postgres/metric/metric_exists.sql",
        },
        {
            "name": "metric_list",
            "scope": "postgres/metric",
            "description": "List all available metric names",
            "tool_type": "metric",
            "operation": "list",
            "file": "postgres/metric/metric_list.sql",
        },
        {
            "name": "metric_aggregate",
            "scope": "postgres/metric",
            "description": "Aggregate metric values (count, max, min, avg)",
            "tool_type": "metric",
            "operation": "aggregate",
            "file": "postgres/metric/metric_aggregate.sql",
        },
        {
            "name": "metric_aggregate_by_ci",
            "scope": "postgres/metric",
            "description": "Aggregate metric values per CI, returning top N sorted by value",
            "tool_type": "metric",
            "operation": "aggregate_by_ci",
            "file": "postgres/metric/metric_aggregate_by_ci.sql",
        },
        {
            "name": "metric_series",
            "scope": "postgres/metric",
            "description": "Get time series data for a metric",
            "tool_type": "metric",
            "operation": "series",
            "file": "postgres/metric/metric_series.sql",
        },
        # CI queries
        {
            "name": "ci_search",
            "scope": "postgres/ci",
            "description": "Search CI by keywords and filters",
            "tool_type": "ci",
            "operation": "search",
            "file": "postgres/ci/ci_search.sql",
        },
        {
            "name": "ci_get",
            "scope": "postgres/ci",
            "description": "Get CI by ID or code",
            "tool_type": "ci",
            "operation": "get",
            "file": "postgres/ci/ci_get.sql",
        },
        {
            "name": "ci_aggregate_group",
            "scope": "postgres/ci",
            "description": "Aggregate CI with GROUP BY clause",
            "tool_type": "ci",
            "operation": "aggregate_group",
            "file": "postgres/ci/ci_aggregate_group.sql",
        },
        {
            "name": "ci_aggregate_total",
            "scope": "postgres/ci",
            "description": "Aggregate CI without GROUP BY (total counts)",
            "tool_type": "ci",
            "operation": "aggregate_total",
            "file": "postgres/ci/ci_aggregate_total.sql",
        },
        {
            "name": "ci_aggregate_count",
            "scope": "postgres/ci",
            "description": "Count CI matching filters",
            "tool_type": "ci",
            "operation": "aggregate_count",
            "file": "postgres/ci/ci_aggregate_count.sql",
        },
        {
            "name": "ci_list_preview",
            "scope": "postgres/ci",
            "description": "List CI with pagination",
            "tool_type": "ci",
            "operation": "list_preview",
            "file": "postgres/ci/ci_list_preview.sql",
        },
    ]

    with psycopg.connect(DB_URL, autocommit=True) as conn:
        registered_count = 0
        skipped_count = 0
        error_count = 0

        print("="*60)
        print("Importing Query Assets")
        print("="*60)

        for asset_def in query_assets:
            name = asset_def["name"]
            scope = asset_def["scope"]
            file_rel = asset_def["file"]

            print(f"\nProcessing: {name}")

            # Check if already exists
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT asset_id, name, version, status
                    FROM tb_asset_registry
                    WHERE asset_type = 'query'
                    AND name = %s
                    AND scope = %s
                    AND status = 'published'
                    """,
                    (name, scope)
                )
                existing = cur.fetchone()

                if existing:
                    print(f"  ℹ️  Already exists (v{existing['version']}), skipping")
                    skipped_count += 1
                    continue

            # Read SQL file
            sql_file = query_root / file_rel
            if not sql_file.exists():
                print(f"  ⚠️  File not found: {sql_file}")
                error_count += 1
                continue

            sql_content = _load_text(sql_file)

            # Generate UUID for the asset
            asset_id = str(uuid.uuid4())

            # Create asset
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tb_asset_registry (
                        asset_id, asset_type, name, description, scope,
                        query_sql, query_params, query_metadata,
                        status, created_by, published_by, published_at,
                        version, created_at, updated_at
                    ) VALUES (
                        %s, 'query', %s, %s, %s, %s, %s, %s,
                        'published', %s, %s, %s, 1, now(), now()
                    )
                    RETURNING asset_id, version
                    """,
                    (
                        asset_id,
                        name,
                        asset_def.get("description"),
                        scope,
                        sql_content,
                        "{}",
                        psycopg.types.json.Json({
                            "tool_type": asset_def["tool_type"],
                            "operation": asset_def["operation"],
                        }),
                        actor,
                        actor,
                        datetime.now(timezone.utc),
                    )
                )
                result = cur.fetchone()

            print(f"  ✓ Registered (v{result[1]})")
            print(f"     tool_type={asset_def['tool_type']}, operation={asset_def['operation']}")
            registered_count += 1

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Registered: {registered_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"{'='*60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Register Query Assets to Asset Registry via SQL"
    )
    parser.add_argument(
        "--actor",
        default="system",
        help="Actor name for asset creation (default: system)",
    )
    parser.add_argument(
        "--db-url",
        help=f"Database URL (default: {DB_URL})",
    )

    args = parser.parse_args()

    # Use provided DB URL or default
    db_url = args.db_url or DB_URL

    # Register with provided DB URL
    register_query_assets_with_db(actor=args.actor, db_url=db_url)


def register_query_assets_with_db(actor: str, db_url: str) -> None:
    """Register query assets using specific DB URL."""
    global DB_URL
    DB_URL = db_url
    register_query_assets(actor=actor)


if __name__ == "__main__":
    main()
