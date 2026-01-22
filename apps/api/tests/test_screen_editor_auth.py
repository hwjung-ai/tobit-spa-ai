"""
Screen Editor Authentication Tests
Tests for API authentication and asset-registry endpoints
"""

import pytest
from fastapi.testclient import TestClient
from main import app


def _extract_asset_id(response):
    body = response.json()
    if isinstance(body, dict):
        return (
            body.get("asset_id")
            or (body.get("data") or {}).get("asset_id")
            or (body.get("asset") or {}).get("asset_id")
        )
    return None


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client) -> str:
    """Get authentication token for admin user."""
    # Try multiple email formats as tests might use different configurations
    emails_to_try = [
        ("admin@example.com", "admin123"),
        ("admin@test.com", "admin123"),
    ]

    for email, password in emails_to_try:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json()["data"]["access_token"]

    # If no email works, skip test
    pytest.skip("No valid admin credentials found for testing")


class TestScreenEditorAuth:
    """Test suite for screen editor authentication."""

    def test_save_draft_requires_auth(self, client):
        """Test that save draft endpoint requires authentication."""
        # Try to POST without token
        response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "test-screen",
                "name": "Test Screen",
                "description": "Test",
                "schema_json": {
                    "screen_id": "test-screen",
                    "layout": {"type": "dashboard"},
                    "components": [],
                    "state": {"initial": {}},
                },
            }
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401
        assert "authorization" in response.text.lower() or "credentials" in response.text.lower()

    def test_save_draft_with_valid_token(self, client, auth_token):
        """Test that save draft works with valid token."""
        response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "test-screen-001",
                "name": "Test Screen",
                "description": "Test screen for validation",
                "schema_json": {
                    "screen_id": "test-screen-001",
                    "layout": {"type": "dashboard"},
                    "components": [],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should succeed (201 Created or 200 OK)
        assert response.status_code in [200, 201], f"Request failed: {response.text}"

    def test_invalid_token_rejected(self, client):
        """Test that invalid token is rejected."""
        response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "test-screen",
                "name": "Test Screen",
                "description": "Test",
                "schema_json": {
                    "screen_id": "test-screen",
                    "layout": {"type": "dashboard"},
                    "components": [],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Should return 401
        assert response.status_code == 401

    def test_missing_authorization_header_error(self, client):
        """Test that missing auth header returns proper error message."""
        response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "test-screen",
                "name": "Test Screen",
                "description": "Test",
                "schema_json": {
                    "screen_id": "test-screen",
                    "layout": {"type": "dashboard"},
                    "components": [],
                    "state": {"initial": {}},
                },
            }
        )

        # Should return 401 with "Missing authorization header"
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]

    def test_publish_requires_auth(self, client, auth_token):
        """Test that publish endpoint requires authentication."""
        # First create a screen
        create_response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "test-screen-pub",
                "name": "Test Screen",
                "description": "Test",
                "schema_json": {
                    "screen_id": "test-screen-pub",
                    "layout": {"type": "dashboard"},
                    "components": [],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create test screen")

        asset_id = _extract_asset_id(create_response)
        if not asset_id:
            pytest.skip("Failed to extract asset_id after asset creation")

        # Try to publish without token
        response = client.post(f"/asset-registry/assets/{asset_id}/publish")

        # Should return 401
        assert response.status_code == 401

    def test_rollback_requires_auth(self, client, auth_token):
        """Test that rollback endpoint requires authentication."""
        # First create a screen
        create_response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "test-screen-rollback",
                "name": "Test Screen",
                "description": "Test",
                "schema_json": {
                    "screen_id": "test-screen-rollback",
                    "layout": {"type": "dashboard"},
                    "components": [],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Failed to create test screen")

        asset_id = _extract_asset_id(create_response)
        if not asset_id:
            pytest.skip("Failed to extract asset_id after asset creation")

        # Try to rollback without token
        response = client.post(f"/asset-registry/assets/{asset_id}/unpublish")

        # Should return 401
        assert response.status_code == 401


class TestScreenEditorAuthFlow:
    """Test complete auth flow for screen editing."""

    def test_complete_screen_save_workflow(self, client, auth_token):
        """Test complete workflow: create → update → publish."""
        # Step 1: Create screen
        create_response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "workflow-test-screen",
                "name": "Workflow Test Screen",
                "description": "Testing complete workflow",
                "schema_json": {
                    "screen_id": "workflow-test-screen",
                    "layout": {"type": "dashboard"},
                    "components": [
                        {
                            "id": "button_1",
                            "type": "button",
                            "label": "Test Button",
                            "props": {},
                        }
                    ],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert create_response.status_code in [200, 201]
        asset_id = _extract_asset_id(create_response)
        assert asset_id is not None

        # Step 2: Update screen (PUT)
        update_response = client.put(
            f"/asset-registry/assets/{asset_id}",
            json={
                "schema_json": {
                    "screen_id": "workflow-test-screen",
                    "layout": {"type": "dashboard"},
                    "components": [
                        {
                            "id": "button_2",
                            "type": "button",
                            "label": "Updated Button",
                            "props": {},
                        }
                    ],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert update_response.status_code in [200, 204]

        # Step 3: Publish screen
        publish_response = client.post(
            f"/asset-registry/assets/{asset_id}/publish",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should succeed or at least not fail due to auth
        assert publish_response.status_code != 401

        # Step 4: Rollback screen
        rollback_response = client.post(
            f"/asset-registry/assets/{asset_id}/unpublish",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should succeed or at least not fail due to auth
        assert rollback_response.status_code != 401

    def test_publish_invalid_asset_returns_validation_error(self, client, auth_token):
        """Publish should fail when screen schema validation fails on the server."""
        create_response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "invalid-screen",
                "name": "Invalid Screen",
                "description": "Missing components in schema",
                "schema_json": {
                    "screen_id": "invalid-screen",
                    "layout": {"type": "dashboard"},
                    "components": [],  # Validator requires at least one component
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert create_response.status_code in [200, 201]
        asset_id = _extract_asset_id(create_response)
        assert asset_id is not None

        publish_response = client.post(
            f"/asset-registry/assets/{asset_id}/publish",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"published_by": "system-test"},
        )

        assert publish_response.status_code == 422
        assert "components must contain at least one component" in publish_response.json().get("detail", "")

    def test_stage_published_endpoint_blocks_drafts(self, client, auth_token):
        """Requesting ?stage=published should hide draft screens and succeed after publish."""
        create_response = client.post(
            "/asset-registry/assets",
            json={
                "asset_type": "screen",
                "screen_id": "stage-test-screen",
                "name": "Stage Test Screen",
                "description": "Stage filter test",
                "schema_json": {
                    "screen_id": "stage-test-screen",
                    "layout": {"type": "dashboard"},
                    "components": [
                        {
                            "id": "stage_button",
                            "type": "button",
                            "label": "Stage",
                            "props": {},
                        }
                    ],
                    "state": {"initial": {}},
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert create_response.status_code in [200, 201]
        asset_id = _extract_asset_id(create_response)
        assert asset_id is not None

        pre_publish = client.get(
            f"/asset-registry/assets/{asset_id}?stage=published",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert pre_publish.status_code == 404

        publish_response = client.post(
            f"/asset-registry/assets/{asset_id}/publish",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"published_by": "stage-test"},
        )
        assert publish_response.status_code in [200, 201]

        post_publish = client.get(
            f"/asset-registry/assets/{asset_id}?stage=published",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert post_publish.status_code == 200
    
    def test_token_in_authorization_header(self, client, auth_token):
        """Verify that token is correctly sent in Authorization header."""
        # This test verifies the format expected by the backend

        # Valid Bearer token format
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Should return 200 if token is valid
        assert response.status_code == 200

        # Invalid format should fail
        response_invalid = client.get(
            "/auth/me",
            headers={"Authorization": f"Token {auth_token}"},  # Wrong prefix
        )

        assert response_invalid.status_code == 401

        # Missing Bearer prefix should fail
        response_no_bearer = client.get(
            "/auth/me",
            headers={"Authorization": auth_token},
        )

        assert response_no_bearer.status_code == 401
