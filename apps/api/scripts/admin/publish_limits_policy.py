#!/usr/bin/env python3
"""
Create or update limits policy asset in Asset Registry.

This script migrates hardcoded limit constants from ci.py, history.py, graph.py to a policy asset in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context


def create_limits_policy():
    """Create limits policy asset."""

    # Asset content - unified limits for all tools
    content = {
        "ci": {
            "max_search_limit": 50,
            "max_agg_rows": 200,
            "default_search_limit": 10,
            "default_agg_limit": 50
        },
        "history": {
            "max_limit": 200,
            "default_limit": 50
        },
        "graph": {
            "max_nodes": 200,
            "max_edges": 400,
            "max_paths": 25
        },
        "metric": {
            "max_ci_ids": 300,
            "default_top_n": 10
        },
        "description": "Limit configurations for all OPS tools"
    }

    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "tool_limits",
            TbAssetRegistry.asset_type == "policy",
        ).first()

        if existing:
            print(f"⚠️  Asset 'tool_limits' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = "Limit configurations for all OPS tools (ci, history, graph, metric)"
            existing.policy_type = "tool_limits"
            session.commit()
            print(f"✅ Updated asset 'tool_limits' (id={existing.asset_id})")
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name="tool_limits",
                asset_type="policy",
                policy_type="tool_limits",
                scope="ops",
                description="Limit configurations for all OPS tools (ci, history, graph, metric)",
                content=content,
                status="published",
                tenant_id="system",
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset 'tool_limits' (id={asset.asset_id})")

        # Display the limits
        print("\n📋 Configured limits:")
        for tool_name, tool_limits in content.items():
            if tool_name != "description" and isinstance(tool_limits, dict):
                print(f"\n   {tool_name.upper()}:")
                for limit_key, limit_value in tool_limits.items():
                    print(f"      • {limit_key}: {limit_value}")


if __name__ == "__main__":
    create_limits_policy()
