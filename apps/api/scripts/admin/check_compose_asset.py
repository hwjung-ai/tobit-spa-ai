#!/usr/bin/env python
"""Check if ci_compose_summary asset is registered in the database"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.db import get_session_context
from sqlmodel import select
from app.modules.asset_registry.models import TbAssetRegistry


def check_compose_asset() -> None:
    """Check for ci_compose_summary in the database"""
    with get_session_context() as session:
        # Check for published ci_compose_summary
        published = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "compose")
            .where(TbAssetRegistry.name == "ci_compose_summary")
            .where(TbAssetRegistry.status == "published")
        ).all()

        # Check for draft ci_compose_summary
        draft = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "compose")
            .where(TbAssetRegistry.name == "ci_compose_summary")
            .where(TbAssetRegistry.status == "draft")
        ).all()

        # Check for all prompts with compose engine
        all_compose = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.engine == "compose")
        ).all()

        print("\n" + "=" * 80)
        print("CHECKING ci_compose_summary ASSET REGISTRATION")
        print("=" * 80 + "\n")

        print(f"Published ci_compose_summary entries: {len(published)}")
        for asset in published:
            print(f"  ✓ {asset.asset_id} (v{asset.version}, {asset.status})")

        print(f"\nDraft ci_compose_summary entries: {len(draft)}")
        for asset in draft:
            print(f"  ✓ {asset.asset_id} (v{asset.version}, {asset.status})")

        print(f"\nAll 'compose' engine prompts: {len(all_compose)}")
        for asset in all_compose:
            print(f"  - {asset.name} ({asset.status})")

        if len(published) == 0 and len(draft) == 0:
            print("\n❌ ci_compose_summary is NOT registered in the database!")
            print("   Status: MISSING")
            print("\n   Action needed: Run seed_assets.py with --force flag to register compose.yaml")
        else:
            print("\n✓ ci_compose_summary is registered in the database")

        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    check_compose_asset()
