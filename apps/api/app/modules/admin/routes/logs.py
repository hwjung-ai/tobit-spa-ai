"""
Admin Logs API

Provides endpoints for viewing system logs including:
- Database logs (query_history, execution_trace, audit_log, etc.)
- File logs (API server, WEB server)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Literal

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
    from sqlalchemy import text

    # Build SQL query (avoid SQLModel Row mapping issues)
    sql = """
        SELECT
            id, tenant_id, user_id, feature, question, summary,
            status, trace_id, created_at, response, metadata
        FROM query_history
        WHERE 1=1
    """
    params: dict[str, Any] = {}

    if feature:
        sql += " AND feature = :feature"
        params["feature"] = feature
    if status:
        sql += " AND status = :status"
        params["status"] = status
    if date_from:
        sql += " AND created_at >= :date_from"
        params["date_from"] = date_from
    if date_to:
        sql += " AND created_at <= :date_to"
        params["date_to"] = date_to

    # Get total count
    count_sql = "SELECT COUNT(*) FROM query_history WHERE 1=1"
    if feature:
        count_sql += " AND feature = :feature"
    if status:
        count_sql += " AND status = :status"
    if date_from:
        count_sql += " AND created_at >= :date_from"
    if date_to:
        count_sql += " AND created_at <= :date_to"

    total = session.execute(text(count_sql), params).scalar()

    sql += " ORDER BY created_at DESC"
    sql += f" LIMIT {limit} OFFSET {offset}"

    result = session.execute(text(sql), params)
    records = []
    for row in result:
        records.append({
            "id": str(row[0]),
            "tenant_id": row[1],
            "user_id": row[2],
            "feature": row[3],
            "question": row[4],
            "summary": row[5],
            "status": row[6],
            "trace_id": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "response": row[9],
            "metadata": row[10],
        })

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
    # Import here to avoid circular dependency
    from sqlalchemy import text

    # Build SQL query
    sql = """
        SELECT
            trace_id,
            parent_trace_id,
            feature,
            endpoint,
            method,
            ops_mode,
            question,
            status,
            duration_ms,
            route,
            created_at
        FROM tb_execution_trace
        WHERE 1=1
    """
    params: dict[str, Any] = {}

    if feature:
        sql += " AND feature = :feature"
        params["feature"] = feature
    if status:
        sql += " AND status = :status"
        params["status"] = status
    if date_from:
        sql += " AND created_at >= :date_from"
        params["date_from"] = date_from
    if date_to:
        sql += " AND created_at <= :date_to"
        params["date_to"] = date_to

    sql += " ORDER BY created_at DESC"
    sql += f" LIMIT {limit} OFFSET {offset}"

    # Execute query
    result = session.execute(text(sql), params)
    records = []
    for row in result:
        records.append({
            "trace_id": row[0],
            "parent_trace_id": row[1],
            "feature": row[2],
            "endpoint": row[3],
            "method": row[4],
            "ops_mode": row[5],
            "question": row[6],
            "status": row[7],
            "duration_ms": row[8],
            "route": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
        })

    # Get total count
    count_sql = "SELECT COUNT(*) FROM tb_execution_trace WHERE 1=1"
    if feature:
        count_sql += " AND feature = :feature"
    if status:
        count_sql += " AND status = :status"
    if date_from:
        count_sql += " AND created_at >= :date_from"
    if date_to:
        count_sql += " AND created_at <= :date_to"

    total = session.execute(text(count_sql), params).scalar()

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
    from sqlalchemy import text

    try:
        sql = """
            SELECT
                audit_id, trace_id, resource_type, resource_id,
                action, user_id, timestamp, details
            FROM tb_audit_log
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        if resource_type:
            sql += " AND resource_type = :resource_type"
            params["resource_type"] = resource_type
        if action:
            sql += " AND action = :action"
            params["action"] = action
        if date_from:
            sql += " AND timestamp >= :date_from"
            params["date_from"] = date_from
        if date_to:
            sql += " AND timestamp <= :date_to"
            params["date_to"] = date_to

        count_sql = "SELECT COUNT(*) FROM tb_audit_log WHERE 1=1"
        if resource_type:
            count_sql += " AND resource_type = :resource_type"
        if action:
            count_sql += " AND action = :action"
        if date_from:
            count_sql += " AND timestamp >= :date_from"
        if date_to:
            count_sql += " AND timestamp <= :date_to"

        total = session.execute(text(count_sql), params).scalar()

        sql += " ORDER BY timestamp DESC"
        sql += f" LIMIT {limit} OFFSET {offset}"

        result = session.execute(text(sql), params)
        records = []
        for row in result:
            records.append({
                "audit_id": str(row[0]),
                "trace_id": row[1],
                "resource_type": row[2],
                "resource_id": row[3],
                "action": row[4],
                "user_id": row[5],
                "timestamp": row[6].isoformat() if row[6] else None,
                "details": row[7],
            })
    except Exception:
        records = []
        total = 0

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
    from sqlalchemy import text

    try:
        query_stats = session.exec(
            text("""
                SELECT feature, status, COUNT(*) as count
                FROM query_history
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY feature, status
            """)
        ).all()
    except Exception:
        query_stats = []

    try:
        trace_stats = session.exec(
            text("""
                SELECT feature, status, COUNT(*) as count, AVG(duration_ms) as avg_duration
                FROM tb_execution_trace
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY feature, status
            """)
        ).all()
    except Exception:
        trace_stats = []

    try:
        audit_stats = session.exec(
            text("""
                SELECT resource_type, action, COUNT(*) as count
                FROM tb_audit_log
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY resource_type, action
            """)
        ).all()
    except Exception:
        audit_stats = []

    return ResponseEnvelope.success(
        data={
            "query_history": [
                {"feature": row[0], "status": row[1], "count": row[2]}
                for row in query_stats
            ],
            "execution_trace": [
                {
                    "feature": row[0],
                    "status": row[1],
                    "count": row[2],
                    "avg_duration_ms": float(row[3]) if row[3] else 0,
                }
                for row in trace_stats
            ],
            "audit_log": [
                {"resource_type": row[0], "action": row[1], "count": row[2]}
                for row in audit_stats
            ],
        }
    )
