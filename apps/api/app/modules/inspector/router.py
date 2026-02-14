from __future__ import annotations

from datetime import datetime
from typing import List

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.audit_log.crud import get_audit_logs_by_trace
from app.modules.audit_log.models import TbAuditLog
from app.modules.inspector import crud
from app.modules.inspector.models import TbExecutionTrace
from app.modules.inspector.regression import service
from app.modules.inspector.regression.schemas import RegressionAnalysisRequest
from app.modules.inspector.schemas import (
    ExecutionTraceCreate,
    ExecutionTraceRead,
    TraceSummary,
    UIRenderPayload,
)

router = APIRouter(prefix="/inspector", tags=["inspector"])


def _truncate_question(question: str | None, length: int = 120) -> str:
    if not question:
        return ""
    return question[:length] + "…" if len(question) > length else question


@router.get("/traces", response_model=ResponseEnvelope)
def list_traces(
    q: str | None = Query(
        None, description="Search text for question/feature/endpoint"
    ),
    feature: str | None = Query(None),
    status: str | None = Query(None),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    asset_id: str | None = Query(None),
    parent_trace_id: str | None = Query(None),
    route: str | None = Query(
        None, description="Filter by route: direct, orch, reject"
    ),
    replan_count: int | None = Query(None, description="Filter by number of replans"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    traces, total = crud.list_execution_traces(
        session,
        q=q,
        feature=feature,
        status=status,
        from_ts=from_ts,
        to_ts=to_ts,
        asset_id=asset_id,
        parent_trace_id=parent_trace_id,
        route=route,
        replan_count=replan_count,
        limit=limit,
        offset=offset,
    )
    summaries: List[TraceSummary] = []
    for trace in traces:
        # Calculate replan_count from replan_events
        replan_count = len(trace.replan_events) if trace.replan_events else 0
        summaries.append(
            TraceSummary(
                trace_id=trace.trace_id,
                created_at=trace.created_at,
                feature=trace.feature,
                status=trace.status,
                duration_ms=trace.duration_ms,
                question_snippet=_truncate_question(trace.question),
                applied_asset_versions=trace.asset_versions or [],
                route=trace.route,
                replan_count=replan_count,
            )
        )
    return ResponseEnvelope.success(
        data={
            "traces": [summary.model_dump() for summary in summaries],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.post("/traces", response_model=ResponseEnvelope)
def create_trace(
    payload: ExecutionTraceCreate, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    if crud.get_execution_trace(session, payload.trace_id):
        raise HTTPException(
            status_code=409, detail=f"Trace {payload.trace_id} already exists"
        )

    trace = TbExecutionTrace(
        trace_id=payload.trace_id,
        parent_trace_id=payload.parent_trace_id,
        feature=payload.feature,
        endpoint=payload.endpoint,
        method=payload.method,
        ops_mode=payload.ops_mode,
        question=payload.question,
        status=payload.status,
        duration_ms=payload.duration_ms,
        request_payload=payload.request_payload,
        applied_assets=payload.applied_assets,
        asset_versions=payload.asset_versions,
        fallbacks=payload.fallbacks,
        plan_raw=payload.plan_raw,
        plan_validated=payload.plan_validated,
        execution_steps=payload.execution_steps,
        references=payload.references,
        answer=payload.answer,
        ui_render=payload.ui_render,
        audit_links=payload.audit_links,
        flow_spans=[span.model_dump() for span in (payload.flow_spans or [])],
        route=payload.route,
        stage_inputs=payload.stage_inputs or [],
        stage_outputs=payload.stage_outputs or [],
        replan_events=payload.replan_events or [],
    )
    created = crud.create_execution_trace(session, trace)
    return ResponseEnvelope.success(data={"trace_id": created.trace_id})


@router.get("/traces/{trace_id}", response_model=ResponseEnvelope)
def get_trace(
    trace_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    trace = crud.get_execution_trace(session, trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    audit_logs = get_audit_logs_by_trace(session, trace_id)
    trace_data = ExecutionTraceRead.model_validate(trace.model_dump())
    return ResponseEnvelope.success(
        data={
            "trace": trace_data.model_dump(),
            "audit_logs": [log.model_dump() for log in audit_logs],
        }
    )


@router.get("/audit-logs", response_model=ResponseEnvelope)
def list_inspector_audit_logs(
    trace_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    statement = select(TbAuditLog)
    if trace_id:
        statement = statement.where(TbAuditLog.trace_id == trace_id)
    if resource_type:
        statement = statement.where(TbAuditLog.resource_type == resource_type)
    if resource_id:
        statement = statement.where(TbAuditLog.resource_id == resource_id)
    statement = (
        statement.order_by(TbAuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    logs = session.exec(statement).all()
    return ResponseEnvelope.success(
        data={
            "logs": [log.model_dump() for log in logs],
            "paging": {"limit": limit, "offset": offset, "returned": len(logs)},
        }
    )


@router.post("/traces/{trace_id}/ui-render", response_model=ResponseEnvelope)
def post_ui_render(
    trace_id: str,
    payload: UIRenderPayload,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    trace = crud.get_execution_trace(session, trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    trace.ui_render = payload.model_dump()
    session.add(trace)
    session.commit()
    session.refresh(trace)
    return ResponseEnvelope.success(data={"trace_id": trace.trace_id})


@router.post("/regression/analyze", response_model=ResponseEnvelope)
async def analyze_regression(
    request: RegressionAnalysisRequest,
) -> ResponseEnvelope:
    """Perform regression analysis between two traces."""
    try:
        result = await service.regression_service.analyze_stage_regression(request)
        return ResponseEnvelope.success(data=result.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/regression/{analysis_id}", response_model=ResponseEnvelope)
def get_regression_analysis(
    analysis_id: str,
) -> ResponseEnvelope:
    """Get regression analysis by ID."""
    analysis = service.regression_service.analysis_registry.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return ResponseEnvelope.success(data=analysis.model_dump())


@router.post("/regression/stage-compare", response_model=ResponseEnvelope)
async def compare_stages(
    baseline_trace_id: str,
    comparison_trace_id: str,
    stages: list[str] | None = None,
) -> ResponseEnvelope:
    """Compare stages between two traces directly."""
    try:
        result = await service.regression_service.compare_stages_direct(
            baseline_trace_id, comparison_trace_id, stages
        )
        return ResponseEnvelope.success(data=result.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
