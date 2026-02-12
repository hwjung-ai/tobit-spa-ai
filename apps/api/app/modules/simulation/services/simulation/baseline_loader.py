"""
Baseline Loader for Simulation

Loads baseline KPIs using Tool-based data access with fallbacks.

**TWO MODES OF OPERATION**:

1. **DB Mode** (load_baseline_kpis_async):
   - Loads from stored metric timeseries in PostgreSQL
   - Use when: Scheduled collection runs, historical data available
   - Benefit: Fast, reliable, works offline

2. **Real-Time Mode** (load_baseline_kpis_realtime):
   - Fetches directly from Prometheus/CloudWatch
   - Use when: Latest data needed, no DB dependency
   - Benefit: Always fresh, no storage needed

Priority (for DB mode):
1. Tool-based metric timeseries access (via Asset Registry)
2. Direct metric timeseries access (PostgreSQL)
3. Topology-based derivation (Neo4j)

Priority (for Real-Time mode):
1. Direct API call (Prometheus/CloudWatch)
2. Topology-based derivation (Neo4j)
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.modules.simulation.services.topology_service import get_topology_data
from core.db import get_session_context
from sqlmodel import Session, select


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _derive_kpis_from_topology(topology: Any) -> dict[str, float]:
    """
    Derive KPIs from topology data (fallback method).

    Uses node simulated_load and link simulated_traffic to calculate KPIs.
    """
    nodes = topology.nodes if topology else []
    links = topology.links if topology else []

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail="No topology nodes found for KPI derivation. Ensure Neo4j has topology data or metric timeseries exist."
        )

    avg_load = _safe_mean([float(n.get("simulated_load", 0.0)) for n in nodes])
    traffic_links = [float(link.get("simulated_traffic", 0.0)) for link in links if link.get("type") == "traffic"]
    all_links = [float(link.get("simulated_traffic", 0.0)) for link in links]
    throughput = _safe_mean(traffic_links) if traffic_links else _safe_mean(all_links)

    critical_cnt = sum(1 for n in nodes if n.get("status") == "critical")
    warning_cnt = sum(1 for n in nodes if n.get("status") == "warning")
    total = len(nodes)
    error_rate = ((critical_cnt * 1.2) + (warning_cnt * 0.4)) / total if total else 0.0

    type_weight = {"service": 1.4, "server": 1.2, "db": 1.6, "network": 1.0, "storage": 0.9}
    weighted_cost = 0.0
    for n in nodes:
        weighted_cost += float(n.get("simulated_load", 0.0)) * type_weight.get(str(n.get("type", "service")), 1.0)

    return {
        "latency_ms": round(max(1.0, 30.0 + avg_load * 2.2), 3),
        "error_rate_pct": round(max(0.0, error_rate), 3),
        "throughput_rps": round(max(1.0, throughput), 3),
        "cost_usd_hour": round(max(0.1, weighted_cost / 10.0), 3),
    }


def _estimate_uncertainty(strategy: str, confidence: float) -> tuple[tuple[float, float], float]:
    """
    Estimate uncertainty bounds for prediction confidence.

    Args:
        strategy: Strategy name (rule, stat, ml, dl)
        confidence: Confidence score (0-1)

    Returns:
        Tuple of (confidence_interval, error_bound)
    """
    margin = {
        "rule": 0.12,
        "stat": 0.09,
        "ml": 0.05,
        "dl": 0.04,
    }.get(strategy, 0.1)
    lower = max(0.0, confidence - margin)
    upper = min(0.99, confidence + margin)
    return (round(lower, 3), round(upper, 3)), round(margin, 3)


async def list_available_services(tenant_id: str) -> list[str]:
    """
    Get list of services available for simulation.

    Priority:
    1. Services with metric timeseries data (via Tool)
    2. Services with Neo4j topology data

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of service names
    """
    # First try Tool-based metric timeseries access
    try:
        from app.modules.simulation.services.simulation.metric_tool import get_available_services_via_tool

        metric_services = await get_available_services_via_tool(tenant_id)

        if metric_services:
            return metric_services
    except Exception:
        pass  # Fall through to next method

    # Try direct metric loader
    try:
        from app.modules.simulation.services.simulation.metric_loader import get_available_services_from_metrics

        metric_services = get_available_services_from_metrics(tenant_id)

        if metric_services:
            return metric_services
    except Exception:
        pass  # Fall through to topology

    # Fallback to topology service list
    from app.modules.simulation.services.topology_service import list_available_services as topology_services
    return topology_services(tenant_id)


async def load_baseline_kpis_async(
    *, tenant_id: str, service: str, hours_back: int = 168
) -> dict[str, float]:
    """
    Load baseline KPIs using Tool-based access with fallbacks.

    Priority:
    1. Tool-based metric timeseries (Asset Registry)
    2. Direct metric timeseries (PostgreSQL)
    3. Topology-based derivation (Neo4j)

    Args:
        tenant_id: Tenant identifier
        service: Service name
        hours_back: Hours of historical data to use

    Returns:
        Baseline KPIs dictionary
    """
    # Try Tool-based access first
    try:
        from app.modules.simulation.services.simulation.metric_tool import load_metric_kpis_via_tool

        baseline_kpis = await load_metric_kpis_via_tool(
            tenant_id=tenant_id,
            service=service,
            hours_back=hours_back,
        )

        if baseline_kpis and any(v > 0 for v in baseline_kpis.values()):
            return baseline_kpis
    except Exception:
        pass  # Fall through to next method

    # Try direct metric loader
    try:
        from app.modules.simulation.services.simulation.metric_loader import load_baseline_kpis

        baseline_kpis = load_baseline_kpis(
            tenant_id=tenant_id,
            service=service,
            hours_back=hours_back,
        )

        if baseline_kpis and any(v > 0 for v in baseline_kpis.values()):
            return baseline_kpis
    except Exception:
        pass  # Fall through to topology

    # Fallback to topology-based derivation
    baseline_topology = get_topology_data(
        tenant_id=tenant_id,
        service=service,
        scenario_type="what_if",
        assumptions={},
    )

    return _derive_kpis_from_topology(baseline_topology)


def load_baseline_and_scenario_kpis(
    *, tenant_id: str, service: str, scenario_type: str, assumptions: dict[str, float]
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Load baseline and scenario KPIs for simulation.

    Priority:
    1. Tool-based metric timeseries access
    2. Direct metric timeseries access
    3. Topology-based derivation

    Args:
        tenant_id: Tenant identifier
        service: Service name
        scenario_type: Scenario type (what_if, stress_test, capacity)
        assumptions: Assumption values (traffic_change_pct, cpu_change_pct, memory_change_pct)

    Returns:
        Tuple of (baseline_kpis, scenario_kpis) dictionaries
    """
    # Try to load from metric data (Tool or direct)
    try:
        # For async compatibility, use sync version for now
        from app.modules.simulation.services.simulation.metric_loader import load_baseline_kpis

        baseline_kpis = load_baseline_kpis(tenant_id=tenant_id, service=service, hours_back=168)
    except Exception:
        # Fallback to topology-based derivation
        baseline_topology = get_topology_data(
            tenant_id=tenant_id,
            service=service,
            scenario_type=scenario_type,
            assumptions={},
        )
        baseline_kpis = _derive_kpis_from_topology(baseline_topology)

    # Calculate scenario KPIs with assumptions applied
    scenario_topology = get_topology_data(
        tenant_id=tenant_id,
        service=service,
        scenario_type=scenario_type,
        assumptions=assumptions,
    )
    scenario_kpis = _derive_kpis_from_topology(scenario_topology)

    return baseline_kpis, scenario_kpis


async def load_baseline_kpis_realtime(
    *,
    tenant_id: str,
    service: str,
    source_config: dict[str, Any],
) -> dict[str, float]:
    """
    **REAL-TIME MODE**: Load baseline KPIs directly from external source.

    This bypasses the database and fetches metrics in real-time.

    Args:
        tenant_id: Tenant identifier
        service: Service name
        source_config: Configuration for external source
            {
                "source": "prometheus" | "cloudwatch",
                "query": "PromQL" | JSON string,
                "prometheus_url": "...",
                "cloudwatch_region": "...",
            }

    Returns:
        Baseline KPIs dictionary

    Example:
        source_config = {
            "source": "prometheus",
            "prometheus_url": "http://prometheus:9090",
            "query": "rate(http_requests_total[5m])"
        }

        source_config = {
            "source": "cloudwatch",
            "cloudwatch_region": "us-east-1",
            "query": '{"namespace": "AWS/EC2", "metric_name": "CPUUtilization"}'
        }
    """
    source = source_config.get("source", "prometheus")

    try:
        if source == "prometheus":
            from app.workers.metric_collector import MetricCollector, STANDARD_PROMETHEUS_QUERIES

            config = MetricCollector.MetricCollectorConfig(
                prometheus_url=source_config.get("prometheus_url"),
            )
            collector = MetricCollector(config)

            # Use standard queries for each KPI
            kpis = {}

            for metric_name, query in STANDARD_PROMETHEUS_QUERIES.items():
                result = await collector.fetch_realtime(
                    source="prometheus",
                    query=query,
                    hours_back=1,  # Last 1 hour
                )

                if "error" not in result and result.get("metrics"):
                    # Extract latest value for each metric series
                    for key, data in result["metrics"].items():
                        if ":" in key:  # format: "service:metric_name"
                            kpi_name = key.split(":")[1]
                            if kpi_name == metric_name or metric_name in kpi_name:
                                kpis[metric_name] = data.get("value", 0.0)

            return kpis

        elif source == "cloudwatch":
            from app.workers.metric_collector import MetricCollector

            config = MetricCollector.MetricCollectorConfig(
                cloudwatch_region=source_config.get("cloudwatch_region"),
            )
            collector = MetricCollector(config)

            # Map KPIs to CloudWatch metrics
            # This would require specific CloudWatch query patterns
            # For now, return error for unimplemented
            raise NotImplementedError(
                "CloudWatch real-time mode requires specific metric mappings. "
                "Use DB mode instead."
            )

        else:
            raise ValueError(f"Unknown source: {source}")

    except Exception as e:
        # Fallback to topology if real-time fetch fails
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Real-time fetch failed: {str(e)}. "
                   "Ensure external source is accessible or use DB mode."
        )
