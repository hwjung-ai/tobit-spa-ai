"""
Admin script to create Neo4j Source Asset.

This script creates a Neo4j Source Asset in the Asset Registry for
use with Query Assets that need Cypher queries.
"""

from __future__ import annotations

import logging
import os
import uuid

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select

logger = logging.getLogger(__name__)


def create_neo4j_source_asset() -> None:
    """
    Create a Neo4j Source Asset in the database.

    The connection details are read from environment variables:
    - NEO4J_HOST: Neo4j server host (default: localhost)
    - NEO4J_USER: Neo4j username (default: neo4j)
    - NEO4J_PASSWORD: Neo4j password (via secret_key_ref)
    - NEO4J_DATABASE: Neo4j database name (default: neo4j)
    """
    neo4j_host = os.getenv("NEO4J_HOST", "localhost")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    asset_config = {
        "source_type": "neo4j",
        "connection": {
            "uri": f"bolt://{neo4j_host}:7687",
            "username": neo4j_user,
            "database": neo4j_database,
            "secret_key_ref": "env:NEO4J_PASSWORD",
            "max_connections": 50,
        },
        "spec": {
            "version": "5.x",
            "driver_version": "5.x",
        },
    }

    asset_name = "primary_neo4j"
    asset_description = "Primary Neo4j graph database source"

    with get_session_context() as session:
        # Check if asset already exists
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "source")
            .where(TbAssetRegistry.name == asset_name)
        )
        existing = session.exec(query).first()

        if existing:
            logger.info(f"Neo4j Source Asset '{asset_name}' already exists.")
            logger.info(
                f"  ID: {existing.asset_id}, Status: {existing.status}, Version: {existing.version}"
            )
            # Update to published if draft
            if existing.status == "draft":
                existing.status = "published"
                session.add(existing)
                session.commit()
                logger.info("  Updated status to 'published'")
            return

        # Create new asset
        new_asset = TbAssetRegistry(
            asset_id=uuid.uuid4(),
            asset_type="source",
            name=asset_name,
            description=asset_description,
            version=1,
            status="published",
            scope="default",
            content=asset_config,
            tags={"graph": "true", "cypher": "true"},
        )

        session.add(new_asset)
        session.commit()

        logger.info("Created Neo4j Source Asset:")
        logger.info(f"  ID: {new_asset.asset_id}")
        logger.info(f"  Name: {new_asset.name}")
        logger.info(f"  Status: {new_asset.status}")
        logger.info(f"  Version: {new_asset.version}")
        logger.info(f"  Connection URI: {asset_config['connection']['uri']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    create_neo4j_source_asset()
