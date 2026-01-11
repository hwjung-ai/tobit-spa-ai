import pytest

from httpx import AsyncClient

from main import app


@pytest.mark.asyncio
async def test_hello_endpoint_structure():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/hello")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["message"] == "OK"
    assert payload["data"] == {"hello": "tobit-spa-ai"}
