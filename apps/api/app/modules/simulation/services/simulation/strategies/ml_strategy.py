from __future__ import annotations

from typing import Any

from app.modules.simulation.services.simulation.model_registry import get_model_metadata
from app.modules.simulation.services.simulation.schemas import KpiResult, SimulationPlan


class MLPredictiveStrategy:
    name = "ml"

    def run(self, *, plan: SimulationPlan, baseline_data: dict[str, float], tenant_id: str) -> tuple[list[KpiResult], float, dict[str, Any]]:
        traffic = plan.assumptions.get("traffic_change_pct", 0.0)
        cpu = plan.assumptions.get("cpu_change_pct", 0.0)
        memory = plan.assumptions.get("memory_change_pct", 0.0)

        # Deterministic surrogate for a trained model.
        z = 0.04 * traffic + 0.03 * cpu + 0.015 * memory + 0.0006 * traffic * cpu
        latency_multiplier = max(0.5, min(2.5, 1.0 + z))

        latency = baseline_data["latency_ms"] * latency_multiplier
        throughput = baseline_data["throughput_rps"] * max(0.2, (1.0 + 0.005 * traffic - 0.002 * cpu))
        error_rate = baseline_data["error_rate_pct"] + max(0.0, z * 0.55)
        cost = baseline_data["cost_usd_hour"] * (1.0 + max(0.0, traffic) / 100.0 * 0.22)

        kpis = [
            KpiResult(kpi="latency_ms", baseline=baseline_data["latency_ms"], simulated=round(latency, 2), unit="ms"),
            KpiResult(kpi="error_rate_pct", baseline=baseline_data["error_rate_pct"], simulated=round(error_rate, 3), unit="%"),
            KpiResult(kpi="throughput_rps", baseline=baseline_data["throughput_rps"], simulated=round(throughput, 2), unit="rps"),
            KpiResult(kpi="cost_usd_hour", baseline=baseline_data["cost_usd_hour"], simulated=round(cost, 2), unit="USD/h"),
        ]
        model_info = get_model_metadata("ml")
        model_info["strategy"] = "ml"
        model_info["tenant_id"] = tenant_id
        return kpis, 0.84, model_info
