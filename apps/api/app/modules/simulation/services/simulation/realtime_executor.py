from __future__ import annotations

from typing import Any

from app.modules.simulation.schemas import SimulationRealtimeRunRequest
from app.modules.simulation.services.simulation.baseline_loader import (
    load_baseline_kpis_realtime,
)


async def run_realtime_simulation(
    *,
    payload: SimulationRealtimeRunRequest,
    tenant_id: str,
    requested_by: str,
) -> dict[str, Any]:
    baseline_kpis = await load_baseline_kpis_realtime(
        tenant_id=tenant_id,
        service=payload.service,
        source_config=payload.source_config.model_dump(exclude_none=True),
    )

    scenario_kpis: dict[str, float] = {}
    for kpi, value in baseline_kpis.items():
        factor = 1.0
        if "latency" in kpi:
            traffic_change = payload.assumptions.get("traffic_change_pct", 0) / 100
            cpu_change = payload.assumptions.get("cpu_change_pct", 0) / 100
            factor = 1 + (traffic_change * 0.3) + (cpu_change * 0.2)
        elif "throughput" in kpi:
            traffic_change = payload.assumptions.get("traffic_change_pct", 0) / 100
            factor = 1 + traffic_change
        elif "error" in kpi:
            traffic_change = payload.assumptions.get("traffic_change_pct", 0) / 100
            factor = 1 + (traffic_change * 0.5) + (traffic_change**2 * 0.01)
        elif "cost" in kpi:
            cpu_change = payload.assumptions.get("cpu_change_pct", 0) / 100
            memory_change = payload.assumptions.get("memory_change_pct", 0) / 100
            factor = 1 + (cpu_change * 0.3) + (memory_change * 0.2)
        scenario_kpis[kpi] = round(value * factor, 3)

    source = payload.source_config.source
    return {
        "simulation": {
            "scenario_id": f"realtime-{payload.scenario_type}",
            "strategy": payload.strategy,
            "scenario_type": payload.scenario_type,
            "question": payload.question,
            "horizon": payload.horizon,
            "assumptions": payload.assumptions,
            "kpis": [
                {"kpi": k, "baseline": round(baseline_kpis[k], 3), "simulated": v, "unit": "unknown"}
                for k, v in scenario_kpis.items()
            ],
            "confidence": 0.85,
            "confidence_interval": (0.80, 0.90),
            "error_bound": 0.10,
            "warnings": [
                "Real-time mode: Using live metrics without historical validation",
                "Lower confidence due to lack of training data",
            ],
            "explanation": f"Simulation computed with real-time metrics from {source}",
            "recommended_actions": [],
            "model_info": {},
        },
        "summary": f"Real-time simulation using {source} metrics",
        "plan": {"scenario_type": payload.scenario_type},
        "data_source": source,
        "data_transparency": {
            "mode": "realtime",
            "source": source,
            "metrics_fresh": True,
            "using_cached_data": False,
        },
        "tenant_id": tenant_id,
        "requested_by": requested_by,
    }
