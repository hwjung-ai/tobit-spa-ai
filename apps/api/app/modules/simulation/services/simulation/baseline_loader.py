from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.modules.simulation.services.topology_service import get_topology_data


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _derive_kpis(topology: Any) -> dict[str, float]:
    nodes = topology.nodes if topology else []
    links = topology.links if topology else []
    if not nodes:
        raise HTTPException(status_code=404, detail="No nodes found for simulation baseline")

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


def load_baseline_and_scenario_kpis(
    *, tenant_id: str, service: str, scenario_type: str, assumptions: dict[str, float]
) -> tuple[dict[str, float], dict[str, float]]:
    baseline_topology = get_topology_data(
        tenant_id=tenant_id,
        service=service,
        scenario_type=scenario_type,
        assumptions={},
    )
    scenario_topology = get_topology_data(
        tenant_id=tenant_id,
        service=service,
        scenario_type=scenario_type,
        assumptions=assumptions,
    )
    return _derive_kpis(baseline_topology), _derive_kpis(scenario_topology)
