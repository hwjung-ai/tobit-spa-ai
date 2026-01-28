#!/usr/bin/env python3
"""
Inventory Tool Asset Importer

This script imports 3 inventory tool assets into the Asset Registry database.
These tools demonstrate the Generic Orchestration System's capability to load tools dynamically.
"""

import argparse
import os
import sys
from pathlib import Path

# Add apps/api to Python path
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

import yaml

from core.db import get_session, get_session_context
from core.logging import get_logger
from app.modules.asset_registry.crud import create_asset, publish_asset

logger = get_logger(__name__)

# Inventory tool definitions
INVENTORY_TOOLS = [
    "inventory_list_items.yaml",
    "inventory_get_item.yaml",
    "inventory_update_item.yaml",
]

TOOLS_DIR = Path(__file__).resolve().parents[1] / "resources" / "tools" / "inventory"


def load_yaml_file(filepath: Path) -> dict:
    """Load YAML file and return parsed content."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        raise


def import_inventory_tool(session, tool_file: str) -> dict:
    """Import a single inventory tool asset."""
    filepath = TOOLS_DIR / tool_file

    if not filepath.exists():
        raise FileNotFoundError(f"Tool file not found: {filepath}")

    tool_data = load_yaml_file(filepath)

    asset = create_asset(
        session=session,
        asset_type="tool",
        name=tool_data["name"],
        description=tool_data["description"],
        tool_type=tool_data["tool_type"],
        tool_config=tool_data["tool_config"],
        tool_input_schema=tool_data["tool_input_schema"],
        tool_output_schema=tool_data["tool_output_schema"],
        created_by="inventory_seed_script",
    )

    logger.info(f"Created inventory tool: {tool_data['name']} (id={asset.asset_id})")

    return {
        "name": tool_data["name"],
        "asset_id": str(asset.asset_id),
        "status": "draft",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import inventory tool assets into Asset Registry"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes to database (create assets)"
    )
    parser.add_argument(
        "--publish", action="store_true", help="Publish created tool assets"
    )
    parser.add_argument(
        "--cleanup-drafts",
        action="store_true",
        help="Cleanup existing draft tool assets before import",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run - show what would be done"
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Inventory Tool Asset Importer")
    logger.info("=" * 60)

    if args.dry_run:
        print("=== Dry Run Mode ===")
        print(f"Would import {len(INVENTORY_TOOLS)} inventory tools:")
        for tool_file in INVENTORY_TOOLS:
            filepath = TOOLS_DIR / tool_file
            if filepath.exists():
                print(f"  - {tool_file}")
            else:
                print(f"  - {tool_file} (NOT FOUND)")
        print("\nUse --apply to create assets in database.")
        print("Use --publish to publish all created assets.")
        sys.exit(0)

    if args.apply:
        with get_session_context() as session:
            if args.cleanup_drafts:
                logger.info("Cleaning up existing draft tool assets...")
                from sqlmodel import select
                from app.modules.asset_registry.models import TbAssetRegistry

                existing_drafts = session.exec(
                    select(TbAssetRegistry)
                    .where(TbAssetRegistry.asset_type == "tool")
                    .where(TbAssetRegistry.status == "draft")
                ).all()

                if existing_drafts:
                    for asset in existing_drafts:
                        session.delete(asset)
                    logger.info(f"Deleted draft tool: {asset.name}")
                session.commit()
                logger.info(
                    f"Deleted {len(existing_drafts)} existing draft tool assets"
                )

            created_assets = []
            for tool_file in INVENTORY_TOOLS:
                try:
                    result = import_inventory_tool(session, tool_file)
                    created_assets.append(result)
                except Exception as e:
                    logger.error(f"Failed to import {tool_file}: {e}")
                    continue

            if args.publish:
                logger.info("Publishing inventory tool assets...")
                for asset_info in created_assets:
                    try:
                        asset = session.get(TbAssetRegistry, asset_info["asset_id"])
                        publish_asset(
                            session, asset, published_by="inventory_seed_script"
                        )
                        logger.info(f"Published: {asset_info['name']}")
                    except Exception as e:
                        logger.error(f"Failed to publish {asset_info['name']}: {e}")
                        continue

        logger.info("=" * 60)
        logger.info(f"Created {len(created_assets)} inventory tool assets")
        if args.publish:
            logger.info("All inventory tools published")
        logger.info("=" * 60)

        print(f"\nCreated {len(created_assets)} inventory tool assets")
        print("Status: " + ("published" if args.publish else "draft"))
        print("\nUse --publish to publish all created tool assets.")


if __name__ == "__main__":
    main()
