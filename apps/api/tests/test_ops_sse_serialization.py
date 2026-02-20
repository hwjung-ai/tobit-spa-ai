import json
from uuid import uuid4

from app.modules.ops.routes.ask_stream import _sse_event as ask_stream_sse_event
from app.modules.ops.services.ops_sse_handler import OpsSSEHandler
from app.modules.ops.services.orchestration.planner.plan_schema import (
    DirectAnswerPayload,
    PlanOutput,
    PlanOutputKind,
)


def test_ask_stream_sse_event_serializes_uuid() -> None:
    payload = {"trace_id": uuid4(), "message": "ok"}

    event = ask_stream_sse_event("complete", payload)

    assert event.startswith("event: complete\n")
    assert '"message": "ok"' in event
    assert str(payload["trace_id"]) in event


def test_ops_sse_handler_serializes_uuid() -> None:
    handler = OpsSSEHandler()
    payload = {"id": uuid4(), "status": "done"}

    event = handler._sse_event("progress", payload)

    assert event.startswith("event: progress\n")
    assert '"status": "done"' in event
    assert str(payload["id"]) in event


def test_ops_ask_stream_emits_complete_event(client, monkeypatch) -> None:
    from app.modules.ops.routes import ask_stream as ask_stream_module

    monkeypatch.setattr(ask_stream_module, "load_resolver_asset", lambda *_a, **_k: None)
    monkeypatch.setattr(ask_stream_module, "load_source_asset", lambda *_a, **_k: None)
    monkeypatch.setattr(ask_stream_module, "load_catalog_asset", lambda *_a, **_k: None)
    monkeypatch.setattr(
        ask_stream_module, "resolve_catalog_asset_for_source", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        ask_stream_module, "load_mapping_asset", lambda *_a, **_k: ({}, "meta")
    )
    monkeypatch.setattr(ask_stream_module, "load_policy_asset", lambda *_a, **_k: {})
    monkeypatch.setattr(ask_stream_module, "persist_execution_trace", lambda *_a, **_k: None)
    monkeypatch.setattr(ask_stream_module, "get_all_spans", lambda: [])

    monkeypatch.setattr(
        ask_stream_module.planner_llm,
        "create_plan_output",
        lambda *_a, **_k: PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct_answer=DirectAnswerPayload(answer="총 CI 개수는 42개입니다."),
            confidence=1.0,
        ),
    )

    response = client.post(
        "/ops/ask/stream",
        json={"question": "전체 ci 갯수를 알려줘"},
        headers={"x-tenant-id": "default"},
    )

    assert response.status_code == 200
    body = response.text
    assert "event: progress" in body
    assert "event: complete" in body
    assert "총 CI 개수는 42개입니다." in body


def test_ops_ask_stream_persists_history_with_uuid_payload(client, monkeypatch) -> None:
    from app.modules.ops.routes import ask_stream as ask_stream_module
    from app.modules.ops.services.orchestration.planner.plan_schema import Plan

    monkeypatch.setattr(ask_stream_module, "load_resolver_asset", lambda *_a, **_k: None)
    monkeypatch.setattr(ask_stream_module, "load_source_asset", lambda *_a, **_k: None)
    monkeypatch.setattr(ask_stream_module, "load_catalog_asset", lambda *_a, **_k: None)
    monkeypatch.setattr(
        ask_stream_module, "resolve_catalog_asset_for_source", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        ask_stream_module, "load_mapping_asset", lambda *_a, **_k: ({}, "meta")
    )
    monkeypatch.setattr(ask_stream_module, "load_policy_asset", lambda *_a, **_k: {})
    monkeypatch.setattr(ask_stream_module, "persist_execution_trace", lambda *_a, **_k: None)
    monkeypatch.setattr(ask_stream_module, "get_all_spans", lambda: [])
    monkeypatch.setattr(
        ask_stream_module.planner_llm,
        "create_plan_output",
        lambda *_a, **_k: PlanOutput(
            kind=PlanOutputKind.PLAN,
            plan=Plan(),
            confidence=1.0,
        ),
    )
    monkeypatch.setattr(
        ask_stream_module.validator,
        "validate_plan",
        lambda plan, **_kwargs: (plan, {"validated": True}),
    )

    expected_trace_uuid = uuid4()

    class FakeRunner:
        def __init__(self, *_args, **_kwargs):
            pass

        async def run_async(self, _plan_output):
            return {
                "answer": "ok",
                "blocks": [{"type": "text", "content": "ok"}],
                "trace": {"trace_uuid": expected_trace_uuid, "tool_calls": []},
                "next_actions": [],
                "meta": {"summary": "ok"},
            }

    monkeypatch.setattr(ask_stream_module, "OpsOrchestratorRunner", FakeRunner)

    store: dict[str, object] = {"history": None}

    class FakeSession:
        def add(self, obj):
            if hasattr(obj, "question"):
                if getattr(obj, "id", None) is None:
                    obj.id = str(uuid4())
                store["history"] = obj

        def commit(self):
            history = store.get("history")
            if history is not None and getattr(history, "response", None) is not None:
                json.dumps(history.response)

        def refresh(self, _obj):
            return None

        def get(self, _model, _history_id):
            return store.get("history")

    class FakeSessionContext:
        def __enter__(self):
            return FakeSession()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ask_stream_module, "get_session_context", lambda: FakeSessionContext())

    response = client.post(
        "/ops/ask/stream",
        json={"question": "uuid payload history 저장 테스트"},
        headers={"x-tenant-id": "default"},
    )
    assert response.status_code == 200
    assert "event: complete" in response.text
    history = store.get("history")
    assert history is not None
    assert history.status == "ok"
    assert history.response is not None
    assert history.response["trace"]["trace_uuid"] == str(expected_trace_uuid)
