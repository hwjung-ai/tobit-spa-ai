"""Block building utilities for orchestration.

This module handles conversion of tool output data to display blocks
for metrics, history, and graph visualization.
"""

from typing import Any, Dict, List

from app.modules.ops.services.orchestration.blocks import (
    Block,
    table_block,
    text_block,
)
from app.modules.ops.services.orchestration.planner.plan_schema import MetricSpec, View


def build_metric_blocks_from_data(
    data: Dict[str, Any],
    metric_name: str,
    detail: Dict[str, Any],
    series_chart_builder=None,
) -> tuple[List[Block], Dict[str, Any] | None]:
    """Convert metric_query Tool Asset output to display blocks.

    Args:
        data: Tool output with 'rows' key
        metric_name: Name of the metric
        detail: CI detail information
        series_chart_builder: Optional function to build series chart

    Returns:
        Tuple of (blocks, metric_context)
    """
    rows = data.get("rows", [])
    metric_context = None

    if not rows:
        ci_code = detail.get("ci_code") or detail.get("ci_id") or "unknown"
        return [
            text_block(
                f"{metric_name} ({metric_name}) returned no data for CI {ci_code}",
                title="Metric data unavailable",
            ),
        ], metric_context

    blocks: List[Block] = []

    # Create time series chart if we have multiple data points
    if len(rows) > 1 and series_chart_builder:
        try:
            times = [str(r.get("time", ""))[:10] for r in rows]
            values = [float(r.get("value", 0)) for r in rows]

            chart = series_chart_builder(
                detail,
                MetricSpec(
                    metric_name=metric_name,
                    agg="AVG",
                    time_range={"days": 7},
                ),
                [[times[i], values[i]] for i in range(len(times))],
            )
            if chart:
                blocks.append(chart)
        except Exception:
            # Silently skip chart on error, continue with table
            pass

    # Create summary table
    table_rows = [
        [
            str(r.get("time", ""))[:19],
            str(round(float(r.get("value", 0)), 2)) if r.get("value") else "null",
            r.get("unit", ""),
        ]
        for r in rows
    ]

    blocks.append(
        table_block(
            ["Time", "Value", "Unit"],
            table_rows,
            title=f"{metric_name} Details",
        )
    )

    # Store context for later use
    if rows:
        latest = rows[0]
        metric_context = {
            "metric_name": metric_name,
            "time_range": {"days": 7},
            "agg": "AVG",
            "value": float(latest.get("value", 0)) if latest.get("value") else None,
        }

    return blocks, metric_context


def build_history_blocks_from_data(
    data: Dict[str, Any],
    history_type: str,
) -> List[Block]:
    """Convert work/maintenance history Tool Asset output to display blocks.

    Args:
        data: Tool output with 'rows' key
        history_type: Type of history (work, maintenance, etc.)

    Returns:
        List of display blocks
    """
    rows = data.get("rows", [])

    if not rows:
        return [
            text_block(
                f"No {history_type} records found",
                title=f"{history_type.capitalize()} History",
            ),
        ]

    blocks: List[Block] = []

    # Create summary text
    blocks.append(
        text_block(
            f"Found {len(rows)} {history_type} records",
            title=f"{history_type.capitalize()} History",
        )
    )

    # Create detailed table
    table_rows = [
        [
            rows[i].get("work_type", rows[i].get("maint_type", ""))[:20],
            rows[i].get("summary", "")[:50],
            str(rows[i].get("start_time", ""))[:10],
            str(rows[i].get("duration_min", 0)),
            rows[i].get("result", ""),
        ]
        for i in range(len(rows))
    ]

    blocks.append(
        table_block(
            ["Type", "Summary", "Start Date", "Duration (min)", "Result"],
            table_rows,
            title=f"{history_type.capitalize()} Details",
        )
    )

    return blocks


def build_graph_payload_from_tool_data(
    data: Dict[str, Any],
    detail: Dict[str, Any],
    view: View,
) -> Dict[str, Any]:
    """Convert ci_graph_query Tool Asset output to graph visualization payload.

    Args:
        data: Tool output with 'rows' key
        detail: CI detail information
        view: Graph view type

    Returns:
        Graph payload with nodes, edges, and metadata
    """
    rows = data.get("rows", [])

    # Build nodes set
    nodes_set = {detail["ci_id"]}  # Start with source CI
    edges = []
    node_info_map = {detail["ci_id"]: detail}

    for row in rows:
        from_id = row.get("from_ci_id")
        to_id = row.get("to_ci_id")

        if from_id:
            nodes_set.add(from_id)
            if from_id not in node_info_map:
                node_info_map[from_id] = {
                    "ci_id": from_id,
                    "ci_code": row.get("from_ci_code", ""),
                    "ci_name": row.get("from_ci_name", ""),
                }

        if to_id:
            nodes_set.add(to_id)
            if to_id not in node_info_map:
                node_info_map[to_id] = {
                    "ci_id": to_id,
                    "ci_code": row.get("to_ci_code", ""),
                    "ci_name": row.get("to_ci_name", ""),
                }

        if from_id and to_id:
            edges.append({
                "from": from_id,
                "to": to_id,
                "type": row.get("relationship_type", ""),
                "strength": row.get("strength", 1.0),
            })

    # Build nodes
    nodes = [
        {
            "id": node_id,
            "label": node_info_map.get(node_id, {}).get("ci_name", node_id),
        }
        for node_id in nodes_set
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "depth": 1,
            "view": view.value if hasattr(view, "value") else str(view),
        },
        "ids": [detail.get("ci_code", "")],
        "truncated": len(rows) >= 500,  # Assume truncated if at limit
    }
