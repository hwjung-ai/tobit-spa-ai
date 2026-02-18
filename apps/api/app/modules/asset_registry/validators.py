from __future__ import annotations

from .models import TbAssetRegistry


def validate_asset(asset: TbAssetRegistry) -> None:
    """Type-specific validation before publish"""
    if asset.asset_type == "prompt":
        validate_prompt_asset(asset)
    elif asset.asset_type == "mapping":
        validate_mapping_asset(asset)
    elif asset.asset_type == "policy":
        validate_policy_asset(asset)
    elif asset.asset_type == "query":
        validate_query_asset(asset)
    elif asset.asset_type == "source":
        validate_source_asset(asset)
    elif asset.asset_type == "resolver":
        validate_resolver_asset(asset)
    elif asset.asset_type == "screen":
        validate_screen_asset(asset)
    else:
        raise ValueError(f"Unknown asset_type: {asset.asset_type}")


def validate_prompt_asset(asset: TbAssetRegistry) -> None:
    """Validate prompt asset fields"""
    # No hardcoded scope validation - allow any custom scope
    if not asset.scope:
        raise ValueError("Prompt asset must have scope")

    # No hardcoded engine validation - allow any custom engine
    if not asset.engine:
        raise ValueError("Prompt asset must have engine")

    if not asset.template or not asset.template.strip():
        raise ValueError("Prompt asset must have non-empty template")

    if not asset.input_schema:
        raise ValueError("Prompt asset must have input_schema")

    # Validate input_schema is valid JSONSchema
    try:
        # Check required 'question' field
        properties = asset.input_schema.get("properties", {})
        if "question" not in properties:
            raise ValueError("input_schema must include 'question' property")

        required = asset.input_schema.get("required", [])
        if "question" not in required:
            raise ValueError("input_schema must require 'question' field")
    except Exception as e:
        raise ValueError(f"Invalid input_schema: {e}")

    if not asset.output_contract:
        raise ValueError("Prompt asset must have output_contract for publish")

    # Validate output_contract has required keys
    properties = asset.output_contract.get("properties", {})
    if "plan" not in properties:
        raise ValueError("output_contract must include 'plan' property")

    plan_props = properties.get("plan", {}).get("properties", {})
    if "steps" not in plan_props and "policy" not in plan_props:
        raise ValueError("output_contract.plan must have 'steps' or 'policy' property")


def validate_mapping_asset(asset: TbAssetRegistry) -> None:
    """Validate mapping asset fields"""
    if not asset.mapping_type:
        raise ValueError("Mapping asset must have mapping_type")

    if not asset.content:
        raise ValueError("Mapping asset must have content")

    # No hardcoded structure validation - allow flexible mapping content
    # Basic validation only
    if not isinstance(asset.content, dict):
        raise ValueError("Mapping content must be a dictionary")

    # summary_neighbors_allowlist validation (optional)
    if "summary_neighbors_allowlist" in asset.content:
        allowlist = asset.content["summary_neighbors_allowlist"]
        if not isinstance(allowlist, list):
            raise ValueError(
                "Mapping content.summary_neighbors_allowlist must be a list"
            )
        for rel_type in allowlist:
            if not isinstance(rel_type, str):
                raise ValueError(
                    "Mapping content.summary_neighbors_allowlist must contain only strings"
                )

    # exclude_rel_types validation (optional)
    if "exclude_rel_types" in asset.content:
        exclude = asset.content["exclude_rel_types"]
        if not isinstance(exclude, list):
            raise ValueError("Mapping content.exclude_rel_types must be a list")


def validate_policy_asset(asset: TbAssetRegistry) -> None:
    """Validate policy asset fields"""
    if not asset.policy_type:
        raise ValueError("Policy asset must have policy_type")

    if not asset.limits and not asset.content:
        raise ValueError("Policy asset must have limits or content")

    # No hardcoded policy_type validation - allow any custom policy type
    # No hardcoded structure validation - limits/content structure is flexible


def validate_query_asset(asset: TbAssetRegistry) -> None:
    """Validate query asset fields"""
    import re

    if not asset.query_sql or not asset.query_sql.strip():
        raise ValueError("Query asset must have non-empty query_sql")

    # Validate SQL is SELECT only
    sql_upper = asset.query_sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Query asset must contain only SELECT statements")

    # Check for dangerous keywords using word boundaries to avoid false positives
    # e.g., "updated_at" should not trigger "UPDATE"
    dangerous_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
    ]
    for keyword in dangerous_keywords:
        # Word boundary pattern: keyword must be preceded and followed by non-word characters
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, sql_upper):
            raise ValueError(f"Query asset cannot contain {keyword} statements")

    # query_metadata should exist but can be empty
    if asset.query_metadata is None:
        asset.query_metadata = {}

    # query_params should exist but can be empty
    if asset.query_params is None:
        asset.query_params = {}


def validate_source_asset(asset: TbAssetRegistry) -> None:
    """Validate source asset fields"""
    content = asset.content or {}
    source_type = content.get("source_type")
    connection = content.get("connection") or {}

    if not source_type:
        raise ValueError("Source asset must include source_type in content")
    if not isinstance(connection, dict):
        raise ValueError("Source asset connection must be a dictionary")

    if not connection.get("host"):
        raise ValueError("Source asset connection must include host")
    if not connection.get("username"):
        raise ValueError("Source asset connection must include username")


def validate_resolver_asset(asset: TbAssetRegistry) -> None:
    """Validate resolver asset fields"""
    content = asset.content or {}
    rules = content.get("rules", [])
    default_namespace = content.get("default_namespace")

    if not isinstance(rules, list):
        raise ValueError("Resolver asset rules must be a list")
    if default_namespace is not None and not isinstance(default_namespace, str):
        raise ValueError("Resolver asset default_namespace must be a string")


def validate_screen_asset(asset: TbAssetRegistry) -> None:
    """Validate screen asset fields"""
    # Check required fields
    if not asset.screen_id or not asset.screen_id.strip():
        raise ValueError("Screen asset must have non-empty screen_id")

    if not asset.name or not asset.name.strip():
        raise ValueError("Screen asset must have non-empty name")

    # Check schema_json
    if not asset.schema_json:
        raise ValueError("Screen asset must have schema_json")

    if not isinstance(asset.schema_json, dict):
        raise ValueError("Screen asset schema_json must be a dictionary")

    # Validate schema_json structure
    schema = asset.schema_json

    # Required fields in schema_json
    required_fields = ["components", "layout", "state"]
    for field in required_fields:
        if field not in schema:
            raise ValueError(f"Screen schema_json must include '{field}' field")

    # Validate components is a list
    if not isinstance(schema["components"], list):
        raise ValueError("Screen schema_json.components must be a list")

    # Validate each component
    for i, component in enumerate(schema["components"]):
        if not isinstance(component, dict):
            raise ValueError(f"Screen component at index {i} must be a dictionary")

        if "id" not in component:
            raise ValueError(f"Screen component at index {i} must have 'id'")

        if "type" not in component:
            raise ValueError(f"Screen component at index {i} must have 'type'")

        valid_types = [
            "text", "button", "input", "table", "chart", "keyvalue",
            "row", "modal", "column", "tabs", "accordion"
        ]
        if component["type"] not in valid_types:
            raise ValueError(
                f"Screen component '{component['id']}' has invalid type '{component['type']}'. "
                f"Valid types: {valid_types}"
            )

    # Validate layout
    if not isinstance(schema["layout"], dict):
        raise ValueError("Screen schema_json.layout must be a dictionary")

    # Validate state
    if not isinstance(schema["state"], dict):
        raise ValueError("Screen schema_json.state must be a dictionary")

    state = schema["state"]

    if "schema" not in state:
        raise ValueError("Screen schema_json.state must include 'schema'")

    if "initial" not in state:
        raise ValueError("Screen schema_json.state must include 'initial'")

