"""
CRUD operations for Document Search.

Provides text search, vector search, and search logging functionality.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlmodel import Session

logger = logging.getLogger(__name__)


# ============================================================================
# Document Chunk Search (Text + Vector)
# ============================================================================


def search_chunks_by_text(
    session: Session,
    query: str,
    tenant_id: str,
    top_k: int = 10,
    document_types: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Search document chunks using full-text search (PostgreSQL tsvector).

    Args:
        session: Database session
        query: Search query string
        tenant_id: Tenant ID for isolation
        top_k: Maximum results to return
        document_types: Optional list of document types to filter
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        List of dicts with chunk data
    """
    # Build base WHERE conditions
    base_where = ["d.tenant_id = :tenant_id", "d.deleted_at IS NULL"]
    params: Dict[str, Any] = {"tenant_id": tenant_id, "query": query, "top_k": top_k}

    if document_types:
        placeholders = ", ".join([f":dt{i}" for i, dt in enumerate(document_types)])
        base_where.append(f"d.format IN ({placeholders})")
        for i, dt in enumerate(document_types):
            params[f"dt{i}"] = dt

    if date_from:
        base_where.append("d.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        base_where.append("d.created_at <= :date_to")
        params["date_to"] = date_to

    where_clause = " AND ".join(base_where)

    # Try tsvector search first
    ts_sql = f"""
    SELECT dc.id, dc.document_id, d.filename, dc.text,
           dc.page_number, dc.chunk_type,
           ts_rank(to_tsvector('simple', dc.text),
                   plainto_tsquery('simple', :query)) as score
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    WHERE {where_clause}
    ORDER BY score DESC
    LIMIT :top_k
    """

    try:
        rows = session.execute(text(ts_sql), params).fetchall()

        # If tsvector returns nothing, fallback to ILIKE
        if not rows:
            keywords = [kw.strip() for kw in query.split() if len(kw.strip()) >= 2]
            if keywords:
                ilike_conditions = " OR ".join(
                    [f"dc.text ILIKE :kw{i}" for i in range(len(keywords))]
                )
                ilike_where = base_where + [f"({ilike_conditions})"]
                ilike_sql = f"""
                SELECT dc.id, dc.document_id, d.filename, dc.text,
                       dc.page_number, dc.chunk_type,
                       0.5 as score
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE {' AND '.join(ilike_where)}
                LIMIT :top_k
                """
                ilike_params = dict(params)
                for i, kw in enumerate(keywords):
                    ilike_params[f"kw{i}"] = f"%{kw}%"
                rows = session.execute(text(ilike_sql), ilike_params).fetchall()

        return [
            {
                "id": str(row[0]),
                "document_id": str(row[1]),
                "filename": row[2],
                "text": row[3],
                "page_number": row[4],
                "chunk_type": row[5],
                "score": float(row[6]) if row[6] else 0.0,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Text search error: {str(e)}")
        return []


def search_chunks_by_vector(
    session: Session,
    query_embedding: List[float],
    tenant_id: str,
    top_k: int = 10,
    document_types: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Search document chunks using vector similarity (pgvector).

    Args:
        session: Database session
        query_embedding: Query embedding vector (1536-dim)
        tenant_id: Tenant ID for isolation
        top_k: Maximum results to return
        document_types: Optional list of document types to filter
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        List of dicts with chunk data and similarity scores
    """
    # Convert embedding to PostgreSQL array format
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    # Build WHERE conditions
    base_where = ["d.tenant_id = :tenant_id", "dc.embedding IS NOT NULL", "d.deleted_at IS NULL"]
    params: Dict[str, Any] = {"tenant_id": tenant_id, "embedding": embedding_str, "top_k": top_k}

    if document_types:
        placeholders = ", ".join([f":dt{i}" for i, dt in enumerate(document_types)])
        base_where.append(f"d.format IN ({placeholders})")
        for i, dt in enumerate(document_types):
            params[f"dt{i}"] = dt

    if date_from:
        base_where.append("d.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        base_where.append("d.created_at <= :date_to")
        params["date_to"] = date_to

    where_clause = " AND ".join(base_where)

    sql = f"""
    SELECT dc.id, dc.document_id, d.filename, dc.text,
           dc.page_number, dc.chunk_type,
           1 - (dc.embedding <=> :embedding::vector) as cosine_similarity
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    WHERE {where_clause}
    ORDER BY cosine_similarity DESC
    LIMIT :top_k
    """

    try:
        rows = session.execute(text(sql), params).fetchall()

        return [
            {
                "id": str(row[0]),
                "document_id": str(row[1]),
                "filename": row[2],
                "text": row[3],
                "page_number": row[4],
                "chunk_type": row[5],
                "score": float(row[6]),
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Vector search error: {str(e)}")
        return []


def log_search(
    session: Session,
    tenant_id: str,
    user_id: str,
    query: str,
    search_type: str,
    result_count: int,
    execution_time_ms: int,
) -> None:
    """
    Log search query for analytics.

    Args:
        session: Database session
        tenant_id: Tenant ID
        user_id: User who performed the search
        query: Search query string
        search_type: Type of search (text, vector, hybrid)
        result_count: Number of results returned
        execution_time_ms: Execution time in milliseconds
    """
    try:
        session.execute(
            text("""
                INSERT INTO document_search_log (tenant_id, user_id, query, search_type, result_count, execution_time_ms, created_at)
                VALUES (:tenant_id, :user_id, :query, :search_type, :result_count, :execution_time_ms, NOW())
            """),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "query": query,
                "search_type": search_type,
                "result_count": result_count,
                "execution_time_ms": execution_time_ms,
            },
        )
        session.commit()
    except Exception as e:
        logger.warning(f"Failed to log search: {str(e)}")


def get_popular_searches(
    session: Session, tenant_id: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get popular search queries from search logs.

    Args:
        session: Database session
        tenant_id: Tenant ID
        limit: Maximum results

    Returns:
        List of {query, count} dicts
    """
    try:
        rows = session.execute(
            text("""
                SELECT query, COUNT(*) as freq
                FROM document_search_log
                WHERE tenant_id = :tenant_id
                  AND created_at >= NOW() - INTERVAL '7 days'
                GROUP BY query
                ORDER BY freq DESC
                LIMIT :limit
            """),
            {"tenant_id": tenant_id, "limit": limit},
        ).fetchall()

        return [
            {"query": row[0], "count": row[1]}
            for row in rows
        ]

    except Exception as e:
        logger.warning(f"Failed to get popular searches: {str(e)}")
        return []


def get_search_suggestions(
    session: Session,
    query_prefix: str,
    limit: int = 5,
    tenant_id: Optional[str] = None,
) -> List[str]:
    """
    Get search suggestions based on previous queries.

    Args:
        session: Database session
        query_prefix: Prefix to match
        limit: Number of suggestions
        tenant_id: Optional tenant ID for filtering

    Returns:
        List of suggested queries
    """
    if not query_prefix.strip():
        return []

    try:
        params = {
            "prefix": f"{query_prefix.strip()}%",
            "limit": max(1, min(limit, 20)),
        }
        where = ["query ILIKE :prefix", "created_at > NOW() - INTERVAL '30 days'"]
        if tenant_id:
            where.append("tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id

        sql = f"""
            SELECT query, COUNT(*) as freq
            FROM document_search_log
            WHERE {' AND '.join(where)}
            GROUP BY query
            ORDER BY freq DESC, MAX(created_at) DESC
            LIMIT :limit
        """
        rows = session.execute(text(sql), params).fetchall()
        return [str(row[0]) for row in rows if row and row[0]]
    except Exception as e:
        logger.warning(f"Failed to get search suggestions: {str(e)}")
        return []
