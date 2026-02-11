"""
OPS Query Route

Handles standard OPS query processing endpoints.

Endpoints:
    POST /ops/query - Process OPS query with specified mode
    GET /ops/observability/kpis - Retrieve observability metrics
"""

from __future__ import annotations

import uuid
from datetime import datetime

from core.auth import get_current_user
from core.db import get_session, get_session_context
from core.logging import get_logger, set_request_context
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from models.history import QueryHistory
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.auth.models import TbUser
from app.modules.ops.schemas import OpsQueryRequest
from app.modules.ops.security import SecurityUtils
from app.modules.ops.services import handle_ops_query
from app.modules.ops.services.data_export import DataExporter
from app.modules.ops.services.observability_service import collect_observability_metrics
from app.modules.ops.services.report_service import pdf_report_service

from .utils import _tenant_id

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.post("/query", response_model=ResponseEnvelope)
def query_ops(
    payload: OpsQueryRequest,
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Process OPS query with specified mode.

    Creates a history entry for the query, executes the query using the specified
    mode (config, history, relation, metric, etc.), and updates the history with
    the response.

    Args:
        payload: OPS query request with mode and question
        request: HTTP request object

    Returns:
        ResponseEnvelope with query answer and trace data

    """
    # 요청 받을 때 history 생성 (상태: processing)
    user_id = str(current_user.id)

    # Set request context for tenant_id to be available throughout the request
    request_id = str(uuid.uuid4())
    set_request_context(request_id=request_id, tenant_id=tenant_id, mode="ops")

    # 로깅을 위해 요청 데이터 마스킹
    masked_payload = SecurityUtils.mask_dict(payload.model_dump())
    logger.debug(
        "ops.query.request_received",
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

    Exports observability metrics, stats, timeline, and errors to CSV or JSON format.

    Args:
        format_type: Export format (csv, json)
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


@router.post("/conversation/summary")
def get_conversation_summary(
    request_data: dict,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(_tenant_id)
) -> ResponseEnvelope:
    """Get conversation summary for preview.

    Returns a structured summary of the conversation including:
    - Title, date, topic metadata
    - Questions and answers
    - Key insights

    Args:
        request_data: Dictionary containing:
            - history_id: Optional specific history entry ID
            - thread_id: Optional thread ID to get full conversation
            - summary_type: "individual" (개별 요약) or "overall" (전체 요약)
        session: Database session dependency

    Returns:
        ResponseEnvelope with summary data
    """
    try:
        history_id = request_data.get("history_id")
        thread_id = request_data.get("thread_id")
        summary_type = request_data.get("summary_type", "individual")  # individual | overall

        if not history_id and not thread_id:
            return ResponseEnvelope.error(
                message="Either history_id or thread_id is required"
            )

        # Fetch history entries
        query = session.query(QueryHistory).filter(
            QueryHistory.tenant_id == tenant_id
        )

        if history_id:
            query = query.filter(QueryHistory.id == history_id)
        elif thread_id:
            query = query.filter(QueryHistory.thread_id == thread_id).order_by(
                QueryHistory.created_at.asc()
            )

        entries = query.all()

        if not entries:
            return ResponseEnvelope.error(
                message="No conversation history found"
            )

        # Build summary data
        first_entry = entries[0]

        # Extract title from first question
        title = request_data.get("title")
        if not title:
            question_text = first_entry.question or ""
            title = question_text[:50] + "..." if len(question_text) > 50 else question_text

        # Build Q&A list
        questions_and_answers = []
        for entry in entries:
            qa = {
                "question": entry.question or "",
                "timestamp": entry.created_at.isoformat() if entry.created_at else None,
                "mode": entry.meta.get("mode", "unknown") if entry.meta else "unknown",
            }

            # Parse answer to extract summary and blocks
            if entry.answer:
                answer = entry.answer if isinstance(entry.answer, dict) else {}
                qa["summary"] = answer.get("summary", "")
                qa["blocks"] = answer.get("blocks", [])

                # Extract references if available
                meta = answer.get("meta", {})
                if isinstance(meta, dict):
                    refs = meta.get("references", [])
                    if refs:
                        qa["references"] = refs

            questions_and_answers.append(qa)

        summary_data = {
            "title": title,
            "topic": request_data.get("topic", "OPS 분석"),
            "date": first_entry.created_at.strftime("%Y-%m-%d") if first_entry.created_at else "",
            "created_at": datetime.now().isoformat(),
            "question_count": len(entries),
            "summary_type": summary_type,
            "questions_and_answers": questions_and_answers,
        }

        # If overall summary requested, generate it
        if summary_type == "overall":
            overall_summary = _generate_overall_summary(questions_and_answers)
            summary_data["overall_summary"] = overall_summary

        return ResponseEnvelope.success(data=summary_data)

    except Exception as e:
        logger.error(f"Failed to get conversation summary: {e}", exc_info=True)
        return ResponseEnvelope.error(message=str(e))


def _generate_overall_summary(questions_and_answers: list) -> str:
    """Generate overall summary from Q&A list.

    Creates a concise summary of the entire conversation.
    """
    if not questions_and_answers:
        return "대화 내용이 없습니다."

    # Extract key points from each Q&A
    key_points = []

    for qa in questions_and_answers:
        if qa.get("summary"):
            key_points.append(qa["summary"])
        elif qa.get("question"):
            key_points.append(f"질문: {qa['question']}")

    if not key_points:
        return f"{len(questions_and_answers)}개의 질문이 있으나 요약 내용이 없습니다."

    # Create overall summary
    overall = f"""전체 대화 요약 ({len(questions_and_answers)}개의 질문)

주요 내용:
"""

    for i, point in enumerate(key_points[:5], 1):
        overall += f"{i}. {point}\n"

    if len(key_points) > 5:
        overall += f"\n... 그 외 {len(key_points) - 5}개의 질문이 있습니다."

    return overall


@router.post("/conversation/export/pdf")
def export_conversation_pdf(
    request_data: dict,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(_tenant_id)
) -> ResponseEnvelope:
    """Export conversation as PDF report.

    Generates a professional PDF report from the conversation history.

    Args:
        request_data: Dictionary containing:
            - history_id: Optional specific history entry ID
            - thread_id: Optional thread ID to get full conversation
            - title: Optional report title
            - topic: Optional report topic
            - summary_type: "individual" (개별 요약) or "overall" (전체 요약)
        session: Database session dependency

    Returns:
        ResponseEnvelope with PDF content (base64 encoded) and metadata
    """
    try:
        import base64
        from datetime import datetime

        history_id = request_data.get("history_id")
        thread_id = request_data.get("thread_id")
        title = request_data.get("title")
        topic = request_data.get("topic", "OPS 분석")
        summary_type = request_data.get("summary_type", "individual")

        if not history_id and not thread_id:
            return ResponseEnvelope.error(
                message="Either history_id or thread_id is required"
            )

        # Fetch history entries
        query = session.query(QueryHistory).filter(
            QueryHistory.tenant_id == tenant_id
        )

        if history_id:
            query = query.filter(QueryHistory.id == history_id)
        elif thread_id:
            query = query.filter(QueryHistory.thread_id == thread_id).order_by(
                QueryHistory.created_at.asc()
            )

        entries = query.all()

        if not entries:
            return ResponseEnvelope.error(
                message="No conversation history found"
            )

        # Build conversation data for PDF
        first_entry = entries[0]

        if not title:
            question_text = first_entry.question or ""
            title = question_text[:40] + "..." if len(question_text) > 40 else question_text

        # Build Q&A list for PDF
        questions_and_answers = []
        for entry in entries:
            qa = {
                "question": entry.question or "",
                "timestamp": entry.created_at.strftime("%Y-%m-%d %H:%M:%S") if entry.created_at else "",
                "mode": entry.meta.get("mode", "unknown") if entry.meta else "unknown",
            }

            # Parse answer to extract summary and blocks
            if entry.answer:
                answer = entry.answer if isinstance(entry.answer, dict) else {}
                qa["summary"] = answer.get("summary", "")
                qa["blocks"] = answer.get("blocks", [])

                # Extract references if available
                meta = answer.get("meta", {})
                if isinstance(meta, dict):
                    refs = meta.get("references", [])
                    if refs:
                        qa["references"] = refs

            questions_and_answers.append(qa)

        conversation_data = {
            "title": title,
            "topic": topic,
            "date": first_entry.created_at.strftime("%Y-%m-%d") if first_entry.created_at else datetime.now().strftime("%Y-%m-%d"),
            "questions_and_answers": questions_and_answers,
        }

        # Add overall summary if requested
        if summary_type == "overall":
            conversation_data["overall_summary"] = _generate_overall_summary(questions_and_answers)

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
