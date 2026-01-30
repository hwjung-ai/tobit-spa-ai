#!/usr/bin/env python3
"""
Automated script to register all OPS assets to the Asset Registry.

This script registers all necessary OPS assets in the correct order:
1. Source Assets (primary_postgres_ops)
2. Query Assets (ci_search, metric_aggregate, event_history, graph_expand)
3. Policy Assets (plan_budget_ops, view_depth_ops)
4. Mapping Assets (graph_relation_ops)
5. Prompt Assets (ops_planner, ops_composer)
6. Schema Catalog (primary_postgres_catalog)

Usage:
  python scripts/register_ops_assets.py [--base-url http://localhost:8000] [--publish] [--cleanup]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]


def print_step(step: int, title: str) -> None:
    """Print a formatted step header."""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {title}")
    print(f"{'='*60}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"✗ {message}")


def register_query_assets(base_url: str, cleanup_drafts: bool = False, publish: bool = True) -> bool:
    """Register query assets for OPS scope."""
    print_step(1, "Registering Query Assets")

    cmd = [
        "python", "scripts/query_asset_importer.py",
        "--scope", "ops",
        "--apply",
        "--base-url", base_url,
    ]

    if cleanup_drafts:
        cmd.append("--cleanup-drafts")

    if publish:
        cmd.append("--publish")

    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=False)
    if result.returncode == 0:
        print_success("Query assets registered")
        return True
    else:
        print_error("Failed to register query assets")
        return False


def register_policy_assets(base_url: str, cleanup_drafts: bool = False, publish: bool = True) -> bool:
    """Register policy assets for OPS scope."""
    print_step(2, "Registering Policy Assets")

    cmd = [
        "python", "scripts/policy_asset_importer.py",
        "--scope", "ops",
        "--apply",
        "--base-url", base_url,
    ]

    if cleanup_drafts:
        cmd.append("--cleanup-drafts")

    if publish:
        cmd.append("--publish")

    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=False)
    if result.returncode == 0:
        print_success("Policy assets registered")
        return True
    else:
        print_error("Failed to register policy assets")
        return False


def register_mapping_assets(base_url: str, cleanup_drafts: bool = False, publish: bool = True) -> bool:
    """Register mapping assets for OPS scope."""
    print_step(3, "Registering Mapping Assets")

    cmd = [
        "python", "scripts/mapping_asset_importer.py",
        "--scope", "ops",
        "--apply",
        "--base-url", base_url,
    ]

    if cleanup_drafts:
        cmd.append("--cleanup-drafts")

    if publish:
        cmd.append("--publish")

    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=False)
    if result.returncode == 0:
        print_success("Mapping assets registered")
        return True
    else:
        print_error("Failed to register mapping assets")
        return False


def register_prompt_assets(base_url: str, cleanup_drafts: bool = False, publish: bool = True) -> bool:
    """Register prompt assets for OPS scope."""
    print_step(4, "Registering Prompt Assets")

    cmd = [
        "python", "scripts/prompt_asset_importer.py",
        "--scope", "ops",
        "--apply",
        "--base-url", base_url,
    ]

    if cleanup_drafts:
        cmd.append("--cleanup-drafts")

    if publish:
        cmd.append("--publish")

    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=False)
    if result.returncode == 0:
        print_success("Prompt assets registered")
        return True
    else:
        print_error("Failed to register prompt assets")
        return False


def register_source_asset(client: httpx.Client, base_url: str, publish: bool = True) -> bool:
    """Register primary_postgres_ops source asset."""
    print_step(5, "Registering Source Assets")

    assets_url = base_url.rstrip("/") + "/asset-registry/assets"

    payload = {
        "asset_type": "source",
        "name": "primary_postgres_ops",
        "description": "Primary PostgreSQL source for OPS queries (env-driven fallback)",
        "scope": "ops",
        "source_type": "postgresql",
        "connection": {
            "host": "${PG_HOST}",
            "port": "${PG_PORT}",
            "username": "${PG_USER}",
            "database": "${PG_DB}",
            "secret_key_ref": "env:PG_PASSWORD",
            "timeout": 30,
            "ssl_mode": "verify-full",
            "connection_params": {}
        },
        "created_by": "ops_asset_registration"
    }

    try:
        response = client.post(assets_url, json=payload)
        if response.status_code != 200:
            print_error(f"Failed to create source asset: {response.status_code} {response.text}")
            return False

        asset_info = response.json().get("data", {}).get("asset", {})
        asset_id = asset_info.get("asset_id")
        print_success(f"Source asset created: {asset_id}")

        if publish and asset_id:
            publish_url = assets_url + f"/{asset_id}/publish"
            publish_response = client.post(
                publish_url,
                json={"published_by": "ops_asset_registration"}
            )
            if publish_response.status_code == 200:
                print_success("Source asset published")
                return True
            else:
                print_error(f"Failed to publish: {publish_response.status_code}")
                return False

        return True
    except Exception as e:
        print_error(f"Exception registering source asset: {e}")
        return False


def register_catalog_asset(client: httpx.Client, base_url: str, publish: bool = True) -> bool:
    """Register primary_postgres_catalog asset."""
    print_step(6, "Registering Schema Catalog Assets")

    assets_url = base_url.rstrip("/") + "/asset-registry/assets"

    payload = {
        "asset_type": "catalog",
        "name": "primary_postgres_catalog",
        "description": "PostgreSQL catalog with table/column metadata for OPS",
        "scope": "ops",
        "source_ref": "primary_postgres_ops",
        "catalog": {
            "name": "primary_postgres_catalog",
            "description": "Placeholder catalog; run scan to populate",
            "source_ref": "primary_postgres_ops",
            "tables": [],
            "scan_status": "pending",
            "scan_metadata": {}
        },
        "created_by": "ops_asset_registration"
    }

    try:
        response = client.post(assets_url, json=payload)
        if response.status_code != 200:
            print_error(f"Failed to create catalog asset: {response.status_code} {response.text}")
            return False

        asset_info = response.json().get("data", {}).get("asset", {})
        asset_id = asset_info.get("asset_id")
        print_success(f"Catalog asset created: {asset_id}")

        if publish and asset_id:
            publish_url = assets_url + f"/{asset_id}/publish"
            publish_response = client.post(
                publish_url,
                json={"published_by": "ops_asset_registration"}
            )
            if publish_response.status_code == 200:
                print_success("Catalog asset published")
                return True
            else:
                print_error(f"Failed to publish: {publish_response.status_code}")
                return False

        return True
    except Exception as e:
        print_error(f"Exception registering catalog asset: {e}")
        return False


def verify_assets(client: httpx.Client, base_url: str) -> bool:
    """Verify all OPS assets are registered and published."""
    print_step(7, "Verifying Registered Assets")

    assets_url = base_url.rstrip("/") + "/asset-registry/assets"

    try:
        response = client.get(assets_url, params={"scope": "ops"})
        if response.status_code != 200:
            print_error(f"Failed to fetch assets: {response.status_code}")
            return False

        data = response.json().get("data", {})
        assets = data.get("assets", [])

        print(f"\nTotal assets found for scope 'ops': {len(assets)}")

        expected_assets = {
            "ci_search": "query",
            "metric_aggregate": "query",
            "event_history": "query",
            "graph_expand": "query",
            "plan_budget_ops": "policy",
            "view_depth_ops": "policy",
            "ops_planner": "prompt",
            "ops_composer": "prompt",
            "primary_postgres_ops": "source",
            "graph_relation_ops": "mapping",
            "primary_postgres_catalog": "catalog",
        }

        found_assets = {}
        for asset in assets:
            name = asset.get("name")
            if name in expected_assets:
                found_assets[name] = asset

        print("\nAsset Status Summary:")
        print("-" * 60)

        all_published = True
        for asset_name, expected_type in expected_assets.items():
            if asset_name in found_assets:
                asset = found_assets[asset_name]
                status = asset.get("status")
                asset_type = asset.get("asset_type")
                version = asset.get("version")

                status_icon = "✓" if status == "published" else "⚠"
                type_match = "✓" if asset_type == expected_type else "✗"

                print(f"{status_icon} {asset_name:<30} {asset_type:<10} v{version} {status}")

                if status != "published":
                    all_published = False
            else:
                print(f"✗ {asset_name:<30} NOT FOUND")
                all_published = False

        print("-" * 60)

        if all_published and len(found_assets) == len(expected_assets):
            print_success("All OPS assets are registered and published!")
            return True
        else:
            print_error("Some assets are missing or not published")
            return False

    except Exception as e:
        print_error(f"Exception verifying assets: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register all OPS assets to the Asset Registry"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running API server"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        default=True,
        help="Publish assets immediately (default: True)"
    )
    parser.add_argument(
        "--no-publish",
        dest="publish",
        action="store_false",
        help="Do not publish assets after creating"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up existing draft assets before registering"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("OPS Asset Registration Script")
    print("=" * 60)
    print(f"API Server: {args.base_url}")
    print(f"Publish: {args.publish}")
    print(f"Cleanup Drafts: {args.cleanup}")

    # Check API connectivity
    try:
        client = httpx.Client(timeout=30.0)
        health_response = client.get(f"{args.base_url.rstrip('/')}/health")
        if health_response.status_code != 200:
            print_error("API server is not responding correctly")
            return 1
        print_success("API server is accessible")
    except Exception as e:
        print_error(f"Failed to connect to API server: {e}")
        return 1

    # Register assets in order
    results = []

    # 1. Query assets
    results.append(("Query Assets", register_query_assets(
        args.base_url, args.cleanup, args.publish
    )))

    # 2. Policy assets
    results.append(("Policy Assets", register_policy_assets(
        args.base_url, args.cleanup, args.publish
    )))

    # 3. Mapping assets
    results.append(("Mapping Assets", register_mapping_assets(
        args.base_url, args.cleanup, args.publish
    )))

    # 4. Prompt assets
    results.append(("Prompt Assets", register_prompt_assets(
        args.base_url, args.cleanup, args.publish
    )))

    # 5. Source assets
    results.append(("Source Assets", register_source_asset(
        client, args.base_url, args.publish
    )))

    # 6. Catalog assets
    results.append(("Catalog Assets", register_catalog_asset(
        client, args.base_url, args.publish
    )))

    # 7. Verify all assets
    verify_success = verify_assets(client, args.base_url)
    results.append(("Verification", verify_success))

    client.close()

    # Summary
    print("\n" + "=" * 60)
    print("REGISTRATION SUMMARY")
    print("=" * 60)

    all_success = True
    for step_name, success in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{step_name:<30} {status}")
        if not success:
            all_success = False

    print("=" * 60)

    if all_success:
        print("\nAll OPS assets have been successfully registered and published!")
        print("\nYou can now use OPS queries:")
        print("  - ci_search: Search for configuration items")
        print("  - metric_aggregate: Aggregate metrics by group")
        print("  - event_history: Retrieve operational event logs")
        print("  - graph_expand: Expand graph relationships")
        print("\nWith policies:")
        print("  - plan_budget_ops: Plan execution budget constraints")
        print("  - view_depth_ops: Graph view depth constraints")
        print("\nAnd prompts:")
        print("  - ops_planner: Generate execution plans")
        print("  - ops_composer: Compose operational insights")
        return 0
    else:
        print("\nSome assets failed to register. Please check the errors above.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
