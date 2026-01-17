#!/usr/bin/env python3
"""
Utility for migrating seed Query files under apps/api/resources/queries into the Asset Registry.

Usage:
  python scripts/query_asset_importer.py --scope ci --apply --publish
  python scripts/query_asset_importer.py --scope ci --apply --cleanup-drafts  (delete drafts only)

Run with --apply once the API server is running so assets are actually created and published.

Flags:
  --cleanup-drafts: Delete existing draft assets. When used alone, only deletes drafts without creating new assets.
  --publish: Publish assets immediately after creating them (requires --apply).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUERY_ROOT = REPO_ROOT / "apps/api/resources/queries"

def collect_query_files(scopes: list[str]) -> list[tuple[Path, Path]]:
    """Collect query YAML metadata files.

    Returns list of (yaml_file, sql_file) tuples.
    """
    files: list[tuple[Path, Path]] = []
    if not QUERY_ROOT.exists():
        raise RuntimeError(f"Query directory not found: {QUERY_ROOT}")

    for db_dir in sorted(QUERY_ROOT.iterdir()):
        if not db_dir.is_dir():
            continue
        for scope_dir in sorted(db_dir.iterdir()):
            if not scope_dir.is_dir():
                continue
            if scopes and scope_dir.name not in scopes:
                continue
            for yaml_file in sorted(scope_dir.glob("*.yaml")):
                # Find corresponding SQL file
                sql_file = yaml_file.with_suffix(".sql")
                if not sql_file.exists():
                    print(f"  ⚠ SQL file not found for {yaml_file.relative_to(REPO_ROOT)}", file=sys.stderr)
                    continue
                files.append((yaml_file, sql_file))
    return files


def build_asset_payload(
    yaml_file: Path,
    sql_file: Path,
    yaml_data: dict[str, Any],
    sql_content: str,
    created_by: str | None,
) -> dict[str, Any]:
    """Build query asset payload from YAML metadata and SQL content."""
    db_name = yaml_file.parent.parent.name
    scope = yaml_data.get("scope") or yaml_file.parent.name
    asset_name = yaml_data.get("name") or yaml_file.stem

    # Get query parameters from YAML
    parameters = yaml_data.get("parameters", [])
    param_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    for param in parameters:
        param_name = param.get("name")
        param_type = param.get("type", "string")
        if param_name:
            param_schema["properties"][param_name] = {
                "type": param_type,
                "description": param.get("description", "")
            }
            if param.get("required"):
                param_schema["required"].append(param_name)

    output_schema = yaml_data.get("output_schema", {
        "type": "object",
        "properties": {}
    })

    payload: dict[str, Any] = {
        "asset_type": "query",
        "name": asset_name,
        "description": yaml_data.get("description", ""),
        "scope": scope,
        "query_sql": sql_content.strip(),
        "query_params": {
            "input_schema": param_schema,
            "output_schema": output_schema
        },
        "query_metadata": {
            "database": db_name,
            "category": yaml_data.get("category"),
            "tags": yaml_data.get("tags", []),
            "seed_yaml": yaml_file.relative_to(REPO_ROOT).as_posix(),
            "seed_sql": sql_file.relative_to(REPO_ROOT).as_posix(),
        },
        "created_by": created_by,
    }
    return payload


def fetch_query_assets(client: httpx.Client, assets_url: str, scopes: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Fetch existing query assets from registry.

    Args:
        client: HTTP client
        assets_url: API endpoint URL
        scopes: Optional list of scopes to filter by. If None, returns all assets.

    Returns:
        Dict mapping asset name to list of asset objects
    """
    response = client.get(assets_url, params={"asset_type": "query"})
    response.raise_for_status()
    assets = response.json().get("data", {}).get("assets", [])
    asset_map: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        name = asset.get("name")
        if not name:
            continue
        # Filter by scope if provided
        if scopes is not None:
            asset_scope = asset.get("scope")
            if asset_scope not in scopes:
                continue
        asset_map.setdefault(name, []).append(asset)
    return asset_map


def execute_import(
    files: list[tuple[Path, Path]],
    base_url: str,
    actor: str,
    apply: bool,
    publish: bool,
    cleanup_drafts: bool,
    scopes: list[str],
) -> None:
    """Execute query asset import."""
    assets_url = base_url.rstrip("/") + "/asset-registry/assets"
    client = httpx.Client(timeout=30.0) if apply else None
    existing_assets: dict[str, list[dict[str, Any]]] = {}
    if client:
        try:
            # Fetch assets for the specified scopes only
            existing_assets = fetch_query_assets(client, assets_url, scopes=scopes)
        except Exception as exc:
            print(f"Failed to fetch existing assets: {exc}", file=sys.stderr)

    if cleanup_drafts and client:
        print(f"\n--- Cleaning up existing drafts in scopes: {scopes} ---")
        cleaned_count = 0
        failed_deletions = []

        for name, asset_list in list(existing_assets.items()):
            remaining = []
            for asset in asset_list:
                # Check if this is a draft and matches one of the target scopes
                is_draft = asset.get("status") == "draft"
                asset_scope = asset.get("scope")
                scope_matches = asset_scope in scopes if asset_scope else False

                if is_draft and scope_matches:
                    draft_id = asset["asset_id"]
                    delete_url = assets_url + f"/{draft_id}"

                    try:
                        delete_response = client.delete(delete_url)
                        if delete_response.status_code == 200:
                            print(f"  ✓ Deleted draft: {name} (id={draft_id})")
                            cleaned_count += 1
                            # DO NOT add to remaining - it's deleted
                            continue
                        else:
                            # Delete failed, keep it in the list and log error
                            error_detail = delete_response.text if delete_response.text else f"HTTP {delete_response.status_code}"
                            print(f"  ✖ Failed to delete draft {draft_id}: {error_detail}")
                            remaining.append(asset)
                            failed_deletions.append((name, draft_id, delete_response.status_code))
                    except Exception as e:
                        print(f"  ✖ Exception deleting draft {draft_id}: {e}")
                        remaining.append(asset)
                        failed_deletions.append((name, draft_id, str(e)))
                else:
                    # Not a draft or doesn't match scope - keep it
                    remaining.append(asset)

            existing_assets[name] = remaining

        print(f"--- Cleanup complete. {cleaned_count} draft(s) removed.", end="")
        if failed_deletions:
            print(f", {len(failed_deletions)} failed ---")
            for name, draft_id, reason in failed_deletions:
                print(f"     (Failed: {name}:{draft_id} - {reason})")
        else:
            print(" ---")

        # Refresh existing assets from DB after cleanup to ensure deleted assets are removed
        print("--- Refreshing asset list from server ---")
        try:
            existing_assets = fetch_query_assets(client, assets_url, scopes=scopes)
            print(f"Updated: {len(existing_assets)} asset name(s) remaining\n")
        except Exception as exc:
            print(f"Warning: Failed to refresh after cleanup: {exc}\n", file=sys.stderr)

        # If cleanup-drafts only, stop here (don't create new assets)
        if client:
            return

    for yaml_file, sql_file in files:
        yaml_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        sql_content = sql_file.read_text(encoding="utf-8")
        payload = build_asset_payload(yaml_file, sql_file, yaml_data, sql_content, actor)
        asset_name = payload["name"]

        print(f"\n=== {yaml_file.relative_to(REPO_ROOT)} ===")
        print(f"name: {asset_name}")
        print(f"scope: {payload['scope']}")
        print(f"description: {payload['description'][:60]}...")
        print(f"SQL lines: {len(sql_content.splitlines())}")

        if not apply or not client:
            print("Dry run only. Add --apply to POST to the API.")
            continue

        existing_list = existing_assets.get(asset_name, [])
        existing = next((a for a in existing_list if a.get("status") == "draft"), None)
        asset_info: dict[str, Any] | None = None

        if existing and existing.get("status") == "draft":
            print(f"  ⟳ Updating existing draft {existing.get('asset_id')} for {asset_name}")
            update_payload = {
                "query_sql": payload["query_sql"],
                "query_params": payload["query_params"],
                "query_metadata": payload["query_metadata"],
            }
            update_url = assets_url + f"/{existing['asset_id']}"
            update_response = client.put(update_url, json=update_payload)
            if update_response.status_code != 200:
                print(f"  ✖ failed to update draft: {update_response.status_code} {update_response.text}")
                continue
            asset_info = update_response.json().get("data", {}).get("asset", {})
            if asset_info:
                existing_assets[asset_name] = [asset_info]
        else:
            if existing:
                print(
                    f"  ⟳ Existing published asset detected ({existing.get('asset_id')}); creating new draft to replace it."
                )
            response = client.post(assets_url, json=payload)
            if response.status_code != 200:
                print(f"  ✖ failed to create asset: {response.status_code} {response.text}")
                continue
            asset_info = response.json().get("data", {}).get("asset", {})
            if asset_info:
                existing_assets[asset_name] = [asset_info]

        if not asset_info:
            continue

        asset_id = asset_info.get("asset_id")
        print(f"  ✓ Draft asset {asset_id} (status={asset_info.get('status')})")
        if publish and asset_id:
            publish_url = assets_url + f"/{asset_id}/publish"
            publish_payload = {"published_by": actor or "query_migration"}
            publish_response = client.post(publish_url, json=publish_payload)
            if publish_response.status_code == 200:
                published_asset = publish_response.json().get("data", {}).get("asset", {})
                print(
                    f"  ✓ Published asset v{published_asset.get('version')} (status={published_asset.get('status')})"
                )
                existing_assets[asset_name] = [published_asset]
            else:
                print(f"  ✖ Publish failed: {publish_response.status_code} {publish_response.text}")
        else:
            existing_assets[asset_name] = [asset_info]

    if client:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Query Seeds into the Asset Registry.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running API server",
    )
    parser.add_argument(
        "--scope",
        action="append",
        help="Scope(s) to import (e.g., ci, discovery, metric). Repeat flag for multiple.",
    )
    parser.add_argument(
        "--created-by", default="query_migration", help="Actor recorded in created_by/published_by"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually POST assets to the API instead of printing payloads",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish assets immediately after creating them (requires --apply)",
    )
    parser.add_argument(
        "--cleanup-drafts",
        "--cleanup",
        dest="cleanup_drafts",
        action="store_true",
        help="Delete existing draft assets with the same name before import",
    )

    args = parser.parse_args()
    scopes = args.scope or ["ci"]
    if args.publish and not args.apply:
        print("Error: --publish requires --apply.", file=sys.stderr)
        return 1

    try:
        files = collect_query_files(scopes)
        if not files:
            print("No query files found for the requested scope(s).")
            return 0
        execute_import(
            files=files,
            base_url=args.base_url,
            actor=args.created_by,
            apply=args.apply,
            publish=args.publish,
            cleanup_drafts=args.cleanup_drafts,
            scopes=scopes,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
