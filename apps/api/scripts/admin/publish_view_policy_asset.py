#!/usr/bin/env python3
"""
Create or update view_depth_policies policy asset in Asset Registry.

This script migrates hardcoded VIEW_REGISTRY from view_registry.py to a policy asset in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.config import get_settings
from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry


def create_view_policy_asset():
    """Create view_depth_policies policy asset."""

    # Asset content matching the hardcoded VIEW_REGISTRY
    content = {
        "views": {
            "SUMMARY": {
                "description": "Top-level overview of a CI with immediate key statistics.",
                "default_depth": 1,
                "max_depth": 1,
                "direction_default": "BOTH",
                "output_defaults": ["overviews", "counts"],
            },
            "COMPOSITION": {
                "description": "System/component composition that highlights parent/child links.",
                "default_depth": 2,
                "max_depth": 3,
                "direction_default": "OUT",
                "output_defaults": ["hierarchy", "children"],
            },
            "DEPENDENCY": {
                "description": "Bidirectional dependency relationships for the selected CI.",
                "default_depth": 2,
                "max_depth": 3,
                "direction_default": "BOTH",
                "output_defaults": ["dependency_graph", "counts"],
            },
            "IMPACT": {
                "description": "Propagated impact along dependencies (assumption-based).",
                "default_depth": 2,
                "max_depth": 2,
                "direction_default": "OUT",
                "output_defaults": ["impact_summary"],
                "notes": "IMPACT는 의존 기반 영향(가정)으로 정의합니다.",
            },
            "PATH": {
                "description": "Path discovery capped by a maximum hop limit.",
                "default_depth": 3,
                "max_depth": 6,
                "direction_default": "BOTH",
                "output_defaults": ["path_segments"],
                "max_hops": 6,
            },
            "NEIGHBORS": {
                "description": "Immediate neighbors for the selected CI.",
                "default_depth": 1,
                "max_depth": 2,
                "direction_default": "BOTH",
                "output_defaults": ["neighbors"],
            },
        }
    }

    settings = get_settings()

    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "view_depth_policies",
            TbAssetRegistry.asset_type == "policy",
        ).first()

        if existing:
            print(f"⚠️  Asset 'view_depth_policies' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = "View depth policies for graph expansion - defines default/max depth, direction, and outputs for each view type"
            session.commit()
            print(f"✅ Updated asset 'view_depth_policies' (id={existing.asset_id})")
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name="view_depth_policies",
                asset_type="policy",
                scope="graph",
                description="View depth policies for graph expansion - defines default/max depth, direction, and outputs for each view type",
                content=content,
                status="published",
                tenant_id="system",  # System-wide policy
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset 'view_depth_policies' (id={asset.asset_id})")

        # Display the views
        print("\n📋 Configured views:")
        for view_name, view_config in content["views"].items():
            print(f"   • {view_name}: depth={view_config['default_depth']}/{view_config['max_depth']}, direction={view_config['direction_default']}")


if __name__ == "__main__":
    create_view_policy_asset()
