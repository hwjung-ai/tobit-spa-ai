"""
Unit tests for BindingEngine - Template substitution and variable binding.

Tests cover:
- Simple template rendering
- Nested path access
- trace_id special handling
- Sensitive data masking
- Error handling
"""

import pytest
from app.modules.ops.services.binding_engine import (
    BindingEngine,
    BindingError,
    mask_sensitive_inputs,
)


class TestBindingEngineSimpleRendering:
    """Test simple template rendering with basic bindings."""

    def test_render_simple_string_with_inputs(self):
        """Test rendering simple string with inputs.field binding."""
        template = "Device: {{inputs.device_id}}"
        context = {
            "inputs": {"device_id": "srv-erp-01"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Device: srv-erp-01"

    def test_render_simple_string_with_state(self):
        """Test rendering simple string with state.field binding."""
        template = "Status: {{state.status}}"
        context = {
            "inputs": {},
            "state": {"status": "healthy"},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Status: healthy"

    def test_render_simple_string_with_context(self):
        """Test rendering simple string with context.field binding."""
        template = "Mode: {{context.mode}}"
        context = {
            "inputs": {},
            "state": {},
            "context": {"mode": "production"},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Mode: production"

    def test_render_trace_id_special(self):
        """Test rendering special trace_id binding."""
        template = "Trace: {{trace_id}}"
        context = {
            "inputs": {},
            "state": {},
            "context": {},
            "trace_id": "trace-abc-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Trace: trace-abc-123"

    def test_render_entire_string_preserves_type(self):
        """Test that single {{expr}} returns value as-is (type preserved)."""
        template = "{{inputs.count}}"
        context = {
            "inputs": {"count": 42},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == 42
        assert isinstance(result, int)

    def test_render_entire_string_with_boolean(self):
        """Test that single {{expr}} preserves boolean type."""
        template = "{{inputs.enabled}}"
        context = {
            "inputs": {"enabled": True},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result is True

    def test_render_with_explicit_none_value(self):
        """Test rendering with explicit None value in bindings raises error."""
        template = "Value: {{inputs.missing}}"
        context = {
            "inputs": {"missing": None},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        # Missing values raise BindingError
        with pytest.raises(BindingError):
            BindingEngine.render_template(template, context)


class TestBindingEngineNestedPath:
    """Test nested path access with dot notation."""

    def test_render_nested_single_level(self):
        """Test accessing nested object with single level."""
        template = "Zone: {{state.network.zone}}"
        context = {
            "inputs": {},
            "state": {"network": {"zone": "us-east-1"}},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Zone: us-east-1"

    def test_render_nested_multiple_levels(self):
        """Test accessing deeply nested object."""
        template = "Location: {{inputs.database.connection.host}}"
        context = {
            "inputs": {
                "database": {
                    "connection": {
                        "host": "db.example.com",
                        "port": 5432,
                    }
                }
            },
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Location: db.example.com"

    def test_render_nested_path_returns_as_is_when_whole(self):
        """Test that entire nested object is returned as-is when it's the whole template."""
        template = "{{state.config}}"
        context = {
            "inputs": {},
            "state": {"config": {"version": 2, "enabled": True}},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == {"version": 2, "enabled": True}

    def test_get_nested_value_from_path(self):
        """Test get_nested_value static method."""
        obj = {"user": {"profile": {"email": "test@example.com"}}}
        value = BindingEngine.get_nested_value(obj, "user.profile.email")
        assert value == "test@example.com"

    def test_get_nested_value_missing_path(self):
        """Test get_nested_value returns None for missing path."""
        obj = {"user": {"profile": {}}}
        value = BindingEngine.get_nested_value(obj, "user.profile.email")
        assert value is None

    def test_get_nested_value_null_intermediate(self):
        """Test get_nested_value returns None when intermediate is None."""
        obj = {"user": None}
        value = BindingEngine.get_nested_value(obj, "user.profile.email")
        assert value is None

    def test_set_nested_value_creates_path(self):
        """Test set_nested_value creates nested structure."""
        obj = {}
        BindingEngine.set_nested_value(obj, "a.b.c", 42)
        assert obj == {"a": {"b": {"c": 42}}}

    def test_set_nested_value_overwrites_existing(self):
        """Test set_nested_value overwrites existing value."""
        obj = {"a": {"b": {"c": 10}}}
        BindingEngine.set_nested_value(obj, "a.b.c", 42)
        assert obj["a"]["b"]["c"] == 42


class TestBindingEngineArrayAccess:
    """Test that array indexing is not allowed (MVP)."""

    def test_array_in_context_returns_as_is(self):
        """Test that arrays in context are returned but not indexed."""
        obj = {"items": [{"id": 1}]}
        # get_nested_value returns the array as-is
        result = BindingEngine.get_nested_value(obj, "items")
        assert result == [{"id": 1}]

    def test_array_indexing_not_supported_in_path(self):
        """Test that array indexing in path is not supported."""
        obj = {"items": [{"id": 1}]}
        # Trying to access array element with dot notation raises error
        with pytest.raises(BindingError, match="Array indexing not supported"):
            BindingEngine.get_nested_value(obj, "items.id")


class TestBindingEngineDictRendering:
    """Test rendering complex dict structures."""

    def test_render_dict_with_multiple_bindings(self):
        """Test rendering dict with multiple binding expressions."""
        template = {
            "device_id": "{{inputs.device_id}}",
            "status": "{{state.status}}",
            "mode": "{{context.mode}}",
        }
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {"status": "running"},
            "context": {"mode": "real"},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == {
            "device_id": "srv-01",
            "status": "running",
            "mode": "real",
        }

    def test_render_dict_with_nested_dict(self):
        """Test rendering dict with nested structure."""
        template = {
            "device": {
                "id": "{{inputs.device_id}}",
                "config": {
                    "enabled": "{{inputs.enabled}}",
                    "timeout": 30,
                },
            }
        }
        context = {
            "inputs": {"device_id": "dev-1", "enabled": True},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == {
            "device": {
                "id": "dev-1",
                "config": {
                    "enabled": True,
                    "timeout": 30,
                },
            }
        }

    def test_render_dict_with_list(self):
        """Test rendering dict with list containing bindings."""
        template = {
            "items": [
                "{{inputs.item1}}",
                "static_value",
                "{{inputs.item2}}",
            ]
        }
        context = {
            "inputs": {"item1": "value1", "item2": "value2"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == {
            "items": ["value1", "static_value", "value2"]
        }

    def test_render_list_of_dicts(self):
        """Test rendering list of dicts with bindings."""
        template = [
            {"id": "{{inputs.id1}}", "name": "Item 1"},
            {"id": "{{inputs.id2}}", "name": "Item 2"},
        ]
        context = {
            "inputs": {"id1": "a", "id2": "b"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == [
            {"id": "a", "name": "Item 1"},
            {"id": "b", "name": "Item 2"},
        ]


class TestBindingEngineErrorHandling:
    """Test error handling for invalid expressions."""

    def test_missing_trace_id(self):
        """Test error when trace_id is required but missing."""
        template = "Trace: {{trace_id}}"
        context = {
            "inputs": {},
            "state": {},
            "context": {},
            "trace_id": None,
        }
        with pytest.raises(BindingError, match="trace_id not found"):
            BindingEngine.render_template(template, context)

    def test_unknown_variable(self):
        """Test error for unknown variable root."""
        template = "Value: {{unknown.field}}"
        context = {
            "inputs": {},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        with pytest.raises(BindingError, match="Unknown variable"):
            BindingEngine.render_template(template, context)

    def test_missing_required_field(self):
        """Test error when required field is missing."""
        template = "Device: {{inputs.device_id}}"
        context = {
            "inputs": {},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        with pytest.raises(BindingError, match="Value not found"):
            BindingEngine.render_template(template, context)

    def test_set_nested_value_overwrites_non_dict(self):
        """Test set_nested_value with existing non-dict value."""
        obj = {"a": "string_value"}
        # This will cause an error when trying to set nested value
        with pytest.raises(BindingError, match="Cannot navigate through non-dict"):
            BindingEngine.set_nested_value(obj, "a.b.c", 10)


class TestBindingEngineValidation:
    """Test template validation."""

    def test_validate_valid_template(self):
        """Test validation passes for valid template."""
        template = {
            "device": "{{inputs.device_id}}",
            "status": "{{state.status}}",
        }
        errors = BindingEngine.validate_template(template)
        assert len(errors) == 0

    def test_validate_unknown_binding_root(self):
        """Test validation catches unknown binding root."""
        template = "Device: {{unknown.field}}"
        errors = BindingEngine.validate_template(template)
        assert len(errors) == 1
        assert "Unknown binding root" in errors[0]

    def test_validate_multiple_errors(self):
        """Test validation finds multiple errors."""
        template = "{{unknown1.field}} and {{unknown2.field}}"
        errors = BindingEngine.validate_template(template)
        assert len(errors) == 2

    def test_validate_trace_id(self):
        """Test validation accepts trace_id."""
        template = "Trace: {{trace_id}}"
        errors = BindingEngine.validate_template(template)
        assert len(errors) == 0

    def test_validate_context_keyword(self):
        """Test validation accepts context (not confused with dict key)."""
        template = "Mode: {{context.mode}}"
        errors = BindingEngine.validate_template(template)
        assert len(errors) == 0


class TestBindingEngineMultipleBindings:
    """Test string with multiple bindings."""

    def test_multiple_bindings_in_string(self):
        """Test string with multiple binding expressions."""
        template = "Device {{inputs.device_id}} has status {{state.status}}"
        context = {
            "inputs": {"device_id": "srv-01"},
            "state": {"status": "healthy"},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "Device srv-01 has status healthy"

    def test_multiple_bindings_same_variable(self):
        """Test multiple bindings of same variable."""
        template = "ID: {{inputs.id}}, Name: {{inputs.id}}"
        context = {
            "inputs": {"id": "resource-1"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "ID: resource-1, Name: resource-1"

    def test_adjacent_bindings(self):
        """Test adjacent bindings without separator."""
        template = "{{inputs.first}}-{{inputs.last}}"
        context = {
            "inputs": {"first": "abc", "last": "xyz"},
            "state": {},
            "context": {},
            "trace_id": "trace-123",
        }
        result = BindingEngine.render_template(template, context)
        assert result == "abc-xyz"


class TestMaskSensitiveInputs:
    """Test sensitive data masking."""

    def test_mask_password_field(self):
        """Test masking of password field."""
        inputs = {"password": "secret123"}
        result = mask_sensitive_inputs(inputs)
        assert result["password"] == "***MASKED***"

    def test_mask_api_key_field(self):
        """Test masking of api_key field."""
        inputs = {"api_key": "sk-abc123def456"}
        result = mask_sensitive_inputs(inputs)
        assert result["api_key"] == "***MASKED***"

    def test_mask_multiple_sensitive_fields(self):
        """Test masking multiple sensitive fields."""
        inputs = {
            "password": "pass",
            "api_key": "key",
            "credit_card": "4111111111111111",
            "normal_field": "value",
        }
        result = mask_sensitive_inputs(inputs)
        assert result["password"] == "***MASKED***"
        assert result["api_key"] == "***MASKED***"
        assert result["credit_card"] == "***MASKED***"
        assert result["normal_field"] == "value"

    def test_mask_nested_sensitive_data(self):
        """Test masking nested sensitive data."""
        inputs = {
            "config": {
                "database": {
                    "password": "dbpass123"
                }
            }
        }
        result = mask_sensitive_inputs(inputs)
        # Nested password in dict is masked with first 3 and last 1 chars
        # "dbpass123" -> "dbp***3"
        assert "***" in result["config"]["database"]["password"]

    def test_mask_email_field(self):
        """Test masking of email field."""
        inputs = {"email": "user@example.com"}
        result = mask_sensitive_inputs(inputs)
        assert result["email"] == "***MASKED***"

    def test_mask_phone_field(self):
        """Test masking of phone field."""
        inputs = {"phone": "010-1234-5678"}
        result = mask_sensitive_inputs(inputs)
        assert result["phone"] == "***MASKED***"

    def test_mask_preserves_normal_fields(self):
        """Test that normal fields are preserved."""
        inputs = {
            "device_id": "srv-01",
            "user_id": "user-123",
            "status": "active",
        }
        result = mask_sensitive_inputs(inputs)
        assert result == inputs

    def test_mask_empty_inputs(self):
        """Test masking empty inputs."""
        inputs = {}
        result = mask_sensitive_inputs(inputs)
        assert result == {}

    def test_mask_none_inputs(self):
        """Test masking None inputs."""
        result = mask_sensitive_inputs(None)
        assert result is None

    def test_mask_case_insensitive(self):
        """Test masking is case insensitive."""
        inputs = {
            "PASSWORD": "secret",
            "Api_Key": "key",
            "CC_NUMBER": "4111111111111111",
        }
        result = mask_sensitive_inputs(inputs)
        assert result["PASSWORD"] == "***MASKED***"
        assert result["Api_Key"] == "***MASKED***"
        assert result["CC_NUMBER"] == "***MASKED***"

    def test_mask_preserves_short_values(self):
        """Test masking short sensitive values."""
        inputs = {"password": "123"}
        result = mask_sensitive_inputs(inputs)
        assert result["password"] == "***MASKED***"
