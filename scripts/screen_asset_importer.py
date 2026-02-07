#!/usr/bin/env python3
"""
Screen Asset Importer for UI Screen Creator
Imports screen JSON files into Asset Registry as 'screen' type assets.

Usage:
  python scripts/screen_asset_importer.py --apply --publish
  python scripts/screen_asset_importer.py --apply --cleanup-drafts

Run with --apply once API server is running so assets are actually created and published.

Flags:
  --apply: Actually POST assets to API instead of printing payloads
  --publish: Publish assets immediately after creating them (requires --apply).
  --cleanup-drafts: Delete existing draft assets before importing
"""

import argparse
import httpx
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).parent.parent
SCREENS_DIR = REPO_ROOT / "apps/web/src/lib/ui-screen/screens"


def build_asset_payload(
    screen_file: Path,
    screen_data: Dict[str, Any],
    actor: str,
) -> Dict[str, Any]:
    """Build screen asset payload from JSON screen file."""
    return {
        "asset_type": "screen",
        "screen_id": screen_data.get("screen_id", screen_file.stem),
        "name": screen_data.get("name", screen_file.stem),
        "description": screen_data.get("description", ""),
        "schema_json": screen_data,
        "scope": "ui",
        "created_by": actor,
    }


def fetch_screen_assets(
    client: httpx.Client, assets_url: str, scopes: List[str] | None = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch existing screen assets from registry.

    Args:
        client: HTTP client
        assets_url: API endpoint URL
        scopes: Optional list of scopes to filter by. If None, returns all assets.

    Returns:
        Dict mapping asset name to list of asset objects
    """
    response = client.get(assets_url, params={"asset_type": "screen"})
    response.raise_for_status()
    assets = response.json().get("data", {}).get("assets", [])

    asset_map: Dict[str, List[Dict[str, Any]]] = {}
    for asset in assets:
        name = asset.get("name")
        if not name:
            continue
        if scopes is not None:
            asset_scope = asset.get("scope")
            if asset_scope not in scopes:
                continue
        asset_map.setdefault(name, []).append(asset)
    return asset_map


def cleanup_drafts(
    client: httpx.Client,
    base_url: str,
    scopes: List[str] | None = None,
) -> None:
    """Delete existing draft screen assets."""
    assets_url = base_url.rstrip("/") + "/asset-registry/assets"
    existing_assets: Dict[str, List[Dict[str, Any]]] = {}
    failed_deletions: List[tuple[str, str, int | str]] = []

    if client:
        try:
            # Fetch assets for specified scopes only
            existing_assets = fetch_screen_assets(client, assets_url, scopes=scopes)
        except Exception as exc:
            print(f"Failed to fetch existing assets: {exc}", file=sys.stderr)
            return

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
                            print(f"  ✓ Deleted draft {draft_id} for {name}")
                        else:
                            error_detail = delete_response.text
                            print(f"  ✖ Failed to delete draft {draft_id}: {error_detail}")
                            remaining.append(asset)
                            failed_deletions.append((name, draft_id, delete_response.status_code))
                    except httpx.HTTPStatusError as e:
                        print(f"  ✖ Failed to delete draft {draft_id}: {e.response.status_code}")
                        remaining.append(asset)
                        failed_deletions.append((name, draft_id, e.response.status_code))
                    except Exception as e:
                        print(f"  ✖ Exception deleting draft {draft_id}: {e}")
                        remaining.append(asset)
                        failed_deletions.append((name, draft_id, str(e)))
                # Not a draft or doesn't match scope - keep it
                else:
                    remaining.append(asset)

            existing_assets[name] = remaining

        # Refresh existing assets from DB after cleanup to ensure deleted assets are removed
        print("--- Refreshing asset list from server ---")
        try:
            existing_assets = fetch_screen_assets(client, assets_url, scopes=scopes)
            print(f"Updated: {len(existing_assets)} asset name(s) remaining\n")
        except Exception as exc:
            print(f"Warning: Failed to refresh asset list: {exc}", file=sys.stderr)

        if failed_deletions:
            print("\nFailed deletions:")
            for name, asset_id, error in failed_deletions:
                print(f"  ✖ {name}: {asset_id} - {error}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import screen JSON files into Asset Registry"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually POST assets to API instead of printing payloads",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish assets immediately after creating them (requires --apply)",
    )
    parser.add_argument(
        "--cleanup-drafts",
        action="store_true",
        help="Delete existing draft assets with the same name before importing",
    )
    parser.add_argument(
        "--scope",
        default="ui",
        help="Scope for screen assets (default: ui)",
    )
    args = parser.parse_args()

    assets_url = args.base_url.rstrip("/") + "/asset-registry/assets"
    client = httpx.Client(timeout=30.0) if args.apply else None
    existing_assets: Dict[str, List[Dict[str, Any]]] = {}

    scopes = [args.scope]

    # Cleanup drafts if requested
    if args.cleanup_drafts and client:
        cleanup_drafts(client, args.base_url, scopes=scopes)

    # If cleanup-drafts only, stop here (don't create new assets)
    if args.cleanup_drafts and not args.apply:
        return

    # Find all screen JSON files
    screen_files = sorted(SCREENS_DIR.glob("*.screen.json"))
    if not screen_files:
        print(f"No screen JSON files found in {SCREENS_DIR}")
        return

    print(f"Found {len(screen_files)} screen file(s)\n")

    # Fetch existing assets
    if client:
        try:
            existing_assets = fetch_screen_assets(client, assets_url, scopes=scopes)
        except Exception as exc:
            print(f"Failed to fetch existing assets: {exc}", file=sys.stderr)

    # Import each screen
    actor = "screen_importer"
    created_count = 0
    published_count = 0
    failed_count = 0

    for screen_file in screen_files:
        # Load screen JSON
        with open(screen_file, encoding="utf-8") as f:
            screen_data = json.load(f)

        payload = build_asset_payload(screen_file, screen_data, actor)
        asset_name = payload["name"]

        print(f"\n=== {screen_file.relative_to(REPO_ROOT)} ===")
        print(f"screen_id: {payload['screen_id']}")
        print(f"name: {asset_name}")
        print(f"scope: {payload['scope']}")

        if not args.apply:
            print("  (Dry run - would create asset with above payload)")
            continue

        # Check for existing draft
        existing_list = existing_assets.get(asset_name, [])
        existing = next((a for a in existing_list if a.get("status") == "draft"), None)

        asset_info: Dict[str, Any] | None = None

        if existing and existing.get("status") == "draft":
            print(f"  ⟳ Updating existing draft {existing.get('asset_id')} for {asset_name}")
            update_payload = {
                "schema_json": payload["schema_json"],
                "expected_updated_at": existing.get("updated_at"),
            }
            update_url = assets_url + f"/{existing['asset_id']}"

            try:
                update_response = client.put(update_url, json=update_payload)
                if update_response.status_code != 200:
                    print(f"  ✖ Failed to update draft: {update_response.status_code}")
                    print(f"     {update_response.text}")
                    failed_count += 1
                    continue
                asset_info = update_response.json().get("data", {}).get("asset", {})
                if asset_info:
                    existing_assets[asset_name] = [asset_info]
                    created_count += 1
            except Exception as e:
                print(f"  ✖ Exception updating draft: {e}")
                failed_count += 1
                continue
        else:
            # Check if published asset exists
            if existing:
                print(
                    f"  ⟳ Existing published asset detected ({existing.get('asset_id')}); creating new draft to replace it."
                )
            else:
                print(f"  ✓ Creating new draft for {asset_name}")

            response = client.post(assets_url, json=payload)
            if response.status_code != 200:
                print(f"  ✖ Failed to create asset: {response.status_code}")
                print(f"     {response.text}")
                failed_count += 1
                continue
            asset_info = response.json().get("data", {}).get("asset", {})
            if asset_info:
                existing_assets[asset_name] = [asset_info]
                created_count += 1

        if not asset_info:
            failed_count += 1
            continue

        asset_id = asset_info.get("asset_id")
        print(f"  ✓ Draft asset {asset_id} (status={asset_info.get('status')})")

        # Publish if requested
        if args.publish and asset_id:
            publish_url = assets_url + f"/{asset_id}/publish"
            publish_payload = {"published_by": actor or "screen_importer"}
            try:
                publish_response = client.post(publish_url, json=publish_payload)
                if publish_response.status_code == 200:
                    published_asset = publish_response.json().get("data", {}).get("asset", {})
                    print(
                        f"  ✓ Published asset v{published_asset.get('version')} (status={published_asset.get('status')})"
                    )
                    existing_assets[asset_name] = [published_asset]
                    published_count += 1
                else:
                    print(f"  ⚠ Failed to publish: {publish_response.status_code}")
                    existing_assets[asset_name] = [asset_info]
            except Exception as e:
                print(f"  ⚠ Exception publishing: {e}")
                existing_assets[asset_name] = [asset_info]
        else:
            existing_assets[asset_name] = [asset_info]

    # Summary
    print("\n" + "=" * 60)
    print(f"Import summary:")
    print(f"  Created/Updated: {created_count}")
    print(f"  Published: {published_count}")
    print(f"  Failed: {failed_count}")
    print("=" * 60)

    if failed_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())