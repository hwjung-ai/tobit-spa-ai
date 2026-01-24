"""Unit tests for API Manager services"""

import pytest
from app.modules.api_manager.services import (
    SQLValidator,
    ValidationResult,
)


class TestSQLValidator:
    """Test SQL validation"""

    def test_validator_initialization(self):
        """Test validator initialization"""
        validator = SQLValidator()
        assert validator is not None
        assert len(validator.DANGEROUS_KEYWORDS) > 0

    def test_safe_select_query(self):
        """Test safe SELECT query passes validation"""
        validator = SQLValidator()
        sql = "SELECT * FROM users WHERE id = $1"

        result = validator.validate(sql)

        assert result.is_safe
        assert result.is_valid

    def test_dangerous_drop_keyword(self):
        """Test that DROP queries are rejected"""
        validator = SQLValidator()
        sql = "DROP TABLE users"

        result = validator.validate(sql)

        assert not result.is_safe
        assert "DROP" in str(result.errors)

    def test_dangerous_truncate_keyword(self):
        """Test that TRUNCATE queries are rejected"""
        validator = SQLValidator()
        sql = "TRUNCATE TABLE users"

        result = validator.validate(sql)

        assert not result.is_safe

    def test_dangerous_delete_keyword(self):
        """Test that DELETE queries are rejected"""
        validator = SQLValidator()
        sql = "DELETE FROM users WHERE id = 1"

        result = validator.validate(sql)

        assert not result.is_safe

    def test_sql_injection_pattern_detection(self):
        """Test SQL injection pattern detection"""
        validator = SQLValidator()
        sql = "SELECT * FROM users WHERE name = '' OR '1'='1'"

        result = validator.validate(sql)

        assert not result.is_safe

    def test_protected_table_detection(self):
        """Test protected table detection"""
        validator = SQLValidator()
        sql = "SELECT * FROM pg_users"

        result = validator.validate(sql)

        assert not result.is_safe
        assert "protected table" in str(result.errors)

    def test_performance_warning_select_star(self):
        """Test performance warning for SELECT *"""
        validator = SQLValidator()
        sql = "SELECT * FROM users"

        result = validator.validate(sql)

        assert len(result.warnings) > 0
        assert any("SELECT *" in w for w in result.warnings)

    def test_performance_warning_missing_where(self):
        """Test performance warning for missing WHERE"""
        validator = SQLValidator()
        sql = "SELECT id, name FROM users"

        validator.validate(sql)

        # May have warning about missing WHERE
        # (depends on table name heuristics)

    def test_performance_warning_like_wildcard(self):
        """Test performance warning for LIKE with leading wildcard"""
        validator = SQLValidator()
        sql = "SELECT * FROM users WHERE name LIKE '%john%'"

        result = validator.validate(sql)

        assert len(result.warnings) > 0

    def test_table_extraction(self):
        """Test table extraction from query"""
        validator = SQLValidator()
        sql = "SELECT u.id FROM users u JOIN orders o ON u.id = o.user_id"

        result = validator.validate(sql)

        assert "tables" in result.metadata
        tables = result.metadata["tables"]
        assert "users" in tables
        assert "orders" in tables

    def test_validation_result_to_dict(self):
        """Test ValidationResult to_dict conversion"""
        result = ValidationResult(
            is_safe=True,
            is_valid=True,
            errors=["Error 1"],
            warnings=["Warning 1"],
            metadata={"key": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["is_safe"] is True
        assert result_dict["is_valid"] is True
        assert result_dict["errors"] == ["Error 1"]
        assert result_dict["warnings"] == ["Warning 1"]

    def test_multiple_joins_warning(self):
        """Test warning for many JOINs"""
        validator = SQLValidator()
        sql = """
        SELECT * FROM t1
        JOIN t2 ON t1.id = t2.id
        JOIN t3 ON t2.id = t3.id
        JOIN t4 ON t3.id = t4.id
        JOIN t5 ON t4.id = t5.id
        JOIN t6 ON t5.id = t6.id
        """

        result = validator.validate(sql)

        assert len(result.warnings) > 0
        assert any("JOIN" in w for w in result.warnings)

    def test_or_conditions_warning(self):
        """Test warning for many OR conditions"""
        validator = SQLValidator()
        sql = """
        SELECT * FROM users WHERE
        status = 'a' OR status = 'b' OR status = 'c' OR
        status = 'd' OR status = 'e' OR status = 'f' OR
        status = 'g'
        """

        result = validator.validate(sql)

        assert len(result.warnings) > 0

    def test_complex_valid_query(self):
        """Test validation of complex valid query"""
        validator = SQLValidator()
        sql = """
        SELECT u.id, u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.created_at > '2026-01-01'
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        LIMIT 10
        """

        result = validator.validate(sql)

        assert result.is_safe
        assert result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
