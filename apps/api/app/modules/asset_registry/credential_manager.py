"""
Secure Credential Management for Tool Assets

This module provides secure handling of credentials in tool configurations
using secret_key_ref references instead of plaintext storage.

BLOCKER-2: Credential 평문 저장 제거
"""

from __future__ import annotations

from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class CredentialManager:
    """
    Manage credentials securely in tool configurations.

    Rules:
    1. Never store plaintext credentials in tool_config
    2. Use secret_key_ref: "env:CREDENTIAL_NAME" for environment variables
    3. Use secret_key_ref: "vault:secret/path" for vault references
    4. Sanitize tool_config on retrieval (mask sensitive fields)
    """

    # Sensitive field patterns to detect plaintext credentials
    SENSITIVE_PATTERNS = {
        "password",
        "secret",
        "token",
        "api_key",
        "api_secret",
        "auth",
        "key",
        "credential",
        "bearer",
        "authorization",
    }

    @staticmethod
    def sanitize_tool_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Sanitize tool_config by removing/masking sensitive values.

        For display purposes, replace plaintext credentials with masked values.

        Args:
            config: Tool configuration dict

        Returns:
            Sanitized configuration dict (deep copy)
        """
        if not config:
            return config

        import copy

        sanitized = copy.deepcopy(config)

        # Sanitize headers
        if isinstance(sanitized.get("headers"), dict):
            for key, value in sanitized["headers"].items():
                if isinstance(value, str) and CredentialManager._is_plaintext_credential(
                    key, value
                ):
                    sanitized["headers"][key] = "***MASKED***"

        # Sanitize other potentially sensitive fields
        for key in list(sanitized.keys()):
            value = sanitized[key]
            if isinstance(value, str) and CredentialManager._is_plaintext_credential(
                key, value
            ):
                sanitized[key] = "***MASKED***"

        return sanitized

    @staticmethod
    def validate_no_plaintext_credentials(config: dict[str, Any] | None) -> list[str]:
        """
        Validate that tool_config contains no plaintext credentials.

        Returns list of validation errors (empty if all valid).

        Args:
            config: Tool configuration dict

        Returns:
            List of validation error messages
        """
        errors = []

        if not config:
            return errors

        # Check headers
        headers = config.get("headers", {})
        if isinstance(headers, dict):
            for key, value in headers.items():
                if isinstance(value, str) and CredentialManager._is_plaintext_credential(
                    key, value
                ):
                    errors.append(
                        f"Plaintext credential in headers.{key}: "
                        f"Use secret_key_ref instead (e.g., 'env:API_KEY_NAME')"
                    )

        # Check all top-level fields for plaintext credentials
        for key, value in config.items():
            if key == "headers":  # Already checked above
                continue
            if isinstance(value, str) and CredentialManager._is_plaintext_credential(
                key, value
            ):
                errors.append(
                    f"Plaintext credential in {key}: "
                    f"Use secret_key_ref instead (e.g., 'env:{key.upper()}')"
                )

        return errors

    @staticmethod
    def extract_credential_refs(config: dict[str, Any] | None) -> dict[str, str]:
        """
        Extract all credential references (env:*, vault:*) from tool_config.

        Args:
            config: Tool configuration dict

        Returns:
            Dict mapping credential keys to their references
        """
        refs = {}

        if not config:
            return refs

        # Check headers
        headers = config.get("headers", {})
        if isinstance(headers, dict):
            for key, value in headers.items():
                if isinstance(value, str) and (
                    value.startswith("env:") or value.startswith("vault:")
                ):
                    refs[f"headers.{key}"] = value

        # Check other sensitive fields
        for key in config:
            value = config.get(key)
            if isinstance(value, str) and (
                value.startswith("env:") or value.startswith("vault:")
            ):
                refs[key] = value

        return refs

    @staticmethod
    def _is_plaintext_credential(field_name: str, value: str) -> bool:
        """
        Detect if a field contains a plaintext credential.

        Args:
            field_name: Field name (e.g., 'Authorization', 'password')
            value: Field value

        Returns:
            True if value appears to be plaintext credential
        """
        # Template variables like {token} are OK (will be filled at runtime)
        if value.startswith("{") and value.endswith("}"):
            return False

        # Credential references are OK
        if value.startswith(("env:", "vault:", "***")):
            return False

        # Empty values are OK
        if not value or value == "":
            return False

        # Check if field name suggests it's sensitive
        field_lower = field_name.lower()
        for pattern in CredentialManager.SENSITIVE_PATTERNS:
            if pattern in field_lower:
                # If field is sensitive AND value is not a reference, it's plaintext
                return True

        return False


def validate_tool_config_credentials(config: dict[str, Any] | None) -> list[str]:
    """
    Validate that tool_config contains no plaintext credentials.

    This is the main validation function to be used in tool asset validation.

    Args:
        config: Tool configuration dict

    Returns:
        List of validation error messages (empty if valid)
    """
    return CredentialManager.validate_no_plaintext_credentials(config)
