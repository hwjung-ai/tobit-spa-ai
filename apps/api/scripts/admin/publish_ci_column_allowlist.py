#!/usr/bin/env python3
"""
Create or update ci_column_allowlist policy asset in Asset Registry.

This script migrates hardcoded SEARCH_COLUMNS and FILTER_FIELDS from ci.py to a policy asset in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry


def create_ci_column_allowlist():
    """Create ci_column_allowlist policy asset."""

    # Asset content - unified column allowlists for CI operations
    content = {
        "search_columns": [
            "ci_code",
            "ci_name",
            "ci_type",
            "ci_subtype",
            "ci_category"
        ],
        "filter_fields": [
            "ci_type",
            "ci_subtype",
            "ci_category",
            "status",
            "location",
            "owner"
        ],
        "jsonb_tag_keys": [
            "system",
            "role",
            "runs_on",
            "host_server",
            "ci_subtype",
            "connected_servers"
        ],
        "jsonb_attr_keys": [
            "engine",
            "version",
            "zone",
            "ip",
            "cpu_cores",
            "memory_gb"
        ],
        "description": "Column allowlists for CI search, filter, and JSONB field validation"
    }

    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "ci_column_allowlist",
            TbAssetRegistry.asset_type == "policy",
        ).first()

        if existing:
            print(f"⚠️  Asset 'ci_column_allowlist' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = "Column allowlists for CI operations - controls searchable columns, filter fields, and JSONB keys"
            existing.policy_type = "column_allowlist"
            session.commit()
            print(f"✅ Updated asset 'ci_column_allowlist' (id={existing.asset_id})")
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name="ci_column_allowlist",
                asset_type="policy",
                policy_type="column_allowlist",
                scope="ci",
                description="Column allowlists for CI operations - controls searchable columns, filter fields, and JSONB keys",
                content=content,
                status="published",
                tenant_id="system",
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset 'ci_column_allowlist' (id={asset.asset_id})")

        # Display the configuration
        print("\n📋 Configured column allowlists:")
        print(f"\n   SEARCH_COLUMNS ({len(content['search_columns'])} columns):")
        for col in content["search_columns"]:
            print(f"      • {col}")

        print(f"\n   FILTER_FIELDS ({len(content['filter_fields'])} fields):")
        for field in content["filter_fields"]:
            print(f"      • {field}")

        print(f"\n   JSONB_TAG_KEYS ({len(content['jsonb_tag_keys'])} keys):")
        for key in content["jsonb_tag_keys"]:
            print(f"      • {key}")

        print(f"\n   JSONB_ATTR_KEYS ({len(content['jsonb_attr_keys'])} keys):")
        for key in content["jsonb_attr_keys"]:
            print(f"      • {key}")


if __name__ == "__main__":
    create_ci_column_allowlist()
