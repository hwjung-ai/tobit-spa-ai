#!/usr/bin/env python
"""Check ci_planner_output_parser duplicates in the database"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def check_ci_planner_duplicates() -> None:
    """Check for duplicate ci_planner_output_parser entries"""
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

        print("\n" + "=" * 80)
        print(f"Found {len(planners)} published ci_planner_output_parser entries")
        print("=" * 80 + "\n")

        for idx, asset in enumerate(planners, 1):
            print(f"{idx}. Version {asset.version}")
            print(f"   Asset ID:     {asset.asset_id}")
            print(f"   Name:         {asset.name}")
            print(f"   Scope:        {asset.scope}")
            print(f"   Engine:       {asset.engine}")
            print(f"   Status:       {asset.status}")
            print(f"   Created:      {asset.created_at}")
            print(f"   Published:    {asset.published_at}")
            print(f"   Published By: {asset.published_by}")
            print()

        if len(planners) > 1:
            print("\n⚠️  Found duplicates!")
            print(f"   → Keep:    Version {planners[0].version} (latest, ID: {planners[0].asset_id})")
            for old in planners[1:]:
                print(f"   → Delete:  Version {old.version} (ID: {old.asset_id})")
        else:
            print("✓ No duplicates found")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    check_ci_planner_duplicates()
