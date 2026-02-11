#!/usr/bin/env python3
"""
Register Query Assets directly via database.

This script reads SQL query files and registers them in the Asset Registry
with tool_type and operation metadata for dynamic discovery.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

# Find the API root and add to path
SCRIPT_DIR = Path(__file__).resolve().parent
API_ROOT = SCRIPT_DIR.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.modules.asset_registry.models import TbAssetRegistry  # noqa: E402
from core.db import get_session_context  # noqa: E402

RESOURCES = API_ROOT / "resources"


def _load_text(path: Path) -> str:
    """Load text file content."""
    return path.read_text(encoding="utf-8")


def _published_exists(session: Session, asset_type: str, **filters: Any) -> bool:
    """Check if a published asset exists."""
    statement = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == asset_type)
    for key, value in filters.items():
        column = getattr(TbAssetRegistry, key)
        statement = statement.where(column == value)
    statement = statement.where(TbAssetRegistry.status == "published")
    return session.exec(statement).first() is not None


def import_queries(actor: str = "system") -> None:
    """Import query assets from SQL files."""
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

    with get_session_context() as session:
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
            if _published_exists(session, "query", name=name, scope=scope):
                print("  ℹ️  Already exists, skipping")
                skipped_count += 1
                continue

            # Read SQL file
            sql_file = query_root / file_rel
            if not sql_file.exists():
                print(f"  ⚠️  File not found: {sql_file}")
                error_count += 1
                continue

            sql_content = _load_text(sql_file)

            # Create asset
            asset = TbAssetRegistry(
                asset_type="query",
                name=name,
                description=asset_def.get("description"),
                scope=scope,
                query_sql=sql_content,
                query_params={},
                query_metadata={
                    "tool_type": asset_def["tool_type"],
                    "operation": asset_def["operation"],
                },
                status="published",
                created_by=actor,
                published_by=actor,
                published_at=datetime.utcnow(),
                version=1,
            )
            session.add(asset)
            session.flush()

            print(f"  ✓ Registered (v{asset.version})")
            print(f"     tool_type={asset_def['tool_type']}, operation={asset_def['operation']}")
            registered_count += 1

        session.commit()

        print(f"\n{'='*60}")
        print("Summary:")
        print(f"  Registered: {registered_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"{'='*60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Register Query Assets to Asset Registry"
    )
    parser.add_argument(
        "--actor",
        default="system",
        help="Actor name for asset creation (default: system)",
    )

    args = parser.parse_args()

    import_queries(actor=args.actor)


if __name__ == "__main__":
    main()
