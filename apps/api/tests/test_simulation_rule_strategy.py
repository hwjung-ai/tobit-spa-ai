from __future__ import annotations

from app.modules.simulation.services.simulation.schemas import SimulationPlan
from app.modules.simulation.services.simulation.strategies.rule_strategy import (
    RuleBasedStrategy,
)


def test_rule_strategy_is_deterministic():
    strategy = RuleBasedStrategy()
    plan = SimulationPlan(
        scenario_name="what_if:api-gateway",
        assumptions={"traffic_change_pct": 20, "cpu_change_pct": 10, "memory_change_pct": 5},
        horizon="7d",
        strategy="rule",
        scenario_type="what_if",
        service="api-gateway",
        question="트래픽 증가 영향",
    )
    baseline = {
        "latency_ms": 180.0,
        "error_rate_pct": 1.2,
        "throughput_rps": 1200.0,
        "cost_usd_hour": 42.0,
    }

    kpis_a, confidence_a, model_a = strategy.run(plan=plan, baseline_data=baseline, tenant_id="t1")
    kpis_b, confidence_b, model_b = strategy.run(plan=plan, baseline_data=baseline, tenant_id="t1")

    assert [k.model_dump() for k in kpis_a] == [k.model_dump() for k in kpis_b]
    assert confidence_a == confidence_b
    assert model_a["rule_id"] == model_b["rule_id"]
