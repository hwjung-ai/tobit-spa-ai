from typing import Any

from app.modules.ops.services.orchestration.planner.plan_schema import (
    DirectAnswerPayload,
    PlanOutput,
    PlanOutputKind,
)
from fastapi.testclient import TestClient
from main import app


def _noop_persist(*args: Any, **kwargs: Any) -> None:
    return None


def test_ci_ask_auto_binds_catalog_from_source(monkeypatch):
    import importlib

    ops_router = importlib.import_module("app.modules.ops.router")
    from app.modules.ops.services.orchestration.planner import planner_llm

    captured: dict[str, Any] = {}

    def fake_plan_output(_: str, **kwargs: Any) -> PlanOutput:
        captured["schema_context"] = kwargs.get("schema_context")
        captured["source_context"] = kwargs.get("source_context")
        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct_answer=DirectAnswerPayload(answer="ok", confidence=0.9),
            confidence=0.9,
            reasoning="direct",
        )

    monkeypatch.setattr(ops_router, "load_resolver_asset", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ops_router, "load_catalog_asset", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        ops_router,
        "load_source_asset",
        lambda name, **_kwargs: {"name": name, "source_type": "postgresql", "connection": {}},
    )
    monkeypatch.setattr(
        ops_router,
        "resolve_catalog_asset_for_source",
        lambda source_ref: {
            "name": "primary_postgres_catalog",
            "source_ref": source_ref,
            "catalog": {
                "source_ref": source_ref,
                "tables": [{"name": "ci", "columns": [{"column_name": "ci_id"}]}],
            },
        },
    )
    monkeypatch.setattr(ops_router, "load_mapping_asset", lambda *_args, **_kwargs: ({}, None))
    monkeypatch.setattr(ops_router, "load_policy_asset", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(planner_llm, "create_plan_output", fake_plan_output)
    monkeypatch.setattr(ops_router, "persist_execution_trace", _noop_persist)

    client = TestClient(app)
    response = client.post(
        "/ops/ask",
        json={"question": "show ci", "source_asset": "primary_postgres_ops"},
    )

    assert response.status_code == 200
    assert captured.get("source_context") is not None
    assert captured.get("schema_context") is not None
    assert captured["schema_context"]["name"] == "primary_postgres_catalog"
    assert captured["schema_context"]["source_ref"] == "primary_postgres_ops"
