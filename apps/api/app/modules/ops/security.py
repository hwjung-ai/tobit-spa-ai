"""
Security utilities for OPS module.

Provides comprehensive data masking and security features for sensitive information
handling across all OPS routes and logging systems.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Union


class SecurityUtils:
    """
    Security utilities for masking and sanitizing sensitive data.

    Supports masking of:
    - Database credentials and API keys
    - Personal identifiable information (PII)
    - Payment card information
    - Passwords and tokens
    - Authentication credentials
    """

    # Sensitive field patterns
    SENSITIVE_PATTERNS: Set[str] = {
        # Credentials and authentication
        "password", "passwd", "pwd", "secret", "private_key", "privatesecret",
        "api_key", "apikey", "apisecret", "api_token", "accesstoken",
        "refreshtoken", "bearer", "auth", "authorization", "credential",
        "credentials", "token", "session", "cookie", "jwt", "oauth",

        # Database and connection strings
        "connectionstring", "connection", "url", "host", "database",
        "dbpassword", "dbsecret", "dbuser", "dsn",

        # Financial information
        "creditcard", "ccnumber", "cc", "cardnumber", "cvv",
        "ssn", "sin", "taxid", "bankaccount", "routingnumber",

        # Personal information
        "email", "phone", "phonenumber", "mobile", "cell",
        "socialsecurity", "dateofbirth", "dob",
        "address", "street", "zip", "zipcode", "postalcode",

        # Access control
        "key", "access", "secret", "private", "encrypted",

        # Service tokens
        "slacktoken", "githubtoken", "awskey", "azurekey",
        "gcpkey", "stripekey", "twiliokey", "sendgridkey",

        # Headers and metadata
        "xapikey", "xsecret", "xtoken", "authorization",
        "xauthtoken", "xaccesstoken",
    }

    # Regex patterns for detecting sensitive data
    SENSITIVE_REGEX_PATTERNS: Dict[str, re.Pattern] = {
        # Credit card patterns
        "credit_card": re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"  # 1234-5678-9012-3456 or similar
        ),
        # Email pattern
        "email": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        # Phone pattern (basic)
        "phone": re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
        ),
        # API key pattern (generic)
        "api_key": re.compile(
            r"\b[A-Za-z0-9_-]{32,}\b"  # Long alphanumeric strings
        ),
        # UUID pattern
        "uuid": re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.IGNORECASE
        ),
    }

    # Mask characters
    MASK_CHAR: str = "*"
    MASK_LENGTH: int = 8

    @classmethod
    def mask_value(cls, value: Any, field_name: str = "") -> str:
        """
        Mask a sensitive value.

        Args:
            value: The value to mask
            field_name: Optional field name for pattern matching

        Returns:
            Masked string representation of the value
        """
        if value is None:
            return "null"

        if isinstance(value, bool):
            return str(value)

        if isinstance(value, (int, float)):
            # For numbers, show only first and last digit
            str_val = str(value)
            if len(str_val) <= 2:
                return cls.MASK_CHAR * len(str_val)
            return f"{str_val[0]}{'*' * (len(str_val) - 2)}{str_val[-1]}"

        str_value = str(value)

        # For short values, mask entirely
        if len(str_value) <= 4:
            return cls.MASK_CHAR * len(str_value)

        # For longer values, show first 2 and last 2 characters
        if len(str_value) <= 8:
            return f"{str_value[:2]}{'*' * (len(str_value) - 4)}{str_value[-2:]}"

        # For very long values, show first 4 and last 4 characters
        return f"{str_value[:4]}...{cls.MASK_CHAR * cls.MASK_LENGTH}...{str_value[-4:]}"

    @classmethod
    def _is_sensitive(cls, key: str) -> bool:
        """
        Check if a key represents sensitive information.

        Args:
            key: The key to check

        Returns:
            True if the key is sensitive, False otherwise
        """
        key_lower = key.lower().replace("_", "").replace("-", "")

        # Direct pattern matching
        for pattern in cls.SENSITIVE_PATTERNS:
            if pattern in key_lower:
                return True

        return False

    @classmethod
    def mask_dict(
        cls,
        data: Dict[str, Any],
        preserve_keys: Optional[List[str]] = None,
        depth: int = 0,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Recursively mask sensitive values in a dictionary.

        Args:
            data: Dictionary to mask
            preserve_keys: List of keys to preserve without masking
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Dictionary with masked sensitive values
        """
        if depth > max_depth:
            return data

        if not isinstance(data, dict):
            return data

        preserve_keys = preserve_keys or []
        masked = {}

        for key, value in data.items():
            if key in preserve_keys:
                masked[key] = value
                continue

            if cls._is_sensitive(key):
                masked[key] = cls.mask_value(value, key)
            elif isinstance(value, dict):
                masked[key] = cls.mask_dict(
                    value,
                    preserve_keys=preserve_keys,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            elif isinstance(value, (list, tuple)):
                masked[key] = cls.mask_list(
                    value,
                    preserve_keys=preserve_keys,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            else:
                masked[key] = value

        return masked

    @classmethod
    def mask_list(
        cls,
        items: Union[List[Any], tuple],
        preserve_keys: Optional[List[str]] = None,
        depth: int = 0,
        max_depth: int = 10,
    ) -> Union[List[Any], tuple]:
        """
        Recursively mask sensitive values in a list or tuple.

        Args:
            items: List or tuple to mask
            preserve_keys: List of keys to preserve without masking
            depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            List or tuple with masked sensitive values
        """
        if depth > max_depth:
            return items

        if not isinstance(items, (list, tuple)):
            return items

        preserve_keys = preserve_keys or []
        is_tuple = isinstance(items, tuple)
        masked: List[Any] = []

        for item in items:
            if isinstance(item, dict):
                masked.append(
                    cls.mask_dict(
                        item,
                        preserve_keys=preserve_keys,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                )
            elif isinstance(item, (list, tuple)):
                masked.append(
                    cls.mask_list(
                        item,
                        preserve_keys=preserve_keys,
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                )
            else:
                masked.append(item)

        return tuple(masked) if is_tuple else masked

    @classmethod
    def sanitize_log_data(
        cls,
        data: Any,
        fields: Optional[List[str]] = None,
        preserve_keys: Optional[List[str]] = None,
    ) -> Any:
        """
        Sanitize data for logging purposes.

        Removes or masks sensitive information to prevent leakage in logs.

        Args:
            data: Data to sanitize
            fields: Specific fields to sanitize (if None, all sensitive fields are masked)
            preserve_keys: Keys to preserve without masking

        Returns:
            Sanitized data safe for logging
        """
        preserve_keys = preserve_keys or []

        if isinstance(data, dict):
            if fields is None:
                # Mask all sensitive fields
                return cls.mask_dict(data, preserve_keys=preserve_keys)
            else:
                # Mask only specified fields
                sanitized = deepcopy(data)
                for field in fields:
                    if field in sanitized:
                        sanitized[field] = cls.mask_value(sanitized[field], field)
                return sanitized

        elif isinstance(data, (list, tuple)):
            return cls.mask_list(data, preserve_keys=preserve_keys)

        return data

    @classmethod
    def extract_sensitive_fields(cls, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract sensitive fields from data.

        Args:
            data: Dictionary to analyze

        Returns:
            Dictionary mapping keys to their values (for audit purposes)
        """
        sensitive: Dict[str, List[str]] = {
            "found": [],
            "types": [],
        }

        for key in data.keys():
            if cls._is_sensitive(key):
                sensitive["found"].append(key)

        return sensitive

    @classmethod
    def mask_string(cls, value: str, show_prefix: int = 2, show_suffix: int = 2) -> str:
        """
        Mask a string value.

        Args:
            value: String to mask
            show_prefix: Number of characters to show at the beginning
            show_suffix: Number of characters to show at the end

        Returns:
            Masked string
        """
        if not value:
            return ""

        if len(value) <= (show_prefix + show_suffix):
            return cls.MASK_CHAR * len(value)

        prefix = value[:show_prefix]
        suffix = value[-show_suffix:]
        middle = cls.MASK_CHAR * (len(value) - show_prefix - show_suffix)

        return f"{prefix}{middle}{suffix}"

    @classmethod
    def mask_query_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive query parameters.

        Args:
            params: Query parameters dictionary

        Returns:
            Masked query parameters
        """
        return cls.mask_dict(params)

    @classmethod
    def mask_request_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Mask sensitive HTTP headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            Masked headers
        """
        masked = {}
        for key, value in headers.items():
            if cls._is_sensitive(key):
                masked[key] = cls.mask_value(value, key)
            else:
                masked[key] = value
        return masked

    @classmethod
    def mask_database_url(cls, url: str) -> str:
        """
        Mask database connection URL.

        Masks password in URLs like: postgresql://user:password@host:5432/db

        Args:
            url: Database URL

        Returns:
            Masked URL
        """
        # Pattern: scheme://user:password@host:port/db
        pattern = r"(://[^:]+:)([^@]+)(@)"
        return re.sub(pattern, r"\1" + cls.MASK_CHAR * 8 + r"\3", url)

    @classmethod
    def mask_json_string(cls, json_str: str) -> str:
        """
        Mask sensitive values in JSON string.

        Args:
            json_str: JSON string to mask

        Returns:
            JSON string with masked sensitive values
        """
        try:
            data = json.loads(json_str)
            masked = cls.mask_dict(data)
            return json.dumps(masked)
        except (json.JSONDecodeError, TypeError):
            return json_str

    @classmethod
    def create_audit_log_entry(
        cls,
        action: str,
        resource: str,
        user_id: str,
        timestamp: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an audit log entry with masked sensitive data.

        Args:
            action: Action performed
            resource: Resource affected
            user_id: User performing action
            timestamp: When action occurred
            details: Additional details

        Returns:
            Audit log entry with masked data
        """
        entry = {
            "action": action,
            "resource": resource,
            "user_id": user_id,
            "timestamp": timestamp,
            "details": cls.mask_dict(details) if details else None,
        }
        return entry

    @classmethod
    def is_pii(cls, value: str) -> bool:
        """
        Check if a string contains personally identifiable information.

        Args:
            value: String to check

        Returns:
            True if PII detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        value_lower = value.lower()

        # Check against regex patterns
        for pattern_name, pattern in cls.SENSITIVE_REGEX_PATTERNS.items():
            if pattern.search(value):
                return True

        return False

    @classmethod
    def get_mask_stats(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about sensitive data in a dictionary.

        Args:
            data: Dictionary to analyze

        Returns:
            Statistics about sensitive fields found
        """
        stats = {
            "total_keys": 0,
            "sensitive_keys": 0,
            "sensitive_fields": [],
            "sensitive_values": [],
        }

        def analyze_dict(d: Dict[str, Any]) -> None:
            if not isinstance(d, dict):
                return

            for key, value in d.items():
                stats["total_keys"] += 1

                if cls._is_sensitive(key):
                    stats["sensitive_keys"] += 1
                    stats["sensitive_fields"].append(key)
                    stats["sensitive_values"].append(
                        {"field": key, "type": type(value).__name__}
                    )

                if isinstance(value, dict):
                    analyze_dict(value)

        analyze_dict(data)
        return stats
