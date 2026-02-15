"""
OPS Ask Stream Route

SSE-based streaming endpoint for OPS queries with real-time progress updates.
Provides ChatGPT-style status indicators during query execution.

Endpoints:
    POST /ops/ask/stream - Stream OPS query with progress updates
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from core.auth import get_current_user
from core.config import get_settings
from core.db import get_session_context
from core.logging import get_logger
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from models.history import QueryHistory
from pydantic import BaseModel

from app.modules.asset_registry.loader import (
    load_catalog_asset,
    load_mapping_asset,
    load_policy_asset,
    load_resolver_asset,
    load_source_asset,
)
from app.modules.auth.models import TbUser
from app.modules.inspector.service import persist_execution_trace
from app.modules.inspector.span_tracker import (
    clear_spans,
    end_span,
    get_all_spans,
    start_span,
)
from app.modules.ops.schemas import CiAskRequest
from app.modules.ops.security import SecurityUtils
from app.modules.ops.services.orchestration.orchestrator.runner import (
    OpsOrchestratorRunner,
)
from app.modules.ops.services.orchestration.planner import planner_llm, validator
from app.modules.ops.services.orchestration.planner.plan_schema import (
    PlanOutput,
    PlanOutputKind,
)

from .utils import _tenant_id, apply_patch, generate_references_from_tool_calls

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


class StreamProgressEvent(BaseModel):
    """Progress event sent to client."""
    stage: str
    message: str
    elapsed_ms: float
    details: dict[str, Any] = {}


class StreamCompleteEvent(BaseModel):
    """Complete event sent to client."""
    answer: str
    blocks: list[dict[str, Any]]
    meta: dict[str, Any]
    trace: dict[str, Any]
    next_actions: list[dict[str, Any]]


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format data as SSE event."""
    import json
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ask/stream")
async def ask_ops_stream(
    payload: CiAskRequest,
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream OPS query execution with real-time progress updates.
    
    SSE Event Types:
    - progress: Current stage (init, resolving, planning, executing, composing, complete)
    - tool_start: Tool execution started
    - tool_complete: Tool execution completed
    - block: Individual answer block
    - complete: Final result with full response
    - error: Error occurred
    
    Progress stages:
    1. init - 초기화
    2. resolving - 질의 분석
    3. planning - 실행 계획 수립
    4. executing - 도구 실행
    5. composing - 결과 종합
    6. complete - 완료
    """
    from app.modules.ops.services.ops_sse_handler import (
        OpsProgressStage,
        ops_sse_handler,
    )
    
    start_time = time.perf_counter()
    
    # Stage display messages (Korean)
    STAGE_MESSAGES = {
        OpsProgressStage.INIT: "초기화 중...",
        OpsProgressStage.RESOLVING: "질의 분석 중...",
        OpsProgressStage.PLANNING: "실행 계획 수립 중...",
        OpsProgressStage.VALIDATING: "계획 검증 중...",
        OpsProgressStage.EXECUTING: "데이터 조회 및 분석 중...",
        OpsProgressStage.COMPOSING: "결과 종합 중...",
        OpsProgressStage.PRESENTING: "응답 생성 중...",
        OpsProgressStage.COMPLETE: "완료",
        OpsProgressStage.ERROR: "오류 발생",
    }
    
    def elapsed_ms() -> float:
        return round((time.perf_counter() - start_time) * 1000, 1)
    
    async def event_generator():
        """Generate SSE events during query execution."""
        status = "ok"
        trace_status = "success"
        active_trace_id = str(uuid.uuid4())
        result = None
        envelope_blocks = []
        next_actions = []
        trace_payload = {}
        meta = {}
        history_id = None
        completed_stages = []
        
        try:
            # Stage 1: Init
            yield _sse_event("progress", {
                "stage": OpsProgressStage.INIT.value,
                "message": STAGE_MESSAGES[OpsProgressStage.INIT],
                "elapsed_ms": elapsed_ms(),
                "details": {
                    "question_preview": payload.question[:100] + (
                        "..." if len(payload.question) > 100 else ""
                    )
                }
            })
            completed_stages.append(OpsProgressStage.INIT.value)
            
            # Create history entry
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
                    "uiMode": "all",
                    "backendMode": "all",
                    "streaming": True,
                },
            )
            
            try:
                with get_session_context() as session:
                    session.add(history_entry)
                    session.commit()
                    session.refresh(history_entry)
                history_id = history_entry.id
            except Exception as exc:
                logger.exception("ci.history.create_failed", exc_info=exc)
            
            # Stage 2: Resolving
            yield _sse_event("progress", {
                "stage": OpsProgressStage.RESOLVING.value,
                "message": STAGE_MESSAGES[OpsProgressStage.RESOLVING],
                "elapsed_ms": elapsed_ms(),
                "completed_stages": completed_stages,
            })
            completed_stages.append(OpsProgressStage.RESOLVING.value)
            
            # Load assets
            settings = get_settings()
            resolver_asset_name = (
                payload.resolver_asset or settings.ops_default_resolver_asset
            )
            schema_asset_name = payload.schema_asset or settings.ops_default_schema_asset
            source_asset_name = payload.source_asset or settings.ops_default_source_asset
            
            resolver_payload = (
                load_resolver_asset(resolver_asset_name) if resolver_asset_name else None
            )
            schema_payload = (
                load_catalog_asset(schema_asset_name) if schema_asset_name else None
            )
            source_payload = (
                load_source_asset(source_asset_name) if source_asset_name else None
            )
            mapping_payload, _ = load_mapping_asset("graph_relation", scope="ops")
            load_policy_asset("plan_budget", scope="ops")
            
            # Apply resolver rules if any
            normalized_question = payload.question
            if resolver_payload and "rules" in resolver_payload:
                # Apply basic resolver rules (simplified)
                pass
            
            # Stage 3: Planning
            yield _sse_event("progress", {
                "stage": OpsProgressStage.PLANNING.value,
                "message": STAGE_MESSAGES[OpsProgressStage.PLANNING],
                "elapsed_ms": elapsed_ms(),
                "completed_stages": completed_stages,
            })
            completed_stages.append(OpsProgressStage.PLANNING.value)
            
            # Generate plan
            plan_output: PlanOutput | None = None
            plan_raw = None
            plan_validated = None
            plan_trace = {"asset_context": {}}
            
            clear_spans()
            planner_span = start_span("planner", "stage")
            
            try:
                plan_output = planner_llm.create_plan_output(
                    normalized_question,
                    schema_context=schema_payload,
                    source_context=source_payload,
                )
                end_span(planner_span, links={"plan_path": "plan.raw"})
            except Exception as e:
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
                    plan_validated, plan_trace = validator.validate_plan(
                        plan_raw, resolver_payload=resolver_payload
                    )
                    end_span(validator_span, links={"plan_path": "plan.validated"})
                except Exception as e:
                    end_span(
                        validator_span,
                        status="error",
                        summary={"error_type": type(e).__name__, "error_message": str(e)},
                    )
                    raise
                plan_output = plan_output.model_copy(update={"plan": plan_validated})
            
            # Handle direct/reject routes
            if plan_output.kind in (PlanOutputKind.DIRECT, PlanOutputKind.REJECT):
                from app.modules.ops.services.orchestration.blocks import text_block
                
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                
                if plan_output.kind == PlanOutputKind.DIRECT and plan_output.direct_answer:
                    answer = plan_output.direct_answer.answer
                    blocks = [text_block(answer)]
                    references = plan_output.direct_answer.references
                    route_reason = plan_output.direct_answer.reasoning or "Direct answer"
                else:
                    reject_reason = (
                        plan_output.reject_payload.reason
                        if plan_output.reject_payload
                        else "Not supported"
                    )
                    answer = f"Query rejected: {reject_reason}"
                    blocks = [text_block(answer)]
                    references = []
                    route_reason = plan_output.reasoning or "Rejected"
                
                trace_payload = {
                    "route": plan_output.kind.value,
                    "tool_calls": [],
                    "references": references,
                    "errors": [],
                    "tenant_id": tenant_id,
                    "trace_id": active_trace_id,
                }
                meta = {
                    "route": plan_output.kind.value,
                    "route_reason": route_reason,
                    "timing_ms": duration_ms,
                    "summary": answer,
                    "trace_id": active_trace_id,
                }
                result = {
                    "answer": answer,
                    "blocks": blocks,
                    "trace": trace_payload,
                    "next_actions": [],
                    "meta": meta,
                }
                envelope_blocks = blocks
            else:
                # Stage 4: Executing
                yield _sse_event("progress", {
                    "stage": OpsProgressStage.EXECUTING.value,
                    "message": STAGE_MESSAGES[OpsProgressStage.EXECUTING],
                    "elapsed_ms": elapsed_ms(),
                    "completed_stages": completed_stages,
                })
                completed_stages.append(OpsProgressStage.EXECUTING.value)
                
                # Execute with Orchestrator Runner
                runner_span = start_span("runner", "stage")
                
                try:
                    runner = OpsOrchestratorRunner(
                        plan_validated,
                        plan_raw,
                        tenant_id,
                        normalized_question,
                        plan_trace,
                        asset_overrides=payload.asset_overrides,
                    )
                    runner._flow_spans_enabled = True
                    runner._runner_span_id = runner_span
                    result = runner.run(plan_output)
                    
                    # Send tool execution events
                    tool_calls = result.get("trace", {}).get("tool_calls", [])
                    for tc in tool_calls:
                        yield _sse_event("tool_complete", {
                            "tool_type": tc.get("tool_type", "unknown"),
                            "tool_name": tc.get("tool_name", "unknown"),
                            "elapsed_ms": tc.get("timing_ms", 0),
                            "status": "completed",
                        })
                    
                    next_actions = result.get("next_actions") or []
                    envelope_blocks = result.get("blocks") or []
                    trace_payload = result.get("trace") or {}
                    meta = result.get("meta") or {}
                    trace_status = "error" if trace_payload.get("errors") else "success"
                    
                    end_span(runner_span)
                except Exception as e:
                    end_span(
                        runner_span,
                        status="error",
                        summary={"error_type": type(e).__name__, "error_message": str(e)},
                    )
                    raise
            
            # Stage 5: Composing
            yield _sse_event("progress", {
                "stage": OpsProgressStage.COMPOSING.value,
                "message": STAGE_MESSAGES[OpsProgressStage.COMPOSING],
                "elapsed_ms": elapsed_ms(),
                "completed_stages": completed_stages,
            })
            completed_stages.append(OpsProgressStage.COMPOSING.value)
            
            # Stream blocks
            for i, block in enumerate(envelope_blocks):
                yield _sse_event("block", {
                    "block": block,
                    "index": i,
                    "total": len(envelope_blocks),
                })
            
            # Stage 6: Presenting
            yield _sse_event("progress", {
                "stage": OpsProgressStage.PRESENTING.value,
                "message": STAGE_MESSAGES[OpsProgressStage.PRESENTING],
                "elapsed_ms": elapsed_ms(),
                "completed_stages": completed_stages,
            })
            completed_stages.append(OpsProgressStage.PRESENTING.value)
            
            # Inject trace_id
            if result:
                if result.get("meta") is None:
                    result["meta"] = {}
                result["meta"]["trace_id"] = active_trace_id
                if result.get("trace") is None:
                    result["trace"] = {}
                result["trace"]["trace_id"] = active_trace_id
            
            # Complete event
            yield _sse_event("complete", {
                "answer": result.get("answer", "") if result else "",
                "blocks": envelope_blocks,
                "meta": {**(meta or {}), "timing_ms": elapsed_ms()},
                "trace": trace_payload,
                "next_actions": next_actions,
                "timing": {
                    "total_ms": elapsed_ms(),
                },
                "completed_stages": completed_stages,
            })
            
        except Exception as exc:
            status = "error"
            trace_status = "error"
            logger.exception("ci.ask.stream.error", exc_info=exc)
            
            yield _sse_event("error", {
                "message": str(exc),
                "stage": "execution",
                "elapsed_ms": elapsed_ms(),
            })
        
        finally:
            elapsed = elapsed_ms()
            
            # Persist trace
            flow_spans = get_all_spans()
            request_payload = {
                "question": payload.question,
                "rerun": payload.rerun.dict(exclude_none=True) if payload.rerun else None,
            }
            
            try:
                with get_session_context() as session:
                    persist_execution_trace(
                        session=session,
                        trace_id=active_trace_id,
                        parent_trace_id=None,
                        feature="ops",
                        endpoint="/ops/ask/stream",
                        method="POST",
                        ops_mode=get_settings().ops_mode,
                        question=payload.question,
                        status=trace_status,
                        duration_ms=int(elapsed),
                        request_payload=request_payload,
                        plan_raw=trace_payload.get("plan_raw") if trace_payload else None,
                        plan_validated=trace_payload.get("plan_validated") if trace_payload else None,
                        trace_payload=trace_payload if trace_payload else {},
                        answer_meta=meta if meta else None,
                        blocks=envelope_blocks if envelope_blocks else None,
                        flow_spans=flow_spans if flow_spans else None,
                    )
            except Exception as exc:
                logger.exception("ops.trace.persist_failed", exc_info=exc)
            
            # Update history
            if history_id:
                try:
                    with get_session_context() as session:
                        history_entry = session.get(QueryHistory, history_id)
                        if history_entry:
                            history_entry.status = status
                            history_entry.trace_id = active_trace_id
                            if result:
                                history_entry.summary = (
                                    result.get("meta", {}).get("summary")
                                    or result.get("meta", {}).get("answer", "")[:200]
                                )
                                history_entry.response = result
                            session.add(history_entry)
                            session.commit()
                except Exception as exc:
                    logger.exception("ci.history.update_failed", exc_info=exc)
            
            logger.info(
                "ops.ask.stream.done",
                extra={
                    "status": status,
                    "elapsed_ms": elapsed,
                    "blocks_count": len(envelope_blocks),
                },
            )
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
