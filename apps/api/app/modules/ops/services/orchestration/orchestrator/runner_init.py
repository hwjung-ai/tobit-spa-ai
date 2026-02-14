"""Runner initialization infrastructure.

This module contains the BaseRunner class with shared execution state
and context building utilities.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List

from core.logging import get_logger, get_request_context
from schemas.tool_contracts import ToolCall

from app.modules.ops.schemas import ExecutionContext
from app.modules.ops.services.orchestration.actions import NextAction
from app.modules.ops.services.orchestration.orchestrator.stage_executor import (
    StageExecutor,
)
from app.modules.ops.services.orchestration.orchestrator.tool_selector import (
    SmartToolSelector,
)
from app.modules.ops.services.orchestration.planner.plan_schema import Plan, View
from app.modules.ops.services.orchestration.services.ci_cache import CICache
from app.modules.ops.services.orchestration.tools import get_tool_executor
from app.modules.ops.services.orchestration.tools.cache import ToolResultCache
from app.modules.ops.services.orchestration.tools.observability import ExecutionTracer


@dataclass
class RerunContext:
    selected_ci_id: str | None = None
    selected_secondary_ci_id: str | None = None


class BaseRunner:
    """Base runner with shared execution state and infrastructure.

    This class encapsulates all initialization, caching, and tool execution
    infrastructure needed by the OpsOrchestratorRunner.
    """

    def __init__(
        self,
        plan: Plan,
        plan_raw: Plan,
        tenant_id: str,
        question: str,
        policy_trace: Dict[str, Any],
        rerun_context: RerunContext | None = None,
        asset_overrides: Dict[str, str] | None = None,
    ):
        """Initialize runner with execution context and infrastructure.

        Args:
            plan: Execution plan
            plan_raw: Original unprocessed plan
            tenant_id: Tenant identifier
            question: User question
            policy_trace: Policy execution trace
            rerun_context: Rerun context with CI selection
            asset_overrides: Asset overrides for testing
        """
        self.plan = plan
        self.plan_raw = plan_raw
        self.tenant_id = tenant_id
        self.question = question
        self.plan_trace = policy_trace
        self.rerun_context = rerun_context or RerunContext()
        self.asset_overrides = asset_overrides or {}
        self.logger = get_logger(__name__)
        self.logger.info("ci.runner.instance_start", extra=self._runner_context())

        # Accumulator state
        self.tool_calls: List[ToolCall] = []
        self.tool_calls_raw: List[Dict[str, Any]] = []
        self.references: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.next_actions: List[NextAction] = []

        # Context caches for later use in block building
        self.metric_context: Dict[str, Any] | None = None
        self.history_context: Dict[str, Any] | None = None
        self.list_paging_info: Dict[str, Any] | None = None
        self.aggregation_summary: Dict[str, Any] | None = None

        # CI search recovery state
        self._ci_search_recovery: bool = False

        # Output configuration
        self.DEFAULT_OUTPUT_BLOCKS = ("text", "table")

        # Graph view configuration
        self.GRAPH_VIEWS = {
            View.COMPOSITION,
            View.DEPENDENCY,
            View.IMPACT,
            View.NEIGHBORS,
        }
        self.GRAPH_VIEWS_WITH_PATH = self.GRAPH_VIEWS | {View.PATH}
        self._last_graph_signature: tuple | None = None

        # Graph scope keywords for intent detection
        self.GRAPH_SCOPE_KEYWORDS = (
            "영향권",
            "영향",
            "범위",
            "의존",
            "dependency",
            "impact",
        )
        self.GRAPH_SCOPE_METRIC_KEYWORDS = (
            "cpu",
            "latency",
            "error",
            "memory",
            "disk",
            "network",
        )

        # Flow span tracking
        self._flow_spans_enabled: bool = False
        self._runner_span_id: str | None = None

        # Tool infrastructure
        self._tool_cache = ToolResultCache()
        self._tool_executor = get_tool_executor(cache=self._tool_cache)
        self._tool_selector = SmartToolSelector()
        self._tracer = ExecutionTracer()

        # CI search cache for performance optimization
        self._ci_search_cache = CICache(
            max_size=500,
            default_ttl=timedelta(seconds=300),
        )

        # Stage execution infrastructure
        self._execution_context = self._build_execution_context()
        self._stage_executor = StageExecutor(
            self._execution_context, tool_executor=self._tool_executor
        )

    def _build_execution_context(self) -> ExecutionContext:
        """Build execution context from request context and runner state.

        Returns:
            ExecutionContext with trace ID, rerun payload, and asset overrides
        """
        context = get_request_context()
        trace_id = (
            context.get("trace_id") or context.get("request_id") or str(uuid.uuid4())
        )
        rerun_payload = None
        if (
            self.rerun_context.selected_ci_id
            or self.rerun_context.selected_secondary_ci_id
        ):
            rerun_payload = {
                "selected_ci_id": self.rerun_context.selected_ci_id,
                "selected_secondary_ci_id": self.rerun_context.selected_secondary_ci_id,
            }
        return ExecutionContext(
            tenant_id=self.tenant_id,
            question=self.question,
            trace_id=trace_id,
            rerun_context=rerun_payload,
            test_mode=bool(self.asset_overrides),
            asset_overrides=self.asset_overrides,
        )

    def _runner_context(self) -> Dict[str, Any]:
        """Get runner context for logging."""
        return {
            "tenant_id": self.tenant_id,
            "trace_id": getattr(self._execution_context, "trace_id", None),
        }
