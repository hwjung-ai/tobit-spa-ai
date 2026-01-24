import os
from pathlib import Path

import pytest
from app.llm.client import get_llm_client
from dotenv import load_dotenv
from services.orchestrator import get_orchestrator

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="API key required")
@pytest.mark.asyncio
async def test_streaming_migration():
    orchestrator = get_orchestrator()
    found_answer = False
    async for chunk in orchestrator.stream_chat("say hi"):
        if chunk.get("type") == "answer":
            found_answer = True
            print(f"Streaming answer: {chunk.get('text')}")
        if chunk.get("type") == "done":
            break
    assert found_answer, "Streaming did not return an answer"


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="API key required")
def test_embedding_migration():
    llm = get_llm_client()
    query = "test query"
    embedding = llm.embed(input=query)
    assert hasattr(embedding, "data")
    assert len(embedding.data[0].embedding) > 0
    print(f"Embedding successful, length: {len(embedding.data[0].embedding)}")


@pytest.mark.asyncio
async def test_llm_client_output_parsing():
    llm = get_llm_client()

    # Mock response object
    class MockResponse:
        output_text = "hello world"
        output_items = [{"type": "text", "text": "hello"}]

    assert llm.get_output_text(MockResponse()) == "hello world"
    items = llm.get_output_items(MockResponse())
    assert len(items) == 1
    assert items[0]["text"] == "hello"

    # Mock response dict
    mock_dict = {
        "output_text": "bye world",
        "output_items": [{"type": "text", "text": "bye"}],
    }
    assert llm.get_output_text(mock_dict) == "bye world"
    assert llm.get_output_items(mock_dict)[0]["text"] == "bye"
