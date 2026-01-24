"""OPS orchestration helpers."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal
from uuid import uuid4

from core.config import get_settings
from core.db import get_session_context
from core.logging import get_request_context
from schemas import (
    AnswerBlock,
    AnswerEnvelope,
    AnswerMeta,
    GraphBlock,
    GraphEdge,
    GraphNode,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TableBlock,
    TimeSeriesBlock,
    TimeSeriesPoint,
    TimeSeriesSeries,
)
from schemas.tool_contracts import ExecutorResult

from app.modules.inspector.service import persist_execution_trace

from .executors.config_executor import run_config as run_config_executor
from .executors.graph_executor import run_graph
from .executors.hist_executor import run_hist
from .executors.metric_executor import run_metric
from .langgraph import LangGraphAllRunner
from .resolvers import resolve_ci, resolve_time_range

OpsMode = Literal["config", "history", "relation", "metric", "all", "hist", "graph"]

METRIC_KEYWORDS = {
    "온도",
    "temp",
    "temperature",
    "cpu",
    "사용률",
    "추이",
    "graph",
    "그래프",
    "memory",
    "ram",
    "disk",
    "network",
    "트래픽",
}
HIST_KEYWORDS = {"정비", "유지보수", "작업", "변경", "이력", "최근 변경", "최근"}
GRAPH_KEYWORDS = {"영향", "의존", "경로", "연결", "토폴로지", "구성요소", "관계"}

ALL_EXECUTOR_ORDER = ("metric", "hist", "graph", "config")

_FALLBACK_ERRORS: dict[str, str] = {
    "query_load_failed": "Query asset missing",
    "no_ci": "CI not found",
    "no_metric": "Metric not found",
    "no_data": "Metric data unavailable",
}


def _fallback_error_message(status: str) -> str | None:
    return _FALLBACK_ERRORS.get(status)


def _serialize_references(
    items: list[dict[str, Any]] | list[Any] | None,
) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    if not items:
        return serialized
    for item in items:
        if isinstance(item, dict):
            serialized.append(item)
        elif hasattr(item, "dict"):
            serialized.append(item.dict())
        else:
            serialized.append({"value": item})
    return serialized


def handle_ops_query(mode: OpsMode, question: str) -> AnswerEnvelope:
    settings = get_settings()
    started = time.perf_counter()
    fallback = False
    error: str | None = None
    executor_result: ExecutorResult | None = None
    context = get_request_context()
    trace_raw = context.get("trace_id") or context.get("request_id")
    if not trace_raw or trace_raw == "-":
        trace_raw = uuid4().hex
    trace_id = trace_raw
    parent_raw = context.get("parent_trace_id")
    parent_trace_id = parent_raw if parent_raw and parent_raw != "-" else None

    if mode == "config":
        blocks, used_tools, route_reason, summary, fallback, error = (
            _handle_config_mode(question, settings)
        )
        executor_result = None
    elif settings.ops_mode != "real":
        blocks = _build_mock_blocks(mode, question)
        used_tools = ["mock"]
        route_reason = "OPS mock mode"
        summary = f"Mocked OPS response for {mode}"
    else:
        result = _execute_real_mode(mode, question, settings)
        blocks, used_tools, extra_error, executor_result = _normalize_real_result(
            result
        )
        if extra_error:
            error = extra_error
            if ";" in error:
                for segment in (segment.strip() for segment in error.split(";")):
                    if "hist service unavailable" in segment:
                        error = segment
                        break
        if executor_result:
            status = executor_result.summary.get("status")
            if status and status != "success":
                fallback = True
                if not error:
                    error = _fallback_error_message(status)
                blocks = _build_mock_blocks(mode, question)
                used_tools = ["mock"]
        route_reason = "OPS real mode"
        summary = f"Real mode response for {mode}"

    meta = AnswerMeta(
        route=mode,
        route_reason=route_reason,
        timing_ms=int((time.perf_counter() - started) * 1000),
        summary=summary,
        used_tools=used_tools,
        fallback=fallback,
        error=error,
        trace_id=trace_id if trace_id != "-" else None,
        parent_trace_id=parent_trace_id,
    )
    envelope = AnswerEnvelope(meta=meta, blocks=blocks)
    payload = envelope.model_dump()

    trace_payload: dict[str, Any] = {
        "tool_calls": [],
        "references": [],
        "used_tools": used_tools,
        "summary": executor_result.summary if executor_result else {},
    }
    if executor_result:
        trace_payload["tool_calls"] = [
            call.model_dump() for call in executor_result.tool_calls
        ]
        trace_payload["references"] = _serialize_references(executor_result.references)

    request_payload = {"question": question, "mode": mode}
    status = "error" if error else "success"
    try:
        with get_session_context() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature=mode,
                endpoint="/ops/query",
                method="POST",
                ops_mode=settings.ops_mode,
                question=question,
                status=status,
                duration_ms=meta.timing_ms,
                request_payload=request_payload,
                plan_raw=None,
                plan_validated=None,
                trace_payload=trace_payload,
                answer_meta=payload.get("meta"),
                blocks=payload.get("blocks"),
            )
    except Exception as exc:
        logging.exception("ops.trace.persist_failed", exc_info=exc)

    return envelope


def _execute_real_mode(
    mode: OpsMode, question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str]]:
    executor = {
        "config": _run_config,
        "history": _run_history,
        "relation": _run_graph,
        "graph": _run_graph,
        "metric": _run_metric,
        "hist": _run_history,
        "all": _run_all,
    }.get(mode)
    if executor is None:
        raise NotImplementedError(f"No executor for mode {mode}")
    return executor(question, settings)


def _normalize_real_result(
    real_result: tuple[list[AnswerBlock], list[str]]
    | tuple[list[AnswerBlock], list[str], str | None]
    | ExecutorResult,
) -> tuple[list[AnswerBlock], list[str], str | None, ExecutorResult | None]:
    # Handle ExecutorResult from new executors
    if isinstance(real_result, ExecutorResult):
        # Convert blocks dicts back to AnswerBlock objects if needed
        blocks = real_result.blocks
        return blocks, real_result.used_tools, None, real_result

    # Handle legacy tuple returns
    if not isinstance(real_result, tuple):
        raise ValueError("Real executor must return a tuple or ExecutorResult")
    if len(real_result) == 2:
        return real_result[0], real_result[1], None, None
    if len(real_result) == 3:
        return real_result[0], real_result[1], real_result[2], None
    raise ValueError("Real executor tuple must have 2 or 3 elements")


def _run_config(question: str, settings: Any) -> tuple[list[AnswerBlock], list[str]]:
    tenant_id = getattr(settings, "tenant_id", "t1")
    try:
        return run_config_executor(question, tenant_id=tenant_id)
    except Exception:
        placeholder_blocks = _build_config_placeholder(question, settings)
        return placeholder_blocks, ["placeholder"]


def _run_history(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = getattr(settings, "tenant_id", "t1")
    return run_hist(question, tenant_id=tenant_id)


def _run_graph(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = getattr(settings, "tenant_id", "t1")
    return run_graph(question, tenant_id=tenant_id)


def _run_metric(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = getattr(settings, "tenant_id", "t1")
    return run_metric(question, tenant_id=tenant_id)


def _run_all(
    question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str], str | None]:
    if settings.ops_enable_langgraph:
        if settings.openai_api_key:
            try:
                return _run_all_langgraph(question, settings)
            except Exception as exc:
                logging.exception(
                    "LangGraph ALL execution failed; falling back to rule-based"
                )
                fallback_blocks, fallback_tools, fallback_error = _run_all_rule_based(
                    question, settings
                )
                lang_err = f"langgraph: {exc}"
                combined_error = "; ".join(filter(None, [lang_err, fallback_error]))
                return fallback_blocks, fallback_tools, combined_error or None
        logging.warning(
            "LangGraph requested but OpenAI API key missing; using rule-based ALL executor"
        )
    return _run_all_rule_based(question, settings)


def _run_all_langgraph(
    question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str], str | None]:
    runner = LangGraphAllRunner(settings)
    return runner.run(question)


def _run_all_rule_based(
    question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str], str | None]:
    selected = _determine_all_executors(question)
    successful_blocks: dict[str, list[AnswerBlock]] = {}
    used_tools: list[str] = []
    errors: list[str] = []
    for name in selected:
        executor = _resolve_executor(name)
        try:
            executor_blocks, executor_tools = executor(question, settings)
            successful_blocks[name] = executor_blocks
            for tool in executor_tools:
                if tool not in used_tools:
                    used_tools.append(tool)
        except Exception as exc:
            logging.exception("ALL executor %s failed", name)
            errors.append(f"{name}: {exc}")
    if not successful_blocks:
        raise RuntimeError(
            "ALL executors all failed" + (f": {'; '.join(errors)}" if errors else "")
        )
    summary_block = _build_all_summary(question, list(successful_blocks.keys()))
    ordered_blocks: list[AnswerBlock] = [summary_block]
    for name in ALL_EXECUTOR_ORDER:
        if name in successful_blocks:
            ordered_blocks.extend(successful_blocks[name])
    error_info = "; ".join(errors) if errors else None
    return ordered_blocks, used_tools, error_info


def _determine_all_executors(question: str) -> list[str]:
    text = question.lower()
    selected: list[str] = []
    if any(keyword in text for keyword in METRIC_KEYWORDS):
        selected.append("metric")
    if any(keyword in text for keyword in HIST_KEYWORDS):
        selected.append("hist")
    if any(keyword in text for keyword in GRAPH_KEYWORDS):
        selected.append("graph")
    if not selected:
        selected = ["hist", "metric", "config"]
    return selected


def _resolve_executor(
    name: str,
) -> Callable[[str, Any], tuple[list[AnswerBlock], list[str]]]:
    executors: dict[str, Callable[[str, Any], tuple[list[AnswerBlock], list[str]]]] = {
        "metric": _run_metric,
        "hist": _run_history,
        "graph": _run_graph,
        "config": _run_config,
    }
    return executors[name]


def _build_all_summary(question: str, executed_names: list[str]) -> MarkdownBlock:
    executed = ", ".join(executed_names) if executed_names else "none"
    ci_code = _safe_resolve_ci_code(question)
    time_range = _safe_resolve_time_range_text(question)
    content = (
        f"실행한 서브툴: {executed}\n"
        f"CI: {ci_code}\n"
        f"시간 범위: {time_range}\n"
        f"질문: {question}"
    )
    return MarkdownBlock(type="markdown", title="ALL summary", content=content)


def _build_config_placeholder(question: str, settings: Any) -> list[AnswerBlock]:
    ci_hint = _safe_resolve_ci_code(question)
    time_range = _safe_resolve_time_range_text(question)
    tenant_id = getattr(settings, "tenant_id", "t1")
    markdown = MarkdownBlock(
        type="markdown",
        title="Config executor not implemented yet",
        content=(
            "Config executor not implemented yet. Upcoming work:\n"
            "- Discover tenant-wide configuration targets\n"
            "- Surface grouped CI metadata + health\n"
            "- Link to related hist/metric/graph insights\n"
        ),
    )
    table = TableBlock(
        type="table",
        title="Config placeholder details",
        columns=["field", "value"],
        rows=[
            ["tenant_id", tenant_id],
            ["hint(ci_code)", ci_hint],
            ["time_range", time_range],
        ],
    )
    references = ReferencesBlock(
        type="references",
        title="todo",
        items=[
            ReferenceItem(
                kind="row",
                title="next steps",
                payload={"next": "implement config executor"},
            )
        ],
    )
    return [markdown, table, references]


def _handle_config_mode(
    question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str], str, str, bool, str | None]:
    if settings.ops_mode == "real":
        try:
            blocks, used_tools = run_config_executor(question)
            return (
                blocks,
                used_tools,
                "OPS config real mode",
                "Config executor returned real data",
                False,
                None,
            )
        except Exception as exc:
            logging.exception(
                "Config executor failed; returning placeholder", exc_info=exc
            )
            placeholder = _build_config_placeholder(question, settings)
            return (
                placeholder,
                ["placeholder"],
                "OPS config real fallback",
                "Config placeholder response",
                True,
                str(exc),
            )
    placeholder = _build_config_placeholder(question, settings)
    return (
        placeholder,
        ["placeholder"],
        "OPS config placeholder",
        "Config placeholder response",
        False,
        None,
    )


def _safe_resolve_ci_code(question: str) -> str:
    try:
        hits = resolve_ci(question)
        if hits:
            return hits[0].ci_code
    except Exception:
        logging.debug("resolve_ci failed while building ALL summary", exc_info=True)
    return "unknown"


def _safe_resolve_time_range_text(question: str) -> str:
    try:
        time_range = resolve_time_range(question, datetime.now(timezone.utc))
        return f"{time_range.start.isoformat()} ~ {time_range.end.isoformat()} ({time_range.bucket})"
    except Exception:
        logging.debug(
            "resolve_time_range failed while building ALL summary", exc_info=True
        )
    return "unknown"


def _build_mock_blocks(mode: OpsMode, question: str) -> list[AnswerBlock]:
    blocks: list[AnswerBlock] = [
        MarkdownBlock(
            type="markdown",
            title="Quick summary",
            content=f"### Mocked {mode.upper()} response\nQuestion: {question}\nData generated for {mode} scenario.",
        ),
        _mock_table(),
    ]
    if mode in {"metric", "all"}:
        blocks.append(_mock_timeseries())
    if mode in {"relation", "all"}:
        blocks.append(_mock_graph())
    blocks.append(
        ReferencesBlock(
            type="references",
            title="Sample references",
            items=[
                ReferenceItem(
                    kind="sql",
                    title="Mock SQL",
                    payload={"query": "SELECT * FROM ci WHERE ci_type = 'SYSTEM';"},
                ),
                ReferenceItem(
                    kind="cypher",
                    title="Mock Cypher",
                    payload="MATCH (n)-[:COMPOSED_OF]->(m) RETURN n, m LIMIT 5",
                ),
            ],
        )
    )
    return blocks


def _mock_table() -> TableBlock:
    return TableBlock(
        type="table",
        title="Configuration snapshot",
        columns=["Key", "Value"],
        rows=[
            ["feature_flag", "enabled"],
            ["release_window", "02:00-04:00 UTC"],
            ["owner", "Platform team"],
        ],
    )


def _mock_timeseries() -> TimeSeriesBlock:
    now = datetime.now(timezone.utc)
    series = TimeSeriesSeries(
        name="cpu_utilization",
        data=[
            _timeseries_point(now, -20, 60),
            _timeseries_point(now, -10, 64),
            _timeseries_point(now, 0, 59),
        ],
    )
    memory = TimeSeriesSeries(
        name="memory_pressure",
        data=[
            _timeseries_point(now, -20, 70),
            _timeseries_point(now, -10, 73),
            _timeseries_point(now, 0, 71),
        ],
    )
    return TimeSeriesBlock(
        type="timeseries", title="Recent metrics", series=[series, memory]
    )


def _mock_graph() -> GraphBlock:
    nodes = [
        GraphNode(id="n1", data={"label": "CI SYSTEM"}, position={"x": 0.0, "y": 0.0}),
        GraphNode(id="n2", data={"label": "SERVICE"}, position={"x": 180.0, "y": 70.0}),
        GraphNode(id="n3", data={"label": "DATABASE"}, position={"x": 360.0, "y": 0.0}),
    ]
    edges = [
        GraphEdge(id="e1", source="n1", target="n2", label="deploys"),
        GraphEdge(id="e2", source="n2", target="n3", label="writes"),
    ]
    return GraphBlock(type="graph", title="Dependency graph", nodes=nodes, edges=edges)


def _timeseries_point(
    origin: datetime, minutes_delta: int, value: int
) -> TimeSeriesPoint:
    timestamp = (origin + timedelta(minutes=minutes_delta)).isoformat()
    return TimeSeriesPoint(timestamp=timestamp, value=float(value))
