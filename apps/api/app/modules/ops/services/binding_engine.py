"""
Binding Engine: Template substitution for UI actions

Supports 3 types of bindings (MVP):
- {{inputs.field}} - user inputs
- {{state.path}} - screen state
- {{context.key}} - execution context
- {{trace_id}} - current trace ID

Only dot-path expressions allowed (no computation, function calls, or dynamic access).
"""

from __future__ import annotations

import re
from typing import Any, Dict


class BindingError(Exception):
    """Binding engine error"""
    pass


class BindingEngine:
    """Template binding engine for UI actions"""

    # Pattern for {{variable.path}} expressions
    BINDING_PATTERN = re.compile(r'\{\{\s*([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\}\}')

    @staticmethod
    def get_nested_value(obj: Any, path: str) -> Any:
        """
        Get nested value from object using dot-path.

        Examples:
            get_nested_value({"a": {"b": 1}}, "a.b") → 1
            get_nested_value({"items": [{"id": 1}]}, "items") → [{"id": 1}]
            get_nested_value({...}, "nonexistent") → None
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # Array access not allowed in MVP
                raise BindingError(f"Array indexing not supported: {path}")
            else:
                # Can't navigate further
                return None

        return current

    @staticmethod
    def set_nested_value(obj: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set nested value in object using dot-path.

        Examples:
            obj = {}
            set_nested_value(obj, "a.b.c", 42)
            # Result: {"a": {"b": {"c": 42}}}
        """
        parts = path.split(".")
        current = obj

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise BindingError(f"Cannot navigate through non-dict: {path}")
            current = current[part]

        current[parts[-1]] = value

    @staticmethod
    def render_template(
        template: Dict[str, Any] | str | Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any] | str | Any:
        """
        Render template by substituting {{expr}} with values from context.

        Context keys:
            - inputs: user input values
            - state: current screen state
            - context: execution context (mode, user_id, etc.)
            - trace_id: current trace ID

        Args:
            template: Template dict/str with {{expr}} patterns
            context: Context dict with keys: inputs, state, context, trace_id

        Returns:
            Rendered value with substitutions applied

        Raises:
            BindingError: If binding expression is invalid or value not found
        """
        if isinstance(template, dict):
            return BindingEngine._render_dict(template, context)
        elif isinstance(template, list):
            return [BindingEngine.render_template(item, context) for item in template]
        elif isinstance(template, str):
            return BindingEngine._render_string(template, context)
        else:
            # Primitives (int, bool, None) pass through
            return template

    @staticmethod
    def _render_dict(
        template_dict: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recursively render all values in dict"""
        result = {}
        for key, value in template_dict.items():
            result[key] = BindingEngine.render_template(value, context)
        return result

    @staticmethod
    def _render_string(template_str: str, context: Dict[str, Any]) -> Any:
        """
        Render string with {{expr}} substitutions.

        If entire string is a single {{expr}}, return the value as-is (type preserved).
        Otherwise, convert substitutions to strings.

        Examples:
            "{{trace_id}}" → value of trace_id (any type)
            "prefix_{{device_id}}" → "prefix_" + str(device_id)
        """
        matches = list(BindingEngine.BINDING_PATTERN.finditer(template_str))

        # No bindings
        if not matches:
            return template_str

        # Single binding that covers entire string → return value as-is
        if len(matches) == 1 and matches[0].group(0) == template_str:
            expr = matches[0].group(1)
            return BindingEngine._resolve_expression(expr, context)

        # Multiple bindings or partial → replace and convert to string
        result = template_str
        for match in reversed(matches):  # Reverse to preserve positions
            expr = match.group(1)
            value = BindingEngine._resolve_expression(expr, context)
            value_str = "" if value is None else str(value)
            result = result[:match.start()] + value_str + result[match.end():]

        return result

    @staticmethod
    def _resolve_expression(expr: str, context: Dict[str, Any]) -> Any:
        """
        Resolve a single expression like "inputs.device_id" or "trace_id".

        Context structure:
            {
                "inputs": {...},
                "state": {...},
                "context": {...},
                "trace_id": "..."
            }
        """
        # Special case: trace_id
        if expr == "trace_id":
            value = context.get("trace_id")
            if value is None:
                raise BindingError("trace_id not found in context")
            return value

        # Split first part
        parts = expr.split(".", 1)
        root = parts[0]
        rest = parts[1] if len(parts) > 1 else None

        # Special case: context (name collision with dict key)
        if root == "context":
            obj = context.get("context", {})
        elif root in ["inputs", "state"]:
            obj = context.get(root, {})
        else:
            raise BindingError(f"Unknown variable: {root}")

        # Navigate to nested value
        if rest:
            value = BindingEngine.get_nested_value(obj, rest)
        else:
            value = obj

        if value is None:
            raise BindingError(f"Value not found in {root}: {expr}")

        return value

    @staticmethod
    def validate_template(template: Dict[str, Any] | str) -> list[str]:
        """
        Validate template for any unresolved or invalid binding expressions.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        def check_string(s: str):
            for match in BindingEngine.BINDING_PATTERN.finditer(s):
                expr = match.group(1)
                # Basic validation: must start with valid root
                parts = expr.split(".")
                root = parts[0]
                if root not in ["inputs", "state", "context", "trace_id"]:
                    errors.append(f"Unknown binding root: {root} (in {expr})")

        def traverse(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    traverse(value)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)
            elif isinstance(obj, str):
                check_string(obj)

        traverse(template)
        return errors


def mask_sensitive_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive fields in inputs before logging to trace.

    Sensitive patterns: password, secret, token, api_key, credit_card, ssn, phone, email
    """
    if not inputs:
        return inputs

    masked = inputs.copy()
    sensitive_patterns = [
        "password", "secret", "token", "api_key", "api_secret",
        "credit_card", "cc_", "ssn", "phone", "email"
    ]

    def mask_value(value):
        if isinstance(value, dict):
            return {k: mask_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [mask_value(item) for item in value]
        elif isinstance(value, str) and len(value) > 0:
            # Mask string (show first 3 chars and last 1)
            if len(value) <= 4:
                return "***MASKED***"
            return value[:3] + "***" + value[-1]
        else:
            return value

    for key in list(masked.keys()):
        if any(pattern in key.lower() for pattern in sensitive_patterns):
            masked[key] = "***MASKED***"
        elif isinstance(masked[key], dict):
            masked[key] = mask_value(masked[key])

    return masked
