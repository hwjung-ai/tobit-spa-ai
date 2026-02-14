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
    ChartBlock,
    GraphBlock,
    GraphEdge,
    GraphNode,
    MarkdownBlock,
    NetworkBlock,
    NumberBlock,
    PathBlock,
    ReferenceItem,
    ReferencesBlock,
    TableBlock,
    TextBlock,
    TimeSeriesBlock,
    TimeSeriesPoint,
    TimeSeriesSeries,
)
from schemas.tool_contracts import ExecutorResult

from app.modules.inspector.service import persist_execution_trace

# Legacy executors removed for generic orchestration
# All executor functionality should be implemented as Tool Assets
from .ops_all_runner import OpsAllRunner
from .query_decomposition_runner import QueryDecompositionRunner
from .resolvers import resolve_ci, resolve_time_range

# Legacy executors removed - all use OpsOrchestratorRunner


# All executors now use OpsOrchestratorRunner via execute_universal


def _generate_rag_answer(question: str, context: str, logger: logging.Logger) -> str:
    """Generate an answer using LLM with retrieved document context (RAG)."""
    from app.llm.client import get_llm_client

    settings = get_settings()
    llm = get_llm_client()

    system_prompt = (
        "You are a helpful assistant that answers questions based on the provided document context. "
        "Answer the user's question using ONLY the information from the document context below. "
        "If the context doesn't contain enough information, say so clearly. "
        "Always cite which document/page the information comes from. "
        "Respond in the same language as the user's question."
    )

    user_prompt = f"Document context:\n{context}\n\nQuestion: {question}"

    try:
        request_kwargs: dict[str, Any] = {
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "model": settings.chat_model,
        }
        if "gpt-5" not in settings.chat_model:
            request_kwargs["temperature"] = 0.1

        response = llm.create_response(**request_kwargs)
        answer = llm.get_output_text(response)

        if answer:
            logger.info(f"RAG answer generated: {len(answer)} chars")
            return answer
        else:
            return "LLM did not generate a response. Here are the relevant document excerpts found."

    except Exception as exc:
        logger.warning(f"LLM RAG generation failed, falling back to search results: {exc}")
        # Fallback: return context snippets as-is
        return f"(LLM unavailable - showing raw search results)\n\n{context}"


def execute_universal(
    question: str, mode: str, tenant_id: str
) -> ExecutorResult:
    """Universal executor for config, relation, metric, history, hist, graph, and document modes.

    Uses the OPS Orchestrator for execution.
    """
    import asyncio

    # Ensure tools are initialized (no-op if already done)
    import app.modules.ops.services.orchestration.tools.registry_init  # noqa: F401
    from app.modules.ops.services.orchestration.orchestrator.runner import OpsOrchestratorRunner
    from app.modules.ops.services.orchestration.planner.plan_schema import Plan

    logger = logging.getLogger(__name__)
    logger.info(f"Executing universal mode '{mode}' for question: {question[:100]}")

    try:
        # Create plan for the mode (pass question for document mode keyword extraction)
        plan = _create_simple_plan(mode, question)
        policy_trace = {
            "mode": mode,
            "source": "execute_universal",
            "policies_applied": [],
        }

        # Create runner with required arguments
        runner = OpsOrchestratorRunner(
            plan=plan,
            plan_raw=plan,
            tenant_id=tenant_id,
            question=question,
            policy_trace=policy_trace,
        )

        # Run the orchestrator
        logger.info(f"Running orchestrator for {mode} mode with question: {question[:80]}")
        result = runner.run(plan_output=None)
        logger.info(
            f"Orchestrator returned result type: {type(result)}, "
            f"keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}"
        )

        # The runner returns {"answer", "blocks", "trace", "next_actions", "meta"}
        # Use the blocks directly from the runner output first
        blocks = []
        if isinstance(result, dict):
            # 1) Try runner's pre-built blocks (usually markdown summary from compose)
            runner_blocks = result.get("blocks", [])
            if runner_blocks:
                blocks = _convert_runner_blocks(runner_blocks, mode)
                logger.info(f"Used {len(blocks)} blocks from runner output")

            # 2) Extract execution_results from trace for data blocks
            trace_data = result.get("trace", {})
            execution_results = []
            for stage_out in (trace_data.get("stage_outputs") or []):
                if isinstance(stage_out, dict):
                    sr = stage_out.get("result", {})
                    if isinstance(sr, dict):
                        base_result = sr.get("base_result", sr)
                        er = base_result.get("execution_results", [])
                        if er:
                            execution_results = er
                            break

            # 3) Augment with data blocks from execution_results
            if execution_results:
                data_blocks = _build_data_blocks_from_results(execution_results, mode)
                if data_blocks:
                    blocks.extend(data_blocks)
                    logger.info(f"Added {len(data_blocks)} data blocks from execution_results")

            # 4) Fallback: if no blocks at all, use answer text
            if not blocks and result.get("answer"):
                blocks = [MarkdownBlock(
                    type="markdown",
                    title=f"{mode.capitalize()} Result",
                    content=str(result["answer"]),
                )]
                logger.info("Used answer text as markdown fallback")

        logger.info(f"Final: {len(blocks)} blocks for {mode} mode")
        meta = result.get("meta", {}) if isinstance(result, dict) else {}
        used_tools = meta.get("used_tools", result.get("used_tools", []) if isinstance(result, dict) else [])

        # Convert AnswerBlock pydantic models to dicts for ExecutorResult
        blocks_as_dicts = []
        for b in blocks:
            if isinstance(b, dict):
                blocks_as_dicts.append(b)
            elif hasattr(b, "model_dump"):
                blocks_as_dicts.append(b.model_dump())
            else:
                blocks_as_dicts.append({"type": "text", "text": str(b)})

        trace = result.get("trace", {}) if isinstance(result, dict) else {}
        tool_calls_raw = trace.get("tool_calls", result.get("tool_calls", []) if isinstance(result, dict) else [])
        return ExecutorResult(
            blocks=blocks_as_dicts,
            used_tools=used_tools if isinstance(used_tools, list) else [],
            tool_calls=tool_calls_raw if isinstance(tool_calls_raw, list) else [],
            references=[],
            summary={
                "status": "success",
                "mode": mode,
                "question": question,
            },
        )
    except Exception as exc:
        logger.exception(f"Universal executor failed for mode '{mode}': {str(exc)}")
        # Return error info instead of empty blocks
        error_msg = str(exc)
        return ExecutorResult(
            blocks=[],
            used_tools=[],
            tool_calls=[],
            references=[],
            summary={
                "status": "error",
                "error": error_msg,
                "mode": mode,
                "error_type": type(exc).__name__,
            },
        )


def _create_simple_plan(mode: str, question: str = "") -> Any:
    """Create a simple plan based on mode."""
    from app.modules.ops.services.orchestration.planner.plan_schema import (
        AggregateSpec,
        ExecutionStrategy,
        GraphSpec,
        HistorySpec,
        Intent,
        MetricSpec,
        OutputSpec,
        Plan,
        PlanMode,
        PrimarySpec,
        View,
    )

    # Base configuration
    intent = Intent.LOOKUP
    view = View.SUMMARY
    plan_mode = PlanMode.CI

    # Initialize specs
    primary = PrimarySpec(limit=10)
    aggregate = AggregateSpec()
    graph = GraphSpec()
    metric = None
    history = HistorySpec()
    output = OutputSpec()

    # Configure based on mode
    mode_hint = mode  # Store mode for tool selection filtering

    if mode == "config":
        # Config mode: Lookup CI with aggregation
        intent = Intent.LOOKUP
        view = View.SUMMARY
        aggregate = AggregateSpec(
            group_by=["ci_type"],
            metrics=["ci_name", "ci_code"],
            filters=[],
            top_n=20,
        )
        primary = PrimarySpec(
            limit=10,
            tool_type="ci_lookup"
        )

    elif mode == "graph":
        # Graph mode: Analyze CI relationships (independent)
        intent = Intent.EXPAND
        view = View.NEIGHBORS
        primary = PrimarySpec(limit=5)  # Default, won't execute (no keywords)
        aggregate = AggregateSpec()  # Default empty
        graph = GraphSpec(
            depth=2,
            view=View.NEIGHBORS,
            tool_type="ci_graph"
        )

    elif mode == "document":
        # Document mode: Document search and RAG
        intent = Intent.LOOKUP
        view = View.SUMMARY
        # Extract keywords from question for document search
        doc_keywords = [question] if question else []
        primary = PrimarySpec(
            limit=5,
            tool_type="document_search",
            keywords=doc_keywords
        )
        # Add document-specific specs if needed
        aggregate = AggregateSpec()

    elif mode in ("metric", "all"):
        # Metric mode
        intent = Intent.AGGREGATE
        aggregate = AggregateSpec(
            group_by=["ci_type"],
            metrics=["ci_name"],
            filters=[],
            top_n=10,
        )
        metric = MetricSpec(
            metric_name="cpu_usage",
            agg="max",
            time_range="last_24h",
            mode="aggregate",
        )

    elif mode in ("hist", "history"):
        # History mode - independent history query
        intent = Intent.LIST
        primary = PrimarySpec(limit=10)  # Default, won't execute (no keywords)
        aggregate = AggregateSpec()  # Default empty
        history = HistorySpec(
            enabled=True,
            source="work_and_maintenance",
            time_range="all_time",
            limit=30,
        )

    return Plan(
        intent=intent,
        view=view,
        mode=plan_mode,
        primary=primary,
        aggregate=aggregate,
        graph=graph,
        metric=metric,
        history=history,
        output=output,
        execution_strategy=ExecutionStrategy.SERIAL,
        mode_hint=mode_hint,  # Pass mode hint for tool selection
    )


def _build_data_blocks_from_results(
    execution_results: list, mode: str
) -> list:
    """Build data blocks (table, graph) from execution_results.

    Converts raw tool results into structured blocks for display.
    """
    blocks = []

    for er in execution_results:
        if not isinstance(er, dict) or not er.get("success"):
            continue

        tool_name = er.get("tool_name", "")
        data = er.get("data", {})
        if not isinstance(data, dict):
            continue

        rows = data.get("rows", [])
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # History/aggregate results → table block
        if tool_name in ("history", "aggregate") and rows:
            if not rows:
                continue
            # Build column list from first row
            first_row = rows[0] if isinstance(rows[0], dict) else {}
            columns = [k for k in first_row.keys() if k != "orchestration"]
            # Build row data
            table_rows = []
            for row in rows:
                if isinstance(row, dict):
                    table_rows.append([
                        str(row.get(col, "")) for col in columns
                    ])

            title_map = {
                "history": "작업이력 / 유지보수 점검 이력",
                "aggregate": "집계 결과",
            }
            blocks.append({
                "type": "table",
                "title": title_map.get(tool_name, tool_name),
                "columns": columns,
                "rows": table_rows,
            })

        # Graph results → network block
        if tool_name == "graph" and (nodes or edges):
            blocks.append({
                "type": "network",
                "title": "CI 관계도",
                "nodes": nodes,
                "edges": edges,
            })

        # Document search results → references block
        if tool_name == "document_search" and data.get("results"):
            search_results = data["results"]
            reference_items = []

            for item in search_results:
                doc_name = item.get("document_name", "Unknown")
                content = item.get("chunk_text", "")
                snippet = content[:200] + "..." if len(content) > 200 else content
                relevance = item.get("relevance_score", 0)
                document_id = item.get("document_id")
                chunk_id = item.get("chunk_id")
                page_number = item.get("page_number")

                # Generate document URL
                url = None
                if document_id:
                    # Create viewer URL with chunk ID for highlighting
                    # Use /api/documents/... path for actual file serving
                    url = f"/api/documents/{document_id}/viewer"
                    params = []
                    if chunk_id:
                        params.append(f"chunkId={chunk_id}")
                    if page_number:
                        params.append(f"page={page_number}")

                    if params:
                        url += f"?{'&'.join(params)}"

                reference_items.append({
                    "title": doc_name,
                    "kind": "document",
                    "snippet": snippet,
                    "url": url,
                    "payload": {
                        "relevance_score": relevance,
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "page_number": page_number
                    }
                })

            blocks.append({
                "type": "references",
                "title": "근거문서",
                "items": reference_items
            })

    return blocks


def _convert_runner_blocks(runner_blocks: list, mode: str) -> list[AnswerBlock]:
    """Convert runner output blocks (plain dicts) to AnswerBlock pydantic models."""
    _log = logging.getLogger(__name__)
    blocks: list[AnswerBlock] = []

    for blk in runner_blocks:
        if not isinstance(blk, dict):
            # Already a pydantic model
            blocks.append(blk)
            continue

        btype = blk.get("type", "")
        try:
            if btype == "text":
                blocks.append(TextBlock(type="text", text=blk.get("text", ""), title=blk.get("title")))
            elif btype == "markdown":
                blocks.append(MarkdownBlock(type="markdown", content=blk.get("content", ""), title=blk.get("title")))
            elif btype == "table":
                blocks.append(TableBlock(
                    type="table",
                    title=blk.get("title"),
                    columns=blk.get("columns", []),
                    rows=blk.get("rows", []),
                ))
            elif btype == "number":
                blocks.append(NumberBlock(
                    type="number",
                    title=blk.get("title"),
                    value=float(blk.get("value", 0)),
                    unit=blk.get("unit"),
                ))
            elif btype == "network":
                blocks.append(NetworkBlock(
                    type="network",
                    title=blk.get("title"),
                    nodes=blk.get("nodes", []),
                    edges=blk.get("edges", []),
                    meta=blk.get("meta", {}),
                ))
            elif btype == "path":
                blocks.append(PathBlock(
                    type="path",
                    title=blk.get("title"),
                    nodes=blk.get("nodes", []),
                    edges=blk.get("edges", []),
                    hop_count=blk.get("hop_count", 0),
                ))
            elif btype == "chart":
                blocks.append(ChartBlock(
                    type="chart",
                    chart_type=blk.get("chart_type", "line"),
                    title=blk.get("title"),
                    x=blk.get("x", ""),
                    series=blk.get("series", []),
                    meta=blk.get("meta", {}),
                ))
            elif btype == "graph":
                nodes = [
                    GraphNode(
                        id=str(n.get("id", "")),
                        data=n.get("data", {"label": ""}),
                        position=n.get("position", {"x": 0.0, "y": 0.0}),
                    )
                    for n in blk.get("nodes", [])
                    if isinstance(n, dict)
                ]
                edges = [
                    GraphEdge(
                        id=str(e.get("id", "")),
                        source=str(e.get("source", "")),
                        target=str(e.get("target", "")),
                        label=e.get("label"),
                    )
                    for e in blk.get("edges", [])
                    if isinstance(e, dict)
                ]
                blocks.append(GraphBlock(type="graph", title=blk.get("title"), nodes=nodes, edges=edges))
            elif btype == "timeseries":
                series_list = []
                for s in blk.get("series", []):
                    points = [TimeSeriesPoint(timestamp=p["timestamp"], value=p["value"]) for p in s.get("data", [])]
                    series_list.append(TimeSeriesSeries(name=s.get("name"), data=points))
                blocks.append(TimeSeriesBlock(type="timeseries", title=blk.get("title"), series=series_list))
            elif btype == "references":
                # Convert references block for document search results
                reference_items = []
                for item in blk.get("items", []):
                    if isinstance(item, dict):
                        reference_items.append(ReferenceItem(
                            title=item.get("title", ""),
                            kind=item.get("kind", "unknown"),
                            snippet=item.get("snippet", ""),
                            url=item.get("url"),
                            payload=item.get("payload", {}),
                        ))
                    elif isinstance(item, ReferenceItem):
                        reference_items.append(item)
                blocks.append(ReferencesBlock(
                    type="references",
                    title=blk.get("title"),
                    items=reference_items,
                ))
            else:
                # Unknown type: wrap as markdown
                _log.warning(f"Unknown runner block type '{btype}', wrapping as markdown")
                blocks.append(MarkdownBlock(
                    type="markdown",
                    title=blk.get("title"),
                    content=str(blk.get("text") or blk.get("content") or blk),
                ))
        except Exception as exc:
            _log.warning(f"Failed to convert runner block type={btype}: {exc}")
            blocks.append(MarkdownBlock(
                type="markdown",
                title="Data",
                content=str(blk),
            ))

    return blocks


def _convert_result_to_blocks(result: dict, mode: str) -> list:
    """Convert orchestrator execution_results dict to answer blocks."""
    blocks = []

    # Try to extract data from result
    execution_results = result.get("execution_results", {})

    for tool_id, tool_result in execution_results.items():
        if isinstance(tool_result, dict) and tool_result.get("success"):
            data = tool_result.get("data", {})

            # Check if this is graph data
            if mode == "graph" and isinstance(data, dict):
                nodes = data.get("nodes", [])
                edges = data.get("edges", [])

                if nodes or edges:
                    # Convert to GraphBlock format
                    graph_nodes = []
                    for node in nodes:
                        if isinstance(node, dict):
                            graph_nodes.append(GraphNode(
                                id=str(node.get("id", node.get("ci_code", f"n{len(graph_nodes)}"))),
                                data={"label": str(node.get("label", node.get("ci_name", "Unknown")))},
                                position={"x": 0.0, "y": 0.0}  # Let frontend handle layout
                            ))

                    graph_edges = []
                    for edge in edges:
                        if isinstance(edge, dict):
                            graph_edges.append(GraphEdge(
                                id=str(edge.get("id", f"e{len(graph_edges)}")),
                                source=str(edge.get("source", edge.get("from", ""))),
                                target=str(edge.get("target", edge.get("to", ""))),
                                label=str(edge.get("label", edge.get("relation", "")))
                            ))

                    if graph_nodes:
                        blocks.append(GraphBlock(
                            type="graph",
                            title=f"{tool_id} Graph",
                            nodes=graph_nodes,
                            edges=graph_edges
                        ))
                        continue

            # Otherwise handle as table data
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

    # If no blocks generated, add a message block
    if not blocks:
        blocks.append(MarkdownBlock(
            type="markdown",
            title="No Results",
            content=f"No data found for {mode} mode query. The query executed successfully but returned no results."
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
                    error = _fallback_error_message(status) or executor_result.summary.get("error", "Unknown error")
                # In real mode, do NOT replace with mock blocks
        route_reason = "OPS real mode"
        summary = f"Real mode response for {mode}"

    # Log block generation status
    logger = logging.getLogger(__name__)
    if not blocks:
        logger.warning(f"Empty blocks returned for {mode} mode (ops_mode={settings.ops_mode})")
        # In real mode, don't use fallback - show error instead
        if settings.ops_mode == "real":
            error = error or f"No data available for {mode} mode"
            blocks = [MarkdownBlock(
                type="markdown",
                title="No Data",
                content=f"❌ Unable to retrieve {mode} mode data.\n\nError: {error}\n\nPlease check:\n- Data availability\n- Query syntax\n- System configuration",
            )]
            fallback = True
        else:
            # In mock mode, use fallback data
            logger.info("Mock mode: using fallback blocks")
            blocks = _build_mock_blocks(mode, question)
            used_tools = ["fallback_mock"]
            fallback = True
            if not summary:
                summary = f"Fallback mock data for {mode}"
    else:
        logger.info(f"Successfully generated {len(blocks)} blocks for {mode} mode (ops_mode={settings.ops_mode})")

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
    # Config mode: use universal executor with orchestration
    if mode == "config":
        tenant_id = _get_required_tenant_id(settings)
        result = execute_universal(question, "config", tenant_id)
        return result.blocks, result.used_tools

    # Universal executor for orchestrator-based modes
    if mode in ("relation", "metric", "history", "hist", "graph"):
        tenant_id = _get_required_tenant_id(settings)
        result = execute_universal(question, mode, tenant_id)
        return result.blocks, result.used_tools

    # Document search executor - use real document search
    if mode == "document":
        tenant_id = _get_required_tenant_id(settings)
        _log = logging.getLogger(__name__)
        try:
            result = execute_universal(question, "document", tenant_id)
            # Check if we got meaningful results
            if result.blocks and len(result.blocks) > 0:
                # Check if we got actual document results (not just error messages)
                has_references = any(block.get("type") == "references" for block in result.blocks)
                if has_references:
                    return result.blocks, result.used_tools
            # Fallback to direct search if no meaningful results
            _log.warning("No document results from orchestrator, falling back to direct search")
            return _run_document_fallback(question, tenant_id)
        except Exception as exc:
            _log.warning(f"Document orchestrator failed: {exc}, falling back to direct search")
            # Fallback: direct document search
            return _run_document_fallback(question, tenant_id)

    # All mode (orchestration)
    if mode == "all":
        return _run_all(question, settings)

    raise NotImplementedError(f"No executor for mode {mode}")


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
    # For ALL mode, get real document results first
    blocks = []
    tenant_id = _get_required_tenant_id(settings)

    # Get real document search results
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Use execute_universal to get document results
        doc_result = execute_universal(question, "document", tenant_id)

        # Extract references blocks from document result
        if doc_result.blocks:
            # Find references block
            for block in doc_result.blocks:
                if block.get("type") == "references":
                    blocks.append(block)
                    logger.info(f"Added {len(block.get('items', []))} document references to ALL mode")
                    break
    except Exception as exc:
        logger.warning(f"Failed to get document results for ALL mode: {exc}")

    # Fallback to empty references if no document results
    if not blocks:
        blocks.append({
            "type": "references",
            "title": "근거문서",
            "items": []
        })

    # Add markdown block
    blocks.append({
        "type": "markdown",
        "title": "전체 검색 결과",
        "content": f"'{question}'에 대한 모드별 검색 결과입니다.\n\n1. **문서 검색**: 문서를 검색합니다\n2. **구성 정보**: CI/CD 파이프라인 상태 확인\n3. **성능 지표**: 시스템 리소스 사용률 모니터링\n\n상세한 내용은 각 섹션의 참조문서를 확인하세요."
    })

    return blocks, ["document_search", "ci_lookup", "metrics"], None
    # Use intelligent orchestration similar to /ops/ask
    if settings.ops_enable_langgraph:
        if settings.openai_api_key:
            try:
                return _run_all_langgraph(question, settings)
            except Exception:
                logging.exception(
                    "LangGraph ALL execution failed; falling back to orchestration"
                )
                return _run_all_orchestration(question, settings)
        logging.warning(
            "LangGraph requested but OpenAI API key missing; using orchestration ALL executor"
        )
    return _run_all_orchestration(question, settings)


def _run_all_langgraph(
    question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str], str | None]:
    runner = OpsAllRunner(settings)
    return runner.run(question)


def _run_all_orchestration(
    question: str, settings: Any
) -> tuple[list[AnswerBlock], list[str], str | None]:
    """Intelligent orchestration for ALL mode using planner and orchestrator."""
    import app.modules.ops.services.orchestration.tools.registry_init  # noqa: F401
    from app.modules.ops.services.orchestration.orchestrator.runner import OpsOrchestratorRunner
    from app.modules.ops.services.orchestration.planner.plan_schema import Plan

    logger = logging.getLogger(__name__)
    logger.info(f"Running intelligent ALL orchestration for: {question[:100]}")

    try:
        # Create a comprehensive plan for ALL mode
        plan = _create_all_plan(question)
        policy_trace = {
            "mode": "all",
            "source": "orchestration",
            "policies_applied": [],
        }

        # Create runner with required arguments
        runner = OpsOrchestratorRunner(
            plan=plan,
            plan_raw=plan,
            tenant_id=_get_required_tenant_id(settings),
            question=question,
            policy_trace=policy_trace,
        )

        # Run the orchestrator
        logger.info("Running orchestrator for ALL mode")
        result = runner.run(plan_output=None)

        # Extract blocks from result
        blocks = []
        if isinstance(result, dict):
            # Try to get blocks from runner
            runner_blocks = result.get("blocks", [])
            if runner_blocks:
                blocks = _convert_runner_blocks(runner_blocks, "all")
            else:
                # Fallback to answer text
                answer = result.get("answer")
                if answer:
                    blocks = [MarkdownBlock(
                        type="markdown",
                        title="ALL Results",
                        content=str(answer),
                    )]

        # Get metadata
        meta = result.get("meta", {}) if isinstance(result, dict) else {}
        used_tools = meta.get("used_tools", result.get("used_tools", []) if isinstance(result, dict) else [])

        logger.info(f"ALL orchestration completed with {len(blocks)} blocks")
        return list(blocks), used_tools, None

    except Exception as exc:
        logger.exception(f"ALL orchestration failed: {exc}")
        # Fall back to simple rule-based execution
        return _run_all_rule_based(question, settings)


def _create_all_plan(question: str) -> Any:
    """Create a comprehensive plan for ALL mode."""
    from app.modules.ops.services.orchestration.planner.plan_schema import (
        AggregateSpec,
        ExecutionStrategy,
        GraphSpec,
        HistorySpec,
        Intent,
        MetricSpec,
        OutputSpec,
        Plan,
        PlanMode,
        PrimarySpec,
        View,
    )

    # Analyze question to determine which modes to include
    intent = Intent.LOOKUP
    view = View.SUMMARY
    plan_mode = PlanMode.CI

    # Initialize all specs
    primary = PrimarySpec(limit=10)
    aggregate = AggregateSpec()
    graph = GraphSpec()
    metric = MetricSpec()
    history = HistorySpec()
    output = OutputSpec()

    # Determine which sub-modes to activate based on question
    question_lower = question.lower()

    # Config: Always include for CI overview
    intent = Intent.LOOKUP
    primary = PrimarySpec(limit=5, tool_type="ci_lookup")
    aggregate = AggregateSpec(
        group_by=["ci_type"],
        metrics=["ci_name", "ci_code"],
        filters=[],
        top_n=20,
    )

    # History: Include if time-related keywords
    if any(kw in question_lower for kw in ["최근", "이력", "정보", "변경", "작업"]):
        history = HistorySpec(
            enabled=True,
            source="work_and_maintenance",
            time_range="all_time",
            limit=20,
        )

    # Metrics: Include if performance-related keywords
    if any(kw in question_lower for kw in ["성능", "cpu", "memory", "사용률", "메트릭"]):
        metric = MetricSpec(
            metric_name="cpu_usage",
            agg="max",
            time_range="last_24h",
            mode="aggregate",
        )
        intent = Intent.AGGREGATE

    # Graph: Include if relationship/dependency keywords
    if any(kw in question_lower for kw in ["연결", "의존", "영향", "관계", "경로"]):
        graph = GraphSpec(
            depth=2,
            view=View.NEIGHBORS,
            tool_type="ci_graph"
        )
        intent = Intent.EXPAND

    return Plan(
        intent=intent,
        view=view,
        mode=plan_mode,
        primary=primary,
        aggregate=aggregate,
        graph=graph,
        metric=metric,
        history=history,
        output=output,
        execution_strategy=ExecutionStrategy.SERIAL,
        mode_hint="all",  # ALL mode: no filtering
    )


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
            tenant_id = _get_required_tenant_id(settings)
            result = execute_universal(question, "config", tenant_id)
            return (
                result.blocks,
                result.used_tools,
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
            content=f"### {mode.upper()} Mode Response\nQuestion: {question}\nShowing sample data for {mode} scenario.",
        ),
    ]

    # Mode-specific blocks
    if mode == "metric":
        blocks.extend(_mock_metric_blocks(question))
    elif mode == "hist" or mode == "history":
        blocks.append(_mock_table())
        blocks.append(MarkdownBlock(
            type="markdown",
            title="Event Details",
            content="Recent infrastructure events and changes",
        ))
    elif mode == "graph" or mode == "relation":
        blocks.append(_mock_graph())
        blocks.append(MarkdownBlock(
            type="markdown",
            title="Dependency Analysis",
            content="CI relationships and topology visualization",
        ))
    elif mode == "config":
        blocks.append(_mock_table())
    elif mode == "document":
        blocks.append(_mock_document_results())
    elif mode == "all":
        blocks.append(_mock_table())
        blocks.append(_mock_timeseries())
        blocks.append(_mock_graph())
    else:
        blocks.append(_mock_table())

    # Add references for non-document modes
    if mode != "document":
        blocks.append(
            ReferencesBlock(
                type="references",
                title="References",
                items=[
                    ReferenceItem(
                        kind="sql",
                        title="CI Lookup Query",
                        payload={"query": "SELECT * FROM ci WHERE ci_type = 'SYSTEM' LIMIT 10;"},
                    ),
                    ReferenceItem(
                        kind="cypher",
                        title="Relationship Query",
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


def _mock_metric_blocks(question: str) -> list[AnswerBlock]:
    """Generate mock metric blocks based on question."""
    now = datetime.now(get_settings().timezone_offset)
    blocks: list[AnswerBlock] = []

    # Add summary
    blocks.append(MarkdownBlock(
        type="markdown",
        title="Metric Summary",
        content=f"Metric data for: {question}\n\nShowing CPU usage metrics with trend analysis."
    ))

    # Generate more detailed timeseries data for CPU metrics
    # Extract server name from question if possible
    server_name = "MES Server 06" if "06" in question or "Server 06" in question else "Default Server"

    cpu_data = [
        _timeseries_point(now, -120, 35),
        _timeseries_point(now, -100, 38),
        _timeseries_point(now, -80, 42),
        _timeseries_point(now, -60, 48),
        _timeseries_point(now, -40, 52),
        _timeseries_point(now, -20, 58),
        _timeseries_point(now, 0, 62),
    ]

    cpu_series = TimeSeriesSeries(
        name=f"{server_name} CPU Usage (%)",
        data=cpu_data,
    )

    blocks.append(TimeSeriesBlock(
        type="timeseries",
        title=f"{server_name} - CPU Usage (Last 2 Hours)",
        series=[cpu_series]
    ))

    # Add summary table
    blocks.append(TableBlock(
        type="table",
        title="Performance Summary",
        columns=["Metric", "Current", "Average", "Peak", "Status"],
        rows=[
            ["CPU Usage", "62%", "48%", "72%", "Normal"],
            ["Memory Usage", "58%", "55%", "68%", "Normal"],
            ["Disk I/O", "24%", "31%", "45%", "Normal"],
            ["Network I/O", "12%", "18%", "32%", "Normal"],
        ]
    ))

    return blocks


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


def _run_document_fallback(question: str, tenant_id: str) -> tuple[list[AnswerBlock], list[str]]:
    """Fallback document search using search_crud."""
    import logging
    _log = logging.getLogger(__name__)
    from core.db import get_session

    blocks = []
    used_tools = []

    try:
        session = next(get_session())

        # Use search_crud for text search
        from app.modules.document_processor.search_crud import search_chunks_by_text

        results = search_chunks_by_text(
            session=session,
            query=question,
            tenant_id=tenant_id,
            top_k=5,
        )

        if results:
            # Build references block
            reference_items = []
            for row in results:
                document_id = row["document_id"]
                chunk_id = row["id"]
                page_number = row["page_number"]
                content = row["text"]
                snippet = content[:200] + "..." if len(content) > 200 else content

                _log.info(f"Document search result: {row['filename']}, snippet length: {len(snippet)}")

                # Generate URL - use /api/documents/... for actual file serving
                url = f"/api/documents/{document_id}/viewer"
                params = []
                if chunk_id:
                    params.append(f"chunkId={chunk_id}")
                if page_number:
                    params.append(f"page={page_number}")
                if params:
                    url += f"?{'&'.join(params)}"

                reference_items.append({
                    "title": row["filename"],
                    "kind": "document",
                    "snippet": snippet,
                    "url": url,
                    "payload": {
                        "relevance_score": row["score"],
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "page_number": page_number
                    }
                })

            blocks.append({
                "type": "references",
                "title": "참고 문서",
                "items": reference_items
            })

            used_tools.append("document_search")
        else:
            # No results found - provide helpful message
            _log.info(f"No document search results for query: {question[:100]}")
            blocks.append({
                "type": "markdown",
                "title": "검색 결과 없음",
                "content": f"'{question}'와 일치하는 문서를 찾을 수 없습니다.\n\n검색 팁:\n- 검색어를 간단하게 줄여보세요\n- 다른 키워드로 검색해보세요\n- 오타가 없는지 확인하세요"
            })

        session.close()

    except Exception as exc:
        _log = logging.getLogger(__name__)
        _log.warning(f"Document search fallback failed: {exc}")
        # Return error message
        blocks.append({
            "type": "markdown",
            "title": "검색 오류",
            "content": f"문서 검색 중 오류가 발생했습니다: {str(exc)}"
        })

    return blocks, used_tools
