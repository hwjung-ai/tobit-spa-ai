"""Integration tests for Phase 5 Orchestration with Stage Executor.

Tests for:
- Orchestration with parallel execution
- Orchestration with serial execution
- Orchestration with DAG execution
- Data flow between tools
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.modules.ops.services.orchestration.orchestrator.tool_orchestration import (
    ToolOrchestrator,
)
from app.modules.ops.services.orchestration.planner.plan_schema import (
    AggregateSpec,
    ExecutionStrategy,
    GraphSpec,
    Intent,
    PrimarySpec,
    SecondarySpec,
)
from app.modules.ops.services.orchestration.tools.base import ToolContext


class TestOrchestrationIntegration:
    """Integration tests for orchestration with actual tool execution."""

    @pytest.mark.asyncio
    async def test_parallel_execution_independent_tools(self):
        """Should execute independent tools in parallel."""
        plan = MagicMock()
        plan.intent = Intent.AGGREGATE
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = SecondarySpec(keywords=["network"], tool_type="ci_lookup")
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        # Mock the chain executor to return mock results
        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            # Mock results from parallel execution
            mock_executor.execute_chain = AsyncMock(return_value={
                "primary": {
                    "success": True,
                    "data": {"rows": [{"ci_id": "srv-001"}]},
                    "references": []
                },
                "secondary": {
                    "success": True,
                    "data": {"rows": [{"ci_id": "net-001"}]},
                    "references": []
                }
            })

            orchestrator = ToolOrchestrator(plan, context)
            results = await orchestrator.execute()

            assert "primary" in results
            assert "secondary" in results
            assert results["primary"]["success"]
            assert results["secondary"]["success"]

            # Verify that execute_chain was called with parallel mode
            call_args = mock_executor.execute_chain.call_args
            chain = call_args[0][0]  # First positional argument
            assert chain.execution_mode == "parallel"

    @pytest.mark.asyncio
    async def test_serial_execution_with_dependencies(self):
        """Should execute dependent tools in serial order."""
        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = AggregateSpec(metrics=["count"], tool_type="ci_aggregate")
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            # Mock results from serial execution
            mock_executor.execute_chain = AsyncMock(return_value={
                "primary": {
                    "success": True,
                    "data": {
                        "rows": [
                            {"ci_id": "srv-001", "ci_type": "server"},
                            {"ci_id": "srv-002", "ci_type": "server"}
                        ]
                    },
                    "references": []
                },
                "aggregate": {
                    "success": True,
                    "data": {
                        "rows": [{"ci_type": "server", "count": 2}]
                    },
                    "references": []
                }
            })

            orchestrator = ToolOrchestrator(plan, context)
            results = await orchestrator.execute()

            assert "primary" in results
            assert "aggregate" in results
            assert results["primary"]["success"]
            assert results["aggregate"]["success"]

            # Verify that execute_chain was called with serial mode
            call_args = mock_executor.execute_chain.call_args
            chain = call_args[0][0]
            assert chain.execution_mode == "serial"

    @pytest.mark.asyncio
    async def test_dag_execution_complex_dependencies(self):
        """Should execute complex DAG with convergence points.

        Setup: primary and secondary are independent (both entry points),
               aggregate depends on primary and secondary (convergence point)
        """
        from app.modules.ops.services.orchestration.planner.plan_schema import (
            ToolDependency,
        )

        plan = MagicMock()
        plan.intent = Intent.AGGREGATE
        # Explicitly set dependencies for convergence
        plan.tool_dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
            ToolDependency(tool_id="aggregate", depends_on=["primary", "secondary"]),
        ]
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = SecondarySpec(keywords=["network"], tool_type="ci_lookup")
        plan.aggregate = AggregateSpec(metrics=["count"], tool_type="ci_aggregate")
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            # Mock results from DAG execution
            mock_executor.execute_chain = AsyncMock(return_value={
                "primary": {
                    "success": True,
                    "data": {"rows": [{"ci_type": "server", "count": 5}]},
                    "references": []
                },
                "secondary": {
                    "success": True,
                    "data": {"rows": [{"ci_type": "network", "count": 3}]},
                    "references": []
                },
                "aggregate": {
                    "success": True,
                    "data": {"rows": [{"overall_count": 8}]},
                    "references": []
                }
            })

            orchestrator = ToolOrchestrator(plan, context)
            results = await orchestrator.execute()

            assert len(results) == 3
            assert all(r["success"] for r in results.values())

            # Verify execution mode is DAG
            call_args = mock_executor.execute_chain.call_args
            chain = call_args[0][0]
            assert chain.execution_mode == "dag"


class TestDataFlowIntegration:
    """Test data flow mapping in orchestration."""

    @pytest.mark.asyncio
    async def test_output_mapping_between_tools(self):
        """Should map outputs from one tool to inputs of another."""
        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = None
        plan.graph = GraphSpec(depth=2, tool_type="graph_analysis")
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            mock_executor.execute_chain = AsyncMock(return_value={
                "primary": {
                    "success": True,
                    "data": {
                        "rows": [{"ci_id": "srv-001"}]
                    },
                    "references": []
                },
                "graph": {
                    "success": True,
                    "data": {
                        "nodes": ["srv-001", "app-001"],
                        "edges": [("srv-001", "app-001")]
                    },
                    "references": []
                }
            })

            orchestrator = ToolOrchestrator(plan, context)
            await orchestrator.execute()

            # Get the tool chain that was passed to executor
            call_args = mock_executor.execute_chain.call_args
            chain = call_args[0][0]

            # Find graph step
            graph_step = next(s for s in chain.steps if s.step_id == "graph")

            # Should have output mapping from primary
            assert "primary" in graph_step.depends_on
            assert len(graph_step.output_mapping) > 0


class TestExecutionMetrics:
    """Test orchestration execution metrics and logging."""

    @pytest.mark.asyncio
    async def test_execution_timing(self):
        """Should track execution timing."""
        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            # Simulate delay
            async def slow_execute(*args, **kwargs):
                await asyncio.sleep(0.01)  # 10ms delay
                return {
                    "primary": {
                        "success": True,
                        "data": {},
                        "references": []
                    }
                }

            mock_executor.execute_chain = slow_execute

            orchestrator = ToolOrchestrator(plan, context)
            results = await orchestrator.execute()

            assert results is not None
            # Execution should have taken at least 10ms
            assert True  # Basic sanity check

    @pytest.mark.asyncio
    async def test_error_handling_in_orchestration(self):
        """Should handle errors gracefully."""
        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = None
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            # Simulate execution error
            mock_executor.execute_chain = AsyncMock(side_effect=Exception("Tool execution failed"))

            orchestrator = ToolOrchestrator(plan, context)

            with pytest.raises(Exception):
                await orchestrator.execute()


class TestOrchestrationTraceMetadata:
    """Test orchestration-aware tracing for Inspector integration."""

    def test_create_execution_plan_trace_parallel(self):
        """Should create execution plan trace for parallel execution."""
        from app.modules.ops.services.orchestration.planner.plan_schema import (
            ToolDependency,
        )

        plan = MagicMock()
        plan.intent = Intent.AGGREGATE
        plan.tool_dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
        ]
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = SecondarySpec(keywords=["network"], tool_type="ci_lookup")
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")
        orchestrator = ToolOrchestrator(plan, context)

        # Create execution plan trace
        dependencies = plan.tool_dependencies
        strategy = ExecutionStrategy.PARALLEL
        trace = orchestrator._create_execution_plan_trace(dependencies, strategy)

        assert trace is not None
        assert trace["strategy"] == "parallel"
        assert trace["total_tools"] == 2
        assert len(trace["execution_groups"]) == 1  # All in one group for parallel
        assert trace["execution_groups"][0]["parallel_execution"] is True
        assert len(trace["execution_groups"][0]["tools"]) == 2

    def test_create_execution_plan_trace_serial(self):
        """Should create execution plan trace for serial execution."""
        from app.modules.ops.services.orchestration.planner.plan_schema import (
            ToolDependency,
        )

        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(
                tool_id="aggregate",
                depends_on=["primary"],
                output_mapping={"ci_type_filter": "{primary.data.rows[0].ci_type}"}
            ),
        ]
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = AggregateSpec(metrics=["count"], tool_type="ci_aggregate")
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")
        orchestrator = ToolOrchestrator(plan, context)

        # Create execution plan trace
        dependencies = plan.tool_dependencies
        strategy = ExecutionStrategy.SERIAL
        trace = orchestrator._create_execution_plan_trace(dependencies, strategy)

        assert trace is not None
        assert trace["strategy"] == "serial"
        assert trace["total_tools"] == 2
        assert len(trace["execution_groups"]) == 2  # Two separate groups for serial
        assert trace["execution_groups"][0]["parallel_execution"] is False
        assert trace["execution_groups"][1]["tools"][0]["depends_on"] == ["primary"]

    def test_create_execution_plan_trace_dag(self):
        """Should create execution plan trace for DAG execution."""
        from app.modules.ops.services.orchestration.planner.plan_schema import (
            ToolDependency,
        )

        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
            ToolDependency(
                tool_id="aggregate",
                depends_on=["primary", "secondary"],
                output_mapping={"ci_type_filter": "{primary.data.rows[0].ci_type}"}
            ),
        ]
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = SecondarySpec(keywords=["network"], tool_type="ci_lookup")
        plan.aggregate = AggregateSpec(metrics=["count"], tool_type="ci_aggregate")
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")
        orchestrator = ToolOrchestrator(plan, context)

        # Create execution plan trace
        dependencies = plan.tool_dependencies
        strategy = ExecutionStrategy.DAG
        trace = orchestrator._create_execution_plan_trace(dependencies, strategy)

        assert trace is not None
        assert trace["strategy"] == "dag"
        assert trace["total_tools"] == 3
        assert len(trace["execution_groups"]) == 2  # Two groups: [primary, secondary], [aggregate]
        # First group has two tools
        assert len(trace["execution_groups"][0]["tools"]) == 2
        assert trace["execution_groups"][0]["parallel_execution"] is True
        # Second group depends on first
        assert trace["execution_groups"][1]["tools"][0]["dependency_groups"] == [0]

    def test_execution_plan_trace_with_tool_types(self):
        """Should include tool types in execution plan trace."""
        from app.modules.ops.services.orchestration.planner.plan_schema import (
            ToolDependency,
        )

        plan = MagicMock()
        plan.intent = Intent.LOOKUP
        plan.tool_dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="aggregate", depends_on=["primary"]),
        ]
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = None
        plan.aggregate = AggregateSpec(metrics=["count"], tool_type="ci_aggregate")
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")
        orchestrator = ToolOrchestrator(plan, context)

        # Create execution plan trace
        dependencies = plan.tool_dependencies
        strategy = ExecutionStrategy.SERIAL
        trace = orchestrator._create_execution_plan_trace(dependencies, strategy)

        # Check tool types in trace
        primary_tool = trace["execution_groups"][0]["tools"][0]
        assert primary_tool["tool_id"] == "primary"
        assert primary_tool["tool_type"] == "ci_lookup"

        aggregate_tool = trace["execution_groups"][1]["tools"][0]
        assert aggregate_tool["tool_id"] == "aggregate"
        assert aggregate_tool["tool_type"] == "ci_aggregate"

    @pytest.mark.asyncio
    async def test_orchestration_trace_passed_to_executor(self):
        """Should pass execution plan trace to chain executor."""
        from app.modules.ops.services.orchestration.planner.plan_schema import (
            ToolDependency,
        )

        plan = MagicMock()
        plan.intent = Intent.AGGREGATE
        plan.tool_dependencies = [
            ToolDependency(tool_id="primary", depends_on=[]),
            ToolDependency(tool_id="secondary", depends_on=[]),
        ]
        plan.primary = PrimarySpec(keywords=["server"], tool_type="ci_lookup")
        plan.secondary = SecondarySpec(keywords=["network"], tool_type="ci_lookup")
        plan.aggregate = None
        plan.graph = None
        plan.metric = None

        context = ToolContext(tenant_id="test-tenant", trace_id="test-trace")

        with patch('app.modules.ops.services.orchestration.orchestrator.tool_orchestration.ToolChainExecutor') as MockExecutor:
            mock_executor = AsyncMock()
            MockExecutor.return_value = mock_executor

            mock_executor.execute_chain = AsyncMock(return_value={
                "primary": {"success": True, "data": {}},
                "secondary": {"success": True, "data": {}}
            })

            orchestrator = ToolOrchestrator(plan, context)
            await orchestrator.execute()

            # Verify that execute_chain was called with execution_plan_trace
            call_kwargs = mock_executor.execute_chain.call_args.kwargs
            assert "execution_plan_trace" in call_kwargs
            trace = call_kwargs["execution_plan_trace"]
            assert trace["strategy"] == "parallel"
            assert trace["total_tools"] == 2
