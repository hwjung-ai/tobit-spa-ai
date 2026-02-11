from __future__ import annotations

from typing import Any

from app.modules.simulation.services.simulation.schemas import KpiResult, SimulationPlan


class StatisticalStrategy:
    name = "stat"

    def run(self, *, plan: SimulationPlan, baseline_data: dict[str, float], tenant_id: str) -> tuple[list[KpiResult], float, dict[str, Any]]:
        traffic = plan.assumptions.get("traffic_change_pct", 0.0)
        cpu = plan.assumptions.get("cpu_change_pct", 0.0)
        memory = plan.assumptions.get("memory_change_pct", 0.0)

        ema_component = (traffic * 0.35) + (cpu * 0.25) + (memory * 0.15)
        latency = baseline_data["latency_ms"] * (1.0 + ema_component / 100.0 * 0.8)
        throughput = baseline_data["throughput_rps"] * (1.0 + (traffic - 0.5 * cpu) / 100.0 * 0.7)
        error_rate = baseline_data["error_rate_pct"] + max(0.0, ema_component) * 0.012
        cost = baseline_data["cost_usd_hour"] * (1.0 + max(0.0, traffic) / 100.0 * 0.18)

        kpis = [
            KpiResult(kpi="latency_ms", baseline=baseline_data["latency_ms"], simulated=round(latency, 2), unit="ms"),
            KpiResult(kpi="error_rate_pct", baseline=baseline_data["error_rate_pct"], simulated=round(error_rate, 3), unit="%"),
            KpiResult(kpi="throughput_rps", baseline=baseline_data["throughput_rps"], simulated=round(throughput, 2), unit="rps"),
            KpiResult(kpi="cost_usd_hour", baseline=baseline_data["cost_usd_hour"], simulated=round(cost, 2), unit="USD/h"),
        ]
        model_info = {
            "strategy": "stat",
            "method": "ema+linear-regression-lite",
            "version": "stat-v1",
            "confidence_interval": "p50+-8%",
            "tenant_id": tenant_id,
        }
        return kpis, 0.79, model_info
