#!/usr/bin/env python3
"""
Create or update graph_relation_allowlist mapping asset in Asset Registry.

This script migrates hardcoded SUMMARY_NEIGHBORS_ALLOWLIST from policy.py to a mapping asset in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.asset_registry.models import TbAssetRegistry
from core.config import get_settings
from core.db import get_session_context


def create_graph_relation_mapping():
    """Create graph_relation_allowlist mapping asset."""

    # Asset content matching the hardcoded SUMMARY_NEIGHBORS_ALLOWLIST
    content = {
        "summary_neighbors_allowlist": [
            "COMPOSED_OF",
            "DEPENDS_ON",
            "RUNS_ON",
            "DEPLOYED_ON",
            "USES",
            "PROTECTED_BY",
            "CONNECTED_TO",
        ],
        "description": "Allowlist of relationship types for SUMMARY and NEIGHBORS views"
    }

    settings = get_settings()

    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "graph_relation_allowlist",
            TbAssetRegistry.asset_type == "mapping",
        ).first()

        if existing:
            print(f"⚠️  Asset 'graph_relation_allowlist' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = "Relationship type allowlist for graph views - controls which relation types are shown in SUMMARY and NEIGHBORS views"
            existing.mapping_type = "graph_relation"
            session.commit()
            print(f"✅ Updated asset 'graph_relation_allowlist' (id={existing.asset_id})")
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name="graph_relation_allowlist",
                asset_type="mapping",
                scope="graph",
                mapping_type="graph_relation",
                description="Relationship type allowlist for graph views - controls which relation types are shown in SUMMARY and NEIGHBORS views",
                content=content,
                status="published",
                tenant_id="system",  # System-wide mapping
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset 'graph_relation_allowlist' (id={asset.asset_id})")

        # Display the allowlist
        print("\n📋 Allowed relationship types:")
        for rel_type in content["summary_neighbors_allowlist"]:
            print(f"   • {rel_type}")


if __name__ == "__main__":
    create_graph_relation_mapping()
