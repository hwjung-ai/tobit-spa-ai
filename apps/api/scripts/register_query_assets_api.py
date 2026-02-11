#!/usr/bin/env python3
"""
Register Query Assets to Asset Registry using HTTP API.

This script reads SQL query files and registers them in the Asset Registry
with tool_type and operation metadata for dynamic discovery.
"""

import argparse
from pathlib import Path

import httpx

# Find the resources directory
SCRIPT_DIR = Path(__file__).resolve().parent
# Resources are at apps/api/resources/
QUERY_ROOT = SCRIPT_DIR.parent / "resources" / "queries"


# Query asset definitions with metadata
QUERY_ASSETS = [
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


def read_sql_file(file_path: Path) -> str:
    """Read SQL file content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def register_via_api(
    api_url: str = "http://localhost:8000",
    publish: bool = False,
    force: bool = False,
) -> None:
    """Register query assets via HTTP API."""
    registered_count = 0
    skipped_count = 0
    error_count = 0

    for asset_def in QUERY_ASSETS:
        name = asset_def["name"]
        scope = asset_def["scope"]
        file_rel = asset_def["file"]

        # Read SQL file
        sql_file = QUERY_ROOT / file_rel
        if not sql_file.exists():
            print(f"⚠️  File not found: {sql_file}")
            skipped_count += 1
            continue

        sql_content = read_sql_file(sql_file)

        # Prepare payload
        payload = {
            "asset_type": "query",
            "name": name,
            "scope": scope,
            "description": asset_def.get("description"),
            "status": "published" if publish else "draft",
            "query_sql": sql_content,
            "query_metadata": {
                "tool_type": asset_def["tool_type"],
                "operation": asset_def["operation"],
            },
        }

        print(f"\n{'='*60}")
        print(f"Processing: {name}")
        print(f"  scope: {scope}")
        print(f"  tool_type: {asset_def['tool_type']}")
        print(f"  operation: {asset_def['operation']}")

        try:
            with httpx.Client(timeout=30.0) as client:
                # Try to create the asset
                response = client.post(f"{api_url}/api/assets/", json=payload)

                if response.status_code == 200:
                    result = response.json()
                    print(f"  ✓ Created: {result.get('asset_id')}")
                    registered_count += 1
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "")
                    if "already exists" in error_detail.lower() or "duplicate" in error_detail.lower():
                        print("  ℹ️  Already exists, skipping")
                        skipped_count += 1
                    else:
                        print(f"  ⚠️  Error: {error_detail}")
                        error_count += 1
                else:
                    print(f"  ⚠️  HTTP {response.status_code}: {response.text[:200]}")
                    error_count += 1

        except httpx.ConnectError:
            print(f"  ⚠️  Could not connect to API at {api_url}")
            print("     Make sure the API server is running")
            error_count += 1
            break
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
            error_count += 1

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Registered: {registered_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Register Query Assets to Asset Registry via API"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish assets immediately",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be registered without actually doing it",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - Would register the following assets:")
        for asset in QUERY_ASSETS:
            print(f"\n  {asset['name']}")
            print(f"    scope: {asset['scope']}")
            print(f"    tool_type: {asset['tool_type']}")
            print(f"    operation: {asset['operation']}")
        return

    register_via_api(api_url=args.api_url, publish=args.publish)


if __name__ == "__main__":
    main()
