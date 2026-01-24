from fastapi.testclient import TestClient
from main import app


def test_hello_endpoint_structure():
    client = TestClient(app)
    response = client.get("/hello")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["message"] == "OK"
    assert payload["data"] == {"hello": "tobit-spa-ai"}


def test_hello_endpoint_invalid_method():
    client = TestClient(app)
    response = client.post("/hello")

    # FastAPI should return 405 Method Not Allowed
    assert response.status_code == 405
