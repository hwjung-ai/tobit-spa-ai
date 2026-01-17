#!/usr/bin/env python3
"""
Utility for migrating seed Policy files under apps/api/resources/policies into the Asset Registry.

Usage:
  python scripts/policy_asset_importer.py --scope ci --apply --publish
  python scripts/policy_asset_importer.py --scope ci --apply --cleanup-drafts  (delete drafts only)

Run with --apply once the API server is running so assets are actually created and published.

Flags:
  --cleanup-drafts: Delete existing draft assets. When used alone, only deletes drafts without creating new assets.
  --publish: Publish assets immediately after creating them (requires --apply).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_ROOT = REPO_ROOT / "apps/api/resources/policies"


def collect_policy_files(scopes: list[str] | None = None) -> list[Path]:
    """Collect policy YAML files from resources/policies/.

    Args:
        scopes: Optional list of scopes to filter by. If None, returns all files.
    """
    files: list[Path] = []
    if not POLICY_ROOT.exists():
        raise RuntimeError(f"Policy directory not found: {POLICY_ROOT}")

    for yaml_file in sorted(POLICY_ROOT.rglob("*.yaml")):
        # If scopes are specified, filter by scope in YAML
        if scopes:
            yaml_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
            asset_scope = yaml_data.get("scope", "ci")
            if asset_scope not in scopes:
                continue
        files.append(yaml_file)
    return files


def build_policy_payload(
    yaml_file: Path,
    yaml_data: dict[str, Any],
    created_by: str | None,
) -> dict[str, Any]:
    """Build policy asset payload from YAML metadata."""
    asset_name = yaml_data.get("name") or yaml_file.stem
    policy_type = yaml_data.get("policy_type")
    scope = yaml_data.get("scope", "ci")

    payload: dict[str, Any] = {
        "asset_type": "policy",
        "name": asset_name,
        "description": yaml_data.get("description", ""),
        "scope": scope,
        "policy_type": policy_type,
        "limits": yaml_data.get("limits", {}),
        "created_by": created_by,
    }
    return payload


def fetch_policy_assets(client: httpx.Client, assets_url: str, scopes: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Fetch existing policy assets from registry.

    Args:
        client: HTTP client
        assets_url: API endpoint URL
        scopes: Optional list of scopes to filter by. If None, returns all assets.

    Returns:
        Dict mapping asset name to list of asset objects
    """
    response = client.get(assets_url, params={"asset_type": "policy"})
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
    files: list[Path],
    base_url: str,
    actor: str,
    apply: bool,
    publish: bool,
    cleanup_drafts: bool,
    scopes: list[str],
) -> None:
    """Execute policy asset import."""
    assets_url = base_url.rstrip("/") + "/asset-registry/assets"
    client = httpx.Client(timeout=30.0) if apply else None
    existing_assets: dict[str, list[dict[str, Any]]] = {}
    if client:
        try:
            # Fetch assets for the specified scopes only
            existing_assets = fetch_policy_assets(client, assets_url, scopes=scopes)
        except Exception as exc:
            print(f"Failed to fetch existing assets: {exc}", file=sys.stderr)

    if cleanup_drafts and client:
        print(f"\n--- Cleaning up existing policy drafts in scopes: {scopes} ---")
        cleaned_count = 0
        failed_deletions = []

        for name, asset_list in list(existing_assets.items()):
            remaining = []
            for asset in asset_list:
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
                            continue
                        else:
                            error_detail = delete_response.text if delete_response.text else f"HTTP {delete_response.status_code}"
                            print(f"  ✖ Failed to delete draft {draft_id}: {error_detail}")
                            remaining.append(asset)
                            failed_deletions.append((name, draft_id, delete_response.status_code))
                    except Exception as e:
                        print(f"  ✖ Exception deleting draft {draft_id}: {e}")
                        remaining.append(asset)
                        failed_deletions.append((name, draft_id, str(e)))
                else:
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
            existing_assets = fetch_policy_assets(client, assets_url, scopes=scopes)
            print(f"Updated: {len(existing_assets)} asset name(s) remaining\n")
        except Exception as exc:
            print(f"Warning: Failed to refresh after cleanup: {exc}\n", file=sys.stderr)

        # If cleanup-drafts only, stop here (don't create new assets)
        if client:
            return

    for yaml_file in files:
        yaml_data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        payload = build_policy_payload(yaml_file, yaml_data, actor)
        asset_name = payload["name"]

        print(f"\n=== {yaml_file.relative_to(REPO_ROOT)} ===")
        print(f"name: {asset_name}")
        print(f"policy_type: {payload['policy_type']}")
        print(f"scope: {payload['scope']}")
        print(f"description: {payload['description'][:60]}...")

        if not apply or not client:
            print("Dry run only. Add --apply to POST to the API.")
            continue

        existing_list = existing_assets.get(asset_name, [])
        existing = next((a for a in existing_list if a.get("status") == "draft"), None)
        asset_info: dict[str, Any] | None = None

        if existing and existing.get("status") == "draft":
            print(f"  ⟳ Updating existing draft {existing.get('asset_id')} for {asset_name}")
            update_payload = {
                "limits": payload["limits"],
                "description": payload["description"],
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
            publish_payload = {"published_by": actor or "policy_migration"}
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
    parser = argparse.ArgumentParser(description="Import Policy Seeds into the Asset Registry.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running API server",
    )
    parser.add_argument(
        "--scope",
        action="append",
        help="Scope(s) to import (e.g., ci, ops). Repeat flag for multiple.",
    )
    parser.add_argument(
        "--created-by", default="policy_migration", help="Actor recorded in created_by/published_by"
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
        files = collect_policy_files(scopes)
        if not files:
            print("No policy files found for the requested scope(s).")
            return 0
        print(f"Found {len(files)} policy file(s) to import")
        execute_import(
            files=files,
            base_url=args.base_url,
            actor=args.created_by,
            apply=args.apply,
            publish=args.publish,
            cleanup_drafts=args.cleanup_drafts,
            scopes=scopes,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
