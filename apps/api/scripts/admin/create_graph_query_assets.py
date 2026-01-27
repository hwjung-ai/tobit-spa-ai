"""
Admin script to create Graph Query Assets with Cypher queries.

This script creates Query Assets for graph operations that use Neo4j,
adding query_cypher content to the assets.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from core.db import get_session_context
from sqlmodel import select

from app.modules.asset_registry.models import TbAssetRegistry
from app.shared.config_loader import load_text

logger = logging.getLogger(__name__)

# Graph query mapping: asset name -> (operation, description)
GRAPH_QUERIES = {
    "graph_expand": ("expand", "Expand graph from root CI node"),
    "graph_path": ("path", "Find path between two CI nodes"),
    "dependency_expand": ("dependency_expand", "Expand dependency relationships"),
    "dependency_paths": ("dependency_paths", "Find all dependency paths"),
    "component_composition": ("component_composition", "Get component composition graph"),
}


def create_graph_query_asset(
    name: str,
    operation: str,
    description: str,
    cypher_content: str,
) -> None:
    """
    Create or update a Graph Query Asset with Cypher content.

    Args:
        name: Asset name (e.g., "graph_expand")
        operation: Operation name for query registry
        description: Human-readable description
        cypher_content: Cypher query content
    """
    with get_session_context() as session:
        # Check if asset already exists
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "query")
            .where(TbAssetRegistry.name == name)
        )
        existing = session.exec(query).first()

        metadata = {
            "tool_type": "graph",
            "operation": operation,
            "source_ref": "primary_neo4j",
            "source_type": "neo4j",
        }

        if existing:
            # Update existing asset
            existing.query_cypher = cypher_content
            existing.query_metadata = metadata
            existing.description = description
            existing.status = "published"
            session.add(existing)
            session.commit()
            logger.info(f"Updated Query Asset: {name}")
        else:
            # Create new asset
            new_asset = TbAssetRegistry(
                asset_id=uuid.uuid4(),
                asset_type="query",
                name=name,
                description=description,
                version=1,
                status="published",
                scope="default",
                query_cypher=cypher_content,
                query_metadata=metadata,
            )
            session.add(new_asset)
            session.commit()
            logger.info(f"Created Query Asset: {name}")


def main() -> None:
    """Create all Graph Query Assets."""
    # Get the correct path to resources/queries/neo4j/graph
    # Script is at apps/api/scripts/admin/create_graph_query_assets.py
    # Resources are at apps/api/resources/queries/neo4j/graph
    script_dir = Path(__file__).resolve().parent
    queries_dir = script_dir.parents[1] / "resources/queries/neo4j/graph"

    if not queries_dir.exists():
        logger.error(f"Queries directory not found: {queries_dir}")
        return

    created_count = 0
    for filename, (operation, description) in GRAPH_QUERIES.items():
        cypher_file = queries_dir / f"{filename}.cypher"
        if not cypher_file.exists():
            logger.warning(f"Cypher file not found: {cypher_file}")
            continue

        # Load Cypher content
        cypher_content = load_text(f"queries/neo4j/graph/{filename}.cypher")
        if not cypher_content:
            logger.warning(f"Failed to load Cypher query: {filename}")
            continue

        # Create Query Asset
        create_graph_query_asset(filename, operation, description, cypher_content)
        created_count += 1

    logger.info(f"{'=' * 60}")
    logger.info(f"Summary: {created_count} Graph Query Assets processed")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    main()
