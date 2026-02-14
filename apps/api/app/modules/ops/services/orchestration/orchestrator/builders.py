"""Block builders for OPS orchestration.

This module contains consolidated block building logic extracted from runner.py:
- BlockBuilder: Metric, history, CEP, and graph blocks
- Deduplication: Consolidated 6 duplicate methods from runner.py
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from core.logging import get_logger
from app.modules.ops.schemas import StageDiagnostics
from app.modules.ops.services.orchestration.blocks import (
    Block,
    chart_block,
    table_block,
    text_block,
)
from app.modules.ops.services.orchestration.planner.plan_schema import (
    MetricSpec,
    View,
)
from app.modules.ops.services.orchestration.actions import NextAction


class BlockBuilder:
    """Consolidated block building for metrics, history, CEP, and graphs."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    # ===== METRIC BLOCKS =====

    def metric_blocks(
        self, detail: Dict[str, Any], graph_payload: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """Build metric blocks (wrapper)."""
        return asyncio.run(self.metric_blocks_async(detail, graph_payload))

    async def metric_blocks_async(
        self, detail: Dict[str, Any], graph_payload: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """Build metric blocks asynchronously.

        Handles both single CI and graph scope metrics via Tool Assets.
        Consolidated from duplicate methods at runner.py:3574 and 4296.
        """
        metric_spec = self.runner.plan.metric
        if not metric_spec:
            return []

        metric_trace = self.runner.plan_trace.setdefault("metric", {})
        metric_trace["requested"] = metric_spec.dict()

        # Handle graph scope metrics
        if metric_spec.scope == "graph":
            return await self.graph_metric_blocks_async(
                detail, metric_spec, metric_trace, graph_payload=graph_payload
            )

        # Use Tool Assets for single CI metrics
        try:
            metric_params = {
                "tenant_id": self.runner.tenant_id,
                "ci_code": detail.get("ci_code", ""),
                "ci_id": detail.get("ci_id", ""),
                "metric_name": metric_spec.metric_name,
                "time_range": metric_spec.time_range or "last_24h",
                "agg": metric_spec.agg or "AVG",
            }

            result = await self.runner._execute_tool_asset_async(
                "metric_query", metric_params
            )

            if not result.get("success"):
                error_msg = result.get("error", "Failed to retrieve metric data")
                metric_trace.update({"status": "error", "error": error_msg})
                self.runner._log_metric_blocks_return([text_block(error_msg)])
                return [text_block(error_msg, title="Metric query")]

            data = result.get("data", {})
            metric_trace.update(
                {"status": "success", "data_rows": len(data.get("rows", []))}
            )

            # Build blocks from metric data
            blocks = self.runner._build_metric_blocks_from_data(
                data, metric_spec.metric_name, detail
            )

            # Add next actions
            self.runner.next_actions.extend(
                self.metric_next_actions(metric_spec.time_range or "last_24h")
            )

            self.runner._log_metric_blocks_return(blocks)
            return blocks

        except Exception as exc:
            self.logger.error(
                "metric_blocks_async failed",
                extra={"error": str(exc), "metric": metric_spec.metric_name},
            )
            metric_trace.update({"status": "error", "error": str(exc)})
            return [text_block(f"Metric error: {str(exc)}", title="Metric")]

    async def graph_metric_blocks_async(
        self,
        detail: Dict[str, Any],
        metric_spec: MetricSpec,
        metric_trace: Dict[str, Any],
        graph_payload: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Build metric blocks for graph scope.

        Consolidated from duplicate methods at runner.py:3701 and 4354.
        """
        graph_view = self.runner.plan.graph.view or (
            self.runner.plan.view or View.DEPENDENCY
        )
        graph_depth = self.runner.plan.graph.depth
        graph_limits = self.runner.plan.graph.limits.dict()

        if not graph_payload:
            graph_payload = await self.runner._graph_expand_async(
                detail["ci_id"], graph_view.value, graph_depth, graph_limits
            )

        node_ids = graph_payload.get("ids") or [detail["ci_id"]]

        try:
            aggregate = await self.runner._metric_aggregate_async(
                metric_spec.metric_name,
                metric_spec.agg,
                metric_spec.time_range,
                ci_ids=node_ids,
            )
        except Exception as exc:
            self.logger.error("graph_metric_blocks failed", extra={"error": str(exc)})
            metric_trace.update({"status": "error", "error": str(exc)})
            return [text_block(f"Graph metric error: {str(exc)}")]

        graph_meta = graph_payload.get("meta", {})
        graph_summary = graph_payload.get("summary", {})
        depth_applied = graph_meta.get("depth", graph_depth)
        truncated = graph_payload.get("truncated", False)

        metric_trace.update(
            {
                "status": "graph_aggregate",
                "requested": metric_spec.dict(),
                "scope": metric_spec.scope,
                "graph_expand": {
                    "view": graph_view.value,
                    "depth_requested": graph_depth,
                    "depth_applied": depth_applied,
                    "node_count": graph_summary.get("node_count"),
                    "edge_count": graph_summary.get("edge_count"),
                    "rel_types": graph_meta.get("rel_types"),
                    "truncated": truncated,
                },
                "result": aggregate,
            }
        )

        rows = [
            [
                "graph",
                graph_view.value,
                str(depth_applied),
                str(aggregate.get("ci_count_used")),
                aggregate["metric_name"],
                aggregate["agg"],
                aggregate["time_from"],
                aggregate["time_to"],
                (
                    str(aggregate["value"])
                    if aggregate["value"] is not None
                    else "<null>"
                ),
            ]
        ]

        self.runner.next_actions.extend(
            self.graph_metric_next_actions(
                graph_view.value,
                depth_applied,
                truncated,
                metric_spec,
            )
        )

        title = f"Graph metric ({metric_spec.metric_name})"
        return [
            table_block(
                [
                    "scope",
                    "view",
                    "depth",
                    "ci_count",
                    "metric_name",
                    "agg",
                    "time_from",
                    "time_to",
                    "value",
                ],
                rows,
                title=title,
            )
        ]

    # ===== HISTORY BLOCKS =====

    def history_blocks(
        self, detail: Dict[str, Any], graph_payload: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """Build history blocks (wrapper)."""
        return asyncio.run(self.history_blocks_async(detail, graph_payload))

    async def history_blocks_async(
        self, detail: Dict[str, Any], graph_payload: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """Build history blocks asynchronously.

        Consolidated from duplicate methods at runner.py:3979 and 4637.
        """
        history_spec = self.runner.plan.history
        if not history_spec or not history_spec.enabled:
            return []

        history_trace = self.runner.plan_trace.setdefault("history", {})
        history_trace["requested"] = history_spec.dict()

        if history_spec.scope == "graph":
            return await self.graph_history_blocks_async(
                detail, history_spec, history_trace, graph_payload=graph_payload
            )

        return await self.ci_history_blocks_async(
            detail, history_spec, history_trace
        )

    async def ci_history_blocks_async(
        self,
        detail: Dict[str, Any],
        history_spec: Any,
        history_trace: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build CI history blocks."""
        try:
            result = await self.runner._history_recent_async(
                history_spec,
                {"ci_id": detail["ci_id"], "ci_code": detail.get("ci_code")},
            )
        except Exception as exc:
            self.logger.error(
                "ci_history_blocks failed", extra={"error": str(exc)}
            )
            return [text_block(f"History error: {str(exc)}", title="History")]

        if not result.get("available"):
            history_trace["available"] = False
            warnings = result.get("warnings", [])
            if warnings:
                history_trace.setdefault("warnings", []).extend(warnings)
            message = (
                f"event_log unavailable: {'; '.join(warnings)}"
                if warnings
                else "event_log unavailable"
            )
            return [text_block(message, title="History")]

        history_trace["available"] = True
        history_meta = result.get("meta", {})
        history_trace["meta"] = history_meta
        history_trace["rows"] = len(result.get("rows", []))

        self.runner.history_context = {
            "time_range": history_spec.time_range,
            "source": history_spec.source,
            "rows": len(result.get("rows", [])),
            "recent": self.runner._format_history_recent(result.get("rows", [])),
        }

        self.runner.next_actions.extend(
            self.history_time_actions(history_spec.time_range)
        )

        title = f"Recent events ({history_spec.time_range})"
        return [table_block(result["columns"], result["rows"], title=title)]

    async def graph_history_blocks_async(
        self,
        detail: Dict[str, Any],
        history_spec: Any,
        history_trace: Dict[str, Any],
        graph_payload: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Build graph history blocks.

        Consolidated from duplicate methods at runner.py:4043 and elsewhere.
        """
        graph_view = self.runner.plan.graph.view or (
            self.runner.plan.view or View.DEPENDENCY
        )
        graph_depth = self.runner.plan.graph.depth
        graph_limits = self.runner.plan.graph.limits.dict()

        if not graph_payload:
            graph_payload = await self.runner._graph_expand_async(
                detail["ci_id"], graph_view.value, graph_depth, graph_limits
            )

        node_ids = graph_payload.get("ids") or [detail["ci_id"]]

        try:
            result = await self.runner._history_recent_async(
                history_spec,
                {"ci_id": detail["ci_id"], "ci_code": detail.get("ci_code")},
                ci_ids=node_ids,
            )
        except Exception as exc:
            self.logger.error(
                "graph_history_blocks failed", extra={"error": str(exc)}
            )
            return [text_block(f"History error: {str(exc)}", title="History")]

        if not result.get("available"):
            history_trace["available"] = False
            warnings = result.get("warnings", [])
            if warnings:
                history_trace.setdefault("warnings", []).extend(warnings)
            message = (
                f"event_log unavailable: {'; '.join(warnings)}"
                if warnings
                else "event_log unavailable"
            )
            return [text_block(message, title="History")]

        history_trace["available"] = True
        history_trace["scope"] = "graph"
        history_meta = result.get("meta", {})
        depth_applied = graph_payload.get("meta", {}).get("depth", graph_depth)
        truncated = graph_payload.get("truncated", False)

        history_trace["meta"] = history_meta
        history_trace["graph"] = {
            "view": graph_view.value,
            "depth_requested": graph_depth,
            "depth_applied": depth_applied,
            "truncated": truncated,
            "node_count": graph_payload.get("summary", {}).get("node_count"),
            "edge_count": graph_payload.get("summary", {}).get("edge_count"),
        }
        history_trace["rows"] = len(result.get("rows", []))

        ci_count_used = history_meta.get("ci_count_used")
        history_trace["ci_ids_used"] = ci_count_used
        history_trace["ci_ids_truncated"] = history_meta.get("ci_ids_truncated")

        self.runner.next_actions.extend(
            self.graph_history_next_actions(
                history_spec,
                graph_view.value,
                depth_applied,
                truncated,
            )
        )

        title = f"Recent events (graph scope, {graph_view.value}, depth={depth_applied}, {history_spec.time_range})"

        self.runner.history_context = {
            "time_range": history_spec.time_range,
            "source": self.runner._history_context_source(history_spec),
            "rows": len(result.get("rows", [])),
            "recent": self.runner._format_history_recent(result.get("rows", [])),
        }

        return [table_block(result["columns"], result["rows"], title=title)]

    # ===== CEP BLOCKS =====

    def cep_blocks(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build CEP blocks (wrapper)."""
        return asyncio.run(self.cep_blocks_async(detail))

    async def cep_blocks_async(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build CEP simulation blocks.

        Consolidated from duplicate methods at runner.py:4122 and 4763.
        """
        cep_spec = self.runner.plan.cep
        if not cep_spec or cep_spec.mode != "simulate":
            return []

        cep_trace = self.runner.plan_trace.setdefault("cep", {})
        cep_trace["requested"] = cep_spec.dict()

        if not cep_spec.rule_id:
            cep_trace["error"] = "rule_id missing"
            return [
                text_block(
                    "CEP simulate requires a rule ID to be included in the question (e.g. rule <uuid>).",
                    title="CEP simulate",
                )
            ]

        ci_context = {
            "ci_id": detail.get("ci_id"),
            "ci_code": detail.get("ci_code"),
            "tags": detail.get("tags") or {},
            "attributes": detail.get("attributes") or {},
        }

        metric_ctx = self.runner.metric_context
        history_ctx = self.runner.history_context

        try:
            result = await self.runner._cep_simulate_async(
                cep_spec.rule_id, ci_context, metric_ctx, history_ctx
            )
        except Exception as exc:
            self.logger.error("cep_blocks failed", extra={"error": str(exc)})
            cep_trace["error"] = str(exc)
            return [text_block(f"CEP simulate error: {str(exc)}", title="CEP")]

        cep_trace["result"] = result

        payload_meta = result.get("test_payload_meta") or {}
        cep_trace["test_payload_built"] = payload_meta.get("built", False)
        cep_trace["test_payload_size_bytes"] = payload_meta.get("size_bytes")
        cep_trace["test_payload_sources"] = payload_meta.get("sources")
        cep_trace["payload_truncated"] = payload_meta.get("truncated")

        if payload_meta.get("built"):
            cep_trace["test_payload"] = result.get("test_payload")

        evidence_meta = result.get("evidence_meta") or {}
        cep_trace["params_masked"] = evidence_meta.get("params_masked")
        cep_trace["extracted_value_truncated"] = evidence_meta.get(
            "extracted_value_truncated"
        )

        runtime_params_meta = evidence_meta.get("runtime_params_meta")
        cep_trace["runtime_params_meta"] = runtime_params_meta
        cep_trace["runtime_params_keys"] = evidence_meta.get("runtime_params_keys")
        cep_trace["runtime_params_policy_source"] = evidence_meta.get(
            "runtime_params_policy_source"
        )
        cep_trace["test_payload_sections"] = evidence_meta.get(
            "test_payload_sections"
        )
        cep_trace["test_payload_metric_keys_present"] = evidence_meta.get(
            "test_payload_metric_keys_present"
        )
        cep_trace["test_payload_history_keys_present"] = evidence_meta.get(
            "test_payload_history_keys_present"
        )
        cep_trace["exec_log_id"] = result.get("exec_log_id")
        cep_trace["simulation_id"] = result.get("simulation_id")

        if not result.get("success"):
            cep_trace["error"] = result.get("error")
            message = result.get("error") or "Unknown CEP simulate failure"
            return [text_block(f"CEP simulate failed: {message}", title="CEP")]

        simulation = result.get("simulation") or {}
        cep_trace["simulation"] = simulation

        summary_text = f"Condition evaluated: {simulation.get('condition_evaluated')} · triggered: {simulation.get('triggered')}"
        cep_trace["summary"] = summary_text

        rows = [
            [
                simulation.get("rule_id"),
                str(simulation.get("condition_evaluated")),
                str(simulation.get("triggered")),
                str(simulation.get("operator") or "-"),
                str(simulation.get("threshold") or "-"),
                str(simulation.get("extracted_value") or "-"),
                result.get("exec_log_id") or result.get("simulation_id") or "",
            ]
        ]

        evidence = result.get("evidence") or {}
        cep_evidence = result.get("evidence") or {}
        cep_trace["evidence"] = cep_evidence

        params_keys = evidence_meta.get("runtime_params_keys") or []
        params_display = ", ".join(params_keys)
        if len(params_display) > 200:
            params_display = params_display[:200] + "..."

        self.runner.next_actions.append(
            {
                "type": "open_event_browser",
                "label": "Event Browser로 보기",
                "payload": {
                    "exec_log_id": result.get("exec_log_id"),
                    "simulation_id": result.get("simulation_id"),
                    "tenant_id": self.runner.tenant_id,
                },
            }
        )

        return [
            text_block(summary_text, title="CEP simulate"),
            table_block(
                [
                    "rule_id",
                    "condition_evaluated",
                    "triggered",
                    "operator",
                    "threshold",
                    "extracted_value",
                    "exec_log_id",
                ],
                rows,
                title="CEP simulate results",
            ),
            table_block(
                [
                    "section",
                    "status",
                    "duration_ms",
                    "message",
                ],
                evidence.get("rows", []),
                title="CEP simulate evidence",
            ),
        ]

    # ===== NEXT ACTIONS =====

    def metric_next_actions(self, current_range: str) -> List[NextAction]:
        """Generate next actions for metric queries."""
        actions: List[NextAction] = []
        ranges = [
            ("last_1h", "최근 1시간"),
            ("last_24h", "최근 24시간"),
            ("last_7d", "최근 7일"),
        ]
        for key, label in ranges:
            if key == current_range:
                continue
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{label}",
                    "payload": {"patch": {"metric": {"time_range": key}}},
                }
            )
        return actions

    def graph_metric_next_actions(
        self, graph_view: str, depth: int, truncated: bool, metric_spec: MetricSpec
    ) -> List[NextAction]:
        """Generate next actions for graph metrics."""
        actions: List[NextAction] = []
        ranges = [
            ("last_1h", "최근 1시간"),
            ("last_24h", "최근 24시간"),
            ("last_7d", "최근 7일"),
        ]
        for key, label in ranges:
            if key == metric_spec.time_range:
                continue
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{label}",
                    "payload": {"patch": {"metric": {"time_range": key}}},
                }
            )
        for agg in ("count", "max", "min", "avg"):
            if agg != metric_spec.agg:
                actions.append(
                    {
                        "type": "rerun",
                        "label": f"집계: {agg}",
                        "payload": {"patch": {"metric": {"agg": agg}}},
                    }
                )
        if truncated:
            actions.append(
                {
                    "type": "rerun",
                    "label": "depth +1",
                    "payload": {"patch": {"graph": {"depth": depth + 1}}},
                }
            )
        for target_view in ["DEPENDENCY", "NEIGHBORS", "IMPACT"]:
            if target_view != graph_view:
                actions.append(
                    {
                        "type": "rerun",
                        "label": f"View {target_view}로 보기",
                        "payload": {
                            "patch": {
                                "view": target_view,
                                "graph": {"view": target_view},
                            }
                        },
                    }
                )
        return actions

    def history_time_actions(self, current_range: str) -> List[NextAction]:
        """Generate next actions for history time ranges."""
        actions: List[NextAction] = []
        ranges = [
            ("last_24h", "최근 24시간"),
            ("last_7d", "최근 7일"),
            ("last_30d", "최근 30일"),
        ]
        for key, label in ranges:
            if key == current_range:
                continue
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{label}",
                    "payload": {"patch": {"history": {"time_range": key}}},
                }
            )
        return actions

    def graph_history_next_actions(
        self, history_spec: Any, graph_view: str, depth: int, truncated: bool
    ) -> List[NextAction]:
        """Generate next actions for graph history."""
        actions: List[NextAction] = []
        ranges = [
            ("last_24h", "최근 24시간"),
            ("last_7d", "최근 7일"),
            ("last_30d", "최근 30일"),
        ]
        for key, label in ranges:
            if key == history_spec.time_range:
                continue
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{label}",
                    "payload": {"patch": {"history": {"time_range": key}}},
                }
            )
        if truncated:
            actions.append(
                {
                    "type": "rerun",
                    "label": "depth +1",
                    "payload": {
                        "patch": {"graph": {"depth": depth + 1, "view": graph_view}}
                    },
                }
            )
        for target_view in ["DEPENDENCY", "NEIGHBORS", "IMPACT"]:
            if target_view != graph_view:
                actions.append(
                    {
                        "type": "rerun",
                        "label": f"View {target_view}로 보기",
                        "payload": {
                            "patch": {
                                "view": target_view,
                                "graph": {"view": target_view},
                            }
                        },
                    }
                )
        return actions
