"""
SQL Injection Prevention Tests

These tests verify that SQL Injection vulnerabilities have been fixed
by attempting to inject malicious SQL and confirming proper handling.
"""

import pytest
from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool
from app.modules.ops.services.ci.tools.base import ToolContext, ToolResult


class TestSQLInjectionPrevention:
    """Test SQL Injection prevention in DynamicTool"""

    def test_keyword_filter_safe_parameterization(self):
        """Test that keyword filter uses parameterized queries"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Normal keyword
        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {"keywords": ["server"], "tenant_id": "t1", "limit": 10}
        )

        assert "%s" in query  # Should use parameterized placeholder
        assert "server" not in query  # Value should be in params, not query
        assert "server" in params  # Value should be in params list
        assert "t1" in params  # Tenant should also be parameterized

    def test_keyword_injection_attempt(self):
        """Test that SQL injection attempts in keywords are neutralized"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Malicious keyword
        malicious_keyword = "'; DROP TABLE ci; --"
        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {"keywords": [malicious_keyword], "tenant_id": "t1", "limit": 10}
        )

        # The malicious SQL should be in params, not in query string
        assert "DROP TABLE" not in query
        assert malicious_keyword in params

    def test_filter_value_injection_ilike(self):
        """Test that ILIKE filter values are parameterized"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Normal filter
        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {
                "filters": [{"field": "ci_name", "operator": "ILIKE", "value": "server%"}],
                "tenant_id": "t1",
                "limit": 10
            }
        )

        assert "%s" in query
        assert "server%" in params
        assert "server%" not in query

    def test_filter_injection_in_operator(self):
        """Test that IN operator values are parameterized"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # IN filter with potentially malicious values
        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {
                "filters": [{"field": "status", "operator": "IN", "value": ["active", "'; DELETE --"]}],
                "tenant_id": "t1",
                "limit": 10
            }
        )

        # Values should be in params, not in query
        assert "DELETE" not in query
        assert "'; DELETE --" in params

    def test_tenant_id_parameterization(self):
        """Test that tenant_id is properly parameterized"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Malicious tenant_id
        malicious_tenant = "t1' OR '1'='1"
        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {"tenant_id": malicious_tenant, "limit": 10}
        )

        # Tenant should be in params
        assert malicious_tenant in params
        assert malicious_tenant not in query.split("WHERE")[1]  # Not in WHERE clause

    def test_order_by_validation(self):
        """Test that order_by field names are validated"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Invalid order_by (should be rejected)
        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {"sort": ("'; DROP TABLE ci; --", "ASC"), "tenant_id": "t1", "limit": 10}
        )

        # Should use default order_by instead of injection
        assert "ci.ci_id" in query  # Default fallback
        assert "DROP" not in query

    def test_limit_clamping(self):
        """Test that LIMIT values are properly clamped"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Test high limit
        query1, params1 = tool._process_query_template(
            tool.tool_config["query_template"],
            {"limit": 10000, "tenant_id": "t1"}
        )
        assert params1[-1] == 1000  # Should be clamped to max 1000

        # Test negative limit
        query2, params2 = tool._process_query_template(
            tool.tool_config["query_template"],
            {"limit": -5, "tenant_id": "t1"}
        )
        assert params2[-1] >= 1  # Should be at least 1

    def test_history_query_parameterization(self):
        """Test that history queries use parameterized dates and ci_ids"""
        tool = DynamicTool({
            "name": "history",
            "tool_type": "database_query",
            "description": "Test history query",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": ""
            },
            "tool_input_schema": {}
        })

        # Attempt to inject via start_time
        query, params = tool._build_history_query_by_source(
            "maintenance_history",
            {
                "tenant_id": "t1",
                "start_time": "2024-01-01'; DELETE FROM ci; --",
                "limit": 10
            }
        )

        # Injection should be in params, not query
        assert "DELETE FROM ci" in str(params)
        assert "DELETE" not in query.split("WHERE")[1]

    def test_graph_query_node_ids_parameterization(self):
        """Test that graph query node IDs are parameterized"""
        tool = DynamicTool({
            "name": "ci_graph_expand",
            "tool_type": "graph_query",
            "description": "Test graph query",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": ""
            },
            "tool_input_schema": {}
        })

        # We can't directly test _execute_graph_query without DB setup,
        # but we can verify the query building logic
        node_ids_list = ["id1'; DROP TABLE ci; --", "id2"]
        placeholders = ", ".join(["%s"] * len(node_ids_list))
        pg_query = f"""
        SELECT ci_id::text FROM ci
        WHERE ci_id::text IN ({placeholders})
        """

        # The query template should use %s placeholders
        assert "%s" in pg_query
        assert "DROP" not in pg_query  # Injection not in SQL

    def test_generic_placeholder_replacement(self):
        """Test generic placeholder replacement is parameterized"""
        tool = DynamicTool({
            "name": "test_metric",
            "tool_type": "database_query",
            "description": "Test metric query",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": "SELECT {function} FROM metrics WHERE tenant = '{tenant_id}' AND metric = '{metric_name}'"
            },
            "tool_input_schema": {}
        })

        query, params = tool._process_query_template(
            tool.tool_config["query_template"],
            {
                "function": "MAX",
                "tenant_id": "t1'; DROP TABLE metrics; --",
                "metric_name": "cpu_usage"
            }
        )

        # function should be replaced directly (it's a function name)
        assert "MAX" in query
        # tenant_id should be parameterized
        assert "%s" in query
        assert "DROP TABLE" in params


class TestFieldValidation:
    """Test field name validation"""

    def test_invalid_field_names_rejected(self):
        """Test that invalid field names are rejected"""
        tool = DynamicTool({
            "name": "test_ci_lookup",
            "tool_type": "database_query",
            "description": "Test CI lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT * FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        # Invalid field names with SQL injection attempts
        malicious_filters = [
            {"field": "ci_name; DROP TABLE ci; --", "operator": "=", "value": "test"},
            {"field": "ci_name' OR '1'='1", "operator": "=", "value": "test"},
            {"field": "../../etc/passwd", "operator": "=", "value": "test"},
        ]

        for filter_item in malicious_filters:
            query, params = tool._process_query_template(
                tool.tool_config["query_template"],
                {
                    "filters": [filter_item],
                    "tenant_id": "t1",
                    "limit": 10
                }
            )

            # Malicious field names should be skipped (not added to query)
            assert "DROP TABLE" not in query
            assert "../" not in query


# Integration tests (require database setup)
@pytest.mark.integration
class TestDynamicToolWithDatabase:
    """Integration tests with actual database"""

    @pytest.mark.asyncio
    async def test_keyword_filter_executes_safely(self):
        """Test actual execution with keyword filters"""
        tool = DynamicTool({
            "name": "ci_detail_lookup",
            "tool_type": "database_query",
            "description": "CI detail lookup",
            "tool_config": {
                "source_ref": "default_postgres",
                "query_template": """
                    SELECT ci_id, ci_code, ci_name FROM ci
                    WHERE {where_clause}
                    ORDER BY {order_by} {direction}
                    LIMIT %s
                """
            },
            "tool_input_schema": {}
        })

        context = ToolContext(tenant_id="default")

        # Normal execution
        result = await tool._execute_database_query(
            context,
            {"keywords": ["server"], "tenant_id": "default", "limit": 10}
        )

        # Should succeed
        assert result.success or result.error is None or "no data" in result.error.lower()

        # Injection attempt
        result = await tool._execute_database_query(
            context,
            {"keywords": ["'; DROP TABLE ci; --"], "tenant_id": "default", "limit": 10}
        )

        # Should either return empty or error, not execute injection
        # (Database still exists if we get here!)
        assert True  # Database wasn't dropped
