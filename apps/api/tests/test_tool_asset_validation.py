"""
BLOCKER-3: Tool Asset Validation Tests

Tests to verify that Tool Asset definitions are validated for
completeness, security, and correctness.
"""

from unittest.mock import MagicMock

import pytest
from app.modules.asset_registry.tool_validator import (
    validate_tool_asset,
    validate_tool_for_publication,
)


def create_mock_asset(
    tool_type: str = "database_query",
    name: str = "test_tool",
    description: str = "Test description",
    tool_config: dict | None = None,
    input_schema: dict | None = None,
    output_schema: dict | None = None,
    tags: dict | None = None,
) -> MagicMock:
    """Create a mock Tool Asset for testing."""
    asset = MagicMock()
    asset.tool_type = tool_type
    asset.name = name
    asset.description = description
    asset.tool_config = tool_config or {}
    asset.tool_input_schema = input_schema
    asset.tool_output_schema = output_schema
    asset.tags = tags
    return asset


class TestToolAssetValidation:
    """Test suite for Tool Asset validation."""

    def test_missing_tool_type_detected(self):
        """Tool type is required."""
        asset = create_mock_asset(tool_type=None)
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "tool_type is required" in str(errors)

    def test_empty_tool_type_detected(self):
        """Empty tool type is invalid."""
        asset = create_mock_asset(tool_type="")
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "tool_type is required" in str(errors)

    def test_database_query_missing_source_ref(self):
        """database_query must have source_ref."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={},  # Missing source_ref
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "source_ref is required" in str(errors)

    def test_database_query_missing_query_template(self):
        """database_query must have query_template."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={"source_ref": "default_postgres"},  # Missing query_template
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "query_template is required" in str(errors)

    def test_database_query_dangerous_sql_keyword_drop(self):
        """Detect DROP keyword in SQL query."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "DROP TABLE users;",
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "DROP" in str(errors)

    def test_database_query_dangerous_sql_keyword_delete(self):
        """Detect DELETE keyword in SQL query."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "DELETE FROM users WHERE id = $1;",
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "DELETE" in str(errors)

    def test_database_query_dangerous_sql_keyword_truncate(self):
        """Detect TRUNCATE keyword in SQL query."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "TRUNCATE TABLE users;",
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "TRUNCATE" in str(errors)

    def test_database_query_safe_select(self):
        """SELECT queries are safe."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "SELECT * FROM users WHERE id = $1;",
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) == 0

    def test_database_query_allowed_in_template_variable(self):
        """DROP/DELETE in template variables like {DROP_IF_EXISTS} is allowed."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "{DROP_IF_EXISTS} SELECT * FROM {TABLE_NAME};",
            },
        )
        errors = validate_tool_asset(asset)
        # Should not report error because it's in a template variable
        dangerous_errors = [e for e in errors if "DROP" in e]
        assert len(dangerous_errors) == 0

    def test_http_api_missing_url(self):
        """http_api must have URL."""
        asset = create_mock_asset(
            tool_type="http_api",
            tool_config={},  # Missing url
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "url is required" in str(errors)

    def test_http_api_invalid_url_format(self):
        """http_api URL must be valid format."""
        asset = create_mock_asset(
            tool_type="http_api",
            tool_config={
                "url": "not_a_valid_url",  # Invalid format
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "Invalid URL format" in str(errors)

    def test_http_api_valid_urls(self):
        """http_api accepts various valid URL formats."""
        valid_urls = [
            "https://api.example.com/endpoint",
            "http://localhost:8000/api",
            "/api/internal/endpoint",
        ]

        for url in valid_urls:
            asset = create_mock_asset(
                tool_type="http_api",
                tool_config={"url": url},
            )
            errors = validate_tool_asset(asset)
            # Only check for URL-related errors
            url_errors = [e for e in errors if "URL" in e]
            assert len(url_errors) == 0, f"Valid URL {url} should not cause errors"

    def test_http_api_invalid_method(self):
        """http_api must have valid HTTP method."""
        asset = create_mock_asset(
            tool_type="http_api",
            tool_config={
                "url": "https://api.example.com",
                "method": "INVALID",  # Invalid method
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "Invalid HTTP method" in str(errors)

    def test_http_api_valid_methods(self):
        """http_api accepts standard HTTP methods."""
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        for method in valid_methods:
            asset = create_mock_asset(
                tool_type="http_api",
                tool_config={
                    "url": "https://api.example.com",
                    "method": method,
                },
            )
            errors = validate_tool_asset(asset)
            # Only check for method-related errors
            method_errors = [e for e in errors if "method" in e.lower()]
            assert len(method_errors) == 0, f"Valid method {method} should not cause errors"

    def test_graph_query_missing_source_ref(self):
        """graph_query must have source_ref."""
        asset = create_mock_asset(
            tool_type="graph_query",
            tool_config={},
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "source_ref is required" in str(errors)

    def test_graph_query_missing_query_template(self):
        """graph_query must have query_template."""
        asset = create_mock_asset(
            tool_type="graph_query",
            tool_config={"source_ref": "neo4j"},
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "query_template is required" in str(errors)

    def test_mcp_missing_server_ref(self):
        """MCP tool must have mcp_server_ref."""
        asset = create_mock_asset(
            tool_type="mcp",
            tool_config={},
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "mcp_server_ref is required" in str(errors)

    def test_mcp_missing_tool_name(self):
        """MCP tool must have tool_name."""
        asset = create_mock_asset(
            tool_type="mcp",
            tool_config={"mcp_server_ref": "local"},
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "tool_name is required" in str(errors)

    def test_empty_tool_name(self):
        """Tool name cannot be empty."""
        asset = create_mock_asset(name="")
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "name cannot be empty" in str(errors)

    def test_whitespace_only_tool_name(self):
        """Tool name cannot be whitespace only."""
        asset = create_mock_asset(name="   ")
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "name cannot be empty" in str(errors)

    def test_input_schema_validation(self):
        """Input schema should be valid."""
        # Invalid schema (not a dict)
        asset = create_mock_asset(
            input_schema="not_a_dict"  # Invalid
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "input_schema must be a dict" in str(errors)

    def test_valid_json_schema(self):
        """Valid JSON Schema should pass."""
        asset = create_mock_asset(
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "query": {"type": "string"},
                },
            }
        )
        errors = validate_tool_asset(asset)
        # Should not have schema errors
        schema_errors = [e for e in errors if "schema" in e.lower()]
        assert len(schema_errors) == 0

    def test_publication_requires_description(self):
        """Tool must have description for publication."""
        asset = create_mock_asset(description="")
        errors = validate_tool_for_publication(asset)
        assert len(errors) > 0
        assert "description is required" in str(errors)

    def test_publication_requires_tags(self):
        """Tool should have tags with 'source' for publication."""
        asset = create_mock_asset(tags=None)
        errors = validate_tool_for_publication(asset)
        assert len(errors) > 0
        assert "tags" in str(errors)

    def test_complete_tool_publication_valid(self):
        """Complete tool with all required fields is valid for publication."""
        asset = create_mock_asset(
            tool_type="database_query",
            name="valid_tool",
            description="Complete tool for testing",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "SELECT * FROM users WHERE id = $1;",
            },
            input_schema={
                "type": "object",
                "properties": {"user_id": {"type": "integer"}},
            },
            tags={"source": "default"},
        )
        errors = validate_tool_for_publication(asset)
        assert len(errors) == 0


class TestToolAssetValidationEdgeCases:
    """Test edge cases in Tool Asset validation."""

    def test_tool_type_case_insensitive(self):
        """Tool type should be case-insensitive."""
        asset = create_mock_asset(
            tool_type="DATABASE_QUERY",  # Uppercase
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "SELECT 1;",
            },
        )
        errors = validate_tool_asset(asset)
        # Should be treated as database_query
        db_errors = [e for e in errors if "source_ref" in e or "query_template" in e]
        assert len(db_errors) == 0

    def test_sql_keyword_case_insensitive(self):
        """SQL keywords should be detected case-insensitively."""
        asset = create_mock_asset(
            tool_type="database_query",
            tool_config={
                "source_ref": "default_postgres",
                "query_template": "drop table users;",  # Lowercase
            },
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0
        assert "DROP" in str(errors) or "drop" in str(errors)

    def test_none_config_values(self):
        """None values in tool_config should be handled gracefully."""
        asset = create_mock_asset(
            tool_type="http_api",
            tool_config=None,
        )
        errors = validate_tool_asset(asset)
        assert len(errors) > 0  # Should have url error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
