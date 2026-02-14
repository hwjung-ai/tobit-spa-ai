"""
Tool Executor Module - Phase 7

Extracts tool execution logic from runner.py including:
- Core tool execution methods (_execute_tool, _execute_tool_async, _execute_tool_with_tracing)
- Tool selection methods (_select_best_tools, _selection_strategy, _estimate_tool_times)
- Registry wrapper methods for CI, Metric, Graph, History, and CEP tools
- Both sync and async execution paths with tracing support
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal

from core.logging import get_logger, get_request_context

from app.modules.ops.services.orchestration.orchestrator.tool_selector import (
    SelectionStrategy,
    SmartToolSelector,
    ToolSelectionContext,
)
from app.modules.ops.services.orchestration.planner.plan_schema import PlanMode
from app.modules.ops.services.orchestration.tools import (
    ToolContext,
    ToolType,
)
from app.modules.ops.services.orchestration.tools.observability import ExecutionTracer

MODULE_LOGGER = get_logger(__name__)

# FilterSpec type alias
FilterSpec = Dict[str, Any]


class ToolExecutor:
    """
    Handles all tool execution operations including registry calls and tracing.

    Responsibilities:
    - Direct tool execution (sync/async)
    - Tool execution with tracing
    - Tool selection and ranking
    - System load estimation
    - 11 registry wrapper methods for each tool type
    """

    def __init__(
        self,
        tenant_id: str,
        tool_executor: Any,
        tool_selector: SmartToolSelector,
        tracer: ExecutionTracer,
    ):
        """
        Initialize ToolExecutor.

        Args:
            tenant_id: Current tenant ID
            tool_executor: The underlying tool executor instance
            tool_selector: Smart tool selector for ranking
            tracer: Execution tracer for observability
        """
        self.tenant_id = tenant_id
        self._tool_executor = tool_executor
        self._tool_selector = tool_selector
        self._tracer = tracer

    # Core Execution Methods (3 methods)

    def execute_tool(
        self, tool_type: ToolType, operation: str, **params
    ) -> Dict[str, Any]:
        """
        Execute a tool through the registry with standardized error handling.

        Args:
            tool_type: Type of tool to execute
            operation: Operation to perform
            **params: Operation-specific parameters

        Returns:
            Tool result data

        Raises:
            ValueError: If tool execution fails
        """
        context = ToolContext(
            tenant_id=self.tenant_id,
            request_id=get_request_context().get("request_id"),
            trace_id=get_request_context().get("trace_id"),
        )

        # Handle string tool_type (for generic orchestration)
        tool_type_str = tool_type if isinstance(tool_type, str) else tool_type.value

        params_with_op = {"operation": operation, **params}
        result = self._tool_executor.execute(tool_type_str, context, params_with_op)

        if not result.success:
            raise ValueError(result.error or "Unknown tool error")

        return result.data

    async def execute_tool_async(
        self, tool_type: ToolType, operation: str, **params
    ) -> Dict[str, Any]:
        """
        Execute a tool asynchronously through the registry.
        """
        # Handle string tool_type (for generic orchestration)
        tool_type_str = tool_type if isinstance(tool_type, str) else tool_type.value

        context = ToolContext(
            tenant_id=self.tenant_id,
            request_id=get_request_context().get("request_id"),
            trace_id=get_request_context().get("trace_id"),
        )
        params_with_op = {"operation": operation, **params}
        return await self._tool_executor.execute_async(
            tool_type_str, context, params_with_op
        )

    async def execute_tool_with_tracing(
        self, tool_type: ToolType, operation: str, **params
    ) -> Dict[str, Any]:
        """Execute a tool with distributed tracing support."""
        # Handle string tool_type (for generic orchestration)
        tool_type_str = tool_type if isinstance(tool_type, str) else tool_type.value
        trace_id = self._tracer.start_trace(tool_type_str, operation, params)
        try:
            result = await self.execute_tool_async(tool_type, operation, **params)
            records = result.get("records") if isinstance(result, dict) else None
            result_count = len(records) if isinstance(records, list) else None
            self._tracer.end_trace(
                trace_id,
                success=True,
                result_size=len(str(result)),
                result_count=result_count,
            )
            return result
        except Exception as exc:
            self._tracer.end_trace(
                trace_id,
                success=False,
                error=str(exc),
            )
            raise

    # Tool Selection Methods (3 methods)

    async def select_best_tools(self) -> List[str]:
        """Select and rank tools based on execution context."""
        context = ToolSelectionContext(
            intent=None,  # Plan intent would be passed in by caller
            user_pref=self.selection_strategy(None),
            current_load=await self.get_system_load(),
            cache_status={},
            estimated_time=self.estimate_tool_times(),
            mode_hint=None,
        )
        ranked = await self._tool_selector.select_tools(context)
        return [tool for tool, _ in ranked]

    async def get_system_load(self) -> Dict[str, float]:
        """Get current system load for each tool."""
        # Placeholder implementation - real implementation would read from monitoring data
        return {tool: 0.0 for tool in self._tool_selector.tool_profiles.keys()}

    def selection_strategy(self, plan_mode: PlanMode | None) -> SelectionStrategy:
        """Determine tool selection strategy based on plan mode."""
        if plan_mode == PlanMode.CI:
            return SelectionStrategy.FASTEST
        return SelectionStrategy.MOST_ACCURATE

    def estimate_tool_times(self) -> Dict[str, float]:
        """Estimate execution time for each tool."""
        return {
            name: profile.get("base_time", 100.0)
            for name, profile in self._tool_selector.tool_profiles.items()
        }

    # CI Tool Helpers (4 sync methods)

    def ci_search(
        self,
        keywords: Iterable[str] | None = None,
        filters: Iterable[FilterSpec] | None = None,
        limit: int | None = None,
        sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Execute CI search through ToolRegistry."""
        result = self.execute_tool(
            "ci",
            "search",
            keywords=keywords,
            filters=filters,
            limit=limit,
            sort=sort,
        )
        return [r.dict() if hasattr(r, "dict") else r for r in result.records]

    def ci_get(self, ci_id: str) -> Dict[str, Any] | None:
        """Execute CI get through ToolRegistry."""
        try:
            result = self.execute_tool("ci", "get", ci_id=ci_id)
            return result.dict() if hasattr(result, "dict") else result
        except ValueError:
            return None

    def ci_get_by_code(self, ci_code: str) -> Dict[str, Any] | None:
        """Execute CI get_by_code through ToolRegistry."""
        try:
            result = self.execute_tool("ci", "get_by_code", ci_code=ci_code)
            return result.dict() if hasattr(result, "dict") else result
        except ValueError:
            return None

    def ci_aggregate(
        self,
        group_by: Iterable[str],
        metrics: Iterable[str],
        filters: Iterable[FilterSpec] | None = None,
        ci_ids: Iterable[str] | None = None,
        top_n: int | None = None,
    ) -> Dict[str, Any]:
        """Execute CI aggregate through ToolRegistry."""
        result = self.execute_tool(
            "ci",
            "aggregate",
            group_by=group_by,
            metrics=metrics,
            filters=filters,
            ci_ids=ci_ids,
            top_n=top_n,
        )
        return result.dict() if hasattr(result, "dict") else result

    def ci_list_preview(
        self,
        limit: int,
        offset: int = 0,
        filters: Iterable[FilterSpec] | None = None,
    ) -> Dict[str, Any]:
        """Execute CI list_preview through ToolRegistry."""
        result = self.execute_tool(
            "ci",
            "list_preview",
            limit=limit,
            offset=offset,
            filters=filters,
        )
        return result.dict() if hasattr(result, "dict") else result

    # Metric Tool Helpers (2 sync methods)

    def metric_aggregate(
        self,
        metric_name: str,
        agg: str,
        time_range: str,
        ci_id: str | None = None,
        ci_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Execute Metric aggregate through ToolRegistry."""
        result = self.execute_tool(
            "metric",
            "aggregate",
            metric_name=metric_name,
            agg=agg,
            time_range=time_range,
            ci_id=ci_id,
            ci_ids=ci_ids,
        )
        return result.dict() if hasattr(result, "dict") else result

    def metric_series_table(
        self,
        ci_id: str,
        metric_name: str,
        time_range: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Execute Metric series through ToolRegistry."""
        result = self.execute_tool(
            "metric",
            "series",
            ci_id=ci_id,
            metric_name=metric_name,
            time_range=time_range,
            limit=limit,
        )
        return result.dict() if hasattr(result, "dict") else result

    # Graph Tool Helpers (2 sync methods)

    def graph_expand(
        self,
        ci_id: str,
        view: str,
        depth: int,
        limits: dict[str, int],
    ) -> Dict[str, Any]:
        """Execute Graph expand through ToolRegistry."""
        result = self.execute_tool(
            "graph",
            "expand",
            ci_id=ci_id,
            view=view,
            depth=depth,
            limits=limits,
        )
        return result if isinstance(result, dict) else result.dict()

    def graph_path(
        self,
        source_id: str,
        target_id: str,
        hops: int,
    ) -> Dict[str, Any]:
        """Execute Graph path through ToolRegistry."""
        result = self.execute_tool(
            "graph",
            "path",
            ci_id=source_id,
            target_ci_id=target_id,
            max_hops=hops,
        )
        return result if isinstance(result, dict) else result.dict()

    # History Tool Helpers (1 sync method)

    def history_recent(
        self,
        history_spec: Any,
        ci_context: Dict[str, Any],
        ci_ids: list[str] | None = None,
        time_range: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Execute History event_log through ToolRegistry."""
        final_time_range = (
            time_range or getattr(history_spec, "time_range", None) or "last_7d"
        )
        final_limit = limit or getattr(history_spec, "limit", None) or 50

        result = self.execute_tool(
            "history",
            "event_log",
            ci=ci_context,
            time_range=final_time_range,
            limit=final_limit,
            ci_ids=ci_ids,
        )
        return result if isinstance(result, dict) else result.dict()

    # CEP Tool Helpers (1 sync method)

    def cep_simulate(
        self,
        rule_id: str | None,
        ci_context: Dict[str, Any],
        metric_context: Dict[str, Any] | None,
        history_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """Execute CEP simulate through ToolRegistry."""
        result = self.execute_tool(
            "cep",
            "simulate",
            rule_id=rule_id or "",
            ci_context=ci_context,
            metric_context=metric_context,
            history_context=history_context,
        )
        return result if isinstance(result, dict) else result.dict()

    # Async Tool Helpers (4 async methods)

    async def ci_search_async(
        self,
        keywords: Iterable[str] | None = None,
        filters: Iterable[FilterSpec] | None = None,
        limit: int | None = None,
        sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Execute CI search asynchronously through ToolRegistry."""
        result = await self.execute_tool_with_tracing(
            "ci",
            "search",
            keywords=keywords,
            filters=filters,
            limit=limit,
            sort=sort,
        )
        return [r.dict() if hasattr(r, "dict") else r for r in result.records]

    async def ci_get_async(self, ci_id: str) -> Dict[str, Any] | None:
        """Execute CI get asynchronously through ToolRegistry."""
        try:
            result = await self.execute_tool_with_tracing(
                "ci", "get", ci_id=ci_id
            )
            return result.dict() if hasattr(result, "dict") else result
        except ValueError:
            return None

    async def ci_aggregate_async(
        self,
        group_by: Iterable[str],
        metrics: Iterable[str],
        filters: Iterable[FilterSpec] | None = None,
        ci_ids: Iterable[str] | None = None,
        top_n: int | None = None,
    ) -> Dict[str, Any]:
        """Execute CI aggregate asynchronously through ToolRegistry."""
        result = await self.execute_tool_with_tracing(
            "ci",
            "aggregate",
            group_by=group_by,
            metrics=metrics,
            filters=filters,
            ci_ids=ci_ids,
            top_n=top_n,
        )
        return result.dict() if hasattr(result, "dict") else result

    async def metric_aggregate_async(
        self,
        metric_name: str,
        agg: str,
        time_range: str,
        ci_id: str | None = None,
        ci_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Execute Metric aggregate asynchronously through ToolRegistry."""
        result = await self.execute_tool_with_tracing(
            "metric",
            "aggregate",
            metric_name=metric_name,
            agg=agg,
            time_range=time_range,
            ci_id=ci_id,
            ci_ids=ci_ids,
        )
        return result.dict() if hasattr(result, "dict") else result
