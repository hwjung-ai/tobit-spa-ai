"""API Manager logs endpoints for retrieving execution history."""

import logging

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import ResponseEnvelope
from sqlmodel import Session

from ..crud import list_exec_logs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])


@router.get("/apis/{api_id}/execution-logs", response_model=ResponseEnvelope)
async def get_logs(
    api_id: str,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """Get API execution history from available execution log table(s)."""
    try:
        logs = list_exec_logs(session, api_id, limit)
        log_list = []
        for log in logs:
            exec_id = getattr(log, "exec_id", None) or getattr(log, "id", None)
            executed_at = getattr(log, "executed_at", None) or getattr(
                log, "execution_time", None
            )
            status = getattr(log, "status", None) or getattr(log, "response_status", None)
            row_count = getattr(log, "row_count", None)
            if row_count is None:
                row_count = getattr(log, "rows_affected", 0)
            log_list.append(
                {
                    "exec_id": str(exec_id) if exec_id else None,
                    "api_id": str(log.api_id),
                    "executed_at": executed_at.isoformat() if executed_at else None,
                    "executed_by": log.executed_by,
                    "status": status,
                    "duration_ms": log.duration_ms,
                    "row_count": row_count,
                    "request_params": log.request_params,
                    "error_message": log.error_message,
                }
            )
        return ResponseEnvelope.success(data={"api_id": api_id, "logs": log_list})
    except Exception as e:
        logger.error(f"Get logs failed: {str(e)}")
        raise HTTPException(500, str(e))
