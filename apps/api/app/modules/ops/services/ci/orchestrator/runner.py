from __future__ import annotations

import importlib
import re

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, Iterable, List, Literal, Sequence, Tuple

import os
import threading

from core.logging import get_logger, get_request_context
from schemas.tool_contracts import ToolCall
from app.modules.ops.services.ci import policy, response_builder
from app.modules.ops.services.ci.actions import NextAction, RerunPayload
from app.modules.ops.services.ci.blocks import Block, chart_block, number_block, table_block, text_block
from app.modules.ops.services.ci.planner.plan_schema import AutoSpec, Intent, MetricSpec, Plan, PlanMode, View
from app.modules.ops.services.ci.planner.planner_llm import (
    AGG_KEYWORDS,
    ISO_DATE_PATTERN,
    LIST_KEYWORDS,
    METRIC_ALIASES,
    METRIC_KEYWORDS,
    SERIES_KEYWORDS,
    TIME_RANGE_MAP,
)
from app.modules.ops.services.ci.tools import cep as cep_tools
from app.modules.ops.services.ci.tools import ci as ci_tools
from app.modules.ops.services.ci.tools import graph as graph_tools
from app.modules.ops.services.ci.tools import history as history_tools
from app.modules.ops.services.ci.tools import metric as metric_tools
from app.modules.ops.services.ci.tools.ci import FilterSpec


@dataclass
class RerunContext:
    selected_ci_id: str | None = None
    selected_secondary_ci_id: str | None = None


AUTO_METRIC_PREFERENCES = [
    ("cpu_usage", "max"),
    ("latency", "max"),
    ("error", "count"),
]
AUTO_VIEW_DEFAULT_DEPTHS = {
    View.COMPOSITION: 2,
    View.DEPENDENCY: 2,
    View.IMPACT: 2,
    View.NEIGHBORS: 1,
    View.PATH: 2,
}


def _find_exact_candidate(candidates: Sequence[dict], identifiers: Sequence[str]) -> dict | None:
    if not candidates or not identifiers:
        return None
    normalized_identifiers: List[str] = []
    for value in identifiers:
        cleaned = (value or "").strip()
        if cleaned:
            normalized_identifiers.append(cleaned.lower())
    if not normalized_identifiers:
        return None
    for candidate in candidates:
        ci_code = (candidate.get("ci_code") or "").strip().lower()
        ci_name = (candidate.get("ci_name") or "").strip().lower()
        if not ci_code and not ci_name:
            continue
        for identifier in normalized_identifiers:
            if identifier and (identifier == ci_code or identifier == ci_name):
                return candidate
    return None


CI_IDENTIFIER_PATTERN = re.compile(r"[a-z0-9_]+(?:-[a-z0-9_]+)+", re.IGNORECASE)

RUNNER_MARKER = "RUNNER_PATCH_GRAPH_20260112"
HISTORY_FALLBACK_KEYWORDS = {"이력", "작업", "점검", "history", "log", "이벤트", "기록"}


def _runner_context() -> Dict[str, Any]:
    return {
        "marker": RUNNER_MARKER,
        "file": __file__,
        "pid": os.getpid(),
        "thread_id": threading.get_ident(),
    }


MODULE_LOGGER = get_logger(__name__)
MODULE_LOGGER.info("ci.runner.module_start", extra=_runner_context())


class CIOrchestratorRunner:
    def __init__(
        self,
        plan: Plan,
        plan_raw: Plan,
        tenant_id: str,
        question: str,
        policy_trace: Dict[str, Any],
        rerun_context: RerunContext | None = None,
    ):
        self.plan = plan
        self.plan_raw = plan_raw
        self.tenant_id = tenant_id
        self.question = question
        self.plan_trace = policy_trace
        self.rerun_context = rerun_context or RerunContext()
        self.logger = get_logger(__name__)
        self.logger.info("ci.runner.instance_start", extra=_runner_context())
        self.tool_calls: List[ToolCall] = []
        self.tool_calls_raw: List[Dict[str, Any]] = []
        self.references: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.next_actions: List[NextAction] = []
        self.metric_context: Dict[str, Any] | None = None
        self.history_context: Dict[str, Any] | None = None
        self.list_paging_info: Dict[str, Any] | None = None
        self.aggregation_summary: Dict[str, Any] | None = None
        self._ci_search_recovery: bool = False
        self.DEFAULT_OUTPUT_BLOCKS = ("text", "table")
        self.GRAPH_VIEWS = {View.COMPOSITION, View.DEPENDENCY, View.IMPACT, View.NEIGHBORS}
        self.GRAPH_VIEWS_WITH_PATH = self.GRAPH_VIEWS | {View.PATH}
        self._last_graph_signature: tuple | None = None
        self.GRAPH_SCOPE_KEYWORDS = ("영향권", "영향", "범위", "의존", "dependency", "impact")
        self.GRAPH_SCOPE_METRIC_KEYWORDS = ("cpu", "latency", "error", "memory", "disk", "network")

    @contextmanager
    def _tool_context(self, tool: str, input_params: Dict[str, Any] | None = None, **meta):
        meta = dict(meta)
        start = perf_counter()
        self.logger.info(f"ci.tool.{tool}.start", extra=meta)
        try:
            yield meta
        except Exception as exc:
            meta["error"] = str(exc)
            raise
        finally:
            elapsed = int((perf_counter() - start) * 1000)
            meta["elapsed_ms"] = elapsed
            self.logger.info(f"ci.tool.{tool}.done", extra=meta)

            # Store raw entry for backward compatibility
            entry = {"tool": tool, **meta}
            self.tool_calls_raw.append(entry)

            # Create ToolCall with standardized structure
            output_summary = {k: v for k, v in meta.items()
                            if k not in ("error", "elapsed_ms") and not k.startswith("_")}
            error = meta.get("error")

            tool_call = ToolCall(
                tool=tool,
                elapsed_ms=elapsed,
                input_params=input_params or {},
                output_summary=output_summary,
                error=error
            )
            self.tool_calls.append(tool_call)

    def _log_routing(self, route: str) -> None:
        self.logger.info(
            "ci.runner.routing",
            extra={"intent": self.plan.intent.value if self.plan.intent else None, "metric": bool(self.plan.metric), "route": route},
        )

    def _extract_references_from_blocks(self, blocks: List[Block]) -> None:
        """Extract and accumulate references from blocks."""
        for block in blocks:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "references":
                    items = block.get("items", [])
                    for item in items:
                        if isinstance(item, dict) and "kind" in item and "payload" in item:
                            self.references.append(item)
            else:
                # Pydantic model
                block_type = getattr(block, "type", None)
                if block_type == "references":
                    items = getattr(block, "items", [])
                    for item in items:
                        item_dict = item.dict() if hasattr(item, "dict") else dict(item)
                        if "kind" in item_dict and "payload" in item_dict:
                            self.references.append(item_dict)

    def _log_metric_blocks_return(self, blocks: List[Block]) -> None:
        types = [block.get("type") if isinstance(block, dict) else getattr(block, "type", None) for block in blocks]
        self.logger.info("ci.metric.blocks_debug", extra={"types": types, "count": len(blocks)})

    def _ci_search(
        self,
        keywords: Iterable[str] | None = None,
        filters: Iterable[FilterSpec] | None = None,
        limit: int | None = None,
        sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
    ) -> List[Dict[str, Any]]:
        keywords_tuple = tuple(keywords or ())
        filters_tuple = tuple(filters or ())
        input_params = {
            "keywords": list(keywords_tuple),
            "filter_count": len(filters_tuple),
            "limit": limit,
            "sort": sort,
        }
        with self._tool_context(
            "ci.search",
            input_params=input_params,
            keyword_count=len(keywords_tuple),
            filter_count=len(filters_tuple),
            limit=limit,
            sort_column=sort[0] if sort else None,
        ) as meta:
            result = ci_tools.ci_search(
                self.tenant_id,
                keywords=keywords_tuple,
                filters=filters_tuple,
                limit=limit,
                sort=sort,
            )
            meta["row_count"] = len(result)
        if not result and not self._ci_search_recovery:
            recovered = self._recover_ci_identifiers()
            if recovered:
                self._ci_search_recovery = True
                self.logger.info("ci.runner.ci_search_recovery", extra={"recovery_keywords": recovered})
                self.plan = self.plan.copy(
                    update={"primary": self.plan.primary.copy(update={"keywords": list(recovered)})}
                )
                return self._ci_search(keywords=recovered, filters=filters, limit=limit, sort=sort)
        return result

    def _ci_search_broad_or(
        self,
        keywords: Sequence[str],
        filters: Sequence[dict] | None,
        limit: int,
    ) -> List[Dict[str, Any]]:
        tokens: List[str] = []
        for keyword in keywords or ():
            value = (keyword or "").strip()
            if not value:
                continue
            tokens.append(value)
            for part in re.split(r"[\\s_\\-]+", value):
                part = part.strip()
                if len(part) >= 2:
                    tokens.append(part)
        if self.question:
            for part in re.split(r"[\\s_\\-]+", self.question):
                part = part.strip()
                if len(part) >= 2 and part.isascii() and any(ch.isalnum() for ch in part):
                    tokens.append(part)
        deduped: List[str] = []
        seen = set()
        for token in tokens:
            lower = token.lower()
            if lower in seen:
                continue
            seen.add(lower)
            deduped.append(token)
        with self._tool_context(
            "ci.search_broad",
            keyword_count=len(deduped),
            filter_count=len(filters or ()),
            limit=limit,
            sort_column=None,
        ) as meta:
            result = ci_tools.ci_search_broad_or(
                self.tenant_id,
                keywords=tuple(deduped),
                filters=tuple(filters or ()),
                limit=limit,
                sort=None,
            )
            meta["row_count"] = len(result)
        return result

    def _recover_ci_identifiers(self) -> tuple[str, ...] | None:
        if not self.question:
            return None
        normalized = self.question.lower()
        # Accept identifiers containing underscores and multiple hyphen segments.
        # Examples: os-erp-02, apm_app_scheduler_05-1, app-apm-scheduler-05-1
        matches = re.findall(r"[a-z0-9_]+(?:-[a-z0-9_]+)+", normalized)
        unique = []
        for match in matches:
            if match not in unique:
                unique.append(match)
        if unique:
            return tuple(unique[:5])
        return None

    def _sanitize_ci_keywords(self, keywords: Sequence[str]) -> List[str]:
        filtered = set()
        filtered.update(k.lower() for k in METRIC_KEYWORDS)
        filtered.update(k.lower() for k in METRIC_ALIASES.keys())
        filtered.update(k.lower() for k in AGG_KEYWORDS.keys())
        filtered.update(k.lower() for k in TIME_RANGE_MAP.keys())
        filtered.update(k.lower() for k in SERIES_KEYWORDS)
        filtered.update(k.lower() for k in LIST_KEYWORDS)
        sanitized: List[str] = []
        for token in keywords:
            normalized = token.lower().strip()
            if not normalized:
                continue
            if normalized in filtered:
                continue
            if ISO_DATE_PATTERN.search(normalized):
                continue
            sanitized.append(token)
            if len(sanitized) >= 5:
                break
        return sanitized

    def _build_ci_search_keywords(self) -> tuple[List[str], str, List[str]]:
        before = list(self.plan.primary.keywords)
        recovered = self._recover_ci_identifiers()
        if recovered:
            return list(recovered[:5]), "recover_ci_identifiers", before
        primary_sanitized = self._sanitize_ci_keywords(self.plan.primary.keywords)
        if primary_sanitized:
            return primary_sanitized, "plan_primary", before
        secondary_sanitized = self._sanitize_ci_keywords(self.plan.secondary.keywords or [])
        if secondary_sanitized:
            return secondary_sanitized, "plan_secondary", before
        fallback = before[: min(2, len(before))] or (self.plan.secondary.keywords or [])[:2]
        return fallback, "fallback", before

    def _extract_ci_identifiers(self, keywords: Sequence[str]) -> List[str]:
        identifiers: List[str] = []
        for token in keywords:
            if not token:
                continue
            match = CI_IDENTIFIER_PATTERN.fullmatch(token.lower())
            if match:
                identifiers.append(token)
        return identifiers

    def _has_ci_identifier_in_keywords(self) -> bool:
        if self._extract_ci_identifiers(self.plan.primary.keywords):
            return True
        if self._extract_ci_identifiers(self.plan.secondary.keywords or []):
            return True
        return False

    def _routing_identifiers(self) -> List[str]:
        identifiers: List[str] = []
        for source in (
            self.plan.primary.keywords,
            self.plan.secondary.keywords or [],
            self._recover_ci_identifiers() or (),
        ):
            for token in self._extract_ci_identifiers(source):
                if token not in identifiers:
                    identifiers.append(token)
        return identifiers

    def _is_graph_requested(self) -> bool:
        view = (self.plan.graph.view or self.plan.view) or View.SUMMARY
        if view in {View.COMPOSITION, View.DEPENDENCY, View.IMPACT, View.NEIGHBORS, View.PATH}:
            return True
        return "network" in (self.plan.output.blocks or [])

    def _should_list_fallthrough_to_lookup(self) -> bool:
        if not (self.plan.intent == Intent.LIST or self.plan.list.enabled):
            return False
        if not self._is_graph_requested():
            return False
        return self._has_ci_identifier_in_keywords()

    def _ci_get(self, ci_id: str) -> Dict[str, Any] | None:
        with self._tool_context("ci.get", input_params={"ci_id": ci_id}, ci_id=ci_id) as meta:
            detail = ci_tools.ci_get(self.tenant_id, ci_id)
            meta["found"] = bool(detail)
        return detail

    def _ci_get_by_code(self, ci_code: str) -> Dict[str, Any] | None:
        with self._tool_context("ci.get", input_params={"ci_code": ci_code}, ci_code=ci_code) as meta:
            detail = ci_tools.ci_get_by_code(self.tenant_id, ci_code)
            meta["found"] = bool(detail)
        return detail

    def _ci_aggregate(
        self,
        group_by: Iterable[str],
        metrics: Iterable[str],
        filters: Iterable[FilterSpec] | None = None,
        ci_ids: Iterable[str] | None = None,
        top_n: int | None = None,
    ) -> Dict[str, Any]:
        group_list = tuple(group_by or ())
        metric_list = tuple(metrics or ())
        filters_tuple = tuple(filters or ())
        ci_ids_tuple = tuple(ci_ids or ())
        input_params = {
            "group_by": list(group_list),
            "metrics": list(metric_list),
            "filter_count": len(filters_tuple),
            "ci_ids_count": len(ci_ids_tuple),
            "top_n": top_n,
        }
        with self._tool_context(
            "ci.aggregate",
            input_params=input_params,
            group_by=",".join(group_list),
            metrics=",".join(metric_list),
            filter_count=len(filters_tuple),
            ci_ids_count=len(ci_ids_tuple),
            top_n=top_n,
        ) as meta:
            result = ci_tools.ci_aggregate(
                self.tenant_id,
                group_by,
                metrics,
                filters=filters,
                ci_ids=ci_ids,
                top_n=top_n,
            )
            meta["row_count"] = len(result.get("rows", []))
        return result

    def _ci_list_preview(
        self,
        limit: int,
        offset: int = 0,
        filters: Iterable[FilterSpec] | None = None,
    ) -> Dict[str, Any]:
        filters_tuple = tuple(filters or ())
        input_params = {
            "limit": limit,
            "offset": offset,
            "filter_count": len(filters_tuple),
        }
        with self._tool_context(
            "ci.list",
            input_params=input_params,
            limit=limit,
            offset=offset,
            filter_count=len(filters_tuple),
        ) as meta:
            result = ci_tools.ci_list_preview(self.tenant_id, limit, offset, filters)
            meta["row_count"] = len(result.get("rows", []))
        return result

    def _graph_expand(self, ci_id: str, view: str, depth: int, limits: dict[str, int]) -> Dict[str, Any]:
        input_params = {
            "ci_id": ci_id,
            "view": view,
            "depth": depth,
            "limits": limits,
        }
        with self._tool_context("graph.expand", input_params=input_params, view=view, depth=depth) as meta:
            raw_payload = graph_tools.graph_expand(self.tenant_id, ci_id, view, depth=depth, limits=limits)
            payload_type = type(raw_payload).__name__ if raw_payload is not None else "NoneType"
            raw_extra: Dict[str, Any] = {"type": payload_type, "preview": str(raw_payload)[:200]}
            if isinstance(raw_payload, dict):
                raw_extra["keys"] = list(raw_payload.keys())
            elif isinstance(raw_payload, list):
                raw_extra["list_len"] = len(raw_payload)
            else:
                raw_extra["attrs"] = [attr for attr in dir(raw_payload) if not attr.startswith("_")]
            self.logger.info("ci.graph.expand_return_debug", extra=raw_extra)
            normalized = self._normalize_graph_payload(raw_payload, payload_type, meta)
        return normalized

    def _normalize_graph_payload(self, raw_payload: Any, payload_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {
            "nodes": [],
            "edges": [],
            "summary": {},
            "meta": {},
            "truncated": False,
        }
        if isinstance(raw_payload, dict):
            normalized.update(raw_payload)
        elif isinstance(raw_payload, list):
            normalized["nodes"] = list(raw_payload)
        else:
            normalized.update(
                {
                    "nodes": getattr(raw_payload, "nodes", []) or [],
                    "edges": getattr(raw_payload, "edges", []) or [],
                    "summary": getattr(raw_payload, "summary", {}) or {},
                    "meta": getattr(raw_payload, "meta", {}) or {},
                    "truncated": bool(getattr(raw_payload, "truncated", False)),
                }
            )
        nodes = normalized.get("nodes")
        normalized["nodes"] = list(nodes) if isinstance(nodes, list) else []
        edges = normalized.get("edges")
        normalized["edges"] = list(edges) if isinstance(edges, list) else []
        summary = normalized.get("summary")
        normalized["summary"] = summary if isinstance(summary, dict) else {}
        meta_value = normalized.get("meta")
        normalized["meta"] = meta_value if isinstance(meta_value, dict) else {}
        normalized["truncated"] = bool(normalized.get("truncated", False))
        meta["payload_type"] = payload_type
        meta["node_count"] = len(normalized["nodes"])
        meta["edge_count"] = len(normalized["edges"])
        meta["truncated"] = normalized["truncated"]
        self.logger.info(
            "ci.graph.expand_normalized_debug",
            extra={
                "nodes_len": len(normalized["nodes"]),
                "edges_len": len(normalized["edges"]),
                "keys": list(normalized.keys()),
            },
        )
        return normalized

    def _graph_path(self, source_id: str, target_id: str, hops: int) -> Dict[str, Any]:
        input_params = {
            "source_id": source_id,
            "target_id": target_id,
            "hops": hops,
        }
        with self._tool_context("graph.path", input_params=input_params, hop_count=hops) as meta:
            payload = graph_tools.graph_path(self.tenant_id, source_id, target_id, hops)
            meta["node_count"] = len(payload.get("nodes", []))
            meta["edge_count"] = len(payload.get("edges", []))
            meta["hop_count"] = payload.get("hop_count")
        return payload

    def _metric_aggregate(
        self,
        metric_name: str,
        agg: str,
        time_range: str,
        ci_id: str | None = None,
        ci_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        ci_ids_tuple = tuple(ci_ids or ())
        input_params = {
            "metric_name": metric_name,
            "agg": agg,
            "time_range": time_range,
            "ci_id": ci_id,
            "ci_ids_count": len(ci_ids_tuple),
        }
        with self._tool_context(
            "metric.aggregate",
            input_params=input_params,
            metric=metric_name,
            agg=agg,
            time_range=time_range,
            ci_ids_count=len(ci_ids_tuple),
        ) as meta:
            result = metric_tools.metric_aggregate(self.tenant_id, metric_name, time_range, agg, ci_id=ci_id, ci_ids=ci_ids_tuple or None)
            meta["value_present"] = result.get("value") is not None
            meta["ci_count_used"] = len(result.get("ci_ids", []))
        return result

    def _metric_series_table(
        self,
        ci_id: str,
        metric_name: str,
        time_range: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        input_params = {
            "ci_id": ci_id,
            "metric_name": metric_name,
            "time_range": time_range,
            "limit": limit,
        }
        with self._tool_context("metric.series", input_params=input_params, metric=metric_name, time_range=time_range, limit=limit) as meta:
            result = metric_tools.metric_series_table(self.tenant_id, ci_id, metric_name, time_range, limit)
            meta["rows_count"] = len(result.get("rows", []))
        return result

    def _history_recent(
        self,
        history_spec: Any,
        ci_context: Dict[str, Any],
        ci_ids: list[str] | None = None,
        time_range: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        final_time_range = time_range or getattr(history_spec, "time_range", None) or "last_7d"
        final_limit = limit or getattr(history_spec, "limit", None) or 50
        scope = getattr(history_spec, "scope", "ci")
        input_params = {
            "time_range": final_time_range,
            "scope": scope,
            "limit": final_limit,
            "ci_ids_count": len(ci_ids) if ci_ids else 0,
        }
        with self._tool_context(
            "history.recent",
            input_params=input_params,
            time_range=final_time_range,
            scope=scope,
            limit=final_limit,
        ) as meta:
            result = history_tools.event_log_recent(
                self.tenant_id,
                ci_context,
                final_time_range,
                final_limit,
                ci_ids=ci_ids,
            )
            meta["row_count"] = len(result.get("rows", []))
            meta["warnings_count"] = len(result.get("warnings", []))
            meta["available"] = result.get("available")
        return result

    def _cep_simulate(
        self,
        rule_id: str | None,
        ci_context: Dict[str, Any],
        metric_context: Dict[str, Any] | None,
        history_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        input_params = {
            "rule_id": rule_id,
            "ci_context_keys": list(ci_context.keys()) if ci_context else [],
            "metric_context_present": bool(metric_context),
            "history_context_present": bool(history_context),
        }
        with self._tool_context("cep.simulate", input_params=input_params, rule_id=rule_id) as meta:
            result = cep_tools.cep_simulate(
                self.tenant_id,
                rule_id or "",
                ci_context,
                metric_context=metric_context,
                history_context=history_context,
            )
            meta["success"] = bool(result.get("success"))
            meta["exec_log_present"] = bool(result.get("exec_log_id"))
        return result

    def run(self) -> Dict[str, Any]:
        blocks: List[Block] = []
        answer = "CI insight ready"
        auto_trace: Dict[str, Any] | None = None
        start = perf_counter()
        plan_view = (self.plan.view or View.SUMMARY).value if self.plan.view else View.SUMMARY.value
        runner_context = _runner_context()
        self.logger.info(
            "ci.runner.start",
            extra={
                "rerun": bool(self.rerun_context.selected_ci_id or self.rerun_context.selected_secondary_ci_id),
                "view": plan_view,
                "depth": self.plan.graph.depth,
                "list_enabled": self.plan.list.enabled,
                "metric_enabled": bool(self.plan.metric),
                "history_enabled": bool(self.plan.history.enabled),
                "cep_enabled": bool(self.plan.cep and self.plan.cep.rule_id),
                **runner_context,
            },
        )
        self.logger.info("ci.runner.version", extra={**runner_context, "class": self.__class__.__name__})
        self._runner_context = runner_context
        # self-check: 
        # 1) "srv-erp-02 cpu 평균 오늘" → keywords sanitizes to ["srv-erp-02"] → _handle_lookup() runs metric.aggregate/series.
        # 2) "ci 타입별 개수" → no plan.metric → _handle_aggregate() returns ci.aggregate blocks as before.
        # 3) "srv-erp-02 영향권 cpu max" → graph expand happens first, then graph-scope metric blocks (graph_payload keeps ids).
        extracted_identifiers = self._routing_identifiers()
        graph_requested = self._is_graph_requested()
        list_patch_present = bool(self.plan.list.offset or self.plan.list.limit)
        rerun_present = bool(
            self.rerun_context.selected_ci_id or self.rerun_context.selected_secondary_ci_id
        )
        decision_context = {
            "list_fallthrough": self._should_list_fallthrough_to_lookup(),
            "graph_requested": graph_requested,
            "extracted_identifiers": extracted_identifiers,
            "list_patch_present": list_patch_present,
            "rerun": rerun_present,
        }
        self.logger.info("ci.runner.routing_decision", extra=decision_context)
        try:
            if self.plan.mode == PlanMode.AUTO:
                self._log_routing("auto")
                blocks, answer, auto_trace = self._run_auto_recipe()
            elif self._should_list_fallthrough_to_lookup():
                self._log_routing("graph requested → lookup")
                blocks, answer = self._handle_lookup()
            elif graph_requested and extracted_identifiers:
                self._log_routing("graph requested + identifier → lookup")
                blocks, answer = self._handle_lookup()
            elif self.plan.intent == Intent.LIST or self.plan.list.enabled:
                self._log_routing("list (pure)")
                blocks, answer = self._handle_list_preview()
            elif self.plan.metric:
                self._log_routing("metric → lookup")
                blocks, answer = self._handle_lookup()
            elif self.plan.intent == Intent.LOOKUP:
                self._log_routing("lookup")
                blocks, answer = self._handle_lookup()
            elif self.plan.intent == Intent.AGGREGATE:
                self._log_routing("aggregate")
                blocks, answer = self._handle_aggregate()
            elif self.plan.intent == Intent.PATH:
                self._log_routing("path")
                blocks, answer = self._handle_path()
            elif self.plan.list.enabled:
                self._log_routing("list (fallback)")
                blocks, answer = self._handle_list_preview()
            else:
                self._log_routing("lookup (fallback)")
                blocks, answer = self._handle_lookup()
        except Exception as exc:  # pragma: no cover - best effort
            self.errors.append(str(exc))
            raise

        # Extract references from blocks
        self._extract_references_from_blocks(blocks)

        context = get_request_context()
        trace_id = context.get("trace_id") or "-"
        parent_trace_id = context.get("parent_trace_id") or "-"

        trace = {
            "plan_raw": self.plan_raw.dict(),
            "plan_validated": self.plan.dict(),
            "policy_decisions": self.plan_trace.get("policy_decisions"),
            "tool_calls": [call.dict() for call in self.tool_calls],
            "references": self.references,
            "errors": self.errors,
            "tenant_id": self.tenant_id,
            "trace_id": trace_id if trace_id != "-" else None,
            "parent_trace_id": parent_trace_id if parent_trace_id != "-" else None,
        }
        if self.aggregation_summary:
            plan_trace = trace.setdefault("plan", {})
            plan_trace["aggregation"] = self.aggregation_summary
        self._apply_list_trace(trace)
        if auto_trace:
            trace["auto"] = auto_trace
        used_tools = [call.tool for call in self.tool_calls if call.tool]
        if self.plan.metric and "ci.aggregate" in used_tools:
            self.logger.warning(
                "ci.runner.assert_failed",
                extra={"used_tools": used_tools, "intent": self.plan.intent.value if self.plan.intent else None, "metric": True},
            )
        if graph_requested and "graph.expand" not in used_tools:
            self.logger.warning(
                "ci.runner.graph_missing",
                extra={"graph_requested": graph_requested, "used_tools": used_tools},
            )
            trace["graph_expected_but_missing"] = True
            self.plan_trace["graph_expected_but_missing"] = True
        runner_context_meta = getattr(self, "_runner_context", _runner_context())
        meta = {
            "route": "ci",
            "route_reason": "CI tab",
            "timing_ms": 0,
            "summary": answer,
            "used_tools": used_tools,
            "fallback": len(self.errors) > 0,
            "runner_context": runner_context_meta,
            "trace_id": trace_id if trace_id != "-" else None,
            "parent_trace_id": parent_trace_id if parent_trace_id != "-" else None,
        }
        block_types = []
        for block in blocks:
            if isinstance(block, dict):
                block_type = block.get("type")
            else:
                block_type = getattr(block, "type", None)
            if block_type:
                block_types.append(block_type)
        self.logger.info("ci.runner.blocks_debug", extra={"types": block_types, "count": len(blocks)})
        self.logger.info(
            "ci.runner.blocks",
            extra={"blocks_count": len(blocks), "block_types": block_types},
        )
        elapsed_ms = int((perf_counter() - start) * 1000)
        self.logger.info(
            "ci.runner.done",
            extra={"elapsed_ms": elapsed_ms, "errors": len(self.errors)},
        )
        return {
            "answer": answer,
            "blocks": blocks,
            "trace": trace,
            "next_actions": self._finalize_next_actions(),
            "meta": meta,
        }

    def _handle_lookup(self) -> tuple[List[Block], str]:
        self.metric_context = None
        self.history_context = None
        detail, fallback_blocks, fallback_message = self._resolve_ci_detail()
        if not detail:
            return fallback_blocks or [], fallback_message or "Unable to resolve CI"
        blocks = response_builder.build_ci_detail_blocks(detail)
        graph_view = self.plan.graph.view or (self.plan.view or View.SUMMARY)
        if self._should_run_sections_loop():
            blocks.extend(self._execute_sections_loop(detail, graph_view))
        else:
            blocks.extend(self._metric_blocks(detail))
            blocks.extend(self._history_blocks(detail))
            graph_blocks, _ = self._build_graph_blocks(detail, graph_view)
            blocks.extend(graph_blocks)
            blocks.extend(self._cep_blocks(detail))
        answer = f"Lookup result for {detail['ci_code']}"
        return blocks, answer

    def _should_run_sections_loop(self) -> bool:
        if self.plan.mode == PlanMode.AUTO:
            return True
        output_blocks = tuple(self.plan.output.blocks or ())
        if len(output_blocks) >= 2 and output_blocks != self.DEFAULT_OUTPUT_BLOCKS:
            return True
        section_count = 0
        if self.plan.metric:
            section_count += 1
        if self.plan.history.enabled:
            section_count += 1
        if self.plan.cep and self.plan.cep.mode == "simulate":
            section_count += 1
        return section_count >= 2

    def _graph_scope_metric_requested(self) -> bool:
        if self.plan.metric and self.plan.metric.scope == "graph":
            return True
        text = (self.question or "").lower()
        if not text:
            return False
        return (
            any(kw in text for kw in self.GRAPH_SCOPE_KEYWORDS)
            and any(kw in text for kw in self.GRAPH_SCOPE_METRIC_KEYWORDS)
        )

    def _compute_graph_signature(self, payload: Dict[str, Any] | None) -> tuple | None:
        if not payload:
            return None
        nodes_value = payload.get("nodes")
        nodes = nodes_value if isinstance(nodes_value, list) else []
        edges_value = payload.get("edges")
        edges = edges_value if isinstance(edges_value, list) else []
        meta_value = payload.get("meta")
        if isinstance(meta_value, dict):
            depth = meta_value.get("depth")
        else:
            depth = None
        truncated = bool(payload.get("truncated", False))
        ids_source = payload.get("ids")
        if isinstance(ids_source, list):
            ids = tuple(ids_source[:5])
        else:
            ids = tuple()
        preview_ids = tuple(identifier for identifier in ids if identifier)
        return (len(nodes), len(edges), depth, truncated, preview_ids)

    def _build_graph_blocks(self, detail: Dict[str, Any], graph_view: View, allow_path: bool = False) -> tuple[List[Block], Dict[str, Any] | None]:
        if not graph_view:
            return [], None
        allowed = self.GRAPH_VIEWS_WITH_PATH if allow_path else self.GRAPH_VIEWS
        if graph_view not in allowed:
            return [], None
        try:
            self.logger.info(
                "ci.graph.payload_type_debug",
                extra={"stage": "before_expand", "view": graph_view.value},
            )
            payload = self._graph_expand(
                detail["ci_id"],
                graph_view.value,
                self.plan.graph.depth,
                self.plan.graph.limits.dict(),
            )
            self.logger.info(
                "ci.graph.payload_type_debug",
                extra={
                    "stage": "after_expand",
                    "type": type(payload).__name__,
                    "keys": list(payload.keys()) if isinstance(payload, dict) else None,
                    "view": graph_view.value,
                    "nodes_len": len(payload.get("nodes", [])) if isinstance(payload, dict) and isinstance(payload.get("nodes"), list) else None,
                    "edges_len": len(payload.get("edges", [])) if isinstance(payload, dict) and isinstance(payload.get("edges"), list) else None,
                },
            )
            if not isinstance(payload, dict):
                self.logger.error(
                    "ci.graph.payload_type",
                    extra={"type": type(payload).__name__, "message": "graph payload not dict"},
                )
                self._last_graph_signature = self._compute_graph_signature(None)
                return [
                    text_block("Graph payload malformed", title=f"Graph {graph_view.value}")
                ], None
            truncated = payload.get("truncated", False)
            nodes = payload.get("nodes")
            edges = payload.get("edges")
            if not isinstance(nodes, list) or not isinstance(edges, list):
                self.logger.error(
                    "ci.graph.payload_type",
                    extra={
                        "type": type(payload).__name__,
                        "message": "graph payload missing nodes/edges",
                        "keys": list(payload.keys()),
                    },
                )
                self._last_graph_signature = self._compute_graph_signature(None)
                return [
                    text_block("Graph payload malformed", title=f"Graph {graph_view.value}")
                ], payload
            self.logger.info(
                "ci.graph.payload_debug",
                extra={
                    "keys": list(payload.keys()),
                    "nodes_len": len(nodes),
                    "edges_len": len(edges),
                },
            )
            self.next_actions.extend(
                self._graph_next_actions(
                    graph_view.value,
                    payload.get("meta", {}).get("depth", self.plan.graph.depth),
                    truncated,
                )
            )
            self._last_graph_signature = self._compute_graph_signature(payload)
            return response_builder.build_network_blocks(payload), payload
        except Exception as exc:
            self.logger.exception("ci.graph.build_graph_blocks.error", exc_info=exc)
            self.errors.append(str(exc))
            self._last_graph_signature = self._compute_graph_signature(None)
            return [text_block(f"Graph {graph_view.value} expansion failed: {exc}", title=f"Graph {graph_view.value}")], None

    def _execute_sections_loop(self, detail: Dict[str, Any], graph_view: View) -> List[Block]:
        if not detail:
            return []
        sections = []
        if self.plan.metric:
            sections.append("metric")
        if self.plan.history.enabled:
            sections.append("history")
        if self.plan.cep and self.plan.cep.mode == "simulate":
            sections.append("cep")
        graph_enabled = graph_view in self.GRAPH_VIEWS_WITH_PATH
        force_graph = self._graph_scope_metric_requested() or (self.plan.history.scope == "graph" and self.plan.history.enabled)
        if graph_enabled or force_graph:
            graph_view_for_loop = graph_view if graph_enabled else (self.plan.graph.view or View.DEPENDENCY)
            sections.append("graph")
        else:
            graph_view_for_loop = graph_view
        if not sections:
            return []
        outputs: Dict[str, List[Block]] = {}
        prev_signature = None
        iteration = 0
        max_iterations = 4
        self._last_graph_signature = None
        graph_payload: Dict[str, Any] | None = None
        graph_call_index = 0
        while iteration < max_iterations:
            iteration += 1
            if "graph" in sections:
                graph_call_index += 1
                self.logger.info(
                    "ci.graph.build_graph_blocks.start",
                    extra={
                        "view": graph_view_for_loop.value,
                        "depth": self.plan.graph.depth,
                        "call_index": graph_call_index,
                    },
                )
                try:
                    graph_blocks, graph_payload = self._build_graph_blocks(detail, graph_view_for_loop, allow_path=True)
                except Exception as exc:
                    self.logger.exception("ci.graph.build_graph_blocks.exception", exc_info=exc)
                    graph_blocks, graph_payload = (
                        [text_block(f"Graph {graph_view_for_loop.value} expansion failed: {exc}", title=f"Graph {graph_view_for_loop.value}")],
                        None,
                    )
                outputs["graph"] = graph_blocks
            if "metric" in sections:
                outputs["metric"] = self._metric_blocks(detail, graph_payload)
            if "history" in sections:
                outputs["history"] = self._history_blocks(detail, graph_payload)
            if "cep" in sections:
                outputs["cep"] = self._cep_blocks(detail)
            signature = (repr(self.metric_context), repr(self.history_context), self._last_graph_signature)
            if signature == prev_signature:
                break
            prev_signature = signature
        combined: List[Block] = []
        for name in ["metric", "history", "graph", "cep"]:
            combined.extend(outputs.get(name) or [])
        return combined
    def _run_auto_recipe(self) -> tuple[List[Block], str, Dict[str, Any]]:
        detail, fallback_blocks, fallback_message = self._resolve_ci_detail()
        auto_spec = self.plan.auto
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
            return fallback_blocks or [], fallback_message or "AUTO recipe could not resolve CI", auto_trace
        graph_blocks, graph_payloads, view_entries = self._auto_graph_blocks(detail, auto_spec)
        path_blocks, path_trace = self._auto_path_blocks(detail, auto_spec)
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
        metrics_blocks, metric_trace = self._run_auto_metrics(detail, auto_spec)
        auto_trace["metrics"] = metric_trace
        history_blocks, history_trace = self._run_auto_history(detail, auto_spec)
        auto_trace["history"] = history_trace
        graph_scope_blocks, graph_scope_trace = self._auto_graph_scope_sections(detail, auto_spec, graph_payloads)
        auto_trace["graph_scope"] = graph_scope_trace
        cep_blocks = self._cep_blocks(detail)
        cep_status = "simulated" if self.plan.cep and self.plan.cep.rule_id else "skipped"
        auto_trace["cep"] = {"status": cep_status, "rule_id": self.plan.cep.rule_id if self.plan.cep else None}
        view_labels = "+".join(entry.get("view", "") for entry in view_entries_with_path if entry.get("view")) or "NEIGHBORS"
        metrics_label = metric_trace.get("status", "disabled")
        history_label = history_trace.get("status", "disabled")
        graph_scope_label = graph_scope_trace.get("label", "disabled")
        path_label = path_trace.get("status", "skipped") if path_trace else "skipped"
        summary_text = (
            f"AUTO 점검 결과: CI={detail.get('ci_code','N/A')}, views={view_labels}, path={path_label}, "
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

    def _auto_depth_for_view(self, view: View, auto_spec: AutoSpec) -> int:
        requested = auto_spec.depth_hint or AUTO_VIEW_DEFAULT_DEPTHS.get(view, 2)
        return policy.clamp_depth(view.value, requested)

    def _auto_graph_blocks(
        self, detail: Dict[str, Any], auto_spec: AutoSpec
    ) -> tuple[List[Block], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        views = [view for view in auto_spec.views if view not in {View.SUMMARY, View.PATH}]
        if not views:
            views = [View.NEIGHBORS]
        graph_blocks: List[Block] = []
        graph_payloads: Dict[str, Dict[str, Any]] = {}
        entries: List[Dict[str, Any]] = []
        for view in views:
            depth = self._auto_depth_for_view(view, auto_spec)
            view_entry: Dict[str, Any] = {"view": view.value}
            try:
                payload = self._graph_expand(
                    detail["ci_id"],
                    view.value,
                    depth,
                    self.plan.graph.limits.dict(),
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
                self.next_actions.extend(
                    self._graph_next_actions(
                        view.value,
                        payload.get("meta", {}).get("depth", depth),
                        truncated,
                    )
                )
            except Exception as exc:
                view_entry.update({"status": "fail", "error": str(exc)})
                graph_blocks.append(text_block(f"Graph {view.value} expansion failed: {exc}", title=f"AUTO {view.value}"))
            entries.append(view_entry)
        return graph_blocks, graph_payloads, entries

    def _auto_path_blocks(self, detail: Dict[str, Any], auto_spec: AutoSpec) -> tuple[List[Block], Dict[str, Any]]:
        if View.PATH not in auto_spec.views:
            return [], {"status": "skipped"}
        path_spec = auto_spec.path
        trace: Dict[str, Any] = {"requested": path_spec.dict(), "view": View.PATH.value}
        source_detail = detail
        if path_spec.source_ci_code and path_spec.source_ci_code.lower() != detail["ci_code"].lower():
            resolved = self._ci_detail_by_code(path_spec.source_ci_code)
            if resolved:
                source_detail = resolved
            else:
                trace.setdefault("warnings", []).append(f"Source CI '{path_spec.source_ci_code}' not found")
        target_detail = None
        if path_spec.target_ci_code:
            target_detail = self._ci_detail_by_code(path_spec.target_ci_code)
            if not target_detail:
                trace["status"] = "target_not_found"
        if target_detail:
            hops = self._auto_path_hops(auto_spec)
            path_payload = self._graph_path(source_detail["ci_id"], target_detail["ci_id"], hops)
            if not path_payload.get("nodes"):
                message = f"No path found from {source_detail['ci_code']} to {target_detail['ci_code']}"
                trace.update({"status": "no_path", "source": source_detail["ci_code"], "target": target_detail["ci_code"]})
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
        candidates = self._auto_path_candidates(detail)
        if not candidates:
            trace["status"] = "no_candidates"
            return [text_block("No path candidates available.", title="AUTO Path")], trace
        trace.update({"status": "awaiting_target", "candidates": [candidate.get("ci_code") for candidate in candidates]})
        blocks: List[Block] = [
            text_block("No target CI specified. Select one to complete the path.", title="AUTO Path"),
            response_builder.build_candidate_table(candidates, role="target"),
        ]
        self.next_actions.extend(self._path_target_next_actions(candidates))
        return blocks, trace

    def _ci_detail_by_code(self, ci_code: str | None) -> Dict[str, Any] | None:
        if not ci_code:
            return None
        detail = self._ci_get_by_code(ci_code)
        if detail:
            return detail
        # fallback will search, let `_ci_search` handle logging
        return None

    def _auto_path_hops(self, auto_spec: AutoSpec) -> int:
        hint = auto_spec.depth_hint or self.plan.graph.depth or 4
        return policy.clamp_depth("PATH", max(1, hint))

    def _auto_path_candidates(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            payload = self._graph_expand(
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
            search = self._ci_search(limit=5)
            for entry in search:
                if entry["ci_code"] == detail["ci_code"] or entry["ci_id"] in seen:
                    continue
                candidates.append(entry)
                seen.add(entry["ci_id"])
        return candidates[:5]

    def _path_target_next_actions(self, candidates: List[Dict[str, Any]]) -> List[NextAction]:
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
                        "patch": {
                            "auto": {
                                "path": {"target_ci_code": ci_code}
                            }
                        }
                    },
                }
            )
        return actions

    def _auto_metric_candidate_blocks(self, detail: Dict[str, Any]) -> tuple[List[Block], Dict[str, Any]]:
        rows: List[List[str]] = []
        candidates: List[Dict[str, Any]] = []
        highlights: List[Dict[str, Any]] = []
        for metric_name, agg in AUTO_METRIC_PREFERENCES:
            entry: Dict[str, Any] = {"metric": metric_name}
            if not metric_tools.metric_exists(self.tenant_id, metric_name):
                entry["available"] = False
                candidates.append(entry)
                continue
            try:
                aggregate = self._metric_aggregate(
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
                if value is not None and not self.metric_context:
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        numeric = None
                    self.metric_context = {
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
                candidates.append({"metric": metric_name, "status": "error", "error": str(exc)})
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

    def _run_auto_metrics(self, detail: Dict[str, Any], auto_spec: AutoSpec) -> tuple[List[Block], Dict[str, Any]]:
        if not auto_spec.include_metric:
            return [], {"status": "disabled"}
        if self.plan.metric:
            blocks = self._metric_blocks(detail)
            status = {
                "status": "spec",
                "metric": self.plan.metric.metric_name,
                "mode": self.plan.metric.mode,
            }
            highlights: List[Dict[str, Any]] = []
            if self.metric_context and self.metric_context.get("value") is not None:
                highlights.append(
                    {
                        "label": f"{self.metric_context['metric_name']} {self.metric_context['agg']} ({self.metric_context['time_range']})",
                        "value": self.metric_context["value"],
                    }
                )
            if highlights:
                status["highlights"] = highlights
            return blocks, status
        return self._auto_metric_candidate_blocks(detail)

    def _run_auto_history(self, detail: Dict[str, Any]) -> tuple[List[Block], Dict[str, Any]]:
        if not self.plan.history or not self.plan.history.enabled:
            return [], {"status": "disabled"}
        try:
            blocks = self._history_blocks(detail)
            rows = self.history_context.get("rows") if self.history_context else None
            status = {
                "status": "ok",
                "rows": rows,
            }
            return blocks, status
        except Exception as exc:
            return [text_block(f"History retrieval failed: {exc}", title="AUTO History")], {
                "status": "fail",
                "error": str(exc),
            }

    def _auto_graph_scope_sections(
        self,
        detail: Dict[str, Any],
        auto_spec: AutoSpec,
        graph_payloads: Dict[str, Dict[str, Any]],
    ) -> tuple[List[Block], Dict[str, Any]]:
        spec = auto_spec.graph_scope
        eligible_view = next((view for view in auto_spec.views if view in {View.DEPENDENCY, View.IMPACT}), None)
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
                if not metric_tools.metric_exists(self.tenant_id, metric_name):
                    entry["available"] = False
                    entries.append(entry)
                    continue
                try:
                    aggregate = self._metric_aggregate(
                        metric_name,
                        agg,
                        "last_24h",
                        ci_ids=ci_ids,
                    )
                    value = aggregate.get("value")
                    rows.append(
                        [
                            aggregate["metric_name"],
                            aggregate["agg"],
                            str(value if value is not None else "<null>"),
                            aggregate["time_range"],
                            str(aggregate.get("ci_count_used")),
                        ]
                    )
                    entries.append({"metric": metric_name, "status": "ok"})
                except Exception as exc:
                    entries.append({"metric": metric_name, "status": "error", "error": str(exc)})
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
            result = self._history_recent(
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
                        "ci_ids_truncated": result.get("meta", {}).get("ci_ids_truncated"),
                        "rows": len(result.get("rows", [])),
                    }
                )
            else:
                warnings = result.get("warnings", [])
                message = (
                    f"Graph-scope events unavailable: {'; '.join(warnings)}" if warnings else "Graph-scope events unavailable"
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
            trace["status"] = "ok" if any(status == "ok" for status in statuses if status) else "partial"
        else:
            trace["status"] = "disabled"
        label_parts = []
        if spec.include_metric:
            label_parts.append("metrics")
        if spec.include_history:
            label_parts.append("history")
        trace["label"] = ", ".join(label_parts) if label_parts else "disabled"
        return [*metric_blocks, *history_blocks], trace

    def _build_auto_insights(self, detail: Dict[str, Any], auto_trace: Dict[str, Any], summary_text: str) -> List[Block]:
        blocks: List[Block] = [text_block(summary_text, title="AUTO Insights")]
        views = auto_trace.get("views") or []
        primary = next((entry for entry in views if entry.get("status") == "ok"), views[0] if views else {})
        if primary:
            view_label = primary.get("view", "N/A")
            node_count = primary.get("node_count")
            depth = primary.get("depth")
            if node_count is not None:
                blocks.append(number_block("Graph nodes", node_count, title=f"{view_label} view"))
            if depth is not None:
                blocks.append(number_block("Graph depth", depth))
        history_rows = auto_trace.get("history", {}).get("rows")
        if history_rows is not None:
            blocks.append(number_block("Recent events (7d)", history_rows))
        metric_highlights = auto_trace.get("metrics", {}).get("highlights", [])
        if self.metric_context and self.metric_context.get("value") is not None:
            metric_highlights = [
                {
                    "label": f"{self.metric_context['metric_name']} {self.metric_context['agg']} ({self.metric_context['time_range']})",
                    "value": self.metric_context["value"],
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
            blocks.append(text_block(f"CEP simulate rule {exec_id} ({status})", title="CEP Insights"))
        return blocks

    def _build_auto_quality(self, auto_trace: Dict[str, Any]) -> tuple[List[Block], Dict[str, Any]]:
        blocks: List[Block] = []
        policy_decisions = self.plan_trace.get("policy_decisions", {})
        requested_depth = policy_decisions.get("requested_depth")
        clamped_depth = policy_decisions.get("clamped_depth")
        policy_clamped = False
        if requested_depth is not None and clamped_depth is not None and requested_depth != clamped_depth:
            policy_clamped = True
        graph_truncated = any(entry.get("truncated") for entry in auto_trace.get("views", []))
        graph_scope = auto_trace.get("graph_scope", {})
        if graph_scope.get("ci_ids_truncated"):
            graph_truncated = True
        metric_status = auto_trace.get("metrics", {}).get("status")
        metric_fallback = metric_status == "missing"
        metric_missing = self.plan.auto.include_metric and metric_status != "ok"
        history_status = auto_trace.get("history", {}).get("status")
        history_missing = self.plan.auto.include_history and history_status != "ok"
        cep_trace = self.plan_trace.get("cep", {}) or {}
        cep_error = bool(cep_trace.get("error")) or ("condition_evaluated" not in cep_trace.get("result", {}) and self.plan.cep and self.plan.cep.rule_id)
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
        blocks.append(number_block("Confidence", round(confidence, 2), title="Quality signal"))
        quality_trace = {
            "confidence": round(confidence, 2),
            "confidence_reasons": conf_reasons,
            "signals": signals,
            "warnings": warnings,
        }
        return blocks, quality_trace

    def _recommend_auto_actions(self, auto_trace: Dict[str, Any], detail: Dict[str, Any]) -> tuple[List[NextAction], List[Dict[str, str]]]:
        recommended: List[NextAction] = []
        reasons: List[Dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        def enqueue(action: NextAction, reason: str) -> None:
            if len(recommended) >= 5:
                return
            key = (action.get("type"), action.get("label"))
            if key in seen:
                return
            seen.add(key)
            recommended.append(action)
            reasons.append({"type": action.get("type"), "label": action.get("label"), "reason": reason})

        path_trace = auto_trace.get("path", {})
        if path_trace.get("status") == "awaiting_target":
            target_actions = [act for act in self.next_actions if "(target)" in act.get("label", "")]
            for action in target_actions:
                enqueue(action, "Choose a target CI for PATH")
        for entry in auto_trace.get("views", []):
            if entry.get("truncated"):
                current_depth = (entry.get("depth") or self.plan.graph.depth or 2) + 1
                payload: RerunPayload = {"patch": {"graph": {"depth": current_depth, "view": entry.get("view")}}}
                enqueue(
                    {
                        "type": "rerun",
                        "label": f"Depth +1 ({entry.get('view')})",
                        "payload": payload,
                    },
                    "Graph truncated; dig deeper",
                )
        present_views = {entry.get("view") for entry in auto_trace.get("views", []) if entry.get("view")}
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
                {"type": "rerun", "label": "Metric time_range: 최근 24시간", "payload": payload},
                "Refresh metrics with recent window",
            )
        history_trace = auto_trace.get("history", {})
        history_limit = self.plan.history.limit or 20
        history_rows = history_trace.get("rows")
        if history_rows and history_limit < 50 and history_rows >= history_limit:
            payload = {"patch": {"history": {"limit": min(history_limit + 10, 50)}}}
            enqueue(
                {"type": "rerun", "label": "History limit +10", "payload": payload},
                "More history rows available",
            )
        cep_info = auto_trace.get("cep", {})
        for action in self.next_actions:
            if action.get("type") == "open_event_browser":
                enqueue(action, "Open the CEP event browser for this run")
                break
        if cep_info.get("include_cep_requested") and not cep_info.get("rule_id"):
            sample = f"{detail.get('ci_code')} rule <uuid> simulate"
            enqueue(
                {"type": "copy_payload", "label": "Rule simulate sample", "payload": sample},
                "Add a rule ID to trigger CEP simulate",
            )
        return recommended, reasons

    def _insert_recommended_actions(self, recommended: List[NextAction]) -> None:
        prioritized: List[NextAction] = []
        for rec in recommended:
            match = None
            for action in self.next_actions:
                if action.get("label") == rec.get("label"):
                    match = action
                    break
            if match:
                self.next_actions.remove(match)
                prioritized.append(match)
            else:
                prioritized.append(rec)
        self.next_actions = prioritized + self.next_actions

    def _handle_aggregate(self) -> tuple[List[Block], str]:
        agg_filters = [filter.dict() for filter in self.plan.aggregate.filters]
        agg = self._ci_aggregate(
            self.plan.aggregate.group_by,
            self.plan.aggregate.metrics,
            filters=agg_filters or None,
            top_n=self.plan.aggregate.top_n,
        )
        blocks: List[Block] = []
        total_count = agg.get("total_count")
        if isinstance(total_count, int):
            blocks.append(response_builder.build_aggregate_summary_block(total_count))
            self.aggregation_summary = {
                "total_count": total_count,
                "group_by": list(self.plan.aggregate.group_by),
            }
        block = response_builder.build_aggregate_block(agg)
        blocks.append(block)
        query = agg.get("query")
        params = agg.get("params")
        if query and params is not None:
            blocks.append(response_builder.build_sql_reference_block(query, params))
        answer = f"Aggregated {len(agg.get('rows', []))} groups"
        blocks.extend(self._build_list_preview_blocks())
        return blocks, answer

    def _handle_list_preview(self) -> tuple[List[Block], str]:
        blocks = self._build_list_preview_blocks()
        if not blocks:
            return [text_block("No CI entries found", title="CI list preview")], "CI list preview"
        return blocks, "CI list preview"

    def _build_list_preview_blocks(self) -> List[Block]:
        if not self.plan.list.enabled:
            return []
        spec = self.plan.list
        filters = [filter.dict() for filter in self.plan.primary.filters]
        preview = self._ci_list_preview(limit=spec.limit, offset=spec.offset, filters=filters)
        rows = preview.get("rows", [])
        columns = ["ci_id", "ci_code", "ci_name", "ci_type", "ci_subtype", "status", "owner", "location", "created_at"]
        table_rows = [[str(row.get(col) or "") for col in columns] for row in rows]
        block = table_block(columns, table_rows, title="CI 목록 (미리보기)", block_id="ci-list-preview")
        meta = block.get("meta", {})
        meta.update(
            {
                "limit": preview.get("limit"),
                "offset": preview.get("offset"),
                "total": preview.get("total"),
            }
        )
        block["meta"] = meta
        blocks: List[Block] = [block]
        total = preview.get("total")
        if isinstance(total, int):
            shown = len(rows)
            blocks.append(
                text_block(f"총 {total}개 중 {shown}개 표시", title="CI 목록 힌트")
            )
            offset = preview.get("offset", 0)
            limit = preview.get("limit", spec.limit)
            has_more = offset + limit < total
            has_prev = offset > 0
            start = offset + 1 if total > 0 else 0
            end = offset + shown
            self.list_paging_info = {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "has_prev": has_prev,
                "page_range": [start, end],
            }
            if has_more:
                payload: RerunPayload = {"patch": {"list": {"offset": offset + limit}}}
                self.next_actions.append(
                    {
                        "type": "rerun",
                        "label": f"다음 {limit}개",
                        "payload": payload,
                    }
                )
            if has_prev:
                prev_offset = max(0, offset - limit)
                payload = {"patch": {"list": {"offset": prev_offset}}}
                self.next_actions.append(
                    {
                        "type": "rerun",
                        "label": f"이전 {limit}개",
                        "payload": payload,
                    }
                )
                if offset != 0:
                    payload = {"patch": {"list": {"offset": 0}}}
                    self.next_actions.append(
                        {
                            "type": "rerun",
                            "label": "처음으로",
                            "payload": payload,
                        }
                    )
        return blocks

    def _apply_list_trace(self, trace: Dict[str, Any]) -> None:
        if not self.plan.list.enabled or not self.list_paging_info:
            return
        list_trace = trace.setdefault("list", {})
        list_trace.update(self.list_paging_info)

    def _handle_path(self) -> tuple[List[Block], str]:
        source_keywords = self.plan.primary.keywords
        target_keywords = self.plan.secondary.keywords or source_keywords
        search_limit = max(2, self.plan.primary.limit)
        source, source_blocks, source_message = self._resolve_path_endpoint(
            role="source",
            keywords=source_keywords,
            limit=search_limit,
        )
        if source_blocks:
            return source_blocks, source_message or "Multiple source candidates"
        target, target_blocks, target_message = self._resolve_path_endpoint(
            role="target",
            keywords=target_keywords,
            limit=search_limit,
        )
        if target_blocks:
            return target_blocks, target_message or "Multiple target candidates"
        path_payload = self._graph_path(source["ci_id"], target["ci_id"], self.plan.graph.depth)
        blocks = response_builder.build_path_blocks(path_payload)
        answer = f"Path from {source['ci_code']} to {target['ci_code']}"
        self.next_actions.extend(
            self._graph_next_actions(
                (self.plan.view or View.PATH).value,
                self.plan.graph.depth,
                path_payload.get("truncated", False),
            )
        )
        return blocks, answer

    def _resolve_ci_detail(
        self,
        role: str = "primary",
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]] | None, str | None]:
        if role == "primary" and self.rerun_context.selected_ci_id:
            detail = self._ci_get(self.rerun_context.selected_ci_id)
            if not detail:
                message = f"CI {self.rerun_context.selected_ci_id} not found."
                return None, [text_block(message)], message
            return detail, None, None
        requested_keywords = list(self.plan.primary.keywords)
        if not requested_keywords:
            secondary_ids = self._extract_ci_identifiers(self.plan.secondary.keywords or [])
            if secondary_ids:
                requested_keywords = secondary_ids
        search_keywords, sanitized_source, before_keywords = self._build_ci_search_keywords()
        self.plan_trace.setdefault("keywords_sanitized", {})
        self.plan_trace["keywords_sanitized"].update(
            {"before": before_keywords, "after": search_keywords, "source": sanitized_source}
        )
        ci_search_trace = self.plan_trace.setdefault("ci_search_trace", [])
        ci_search_trace.append({"stage": "initial", "keywords": search_keywords, "source": sanitized_source})
        candidates = self._ci_search(
            keywords=search_keywords,
            filters=[filter.dict() for filter in self.plan.primary.filters],
            limit=self.plan.primary.limit,
        )
        ci_search_trace[-1]["row_count"] = len(candidates)
        if not candidates:
            candidates = self._ci_search_broad_or(
                keywords=search_keywords,
                filters=[filter.dict() for filter in self.plan.primary.filters],
                limit=10,
            )
            ci_search_trace.append({"stage": "broad_or", "keywords": search_keywords})
        if not candidates:
            message = "No CI matches found."
            history_fallback = self._history_fallback_for_question()
            if history_fallback:
                blocks, hist_message = history_fallback
                return None, blocks, hist_message
            return None, [text_block(message, title="Lookup")], message
        if len(candidates) > 1:
            exact = _find_exact_candidate(candidates, search_keywords)
            if exact:
                self.logger.info(
                    "ci.runner.ci_search_exact_match",
                    extra={"ci_id": exact.get("ci_id"), "ci_code": exact.get("ci_code")},
                )
                self.logger.info(
                    "ci.resolve.debug",
                    extra={
                        "keywords": search_keywords,
                        "row_count": len(candidates),
                        "exact_ci_id": exact.get("ci_id"),
                        "exact_ci_code": exact.get("ci_code"),
                    },
                )
                detail = self._ci_get(exact["ci_id"])
                if not detail:
                    message = f"CI {exact.get('ci_code') or exact['ci_id']} not found."
                    return None, [text_block(message)], message
                return detail, None, None
            self._register_ambiguous_candidates(candidates, "primary")
            self.next_actions.extend(
                self._candidate_next_actions(candidates, use_secondary=False, role="primary")
            )
            table = response_builder.build_candidate_table(candidates, role="primary")
            return None, [text_block("Multiple candidates found"), table], "Multiple CI candidates"
        detail = self._ci_get(candidates[0]["ci_id"])
        if not detail:
            message = f"CI {candidates[0]['ci_code']} not found."
            return None, [text_block(message)], message
        return detail, None, None

    def _history_fallback_for_question(self) -> tuple[List[Dict[str, Any]], str] | None:
        text = (self.question or "").lower()
        if not any(keyword in text for keyword in HISTORY_FALLBACK_KEYWORDS):
            return None
        try:
            history = history_tools.recent_work_and_maintenance(
                self.tenant_id,
                "last_7d",
                limit=50,
            )
        except Exception as exc:
            self.logger.debug("ci.runner.history_fallback_failed", exc_info=exc)
            return [text_block("전체 이력 조회에 실패했습니다. 이력 탭을 이용해주세요.", title="History fallback")], "History fallback failed"
        work_rows = history.get("work_rows", [])
        maint_rows = history.get("maint_rows", [])
        types = history_tools.detect_history_sections(self.question)
        fallback_blocks: List[Dict[str, Any]] = [text_block("CI 없이 전체 이력을 가져왔습니다.", title="History fallback")]
        if "work" in types or not types:
            fallback_blocks.append(
                table_block(
                    ["start_time", "ci_code", "ci_name", "work_type", "impact_level", "result", "summary"],
                    [
                        [
                            str(row[0]),
                            row[1] or "-",
                            row[2] or "-",
                            row[3],
                            str(row[4]),
                            row[5] or "",
                            row[6] or "",
                        ]
                        for row in work_rows
                    ]
                    or [["데이터 없음", "-", "-", "-", "-", "-", "-"]],
                    title="Work history (최근 7일)",
                )
            )
        if "maintenance" in types or not types:
            fallback_blocks.append(
                table_block(
                    ["start_time", "ci_code", "ci_name", "maint_type", "duration_min", "result", "summary"],
                    [
                        [
                            str(row[0]),
                            row[1] or "-",
                            row[2] or "-",
                            row[3],
                            str(row[4]),
                            row[5] or "",
                            row[6] or "",
                        ]
                        for row in maint_rows
                    ]
                    or [["데이터 없음", "-", "-", "-", "-", "-", "-"]],
                    title="Maintenance history (최근 7일)",
                )
            )
        return fallback_blocks, "History fallback executed"

    def _resolve_path_endpoint(
        self,
        role: str,
        keywords: List[str],
        limit: int,
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]] | None, str | None]:
        selected_id = (
            self.rerun_context.selected_ci_id if role == "source" else self.rerun_context.selected_secondary_ci_id
        )
        if selected_id:
            detail = self._ci_get(selected_id)
            if not detail:
                message = f"CI {selected_id} not found."
                return None, [text_block(message)], message
            return detail, None, None
        candidates = self._ci_search(keywords=keywords, limit=limit)
        if not candidates:
            message = f"Unable to resolve {role} endpoint."
            return None, [text_block(message)], message
        if len(candidates) > 1:
            self._register_ambiguous_candidates(candidates, role)
            use_secondary = role != "source"
            self.next_actions.extend(self._candidate_next_actions(candidates, use_secondary=use_secondary, role=role))
            table = response_builder.build_candidate_table(candidates, role=role)
            label = f"Multiple {role} candidates"
            return None, [text_block(label), table], label
        return candidates[0], None, None

    def _register_ambiguous_candidates(self, candidates: List[Dict[str, Any]], role: str) -> None:
        self.plan_trace["ambiguous"] = True
        roles = self.plan_trace.setdefault("ambiguous_roles", [])
        if role not in roles:
            roles.append(role)
        entries = self.plan_trace.setdefault("candidates", [])
        entries.append({"role": role, "items": candidates})

    def _finalize_next_actions(self) -> List[NextAction]:
        actions = list(self.next_actions)
        actions.append({"type": "open_trace", "label": "Trace details"})
        return actions

    def _candidate_next_actions(
        self,
        candidates: List[Dict[str, Any]],
        use_secondary: bool,
        role: str,
    ) -> List[NextAction]:
        actions: List[NextAction] = []
        for candidate in candidates:
            payload: RerunPayload = {}
            if use_secondary:
                payload["selected_secondary_ci_id"] = candidate["ci_id"]
            else:
                payload["selected_ci_id"] = candidate["ci_id"]
            actions.append(
                {
                    "type": "rerun",
                    "label": f"{candidate['ci_code']} 선택 ({role})",
                    "payload": payload,
                }
            )
        return actions

    def _metric_blocks(self, detail: Dict[str, Any], graph_payload: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        metric_spec = self.plan.metric
        if not metric_spec:
            return []
        metric_trace = self.plan_trace.setdefault("metric", {})
        if not metric_tools.metric_exists(self.tenant_id, metric_spec.metric_name):
            metric_trace.update({"status": "missing", "requested": metric_spec.dict()})
            candidates = metric_tools.list_metric_names(self.tenant_id)
            rows = [[name] for name in candidates]
            blocks = [
                text_block(f"Metric '{metric_spec.metric_name}' not found", title="Metric lookup"),
                table_block(["metric_name"], rows, title="Available metrics"),
            ]
            self._log_metric_blocks_return(blocks)
            return blocks
        if metric_spec.scope == "graph":
            return self._graph_metric_blocks(detail, metric_spec, metric_trace, graph_payload=graph_payload)
        if metric_spec.mode == "series":
            series = self._metric_series_table(
                detail["ci_id"],
                metric_spec.metric_name,
                metric_spec.time_range,
            )
            rows = [list(row) for row in series["rows"]]
            metric_trace.update(
                {
                    "status": "series",
                    "requested": metric_spec.dict(),
                    "rows": len(rows),
                }
            )
            self.next_actions.extend(self._metric_next_actions(metric_spec.time_range))
            if not rows:
                ci_code = detail.get("ci_code") or detail.get("ci_id") or "unknown"
                reason = (
                    f"{metric_spec.metric_name} ({metric_spec.time_range}) returned no data "
                    f"for CI {ci_code}"
                )
                blocks = [
                    text_block(reason, title="Metric data unavailable"),
                    table_block(
                        ["metric", "time_range", "ci_code"],
                        [[metric_spec.metric_name, metric_spec.time_range, ci_code]],
                        title="Metric request details",
                    ),
                ]
                self._log_metric_blocks_return(blocks)
                return blocks
            table_block_rows = table_block(["ts", "value"], rows, title="Metric series")
            chart = None
            try:
                chart = self._series_chart_block(detail, metric_spec, rows)
                if chart:
                    metric_trace.setdefault("chart", {})["rendered"] = True
            except Exception as exc:  # pragma: no cover
                metric_trace.setdefault("chart", {}).setdefault("warnings", []).append(str(exc))
                chart = None
            blocks: List[Dict[str, Any]] = []
            if chart:
                blocks.append(chart)
            blocks.append(table_block_rows)
            if rows:
                latest = rows[0]
                self.metric_context = {
                    "metric_name": metric_spec.metric_name,
                    "time_range": metric_spec.time_range,
                    "agg": metric_spec.agg,
                    "value": float(latest[1]) if len(latest) > 1 and latest[1] not in (None, "<null>") else None,
                }
            return blocks
        aggregate = self._metric_aggregate(
            metric_spec.metric_name,
            metric_spec.agg,
            metric_spec.time_range,
            detail["ci_id"],
        )
        metric_trace.update(
            {
                "status": "aggregate",
                "requested": metric_spec.dict(),
                "result": aggregate,
            }
        )
        self.next_actions.extend(self._metric_next_actions(metric_spec.time_range))
        rows = [
            [
                aggregate["metric_name"],
                aggregate["agg"],
                aggregate["time_from"],
                aggregate["time_to"],
                str(aggregate["value"]) if aggregate["value"] is not None else "<null>",
            ]
        ]
        self.metric_context = {
            "metric_name": aggregate["metric_name"],
            "time_range": aggregate["time_range"],
            "agg": aggregate["agg"],
            "value": aggregate.get("value"),
        }
        blocks = [table_block(["metric_name", "agg", "time_from", "time_to", "value"], rows, title="Metric aggregate")]
        self._log_metric_blocks_return(blocks)
        return blocks

    def _graph_metric_blocks(
        self,
        detail: Dict[str, Any],
        metric_spec: MetricSpec,
        metric_trace: Dict[str, Any],
        graph_payload: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        graph_view = self.plan.graph.view or (self.plan.view or View.DEPENDENCY)
        graph_depth = self.plan.graph.depth
        graph_limits = self.plan.graph.limits.dict()
        if not graph_payload:
            graph_payload = self._graph_expand(detail["ci_id"], graph_view.value, graph_depth, graph_limits)
        node_ids = graph_payload.get("ids") or [detail["ci_id"]]
        aggregate = self._metric_aggregate(
            metric_spec.metric_name,
            metric_spec.agg,
            metric_spec.time_range,
            ci_ids=node_ids,
        )
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
                str(aggregate["value"]) if aggregate["value"] is not None else "<null>",
            ]
        ]
        self.next_actions.extend(
            self._graph_metric_next_actions(
                graph_view.value,
                depth_applied,
                truncated,
                metric_spec,
            )
        )
        title = f"Graph metric ({metric_spec.metric_name})"
        return [
            table_block(
                ["scope", "view", "depth", "ci_count", "metric_name", "agg", "time_from", "time_to", "value"],
                rows,
                title=title,
            )
        ]

    def _metric_next_actions(self, current_range: str) -> List[NextAction]:
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

    def _graph_metric_next_actions(
        self, graph_view: str, depth: int, truncated: bool, metric_spec: MetricSpec
    ) -> List[NextAction]:
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
                            "patch": {"view": target_view, "graph": {"view": target_view}}
                        },
                    }
                )
        return actions

    def _series_chart_block(
        self, detail: Dict[str, Any], metric_spec: MetricSpec, rows: List[List[str]]
    ) -> Dict[str, Any] | None:
        if len(rows) <= 1:
            return None
        parsed_points: List[tuple[str, float]] = []
        for row in rows:
            if len(row) < 2:
                continue
            timestamp = row[0]
            try:
                value = float(row[1])
            except (TypeError, ValueError):
                continue
            if not timestamp or value != value:
                continue
            parsed_points.append((timestamp, value))
        if len(parsed_points) <= 1:
            return None
        parsed_points.sort(key=lambda entry: entry[0])
        series_points = [[timestamp, value] for timestamp, value in parsed_points]
        chart_series = [
            {
                "name": metric_spec.metric_name,
                "points": series_points,
            }
        ]
        meta = {
            "ci_id": detail.get("ci_id"),
            "metric_name": metric_spec.metric_name,
            "time_range": metric_spec.time_range,
        }
        title = f"{metric_spec.metric_name} ({metric_spec.time_range})"
        return chart_block(title + " trend", "timestamp", chart_series, meta)

    def _graph_history_next_actions(
        self, history_spec: Any, graph_view: str, depth: int, truncated: bool
    ) -> List[NextAction]:
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
                    "payload": {"patch": {"graph": {"depth": depth + 1, "view": graph_view}}},
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

    def _graph_next_actions(self, view: str, depth: int, truncated: bool) -> List[NextAction]:
        actions: List[NextAction] = []
        if truncated:
            actions.append(
                {
                    "type": "rerun",
                    "label": "depth +1",
                    "payload": {"patch": {"graph": {"depth": depth + 1}}},
                }
            )
        for target_view in ["COMPOSITION", "DEPENDENCY", "IMPACT", "NEIGHBORS"]:
            if target_view != view:
                actions.append(
                    {
                        "type": "rerun",
                        "label": f"View {target_view}로 보기",
                        "payload": {"patch": {"view": target_view}},
                    }
                )
        actions.append(
            {
                "type": "rerun",
                "label": "집계: ci_subtype",
                "payload": {"patch": {"aggregate": {"group_by": ["ci_subtype"], "top_n": 10}}},
            }
        )
        return actions

    def _history_blocks(self, detail: Dict[str, Any], graph_payload: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        history_spec = self.plan.history
        if not history_spec or not history_spec.enabled:
            return []
        history_trace = self.plan_trace.setdefault("history", {})
        history_trace["requested"] = history_spec.dict()
        if history_spec.scope == "graph":
            return self._graph_history_blocks(detail, history_spec, history_trace, graph_payload=graph_payload)
        return self._ci_history_blocks(detail, history_spec, history_trace)

    def _ci_history_blocks(
        self,
        detail: Dict[str, Any],
        history_spec: Any,
        history_trace: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        result = self._history_recent(
            history_spec,
            {"ci_id": detail["ci_id"], "ci_code": detail.get("ci_code")},
        )
        if not result.get("available"):
            history_trace["available"] = False
            warnings = result.get("warnings", [])
            if warnings:
                history_trace.setdefault("warnings", []).extend(warnings)
            message = f"event_log unavailable: {'; '.join(warnings)}" if warnings else "event_log unavailable"
            return [text_block(message, title="History")]
        history_trace["available"] = True
        history_meta = result.get("meta", {})
        history_trace["meta"] = history_meta
        history_trace["rows"] = len(result.get("rows", []))
        self.history_context = {
            "time_range": history_spec.time_range,
            "source": history_spec.source,
            "rows": len(result.get("rows", [])),
            "recent": self._format_history_recent(result.get("rows", [])),
        }
        self.next_actions.extend(self._history_time_actions(history_spec.time_range))
        title = f"Recent events ({history_spec.time_range})"
        return [table_block(result["columns"], result["rows"], title=title)]

    def _graph_history_blocks(
        self,
        detail: Dict[str, Any],
        history_spec: Any,
        history_trace: Dict[str, Any],
        graph_payload: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        graph_view = self.plan.graph.view or (self.plan.view or View.DEPENDENCY)
        graph_depth = self.plan.graph.depth
        graph_limits = self.plan.graph.limits.dict()
        if not graph_payload:
            graph_payload = self._graph_expand(detail["ci_id"], graph_view.value, graph_depth, graph_limits)
        node_ids = graph_payload.get("ids") or [detail["ci_id"]]
        result = self._history_recent(
            history_spec,
            {"ci_id": detail["ci_id"], "ci_code": detail.get("ci_code")},
            ci_ids=node_ids,
        )
        if not result.get("available"):
            history_trace["available"] = False
            warnings = result.get("warnings", [])
            if warnings:
                history_trace.setdefault("warnings", []).extend(warnings)
            message = f"event_log unavailable: {'; '.join(warnings)}" if warnings else "event_log unavailable"
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
        self.next_actions.extend(
            self._graph_history_next_actions(
                history_spec,
                graph_view.value,
                depth_applied,
                truncated,
            )
        )
        title = (
            f"Recent events (graph scope, {graph_view.value}, depth={depth_applied}, {history_spec.time_range})"
        )
        self.history_context = {
            "time_range": history_spec.time_range,
            "source": self._history_context_source(history_spec),
            "rows": len(result.get("rows", [])),
            "recent": self._format_history_recent(result.get("rows", [])),
        }
        return [table_block(result["columns"], result["rows"], title=title)]

    def _cep_blocks(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        cep_spec = self.plan.cep
        if not cep_spec or cep_spec.mode != "simulate":
            return []
        cep_trace = self.plan_trace.setdefault("cep", {})
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
        metric_ctx = self.metric_context
        history_ctx = self.history_context
        result = self._cep_simulate(cep_spec.rule_id, ci_context, metric_ctx, history_ctx)
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
        cep_trace["extracted_value_truncated"] = evidence_meta.get("extracted_value_truncated")
        runtime_params_meta = evidence_meta.get("runtime_params_meta")
        cep_trace["runtime_params_meta"] = runtime_params_meta
        cep_trace["runtime_params_keys"] = evidence_meta.get("runtime_params_keys")
        cep_trace["runtime_params_policy_source"] = evidence_meta.get("runtime_params_policy_source")
        cep_trace["test_payload_sections"] = evidence_meta.get("test_payload_sections")
        cep_trace["test_payload_metric_keys_present"] = evidence_meta.get("test_payload_metric_keys_present")
        cep_trace["test_payload_history_keys_present"] = evidence_meta.get("test_payload_history_keys_present")
        cep_trace["exec_log_id"] = result.get("exec_log_id")
        cep_trace["simulation_id"] = result.get("simulation_id")
        if not result.get("success"):
            cep_trace["error"] = result.get("error")
            message = result.get("error") or "Unknown CEP simulate failure"
            return [text_block(f"CEP simulate failed: {message}", title="CEP simulate")]
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
        title = "CEP simulate results"
        evidence = result.get("evidence") or {}
        evidence_title = "CEP simulate evidence"
        cep_evidence = result.get("evidence") or {}
        cep_trace["evidence"] = cep_evidence
        params_keys = evidence_meta.get("runtime_params_keys") or []
        params_display = ", ".join(params_keys)
        if len(params_display) > 200:
            params_display = params_display[:200] + "..."
        self.next_actions.append(
            {
                "type": "open_event_browser",
                "label": "Event Browser로 보기",
                "payload": {
                    "exec_log_id": result.get("exec_log_id"),
                    "simulation_id": result.get("simulation_id"),
                    "tenant_id": self.tenant_id,
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
                title=title,
            ),
            table_block(
                ["endpoint", "method", "value_path", "op", "threshold", "extracted_value", "evaluated", "status", "error", "params_keys"],
                [
                    [
                        evidence.get("runtime_endpoint"),
                        evidence.get("method"),
                        evidence.get("value_path"),
                        evidence.get("op"),
                        evidence.get("threshold"),
                        evidence.get("extracted_value"),
                        str(evidence.get("condition_evaluated")),
                        evidence.get("fetch_status"),
                        evidence.get("fetch_error"),
                        params_display,
                    ]
                ],
                title=evidence_title,
            ),
        ]

    def _history_time_actions(self, current_range: str) -> List[NextAction]:
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
                    "label": label,
                    "payload": {"patch": {"history": {"time_range": key}}},
                }
            )
        return actions

    def _format_history_recent(self, rows: List[List[str]]) -> List[Dict[str, str]]:
        recent = []
        for row in rows[:3]:
            ts = row[1] if len(row) > 1 else row[0]
            summary = row[-1] if row else ""
            recent.append(
                {"ts": ts, "summary": summary if isinstance(summary, str) else str(summary)}
            )
        return recent

    def _history_context_source(self, history_spec: Any) -> str:
        return history_spec.source if getattr(history_spec, "source", None) else "event_log"
