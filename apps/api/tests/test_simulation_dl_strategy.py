from __future__ import annotations

from app.modules.simulation.services.simulation.schemas import SimulationPlan
from app.modules.simulation.services.simulation.strategies.dl_strategy import (
    DeepLearningStrategy,
)


def test_dl_strategy_deterministic_output_shape():
    strategy = DeepLearningStrategy()
    plan = SimulationPlan(
        scenario_name="stress:api-gateway",
        assumptions={"traffic_change_pct": 80, "cpu_change_pct": 30, "memory_change_pct": 20},
        horizon="7d",
        strategy="dl",
        scenario_type="stress_test",
        service="api-gateway",
        question="버스트 트래픽 영향",
    )
    baseline = {
        "latency_ms": 180.0,
        "error_rate_pct": 1.2,
        "throughput_rps": 1200.0,
        "cost_usd_hour": 42.0,
    }

    kpis_a, confidence_a, model_a = strategy.run(plan=plan, baseline_data=baseline, tenant_id="t1")
    kpis_b, confidence_b, model_b = strategy.run(plan=plan, baseline_data=baseline, tenant_id="t1")

    assert len(kpis_a) == 4
    assert [k.model_dump() for k in kpis_a] == [k.model_dump() for k in kpis_b]
    assert confidence_a == confidence_b
    assert model_a["version"] == model_b["version"] == "dl-v1"
