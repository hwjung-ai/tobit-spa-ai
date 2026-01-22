"""Test operation settings management."""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client(session):
    # Override the default session in the app
    from unittest.mock import patch

    import core.db

    def get_session_override():
        yield session

    with patch.object(core.db, "get_session", get_session_override):
        with TestClient(app) as test_client:
            yield test_client




def test_get_all_operation_settings(client):
    """Test GET /settings/operations returns all settings."""
    response = client.get("/settings/operations")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert "settings" in data["data"]

    settings = data["data"]["settings"]
    assert isinstance(settings, dict)

    # Check that expected settings are present
    expected_keys = {
        "ops_mode",
        "ops_enable_langgraph",
        "enable_system_apis",
        "enable_data_explorer",
    }
    for key in expected_keys:
        assert key in settings, f"Setting {key} should be present"
        setting = settings[key]
        assert "value" in setting
        assert "source" in setting
        assert "restart_required" in setting
        assert "description" in setting
        assert "default" in setting


def test_get_ops_mode_setting(client):
    """Test GET /settings/operations/ops_mode returns ops_mode setting."""
    response = client.get("/settings/operations/ops_mode")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    setting = data["data"]

    assert setting["key"] == "ops_mode"
    assert setting["value"] in ["mock", "real"]
    assert setting["source"] in ["published", "env", "default"]
    assert "restart_required" in setting
    assert setting["allowed_values"] == ["mock", "real"]


def test_get_unknown_setting(client):
    """Test GET /settings/operations/<unknown> returns 400."""
    response = client.get("/settings/operations/unknown_setting")
    assert response.status_code == 400
    assert "Unknown setting" in response.json()["detail"]


def test_update_ops_mode_setting(client):
    """Test PUT /settings/operations/ops_mode updates the setting."""
    # Get current value
    response = client.get("/settings/operations/ops_mode")
    assert response.status_code == 200
    current = response.json()["data"]
    current_value = current["value"]

    # Update to opposite value
    new_value = "real" if current_value == "mock" else "mock"
    response = client.put(
        "/settings/operations/ops_mode",
        json={"value": new_value},
        params={"updated_by": "test_user"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    updated = data["data"]

    assert updated["key"] == "ops_mode"
    assert updated["value"] == new_value
    assert updated["source"] == "published"
    assert updated["restart_required"] is True
    assert updated["published_by"] == "test_user"


def test_update_setting_with_invalid_value(client):
    """Test PUT /settings/operations/ops_mode with invalid value returns 400."""
    response = client.put(
        "/settings/operations/ops_mode",
        json={"value": "invalid_mode"},
        params={"updated_by": "test_user"},
    )
    assert response.status_code == 400
    assert "Invalid value" in response.json()["detail"]


def test_update_setting_with_wrong_type(client):
    """Test PUT /settings/operations/ops_mode with wrong type returns 400."""
    response = client.put(
        "/settings/operations/ops_mode",
        json={"value": 123},  # should be string
        params={"updated_by": "test_user"},
    )
    assert response.status_code == 400
    assert "Invalid type" in response.json()["detail"]


def test_update_boolean_setting(client):
    """Test PUT /settings/operations/enable_system_apis updates boolean setting."""
    # Get current value
    response = client.get("/settings/operations/enable_system_apis")
    assert response.status_code == 200
    current = response.json()["data"]
    current_value = current["value"]

    # Update to opposite value
    new_value = not current_value
    response = client.put(
        "/settings/operations/enable_system_apis",
        json={"value": new_value},
        params={"updated_by": "test_user"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    updated = data["data"]

    assert updated["key"] == "enable_system_apis"
    assert updated["value"] == new_value
    assert updated["source"] == "published"


def test_setting_persistence_across_requests(client):
    """Test that updated settings persist across requests."""
    # Update a setting
    new_value = "real"
    response1 = client.put(
        "/settings/operations/ops_mode",
        json={"value": new_value},
        params={"updated_by": "test_user"},
    )
    assert response1.status_code == 200

    # Get the setting again
    response2 = client.get("/settings/operations/ops_mode")
    assert response2.status_code == 200

    data = response2.json()["data"]
    assert data["value"] == new_value
    assert data["source"] == "published"


def test_setting_missing_value_field(client):
    """Test PUT /settings with missing value field returns 400."""
    response = client.put(
        "/settings/operations/ops_mode",
        json={},  # missing "value" field
        params={"updated_by": "test_user"},
    )
    assert response.status_code == 400
    assert "must include 'value'" in response.json()["detail"]
