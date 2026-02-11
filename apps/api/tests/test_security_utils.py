"""
Tests for SecurityUtils module.

Tests masking, sanitization, and security functions for protecting sensitive data.
"""

from app.modules.ops.security import SecurityUtils


class TestSecurityUtilsMasking:
    """Test cases for value masking."""

    def test_mask_value_none(self):
        """Test masking None value."""
        result = SecurityUtils.mask_value(None)
        assert result == "null"

    def test_mask_value_boolean(self):
        """Test masking boolean values."""
        assert SecurityUtils.mask_value(True) == "True"
        assert SecurityUtils.mask_value(False) == "False"

    def test_mask_value_short_string(self):
        """Test masking short strings."""
        result = SecurityUtils.mask_value("abc")
        assert len(result) == 3
        assert all(c == "*" for c in result)

    def test_mask_value_long_string(self):
        """Test masking long strings."""
        result = SecurityUtils.mask_value("this_is_a_very_long_password_string_12345")
        # Should show first 4 and last 4 characters
        assert result.startswith("this")
        assert result.endswith("2345")
        assert "..." in result

    def test_mask_value_numbers(self):
        """Test masking numeric values."""
        result = SecurityUtils.mask_value(12345)
        assert "1" in result  # First digit
        assert "5" in result  # Last digit
        assert "*" in result  # Masked middle

    def test_mask_string_with_custom_params(self):
        """Test masking with custom show_prefix and show_suffix."""
        result = SecurityUtils.mask_string("mysecretpassword", show_prefix=3, show_suffix=3)
        assert result.startswith("mys")
        assert result.endswith("ord")


class TestSecurityUtilsDictMasking:
    """Test cases for dictionary masking."""

    def test_mask_dict_simple(self):
        """Test masking simple dictionary."""
        data = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",
        }
        masked = SecurityUtils.mask_dict(data)

        assert "john_doe" in masked["username"]  # Non-sensitive, not masked
        assert SecurityUtils._is_sensitive("password")
        assert masked["password"] != "secret123"

    def test_mask_dict_preserves_non_sensitive(self):
        """Test that non-sensitive fields are preserved."""
        data = {
            "name": "John Doe",
            "age": 30,
            "city": "New York",
        }
        masked = SecurityUtils.mask_dict(data)

        assert masked["name"] == "John Doe"
        assert masked["age"] == 30
        assert masked["city"] == "New York"

    def test_mask_dict_nested(self):
        """Test masking nested dictionaries."""
        data = {
            "user": {
                "username": "john",
                "password": "secret123",
                "profile": {
                    "email": "john@example.com",
                    "phone": "555-1234",
                },
            }
        }
        masked = SecurityUtils.mask_dict(data)

        assert SecurityUtils._is_sensitive("password")
        assert masked["user"]["password"] != "secret123"
        assert masked["user"]["username"] == "john"  # Not sensitive

    def test_mask_dict_with_preserve_keys(self):
        """Test masking with preserved keys."""
        data = {
            "password": "secret123",
            "api_key": "key123",
            "public_info": "can_be_public",
        }
        masked = SecurityUtils.mask_dict(
            data, preserve_keys=["api_key"]
        )

        assert masked["password"] != "secret123"
        assert masked["api_key"] == "key123"  # Preserved

    def test_mask_dict_list_values(self):
        """Test masking dictionaries with list values."""
        data = {
            "users": [
                {"user": "john", "password": "pass1"},
                {"user": "jane", "password": "pass2"},
            ]
        }
        masked = SecurityUtils.mask_dict(data)

        assert isinstance(masked["users"], list)
        assert masked["users"][0]["user"] == "john"
        assert masked["users"][0]["password"] != "pass1"
        assert masked["users"][1]["password"] != "pass2"


class TestSecurityUtilsListMasking:
    """Test cases for list masking."""

    def test_mask_list_simple(self):
        """Test masking simple list."""
        data = [
            {"password": "secret1"},
            {"password": "secret2"},
        ]
        masked = SecurityUtils.mask_list(data)

        assert len(masked) == 2
        assert masked[0]["password"] != "secret1"
        assert masked[1]["password"] != "secret2"

    def test_mask_tuple(self):
        """Test masking tuple."""
        data = (
            {"api_key": "key123"},
            {"api_key": "key456"},
        )
        masked = SecurityUtils.mask_list(data)

        assert isinstance(masked, tuple)
        assert masked[0]["api_key"] != "key123"
        assert masked[1]["api_key"] != "key456"


class TestSecurityUtilsSensitiveDetection:
    """Test cases for sensitive field detection."""

    def test_is_sensitive_password(self):
        """Test detection of password fields."""
        assert SecurityUtils._is_sensitive("password") is True
        assert SecurityUtils._is_sensitive("passwd") is True
        assert SecurityUtils._is_sensitive("user_password") is True
        assert SecurityUtils._is_sensitive("pwd") is True

    def test_is_sensitive_api_key(self):
        """Test detection of API key fields."""
        assert SecurityUtils._is_sensitive("api_key") is True
        assert SecurityUtils._is_sensitive("apikey") is True
        assert SecurityUtils._is_sensitive("api_secret") is True
        assert SecurityUtils._is_sensitive("access_token") is True

    def test_is_sensitive_credentials(self):
        """Test detection of credential fields."""
        assert SecurityUtils._is_sensitive("credentials") is True
        assert SecurityUtils._is_sensitive("secret") is True
        assert SecurityUtils._is_sensitive("private_key") is True

    def test_is_sensitive_pii(self):
        """Test detection of PII fields."""
        assert SecurityUtils._is_sensitive("email") is True
        assert SecurityUtils._is_sensitive("phone") is True
        assert SecurityUtils._is_sensitive("ssn") is True
        assert SecurityUtils._is_sensitive("credit_card") is True

    def test_is_sensitive_non_sensitive(self):
        """Test that non-sensitive fields are not flagged."""
        assert SecurityUtils._is_sensitive("username") is False
        assert SecurityUtils._is_sensitive("name") is False
        assert SecurityUtils._is_sensitive("age") is False
        assert SecurityUtils._is_sensitive("city") is False


class TestSecurityUtilsSanitizeLogData:
    """Test cases for log data sanitization."""

    def test_sanitize_log_data_dict(self):
        """Test sanitizing dictionary for logging."""
        data = {
            "action": "login",
            "username": "john",
            "password": "secret123",
        }
        sanitized = SecurityUtils.sanitize_log_data(data)

        assert sanitized["action"] == "login"
        assert sanitized["username"] == "john"
        assert sanitized["password"] != "secret123"

    def test_sanitize_log_data_specific_fields(self):
        """Test sanitizing specific fields only."""
        data = {
            "password": "secret123",
            "api_key": "key123",
            "name": "John",
        }
        sanitized = SecurityUtils.sanitize_log_data(
            data, fields=["api_key"]
        )

        assert sanitized["password"] == "secret123"  # Not in fields list
        assert sanitized["api_key"] != "key123"
        assert sanitized["name"] == "John"

    def test_sanitize_log_data_preserve_keys(self):
        """Test preserving certain keys during sanitization."""
        data = {
            "password": "secret123",
            "app_password": "app_secret",
        }
        sanitized = SecurityUtils.sanitize_log_data(
            data, preserve_keys=["app_password"]
        )

        assert sanitized["password"] != "secret123"
        assert sanitized["app_password"] == "app_secret"


class TestSecurityUtilsMaskingPatterns:
    """Test cases for database and URL masking."""

    def test_mask_database_url(self):
        """Test masking database connection URLs."""
        url = "postgresql://user:password123@localhost:5432/mydb"
        masked = SecurityUtils.mask_database_url(url)

        assert "password123" not in masked
        assert "user" in masked  # Username should still be visible
        assert "localhost" in masked
        assert masked.count("*") > 0

    def test_mask_query_params(self):
        """Test masking query parameters."""
        params = {
            "api_key": "secret_key_12345",
            "username": "john",
            "password": "pass123",
        }
        masked = SecurityUtils.mask_query_params(params)

        assert masked["api_key"] != "secret_key_12345"
        assert masked["username"] == "john"
        assert masked["password"] != "pass123"

    def test_mask_request_headers(self):
        """Test masking HTTP headers."""
        headers = {
            "Authorization": "Bearer token_12345",
            "X-API-Key": "secret_key",
            "Content-Type": "application/json",
        }
        masked = SecurityUtils.mask_request_headers(headers)

        assert masked["Authorization"] != "Bearer token_12345"
        assert masked["X-API-Key"] != "secret_key"
        assert masked["Content-Type"] == "application/json"


class TestSecurityUtilsMaskingJSON:
    """Test cases for JSON string masking."""

    def test_mask_json_string(self):
        """Test masking sensitive values in JSON string."""
        json_str = '{"username": "john", "password": "secret123", "api_key": "key123"}'
        masked = SecurityUtils.mask_json_string(json_str)

        assert "secret123" not in masked
        assert "key123" not in masked
        assert '"username": "john"' in masked  # Non-sensitive preserved

    def test_mask_json_string_invalid(self):
        """Test handling of invalid JSON."""
        invalid_json = "not valid json"
        result = SecurityUtils.mask_json_string(invalid_json)
        assert result == invalid_json  # Returned as-is


class TestSecurityUtilsAuditLog:
    """Test cases for audit log creation."""

    def test_create_audit_log_entry(self):
        """Test creating audit log entry."""
        entry = SecurityUtils.create_audit_log_entry(
            action="create_query",
            resource="golden_query",
            user_id="user123",
            timestamp="2024-01-01T00:00:00Z",
            details={"query_text": "SELECT * FROM table", "api_key": "secret"},
        )

        assert entry["action"] == "create_query"
        assert entry["resource"] == "golden_query"
        assert entry["user_id"] == "user123"
        assert entry["details"]["api_key"] != "secret"


class TestSecurityUtilsPII:
    """Test cases for PII detection."""

    def test_is_pii_email(self):
        """Test PII detection for email addresses."""
        assert SecurityUtils.is_pii("john@example.com") is True
        assert SecurityUtils.is_pii("jane.doe@company.co.uk") is True

    def test_is_pii_phone(self):
        """Test PII detection for phone numbers."""
        assert SecurityUtils.is_pii("555-123-4567") is True
        assert SecurityUtils.is_pii("(555) 123-4567") is True
        assert SecurityUtils.is_pii("+1-555-123-4567") is True

    def test_is_pii_credit_card(self):
        """Test PII detection for credit cards."""
        assert SecurityUtils.is_pii("1234-5678-9012-3456") is True
        assert SecurityUtils.is_pii("4532015112830366") is True

    def test_is_pii_non_pii(self):
        """Test that normal strings are not detected as PII."""
        assert SecurityUtils.is_pii("John Doe") is False
        assert SecurityUtils.is_pii("United States") is False


class TestSecurityUtilsMaskStats:
    """Test cases for mask statistics."""

    def test_get_mask_stats(self):
        """Test getting statistics about sensitive fields."""
        data = {
            "username": "john",
            "password": "secret",
            "email": "john@example.com",
            "api_key": "key123",
        }
        stats = SecurityUtils.get_mask_stats(data)

        assert stats["total_keys"] == 4
        assert stats["sensitive_keys"] == 3
        assert "password" in stats["sensitive_fields"]
        assert "email" in stats["sensitive_fields"]
        assert "api_key" in stats["sensitive_fields"]

    def test_get_mask_stats_nested(self):
        """Test mask stats with nested data."""
        data = {
            "user": {
                "username": "john",
                "password": "secret",
            },
            "config": {
                "api_key": "key123",
            },
        }
        stats = SecurityUtils.get_mask_stats(data)

        assert stats["total_keys"] >= 3
        assert stats["sensitive_keys"] >= 2


class TestSecurityUtilsIntegration:
    """Integration tests for security utilities."""

    def test_complete_workflow(self):
        """Test complete masking workflow."""
        request_data = {
            "question": "What is the status?",
            "mode": "ci",
            "db_config": {
                "api_key": "secret_key_12345",
                "password": "pass123",
            },
        }

        # Mask for logging
        masked_for_log = SecurityUtils.mask_dict(request_data)
        # db_config itself is not sensitive, but its contents are
        assert isinstance(masked_for_log["db_config"], dict)
        assert masked_for_log["db_config"]["api_key"] != "secret_key_12345"
        assert masked_for_log["question"] == "What is the status?"

        # Sanitize for storage
        sanitized = SecurityUtils.sanitize_log_data(request_data)
        assert sanitized["db_config"]["api_key"] != "secret_key_12345"

    def test_extract_sensitive_fields(self):
        """Test extracting sensitive fields."""
        data = {
            "name": "John",
            "password": "secret",
            "email": "john@example.com",
            "api_token": "token123",
        }
        sensitive = SecurityUtils.extract_sensitive_fields(data)

        assert "password" in sensitive["found"]
        assert "email" in sensitive["found"]
        assert "api_token" in sensitive["found"]
        assert "name" not in sensitive["found"]
