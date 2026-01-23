"""Tests for /ops/ci/ask pipeline routing and trace wiring."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.modules.ops.services.ci.planner.plan_schema import (
    DirectAnswerPayload,
    Plan,
    PlanOutput,
    PlanOutputKind,
    RejectPayload,
)
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _noop_persist(*args: Any, **kwargs: Any) -> None:
    return None


def test_ci_ask_direct_route(monkeypatch, client):
    import importlib

    from app.modules.ops.services.ci.planner import planner_llm

    ops_router = importlib.import_module("app.modules.ops.router")

    def fake_plan_output(_: str) -> PlanOutput:
        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct_answer=DirectAnswerPayload(answer="Hello there!", confidence=0.9),
            confidence=0.9,
            reasoning="direct greeting",
        )

    monkeypatch.setattr(planner_llm, "create_plan_output", fake_plan_output)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    response = client.post("/ops/ci/ask", json={"question": "hello"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["meta"]["route"] == "direct"
    assert data["trace"]["route"] == "direct"
    assert data["trace"]["stage_inputs"], "stage_inputs should be populated"
    assert data["trace"]["stage_outputs"], "stage_outputs should be populated"


def test_ci_ask_reject_route(monkeypatch, client):
    import importlib

    from app.modules.ops.services.ci.planner import planner_llm

    ops_router = importlib.import_module("app.modules.ops.router")

    def fake_plan_output(_: str) -> PlanOutput:
        return PlanOutput(
            kind=PlanOutputKind.REJECT,
            reject_payload=RejectPayload(reason="Unsupported question", confidence=1.0),
            confidence=1.0,
            reasoning="policy block",
        )

    monkeypatch.setattr(planner_llm, "create_plan_output", fake_plan_output)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    response = client.post("/ops/ci/ask", json={"question": "drop table"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["meta"]["route"] == "reject"
    assert data["trace"]["route"] == "reject"
    assert data["trace"]["stage_inputs"], "stage_inputs should be populated"
    assert data["trace"]["stage_outputs"], "stage_outputs should be populated"


def test_ci_ask_orchestration_stages(monkeypatch, client):
    import importlib

    from app.modules.ops.services.ci.planner import planner_llm, validator
    from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner

    ops_router = importlib.import_module("app.modules.ops.router")

    plan = Plan()

    def fake_plan_output(_: str) -> PlanOutput:
        return PlanOutput(kind=PlanOutputKind.PLAN, plan=plan, confidence=1.0, reasoning="orch")

    def fake_validate_plan(_: Plan):
        return plan, {"policy_decisions": {"dummy": True}}

    async def fake_run_with_stages(self, plan_output: PlanOutput):
        return {
            "answer": "ok",
            "blocks": [{"type": "text", "text": "ok"}],
            "trace": {
                "stage_inputs": [{"stage": "route_plan"}],
                "stage_outputs": [
                    {
                        "stage": "route_plan",
                        "result": {"route": "orch"},
                        "diagnostics": {"status": "ok", "warnings": [], "errors": []},
                        "references": [],
                        "duration_ms": 1,
                    }
                ],
                "stages": [
                    {
                        "name": "route_plan",
                        "input": {"stage": "route_plan"},
                        "output": {"route": "orch"},
                        "elapsed_ms": 1,
                        "status": "ok",
                    }
                ],
                "tool_calls": [],
                "references": [],
                "errors": [],
            },
            "next_actions": [],
            "meta": {"route": "orch", "route_reason": "Stage-based execution"},
        }

    monkeypatch.setattr(planner_llm, "create_plan_output", fake_plan_output)
    monkeypatch.setattr(validator, "validate_plan", fake_validate_plan)
    monkeypatch.setattr(CIOrchestratorRunner, "_run_async_with_stages", fake_run_with_stages)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    response = client.post("/ops/ci/ask", json={"question": "cpu usage"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trace"]["route"] == "orch"
    assert data["trace"]["stage_inputs"], "stage_inputs should be populated"
    assert data["trace"]["stage_outputs"], "stage_outputs should be populated"


def test_ci_ask_rerun_replan_events(monkeypatch, client):
    import importlib

    from app.modules.ops.services.ci.planner import validator
    from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner

    ops_router = importlib.import_module("app.modules.ops.router")

    plan = Plan()

    def fake_validate_plan(_: Plan):
        return plan, {"policy_decisions": {"dummy": True}}

    def fake_run(self, plan_output: PlanOutput):
        return {
            "answer": "ok",
            "blocks": [{"type": "text", "text": "ok"}],
            "trace": {"errors": [], "stage_inputs": [{}], "stage_outputs": [{}]},
            "next_actions": [],
            "meta": {"route": "orch"},
        }

    monkeypatch.setattr(validator, "validate_plan", fake_validate_plan)
    monkeypatch.setattr(CIOrchestratorRunner, "run", fake_run)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    response = client.post(
        "/ops/ci/ask",
        json={
            "question": "rerun",
            "rerun": {
                "base_plan": plan.model_dump(),
                "patch": {"output": {"primary": "table"}},
            },
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trace"]["replan_events"], "replan_events should be recorded for rerun"


def test_ci_ask_auto_replan_on_error(monkeypatch, client):
    import importlib

    from app.modules.ops.services.ci.planner import planner_llm, validator
    from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner

    ops_router = importlib.import_module("app.modules.ops.router")

    plan = Plan()

    def fake_plan_output(_: str) -> PlanOutput:
        return PlanOutput(kind=PlanOutputKind.PLAN, plan=plan, confidence=1.0, reasoning="orch")

    def fake_validate_plan(_: Plan):
        return plan, {"policy_decisions": {"dummy": True}}

    call_count = {"count": 0}

    def fake_run(self, plan_output: PlanOutput):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return {
                "answer": "fail",
                "blocks": [{"type": "text", "text": "fail"}],
                "trace": {"errors": ["boom"], "stage_inputs": [{}], "stage_outputs": [{}]},
                "next_actions": [],
                "meta": {"route": "orch"},
            }
        return {
            "answer": "ok",
            "blocks": [{"type": "text", "text": "ok"}],
            "trace": {"errors": [], "stage_inputs": [{}], "stage_outputs": [{}]},
            "next_actions": [],
            "meta": {"route": "orch"},
        }

    monkeypatch.setattr(planner_llm, "create_plan_output", fake_plan_output)
    monkeypatch.setattr(validator, "validate_plan", fake_validate_plan)
    monkeypatch.setattr(CIOrchestratorRunner, "run", fake_run)
    monkeypatch.setattr(ops_router, "evaluate_replan", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    response = client.post("/ops/ci/ask", json={"question": "auto replan"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trace"]["replan_events"], "auto replan should record events"
    assert data["answer"] == "ok"


def test_ci_ask_resolver_asset_applies_rules(monkeypatch, client):
    import importlib

    from app.modules.ops.services.ci.planner import planner_llm

    ops_router = importlib.import_module("app.modules.ops.router")

    captured = {"question": None}

    def fake_plan_output(question: str) -> PlanOutput:
        captured["question"] = question
        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct_answer=DirectAnswerPayload(answer="ok"),
            confidence=1.0,
        )

    resolver_payload = {
        "rules": [
            {
                "rule_type": "alias_mapping",
                "name": "alias-ci",
                "rule_data": {"source_entity": "srv-foo-01", "target_entity": "srv-erp-01"},
            }
        ]
    }

    monkeypatch.setattr(planner_llm, "create_plan_output", fake_plan_output)
    monkeypatch.setattr(ops_router, "load_resolver_asset", lambda _name: resolver_payload)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    response = client.post(
        "/ops/ci/ask",
        json={"question": "srv-foo-01 상태 알려줘", "resolver_asset": "ci-resolver"},
    )

    assert response.status_code == 200
    assert captured["question"] == "srv-erp-01 상태 알려줘"
