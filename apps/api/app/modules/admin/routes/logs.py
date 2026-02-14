"""
Admin Logs API

Provides endpoints for viewing system logs including:
- Database logs (query_history, execution_trace, audit_log, etc.)
- File logs (API server, WEB server)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from app.modules.admin import crud as admin_crud
from core.db import get_session
from fastapi import APIRouter, Depends, Query
from schemas import ResponseEnvelope
from sqlmodel import Session

router = APIRouter(prefix="/logs", tags=["admin-logs"])


@router.get("/query-history", response_model=ResponseEnvelope)
def get_query_history(
    feature: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get query history logs.

    Args:
        feature: Filter by feature (ops, docs)
        status: Filter by status (ok, error, processing)
        date_from: Start date filter
        date_to: End date filter
        limit: Number of records to return
        offset: Offset for pagination
        session: Database session

    Returns:
        ResponseEnvelope with query history records
    """
    records, total = admin_crud.list_query_history(
        session,
        feature=feature,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope.success(
        data={
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/execution-trace", response_model=ResponseEnvelope)
def get_execution_trace(
    feature: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get execution trace logs.

    Args:
        feature: Filter by feature
        status: Filter by status
        date_from: Start date filter
        date_to: End date filter
        limit: Number of records to return
        offset: Offset for pagination
        session: Database session

    Returns:
        ResponseEnvelope with execution trace records
    """
    records, total = admin_crud.list_execution_traces(
        session,
        feature=feature,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope.success(
        data={
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/audit", response_model=ResponseEnvelope)
def get_audit_logs(
    resource_type: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get audit logs.

    Args:
        resource_type: Filter by resource type
        action: Filter by action
        date_from: Start date filter
        date_to: End date filter
        limit: Number of records to return
        offset: Offset for pagination
        session: Database session

    Returns:
        ResponseEnvelope with audit log records
    """
    records, total = admin_crud.list_audit_logs(
        session,
        resource_type=resource_type,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope.success(
        data={
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/file/{log_type}/tail", response_model=ResponseEnvelope)
def tail_log_file(
    log_type: Literal["api", "web"],
    lines: int = Query(default=100, le=1000),
) -> ResponseEnvelope:
    """Get last N lines from log file.

    Args:
        log_type: Type of log (api or web)
        lines: Number of lines to return

    Returns:
        ResponseEnvelope with log lines
    """
    from core.config import get_settings
    settings = get_settings()

    # Determine log file path from settings
    if log_type == "api":
        log_path = settings.log_api_file_path
    else:  # web
        log_path = settings.log_web_file_path

    # Check if file exists
    if not os.path.exists(log_path):
        return ResponseEnvelope.success(
            data={
                "lines": [],
                "file": log_path,
                "exists": False,
            }
        )

    # Read last N lines
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read all lines
            all_lines = f.readlines()
            # Get last N lines
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return ResponseEnvelope.success(
            data={
                "lines": [line.rstrip() for line in log_lines],
                "file": log_path,
                "exists": True,
                "total_lines": len(all_lines),
            }
        )
    except Exception as e:
        return ResponseEnvelope.error(
            message=f"Error reading log file: {str(e)}"
        )


@router.get("/stats", response_model=ResponseEnvelope)
def get_log_stats(
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get log statistics.

    Returns:
        ResponseEnvelope with log statistics
    """
    # Use CRUD functions for stats
    query_stats = admin_crud.get_query_history_stats(session)
    trace_stats = admin_crud.get_execution_trace_stats(session)
    audit_stats = admin_crud.get_audit_log_stats(session)

    return ResponseEnvelope.success(
        data={
            "query_history": query_stats,
            "execution_trace": trace_stats,
            "audit_log": audit_stats,
        }
    )
