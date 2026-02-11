from __future__ import annotations

from types import SimpleNamespace

from app.llm import client as llm_client_module
from app.llm.client import LlmClient


class _DummyResponses:
    def __init__(self, fail_once: bool = False):
        self.calls = []
        self.fail_once = fail_once

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_once and len(self.calls) == 1:
            raise RuntimeError("primary failed")
        return {"output_text": "ok", "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}


class _DummyClient:
    def __init__(self, fail_once: bool = False):
        self.responses = _DummyResponses(fail_once=fail_once)
        self.embeddings = SimpleNamespace(create=lambda **kwargs: {"data": []})


def test_llm_client_uses_internal_provider_settings(monkeypatch):
    captured_sync = {}
    captured_async = {}

    monkeypatch.setattr(
        llm_client_module,
        "_get_runtime_llm_settings",
        lambda: {
            "provider": "internal",
            "base_url": "http://internal-llm:8000/v1",
            "default_model": "internal-chat-v1",
            "fallback_model": "internal-chat-fallback",
            "timeout_seconds": 45,
            "max_retries": 1,
            "enable_fallback": True,
            "routing_policy": "latency",
            "openai_api_key": None,
            "internal_api_key": "internal-token",
        },
    )

    def _openai_ctor(**kwargs):
        captured_sync.update(kwargs)
        return _DummyClient()

    def _async_ctor(**kwargs):
        captured_async.update(kwargs)
        return _DummyClient()

    monkeypatch.setattr(llm_client_module, "OpenAI", _openai_ctor)
    monkeypatch.setattr(llm_client_module, "AsyncOpenAI", _async_ctor)

    client = LlmClient()

    assert client.provider == "internal"
    assert client.default_model == "internal-chat-v1"
    assert captured_sync["base_url"] == "http://internal-llm:8000/v1"
    assert captured_sync["api_key"] == "internal-token"
    assert float(captured_sync["timeout"]) == 45.0
    assert captured_async["base_url"] == "http://internal-llm:8000/v1"


def test_llm_client_fallback_model_on_failure(monkeypatch):
    monkeypatch.setattr(
        llm_client_module,
        "_get_runtime_llm_settings",
        lambda: {
            "provider": "openai",
            "base_url": None,
            "default_model": "gpt-primary",
            "fallback_model": "gpt-fallback",
            "timeout_seconds": 30,
            "max_retries": 2,
            "enable_fallback": True,
            "routing_policy": "default",
            "openai_api_key": "sk-test",
            "internal_api_key": None,
        },
    )

    failing_client = _DummyClient(fail_once=True)
    monkeypatch.setattr(llm_client_module, "OpenAI", lambda **kwargs: failing_client)
    monkeypatch.setattr(llm_client_module, "AsyncOpenAI", lambda **kwargs: _DummyClient())

    client = LlmClient()
    result = client.create_response(input="hello")

    assert result["output_text"] == "ok"
    assert len(failing_client.responses.calls) == 2
    assert failing_client.responses.calls[0]["model"] == "gpt-primary"
    assert failing_client.responses.calls[1]["model"] == "gpt-fallback"
