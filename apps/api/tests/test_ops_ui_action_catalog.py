"""Tests for /ops/ui-actions/catalog endpoint."""

from fastapi.testclient import TestClient
from main import app


def test_ui_actions_catalog_returns_envelope(monkeypatch):
    """Catalog endpoint returns standardized envelope and action list."""
    expected_actions = [
        {
            "action_id": "fetch_device_detail",
            "label": "Fetch Device Detail",
            "description": "Fetch device detail view",
            "input_schema": {"type": "object"},
            "tags": ["device", "detail"],
            "version": "v1",
            "experimental": False,
        }
    ]

    monkeypatch.setattr(
        "app.modules.ops.router.list_registered_actions",
        lambda: expected_actions,
    )

    client = TestClient(app)
    response = client.get("/ops/ui-actions/catalog")

    assert response.status_code == 200
    envelope = response.json()
    assert envelope["code"] == 0
    assert envelope["message"] == "OK"
    assert "data" in envelope
    assert envelope["data"]["actions"] == expected_actions
    assert envelope["data"]["count"] == 1

