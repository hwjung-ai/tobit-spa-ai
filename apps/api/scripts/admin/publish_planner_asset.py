#!/usr/bin/env python
"""Publish ci_planner_output_parser asset to database"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.crud import publish_asset
from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def publish_planner_asset() -> None:
    """Publish ci_planner_output_parser asset"""
    with get_session_context() as session:
        # Find draft ci_planner_output_parser
        asset = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "planner")
            .where(TbAssetRegistry.name == "ci_planner_output_parser")
            .where(TbAssetRegistry.status == "draft")
        ).first()

        if not asset:
            print("\n❌ ci_planner_output_parser not found in draft status")
            print("   Please run update_planner_asset.py first\n")
            return

        print("\n" + "=" * 80)
        print("PUBLISHING ci_planner_output_parser ASSET")
        print("=" * 80 + "\n")

        print(f"Asset ID:    {asset.asset_id}")
        print(f"Name:        {asset.name}")
        print(f"Scope:       {asset.scope}")
        print(f"Engine:      {asset.engine}")
        print(f"Version:     {asset.version}")
        print(f"Current Status: {asset.status}\n")

        # Publish the asset
        published = publish_asset(session, asset, "admin")

        print("✓ Successfully published ci_planner_output_parser!")
        print("  Status changed: draft → published")
        print(f"  Published At: {published.published_at}\n")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    publish_planner_asset()
