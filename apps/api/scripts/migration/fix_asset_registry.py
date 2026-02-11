#!/usr/bin/env python
"""
Migration script to fix asset registry issues:
1. Change validator and response_builder from published to draft
2. Keep only the latest ci_planner_output_parser as published
3. Archive older versions of ci_planner_output_parser
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def fix_validator_response_builder() -> tuple[int, int]:
    """Change validator.yaml and response_builder.yaml from published to draft"""
    with get_session_context() as session:
        count_validator = 0
        count_builder = 0

        # Fix validator
        validators = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.name == "validator")
            .where(TbAssetRegistry.status == "published")
        ).all()

        for asset in validators:
            asset.status = "draft"
            asset.updated_at = datetime.now()
            session.add(asset)
            count_validator += 1
            print(f"  ✓ Changed validator v{asset.version} (id: {asset.asset_id}) to draft")

        # Fix response_builder
        builders = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.name == "response_builder")
            .where(TbAssetRegistry.status == "published")
        ).all()

        for asset in builders:
            asset.status = "draft"
            asset.updated_at = datetime.now()
            session.add(asset)
            count_builder += 1
            print(f"  ✓ Changed response_builder v{asset.version} (id: {asset.asset_id}) to draft")

        session.commit()
        return count_validator, count_builder


def fix_ci_planner_duplicates() -> int:
    """Keep only the latest ci_planner_output_parser as published, archive others"""
    with get_session_context() as session:
        planners = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "planner")
            .where(TbAssetRegistry.name == "ci_planner_output_parser")
            .where(TbAssetRegistry.status == "published")
            .order_by(TbAssetRegistry.version.desc())
        ).all()

        if len(planners) <= 1:
            print("  ℹ ci_planner_output_parser: No duplicates found (count: {})".format(len(planners)))
            return 0

        # Keep the latest (first in sorted list), archive the rest
        latest = planners[0]
        to_archive = planners[1:]
        count = 0

        for asset in to_archive:
            asset.status = "draft"
            asset.updated_at = datetime.now()
            session.add(asset)
            count += 1
            print(f"  ✓ Archived ci_planner_output_parser v{asset.version} (id: {asset.asset_id}) to draft (newer: v{latest.version})")

        session.commit()
        return count


def main() -> None:
    print("\n=== Fixing Asset Registry ===\n")

    print("1. Changing validator.yaml and response_builder.yaml from published to draft:")
    count_val, count_builder = fix_validator_response_builder()
    print(f"   → validator: {count_val} updated")
    print(f"   → response_builder: {count_builder} updated\n")

    print("2. Archiving duplicate ci_planner_output_parser versions:")
    count_dups = fix_ci_planner_duplicates()
    print(f"   → {count_dups} duplicates archived\n")

    total = count_val + count_builder + count_dups
    if total == 0:
        print("✓ Asset registry is already clean!\n")
    else:
        print(f"✓ Fixed {total} assets total\n")


if __name__ == "__main__":
    main()
