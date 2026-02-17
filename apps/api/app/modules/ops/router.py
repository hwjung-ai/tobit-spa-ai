from __future__ import annotations

import asyncio
import importlib
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.auth import get_current_user
from core.config import get_settings
from core.db import get_session, get_session_context
from core.logging import get_logger, get_request_context
from core.security import decode_token
from core.tenant import get_current_tenant
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from jose import JWTError
from models.history import QueryHistory
from schemas import ResponseEnvelope
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from app.core.exceptions import (
    DatabaseError,
    PlanningError,
    ToolExecutionError,
)
from app.modules.asset_registry.loader import (
    load_catalog_asset,
    load_mapping_asset,
    load_policy_asset,
    load_resolver_asset,
    load_source_asset,
    resolve_catalog_asset_for_source,
)
from app.modules.auth.models import TbUser
from app.modules.inspector.service import persist_execution_trace
from app.modules.inspector.span_tracker import (
    clear_spans,
    end_span,
    get_all_spans,
    start_span,
)

from .schemas import (
    OpsAskRequest,
    OpsAskResponse,
    IsolatedStageTestRequest,
    OpsQueryRequest,
    ReplanPatchDiff,
    ReplanTrigger,
    RerunContext,
    RerunPatch,
    StageInput,
    UIActionRequest,
    UIEditorPresenceHeartbeatRequest,
)
from .services import handle_ops_query
from .services.action_registry import list_registered_actions
from .services.control_loop import evaluate_replan
from .services.observability_service import collect_observability_metrics
from .services.orchestration.blocks import text_block
from .services.orchestration.orchestrator.runner import OpsOrchestratorRunner
from .services.orchestration.planner import planner_llm, validator
from .services.orchestration.planner.plan_schema import (
    Intent,
    Plan,
    PlanOutput,
    PlanOutputKind,
    View,
)
from .services.ui_editor_collab import ui_editor_collab_manager
from .services.ui_editor_presence import ui_editor_presence_manager

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


def _generate_references_from_tool_calls(
    tool_calls: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate references from tool calls for trace documentation.

    Each tool call represents a data access or operation that should be documented
    as a reference in the execution trace.
    """
    references = []
    for i, tool_call in enumerate(tool_calls or []):
        if not isinstance(tool_call, dict):
            continue

        tool_name = tool_call.get("tool") or tool_call.get("name") or f"tool_{i}"
        params = tool_call.get("params") or tool_call.get("arguments") or {}
        result = tool_call.get("result") or tool_call.get("output")

        ref = {
            "type": "tool_call",
            "tool_name": tool_name,
            "params": params if isinstance(params, dict) else {},
            "result_summary": str(result)[:200] if result else None,
            "index": i,
        }
        references.append(ref)

    return references


# --- Standard OPS Query ---


@router.post("/query", response_model=ResponseEnvelope)
def query_ops(
    payload: OpsQueryRequest,
    request: Request,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    # 요청 받을 때 history 생성 (상태: processing)
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    user_id = str(current_user.id)

    # Set request context for tenant_id to be available throughout the request
    from core.logging import set_request_context
    request_id = str(uuid.uuid4())
    set_request_context(
        request_id=request_id,
        tenant_id=tenant_id,
        mode="ops"
    )

    history_entry = QueryHistory(
        tenant_id=tenant_id,
        user_id=user_id,
        feature="ops",
        question=payload.question,
        summary=None,
        status="processing",
        response=None,
        metadata_info={
            "uiMode": payload.mode,
            "backendMode": payload.mode,
        },
    )

    # history를 DB에 저장하고 ID 생성
    history_id = None
    try:
        with get_session_context() as session:
            session.add(history_entry)
            session.commit()
            session.refresh(history_entry)
        history_id = history_entry.id
    except DatabaseError as exc:
        logger.error(f"Failed to create query history record: {exc}")
        history_id = None
    except Exception as exc:
        logger.exception(f"Unexpected error creating history: {exc}", exc_info=exc)
        history_id = None

    # OPS 쿼리 실행
    envelope, trace_data = handle_ops_query(payload.mode, payload.question)
    response_payload = ResponseEnvelope.success(data={
        "answer": envelope.model_dump(),
        "trace": trace_data,
    })

    # 응답 완료 시 history 업데이트
    status = "ok"
    if history_id:
        try:
            with get_session_context() as session:
                history_entry = session.get(QueryHistory, history_id)
                if history_entry:
                    history_entry.status = status
                    history_entry.response = jsonable_encoder(response_payload.model_dump())
                    history_entry.summary = envelope.meta.summary if envelope.meta else ""
                    history_entry.metadata_info = jsonable_encoder({
                        "uiMode": payload.mode,
                        "backendMode": payload.mode,
                        "trace_id": envelope.meta.trace_id if envelope.meta else None,
                        "trace": trace_data,  # Include full trace data for consistency with ops ask
                    })
                    session.add(history_entry)
                    session.commit()
        except Exception as exc:
            logger.exception("ops.query.history.update_failed", exc_info=exc)

    return response_payload


@router.get("/observability/kpis", response_model=ResponseEnvelope)
def observability_kpis(
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    try:
        payload = collect_observability_metrics(session)
        if not payload:
            logger.warning("Empty observability metrics returned")
            return ResponseEnvelope.error(code=500, message="Failed to collect metrics")
        return ResponseEnvelope.success(data={"kpis": payload})
    except Exception as e:
        logger.error(f"Observability metrics error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            code=500, message=f"Observability service error: {str(e)}"
        )


@router.post("/conversation/summary", response_model=ResponseEnvelope)
def conversation_summary(
    request_data: dict,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get conversation summary for preview and PDF export.

    Returns a structured summary of the conversation including:
    - Title, date, topic metadata
    - Questions and answers
    - Overall summary (if requested)

    Args:
        request_data: Dictionary containing:
            - history_id: The history entry ID to get summary for
            - summary_type: "individual" or "overall"
            - title: Optional report title
            - topic: Optional report topic
        session: Database session dependency

    Returns:
        ResponseEnvelope with summary data
    """
    from datetime import datetime

    try:
        from .routes.query import _generate_overall_summary

        history_id = request_data.get("history_id")
        summary_type = request_data.get("summary_type", "individual")

        if not history_id:
            return ResponseEnvelope.error(
                message="history_id is required"
            )

        # Fetch the specific history entry (no tenant filter for summary access)
        entry = session.get(QueryHistory, history_id)

        if not entry:
            return ResponseEnvelope.error(
                message="History entry not found"
            )

        # Extract title from question
        title = request_data.get("title")
        if not title:
            question_text = entry.question or ""
            title = question_text[:50] + "..." if len(question_text) > 50 else question_text

        # Get mode from metadata_info
        mode = "unknown"
        if entry.metadata_info:
            mode = entry.metadata_info.get("mode", "unknown")

        # Parse response to extract summary and blocks
        summary = ""
        blocks = []
        references = []

        if entry.response:
            response = entry.response if isinstance(entry.response, dict) else {}
            summary = response.get("summary", "")
            blocks = response.get("blocks", [])

            # Extract references if available
            meta = response.get("meta", {})
            if isinstance(meta, dict):
                refs = meta.get("references", [])
                if refs:
                    references = refs

        # Build Q&A entry
        qa = {
            "question": entry.question or "",
            "timestamp": entry.created_at.isoformat() if entry.created_at else None,
            "mode": mode,
            "summary": summary,
            "blocks": blocks,
        }

        if references:
            qa["references"] = references

        summary_data = {
            "title": title,
            "topic": request_data.get("topic", "OPS 분석"),
            "date": entry.created_at.strftime("%Y-%m-%d") if entry.created_at else "",
            "created_at": datetime.now().isoformat(),
            "question_count": 1,
            "summary_type": summary_type,
            "questions_and_answers": [qa],
        }

        # If overall summary requested, generate it
        if summary_type == "overall":
            summary_data["overall_summary"] = _generate_overall_summary([qa])

        return ResponseEnvelope.success(data=summary_data)

    except DatabaseError as e:
        logger.error(f"Database error retrieving conversation: {e}")
        return ResponseEnvelope.error(message="Failed to retrieve conversation data")
    except Exception as e:
        logger.exception(f"Unexpected error generating summary: {e}", exc_info=True)
        return ResponseEnvelope.error(message="Failed to generate summary")


@router.post("/conversation/export/pdf", response_model=ResponseEnvelope)
def conversation_export_pdf(
    request_data: dict,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Export conversation as PDF report.

    Generates a professional PDF report from the conversation history.

    Args:
        request_data: Dictionary containing:
            - history_id: The history entry ID to export
            - title: Optional report title
            - topic: Optional report topic
            - summary_type: "individual" or "overall"
        session: Database session dependency

    Returns:
        ResponseEnvelope with PDF content (base64 encoded) and metadata
    """
    import base64
    from datetime import datetime

    from .services.report_service import pdf_report_service

    try:
        history_id = request_data.get("history_id")
        title = request_data.get("title")
        topic = request_data.get("topic", "OPS 분석")
        summary_type = request_data.get("summary_type", "individual")

        if not history_id:
            return ResponseEnvelope.error(
                message="history_id is required"
            )

        # Fetch the specific history entry (no tenant filter for export access)
        entry = session.get(QueryHistory, history_id)

        if not entry:
            return ResponseEnvelope.error(
                message="History entry not found"
            )

        if not title:
            question_text = entry.question or ""
            title = question_text[:40] + "..." if len(question_text) > 40 else question_text

        # Get mode from metadata_info
        mode = "unknown"
        if entry.metadata_info:
            mode = entry.metadata_info.get("mode", "unknown")

        # Parse response to extract summary and blocks
        summary = ""
        blocks = []
        references = []

        if entry.response:
            response = entry.response if isinstance(entry.response, dict) else {}
            summary = response.get("summary", "")
            blocks = response.get("blocks", [])

            # Extract references if available
            meta = response.get("meta", {})
            if isinstance(meta, dict):
                refs = meta.get("references", [])
                if refs:
                    references = refs

        # Build Q&A entry for PDF
        qa = {
            "question": entry.question or "",
            "timestamp": entry.created_at.strftime("%Y-%m-%d %H:%M:%S") if entry.created_at else "",
            "mode": mode,
            "summary": summary,
            "blocks": blocks,
        }

        if references:
            qa["references"] = references

        conversation_data = {
            "title": title,
            "topic": topic,
            "date": entry.created_at.strftime("%Y-%m-%d") if entry.created_at else datetime.now().strftime("%Y-%m-%d"),
            "questions_and_answers": [qa],
        }

        # Add overall summary if requested
        if summary_type == "overall":
            from .routes.query import _generate_overall_summary
            conversation_data["overall_summary"] = _generate_overall_summary([qa])

        # Generate PDF
        pdf_content = pdf_report_service.generate_conversation_report(conversation_data)

        # Encode to base64 for JSON response
        pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")

        # Generate filename
        filename = f"ops_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return ResponseEnvelope.success(
            data={
                "filename": filename,
                "content": pdf_base64,
                "content_type": "application/pdf",
                "size": len(pdf_content),
            }
        )

    except Exception as e:
        logger.error(f"Failed to export conversation PDF: {e}", exc_info=True)
        return ResponseEnvelope.error(message=str(e))


@router.get("/summary/stats", response_model=ResponseEnvelope)
def ops_summary_stats(session: Session = Depends(get_session)) -> ResponseEnvelope:
    try:
        from .services.observability_service import collect_ops_summary_stats

        payload = collect_ops_summary_stats(session)
        return ResponseEnvelope.success(data=payload)
    except Exception as e:
        logger.error(f"Failed to collect OPS summary stats: {e}", exc_info=True)
        return ResponseEnvelope.error(
            code=500, message=f"Failed to collect summary stats: {str(e)}"
        )


# --- RCA (Root Cause Analysis) ---


@router.post("/rca/analyze-trace", response_model=ResponseEnvelope)
def rca_analyze_trace(
    trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run RCA on a single trace.

    Returns list of RCA hypotheses with:
    - rank, title, confidence
    - evidence (with inspector jump links)
    - checks (verification steps)
    - recommended_actions
    """
    from app.modules.inspector.crud import get_execution_trace
    from app.modules.ops.services.rca_engine import RCAEngine

    trace = get_execution_trace(session, trace_id)
    if not trace:
        return ResponseEnvelope.error(code=404, message=f"Trace {trace_id} not found")

    try:
        engine = RCAEngine()
        hypotheses = engine.analyze_single_trace(trace.answer or {})

        # Convert hypotheses to dict format with inspector links
        result = {
            "trace_id": trace_id,
            "status": trace.status,
            "hypotheses": [
                {
                    "rank": h.rank,
                    "title": h.title,
                    "confidence": h.confidence,
                    "evidence": [
                        {
                            "path": ev.path,
                            "snippet": ev.snippet,
                            "display": ev.display,
                            # Inspector jump link
                            "inspector_link": f"/admin/inspector?trace_id={trace_id}&focus={ev.path}",
                        }
                        for ev in h.evidence
                    ],
                    "checks": h.checks,
                    "recommended_actions": h.recommended_actions,
                    "description": h.description,
                }
                for h in hypotheses
            ],
        }
        return ResponseEnvelope.success(data=result)
    except Exception as e:
        logger.error(f"RCA analysis failed for trace {trace_id}: {e}")
        return ResponseEnvelope.error(
            code=500, message=f"RCA analysis failed: {str(e)}"
        )


@router.post("/rca/analyze-regression", response_model=ResponseEnvelope)
def rca_analyze_regression(
    baseline_trace_id: str,
    candidate_trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run RCA on a regression (baseline vs candidate).

    Identifies differences and root causes.
    """
    from app.modules.inspector.crud import get_execution_trace
    from app.modules.ops.services.rca_engine import RCAEngine

    baseline_trace = get_execution_trace(session, baseline_trace_id)
    candidate_trace = get_execution_trace(session, candidate_trace_id)

    if not baseline_trace:
        return ResponseEnvelope.error(
            code=404, message=f"Baseline trace {baseline_trace_id} not found"
        )
    if not candidate_trace:
        return ResponseEnvelope.error(
            code=404, message=f"Candidate trace {candidate_trace_id} not found"
        )

    try:
        engine = RCAEngine()
        hypotheses = engine.analyze_diff(
            baseline_trace.answer or {},
            candidate_trace.answer or {},
        )

        # Convert with inspector links
        result = {
            "baseline_trace_id": baseline_trace_id,
            "candidate_trace_id": candidate_trace_id,
            "hypotheses": [
                {
                    "rank": h.rank,
                    "title": h.title,
                    "confidence": h.confidence,
                    "evidence": [
                        {
                            "path": ev.path,
                            "snippet": ev.snippet,
                            "display": ev.display,
                            # Inspector comparison link
                            "inspector_link": f"/admin/inspector?baseline={baseline_trace_id}&candidate={candidate_trace_id}&focus={ev.path}",
                        }
                        for ev in h.evidence
                    ],
                    "checks": h.checks,
                    "recommended_actions": h.recommended_actions,
                    "description": h.description,
                }
                for h in hypotheses
            ],
        }
        return ResponseEnvelope.success(data=result)
    except Exception as e:
        logger.error(f"RCA regression analysis failed: {e}")
        return ResponseEnvelope.error(
            code=500, message=f"RCA analysis failed: {str(e)}"
        )


# --- CI OPS (Ask CI) ---


def _tenant_id(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> str:
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return tenant_id


def _apply_patch(plan: Plan, patch: Optional[RerunPatch]) -> Plan:
    if not patch:
        return plan
    updates: dict[str, Any] = {}
    if patch.view:
        updates["view"] = patch.view
    if patch.graph:
        graph_updates: dict[str, Any] = {}
        if patch.graph.depth is not None:
            graph_updates["depth"] = patch.graph.depth
        if patch.graph.limits:
            graph_updates["limits"] = patch.graph.limits
        if patch.graph.view:
            graph_updates["view"] = patch.graph.view
        updates["graph"] = plan.graph.copy(update=graph_updates)
    if patch.aggregate:
        agg_updates: dict[str, Any] = {}
        if patch.aggregate.group_by:
            agg_updates["group_by"] = patch.aggregate.group_by
        if patch.aggregate.top_n is not None:
            agg_updates["top_n"] = patch.aggregate.top_n
        updates["aggregate"] = plan.aggregate.copy(update=agg_updates)
    if patch.output:
        out_updates: dict[str, Any] = {}
        if patch.output.primary:
            out_updates["primary"] = patch.output.primary
        if patch.output.blocks:
            out_updates["blocks"] = patch.output.blocks
        updates["output"] = plan.output.copy(update=out_updates)
    if patch.metric and plan.metric:
        metric_updates: dict[str, Any] = {}
        if patch.metric.time_range:
            metric_updates["time_range"] = patch.metric.time_range
        if patch.metric.agg:
            metric_updates["agg"] = patch.metric.agg
        if patch.metric.mode:
            metric_updates["mode"] = patch.metric.mode
        if metric_updates:
            updates["metric"] = plan.metric.copy(update=metric_updates)
    if patch.history and plan.history:
        history_updates: dict[str, Any] = {}
        if patch.history.time_range:
            history_updates["time_range"] = patch.history.time_range
        if patch.history.limit is not None:
            history_updates["limit"] = patch.history.limit
        if history_updates:
            updates["history"] = plan.history.copy(update=history_updates)
    if patch.list and plan.list:
        list_updates: dict[str, Any] = {}
        if patch.list.offset is not None:
            list_updates["offset"] = patch.list.offset
        if patch.list.limit is not None:
            list_updates["limit"] = patch.list.limit
        if list_updates:
            updates["list"] = plan.list.copy(update=list_updates)
    if patch.auto:
        auto_updates: dict[str, Any] = {}
        if patch.auto.path:
            path_updates: dict[str, Any] = {}
            if patch.auto.path.source_ci_code is not None:
                path_updates["source_ci_code"] = patch.auto.path.source_ci_code
            if patch.auto.path.target_ci_code is not None:
                path_updates["target_ci_code"] = patch.auto.path.target_ci_code
            if path_updates:
                auto_updates["path"] = plan.auto.path.copy(update=path_updates)
        if patch.auto.graph_scope:
            graph_updates: dict[str, Any] = {}
            if patch.auto.graph_scope.include_metric is not None:
                graph_updates["include_metric"] = patch.auto.graph_scope.include_metric
            if patch.auto.graph_scope.include_history is not None:
                graph_updates["include_history"] = (
                    patch.auto.graph_scope.include_history
                )
            if graph_updates:
                auto_updates["graph_scope"] = plan.auto.graph_scope.copy(
                    update=graph_updates
                )
        if auto_updates:
            updates["auto"] = plan.auto.copy(update=auto_updates)
    return plan.copy(update=updates) if updates else plan


@router.post("/ask")
def ask_ops(
    payload: OpsAskRequest,
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
):
    start = time.perf_counter()
    status = "ok"
    envelope_blocks: list[dict[str, Any]] | None = None
    next_actions_count = 0
    patched = bool(payload.rerun)
    patch_keys: list[str] = []
    has_trace_plan_validated = False
    if payload.rerun:
        has_trace_plan_validated = bool(payload.rerun.base_plan)
        if payload.rerun.patch:
            patch_keys = list(payload.rerun.patch.dict(exclude_none=True).keys())

    # 요청 받을 때 history 생성 (상태: processing)
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    user_id = str(current_user.id)
    history_entry = QueryHistory(
        tenant_id=tenant_id,
        user_id=user_id,
        feature="ops",
        question=payload.question,
        summary=None,
        status="processing",
        response=None,
        metadata_info={
            "uiMode": payload.mode or "all",
            "backendMode": payload.mode or "all",
        },
    )

    # history를 DB에 저장하고 ID 생성
    try:
        with get_session_context() as session:
            session.add(history_entry)
            session.commit()
            session.refresh(history_entry)
        history_id = history_entry.id
    except DatabaseError as exc:
        logger.error(f"Failed to create CI history record: {exc}")
        history_id = None
    except Exception as exc:
        logger.exception(f"Unexpected error creating CI history: {exc}", exc_info=exc)
        history_id = None

    logger.info(
        "ops.ask.start",
        extra={
            "query_len": len(payload.question),
            "has_patch": patched,
            "patch_keys": patch_keys,
            "has_trace_plan_validated": has_trace_plan_validated,
            "history_id": str(history_id) if history_id else None,
        },
    )
    response_payload: ResponseEnvelope | None = None
    error_response: JSONResponse | None = None
    duration_ms: int | None = None
    trace_payload: dict[str, Any] = {}
    meta: dict[str, Any] | None = None
    envelope_blocks: list[dict[str, Any]] = []
    next_actions: list[dict[str, Any]] = []
    flow_spans: list[Dict[str, Any]] = []
    active_trace_id: str | None = None
    parent_trace_id: str | None = None
    result: dict[str, Any] | None = None
    trace_status: str = "success"

    # Initialize span tracking for this trace
    clear_spans()

    # Set trace_id EARLY before any errors occur
    context = get_request_context()
    # request.state에서 먼저 확인 (middleware에서 설정한 값)
    active_trace_id = getattr(request.state, "trace_id", None) or context.get("trace_id")
    request_id = getattr(request.state, "request_id", None) or context.get("request_id")
    logger.info(
        f"ops.ask.context: trace_id={active_trace_id}, request_id={request_id}"
    )
    if not active_trace_id or active_trace_id == "-" or active_trace_id == "None":
        active_trace_id = str(uuid.uuid4())
        logger.info(f"ops.ask.new_trace_id: {active_trace_id}")
    parent_trace_id = context.get("parent_trace_id")
    if parent_trace_id == "-":
        parent_trace_id = None

    def _apply_resolver_rules(
        question: str, resolver_payload: Dict[str, Any] | None
    ) -> tuple[str, list[str]]:
        if not resolver_payload:
            return question, []
        rules = resolver_payload.get("rules", [])
        applied: list[str] = []
        normalized = question
        for rule in rules:
            rule_type = rule.get("rule_type")
            rule_data = rule.get("rule_data", {})
            name = rule.get("name") or rule_data.get("name") or rule_type or "rule"
            if rule_type == "alias_mapping":
                source_entity = rule_data.get("source_entity")
                target_entity = rule_data.get("target_entity")
                if (
                    source_entity
                    and target_entity
                    and source_entity.lower() in normalized.lower()
                ):
                    normalized = normalized.replace(source_entity, target_entity)
                    applied.append(name)
            elif rule_type == "pattern_rule":
                pattern = rule_data.get("pattern")
                replacement = rule_data.get("replacement")
                if pattern and replacement is not None:
                    try:
                        normalized = re.sub(pattern, replacement, normalized)
                        applied.append(name)
                    except re.error:
                        logger.warning(
                            "resolver.rule.invalid_pattern", extra={"name": name}
                        )
            elif rule_type == "transformation":
                transform = rule_data.get("transformation_type")
                if transform == "lowercase":
                    normalized = normalized.lower()
                    applied.append(name)
                elif transform == "uppercase":
                    normalized = normalized.upper()
                    applied.append(name)
                elif transform == "strip":
                    normalized = normalized.strip()
                    applied.append(name)
        return normalized, applied

    try:

        def build_fallback_plan(source: Plan) -> Plan:
            history = source.history.model_copy(update={"enabled": False})
            graph = source.graph.model_copy(update={"depth": 0, "view": None})
            list_spec = source.list.model_copy(update={"enabled": False})
            output = source.output.model_copy(
                update={"blocks": ["text", "table"], "primary": "table"}
            )
            return source.model_copy(
                update={
                    "intent": Intent.LOOKUP,
                    "view": View.SUMMARY,
                    "metric": None,
                    "history": history,
                    "graph": graph,
                    "list": list_spec,
                    "output": output,
                }
            )

        # Load assets (require explicit asset names in request)
        resolver_asset_name = payload.resolver_asset
        schema_asset_name = payload.schema_asset
        source_asset_name = payload.source_asset

        resolver_payload = (
            load_resolver_asset(resolver_asset_name) if resolver_asset_name else None
        )
        source_payload = load_source_asset(source_asset_name) if source_asset_name else None
        schema_payload = load_catalog_asset(schema_asset_name) if schema_asset_name else None

        # Auto-resolve catalog from source when schema isn't explicitly provided.
        if not schema_payload and source_asset_name:
            resolved_catalog = resolve_catalog_asset_for_source(source_asset_name)
            if resolved_catalog:
                schema_payload = resolved_catalog
                schema_asset_name = str(resolved_catalog.get("name") or schema_asset_name)
                logger.info(
                    "ops.ask.catalog.auto_resolved",
                    extra={
                        "source_asset": source_asset_name,
                        "schema_asset": schema_asset_name,
                    },
                )

        # If schema is selected but source is missing, derive source from schema payload.
        if not source_payload and schema_payload:
            derived_source_ref = schema_payload.get("source_ref")
            if derived_source_ref:
                source_asset_name = str(derived_source_ref)
                source_payload = load_source_asset(source_asset_name)

        # If both are present but mismatched, prefer source-bound catalog for consistency.
        if schema_payload and source_asset_name:
            schema_source_ref = schema_payload.get("source_ref")
            if schema_source_ref and schema_source_ref != source_asset_name:
                resolved_catalog = resolve_catalog_asset_for_source(source_asset_name)
                if resolved_catalog:
                    logger.warning(
                        "ops.ask.catalog.source_mismatch.corrected",
                        extra={
                            "source_asset": source_asset_name,
                            "schema_asset_before": schema_asset_name,
                            "schema_source_ref": schema_source_ref,
                            "schema_asset_after": resolved_catalog.get("name"),
                        },
                    )
                    schema_payload = resolved_catalog
                    schema_asset_name = str(resolved_catalog.get("name") or schema_asset_name)
                else:
                    logger.warning(
                        "ops.ask.catalog.source_mismatch.unresolved",
                        extra={
                            "source_asset": source_asset_name,
                            "schema_asset": schema_asset_name,
                            "schema_source_ref": schema_source_ref,
                        },
                    )
        # Load tracking assets opportunistically. Missing assets should not block ask flow.
        try:
            load_mapping_asset("graph_relation", scope="ops")
        except Exception as e:
            logger.warning(
                "ops.ask.optional_mapping_load_failed",
                extra={"mapping_type": "graph_relation", "scope": "ops", "error": str(e)},
            )
        try:
            load_policy_asset("plan_budget", scope="ops")
        except Exception as e:
            logger.warning(
                "ops.ask.optional_policy_load_failed",
                extra={"policy_type": "plan_budget", "scope": "ops", "error": str(e)},
            )

        normalized_question, resolver_rules_applied = _apply_resolver_rules(
            payload.question, resolver_payload
        )

        rerun_ctx: RerunContext | None = None
        plan_output: PlanOutput | None = None
        plan_raw: Plan | None = None
        plan_validated: Plan | None = None
        plan_trace: Dict[str, Any] = {
            "asset_context": {
                "source_asset": source_asset_name,
                "schema_asset": schema_asset_name,
                "resolver_asset": resolver_asset_name,
            },
            "resolver_rules_applied": resolver_rules_applied,
        }
        replan_events: list[Dict[str, Any]] = []
        # Store planner timing to include in route_plan stage duration
        planner_elapsed_ms: int = 0

        if payload.rerun:
            # Start route_plan timing for rerun path (captures validation time)
            route_plan_start = time.perf_counter()
            logger.info("ci.runner.planner.skipped", extra={"reason": "rerun"})
            validator_span = start_span("validator", "stage")
            try:
                patched_plan = _apply_patch(
                    payload.rerun.base_plan, payload.rerun.patch
                )
                logger.info("ci.runner.validator.start", extra={"phase": "rerun"})
                plan_validated, plan_trace = validator.validate_plan(
                    patched_plan, resolver_payload=resolver_payload
                )
                logger.info("ci.runner.validator.done", extra={"phase": "rerun"})
                end_span(validator_span, links={"plan_path": "plan.validated"})
                # Calculate route_plan time for rerun (validation time only)
                planner_elapsed_ms = int((time.perf_counter() - route_plan_start) * 1000)
                logger.info(f"ci.runner.rerun.route_plan_time: {planner_elapsed_ms}ms")
            except (PlanningError, ToolExecutionError) as e:
                logger.error(f"Plan validation error during rerun: {e}")
                end_span(
                    validator_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
            except Exception as e:
                logger.exception(f"Unexpected error validating plan: {e}", exc_info=True)
                end_span(
                    validator_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise
            plan_raw = payload.rerun.base_plan
            plan_output = PlanOutput(
                kind=PlanOutputKind.PLAN,
                plan=plan_validated,
                confidence=1.0,
                reasoning="Rerun execution",
                metadata={"route": "orch"},
            )
            rerun_ctx = RerunContext(
                selected_ci_id=payload.rerun.selected_ci_id,
                selected_secondary_ci_id=payload.rerun.selected_secondary_ci_id,
            )
            timestamp = datetime.now(get_settings().timezone_offset).isoformat()
            replan_events.append(
                {
                    "event_type": "replan_execution",
                    "stage_name": "route_plan",
                    "trigger": {
                        "trigger_type": "manual",
                        "stage_name": "route_plan",
                        "severity": "low",
                        "reason": "rerun requested",
                        "timestamp": timestamp,
                        "metadata": {
                            "patch_keys": patch_keys,
                        },
                    },
                    "patch": {
                        "before": plan_raw.model_dump(),
                        "after": patched_plan.model_dump(),
                    },
                    "timestamp": timestamp,
                    "decision_metadata": {
                        "selected_ci_id": payload.rerun.selected_ci_id,
                        "selected_secondary_ci_id": payload.rerun.selected_secondary_ci_id,
                    },
                    "execution_metadata": {
                        "patch_keys": patch_keys,
                    },
                }
            )
        else:
            # Start route_plan timing BEFORE planner to capture full planning time
            route_plan_start = time.perf_counter()
            planner_span = start_span("planner", "stage")
            try:
                logger.info(
                    "ci.runner.planner.start",
                    extra={
                        "llm_called": False,
                        "has_schema": bool(schema_payload),
                        "has_source": bool(source_payload),
                    },
                )
                # Pass explicit mode if provided, default to "all"
                explicit_mode = payload.mode or "all"
                plan_output = planner_llm.create_plan_output(
                    normalized_question,
                    schema_context=schema_payload,
                    source_context=source_payload,
                    mode=explicit_mode,
                )
                planner_elapsed_ms = int((time.perf_counter() - route_plan_start) * 1000)
                logger.info(
                    "ci.runner.planner.done",
                    extra={"llm_called": False, "elapsed_ms": planner_elapsed_ms},
                )
                end_span(planner_span, links={"plan_path": "plan.raw"})
            except PlanningError as e:
                logger.error(f"LLM plan generation failed: {e}")
                end_span(
                    planner_span,
                    status="error",
                    summary={"error_type": "PlanningError", "error_message": str(e)},
                )
                raise
            except Exception as e:
                logger.exception(f"Unexpected error in planning phase: {e}", exc_info=True)
                end_span(
                    planner_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise

            if plan_output.kind == PlanOutputKind.PLAN and plan_output.plan:
                plan_raw = plan_output.plan
                validator_span = start_span("validator", "stage")
                try:
                    logger.info("ci.runner.validator.start", extra={"phase": "initial"})
                    plan_validated, plan_trace = validator.validate_plan(
                        plan_raw, resolver_payload=resolver_payload
                    )
                    logger.info("ci.runner.validator.done", extra={"phase": "initial"})
                    end_span(validator_span, links={"plan_path": "plan.validated"})
                except Exception as e:
                    end_span(
                        validator_span,
                        status="error",
                        summary={
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                    )
                    raise
                plan_output = plan_output.model_copy(update={"plan": plan_validated})

        if plan_output is None:
            raise ValueError("Planner output missing")

        # Update history entry with trace_id
        if history_id:
            try:
                with get_session_context() as session:
                    history_entry = session.get(QueryHistory, history_id)
                    if history_entry:
                        history_entry.trace_id = active_trace_id
                        session.add(history_entry)
                        session.commit()
            except Exception as exc:
                logger.warning(f"Failed to update trace_id in history: {exc}")

        if plan_output.kind in (PlanOutputKind.DIRECT, PlanOutputKind.REJECT):
            stage_inputs: list[dict[str, Any]] = []
            stage_outputs: list[dict[str, Any]] = []
            stages: list[dict[str, Any]] = []

            def build_stage_output(
                stage: str, result: Dict[str, Any], status_label: str, duration: int = 0
            ) -> Dict[str, Any]:
                payload = {
                    "stage": stage,
                    "result": result,
                    "diagnostics": {
                        "status": status_label,
                        "warnings": ["skipped"] if status_label == "warning" else [],
                        "errors": [],
                    },
                    "references": result.get("references", []),
                    "duration_ms": duration,
                }
                return payload

            # route_plan_start was already set before planner to capture full planning time
            route_input = StageInput(
                stage="route_plan",
                applied_assets={},
                params={"plan_output": plan_output.model_dump()},
                prev_output=None,
                trace_id=active_trace_id,
            )
            route_output = build_stage_output(
                "route_plan",
                {"route": plan_output.kind.value},
                "ok",
                duration=int((time.perf_counter() - route_plan_start) * 1000),
            )
            stage_inputs.append(route_input.model_dump())
            stage_outputs.append(route_output)
            stages.append(
                {
                    "name": "route_plan",
                    "input": route_input.model_dump(),
                    "output": route_output.get("result"),
                    "elapsed_ms": route_output.get("duration_ms", 0),
                    "status": route_output.get("diagnostics", {}).get("status", "ok"),
                }
            )

            skipped_reason = (
                "direct_answer"
                if plan_output.kind == PlanOutputKind.DIRECT
                else "rejected"
            )
            for stage_name in ("validate", "execute", "compose"):
                stage_input = StageInput(
                    stage=stage_name,
                    applied_assets={},
                    params={"plan_output": plan_output.model_dump()},
                    prev_output=route_output,
                    trace_id=active_trace_id,
                )
                stage_output = build_stage_output(
                    stage_name, {"skipped": True, "reason": skipped_reason}, "warning"
                )
                stage_inputs.append(stage_input.model_dump())
                stage_outputs.append(stage_output)
                stages.append(
                    {
                        "name": stage_name,
                        "input": stage_input.model_dump(),
                        "output": stage_output.get("result"),
                        "elapsed_ms": stage_output.get("duration_ms", 0),
                        "status": stage_output.get("diagnostics", {}).get(
                            "status", "ok"
                        ),
                    }
                )

            if plan_output.kind == PlanOutputKind.DIRECT and plan_output.direct_answer:
                answer = plan_output.direct_answer.answer
                blocks = [text_block(answer)]
                references = plan_output.direct_answer.references
                route_reason = (
                    plan_output.direct_answer.reasoning
                    or plan_output.reasoning
                    or "Direct answer route selected"
                )
                route_output_payload = {
                    "route": "direct",
                    "direct_answer": plan_output.direct_answer.model_dump(),
                }
            else:
                reject_reason = (
                    plan_output.reject_payload.reason
                    if plan_output.reject_payload
                    else "This query is not supported"
                )
                answer = f"Query rejected: {reject_reason}"
                blocks = [text_block(answer)]
                references = []
                route_reason = (
                    plan_output.reject_payload.reasoning
                    if plan_output.reject_payload
                    else plan_output.reasoning
                )
                route_reason = route_reason or "Reject route selected"
                route_output_payload = {
                    "route": "reject",
                    "reject_reason": reject_reason,
                }

            present_start = time.perf_counter()
            present_input = StageInput(
                stage="present",
                applied_assets={},
                params={"plan_output": plan_output.model_dump()},
                prev_output=route_output,
                trace_id=active_trace_id,
            )
            present_output = build_stage_output(
                "present",
                {"summary": answer, "blocks": blocks, "references": references},
                "ok",
                duration=int((time.perf_counter() - present_start) * 1000),
            )
            stage_inputs.append(present_input.model_dump())
            stage_outputs.append(present_output)
            stages.append(
                {
                    "name": "present",
                    "input": present_input.model_dump(),
                    "output": present_output.get("result"),
                    "elapsed_ms": present_output.get("duration_ms", 0),
                    "status": present_output.get("diagnostics", {}).get("status", "ok"),
                }
            )

            duration_ms = int((time.perf_counter() - start) * 1000)
            trace_payload = {
                "route": plan_output.kind.value,
                "route_output": route_output_payload,
                "route_decision": {
                    "route": plan_output.kind.value,
                    "reason": route_reason,
                    "confidence": plan_output.confidence,
                    "metadata": plan_output.metadata,
                },
                "plan_raw": None,
                "plan_validated": None,
                "policy_decisions": plan_trace.get("policy_decisions"),
                "stage_inputs": stage_inputs,
                "stage_outputs": stage_outputs,
                "stages": stages,
                "replan_events": replan_events,
                "tool_calls": [],
                "references": references,
                "errors": [],
                "tenant_id": tenant_id,
                "trace_id": active_trace_id,
                "parent_trace_id": parent_trace_id,
            }
            meta = {
                "route": plan_output.kind.value,
                "route_reason": route_reason,
                "timing_ms": duration_ms,
                "summary": answer,
                "used_tools": [],
                "fallback": False,
                "trace_id": active_trace_id,
                "parent_trace_id": parent_trace_id,
            }
            result = {
                "answer": answer,
                "blocks": blocks,
                "trace": trace_payload,
                "next_actions": [],
                "meta": meta,
            }
            envelope_blocks = blocks
            next_actions_count = 0
            trace_status = "success"
        else:
            runner_span = start_span("runner", "stage")
            try:
                runner_module = importlib.import_module(OpsOrchestratorRunner.__module__)
                logger.info(
                    "ci.endpoint.entry", extra={"runner_file": runner_module.__file__}
                )
                runner = OpsOrchestratorRunner(
                    plan_validated,
                    plan_raw,
                    tenant_id,
                    normalized_question,
                    plan_trace,
                    rerun_context=rerun_ctx,
                    asset_overrides=payload.asset_overrides,
                )
                runner._flow_spans_enabled = True
                runner._runner_span_id = runner_span
                result = runner.run(plan_output)
                next_actions = result.get("next_actions") or []
                next_actions_count = len(next_actions)
                envelope_blocks = result.get("blocks") or []
                trace_payload = result.get("trace") or {}
                meta = result.get("meta") or {}

                # Add planner timing to route_plan stage duration (planner happens before runner)
                logger.info(f"ci.route_plan.timing: planner_elapsed_ms={planner_elapsed_ms}, stages_count={len(trace_payload.get('stages', []))}")
                if planner_elapsed_ms > 0:
                    # Update stage_outputs
                    stage_outputs = trace_payload.get("stage_outputs", [])
                    for stage_output in stage_outputs:
                        if stage_output and stage_output.get("stage") == "route_plan":
                            original_duration = stage_output.get("duration_ms", 0)
                            stage_output["duration_ms"] = original_duration + planner_elapsed_ms
                            logger.info(f"ci.route_plan.updated stage_output: {original_duration} -> {original_duration + planner_elapsed_ms}")
                            break
                    # Also update stages array (for response)
                    stages = trace_payload.get("stages", [])
                    for stage in stages:
                        if stage and stage.get("name") == "route_plan":
                            original_duration = stage.get("duration_ms", 0)
                            stage["duration_ms"] = original_duration + planner_elapsed_ms
                            logger.info(f"ci.route_plan.updated stages: {original_duration} -> {original_duration + planner_elapsed_ms}")
                            break

                # Generate references from tool calls if not already present
                tool_calls = (
                    trace_payload.get("tool_calls") or result.get("tool_calls") or []
                )
                if tool_calls and not trace_payload.get("references"):
                    trace_payload["references"] = _generate_references_from_tool_calls(
                        tool_calls
                    )
                else:
                    trace_payload.setdefault("references", [])

                if replan_events:
                    trace_payload["replan_events"] = replan_events
                route_output_payload = {
                    "route": "orch",
                    "plan_raw": plan_raw.model_dump() if plan_raw else None,
                }
                trace_payload.setdefault("route", "orch")
                trace_payload["route_output"] = route_output_payload
                trace_payload.setdefault(
                    "route_decision",
                    {
                        "route": "orch",
                        "reason": plan_output.reasoning or "Orchestration plan created",
                        "confidence": plan_output.confidence,
                        "metadata": plan_output.metadata,
                    },
                )
                meta["route"] = "orch"
                meta.setdefault("route_reason", "Stage-based execution")
                trace_status = "error" if trace_payload.get("errors") else "success"

                if trace_status == "error" and not payload.rerun:
                    trigger = ReplanTrigger(
                        trigger_type="error",
                        stage_name="execute",
                        severity="high",
                        reason="runner execution error",
                        timestamp=datetime.now(get_settings().timezone_offset).isoformat(),
                    )
                    fallback_plan = build_fallback_plan(plan_validated)
                    patch_diff = ReplanPatchDiff(
                        before=plan_validated.model_dump(),
                        after=fallback_plan.model_dump(),
                    )
                    should_replan = evaluate_replan(trigger, patch_diff)
                    decision_event = {
                        "event_type": "replan_decision",
                        "stage_name": "execute",
                        "trigger": trigger.model_dump(),
                        "patch": patch_diff.model_dump(),
                        "timestamp": datetime.now(get_settings().timezone_offset).isoformat(),
                        "decision_metadata": {
                            "should_replan": should_replan,
                        },
                    }
                    replan_events.append(decision_event)

                    if should_replan:
                        validator_span = start_span("validator", "stage")
                        try:
                            fallback_validated, fallback_trace = (
                                validator.validate_plan(
                                    fallback_plan, resolver_payload=resolver_payload
                                )
                            )
                            end_span(
                                validator_span, links={"plan_path": "plan.validated"}
                            )
                        except Exception as e:
                            end_span(
                                validator_span,
                                status="error",
                                summary={
                                    "error_type": type(e).__name__,
                                    "error_message": str(e),
                                },
                            )
                            raise
                        fallback_output = PlanOutput(
                            kind=PlanOutputKind.PLAN,
                            plan=fallback_validated,
                            confidence=plan_output.confidence,
                            reasoning="Auto replan fallback",
                            metadata={"route": "orch"},
                        )
                        runner = OpsOrchestratorRunner(
                            fallback_validated,
                            fallback_plan,
                            tenant_id,
                            normalized_question,
                            fallback_trace,
                            rerun_context=rerun_ctx,
                            asset_overrides=payload.asset_overrides,
                        )
                        runner._flow_spans_enabled = True
                        runner._runner_span_id = runner_span
                        result = runner.run(fallback_output)
                        next_actions = result.get("next_actions") or []
                        next_actions_count = len(next_actions)
                        envelope_blocks = result.get("blocks") or []
                        trace_payload = result.get("trace") or {}
                        meta = result.get("meta") or {}
                        trace_payload["route"] = "orch"
                        trace_payload["route_output"] = {
                            "route": "orch",
                            "plan_raw": fallback_plan.model_dump(),
                        }
                        trace_payload["route_decision"] = {
                            "route": "orch",
                            "reason": fallback_output.reasoning
                            or "Auto replan fallback",
                            "confidence": fallback_output.confidence,
                            "metadata": fallback_output.metadata,
                        }
                        execution_event = {
                            "event_type": "replan_execution",
                            "stage_name": "execute",
                            "trigger": trigger.model_dump(),
                            "patch": patch_diff.model_dump(),
                            "timestamp": datetime.now(get_settings().timezone_offset).isoformat(),
                            "execution_metadata": {
                                "fallback_plan": True,
                            },
                        }
                        replan_events.append(execution_event)
                        trace_payload["replan_events"] = replan_events
                        trace_status = (
                            "error" if trace_payload.get("errors") else "success"
                        )
                        meta["route"] = "orch"
                        meta.setdefault("route_reason", "Stage-based execution")

                end_span(runner_span)
            except Exception as e:
                end_span(
                    runner_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise
            finally:
                duration_ms = int((time.perf_counter() - start) * 1000)
        request_payload = {
            "question": payload.question,
            "rerun": payload.rerun.dict(exclude_none=True) if payload.rerun else None,
        }

        # Inject trace_id into result meta before creating response
        if result.get("meta") is None:
            result["meta"] = {}
        result["meta"]["trace_id"] = active_trace_id
        result["meta"]["parent_trace_id"] = parent_trace_id
        # Also inject into trace dict for consistency
        if result.get("trace") is None:
            result["trace"] = {}
        result["trace"]["trace_id"] = active_trace_id
        result["trace"]["parent_trace_id"] = parent_trace_id
        response: OpsAskResponse = OpsAskResponse(**result)
        response_payload = ResponseEnvelope.success(data=response.model_dump())
    except (PlanningError, ToolExecutionError) as exc:
        status = "error"
        logger.error(f"Orchestration error in ask endpoint: {exc}")
        error_body = ResponseEnvelope.error(message="Tool orchestration failed").model_dump(mode="json")
        error_response = JSONResponse(status_code=500, content=error_body)
        response_payload = None
        result = None
    except DatabaseError as exc:
        status = "error"
        logger.error(f"Database error during ask: {exc}")
        error_body = ResponseEnvelope.error(message="Data access failed").model_dump(mode="json")
        error_response = JSONResponse(status_code=503, content=error_body)
        response_payload = None
        result = None
    except Exception as exc:
        status = "error"
        logger.exception(f"Unexpected error in ask endpoint: {exc}", exc_info=exc)
        error_body = ResponseEnvelope.error(message="Internal error").model_dump(mode="json")
        error_response = JSONResponse(status_code=500, content=error_body)
        response_payload = None
        result = None

        # 에러 발생 시 history도 업데이트
        if history_id:
            try:
                with get_session_context() as session:
                    history_entry = session.get(QueryHistory, history_id)
                    if history_entry:
                        history_entry.status = "error"
                        history_entry.response = error_body
                        history_entry.summary = f"Error: {str(exc)[:200]}"
                        session.add(history_entry)
                        session.commit()
            except Exception as hist_exc:
                logger.exception("ci.history.error_update_failed", exc_info=hist_exc)
    finally:
        elapsed_ms = (
            duration_ms
            if duration_ms is not None
            else int((time.perf_counter() - start) * 1000)
        )

        # Persist trace to database ALWAYS (even on error)
        request_payload = {
            "question": payload.question,
            "rerun": payload.rerun.dict(exclude_none=True) if payload.rerun else None,
        }
        flow_spans = get_all_spans()

        try:
            with get_session_context() as session:
                persist_execution_trace(
                    session=session,
                    trace_id=active_trace_id,
                    parent_trace_id=parent_trace_id,
                    feature="ops",
                    endpoint="/ops/ask",
                    method="POST",
                    ops_mode=get_settings().ops_mode,
                    question=payload.question,
                    status=trace_status,
                    duration_ms=elapsed_ms,
                    request_payload=request_payload,
                    plan_raw=trace_payload.get("plan_raw") if trace_payload else None,
                    plan_validated=trace_payload.get("plan_validated") if trace_payload else None,
                    trace_payload=trace_payload if trace_payload else {},
                    answer_meta=meta if meta else None,
                    blocks=envelope_blocks if envelope_blocks else None,
                    flow_spans=flow_spans if flow_spans else None,
                )
                logger.info(f"✅ Trace persisted successfully: {active_trace_id}")
        except Exception as exc:
            logger.exception("ops.trace.persist_failed", exc_info=exc)

        # Update history entry with final status
        if history_id:
            try:
                with get_session_context() as session:
                    history_entry = session.get(QueryHistory, history_id)
                    if history_entry:
                        history_entry.status = status
                        history_entry.response = (
                            jsonable_encoder(response_payload.model_dump()) if response_payload else None
                        )
                        if result:
                            history_entry.summary = result.get("meta", {}).get("summary") or result.get("meta", {}).get("answer", "")[:200]
                            # Use explicit mode instead of hardcoded "ci"
                            explicit_mode = payload.mode or "all"
                            history_entry.metadata_info = jsonable_encoder({
                                "uiMode": explicit_mode,
                                "backendMode": explicit_mode,
                                "trace": trace_payload,
                                "nextActions": next_actions,
                            })
                        session.add(history_entry)
                        session.commit()
            except Exception as exc:
                logger.exception("ci.history.update_failed", exc_info=exc)

        block_types: list[str] = []
        if envelope_blocks:
            for block in envelope_blocks:
                if isinstance(block, dict):
                    block_type = block.get("type")
                else:
                    block_type = getattr(block, "type", None)
                if block_type:
                    block_types.append(block_type)
        logger.info(
            "ops.ask.done",
            extra={
                "status": status,
                "elapsed_ms": elapsed_ms,
                "blocks_count": len(envelope_blocks or []),
                "block_types": block_types,
                "next_actions_count": next_actions_count,
                "has_patch": patched,
                "has_trace_plan_validated": has_trace_plan_validated,
            },
        )
    assert response_payload or error_response  # ensure we always have a response
    return response_payload or error_response


# --- UI Actions (Deterministic Interactive UI) ---


@router.get("/ui-actions/catalog", response_model=ResponseEnvelope)
def list_ui_actions_catalog(
    include_api_manager: bool = Query(False, description="Include API Manager APIs in catalog"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Return deterministic UI action catalog for screen editor.

    The catalog is sourced from ActionRegistry metadata and optionally includes
    user-defined APIs from API Manager. Used by admin screen editors to render
    validated handler choices with metadata, input schemas, and sample output.

    Query params:
        include_api_manager: If true, also returns active API Manager APIs as
            selectable action sources with handler "api_manager.execute".
    """
    actions = list_registered_actions()

    # Mark built-in actions with source
    for action in actions:
        if "source" not in action:
            action["source"] = "builtin"

    api_manager_items: list[dict] = []
    if include_api_manager:
        try:
            from models.api_definition import ApiDefinition
            from sqlmodel import select as sql_select

            statement = sql_select(ApiDefinition).where(
                ApiDefinition.deleted_at.is_(None),
                ApiDefinition.is_enabled == True,  # noqa: E712
            )
            apis = session.exec(statement).all()
            for api in apis:
                mode = api.mode.value if api.mode else "sql"
                api_manager_items.append({
                    "action_id": f"api_manager:{api.id}",
                    "label": f"[API] {api.name}",
                    "description": api.description or f"{api.method} {api.path}",
                    "source": "api_manager",
                    "mode": mode,
                    "tags": (api.tags or []) + [mode],
                    "input_schema": {
                        "type": "object",
                        "required": ["api_id"],
                        "properties": {
                            "api_id": {
                                "type": "string",
                                "title": "API ID",
                                "default": str(api.id),
                            },
                            "params": {
                                "type": "object",
                                "title": "Execution Parameters",
                            },
                        },
                    },
                    "output": {"state_patch_keys": ["api_result"]},
                    "required_context": [],
                    "sample_output": None,
                    "api_manager_meta": {
                        "api_id": str(api.id),
                        "method": api.method,
                        "path": api.path,
                        "mode": mode,
                    },
                })
        except Exception as e:
            logger.warning(
                "Failed to load API Manager APIs for catalog",
                extra={"error": str(e)},
            )

    all_items = actions + api_manager_items
    return ResponseEnvelope.success(data={
        "actions": all_items,
        "count": len(all_items),
        "builtin_count": len(actions),
        "api_manager_count": len(api_manager_items),
    })


@router.post("/ui-editor/presence/heartbeat", response_model=ResponseEnvelope)
async def ui_editor_presence_heartbeat(
    payload: UIEditorPresenceHeartbeatRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """
    Register/refresh active editor session for a screen.

    This endpoint is used by admin screen editor tabs to provide server-side
    collaboration presence. It is tenant-scoped and user-aware.
    """
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    snapshot = await ui_editor_presence_manager.heartbeat(
        tenant_id=tenant_id,
        screen_id=payload.screen_id,
        session_id=payload.session_id,
        user_id=str(current_user.id),
        user_label=current_user.username,
        tab_name=payload.tab_name,
    )
    return ResponseEnvelope.success(
        data={
            "screen_id": payload.screen_id,
            "count": len(snapshot),
            "sessions": snapshot,
        }
    )


@router.post("/ui-editor/presence/leave", response_model=ResponseEnvelope)
async def ui_editor_presence_leave(
    payload: UIEditorPresenceHeartbeatRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Remove editor session from presence set."""
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    snapshot = await ui_editor_presence_manager.leave(
        tenant_id=tenant_id,
        screen_id=payload.screen_id,
        session_id=payload.session_id,
    )
    return ResponseEnvelope.success(
        data={
            "screen_id": payload.screen_id,
            "count": len(snapshot),
            "sessions": snapshot,
        }
    )


@router.get("/ui-editor/presence/stream")
async def ui_editor_presence_stream(
    request: Request,
    screen_id: str = Query(..., min_length=1),
    session_id: str = Query(..., min_length=1),
    tab_name: str | None = Query(None),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> EventSourceResponse:
    """
    SSE stream for editor presence updates.

    Events:
    - presence: full active session snapshot
    - ping: connection keepalive
    """
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    queue, initial_snapshot = await ui_editor_presence_manager.subscribe(
        tenant_id=tenant_id,
        screen_id=screen_id,
    )

    # Register stream-owner session immediately.
    await ui_editor_presence_manager.heartbeat(
        tenant_id=tenant_id,
        screen_id=screen_id,
        session_id=session_id,
        user_id=str(current_user.id),
        user_label=current_user.username,
        tab_name=tab_name,
    )

    async def event_generator():
        try:
            initial_payload = {
                "type": "presence",
                "tenant_id": tenant_id,
                "screen_id": screen_id,
                "count": len(initial_snapshot),
                "sessions": initial_snapshot,
            }
            yield {"event": "presence", "data": json.dumps(initial_payload)}

            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield {"event": "presence", "data": json.dumps(payload)}
                except asyncio.TimeoutError:
                    await ui_editor_presence_manager.heartbeat(
                        tenant_id=tenant_id,
                        screen_id=screen_id,
                        session_id=session_id,
                        user_id=str(current_user.id),
                        user_label=current_user.username,
                        tab_name=tab_name,
                    )
                    yield {"event": "ping", "data": "{}"}
        finally:
            await ui_editor_presence_manager.unsubscribe(tenant_id, screen_id, queue)
            await ui_editor_presence_manager.leave(tenant_id, screen_id, session_id)

    return EventSourceResponse(event_generator())


@router.websocket("/ui-editor/collab/ws")
async def ui_editor_collab_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for screen editor real-time collaboration.

    Query params:
    - screen_id: target screen id
    - tenant_id: tenant scope
    - session_id: browser-tab session id
    - token: optional JWT (required when auth is enabled)
    """
    settings = get_settings()
    qp = websocket.query_params
    screen_id = qp.get("screen_id", "").strip()
    tenant_id = qp.get("tenant_id", "").strip()
    session_id = qp.get("session_id", "").strip()
    token = qp.get("token", "").strip()

    if not screen_id or not tenant_id:
        await websocket.close(code=4400)
        return
    if not session_id:
        session_id = f"ws-{uuid.uuid4()}"

    user_id = "anonymous"
    user_label = "anonymous"

    try:
        with get_session_context() as session:
            if settings.enable_auth:
                if not token:
                    await websocket.close(code=4401)
                    return
                try:
                    payload = decode_token(
                        token, settings.jwt_secret_key, settings.jwt_algorithm
                    )
                except JWTError:
                    await websocket.close(code=4401)
                    return
                if payload.get("type") != "access":
                    await websocket.close(code=4401)
                    return
                token_user_id = payload.get("sub")
                if not token_user_id:
                    await websocket.close(code=4401)
                    return
                current_user = session.get(TbUser, token_user_id)
                if current_user is None or not current_user.is_active:
                    await websocket.close(code=4403)
                    return
                if current_user.tenant_id != tenant_id:
                    await websocket.close(code=4403)
                    return
                user_id = str(current_user.id)
                user_label = current_user.username or str(current_user.id)
                logger.info(
                    f"WebSocket authenticated: user={user_id}, screen={screen_id}, tenant={tenant_id}"
                )
            else:
                # Auth disabled - log warning for audit trail
                logger.warning(
                    f"WebSocket connection without auth enabled: screen={screen_id}, tenant={tenant_id}, session={session_id}"
                )
                debug_user = session.exec(
                    select(TbUser).where(TbUser.username == "admin@tobit.local")
                ).first()
                if debug_user:
                    user_id = str(debug_user.id)
                    user_label = debug_user.username or "debug@dev"
                else:
                    user_id = "dev-user"
                    user_label = "debug@dev"
    except Exception as ws_auth_err:
        logger.error(
            f"WebSocket auth/setup failed for screen_id={screen_id}: "
            f"{type(ws_auth_err).__name__}: {ws_auth_err}",
            exc_info=True,
        )
        await websocket.close(code=1011)
        return

    await ui_editor_collab_manager.connect(
        websocket,
        tenant_id=tenant_id,
        screen_id=screen_id,
        session_id=session_id,
        user_id=user_id,
        user_label=user_label,
    )
    logger.info(
        f"WebSocket connected: user={user_id} ({user_label}), screen={screen_id}, tenant={tenant_id}"
    )

    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                continue
            msg_type = str(payload.get("type") or "")
            if msg_type == "hello":
                await ui_editor_collab_manager.touch(
                    websocket, tenant_id=tenant_id, screen_id=screen_id
                )
                await ui_editor_collab_manager.broadcast_presence(
                    tenant_id=tenant_id, screen_id=screen_id
                )
            elif msg_type == "screen_update":
                screen = payload.get("screen")
                if isinstance(screen, dict):
                    await ui_editor_collab_manager.broadcast_screen_update(
                        tenant_id=tenant_id,
                        screen_id=screen_id,
                        source_session_id=session_id,
                        screen=screen,
                        updated_at=str(payload.get("updated_at") or ""),
                    )
            else:
                await ui_editor_collab_manager.touch(
                    websocket, tenant_id=tenant_id, screen_id=screen_id
                )
    except WebSocketDisconnect:
        pass
    finally:
        await ui_editor_collab_manager.disconnect(
            websocket, tenant_id=tenant_id, screen_id=screen_id
        )


@router.post("/ui-actions", response_model=ResponseEnvelope)
async def execute_ui_action(
    payload: UIActionRequest,
    tenant_id: str = Depends(get_current_tenant),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Execute deterministic UI action based on action_id.

    Flow:
    1. Validate action_id and inputs
    2. Generate new trace_id with parent_trace_id = payload.trace_id
    3. Route to deterministic executor based on action_id
    4. Execute using existing OPS executors (no LLM)
    5. Persist execution trace
    6. Return blocks as UIActionResponse
    """
    from .services.ui_actions import execute_action_deterministic, mask_sensitive_inputs

    # Setup
    trace_id = str(uuid.uuid4())
    parent_trace_id = payload.trace_id
    settings = get_settings()

    ts_start = time.time()

    # Start span tracking
    clear_spans()
    action_span = start_span(f"ui_action:{payload.action_id}", "ui_action")

    try:
        if get_settings().enable_auth and current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")

        # Validate OPS_MODE (no mock in real mode)
        mode = payload.context.get("mode", "real")
        if mode == "mock" and settings.OPS_MODE == "real":
            raise ValueError("Mock mode not allowed in OPS_MODE=real")

        # Execute action deterministically
        with get_session_context() as session:
            executor_result = await execute_action_deterministic(
                action_id=payload.action_id,
                inputs=payload.inputs,
                context=payload.context,
                session=session,
            )

        # End span
        end_span(action_span, status="ok")

        # Persist trace
        duration_ms = int((time.time() - ts_start) * 1000)
        all_spans = get_all_spans()

        with get_session_context() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature="ui_action",
                endpoint="/ops/ui-actions",
                method="POST",
                ops_mode=mode,
                question=f"UI Action: {payload.action_id}",
                status="success",
                duration_ms=duration_ms,
                request_payload={
                    "trace_id": payload.trace_id,
                    "action_id": payload.action_id,
                    "inputs": mask_sensitive_inputs(payload.inputs),
                    "context": payload.context,
                },
                plan_raw=None,
                plan_validated=None,
                trace_payload={
                    "route": payload.action_id,
                    "tool_calls": executor_result.get("tool_calls", []),
                    "references": executor_result.get("references", []),
                },
                answer_meta={
                    "route": payload.action_id,
                    "route_reason": "UI action execution",
                    "timing_ms": duration_ms,
                    "trace_id": trace_id,
                    "parent_trace_id": parent_trace_id,
                },
                blocks=executor_result["blocks"],
                flow_spans=all_spans,
            )

        logger.info(
            "ui_action.success",
            extra={
                "action_id": payload.action_id,
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "duration_ms": duration_ms,
                "blocks_count": len(executor_result.get("blocks", [])),
            },
        )

        return ResponseEnvelope.success(
            data={
                "trace_id": trace_id,
                "status": "ok",
                "blocks": executor_result["blocks"],
                "references": executor_result.get("references", []),
                "state_patch": executor_result.get("state_patch", {}),
            }
        )

    except Exception as exc:
        # Error handling
        end_span(
            action_span,
            status="error",
            summary={"error_type": type(exc).__name__, "error_message": str(exc)},
        )

        duration_ms = int((time.time() - ts_start) * 1000)
        all_spans = get_all_spans()

        # Error blocks
        error_blocks = [
            {
                "type": "markdown",
                "content": f"## ❌ UI Action 실행 실패\n\n**Action**: {payload.action_id}\n\n**Error**: {str(exc)}",
            }
        ]

        with get_session_context() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature="ui_action",
                endpoint="/ops/ui-actions",
                method="POST",
                ops_mode=payload.context.get("mode", "real"),
                question=f"UI Action: {payload.action_id}",
                status="error",
                duration_ms=duration_ms,
                request_payload={
                    "trace_id": payload.trace_id,
                    "action_id": payload.action_id,
                    "inputs": mask_sensitive_inputs(payload.inputs),
                    "context": payload.context,
                },
                plan_raw=None,
                plan_validated=None,
                trace_payload={
                    "route": payload.action_id,
                    "tool_calls": [],
                    "references": [],
                },
                answer_meta={
                    "route": payload.action_id,
                    "route_reason": "UI action execution",
                    "timing_ms": duration_ms,
                    "trace_id": trace_id,
                    "parent_trace_id": parent_trace_id,
                    "error": str(exc),
                },
                blocks=error_blocks,
                flow_spans=all_spans,
            )

        logger.error(
            "ui_action.error",
            extra={
                "action_id": payload.action_id,
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "error": str(exc),
                "duration_ms": duration_ms,
            },
        )

        return ResponseEnvelope.success(
            data={
                "trace_id": trace_id,
                "status": "error",
                "blocks": error_blocks,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        )


# --- Regression Watch (Step 5) ---


@router.get("/golden-queries")
def list_golden_queries(
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """List all golden queries"""
    from app.modules.inspector.crud import list_golden_queries

    queries = list_golden_queries(session)
    return ResponseEnvelope.success(
        data={
            "queries": [
                {
                    "id": q.id,
                    "name": q.name,
                    "query_text": q.query_text,
                    "ops_type": q.ops_type,
                    "enabled": q.enabled,
                    "created_at": q.created_at.isoformat(),
                }
                for q in queries
            ]
        }
    )


@router.post("/golden-queries")
def create_golden_query(
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Create a new golden query"""
    from app.modules.inspector.crud import create_golden_query as crud_create

    try:
        query = crud_create(
            session,
            name=payload.get("name"),
            query_text=payload.get("query_text"),
            ops_type=payload.get("ops_type"),
            options=payload.get("options"),
        )
        return ResponseEnvelope.success(
            data={
                "id": query.id,
                "name": query.name,
                "query_text": query.query_text,
                "ops_type": query.ops_type,
                "created_at": query.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to create golden query: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.put("/golden-queries/{query_id}")
def update_golden_query(
    query_id: str,
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Update golden query"""
    from app.modules.inspector.crud import update_golden_query as crud_update

    try:
        query = crud_update(
            session,
            query_id,
            name=payload.get("name"),
            query_text=payload.get("query_text"),
            enabled=payload.get("enabled"),
            options=payload.get("options"),
        )
        if not query:
            return ResponseEnvelope.error(message="Golden query not found")
        return ResponseEnvelope.success(
            data={
                "id": query.id,
                "name": query.name,
                "query_text": query.query_text,
                "ops_type": query.ops_type,
                "enabled": query.enabled,
                "created_at": query.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to update golden query: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.delete("/golden-queries/{query_id}")
def delete_golden_query(
    query_id: str,
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Delete golden query"""
    from app.modules.inspector.crud import delete_golden_query as crud_delete

    try:
        success = crud_delete(session, query_id)
        if not success:
            return ResponseEnvelope.error(message="Golden query not found")
        return ResponseEnvelope.success(data={"deleted": True})
    except Exception as e:
        logger.error(f"Failed to delete golden query: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.post("/golden-queries/{query_id}/set-baseline")
def set_baseline(
    query_id: str,
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Set baseline trace for a golden query"""
    from app.modules.inspector.crud import (
        create_regression_baseline,
        get_execution_trace,
        get_golden_query,
    )

    try:
        # Verify golden query exists
        query = get_golden_query(session, query_id)
        if not query:
            return ResponseEnvelope.error(message="Golden query not found")

        # Verify baseline trace exists
        baseline_trace_id = payload.get("trace_id")
        baseline_trace = get_execution_trace(session, baseline_trace_id)
        if not baseline_trace:
            return ResponseEnvelope.error(message="Baseline trace not found")

        # Create baseline record
        baseline = create_regression_baseline(
            session,
            golden_query_id=query_id,
            baseline_trace_id=baseline_trace_id,
            baseline_status=baseline_trace.status,
            asset_versions=baseline_trace.asset_versions,
            created_by=payload.get("created_by"),
        )

        return ResponseEnvelope.success(
            data={
                "id": baseline.id,
                "baseline_trace_id": baseline.baseline_trace_id,
                "baseline_status": baseline.baseline_status,
                "created_at": baseline.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to set baseline: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.post("/golden-queries/{query_id}/run-regression")
def run_regression(
    query_id: str,
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run regression check for a golden query.

    Executes the golden query and compares result against baseline.
    """
    from app.modules.inspector.crud import (
        create_regression_run,
        get_execution_trace,
        get_golden_query,
        get_latest_regression_baseline,
    )
    from app.modules.ops.services.regression_executor import (
        compute_regression_diff,
        determine_judgment,
    )

    try:
        # Verify golden query exists
        query = get_golden_query(session, query_id)
        if not query:
            return ResponseEnvelope.error(message="Golden query not found")

        # Get baseline
        baseline = get_latest_regression_baseline(session, query_id)
        if not baseline:
            return ResponseEnvelope.error(
                message="No baseline set for this golden query"
            )

        # Get baseline trace for comparison
        baseline_trace = get_execution_trace(session, baseline.baseline_trace_id)
        if not baseline_trace:
            return ResponseEnvelope.error(message="Baseline trace not found")

        # Execute golden query (use existing OPS handler)
        ts_start = time.time()
        clear_spans()

        try:
            # Use handle_ops_query to execute the golden query
            answer_envelope = handle_ops_query(query.ops_type, query.query_text)
            duration_ms = int((time.time() - ts_start) * 1000)

            # Create execution trace for candidate
            candidate_trace_id = str(uuid.uuid4())
            get_all_spans()

            # Build candidate trace dict for comparison
            candidate_trace = {
                "status": "success",
                "asset_versions": [],  # Will be populated by OPS execution
                "plan_validated": answer_envelope.meta.__dict__
                if answer_envelope.meta
                else None,
                "execution_steps": [],
                "answer": answer_envelope.model_dump() if answer_envelope else {},
                "references": answer_envelope.blocks
                if answer_envelope and answer_envelope.blocks
                else [],
                "ui_render": {"error_count": 0},
            }

            # Compute regression diff
            diff = compute_regression_diff(
                baseline_trace.model_dump(),
                candidate_trace,
            )

            # Determine judgment
            judgment, verdict_reason = determine_judgment(diff)

            # Create regression run record
            run = create_regression_run(
                session,
                golden_query_id=query_id,
                baseline_id=baseline.id,
                candidate_trace_id=candidate_trace_id,
                baseline_trace_id=baseline.baseline_trace_id,
                judgment=judgment,
                triggered_by=payload.get("triggered_by", "manual"),
                verdict_reason=verdict_reason,
                diff_summary={
                    "assets_changed": diff.assets_changed,
                    "plan_intent_changed": diff.plan_intent_changed,
                    "plan_output_changed": diff.plan_output_changed,
                    "tool_calls_added": diff.tool_calls_added,
                    "tool_calls_removed": diff.tool_calls_removed,
                    "tool_calls_failed": diff.tool_calls_failed,
                    "blocks_structure_changed": diff.blocks_structure_changed,
                    "references_variance": diff.references_variance,
                    "status_changed": diff.status_changed,
                    "ui_errors_increase": diff.ui_errors_increase,
                },
                trigger_info=payload.get("trigger_info"),
                execution_duration_ms=duration_ms,
            )

            return ResponseEnvelope.success(
                data={
                    "id": run.id,
                    "candidate_trace_id": candidate_trace_id,
                    "baseline_trace_id": baseline.baseline_trace_id,
                    "judgment": judgment,
                    "verdict_reason": verdict_reason,
                    "diff_summary": run.diff_summary,
                    "execution_duration_ms": duration_ms,
                    "created_at": run.created_at.isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Regression execution failed: {e}")
            return ResponseEnvelope.error(
                message=f"Regression execution failed: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Failed to run regression: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.get("/regression-runs")
def list_regression_runs(
    golden_query_id: str | None = None,
    limit: int = 50,
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """List regression runs"""
    from app.modules.inspector.crud import list_regression_runs

    try:
        runs = list_regression_runs(
            session, golden_query_id=golden_query_id, limit=limit
        )
        return ResponseEnvelope.success(
            data={
                "runs": [
                    {
                        "id": r.id,
                        "golden_query_id": r.golden_query_id,
                        "baseline_id": r.baseline_id,
                        "candidate_trace_id": r.candidate_trace_id,
                        "baseline_trace_id": r.baseline_trace_id,
                        "judgment": r.judgment,
                        "verdict_reason": r.verdict_reason,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in runs
                ]
            }
        )
    except Exception as e:
        logger.error(f"Failed to list regression runs: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.get("/regression-runs/{run_id}")
def get_regression_run(
    run_id: str,
    session: Any = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Get regression run details"""
    from app.modules.inspector.crud import get_regression_run

    try:
        run = get_regression_run(session, run_id)
        if not run:
            return ResponseEnvelope.error(message="Regression run not found")

        return ResponseEnvelope.success(
            data={
                "id": run.id,
                "golden_query_id": run.golden_query_id,
                "baseline_id": run.baseline_id,
                "candidate_trace_id": run.candidate_trace_id,
                "baseline_trace_id": run.baseline_trace_id,
                "judgment": run.judgment,
                "verdict_reason": run.verdict_reason,
                "diff_summary": run.diff_summary,
                "triggered_by": run.triggered_by,
                "execution_duration_ms": run.execution_duration_ms,
                "created_at": run.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to get regression run: {e}")
        return ResponseEnvelope.error(message=str(e))


# --- RCA Assist (Step 6) ---


@router.post("/rca")
def run_rca(
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run Root Cause Analysis on a trace or trace diff.

    Mode 1: Single trace analysis (failure/issue diagnosis)
    {
      "mode": "single",
      "trace_id": "abc-123",
      "options": { "max_hypotheses": 5, "include_snippets": true, "use_llm": true }
    }

    Mode 2: Diff analysis (regression/change analysis)
    {
      "mode": "diff",
      "baseline_trace_id": "base-123",
      "candidate_trace_id": "cand-456",
      "options": { "max_hypotheses": 7, "include_snippets": true, "use_llm": true }
    }

    Returns RCA trace with hypotheses as blocks.
    """
    from app.modules.inspector.crud import (
        create_execution_trace,
        get_execution_trace,
    )
    from app.modules.llm.rca_summarizer import summarize_rca_results
    from app.modules.ops.services.rca_engine import RCAEngine

    try:
        mode = payload.get("mode")
        options = payload.get("options", {})
        max_hypotheses = options.get("max_hypotheses", 5)
        use_llm = options.get("use_llm", True)
        options.get("include_snippets", True)

        ts_start = time.time()
        rca_engine = RCAEngine()

        # ===== Single Trace Mode =====
        if mode == "single":
            trace_id = payload.get("trace_id")
            if not trace_id:
                return ResponseEnvelope.error(
                    message="trace_id required for single mode"
                )

            # Fetch trace
            trace = get_execution_trace(session, trace_id)
            if not trace:
                return ResponseEnvelope.error(message=f"Trace {trace_id} not found")

            # Generate hypotheses
            rca_engine.analyze_single_trace(
                trace.model_dump(),
                max_hypotheses=max_hypotheses,
            )

            source_traces = [trace_id]
            question = f"RCA: Analyze failure in trace {trace_id[:8]}..."

        # ===== Diff Mode =====
        elif mode == "diff":
            baseline_trace_id = payload.get("baseline_trace_id")
            candidate_trace_id = payload.get("candidate_trace_id")

            if not baseline_trace_id or not candidate_trace_id:
                return ResponseEnvelope.error(
                    message="baseline_trace_id and candidate_trace_id required for diff mode"
                )

            # Fetch traces
            baseline = get_execution_trace(session, baseline_trace_id)
            candidate = get_execution_trace(session, candidate_trace_id)

            if not baseline:
                return ResponseEnvelope.error(
                    message=f"Baseline trace {baseline_trace_id} not found"
                )
            if not candidate:
                return ResponseEnvelope.error(
                    message=f"Candidate trace {candidate_trace_id} not found"
                )

            # Generate hypotheses
            try:
                rca_engine.analyze_diff(
                    baseline.model_dump(),
                    candidate.model_dump(),
                    max_hypotheses=max_hypotheses,
                )
            except Exception as diff_err:
                logger.error(f"Diff analysis error: {diff_err}", exc_info=True)
                raise

            source_traces = [baseline_trace_id, candidate_trace_id]
            question = f"RCA: Analyze regression/change between {baseline_trace_id[:8]}... and {candidate_trace_id[:8]}..."

        else:
            return ResponseEnvelope.error(message="mode must be 'single' or 'diff'")

        # ===== Convert to dict and summarize =====
        rca_data = rca_engine.to_dict()
        hypotheses = rca_data.get("hypotheses", [])

        # Add LLM descriptions if enabled
        if use_llm and hypotheses:
            try:
                hypotheses = summarize_rca_results(
                    hypotheses,
                    use_llm=True,
                    language="korean",
                )
                logger.info(
                    f"RCA summarization completed for {len(hypotheses)} hypotheses"
                )
            except Exception as e:
                logger.warning(f"RCA summarization failed (using fallback): {e}")
                for hyp in hypotheses:
                    hyp["description"] = ""

        # ===== Create RCA trace =====
        rca_trace_id = str(uuid.uuid4())
        duration_ms = int((time.time() - ts_start) * 1000)

        # Build RCA answer blocks
        rca_blocks = []

        # Block 1: Summary
        rca_blocks.append(
            {
                "type": "markdown",
                "title": "RCA Analysis Summary",
                "content": f"**Mode:** {mode}\n**Traces Analyzed:** {', '.join(source_traces[:2])}\n**Hypotheses Found:** {len(hypotheses)}",
            }
        )

        # Block 2: Hypotheses list (one hypothesis per block)
        for hyp in hypotheses:
            hyp_content = f"""**Rank {hyp["rank"]}: {hyp["title"]}**

**Confidence:** {hyp["confidence"].upper()}

**Description:** {hyp.get("description", "N/A")}

**Evidence:**
"""
            for evidence in hyp.get("evidence", []):
                hyp_content += f"- `{evidence['path']}`: {evidence['snippet']}\n"

            hyp_content += "\n**Verification Checks:**\n"
            for check in hyp.get("checks", [])[:3]:
                hyp_content += f"- {check}\n"

            hyp_content += "\n**Recommended Actions:**\n"
            for action in hyp.get("recommended_actions", [])[:3]:
                hyp_content += f"- {action}\n"

            rca_blocks.append(
                {
                    "type": "markdown",
                    "title": f"Hypothesis {hyp['rank']}",
                    "content": hyp_content,
                }
            )

        # Create execution trace for RCA run
        from app.modules.inspector.models import TbExecutionTrace

        rca_trace_obj = TbExecutionTrace(
            trace_id=rca_trace_id,
            parent_trace_id=None,  # RCA is top-level
            feature="rca",
            endpoint="/ops/rca",
            method="POST",
            ops_mode="real",
            question=question,
            status="success" if hypotheses else "warning",
            duration_ms=duration_ms,
            request_payload={
                "mode": mode,
                "source_traces": source_traces,
                "options": options,
            },
            applied_assets=None,
            asset_versions=None,
            fallbacks=None,
            plan_raw=None,
            plan_validated=None,
            execution_steps=None,
            references=None,
            answer={
                "meta": {
                    "route": "rca",
                    "summary": f"RCA: {len(hypotheses)} hypotheses generated",
                },
                "blocks": rca_blocks,
            },
            ui_render=None,
            audit_links=None,
            flow_spans=None,
        )
        try:
            create_execution_trace(session, rca_trace_obj)
            logger.info(f"RCA trace created successfully: {rca_trace_id}")
        except Exception as trace_err:
            logger.error(f"Failed to create RCA trace: {trace_err}", exc_info=True)
            return ResponseEnvelope.error(
                message=f"Failed to persist RCA results: {str(trace_err)}"
            )

        # ===== Return response =====
        logger.info(f"Returning RCA response with trace_id: {rca_trace_id}")
        return ResponseEnvelope.success(
            data={
                "trace_id": rca_trace_id,
                "status": "ok",
                "blocks": rca_blocks,
                "rca": {
                    "mode": mode,
                    "source_traces": source_traces,
                    "hypotheses": hypotheses,
                    "total_hypotheses": len(hypotheses),
                    "analysis_duration_ms": duration_ms,
                },
            }
        )

    except Exception as e:
        logger.error(f"RCA analysis failed: {e}", exc_info=True)
        return ResponseEnvelope.error(message=f"RCA analysis failed: {str(e)}")


# --- OPS Actions ---


@router.post("/actions")
def execute_action(
    payload: Dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Execute recovery actions for OPS orchestration.

    Payload structure:
    {
        "action": "rerun|replan|debug|skip|rollback",
        "trigger": { ...ReplanTrigger... },
        "stage": "stage_name",
        "params": { ...action-specific parameters... }
    }
    """
    import uuid

    from app.modules.ops.services.control_loop import ControlLoop
    from app.modules.ops.services.orchestration.orchestrator.runner import (
        OpsOrchestratorRunner,
    )

    try:
        action = payload.get("action")
        trigger = payload.get("trigger")
        stage = payload.get("stage")
        params = payload.get("params", {})

        if not action:
            return ResponseEnvelope.error(message="action is required")

        # Validate trigger if provided
        if trigger:
            try:
                from .schemas import safe_parse_trigger

                trigger = safe_parse_trigger(trigger)
            except Exception:
                return ResponseEnvelope.error(message="invalid trigger format")

        action_id = str(uuid.uuid4())
        logger.info(f"Executing action: {action} for stage: {stage}")

        # Execute action based on type
        result = None
        message = f"Action {action} executed successfully"

        if action == "rerun":
            # Re-run CI with provided parameters
            ci_code = params.get("ci_code")
            if not ci_code:
                return ResponseEnvelope.error(message="ci_code is required for rerun")

            orchestrator = OpsOrchestratorRunner()
            result = orchestrator.rerun_ci(ci_code, params)

        elif action == "replan":
            # Trigger replanning
            control_loop = ControlLoop()
            result = control_loop.trigger_replan(
                trigger
                or ReplanTrigger(
                    trigger_type="manual",
                    stage_name=stage or "unknown",
                    reason="Manual replan triggered",
                    timestamp="now",
                )
            )

        elif action == "debug":
            # Run diagnostics on a specific execution trace
            from app.modules.ops.routes.actions import _run_debug_diagnostics
            execution_id = params.get("execution_id") or params.get("trace_id")
            result = _run_debug_diagnostics(session, execution_id, stage)

        elif action == "skip":
            # Skip stage
            control_loop = ControlLoop()
            result = control_loop.skip_stage(
                stage or "unknown", params.get("skip_reason", "")
            )

        elif action == "rollback":
            # Rollback to a previous execution by re-running with original params
            from app.modules.ops.routes.actions import _run_rollback
            execution_id = params.get("execution_id") or params.get("trace_id")
            result = _run_rollback(session, execution_id, params)

        else:
            return ResponseEnvelope.error(message=f"Unknown action: {action}")

        # Log the action execution
        logger.info(f"Action {action} completed: {result}")

        return ResponseEnvelope.success(
            data={
                "action_id": action_id,
                "action": action,
                "stage": stage,
                "result": result,
                "message": message,
            }
        )

    except Exception as e:
        logger.error(f"Action execution failed: {e}", exc_info=True)
        return ResponseEnvelope.error(message=f"Action failed: {str(e)}")


# --- Isolated Stage Test ---


@router.post("/stage-test", response_model=ResponseEnvelope)
async def execute_isolated_stage_test(
    payload: IsolatedStageTestRequest,
    tenant_id: str = Depends(get_current_tenant),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Execute a single stage in isolation for testing and validation.

    This endpoint allows testing individual stages with asset overrides and
    baseline comparison for regression testing.
    """
    import time

    from core.logging import get_logger

    from app.modules.ops.schemas import ExecutionContext
    from app.modules.ops.services.orchestration.orchestrator.stage_executor import (
        StageExecutor,
    )

    logger = get_logger(__name__)
    get_settings()

    # Setup
    if get_settings().enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    trace_id = str(uuid.uuid4())

    # Validate stage
    valid_stages = ["route_plan", "validate", "execute", "compose", "present"]
    if payload.stage not in valid_stages:
        return ResponseEnvelope.error(
            message=f"Invalid stage: {payload.stage}. Must be one of {valid_stages}"
        )

    # Create execution context
    context = ExecutionContext(
        tenant_id=tenant_id,
        question=payload.question,
        trace_id=trace_id,
        test_mode=True,
        asset_overrides=payload.asset_overrides,
        baseline_trace_id=payload.baseline_trace_id,
    )

    logger.info(
        f"Starting isolated stage test: {payload.stage}",
        extra={
            "tenant_id": tenant_id,
            "stage": payload.stage,
            "test_mode": True,
            "asset_overrides_count": len(payload.asset_overrides),
        },
    )

    try:
        # Create stage executor
        stage_executor = StageExecutor(context)

        # Build stage input
        stage_input = StageInput(
            stage=payload.stage,
            applied_assets=payload.asset_overrides,  # Use overrides for this test
            params=payload.test_plan or {},
            prev_output=None,
        )

        # Execute stage
        start_time = time.time()
        stage_output = await stage_executor.execute_stage(stage_input)
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Stage test completed: {payload.stage}",
            extra={
                "duration_ms": duration_ms,
                "status": stage_output.diagnostics.status,
            },
        )

        return ResponseEnvelope.success(
            data={
                "stage": payload.stage,
                "result": stage_output.result,
                "duration_ms": duration_ms,
                "diagnostics": stage_output.diagnostics.dict(),
                "references": stage_output.references,
                "asset_overrides_used": payload.asset_overrides,
                "baseline_trace_id": payload.baseline_trace_id,
                "trace_id": trace_id,
            }
        )

    except Exception as e:
        logger.error(f"Stage test failed: {payload.stage} - {str(e)}", exc_info=True)
        return ResponseEnvelope.error(message=f"Stage test failed: {str(e)}")


# --- Stage Comparison for Regression ---


@router.post("/stage-compare", response_model=ResponseEnvelope)
async def compare_stages(
    payload: Dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Compare stages between two execution traces for regression analysis.

    Payload structure:
    {
        "baseline_trace_id": "trace_id_1",
        "current_trace_id": "trace_id_2",
        "stages_to_compare": ["route_plan", "validate", "execute", "compose", "present"],
        "comparison_depth": "detailed|summary"
    }
    """

    from app.modules.inspector.service import get_execution_trace

    try:
        baseline_id = payload.get("baseline_trace_id")
        current_id = payload.get("current_trace_id")
        stages_to_compare = payload.get(
            "stages_to_compare",
            ["route_plan", "validate", "execute", "compose", "present"],
        )
        comparison_depth = payload.get("comparison_depth", "summary")

        if not baseline_id or not current_id:
            return ResponseEnvelope.error(
                message="baseline_trace_id and current_trace_id are required"
            )

        # Fetch traces
        baseline_trace = get_execution_trace(session, baseline_id)
        current_trace = get_execution_trace(session, current_id)

        if not baseline_trace or not current_trace:
            return ResponseEnvelope.error(message="One or both traces not found")

        # Compare stages
        comparison_results = []

        for stage in stages_to_compare:
            baseline_stage = None
            current_stage = None

            # Find stage in baseline trace
            for stage_output in baseline_trace.get("stage_outputs", []):
                if stage_output.get("stage") == stage:
                    baseline_stage = stage_output
                    break

            # Find stage in current trace
            for stage_output in current_trace.get("stage_outputs", []):
                if stage_output.get("stage") == stage:
                    current_stage = stage_output
                    break

            if baseline_stage and current_stage:
                comparison = {
                    "stage": stage,
                    "baseline": {
                        "duration_ms": baseline_stage.get("duration_ms"),
                        "status": baseline_stage.get("diagnostics", {}).get("status"),
                        "counts": baseline_stage.get("diagnostics", {}).get(
                            "counts", {}
                        ),
                        "has_references": len(baseline_stage.get("references", [])) > 0,
                    },
                    "current": {
                        "duration_ms": current_stage.get("duration_ms"),
                        "status": current_stage.get("diagnostics", {}).get("status"),
                        "counts": current_stage.get("diagnostics", {}).get(
                            "counts", {}
                        ),
                        "has_references": len(current_stage.get("references", [])) > 0,
                    },
                    "changed": False,
                }

                # Check for changes
                if (
                    comparison["baseline"]["duration_ms"]
                    != comparison["current"]["duration_ms"]
                    or comparison["baseline"]["status"]
                    != comparison["current"]["status"]
                    or comparison["baseline"]["has_references"]
                    != comparison["current"]["has_references"]
                ):
                    comparison["changed"] = True

                if comparison_depth == "detailed":
                    comparison["baseline_result"] = baseline_stage.get("result", {})
                    comparison["current_result"] = current_stage.get("result", {})
                    comparison["baseline_references"] = baseline_stage.get(
                        "references", []
                    )
                    comparison["current_references"] = current_stage.get(
                        "references", []
                    )

                comparison_results.append(comparison)

        # Calculate summary metrics
        total_stages = len(comparison_results)
        changed_stages = len([r for r in comparison_results if r["changed"]])
        regressed_stages = len(
            [
                r
                for r in comparison_results
                if r["current"]["status"] == "error"
                and r["baseline"]["status"] != "error"
            ]
        )

        return ResponseEnvelope.success(
            data={
                "baseline_trace_id": baseline_id,
                "current_trace_id": current_id,
                "total_stages": total_stages,
                "changed_stages": changed_stages,
                "regressed_stages": regressed_stages,
                "comparison_results": comparison_results,
                "summary": {
                    "regression_detected": regressed_stages > 0,
                    "change_percentage": (changed_stages / total_stages * 100)
                    if total_stages > 0
                    else 0,
                    "performance_change": sum(
                        1 for r in comparison_results if r["changed"]
                    )
                    / total_stages
                    * 100
                    if total_stages > 0
                    else 0,
                },
            }
        )

    except Exception as e:
        logger.error(f"Stage comparison failed: {str(e)}", exc_info=True)
        return ResponseEnvelope.error(message=f"Stage comparison failed: {str(e)}")


def _calculate_performance_change(comparison_results: List[Dict]) -> Dict[str, float]:
    """Calculate performance metrics from stage comparisons"""
    if not comparison_results:
        return {"avg_duration_change": 0, "total_duration_change": 0}

    total_baseline_duration = sum(
        r["baseline"]["duration_ms"] for r in comparison_results
    )
    total_current_duration = sum(
        r["current"]["duration_ms"] for r in comparison_results
    )

    if total_baseline_duration == 0:
        return {"avg_duration_change": 0, "total_duration_change": 0}

    avg_change = (
        (total_current_duration - total_baseline_duration) / total_baseline_duration
    ) * 100
    return {
        "avg_duration_change": avg_change,
        "total_duration_change": total_current_duration - total_baseline_duration,
    }


# --- Runtime Tool Discovery Webhooks ---


@router.post("/webhooks/tool-discovery")
async def tool_discovery_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_secret: Optional[str] = Header(None),
    current_user: TbUser = Depends(get_current_user),
) -> JSONResponse:
    """
    Webhook endpoint for tool discovery updates.

    Allows authorized users to trigger immediate tool discovery scans
    when new tools are added to the Asset Registry.

    Headers:
    - X-Webhook-Signature: HMAC-SHA256 signature of the payload
    - X-Webhook-Secret: Secret key for signature verification (alternative to config)
    """
    try:
        # Get payload
        payload = await request.json()

        # Get discovery instance
        from .services.orchestration.tools.runtime_tool_discovery import (
            get_runtime_discovery,
        )
        discovery = get_runtime_discovery()

        # Process webhook
        success = await discovery.handle_webhook(
            payload=payload,
            signature=x_webhook_signature
        )

        if success:
            status_code = 200
            message = "Webhook processed successfully"
        else:
            status_code = 400
            message = "Webhook processing failed"

        return JSONResponse(
            status_code=status_code,
            content={"message": message, "processed_at": datetime.now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )


@router.get("/tool-discovery/status")
async def get_tool_discovery_status() -> JSONResponse:
    """
    Get the current status of the runtime tool discovery system.

    Returns information about:
    - Whether discovery is running
    - Last scan time
    - Registered tools count
    - Configuration settings
    """
    try:
        from .services.orchestration.tools.runtime_tool_discovery import (
            get_runtime_discovery,
        )
        discovery = get_runtime_discovery()

        status = discovery.get_discovery_status()

        return JSONResponse(
            status_code=200,
            content={"status": status, "timestamp": datetime.now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Error getting discovery status: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": f"Internal server error: {str(e)}"}
        )


@router.post("/tool-discovery/refresh")
async def refresh_tool_discovery(
    force: bool = Query(False, description="Force refresh even if not scheduled")
) -> JSONResponse:
    """
    Manually trigger a tool discovery refresh.

    Useful for testing or when you need immediate updates
    without waiting for the next scheduled scan.

    Query Parameters:
    - force: Force refresh regardless of scan interval
    """
    try:
        from .services.orchestration.tools.runtime_tool_discovery import (
            get_runtime_discovery,
        )
        discovery = get_runtime_discovery()

        # Check if discovery is running
        if not discovery._running:
            return JSONResponse(
                status_code=400,
                content={"message": "Tool discovery is not running"}
            )

        # Scan for changes
        changes = await discovery.scan_for_changes(force=force)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Discovery refresh completed",
                "changes_detected": len(changes),
                "changes": [
                    {
                        "type": change.change_type.value,
                        "tool_name": change.tool_name,
                        "detected_at": change.detected_at.isoformat()
                    }
                    for change in changes
                ],
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Error refreshing discovery: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": f"Internal server error: {str(e)}"}
        )
