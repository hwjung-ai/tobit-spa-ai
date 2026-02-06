"""
Tests for StageExecutor in OPS Orchestration.

Tests the core stage execution functionality including:
- Asset override resolution
- Stage execution flow
- Diagnostics generation
- Error handling
"""

from unittest.mock import AsyncMock

import pytest
from app.modules.ops.schemas import (
    ExecutionContext,
    StageDiagnostics,
    StageInput,
    StageOutput,
)
from app.modules.ops.services.ci.orchestrator.stage_executor import StageExecutor


@pytest.fixture
def base_context():
    """Basic execution context without overrides."""
    return ExecutionContext(
        tenant_id="test-tenant",
        question="Test question",
        trace_id="test-trace-001",
        test_mode=False,
        asset_overrides={},
        baseline_trace_id=None,
        cache_hit=False,
        final_attributions=[],
        action_cards=[],
    )


@pytest.fixture
def override_context():
    """Execution context with asset overrides."""
    return ExecutionContext(
        tenant_id="test-tenant",
        question="Test question with overrides",
        trace_id="test-trace-002",
        test_mode=True,
        asset_overrides={
            "prompt:planner": "planner:version-2",
            "policy:timeout": "timeout:draft-v3",
        },
        baseline_trace_id="baseline-trace-123",
        cache_hit=False,
        final_attributions=[],
        action_cards=[],
    )


@pytest.fixture
def stage_input():
    """Sample stage input."""
    return StageInput(
        stage="route_plan",
        applied_assets={
            "prompt": "planner:published",
            "policy": "timeout:published",
        },
        params={"query": "Show me CPU metrics for last 24 hours"},
        prev_output=None,
        trace_id="test-trace-001",
    )


class TestStageExecutor:
    """Test suite for StageExecutor."""

    def test_initialization(self, base_context):
        """Test StageExecutor initialization."""
        executor = StageExecutor(context=base_context)

        assert executor.context == base_context
        assert executor.tool_executor is not None
        assert executor.stage_inputs == []
        assert executor.stage_outputs == []

    def test_resolve_asset_no_override(self, base_context):
        """Test asset resolution without overrides."""
        executor = StageExecutor(context=base_context)

        resolved = executor._resolve_asset("prompt", "planner")
        assert resolved == "planner:published"

    def test_resolve_asset_with_override(self, override_context):
        """Test asset resolution with overrides."""
        executor = StageExecutor(context=override_context)

        # Override exists
        resolved = executor._resolve_asset("prompt", "planner")
        assert resolved == "planner:version-2"

        # Override doesn't exist, should use default
        resolved = executor._resolve_asset("query", "metrics")
        assert resolved == "metrics:published"

    @pytest.mark.asyncio
    async def test_execute_stage_route_plan(self, base_context, stage_input):
        """Test execution of route_plan stage."""
        executor = StageExecutor(context=base_context)

        # Mock the _execute_route_plan method
        mock_result = {
            "plan_output": {
                "kind": "plan",
                "confidence": 0.95,
            }
        }
        executor._execute_route_plan = AsyncMock(return_value=mock_result)

        output = await executor.execute_stage(stage_input)

        assert isinstance(output, StageOutput)
        assert output.stage == "route_plan"
        assert output.result == mock_result
        assert isinstance(output.diagnostics, StageDiagnostics)
        assert output.duration_ms >= 0  # Can be 0 in fast async mocks

    @pytest.mark.asyncio
    async def test_execute_stage_with_error(self, base_context, stage_input):
        """Test stage execution with error."""
        executor = StageExecutor(context=base_context)

        # Mock the stage handler to raise an error
        executor._execute_route_plan = AsyncMock(side_effect=ValueError("Test error"))

        output = await executor.execute_stage(stage_input)

        assert isinstance(output, StageOutput)
        assert output.diagnostics.status == "error"
        assert len(output.diagnostics.errors) > 0
        assert "Test error" in output.diagnostics.errors[0]

    @pytest.mark.asyncio
    async def test_generate_llm_summary_full_time_metric_fallback(self, base_context):
        """Ensure full-time summary uses metric_result when primary_result is missing."""
        executor = StageExecutor(context=base_context)
        composed_result = {
            "ci_detail": {
                "ci_id": "ci-1",
                "ci_code": "CI-001",
                "ci_name": "test-ci",
                "ci_type": "server",
                "status": "active",
            },
            "metric_result": {
                "rows": [{"ci_id": "ci-1", "metric_value": 95.5}],
            },
            "history_result": {
                "rows": [{"id": 1}, {"id": 2}],
            },
        }

        summary = await executor._generate_llm_summary(
            question="전체기간 cpu 사용률이 가장 높은 ci 알려줘",
            intent="AGGREGATE",
            execution_results=[],
            composed_result=composed_result,
        )

        assert "CI-001" in summary
        assert "95.50" in summary
        assert "최근 작업 이력은 2건" in summary

    def test_build_diagnostics_success(self, base_context):
        """Test diagnostics building for successful execution."""
        executor = StageExecutor(context=base_context)

        result = {
            "results": [1, 2, 3],
            "references": ["ref1", "ref2"],
        }

        diagnostics = executor._build_diagnostics(result, "execute")

        assert diagnostics.status == "ok"
        assert diagnostics.warnings == []
        assert diagnostics.errors == []

    def test_build_diagnostics_empty_result(self, base_context):
        """Test diagnostics building for empty result."""
        executor = StageExecutor(context=base_context)

        result = {}

        diagnostics = executor._build_diagnostics(result, "execute")

        assert "result_empty" in diagnostics.empty_flags
        assert diagnostics.empty_flags["result_empty"] is True

    def test_build_diagnostics_with_errors(self, base_context):
        """Test diagnostics building with errors."""
        executor = StageExecutor(context=base_context)

        result = {"error": "Database connection failed"}

        diagnostics = executor._build_diagnostics(result, "execute")

        assert diagnostics.status == "error"
        assert len(diagnostics.errors) >= 1
        assert "Database connection failed" in diagnostics.errors[0]

    @pytest.mark.asyncio
    async def test_stage_input_output_tracking(self, base_context, stage_input):
        """Test that stages are properly tracked."""
        executor = StageExecutor(context=base_context)

        mock_result = {"status": "success"}
        executor._execute_route_plan = AsyncMock(return_value=mock_result)

        # Execute stage
        output = await executor.execute_stage(stage_input)

        # Verify tracking
        assert len(executor.stage_inputs) == 1
        assert len(executor.stage_outputs) == 1
        assert executor.stage_inputs[0] == stage_input
        assert executor.stage_outputs[0] == output

    @pytest.mark.asyncio
    async def test_multiple_stages_execution(self, base_context):
        """Test execution of multiple stages in sequence."""
        executor = StageExecutor(context=base_context)

        # Mock all stage handlers
        executor._execute_route_plan = AsyncMock(return_value={"kind": "plan"})
        executor._execute_validate = AsyncMock(return_value={"valid": True})
        executor._execute_execute = AsyncMock(
            return_value={"rows": [{"metric": "cpu", "value": 75}]}
        )

        # Execute stages
        stages = [
            StageInput(
                stage="route_plan",
                applied_assets={},
                params={"query": "test"},
                prev_output=None,
                trace_id="test-001",
            ),
            StageInput(
                stage="validate",
                applied_assets={},
                params={},
                prev_output={"kind": "plan"},
                trace_id="test-001",
            ),
            StageInput(
                stage="execute",
                applied_assets={},
                params={},
                prev_output={"valid": True},
                trace_id="test-001",
            ),
        ]

        for stage in stages:
            output = await executor.execute_stage(stage)
            assert output.stage == stage.stage

        assert len(executor.stage_inputs) == 3
        assert len(executor.stage_outputs) == 3

    def test_test_mode_flag(self, override_context, stage_input):
        """Test that test mode is properly set."""
        executor = StageExecutor(context=override_context)

        assert executor.context.test_mode is True
        assert len(executor.context.asset_overrides) > 0

    @pytest.mark.asyncio
    async def test_baseline_comparison(self, override_context, stage_input):
        """Test baseline trace comparison."""
        executor = StageExecutor(context=override_context)

        # Context has baseline_trace_id
        assert executor.context.baseline_trace_id == "baseline-trace-123"

        mock_result = {"data": "new result"}
        executor._execute_route_plan = AsyncMock(return_value=mock_result)

        output = await executor.execute_stage(stage_input)

        # Output should be generated successfully
        assert output.result == mock_result

    def test_diagnostics_counts(self, base_context):
        """Test that diagnostics include proper counts."""
        executor = StageExecutor(context=base_context)

        result = {
            "execution_results": [1, 2, 3, 4, 5],
            "references": ["ref1", "ref2"],
        }

        diagnostics = executor._build_diagnostics(result, "execute")

        assert "execution_results" in diagnostics.counts
        assert diagnostics.counts["execution_results"] == 5
        assert "references" in diagnostics.counts
        assert diagnostics.counts["references"] == 2

    @pytest.mark.asyncio
    async def test_stage_unknown_handler(self, base_context):
        """Test handling of unknown stage type."""
        executor = StageExecutor(context=base_context)

        unknown_stage = StageInput(
            stage="unknown_stage",
            applied_assets={},
            params={},
            prev_output=None,
            trace_id="test-unknown",
        )

        output = await executor.execute_stage(unknown_stage)

        # Should return error diagnostics
        assert output.diagnostics.status == "error"
        assert len(output.diagnostics.errors) > 0

    @pytest.mark.asyncio
    async def test_stage_with_references(self, base_context, stage_input):
        """Test stage execution that generates references."""
        executor = StageExecutor(context=base_context)

        mock_result = {
            "data": {"metric": "cpu"},
        }

        # Mock to return result with references
        async def mock_execute(stage_input):
            return mock_result

        executor._execute_route_plan = mock_execute

        output = await executor.execute_stage(stage_input)

        assert output.result == mock_result
        assert isinstance(output.references, list)


class TestStageDiagnostics:
    """Test suite for StageDiagnostics."""

    def test_diagnostics_creation(self):
        """Test creating diagnostics."""
        diag = StageDiagnostics(
            status="ok",
            warnings=[],
            errors=[],
            empty_flags={},
            counts={"rows": 10},
        )

        assert diag.status == "ok"
        assert diag.counts["rows"] == 10

    def test_diagnostics_with_warnings(self):
        """Test diagnostics with warnings."""
        diag = StageDiagnostics(
            status="warning",
            warnings=["Low confidence", "Missing field"],
            errors=[],
            empty_flags={"result_empty": False},
            counts={},
        )

        assert diag.status == "warning"
        assert len(diag.warnings) == 2

    def test_diagnostics_with_errors(self):
        """Test diagnostics with errors."""
        diag = StageDiagnostics(
            status="error",
            warnings=[],
            errors=["Connection failed"],
            empty_flags={},
            counts={},
        )

        assert diag.status == "error"
        assert "Connection failed" in diag.errors


class TestExecutionContext:
    """Test suite for ExecutionContext."""

    def test_context_creation(self):
        """Test creating execution context."""
        context = ExecutionContext(
            tenant_id="test-tenant",
            question="Test question",
            trace_id="trace-001",
            test_mode=True,
            asset_overrides={"prompt:test": "test:v2"},
            baseline_trace_id="baseline-001",
            cache_hit=False,
            final_attributions=[],
            action_cards=[],
        )

        assert context.test_mode is True
        assert len(context.asset_overrides) == 1
        assert context.baseline_trace_id == "baseline-001"
        assert context.tenant_id == "test-tenant"
        assert context.question == "Test question"
        assert context.trace_id == "trace-001"

    def test_context_defaults(self):
        """Test default values in execution context."""
        context = ExecutionContext(
            tenant_id="test-tenant",
            question="Test question",
            trace_id="trace-002",
            test_mode=False,
            asset_overrides={},
            baseline_trace_id=None,
            cache_hit=False,
            final_attributions=[],
            action_cards=[],
        )

        assert context.test_mode is False
        assert context.asset_overrides == {}
        assert context.baseline_trace_id is None
        assert context.cache_hit is False
        assert context.final_attributions == []
        assert context.action_cards == []
