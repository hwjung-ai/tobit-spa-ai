"""
Tool Asset Validation

This module provides validation for Tool Asset configuration to ensure
security, completeness, and correctness of tool definitions.

BLOCKER-3: Tool Asset 검증 추가
"""

from __future__ import annotations

import json
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class ToolAssetValidator:
    """
    Validate Tool Asset definitions for completeness, security, and correctness.

    Validation rules:
    1. tool_type is required
    2. database_query: SQL safety validation (no DDL keywords)
    3. input_schema: Valid JSON Schema
    4. Credentials: No plaintext credentials (delegated to credential_manager)
    5. tool_config: Type-specific validation
    6. URLs: Valid format for http_api tools
    """

    # Dangerous SQL keywords that should not appear in queries
    DANGEROUS_SQL_KEYWORDS = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"]

    @staticmethod
    def validate_tool_asset(asset: Any) -> list[str]:
        """
        Validate a Tool Asset for completeness and security.

        Args:
            asset: TbAssetRegistry instance with tool asset data

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # 1. Validate required tool_type
        if not asset.tool_type:
            errors.append("tool_type is required")
            return errors  # Can't proceed without tool_type

        tool_type = asset.tool_type.lower()

        # 2. Type-specific validation
        if tool_type == "database_query":
            errors.extend(ToolAssetValidator._validate_database_query(asset))
        elif tool_type == "http_api":
            errors.extend(ToolAssetValidator._validate_http_api(asset))
        elif tool_type == "graph_query":
            errors.extend(ToolAssetValidator._validate_graph_query(asset))
        elif tool_type == "mcp":
            errors.extend(ToolAssetValidator._validate_mcp(asset))

        # 3. Validate input_schema if present
        if asset.tool_input_schema:
            errors.extend(ToolAssetValidator._validate_json_schema(asset.tool_input_schema, "input_schema"))

        # 4. Validate output_schema if present
        if asset.tool_output_schema:
            errors.extend(ToolAssetValidator._validate_json_schema(asset.tool_output_schema, "output_schema"))

        # 5. Validate name
        if not asset.name or not asset.name.strip():
            errors.append("Tool name cannot be empty")

        return errors

    @staticmethod
    def _validate_database_query(asset: Any) -> list[str]:
        """Validate database_query type tool."""
        errors = []
        config = asset.tool_config or {}

        # Check source_ref
        if not config.get("source_ref"):
            errors.append("database_query: source_ref is required in tool_config")

        # Check query_template
        query_template = config.get("query_template", "")
        if not query_template:
            errors.append("database_query: query_template is required in tool_config")
        else:
            # SQL safety check
            sql_upper = query_template.upper()
            for keyword in ToolAssetValidator.DANGEROUS_SQL_KEYWORDS:
                if keyword in sql_upper:
                    # Allow in template variables like {DROP_IF_EXISTS}
                    if f"{{{keyword}" not in query_template.upper():
                        errors.append(
                            f"database_query: Dangerous SQL keyword '{keyword}' found in query_template. "
                            f"Use parameterized queries instead."
                        )
                        break

        return errors

    @staticmethod
    def _validate_http_api(asset: Any) -> list[str]:
        """Validate http_api type tool."""
        errors = []
        config = asset.tool_config or {}

        # Check URL
        url = config.get("url")
        if not url:
            errors.append("http_api: url is required in tool_config")
        else:
            # Validate URL format
            if not url.startswith(("http://", "https://", "/")):
                errors.append(
                    f"http_api: Invalid URL format in tool_config. "
                    f"Must start with http://, https://, or / (relative)"
                )

        # Check method
        method = config.get("method", "GET").upper()
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if method not in valid_methods:
            errors.append(f"http_api: Invalid HTTP method '{method}'. Must be one of {valid_methods}")

        return errors

    @staticmethod
    def _validate_graph_query(asset: Any) -> list[str]:
        """Validate graph_query type tool."""
        errors = []
        config = asset.tool_config or {}

        # Check source_ref (for Neo4j)
        if not config.get("source_ref"):
            errors.append("graph_query: source_ref is required in tool_config")

        # Check query_template
        if not config.get("query_template"):
            errors.append("graph_query: query_template is required in tool_config")

        return errors

    @staticmethod
    def _validate_mcp(asset: Any) -> list[str]:
        """Validate MCP (Model Context Protocol) type tool."""
        errors = []
        config = asset.tool_config or {}

        # Check MCP server reference (accept both field names for compatibility)
        has_server_ref = (
            config.get("mcp_server_ref")
            or config.get("mcp_server_url")
            or config.get("server_url")
        )
        if not has_server_ref:
            errors.append("mcp: mcp_server_ref or mcp_server_url is required in tool_config")

        # Check tool name in MCP
        if not config.get("tool_name"):
            errors.append("mcp: tool_name is required in tool_config")

        return errors

    @staticmethod
    def _validate_json_schema(schema: dict[str, Any], schema_name: str) -> list[str]:
        """
        Validate JSON Schema format.

        Args:
            schema: Schema dictionary
            schema_name: Name of schema for error messages

        Returns:
            List of validation errors
        """
        errors = []

        try:
            # Basic validation: ensure it's a dict
            if not isinstance(schema, dict):
                errors.append(f"{schema_name} must be a dict")
                return errors

            # Check for basic schema properties
            # Note: Full JSON Schema validation would require jsonschema library
            # For now, just check that it has reasonable structure
            if schema.get("type") not in [
                "object",
                "array",
                "string",
                "number",
                "integer",
                "boolean",
                "null",
                "object",
            ]:
                # type is optional, but if present should be valid
                if "type" in schema and schema["type"] not in [
                    "object",
                    "array",
                    "string",
                    "number",
                    "integer",
                    "boolean",
                    "null",
                ]:
                    errors.append(f"{schema_name}: Invalid schema type '{schema['type']}'")

            # Check properties if object type
            if schema.get("type") == "object":
                properties = schema.get("properties", {})
                if not isinstance(properties, dict):
                    errors.append(f"{schema_name}: properties must be a dict")

        except Exception as e:
            errors.append(f"{schema_name}: Schema validation error: {str(e)}")

        return errors

    @staticmethod
    def validate_for_publication(asset: Any) -> list[str]:
        """
        Enhanced validation for tool publication.

        Tools being published to production should meet higher standards.

        Args:
            asset: TbAssetRegistry instance

        Returns:
            List of validation errors
        """
        errors = ToolAssetValidator.validate_tool_asset(asset)

        # Additional publication checks
        if not asset.description or not asset.description.strip():
            errors.append("Tool description is required for publication")

        # Check that tags are present (helpful for discoverability)
        if not asset.tags or not asset.tags.get("source"):
            errors.append("Tool tags with 'source' are recommended for publication")

        return errors


def validate_tool_asset(asset: Any) -> list[str]:
    """
    Validate a Tool Asset for completeness and security.

    This is the main validation function to be used in tool asset CRUD operations.

    Args:
        asset: TbAssetRegistry instance with tool asset data

    Returns:
        List of validation error messages (empty if valid)
    """
    return ToolAssetValidator.validate_tool_asset(asset)


def validate_tool_for_publication(asset: Any) -> list[str]:
    """
    Validate a Tool Asset for publication with enhanced checks.

    Args:
        asset: TbAssetRegistry instance with tool asset data

    Returns:
        List of validation error messages (empty if valid)
    """
    return ToolAssetValidator.validate_for_publication(asset)
