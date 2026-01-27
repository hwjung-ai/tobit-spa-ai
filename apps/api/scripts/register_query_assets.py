#!/usr/bin/env python3
"""
Register Query Assets to Asset Registry with tool_type and operation metadata.

This script reads SQL query files from resources/queries/ and registers them
in the Asset Registry database with appropriate metadata for dynamic discovery.

The query_metadata includes:
- tool_type: Which tool uses this query (e.g., "metric", "ci")
- operation: Which operation this query supports (e.g., "aggregate_by_ci", "search")

After registration, tools can use QueryAssetRegistry to dynamically discover
and use queries without hardcoding filenames.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# Add apps/api to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import yaml
from sqlmodel import Session, select

from core.db import engine
from app.modules.asset_registry.models import TbAssetRegistry
from app.shared.config_loader import load_text


# Query asset definitions with metadata
QUERY_ASSETS: List[Dict[str, any]] = [
    # Metric queries
    {
        "name": "metric_exists",
        "scope": "postgres/metric",
        "description": "Check if a metric exists in metric_def table",
        "tool_type": "metric",
        "operation": "exists",
        "file": "queries/postgres/metric/metric_exists.sql",
    },
    {
        "name": "metric_list",
        "scope": "postgres/metric",
        "description": "List all available metric names",
        "tool_type": "metric",
        "operation": "list",
        "file": "queries/postgres/metric/metric_list.sql",
    },
    {
        "name": "metric_aggregate",
        "scope": "postgres/metric",
        "description": "Aggregate metric values (count, max, min, avg)",
        "tool_type": "metric",
        "operation": "aggregate",
        "file": "queries/postgres/metric/metric_aggregate.sql",
    },
    {
        "name": "metric_aggregate_by_ci",
        "scope": "postgres/metric",
        "description": "Aggregate metric values per CI, returning top N sorted by value",
        "tool_type": "metric",
        "operation": "aggregate_by_ci",
        "file": "queries/postgres/metric/metric_aggregate_by_ci.sql",
    },
    {
        "name": "metric_series",
        "scope": "postgres/metric",
        "description": "Get time series data for a metric",
        "tool_type": "metric",
        "operation": "series",
        "file": "queries/postgres/metric/metric_series.sql",
    },
    # CI queries
    {
        "name": "ci_search",
        "scope": "postgres/ci",
        "description": "Search CI by keywords and filters",
        "tool_type": "ci",
        "operation": "search",
        "file": "queries/postgres/ci/ci_search.sql",
    },
    {
        "name": "ci_get",
        "scope": "postgres/ci",
        "description": "Get CI by ID or code",
        "tool_type": "ci",
        "operation": "get",
        "file": "queries/postgres/ci/ci_get.sql",
    },
    {
        "name": "ci_aggregate_group",
        "scope": "postgres/ci",
        "description": "Aggregate CI with GROUP BY clause",
        "tool_type": "ci",
        "operation": "aggregate_group",
        "file": "queries/postgres/ci/ci_aggregate_group.sql",
    },
    {
        "name": "ci_aggregate_total",
        "scope": "postgres/ci",
        "description": "Aggregate CI without GROUP BY (total counts)",
        "tool_type": "ci",
        "operation": "aggregate_total",
        "file": "queries/postgres/ci/ci_aggregate_total.sql",
    },
    {
        "name": "ci_aggregate_count",
        "scope": "postgres/ci",
        "description": "Count CI matching filters",
        "tool_type": "ci",
        "operation": "aggregate_count",
        "file": "queries/postgres/ci/ci_aggregate_count.sql",
    },
    {
        "name": "ci_list_preview",
        "scope": "postgres/ci",
        "description": "List CI with pagination",
        "tool_type": "ci",
        "operation": "list_preview",
        "file": "queries/postgres/ci/ci_list_preview.sql",
    },
]


def get_or_create_query_asset(
    session: Session,
    name: str,
    scope: str,
) -> TbAssetRegistry | None:
    """
    Get existing query asset or create a new one.

    Args:
        session: Database session
        name: Asset name
        scope: Asset scope

    Returns:
        TbAssetRegistry instance or None
    """
    # Check for existing published asset
    query = (
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "query")
        .where(TbAssetRegistry.scope == scope)
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    )
    existing = session.exec(query).first()

    if existing:
        return existing

    # Check for any draft asset
    query = query.where(TbAssetRegistry.status == "draft")
    draft = session.exec(query).first()

    if draft:
        return draft

    # Create new asset
    asset = TbAssetRegistry(
        asset_type="query",
        name=name,
        scope=scope,
        status="draft",
        version=1,
    )
    session.add(asset)
    session.flush()
    return asset


def register_query_assets(
    publish: bool = False,
    force_update: bool = False,
) -> None:
    """
    Register query assets to the Asset Registry.

    Args:
        publish: If True, mark assets as published
        force_update: If True, update existing assets
    """
    with Session(engine) as session:
        registered_count = 0
        updated_count = 0
        skipped_count = 0

        for asset_def in QUERY_ASSETS:
            name = asset_def["name"]
            scope = asset_def["scope"]
            file_path = asset_def["file"]

            print(f"\nProcessing: {name}")

            # Load SQL file
            sql_content = load_text(file_path)
            if not sql_content:
                print(f"  ⚠️  File not found: {file_path}")
                skipped_count += 1
                continue

            # Get or create asset
            asset = get_or_create_query_asset(session, name, scope)
            if not asset:
                print(f"  ⚠️  Could not create asset")
                skipped_count += 1
                continue

            # Check if asset needs update
            if not force_update and asset.query_sql:
                print(f"  ℹ️  Already exists (v{asset.version}), skipping")
                skipped_count += 1
                continue

            # Update asset fields
            asset.description = asset_def.get("description")
            asset.query_sql = sql_content
            asset.query_metadata = {
                "tool_type": asset_def["tool_type"],
                "operation": asset_def["operation"],
            }
            asset.status = "published" if publish else "draft"

            session.add(asset)
            registered_count += 1
            print(f"  ✓ Registered (v{asset.version})")
            print(f"     tool_type={asset_def['tool_type']}, operation={asset_def['operation']}")

        # Commit changes
        session.commit()

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Registered: {registered_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"{'='*60}")

        if publish:
            print(f"\n✅ Assets published and ready for use!")
        else:
            print(f"\n⚠️  Assets created as DRAFT.")
            print(f"   Use --publish to publish them or publish via Admin UI.")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Register Query Assets to Asset Registry"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish assets (mark as published instead of draft)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update existing assets",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check existing query assets in database",
    )

    args = parser.parse_args()

    if args.check:
        # Check existing assets
        with Session(engine) as session:
            query = (
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "query")
                .order_by(TbAssetRegistry.scope, TbAssetRegistry.name)
            )
            assets = session.exec(query).all()

            print(f"\nExisting Query Assets ({len(assets)}):")
            print(f"{'-'*60}")
            for asset in assets:
                metadata = asset.query_metadata or {}
                tool_type = metadata.get("tool_type", "-")
                operation = metadata.get("operation", "-")
                print(
                    f"  {asset.scope:20} | {asset.name:30} | "
                    f"{tool_type:10} | {operation:20} | {asset.status}"
                )
        return

    register_query_assets(publish=args.publish, force_update=args.force)


if __name__ == "__main__":
    main()
