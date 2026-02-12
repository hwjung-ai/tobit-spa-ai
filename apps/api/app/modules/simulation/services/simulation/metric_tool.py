"""
Metric Data Tool - Tool-based data access for simulation

Uses the Tool system (dynamic_tool) to access metric timeseries data
instead of direct database access.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.logging import get_logger
from sqlmodel import Session

from app.modules.asset_registry.loader import load_source_asset
from app.modules.ops.services.ci.tools.base import ToolContext, ToolResult

logger = get_logger(__name__)


# Tool name for metric data access
METRIC_DATA_TOOL_NAME = "sim_metric_timeseries_query"
TOOL_SOURCE_NAME = "default_postgres"


async def load_metric_kpis_via_tool(
    *,
    tenant_id: str,
    service: str,
    hours_back: int = 168,
    metric_names: list[str] | None = None,
) -> dict[str, float]:
    """
    Load baseline KPIs using Tool-based data access.

    This uses the Tool Asset system instead of direct DB access.

    Args:
        tenant_id: Tenant identifier
        service: Service name
        hours_back: Hours of historical data to use
        metric_names: List of metric names to load

    Returns:
        Dictionary with baseline KPIs
    """
    if metric_names is None:
        metric_names = ["latency_ms", "throughput_rps", "error_rate_pct", "cost_usd_hour"]

    # Try to load tool asset
    tool_asset = await _get_or_create_metric_tool_asset()

    if not tool_asset:
        logger.warning("Metric tool asset not available, using fallback")
        return _get_fallback_baseline()

    # Execute tool to get metric data
    from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

    tool = DynamicTool(tool_asset)

    # Create tool context
    context = ToolContext(
        tenant_id=tenant_id,
        user_id="simulation_system",
        request_id=f"sim_{service}_{datetime.utcnow().isoformat()}",
    )

    # Prepare input parameters
    since = datetime.utcnow() - timedelta(hours=hours_back)

    input_data = {
        "tenant_id": tenant_id,
        "service": service,
        "metric_names": metric_names,
        "since": since.isoformat(),
        "aggregation": "mean",
    }

    try:
        result = await tool.execute(context, input_data)

        if result.is_success():
            metric_data = result.data
            return _extract_baseline_from_metric_data(metric_data)
        else:
            logger.warning(f"Tool execution failed: {result.error}")
            return _get_fallback_baseline()

    except Exception as e:
        logger.error(f"Error loading metrics via tool: {e}")
        return _get_fallback_baseline()


async def _get_or_create_metric_tool_asset() -> dict[str, Any] | None:
    """
    Get or create the metric data Tool Asset.

    Returns tool asset dict or None if not available.
    """
    # Try to load from asset registry
    catalog = await load_source_asset(TOOL_SOURCE_NAME)

    if not catalog:
        return None

    # Look for metric data tool
    tools = catalog.get("tools", [])

    for tool in tools:
        if tool.get("name") == METRIC_DATA_TOOL_NAME:
            return tool

    # Tool not found, could create dynamically here
    # For now, return None to trigger fallback
    return None


def _extract_baseline_from_metric_data(metric_data: dict[str, Any]) -> dict[str, float]:
    """
    Extract baseline KPIs from metric data returned by tool.

    Args:
        metric_data: Tool output with metric timeseries data

    Returns:
        Baseline KPIs dictionary
    """
    baseline = {}

    # Expected structure: {metric_name: [aggregated_value]}
    for metric_name in ["latency_ms", "throughput_rps", "error_rate_pct", "cost_usd_hour"]:
        value = metric_data.get(metric_name)

        if value is not None:
            if isinstance(value, (int, float)):
                baseline[metric_name] = float(value)
            elif isinstance(value, list) and len(value) > 0:
                # Average if list of values
                baseline[metric_name] = sum(float(v) for v in value) / len(value)
            else:
                baseline[metric_name] = _get_fallback_baseline().get(metric_name, 0.0)
        else:
            baseline[metric_name] = _get_fallback_baseline().get(metric_name, 0.0)

    return baseline


def _get_fallback_baseline() -> dict[str, float]:
    """Get fallback baseline values when metric data unavailable."""
    return {
        "latency_ms": 45.0,
        "throughput_rps": 100.0,
        "error_rate_pct": 0.5,
        "cost_usd_hour": 10.0,
    }


async def get_available_services_via_tool(tenant_id: str) -> list[str]:
    """
    Get list of services with metric data using Tool-based access.

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of service names
    """
    tool_asset = await _get_or_create_metric_tool_asset()

    if not tool_asset:
        return []

    from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

    tool = DynamicTool(tool_asset)

    context = ToolContext(
        tenant_id=tenant_id,
        user_id="simulation_system",
        request_id=f"sim_services_{datetime.utcnow().isoformat()}",
    )

    input_data = {
        "tenant_id": tenant_id,
        "hours_back": 24,
        "distinct_services_only": True,
    }

    try:
        result = await tool.execute(context, input_data)

        if result.is_success():
            services = result.data.get("services", [])
            return services if isinstance(services, list) else []
        return []

    except Exception as e:
        logger.error(f"Error loading services via tool: {e}")
        return []
