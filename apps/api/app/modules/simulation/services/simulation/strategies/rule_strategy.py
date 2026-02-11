from __future__ import annotations

from typing import Any

from app.modules.simulation.services.simulation.rule_registry import get_published_rule
from app.modules.simulation.services.simulation.schemas import KpiResult, SimulationPlan


class RuleBasedStrategy:
    name = "rule"

    def run(self, *, plan: SimulationPlan, baseline_data: dict[str, float], tenant_id: str) -> tuple[list[KpiResult], float, dict[str, Any]]:
        traffic = plan.assumptions.get("traffic_change_pct", 0.0)
        cpu = plan.assumptions.get("cpu_change_pct", 0.0)
        memory = plan.assumptions.get("memory_change_pct", 0.0)
        impact = (0.6 * traffic) + (0.3 * cpu) + (0.2 * memory)

        latency = baseline_data["latency_ms"] * (1.0 + max(-60.0, impact) / 100.0 * 0.9)
        throughput = baseline_data["throughput_rps"] * (1.0 + (traffic / 100.0) * 0.8 - (cpu / 100.0) * 0.15)
        error_rate = baseline_data["error_rate_pct"] + max(0.0, impact) * 0.015
        cost = baseline_data["cost_usd_hour"] * (1.0 + max(0.0, traffic) / 100.0 * 0.2)

        kpis = [
            KpiResult(kpi="latency_ms", baseline=baseline_data["latency_ms"], simulated=round(latency, 2), unit="ms"),
            KpiResult(kpi="error_rate_pct", baseline=baseline_data["error_rate_pct"], simulated=round(error_rate, 3), unit="%"),
            KpiResult(kpi="throughput_rps", baseline=baseline_data["throughput_rps"], simulated=round(throughput, 2), unit="rps"),
            KpiResult(kpi="cost_usd_hour", baseline=baseline_data["cost_usd_hour"], simulated=round(cost, 2), unit="USD/h"),
        ]
        rule = get_published_rule(plan.service)
        model_info = {
            "strategy": "rule",
            "rule_id": rule["rule_id"],
            "rule_version": rule["version"],
            "formula": rule["formula"],
            "tenant_id": tenant_id,
        }
        return kpis, 0.72, model_info
