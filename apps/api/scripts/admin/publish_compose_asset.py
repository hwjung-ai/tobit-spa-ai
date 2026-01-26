#!/usr/bin/env python
"""Publish ci_compose_summary asset to database"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.db import get_session_context
from sqlmodel import select
from app.modules.asset_registry.models import TbAssetRegistry


def publish_compose_asset() -> None:
    """Publish ci_compose_summary asset"""
    with get_session_context() as session:
        # Find draft ci_compose_summary
        asset = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "compose")
            .where(TbAssetRegistry.name == "ci_compose_summary")
            .where(TbAssetRegistry.status == "draft")
        ).first()

        if not asset:
            print("\n❌ ci_compose_summary not found in draft status")
            print("   Please register compose.yaml first using seed_assets.py\n")
            return

        print("\n" + "=" * 80)
        print("PUBLISHING ci_compose_summary ASSET")
        print("=" * 80 + "\n")

        print(f"Asset ID:    {asset.asset_id}")
        print(f"Name:        {asset.name}")
        print(f"Scope:       {asset.scope}")
        print(f"Engine:      {asset.engine}")
        print(f"Version:     {asset.version}")
        print(f"Current Status: {asset.status}\n")

        # Publish the asset
        asset.status = "published"
        asset.published_by = "admin"
        asset.published_at = datetime.now()
        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()

        print(f"✓ Successfully published ci_compose_summary!")
        print(f"  Status changed: draft → published")
        print(f"  Published At: {asset.published_at}\n")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    publish_compose_asset()
