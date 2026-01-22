import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_health_endpoint_structure():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert isinstance(payload["time"], str)
    assert payload["message"] == "Healthy"
    assert isinstance(payload["data"], dict)
