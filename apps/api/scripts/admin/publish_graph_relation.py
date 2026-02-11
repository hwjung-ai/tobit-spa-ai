#!/usr/bin/env python3
"""
Create graph_relation mapping asset.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context


def create_graph_relation_asset():
    """Create graph_relation mapping asset."""
    content = {
        "views": {
            "COMPOSITION": {"rel_types": ["COMPOSED_OF"], "direction": "OUT"},
            "DEPENDENCY": {"rel_types": ["DEPENDS_ON"], "direction": "BOTH"},
            "IMPACT": {"rel_types": ["DEPENDS_ON"], "direction": "OUT"},
            "PATH": {"rel_types": ["DEPENDS_ON", "COMPOSED_OF", "RUNS_ON", "DEPLOYED_ON"], "direction": "BOTH"},
            "SUMMARY": {"rel_types": [], "direction": "BOTH"},
            "NEIGHBORS": {"rel_types": [], "direction": "BOTH"},
        },
        "exclude_rel_types": [],
        "description": "Graph relation mapping for view types"
    }

    with get_session_context() as session:
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "graph_relation",
            TbAssetRegistry.asset_type == "mapping",
        ).first()

        if existing:
            print(f"Asset 'graph_relation' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            session.commit()
            print(f"Updated asset 'graph_relation' (id={existing.asset_id})")
        else:
            asset = TbAssetRegistry(
                name="graph_relation",
                asset_type="mapping",
                scope="graph",
                mapping_type="graph_relation",
                description="Graph relation mapping for view types",
                content=content,
                status="published",
                tenant_id="system",
            )
            session.add(asset)
            session.commit()
            print(f"Created asset 'graph_relation' (id={asset.asset_id})")


if __name__ == "__main__":
    create_graph_relation_asset()
