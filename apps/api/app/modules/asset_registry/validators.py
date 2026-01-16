from __future__ import annotations

from typing import Any

from .models import TbAssetRegistry


def validate_asset(asset: TbAssetRegistry) -> None:
    """Type-specific validation before publish"""
    if asset.asset_type == "prompt":
        validate_prompt_asset(asset)
    elif asset.asset_type == "mapping":
        validate_mapping_asset(asset)
    elif asset.asset_type == "policy":
        validate_policy_asset(asset)
    else:
        raise ValueError(f"Unknown asset_type: {asset.asset_type}")


def validate_prompt_asset(asset: TbAssetRegistry) -> None:
    """Validate prompt asset fields"""
    if not asset.scope or asset.scope not in ["ci", "ops"]:
        raise ValueError("Prompt asset must have scope of 'ci' or 'ops'")

    if not asset.engine or asset.engine not in ["planner", "langgraph"]:
        raise ValueError("Prompt asset must have engine of 'planner' or 'langgraph'")

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
    if not asset.mapping_type or asset.mapping_type != "graph_relation":
        raise ValueError("Mapping asset must have mapping_type of 'graph_relation'")

    if not asset.content:
        raise ValueError("Mapping asset must have content")

    # Validate structure matches relation_mapping.yaml
    if "version" not in asset.content:
        raise ValueError("Mapping content must have 'version' field")

    if "views" not in asset.content:
        raise ValueError("Mapping content must have 'views' field")

    views = asset.content.get("views", {})
    if not isinstance(views, dict):
        raise ValueError("Mapping content 'views' must be a dictionary")


def validate_policy_asset(asset: TbAssetRegistry) -> None:
    """Validate policy asset fields"""
    if not asset.policy_type or asset.policy_type != "plan_budget":
        raise ValueError("Policy asset must have policy_type of 'plan_budget'")

    if not asset.limits:
        raise ValueError("Policy asset must have limits")

    limits = asset.limits

    # Validate max_steps
    max_steps = limits.get("max_steps")
    if max_steps is None or not isinstance(max_steps, int) or max_steps < 1:
        raise ValueError("limits.max_steps must be integer >= 1")

    # Validate timeout_ms
    timeout_ms = limits.get("timeout_ms")
    if timeout_ms is None or not isinstance(timeout_ms, int) or timeout_ms < 1000:
        raise ValueError("limits.timeout_ms must be integer >= 1000")

    # Validate max_depth
    max_depth = limits.get("max_depth")
    if max_depth is None or not isinstance(max_depth, int) or max_depth < 1:
        raise ValueError("limits.max_depth must be integer >= 1")

    if max_depth > 10:
        raise ValueError("limits.max_depth must be <= 10")
