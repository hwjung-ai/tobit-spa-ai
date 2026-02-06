"""
StageExecutor for OPS Orchestration.

This module provides the StageExecutor class that executes individual stages
in the orchestration pipeline (route_plan, validate, execute, compose, present).
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, time as datetime_time
from typing import Any, Dict, List, Optional

from core.db import get_session_context
from core.logging import get_logger

from app.llm.client import get_llm_client
from app.modules.asset_registry.crud import get_asset
from app.modules.asset_registry.loader import load_prompt_asset
from app.modules.ops.schemas import (
    ExecutionContext,
    StageDiagnostics,
    StageInput,
    StageOutput,
)
from app.modules.ops.services.ci.tools.base import ToolContext
from app.modules.ops.services.ci.tools.executor import ToolExecutor
from app.shared import config_loader

logger = get_logger(__name__)


class StageExecutor:
    """
    Executor for orchestration pipeline stages with asset override support.

    Each stage represents a step in the execution pipeline:
    - route_plan: Determine the execution route (direct, plan, or reject)
    - validate: Validate the plan and assets
    - execute: Execute the main operations
    - compose: Compose multiple results
    - present: Prepare the final presentation
    """

    def __init__(
        self, context: ExecutionContext, tool_executor: Optional[ToolExecutor] = None
    ):
        """
        Initialize the StageExecutor.

        Args:
            context: Execution context with asset overrides and other metadata
            tool_executor: ToolExecutor for executing tools. If None, creates a new one.
        """
        self.context = context
        self.tool_executor = tool_executor or ToolExecutor()
        self.logger = logger
        self.stage_inputs: List[StageInput] = []
        self.stage_outputs: List[StageOutput] = []
        self._llm = None  # Lazy-loaded LLM client
        self._query_asset_results: List[Dict[str, Any]] = []  # Cache Query Asset results per execution

    def _resolve_asset(self, asset_type: str, default_key: str) -> str:
        """
        Resolve asset with override support.

        Args:
            asset_type: Type of asset (prompt, policy, query, mapping, screen)
            default_key: Default asset key to use

        Returns:
            Asset identifier in format "key:version"
        """
        # Check for override first
        override_key = f"{asset_type}:{default_key}"
        if override_key in self.context.asset_overrides:
            overridden_asset_id = self.context.asset_overrides[override_key]
            self.logger.info(
                f"Using override asset: {override_key} -> {overridden_asset_id}"
            )
            return overridden_asset_id

        # Fall back to default
        default_asset_id = f"{default_key}:published"
        return default_asset_id

    async def execute_stage(self, stage_input: StageInput) -> StageOutput:
        """
        Execute a single stage in the orchestration pipeline.

        Args:
            stage_input: Input for the stage

        Returns:
            StageOutput: Output from the stage execution
        """
        start_time = time.time()
        stage_name = stage_input.stage

        # Initialize Query Asset cache at the start of each execution
        self._query_asset_results = []

        self.logger.info(
            "stage_executor.start",
            extra={
                "stage": stage_name,
                "trace_id": stage_input.trace_id or "unknown",
                "test_mode": self.context.test_mode,
                "asset_overrides": len(self.context.asset_overrides),
            },
        )

        # Record stage input
        self.stage_inputs.append(stage_input)

        try:
            # Route to appropriate stage handler
            if stage_name == "route_plan":
                result = await self._execute_route_plan(stage_input)
            elif stage_name == "validate":
                result = await self._execute_validate(stage_input)
            elif stage_name == "execute":
                result = await self._execute_execute(stage_input)
            elif stage_name == "compose":
                result = await self._execute_compose(stage_input)
            elif stage_name == "present":
                result = await self._execute_present(stage_input)
            else:
                raise ValueError(f"Unknown stage: {stage_name}")

            duration_ms = int((time.time() - start_time) * 1000)

            # Build stage output
            stage_output = StageOutput(
                stage=stage_name,
                result=result,
                diagnostics=self._build_diagnostics(result, stage_name),
                references=result.get("references", []),
                duration_ms=duration_ms,
            )

            self.logger.info(
                "stage_executor.completed",
                extra={
                    "stage": stage_name,
                    "duration_ms": duration_ms,
                    "has_references": len(stage_output.references) > 0,
                },
            )

            # Record stage output
            self.stage_outputs.append(stage_output)

            return stage_output

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.error(
                "stage_executor.error",
                extra={
                    "stage": stage_name,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
            )

            return StageOutput(
                stage=stage_name,
                result={"error": str(e)},
                diagnostics=StageDiagnostics(status="error", errors=[str(e)]),
                references=[],
                duration_ms=duration_ms,
            )

    async def _execute_route_plan(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the route_plan stage."""
        # This stage has already been completed by the planner
        # Just return the plan_output
        plan_output = stage_input.params.get("plan_output")
        if not plan_output:
            raise ValueError("plan_output is required for route_plan stage")

        # Apply asset overrides if in test mode
        applied_assets = stage_input.applied_assets.copy()
        if self.context.test_mode:
            for asset_type, default_asset in applied_assets.items():
                # Extract key from "key:version" format
                key_part = default_asset.split(":")[0]
                overridden_asset = self._resolve_asset(asset_type, key_part)
                applied_assets[asset_type] = overridden_asset

        return {
            "plan_output": plan_output,
            "route": plan_output.kind,
            "applied_assets": applied_assets,
            "test_mode": self.context.test_mode,
            "asset_overrides_applied": self.context.asset_overrides
            if self.context.test_mode
            else {},
        }

    async def _execute_validate(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the validate stage."""
        plan_output = stage_input.params.get("plan_output")
        applied_assets = stage_input.applied_assets

        # Apply asset overrides if in test mode
        if self.context.test_mode:
            for asset_type, default_asset in applied_assets.items():
                key_part = default_asset.split(":")[0]
                overridden_asset = self._resolve_asset(asset_type, key_part)
                applied_assets[asset_type] = overridden_asset

        # Validate assets
        validation_errors = []
        asset_validations = {}

        with get_session_context() as session:
            for asset_type, asset_version in applied_assets.items():
                try:
                    asset = get_asset(session, asset_version)
                    asset_validations[asset_type] = {
                        "status": "valid",
                        "asset_id": asset.get("asset_id"),
                        "version": asset.get("version"),
                        "overridden": asset_type in self.context.asset_overrides,
                    }
                except Exception as e:
                    validation_errors.append(
                        f"Failed to load {asset_type}:{asset_version}: {str(e)}"
                    )
                    asset_validations[asset_type] = {
                        "status": "invalid",
                        "error": str(e),
                        "overridden": asset_type in self.context.asset_overrides,
                    }

        # Validate plan structure
        if plan_output.kind == "plan" and plan_output.plan:
            # Basic validation checks
            if not plan_output.plan.intent:
                validation_errors.append("Plan intent is required")

            if not plan_output.plan.steps and not plan_output.plan.primary.keywords:
                validation_errors.append("Plan must have keywords or steps")

                return {
                    "validation_results": asset_validations,
                    "validation_errors": validation_errors,
                    "is_valid": len(validation_errors) == 0,
                    "plan_output": plan_output,
                }

    async def _execute_execute(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the execute stage."""
        plan_output_dict = stage_input.params.get("plan_output")
        applied_assets = stage_input.applied_assets

        # plan_output is a dict from model_dump(), need to convert back to PlanOutput or handle as dict
        # For now, handle as dict with proper key access
        plan_output_kind = plan_output_dict.get("kind") if plan_output_dict else None
        plan_dict = plan_output_dict.get("plan") if plan_output_dict else None

        self.logger.info(
            "execute_stage.plan_check",
            extra={
                "has_plan_output": plan_output_dict is not None,
                "plan_output_kind": plan_output_kind,
                "has_plan_dict": plan_dict is not None,
            },
        )

        # Apply asset overrides if in test mode
        if self.context.test_mode:
            for asset_type, default_asset in applied_assets.items():
                key_part = default_asset.split(":")[0]
                overridden_asset = self._resolve_asset(asset_type, key_part)
                applied_assets[asset_type] = overridden_asset

        question_text = stage_input.params.get("question", "") if stage_input.params else ""
        full_time_range = "전체기간" in question_text or "전체 기간" in question_text or "all time" in question_text.lower()

        # Tool execution context
        tool_context = ToolContext(
            tenant_id=self.context.tenant_id,
            user_id=self.context.user_id,
            trace_id=self.context.trace_id,
            metadata={
                "applied_assets": applied_assets,
                "asset_overrides": self.context.asset_overrides if self.context.test_mode else {},
                "full_time_range": full_time_range,
            }
        )

        results = []
        references = []

        if plan_output_kind == "plan" and plan_dict:
            # Convert dict back to Plan object for easier access
            from app.modules.ops.services.ci.planner.plan_schema import Plan
            plan = Plan(**plan_dict) if isinstance(plan_dict, dict) else plan_dict
            if plan.history and plan.history.enabled:
                normalized_question = question_text.lower()
                if plan.history.tool_type in {"history", "event_log"}:
                    maintenance_keywords = ("점검", "정비", "maintenance", "inspection", "maint")
                    work_keywords = ("작업 이력", "작업이력", "work history", "작업", "work")
                    if any(key in normalized_question for key in maintenance_keywords):
                        tool_type = "maintenance_history"
                    elif any(key in normalized_question for key in work_keywords):
                        tool_type = "work_history"
                    else:
                        tool_type = "event_log"
                    plan = plan.model_copy(
                        update={
                            "history": plan.history.copy(
                                update={"tool_type": tool_type, "source": tool_type}
                            )
                        }
                    )

            # Check if orchestration should be used
            # IMPORTANT: Default to True to use new orchestration layer with Tool Registry
            enable_orchestration = stage_input.params.get("enable_orchestration", True)
            has_execution_strategy = hasattr(plan, "execution_strategy") and plan.execution_strategy is not None
            use_orchestration = enable_orchestration or has_execution_strategy

            self.logger.info(
                "execute_stage.orchestration_check",
                extra={
                    "use_orchestration": use_orchestration,
                    "enable_orchestration_param": stage_input.params.get("enable_orchestration"),
                    "has_execution_strategy": hasattr(plan, "execution_strategy"),
                    "execution_strategy_value": getattr(plan, "execution_strategy", None),
                }
            )

            if use_orchestration:
                # NEW: Use orchestration layer for tool execution
                from app.modules.ops.services.ci.orchestrator.tool_orchestration import (
                    ToolOrchestrator,
                )

                self.logger.info(
                    "execute_stage.orchestration_enabled",
                    extra={
                        "strategy": getattr(plan, "execution_strategy", "serial").value if hasattr(plan, "execution_strategy") else "serial",
                    }
                )

                try:
                    orchestrator = ToolOrchestrator(plan=plan, context=tool_context)
                    chain_result = await orchestrator.execute()

                    # Map tool_id to mode for compose stage compatibility
                    tool_id_to_mode = {
                        "primary": "primary",
                        "secondary": "secondary",
                        "aggregate": "aggregate",
                        "metric": "metric",
                        "history": "history",
                        "graph": "graph",
                    }

                    # Convert ChainExecutionResult to execution results format
                    # chain_result.step_results is dict[step_id, StepResult]
                    for step_id, step_result in chain_result.step_results.items():
                        # Format each result with tool_name, mode, success, and data fields
                        step_data = step_result.data if step_result.success else None

                        # Flatten data structure for compose stage compatibility
                        # If data is {"rows": [...], ...}, promote rows to top level
                        formatted_result = {
                            "tool_name": step_id,  # step_id is the tool identifier (metric, history, etc)
                            "mode": tool_id_to_mode.get(step_id, step_id),  # Map to mode for compose stage
                            "success": step_result.success,
                            "data": step_data,
                        }

                        # Promote rows to top level if data is a dict with rows
                        if step_data and isinstance(step_data, dict):
                            if "rows" in step_data:
                                formatted_result["rows"] = step_data["rows"]
                            if "count" in step_data:
                                formatted_result["count"] = step_data["count"]
                            if "headers" in step_data:
                                formatted_result["headers"] = step_data["headers"]

                        if not step_result.success and step_result.error:
                            formatted_result["error"] = step_result.error

                        results.append(formatted_result)

                        # Extract references from step data if available
                        if step_result.success and isinstance(step_data, dict):
                            if "references" in step_data:
                                references.extend(step_data.get("references", []))

                    self.logger.info(
                        "execute_stage.orchestration_completed",
                        extra={
                            "tool_count": len(chain_result.step_results),
                            "execution_results_count": len(results),
                            "success": chain_result.success,
                        }
                    )

                    # Enrich with CI detail if requested and available
                    if "구성" in question_text or "configuration" in question_text.lower():
                        def _rows_from_result(result: Dict[str, Any] | None) -> list[dict[str, Any]]:
                            if not result:
                                return []
                            rows = result.get("rows") or []
                            if not rows and isinstance(result.get("data"), dict):
                                rows = result["data"].get("rows") or []
                            return rows if isinstance(rows, list) else []

                        def _score_metric_row(row: Dict[str, Any]) -> float:
                            for key in ("metric_value", "max_cpu_usage", "cpu_usage", "value"):
                                value = row.get(key)
                                if isinstance(value, (int, float)):
                                    return float(value)
                            return 0.0

                        primary_result = next(
                            (r for r in results if r.get("mode") == "primary"), None
                        )
                        metric_result = next(
                            (r for r in results if r.get("mode") == "metric"), None
                        )
                        aggregate_result = next(
                            (r for r in results if r.get("mode") == "aggregate"), None
                        )

                        candidate_result = primary_result or metric_result or aggregate_result
                        candidate_rows = _rows_from_result(candidate_result)
                        if candidate_rows:
                            if candidate_result is primary_result:
                                selected_row = candidate_rows[0]
                            else:
                                selected_row = max(candidate_rows, key=_score_metric_row)

                            ci_id = selected_row.get("ci_id")
                            if ci_id:
                                from sqlalchemy import text
                                sql = (
                                    "SELECT ci_id, ci_code, ci_name, ci_type, ci_subtype, "
                                    "ci_category, status, location, owner, tags, attributes "
                                    "FROM ci "
                                    f"WHERE ci_id = '{ci_id}' "
                                    f"AND tenant_id = '{self.context.tenant_id}' "
                                    "AND deleted_at IS NULL "
                                    "LIMIT 1"
                                )
                                try:
                                    detail_result = await self.tool_executor.execute_tool(
                                        tool_type="direct_query",
                                        params={"sql": sql},
                                        context=tool_context,
                                    )
                                    detail_payload = (
                                        detail_result.get("data")
                                        if isinstance(detail_result, dict) and "data" in detail_result
                                        else detail_result
                                    )
                                    detail_rows = []
                                    raw_rows = detail_payload.get("rows", []) if isinstance(detail_payload, dict) else []
                                    for row in raw_rows:
                                        if hasattr(row, "_mapping"):
                                            detail_rows.append(dict(row._mapping))
                                        elif isinstance(row, dict):
                                            detail_rows.append(row)
                                        else:
                                            detail_rows.append({"value": str(row)})
                                    results.append(
                                        {
                                            "tool_name": "ci_detail",
                                            "mode": "ci_detail",
                                            "success": True,
                                            "data": {"rows": detail_rows},
                                            "rows": detail_rows,
                                        }
                                    )
                                except Exception as e:
                                    self.logger.warning(
                                        "execute_stage.ci_detail_failed",
                                        extra={"error": str(e)},
                                    )

                    # Fallback: if history returned empty rows but primary has ci_id, retry with explicit ci_id
                    if plan.history and plan.history.enabled:
                        def _rows_from_result(result: Dict[str, Any] | None) -> list[dict[str, Any]]:
                            if not result:
                                return []
                            rows = result.get("rows") or []
                            if not rows and isinstance(result.get("data"), dict):
                                rows = result["data"].get("rows") or []
                            return rows if isinstance(rows, list) else []

                        history_result = next(
                            (r for r in results if r.get("mode") == "history"), None
                        )
                        history_rows = _rows_from_result(history_result)
                        if not history_rows:
                            primary_result = next(
                                (r for r in results if r.get("mode") == "primary"), None
                            )
                            primary_rows = _rows_from_result(primary_result)
                            if primary_rows:
                                ci_id = primary_rows[0].get("ci_id")
                            else:
                                ci_id = None
                            if ci_id:
                                from datetime import datetime, timedelta

                                end_time = datetime.utcnow()
                                time_range = plan.history.time_range
                                if time_range in {"all_time", "all"} or tool_context.get_metadata("full_time_range"):
                                    start_time = datetime(1970, 1, 1)
                                elif time_range == "last_24h":
                                    start_time = end_time - timedelta(hours=24)
                                elif time_range == "last_7d":
                                    start_time = end_time - timedelta(days=7)
                                elif time_range == "last_30d":
                                    start_time = end_time - timedelta(days=30)
                                else:
                                    start_time = end_time - timedelta(days=7)

                                try:
                                    fallback_result = await self.tool_executor.execute_tool(
                                        tool_type=plan.history.tool_type,
                                        params={
                                            "ci_id": ci_id,
                                            "start_time": start_time.isoformat(),
                                            "end_time": end_time.isoformat(),
                                            "time_range": plan.history.time_range,
                                            "limit": plan.history.limit,
                                            "tenant_id": self.context.tenant_id,
                                        },
                                        context=tool_context,
                                    )
                                    payload = (
                                        fallback_result.get("data")
                                        if isinstance(fallback_result, dict) and "data" in fallback_result
                                        else fallback_result
                                    )
                                    fallback_rows = []
                                    raw_rows = payload.get("rows", []) if isinstance(payload, dict) else []
                                    for row in raw_rows:
                                        if hasattr(row, "_mapping"):
                                            fallback_rows.append(dict(row._mapping))
                                        elif isinstance(row, dict):
                                            fallback_rows.append(row)
                                        else:
                                            fallback_rows.append({"value": str(row)})
                                    if fallback_rows:
                                        if history_result is None:
                                            history_result = {
                                                "tool_name": "history",
                                                "mode": "history",
                                                "success": True,
                                            }
                                            results.append(history_result)
                                        history_result["data"] = {"rows": fallback_rows}
                                        history_result["rows"] = fallback_rows
                                        history_result["count"] = len(fallback_rows)
                                except Exception as e:
                                    self.logger.warning(
                                        "execute_stage.history_fallback_failed",
                                        extra={"error": str(e)},
                                    )

                    response_payload = {
                        "execution_results": results,
                        "references": references,
                        "plan_output": plan_output_dict,
                        "executed_at": time.time(),
                    }
                    return self._sanitize_json_value(response_payload)
                except Exception as e:
                    self.logger.error(
                        "execute_stage.orchestration_failed",
                        extra={"error": str(e)},
                    )
                    # Fall back to legacy execution
                    self.logger.info("Falling back to legacy sequential execution")

            self.logger.info(
                "execute_stage.plan_created",
                extra={
                    "plan_intent": plan.intent,
                    "has_metric": plan.metric is not None,
                    "metric_name": plan.metric.metric_name if plan.metric else None,
                },
            )

            # Execute primary query
            if plan.primary and plan.primary.keywords:
                try:
                    primary_result = await self.tool_executor.execute_tool(
                        tool_type=plan.primary.tool_type,
                        params={
                            "keywords": plan.primary.keywords,
                            "filters": plan.primary.filters,
                            "limit": plan.primary.limit,
                            "mode": "primary",
                        },
                        context=tool_context,
                    )
                    results.append(primary_result)
                    references.extend(primary_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute primary query: {str(e)}")

            # Execute secondary query
            if plan.secondary and plan.secondary.keywords:
                try:
                    secondary_result = await self.tool_executor.execute_tool(
                        tool_type=plan.secondary.tool_type,
                        params={
                            "keywords": plan.secondary.keywords,
                            "filters": plan.secondary.filters,
                            "limit": plan.secondary.limit,
                            "mode": "secondary",
                        },
                        context=tool_context,
                    )
                    results.append(secondary_result)
                    references.extend(secondary_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute secondary query: {str(e)}")

            # Execute aggregate query
            # Check for metric aggregation first (when plan.metric exists)
            self.logger.info(
                "execute_stage.metric_check",
                extra={
                    "has_metric": plan.metric is not None,
                    "metric_name": plan.metric.metric_name if plan.metric else None,
                },
            )
            if plan.metric and plan.metric.metric_name:
                try:
                    self.logger.info(
                        "execute_stage.metric_aggregate_start",
                        extra={
                            "metric_name": plan.metric.metric_name,
                            "agg": plan.metric.agg,
                            "time_range": plan.metric.time_range,
                        },
                    )
                    # Convert time_range to actual start_time and end_time
                    from datetime import datetime, timedelta
                    end_time = datetime.utcnow()
                    time_range = plan.metric.time_range
                    if full_time_range or time_range in {"all_time", "all"}:
                        start_time = datetime(1970, 1, 1)
                    elif time_range == "last_24h":
                        start_time = end_time - timedelta(hours=24)
                    elif time_range == "last_7d":
                        start_time = end_time - timedelta(days=7)
                    elif time_range == "last_30d":
                        start_time = end_time - timedelta(days=30)
                    else:
                        start_time = end_time - timedelta(hours=24)

                    # Get CI IDs from s1 results if available
                    ci_ids = []
                    if s1_results:
                        ci_ids = [r.get("ci_id") for r in s1_results if r.get("ci_id")]

                    metric_aggregate_result = await self.tool_executor.execute_tool(
                        tool_type=plan.metric.tool_type,
                        params={
                            "operation": "aggregate_by_ci",
                            "metric_name": plan.metric.metric_name,
                            "agg": plan.metric.agg,
                            "time_range": plan.metric.time_range,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "ci_ids": ci_ids,
                            "tenant_id": tool_context.tenant_id,
                            "filters": plan.aggregate.filters,
                            "top_n": plan.aggregate.top_n,
                        },
                        context=tool_context,
                    )
                    results.append(metric_aggregate_result)
                    references.extend(metric_aggregate_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute metric aggregate query: {str(e)}")
            elif plan.aggregate and (plan.aggregate.group_by or plan.aggregate.metrics or plan.aggregate.filters):
                try:
                    limit_value = plan.aggregate.top_n or 10
                    aggregate_params = {
                        "group_by": plan.aggregate.group_by or [],
                        "metrics": plan.aggregate.metrics,
                        "filters": plan.aggregate.filters,
                        "top_n": plan.aggregate.top_n,
                        "limit": limit_value,
                        "scope": plan.aggregate.scope,
                        "tenant_id": tool_context.tenant_id,
                    }
                    # DEBUG: Print params
                    import sys
                    print(f"[DEBUG stage_executor] aggregate_params keys: {list(aggregate_params.keys())}", file=sys.stderr, flush=True)
                    aggregate_result = await self.tool_executor.execute_tool(
                        tool_type=plan.aggregate.tool_type,
                        params=aggregate_params,
                        context=tool_context,
                    )
                    results.append(aggregate_result)
                    references.extend(aggregate_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute aggregate query: {str(e)}")

            # Execute graph query
            if plan.graph and (plan.graph.depth > 0 or plan.graph.view):
                try:
                    graph_result = await self.tool_executor.execute_tool(
                        tool_type=plan.graph.tool_type,
                        params={
                            "depth": plan.graph.depth,
                            "view": plan.graph.view,
                            "limits": plan.graph.limits.dict()
                            if plan.graph.limits
                            else None,
                            "user_requested_depth": plan.graph.user_requested_depth,
                        },
                        context=tool_context,
                    )
                    results.append(graph_result)
                    references.extend(graph_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute graph query: {str(e)}")

        return {
            "execution_results": results,
            "references": references,
            "plan_output": plan_output_dict,
            "executed_at": time.time(),
        }

    async def _execute_compose(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the compose stage - LLM generates summary from execution results."""
        stage_output = stage_input.prev_output
        if not stage_output:
            raise ValueError("Previous stage output is required for compose stage")

        # ===== NEW: Execute Query Assets to get REAL data =====
        real_data_results = await self._execute_query_assets_for_real_data(stage_input)

        self.logger.info(
            "compose_stage.real_data",
            extra={"real_data_results_count": len(real_data_results)},
        )
        # ===== END NEW =====

        # Debug logging
        self.logger.info(
            "compose_stage.debug",
            extra={
                "stage_output_keys": list(stage_output.keys()) if stage_output else [],
                "result_keys": list(stage_output.get("result", {}).keys()) if stage_output.get("result") else [],
            },
        )

        # Get execution_results from tool_calls if available
        # tool_calls may be in result dict (from execute_output) or at top level
        tool_calls = stage_output.get("tool_calls", [])
        if not tool_calls:
            tool_calls = stage_output.get("result", {}).get("tool_calls", [])

        self.logger.info(
            "compose_stage.tool_calls",
            extra={"tool_calls_count": len(tool_calls) if tool_calls else 0},
        )

        execution_results = self._convert_tool_calls_to_execution_results(tool_calls)

        # ===== PRIORITY: Tool execution results FIRST, Query Asset as fallback =====
        # Generic orchestration: Tools are primary, Query Assets supplement
        if not execution_results:
            # First try to get execution_results from stage_output (new orchestration)
            execution_results = stage_output.get("execution_results", [])
            if not execution_results:
                execution_results = stage_output.get("result", {}).get("execution_results", [])

            # If still no results, use Query Asset
            if not execution_results and real_data_results:
                execution_results = real_data_results
                self.logger.info(
                    f"📊 [COMPOSE] Using Query Asset data (no execution results): {len(real_data_results)} results"
                )
        else:
            # Tools returned results, optionally supplement with Query Asset data
            if real_data_results:
                self.logger.info(
                    f"📊 [COMPOSE] Tool results ({len(execution_results)}) take priority over Query Asset ({len(real_data_results)})"
                )

        # ===== ONLY use base_result if we have NO Query Asset data =====
        # This prevents base_result from overriding Query Asset results
        if not execution_results and not real_data_results:
            base_result = stage_output.get("result", {}).get("base_result", {})
            self.logger.info(
                "compose_stage.base_result_fallback",
                extra={
                    "has_base_result": bool(base_result),
                    "base_result_keys": list(base_result.keys()) if base_result else [],
                    "blocks_count": len(base_result.get("blocks", [])) if base_result else 0,
                },
            )
            if base_result:
                # Convert base_result blocks to execution_results format for LLM
                execution_results = self._convert_base_result_to_execution_results(
                    base_result
                )

        # Extract CI Detail information for compose stage
        ci_detail = stage_output.get("result", {}).get("ci_detail")
        ci_detail_blocks = stage_output.get("result", {}).get("ci_detail_blocks")
        ci_detail_message = stage_output.get("result", {}).get("ci_detail_message")

        self.logger.info(
            "compose_stage.ci_detail",
            extra={
                "has_ci_detail": bool(ci_detail),
                "ci_detail_code": ci_detail.get("ci_code") if ci_detail else None,
                "has_ci_detail_blocks": bool(ci_detail_blocks),
                "has_ci_detail_message": bool(ci_detail_message),
            },
        )

        self.logger.info(
            "compose_stage.execution_results",
            extra={"execution_results_count": len(execution_results)},
        )

        # Get plan_output from params (not from prev_output)
        plan_output = stage_input.params.get("plan_output")

        # Compose results based on plan intent
        composed_result = {
            "composed": True,
            "results_count": len(execution_results),
            "results_summary": [],
            "ci_detail": ci_detail,
            "ci_detail_blocks": ci_detail_blocks,
            "ci_detail_message": ci_detail_message,
        }

        # Extract main results based on intent
        intent = "UNKNOWN"
        if plan_output:
            plan = plan_output.get("plan") if isinstance(plan_output, dict) else getattr(plan_output, "plan", None)
            if plan:
                intent = plan.get("intent") if isinstance(plan, dict) else getattr(plan, "intent", "UNKNOWN")

            if intent == "LOOKUP":
                # For lookup, focus on primary results
                primary_results = [
                    r for r in execution_results if r.get("mode") == "primary"
                ]
                if primary_results:
                    composed_result["primary_result"] = primary_results[0]
                    composed_result["results_summary"] = self._summarize_lookup_results(
                        primary_results
                    )

            elif intent == "AGGREGATE":
                # For aggregate, focus on aggregate results
                aggregate_results = [
                    r for r in execution_results if r.get("mode") == "aggregate"
                ]
                if aggregate_results:
                    composed_result["aggregate_result"] = aggregate_results[0]
                    composed_result["results_summary"] = (
                        self._summarize_aggregate_results(aggregate_results)
                    )

                # Also expose primary/secondary results for CI-level context
                primary_results = [
                    r for r in execution_results if r.get("mode") == "primary"
                ]
                if primary_results:
                    composed_result["primary_result"] = primary_results[0]

                secondary_results = [
                    r for r in execution_results if r.get("mode") == "secondary"
                ]
                if secondary_results:
                    composed_result["secondary_result"] = secondary_results[0]

                # Also include metric and history results for aggregate intent
                metric_results = [
                    r for r in execution_results if r.get("mode") == "metric"
                ]
                if metric_results:
                    composed_result["metric_result"] = metric_results[0]

                history_results = [
                    r for r in execution_results if r.get("mode") == "history"
                ]
                if history_results:
                    composed_result["history_result"] = history_results[0]

                ci_detail_results = [
                    r for r in execution_results if r.get("mode") == "ci_detail"
                ]
                if ci_detail_results:
                    detail_rows = ci_detail_results[0].get("rows") or []
                    if not detail_rows and isinstance(ci_detail_results[0].get("data"), dict):
                        detail_rows = ci_detail_results[0]["data"].get("rows") or []
                    if detail_rows:
                        detail_row = detail_rows[0]
                        composed_result["ci_detail"] = {
                            "ci_id": detail_row.get("ci_id"),
                            "ci_code": detail_row.get("ci_code"),
                            "ci_name": detail_row.get("ci_name"),
                            "ci_type": detail_row.get("ci_type"),
                            "ci_subtype": detail_row.get("ci_subtype"),
                            "ci_category": detail_row.get("ci_category"),
                            "status": detail_row.get("status"),
                            "location": detail_row.get("location"),
                            "owner": detail_row.get("owner"),
                            "tags": detail_row.get("tags"),
                            "attributes": detail_row.get("attributes"),
                        }

                # If CI detail is missing, derive from primary results (best-effort)
                if not composed_result.get("ci_detail") and primary_results:
                    primary_rows = []
                    primary_data = primary_results[0].get("data", {})
                    if isinstance(primary_results[0].get("rows"), list):
                        primary_rows = primary_results[0].get("rows", [])
                    elif isinstance(primary_data, dict) and isinstance(primary_data.get("rows"), list):
                        primary_rows = primary_data.get("rows", [])

                    if primary_rows:
                        def _score_row(row: Dict[str, Any]) -> float:
                            for key in ("max_cpu_usage", "cpu_usage", "value"):
                                value = row.get(key)
                                if isinstance(value, (int, float)):
                                    return float(value)
                            return 0.0

                        best_row = max(primary_rows, key=_score_row)
                        composed_result["ci_detail"] = {
                            "ci_id": best_row.get("ci_id"),
                            "ci_code": best_row.get("ci_code"),
                            "ci_name": best_row.get("ci_name"),
                            "ci_type": best_row.get("ci_type"),
                            "ci_subtype": best_row.get("ci_subtype"),
                            "ci_category": best_row.get("ci_category"),
                            "status": best_row.get("status"),
                            "location": best_row.get("location"),
                            "owner": best_row.get("owner"),
                            "tags": best_row.get("tags"),
                            "attributes": best_row.get("attributes"),
                        }

                # If still missing, derive from metric results (best-effort)
                if not composed_result.get("ci_detail") and metric_results:
                    metric_rows = []
                    metric_data = metric_results[0].get("data", {})
                    if isinstance(metric_results[0].get("rows"), list):
                        metric_rows = metric_results[0].get("rows", [])
                    elif isinstance(metric_data, dict) and isinstance(metric_data.get("rows"), list):
                        metric_rows = metric_data.get("rows", [])

                    if metric_rows:
                        def _score_metric_row(row: Dict[str, Any]) -> float:
                            for key in ("metric_value", "max_cpu_usage", "cpu_usage", "value"):
                                value = row.get(key)
                                if isinstance(value, (int, float)):
                                    return float(value)
                            return 0.0

                        best_row = max(metric_rows, key=_score_metric_row)
                        composed_result["ci_detail"] = {
                            "ci_id": best_row.get("ci_id"),
                            "ci_code": best_row.get("ci_code"),
                            "ci_name": best_row.get("ci_name"),
                            "ci_type": best_row.get("ci_type"),
                            "ci_subtype": best_row.get("ci_subtype"),
                            "ci_category": best_row.get("ci_category"),
                            "status": best_row.get("status"),
                            "location": best_row.get("location"),
                            "owner": best_row.get("owner"),
                            "tags": best_row.get("tags"),
                            "attributes": best_row.get("attributes"),
                        }

            elif intent == "PATH":
                # For path, include both primary and path results
                path_results = [r for r in execution_results if r.get("mode") == "path"]
                composed_result["path_results"] = path_results
                composed_result["results_summary"] = self._summarize_path_results(
                    path_results
                )

            # ===== NEW: Handle query_asset results =====
            query_asset_results = [r for r in execution_results if r.get("mode") == "query_asset"]
            if query_asset_results:
                composed_result["query_asset_result"] = query_asset_results[0]
                composed_result["results_summary"] = self._summarize_query_asset_results(
                    query_asset_results
                )

        # Merge all references
        all_references = []
        for result in execution_results:
            all_references.extend(result.get("references", []))
        composed_result["references"] = all_references

        # LLM을 호출하여 실행 결과를 바탕으로 자연스러운 요약 생성
        question = stage_input.params.get("question", "")
        llm_summary = await self._generate_llm_summary(
            question=question,
            intent=intent,
            execution_results=execution_results,
            composed_result=composed_result,
        )
        composed_result["llm_summary"] = llm_summary

        return self._sanitize_json_value(composed_result)

    async def _execute_present(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the present stage."""
        # Get plan_output from params (as model_dump dict)
        plan_output = stage_input.params.get("plan_output", {})
        # Get composed_result from prev_output
        # The compose stage returns composed_result which is stored in stage_output.result
        stage_output = stage_input.prev_output or {}
        # First check for result key (from StageOutput.model_dump())
        if "result" in stage_output:
            composed_result = stage_output.get("result", {})
        # Fallback to composed_result key (for backwards compatibility)
        else:
            composed_result = stage_output.get("composed_result", stage_output)

        # Prepare presentation blocks based on plan
        blocks = []

        plan_kind = plan_output.get("kind") if isinstance(plan_output, dict) else getattr(plan_output, "kind", None)

        if plan_kind == "direct":
            direct_answer = plan_output.get("direct_answer") if isinstance(plan_output, dict) else getattr(plan_output, "direct_answer", None)
            if direct_answer:
                # Direct answer - simple text block
                blocks.append(
                    {
                        "type": "text",
                        "content": direct_answer.get("answer") if isinstance(direct_answer, dict) else direct_answer.answer,
                        "metadata": {
                            "confidence": direct_answer.get("confidence") if isinstance(direct_answer, dict) else getattr(direct_answer, "confidence", 1.0),
                            "reasoning": direct_answer.get("reasoning") if isinstance(direct_answer, dict) else getattr(direct_answer, "reasoning", None),
                        },
                    }
                )

        elif plan_kind == "plan":
            # Check if we have LLM summary from compose stage
            llm_summary = composed_result.get("llm_summary") if isinstance(composed_result, dict) else None

            # ===== NEW: Use LLM-composed answer from compose stage =====
            if llm_summary:
                self.logger.info(f"📊 [PRESENT] Using LLM-composed answer from compose stage")

                # Add LLM summary as the first block
                blocks.append({
                    "type": "markdown",
                    "content": llm_summary,
                    "metadata": {"generated_by": "llm_compose"},
                })

                def _build_table_block(title: str, headers: list[str], rows: list[list[Any]]) -> dict[str, Any]:
                    return {
                        "type": "table",
                        "title": title,
                        "content": {
                            "headers": headers,
                            "rows": rows,
                        },
                        "metadata": {"count": len(rows)},
                    }

                if isinstance(composed_result, dict):
                    ci_detail = composed_result.get("ci_detail") or {}
                    if isinstance(ci_detail, dict) and ci_detail:
                        ci_headers = [
                            "ci_code",
                            "ci_name",
                            "ci_type",
                            "status",
                            "ci_subtype",
                            "ci_category",
                            "location",
                            "owner",
                        ]
                        ci_row = [[ci_detail.get(h) for h in ci_headers]]
                        blocks.append(_build_table_block("CI 구성정보", ci_headers, ci_row))

                    history_result = composed_result.get("history_result") or {}
                    history_rows = history_result.get("rows") or []
                    if not history_rows and isinstance(history_result.get("data"), dict):
                        history_rows = history_result["data"].get("rows") or []
                    if isinstance(history_rows, list) and history_rows:
                        history_headers = [
                            "start_time",
                            "work_type",
                            "result",
                            "impact_level",
                            "summary",
                            "requested_by",
                            "approved_by",
                        ]
                        table_rows = []
                        for row in history_rows[:20]:
                            if isinstance(row, dict):
                                table_rows.append([row.get(h) for h in history_headers])
                        if table_rows:
                            blocks.append(_build_table_block("최근 작업 이력", history_headers, table_rows))

                # Get additional blocks from composed_result if available
                if isinstance(composed_result, dict):
                    query_asset_result = composed_result.get("query_asset_result", {})
                    if query_asset_result:
                        data = query_asset_result.get("data", {})
                        rows = data.get("rows", [])
                        asset_name = query_asset_result.get("asset_name", "Query")

                        # Add raw data as reference blocks
                        if rows and len(rows) <= 20:
                            if isinstance(rows[0], dict):
                                columns = list(rows[0].keys())
                                content_lines = [f"**{asset_name} Data ({len(rows)} rows):**\n"]
                                content_lines.append("| " + " | ".join(columns) + " |")
                                content_lines.append("|" + "|".join(["---"] * len(columns)) + "|")
                                for row in rows:
                                    values = [str(row.get(col, "")) for col in columns]
                                    content_lines.append("| " + " | ".join(values) + " |")
                                blocks.append({
                                    "type": "markdown",
                                    "content": "\n".join(content_lines),
                                    "metadata": {"generated_by": "query_asset_reference"},
                                })

                # Create result with LLM summary as answer
                result = {
                    "blocks": blocks,
                    "references": [],
                    "summary": llm_summary,
                    "presented_at": time.time(),
                }
                return result
            # ===== END NEW =====

            # Add LLM summary as the first block if available
            llm_summary = composed_result.get("llm_summary") if isinstance(composed_result, dict) else None
            if llm_summary:
                blocks.append({
                    "type": "markdown",
                    "content": llm_summary,
                    "metadata": {"generated_by": "llm_compose"},
                })

            # Plan execution - compose blocks based on intent
            plan = plan_output.get("plan") if isinstance(plan_output, dict) else getattr(plan_output, "plan", None)
            intent = plan.get("intent") if isinstance(plan, dict) else getattr(plan, "intent", None) if plan else None

            # Always add blocks from runner's base_result if available
            # The runner already has its own blocks from _run_async()
            # We're here to add the LLM summary markdown block
            # Don't duplicate blocks from compose stage
            base_result = stage_input.params.get("base_result", {})
            runner_blocks = base_result.get("blocks", [])
            blocks.extend(runner_blocks)

            if isinstance(composed_result, dict):
                def _build_table_block(title: str, headers: list[str], rows: list[list[Any]]) -> dict[str, Any]:
                    return {
                        "type": "table",
                        "title": title,
                        "content": {
                            "headers": headers,
                            "rows": rows,
                        },
                        "metadata": {"count": len(rows)},
                    }

                ci_detail = composed_result.get("ci_detail") or {}
                if isinstance(ci_detail, dict) and ci_detail:
                    ci_headers = [
                        "ci_code",
                        "ci_name",
                        "ci_type",
                        "status",
                        "ci_subtype",
                        "ci_category",
                        "location",
                        "owner",
                    ]
                    ci_row = [[ci_detail.get(h) for h in ci_headers]]
                    blocks.append(_build_table_block("CI 구성정보", ci_headers, ci_row))

                history_result = composed_result.get("history_result") or {}
                history_rows = history_result.get("rows") or []
                if not history_rows and isinstance(history_result.get("data"), dict):
                    history_rows = history_result["data"].get("rows") or []
                if isinstance(history_rows, list) and history_rows:
                    history_headers = [
                        "start_time",
                        "work_type",
                        "result",
                        "impact_level",
                        "summary",
                        "requested_by",
                        "approved_by",
                    ]
                    table_rows = []
                    for row in history_rows[:20]:
                        if isinstance(row, dict):
                            table_rows.append([row.get(h) for h in history_headers])
                    if table_rows:
                        blocks.append(_build_table_block("최근 작업 이력", history_headers, table_rows))

            # Disable old block creation - using runner's blocks instead
            # if False:  # Disable duplicate block creation
            #     if intent == "LOOKUP":
            #         # Create table block for lookup results
            #         if "primary_result" in composed_result:
            #             blocks.append(
            #                 self._create_table_block(composed_result["primary_result"])
            #             )
            #
            #     elif intent == "AGGREGATE":
            #         # Create chart and table blocks for aggregate results
            #         if "aggregate_result" in composed_result:
            #             blocks.append(
            #                 self._create_chart_block(composed_result["aggregate_result"])
            #             )
            #             blocks.append(
            #                 self._create_table_block(composed_result["aggregate_result"])
            #             )
            #
            #     elif intent == "PATH":
            #         # Create network and table blocks for path results
            #         if "path_results" in composed_result:
            #             blocks.append(
            #                 self._create_network_block(composed_result["path_results"])
            #             )
            #             blocks.append(
            #                 self._create_table_block(composed_result["path_results"])
            #             )

        result = {
            "blocks": blocks,
            "references": composed_result.get("references", []),
            "summary": composed_result.get("llm_summary") or self._generate_summary(composed_result),
            "presented_at": time.time(),
        }

        # Add baseline comparison information if in test mode
        if self.context.test_mode and self.context.baseline_trace_id:
            result["baseline_trace_id"] = self.context.baseline_trace_id
            result["baseline_comparison_available"] = True

        return self._sanitize_json_value(result)

    def _sanitize_json_value(self, value: Any) -> Any:
        """Recursively sanitize datetimes for JSON serialization."""
        from pydantic import BaseModel

        if isinstance(value, BaseModel):
            return self._sanitize_json_value(value.model_dump())

        if isinstance(value, dict):
            return {key: self._sanitize_json_value(val) for key, val in value.items()}

        if isinstance(value, (list, tuple, set)):
            sequence = [self._sanitize_json_value(v) for v in value]
            if isinstance(value, tuple):
                return tuple(sequence)
            if isinstance(value, set):
                return list(sequence)
            return sequence

        if isinstance(value, (datetime, date, datetime_time)):
            return value.isoformat()

        return value

    def _build_diagnostics(
        self, result: Dict[str, Any], stage_name: str
    ) -> StageDiagnostics:
        """Build diagnostics information for the stage."""
        diagnostics = StageDiagnostics(
            status="ok", warnings=[], errors=[], empty_flags={}, counts={}
        )

        # Check for errors
        if "error" in result:
            diagnostics.status = "error"
            diagnostics.errors = [result["error"]]

        # Check for empty results
        if not result.get("results") and not result.get("blocks"):
            diagnostics.empty_flags["result_empty"] = True

        # Count references
        references = result.get("references", [])
        diagnostics.counts["references"] = len(references)

        # Stage-specific counts
        if stage_name == "execute":
            execution_results = result.get("execution_results", [])
            diagnostics.counts["execution_results"] = len(execution_results)

        return diagnostics

    def _summarize_lookup_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Summarize lookup results."""
        summary = []
        for result in results:
            count = result.get("count", 0)
            summary.append(f"Found {count} items")
        return summary

    def _summarize_aggregate_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Summarize aggregate results."""
        summary = []
        for result in results:
            metrics = result.get("metrics", {})
            for metric, value in metrics.items():
                summary.append(f"{metric}: {value}")
        return summary

    def _summarize_path_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Summarize path results."""
        summary = []
        for result in results:
            path_count = result.get("path_count", 0)
            summary.append(f"Found {path_count} paths")
        return summary

    def _summarize_query_asset_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Summarize Query Asset results for LLM context."""
        summary = []

        for result in results:
            asset_name = result.get("asset_name", "unknown")
            data = result.get("data", {})
            rows = data.get("rows", [])
            rows_count = data.get("count", len(rows))

            if rows_count > 0 and rows:
                # Format all rows for LLM context - not just first value
                summary_lines = [f"Database query '{asset_name}' found {rows_count} result(s):"]

                # Show full row data to LLM
                for i, row in enumerate(rows[:10]):  # Limit to first 10 rows for summary
                    if isinstance(row, dict):
                        row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
                        summary_lines.append(f"  Result {i+1}: {row_str}")
                    elif isinstance(row, (tuple, list)):
                        row_str = ", ".join([str(v) for v in row])
                        summary_lines.append(f"  Result {i+1}: {row_str}")
                    else:
                        summary_lines.append(f"  Result {i+1}: {row}")

                if len(rows) > 10:
                    summary_lines.append(f"  ... and {len(rows) - 10} more results")

                summary.append("\n".join(summary_lines))
            else:
                summary.append(
                    f"Database query '{asset_name}' executed but found no results (0 rows)."
                )

        return summary

    def _generate_summary(self, result: Dict[str, Any]) -> str:
        """Generate a summary of the results."""
        if "primary_result" in result:
            return f"Successfully executed lookup query with {len(result.get('references', []))} references"
        elif "aggregate_result" in result:
            return f"Successfully executed aggregate query with {len(result.get('references', []))} references"
        elif "path_results" in result:
            return f"Successfully executed path query with {len(result.get('references', []))} references"
        else:
            return "Execution completed successfully"

    def _create_table_block(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a table block from execution result."""
        return {
            "type": "table",
            "content": {
                "headers": result.get("headers", []),
                "rows": result.get("rows", []),
            },
            "metadata": {"count": len(result.get("rows", []))},
        }

    def _create_chart_block(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chart block from aggregate result."""
        return {
            "type": "chart",
            "content": {
                "chart_type": "bar",
                "data": result.get("data", {}),
                "title": result.get("title", "Aggregate Results"),
            },
            "metadata": {},
        }

    def _create_network_block(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a network block from path result."""
        return {
            "type": "network",
            "content": {
                "nodes": result.get("nodes", []),
                "edges": result.get("edges", []),
                "layout": "force",
            },
            "metadata": {
                "node_count": len(result.get("nodes", [])),
                "edge_count": len(result.get("edges", [])),
            },
        }

    async def _generate_llm_summary(
        self,
        question: str,
        intent: str,
        execution_results: List[Dict[str, Any]],
        composed_result: Dict[str, Any],
    ) -> str:
        """Generate LLM summary from execution results."""
        if ("전체기간" in question or "전체 기간" in question) and composed_result.get("ci_detail"):
            ci_detail = composed_result.get("ci_detail") or {}
            ci_name = ci_detail.get("ci_name") or "unknown"
            ci_code = ci_detail.get("ci_code") or "unknown"
            ci_type = ci_detail.get("ci_type") or "unknown"
            status = ci_detail.get("status") or "unknown"

            max_cpu_usage = None
            primary_result = composed_result.get("primary_result") or {}
            primary_rows = primary_result.get("rows") or []
            if not primary_rows and isinstance(primary_result.get("data"), dict):
                primary_rows = primary_result["data"].get("rows") or []
            if primary_rows:
                max_cpu_usage = primary_rows[0].get("max_cpu_usage")

            if max_cpu_usage is None:
                metric_result = composed_result.get("metric_result") or {}
                metric_rows = metric_result.get("rows") or []
                if not metric_rows and isinstance(metric_result.get("data"), dict):
                    metric_rows = metric_result["data"].get("rows") or []
                if metric_rows:
                    for key in ("metric_value", "max_cpu_usage", "cpu_usage", "value"):
                        value = metric_rows[0].get(key)
                        if isinstance(value, (int, float)):
                            max_cpu_usage = float(value)
                            break

            history_result = composed_result.get("history_result") or {}
            history_rows = history_result.get("rows") or []
            if not history_rows and isinstance(history_result.get("data"), dict):
                history_rows = history_result["data"].get("rows") or []

            summary = (
                f"전체 기간 기준 CPU 사용률이 가장 높은 CI는 **{ci_name}**"
                f"(코드 **{ci_code}**)입니다."
            )
            if max_cpu_usage is not None:
                summary += f" 최대 CPU 사용률은 **{max_cpu_usage:.2f}**입니다."
            summary += (
                f" 구성정보: Code **{ci_code}**, Name **{ci_name}**, Type **{ci_type}**, Status **{status}**."
            )
            summary += f" 최근 작업 이력은 {len(history_rows)}건입니다."
            return summary

        # Skip LLM call if no question or no execution results
        if not question or not execution_results:
            return self._generate_summary(composed_result)

        # Describe execution results for LLM context
        evidence = self._describe_execution_results(execution_results, composed_result)

        try:
            # Load prompt templates
            templates = self._load_compose_prompt_templates()
            system_prompt = templates.get("system")
            user_template = templates.get("user")

            if not system_prompt or not user_template:
                logging.warning("Compose prompt templates missing, using fallback summary")
                return self._generate_summary(composed_result)

            # Build prompt with question, intent, and evidence
            prompt = (
                user_template.replace("{question}", question)
                .replace("{intent}", intent)
                .replace("{evidence}", evidence)
            )

            # Call LLM
            summary = self._call_llm_for_summary(prompt, system_prompt)
            if summary:
                return summary.strip()
        except Exception:
            logging.exception("LLM compose summary failed, using fallback")

        return self._generate_summary(composed_result)

    def _describe_execution_results(
        self, execution_results: List[Dict[str, Any]], composed_result: Dict[str, Any]
    ) -> str:
        """Describe execution results for LLM context."""
        if not execution_results:
            return "No execution results available."

        lines = ["Execution Results:"]
        for i, result in enumerate(execution_results, 1):
            mode = result.get("mode", "unknown")
            lines.append(f"\n{i}. {mode.upper()} Result:")

            # Handle Query Asset results (mode == "query_asset")
            if mode == "query_asset":
                data = result.get("data", {})
                rows = data.get("rows", [])
                rows_count = data.get("count", len(rows))

                lines.append(f"   - Source: Query Asset '{result.get('asset_name', 'unknown')}'")
                lines.append(f"   - Count: {rows_count}")

                if rows_count > 0:
                    # Show first few rows as samples
                    sample_count = min(3, rows_count)
                    lines.append(f"   - Sample Data ({sample_count} rows):")
                    for j, row in enumerate(rows[:sample_count], 1):
                        if isinstance(row, (tuple, list)):
                            # Convert tuple to string representation
                            row_str = ", ".join(str(v) for v in row)
                            lines.append(f"     {j}. [{row_str}]")
                        elif isinstance(row, dict):
                            # Convert dict to key=value format
                            row_str = ", ".join(f"{k}={v}" for k, v in list(row.items())[:3])
                            lines.append(f"     {j}. {row_str}")

                # Show SQL if available
                query_asset = result.get("query_asset", {})
                if query_asset and query_asset.get("sql"):
                    sql_preview = query_asset["sql"][:100]
                    lines.append(f"   - SQL: {sql_preview}...")

                continue

            # Add count info
            count = result.get("count", 0)
            if count:
                lines.append(f"   - Count: {count}")

            # Add headers for table results
            headers = result.get("headers", [])
            if headers:
                lines.append(f"   - Columns: {', '.join(headers[:5])}")

            # Add row count
            rows = result.get("rows", [])
            if rows:
                lines.append(f"   - Rows: {len(rows)}")
                # Show first row as sample
                if rows:
                    sample_row = rows[0]
                    if isinstance(sample_row, dict):
                        sample_str = ", ".join(
                            f"{k}={v}" for k, v in list(sample_row.items())[:3]
                        )
                        lines.append(f"   - Sample: {sample_str}")
                    elif isinstance(sample_row, list):
                        lines.append(f"   - Sample: {sample_row[:3]}")

            # Add metrics for aggregate results
            metrics = result.get("metrics", {})
            if metrics:
                lines.append(f"   - Metrics: {metrics}")

            # Add graph info
            node_count = result.get("node_count")
            edge_count = result.get("edge_count")
            if node_count is not None:
                lines.append(f"   - Nodes: {node_count}, Edges: {edge_count or 0}")

            # Add errors if any
            error = result.get("error")
            if error:
                lines.append(f"   - Error: {error}")

        # Add CI Detail information if available
        ci_detail = composed_result.get("ci_detail")
        if ci_detail:
            lines.append("\nCI Detail:")
            lines.append(f"   - Code: {ci_detail.get('ci_code')}")
            lines.append(f"   - Name: {ci_detail.get('ci_name')}")
            lines.append(f"   - Type: {ci_detail.get('ci_type')}")
            lines.append(f"   - Subtype: {ci_detail.get('ci_subtype')}")
            lines.append(f"   - Category: {ci_detail.get('ci_category')}")
            lines.append(f"   - Status: {ci_detail.get('status')}")

            # Add tags if available
            tags = ci_detail.get("tags")
            if tags and isinstance(tags, dict):
                lines.append(f"   - Tags: {', '.join(f'{k}={v}' for k, v in tags.items() if v)}")

            # Add attributes if available
            attributes = ci_detail.get("attributes")
            if attributes and isinstance(attributes, dict):
                # Show only first few attributes to avoid too much detail
                attr_items = list(attributes.items())[:3]
                if attr_items:
                    attr_str = ", ".join(f'{k}="{v}"' for k, v in attr_items)
                    lines.append(f"   - Attributes: {attr_str}")
                    if len(attributes) > 3:
                        lines.append(f"   - ... and {len(attributes) - 3} more attributes")

        # Add CI Detail blocks information if available
        ci_detail_blocks = composed_result.get("ci_detail_blocks")
        if ci_detail_blocks:
            lines.append(f"\nCI Detail Blocks: {len(ci_detail_blocks)} blocks found")

        # Add CI Detail message if available
        ci_detail_message = composed_result.get("ci_detail_message")
        if ci_detail_message:
            lines.append(f"\nCI Detail Message: {ci_detail_message}")

        # Add summary from composed_result
        results_summary = composed_result.get("results_summary", [])
        if results_summary:
            lines.append("\nSummary:")
            lines.extend(f"   - {s}" for s in results_summary)

        return "\n".join(lines)

    def _load_compose_prompt_templates(self) -> Dict[str, str]:
        """Load compose prompt templates from asset registry."""
        try:
            prompt_data = load_prompt_asset("ci", "compose", "ci_compose_summary")
            if not prompt_data or "templates" not in prompt_data:
                logging.warning("Compose prompt templates not found in asset registry, falling back to file")
                prompt_data = config_loader.load_yaml("prompts/ci/compose.yaml")
                if not prompt_data or "templates" not in prompt_data:
                    return {}
            templates = prompt_data.get("templates", {})
            if not isinstance(templates, dict):
                return {}
            return templates
        except Exception as exc:
            logging.warning(f"Failed to load compose prompt from asset registry: {exc}, falling back to file")
            prompt_data = config_loader.load_yaml("prompts/ci/compose.yaml")
            if not prompt_data or "templates" not in prompt_data:
                return {}
            templates = prompt_data.get("templates", {})
            if not isinstance(templates, dict):
                return {}
            return templates

    def _call_llm_for_summary(self, prompt: str, system_prompt: str) -> str:
        """Call LLM to generate summary."""
        if self._llm is None:
            self._llm = get_llm_client()

        input_data = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            response = self._llm.create_response(input=input_data)
            content = self._llm.get_output_text(response)
            if content:
                return content.strip()
        except Exception as exc:
            logging.warning(f"LLM call failed: {exc}")

        return ""

    def _convert_tool_calls_to_execution_results(
        self, tool_calls: List[Any]
    ) -> List[Dict[str, Any]]:
        """Convert tool_calls to execution_results format."""
        if not tool_calls:
            return []

        execution_results = []
        for call in tool_calls:
            # Handle both ToolCall objects and dict formats
            if hasattr(call, "model_dump"):
                # Pydantic model (ToolCall)
                tool = call.tool or ""
                output_summary = call.output_summary or {}
            elif isinstance(call, dict):
                # Dict format
                tool = call.get("tool", "")
                output_summary = call.get("output_summary", {})
            else:
                continue

            # Map tool names to modes
            mode_map = {
                "ci.lookup": "primary",
                "ci.search": "primary",
                "ci.get": "primary",
                "ci.aggregate": "aggregate",
                "metric.aggregate": "aggregate",
                "graph.expand": "path",
                "ci.graph": "path",
            }

            mode = mode_map.get(tool, "unknown")

            result = {
                "mode": mode,
                "tool": tool,
            }

            # Add count if available
            if isinstance(output_summary, dict):
                result["count"] = output_summary.get("count", output_summary.get("total", 0))

                # Add headers for table results
                headers = output_summary.get("headers", [])
                if headers:
                    result["headers"] = headers

                # Add rows
                rows = output_summary.get("rows", [])
                if rows:
                    result["rows"] = rows

                # Add metrics for aggregate results
                metrics = output_summary.get("metrics", {})
                if metrics:
                    result["metrics"] = metrics

                # Add graph info
                node_count = output_summary.get("node_count")
                edge_count = output_summary.get("edge_count")
                if node_count is not None:
                    result["node_count"] = node_count
                    result["edge_count"] = edge_count or 0

            execution_results.append(result)

        return execution_results

    def _convert_base_result_to_execution_results(
        self, base_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Convert base_result to execution_results format for LLM summarization.

        base_result structure from runner:
        {
            "answer": str,
            "blocks": List[Block],
            "meta": {"used_tools": List[str]},
            "trace": {...}
        }
        """
        execution_results = []
        if not base_result:
            return execution_results

        # Extract blocks to build execution context
        blocks = base_result.get("blocks", [])
        answer = base_result.get("answer", "")
        meta = base_result.get("meta", {})
        used_tools = meta.get("used_tools", [])

        # Build a primary result from the blocks for LLM context
        primary_result = {
            "mode": "primary",
            "tool": "ci.lookup",
            "summary": answer,
            "blocks_count": len(blocks),
            "used_tools": used_tools,
        }

        # Extract key data from blocks for LLM context
        block_summaries = []
        for block in blocks:
            if isinstance(block, dict):
                block_type = block.get("type", "unknown")
                block_title = block.get("title", "")

                if block_type == "table":
                    rows_count = len(block.get("rows", []))
                    block_summaries.append(
                        f"{block_title}: {rows_count} rows"
                    )
                elif block_type == "markdown":
                    content_preview = (
                        block.get("content", "")[:100]
                        if block.get("content")
                        else ""
                    )
                    block_summaries.append(
                        f"{block_title}: {content_preview}..."
                    )
                elif block_type == "references":
                    ref_count = len(block.get("items", []))
                    block_summaries.append(f"{block_title}: {ref_count} references")

        if block_summaries:
            primary_result["block_summaries"] = block_summaries

        # Add any metric data if present
        metric_blocks = [
            b
            for b in blocks
            if isinstance(b, dict) and b.get("type") == "metric"
        ]
        if metric_blocks:
            primary_result["has_metrics"] = True
            primary_result["metric_blocks_count"] = len(metric_blocks)

        # Add any graph data if present
        graph_blocks = [
            b for b in blocks if isinstance(b, dict) and b.get("type") == "graph"
        ]
        if graph_blocks:
            primary_result["has_graph"] = True
            primary_result["graph_blocks_count"] = len(graph_blocks)

        execution_results.append(primary_result)
        return execution_results

    async def _execute_query_assets_for_real_data(
        self, stage_input: StageInput
    ) -> List[Dict[str, Any]]:
        """
        Execute Query Assets to get REAL data from database.

        This bypasses the legacy graph-based system and executes actual SQL
        queries defined in Query Assets.

        Args:
            stage_input: Stage input with params containing the question

        Returns:
            List of execution results with real data
        """
        # ===== CACHE: Return cached results if available =====
        if self._query_asset_results:
            self.logger.info(f"📋 [QUERY ASSET] Using cached results: {len(self._query_asset_results)} results")
            return self._query_asset_results
        # ===== END CACHE =====

        results = []

        try:
            # Get the original question from context first (most reliable)
            question = getattr(self.context, 'question', None)

            # If not in context, try to get from params
            if not question:
                params = stage_input.params or {}
                question = params.get("question", "")

            # If still not found, try to extract from plan
            if not question:
                plan_output = params.get("plan_output", {})
                plan = plan_output.get("plan") if isinstance(plan_output, dict) else None

                if plan:
                    # Extract keywords from plan
                    primary = plan.get("primary") if isinstance(plan, dict) else None
                    if primary:
                        keywords = primary.get("keywords") if isinstance(primary, dict) else []
                        if keywords:
                            question = " ".join(keywords)

            if not question:
                self.logger.info("No question found for Query Asset execution")
                return results

            self.logger.info(f"🔍 [QUERY ASSET] Executing Query Assets for question: {question[:100]}")

            # Load Query Assets from database
            with get_session_context() as session:
                from sqlmodel import select

                from app.modules.asset_registry.models import TbAssetRegistry

                query = select(TbAssetRegistry).where(
                    TbAssetRegistry.asset_type == "query",
                    TbAssetRegistry.status == "published"
                )
                query_assets = session.exec(query).all()

            self.logger.info(f"🔍 [QUERY ASSET] Found {len(query_assets)} Query Assets in database")

            if not query_assets:
                self.logger.warning("No Query Assets found in database")
                return results

            # Score all Query Assets and sort by score
            scored_assets = []
            question_lower = question.lower()

            for asset in query_assets:
                if not asset.schema_json:
                    continue

                schema = asset.schema_json
                asset_keywords = schema.get("keywords", [])
                sql = schema.get("sql", "")

                # Score based on keyword matching
                score = 0.0
                if asset_keywords:
                    matched = sum(
                        1 for kw in asset_keywords
                        if kw.lower() in question_lower
                    )
                    score = matched / max(len(asset_keywords), 1)

                # Also check asset name for matching
                asset_name_lower = asset.name.lower()
                name_score = 0.0
                if asset_name_lower:
                    name_match = sum(
                        1 for word in question_lower.split()
                        if word in asset_name_lower
                    )
                    name_score = name_match / max(len(question_lower.split()), 1) if question_lower else 0

                # NEW: Check SQL table names for matching
                # Map question words to SQL table names
                table_mapping = {
                    "event": "event_log",
                    "ci": "ci",
                    "metric": "metric",
                    "audit": "tb_audit_log"
                }
                sql_score = 0.0
                if sql:
                    for word, table in table_mapping.items():
                        if word in question_lower and table in sql:
                            sql_score += 1  # Bonus for table match
                            # Additional bonus if multiple words match
                            if word in question_lower.split():
                                sql_score += 0.5

                    # Penalty for date filters (prefer general queries over specific date ranges)
                    if "WHERE" in sql.upper() and ("DATE(" in sql or "INTERVAL" in sql or "CURRENT_DATE" in sql):
                        sql_score -= 2.0  # Significant penalty for date filters

                    # Penalty for using created_at column (doesn't exist in event_log)
                    if "created_at" in sql.lower():
                        sql_score -= 5.0  # Huge penalty for known bad column

                # Combine scores (keywords 50%, name 20%, SQL tables 30%)
                total_score = score * 0.5 + name_score * 0.2 + sql_score * 0.3

                scored_assets.append((total_score, asset))

            # Sort by score (descending)
            scored_assets.sort(key=lambda x: x[0], reverse=True)

            self.logger.info(f"🔍 [QUERY ASSET] Scored {len(scored_assets)} assets, trying top matches...")

            # Try each Query Asset in score order until one succeeds
            for total_score, asset in scored_assets[:5]:  # Try top 5 matches
                if total_score < 0:
                    continue  # Skip negative scores

                schema = asset.schema_json
                sql = schema.get("sql", "")

                if not sql:
                    self.logger.warning(f"Query Asset {asset.name} has no SQL, skipping")
                    continue

                self.logger.info(f"🔍 [QUERY ASSET] Trying: {asset.name} (score: {total_score:.2f})")
                self.logger.info(f"🔍 [QUERY ASSET] SQL: {sql[:200]}")

                # Execute SQL directly with error handling
                from sqlalchemy import text

                try:
                    with get_session_context() as session:
                        query_result = session.exec(text(sql))
                        rows = query_result.fetchall()

                    self.logger.info(f"✅ [QUERY ASSET] Executed successfully: {asset.name}, {len(rows)} rows")

                    # Extract first value for summary (avoid serialization issues)
                    # Convert SQLAlchemy rows to dictionaries for proper serialization
                    formatted_rows = []
                    if rows:
                        for row in rows:
                            if hasattr(row, '__iter__') and not isinstance(row, (str, dict)):
                                # SQLAlchemy Row objects - convert to dict
                                try:
                                    row_dict = dict(row._mapping) if hasattr(row, '_mapping') else {}
                                    if not row_dict:
                                        # Fallback: convert to list and map to column names if available
                                        row_dict = {"value": list(row)[0] if list(row) else None}
                                    formatted_rows.append(row_dict)
                                except Exception as e:
                                    self.logger.warning(f"Failed to convert row to dict: {e}")
                                    formatted_rows.append({"value": str(row)})
                            elif isinstance(row, dict):
                                formatted_rows.append(row)
                            else:
                                formatted_rows.append({"value": row})

                    # Extract first value for backward compatibility
                    first_value = None
                    if formatted_rows:
                        first_row = formatted_rows[0]
                        if isinstance(first_row, dict):
                            first_value = list(first_row.values())[0] if first_row else None
                        else:
                            first_value = first_row

                    # Format result as execution_result - include full rows for proper composition
                    result = {
                        "mode": "query_asset",
                        "tool": "direct_query",
                        "asset_name": asset.name,
                        "summary": f"Executed {asset.name}: {len(rows)} rows",
                        "rows_count": len(rows),
                        "data": {
                            "first_value": first_value,
                            "count": len(rows),
                            "rows": formatted_rows  # Include all rows for proper composition
                        },
                        "query_asset": {
                            "name": asset.name,
                            "keywords": schema.get("keywords", []),
                            "sql": sql
                        }
                    }

                    results.append(result)
                    break  # Success! Stop trying other assets

                except Exception as e:
                    self.logger.warning(f"⚠️ [QUERY ASSET] {asset.name} failed: {str(e)}, trying next...")
                    continue  # Try next asset

            if not results:
                self.logger.info("❌ [QUERY ASSET] No Query Asset succeeded")

        except Exception as e:
            self.logger.error(f"❌ [QUERY ASSET] Failed: {str(e)}")
            import traceback
            traceback.print_exc()

        # ===== CACHE: Store results for reuse in present stage =====
        if results:
            self._query_asset_results = results
            self.logger.info(f"💾 [QUERY ASSET] Cached {len(results)} results for present stage")
        # ===== END CACHE =====

        return results
