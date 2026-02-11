"""
Admin script to update Query Assets with tool_type, operation, and source_ref metadata.

This script updates Query Assets to include the necessary metadata for the QueryAssetRegistry
to dynamically discover and use queries with their associated Source Assets.
"""

from __future__ import annotations

import logging

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select

logger = logging.getLogger(__name__)

# Mapping of query asset names to their metadata configuration
QUERY_ASSET_MAPPING = {
    # Metric Tool Queries
    "metric_exists": {
        "tool_type": "metric",
        "operation": "exists",
        "source_ref": "primary_postgres",
    },
    "metric_list": {
        "tool_type": "metric",
        "operation": "list",
        "source_ref": "primary_postgres",
    },
    "metric_aggregate": {
        "tool_type": "metric",
        "operation": "aggregate",
        "source_ref": "primary_postgres",
    },
    "metric_series": {
        "tool_type": "metric",
        "operation": "series",
        "source_ref": "primary_postgres",
    },
    "metric_aggregate_by_ci": {
        "tool_type": "metric",
        "operation": "aggregate_by_ci",
        "source_ref": "primary_postgres",
    },
    # CI Tool Queries
    "ci_search": {
        "tool_type": "ci",
        "operation": "search",
        "source_ref": "primary_postgres",
    },
    "ci_get": {
        "tool_type": "ci",
        "operation": "get",
        "source_ref": "primary_postgres",
    },
    "ci_attributes": {
        "tool_type": "ci",
        "operation": "attributes",
        "source_ref": "primary_postgres",
    },
    "ci_aggregate_count": {
        "tool_type": "ci",
        "operation": "aggregate_count",
        "source_ref": "primary_postgres",
    },
    "ci_aggregate_group": {
        "tool_type": "ci",
        "operation": "aggregate_group",
        "source_ref": "primary_postgres",
    },
    "ci_aggregate_total": {
        "tool_type": "ci",
        "operation": "aggregate_total",
        "source_ref": "primary_postgres",
    },
    "ci_list_preview": {
        "tool_type": "ci",
        "operation": "list_preview",
        "source_ref": "primary_postgres",
    },
    "ci_list": {
        "tool_type": "ci",
        "operation": "list",
        "source_ref": "primary_postgres",
    },
    "ci_resolver_exact": {
        "tool_type": "ci",
        "operation": "resolver_exact",
        "source_ref": "primary_postgres",
    },
    "ci_resolver_pattern": {
        "tool_type": "ci",
        "operation": "resolver_pattern",
        "source_ref": "primary_postgres",
    },
    "resolve_ci": {
        "tool_type": "ci",
        "operation": "resolve",
        "source_ref": "primary_postgres",
    },
    # History Tool Queries
    "work_history": {
        "tool_type": "history",
        "operation": "work_history",
        "source_ref": "primary_postgres",
    },
    "work_history_recent": {
        "tool_type": "history",
        "operation": "work_history_recent",
        "source_ref": "primary_postgres",
    },
    "maintenance_history": {
        "tool_type": "history",
        "operation": "maintenance_history",
        "source_ref": "primary_postgres",
    },
    "maintenance_history_recent": {
        "tool_type": "history",
        "operation": "maintenance_history_recent",
        "source_ref": "primary_postgres",
    },
    "inspection_history": {
        "tool_type": "history",
        "operation": "inspection_history",
        "source_ref": "primary_postgres",
    },
    "event_log": {
        "tool_type": "history",
        "operation": "event_log",
        "source_ref": "primary_postgres",
    },
    "event_log_recent": {
        "tool_type": "history",
        "operation": "event_log_recent",
        "source_ref": "primary_postgres",
    },
    "event_log_columns": {
        "tool_type": "history",
        "operation": "event_log_columns",
        "source_ref": "primary_postgres",
    },
    "event_log_table_exists": {
        "tool_type": "history",
        "operation": "event_log_table_exists",
        "source_ref": "primary_postgres",
    },
}


def update_query_asset_metadata(dry_run: bool = True) -> None:
    """
    Update Query Assets with tool_type, operation, and source_ref metadata.

    Args:
        dry_run: If True, only print what would be updated without making changes
    """
    with get_session_context() as session:
        updated_count = 0
        skipped_count = 0
        not_found_count = 0

        for asset_name, metadata_config in QUERY_ASSET_MAPPING.items():
            # Query for the asset - get the published version
            query = (
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "query")
                .where(TbAssetRegistry.name == asset_name)
                .where(TbAssetRegistry.status == "published")
            )

            asset = session.exec(query).first()

            if not asset:
                logger.warning(f"Query Asset not found (published): {asset_name}")
                not_found_count += 1
                continue

            # Get current metadata
            current_metadata = asset.query_metadata or {}

            # Check if already set correctly
            if (
                current_metadata.get("tool_type") == metadata_config["tool_type"]
                and current_metadata.get("operation") == metadata_config["operation"]
                and current_metadata.get("source_ref") == metadata_config["source_ref"]
            ):
                logger.info(f"Skipping (already set): {asset_name}")
                skipped_count += 1
                continue

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would update: {asset_name}\n"
                    f"  Current: tool_type={current_metadata.get('tool_type')}, "
                    f"operation={current_metadata.get('operation')}, "
                    f"source_ref={current_metadata.get('source_ref')}\n"
                    f"  New: tool_type={metadata_config['tool_type']}, "
                    f"operation={metadata_config['operation']}, "
                    f"source_ref={metadata_config['source_ref']}"
                )
            else:
                # Update the metadata
                new_metadata = {
                    **current_metadata,
                    "tool_type": metadata_config["tool_type"],
                    "operation": metadata_config["operation"],
                    "source_ref": metadata_config["source_ref"],
                }
                asset.query_metadata = new_metadata
                session.add(asset)
                logger.info(
                    f"Updated: {asset_name} "
                    f"(tool_type={metadata_config['tool_type']}, "
                    f"operation={metadata_config['operation']}, "
                    f"source_ref={metadata_config['source_ref']})"
                )

            updated_count += 1

        if not dry_run:
            session.commit()

        logger.info("=" * 60)
        logger.info("Summary:")
        logger.info(f"  Updated: {updated_count}")
        logger.info(f"  Skipped: {skipped_count}")
        logger.info(f"  Not Found: {not_found_count}")
        logger.info("=" * 60)


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    force = "--force" in sys.argv or "-f" in sys.argv

    if dry_run and not force:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("Use --force to apply changes")
        print("=" * 60)
        print()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    update_query_asset_metadata(dry_run=dry_run or not force)
