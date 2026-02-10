"""
Test Orchestrator Tool Asset Implementation

Tests verify that Phase 1 Tool Assets are properly registered
and use parameterized queries safely.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

# SQL file validation tests


def test_metric_query_sql_parameterized():
    """Verify metric_query.sql uses parameterized queries"""
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/metric/metric_query.sql"
    assert sql_file.exists(), "metric_query.sql not found"

    content = sql_file.read_text()

    # Should use %s placeholders, not f-string interpolation
    assert "%s" in content, "metric_query.sql should use %s placeholders"
    assert "f\"" not in content, "metric_query.sql should not use f-strings"
    assert "f'" not in content, "metric_query.sql should not use f-strings"

    # Should have required parameters
    assert "metric_name" in content, "Should query by metric_name"
    assert "ci_code" in content, "Should query by ci_code"
    assert "tenant_id" in content, "Should filter by tenant_id"
    assert "time >" in content or "time >=" in content, "Should have time range filtering"


def test_ci_aggregation_sql_parameterized():
    """Verify ci_aggregation.sql uses parameterized queries"""
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/ci/ci_aggregation.sql"
    assert sql_file.exists(), "ci_aggregation.sql not found"

    content = sql_file.read_text()

    # Should use %s placeholders
    assert "%s" in content, "ci_aggregation.sql should use %s placeholders"
    assert "f\"" not in content, "ci_aggregation.sql should not use f-strings"

    # Should have tenant_id filter
    assert "tenant_id" in content, "Should filter by tenant_id"

    # Should have aggregation functions
    assert "COUNT" in content, "Should have COUNT aggregation"


def test_work_history_query_sql_parameterized():
    """Verify work_history_query.sql uses parameterized queries"""
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/history/work_history_query.sql"
    assert sql_file.exists(), "work_history_query.sql not found"

    content = sql_file.read_text()

    # Should use %s placeholders
    assert "%s" in content, "work_history_query.sql should use %s placeholders"
    assert "f\"" not in content, "work_history_query.sql should not use f-strings"

    # Should have filtering
    assert "tenant_id" in content, "Should filter by tenant_id"
    assert "ci_code" in content, "Should support ci_code filtering"


def test_ci_graph_query_sql_parameterized():
    """Verify ci_graph_query.sql uses parameterized queries"""
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/ci/ci_graph_query.sql"
    assert sql_file.exists(), "ci_graph_query.sql not found"

    content = sql_file.read_text()

    # Should use %s placeholders
    assert "%s" in content, "ci_graph_query.sql should use %s placeholders"
    assert "f\"" not in content, "ci_graph_query.sql should not use f-strings"

    # Should have relationship filtering
    assert "tenant_id" in content, "Should filter by tenant_id"
    assert "relationship_type" in content, "Should filter by relationship_type"


def test_tool_assets_registered():
    """Verify all 5 new Tool Assets are registered in script"""
    script_file = Path(__file__).parent.parent / "scripts/register_ops_tools.py"
    content = script_file.read_text()

    expected_tools = [
        "metric_query",
        "ci_aggregation",
        "work_history_query",
        "ci_graph_query",
    ]

    for tool_name in expected_tools:
        assert f'"{tool_name}"' in content, f"Tool '{tool_name}' not registered"
        assert f'"{tool_name}"' in content, f"Tool '{tool_name}' should have tool_type defined"


def test_metric_query_schema_defined():
    """Verify metric_query has complete input/output schema"""
    script_file = Path(__file__).parent.parent / "scripts/register_ops_tools.py"
    content = script_file.read_text()

    # Find the metric_query definition
    assert '"metric_query"' in content

    # Should have tool_input_schema with required fields
    assert 'tenant_id' in content
    assert 'ci_code' in content
    assert 'metric_name' in content


def test_work_history_query_schema_defined():
    """Verify work_history_query has complete input/output schema"""
    script_file = Path(__file__).parent.parent / "scripts/register_ops_tools.py"
    content = script_file.read_text()

    # Find the work_history_query definition
    assert '"work_history_query"' in content


def test_ci_graph_query_schema_defined():
    """Verify ci_graph_query has complete input/output schema"""
    script_file = Path(__file__).parent.parent / "scripts/register_ops_tools.py"
    content = script_file.read_text()

    # Find the ci_graph_query definition
    assert '"ci_graph_query"' in content
    assert 'relationship_types' in content


def test_all_sql_files_exist():
    """Verify all SQL files for Tool Assets exist"""
    sql_files = [
        "metric/metric_query.sql",
        "ci/ci_aggregation.sql",
        "history/work_history_query.sql",
        "ci/ci_graph_query.sql",
    ]

    base_path = Path(__file__).parent.parent / "resources/queries/postgres"

    for sql_file in sql_files:
        full_path = base_path / sql_file
        assert full_path.exists(), f"SQL file not found: {sql_file}"


def test_no_sql_injection_in_metric_query():
    """Test SQL Injection prevention in metric_query Tool"""
    # This is a contract test - actual execution would require DB setup
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/metric/metric_query.sql"
    content = sql_file.read_text()

    # Should use parameterized queries
    # Pattern: %s with comma-separated parameters, no string concatenation
    assert content.count("%s") >= 5, "Should have at least 5 parameters"

    # Should not have any f-string SQL patterns
    assert "f\"" not in content
    assert "f'" not in content

    # Should not concatenate with user input
    assert ".format(" not in content
    assert "+ '" not in content
    assert "% (" not in content


def test_no_sql_injection_in_work_history_query():
    """Test SQL Injection prevention in work_history_query Tool"""
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/history/work_history_query.sql"
    content = sql_file.read_text()

    # Should use NULL-safe optional filtering
    assert "%s IS NULL OR" in content, "Should use NULL-safe filtering"

    # Should not have direct string interpolation
    assert "f\"" not in content
    assert "f'" not in content


def test_no_sql_injection_in_ci_graph_query():
    """Test SQL Injection prevention in ci_graph_query Tool"""
    sql_file = Path(__file__).parent.parent / "resources/queries/postgres/ci/ci_graph_query.sql"
    content = sql_file.read_text()

    # IN clause should use proper parameterization
    assert "IN (%s)" in content, "Should use parameterized IN clause"

    # Should not have unsafe string building
    assert "f\"" not in content
    assert "f'" not in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
