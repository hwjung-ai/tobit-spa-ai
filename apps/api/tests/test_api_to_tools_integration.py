"""Test API Manager ↔ Tools Integration"""

import uuid

import pytest
from app.modules.asset_registry.models import TbAssetRegistry
from fastapi.testclient import TestClient
from models.api_definition import ApiDefinition, ApiMode
from sqlmodel import Session


# Fixtures
@pytest.fixture
def test_api(db_session: Session, current_user_id: str):
    """Create a test API."""
    api = ApiDefinition(
        id=uuid.uuid4(),
        name="Test Equipment API",
        description="Test API for integration",
        tenant_id="t1",
        created_by=current_user_id,
        mode=ApiMode.sql,
        method="POST",
        path="/test/equipment",
        logic={"sql": "SELECT * FROM equipment LIMIT 10"},
        param_schema={
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "description": "Equipment ID"}
            },
            "required": []
        }
    )
    db_session.add(api)
    db_session.commit()
    db_session.refresh(api)
    return api


class TestExportToTools:
    """Test API Manager export to Tools functionality."""
    
    def test_export_api_to_tools(self, client: TestClient, test_api: ApiDefinition):
        """Test exporting API to Tools."""
        response = client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["export_status"] == "ready"
        assert "import_url" in data["data"]
    
    def test_export_options(self, client: TestClient, test_api: ApiDefinition):
        """Test getting export options."""
        response = client.get(f"/api-manager/apis/{test_api.id}/export-options")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["can_export_to_tools"] is True
    
    def test_cancel_export(self, client: TestClient, test_api: ApiDefinition):
        """Test canceling export."""
        # First export
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        
        # Then cancel
        response = client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": false}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"]["export_status"] == "cancelled"


class TestAvailableExports:
    """Test getting available API exports."""
    
    def test_list_available_exports(self, client: TestClient, test_api: ApiDefinition):
        """Test listing available API exports."""
        # Export API first
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        
        # List exports
        response = client.get("/asset-registry/tools/available-api-exports")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 0
        assert "exports" in data["data"]
        
        exports = data["data"]["exports"]
        assert len(exports) >= 1
        
        # Find our test API
        export = next((e for e in exports if e["api_id"] == str(test_api.id)), None)
        assert export is not None
        assert export["api_name"] == "Test Equipment API"
        assert export["is_imported"] is False
    
    def test_empty_exports_list(self, client: TestClient):
        """Test exports list when no APIs are exported."""
        response = client.get("/asset-registry/tools/available-api-exports")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["total"] == 0
        assert data["data"]["exports"] == []


class TestImportFromApiManager:
    """Test importing API as Tool."""
    
    def test_import_api_as_tool(self, client: TestClient, test_api: ApiDefinition):
        """Test importing API as Tool."""
        # Export API first
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        
        # Import as Tool
        response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}",
            json={
                "name": "Tool: Test Equipment",
                "description": "Custom description",
                "infer_output_schema": False
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 0
        assert "tool_id" in data["data"]
        assert data["data"]["status"] == "imported"
        
        # Check linked_from_api info
        asset = data["data"]["asset"]
        assert "linked_from_api" in asset
        assert asset["linked_from_api"]["is_internal_api"] is True
        assert asset["linked_from_api"]["api_name"] == "Test Equipment API"
    
    def test_import_with_inferred_schema(self, client: TestClient, test_api: ApiDefinition):
        """Test importing with output schema inference."""
        # Export API
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        
        # Import with schema inference
        response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}",
            json={"infer_output_schema": True}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Tool should have output_schema
        assert data["data"]["asset"]["tool_output_schema"] is not None
    
    def test_import_twice_fails(self, client: TestClient, test_api: ApiDefinition):
        """Test importing same API twice fails."""
        # Export and import once
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        
        # Try to import again
        response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        assert response.status_code == 400  # Bad Request


class TestBidirectionalLinkage:
    """Test bidirectional linkage between API and Tool."""
    
    def test_api_has_tool_link(self, client: TestClient, test_api: ApiDefinition, db_session: Session):
        """Test API has tool linkage after import."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        import_response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        tool_id = import_response.json()["data"]["tool_id"]
        
        # Refresh API and check linkage
        db_session.refresh(test_api)
        assert test_api.linked_to_tool_id == uuid.UUID(tool_id)
        assert test_api.linked_to_tool_name is not None
        assert test_api.linked_at is not None
    
    def test_tool_has_api_link(self, client: TestClient, test_api: ApiDefinition, db_session: Session):
        """Test Tool has API linkage."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        import_response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        tool_id = uuid.UUID(import_response.json()["data"]["tool_id"])
        
        # Get Tool
        tool = db_session.get(TbAssetRegistry, tool_id)
        assert tool is not None
        assert tool.linked_from_api_id == test_api.id
        assert tool.linked_from_api_name == "Test Equipment API"
        assert tool.import_mode == "api_to_tool"
        assert tool.linked_from_api_at is not None
    
    def test_unlink_from_api(self, client: TestClient, test_api: ApiDefinition, db_session: Session):
        """Test unlinking from API side."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        
        # Unlink
        response = client.post(f"/api-manager/apis/{test_api.id}/unlink-from-tool")
        assert response.status_code == 200
        
        # Check API linkage is cleared
        db_session.refresh(test_api)
        assert test_api.linked_to_tool_id is None


class TestSyncFromApi:
    """Test syncing Tool with API changes."""
    
    def test_sync_tool_from_api(self, client: TestClient, test_api: ApiDefinition, db_session: Session):
        """Test syncing Tool with API changes."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        import_response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        tool_id = import_response.json()["data"]["tool_id"]
        
        # Modify API
        test_api.param_schema = {
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "description": "Equipment ID"},
                "status": {"type": "string", "description": "Status filter"}
            },
            "required": ["equipment_id"]
        }
        db_session.add(test_api)
        db_session.commit()
        
        # Sync
        response = client.post(f"/asset-registry/tools/{tool_id}/sync-from-api")
        assert response.status_code == 200
        
        data = response.json()
        assert data["code"] == 0
        assert "synced_at" in data["data"]
        
        # Check Tool was updated
        tool = db_session.get(TbAssetRegistry, uuid.UUID(tool_id))
        assert tool.last_synced_at is not None
        assert tool.tool_input_schema["properties"]["status"] is not None
    
    def test_sync_only_draft_tools(self, client: TestClient, test_api: ApiDefinition, db_session: Session):
        """Test only draft tools can be synced."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        import_response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        tool_id = import_response.json()["data"]["tool_id"]
        
        # Publish the tool
        tool = db_session.get(TbAssetRegistry, uuid.UUID(tool_id))
        tool.status = "published"
        db_session.add(tool)
        db_session.commit()
        
        # Try to sync - should fail
        response = client.post(f"/asset-registry/tools/{tool_id}/sync-from-api")
        assert response.status_code == 400  # Bad Request


class TestIsInternalApiFlag:
    """Test is_internal_api flag for identifying linked tools."""
    
    def test_internal_api_flag_in_list(self, client: TestClient, test_api: ApiDefinition):
        """Test internal API flag in tools list."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        
        # List tools
        response = client.get("/asset-registry/tools")
        assert response.status_code == 200
        
        data = response.json()
        assets = data["data"]["assets"]
        
        # Find imported tool
        imported_tool = next(
            (a for a in assets if a.get("linked_from_api") is not None),
            None
        )
        assert imported_tool is not None
        assert imported_tool["linked_from_api"]["is_internal_api"] is True
    
    def test_internal_api_flag_in_detail(self, client: TestClient, test_api: ApiDefinition):
        """Test internal API flag in tool detail."""
        # Export and import
        client.post(
            f"/api-manager/apis/{test_api.id}/export-to-tools",
            json={"export": true}
        )
        import_response = client.post(
            f"/asset-registry/tools/import-from-api-manager/{test_api.id}"
        )
        tool_id = import_response.json()["data"]["tool_id"]
        
        # Get tool detail
        response = client.get(f"/asset-registry/tools/{tool_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "linked_from_api" in data["data"]["asset"]
        assert data["data"]["asset"]["linked_from_api"]["is_internal_api"] is True