#!/usr/bin/env python3
"""
Demo Schema Asset Seeder

This script creates demo Schema Assets to showcase the Schema Auto-Discovery feature.
It directly creates schemas in the database without requiring YAML files.
"""

import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add apps/api to Python path
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from core.db import get_session_context
from core.logging import get_logger
from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from datetime import datetime

logger = get_logger(__name__)

# Demo schema definitions
DEMO_SCHEMAS = [
    {
        "name": "primary_schema",
        "description": "Primary PostgreSQL database schema - ready to scan",
        "asset_type": "schema",
        "content": {
            "source_ref": "primary_postgres",
            "catalog": {
                "scan_status": "pending",
                "tables": [],
                "database_type": "postgresql",
            },
        },
    },
    {
        "name": "factory_schema",
        "description": "Factory management database schema with equipment, maintenance, and production data",
        "asset_type": "schema",
        "content": {
            "source_ref": "primary_postgres",
            "catalog": {
                "scan_status": "pending",
                "tables": [],
                "database_type": "postgresql",
            },
        },
    },
]


def seed_schemas():
    """Create demo schema assets in the database."""
    with get_session_context() as session:
        for schema_def in DEMO_SCHEMAS:
            # Check if schema already exists
            existing = session.query(TbAssetRegistry).filter(
                TbAssetRegistry.asset_type == "schema",
                TbAssetRegistry.name == schema_def["name"],
            ).first()

            if existing:
                logger.info(f"Schema '{schema_def['name']}' already exists, skipping")
                continue

            try:
                # Create schema asset
                asset = TbAssetRegistry(
                    asset_id=str(uuid4()),
                    asset_type="schema",
                    name=schema_def["name"],
                    description=schema_def["description"],
                    status="draft",
                    version=1,
                    content=schema_def["content"],
                    created_by="system",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(asset)
                session.commit()
                session.refresh(asset)

                # Create version history
                history = TbAssetVersionHistory(
                    asset_id=asset.asset_id,
                    version=1,
                    snapshot={
                        "name": asset.name,
                        "description": asset.description,
                        "content": asset.content,
                    },
                    created_by="system",
                    created_at=datetime.now(),
                )
                session.add(history)
                session.commit()

                logger.info(
                    f"✓ Created schema asset: {schema_def['name']} (ID: {asset.asset_id})"
                )

            except Exception as e:
                logger.error(
                    f"✗ Failed to create schema '{schema_def['name']}': {e}",
                    exc_info=True,
                )
                session.rollback()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed demo Schema Assets into the database"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    logger.info("Starting demo schema seeding...")
    try:
        seed_schemas()
        logger.info("✓ Demo schema seeding completed successfully!")
    except Exception as e:
        logger.error(f"✗ Seeding failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
