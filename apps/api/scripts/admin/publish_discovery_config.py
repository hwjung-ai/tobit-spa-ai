#!/usr/bin/env python3
"""
Create or update discovery_config policy asset in Asset Registry.

This script migrates hardcoded TARGET_TABLES and AGG_COLUMNS from postgres_catalog.py
and neo4j_catalog.py to a policy asset in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry


def create_discovery_config():
    """Create discovery_config policy asset."""

    # Asset content - discovery configurations for PostgreSQL and Neo4j catalog generation
    content = {
        "postgres": {
            "target_tables": [
                "ci",
                "ci_ext"
            ],
            "agg_columns": [
                "ci_type",
                "ci_subtype",
                "ci_category",
                "status",
                "location",
                "owner"
            ],
            "description": "PostgreSQL discovery configuration - tables and columns to analyze during catalog generation"
        },
        "neo4j": {
            "target_labels": [
                "CI"
            ],
            "rel_types": [
                "COMPOSED_OF",
                "DEPENDS_ON",
                "RUNS_ON",
                "DEPLOYED_ON",
                "USES",
                "PROTECTED_BY",
                "CONNECTED_TO"
            ],
            "expected_ci_properties": [
                "ci_id",
                "ci_code",
                "tenant_id"
            ],
            "description": "Neo4j discovery configuration - node labels, relationship types, and expected properties to analyze during catalog generation"
        },
        "description": "Discovery configurations for catalog generation from PostgreSQL and Neo4j sources"
    }

    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == "discovery_config",
            TbAssetRegistry.asset_type == "policy",
        ).first()

        if existing:
            print(f"⚠️  Asset 'discovery_config' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = "Discovery configurations for catalog generation from various data sources"
            existing.policy_type = "discovery_config"
            session.commit()
            print(f"✅ Updated asset 'discovery_config' (id={existing.asset_id})")
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name="discovery_config",
                asset_type="policy",
                policy_type="discovery_config",
                scope="discovery",
                description="Discovery configurations for catalog generation from various data sources",
                content=content,
                status="published",
                tenant_id="system",
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset 'discovery_config' (id={asset.asset_id})")

        # Display the configuration
        print("\n📋 Configured discovery settings:")

        print(f"\n   POSTGRESQL:")
        print(f"      Target Tables ({len(content['postgres']['target_tables'])} tables):")
        for table in content["postgres"]["target_tables"]:
            print(f"         • {table}")
        print(f"      Aggregation Columns ({len(content['postgres']['agg_columns'])} columns):")
        for col in content["postgres"]["agg_columns"]:
            print(f"         • {col}")

        print(f"\n   NEO4J:")
        print(f"      Target Labels ({len(content['neo4j']['target_labels'])} labels):")
        for label in content["neo4j"]["target_labels"]:
            print(f"         • {label}")
        print(f"      Relationship Types ({len(content['neo4j']['rel_types'])} types):")
        for rel_type in content["neo4j"]["rel_types"]:
            print(f"         • {rel_type}")


if __name__ == "__main__":
    create_discovery_config()
