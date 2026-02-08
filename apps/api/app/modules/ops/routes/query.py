"""
OPS Query Route

Handles standard OPS query processing endpoints.

Endpoints:
    POST /ops/query - Process OPS query with specified mode
    GET /ops/observability/kpis - Retrieve observability metrics
"""

from __future__ import annotations

import uuid
from typing import Any

from core.db import get_session_context
from core.logging import get_logger, set_request_context
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from models.history import QueryHistory
from schemas import ResponseEnvelope
from sqlmodel import Session
from core.db import get_session

from app.modules.ops.schemas import OpsQueryRequest
from app.modules.ops.services import handle_ops_query
from app.modules.ops.services.observability_service import collect_observability_metrics
from app.modules.ops.services.data_export import DataExporter
from app.modules.ops.security import SecurityUtils
from fastapi.responses import Response

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.post("/query", response_model=ResponseEnvelope)
def query_ops(payload: OpsQueryRequest, request: Request) -> ResponseEnvelope:
    """Process OPS query with specified mode.

    Creates a history entry for the query, executes the query using the specified
    mode (config, history, relation, metric, etc.), and updates the history with
    the response.

    Args:
        payload: OPS query request with mode and question
        request: HTTP request object

    Returns:
        ResponseEnvelope with query answer and trace data

    Raises:
        HTTPException: If X-Tenant-Id header is missing
    """
    # 요청 받을 때 history 생성 (상태: processing)
    user_id = request.headers.get("X-User-Id", "default")
    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="X-Tenant-Id header is required")

    # Set request context for tenant_id to be available throughout the request
    request_id = str(uuid.uuid4())
    set_request_context(request_id=request_id, tenant_id=tenant_id, mode="ops")

    # 로깅을 위해 요청 데이터 마스킹
    masked_payload = SecurityUtils.mask_dict(payload.model_dump())
    logger.debug(
        f"ops.query.request_received",
        extra={
            "question_length": len(payload.question),
            "mode": payload.mode,
            "sanitized_payload": masked_payload,
        },
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
    except Exception as exc:
        logger.exception("ops.query.history.create_failed", exc_info=exc)
        history_id = None

    # OPS 쿼리 실행
    envelope, trace_data = handle_ops_query(payload.mode, payload.question)

    # 민감정보 제거된 응답 생성
    answer_dict = envelope.model_dump()
    trace_data_sanitized = SecurityUtils.mask_dict(trace_data) if trace_data else None

    response_payload = ResponseEnvelope.success(
        data={
            "answer": answer_dict,
            "trace": trace_data_sanitized,
        }
    )

    # 응답 완료 시 history 업데이트
    status = "ok"
    if history_id:
        try:
            with get_session_context() as session:
                history_entry = session.get(QueryHistory, history_id)
                if history_entry:
                    history_entry.status = status
                    history_entry.response = jsonable_encoder(response_payload.model_dump())
                    history_entry.summary = (
                        envelope.meta.summary if envelope.meta else ""
                    )
                    history_entry.metadata_info = jsonable_encoder(
                        {
                            "uiMode": payload.mode,
                            "backendMode": payload.mode,
                            "trace_id": envelope.meta.trace_id if envelope.meta else None,
                            "trace": trace_data_sanitized,
                        }
                    )
                    session.add(history_entry)
                    session.commit()
        except Exception as exc:
            logger.exception("ops.query.history.update_failed", exc_info=exc)

    return response_payload


@router.get("/observability/kpis", response_model=ResponseEnvelope)
def observability_kpis(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """Retrieve observability KPIs.

    Collects and returns observability metrics for monitoring OPS system health.

    Args:
        session: Database session dependency

    Returns:
        ResponseEnvelope with observability metrics
    """
    metrics = collect_observability_metrics(session)
    return ResponseEnvelope.success(data=metrics)


@router.get("/observability/export", response_model=ResponseEnvelope)
def export_observability_data(
    format_type: str = "csv",
    session: Session = Depends(get_session)
) -> ResponseEnvelope:
    """Export observability dashboard data.

    Exports observability metrics, stats, timeline, and errors to CSV, JSON, or Excel format.

    Args:
        format_type: Export format (csv, json, excel)
        session: Database session dependency

    Returns:
        ResponseEnvelope with export data (filename, content, content_type)
    """
    try:
        metrics = collect_observability_metrics(session)
        export_data = DataExporter.export_observability_data(metrics, format_type)
        return ResponseEnvelope.success(data=export_data)
    except Exception as e:
        logger.error(f"Failed to export observability data: {e}", exc_info=True)
        return ResponseEnvelope.error(message=str(e))
