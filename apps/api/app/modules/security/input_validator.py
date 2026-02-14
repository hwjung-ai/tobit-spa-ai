"""
Input Validation and Security Hardening for API
Prevents: XSS, SQL Injection, Command Injection, Path Traversal
"""

import re
import json
from typing import Any, Optional, Dict, List, Pattern
from pydantic import BaseModel, validator


class ValidationRules(BaseModel):
    """Input validation rules."""

    input_type: str = "string"  # string, number, boolean, email, url, json, sql
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_characters: Optional[List[str]] = None
    blocked_patterns: Optional[List[str]] = None
    trim: bool = True
    lowercase: bool = False


class ValidationResult(BaseModel):
    """Validation result."""

    valid: bool
    error: Optional[str] = None
    sanitized_value: Optional[str] = None


# Dangerous SQL keywords pattern
DANGEROUS_SQL_PATTERN = re.compile(
    r';\s*(DELETE|DROP|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|EXEC|EXECUTE)|'
    r'--\s*(SELECT|DELETE|DROP)|'
    r'/\*.*?\*/'
    r'|UNION\s+SELECT'
    r"|OR\s+1\s*=\s*1"
    r"|'\s*(OR|AND)\s*'",
    re.IGNORECASE
)

# XSS patterns
XSS_PATTERNS = [
    re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE),
    re.compile(r'on\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE),
    re.compile(r'on\w+\s*=\s*[^\s>]*', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.[\\/]|[\\/]\.\.[\\/]')

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    re.compile(r'[;&|`$(){}[]<>]'),
    re.compile(r'(?:;|\||&|\$\(|`|>|<|&&|\|\|)'),
]


def validate_input(value: Any, rules: ValidationRules) -> ValidationResult:
    """Validate input against security rules."""

    if not isinstance(value, str) and rules.input_type != "number":
        return ValidationResult(
            valid=False,
            error="Invalid input type"
        )

    str_value = str(value).strip() if rules.trim else str(value)

    # Empty string check
    if not str_value and rules.min_length is None:
        return ValidationResult(
            valid=False,
            error="Input cannot be empty"
        )

    # Length validation
    if rules.min_length and len(str_value) < rules.min_length:
        return ValidationResult(
            valid=False,
            error=f"Minimum {rules.min_length} characters required"
        )

    if rules.max_length and len(str_value) > rules.max_length:
        return ValidationResult(
            valid=False,
            error=f"Maximum {rules.max_length} characters allowed"
        )

    # Pattern validation
    if rules.pattern:
        try:
            if not re.match(rules.pattern, str_value):
                return ValidationResult(
                    valid=False,
                    error="Input does not match required pattern"
                )
        except re.error:
            return ValidationResult(
                valid=False,
                error="Invalid regex pattern"
            )

    # Blocked patterns check
    if rules.blocked_patterns:
        for blocked_pattern in rules.blocked_patterns:
            try:
                if re.search(blocked_pattern, str_value):
                    return ValidationResult(
                        valid=False,
                        error="Input contains invalid characters or patterns"
                    )
            except re.error:
                pass

    # Type-specific validation
    if rules.input_type == "email":
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', str_value):
            return ValidationResult(
                valid=False,
                error="Invalid email format"
            )

    elif rules.input_type == "url":
        if not re.match(r'^https?://', str_value):
            return ValidationResult(
                valid=False,
                error="Invalid URL format (must start with http:// or https://)"
            )

    elif rules.input_type == "json":
        try:
            json.loads(str_value)
        except json.JSONDecodeError:
            return ValidationResult(
                valid=False,
                error="Invalid JSON format"
            )

    elif rules.input_type == "sql":
        if contains_dangerous_sql_patterns(str_value):
            return ValidationResult(
                valid=False,
                error="Input contains potentially dangerous SQL patterns"
            )

    elif rules.input_type == "number":
        try:
            float(str_value)
        except ValueError:
            return ValidationResult(
                valid=False,
                error="Input must be a valid number"
            )

    return ValidationResult(
        valid=True,
        sanitized_value=str_value
    )


def contains_dangerous_sql_patterns(input_text: str) -> bool:
    """Check if input contains dangerous SQL patterns."""
    return bool(DANGEROUS_SQL_PATTERN.search(input_text))


def sanitize_input(
    value: str,
    strip_html: bool = True,
    strip_scripts: bool = True,
    strip_sql: bool = True,
    trim: bool = True,
    remove_null_bytes: bool = True,
) -> str:
    """Sanitize input to prevent XSS and injection attacks."""

    result = value

    # Remove null bytes
    if remove_null_bytes:
        result = result.replace('\0', '')

    # Trim whitespace
    if trim:
        result = result.strip()

    # Strip HTML tags
    if strip_html:
        result = re.sub(r'<[^>]*>', '', result)

    # Strip scripts
    if strip_scripts:
        for pattern in XSS_PATTERNS:
            result = pattern.sub('', result)

    # Strip SQL injection patterns
    if strip_sql:
        result = re.sub(r';\s*(?=SELECT|DELETE|DROP|INSERT|UPDATE)', ' ', result, flags=re.IGNORECASE)
        result = re.sub(r'--[^\n]*', '', result)
        result = re.sub(r'/\*.*?\*/', '', result)

    return result


def is_valid_endpoint_path(path: str) -> bool:
    """Validate endpoint path format."""

    if not path.startswith('/'):
        return False

    if not re.match(r'^/[a-zA-Z0-9\/_-]*$', path):
        return False

    if path != '/' and path.endswith('/'):
        return False

    if '//' in path:
        return False

    return True


def is_valid_identifier(name: str) -> bool:
    """Validate variable/identifier names."""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def escape_sql_string(value: str) -> str:
    """Escape SQL string (parameterized queries are preferred)."""
    # This is a fallback - parameterized queries should be used instead
    return value.replace("'", "''")


def contains_path_traversal(path: str) -> bool:
    """Check for path traversal attempts."""
    return bool(PATH_TRAVERSAL_PATTERN.search(path))


def contains_command_injection(value: str) -> bool:
    """Check for command injection patterns."""
    for pattern in COMMAND_INJECTION_PATTERNS:
        if pattern.search(value):
            return True
    return False


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, window_seconds: int = 60, max_attempts: int = 10):
        self.window_ms = window_seconds * 1000
        self.max_attempts = max_attempts
        self.attempts: Dict[str, List[int]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed."""
        import time

        now_ms = int(time.time() * 1000)
        attempts = self.attempts.get(key, [])

        # Filter out old attempts
        recent_attempts = [t for t in attempts if now_ms - t < self.window_ms]

        if len(recent_attempts) >= self.max_attempts:
            return False

        recent_attempts.append(now_ms)
        self.attempts[key] = recent_attempts

        return True

    def get_remaining_attempts(self, key: str) -> int:
        """Get remaining attempts."""
        import time

        now_ms = int(time.time() * 1000)
        attempts = self.attempts.get(key, [])
        recent_attempts = [t for t in attempts if now_ms - t < self.window_ms]

        return max(0, self.max_attempts - len(recent_attempts))

    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limiter."""
        if key:
            self.attempts.pop(key, None)
        else:
            self.attempts.clear()
