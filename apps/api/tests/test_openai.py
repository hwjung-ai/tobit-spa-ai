import pytest

from services import get_orchestrator


@pytest.mark.asyncio
async def test_openai_stream_hello():
    orchestrator = get_orchestrator()
    message = "hello?"
    chunk_texts = []

    async for chunk in orchestrator.stream_chat(message):
        print("chunk:", chunk)
        chunk_texts.append(chunk)
        if chunk.get("type") == "done":
            break

    assert any(c["type"] == "answer" for c in chunk_texts)
