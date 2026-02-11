from __future__ import annotations

from typing import Any

from app.modules.simulation.services.simulation.model_registry import get_model_metadata
from app.modules.simulation.services.simulation.schemas import KpiResult, SimulationPlan


class DeepLearningStrategy:
    name = "dl"

    def run(self, *, plan: SimulationPlan, baseline_data: dict[str, float], tenant_id: str) -> tuple[list[KpiResult], float, dict[str, Any]]:
        traffic = plan.assumptions.get("traffic_change_pct", 0.0)
        cpu = plan.assumptions.get("cpu_change_pct", 0.0)
        memory = plan.assumptions.get("memory_change_pct", 0.0)

        # Deterministic pseudo-sequence inference to emulate DL-style nonlinearity.
        seq_signal = (0.018 * traffic * traffic / 100.0) + (0.024 * cpu) + (0.014 * memory)
        gate = 1.0 / (1.0 + (2.71828 ** (-0.08 * (traffic + cpu))))
        latent = (seq_signal * 0.55) + (gate * 0.45)

        latency = baseline_data["latency_ms"] * max(0.6, min(2.8, 1.0 + latent * 0.18))
        throughput = baseline_data["throughput_rps"] * max(0.15, 1.0 + (traffic * 0.0042) - (cpu * 0.0027) - (latent * 0.03))
        error_rate = baseline_data["error_rate_pct"] + max(0.0, latent * 0.21)
        cost = baseline_data["cost_usd_hour"] * (1.0 + max(0.0, traffic) / 100.0 * 0.24 + max(0.0, latent) * 0.03)

        kpis = [
            KpiResult(kpi="latency_ms", baseline=baseline_data["latency_ms"], simulated=round(latency, 2), unit="ms"),
            KpiResult(kpi="error_rate_pct", baseline=baseline_data["error_rate_pct"], simulated=round(error_rate, 3), unit="%"),
            KpiResult(kpi="throughput_rps", baseline=baseline_data["throughput_rps"], simulated=round(throughput, 2), unit="rps"),
            KpiResult(kpi="cost_usd_hour", baseline=baseline_data["cost_usd_hour"], simulated=round(cost, 2), unit="USD/h"),
        ]
        model_info = get_model_metadata("dl")
        model_info["tenant_id"] = tenant_id
        model_info["latent_signal"] = round(latent, 4)
        return kpis, 0.88, model_info
