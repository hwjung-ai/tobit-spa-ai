"""Test Asset Registry functionality"""
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, '/home/spa/tobit-spa-ai')

from main import app

client = TestClient(app)


def test_create_prompt_asset():
    """Test creating a prompt asset"""
    payload = {
        "asset_type": "prompt",
        "name": "test_planner",
        "scope": "ci",
        "engine": "planner",
        "template": "You are a planner. Question: {{question}}",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"]
        },
        "output_contract": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "object",
                    "properties": {"steps": {"type": "array"}}
                }
            }
        },
        "created_by": "test_user"
    }
    
    response = client.post("/asset-registry/assets", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["asset"]["status"] == "draft"
    assert data["data"]["asset"]["name"] == "test_planner"
    
    return data["data"]["asset"]["asset_id"]


def test_publish_asset():
    """Test publishing an asset"""
    # Create first
    payload = {
        "asset_type": "prompt",
        "name": "test_publish",
        "scope": "ci",
        "engine": "planner",
        "template": "Test",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"]
        },
        "output_contract": {
            "type": "object",
            "properties": {"plan": {"type": "object", "properties": {"steps": {"type": "array"}}}}
        }
    }
    
    response = client.post("/asset-registry/assets", json=payload)
    assert response.status_code == 200
    asset_id = response.json()["data"]["asset"]["asset_id"]
    
    # Publish
    response = client.post(f"/asset-registry/assets/{asset_id}/publish", 
                          json={"published_by": "admin"})
    print(f"Publish status: {response.status_code}")
    print(f"Publish response: {response.json()}")
    
    assert response.status_code == 200
    asset = response.json()["data"]["asset"]
    assert asset["status"] == "published"
    assert asset["published_by"] == "admin"


def test_validation_error():
    """Test validation error for missing output_contract"""
    payload = {
        "asset_type": "prompt",
        "name": "invalid",
        "scope": "ci",
        "engine": "planner",
        "template": "Test",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"]
        }
        # missing output_contract
    }
    
    # Create - should fail validation
    response = client.post("/asset-registry/assets", json=payload)
    print(f"Validation error status: {response.status_code}")
    print(f"Validation response: {response.json()}")

    assert response.status_code == 422  # validation error


if __name__ == "__main__":
    print("=== Test 1: Create Prompt Asset ===")
    asset_id = test_create_prompt_asset()
    print(f"✓ Asset created: {asset_id}\n")
    
    print("=== Test 2: Publish Asset ===")
    test_publish_asset()
    print("✓ Asset published\n")
    
    print("=== Test 3: Validation Error ===")
    test_validation_error()
    print("✓ Validation error caught\n")
    
    print("✓✓✓ All tests passed!")
