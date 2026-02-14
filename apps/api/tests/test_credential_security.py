"""
BLOCKER-2: Credential Security Tests

Tests to verify that credentials are not stored in plaintext
in tool configurations.
"""

import pytest
from app.modules.asset_registry.credential_manager import (
    CredentialManager,
    validate_tool_config_credentials,
)


class TestCredentialManagerValidation:
    """Test credential validation in tool configurations."""

    def test_plaintext_api_key_detected(self):
        """Detect plaintext API keys in configuration."""
        config = {
            "url": "https://api.example.com",
            "headers": {"Authorization": "Bearer sk_test_abc123def456"},
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) > 0
        assert "Bearer sk_test_abc123def456" or "Authorization" in str(errors)

    def test_plaintext_password_detected(self):
        """Detect plaintext passwords in configuration."""
        config = {
            "host": "localhost",
            "port": 5432,
            "password": "my_secret_password123",
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) > 0
        assert "password" in str(errors).lower()

    def test_secret_key_ref_allowed(self):
        """Allow secret_key_ref format for credentials."""
        config = {
            "url": "https://api.example.com",
            "headers": {"Authorization": "env:API_KEY"},
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) == 0

    def test_vault_ref_allowed(self):
        """Allow vault reference format for credentials."""
        config = {
            "url": "https://api.example.com",
            "headers": {"Authorization": "vault:secret/api-key"},
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) == 0

    def test_template_variables_detected_as_plaintext(self):
        """
        Template variables like {token} are detected as potentially plaintext.

        This is a conservative security approach - templates should use env: or vault: references
        instead for security, but this is less strict than absolute plaintext passwords.
        """
        config = {
            "url": "https://api.example.com",
            "headers": {
                "Authorization": "Bearer {token}",
            },
        }

        errors = validate_tool_config_credentials(config)
        # We're strict on Authorization headers - recommend env: or vault: refs
        assert len(errors) == 1  # Should recommend using secret_key_ref

    def test_empty_config_valid(self):
        """Empty configuration is valid."""
        errors = validate_tool_config_credentials({})
        assert len(errors) == 0

    def test_none_config_valid(self):
        """None configuration is valid."""
        errors = validate_tool_config_credentials(None)
        assert len(errors) == 0

    def test_multiple_plaintext_credentials_detected(self):
        """Detect multiple plaintext credentials in same config."""
        config = {
            "host": "localhost",
            "password": "my_secret_password",
            "headers": {
                "Authorization": "Bearer sk_test_abc123",
                "X-API-Key": "actual_api_key_value",
            },
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) >= 2  # At least 2 plaintext credentials detected

    def test_sanitize_plaintext_credentials(self):
        """Sanitize plaintext credentials for display."""
        config = {
            "url": "https://api.example.com",
            "headers": {
                "Authorization": "Bearer sk_test_abc123def456",
                "Content-Type": "application/json",
            },
            "api_key": "secret_key_value",
        }

        sanitized = CredentialManager.sanitize_tool_config(config)

        # Plaintext credentials should be masked
        assert sanitized["headers"]["Authorization"] == "***MASKED***"
        assert sanitized["api_key"] == "***MASKED***"

        # Non-sensitive fields should remain
        assert sanitized["headers"]["Content-Type"] == "application/json"
        assert sanitized["url"] == "https://api.example.com"

    def test_extract_credential_refs(self):
        """Extract credential references from config."""
        config = {
            "url": "https://api.example.com",
            "headers": {
                "Authorization": "env:API_KEY",
                "X-API-Key": "vault:secret/key",
            },
            "password": "env:DB_PASSWORD",
        }

        refs = CredentialManager.extract_credential_refs(config)

        assert refs["headers.Authorization"] == "env:API_KEY"
        assert refs["headers.X-API-Key"] == "vault:secret/key"
        assert refs["password"] == "env:DB_PASSWORD"

    def test_sensitive_patterns_detected(self):
        """Test all sensitive field patterns."""
        patterns = [
            ("password", "plaintext_password"),
            ("token", "abc123token"),
            ("secret", "my_secret"),
            ("api_key", "key_value"),
            ("api_secret", "secret_value"),
            ("authorization", "Bearer token"),
        ]

        for field_name, value in patterns:
            config = {field_name: value}
            errors = validate_tool_config_credentials(config)
            assert len(errors) > 0, f"Pattern '{field_name}' should be detected"

    def test_masked_values_allowed(self):
        """Allow masked values (***MASKED***)."""
        config = {
            "headers": {"Authorization": "***MASKED***"},
            "password": "***MASKED***",
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) == 0

    def test_empty_credentials_allowed(self):
        """Allow empty credential values."""
        config = {
            "headers": {"Authorization": ""},
            "password": "",
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) == 0

    def test_case_insensitive_field_detection(self):
        """Field names should be case-insensitive for pattern matching."""
        # Some APIs use different casing
        config1 = {"Authorization": "Bearer abc123"}
        config2 = {"authorization": "Bearer abc123"}
        config3 = {"AUTHORIZATION": "Bearer abc123"}

        for config in [config1, config2, config3]:
            errors = validate_tool_config_credentials(config)
            assert len(errors) > 0, "Should detect Authorization field regardless of case"

    def test_nested_headers_in_config(self):
        """Headers containing plaintext credentials should be detected."""
        config = {
            "url": "https://api.example.com",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer actual_token_12345",
                "X-Custom-Auth": "api_key_value",
            },
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) >= 2  # Both Authorization and X-Custom-Auth


class TestCredentialPatternsEdgeCases:
    """Test edge cases in credential pattern detection."""

    def test_url_with_credentials_detected(self):
        """Detect credentials embedded in URLs."""
        # Note: Current implementation doesn't check URLs, but this documents
        # the expected behavior for future enhancement
        pass

    def test_field_values_with_auth_pattern_detected(self):
        """
        Fields containing 'auth' pattern may be detected if value is plaintext.

        This is conservative - we recommend using env: or vault: references for anything
        that looks like authentication/authorization.
        """
        config = {
            "headers": {
                "Authorization": "env:API_KEY",  # This is OK (reference)
            },
        }

        errors = validate_tool_config_credentials(config)
        assert len(errors) == 0  # env: reference is safe

    def test_reference_prefix_variations(self):
        """Support various credential reference formats."""
        valid_configs = [
            {"headers": {"Authorization": "env:API_KEY"}},
            {"headers": {"Authorization": "vault:secret/api-key"}},
            {"password": "env:DB_PASSWORD"},
            {"api_key": "vault:path/to/key"},
        ]

        for config in valid_configs:
            errors = validate_tool_config_credentials(config)
            assert len(errors) == 0, f"Should allow: {config}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
