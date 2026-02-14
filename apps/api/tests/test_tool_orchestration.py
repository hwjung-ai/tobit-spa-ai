"""Unit tests for Tool Orchestration (Phase 5).

Tests for:
- DependencyAnalyzer: Dependency extraction and graph building
- DataFlowMapper: Output mapping and reference resolution
- ExecutionPlanner: Strategy determination and execution grouping
- ToolOrchestrator: Integration tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.modules.ops.services.orchestration.orchestrator.tool_orchestration import (
    DataFlowMapper,
    DependencyAnalyzer,
    ExecutionPlanner,
    IntermediateLLMDecider,
    ToolOrchestrator,
)
from app.modules.ops.services.orchestration.planner.plan_schema import (
    AggregateSpec,
    ExecutionStrategy,
    FilterSpec,
    GraphSpec,
    Intent,
    Plan,
    PrimarySpec,
    SecondarySpec,
    ToolDependency,
)
from app.modules.ops.services.orchestration.tools.base import ToolContext


class TestDependencyAnalyzer:
    """Test dependency extraction and analysis."""

    def test_extract_explicit_dependencies(self):
        """Should use explicit dependencies when provided."""
        plan = Plan(
            intent=Intent.LOOKUP,
            tool_dependencies=[
                ToolDependency(tool_id="primary", depends_on=[]),
                ToolDependency(tool_id="graph", depends_on=["primary"]),
            ]
        )
        analyzer = DependencyAnalyzer()
        deps = analyzer.extract_dependencies(plan)

        assert len(deps) == 2
        assert deps[0].tool_id == "primary"
        assert deps[1].tool_id == "graph"
        assert deps[1].depends_on == ["primary"]

    def test_infer_dependencies_from_plan_structure(self):
        """Should infer dependencies from Plan structure."""
        # Create a simple plan with primary and graph
        plan = MagicMock()
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"])
        plan.secondary = None
        plan.aggregate = None
        plan.graph = GraphSpec(depth=2)
        plan.metric = None

        analyzer = DependencyAnalyzer()
        deps = analyzer.extract_dependencies(plan)

        # Should create 2 dependencies (primary + graph)
        assert len(deps) == 2

        # Primary should have no dependencies
        primary_dep = next((d for d in deps if d.tool_id == "primary"), None)
        assert primary_dep is not None
        assert primary_dep.depends_on == []

        # Graph should depend on primary
        graph_dep = next((d for d in deps if d.tool_id == "graph"), None)
        assert graph_dep is not None
        assert "primary" in graph_dep.depends_on

    def test_infer_aggregate_depends_on_primary(self):
        """Should infer that aggregate depends on primary."""
        plan = MagicMock()
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"])
        plan.secondary = None
        plan.aggregate = AggregateSpec(metrics=["count"])
        plan.graph = None
        plan.metric = None

        analyzer = DependencyAnalyzer()
        deps = analyzer.extract_dependencies(plan)

        aggregate_dep = next((d for d in deps if d.tool_id == "aggregate"), None)
        assert aggregate_dep is not None
        assert "primary" in aggregate_dep.depends_on
        assert "ci_type_filter" in aggregate_dep.output_mapping

    def test_build_dependency_graph(self):
        """Should build adjacency list representation of dependencies."""
        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
            ToolDependency(tool_id="graph", depends_on=["primary"]),
        ]
        analyzer = DependencyAnalyzer()
        graph = analyzer.build_dependency_graph(dependencies)

        assert "primary" in graph
        assert graph["primary"] == set()
        assert graph["graph"] == {"primary"}

    def test_topological_sort_linear_chain(self):
        """Should sort linear dependency chain."""
        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="graph", depends_on=["primary"]),
            ToolDependency(tool_id="metric", depends_on=["graph"]),
        ]
        analyzer = DependencyAnalyzer()
        sorted_tools = analyzer.topological_sort(dependencies)

        assert sorted_tools == ["primary", "graph", "metric"]

    def test_topological_sort_parallel_branches(self):
        """Should handle independent branches."""
        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
            ToolDependency(tool_id="metric", depends_on=[]),
        ]
        analyzer = DependencyAnalyzer()
        sorted_tools = analyzer.topological_sort(dependencies)

        # All should be in result, but order doesn't matter for independent tools
        assert len(sorted_tools) == 3
        assert set(sorted_tools) == {"primary", "secondary", "metric"}

    def test_topological_sort_circular_dependency_error(self):
        """Should raise error for circular dependencies."""
        dependencies = [
            ToolDependency(tool_id="a", depends_on=["b"]),
            ToolDependency(tool_id="b", depends_on=["a"]),
        ]
        analyzer = DependencyAnalyzer()

        with pytest.raises(ValueError, match="Circular dependency"):
            analyzer.topological_sort(dependencies)


class TestDataFlowMapper:
    """Test output mapping and reference resolution."""

    def test_resolve_simple_reference(self):
        """Should resolve simple output.field references."""
        mapper = DataFlowMapper()

        output_mapping = {
            "search_keywords": "{primary.data.rows[0].ci_id}"
        }
        previous_results = {
            "primary": {
                "data": {
                    "rows": [{"ci_id": "srv-001"}]
                }
            }
        }

        resolved = mapper.resolve_mapping(output_mapping, previous_results)
        assert resolved["search_keywords"] == "srv-001"

    def test_resolve_nested_reference(self):
        """Should resolve nested field references."""
        mapper = DataFlowMapper()

        output_mapping = {
            "ci_type": "{primary.data.rows[0].attributes.type}"
        }
        previous_results = {
            "primary": {
                "data": {
                    "rows": [{
                        "attributes": {"type": "Server"}
                    }]
                }
            }
        }

        resolved = mapper.resolve_mapping(output_mapping, previous_results)
        assert resolved["ci_type"] == "Server"

    def test_resolve_array_index_reference(self):
        """Should handle array indexing in references."""
        mapper = DataFlowMapper()

        output_mapping = {
            "second_item": "{primary.data.rows[1].name}"
        }
        previous_results = {
            "primary": {
                "data": {
                    "rows": [
                        {"name": "first"},
                        {"name": "second"},
                        {"name": "third"}
                    ]
                }
            }
        }

        resolved = mapper.resolve_mapping(output_mapping, previous_results)
        assert resolved["second_item"] == "second"

    def test_resolve_literal_value(self):
        """Should handle literal values (not references)."""
        mapper = DataFlowMapper()

        output_mapping = {
            "limit": "100",
            "filter": "active"
        }
        previous_results = {}

        resolved = mapper.resolve_mapping(output_mapping, previous_results)
        assert resolved["limit"] == "100"
        assert resolved["filter"] == "active"

    def test_resolve_missing_tool_returns_none(self):
        """Should return None for references to missing tools."""
        mapper = DataFlowMapper()

        output_mapping = {
            "ci_id": "{missing_tool.data.rows[0].id}"
        }
        previous_results = {"primary": {}}

        resolved = mapper.resolve_mapping(output_mapping, previous_results)
        assert resolved["ci_id"] is None

    def test_resolve_missing_field_returns_none(self):
        """Should return None for references to missing fields."""
        mapper = DataFlowMapper()

        output_mapping = {
            "value": "{primary.data.rows[0].missing_field}"
        }
        previous_results = {
            "primary": {
                "data": {
                    "rows": [{"existing_field": "value"}]
                }
            }
        }

        resolved = mapper.resolve_mapping(output_mapping, previous_results)
        assert resolved["value"] is None


class TestExecutionPlanner:
    """Test execution strategy determination."""

    def test_parallel_strategy_for_independent_tools(self):
        """Should choose PARALLEL for independent tools."""
        planner = ExecutionPlanner()

        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
        ]

        strategy = planner.determine_strategy(dependencies)
        assert strategy == ExecutionStrategy.PARALLEL

    def test_serial_strategy_for_simple_chain(self):
        """Should choose SERIAL for simple dependency chain."""
        planner = ExecutionPlanner()

        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="graph", depends_on=["primary"]),
        ]

        strategy = planner.determine_strategy(dependencies)
        assert strategy == ExecutionStrategy.SERIAL

    def test_dag_strategy_for_complex_dependencies(self):
        """Should choose DAG for complex dependencies."""
        planner = ExecutionPlanner()

        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
            ToolDependency(tool_id="aggregate", depends_on=["primary", "secondary"]),
        ]

        strategy = planner.determine_strategy(dependencies)
        assert strategy == ExecutionStrategy.DAG

    def test_create_execution_groups_parallel(self):
        """Should create single group for PARALLEL execution."""
        planner = ExecutionPlanner()

        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
        ]

        groups = planner.create_execution_groups(dependencies, ExecutionStrategy.PARALLEL)
        assert len(groups) == 1
        assert set(groups[0]) == {"primary", "secondary"}

    def test_create_execution_groups_serial(self):
        """Should create one group per tool for SERIAL execution."""
        planner = ExecutionPlanner()

        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="graph", depends_on=["primary"]),
        ]

        groups = planner.create_execution_groups(dependencies, ExecutionStrategy.SERIAL)
        assert len(groups) == 2
        assert groups[0][0] == "primary"
        assert groups[1][0] == "graph"

    def test_create_execution_groups_dag(self):
        """Should group by levels for DAG execution."""
        planner = ExecutionPlanner()

        dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
            ToolDependency(tool_id="aggregate", depends_on=["primary"]),
            ToolDependency(tool_id="metric", depends_on=["aggregate"]),
        ]

        groups = planner.create_execution_groups(dependencies, ExecutionStrategy.DAG)
        # Level 0: primary, secondary
        # Level 1: aggregate
        # Level 2: metric
        assert len(groups) == 3
        assert set(groups[0]) == {"primary", "secondary"}
        assert groups[1][0] == "aggregate"
        assert groups[2][0] == "metric"


class TestIntermediateLLMDecider:
    """Test intermediate LLM decision making."""

    @pytest.mark.asyncio
    async def test_should_execute_next_yes_response(self):
        """Should return True for 'Yes' responses."""
        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.get_llm_client') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat_completion = AsyncMock(return_value={
                "content": "Yes, we should execute metric next because we need to get performance data."
            })
            mock_get_llm.return_value = mock_llm

            decider = IntermediateLLMDecider()
            result = await decider.should_execute_next(
                "metric",
                {"primary": {"data": {"rows": [{"ci_id": "srv-001"}]}}},
                "Show me servers and their metrics"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_should_execute_next_no_response(self):
        """Should return False for 'No' responses."""
        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.get_llm_client') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat_completion = AsyncMock(return_value={
                "content": "No, we have enough data already."
            })
            mock_get_llm.return_value = mock_llm

            decider = IntermediateLLMDecider()
            result = await decider.should_execute_next(
                "metric",
                {"primary": {"data": {"rows": []}}},
                "Show me servers"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_format_results(self):
        """Should format results for LLM consumption."""
        decider = IntermediateLLMDecider()

        previous_results = {
            "primary": {
                "data": {
                    "rows": [
                        {"ci_id": "srv-001"},
                        {"ci_id": "srv-002"}
                    ]
                }
            },
            "secondary": {
                "data": {
                    "rows": []
                }
            }
        }

        formatted = decider._format_results(previous_results)
        assert "primary: 2 rows" in formatted
        assert "secondary: 0 rows" in formatted


class TestToolOrchestrator:
    """Integration tests for ToolOrchestrator."""

    def test_build_tool_chain_parallel(self):
        """Should build tool chain for parallel execution."""
        plan = MagicMock()
        plan.intent = Intent.AGGREGATE
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = SecondarySpec(keywords=["network"], tool_type="ci_lookup")
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(
            tenant_id="test-tenant",
            trace_id="test-trace",
        )

        orchestrator = ToolOrchestrator(plan, context)
        dependencies = orchestrator.dependency_analyzer.extract_dependencies(plan)
        strategy = orchestrator.execution_planner.determine_strategy(dependencies)

        assert strategy == ExecutionStrategy.PARALLEL

        tool_chain = orchestrator._build_tool_chain(dependencies, strategy)
        assert len(tool_chain.steps) == 2
        assert tool_chain.execution_mode == "parallel"

    def test_build_tool_chain_with_dependencies(self):
        """Should build tool chain with proper dependency links."""
        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = None
        plan.graph = GraphSpec(depth=2, tool_type="graph_analysis")
        plan.metric = None

        context = ToolContext(
            tenant_id="test-tenant",
            trace_id="test-trace",
        )

        orchestrator = ToolOrchestrator(plan, context)
        dependencies = orchestrator.dependency_analyzer.extract_dependencies(plan)

        tool_chain = orchestrator._build_tool_chain(dependencies, ExecutionStrategy.SERIAL)
        assert len(tool_chain.steps) == 2

        # Check that graph depends on primary
        graph_step = next(s for s in tool_chain.steps if s.step_id == "graph")
        assert "primary" in graph_step.depends_on

    def test_extract_tool_spec_primary(self):
        """Should extract tool spec from primary spec."""
        plan = MagicMock()
        plan.primary = PrimarySpec(
            keywords=["server", "database"],
            filters=[FilterSpec(field="status", value="active")],
            limit=10,
            tool_type="ci_lookup"
        )
        plan.secondary = None
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test")
        orchestrator = ToolOrchestrator(plan, context)

        spec = orchestrator._get_tool_spec_by_id("primary")
        assert spec is not None
        assert spec["tool_type"] == "ci_lookup"
        assert spec["params"]["keywords"] == ["server", "database"]
        assert spec["params"]["limit"] == 10

    def test_extract_tool_spec_aggregate(self):
        """Should extract tool spec from aggregate spec."""
        plan = MagicMock()
        plan.primary = None
        plan.secondary = None
        plan.aggregate = AggregateSpec(
            group_by=["ci_type"],
            metrics=["count"],
            top_n=5,
            scope="ci",
            tool_type="ci_aggregate"
        )
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test")
        orchestrator = ToolOrchestrator(plan, context)

        spec = orchestrator._get_tool_spec_by_id("aggregate")
        assert spec is not None
        assert spec["tool_type"] == "ci_aggregate"
        assert spec["params"]["group_by"] == ["ci_type"]
        assert spec["params"]["metrics"] == ["count"]
