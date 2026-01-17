#!/usr/bin/env python3
"""
Utility for migrating seed File Prompts under apps/api/resources/prompts into the Asset Registry.

Usage:
  python scripts/prompt_asset_importer.py --scope ci --apply --publish --cleanup

Run with --apply once the API server is running so assets are actually created and published.
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
PROMPT_ROOT = REPO_ROOT / "apps/api/resources/prompts"

ALLOWED_PROMPT_ENGINES = {"planner", "langgraph"}

DEFAULT_ENGINE_BY_SCOPE = {
    "ci": "planner",
    "ops": "langgraph",
}

DEFAULT_INPUT_SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
}

DEFAULT_OUTPUT_CONTRACT = {
    "type": "object",
    "properties": {
        "plan": {
            "type": "object",
            "properties": {"steps": {"type": "array"}},
        }
    },
}


def parse_schema(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    schema_path = Path(path)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def collect_prompt_files(scopes: list[str]) -> list[Path]:
    files: list[Path] = []
    if not PROMPT_ROOT.exists():
        raise RuntimeError(f"Prompt directory not found: {PROMPT_ROOT}")
    for scope_dir in sorted(PROMPT_ROOT.iterdir()):
        if not scope_dir.is_dir():
            continue
        if scopes and scope_dir.name not in scopes:
            continue
        for prompt_file in sorted(scope_dir.glob("*.yaml")):
            files.append(prompt_file)
    return files


def determine_system_template(templates: dict[str, str]) -> str | None:
    for candidate in ("system", "plan_system", "summary_system"):
        if candidate in templates and templates[candidate]:
            return templates[candidate]
    if templates:
        return next(iter(templates.values()))
    return None


def build_asset_payload(
    prompt_file: Path,
    data: dict[str, Any],
    input_schema: dict[str, Any] | None,
    output_contract: dict[str, Any] | None,
    created_by: str | None,
) -> dict[str, Any]:
    scope = prompt_file.parent.name
    engine = prompt_file.stem
    templates = data.get("templates") or {}
    asset_name = data.get("name") or f"{scope}_{engine}"
    system_template = determine_system_template(templates)

    if not system_template:
        raise ValueError(f"No system template found in {prompt_file}")

    normalized_engine = engine.lower()
    selected_engine = (
        normalized_engine
        if normalized_engine in ALLOWED_PROMPT_ENGINES
        else DEFAULT_ENGINE_BY_SCOPE.get(scope, "planner")
    )
    if normalized_engine != selected_engine:
        print(f"  ✳ Using engine={selected_engine} for {asset_name} (scope={scope})")

    payload: dict[str, Any] = {
        "asset_type": "prompt",
        "name": asset_name,
        "scope": scope,
        "engine": selected_engine,
        "template": system_template,
        "created_by": created_by,
        "input_schema": input_schema or DEFAULT_INPUT_SCHEMA,
        "output_contract": output_contract or DEFAULT_OUTPUT_CONTRACT,
        "content": data,
    }
    return payload


def fetch_prompt_assets(client: httpx.Client, assets_url: str, scopes: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Fetch existing prompt assets from registry.

    Args:
        client: HTTP client
        assets_url: API endpoint URL
        scopes: Optional list of scopes to filter by. If None, returns all assets.

    Returns:
        Dict mapping asset name to list of asset objects
    """
    response = client.get(assets_url, params={"asset_type": "prompt"})
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
    input_schema: dict[str, Any] | None,
    output_contract: dict[str, Any] | None,
    actor: str,
    apply: bool,
    publish: bool,
    cleanup_drafts: bool,
    scopes: list[str],
) -> None:
    assets_url = base_url.rstrip("/") + "/asset-registry/assets"
    client = httpx.Client(timeout=30.0) if apply else None
    existing_assets: dict[str, list[dict[str, Any]]] = {}
    if client:
        try:
            # Fetch assets for the specified scopes only
            existing_assets = fetch_prompt_assets(client, assets_url, scopes=scopes)
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
                        print(f"  → Attempting DELETE {delete_url}")
                        delete_response = client.delete(delete_url)
                        print(f"    Response: HTTP {delete_response.status_code}")
                        if delete_response.text:
                            print(f"    Body: {delete_response.text[:300]}")

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
                        import traceback
                        traceback.print_exc()
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
            existing_assets = fetch_prompt_assets(client, assets_url, scopes=scopes)
            print(f"Updated: {len(existing_assets)} asset name(s) remaining\n")
        except Exception as exc:
            print(f"Warning: Failed to refresh after cleanup: {exc}\n", file=sys.stderr)

    for prompt_file in files:
        data = yaml.safe_load(prompt_file.read_text(encoding="utf-8")) or {}
        payload = build_asset_payload(prompt_file, data, input_schema, output_contract, actor)
        asset_name = payload["name"]
        engine = payload["engine"]
        print(f"\n=== {prompt_file.relative_to(REPO_ROOT)} ===")
        print(f"name: {asset_name}")
        print(f"scope: {payload['scope']}  engine: {engine}")
        print(f"templates: {list(data.get('templates', {}).keys())}")

        if not apply or not client:
            print("Dry run only. Add --apply to POST to the API.")
            continue

        existing_list = existing_assets.get(asset_name, [])

        existing = next((a for a in existing_list if a.get("status") == "draft"), None)
        asset_info: dict[str, Any] | None = None

        if existing and existing.get("status") == "draft":
            print(f"  ⟳ Updating existing draft {existing.get('asset_id')} for {asset_name}")
            update_payload = {
                "template": payload["template"],
                "input_schema": payload["input_schema"],
                "output_contract": payload["output_contract"],
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
            publish_payload = {"published_by": actor or "prompt_migration"}
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
    parser = argparse.ArgumentParser(description="Import File Prompts into the Asset Registry.")
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
        "--input-schema",
        help="JSON file with input_schema override (applies to all prompts)",
    )
    parser.add_argument(
        "--output-contract",
        help="JSON file with output_contract override (applies to all prompts)",
    )
    parser.add_argument(
        "--created-by", default="prompt_migration", help="Actor recorded in created_by/published_by"
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
        input_schema = parse_schema(args.input_schema)
        output_contract = parse_schema(args.output_contract)
        files = collect_prompt_files(scopes)
        if not files:
            print("No prompt files found for the requested scope(s).")
            return 0
        execute_import(
            files=files,
            base_url=args.base_url,
            input_schema=input_schema,
            output_contract=output_contract,
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
