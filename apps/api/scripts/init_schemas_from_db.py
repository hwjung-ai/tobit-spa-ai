#!/usr/bin/env python3
"""
Initialize Schema Assets from actual database

This script:
1. Connects to PostgreSQL and scans the actual schema
2. Creates a Schema Asset for each schema
3. Populates schema metadata (tables, columns, constraints)

This ensures Schema Assets match the real database structure.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add apps/api to Python path
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from dotenv import load_dotenv

# Load .env file BEFORE other imports
env_file = Path(__file__).resolve().parents[1] / ".env"
if env_file.exists():
    load_dotenv(env_file)

from core.db import get_session_context
from core.logging import get_logger
from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.ops.services.ci.discovery.catalog_factory import CatalogFactory
from datetime import datetime

logger = get_logger(__name__)


async def init_schemas_from_db():
    """
    Scan actual database and create Schema Assets.
    """
    # Get connection config from environment
    pg_host = os.getenv("PG_HOST", "localhost")
    pg_port = int(os.getenv("PG_PORT", "5432"))
    pg_user = os.getenv("PG_USER", "postgres")
    pg_password = os.getenv("PG_PASSWORD", "")
    pg_db = os.getenv("PG_DB", "postgres")

    source_asset = {
        "name": "primary_postgres",
        "source_type": "postgresql",
        "connection": {
            "host": pg_host,
            "port": pg_port,
            "username": pg_user,
            "password": pg_password,
            "database": pg_db,
            "timeout": 30,
            "ssl_mode": "prefer",
        }
    }

    print(f"[DEBUG] Environment - PG_HOST: {pg_host}, PG_PORT: {pg_port}, PG_USER: {pg_user}, PG_DB: {pg_db}")
    logger.info(f"Connecting to {pg_host}:{pg_port}/{pg_db} as {pg_user}")

    # Tables to exclude (tobit-spa-ai system tables)
    EXCLUDE_PATTERNS = [
        "tb_",  # System tables
        "alembic_",  # Migrations
        "api_",  # API management
        "chat_",  # Chat system
        "document",  # Document system
        "query_history",  # Query history
        "assets",  # Asset management
    ]

    def should_include_table(table_name: str) -> bool:
        """Check if table should be included in schema"""
        for pattern in EXCLUDE_PATTERNS:
            if table_name.lower().startswith(pattern.lower()):
                return False
        return True

    try:
        # Create catalog and scan
        print(f"[DEBUG] Creating catalog with source_asset: {source_asset}")
        catalog = CatalogFactory.create(source_asset)
        print(f"[DEBUG] Catalog created: {catalog}")
        logger.info("Scanning database schema...")

        # Scan default schema (public)
        catalog_data = await catalog.build_catalog(schema_names=["public"])

        # Filter out system tables
        original_count = len(catalog_data['tables'])
        catalog_data['tables'] = [
            table for table in catalog_data['tables']
            if should_include_table(table['name'])
        ]
        filtered_count = len(catalog_data['tables'])

        logger.info(f"Found {original_count} tables, keeping {filtered_count} domain tables (excluded {original_count - filtered_count} system tables)")

        with get_session_context() as session:
            # Check if primary_postgres_schema already exists
            existing = session.query(TbAssetRegistry).filter(
                TbAssetRegistry.asset_type == "catalog",
                TbAssetRegistry.name == "primary_postgres_schema",
            ).first()

            if existing:
                logger.info("Schema asset already exists, updating...")
                # Update existing schema with new metadata
                existing.content = {
                    "source_ref": "primary_postgres",
                    "catalog": {
                        "tables": catalog_data["tables"],
                        "database_type": catalog_data["database_type"],
                        "last_scanned_at": datetime.now().isoformat(),
                        "scan_status": "completed",
                        "scan_metadata": {
                            "schema_names": ["public"],
                            "table_count": len(catalog_data["tables"]),
                        }
                    },
                }
                existing.status = "published"
                existing.updated_at = datetime.now()
                session.add(existing)
                session.commit()
                logger.info(f"✓ Updated schema asset with {len(catalog_data['tables'])} tables")
            else:
                # Create new schema asset
                asset = TbAssetRegistry(
                    asset_id=str(uuid4()),
                    asset_type="schema",
                    name="primary_postgres_schema",
                    description="Primary PostgreSQL database schema - auto-discovered from database",
                    status="published",
                    version=1,
                    content={
                        "source_ref": "primary_postgres",
                        "catalog": {
                            "tables": catalog_data["tables"],
                            "database_type": catalog_data["database_type"],
                            "last_scanned_at": datetime.now().isoformat(),
                            "scan_status": "completed",
                            "scan_metadata": {
                                "schema_names": ["public"],
                                "table_count": len(catalog_data["tables"]),
                            }
                        },
                    },
                    created_by="system",
                    published_by="system",
                    published_at=datetime.now(),
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
                    published_by="system",
                    published_at=datetime.now(),
                )
                session.add(history)
                session.commit()

                logger.info(f"✓ Created schema asset: primary_postgres_schema (ID: {asset.asset_id})")

            # Log table details
            logger.info("\n📊 Scanned Tables:")
            for table in catalog_data["tables"]:
                col_count = len(table.get("columns", []))
                row_count = table.get("row_count", "?")
                logger.info(f"  • {table['name']} ({col_count} columns, {row_count} rows)")

        await catalog.close()
        logger.info("\n✓ Schema initialization completed successfully!")

    except Exception as e:
        logger.error(f"✗ Failed to initialize schemas: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Schema Assets from actual PostgreSQL database"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    logger.info("Starting database schema initialization...")
    asyncio.run(init_schemas_from_db())


if __name__ == "__main__":
    main()
