import json

import pytest
from api.routes import chat as chat_router
from httpx import AsyncClient
from main import app
from services.summary import ConversationSummaryService

pytestmark = pytest.mark.asyncio(loop_scope="module")


class _StubSummaryService(ConversationSummaryService):
    def __init__(self) -> None:
        pass

    def summarize_thread(self, session, thread):  # type: ignore[override]
        return None


class _ContractBadOrchestrator:
    async def stream_chat(self, prompt: str):
        yield {"type": "answer", "text": "plain text without json"}
        yield {"type": "done", "text": "done"}


class _ContractGoodOrchestrator:
    async def stream_chat(self, prompt: str):
        yield {
            "type": "answer",
            "text": '{"type":"api_draft","draft":{"api_name":"x","method":"GET","endpoint":"/x","logic":{"type":"sql","query":"SELECT 1"},"is_active":true,"runtime_policy":{}}}',
        }
        yield {"type": "done", "text": "done"}


async def test_chat_stream_returns_answer_chunk():
    async with AsyncClient(app=app, base_url="http://testserver", timeout=10) as client:
        async with client.stream(
            "GET", "/chat/stream", params={"message": "test"}
        ) as response:
            assert response.status_code == 200
            found_answer = False
            async for line in response.aiter_lines():
                if not line.strip().startswith("data:"):
                    continue
                payload = json.loads(line.strip()[len("data:") :].strip())
                if payload.get("type") == "answer":
                    found_answer = True
                    break

    assert found_answer


async def test_chat_stream_emits_contract_error_when_invalid_output():
    app.dependency_overrides[chat_router.get_orchestrator] = (
        lambda: _ContractBadOrchestrator()
    )
    app.dependency_overrides[chat_router.get_summary_service] = (
        lambda: _StubSummaryService()
    )
    try:
        async with AsyncClient(
            app=app, base_url="http://testserver", timeout=10
        ) as client:
            async with client.stream(
                "GET",
                "/chat/stream",
                params={"message": "make api", "expected_contract": "api_draft"},
            ) as response:
                assert response.status_code == 200
                saw_contract_error = False
                async for line in response.aiter_lines():
                    if not line.strip().startswith("data:"):
                        continue
                    payload = json.loads(line.strip()[len("data:") :].strip())
                    if payload.get("type") == "contract_error":
                        saw_contract_error = True
                        break
        assert saw_contract_error
    finally:
        app.dependency_overrides.pop(chat_router.get_orchestrator, None)
        app.dependency_overrides.pop(chat_router.get_summary_service, None)


async def test_chat_stream_no_contract_error_for_valid_output():
    app.dependency_overrides[chat_router.get_orchestrator] = (
        lambda: _ContractGoodOrchestrator()
    )
    app.dependency_overrides[chat_router.get_summary_service] = (
        lambda: _StubSummaryService()
    )
    try:
        async with AsyncClient(
            app=app, base_url="http://testserver", timeout=10
        ) as client:
            async with client.stream(
                "GET",
                "/chat/stream",
                params={"message": "make api", "expected_contract": "api_draft"},
            ) as response:
                assert response.status_code == 200
                saw_contract_error = False
                async for line in response.aiter_lines():
                    if not line.strip().startswith("data:"):
                        continue
                    payload = json.loads(line.strip()[len("data:") :].strip())
                    if payload.get("type") == "contract_error":
                        saw_contract_error = True
                        break
        assert not saw_contract_error
    finally:
        app.dependency_overrides.pop(chat_router.get_orchestrator, None)
        app.dependency_overrides.pop(chat_router.get_summary_service, None)
