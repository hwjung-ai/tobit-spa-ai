"""
CRUD operations for Admin Logs module.

Centralizes all database access for query_history, execution_trace, and audit_log.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import text
from sqlmodel import Session

logger = logging.getLogger(__name__)


# ============================================================================
# Query History
# ============================================================================


def list_query_history(
    session: Session,
    feature: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[dict[str, Any]], int]:
    """
    List query history with filtering and pagination.

    Args:
        session: Database session
        feature: Filter by feature (ops, docs)
        status: Filter by status (ok, error, processing)
        date_from: Start date filter
        date_to: End date filter
        limit: Maximum results (max 200)
        offset: Pagination offset

    Returns:
        Tuple of (records, total_count)
    """
    # Build WHERE conditions
    params: dict[str, Any] = {}
    where_clauses = []

    if feature:
        where_clauses.append("feature = :feature")
        params["feature"] = feature
    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    if date_from:
        where_clauses.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM query_history WHERE 1=1{where_sql}"
    total = session.execute(text(count_sql), params).scalar()

    # Get records
    sql = f"""
        SELECT
            id, tenant_id, user_id, feature, question, summary,
            status, trace_id, created_at, response, metadata
        FROM query_history
        WHERE 1=1{where_sql}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
    """

    result = session.execute(text(sql), params)
    records = [
        {
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
        }
        for row in result
    ]

    return records, total


# ============================================================================
# Execution Trace
# ============================================================================


def list_execution_traces(
    session: Session,
    feature: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[dict[str, Any]], int]:
    """
    List execution traces with filtering and pagination.

    Args:
        session: Database session
        feature: Filter by feature
        status: Filter by status
        date_from: Start date filter
        date_to: End date filter
        limit: Maximum results (max 200)
        offset: Pagination offset

    Returns:
        Tuple of (records, total_count)
    """
    # Build WHERE conditions
    params: dict[str, Any] = {}
    where_clauses = []

    if feature:
        where_clauses.append("feature = :feature")
        params["feature"] = feature
    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    if date_from:
        where_clauses.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM tb_execution_trace WHERE 1=1{where_sql}"
    total = session.execute(text(count_sql), params).scalar()

    # Get records
    sql = f"""
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
        WHERE 1=1{where_sql}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
    """

    result = session.execute(text(sql), params)
    records = [
        {
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
        }
        for row in result
    ]

    return records, total


# ============================================================================
# Audit Log
# ============================================================================


def list_audit_logs(
    session: Session,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[dict[str, Any]], int]:
    """
    List audit logs with filtering and pagination.

    Args:
        session: Database session
        resource_type: Filter by resource type
        action: Filter by action
        date_from: Start date filter
        date_to: End date filter
        limit: Maximum results (max 200)
        offset: Pagination offset

    Returns:
        Tuple of (records, total_count)
    """
    try:
        # Build WHERE conditions
        params: dict[str, Any] = {}
        where_clauses = []

        if resource_type:
            where_clauses.append("resource_type = :resource_type")
            params["resource_type"] = resource_type
        if action:
            where_clauses.append("action = :action")
            params["action"] = action
        if date_from:
            where_clauses.append("timestamp >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append("timestamp <= :date_to")
            params["date_to"] = date_to

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        # Get total count
        count_sql = f"SELECT COUNT(*) FROM tb_audit_log WHERE 1=1{where_sql}"
        total = session.execute(text(count_sql), params).scalar()

        # Get records
        sql = f"""
            SELECT
                audit_id, trace_id, resource_type, resource_id,
                action, user_id, timestamp, details
            FROM tb_audit_log
            WHERE 1=1{where_sql}
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        """

        result = session.execute(text(sql), params)
        records = [
            {
                "audit_id": str(row[0]),
                "trace_id": row[1],
                "resource_type": row[2],
                "resource_id": row[3],
                "action": row[4],
                "user_id": row[5],
                "timestamp": row[6].isoformat() if row[6] else None,
                "details": row[7],
            }
            for row in result
        ]

        return records, total

    except Exception as e:
        logger.warning(f"Error querying audit logs: {e}")
        return [], 0


# ============================================================================
# Log Statistics
# ============================================================================


def get_query_history_stats(session: Session) -> List[dict[str, Any]]:
    """
    Get query history statistics for the last 24 hours.

    Args:
        session: Database session

    Returns:
        List of stats with keys: feature, status, count
    """
    try:
        result = session.execute(
            text("""
                SELECT feature, status, COUNT(*) as count
                FROM query_history
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY feature, status
            """)
        ).all()

        return [
            {"feature": row[0], "status": row[1], "count": row[2]}
            for row in result
        ]
    except Exception as e:
        logger.warning(f"Error getting query history stats: {e}")
        return []


def get_execution_trace_stats(session: Session) -> List[dict[str, Any]]:
    """
    Get execution trace statistics for the last 24 hours.

    Args:
        session: Database session

    Returns:
        List of stats with keys: feature, status, count, avg_duration
    """
    try:
        result = session.execute(
            text("""
                SELECT feature, status, COUNT(*) as count, AVG(duration_ms) as avg_duration
                FROM tb_execution_trace
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY feature, status
            """)
        ).all()

        return [
            {
                "feature": row[0],
                "status": row[1],
                "count": row[2],
                "avg_duration": float(row[3]) if row[3] else None,
            }
            for row in result
        ]
    except Exception as e:
        logger.warning(f"Error getting execution trace stats: {e}")
        return []


def get_audit_log_stats(session: Session) -> List[dict[str, Any]]:
    """
    Get audit log statistics for the last 24 hours.

    Args:
        session: Database session

    Returns:
        List of stats with keys: resource_type, action, count
    """
    try:
        result = session.execute(
            text("""
                SELECT resource_type, action, COUNT(*) as count
                FROM tb_audit_log
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY resource_type, action
            """)
        ).all()

        return [
            {"resource_type": row[0], "action": row[1], "count": row[2]}
            for row in result
        ]
    except Exception as e:
        logger.warning(f"Error getting audit log stats: {e}")
        return []
