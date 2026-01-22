"""
StageExecutor for OPS Orchestration.

This module provides the StageExecutor class that executes individual stages
in the orchestration pipeline (route_plan, validate, execute, compose, present).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.db import get_session_context
from core.logging import get_logger

from app.modules.asset_registry.crud import get_asset
from app.modules.ops.schemas import (
    ExecutionContext,
    StageDiagnostics,
    StageInput,
    StageOutput,
)
from app.modules.ops.services.ci.tools.base import ToolContext
from app.modules.ops.services.ci.tools.executor import ToolExecutor

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

    def __init__(self, context: ExecutionContext, tool_executor: Optional[ToolExecutor] = None):
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
            self.logger.info(f"Using override asset: {override_key} -> {overridden_asset_id}")
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

        self.logger.info("stage_executor.start", extra={
            "stage": stage_name,
            "trace_id": stage_input.trace_id or "unknown",
            "test_mode": self.context.test_mode,
            "asset_overrides": len(self.context.asset_overrides)
        })

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
                duration_ms=duration_ms
            )

            self.logger.info("stage_executor.completed", extra={
                "stage": stage_name,
                "duration_ms": duration_ms,
                "has_references": len(stage_output.references) > 0
            })

            # Record stage output
            self.stage_outputs.append(stage_output)

            return stage_output

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.error("stage_executor.error", extra={
                "stage": stage_name,
                "error": str(e),
                "duration_ms": duration_ms
            })

            return StageOutput(
                stage=stage_name,
                result={"error": str(e)},
                diagnostics=StageDiagnostics(
                    status="error",
                    errors=[str(e)]
                ),
                references=[],
                duration_ms=duration_ms
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
            "asset_overrides_applied": self.context.asset_overrides if self.context.test_mode else {}
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
                        "overridden": asset_type in self.context.asset_overrides
                    }
                except Exception as e:
                    validation_errors.append(f"Failed to load {asset_type}:{asset_version}: {str(e)}")
                    asset_validations[asset_type] = {
                    "status": "invalid",
                    "error": str(e),
                    "overridden": asset_type in self.context.asset_overrides
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
            "plan_output": plan_output
        }

    async def _execute_execute(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the execute stage."""
        plan_output = stage_input.params.get("plan_output")
        applied_assets = stage_input.applied_assets

        # Apply asset overrides if in test mode
        if self.context.test_mode:
            for asset_type, default_asset in applied_assets.items():
                key_part = default_asset.split(":")[0]
                overridden_asset = self._resolve_asset(asset_type, key_part)
                applied_assets[asset_type] = overridden_asset

        # Tool execution context
        tool_context = ToolContext(
            trace_id=self.context.trace_id,
            applied_assets=applied_assets,
            params=stage_input.params,
            asset_overrides=self.context.asset_overrides if self.context.test_mode else {}
        )

        results = []
        references = []

        if plan_output.kind == "plan" and plan_output.plan:
            plan = plan_output.plan

            # Execute primary query
            if plan.primary and plan.primary.keywords:
                try:
                    primary_result = await self.tool_executor.execute_tool(
                        tool_type="ci_lookup",
                        params={
                            "keywords": plan.primary.keywords,
                            "filters": plan.primary.filters,
                            "limit": plan.primary.limit,
                            "mode": "primary"
                        },
                        context=tool_context
                    )
                    results.append(primary_result)
                    references.extend(primary_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute primary query: {str(e)}")

            # Execute secondary query
            if plan.secondary and plan.secondary.keywords:
                try:
                    secondary_result = await self.tool_executor.execute_tool(
                        tool_type="ci_lookup",
                        params={
                            "keywords": plan.secondary.keywords,
                            "filters": plan.secondary.filters,
                            "limit": plan.secondary.limit,
                            "mode": "secondary"
                        },
                        context=tool_context
                    )
                    results.append(secondary_result)
                    references.extend(secondary_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute secondary query: {str(e)}")

            # Execute aggregate query
            if plan.aggregate and plan.aggregate.group_by:
                try:
                    aggregate_result = await self.tool_executor.execute_tool(
                        tool_type="ci_aggregate",
                        params={
                            "group_by": plan.aggregate.group_by,
                            "metrics": plan.aggregate.metrics,
                            "filters": plan.aggregate.filters,
                            "top_n": plan.aggregate.top_n
                        },
                        context=tool_context
                    )
                    results.append(aggregate_result)
                    references.extend(aggregate_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute aggregate query: {str(e)}")

            # Execute graph query
            if plan.graph and (plan.graph.depth > 0 or plan.graph.view):
                try:
                    graph_result = await self.tool_executor.execute_tool(
                        tool_type="ci_graph",
                        params={
                            "depth": plan.graph.depth,
                            "view": plan.graph.view,
                            "limits": plan.graph.limits.dict() if plan.graph.limits else None,
                            "user_requested_depth": plan.graph.user_requested_depth
                        },
                        context=tool_context
                    )
                    results.append(graph_result)
                    references.extend(graph_result.get("references", []))
                except Exception as e:
                    self.logger.error(f"Failed to execute graph query: {str(e)}")

        return {
            "execution_results": results,
            "references": references,
            "plan_output": plan_output,
            "executed_at": time.time()
        }

    async def _execute_compose(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the compose stage."""
        stage_output = stage_input.prev_output
        if not stage_output:
            raise ValueError("Previous stage output is required for compose stage")

        execution_results = stage_output.get("execution_results", [])
        plan_output = stage_output.get("plan_output")

        # Compose results based on plan intent
        composed_result = {
            "composed": True,
            "results_count": len(execution_results),
            "results_summary": []
        }

        # Extract main results based on intent
        if plan_output and plan_output.plan:
            intent = plan_output.plan.intent

            if intent == "LOOKUP":
                # For lookup, focus on primary results
                primary_results = [r for r in execution_results if r.get("mode") == "primary"]
                if primary_results:
                    composed_result["primary_result"] = primary_results[0]
                    composed_result["results_summary"] = self._summarize_lookup_results(primary_results)

            elif intent == "AGGREGATE":
                # For aggregate, focus on aggregate results
                aggregate_results = [r for r in execution_results if r.get("mode") == "aggregate"]
                if aggregate_results:
                    composed_result["aggregate_result"] = aggregate_results[0]
                    composed_result["results_summary"] = self._summarize_aggregate_results(aggregate_results)

            elif intent == "PATH":
                # For path, include both primary and path results
                path_results = [r for r in execution_results if r.get("mode") == "path"]
                composed_result["path_results"] = path_results
                composed_result["results_summary"] = self._summarize_path_results(path_results)

        # Merge all references
        all_references = []
        for result in execution_results:
            all_references.extend(result.get("references", []))
        composed_result["references"] = all_references

        return composed_result

    async def _execute_present(self, stage_input: StageInput) -> Dict[str, Any]:
        """Execute the present stage."""
        stage_output = stage_input.prev_output
        if not stage_output:
            raise ValueError("Previous stage output is required for present stage")

        plan_output = stage_output.get("plan_output")
        composed_result = stage_output.get("composed_result", stage_output)

        # Prepare presentation blocks based on plan
        blocks = []

        if plan_output.kind == "direct" and plan_output.direct_answer:
            # Direct answer - simple text block
            blocks.append({
                "type": "text",
                "content": plan_output.direct_answer.answer,
                "metadata": {
                    "confidence": plan_output.direct_answer.confidence,
                    "reasoning": plan_output.direct_answer.reasoning
                }
            })

        elif plan_output.kind == "plan" and plan_output.plan:
            # Plan execution - compose blocks based on intent
            intent = plan_output.plan.intent

            if intent == "LOOKUP":
                # Create table block for lookup results
                if "primary_result" in composed_result:
                    blocks.append(self._create_table_block(composed_result["primary_result"]))

            elif intent == "AGGREGATE":
                # Create chart and table blocks for aggregate results
                if "aggregate_result" in composed_result:
                    blocks.append(self._create_chart_block(composed_result["aggregate_result"]))
                    blocks.append(self._create_table_block(composed_result["aggregate_result"]))

            elif intent == "PATH":
                # Create network and table blocks for path results
                if "path_results" in composed_result:
                    blocks.append(self._create_network_block(composed_result["path_results"]))
                    blocks.append(self._create_table_block(composed_result["path_results"]))

        result = {
            "blocks": blocks,
            "references": composed_result.get("references", []),
            "summary": self._generate_summary(composed_result),
            "presented_at": time.time()
        }

        # Add baseline comparison information if in test mode
        if self.context.test_mode and self.context.baseline_trace_id:
            result["baseline_trace_id"] = self.context.baseline_trace_id
            result["baseline_comparison_available"] = True

        return result

    def _build_diagnostics(self, result: Dict[str, Any], stage_name: str) -> StageDiagnostics:
        """Build diagnostics information for the stage."""
        diagnostics = StageDiagnostics(
            status="ok",
            warnings=[],
            errors=[],
            empty_flags={},
            counts={}
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
                "rows": result.get("rows", [])
            },
            "metadata": {
                "count": len(result.get("rows", []))
            }
        }

    def _create_chart_block(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chart block from aggregate result."""
        return {
            "type": "chart",
            "content": {
                "chart_type": "bar",
                "data": result.get("data", {}),
                "title": result.get("title", "Aggregate Results")
            },
            "metadata": {}
        }

    def _create_network_block(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a network block from path result."""
        return {
            "type": "network",
            "content": {
                "nodes": result.get("nodes", []),
                "edges": result.get("edges", []),
                "layout": "force"
            },
            "metadata": {
                "node_count": len(result.get("nodes", [])),
                "edge_count": len(result.get("edges", []))
            }
        }