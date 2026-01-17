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
    elif asset.asset_type == "query":
        validate_query_asset(asset)
    elif asset.asset_type == "screen":
        validate_screen_asset(asset)
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

    # Extended validation: views structure details
    required_views = {"SUMMARY", "COMPOSITION", "DEPENDENCY", "IMPACT", "PATH", "NEIGHBORS"}

    for view_name in required_views:
        if view_name not in views:
            raise ValueError(f"Mapping content.views must include '{view_name}'")

        view_config = views[view_name]
        if not isinstance(view_config, dict):
            raise ValueError(f"Mapping content.views.{view_name} must be a dictionary")

        # rel_types required
        if "rel_types" not in view_config:
            raise ValueError(f"Mapping content.views.{view_name} must have 'rel_types' field")

        rel_types = view_config["rel_types"]
        if not isinstance(rel_types, list):
            raise ValueError(f"Mapping content.views.{view_name}.rel_types must be a list")

        # All elements must be strings
        for rel_type in rel_types:
            if not isinstance(rel_type, str):
                raise ValueError(f"Mapping content.views.{view_name}.rel_types must contain only strings")

    # summary_neighbors_allowlist validation (optional)
    if "summary_neighbors_allowlist" in asset.content:
        allowlist = asset.content["summary_neighbors_allowlist"]
        if not isinstance(allowlist, list):
            raise ValueError("Mapping content.summary_neighbors_allowlist must be a list")
        for rel_type in allowlist:
            if not isinstance(rel_type, str):
                raise ValueError("Mapping content.summary_neighbors_allowlist must contain only strings")

    # exclude_rel_types validation (optional)
    if "exclude_rel_types" in asset.content:
        exclude = asset.content["exclude_rel_types"]
        if not isinstance(exclude, list):
            raise ValueError("Mapping content.exclude_rel_types must be a list")


def validate_policy_asset(asset: TbAssetRegistry) -> None:
    """Validate policy asset fields"""
    valid_types = ["plan_budget", "view_depth"]
    if not asset.policy_type or asset.policy_type not in valid_types:
        raise ValueError(f"Policy asset must have policy_type in {valid_types}")

    if not asset.limits:
        raise ValueError("Policy asset must have limits")

    limits = asset.limits

    if asset.policy_type == "plan_budget":
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

        # Validate max_branches (optional, default=3)
        max_branches = limits.get("max_branches", 3)
        if not isinstance(max_branches, int) or max_branches < 1:
            raise ValueError("limits.max_branches must be integer >= 1")

        # Validate max_iterations (optional, default=100)
        max_iterations = limits.get("max_iterations", 100)
        if not isinstance(max_iterations, int) or max_iterations < 1:
            raise ValueError("limits.max_iterations must be integer >= 1")

    elif asset.policy_type == "view_depth":
        # Validate view_depth policy type
        views = limits.get("views")
        if not views or not isinstance(views, dict):
            raise ValueError("limits.views must be a dictionary")

        required_views = {"SUMMARY", "COMPOSITION", "DEPENDENCY", "IMPACT", "PATH", "NEIGHBORS"}
        for view_name in required_views:
            if view_name not in views:
                raise ValueError(f"limits.views must include '{view_name}'")

            view_policy = views[view_name]
            if not isinstance(view_policy, dict):
                raise ValueError(f"limits.views.{view_name} must be a dictionary")

            # default_depth validation
            default_depth = view_policy.get("default_depth")
            if default_depth is None or not isinstance(default_depth, int) or default_depth < 1:
                raise ValueError(f"limits.views.{view_name}.default_depth must be integer >= 1")

            # max_depth validation
            max_depth = view_policy.get("max_depth")
            if max_depth is None or not isinstance(max_depth, int) or max_depth < 1:
                raise ValueError(f"limits.views.{view_name}.max_depth must be integer >= 1")
            if max_depth > 10:
                raise ValueError(f"limits.views.{view_name}.max_depth must be <= 10")

            # default_depth <= max_depth constraint
            if default_depth > max_depth:
                raise ValueError(f"limits.views.{view_name}.default_depth must be <= max_depth")


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
    dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"]
    for keyword in dangerous_keywords:
        # Word boundary pattern: keyword must be preceded and followed by non-word characters
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            raise ValueError(f"Query asset cannot contain {keyword} statements")

    # query_metadata should exist but can be empty
    if asset.query_metadata is None:
        asset.query_metadata = {}

    # query_params should exist but can be empty
    if asset.query_params is None:
        asset.query_params = {}


def validate_screen_asset(asset: TbAssetRegistry) -> None:
    """Validate screen asset fields - comprehensive schema and binding validation"""
    import re

    if not asset.screen_id or not str(asset.screen_id).strip():
        raise ValueError("Screen asset must have non-empty screen_id")
    if asset.screen_schema is None:
        raise ValueError("Screen asset must include schema_json")

    schema = asset.screen_schema
    if not isinstance(schema, dict):
        raise ValueError("schema_json must be a dictionary")

    # Validate required top-level fields
    required_fields = ["screen_id", "layout", "components"]
    for field in required_fields:
        if field not in schema:
            raise ValueError(f"Screen schema must have '{field}' field")

    # Validate screen_id matches
    if schema.get("screen_id") != asset.screen_id:
        raise ValueError(f"Screen schema screen_id '{schema.get('screen_id')}' must match asset screen_id '{asset.screen_id}'")

    # Validate layout
    layout = schema.get("layout", {})
    if not isinstance(layout, dict):
        raise ValueError("layout must be a dictionary")
    if "type" not in layout:
        raise ValueError("layout must have 'type' field")

    valid_layout_types = ["grid", "form", "modal", "list", "dashboard"]
    if layout["type"] not in valid_layout_types:
        raise ValueError(f"layout.type must be one of {valid_layout_types}")

    # Validate components array
    components = schema.get("components", [])
    if not isinstance(components, list):
        raise ValueError("components must be an array")

    if len(components) == 0:
        raise ValueError("components must contain at least one component")

    valid_component_types = {"text", "markdown", "button", "input", "table", "chart", "badge", "tabs", "modal", "keyvalue", "divider"}

    for idx, comp in enumerate(components):
        if not isinstance(comp, dict):
            raise ValueError(f"components[{idx}] must be a dictionary")

        if "id" not in comp:
            raise ValueError(f"components[{idx}] must have 'id' field")

        if "type" not in comp:
            raise ValueError(f"components[{idx}] must have 'type' field")

        comp_type = comp["type"]
        if comp_type not in valid_component_types:
            raise ValueError(f"components[{idx}].type must be one of {valid_component_types}, got '{comp_type}'")

    # Validate bindings format (dot-path only, no expressions)
    bindings = schema.get("bindings", {})
    if bindings and isinstance(bindings, dict):
        binding_pattern = re.compile(r'^{{(state|inputs|context)\.[a-zA-Z0-9_\.]+}}$')
        for target, source in bindings.items():
            # Source should be in format "state.x", "inputs.x", etc. (without {{}} when stored as string)
            if not isinstance(source, str):
                raise ValueError(f"bindings['{target}'] value must be a string")

            # Validate dot-path format (state.x, inputs.x, etc.)
            if not re.match(r'^(state|inputs|context)\.[a-zA-Z0-9_\.]+$', source):
                raise ValueError(f"bindings['{target}'] = '{source}' must use dot-path format like 'state.x' or 'inputs.fieldName'")

    # Validate binding expressions in component props ({{...}} format)
    def validate_binding_expressions(obj: Any, path: str = ""):
        if isinstance(obj, str):
            # Find all {{...}} patterns
            binding_exprs = re.findall(r'{{([^}]+)}}', obj)
            for expr in binding_exprs:
                expr_clean = expr.strip()
                # Validate: must be state.x, inputs.x, context.x, or trace_id
                if expr_clean != "trace_id" and not re.match(r'^(state|inputs|context)\.[a-zA-Z0-9_\.]+$', expr_clean):
                    raise ValueError(f"Invalid binding expression '{{{{' + '{expr_clean}' + '}}}}' at {path}: must use dot-path format")
        elif isinstance(obj, dict):
            for key, value in obj.items():
                validate_binding_expressions(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                validate_binding_expressions(item, f"{path}[{idx}]")

    # Validate binding expressions in all components and actions
    for idx, comp in enumerate(components):
        if "props" in comp:
            validate_binding_expressions(comp["props"], f"components[{idx}].props")

        if "actions" in comp and isinstance(comp["actions"], list):
            for aidx, action in enumerate(comp["actions"]):
                if isinstance(action, dict) and "payload_template" in action:
                    validate_binding_expressions(action["payload_template"], f"components[{idx}].actions[{aidx}].payload_template")

    # Validate top-level actions if present
    actions = schema.get("actions", [])
    if actions and isinstance(actions, list):
        for aidx, action in enumerate(actions):
            if isinstance(action, dict) and "payload_template" in action:
                validate_binding_expressions(action["payload_template"], f"actions[{aidx}].payload_template")
