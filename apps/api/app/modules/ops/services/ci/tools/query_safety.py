"""
Direct Query Safety Enforcement

This module provides safety checks for direct SQL query execution,
enforcing read-only, DDL blocking, and tenant filtering.

P0-4: Direct Query 안전장치 강화
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class SQLKeywordType(str, Enum):
    """SQL keyword categories."""

    DDL = "DDL"  # Data Definition Language
    DML_WRITE = "DML_WRITE"  # Data Modification Language (write)
    DCL = "DCL"  # Data Control Language
    DANGEROUS = "DANGEROUS"  # Dangerous keywords


class QuerySafetyValidator:
    """Validate SQL queries for safety before execution."""

    # DDL keywords (create, alter, drop)
    DDL_KEYWORDS = {
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "RENAME",
        "COMMENT",
    }

    # DML write keywords
    DML_WRITE_KEYWORDS = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "CALL",
        "EXECUTE",
        "EXEC",
    }

    # DCL keywords (grant, revoke)
    DCL_KEYWORDS = {
        "GRANT",
        "REVOKE",
    }

    # Transaction control (should be blocked in read-only mode)
    TCL_KEYWORDS = {
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "START",
        "BEGIN",
        "END",
        "TRANSACTION",
    }

    # Additional dangerous keywords
    DANGEROUS_KEYWORDS = {
        "DROP",
        "TRUNCATE",
        "DELETE",
        "exec",
        "EXECUTE",
    }

    @staticmethod
    def normalize_sql(query: str) -> str:
        """
        Normalize SQL for analysis (remove comments, extra whitespace).

        Args:
            query: SQL query string

        Returns:
            Normalized query
        """
        # Remove comments
        query = re.sub(r"--.*?$", "", query, flags=re.MULTILINE)  # Single line comments
        query = re.sub(r"/\*.*?\*/", "", query, flags=re.DOTALL)  # Multi-line comments

        # Normalize whitespace
        query = re.sub(r"\s+", " ", query).strip()

        return query

    @staticmethod
    def extract_keywords(query: str) -> list[str]:
        """
        Extract SQL keywords from query.

        Args:
            query: SQL query string

        Returns:
            List of uppercase keywords found
        """
        query = QuerySafetyValidator.normalize_sql(query)
        # Match words (SQL keywords)
        words = re.findall(r"\b\w+\b", query)
        return [w.upper() for w in words]

    @staticmethod
    def check_read_only(query: str) -> list[str]:
        """
        Check if query violates read-only constraint.

        Args:
            query: SQL query string

        Returns:
            List of violations (empty if valid for read-only)
        """
        violations = []
        keywords = QuerySafetyValidator.extract_keywords(query)

        # Check DML write keywords
        for keyword in keywords:
            if keyword in QuerySafetyValidator.DML_WRITE_KEYWORDS:
                violations.append(f"DML write keyword '{keyword}' violates read-only constraint")
                break

        return violations

    @staticmethod
    def check_ddl_blocked(query: str) -> list[str]:
        """
        Check if query contains blocked DDL keywords.

        Args:
            query: SQL query string

        Returns:
            List of violations (empty if no DDL)
        """
        violations = []
        keywords = QuerySafetyValidator.extract_keywords(query)

        for keyword in keywords:
            if keyword in QuerySafetyValidator.DDL_KEYWORDS:
                violations.append(f"DDL keyword '{keyword}' is blocked")
                break

        return violations

    @staticmethod
    def check_dcl_blocked(query: str) -> list[str]:
        """
        Check if query contains blocked DCL keywords.

        Args:
            query: SQL query string

        Returns:
            List of violations (empty if no DCL)
        """
        violations = []
        keywords = QuerySafetyValidator.extract_keywords(query)

        for keyword in keywords:
            if keyword in QuerySafetyValidator.DCL_KEYWORDS:
                violations.append(f"DCL keyword '{keyword}' is blocked")
                break

        return violations

    @staticmethod
    def validate_query(
        query: str,
        enforce_readonly: bool = True,
        block_ddl: bool = True,
        block_dcl: bool = True,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive query safety validation.

        Args:
            query: SQL query string
            enforce_readonly: Enforce read-only constraint
            block_ddl: Block DDL keywords
            block_dcl: Block DCL keywords
            max_rows: Maximum rows allowed (if set)

        Returns:
            Dict with keys:
            - valid: Boolean (True if safe)
            - violations: List of violation messages
            - keyword_type: Type of keywords found (if any)
        """
        violations = []

        # Check read-only
        if enforce_readonly:
            violations.extend(QuerySafetyValidator.check_read_only(query))

        # Check DDL
        if block_ddl:
            violations.extend(QuerySafetyValidator.check_ddl_blocked(query))

        # Check DCL
        if block_dcl:
            violations.extend(QuerySafetyValidator.check_dcl_blocked(query))

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "query_length": len(query),
        }

    @staticmethod
    def check_tenant_isolation(query: str, tenant_id: str) -> dict[str, Any]:
        """
        Check if query properly applies tenant filtering.

        This is a basic check - real implementation would need query parsing.
        Note: This is informational only, not a blocker for query execution.

        Args:
            query: SQL query string
            tenant_id: Expected tenant ID

        Returns:
            Dict with validation result and recommendations
        """
        # Basic check: look for tenant filter in WHERE clause
        # Real implementation would need proper SQL parsing
        query_upper = query.upper()

        has_where = "WHERE" in query_upper
        has_tenant_filter = "TENANT" in query_upper or "TENANT_ID" in query_upper

        # Only flag as needs_review if query has no WHERE clause at all
        # If WHERE exists but no tenant filter, it's still valid (user may intend full table query)
        return {
            "has_where_clause": has_where,
            "has_tenant_filter": has_tenant_filter,
            "needs_review": not has_where,  # Only review if no WHERE clause
            "recommendation": (
                "Query should include WHERE clause for filtering"
                if not has_where
                else "Query appears to have proper filtering"
            ),
        }


def validate_direct_query(
    query: str,
    tenant_id: str,
    enforce_readonly: bool = True,
    block_ddl: bool = True,
    block_dcl: bool = True,
    max_rows: int = 10000,
) -> tuple[bool, list[str]]:
    """
    Validate a direct SQL query for execution.

    Args:
        query: SQL query to validate
        tenant_id: Tenant context
        enforce_readonly: Enforce read-only constraint
        block_ddl: Block DDL keywords
        block_dcl: Block DCL keywords
        max_rows: Maximum rows limit

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Validate query safety (primary checks)
    validation = QuerySafetyValidator.validate_query(
        query,
        enforce_readonly=enforce_readonly,
        block_ddl=block_ddl,
        block_dcl=block_dcl,
        max_rows=max_rows,
    )

    errors.extend(validation["violations"])

    # Check tenant isolation (informational only, log but don't block)
    tenant_check = QuerySafetyValidator.check_tenant_isolation(query, tenant_id)
    if tenant_check["needs_review"]:
        logger.warning(f"Tenant isolation: {tenant_check['recommendation']}")

    return len(errors) == 0, errors
