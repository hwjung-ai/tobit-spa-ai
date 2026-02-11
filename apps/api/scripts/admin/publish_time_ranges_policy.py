#!/usr/bin/env python3
"""
Create or update time_ranges policy asset in Asset Registry.

This script migrates hardcoded TIME_RANGES from metric.py and history.py to a policy asset in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context


def create_time_ranges_policy():
    """Create time_ranges policy asset."""

    # Asset content - unified time ranges for metric and history tools
    content = {
        "time_ranges": {
            "last_1h": {
                "hours": 1,
                "description": "Last 1 hour"
            },
            "last_24h": {
                "hours": 24,
                "description": "Last 24 hours"
            },
            "last_7d": {
                "days": 7,
                "description": "Last 7 days"
            },
            "last_30d": {
                "days": 30,
                "description": "Last 30 days"
            }
        },
        "default_range": "last_24h",
        "description": "Time range definitions for metric and history queries"
    }

    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "time_ranges",
            TbAssetRegistry.asset_type == "policy",
        ).first()

        if existing:
            print(f"⚠️  Asset 'time_ranges' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = "Time range definitions for metric and history queries"
            existing.policy_type = "time_ranges"
            session.commit()
            print(f"✅ Updated asset 'time_ranges' (id={existing.asset_id})")
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name="time_ranges",
                asset_type="policy",
                policy_type="time_ranges",
                scope="ops",
                description="Time range definitions for metric and history queries",
                content=content,
                status="published",
                tenant_id="system",
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset 'time_ranges' (id={asset.asset_id})")

        # Display the time ranges
        print("\n📋 Configured time ranges:")
        for range_key, range_config in content["time_ranges"].items():
            if "hours" in range_config:
                print(f"   • {range_key}: {range_config['hours']} hours")
            elif "days" in range_config:
                print(f"   • {range_key}: {range_config['days']} days")


if __name__ == "__main__":
    create_time_ranges_policy()
