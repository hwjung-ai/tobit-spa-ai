"""
Data Source Executors for OPS Orchestration
Provides real data connections for Config, Metric, and History modes.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from pydantic import BaseModel
from schemas import AnswerBlock, MarkdownBlock, TableBlock

from app.modules.ops.services.orchestration.tools.base import (
    ToolContext,
    get_tool_registry,
)
from app.modules.ops.services.orchestration.tools.executor import get_tool_executor
from app.modules.ops.services.orchestration.tools.registry_init import initialize_tools

logger = logging.getLogger(__name__)


def _extract_explicit_tool_name(kwargs: dict) -> str | None:
    for key in ("tool_name", "selected_tool", "selected_tool_name", "tool_asset_name"):
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    tool_selection = kwargs.get("tool_selection")
    if isinstance(tool_selection, dict):
        name = tool_selection.get("name") or tool_selection.get("tool_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _resolve_tool_name(
    explicit_tool_name: str | None,
    capability_hints: list[str],
    type_hints: list[str] | None = None,
) -> str | None:
    """Resolve tool name from explicit selection or registry capabilities."""
    initialize_tools()
    registry = get_tool_registry()

    if explicit_tool_name and registry.is_registered(explicit_tool_name):
        return explicit_tool_name

    for capability in capability_hints:
        candidate = registry.find_tool_by_capability(capability)
        if candidate:
            return getattr(candidate, "tool_name", None)

    for tool_type in type_hints or []:
        matches = registry.find_tools_by_type(tool_type)
        if matches:
            return getattr(matches[0], "tool_name", None)

    return None


def _execute_tool(
    tool_name: str,
    params: dict,
    tenant_id: Optional[str],
    user_id: str = "system",
) -> dict:
    """Execute resolved tool through orchestration tool executor."""
    context = ToolContext(
        tenant_id=tenant_id or "default",
        user_id=user_id,
        metadata={"source": "ops_config_executor"},
    )
    result = get_tool_executor().execute(tool_name, context, params)
    return {
        "success": bool(result.success),
        "data": result.data,
        "error": result.error,
    }


class ExecutorResult(BaseModel):
    """Result from an executor."""
    blocks: List[AnswerBlock] = []
    used_tools: List[str] = []
    error: Optional[str] = None
    execution_time_ms: float = 0.0


# ============================================================================
# Config Executor - CI Lookup and Configuration Data
# ============================================================================

def run_config(
    question: str,
    tenant_id: Optional[str] = None,
    session=None,
    **kwargs
) -> ExecutorResult:
    """
    Execute Config mode - lookup CI configuration data.

    Uses Tool Assets to query CI information from configured data sources.
    """
    start_time = time.time()
    used_tools = []
    blocks = []

    try:
        tool_name = _resolve_tool_name(
            explicit_tool_name=_extract_explicit_tool_name(kwargs),
            capability_hints=["ci_lookup", "ci_search", "config_lookup"],
            type_hints=["database_query", "api_query"],
        )
        if not tool_name:
            raise ValueError("No configured tool found for config mode")

        # Execute the tool
        result = _execute_tool(
            tool_name=tool_name,
            params={"query": question, "tenant_id": tenant_id},
            tenant_id=tenant_id,
        )

        if result.get("success"):
            used_tools.append(tool_name)
            data = result.get("data", [])

            if data:
                # Build table block with CI data
                if isinstance(data, list):
                    blocks.append(TableBlock(
                        type="table",
                        title="CI Configuration",
                        columns=["CI ID", "Name", "Type", "Status", "Environment"],
                        rows=[
                            [
                                item.get("ci_id", ""),
                                item.get("ci_name", ""),
                                item.get("ci_type", ""),
                                item.get("status", ""),
                                item.get("environment", ""),
                            ]
                            for item in data[:50]  # Limit to 50 rows
                        ],
                    ))
                else:
                    blocks.append(MarkdownBlock(
                        type="markdown",
                        title="CI Details",
                        content=f"```json\n{data}\n```",
                    ))
            else:
                blocks.append(MarkdownBlock(
                    type="markdown",
                    title="CI Configuration",
                    content="No CI data found matching the query.",
                ))
        else:
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Config executor tool error: {error_msg}")
            blocks.append(MarkdownBlock(
                type="markdown",
                title="CI Configuration",
                content=f"⚠️ Unable to retrieve CI data: {error_msg}\n\nPlease check data source configuration.",
            ))

    except Exception as e:
        logger.exception(f"Config executor error: {e}")
        blocks.append(MarkdownBlock(
            type="markdown",
            title="CI Configuration Error",
            content=f"❌ Error retrieving CI data: {str(e)}",
        ))

    execution_time = (time.time() - start_time) * 1000
    return ExecutorResult(
        blocks=blocks,
        used_tools=used_tools,
        execution_time_ms=execution_time,
    )


def _get_config_fallback(question: str) -> MarkdownBlock:
    """Fallback for config mode when data source is not available."""
    return MarkdownBlock(
        type="markdown",
        title="CI Configuration",
        content="""### Data Source Not Connected

The CI Configuration data source is not currently connected.

**To connect:**
1. Configure the database connection in Admin > Catalog
2. Ensure the CI lookup tool asset is published
3. Verify tenant permissions

**Expected Data:**
- CI ID, Name, Type
- Status, Environment
- Configuration attributes
""",
    )


# ============================================================================
# Metric Executor - Performance and Monitoring Metrics
# ============================================================================

def run_metric(
    question: str,
    tenant_id: Optional[str] = None,
    session=None,
    **kwargs
) -> ExecutorResult:
    """
    Execute Metric mode - retrieve performance and monitoring metrics.

    Supports:
    - Time series metrics (CPU, Memory, Disk, Network)
    - Aggregated statistics (avg, max, min, p95, p99)
    - Service-level metrics (latency, throughput, error rate)
    """
    start_time = time.time()
    used_tools = []
    blocks = []

    try:
        from app.modules.sim.services.metric_loader import load_baseline_kpis

        tool_name = _resolve_tool_name(
            explicit_tool_name=_extract_explicit_tool_name(kwargs),
            capability_hints=["metric_query", "metric_aggregate"],
            type_hints=["database_query", "api_query"],
        )
        if not tool_name:
            raise ValueError("No configured tool found for metric mode")

        result = _execute_tool(
            tool_name=tool_name,
            params={
                "query": question,
                "tenant_id": tenant_id,
                "time_range": kwargs.get("time_range", "last_24h"),
            },
            tenant_id=tenant_id,
        )

        if result.get("success"):
            used_tools.append(tool_name)
            data = result.get("data", {})

            if data:
                # Build metric visualization block
                metrics = data.get("metrics", [])
                if metrics:
                    # Create summary table
                    blocks.append(TableBlock(
                        type="table",
                        title="Performance Metrics",
                        columns=["Service", "Metric", "Value", "Unit", "Timestamp"],
                        rows=[
                            [
                                m.get("service", ""),
                                m.get("metric_name", ""),
                                m.get("value", ""),
                                m.get("unit", ""),
                                m.get("timestamp", ""),
                            ]
                            for m in metrics[:100]
                        ],
                    ))
                else:
                    blocks.append(MarkdownBlock(
                        type="markdown",
                        title="Performance Metrics",
                        content="No metrics data available for the specified time range.",
                    ))
            else:
                # Try direct metric loader
                kpis = load_baseline_kpis(question)
                if kpis:
                    blocks.append(TableBlock(
                        type="table",
                        title="Baseline KPIs",
                        columns=["KPI", "Value", "Unit"],
                        rows=[
                            [kpi.get("name", ""), kpi.get("value", ""), kpi.get("unit", "")]
                            for kpi in kpis
                        ],
                    ))
                else:
                    blocks.append(_get_metric_fallback(question))
        else:
            blocks.append(_get_metric_fallback(question))

    except Exception as e:
        logger.exception(f"Metric executor error: {e}")
        blocks.append(MarkdownBlock(
            type="markdown",
            title="Metrics Error",
            content=f"❌ Error retrieving metrics: {str(e)}",
        ))

    execution_time = (time.time() - start_time) * 1000
    return ExecutorResult(
        blocks=blocks,
        used_tools=used_tools,
        execution_time_ms=execution_time,
    )


def _get_metric_fallback(question: str) -> MarkdownBlock:
    """Fallback for metric mode when data source is not available."""
    return MarkdownBlock(
        type="markdown",
        title="Performance Metrics",
        content="""### Metrics Data Source Not Connected

The metrics data source is not currently connected.

**To connect:**
1. Run database migration: `alembic upgrade head`
2. Seed sample data: `python scripts/seed_metric_timeseries.py`
3. Configure the metric query tool asset

**Supported Metrics:**
- CPU, Memory, Disk, Network usage
- Latency (p50, p95, p99)
- Throughput (requests per second)
- Error rate percentage
""",
    )


# ============================================================================
# History Executor - Event and Change History
# ============================================================================

def run_hist(
    question: str,
    tenant_id: Optional[str] = None,
    session=None,
    **kwargs
) -> ExecutorResult:
    """
    Execute History mode - retrieve event and change history.

    Supports:
    - CI change history
    - Incident history
    - Deployment history
    - Alert history
    """
    start_time = time.time()
    used_tools = []
    blocks = []

    try:
        tool_name = _resolve_tool_name(
            explicit_tool_name=_extract_explicit_tool_name(kwargs),
            capability_hints=["history", "history_search", "event_search"],
            type_hints=["database_query", "api_query"],
        )
        if not tool_name:
            raise ValueError("No configured tool found for history mode")

        result = _execute_tool(
            tool_name=tool_name,
            params={
                "query": question,
                "tenant_id": tenant_id,
                "time_range": kwargs.get("time_range", "last_7d"),
                "limit": kwargs.get("limit", 100),
            },
            tenant_id=tenant_id,
        )

        if result.get("success"):
            used_tools.append(tool_name)
            data = result.get("data", [])

            if data:
                # Build history table
                blocks.append(TableBlock(
                    type="table",
                    title="Event History",
                    columns=["Timestamp", "Event Type", "Source", "Description", "Status"],
                    rows=[
                        [
                            item.get("timestamp", ""),
                            item.get("event_type", ""),
                            item.get("source", ""),
                            item.get("description", "")[:100],  # Truncate long descriptions
                            item.get("status", ""),
                        ]
                        for item in data[:100]
                    ],
                ))
            else:
                blocks.append(MarkdownBlock(
                    type="markdown",
                    title="Event History",
                    content="No events found for the specified time range.",
                ))
        else:
            blocks.append(_get_hist_fallback(question))

    except Exception as e:
        logger.exception(f"History executor error: {e}")
        blocks.append(MarkdownBlock(
            type="markdown",
            title="History Error",
            content=f"❌ Error retrieving history: {str(e)}",
        ))

    execution_time = (time.time() - start_time) * 1000
    return ExecutorResult(
        blocks=blocks,
        used_tools=used_tools,
        execution_time_ms=execution_time,
    )


def _get_hist_fallback(question: str) -> MarkdownBlock:
    """Fallback for history mode when data source is not available."""
    return MarkdownBlock(
        type="markdown",
        title="Event History",
        content="""### History Data Source Not Connected

The event history data source is not currently connected.

**To connect:**
1. Configure the event database connection
2. Ensure the history tool assets are published
3. Verify event collection is running

**Supported Events:**
- CI changes (create, update, delete)
- Incidents (open, close, escalate)
- Deployments (start, complete, rollback)
- Alerts (trigger, acknowledge, resolve)
""",
    )


# ============================================================================
# Graph Executor - CI Relationships and Dependencies
# ============================================================================

def run_graph(
    question: str,
    tenant_id: Optional[str] = None,
    session=None,
    **kwargs
) -> ExecutorResult:
    """
    Execute Graph mode - retrieve CI relationships and dependencies.

    Uses Neo4j or graph database to traverse CI relationships.
    """
    start_time = time.time()
    used_tools = []
    blocks = []

    try:
        tool_name = _resolve_tool_name(
            explicit_tool_name=_extract_explicit_tool_name(kwargs),
            capability_hints=["graph_expand", "graph_query", "graph_topology"],
            type_hints=["graph_query"],
        )
        if not tool_name:
            raise ValueError("No configured tool found for graph mode")

        result = _execute_tool(
            tool_name=tool_name,
            params={
                "query": question,
                "tenant_id": tenant_id,
                "depth": kwargs.get("depth", 2),
                "max_nodes": kwargs.get("max_nodes", 100),
            },
            tenant_id=tenant_id,
        )

        if result.get("success"):
            used_tools.append(tool_name)
            data = result.get("data", {})

            nodes = data.get("nodes", [])
            edges = data.get("edges", [])

            if nodes:
                # Build relationship summary
                blocks.append(MarkdownBlock(
                    type="markdown",
                    title="CI Relationships",
                    content=f"""### Relationship Graph

**Nodes:** {len(nodes)}
**Edges:** {len(edges)}

#### Key Relationships:
{_format_relationships(edges[:20])}
""",
                ))

                # Add node table
                blocks.append(TableBlock(
                    type="table",
                    title="Related CIs",
                    columns=["CI ID", "Name", "Type", "Relationships"],
                    rows=[
                        [
                            node.get("ci_id", ""),
                            node.get("ci_name", ""),
                            node.get("ci_type", ""),
                            str(node.get("relationship_count", 0)),
                        ]
                        for node in nodes[:50]
                    ],
                ))
            else:
                blocks.append(MarkdownBlock(
                    type="markdown",
                    title="CI Relationships",
                    content="No relationships found for the specified CI.",
                ))
        else:
            blocks.append(_get_graph_fallback(question))

    except Exception as e:
        logger.exception(f"Graph executor error: {e}")
        blocks.append(MarkdownBlock(
            type="markdown",
            title="Graph Error",
            content=f"❌ Error retrieving relationships: {str(e)}",
        ))

    execution_time = (time.time() - start_time) * 1000
    return ExecutorResult(
        blocks=blocks,
        used_tools=used_tools,
        execution_time_ms=execution_time,
    )


def _get_graph_fallback(question: str) -> MarkdownBlock:
    """Fallback for graph mode when data source is not available."""
    return MarkdownBlock(
        type="markdown",
        title="CI Relationships",
        content="""### Graph Data Source Not Connected

The CI relationship graph database is not currently connected.

**To connect:**
1. Configure Neo4j connection in settings
2. Ensure the graph tool assets are published
3. Run CI relationship sync job

**Supported Queries:**
- Dependencies (upstream/downstream)
- Impact analysis
- Composition relationships
- Network topology
""",
    )


def _format_relationships(edges: List[Dict]) -> str:
    """Format relationship edges for display."""
    if not edges:
        return "No relationships found."

    lines = []
    for edge in edges:
        source = edge.get("source", "?")
        target = edge.get("target", "?")
        rel_type = edge.get("relationship_type", "related_to")
        lines.append(f"- `{source}` → **{rel_type}** → `{target}`")

    return "\n".join(lines)
