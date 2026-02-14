from __future__ import annotations

from importlib import import_module

import pytest
from app.modules.auth.models import TbUser, UserRole
from core.auth import get_current_user
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def _mock_baseline_loader(monkeypatch):
    router_module = import_module("app.modules.simulation.api.router")

    def _fake_loader(*, tenant_id, service, scenario_type, assumptions):
        _ = (tenant_id, service, scenario_type, assumptions)
        baseline = {
            "latency_ms": 120.0,
            "error_rate_pct": 0.8,
            "throughput_rps": 950.0,
            "cost_usd_hour": 33.0,
        }
        scenario = {
            "latency_ms": 138.0,
            "error_rate_pct": 1.2,
            "throughput_rps": 900.0,
            "cost_usd_hour": 36.0,
        }
        return baseline, scenario

    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.simulation_executor.load_baseline_and_scenario_kpis",
        _fake_loader,
    )
    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.simulation_executor.execute_custom_function",
        lambda function, params, input_payload: {
            "output": {
                "kpis": [
                    {
                        "kpi": "latency_ms",
                        "baseline": 120.0,
                        "simulated": 135.0,
                        "unit": "ms",
                    }
                ],
                "confidence": 0.82,
                "model_info": {"version": "custom-v1"},
                "explanation": "custom function executed",
            },
            "duration_ms": 4,
            "logs": [],
            "references": {"simulated": True},
        },
    )
    monkeypatch.setattr(
        router_module,
        "execute_custom_function",
        lambda function, params, input_payload: {
            "output": {"ok": True, "echo": input_payload},
            "duration_ms": 2,
            "logs": ["validated"],
            "references": {"kind": "custom"},
        },
    )
    monkeypatch.setattr(
        router_module,
        "run_backtest_real",
        lambda strategy, service, horizon, assumptions, tenant_id: {
            "strategy": strategy,
            "service": service,
            "horizon": horizon,
            "summary": "mock backtest",
            "metrics": {
                "r2": 0.72,
                "mape": 0.11,
                "rmse": 2.3,
                "coverage_90": 0.9,
            },
        },
    )


def _mock_user(tenant_id: str = "t1") -> TbUser:
    return TbUser(
        username="sim-user",
        password_hash="hashed",
        role=UserRole.ADMIN,
        tenant_id=tenant_id,
        is_active=True,
        email_encrypted="enc-email",
        phone_encrypted=None,
    )


def test_simulation_run_success():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.post(
        "/sim/run",
        json={
            "question": "트래픽 20% 증가 시 영향",
            "scenario_type": "what_if",
            "strategy": "ml",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {
                "traffic_change_pct": 20,
                "cpu_change_pct": 10,
                "memory_change_pct": 5,
            },
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 0
    data = payload.get("data") or {}
    assert data.get("simulation", {}).get("strategy") == "ml"
    assert len(data.get("simulation", {}).get("kpis", [])) >= 3
    assert len(data.get("tool_calls", [])) == 1
    assert data.get("simulation", {}).get("confidence_interval") is not None


def test_simulation_query_success():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.post(
        "/sim/query",
        json={
            "question": "트래픽 20% 증가 시 영향",
            "scenario_type": "what_if",
            "strategy": "rule",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {"traffic_change_pct": 20},
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 0
    plan = (payload.get("data") or {}).get("plan") or {}
    assert plan.get("strategy") == "rule"
    assert plan.get("service") == "api-gateway"


def test_simulation_run_tenant_mismatch():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("t2")
    client = TestClient(app)

    response = client.post(
        "/sim/run",
        json={
            "question": "tenant mismatch case",
            "scenario_type": "what_if",
            "strategy": "rule",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {"traffic_change_pct": 10},
        },
        headers={"X-Tenant-Id": "t2"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403


def test_simulation_run_invalid_assumption_key():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.post(
        "/sim/run",
        json={
            "question": "invalid assumption",
            "scenario_type": "what_if",
            "strategy": "rule",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {"invalid_key": 10},
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 400


def test_simulation_templates():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.get("/sim/templates", headers={"X-Tenant-Id": "t1"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 0
    templates = (payload.get("data") or {}).get("templates") or []
    assert len(templates) >= 1


def test_simulation_run_dl_strategy_success():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.post(
        "/sim/run",
        json={
            "question": "버스트 트래픽 영향",
            "scenario_type": "stress_test",
            "strategy": "dl",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {
                "traffic_change_pct": 80,
                "cpu_change_pct": 30,
                "memory_change_pct": 20,
            },
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    data = payload.get("data") or {}
    assert data.get("simulation", {}).get("strategy") == "dl"


def test_simulation_backtest_and_export():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    backtest_response = client.post(
        "/sim/backtest",
        json={
            "strategy": "stat",
            "service": "api-gateway",
            "horizon": "30d",
            "assumptions": {"traffic_change_pct": 10},
        },
        headers={"X-Tenant-Id": "t1"},
    )
    assert backtest_response.status_code == 200
    backtest_data = (backtest_response.json().get("data") or {}).get("backtest") or {}
    assert "metrics" in backtest_data

    export_response = client.post(
        "/sim/export",
        json={
            "question": "csv export",
            "scenario_type": "what_if",
            "strategy": "rule",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {"traffic_change_pct": 10, "cpu_change_pct": 5, "memory_change_pct": 2},
        },
        headers={"X-Tenant-Id": "t1"},
    )
    app.dependency_overrides.clear()

    assert export_response.status_code == 200
    assert "kpi,baseline,simulated,change_pct,unit" in export_response.text


def test_simulation_run_custom_strategy_success():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.post(
        "/sim/run",
        json={
            "question": "custom strategy",
            "scenario_type": "what_if",
            "strategy": "custom",
            "horizon": "7d",
            "service": "api-gateway",
            "assumptions": {"traffic_change_pct": 10},
            "custom_input": {"factor": 1.1},
            "custom_function": {
                "name": "latency_adjuster",
                "function_name": "simulate",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "code": "def simulate(params, input_payload):\\n    return {'kpis': []}",
                "runtime_policy": {"timeout_ms": 3000},
            },
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 0
    assert (payload.get("data") or {}).get("simulation", {}).get("strategy") == "custom"


def test_simulation_custom_function_validate_endpoint():
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    response = client.post(
        "/sim/functions/validate",
        json={
            "function": {
                "name": "echo_fn",
                "function_name": "simulate",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "code": "def simulate(params, input_payload):\\n    return {'ok': True}",
                "runtime_policy": {},
            },
            "sample_params": {"tenant_id": "t1"},
            "sample_input": {"sample": 1},
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 0
    assert (payload.get("data") or {}).get("valid") is True


def test_simulation_run_realtime_accepts_source_config_in_body(monkeypatch):
    router_module = import_module("app.modules.simulation.api.router")
    app.dependency_overrides[get_current_user] = lambda: _mock_user("default")
    client = TestClient(app)

    async def _fake_realtime(payload, tenant_id, requested_by):
        _ = (payload, tenant_id, requested_by)
        return {"simulation": {"strategy": "ml"}, "summary": "ok"}

    monkeypatch.setattr(router_module, "run_realtime_simulation", _fake_realtime)

    response = client.post(
        "/sim/run/realtime",
        json={
            "question": "realtime test",
            "scenario_type": "what_if",
            "strategy": "ml",
            "horizon": "24h",
            "service": "api-gateway",
            "assumptions": {"traffic_change_pct": 20},
            "source_config": {
                "source": "prometheus",
                "prometheus_url": "http://prometheus:9090",
                "query": "rate(http_requests_total[5m])",
            },
        },
        headers={"X-Tenant-Id": "t1"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("code") == 0
    assert ((payload.get("data") or {}).get("simulation") or {}).get("strategy") == "ml"
