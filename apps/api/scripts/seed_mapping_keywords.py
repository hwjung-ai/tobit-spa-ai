#!/usr/bin/env python3
"""
Mapping Asset Importer

Imports 6 mapping YAML files into the Asset Registry database.
This script migrates hardcoded keyword sets from planner_llm.py to mapping assets.
"""

import argparse
import os
import sys
from pathlib import Path

import yaml

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from core.db import get_session, get_session_context
from app.modules.asset_registry.crud import create_asset, publish_asset
from core.logging import get_logger

logger = get_logger(__name__)

# Mapping files to import
MAPPING_FILES = [
    "metric_aliases.yaml",
    "agg_keywords.yaml",
    "series_keywords.yaml",
    "history_keywords.yaml",
    "list_keywords.yaml",
    "table_hints.yaml",
]

MAPPINGS_DIR = project_root / "apps/api/resources/mappings"


def load_yaml_file(filepath: Path) -> dict:
    """Load YAML file and return parsed content."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        raise


def import_mapping_asset(name: str, mapping_data: dict, session) -> dict:
    """
    Import a single mapping asset into the database.

    Args:
        name: Mapping asset name (e.g., "metric_aliases")
        mapping_data: Parsed YAML content
        session: Database session

    Returns:
        Created asset information
    """
    # Extract required fields
    description = mapping_data.get("description", "")
    mapping_type = mapping_data.get("mapping_type", name)
    scope = mapping_data.get("scope", "ci")
    content = mapping_data.get("content", {})

    # Create the asset
    asset = create_asset(
        session=session,
        asset_type="mapping",
        name=name,
        description=description,
        mapping_type=mapping_type,
        content=content,
        scope=scope,
        status="draft",
        created_by="mapping_importer_script",
    )

    logger.info(f"Created draft mapping asset: {name} (asset_id={asset.asset_id})")

    return {
        "name": name,
        "asset_id": str(asset.asset_id),
        "status": "draft",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import mapping assets into Asset Registry"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (insert/update assets)",
    )
    parser.add_argument(
        "--publish", action="store_true", help="Publish created mapping assets"
    )
    parser.add_argument(
        "--cleanup-drafts",
        action="store_true",
        help="Cleanup existing draft mappings before import",
    )
    parser.add_argument("--scope", default="ci", help="Asset scope (default: ci)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - show what would be done without making changes",
    )

    args = parser.parse_args()

    # Verify mappings directory exists
    if not MAPPINGS_DIR.exists():
        logger.error(f"Mappings directory not found: {MAPPINGS_DIR}")
        sys.exit(1)

    # Load all mapping files
    mapping_files_data = {}
    for mapping_file in MAPPING_FILES:
        filepath = MAPPINGS_DIR / mapping_file
        if not filepath.exists():
            logger.warning(f"Mapping file not found: {filepath}")
            continue

        try:
            data = load_yaml_file(filepath)
            name = data.get("name", mapping_file.replace(".yaml", ""))
            mapping_files_data[name] = data
            logger.info(f"Loaded mapping file: {name}")
        except Exception as e:
            logger.error(f"Failed to load {mapping_file}: {e}")
            continue

    if not mapping_files_data:
        logger.error("No mapping files were loaded successfully")
        sys.exit(1)

    logger.info(f"Loaded {len(mapping_files_data)} mapping files")

    # Dry run - just show what would be done
    if args.dry_run:
        print("=== Dry Run Mode ===")
        print(f"Would import {len(mapping_files_data)} mapping assets:")
        for name, data in mapping_files_data.items():
            print(f"  - {name}: {data.get('description', '')}")
        print(
            "\nWould apply to database:", "--apply", "publish" if args.publish else ""
        )
        sys.exit(0)

    # Apply changes to database
    if not args.apply:
        logger.info("Dry run mode. Use --apply to create assets in database.")
        print("\nUse --apply to create mapping assets in database.")
        sys.exit(0)

    # Cleanup existing draft mappings if requested
    with get_session_context() as session:
        if args.cleanup_drafts:
            logger.info("Cleaning up existing draft mapping assets...")
            from sqlmodel import select
            from app.modules.asset_registry.models import TbAssetRegistry

            # Find existing draft mapping assets
            existing_drafts = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "mapping")
                .where(TbAssetRegistry.status == "draft")
            ).all()

            if existing_drafts:
                for asset in existing_drafts:
                    session.delete(asset)
                logger.info(f"Deleted draft asset: {asset.name}")
                session.commit()
            logger.info(f"Deleted {len(existing_drafts)} existing draft mapping assets")

        # Create new mapping assets
        created_assets = []
        for name, data in mapping_files_data.items():
            try:
                result = import_mapping_asset(name, data, session)
                created_assets.append(result)
            except Exception as e:
                logger.error(f"Failed to import mapping {name}: {e}")
                continue

        session.commit()
        logger.info(f"Created {len(created_assets)} mapping assets")

        # Publish if requested
        if args.publish:
            logger.info("Publishing mapping assets...")
            for asset_info in created_assets:
                try:
                    asset = session.get(TbAssetRegistry, asset_info["asset_id"])
                    publish_asset(
                        session, asset, published_by="mapping_importer_script"
                    )
                    logger.info(f"Published: {asset_info['name']}")
                except Exception as e:
                    logger.error(f"Failed to publish {asset_info['name']}: {e}")
                    continue

            logger.info("All mapping assets published")
        else:
            logger.info("Mapping assets created in draft status.")
            print("\nMapping assets imported successfully!")
            print(f"Created: {len(created_assets)} assets")
            print("Status: draft")
            print("\nUse --publish to publish all mapping assets.")


if __name__ == "__main__":
    main()
