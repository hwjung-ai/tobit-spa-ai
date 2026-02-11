from __future__ import annotations

import pytest
from app.modules.simulation.schemas import SimulationRunRequest
from app.modules.simulation.services.simulation.simulation_executor import (
    run_simulation,
)


@pytest.fixture(autouse=True)
def _mock_baseline_loader(monkeypatch):
    def _fake_loader(*, tenant_id, service, scenario_type, assumptions):
        _ = (tenant_id, service, scenario_type, assumptions)
        return (
            {
                "latency_ms": 100.0,
                "error_rate_pct": 0.6,
                "throughput_rps": 1100.0,
                "cost_usd_hour": 28.0,
            },
            {
                "latency_ms": 120.0,
                "error_rate_pct": 0.9,
                "throughput_rps": 980.0,
                "cost_usd_hour": 31.0,
            },
        )

    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.simulation_executor.load_baseline_and_scenario_kpis",
        _fake_loader,
    )
    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.simulation_executor.execute_custom_function",
        lambda function, params, input_payload: {
            "output": {
                "kpis": [
                    {"kpi": "latency_ms", "baseline": 100.0, "simulated": 118.0, "unit": "ms"},
                    {"kpi": "error_rate_pct", "baseline": 0.6, "simulated": 0.85, "unit": "%"},
                ],
                "confidence": 0.81,
                "model_info": {"version": "sim-fn-v1"},
                "explanation": "custom executor",
                "recommended_actions": ["review scaling threshold"],
            },
            "duration_ms": 5,
            "logs": [],
            "references": {},
        },
    )


def test_simulation_executor_builds_blocks_and_references():
    payload = SimulationRunRequest(
        question="트래픽 증가 영향",
        scenario_type="what_if",
        strategy="stat",
        horizon="7d",
        service="api-gateway",
        assumptions={"traffic_change_pct": 25, "cpu_change_pct": 10, "memory_change_pct": 5},
    )

    output = run_simulation(payload=payload, tenant_id="t1", requested_by="u1")

    assert output["simulation"]["strategy"] == "stat"
    assert len(output["blocks"]) >= 3
    assert len(output["references"]) >= 2
    assert len(output["tool_calls"]) == 1
    assert output["plan"]["strategy"] == "stat"
    assert output["simulation"]["confidence_interval"] is not None


def test_simulation_executor_custom_strategy():
    payload = SimulationRunRequest(
        question="custom function run",
        scenario_type="what_if",
        strategy="custom",
        horizon="7d",
        service="api-gateway",
        assumptions={"traffic_change_pct": 10},
        custom_function={
            "name": "sim_fn",
            "function_name": "simulate",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "code": "def simulate(params, input_payload):\\n    return {'kpis': []}",
            "runtime_policy": {},
        },
        custom_input={"user_factor": 0.9},
    )

    output = run_simulation(payload=payload, tenant_id="t1", requested_by="u1")

    assert output["simulation"]["strategy"] == "custom"
    assert len(output["simulation"]["kpis"]) >= 1
    assert output["simulation"]["model_info"]["version"] == "sim-fn-v1"
