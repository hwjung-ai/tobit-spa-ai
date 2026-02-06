"""
OPS RCA (Root Cause Analysis) Routes

Handles root cause analysis endpoints for investigating issues and regressions.

Endpoints:
    POST /ops/rca/analyze-trace - Analyze a single trace
    POST /ops/rca/analyze-regression - Analyze regression between traces
"""

from __future__ import annotations

from core.db import get_session
from core.logging import get_logger
from fastapi import APIRouter, Depends
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.ops.security import SecurityUtils

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.post("/rca/analyze-trace", response_model=ResponseEnvelope)
def rca_analyze_trace(
    trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Analyze a single trace for root causes.

    Runs RCA on the specified trace and returns hypotheses about potential issues
    with supporting evidence and recommended actions.

    Args:
        trace_id: ID of the execution trace to analyze
        session: Database session dependency

    Returns:
        ResponseEnvelope with list of RCA hypotheses including:
        - rank, title, confidence
        - evidence (with inspector jump links)
        - checks (verification steps)
        - recommended_actions
    """
    from app.modules.inspector.crud import get_execution_trace
    from app.modules.ops.services.rca_engine import RCAEngine

    # 로깅을 위해 trace_id 마스킹
    logger.debug(
        f"rca.analyze_trace.start",
        extra={"trace_id": SecurityUtils.mask_string(trace_id)},
    )

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
    """Analyze regression by comparing baseline and candidate traces.

    Identifies differences and analyzes root causes of regressions between
    two traces.

    Args:
        baseline_trace_id: ID of the baseline trace
        candidate_trace_id: ID of the candidate trace to compare against
        session: Database session dependency

    Returns:
        ResponseEnvelope with regression analysis including:
        - Hypotheses about root causes
        - Evidence with inspector comparison links
        - Recommended actions
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
