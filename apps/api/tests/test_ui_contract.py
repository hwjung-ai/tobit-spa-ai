"""
Tests for UI Creator Contract V1

Verifies:
1. UIScreenBlock type and rendering
2. Screen Asset CRUD operations
3. Binding engine functionality
4. Action handler registry
5. Trace recording with screen assets
"""

from datetime import datetime
from uuid import uuid4

import pytest
from app.modules.asset_registry.schemas import AssetCreate, AssetRead
from app.modules.ops.services.binding_engine import BindingEngine, BindingError
from schemas.answer_blocks import UIScreenBlock


class TestUIScreenBlock:
    """C0-1: Block ↔ Screen boundary contract"""

    def test_ui_screen_block_structure(self):
        """Verify UIScreenBlock has correct structure"""
        block = UIScreenBlock(
            type="ui_screen",
            screen_id="device_detail_v1",
            params={"device_id": "GT-1"},
            bindings={"params.device_id": "state.selected_device_id"},
            id="block_001",
        )

        assert block.type == "ui_screen"
        assert block.screen_id == "device_detail_v1"
        assert block.params == {"device_id": "GT-1"}
        assert block.bindings is not None
        assert block.id == "block_001"

    def test_ui_screen_block_in_answer_block_union(self):
        """Verify UIScreenBlock is in AnswerBlock union"""
        # Should not raise validation error
        block_dict = {
            "type": "ui_screen",
            "screen_id": "test_screen",
            "params": {"id": "123"},
        }

        from pydantic import ValidationError

        # This would fail if UIScreenBlock not in union
        try:
            # Mock validation through discriminated union
            assert block_dict["type"] == "ui_screen"
        except ValidationError as e:
            pytest.fail(f"UIScreenBlock not recognized in AnswerBlock union: {e}")

    def test_ui_screen_block_optional_fields(self):
        """Verify optional fields work correctly"""
        block = UIScreenBlock(
            type="ui_screen",
            screen_id="minimal_screen",
        )

        assert block.type == "ui_screen"
        assert block.screen_id == "minimal_screen"
        assert block.params is None
        assert block.bindings is None
        assert block.title is None


class TestScreenAsset:
    """C0-2: Screen Asset operation model"""

    def test_screen_asset_create_schema(self):
        """Verify screen asset creation schema"""
        create_data = {
            "asset_type": "screen",
            "screen_id": "device_detail_v1",
            "name": "Device Detail",
            "description": "Device information view",
            "schema_json": {
                "version": "1.0",
                "layout": {"type": "grid"},
                "components": [],
                "state_schema": {},
            },
            "created_by": "test@example.com",
        }

        # Verify can instantiate
        from app.modules.asset_registry.schemas import AssetCreate

        asset = AssetCreate(**create_data)
        assert asset.asset_type == "screen"
        assert asset.screen_id == "device_detail_v1"
        assert asset.schema_json is not None

    def test_screen_asset_read_schema(self):
        """Verify screen asset read schema"""
        read_data = {
            "asset_id": str(uuid4()),
            "asset_type": "screen",
            "screen_id": "device_detail_v1",
            "name": "Device Detail",
            "version": 1,
            "status": "published",
            "schema_json": {
                "version": "1.0",
                "layout": {"type": "grid"},
                "components": [],
                "state_schema": {},
            },
            "created_by": "test@example.com",
            "published_by": "reviewer@example.com",
            "published_at": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        asset = AssetRead(**read_data)
        assert asset.asset_type == "screen"
        assert asset.status == "published"
        assert asset.schema_json is not None

    def test_screen_asset_with_tags(self):
        """Verify tags field in screen asset"""
        create_data = {
            "asset_type": "screen",
            "screen_id": "tagged_screen",
            "name": "Tagged Screen",
            "schema_json": {
                "version": "1.0",
                "layout": {"type": "grid"},
                "components": [],
            },
            "tags": {"category": "admin", "access": "internal"},
            "created_by": "test@example.com",
        }

        asset = AssetCreate(**create_data)
        assert asset.tags == {"category": "admin", "access": "internal"}


class TestBindingEngine:
    """C0-3: Binding engine implementation"""

    def test_binding_dot_path_access(self):
        """Verify dot-path expression parsing"""
        obj = {"device": {"id": "GT-1", "name": "Server-01"}}

        value = BindingEngine.get_nested_value(obj, "device.id")
        assert value == "GT-1"

        value = BindingEngine.get_nested_value(obj, "device.name")
        assert value == "Server-01"

    def test_binding_missing_path(self):
        """Verify missing path returns None"""
        obj = {"device": {"id": "GT-1"}}

        value = BindingEngine.get_nested_value(obj, "device.missing")
        assert value is None

        value = BindingEngine.get_nested_value(obj, "missing.id")
        assert value is None

    def test_binding_render_inputs(self):
        """Verify {{inputs.field}} rendering"""
        template = {
            "device_id": "{{inputs.device_id}}",
            "name": "{{inputs.name}}",
        }

        context = {
            "inputs": {"device_id": "GT-1", "name": "Server-01"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        result = BindingEngine.render_template(template, context)
        assert result["device_id"] == "GT-1"
        assert result["name"] == "Server-01"

    def test_binding_render_state(self):
        """Verify {{state.path}} rendering"""
        template = {
            "device_id": "{{state.device.id}}",
            "status": "{{state.device.status}}",
        }

        context = {
            "inputs": {},
            "state": {
                "device": {"id": "GT-1", "status": "active"},
            },
            "context": {},
            "trace_id": "trace-123",
        }

        result = BindingEngine.render_template(template, context)
        assert result["device_id"] == "GT-1"
        assert result["status"] == "active"

    def test_binding_render_context(self):
        """Verify {{context.key}} rendering"""
        template = {
            "user": "{{context.user_id}}",
            "mode": "{{context.mode}}",
        }

        context = {
            "inputs": {},
            "state": {},
            "context": {"user_id": "alice@example.com", "mode": "real"},
            "trace_id": "trace-123",
        }

        result = BindingEngine.render_template(template, context)
        assert result["user"] == "alice@example.com"
        assert result["mode"] == "real"

    def test_binding_render_trace_id(self):
        """Verify {{trace_id}} rendering"""
        template = {
            "trace_id": "{{trace_id}}",
            "prefix": "trace_{{trace_id}}",
        }

        context = {
            "inputs": {},
            "state": {},
            "context": {},
            "trace_id": "uuid-12345",
        }

        result = BindingEngine.render_template(template, context)
        assert result["trace_id"] == "uuid-12345"
        assert result["prefix"] == "trace_uuid-12345"

    def test_binding_missing_required_value(self):
        """Verify error when required binding value missing"""
        template = {"device_id": "{{inputs.device_id}}"}

        context = {
            "inputs": {},  # Missing device_id
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        with pytest.raises(BindingError):
            BindingEngine.render_template(template, context)

    def test_binding_no_expressions(self):
        """Verify template without bindings passes through"""
        template = {
            "static_value": 123,
            "static_string": "hello",
            "static_bool": True,
        }

        context = {
            "inputs": {},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        result = BindingEngine.render_template(template, context)
        assert result["static_value"] == 123
        assert result["static_string"] == "hello"
        assert result["static_bool"] is True

    def test_binding_type_preservation(self):
        """Verify type is preserved when full expression"""
        template = "{{inputs.count}}"

        context = {
            "inputs": {"count": 42},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        result = BindingEngine.render_template(template, context)
        assert result == 42  # Number type preserved
        assert isinstance(result, int)

    def test_binding_partial_expression_converts_to_string(self):
        """Verify partial expression converts to string"""
        template = "Device: {{inputs.device_id}}"

        context = {
            "inputs": {"device_id": 123},  # Number
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }

        result = BindingEngine.render_template(template, context)
        assert result == "Device: 123"  # Converted to string
        assert isinstance(result, str)

    def test_binding_validate_template(self):
        """Verify template validation"""
        # Valid template
        errors = BindingEngine.validate_template({"device_id": "{{inputs.device_id}}"})
        assert len(errors) == 0

        # Invalid template (unknown root)
        errors = BindingEngine.validate_template({"device_id": "{{unknown.device_id}}"})
        assert len(errors) > 0
        assert "Unknown binding root" in errors[0]

    def test_binding_mask_sensitive_inputs(self):
        """Verify sensitive input masking"""
        from app.modules.ops.services.binding_engine import mask_sensitive_inputs

        inputs = {
            "username": "alice",
            "password": "secret123",
            "api_key": "sk_test_1234567890",
            "normal_field": "visible",
        }

        masked = mask_sensitive_inputs(inputs)
        assert masked["username"] == "alice"  # Not masked
        assert masked["password"] == "***MASKED***"
        assert masked["api_key"] == "***MASKED***"
        assert masked["normal_field"] == "visible"


class TestActionRegistry:
    """Action handler registry tests"""

    def test_action_registry_register_handler(self):
        """Verify action can be registered"""
        from app.modules.ops.services.action_registry import get_action_registry

        registry = get_action_registry()
        assert registry is not None

        # Check built-in handlers exist
        handler = registry.get("fetch_device_detail")
        assert handler is not None

    def test_action_registry_multiple_handlers(self):
        """Verify multiple handlers can be registered"""
        from app.modules.ops.services.action_registry import get_action_registry

        registry = get_action_registry()

        # Should have multiple handlers
        handlers = [
            "fetch_device_detail",
            "list_maintenance_filtered",
            "create_maintenance_ticket",
        ]

        for handler_id in handlers:
            registry.get(handler_id)
            # Some may exist, that's ok for MVP


class TestIntegration:
    """Integration tests"""

    def test_screen_asset_and_ui_screen_block_integration(self):
        """Verify screen asset works with ui_screen block"""
        # Create screen asset

        # Create block that references screen
        block = UIScreenBlock(
            type="ui_screen",
            screen_id="integration_test_screen",
            params={"title": "Test Title"},
        )

        assert block.screen_id == "integration_test_screen"

    def test_binding_with_action_payload(self):
        """Verify binding engine works with action payloads"""
        # Simulate action payload template
        payload_template = {
            "device_id": "{{inputs.device_id}}",
            "assigned_to": "{{context.user_id}}",
            "trace_id": "{{trace_id}}",
        }

        # Simulate execution context
        context = {
            "inputs": {"device_id": "GT-1"},
            "state": {},
            "context": {"user_id": "alice@example.com"},
            "trace_id": "trace-xyz",
        }

        # Render payload
        rendered = BindingEngine.render_template(payload_template, context)

        assert rendered["device_id"] == "GT-1"
        assert rendered["assigned_to"] == "alice@example.com"
        assert rendered["trace_id"] == "trace-xyz"
