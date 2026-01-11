from __future__ import annotations

import json
import os
import re
from time import perf_counter
from typing import List, Set, Tuple

ISO_DATE_PATTERN = re.compile(r"(\d{4})[-년/\\.](\d{1,2})[-월/\\.](\d{1,2})")

from app.llm.client import get_llm_client
from app.modules.ops.services.ci.planner.plan_schema import (
    AutoGraphScopeSpec,
    AutoPathSpec,
    AutoSpec,
    CepSpec,
    FilterSpec,
    HistorySpec,
    Intent,
    MetricSpec,
    Plan,
    PlanMode,
    View,
    ListSpec,
)


def determine_output_types(text: str) -> Set[str]:
    normalized = text.lower()
    output_types: Set[str] = set()
    if any(keyword in normalized for keyword in NUMBER_KEYWORDS):
        output_types.add("number")
    if any(keyword in normalized for keyword in AGG_KEYWORDS):
        output_types.add("aggregate")
    if any(keyword in normalized for keyword in SERIES_KEYWORDS):
        output_types.add("chart")
    if any(keyword in normalized for keyword in LIST_KEYWORDS):
        output_types.add("table")
    if any(keyword in normalized for keyword in GRAPH_SCOPE_KEYWORDS):
        output_types.add("network")
    if not output_types:
        output_types.add("text")
    return output_types


OUTPUT_TYPE_PRIORITIES = ["chart", "table", "number", "network", "text"]


def _build_output_updates(output_types: Set[str]) -> dict[str, list[str] | str]:
    blocks: list[str] = [otype for otype in OUTPUT_TYPE_PRIORITIES if otype in output_types]
    if not blocks:
        blocks = ["text"]
    primary = blocks[0]
    return {"blocks": blocks, "primary": primary}


def derive_intent_from_output(output_types: Set[str]) -> Intent:
    if "network" in output_types:
        return Intent.PATH
    if "aggregate" in output_types or "number" in output_types:
        return Intent.AGGREGATE
    if "chart" in output_types:
        return Intent.AGGREGATE
    return Intent.LOOKUP


def _normalize_time_range(value: str | None) -> str:
    if not value:
        return "last_24h"
    trimmed = value.strip()
    match = ISO_DATE_PATTERN.search(trimmed)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    lower = trimmed.lower()
    if lower in TIME_RANGE_MAP:
        return TIME_RANGE_MAP[lower]
    for key, mapped in TIME_RANGE_MAP.items():
        if key in lower:
            return mapped
    if lower in {"last_1h", "last_24h", "last_7d"}:
        return lower
    return "last_24h"


def _metric_payload_to_spec(payload: dict[str, str] | None) -> MetricSpec | None:
    if not payload:
        return None
    name = payload.get("name")
    if not name:
        return None
    agg = payload.get("agg") or "avg"
    time_range = _normalize_time_range(payload.get("time_range"))
    mode = "aggregate"
    if payload.get("mode") in {"series", "aggregate"}:
        mode = payload["mode"]  # type: ignore
    return MetricSpec(metric_name=name, agg=agg, time_range=time_range, mode=mode)


def _build_output_parser_messages(text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": OUTPUT_SCHEMA_PROMPT},
        {
            "role": "user",
            "content": f"Question:\n```\n{text}\n```\nRespond only with a JSON object matching the schema above.",
        },
    ]


def _extract_json_block(text: str) -> str | None:
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else None


def _call_output_parser_llm(text: str) -> dict | None:
    try:
        llm = get_llm_client()
        start = perf_counter()
        response = llm.create_response(
            model=OUTPUT_PARSER_MODEL,
            input=_build_output_parser_messages(text),
            temperature=0,
            max_tokens=512,
        )
        elapsed = int((perf_counter() - start) * 1000)
        content = llm.get_output_text(response)
        logger.debug(
            "ci.planner.llm_response",
            extra={"model": OUTPUT_PARSER_MODEL, "response_preview": content[:400]},
        )
        logger.info(
            "ci.planner.llm_call",
            extra={
                "model": OUTPUT_PARSER_MODEL,
                "elapsed_ms": elapsed,
                "status": "ok",
            },
        )
        json_text = _extract_json_block(content)
        if not json_text:
            raise ValueError(
                f"LLM response missing JSON block: {content[:400]!r}"
            )
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM JSON parse error: {exc} | raw={json_text[:400]}") from exc
        return payload
    except Exception as exc:
        logger.warning("ci.planner.llm_fallback", extra={"error": str(exc)})
        return None

def is_metric_requested(text: str) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in METRIC_KEYWORDS)

import openai

from apps.api.core.logging import get_logger

TAG_FILTER_KEYS = {"system", "role", "runs_on", "host_server", "ci_subtype", "connected_servers"}
ATTR_FILTER_KEYS = {"engine", "version", "zone", "ip", "cpu_cores", "memory_gb"}
METRIC_ALIASES = {
    "cpu": "cpu_usage",
    "cpu_usage": "cpu_usage",
    "memory": "memory_usage",
    "memory_usage": "memory_usage",
    "disk": "disk_io",
    "disk_io": "disk_io",
    "network": "network_in",
    "network_in": "network_in",
    "temperature": "temperature",
    "latency": "cpu_usage",
    "응답시간": "cpu_usage",
    "response": "cpu_usage",
    "rps": "network_in",
    "error": "error",
}
METRIC_KEYWORDS = set(METRIC_ALIASES.keys()) | {"지표", "지수"}
TIME_RANGE_MAP = {
    "최근 1시간": "last_1h",
    "한시간": "last_1h",
    "최근 1시간": "last_1h",
    "최근 한시간": "last_1h",
    "최근 시간": "last_1h",
    "최근 24시간": "last_24h",
    "하루": "last_24h",
    "오늘": "last_24h",
    "24시간": "last_24h",
    "최근 하루": "last_24h",
    "최근 일주일": "last_7d",
    "지난주": "last_7d",
    "7일": "last_7d",
}
AGG_KEYWORDS = {
    "최대": "max",
    "maximum": "max",
    "max": "max",
    "최소": "min",
    "minimum": "min",
    "min": "min",
    "평균": "avg",
    "average": "avg",
    "avg": "avg",
    "count": "count",
    "건수": "count",
}
SERIES_KEYWORDS = {"추이", "시계열", "그래프", "trend", "series", "line", "chart"}
CI_CODE_PATTERN = re.compile(r"\b(?:sys|srv|app|was|storage|sec|db)[-\w]+\b", re.IGNORECASE)
LIST_KEYWORDS = {"list", "목록", "리스트", "show", "view", "전체", "목록을"}
NUMBER_KEYWORDS = {"얼마나", "숫자", "수치", "크다", "얼마나", "얼마", "몇", "count", "total"}
CEP_KEYWORDS = {"simulate", "시뮬", "시뮬레이션", "규칙", "rule", "cep"}
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

GRAPH_SCOPE_KEYWORDS = {
    "범위",
    "영향",
    "영향권",
    "주변",
    "연관",
    "관련",
    "의존",
    "dependency",
    "impact",
    "neighbors",
}
GRAPH_VIEW_KEYWORD_MAP = {
    "의존": View.DEPENDENCY,
    "dependency": View.DEPENDENCY,
    "주변": View.NEIGHBORS,
    "연관": View.NEIGHBORS,
    "관련": View.NEIGHBORS,
    "neighbors": View.NEIGHBORS,
    "영향": View.IMPACT,
    "impact": View.IMPACT,
    "영향권": View.IMPACT,
}
GRAPH_VIEW_DEFAULT_DEPTH = {
    View.DEPENDENCY: 2,
    View.NEIGHBORS: 1,
    View.IMPACT: 2,
}
GRAPH_DEPTH_PATTERN = re.compile(r"(\d+)\s*(?:단계|depth|깊이)")

AUTO_KEYWORDS = {"점검", "상태", "요약", "진단", "health", "overview", "status"}
AUTO_VIEW_PREFERENCES = [
    (["path", "경로", "연결"], [View.PATH]),
    (["의존", "dependency", "depends", "전원", "네트워크"], [View.DEPENDENCY]),
    (["영향", "impact", "영향권", "downstream"], [View.IMPACT]),
    (["구성", "component", "composition", "부품"], [View.COMPOSITION]),
    (["주변", "neighbor", "연관", "관련", "near"], [View.NEIGHBORS]),
]

CI_CODE_PATTERN = re.compile(r"\b(?:sys|srv|app|was|storage|sec|db)[-\w]+\b", re.IGNORECASE)
GRAPH_SCOPE_METRIC_KEYWORDS = {"cpu", "latency", "error", "성능", "rps", "response", "응답", "performance"}
GRAPH_SCOPE_VIEWS = {View.DEPENDENCY, View.IMPACT}
LIST_KEYWORDS = {
    "목록",
    "리스트",
    "list",
    "전체 목록",
    "나열",
    "보여줘",
    "뽑아",
    "뽑아줘",
    "추출",
    "가져와",
    "출력",
}
LIST_LIMIT_PATTERN = re.compile(r"(\d{1,3})\s*(?:개|건|items?|rows?)")
OUTPUT_PARSER_MODEL = os.environ.get("OPS_CI_OUTPUT_PARSER_MODEL", "gpt-4o-mini")
OUTPUT_SCHEMA_PROMPT = """
You are the OPS CI planner's output parser. Read the user's question and respond ONLY with the following JSON schema:
{
  "output_types": ["number","table","chart","network","text"],
  "ci_identifiers": ["ERP_OS_02"],
  "metric": {
    "name": "cpu_usage",
    "agg": "avg",
    "time_range": "2024-12-29",
    "mode": "aggregate"
  },
  "ambiguity": false,
  "list": { "enabled": false, "limit": 10, "offset": 0 }
}
- Always return JSON only, without markdown, bullet points, or text.
- Use null or empty arrays when the value is not applicable.
- output_types must list at least one element describing the requested blocks.
- ci_identifiers should include specifiers such as CI code/ci_name when available.
- metric must be null if there is no metric/history intent.
- LIST RULES:
  - If the question asks for a list such as “N개/몇 개/목록/리스트/나열/뽑아”, set list.enabled=true.
  - In list mode: output_types must be ["table"] and ci_identifiers may be [].
  - If N is present (e.g. 10개), set list.limit=N, otherwise default to 10.
"""

def _determine_intent(text: str) -> Intent:
    normalized = text.lower()
    if "path" in normalized or "경로" in normalized:
        return Intent.PATH
    if "카운트" in normalized or "몇" in normalized or "count" in normalized:
        return Intent.AGGREGATE
    if "확장" in normalized or "구성" in normalized or "component" in normalized:
        return Intent.EXPAND
    return Intent.LOOKUP


def _determine_view(text: str, intent: Intent) -> View:
    normalized = text.lower()
    if "impact" in normalized or "영향" in normalized:
        return View.IMPACT
    if "dependency" in normalized or "의존" in normalized:
        return View.DEPENDENCY
    if "composition" in normalized or "구성" in normalized:
        return View.COMPOSITION
    if intent == Intent.PATH:
        return View.PATH
    return View.SUMMARY


def _extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9가-힣\-_]+", text)
    return [token for token in tokens if len(token) > 1][:5]


def _extract_filters(text: str) -> List[FilterSpec]:
    filters: List[FilterSpec] = []
    for key, value in re.findall(r"(\w+)=([\w-]+)", text):
        normalized = key.lower()
        if normalized in TAG_FILTER_KEYS:
            filters.append(FilterSpec(field=f"tags.{normalized}", value=value))
        elif normalized in ATTR_FILTER_KEYS:
            filters.append(FilterSpec(field=f"attributes.{normalized}", value=value))
    return filters


def create_plan(question: str) -> Plan:
    normalized = question.strip()
    start = perf_counter()
    logger.info("ci.planner.start", extra={"query_len": len(normalized)})
    plan = Plan()
    plan.mode = _determine_mode(normalized)
    llm_payload = None
    try:
        llm_payload = _call_output_parser_llm(normalized)
    except Exception:  # pragma: no cover - placeholder
        llm_payload = None
    output_types: Set[str]
    ci_keywords: tuple[str, ...]
    if llm_payload:
        output_types = set(llm_payload.get("output_types") or ["text"])
        ci_keywords = tuple(llm_payload.get("ci_identifiers") or ())
    else:
        output_types = determine_output_types(normalized)
        ci_keywords = ()
    plan.intent = derive_intent_from_output(output_types)
    plan.view = _determine_view(normalized, plan.intent)

    if llm_payload and isinstance(llm_payload.get("list"), dict) and llm_payload["list"].get("enabled") is True:
        list_payload = llm_payload["list"]
        limit = list_payload.get("limit", 10)
        offset = list_payload.get("offset", 0)
        try:
            limit_int = int(limit)
        except Exception:
            limit_int = 10
        try:
            offset_int = int(offset)
        except Exception:
            offset_int = 0
        limit_int = max(1, min(50, limit_int))
        offset_int = max(0, min(5000, offset_int))
        plan.list = plan.list.copy(update={"enabled": True, "limit": limit_int, "offset": offset_int})
        plan.intent = Intent.LIST
        plan.output = plan.output.copy(update={"blocks": ["table"], "primary": "table"})
        plan.primary = plan.primary.copy(update={"keywords": []})
        plan.secondary = plan.secondary.copy(update={"keywords": []})
        logger.info(
            "ci.planner.llm.used",
            extra={"ci_identifiers": len(ci_keywords), "output_types": ",".join(sorted(output_types)), "list_enabled": True, "list_limit": limit_int},
        )
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "ci.planner.done",
            extra={
                "elapsed_ms": elapsed_ms,
                "intent": plan.intent.value if plan.intent else None,
                "view": plan.view.value if plan.view else None,
            },
        )
        return plan

    if ci_keywords:
        keywords = list(ci_keywords)
    else:
        keywords = _extract_keywords(normalized)
    plan.primary = plan.primary.copy(update={"keywords": keywords})
    parsed_filters = _extract_filters(normalized)
    if parsed_filters:
        plan.primary = plan.primary.copy(update={"filters": parsed_filters})
    secondary_text = normalized
    if plan.intent == Intent.PATH:
        left, right = _split_path_candidates(normalized)
        plan.primary = plan.primary.copy(update={"keywords": _extract_keywords(left)})
        secondary_text = right
    plan.secondary = plan.secondary.copy(update={"keywords": _extract_keywords(secondary_text)})
    if plan.intent == Intent.AGGREGATE:
        plan.aggregate = plan.aggregate.copy(
            update={"group_by": ["ci_type"], "metrics": ["count"], "top_n": 10}
        )
    if plan.intent == Intent.PATH:
        plan.graph = plan.graph.copy(update={"depth": 4})
    metric_spec = None
    if llm_payload:
        metric_spec = _metric_payload_to_spec(llm_payload.get("metric"))
        if metric_spec and "chart" in output_types and metric_spec.mode != "series":
            metric_spec = metric_spec.copy(update={"mode": "series"})
    if not metric_spec:
        metric_spec = _determine_metric_spec(normalized)
    if metric_spec:
        plan.metric = metric_spec
        if metric_spec.mode == "series" or "chart" in output_types:
            plan.intent = Intent.AGGREGATE
    history_spec = _determine_history_spec(normalized)
    if history_spec:
        plan.history = history_spec
    cep_spec = _determine_cep_spec(normalized)
    if cep_spec:
        plan.cep = cep_spec
    plan = _apply_ci_type_aggregation(plan, normalized)
    if not llm_payload:
        list_spec = _determine_list_spec(normalized)
        if list_spec:
            plan = plan.copy(update={"list": list_spec})
            plan.intent = Intent.LIST
            plan.primary = plan.primary.copy(update={"keywords": []})
    if plan.metric and _has_graph_scope_keyword(normalized):
        plan = _apply_graph_scope(plan, normalized)
    if plan.mode == PlanMode.AUTO:
        plan = plan.copy(update={"auto": _determine_auto_spec(normalized, plan)})
    plan = plan.copy(update={"output": plan.output.copy(update=_build_output_updates(output_types))})
    if llm_payload:
        logger.info("ci.planner.llm.used", extra={"ci_identifiers": len(ci_keywords), "output_types": ",".join(sorted(output_types)), "list_enabled": False})
    else:
        logger.info("ci.planner.llm.skipped", extra={"reason": "heuristic"})
    elapsed_ms = int((perf_counter() - start) * 1000)
    logger.info(
        "ci.planner.done",
        extra={
            "elapsed_ms": elapsed_ms,
            "intent": plan.intent.value if plan.intent else None,
            "view": plan.view.value if plan.view else None,
        },
    )
    return plan


def _split_path_candidates(text: str) -> Tuple[str, str]:
    for separator in ["와", "과", " and ", " to "]:
        if separator in text:
            left, right = text.split(separator, 1)
            return left.strip(), right.strip()
    return text, text


def _determine_metric_spec(text: str):
    normalized = text.lower()
    metric_name = None
    for alias in METRIC_KEYWORDS:
        if alias in normalized:
            metric_name = METRIC_ALIASES.get(alias, alias)
            break
    if not metric_name:
        return None
    time_range = next((value for key, value in TIME_RANGE_MAP.items() if key in normalized), "last_24h")
    agg = next((value for key, value in AGG_KEYWORDS.items() if key in normalized), "avg")
    mode = "series" if any(keyword in normalized for keyword in SERIES_KEYWORDS) else "aggregate"
    # default aggregate/series based on keywords
    return MetricSpec(metric_name=metric_name, agg=agg, time_range=time_range, mode=mode)


def _determine_list_spec(text: str) -> ListSpec | None:
    normalized = text.lower()
    match = LIST_LIMIT_PATTERN.search(normalized)
    has_hint = any(keyword in normalized for keyword in LIST_KEYWORDS)
    if not has_hint and not match:
        return None
    if not has_hint:
        # Heuristic: if the user asks for N items and mentions CI/names, treat as list.
        if "ci" not in normalized and "이름" not in normalized:
            return None
    limit = 10
    if match:
        limit = int(match.group(1))
    limit = max(1, min(50, limit))
    return ListSpec(enabled=True, limit=limit)


def _determine_type_aggregation(text: str) -> bool:
    normalized = text.lower()
    if not any(keyword in normalized for keyword in TYPE_AGG_KEYWORDS):
        return False
    if any(keyword in normalized for keyword in LIST_KEYWORDS):
        return False
    return True


def _apply_ci_type_aggregation(plan: Plan, text: str) -> Plan:
    if not _determine_type_aggregation(text):
        return plan
    if plan.intent == Intent.AGGREGATE and "ci_type" in plan.aggregate.group_by:
        return plan
    aggregate = plan.aggregate.copy(update={"group_by": ["ci_type"], "metrics": ["count"], "top_n": 10})
    return plan.copy(
        update={
            "intent": Intent.AGGREGATE,
            "aggregate": aggregate,
            "normalized_from": "ci_type_distinct",
            "normalized_to": "ci_type_aggregation",
        }
    )


def _determine_graph_view(text: str) -> View:
    normalized = text.lower()
    for keyword, view in GRAPH_VIEW_KEYWORD_MAP.items():
        if keyword in normalized:
            return view
    return View.DEPENDENCY


def _determine_graph_depth(text: str, view: View) -> int:
    match = GRAPH_DEPTH_PATTERN.search(text)
    if match:
        return max(1, int(match.group(1)))
    return GRAPH_VIEW_DEFAULT_DEPTH.get(view, GRAPH_VIEW_DEFAULT_DEPTH.get(View.DEPENDENCY, 2))


def _has_graph_scope_keyword(text: str) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in GRAPH_SCOPE_KEYWORDS)


def _apply_graph_scope(plan: Plan, text: str) -> Plan:
    graph_view = _determine_graph_view(text)
    depth = _determine_graph_depth(text, graph_view)
    metric_spec = plan.metric
    if not metric_spec:
        return plan
    updated_metric = metric_spec.copy(update={"scope": "graph", "mode": "aggregate"})
    return plan.copy(
        update={
            "metric": updated_metric,
            "view": graph_view,
            "graph": plan.graph.copy(update={"view": graph_view, "depth": depth}),
        }
    )


def _apply_graph_history_scope(plan: Plan, text: str) -> Plan:
    graph_view = _determine_graph_view(text)
    depth = _determine_graph_depth(text, graph_view)
    return plan.copy(
        update={
            "view": graph_view,
            "graph": plan.graph.copy(update={"view": graph_view, "depth": depth}),
        }
    )


def _determine_auto_views(text: str) -> List[View]:
    normalized = text.lower()
    selected: List[View] = []
    for keywords, view_candidates in AUTO_VIEW_PREFERENCES:
        if any(keyword in normalized for keyword in keywords):
            for view in view_candidates:
                if view not in selected:
                    selected.append(view)
                    if len(selected) >= 2:
                        break
        if len(selected) >= 2:
            break
    if not selected:
        selected = [View.NEIGHBORS]
    return selected[:2]


def _determine_auto_depth_hint(text: str) -> int | None:
    match = GRAPH_DEPTH_PATTERN.search(text)
    if match:
        return max(1, int(match.group(1)))
    return None


def _determine_auto_spec(text: str, plan: Plan) -> AutoSpec:
    normalized = text.lower()
    views = _determine_auto_views(normalized)
    depth_hint = _determine_auto_depth_hint(normalized)
    include_metric = bool(plan.metric) or any(keyword in normalized for keyword in METRIC_KEYWORDS)
    metric_mode = "series" if any(keyword in normalized for keyword in SERIES_KEYWORDS) else "aggregate"
    include_history = bool(plan.history.enabled) or any(keyword in normalized for keyword in HISTORY_KEYWORDS)
    include_cep = bool(plan.cep and plan.cep.rule_id) or any(keyword in normalized for keyword in CEP_KEYWORDS)
    return AutoSpec(
        views=views,
        depth_hint=depth_hint,
        include_metric=include_metric,
        metric_mode=metric_mode,
        include_history=include_history,
        include_cep=include_cep,
        path=_determine_auto_path_spec(normalized),
        graph_scope=_determine_graph_scope_spec(normalized, views),
    )


def _extract_ci_codes(text: str) -> List[str]:
    seen: List[str] = []
    for match in CI_CODE_PATTERN.finditer(text):
        value = match.group(0)
        if value not in seen:
            seen.append(value)
    return seen


def _determine_auto_path_spec(text: str) -> AutoPathSpec:
    codes = _extract_ci_codes(text)
    source = codes[0] if codes else None
    target = codes[1] if len(codes) > 1 else None
    return AutoPathSpec(source_ci_code=source, target_ci_code=target)


def _determine_graph_scope_spec(text: str, views: List[View]) -> AutoGraphScopeSpec:
    normalized = text.lower()
    has_scope_view = any(view in GRAPH_SCOPE_VIEWS for view in views)
    include_metric = has_scope_view and any(keyword in normalized for keyword in GRAPH_SCOPE_METRIC_KEYWORDS)
    include_history = has_scope_view and any(keyword in normalized for keyword in HISTORY_KEYWORDS)
    return AutoGraphScopeSpec(include_metric=include_metric, include_history=include_history)


HISTORY_KEYWORDS = {"이벤트", "알람", "로그", "event"}
HISTORY_TIME_MAP = {
    "24시간": "last_24h",
    "하루": "last_24h",
    "오늘": "last_24h",
    "7일": "last_7d",
    "일주일": "last_7d",
    "지난주": "last_7d",
    "30일": "last_30d",
    "한달": "last_30d",
}

TYPE_KEYWORDS = {"종류", "타입", "type", "category", "kind"}
TYPE_AGG_KEYWORDS = TYPE_KEYWORDS

logger = get_logger(__name__)


def _determine_history_spec(text: str):
    normalized = text.lower()
    if not any(keyword in normalized for keyword in HISTORY_KEYWORDS):
        return None
    time_range = "last_7d"
    for key, value in HISTORY_TIME_MAP.items():
        if key in normalized:
            time_range = value
            break
    limit = 50
    match = re.search(r"(\\d{1,3})\\s*개", normalized)
    if match:
        limit = min(200, max(1, int(match.group(1))))
    scope = "graph" if _has_graph_scope_keyword(normalized) else "ci"
    return HistorySpec(enabled=True, scope=scope, time_range=time_range, limit=limit)


def _determine_cep_spec(text: str) -> CepSpec | None:
    if not any(keyword in text.lower() for keyword in CEP_KEYWORDS):
        return None
    match = UUID_PATTERN.search(text)
    rule_id = match.group(0) if match else None
    return CepSpec(rule_id=rule_id)


def _determine_mode(text: str):
    normalized = text.lower()
    if any(keyword in normalized for keyword in AUTO_KEYWORDS):
        return PlanMode.AUTO
    return PlanMode.CI
