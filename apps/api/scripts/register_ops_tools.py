#!/usr/bin/env python3
"""
Register OPS Tool Assets to Database

This script registers all OPS-related Tool Assets that replace hardcoded SQL queries.
It should be run once during deployment or when adding new tools.

Usage:
    python scripts/register_ops_tools.py [--reset]

Options:
    --reset: Remove all existing OPS tools before registering (dangerous!)
"""

import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from core.logging import get_logger

logger = get_logger(__name__)


def load_sql_file(filename: str) -> str:
    """Load SQL file content from resources/queries"""
    filepath = Path(__file__).parent.parent / "resources" / "queries" / "postgres" / filename
    if not filepath.exists():
        raise FileNotFoundError(f"SQL file not found: {filepath}")
    return filepath.read_text()


# Define all Tool Assets for OPS
TOOL_ASSETS: List[Dict[str, Any]] = [
    # CI Lookup Tools
    {
        "name": "ci_detail_lookup",
        "asset_type": "tool",
        "tool_type": "database_query",
        "status": "published",
        "version": 1,
        "description": "Fetch CI configuration details including extended attributes and tags",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": load_sql_file("ci/ci_detail_lookup.sql"),
        },
        "tool_input_schema": {
            "type": "object",
            "required": ["field", "value", "tenant_id"],
            "properties": {
                "field": {
                    "type": "string",
                    "enum": ["ci_id", "ci_code"],
                    "description": "Which field to search on",
                },
                "value": {"type": "string", "description": "Value to search for"},
                "tenant_id": {"type": "string", "description": "Tenant identifier"},
            },
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ci_id": {"type": "string"},
                            "ci_code": {"type": "string"},
                            "ci_name": {"type": "string"},
                            "ci_type": {"type": "string"},
                            "status": {"type": "string"},
                        },
                    },
                }
            },
        },
        "tags": {"category": "ci", "operation": "lookup", "phase": "2"},
    },
    {
        "name": "ci_summary_aggregate",
        "asset_type": "tool",
        "tool_type": "database_query",
        "status": "published",
        "version": 1,
        "description": "Aggregate CI distribution by type, subtype, and status",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": load_sql_file("ci/ci_summary_aggregate.sql"),
        },
        "tool_input_schema": {
            "type": "object",
            "required": ["tenant_id"],
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant identifier"},
            },
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ci_type": {"type": "string"},
                            "ci_subtype": {"type": "string"},
                            "status": {"type": "string"},
                            "cnt": {"type": "integer"},
                        },
                    },
                }
            },
        },
        "tags": {"category": "ci", "operation": "aggregate", "phase": "2"},
    },
    {
        "name": "ci_list_paginated",
        "asset_type": "tool",
        "tool_type": "database_query",
        "status": "published",
        "version": 1,
        "description": "List all CIs with pagination support",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": load_sql_file("ci/ci_list_paginated.sql"),
        },
        "tool_input_schema": {
            "type": "object",
            "required": ["tenant_id", "limit", "offset"],
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant identifier"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Number of results to return",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of results to skip",
                },
            },
        },
        "tags": {"category": "ci", "operation": "list", "phase": "2"},
    },
    # Maintenance History Tools
    {
        "name": "maintenance_history_list",
        "asset_type": "tool",
        "tool_type": "database_query",
        "status": "published",
        "version": 1,
        "description": "List maintenance records with optional filtering and pagination",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": load_sql_file("history/maintenance_history_paginated.sql"),
        },
        "tool_input_schema": {
            "type": "object",
            "required": ["tenant_id"],
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant identifier"},
                "ci_id": {
                    "type": ["string", "null"],
                    "description": "Filter by CI ID (optional)",
                },
                "start_time": {
                    "type": ["string", "null"],
                    "format": "date-time",
                    "description": "Filter by start time (optional)",
                },
                "end_time": {
                    "type": ["string", "null"],
                    "format": "date-time",
                    "description": "Filter by end time (optional)",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Number of results to skip",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "description": "Number of results to return",
                },
            },
        },
        "tags": {"category": "maintenance", "operation": "list", "phase": "2"},
    },
    {
        "name": "maintenance_ticket_create",
        "asset_type": "tool",
        "tool_type": "database_query",
        "status": "published",
        "version": 1,
        "description": "Create a new maintenance ticket",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": load_sql_file("history/maintenance_ticket_create.sql"),
        },
        "tool_input_schema": {
            "type": "object",
            "required": ["tenant_id", "ci_id", "maint_type", "summary", "start_time", "performer"],
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Ticket ID (auto-generated if omitted)",
                },
                "tenant_id": {"type": "string", "description": "Tenant identifier"},
                "ci_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "CI to create ticket for",
                },
                "maint_type": {
                    "type": "string",
                    "enum": ["Preventive", "Corrective", "Inspection", "Emergency"],
                    "description": "Type of maintenance",
                },
                "summary": {"type": "string", "description": "Brief description"},
                "detail": {"type": "string", "description": "Detailed description"},
                "start_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "When maintenance starts",
                },
                "performer": {"type": "string", "description": "Person performing maintenance"},
            },
        },
        "tags": {"category": "maintenance", "operation": "create", "phase": "2"},
    },
    {
        "name": "history_combined_union",
        "asset_type": "tool",
        "tool_type": "database_query",
        "status": "published",
        "version": 1,
        "description": "Fetch combined work and maintenance history",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": load_sql_file("history/work_and_maintenance_union.sql"),
        },
        "tool_input_schema": {
            "type": "object",
            "required": ["tenant_id"],
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant identifier"},
                "ci_id": {
                    "type": ["string", "null"],
                    "description": "Filter by CI ID (optional)",
                },
                "start_time": {
                    "type": ["string", "null"],
                    "format": "date-time",
                    "description": "Filter by start time (optional)",
                },
                "end_time": {
                    "type": ["string", "null"],
                    "format": "date-time",
                    "description": "Filter by end time (optional)",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 30,
                    "description": "Number of results to return",
                },
            },
        },
        "tags": {"category": "history", "operation": "union", "phase": "2"},
    },
]


def reset_existing_tools():
    """Remove all existing OPS tools (dangerous!)"""
    with get_session_context() as session:
        # Find and delete all OPS tools
        tools = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.asset_type == "tool",
            TbAssetRegistry.name.in_([tool["name"] for tool in TOOL_ASSETS])
        ).all()

        logger.warning(f"Deleting {len(tools)} existing OPS tools...")
        for tool in tools:
            session.delete(tool)

        session.commit()
        logger.info("Deleted existing OPS tools")


def register_tools():
    """Register all OPS Tool Assets"""
    with get_session_context() as session:
        for tool_def in TOOL_ASSETS:
            # Check if tool already exists
            existing = session.query(TbAssetRegistry).filter_by(
                name=tool_def["name"],
                asset_type="tool"
            ).first()

            if existing:
                logger.info(f"Tool '{tool_def['name']}' already exists, skipping...")
                continue

            # Create new tool asset
            tool_asset = TbAssetRegistry(
                asset_id=str(uuid.uuid4()),
                asset_type=tool_def["asset_type"],
                name=tool_def["name"],
                description=tool_def["description"],
                tool_type=tool_def["tool_type"],
                tool_config=tool_def["tool_config"],
                tool_input_schema=tool_def["tool_input_schema"],
                tool_output_schema=tool_def.get("tool_output_schema"),
                status=tool_def["status"],
                version=tool_def["version"],
                tags=tool_def.get("tags"),
                created_by="system",
                published_by="system",
            )

            session.add(tool_asset)
            logger.info(f"Registered tool: {tool_def['name']}")

        session.commit()
        logger.info(f"Successfully registered {len(TOOL_ASSETS)} OPS tools")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Register OPS Tool Assets")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove all existing OPS tools before registering (dangerous!)",
    )

    args = parser.parse_args()

    try:
        if args.reset:
            confirm = input(
                "WARNING: This will delete all existing OPS tools. Continue? (yes/no): "
            )
            if confirm.lower() != "yes":
                logger.info("Cancelled")
                return

            reset_existing_tools()

        register_tools()
        logger.info("✅ Tool registration complete!")

    except Exception as e:
        logger.error(f"❌ Registration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
