from __future__ import annotations

import json
import os
import re
from time import perf_counter
from typing import Any, Dict, Iterable, List, Set, Tuple

from core.logging import get_logger

from app.llm.client import get_llm_client
from app.modules.asset_registry.loader import load_prompt_asset
from app.modules.ops.services.orchestration.mappings.compat import (
    _get_agg_keywords,
    _get_auto_keywords,
    _get_auto_view_preferences,
    _get_cep_keywords,
    _get_filterable_fields,
    _get_graph_scope_keywords,
    _get_graph_scope_views,
    _get_graph_view_default_depth,
    _get_graph_view_keyword_map,
    _get_history_keywords,
    _get_list_keywords,
    _get_metric_aliases,
    _get_output_type_priorities,
    _get_series_keywords,
    _get_table_hints,
)
from app.modules.ops.services.orchestration.planner.plan_schema import (
    AggregateSpec,
    AutoGraphScopeSpec,
    AutoPathSpec,
    AutoSpec,
    CepSpec,
    DirectAnswerPayload,
    FilterSpec,
    GraphLimits,
    GraphSpec,
    HistorySpec,
    Intent,
    ListSpec,
    MetricSpec,
    Plan,
    PlanMode,
    PlanOutput,
    PlanOutputKind,
    PrimarySpec,
    RejectPayload,
    SecondarySpec,
    # NEW: Orchestration fields
    ToolDependency,
    View,
)

logger = get_logger(__name__)


# CI code pattern for extracting CI identifiers like sys-xxx, srv-yyy, etc
CI_CODE_PATTERN = re.compile(
    r"\b(?:sys|srv|app|was|storage|sec|db)[-\w]+\b", re.IGNORECASE
)

# Views that represent graph-based scope analysis
GRAPH_SCOPE_VIEWS = {View.COMPOSITION, View.DEPENDENCY, View.IMPACT, View.PATH}

# Server filter keywords - used to detect when user is asking about servers specifically
SERVER_FILTER_KEYWORDS = {
    "서버",
    "server",
    "servers",
    "호스트",
    "host",
    "hosts",
    "머신",
    "machine",
    "노드",
    "node",
    "nodes",
    "인스턴스",
    "instance",
}

# 정규식 패턴 (코드 구조상 필수적, 유지)
ISO_DATE_PATTERN = re.compile(r"(\d{4})[-년/\\.](\d{1,2})[-월/\\.](\d{1,2})")
# Depth 파싱: "depth 10", "깊이 10" 등
DEPTH_PATTERN = re.compile(r"(?:depth|깊이)\s+(\d+)", re.IGNORECASE)


def determine_output_types(text: str) -> Set[str]:
    normalized = text.lower()
    output_types: Set[str] = set()

    # Number keywords (하드코딩 유지 - 코드 구조상 필수적)
    NUMBER_KEYWORDS = {
        "얼마나",
        "숫자",
        "수치",
        "크다",
        "얼마나",
        "얼마",
        "몇",
        "count",
        "total",
    }
    if any(keyword in normalized for keyword in NUMBER_KEYWORDS):
        output_types.add("number")

    # Mapping Asset 로드
    agg_keywords = _get_agg_keywords()
    if any(keyword in normalized for keyword in agg_keywords.keys()):
        output_types.add("aggregate")

    series_keywords = _get_series_keywords()
    if any(keyword in normalized for keyword in series_keywords):
        output_types.add("chart")

    table_hints = _get_table_hints()
    if any(keyword in normalized for keyword in table_hints):
        output_types.add("table")

    graph_scope_keywords = _get_graph_scope_keywords()
    if any(keyword in normalized for keyword in graph_scope_keywords["scope_keywords"]):
        output_types.add("network")

    if not output_types:
        output_types.add("text")
    return output_types


def _build_output_updates(output_types: Set[str]) -> dict[str, list[str] | str]:
    priorities = _get_output_type_priorities()
    blocks: list[str] = [otype for otype in priorities if otype in output_types]
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
    lower = trimmed.lower()
    if any(
        key in lower
        for key in (
            "전체기간",
            "전체 기간",
            "전체기간중",
            "전체 기간 중",
            "all time",
            "all-time",
            "full time",
            "lifetime",
        )
    ):
        return "all_time"
    match = ISO_DATE_PATTERN.search(trimmed)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    history_keywords = _get_history_keywords()
    time_map = history_keywords.get("time_map", {})
    if lower in time_map:
        return time_map[lower]
    for key, mapped in time_map.items():
        if key in lower:
            return mapped
    if lower in {"last_1h", "last_24h", "last_7d", "last_30d"}:
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


def _load_planner_prompt_definition() -> dict[str, Any] | None:
    prompt_data = load_prompt_asset(PROMPT_SCOPE, PROMPT_ENGINE, PROMPT_NAME)
    if not prompt_data:
        logger.error(
            "Prompt definition missing for ci planner (scope=%s)", PROMPT_SCOPE
        )
        return None
    templates = prompt_data.get("templates")
    if not isinstance(templates, dict):
        logger.error(
            "Prompt templates invalid for ci planner asset: %s", prompt_data.get("name")
        )
        return None

    logger.info(
        "ci.planner.prompt_loaded",
        extra={
            "prompt_source": prompt_data.get("source"),
            "prompt_name": prompt_data.get("name"),
            "prompt_version": prompt_data.get("version"),
        },
    )
    return prompt_data


def _build_output_parser_messages(
    text: str,
    schema_context: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
) -> list[dict[str, str]] | None:
    prompt_data = _load_planner_prompt_definition()
    if not prompt_data:
        return None

    templates = prompt_data.get("templates", {})
    system_prompt = templates.get("system")
    user_prompt_template = templates.get("user")

    if not system_prompt or not user_prompt_template:
        logger.error(
            "System or user template missing for ci planner prompt definition (source=%s)",
            prompt_data.get("source"),
        )
        return None

    # Build context information from schema and source assets
    context_info = ""
    if schema_context:
        catalog = schema_context.get("catalog", {})
        if isinstance(catalog, dict):
            tables = catalog.get("tables", []) if isinstance(catalog.get("tables", []), list) else []
            table_lines: list[str] = []
            for table in tables[:5]:
                if not isinstance(table, dict):
                    continue
                table_name = str(table.get("name") or "unknown_table")
                raw_columns = table.get("columns") if isinstance(table.get("columns"), list) else []
                column_names: list[str] = []
                for col in raw_columns[:8]:
                    if not isinstance(col, dict):
                        continue
                    col_name = col.get("name") or col.get("column_name")
                    if col_name:
                        column_names.append(str(col_name))
                if column_names:
                    table_lines.append(f"{table_name}({', '.join(column_names)})")
                else:
                    table_lines.append(table_name)
            if table_lines:
                context_info += f"\nAvailable tables: {'; '.join(table_lines)}"

    if source_context:
        source_type = source_context.get("source_type")
        connection = source_context.get("connection", {})
        if source_type and connection:
            context_info += f"\nData source type: {source_type}"
            if connection.get("host"):
                context_info += f" (Host: {connection.get('host')})"

    user_prompt = user_prompt_template.replace("{question}", text)
    if context_info:
        user_prompt = f"{user_prompt}\n{context_info}"

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def _extract_json_block(text: str) -> str | None:
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else None


def _call_output_parser_llm(
    text: str,
    schema_context: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
) -> dict | None:
    """
    Call LLM for query planning with native function calling support.

    First tries to use native function calling (tool_use) for structured output.
    Falls back to JSON extraction from text if function calling unavailable.
    """
    try:
        from app.modules.ops.services.orchestration.planner.tool_schema_converter import (
            build_tools_for_llm_prompt,
            extract_tool_call_from_response,
        )

        messages = _build_output_parser_messages(
            text, schema_context=schema_context, source_context=source_context
        )
        if messages is None:
            raise ValueError("Failed to build LLM messages from prompt template.")

        llm = get_llm_client()
        start = perf_counter()

        # Try native function calling first
        response = None
        tool_call = None
        use_function_calling = True

        try:
            # Build tools list for function calling
            tools, _ = build_tools_for_llm_prompt(include_planner=True)

            logger.debug(
                "ci.planner.function_calling",
                extra={"num_tools": len(tools), "model": OUTPUT_PARSER_MODEL},
            )

            response = llm.create_response(
                model=OUTPUT_PARSER_MODEL,
                input=messages,
                tools=tools if tools else None,  # Only pass if tools available
                temperature=0,
            )

            # Try to extract tool call
            tool_call = extract_tool_call_from_response(response)
            if tool_call and tool_call.get("name") == "create_execution_plan":
                payload = tool_call.get("input", {})
                if payload:
                    elapsed = int((perf_counter() - start) * 1000)
                    logger.info(
                        "ci.planner.llm_call",
                        extra={
                            "model": OUTPUT_PARSER_MODEL,
                            "elapsed_ms": elapsed,
                            "method": "function_calling",
                            "status": "ok",
                        },
                    )
                    return payload

        except Exception as fc_exc:
            # Function calling failed, will fallback to text parsing
            logger.debug(
                "ci.planner.function_calling_failed",
                extra={"error": str(fc_exc)},
            )
            use_function_calling = False

        # Fallback: Extract JSON from response text
        if not tool_call or not use_function_calling:
            logger.debug("ci.planner.fallback_to_text_parsing")
            content = llm.get_output_text(response) if response else ""
            logger.debug(
                "ci.planner.llm_response",
                extra={"model": OUTPUT_PARSER_MODEL, "response_preview": content[:400]},
            )

            json_text = _extract_json_block(content)
            if not json_text:
                raise ValueError(f"LLM response missing JSON block: {content[:400]!r}")

            try:
                payload = json.loads(json_text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"LLM JSON parse error: {exc} | raw={json_text[:400]}"
                ) from exc

            elapsed = int((perf_counter() - start) * 1000)
            logger.info(
                "ci.planner.llm_call",
                extra={
                    "model": OUTPUT_PARSER_MODEL,
                    "elapsed_ms": elapsed,
                    "method": "text_parsing",
                    "status": "ok",
                },
            )
            return payload

        return None

    except Exception as exc:
        logger.warning("ci.planner.llm_fallback", extra={"error": str(exc)})
        return None


def is_metric_requested(text: str) -> bool:
    normalized = text.lower()
    metric_aliases = _get_metric_aliases()
    metric_keywords = set(metric_aliases.get("aliases", {}).keys()) | set(
        metric_aliases.get("keywords", [])
    )
    return any(keyword in normalized for keyword in metric_keywords)


# =============================================
# 필수 정규식 패턴 (코드 구조상 유지)
# =============================================
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
GRAPH_DEPTH_PATTERN = re.compile(r"(\d+)\s*(?:단계|depth|깊이)")
LIST_LIMIT_PATTERN = re.compile(r"(\d{1,3})\s*(?:개|건|items?|rows?)")
CI_IDENTIFIER_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9_-])[a-z0-9_]+(?:-[a-z0-9_]+)+(?![a-zA-Z0-9_-])", re.IGNORECASE
)

# =============================================
# Mapping Asset 로드 함수로 대체 (동적 로딩)
# =============================================
# _get_ci_code_patterns() - CI 코드 패턴
# _get_graph_view_keyword_map() - 그래프 뷰 키워드
# _get_graph_view_default_depth() - 기본 깊이
# _get_auto_view_preferences() - 자동 뷰 선택
# _get_output_type_priorities() - 출력 타입 우선순위
# _get_graph_scope_views() - 그래프 범위 뷰

# Prompt 설정 (환경 변수)
OUTPUT_PARSER_MODEL = os.environ.get(
    "OPS_CI_OUTPUT_PARSER_MODEL", os.environ.get("CHAT_MODEL", "gpt-4o-mini")
)

PROMPT_SCOPE = "ci"
PROMPT_ENGINE = "planner"
PROMPT_NAME = "ci_planner_output_parser"


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
    # Sanitize Korean particles from tokens that look like CI identifiers
    sanitized = []
    for token in tokens:
        # Check if token looks like a CI identifier (has hyphens)
        if "-" in token and re.match(r"[a-z0-9_]+(?:-[a-z0-9_]+)+", token.lower()):
            sanitized.append(_sanitize_korean_particles(token))
        else:
            sanitized.append(token)
    return [token for token in sanitized if len(token) > 1][:5]


def _extract_natural_language_filters(text: str) -> List[FilterSpec]:
    """Extract filters from natural language patterns like 'zone-a에 위치한'"""
    filters: List[FilterSpec] = []
    normalized = text.lower()

    # Location patterns: "zone-a에 위치한", "zone-b에 있는", "zone-c의"
    location_pattern = r"(zone-[abc])\s*(?:에\s*위치한|에\s*있는|의)"
    for match in re.finditer(location_pattern, normalized):
        location = match.group(1)
        filters.append(FilterSpec(field="location", op="=", value=location))

    # Status patterns: "active 상태인", "monitoring인"
    status_patterns = [
        (r"(active|monitoring|inactive)\s*상태인", 1),
        (r"(active|monitoring|inactive)\s*(?:상태)?인", 1),
    ]
    for pattern, group in status_patterns:
        for match in re.finditer(pattern, normalized):
            status = match.group(group)
            filters.append(FilterSpec(field="status", op="=", value=status))

    # CI subtype patterns: "서버", "network", "database/db", "was", "web", "app"
    subtype_map = {
        "서버": "server",
        "server": "server",
        "network": "network",
        "네트워크": "network",
        "db": "db",
        "database": "db",
        "데이터베이스": "db",
        "was": "was",
        "웹": "web",
        "web": "web",
        "app": "app",
        "앱": "app",
        "애플리케이션": "app",
        "os": "os",
        "운영체제": "os",
    }

    # Check for subtype patterns followed by particle or at end of sentence
    for korean, english in subtype_map.items():
        # Pattern: subtype followed by typical Korean particles or sentence boundary
        pattern = rf"\b{korean}\b\s*(?:을|를|의|인|만|목록|리스트|보여|찾아|알려|$|\))"
        if re.search(pattern, normalized, re.IGNORECASE):
            filters.append(FilterSpec(field="ci_subtype", op="=", value=english))

    return filters


def _extract_filters(text: str) -> List[FilterSpec]:
    filters: List[FilterSpec] = []
    filterable_fields = _get_filterable_fields()
    for key, value in re.findall(r"(\w+)=([\w-]+)", text):
        normalized = key.lower()
        if normalized in filterable_fields["tag_filter_keys"]:
            filters.append(FilterSpec(field=f"tags.{normalized}", value=value))
        elif normalized in filterable_fields["attr_filter_keys"]:
            filters.append(FilterSpec(field=f"attributes.{normalized}", value=value))
    # Also try natural language filter extraction
    nl_filters = _extract_natural_language_filters(text)
    filters.extend(nl_filters)
    return filters


def _filters_from_payload(payload: Iterable[dict] | None) -> List[FilterSpec]:
    results: List[FilterSpec] = []
    if not payload:
        return results
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            results.append(FilterSpec(**item))
        except Exception:
            continue
    return results


def _merge_filters(*filter_lists: Iterable[FilterSpec]) -> List[FilterSpec]:
    seen: set[tuple[str, str, str]] = set()
    merged: List[FilterSpec] = []
    for flist in filter_lists:
        for spec in flist:
            key = (spec.field, spec.op, spec.value)
            if key in seen:
                continue
            seen.add(key)
            merged.append(spec)
    return merged


def _should_filter_server(text: str) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in SERVER_FILTER_KEYWORDS)


def create_plan(
    question: str,
    schema_context: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
    mode: str | None = None,
) -> Plan:
    normalized = question.strip()
    start = perf_counter()
    logger.info(
        "ci.planner.start",
        extra={
            "query_len": len(normalized),
            "has_schema": bool(schema_context),
            "has_source": bool(source_context),
            "explicit_mode": mode,
        },
    )
    plan = Plan.model_construct()
    # Use explicit mode if provided, otherwise determine from question
    logger.info("ci.planner.mode_logic", extra={
        "explicit_mode_param": mode,
        "mode_is_truthy": bool(mode),
        "normalized_question": normalized[:100],
    })
    if mode:
        # Explicit mode provided by user/client
        try:
            plan.mode = PlanMode(mode)
            logger.info("ci.planner.explicit_mode_set", extra={
                "mode": mode,
                "plan_mode": plan.mode.value,
            })
        except (ValueError, KeyError) as e:
            # Invalid mode, fall back to auto-detection
            logger.warning("ci.planner.invalid_mode", extra={
                "mode": mode,
                "error": str(e),
            })
            plan.mode = _determine_mode(normalized)
    else:
        # No explicit mode, auto-detect from question
        logger.info("ci.planner.auto_detect_mode", extra={
            "question": normalized[:100],
        })
        plan.mode = _determine_mode(normalized)
    llm_payload = None
    graph_force = _is_graph_force_query(normalized)
    try:
        llm_payload = _call_output_parser_llm(
            normalized, schema_context=schema_context, source_context=source_context
        )
    except Exception:  # pragma: no cover - placeholder
        llm_payload = None
    output_types: Set[str]
    ci_keywords: tuple[str, ...]
    llm_filters_payload = None
    if llm_payload:
        output_types = set(llm_payload.get("output_types") or ["text"])
        # Sanitize Korean particles from LLM-returned CI identifiers
        raw_ci_keywords = llm_payload.get("ci_identifiers") or ()
        ci_keywords = tuple(_sanitize_korean_particles(k) for k in raw_ci_keywords)
        llm_filters_payload = llm_payload.get("filters")
    else:
        output_types = determine_output_types(normalized)
        ci_keywords = ()
    llm_filters = _filters_from_payload(llm_filters_payload)
    if graph_force:
        output_types.add("network")
        recovered = _extract_identifier_candidates(normalized)
        if recovered:
            if ci_keywords:
                merged = list(ci_keywords)
                for value in recovered:
                    if value not in merged:
                        merged.append(value)
                ci_keywords = tuple(merged)
            else:
                ci_keywords = tuple(recovered)
    plan.intent = derive_intent_from_output(output_types)
    plan.view = _determine_view(normalized, plan.intent)

    # Detect document-related questions and override intent to DOCUMENT
    document_keywords = [
        "문서", "매뉴얼", "가이드", "도움말",
        "help", "manual", "guide", "documentation",
        "찾아줘", "검색해", "설명해"
    ]
    is_document_question = any(kw in normalized for kw in document_keywords)

    logger.info(
        "planner.document_detection",
        extra={
            "normalized": normalized[:100],
            "is_document_question": is_document_question,
            "original_intent": plan.intent.value if plan.intent else None,
        }
    )

    if is_document_question:
        plan.intent = Intent.DOCUMENT
        plan.view = _determine_view(normalized, plan.intent)
        # Populate document spec with the user's question as search query
        plan.document = {
            "query": normalized,
            "search_type": "hybrid",
            "top_k": 10,
            "min_relevance": 0.5,
            "tool_type": "document_search",
        }
        logger.info(
            "planner.document_intent_override",
            extra={
                "reason": "document_keywords_detected",
                "detected_keywords": [kw for kw in document_keywords if kw in normalized],
                "new_intent": Intent.DOCUMENT.value,
                "document_spec": plan.document,
            }
        )

    if graph_force:
        plan.intent = Intent.LOOKUP
        plan.view = _determine_view(normalized, plan.intent)

    if (
        llm_payload
        and isinstance(llm_payload.get("list"), dict)
        and llm_payload["list"].get("enabled") is True
        and not graph_force
        and _has_list_hint(normalized)
    ):
        list_payload = llm_payload["list"]
        limit = list_payload.get("limit", 50)
        offset = list_payload.get("offset", 0)
        try:
            limit_int = int(limit)
        except Exception:
            limit_int = 50
        try:
            offset_int = int(offset)
        except Exception:
            offset_int = 0
        limit_int = max(1, min(50, limit_int))
        offset_int = max(0, min(5000, offset_int))
        plan.list = plan.list.model_copy(
            update={"enabled": True, "limit": limit_int, "offset": offset_int}
        )
        plan.intent = Intent.LIST
        plan.output = plan.output.model_copy(
            update={"blocks": ["table"], "primary": "table"}
        )
        plan.primary = plan.primary.model_copy(update={"keywords": []})
        plan.secondary = plan.secondary.model_copy(update={"keywords": []})
        logger.info(
            "ci.planner.llm.used",
            extra={
                "ci_identifiers": len(ci_keywords),
                "output_types": ",".join(sorted(output_types)),
                "list_enabled": True,
                "list_limit": limit_int,
            },
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
    plan.primary = plan.primary.model_copy(update={"keywords": keywords})
    parsed_filters = _extract_filters(normalized)
    if parsed_filters:
        plan.primary = plan.primary.model_copy(update={"filters": parsed_filters})
    server_filter = (
        FilterSpec(field="ci_subtype", value="server")
        if _should_filter_server(normalized)
        else None
    )
    aggregate_filters = _merge_filters(
        plan.primary.filters,
        llm_filters,
        [server_filter] if server_filter else [],
    )
    plan.aggregate = plan.aggregate.model_copy(update={"filters": aggregate_filters})
    secondary_text = normalized
    if plan.intent == Intent.PATH:
        left, right = _split_path_candidates(normalized)
        plan.primary = plan.primary.model_copy(
            update={"keywords": _extract_keywords(left)}
        )
        secondary_text = right
    plan.secondary = plan.secondary.model_copy(
        update={"keywords": _extract_keywords(secondary_text)}
    )
    if plan.intent == Intent.AGGREGATE:
        should_group = _determine_type_aggregation(normalized) and not aggregate_filters
        group_by = ["ci_type"] if should_group else []

        # Auto-detect scope from question keywords for generic orchestration
        # This ensures event questions use event scope, metric questions use metric scope, etc.
        aggregate_scope = "ci"  # default
        if "event" in normalized and any(
            kw in normalized for kw in ["event", "alarm", "alert", "log", "audit"]
        ):
            aggregate_scope = "event"
            # For event scope, group by event_type instead of ci_type
            if should_group:
                group_by = ["event_type"]
        elif "metric" in normalized and any(
            kw in normalized for kw in ["metric", "measurement", "value"]
        ):
            aggregate_scope = "metric"
            if should_group:
                group_by = ["metric_name"]

        plan.aggregate = plan.aggregate.model_copy(
            update={
                "group_by": group_by,
                "metrics": ["count"],
                "top_n": 10,
                "scope": aggregate_scope,
            }
        )
    # Depth 요청 추출 (사용자 질의에서 depth 명시)
    requested_depth = 1  # 기본값
    depth_match = DEPTH_PATTERN.search(normalized)
    if depth_match:
        try:
            requested_depth = int(depth_match.group(1))
            requested_depth = max(1, min(10, requested_depth))  # 1-10 범위
        except ValueError:
            requested_depth = 1

    if plan.intent == Intent.PATH:
        plan.graph = plan.graph.model_copy(
            update={
                "depth": requested_depth if requested_depth > 1 else 4,
                "user_requested_depth": requested_depth,
            }
        )
    else:
        # PATH가 아니어도 user_requested_depth 항상 기록
        plan.graph = plan.graph.model_copy(
            update={"user_requested_depth": requested_depth}
        )
    metric_spec = None
    if llm_payload:
        metric_spec = _metric_payload_to_spec(llm_payload.get("metric"))
        if metric_spec and "chart" in output_types and metric_spec.mode != "series":
            metric_spec = metric_spec.model_copy(update={"mode": "series"})
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
            plan = plan.model_copy(update={"list": list_spec})
            plan.intent = Intent.LIST
            plan.primary = plan.primary.model_copy(update={"keywords": []})
    if plan.metric and _has_graph_scope_keyword(normalized):
        plan = _apply_graph_scope(plan, normalized)
    if plan.mode == PlanMode.AUTO:
        plan = plan.model_copy(update={"auto": _determine_auto_spec(normalized, plan)})
    plan = plan.model_copy(
        update={
            "output": plan.output.model_copy(update=_build_output_updates(output_types))
        }
    )
    if llm_payload:
        logger.info(
            "ci.planner.llm.used",
            extra={
                "ci_identifiers": len(ci_keywords),
                "output_types": ",".join(sorted(output_types)),
                "list_enabled": False,
            },
        )
    else:
        logger.info("ci.planner.llm.skipped", extra={"reason": "heuristic"})

    # ===== FINAL SCOPE CORRECTION =====
    # This is a safety net to ensure scope is correctly set based on question keywords
    # This overrides any LLM or heuristic decisions with explicit keyword detection
    if plan.intent == Intent.AGGREGATE:
        normalized_lower = normalized.lower()
        # Detect event scope
        if any(
            kw in normalized_lower
            for kw in ["event", "alarm", "alert", "log", "audit", "incident"]
        ):
            if plan.aggregate.scope != "event":
                plan.aggregate = plan.aggregate.model_copy(update={"scope": "event"})
                # Also update group_by for event scope
                if (
                    plan.aggregate.group_by == ["ci_type"]
                    or not plan.aggregate.group_by
                ):
                    plan.aggregate = plan.aggregate.model_copy(
                        update={"group_by": ["event_type"]}
                    )
        # Detect metric scope
        elif "metric" in normalized_lower and any(
            kw in normalized_lower for kw in ["metric", "measurement", "value"]
        ):
            if plan.aggregate.scope != "metric":
                plan.aggregate = plan.aggregate.model_copy(update={"scope": "metric"})
    # ===== END FINAL SCOPE CORRECTION =====

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
    metric_aliases = _get_metric_aliases()
    metric_keywords = set(metric_aliases.get("aliases", {}).keys()) | set(
        metric_aliases.get("keywords", [])
    )

    metric_name = None
    for alias in metric_keywords:
        if alias in normalized:
            metric_name = metric_aliases["aliases"].get(alias, alias)
            break
    if not metric_name:
        return None

    history_keywords = _get_history_keywords()
    time_map = history_keywords.get("time_map", {})
    if any(
        key in normalized
        for key in (
            "전체기간",
            "전체 기간",
            "전체기간중",
            "전체 기간 중",
            "all time",
            "all-time",
            "full time",
            "lifetime",
        )
    ):
        time_range = "all_time"
    else:
        time_range = next(
            (value for key, value in time_map.items() if key in normalized),
            "last_24h",
        )

    agg_keywords = _get_agg_keywords()
    agg = next(
        (value for key, value in agg_keywords.items() if key in normalized), "avg"
    )

    series_keywords = _get_series_keywords()
    mode = (
        "series"
        if any(keyword in normalized for keyword in series_keywords)
        else "aggregate"
    )
    # default aggregate/series based on keywords
    return MetricSpec(
        metric_name=metric_name, agg=agg, time_range=time_range, mode=mode
    )


def _determine_list_spec(text: str) -> ListSpec | None:
    normalized = text.lower()
    if _is_graph_force_query(normalized):
        return None
    match = LIST_LIMIT_PATTERN.search(normalized)
    list_keywords = _get_list_keywords()
    has_hint = any(keyword in normalized for keyword in list_keywords)
    if not has_hint and not match:
        return None
    if not has_hint:
        # Heuristic: if user asks for N items and mentions CI/names, treat as list.
        if "ci" not in normalized and "이름" not in normalized:
            return None
    limit = 50
    if match:
        limit = int(match.group(1))
    limit = max(1, min(50, limit))
    return ListSpec(enabled=True, limit=limit)


def _determine_type_aggregation(text: str) -> bool:
    normalized = text.lower()
    type_keywords = {"종류", "타입", "type", "category", "분류"}
    if not any(keyword in normalized for keyword in type_keywords):
        return False
    list_keywords = _get_list_keywords()
    if any(keyword in normalized for keyword in list_keywords):
        return False
    return True


def _apply_ci_type_aggregation(plan: Plan, text: str) -> Plan:
    if not _determine_type_aggregation(text):
        return plan
    if plan.aggregate.filters:
        return plan
    if plan.intent == Intent.AGGREGATE and "ci_type" in plan.aggregate.group_by:
        return plan
    aggregate = plan.aggregate.model_copy(
        update={"group_by": ["ci_type"], "metrics": ["count"], "top_n": 10}
    )
    return plan.model_copy(
        update={
            "intent": Intent.AGGREGATE,
            "aggregate": aggregate,
            "normalized_from": "ci_type_distinct",
            "normalized_to": "ci_type_aggregation",
        }
    )


def _determine_graph_view(text: str) -> View:
    normalized = text.lower()
    keyword_map = _get_graph_view_keyword_map()
    for keyword, view in keyword_map.items():
        if keyword in normalized:
            return view
    return View.DEPENDENCY


def _determine_graph_depth(text: str, view: View) -> int:
    match = GRAPH_DEPTH_PATTERN.search(text)
    if match:
        return max(1, int(match.group(1)))
    default_depths = _get_graph_view_default_depth()
    return default_depths.get(view, default_depths.get(View.DEPENDENCY, 2))


def _has_graph_scope_keyword(text: str) -> bool:
    normalized = text.lower()
    graph_scope_keywords = _get_graph_scope_keywords()
    return any(
        keyword in normalized for keyword in graph_scope_keywords["scope_keywords"]
    )


def _is_graph_force_query(text: str) -> bool:
    normalized = text.lower()
    force_keywords = _get_graph_scope_views()
    if any(keyword in normalized for keyword in force_keywords):
        return True
    if GRAPH_DEPTH_PATTERN.search(text):
        return True
    if "단계" in normalized and "몇" in normalized:
        return True
    return False


def _sanitize_korean_particles(text: str) -> str:
    """Remove Korean particles (조사) from the end of text.

    Korean particles that should be stripped:
    - 조사 (particles): 의, 을, 를, 이, 가, 은, 는, 과, 와, 부터, 까지, 에서, 으로, 로, 만, 조차, 처럼
    """
    korean_particles = {
        "의",
        "을",
        "를",
        "이",
        "가",
        "은",
        "는",
        "과",
        "와",
        "부터",
        "까지",
        "에서",
        "으로",
        "로",
        "만",
        "조차",
        "처럼",
        "랑",
        "이나",
        "나",
        "께",
        "한테",
        "더러",
    }
    result = text
    for particle in sorted(korean_particles, key=len, reverse=True):
        if result.endswith(particle):
            result = result[: -len(particle)]
            break
    return result.strip()


def _extract_identifier_candidates(text: str) -> list[str]:
    matches = CI_IDENTIFIER_PATTERN.findall(text)
    deduped: list[str] = []
    for match in matches:
        value = match.strip()
        # Sanitize Korean particles from extracted identifiers
        value = _sanitize_korean_particles(value)
        if value and value not in deduped:
            deduped.append(value)
    return deduped[:5]


def _has_list_hint(text: str) -> bool:
    normalized = text.lower()
    if LIST_LIMIT_PATTERN.search(normalized):
        return True
    list_keywords = _get_list_keywords()
    return any(keyword in normalized for keyword in list_keywords)


def _apply_graph_scope(plan: Plan, text: str) -> Plan:
    graph_view = _determine_graph_view(text)
    depth = _determine_graph_depth(text, graph_view)
    metric_spec = plan.metric
    if not metric_spec:
        return plan
    updated_metric = metric_spec.model_copy(
        update={"scope": "graph", "mode": "aggregate"}
    )
    return plan.model_copy(
        update={
            "metric": updated_metric,
            "view": graph_view,
            "graph": plan.graph.model_copy(update={"view": graph_view, "depth": depth}),
        }
    )


def _apply_graph_history_scope(plan: Plan, text: str) -> Plan:
    graph_view = _determine_graph_view(text)
    depth = _determine_graph_depth(text, graph_view)
    return plan.model_copy(
        update={
            "view": graph_view,
            "graph": plan.graph.model_copy(update={"view": graph_view, "depth": depth}),
        }
    )


def _determine_auto_views(text: str) -> List[View]:
    normalized = text.lower()
    selected: List[View] = []
    auto_preferences = _get_auto_view_preferences()
    for keywords, view_candidates in auto_preferences:
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

    metric_aliases = _get_metric_aliases()
    metric_keywords = set(metric_aliases.get("aliases", {}).keys()) | set(
        metric_aliases.get("keywords", [])
    )
    include_metric = bool(plan.metric) or any(
        keyword in normalized for keyword in metric_keywords
    )

    series_keywords = _get_series_keywords()
    metric_mode = (
        "series"
        if any(keyword in normalized for keyword in series_keywords)
        else "aggregate"
    )

    history_keywords = _get_history_keywords()
    include_history = bool(plan.history.enabled) or any(
        keyword in normalized for keyword in history_keywords["keywords"]
    )

    cep_keywords = _get_cep_keywords()
    include_cep = bool(plan.cep and plan.cep.rule_id) or any(
        keyword in normalized for keyword in cep_keywords
    )

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

    graph_scope_keywords = _get_graph_scope_keywords()
    include_metric = has_scope_view and any(
        keyword in normalized for keyword in graph_scope_keywords["metric_keywords"]
    )

    history_keywords = _get_history_keywords()
    include_history = has_scope_view and any(
        keyword in normalized for keyword in history_keywords["keywords"]
    )

    return AutoGraphScopeSpec(
        include_metric=include_metric, include_history=include_history
    )


# 하드코딩된 상수 제거 - Mapping Asset 로드로 대체

TYPE_KEYWORDS = {"종류", "타입", "type", "category", "kind"}
TYPE_AGG_KEYWORDS = TYPE_KEYWORDS


def _determine_history_spec(text: str):
    normalized = text.lower()
    history_keywords = _get_history_keywords()
    if not any(keyword in normalized for keyword in history_keywords["keywords"]):
        return None

    time_map = history_keywords.get("time_map", {})
    if any(
        key in normalized
        for key in (
            "전체기간",
            "전체 기간",
            "전체기간중",
            "전체 기간 중",
            "all time",
            "all-time",
            "full time",
            "lifetime",
        )
    ):
        time_range = "all_time"
    else:
        time_range = "last_7d"
    for key, value in time_map.items():
        if key in normalized:
            time_range = value
            break

    limit = 50
    match = re.search(r"(\d{1,3})\s*개", normalized)
    if match:
        limit = min(200, max(1, int(match.group(1))))
    elif "최근" in normalized or "recent" in normalized:
        limit = 6

    scope = "graph" if _has_graph_scope_keyword(normalized) else "ci"
    history_tool_type = _determine_history_tool_type(normalized)
    return HistorySpec(
        enabled=True,
        scope=scope,
        time_range=time_range,
        limit=limit,
        tool_type=history_tool_type,
        source=history_tool_type,
    )


def _determine_history_tool_type(normalized_text: str) -> str:
    maintenance_keywords = ("점검", "정비", "maintenance", "inspection", "maint")
    work_keywords = ("작업", "work history", "work")
    if any(keyword in normalized_text for keyword in maintenance_keywords):
        return "maintenance_history"
    if any(keyword in normalized_text for keyword in work_keywords):
        return "work_history"
    return "event_log"


def _determine_cep_spec(text: str) -> CepSpec | None:
    cep_keywords = _get_cep_keywords()
    if not any(keyword in text.lower() for keyword in cep_keywords):
        return None
    match = UUID_PATTERN.search(text)
    rule_id = match.group(0) if match else None
    return CepSpec(rule_id=rule_id)


def _determine_mode(text: str):
    normalized = text.lower()
    auto_keywords = _get_auto_keywords()
    if any(keyword in normalized for keyword in auto_keywords):
        return PlanMode.AUTO
    return PlanMode.CI


def create_plan_output(
    question: str,
    schema_context: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
    mode: str | None = None,
) -> PlanOutput:
    """Create a plan output with route determination (direct, plan, or reject)

    Args:
        question: User's question
        schema_context: Schema asset for catalog/field context
        source_context: Source asset for data source context
        mode: Explicit mode ("all", "config", "metric", "hist", "graph", "document")
    """
    normalized = question.strip()
    start = perf_counter()
    logger.info(
        "ci.planner.start",
        extra={
            "query_len": len(normalized),
            "has_schema": bool(schema_context),
            "has_source": bool(source_context),
            "mode": mode,
        },
    )

    # Try to get route from LLM first
    route = "orch"  # default
    llm_payload = None
    try:
        llm_payload = _call_output_parser_llm(
            normalized, schema_context=schema_context, source_context=source_context
        )
        if llm_payload and llm_payload.get("route"):
            route = llm_payload["route"]
    except Exception:
        logger.warning("ci.planner.route_fallback", extra={"reason": "heuristic"})

    # Safety check: if query contains CI identifiers or infrastructure keywords, override reject/direct to orch
    # This prevents valid infrastructure queries from being incorrectly classified
    if route in ("reject", "direct"):
        INFRA_KEYWORDS = {
            "구성",
            "구성정보",
            "상태",
            "정보",
            "메트릭",
            "cpu",
            "memory",
            "disk",
            "서버",
            "server",
            "database",
            "db",
            "app",
            "application",
            "네트워크",
            "config",
            "configuration",
            "status",
            "health",
            "metric",
            "연결",
            "의존",
        }
        ci_codes = CI_CODE_PATTERN.findall(normalized)
        ci_identifiers = CI_IDENTIFIER_PATTERN.findall(normalized)
        has_infra_keyword = any(kw in normalized.lower() for kw in INFRA_KEYWORDS)
        if ci_codes or ci_identifiers or has_infra_keyword:
            logger.warning(
                "ci.planner.reject_override",
                extra={
                    "reason": "ci_identifier_or_infra_keyword_detected",
                    "ci_codes": ci_codes[:5],
                    "ci_identifiers": ci_identifiers[:5],
                    "has_infra_keyword": has_infra_keyword,
                    "original_route": route,
                },
            )
            route = "orch"

    # Use LLM-determined route if available, otherwise use heuristic
    if route == "direct":
        end = perf_counter()
        elapsed_ms = int((end - start) * 1000)
        logger.info("ci.planner.direct_answer", extra={"elapsed_ms": elapsed_ms})

        return PlanOutput(
            kind=PlanOutputKind.DIRECT,
            direct_answer=DirectAnswerPayload(
                answer=_generate_direct_answer(normalized),
                confidence=0.95,
                reasoning="Simple query that doesn't require orchestration",
            ),
            confidence=0.95,
            reasoning="Direct answer route selected",
            metadata={"elapsed_ms": elapsed_ms, "llm_route": route},
        )

    if route == "reject":
        end = perf_counter()
        elapsed_ms = int((end - start) * 1000)
        logger.info("ci.planner.reject", extra={"elapsed_ms": elapsed_ms})

        return PlanOutput(
            kind=PlanOutputKind.REJECT,
            reject_payload=RejectPayload(
                reason="This query is not supported or cannot be processed",
                policy="content_policy",
                confidence=1.0,
                reasoning="Query violates content policy or is not supported",
            ),
            confidence=1.0,
            reasoning="Reject route selected",
            metadata={"elapsed_ms": elapsed_ms, "llm_route": route},
        )

    # Otherwise, create a normal plan
    plan = create_plan(
        normalized, schema_context=schema_context, source_context=source_context, mode=mode
    )
    end = perf_counter()
    elapsed_ms = int((end - start) * 1000)
    logger.info("ci.planner.plan_created", extra={"elapsed_ms": elapsed_ms})

    return PlanOutput(
        kind=PlanOutputKind.PLAN,
        plan=plan,
        confidence=1.0,
        reasoning="Orchestration plan created",
        metadata={"elapsed_ms": elapsed_ms, "llm_route": route},
    )


def _should_direct_answer(text: str) -> bool:
    """Determine if a question should be answered directly without orchestration"""
    normalized = text.lower()

    # Simple greetings and common questions
    if any(
        greeting in normalized for greeting in ["hello", "hi", "안녕", "안녕하세요"]
    ):
        return True

    if any(
        keyword in normalized for keyword in ["what is", "who is", "how to", "help"]
    ):
        return True

    # Very simple queries that don't need database access
    if len(normalized) < 20 and any(
        keyword in normalized for keyword in ["simple", "basic"]
    ):
        return True

    return False


def _should_reject(text: str) -> bool:
    """Determine if a question should be rejected"""
    normalized = text.lower()

    # Security concerns
    if any(
        keyword in normalized
        for keyword in ["delete all", "drop table", "format", "hack"]
    ):
        return True

    # Inappropriate content
    if any(keyword in normalized for keyword in ["inappropriate", "offensive", "spam"]):
        return True

    # Queries that would be too expensive
    if any(keyword in normalized for keyword in ["all data", "everything", "infinite"]):
        return True

    return False


def _generate_direct_answer(text: str) -> str:
    """Generate a direct answer for simple queries"""
    normalized = text.lower()

    if "hello" in normalized or "hi" in normalized:
        return "Hello! I'm here to help you with your IT operations questions. What would you like to know?"

    if "안녕" in normalized:
        return "안녕하세요! IT 운영 문제에 도움이 필요하신가요?"

    if "what is" in normalized:
        return "This is the IT Operations Assistant. I can help you with queries about your infrastructure, services, and operational data."

    return "I understand you're asking about something simple. Could you please clarify what you'd like to know?"


async def plan_llm_query(question: str, source_ref: str = None) -> PlanOutput:
    """Generate execution plan from question using LLM with enhanced context."""
    normalized = question.strip()
    start = perf_counter()
    logger.info(
        "ci.planner.plan_llm_query.start",
        extra={
            "query_len": len(normalized),
            "has_source": bool(source_ref),
        },
    )

    # NEW: Load tool registry info
    from app.modules.ops.services.orchestration.tools.base import get_tool_registry

    tool_registry = get_tool_registry()
    tools_info = tool_registry.get_all_tools_info()

    # NEW: Load catalog info if source provided
    catalog_info = None
    if source_ref:
        from app.modules.asset_registry.loader import load_catalog_for_llm

        catalog_info = load_catalog_for_llm(
            source_ref=source_ref,
            max_tables=10,
            max_columns_per_table=15,
            max_sample_rows=3,
        )

    # Pre-check: Detect if this is a document search question
    # If document keywords are detected, force DOCUMENT intent
    document_keywords = [
        "문서", "매뉴얼", "가이드", "도움말",
        "help", "manual", "guide", "documentation",
        "찾아줘", "검색해", "설명해"
    ]
    is_document_question = any(
        kw in normalized for kw in document_keywords
    )

    logger.info(
        "planner.keyword_check",
        extra={
            "normalized": normalized[:100],
            "keywords": document_keywords,
            "is_document_question": is_document_question
        }
    )

    # Build enhanced prompt with tool and catalog info
    prompt = _build_enhanced_planner_prompt(
        question=normalized, tools_info=tools_info, catalog_info=catalog_info
    )

    # Call LLM
    llm = get_llm_client()
    response = await llm.chat_completion(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"User Question: {normalized}"},
        ],
        model=OUTPUT_PARSER_MODEL,
        temperature=0,
    )

    elapsed = int((perf_counter() - start) * 1000)
    logger.info(
        "ci.planner.llm_call",
        extra={
            "model": OUTPUT_PARSER_MODEL,
            "elapsed_ms": elapsed,
            "status": "ok",
        },
    )

    # Parse LLM response
    content = response.get("content", "")
    json_text = _extract_json_block(content)
    if not json_text:
        raise ValueError(f"LLM response missing JSON block: {content[:400]!r}")

    try:
        llm_payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM JSON parse error: {exc} | raw={json_text[:400]}"
        ) from exc

    # Force DOCUMENT intent if document keywords detected
    if is_document_question:
        logger.info(
            "planner.document_detection",
            extra={
                "detected": True,
                "original_intent": llm_payload.get("intent", "unknown")
            }
        )
        llm_payload["intent"] = "DOCUMENT"
        # Add document spec
        llm_payload["document"] = {
            "query": normalized,
            "search_type": "hybrid",
            "top_k": 10,
            "min_relevance": 0.5,
            "tool_type": "document_search"
        }

    # Create Plan from LLM response
    plan = Plan.model_construct()
    plan.mode = _determine_mode(normalized)

    # Extract and validate tool_type values
    valid_tool_types = {tool["type"] for tool in tools_info}

    # Validate Plan
    validation_errors = _validate_plan(plan, tools_info)
    if validation_errors:
        logger.warning(f"Plan validation failed: {validation_errors}")
        # Continue with plan but log errors - in production we might want to
        # regenerate the plan or fallback to defaults

    # Primary spec
    if llm_payload.get("primary"):
        primary_spec = llm_payload["primary"]
        plan.primary = PrimarySpec(
            keywords=primary_spec.get("keywords", []),
            filters=[FilterSpec(**f) for f in primary_spec.get("filters", [])],
            limit=primary_spec.get("limit", 5),
            tool_type=primary_spec.get("tool_type", "ci_lookup"),  # Use tool_type
        )
        # Validate tool_type
        if plan.primary.tool_type not in valid_tool_types:
            logger.warning(f"Invalid primary tool_type: {plan.primary.tool_type}")

    # Secondary spec
    if llm_payload.get("secondary"):
        secondary_spec = llm_payload["secondary"]
        plan.secondary = SecondarySpec(
            keywords=secondary_spec.get("keywords", []),
            filters=[FilterSpec(**f) for f in secondary_spec.get("filters", [])],
            limit=secondary_spec.get("limit", 5),
            tool_type=secondary_spec.get("tool_type", "ci_lookup"),  # Use tool_type
        )
        # Validate tool_type
        if plan.secondary.tool_type not in valid_tool_types:
            logger.warning(f"Invalid secondary tool_type: {plan.secondary.tool_type}")

    # Aggregate spec
    if llm_payload.get("aggregate"):
        aggregate_spec = llm_payload["aggregate"]
        plan.aggregate = AggregateSpec(
            group_by=aggregate_spec.get("group_by", []),
            metrics=aggregate_spec.get("metrics", []),
            filters=[FilterSpec(**f) for f in aggregate_spec.get("filters", [])],
            top_n=aggregate_spec.get("top_n", 10),
            scope=aggregate_spec.get("scope", "ci"),
            tool_type=aggregate_spec.get("tool_type", "ci_aggregate"),  # Use tool_type
        )
        # Validate tool_type
        if plan.aggregate.tool_type not in valid_tool_types:
            logger.warning(f"Invalid aggregate tool_type: {plan.aggregate.tool_type}")

    # Graph spec
    if llm_payload.get("graph"):
        graph_spec = llm_payload["graph"]
        plan.graph = GraphSpec(
            depth=graph_spec.get("depth", 2),
            view=graph_spec.get("view", View.SUMMARY),
            limits=GraphLimits(
                rows=graph_spec.get("rows", 100),
                nodes=graph_spec.get("nodes", 100),
                relationships=graph_spec.get("relationships", 200),
            ),
            user_requested_depth=graph_spec.get("user_requested_depth", 2),
            tool_type=graph_spec.get("tool_type", "ci_graph"),  # Use tool_type
        )
        # Validate tool_type
        if plan.graph.tool_type not in valid_tool_types:
            logger.warning(f"Invalid graph tool_type: {plan.graph.tool_type}")

    # Metric spec
    if llm_payload.get("metric"):
        metric_spec = llm_payload["metric"]
        plan.metric = MetricSpec(
            metric_name=metric_spec.get("metric_name"),
            agg=metric_spec.get("agg", "avg"),
            time_range=metric_spec.get("time_range"),
            tool_type=metric_spec.get("tool_type", "metric"),  # Use tool_type
        )
        # Validate tool_type
        if plan.metric.tool_type not in valid_tool_types:
            logger.warning(f"Invalid metric tool_type: {plan.metric.tool_type}")

    # NEW: Set orchestration fields
    plan.execution_strategy = llm_payload.get("execution_strategy", "serial")
    if llm_payload.get("tool_dependencies"):
        plan.tool_dependencies = [
            ToolDependency(**dep) for dep in llm_payload.get("tool_dependencies", [])
        ]
    plan.enable_intermediate_llm = llm_payload.get("enable_intermediate_llm", False)

    logger.info("ci.planner.plan_llm_query.plan_created", extra={"elapsed_ms": elapsed})

    return PlanOutput(
        kind=PlanOutputKind.PLAN,
        plan=plan,
        confidence=1.0,
        reasoning="Enhanced orchestration plan created with tool and catalog context",
        metadata={"elapsed_ms": elapsed},
    )


def _validate_plan(plan: Plan, tools_info: List[Dict[str, Any]]) -> List[str]:
    """Validate that Plan uses valid tool_type values."""
    errors = []
    valid_tool_types = {tool["type"] for tool in tools_info}

    # Check primary tool_type
    if plan.primary and plan.primary.tool_type not in valid_tool_types:
        errors.append(f"Invalid primary tool_type: {plan.primary.tool_type}")

    # Check secondary tool_type
    if plan.secondary and plan.secondary.tool_type not in valid_tool_types:
        errors.append(f"Invalid secondary tool_type: {plan.secondary.tool_type}")

    # Check metric tool_type
    if plan.metric and plan.metric.tool_type not in valid_tool_types:
        errors.append(f"Invalid metric tool_type: {plan.metric.tool_type}")

    # Check aggregate tool_type
    if plan.aggregate and plan.aggregate.tool_type not in valid_tool_types:
        errors.append(f"Invalid aggregate tool_type: {plan.aggregate.tool_type}")

    # Check graph tool_type
    if plan.graph and plan.graph.tool_type not in valid_tool_types:
        errors.append(f"Invalid graph tool_type: {plan.graph.tool_type}")

    # Check auto tool_type
    if plan.auto and plan.auto.tool_type not in valid_tool_types:
        errors.append(f"Invalid auto tool_type: {plan.auto.tool_type}")

    # Check history tool_type
    if plan.history and plan.history.tool_type not in valid_tool_types:
        errors.append(f"Invalid history tool_type: {plan.history.tool_type}")

    # Check cep tool_type
    if plan.cep and plan.cep.tool_type not in valid_tool_types:
        errors.append(f"Invalid cep tool_type: {plan.cep.tool_type}")

    return errors


def _build_enhanced_planner_prompt(
    question: str,
    tools_info: List[Dict[str, Any]] = None,
    catalog_info: Dict[str, Any] = None,
) -> str:
    """Build enhanced planner prompt with tool and catalog context."""

    prompt_parts = []

    # Base instruction
    prompt_parts.append("""
You are an intelligent query planner for a CI/OPS system.
Your task is to analyze the user's question and create an execution plan.
""")

    # NEW: Tool Registry Section
    if tools_info:
        prompt_parts.append("\n## Available Tools\n")
        for tool in tools_info:
            prompt_parts.append(f"\n### {tool['name']} ({tool['type']})")
            if tool.get("input_schema"):
                prompt_parts.append(
                    f"Input Schema: {json.dumps(tool['input_schema'], indent=2)}"
                )
            if tool.get("output_schema"):
                prompt_parts.append(
                    f"Output Schema: {json.dumps(tool['output_schema'], indent=2)}"
                )

    # NEW: Catalog Section
    if catalog_info:
        prompt_parts.append("\n## Database Schema (Catalog)\n")
        prompt_parts.append(f"Source: {catalog_info['source_ref']}\n")
        prompt_parts.append(f"Tables: {len(catalog_info.get('tables', []))}\n")

        for table in catalog_info.get("tables", [])[:5]:  # Top 5 tables
            prompt_parts.append(f"\n### Table: {table['name']}")
            prompt_parts.append(f"Rows: {table.get('row_count', 'unknown')}")
            prompt_parts.append("Columns:")
            for col in table.get("columns", [])[:10]:  # Top 10 columns
                col_info = f"  - {col['name']} ({col['type']})"
                if col.get("samples"):
                    col_info += f" Examples: {col['samples'][:3]}"
                prompt_parts.append(col_info)

    # Existing instruction sections
    prompt_parts.append("\n## Instructions\n")
    prompt_parts.append("""
1. Identify the user's intent (LOOKUP, AGGREGATE, PATH, DOCUMENT, etc.)
2. For document-related questions (keywords: "문서", "매뉴얼", "가이드", "검색", "찾아줘"), use document_search tool
3. Select appropriate tool(s) from the Available Tools section
4. Define tool parameters based on the Database Schema
5. Specify tool dependencies if one tool needs output from another
6. Return a Plan JSON with tool_type for each operation
7. Choose execution_strategy: "serial", "parallel", or "dag"
""")

    # User question
    prompt_parts.append(f"\n## User Question\n{question}\n")

    # Plan schema
    prompt_parts.append("\n## Plan Schema\n")
    prompt_parts.append("""
{
  "intent": "LOOKUP|AGGREGATE|PATH|EXPAND|DOCUMENT",
  "view": "SUMMARY|COMPOSITION|DEPENDENCY|IMPACT|PATH",
  "primary": {
    "keywords": ["string"],
    "filters": [{"field": "string", "op": "string", "value": "any"}],
    "limit": 5,
    "tool_type": "string"
  },
  "secondary": {
    "keywords": ["string"],
    "filters": [{"field": "string", "op": "string", "value": "any"}],
    "limit": 5,
    "tool_type": "string"
  },
  "aggregate": {
    "group_by": ["string"],
    "metrics": ["string"],
    "filters": [{"field": "string", "op": "string", "value": "any"}],
    "top_n": 10,
    "scope": "ci|event",
    "tool_type": "string"
  },
  "graph": {
    "depth": 2,
    "view": "SUMMARY|COMPOSITION|DEPENDENCY|IMPACT|PATH",
    "limits": {"rows": 100, "nodes": 100, "relationships": 200},
    "user_requested_depth": 2,
    "tool_type": "string"
  },
  "metric": {
    "metric_name": "string",
    "agg": "avg|sum|count|min|max",
    "time_range": null,
    "tool_type": "string"
  },
  "document": {
    "query": "string",
    "search_type": "hybrid|text|vector",
    "top_k": 10,
    "min_relevance": 0.5,
    "tool_type": "string"
  },
  "execution_strategy": "serial|parallel|dag",
  "tool_dependencies": [
    {
      "tool_id": "string",
      "depends_on": ["string"],
      "output_mapping": {"string": "string"},
      "condition": "string"
    }
  ],
  "enable_intermediate_llm": false
}
""")

    return "\n".join(prompt_parts)
