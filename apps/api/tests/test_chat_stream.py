import json

import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
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
