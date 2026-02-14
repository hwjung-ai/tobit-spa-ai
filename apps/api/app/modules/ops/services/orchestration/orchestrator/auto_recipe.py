"""Auto Recipe Engine for AUTO mode orchestration.

This module contains the AutoRecipeEngine class with graph, path, metric, history,
and insights generation for comprehensive CI analysis.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

from app.modules.ops.services.orchestration import policy, response_builder
from app.modules.ops.services.orchestration.actions import NextAction, RerunPayload
from app.modules.ops.services.orchestration.blocks import (
    Block,
    number_block,
    table_block,
    text_block,
)
from app.modules.ops.services.orchestration.planner.plan_schema import (
    AutoSpec,
    View,
)
from core.logging import get_logger

# Auto recipe constants
AUTO_METRIC_PREFERENCES = [
    ("cpu_usage", "max"),
    ("latency", "max"),
    ("error", "count"),
]

AUTO_VIEW_DEFAULT_DEPTHS = {
    View.COMPOSITION: 2,
    View.DEPENDENCY: 2,
    View.IMPACT: 2,
    View.NEIGHBORS: 2,
}

logger = get_logger(__name__)


class AutoRecipeEngine:
    """Engine for AUTO mode recipe generation.

    Handles graph expansion, path finding, metric aggregation, history retrieval,
    and comprehensive insights generation for AUTO mode execution.
    """

    def __init__(self, runner):
        """Initialize AutoRecipeEngine with runner instance."""
        self.runner = runner

    def _run_auto_recipe(self) -> Tuple[List[Block], str, Dict[str, Any]]:
        """Sync wrapper for async auto recipe execution."""
        return asyncio.run(self._run_auto_recipe_async())

    async def _run_auto_recipe_async(self) -> Tuple[List[Block], str, Dict[str, Any]]:
        """Execute full AUTO recipe with all graph, metric, history blocks.

        Returns:
            Tuple of (blocks, answer, auto_trace)
        """
        (
            detail,
            fallback_blocks,
            fallback_message,
        ) = await self.runner._resolve_ci_detail_async()
        auto_spec = self.runner.plan.auto

        # 깊이 관련 정책 결정 명시 (AUTO mode에서도 세 가지 값 분리 기록)
        user_requested_depth = (
            self.runner.plan.graph.user_requested_depth if self.runner.plan.graph else None
        )
        if user_requested_depth is not None:
            policy_decisions = self.runner.plan_trace.setdefault("policy_decisions", {})
            policy_decisions["user_requested_depth"] = user_requested_depth

        auto_trace: Dict[str, Any] = {
            "auto_recipe_applied": True,
            "views": [],
            "metrics": {},
            "history": {},
            "graph_scope": {},
            "path": {},
            "cep": {},
        }
        if not detail:
            auto_trace["status"] = "ci_unresolved"
            return (
                fallback_blocks or [],
                fallback_message or "AUTO recipe could not resolve CI",
                auto_trace,
            )
        (
            graph_blocks,
            graph_payloads,
            view_entries,
        ) = await self._auto_graph_blocks_async(detail, auto_spec)
        path_blocks, path_trace = await self._auto_path_blocks_async(detail, auto_spec)
        view_entries_with_path = list(view_entries)
        if path_trace:
            view_entries_with_path.append(
                {
                    "view": View.PATH.value,
                    "status": path_trace.get("status"),
                    "source": path_trace.get("source"),
                    "target": path_trace.get("target"),
                    "hop_count": path_trace.get("hop_count"),
                }
            )
        auto_trace["views"] = view_entries_with_path
        auto_trace["path"].update(path_trace or {"status": "skipped"})
        metrics_blocks, metric_trace = await self._run_auto_metrics_async(
            detail, auto_spec
        )
        auto_trace["metrics"] = metric_trace
        history_blocks, history_trace = await self._run_auto_history_async(
            detail, auto_spec
        )
        auto_trace["history"] = history_trace
        (
            graph_scope_blocks,
            graph_scope_trace,
        ) = await self._auto_graph_scope_sections_async(
            detail, auto_spec, graph_payloads
        )
        auto_trace["graph_scope"] = graph_scope_trace
        cep_blocks = await self.runner._cep_blocks_async(detail)
        cep_status = (
            "simulated" if self.runner.plan.cep and self.runner.plan.cep.rule_id else "skipped"
        )
        auto_trace["cep"] = {
            "status": cep_status,
            "rule_id": self.runner.plan.cep.rule_id if self.runner.plan.cep else None,
        }
        view_labels = (
            "+".join(
                entry.get("view", "")
                for entry in view_entries_with_path
                if entry.get("view")
            )
            or "NEIGHBORS"
        )
        metrics_label = metric_trace.get("status", "disabled")
        history_label = history_trace.get("status", "disabled")
        graph_scope_label = graph_scope_trace.get("label", "disabled")
        path_label = path_trace.get("status", "skipped") if path_trace else "skipped"
        summary_text = (
            f"AUTO 점검 결과: CI={detail.get('ci_code', 'N/A')}, views={view_labels}, path={path_label}, "
            f"scope={graph_scope_label}, metrics={metrics_label}, events={history_label}, cep={cep_status}"
        )
        insight_blocks = self._build_auto_insights(detail, auto_trace, summary_text)
        quality_blocks, quality_trace = self._build_auto_quality(auto_trace)
        auto_trace["quality"] = quality_trace
        answer = f"AUTO review for {detail['ci_code']}"
        blocks = [
            *insight_blocks,
            *quality_blocks,
            *response_builder.build_ci_detail_blocks(detail),
            *path_blocks,
            *graph_blocks,
            *graph_scope_blocks,
            *metrics_blocks,
            *history_blocks,
            *cep_blocks,
        ]
        recommended, reasons = self._recommend_auto_actions(auto_trace, detail)
        if recommended:
            self._insert_recommended_actions(recommended)
        if reasons:
            auto_trace.setdefault("recommendations", []).extend(reasons)
        return blocks, answer, auto_trace

    async def _auto_graph_blocks_async(
        self, detail: Dict[str, Any], auto_spec: AutoSpec
    ) -> Tuple[List[Block], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate graph blocks for all AUTO views."""
        views = [
            view for view in auto_spec.views if view not in {View.SUMMARY, View.PATH}
        ]
        if not views:
            views = [View.NEIGHBORS]
        graph_blocks: List[Block] = []
        graph_payloads: Dict[str, Dict[str, Any]] = {}
        entries: List[Dict[str, Any]] = []
        for view in views:
            depth = self._auto_depth_for_view(view, auto_spec)
            view_entry: Dict[str, Any] = {"view": view.value}
            try:
                payload = await self.runner._graph_expand_async(
                    detail["ci_id"],
                    view.value,
                    depth,
                    self.runner.plan.graph.limits.dict(),
                )
                graph_blocks.extend(response_builder.build_network_blocks(payload))
                truncated = payload.get("truncated", False)
                graph_payloads[view.value] = payload
                view_entry.update(
                    {
                        "status": "ok",
                        "depth": depth,
                        "node_count": len(payload.get("nodes", [])),
                        "edge_count": len(payload.get("edges", [])),
                        "truncated": truncated,
                    }
                )
                self.runner.next_actions.extend(
                    self.runner._graph_next_actions(
                        view.value,
                        payload.get("meta", {}).get("depth", depth),
                        truncated,
                    )
                )
            except Exception as exc:
                view_entry.update({"status": "fail", "error": str(exc)})
                graph_blocks.append(
                    text_block(
                        f"Graph {view.value} expansion failed: {exc}",
                        title=f"AUTO {view.value}",
                    )
                )
            entries.append(view_entry)
        return graph_blocks, graph_payloads, entries

    async def _auto_path_blocks_async(
        self, detail: Dict[str, Any], auto_spec: AutoSpec
    ) -> Tuple[List[Block], Dict[str, Any]]:
        """Generate AUTO path blocks if PATH view is requested."""
        if View.PATH not in auto_spec.views:
            return [], {"status": "skipped"}
        path_spec = auto_spec.path
        trace: Dict[str, Any] = {"requested": path_spec.dict(), "view": View.PATH.value}
        source_detail = detail
        if (
            path_spec.source_ci_code
            and path_spec.source_ci_code.lower() != detail["ci_code"].lower()
        ):
            resolved = await self.runner._ci_detail_by_code_async(path_spec.source_ci_code)
            if resolved:
                source_detail = resolved
            else:
                trace.setdefault("warnings", []).append(
                    f"Source CI '{path_spec.source_ci_code}' not found"
                )
        target_detail = None
        if path_spec.target_ci_code:
            target_detail = await self.runner._ci_detail_by_code_async(
                path_spec.target_ci_code
            )
            if not target_detail:
                trace["status"] = "target_not_found"
        if target_detail:
            hops = self._auto_path_hops(auto_spec)
            path_payload = await self.runner._graph_path_async(
                source_detail["ci_id"], target_detail["ci_id"], hops
            )
            if not path_payload.get("nodes"):
                message = f"No path found from {source_detail['ci_code']} to {target_detail['ci_code']}"
                trace.update(
                    {
                        "status": "no_path",
                        "source": source_detail["ci_code"],
                        "target": target_detail["ci_code"],
                    }
                )
                return [text_block(message, title="AUTO Path")], trace
            trace.update(
                {
                    "status": "ok",
                    "source": source_detail["ci_code"],
                    "target": target_detail["ci_code"],
                    "hop_count": path_payload.get("hop_count", 0),
                }
            )
            return response_builder.build_path_blocks(path_payload), trace
        candidates = await self._auto_path_candidates_async(detail)
        if not candidates:
            trace["status"] = "no_candidates"
            return [
                text_block("No path candidates available.", title="AUTO Path")
            ], trace
        trace.update(
            {
                "status": "awaiting_target",
                "candidates": [candidate.get("ci_code") for candidate in candidates],
            }
        )
        blocks: List[Block] = [
            text_block(
                "No target CI specified. Select one to complete the path.",
                title="AUTO Path",
            ),
            response_builder.build_candidate_table(candidates, role="target"),
        ]
        self.runner.next_actions.extend(self._path_target_next_actions(candidates))
        return blocks, trace

    def _auto_depth_for_view(self, view: View, auto_spec: AutoSpec) -> int:
        """Get clamped depth for view."""
        requested = auto_spec.depth_hint or AUTO_VIEW_DEFAULT_DEPTHS.get(view, 2)
        return policy.clamp_depth(view.value, requested)

    def _auto_path_hops(self, auto_spec: AutoSpec) -> int:
        """Get clamped hops count for path."""
        hint = auto_spec.depth_hint or self.runner.plan.graph.depth or 4
        return policy.clamp_depth("PATH", max(1, hint))

    async def _auto_path_candidates_async(
        self, detail: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate path target candidates from graph neighbors."""
        try:
            payload = await self.runner._graph_expand_async(
                detail["ci_id"],
                View.NEIGHBORS.value,
                1,
                {"max_nodes": 50, "max_edges": 100, "max_paths": 5},
            )
            nodes = payload.get("nodes", [])
        except Exception:
            nodes = []
        candidates: List[Dict[str, Any]] = []
        seen = set()
        for node in nodes:
            ci_id = node.get("id")
            ci_code = node.get("code")
            if not ci_id or ci_code == detail["ci_code"]:
                continue
            if ci_id in seen:
                continue
            seen.add(ci_id)
            candidates.append(
                {
                    "ci_id": ci_id,
                    "ci_code": ci_code,
                    "ci_name": node.get("ci_code"),
                    "ci_type": node.get("ci_type"),
                    "ci_subtype": node.get("ci_subtype"),
                    "ci_category": node.get("ci_category"),
                    "status": node.get("status", "N/A"),
                    "location": node.get("location", ""),
                    "owner": "",
                }
            )
        if len(candidates) < 5:
            search = await self.runner._ci_search_async(limit=5)
            for entry in search:
                if entry["ci_code"] == detail["ci_code"] or entry["ci_id"] in seen:
                    continue
                candidates.append(entry)
                seen.add(entry["ci_id"])
        return candidates[:5]

    def _path_target_next_actions(
        self, candidates: List[Dict[str, Any]]
    ) -> List[NextAction]:
        """Generate rerun actions for path target candidates."""
        actions: List[NextAction] = []
        for candidate in candidates:
            ci_code = candidate.get("ci_code")
            if not ci_code:
                continue
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{ci_code} 선택 (target)",
                    "payload": {
                        "patch": {"auto": {"path": {"target_ci_code": ci_code}}}
                    },
                }
            )
        return actions

    async def _run_auto_metrics_async(
        self, detail: Dict[str, Any], auto_spec: AutoSpec
    ) -> Tuple[List[Block], Dict[str, Any]]:
        """Generate AUTO metric blocks."""
        if not auto_spec.include_metric:
            return [], {"status": "disabled"}
        if self.runner.plan.metric:
            blocks = await self.runner._metric_blocks_async(detail)
            status = {
                "status": "spec",
                "metric": self.runner.plan.metric.metric_name,
                "mode": self.runner.plan.metric.mode,
            }
            highlights: List[Dict[str, Any]] = []
            if self.runner.metric_context and self.runner.metric_context.get("value") is not None:
                highlights.append(
                    {
                        "label": f"{self.runner.metric_context['metric_name']} {self.runner.metric_context['agg']} ({self.runner.metric_context['time_range']})",
                        "value": self.runner.metric_context["value"],
                    }
                )
            if highlights:
                status["highlights"] = highlights
            return blocks, status
        return await self._auto_metric_candidate_blocks_async(detail)

    async def _auto_metric_candidate_blocks_async(
        self, detail: Dict[str, Any]
    ) -> Tuple[List[Block], Dict[str, Any]]:
        """Generate candidate metric blocks for AUTO mode."""
        rows: List[List[str]] = []
        candidates: List[Dict[str, Any]] = []
        highlights: List[Dict[str, Any]] = []
        for metric_name, agg in AUTO_METRIC_PREFERENCES:
            entry: Dict[str, Any] = {"metric": metric_name}
            if not False:  # Treat as unavailable until Tool Assets are created
                entry["available"] = False
                candidates.append(entry)
                continue
            try:
                aggregate = await self.runner._metric_aggregate_async(
                    metric_name,
                    agg,
                    "last_24h",
                    ci_id=detail["ci_id"],
                )
                value = aggregate.get("value")
                rows.append(
                    [
                        aggregate["metric_name"],
                        aggregate["agg"],
                        str(value if value is not None else "<null>"),
                        aggregate["time_range"],
                    ]
                )
                candidates.append({"metric": metric_name, "status": "ok"})
                if value is not None and not self.runner.metric_context:
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        numeric = None
                    self.runner.metric_context = {
                        "metric_name": metric_name,
                        "time_range": "last_24h",
                        "agg": agg,
                        "value": numeric,
                    }
                if isinstance(value, (int, float)):
                    highlights.append(
                        {
                            "label": f"{metric_name} {agg} (last_24h)",
                            "value": value,
                        }
                    )
            except Exception as exc:
                candidates.append(
                    {"metric": metric_name, "status": "error", "error": str(exc)}
                )
        if rows:
            return (
                [
                    table_block(
                        ["metric_name", "agg", "value", "time_range"],
                        rows,
                        title="AUTO metrics",
                    )
                ],
                {
                    "status": "ok",
                    "rows": len(rows),
                    "candidates": candidates,
                    "highlights": highlights,
                },
            )
        return (
            [
                text_block(
                    "No auto metric candidates available (cpu_usage, latency, error).",
                    title="AUTO metrics",
                )
            ],
            {
                "status": "missing",
                "rows": len(rows),
                "candidates": candidates,
                "highlights": highlights,
            },
        )

    async def _run_auto_history_async(
        self, detail: Dict[str, Any], auto_spec: AutoSpec | None = None
    ) -> Tuple[List[Block], Dict[str, Any]]:
        """Generate AUTO history blocks."""
        if not self.runner.plan.history or not self.runner.plan.history.enabled:
            return [], {"status": "disabled"}
        try:
            blocks = await self.runner._history_blocks_async(detail)
            rows = self.runner.history_context.get("rows") if self.runner.history_context else None
            status = {
                "status": "ok",
                "rows": rows,
            }
            return blocks, status
        except Exception as exc:
            return [
                text_block(f"History retrieval failed: {exc}", title="AUTO History")
            ], {
                "status": "fail",
                "error": str(exc),
            }

    async def _auto_graph_scope_sections_async(
        self,
        detail: Dict[str, Any],
        auto_spec: AutoSpec,
        graph_payloads: Dict[str, Dict[str, Any]],
    ) -> Tuple[List[Block], Dict[str, Any]]:
        """Generate graph-scope metric and history sections."""
        spec = auto_spec.graph_scope
        eligible_view = next(
            (
                view
                for view in auto_spec.views
                if view in {View.DEPENDENCY, View.IMPACT}
            ),
            None,
        )
        if not eligible_view:
            return [], {"status": "disabled"}
        payload = graph_payloads.get(eligible_view.value)
        trace: Dict[str, Any] = {"view": eligible_view.value}
        if not payload:
            trace.update({"status": "no_graph_payload"})
            return [], trace
        ci_ids = payload.get("ids") or [detail["ci_id"]]
        trace["ci_ids_count"] = len(ci_ids)
        metric_blocks: List[Block] = []
        metric_trace: Dict[str, Any] = {"enabled": spec.include_metric}
        if spec.include_metric:
            rows: List[List[str]] = []
            entries: List[Dict[str, Any]] = []
            for metric_name, agg in AUTO_METRIC_PREFERENCES:
                entry: Dict[str, Any] = {"metric": metric_name}
                entry["available"] = False
                entries.append(entry)
                continue
            if rows:
                metric_blocks.append(
                    table_block(
                        ["metric_name", "agg", "value", "time_range", "ci_count"],
                        rows,
                        title=f"Graph-scope metrics ({eligible_view.value})",
                    )
                )
                metric_trace.update({"status": "ok", "entries": entries})
            else:
                metric_blocks.append(
                    text_block(
                        f"No graph-scope metrics available for {eligible_view.value}.",
                        title="Graph-scope metrics",
                    )
                )
                metric_trace.update({"status": "missing", "entries": entries})
        history_blocks: List[Block] = []
        history_trace: Dict[str, Any] = {"enabled": spec.include_history}
        if spec.include_history:
            result = await self.runner._history_recent_async(
                spec,
                {"ci_id": detail["ci_id"], "ci_code": detail.get("ci_code")},
                ci_ids=ci_ids,
                time_range="last_7d",
                limit=20,
            )
            if result.get("available"):
                history_blocks.append(
                    table_block(
                        result["columns"],
                        result["rows"],
                        title=f"Graph-scope events ({eligible_view.value})",
                    )
                )
                history_trace.update(
                    {
                        "status": "ok",
                        "ci_ids_used": len(ci_ids),
                        "ci_ids_truncated": result.get("meta", {}).get(
                            "ci_ids_truncated"
                        ),
                        "rows": len(result.get("rows", [])),
                    }
                )
            else:
                warnings = result.get("warnings", [])
                message = (
                    f"Graph-scope events unavailable: {'; '.join(warnings)}"
                    if warnings
                    else "Graph-scope events unavailable"
                )
                history_blocks.append(text_block(message, title="Graph-scope events"))
                history_trace.update({"status": "unavailable", "warnings": warnings})
        trace.update(
            {
                "metric": metric_trace,
                "history": history_trace,
            }
        )
        if spec.include_metric or spec.include_history:
            statuses = []
            if spec.include_metric:
                statuses.append(metric_trace.get("status"))
            if spec.include_history:
                statuses.append(history_trace.get("status"))
            trace["status"] = (
                "ok"
                if any(status == "ok" for status in statuses if status)
                else "partial"
            )
        else:
            trace["status"] = "disabled"
        label_parts = []
        if spec.include_metric:
            label_parts.append("metrics")
        if spec.include_history:
            label_parts.append("history")
        trace["label"] = ", ".join(label_parts) if label_parts else "disabled"
        return [*metric_blocks, *history_blocks], trace

    def _build_auto_insights(
        self, detail: Dict[str, Any], auto_trace: Dict[str, Any], summary_text: str
    ) -> List[Block]:
        """Build AUTO insight blocks."""
        blocks: List[Block] = [text_block(summary_text, title="AUTO Insights")]
        views = auto_trace.get("views") or []
        primary = next(
            (entry for entry in views if entry.get("status") == "ok"),
            views[0] if views else {},
        )
        if primary:
            view_label = primary.get("view", "N/A")
            node_count = primary.get("node_count")
            depth = primary.get("depth")
            if node_count is not None:
                blocks.append(
                    number_block("Graph nodes", node_count, title=f"{view_label} view")
                )
            if depth is not None:
                blocks.append(number_block("Graph depth", depth))
        history_rows = auto_trace.get("history", {}).get("rows")
        if history_rows is not None:
            blocks.append(number_block("Recent events (7d)", history_rows))
        metric_highlights = auto_trace.get("metrics", {}).get("highlights", [])
        if self.runner.metric_context and self.runner.metric_context.get("value") is not None:
            metric_highlights = [
                {
                    "label": f"{self.runner.metric_context['metric_name']} {self.runner.metric_context['agg']} ({self.runner.metric_context['time_range']})",
                    "value": self.runner.metric_context["value"],
                }
            ]
        for highlight in metric_highlights[:2]:
            value = highlight.get("value")
            label = highlight.get("label", "Metric")
            if isinstance(value, (int, float)):
                blocks.append(number_block(label, value, title="Metric highlight"))
            else:
                blocks.append(text_block(value or label, title="Metric highlight"))
        cep_info = auto_trace.get("cep", {})
        if cep_info.get("rule_id"):
            exec_id = cep_info.get("rule_id")
            status = cep_info.get("status")
            blocks.append(
                text_block(
                    f"CEP simulate rule {exec_id} ({status})", title="CEP Insights"
                )
            )
        return blocks

    def _build_auto_quality(
        self, auto_trace: Dict[str, Any]
    ) -> Tuple[List[Block], Dict[str, Any]]:
        """Build AUTO quality assessment blocks."""
        blocks: List[Block] = []
        policy_decisions = self.runner.plan_trace.get("policy_decisions", {})
        requested_depth = policy_decisions.get("requested_depth")
        clamped_depth = policy_decisions.get("clamped_depth")
        policy_clamped = False
        if (
            requested_depth is not None
            and clamped_depth is not None
            and requested_depth != clamped_depth
        ):
            policy_clamped = True
        graph_truncated = any(
            entry.get("truncated") for entry in auto_trace.get("views", [])
        )
        graph_scope = auto_trace.get("graph_scope", {})
        if graph_scope.get("ci_ids_truncated"):
            graph_truncated = True
        metric_status = auto_trace.get("metrics", {}).get("status")
        metric_fallback = metric_status == "missing"
        metric_missing = self.runner.plan.auto.include_metric and metric_status != "ok"
        history_status = auto_trace.get("history", {}).get("status")
        history_missing = self.runner.plan.auto.include_history and history_status != "ok"
        cep_trace = self.runner.plan_trace.get("cep", {}) or {}
        cep_error = bool(cep_trace.get("error")) or (
            "condition_evaluated" not in cep_trace.get("result", {})
            and self.runner.plan.cep
            and self.runner.plan.cep.rule_id
        )
        path_pending = auto_trace.get("path", {}).get("status") == "awaiting_target"
        signals = {
            "policy_clamped": policy_clamped,
            "graph_truncated": graph_truncated,
            "metric_fallback": metric_fallback,
            "metric_missing": metric_missing,
            "history_missing": history_missing,
            "cep_error": cep_error,
            "path_pending": path_pending,
        }
        warnings: List[Dict[str, str]] = []
        confidence = 1.0
        conf_reasons: List[str] = []

        def deduct(value: float, code: str, message: str) -> None:
            nonlocal confidence
            confidence = max(0.0, confidence - value)
            warnings.append({"code": code, "message": message})
            conf_reasons.append(f"{code}: {message}")

        if policy_clamped:
            deduct(0.05, "POLICY_CLAMP", "Requested depth was clamped by policy")
        if graph_truncated:
            deduct(0.10, "GRAPH_TRUNCATED", "Graph expansion truncated (ci_ids cap)")
        if metric_fallback:
            deduct(0.10, "METRIC_FALLBACK", "Metric fallback to candidate set")
        if metric_missing:
            deduct(0.25, "METRIC_MISSING", "Metrics unavailable for this CI")
        if history_missing:
            deduct(0.20, "HISTORY_MISSING", "History data could not be retrieved")
        if cep_error:
            deduct(0.15, "CEP_ERROR", "CEP simulate failed or was incomplete")
        if path_pending:
            deduct(0.10, "PATH_PENDING", "PATH target selection is pending")
        if not warnings:
            warn_text = "No warnings detected"
        else:
            warn_text = "\n".join(f"- {entry['message']}" for entry in warnings)
        blocks.append(text_block(warn_text, title="Quality & Warnings"))
        blocks.append(
            number_block("Confidence", round(confidence, 2), title="Quality signal")
        )
        quality_trace = {
            "confidence": round(confidence, 2),
            "confidence_reasons": conf_reasons,
            "signals": signals,
            "warnings": warnings,
        }
        return blocks, quality_trace

    def _recommend_auto_actions(
        self, auto_trace: Dict[str, Any], detail: Dict[str, Any]
    ) -> Tuple[List[NextAction], List[Dict[str, str]]]:
        """Recommend AUTO mode next actions."""
        recommended: List[NextAction] = []
        reasons: List[Dict[str, str]] = []
        seen: set[Tuple[str, str]] = set()

        def enqueue(action: NextAction, reason: str) -> None:
            if len(recommended) >= 5:
                return
            key = (action.get("type"), action.get("label"))
            if key in seen:
                return
            seen.add(key)
            recommended.append(action)
            reasons.append(
                {
                    "type": action.get("type"),
                    "label": action.get("label"),
                    "reason": reason,
                }
            )

        path_trace = auto_trace.get("path", {})
        if path_trace.get("status") == "awaiting_target":
            target_actions = [
                act for act in self.runner.next_actions if "(target)" in act.get("label", "")
            ]
            for action in target_actions:
                enqueue(action, "Choose a target CI for PATH")
        for entry in auto_trace.get("views", []):
            if entry.get("truncated"):
                current_depth = (entry.get("depth") or self.runner.plan.graph.depth or 2) + 1
                payload: RerunPayload = {
                    "patch": {
                        "graph": {"depth": current_depth, "view": entry.get("view")}
                    }
                }
                enqueue(
                    {
                        "type": "rerun",
                        "label": f"Depth +1 ({entry.get('view')})",
                        "payload": payload,
                    },
                    "Graph truncated; dig deeper",
                )
        present_views = {
            entry.get("view")
            for entry in auto_trace.get("views", [])
            if entry.get("view")
        }
        for view in ["DEPENDENCY", "IMPACT"]:
            if view not in present_views:
                payload = {"patch": {"view": view, "graph": {"view": view}}}
                enqueue(
                    {"type": "rerun", "label": f"{view} 보기", "payload": payload},
                    f"{view} view not yet shown",
                )
        metric_status = auto_trace.get("metrics", {}).get("status")
        if metric_status in {"missing", "disabled"}:
            payload = {"patch": {"metric": {"time_range": "last_24h"}}}
            enqueue(
                {
                    "type": "rerun",
                    "label": "Metric time_range: 최근 24시간",
                    "payload": payload,
                },
                "Refresh metrics with recent window",
            )
        history_trace = auto_trace.get("history", {})
        history_limit = self.runner.plan.history.limit or 20
        history_rows = history_trace.get("rows")
        if history_rows and history_limit < 50 and history_rows >= history_limit:
            payload = {"patch": {"history": {"limit": min(history_limit + 10, 50)}}}
            enqueue(
                {"type": "rerun", "label": "History limit +10", "payload": payload},
                "More history rows available",
            )
        cep_info = auto_trace.get("cep", {})
        for action in self.runner.next_actions:
            if action.get("type") == "open_event_browser":
                enqueue(action, "Open the CEP event browser for this run")
                break
        if cep_info.get("include_cep_requested") and not cep_info.get("rule_id"):
            sample = f"{detail.get('ci_code')} rule <uuid> simulate"
            enqueue(
                {
                    "type": "copy_payload",
                    "label": "Rule simulate sample",
                    "payload": sample,
                },
                "Add a rule ID to trigger CEP simulate",
            )
        return recommended, reasons

    def _insert_recommended_actions(self, recommended: List[NextAction]) -> None:
        """Insert recommended actions into next_actions with priority."""
        prioritized: List[NextAction] = []
        for rec in recommended:
            match = None
            for action in self.runner.next_actions:
                if action.get("label") == rec.get("label"):
                    match = action
                    break
            if match:
                self.runner.next_actions.remove(match)
                prioritized.append(match)
            else:
                prioritized.append(rec)
        self.runner.next_actions = prioritized + self.runner.next_actions
