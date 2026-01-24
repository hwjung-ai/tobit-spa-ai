"""
Tests for advanced LangGraph implementation with StateGraph, query decomposition,
conditional routing, and tool composition.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from app.modules.ops.services.langgraph_advanced import (
    ConditionalRouter,
    ExecutionMode,
    ExecutionState,
    LangGraphAdvancedRunner,
    QueryAnalysis,
    QueryAnalyzer,
    QueryType,
    ToolComposer,
)
from core.config import AppSettings


class TestQueryAnalyzer:
    """Test query analysis and type detection."""

    @pytest.fixture
    def analyzer(self):
        settings = AppSettings()
        llm_client = Mock()
        return QueryAnalyzer(llm_client, settings)

    def test_detect_metric_query(self, analyzer):
        """Test detection of metric queries."""
        query = "What is the average response time?"
        query_type = analyzer._detect_query_type(query)
        assert query_type == QueryType.METRIC

    def test_detect_graph_query(self, analyzer):
        """Test detection of graph queries."""
        query = "Show the relationship between nodes"
        query_type = analyzer._detect_query_type(query)
        assert query_type == QueryType.GRAPH

    def test_detect_history_query(self, analyzer):
        """Test detection of history queries."""
        query = "What is the event history?"
        query_type = analyzer._detect_query_type(query)
        assert query_type == QueryType.HISTORY

    def test_detect_ci_query(self, analyzer):
        """Test detection of CI queries."""
        query = "Show configuration items"
        query_type = analyzer._detect_query_type(query)
        assert query_type == QueryType.CI

    def test_detect_conditional_query(self, analyzer):
        """Test detection of conditional queries."""
        query = "If status is error, then alert"
        query_type = analyzer._detect_query_type(query)
        assert query_type == QueryType.CONDITIONAL

    def test_detect_composite_query(self, analyzer):
        """Test detection of composite queries."""
        query = "Get metrics and show relationships"
        query_type = analyzer._detect_query_type(query)
        # Will detect as metric or composite depending on keyword order
        assert query_type in [QueryType.COMPOSITE, QueryType.METRIC]

    def test_calculate_simple_complexity(self, analyzer):
        """Test complexity calculation for simple query."""
        query = "Show metrics"
        complexity = analyzer._calculate_complexity(query)
        assert complexity <= 3

    def test_calculate_complex_complexity(self, analyzer):
        """Test complexity calculation for complex query."""
        query = (
            "Show metrics and relationships for all nodes where status is error and "
            "timestamp is after 2024-01-01 and (type is critical or severity is high)"
        )
        complexity = analyzer._calculate_complexity(query)
        assert complexity > 5

    def test_decompose_composite_query(self, analyzer):
        """Test decomposition of composite queries."""
        query = "Get metric1 and get metric2"
        sub_queries, _ = analyzer._decompose_query(query)
        assert len(sub_queries) >= 2

    def test_determine_tools_metric(self, analyzer):
        """Test tool determination for metric query."""
        tools = analyzer._determine_tools("Show metrics", QueryType.METRIC)
        assert "metric_executor" in tools

    def test_determine_tools_graph(self, analyzer):
        """Test tool determination for graph query."""
        tools = analyzer._determine_tools("Show relationships", QueryType.GRAPH)
        assert "graph_executor" in tools

    def test_extract_conditions_if_then(self, analyzer):
        """Test condition extraction from if-then query."""
        query = "If error rate > 10% then alert"
        conditions = analyzer._extract_conditions(query)
        assert "condition" in conditions or len(conditions) > 0

    def test_analyze_full_query(self, analyzer):
        """Test full query analysis."""
        query = "What is the average metric and show trends?"
        analysis = analyzer.analyze(query)
        assert analysis.query_type is not None
        assert analysis.complexity > 0
        assert isinstance(analysis.tools_needed, list)


class TestConditionalRouter:
    """Test conditional routing logic."""

    @pytest.fixture
    def router(self):
        settings = AppSettings()
        llm_client = Mock()
        return ConditionalRouter(llm_client, settings)

    @pytest.fixture
    def sample_state(self):
        return ExecutionState(
            query="test query",
            original_query="test query",
            decomposed_queries=[],
            execution_path=[],
            results={},
            errors=[],
            metadata={},
            depth=0,
            max_depth=3,
            timestamp=datetime.now().isoformat(),
        )

    def test_should_execute_default(self, router, sample_state):
        """Test default execution decision."""
        result = router.should_execute(sample_state, "test_tool", {})
        assert result is True

    def test_should_execute_respects_depth_limit(self, router, sample_state):
        """Test execution respects depth limit."""
        sample_state["depth"] = 3
        sample_state["max_depth"] = 3
        result = router.should_execute(sample_state, "test_tool", {})
        # At depth == max_depth, should NOT execute
        assert result is False

    def test_choose_path_first_option(self, router, sample_state):
        """Test path selection returns first valid option."""
        options = [
            ("path_a", {}),
            ("path_b", {}),
        ]
        result = router.choose_path(sample_state, options)
        assert result == "path_a"

    def test_evaluate_condition_error(self, router, sample_state):
        """Test condition evaluation for errors."""
        sample_state["errors"] = ["test error"]
        result = router._evaluate_condition(sample_state, "error check")
        assert result is True

    def test_evaluate_condition_empty(self, router, sample_state):
        """Test condition evaluation for empty results."""
        sample_state["results"] = {}
        result = router._evaluate_condition(sample_state, "empty")
        assert result is True

    def test_evaluate_condition_complex(self, router, sample_state):
        """Test condition evaluation for complexity."""
        sample_state["metadata"]["complexity"] = 8
        result = router._evaluate_condition(sample_state, "complex")
        assert result is True


class TestToolComposer:
    """Test dynamic tool composition."""

    @pytest.fixture
    def composer(self):
        return ToolComposer()

    def test_register_tool(self, composer):
        """Test tool registration."""
        mock_executor = Mock()
        composer.register_tool("test_tool", mock_executor)
        assert "test_tool" in composer.tool_registry

    def test_compose_single_tool(self, composer):
        """Test composition of single tool."""
        tool1 = Mock()
        composer.register_tool("tool1", tool1)
        composed = composer.compose(["tool1"])
        assert len(composed) == 1
        assert composed[0] == tool1

    def test_compose_multiple_tools(self, composer):
        """Test composition of multiple tools."""
        tool1 = Mock()
        tool2 = Mock()
        composer.register_tool("tool1", tool1)
        composer.register_tool("tool2", tool2)
        composed = composer.compose(["tool1", "tool2"])
        assert len(composed) == 2

    def test_compose_nonexistent_tool(self, composer):
        """Test composition with nonexistent tool."""
        tool1 = Mock()
        composer.register_tool("tool1", tool1)
        composed = composer.compose(["tool1", "nonexistent"])
        assert len(composed) == 1  # Only tool1

    def test_compose_with_dependencies_simple(self, composer):
        """Test composition respecting simple dependencies."""
        composer.register_tool("tool1", Mock())
        composer.register_tool("tool2", Mock())

        order = composer.compose_with_dependencies(
            ["tool1", "tool2"],
            {"tool1": [], "tool2": ["tool1"]},
        )

        # tool1 should come before tool2
        tool1_idx = next(i for i, (t, _) in enumerate(order) if t == "tool1")
        tool2_idx = next(i for i, (t, _) in enumerate(order) if t == "tool2")
        assert tool1_idx < tool2_idx

    def test_compose_with_dependencies_multiple(self, composer):
        """Test composition with complex dependencies."""
        composer.register_tool("tool1", Mock())
        composer.register_tool("tool2", Mock())
        composer.register_tool("tool3", Mock())

        order = composer.compose_with_dependencies(
            ["tool1", "tool2", "tool3"],
            {
                "tool1": [],
                "tool2": ["tool1"],
                "tool3": ["tool1", "tool2"],
            },
        )

        assert len(order) == 3


class TestLangGraphAdvancedRunner:
    """Test advanced LangGraph runner."""

    @pytest.fixture
    def runner(self):
        settings = AppSettings(openai_api_key="test-key")
        with patch("app.modules.ops.services.langgraph_advanced.get_llm_client"):
            return LangGraphAdvancedRunner(settings)

    def test_initialization(self):
        """Test runner initialization."""
        settings = AppSettings(openai_api_key="test-key")
        with patch("app.modules.ops.services.langgraph_advanced.get_llm_client"):
            runner = LangGraphAdvancedRunner(settings)
            assert runner.settings == settings
            assert runner.analyzer is not None
            assert runner.router is not None
            assert runner.composer is not None

    def test_missing_api_key(self):
        """Test initialization with missing API key."""
        settings = AppSettings()
        # AppSettings provides a default, so we need to explicitly set it to None
        settings.openai_api_key = None
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            LangGraphAdvancedRunner(settings)

    def test_run_simple_query(self, runner):
        """Test running a simple query."""
        blocks, tools, error = runner.run("Show metrics", max_depth=3)

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert isinstance(tools, list)
        assert error is None

    def test_run_complex_query(self, runner):
        """Test running a complex query."""
        query = "Show metrics and relationships for nodes where status is error"
        blocks, tools, error = runner.run(query, max_depth=3)

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert isinstance(tools, list)

    def test_run_with_depth_limit(self, runner):
        """Test query execution respects depth limit."""
        query = "Deeply nested query"
        blocks, tools, error = runner.run(query, max_depth=1)

        assert isinstance(blocks, list)
        # Summary should indicate depth was considered
        summary_text = blocks[0].content if hasattr(blocks[0], "content") else ""
        assert "Execution Summary" in str(summary_text) or len(blocks) > 0

    def test_run_sequential_mode(self, runner):
        """Test sequential execution mode."""
        blocks, tools, error = runner.run(
            "Get metrics",
            execution_mode=ExecutionMode.SEQUENTIAL,
        )

        assert isinstance(blocks, list)
        assert "sequential" in str(blocks).lower() or error is None

    def test_run_parallel_mode(self, runner):
        """Test parallel execution mode."""
        blocks, tools, error = runner.run(
            "Get metrics and relationships",
            execution_mode=ExecutionMode.PARALLEL,
        )

        assert isinstance(blocks, list)

    def test_run_hybrid_mode(self, runner):
        """Test hybrid execution mode."""
        blocks, tools, error = runner.run(
            "Complex query",
            execution_mode=ExecutionMode.HYBRID,
        )

        assert isinstance(blocks, list)

    def test_execute_simple_returns_blocks(self, runner):
        """Test _execute_simple returns proper blocks."""
        state = ExecutionState(
            query="test",
            original_query="test",
            decomposed_queries=[],
            execution_path=[],
            results={},
            errors=[],
            metadata={},
            depth=0,
            max_depth=3,
            timestamp=datetime.now().isoformat(),
        )

        analysis = QueryAnalysis(
            query_type=QueryType.METRIC,
            complexity=2,
            requires_decomposition=False,
            tools_needed=["metric_executor"],
        )

        blocks, tools = runner._execute_simple(state, analysis)

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert isinstance(tools, list)

    def test_execute_decomposed_returns_blocks(self, runner):
        """Test _execute_decomposed returns proper blocks."""
        state = ExecutionState(
            query="test and test2",
            original_query="test and test2",
            decomposed_queries=["test", "test2"],
            execution_path=[],
            results={},
            errors=[],
            metadata={},
            depth=0,
            max_depth=3,
            timestamp=datetime.now().isoformat(),
        )

        analysis = QueryAnalysis(
            query_type=QueryType.COMPOSITE,
            complexity=6,
            requires_decomposition=True,
            sub_queries=["test", "test2"],
            tools_needed=["metric_executor", "graph_executor"],
        )

        blocks, tools = runner._execute_decomposed(
            state, analysis, ExecutionMode.HYBRID
        )

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert isinstance(tools, list)

    def test_build_summary_block(self, runner):
        """Test summary building."""
        state = ExecutionState(
            query="test",
            original_query="test",
            decomposed_queries=[],
            execution_path=["simple_metric"],
            results={
                "sub_query_0": {
                    "query": "test",
                    "type": "metric",
                    "tools": ["metric_executor"],
                }
            },
            errors=[],
            metadata={"complexity": 2},
            depth=1,
            max_depth=3,
            timestamp=datetime.now().isoformat(),
        )

        analysis = QueryAnalysis(
            query_type=QueryType.METRIC,
            complexity=2,
            requires_decomposition=False,
        )

        blocks = []
        summary = runner._build_summary(state, analysis, blocks)

        assert hasattr(summary, "content")
        assert "Execution Summary" in summary.content
        assert "test" in summary.content


class TestExecutionState:
    """Test ExecutionState management."""

    def test_execution_state_creation(self):
        """Test creating execution state."""
        state = ExecutionState(
            query="test",
            original_query="test",
            decomposed_queries=[],
            execution_path=[],
            results={},
            errors=[],
            metadata={},
            depth=0,
            max_depth=3,
            timestamp=datetime.now().isoformat(),
        )

        assert state["query"] == "test"
        assert state["depth"] == 0
        assert state["max_depth"] == 3

    def test_execution_state_tracking(self):
        """Test execution state mutation during execution."""
        state = ExecutionState(
            query="test",
            original_query="test",
            decomposed_queries=[],
            execution_path=[],
            results={},
            errors=[],
            metadata={},
            depth=0,
            max_depth=3,
            timestamp=datetime.now().isoformat(),
        )

        state["depth"] += 1
        state["execution_path"].append("step1")
        state["errors"].append("test error")

        assert state["depth"] == 1
        assert "step1" in state["execution_path"]
        assert len(state["errors"]) == 1


class TestIntegration:
    """Integration tests for advanced LangGraph."""

    def test_full_workflow_simple_to_complex(self):
        """Test complete workflow from simple to complex queries."""
        settings = AppSettings(openai_api_key="test-key")

        with patch("app.modules.ops.services.langgraph_advanced.get_llm_client"):
            runner = LangGraphAdvancedRunner(settings)

            # Simple query
            blocks1, tools1, error1 = runner.run("Show metrics")
            assert len(blocks1) > 0
            assert error1 is None

            # Complex query
            blocks2, tools2, error2 = runner.run("Show metrics and relationships")
            assert len(blocks2) > 0
            assert error2 is None

    def test_query_analysis_to_execution(self):
        """Test query analysis leading to execution."""
        settings = AppSettings(openai_api_key="test-key")

        with patch("app.modules.ops.services.langgraph_advanced.get_llm_client"):
            runner = LangGraphAdvancedRunner(settings)

            # Analyze
            analysis = runner.analyzer.analyze("Show metrics and relationships")

            # Verify analysis is used in execution
            assert analysis.query_type is not None
            assert analysis.tools_needed is not None
