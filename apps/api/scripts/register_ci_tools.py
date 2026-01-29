"""
Register CI, Metric, and History tools to Asset Registry.

This script creates Tool Assets for the generic orchestration system,
replacing the old hardcoded tools (ci, metric, graph, history, cep).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add apps/api to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select


def register_ci_search_tool(session):
    """Register ci_search tool for searching CIs."""
    # Check if already exists
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "ci_search")
    ).first()

    if existing:
        print(f"  Tool 'ci_search' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="ci_search",
        description="Search for Configuration Items (CIs) using keywords and filters",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT ci.ci_id, ci.ci_code, ci.ci_name, ci.ci_type, ci.ci_subtype, ci.ci_category,
       ci.status, ci.location, ci.owner
FROM ci
LEFT JOIN ci_ext ON ci.ci_id = ci_ext.ci_id
WHERE {where_clause}
ORDER BY {order_by} {direction}
LIMIT %s
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for in CI name/code",
                },
                "filters": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Filters to apply (field, operator, value)",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of results to return",
                },
                "sort": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sort field and direction",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered ci_search tool")


def register_ci_aggregate_tool(session):
    """Register ci_aggregate tool for aggregating CI data."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "ci_aggregate")
    ).first()

    if existing:
        print(f"  Tool 'ci_aggregate' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="ci_aggregate",
        description="Aggregate CI data with COUNT, GROUP BY operations",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT {select_clause}, COUNT(*) as count
FROM ci
WHERE {where_clause}
GROUP BY {group_clause}
ORDER BY count DESC
LIMIT %s
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to group by (e.g., ci_type, status)",
                },
                "filters": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Filters to apply",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of results",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered ci_aggregate tool")


def register_metric_aggregate_tool(session):
    """Register metric_aggregate tool for aggregating metrics."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "metric_aggregate")
    ).first()

    if existing:
        print(f"  Tool 'metric_aggregate' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="metric_aggregate",
        description="Aggregate metric values with AVG, MAX, MIN, SUM operations",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT {function}(mv.value) AS value
FROM metric_value mv
JOIN metric_def md ON mv.metric_id = md.metric_id
WHERE mv.tenant_id = '{tenant_id}'
  AND md.metric_name = '{metric_name}'
  AND mv.ci_id = ANY(ARRAY{ci_ids})
  AND mv.time >= '{start_time}'
  AND mv.time < '{end_time}'
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": "Name of the metric to aggregate",
                },
                "function": {
                    "type": "string",
                    "enum": ["AVG", "MAX", "MIN", "SUM", "COUNT"],
                    "description": "Aggregation function",
                },
                "ci_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "CI IDs to aggregate metrics for",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range (e.g., '1h', '24h', '7d')",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered metric_aggregate tool")


def register_metric_list_tool(session):
    """Register metric_list tool for listing available metrics."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "metric_list")
    ).first()

    if existing:
        print(f"  Tool 'metric_list' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="metric_list",
        description="List all available metrics in the system",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT metric_id, metric_name, unit, description, value_type
FROM metric_def
WHERE tenant_id = '{tenant_id}'
ORDER BY metric_name
LIMIT 100
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {},
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered metric_list tool")


def register_event_log_tool(session):
    """Register event_log tool for querying event logs."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "event_log")
    ).first()

    if existing:
        print(f"  Tool 'event_log' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="event_log",
        description="Query event logs for a specific CI and time range",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT el.time, el.severity, el.event_type, el.source, el.title, c.ci_code, c.ci_name
FROM event_log AS el
LEFT JOIN ci AS c ON c.ci_id = el.ci_id
WHERE el.tenant_id = '{tenant_id}'
  AND el.ci_id = '{ci_id}'
  AND el.time >= '{start_time}'
  AND el.time < '{end_time}'
ORDER BY el.severity DESC, el.time DESC
LIMIT 50
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "ci_id": {
                    "type": "string",
                    "description": "CI ID to query events for",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range (e.g., '1h', '24h', '7d')",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered event_log tool")


def register_event_aggregate_tool(session):
    """Register event_aggregate tool for aggregating events by type."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "event_aggregate")
    ).first()

    if existing:
        print(f"  Tool 'event_aggregate' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="event_aggregate",
        description="Aggregate events by event_type, severity, or time period",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT {group_field}, COUNT(*) as count
FROM event_log
WHERE tenant_id = '{tenant_id}'
  AND deleted_at IS NULL
  {time_filter}
GROUP BY {group_field}
ORDER BY count DESC
LIMIT 100
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "enum": ["event_type", "severity", "source"],
                    "description": "Field to group by",
                },
                "time_range": {
                    "type": "string",
                    "description": "Optional time range",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered event_aggregate tool")


def main():
    """Register all CI, Metric, and History tools."""
    print("Registering CI, Metric, and History tools to Asset Registry...")
    print()

    with get_session_context() as session:
        # Register CI tools
        print("CI Tools:")
        register_ci_search_tool(session)
        register_ci_aggregate_tool(session)

        print()

        # Register Metric tools
        print("Metric Tools:")
        register_metric_aggregate_tool(session)
        register_metric_list_tool(session)

        print()

        # Register History/Event tools
        print("History/Event Tools:")
        register_event_log_tool(session)
        register_event_aggregate_tool(session)

        session.commit()
        print()
        print("✅ All tools registered successfully!")
        print()

        # Count total tools
        total = session.exec(
            select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")
        ).all()
        print(f"Total tool assets in database: {len(total)}")


if __name__ == "__main__":
    main()
