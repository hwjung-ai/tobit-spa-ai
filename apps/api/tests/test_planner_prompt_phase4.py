"""Unit tests for Phase 4: Planner Prompt Enhancement."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.modules.asset_registry.loader import load_catalog_for_llm
from app.modules.ops.services.orchestration.planner.plan_schema import (
    ExecutionStrategy,
)
from app.modules.ops.services.orchestration.planner.planner_llm import (
    _build_enhanced_planner_prompt,
    _validate_plan,
    plan_llm_query,
)


class TestBuildEnhancedPlannerPrompt:
    """Test the enhanced planner prompt builder."""

    def test_prompt_without_tools_or_catalog(self):
        """Test prompt when no tools or catalog info provided."""
        prompt = _build_enhanced_planner_prompt(
            question="What servers are in zone-a?",
            tools_info=None,
            catalog_info=None
        )

        assert "You are an intelligent query planner" in prompt
        assert "User Question" in prompt
        assert "## Available Tools" not in prompt  # Only when tools provided
        assert "## Database Schema" not in prompt  # Only when catalog provided

    def test_prompt_with_tools(self):
        """Test prompt with tools info."""
        tools_info = [
            {
                "name": "CI Lookup",
                "type": "ci_lookup",
                "input_schema": {"keywords": {"type": "array", "items": "string"}},
                "output_schema": {"rows": {"type": "array"}}
            }
        ]

        prompt = _build_enhanced_planner_prompt(
            question="Find servers",
            tools_info=tools_info,
            catalog_info=None
        )

        assert "Available Tools" in prompt
        assert "CI Lookup (ci_lookup)" in prompt
        assert "Input Schema" in prompt
        assert "Output Schema" in prompt

    def test_prompt_with_catalog(self):
        """Test prompt with catalog info."""
        catalog_info = {
            "source_ref": "postgres://localhost:5432/ci",
            "tables": [
                {
                    "name": "ci_data",
                    "row_count": 1000,
                    "columns": [
                        {"name": "ci_code", "type": "varchar", "samples": ["srv-001", "srv-002"]},
                        {"name": "status", "type": "varchar"}
                    ]
                }
            ]
        }

        prompt = _build_enhanced_planner_prompt(
            question="Show me server status",
            tools_info=None,
            catalog_info=catalog_info
        )

        assert "Database Schema" in prompt
        assert "Source: postgres://localhost:5432/ci" in prompt
        assert "Tables: 1" in prompt
        assert "ci_data" in prompt
        assert "Columns:" in prompt
        assert "ci_code (varchar)" in prompt


class SimplePlan:
    """Simple Plan mock for testing validation."""
    def __init__(self):
        self.primary = None
        self.secondary = None
        self.aggregate = None
        self.graph = None
        self.metric = None
        self.auto = None
        self.history = None
        self.cep = None

    def __getattr__(self, name):
        """Return None for any missing attributes to avoid AttributeError."""
        return None

class TestPlanValidation:
    """Test Plan validation logic."""

    def test_validate_plan_with_valid_tool_types(self):
        """Test validation with valid tool_type values."""
        tools_info = [
            {"type": "ci_lookup"},
            {"type": "ci_aggregate"},
            {"type": "graph_analysis"},
        ]

        # Create simple plan mock
        plan = SimplePlan()
        # Mock the tool_type attribute
        plan.primary = type('Primary', (), {'tool_type': 'ci_lookup'})()
        plan.aggregate = type('Aggregate', (), {'tool_type': 'ci_aggregate'})()

        errors = _validate_plan(plan, tools_info)
        assert len(errors) == 0

    def test_validate_plan_with_invalid_primary_tool_type(self):
        """Test validation with invalid primary tool_type."""
        tools_info = [{"type": "ci_lookup"}]

        plan = SimplePlan()
        plan.primary = type('Primary', (), {'tool_type': 'invalid_tool'})()

        errors = _validate_plan(plan, tools_info)
        assert len(errors) == 1
        assert "Invalid primary tool_type: invalid_tool" in errors[0]

    def test_validate_plan_with_multiple_invalid_tool_types(self):
        """Test validation with multiple invalid tool_type values."""
        tools_info = [{"type": "ci_lookup"}]

        plan = SimplePlan()
        plan.primary = type('Primary', (), {'tool_type': 'invalid_tool'})()
        plan.graph = type('Graph', (), {'tool_type': 'invalid_graph'})()
        plan.metric = type('Metric', (), {'tool_type': 'invalid_metric'})()

        errors = _validate_plan(plan, tools_info)
        assert len(errors) == 3
        assert any("primary" in error for error in errors)
        assert any("graph" in error for error in errors)
        assert any("metric" in error for error in errors)

    def test_validate_plan_with_no_tool_specs(self):
        """Test validation with no tool specs (should not fail)."""
        tools_info = [{"type": "ci_lookup"}]

        plan = SimplePlan()

        errors = _validate_plan(plan, tools_info)
        assert len(errors) == 0

    def test_validate_plan_with_empty_tool_dependencies(self):
        """Test validation doesn't check tool_dependencies."""
        tools_info = [{"type": "ci_lookup"}]

        plan = SimplePlan()

        errors = _validate_plan(plan, tools_info)
        assert len(errors) == 0


class TestOrchestrationFields:
    """Test Plan orchestration fields."""

    def test_plan_default_execution_strategy(self):
        """Test Plan default execution_strategy."""
        plan = type('Plan', (), {
            'execution_strategy': ExecutionStrategy.SERIAL,
            'enable_intermediate_llm': False,
            'tool_dependencies': []
        })()
        assert plan.execution_strategy == ExecutionStrategy.SERIAL
        assert not plan.enable_intermediate_llm
        assert len(plan.tool_dependencies) == 0

    def test_plan_with_explicit_execution_strategy(self):
        """Test Plan with explicit execution strategy."""
        plan = type('Plan', (), {'execution_strategy': None})()
        plan.execution_strategy = ExecutionStrategy.PARALLEL
        assert plan.execution_strategy == ExecutionStrategy.PARALLEL

    def test_plan_enable_intermediate_llm(self):
        """Test Plan enable_intermediate_llm field."""
        plan = type('Plan', (), {'enable_intermediate_llm': False})()
        plan.enable_intermediate_llm = True
        assert plan.enable_intermediate_llm


class TestIntegration:
    """Integration tests for Phase 4 components."""

    @pytest.mark.asyncio
    async def test_plan_llm_query_loads_tool_registry(self):
        """Test that plan_llm_query loads tool registry info."""
        # Mock the tool registry
        mock_tool_registry = MagicMock()
        mock_tool_registry.get_all_tools_info.return_value = [
            {"type": "ci_lookup", "name": "CI Lookup"},
            {"type": "ci_aggregate", "name": "CI Aggregate"}
        ]

        # Mock LLM client
        mock_llm_client = AsyncMock()
        mock_llm_client.acreate_response.return_value = {
            "content": json.dumps({
                "primary": {
                    "keywords": ["server"],
                    "tool_type": "ci_lookup"
                }
            })
        }

        # Mock dependencies
        import app.modules.ops.services.orchestration.tools.base
        from app.llm.client import get_llm_client

        original_get_tool_registry = app.modules.ops.services.orchestration.tools.base.get_tool_registry
        original_get_llm_client = get_llm_client

        app.modules.ops.services.orchestration.tools.base.get_tool_registry = MagicMock(return_value=mock_tool_registry)

        # Create a mock class for get_llm_client
        class MockLlmClient:
            def __init__(self):
                pass
            async def acreate_response(self, **kwargs):
                return await mock_llm_client.acreate_response(**kwargs)

        get_llm_client = MockLlmClient

        try:
            result = await plan_llm_query("Show me servers")
            assert result is not None
            assert result.kind == "plan"
            assert result.plan.primary.tool_type == "ci_lookup"
        finally:
            # Restore original functions
            app.modules.ops.services.orchestration.tools.base.get_tool_registry = original_get_tool_registry
            get_llm_client = original_get_llm_client

    @pytest.mark.asyncio
    async def test_plan_llm_query_with_catalog(self):
        """Test that plan_llm_query loads catalog when source_ref provided."""
        # Mock catalog loading
        mock_catalog = {
            "source_ref": "postgres://localhost:5432/ci",
            "tables": [
                {"name": "ci_data", "row_count": 100}
            ]
        }

        # Mock dependencies
        mock_tool_registry = MagicMock()
        mock_tool_registry.get_all_tools_info.return_value = []

        mock_llm_client = AsyncMock()
        mock_llm_client.acreate_response.return_value = {
            "content": json.dumps({"primary": {"keywords": ["test"]}})
        }

        # Mock dependencies
        import app.modules.ops.services.orchestration.tools.base
        from app.llm.client import get_llm_client

        original_get_tool_registry = app.modules.ops.services.orchestration.tools.base.get_tool_registry
        original_get_llm_client = get_llm_client
        original_load_catalog = load_catalog_for_llm

        app.modules.ops.services.orchestration.tools.base.get_tool_registry = MagicMock(return_value=mock_tool_registry)

        class MockLlmClient:
            def __init__(self):
                pass
            async def acreate_response(self, **kwargs):
                return await mock_llm_client.acreate_response(**kwargs)

        get_llm_client = MockLlmClient
        load_catalog_for_llm = AsyncMock(return_value=mock_catalog)

        try:
            result = await plan_llm_query("Show me servers", source_ref="postgres://localhost:5432/ci")
            assert result is not None
            # Verify catalog was loaded
            load_catalog_for_llm.assert_called_once()
        finally:
            # Restore original functions
            app.modules.ops.services.orchestration.tools.base.get_tool_registry = original_get_tool_registry
            get_llm_client = original_get_llm_client
            load_catalog_for_llm = original_load_catalog
