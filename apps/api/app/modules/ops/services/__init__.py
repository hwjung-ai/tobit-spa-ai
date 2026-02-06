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

# Legacy executors removed for generic orchestration
# All executor functionality should be implemented as Tool Assets
from .langgraph import LangGraphAllRunner
from .resolvers import resolve_ci, resolve_time_range


# Stub implementations for removed executors
def run_config_executor(question: str, **kwargs) -> tuple[list[AnswerBlock], list[str]]:
    """Run config executor - returns placeholder until Tool Asset is implemented."""
    settings = kwargs.get("settings") or get_settings()
    placeholder = _build_config_placeholder(question, settings)
    return (placeholder, ["placeholder"])


def run_graph(question: str, **kwargs) -> tuple[list[AnswerBlock], list[str]]:
    """Run graph executor - returns mock data until Tool Asset is implemented."""
    blocks = _build_mock_blocks("relation", question)
    return (blocks, ["mock"])


def run_hist(question: str, **kwargs) -> tuple[list[AnswerBlock], list[str]]:
    """Run hist executor using execute_universal."""
    tenant_id = kwargs.get("tenant_id")
    if not tenant_id:
        settings = kwargs.get("settings") or get_settings()
        tenant_id = _get_required_tenant_id(settings)
    result = execute_universal(question, "hist", tenant_id)
    return result.blocks, result.used_tools


def run_metric(question: str, **kwargs) -> tuple[list[AnswerBlock], list[str]]:
    """Run metric executor using execute_universal."""
    tenant_id = kwargs.get("tenant_id")
    if not tenant_id:
        settings = kwargs.get("settings") or get_settings()
        tenant_id = _get_required_tenant_id(settings)
    result = execute_universal(question, "metric", tenant_id)
    return result.blocks, result.used_tools


def run_document(question: str, **kwargs) -> tuple[list[AnswerBlock], list[str]]:
    """Run document search executor."""
    import asyncio
    from app.modules.document_processor.services.search_service import DocumentSearchService, SearchFilters
    from core.db import get_session_context

    tenant_id = kwargs.get("tenant_id")
    if not tenant_id:
        settings = kwargs.get("settings") or get_settings()
        tenant_id = _get_required_tenant_id(settings)

    logger = logging.getLogger(__name__)
    logger.info(f"Executing document search for question: {question[:100]}")

    try:
        with get_session_context() as session:
            search_service = DocumentSearchService(session, embedding_service=None)

            filters = SearchFilters(
                tenant_id=tenant_id,
                date_from=None,
                date_to=None,
                document_types=[],
                min_relevance=0.5
            )

            # Run async search
            loop = asyncio.get_event_loop()
            search_results = loop.run_until_complete(
                search_service.search(
                    query=question,
                    filters=filters,
                    top_k=10,
                    search_type="hybrid"
                )
            )

            # Convert search results to blocks
            if not search_results:
                markdown_block = MarkdownBlock(
                    type="markdown",
                    title="Document Search Results",
                    content="No documents found matching your query."
                )
                return [markdown_block], ["document_search"]

            # Create table block with results
            columns = ["Document", "Content", "Score"]
            rows = []
            for result in search_results:
                score_str = f"{result.relevance_score:.2%}" if hasattr(result, 'relevance_score') else "N/A"
                rows.append([
                    result.document_name if hasattr(result, 'document_name') else "Unknown",
                    (result.chunk_text[:100] + "...") if hasattr(result, 'chunk_text') and len(result.chunk_text) > 100 else result.chunk_text if hasattr(result, 'chunk_text') else "",
                    score_str
                ])

            table_block = TableBlock(
                type="table",
                title="Document Search Results",
                columns=columns,
                rows=rows
            )

            # Create references block with detailed results
            items = []
            for i, result in enumerate(search_results, 1):
                doc_name = result.document_name if hasattr(result, 'document_name') else "Unknown"
                chunk_text = result.chunk_text if hasattr(result, 'chunk_text') else ""
                page = result.page_number if hasattr(result, 'page_number') else None

                items.append(ReferenceItem(
                    kind="document",
                    title=f"{i}. {doc_name}",
                    payload={
                        "chunk_id": result.chunk_id if hasattr(result, 'chunk_id') else "",
                        "document_id": result.document_id if hasattr(result, 'document_id') else "",
                        "content": chunk_text,
                        "page": page,
                        "relevance": result.relevance_score if hasattr(result, 'relevance_score') else 0,
                    }
                ))

            references_block = ReferencesBlock(
                type="references",
                title="Detailed Document Matches",
                items=items
            )

            return [table_block, references_block], ["document_search"]

    except Exception as exc:
        logger.exception(f"Document search executor failed: {exc}")
        error_block = MarkdownBlock(
            type="markdown",
            title="Document Search Error",
            content=f"Error performing document search: {str(exc)}"
        )
        return [error_block], ["document_search"]


def execute_universal(
    question: str, mode: str, tenant_id: str
) -> ExecutorResult:
    """Universal executor for relation, metric, history, and hist modes.

    Uses the CI Orchestrator for execution.
    """
    from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner
    from app.modules.ops.services.ci.planner.plan_schema import Plan
    import asyncio

    logger = logging.getLogger(__name__)
    logger.info(f"Executing universal mode '{mode}' for question: {question[:100]}")

    try:
        # Create runner with tenant_id
        runner = CIOrchestratorRunner(
            question=question,
            tenant_id=tenant_id,
        )

        # Create a simple plan based on mode
        plan = _create_simple_plan(mode)

        # Run the orchestrator
        result = runner.run(plan_output=None)

        # Convert result to ExecutorResult
        blocks = _convert_result_to_blocks(result, mode)
        used_tools = result.get("used_tools", [])

        return ExecutorResult(
            blocks=blocks,
            used_tools=used_tools,
            tool_calls=result.get("tool_calls", []),
            references=[],
            summary={
                "status": "success",
                "mode": mode,
                "question": question,
            },
        )
    except Exception as exc:
        logger.exception(f"Universal executor failed for mode '{mode}'")
        # Return empty blocks on error
        return ExecutorResult(
            blocks=[],
            used_tools=[],
            tool_calls=[],
            references=[],
            summary={
                "status": "error",
                "error": str(exc),
                "mode": mode,
            },
        )


def _create_simple_plan(mode: str) -> Any:
    """Create a simple plan based on mode."""
    from app.modules.ops.services.ci.planner.plan_schema import (
        Plan,
        AggregateStage,
        MetricStage,
        HistoryStage,
        OutputStage,
    )
    from app.modules.ops.services.ci.planner.plan_schema import ExecutionStrategy

    # Build stages based on mode
    stages = []
    aggregate = None
    metric = None
    history = None

    if mode in ("metric", "all", "hist"):
        # Add aggregate stage for CI grouping
        aggregate = AggregateStage(
            enabled=True,
            group_by=["ci_type"],
            metrics=["ci_name"],
            filters=[],
            top_n=10,
        )

    if mode in ("metric", "all"):
        # Add metric stage
        metric = MetricStage(
            enabled=True,
            primary="cpu_usage",
            agg="MAX",
            time_range="last_24h",
        )

    if mode in ("history", "all", "hist"):
        # Add history stage
        history = HistoryStage(
            enabled=True,
            event_types=[],
            limit=10,
        )

    return Plan(
        graph=None,
        aggregate=aggregate,
        metric=metric,
        history=history,
        list=None,
        auto=None,
        output=OutputStage(enabled=True),
        execution_strategy=ExecutionStrategy.ORCHESTRATION,
        policy=None,
    )


def _convert_result_to_blocks(result: dict, mode: str) -> list:
    """Convert orchestrator result to answer blocks."""
    blocks = []

    # Try to extract data from result
    execution_results = result.get("execution_results", {})

    for tool_id, tool_result in execution_results.items():
        if isinstance(tool_result, dict) and tool_result.get("success"):
            data = tool_result.get("data", {})
            rows = data.get("rows", []) if isinstance(data, dict) else []
            columns = data.get("columns") if isinstance(data, dict) else None

            if not rows:
                continue

            table_columns: list[str] = []
            table_rows: list[list[str]] = []

            if isinstance(rows[0], dict):
                if isinstance(columns, list) and columns:
                    table_columns = [str(col) for col in columns]
                else:
                    table_columns = [str(col) for col in rows[0].keys()]
                for row in rows:
                    table_rows.append(
                        ["" if row.get(col) is None else str(row.get(col)) for col in table_columns]
                    )
            else:
                if isinstance(columns, list) and columns:
                    table_columns = [str(col) for col in columns]
                else:
                    row_len = len(rows[0]) if hasattr(rows[0], "__len__") else 0
                    table_columns = [f"col_{idx + 1}" for idx in range(row_len)]
                for row in rows:
                    if isinstance(row, (list, tuple)):
                        table_rows.append(["" if cell is None else str(cell) for cell in row])
                    else:
                        table_rows.append(["" if row is None else str(row)])

            blocks.append(TableBlock(
                title=f"{tool_id} Results",
                columns=table_columns,
                rows=table_rows,
            ))

    return blocks


OpsMode = Literal["config", "history", "relation", "metric", "all", "hist", "graph", "document"]


def _get_required_tenant_id(settings: Any) -> str:
    """Get tenant_id from settings or request context, raise error if missing."""
    # First try to get from settings
    tenant_id = getattr(settings, "tenant_id", None)

    # If not in settings, try to get from request context
    if not tenant_id:
        context = get_request_context()
        tenant_id = context.get("tenant_id")

    # Strip whitespace and validate
    if not tenant_id or tenant_id == "-":
        raise ValueError(
            "tenant_id is required in settings or request context. "
            "Please ensure tenant_id is set in the request settings."
        )
    return tenant_id


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


def handle_ops_query(mode: OpsMode, question: str) -> tuple[AnswerEnvelope, dict[str, Any] | None]:
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

    # Build trace data for client (same as persist payload)
    trace_data = {
        "plan_validated": None,  # OPS query doesn't use plan
        "policy_decisions": None,  # OPS query doesn't use policy
        "tool_calls": trace_payload.get("tool_calls", []),
        "references": trace_payload.get("references", []),
        "used_tools": trace_payload.get("used_tools", []),
        "summary": trace_payload.get("summary", {}),
        "stage_inputs": None,  # OPS query doesn't have stages
        "stage_outputs": None,  # OPS query doesn't have stages
    }

    return envelope, trace_data


def _execute_real_mode(
    mode: OpsMode, question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str]]:
    # Universal executor for relation, metric, history modes
    if mode in ("relation", "metric", "history", "hist"):
        tenant_id = _get_required_tenant_id(settings)
        result = execute_universal(question, mode, tenant_id)
        return result.blocks, result.used_tools

    # Document search executor
    if mode == "document":
        tenant_id = _get_required_tenant_id(settings)
        return run_document(question, tenant_id=tenant_id, settings=settings)

    # Legacy executors for other modes
    executor = {
        "config": _run_config,
        "graph": _run_graph,
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
    tenant_id = _get_required_tenant_id(settings)
    try:
        return run_config_executor(question, tenant_id=tenant_id)
    except Exception:
        placeholder_blocks = _build_config_placeholder(question, settings)
        return placeholder_blocks, ["placeholder"]


def _run_history(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = _get_required_tenant_id(settings)
    return run_hist(question, tenant_id=tenant_id)


def _run_ci_search(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = _get_required_tenant_id(settings)
    return run_ci_search(question, tenant_id=tenant_id)


def _run_graph(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = _get_required_tenant_id(settings)
    return run_graph(question, tenant_id=tenant_id)


def _run_metric(
    question: str, settings: Any
) -> ExecutorResult | tuple[list[AnswerBlock], list[str]]:
    tenant_id = _get_required_tenant_id(settings)
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
    tenant_id = _get_required_tenant_id(settings)
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
        time_range = resolve_time_range(question, datetime.now(get_settings().timezone_offset))
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
    if mode == "document":
        blocks.append(_mock_document_results())
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
    now = datetime.now(get_settings().timezone_offset)
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


def _mock_document_results() -> TableBlock:
    return TableBlock(
        type="table",
        title="Document Search Results",
        columns=["Document", "Content Preview", "Relevance"],
        rows=[
            ["system_architecture.pdf", "System architecture overview with component...", "92%"],
            ["deployment_guide.md", "Step-by-step deployment instructions for...", "87%"],
            ["troubleshooting.md", "Common troubleshooting steps and solutions...", "78%"],
        ],
    )


def _timeseries_point(
    origin: datetime, minutes_delta: int, value: int
) -> TimeSeriesPoint:
    timestamp = (origin + timedelta(minutes=minutes_delta)).isoformat()
    return TimeSeriesPoint(timestamp=timestamp, value=float(value))
