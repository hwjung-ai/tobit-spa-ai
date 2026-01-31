"""
Register CI, Metric, and History tools with correct names to Asset Registry.

Tool names must match the tool_type used in stage_executor.py:
- ci_lookup (not ci_search)
- ci_aggregate
- metric (not metric_aggregate)
- ci_graph
- history (for event logs)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select


def register_ci_lookup_tool(session):
    """Register ci_lookup tool (name must match stage_executor usage)."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "ci_lookup")
    ).first()

    if existing:
        print(f"  Tool 'ci_lookup' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="ci_lookup",  # Must match tool_type in stage_executor
        description="Search and lookup Configuration Items (CIs) using keywords and filters",
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
LIMIT {limit}
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
                    "description": "Filters to apply",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                },
                "mode": {
                    "type": "string",
                    "enum": ["primary", "secondary"],
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "references": {"type": "array", "items": {"type": "object"}},
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered ci_lookup tool")


def register_metric_tool(session):
    """Register metric tool (name must match stage_executor usage)."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "metric")
    ).first()

    if existing:
        print(f"  Tool 'metric' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="metric",  # Must match tool_type in stage_executor
        description="Aggregate and query metric values (AVG, MAX, MIN, SUM, COUNT), grouped by CI",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT ci.ci_id, ci.ci_name, {function}(mv.value) AS metric_value
FROM metric_value mv
JOIN metric_def md ON mv.metric_id = md.metric_id
JOIN ci ON mv.ci_id = ci.ci_id
WHERE mv.tenant_id = '{tenant_id}'
  AND md.metric_name = '{metric_name}'
  AND mv.ci_id = ANY(ARRAY{ci_ids})
  AND mv.time >= '{start_time}'
  AND mv.time < '{end_time}'
GROUP BY ci.ci_id, ci.ci_name
ORDER BY metric_value DESC
LIMIT {limit}
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation to perform (aggregate_by_ci, etc)",
                },
                "metric_name": {
                    "type": "string",
                    "description": "Name of the metric to query",
                },
                "agg": {
                    "type": "string",
                    "enum": ["AVG", "MAX", "MIN", "SUM", "COUNT"],
                },
                "time_range": {
                    "type": "string",
                },
                "filters": {
                    "type": "array",
                },
                "top_n": {
                    "type": "integer",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "references": {"type": "array", "items": {"type": "object"}},
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered metric tool")


def register_ci_graph_tool(session):
    """Register ci_graph tool (name must match stage_executor usage)."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "ci_graph")
    ).first()

    if existing:
        print(f"  Tool 'ci_graph' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="ci_graph",  # Must match tool_type in stage_executor
        description="Query CI relationship graphs (dependency, composition, impact, path)",
        tool_type="graph_query",
        tool_config={
            "source_ref": "default_neo4j",
            "query_template": """
MATCH path = (source)-[*1..{depth}]->(target)
WHERE source.ci_id IN {source_ids}
RETURN path
LIMIT {limit}
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "depth": {
                    "type": "integer",
                    "description": "Graph traversal depth",
                },
                "view": {
                    "type": "string",
                    "enum": ["dependency", "composition", "impact", "path", "neighbors"],
                },
                "limits": {
                    "type": "object",
                },
                "user_requested_depth": {
                    "type": "boolean",
                },
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "nodes": {"type": "array", "items": {"type": "object"}},
                "edges": {"type": "array", "items": {"type": "object"}},
                "references": {"type": "array", "items": {"type": "object"}},
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered ci_graph tool")


def register_history_tool(session):
    """Register history tool for event/maintenance logs."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "history")
    ).first()

    if existing:
        print(f"  Tool 'history' already exists (v{existing.version}), skipping...")
        return

    tool = TbAssetRegistry(
        asset_type="tool",
        name="history",  # Generic history tool
        description="Query event logs and maintenance history",
        tool_type="database_query",
        tool_config={
            "source_ref": "default_postgres",
            "query_template": """
SELECT el.time, el.severity, el.event_type, el.source, el.title,
       c.ci_code, c.ci_name
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
                "ci_id": {"type": "string"},
                "time_range": {"type": "string"},
                "event_type": {"type": "string"},
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "references": {"type": "array", "items": {"type": "object"}},
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered history tool")


def main():
    """Register all tools with correct names."""
    print("Registering CI/Metric/Graph/History tools with correct names...")
    print()

    with get_session_context() as session:
        print("Core Tools (matching stage_executor tool_type):")
        register_ci_lookup_tool(session)
        register_ci_aggregate_tool(session)  # already exists with correct name
        register_metric_tool(session)
        register_ci_graph_tool(session)
        register_history_tool(session)

        session.commit()
        print()
        print("✅ All tools registered successfully!")
        print()

        # Count total tools
        total = session.exec(
            select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")
        ).all()
        print(f"Total tool assets in database: {len(total)}")


def register_ci_aggregate_tool(session):
    """Check if ci_aggregate already exists (should exist from previous script)."""
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.name == "ci_aggregate")
    ).first()

    if existing:
        print(f"  Tool 'ci_aggregate' already exists (v{existing.version}), skipping...")
        return

    # If not exists, create it
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
LIMIT {limit}
""",
        },
        tool_input_schema={
            "type": "object",
            "properties": {
                "group_by": {"type": "array"},
                "metrics": {"type": "array"},
                "filters": {"type": "array"},
                "top_n": {"type": "integer"},
            },
        },
        tool_output_schema={
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "references": {"type": "array", "items": {"type": "object"}},
            },
        },
        status="published",
        version=1,
    )
    session.add(tool)
    print("  ✓ Registered ci_aggregate tool")


if __name__ == "__main__":
    main()
