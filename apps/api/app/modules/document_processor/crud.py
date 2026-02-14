"""
CRUD operations for Document Processor module.

Centralizes all database access for documents and document chunks.
Routers and services should use these functions instead of direct SQL.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from models.document import Document, DocumentChunk
from sqlalchemy import text
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


# ============================================================================
# Document CRUD
# ============================================================================


def get_document(
    session: Session, document_id: str | UUID, tenant_id: str
) -> Optional[Document]:
    """
    Get a document by ID and tenant_id.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID for multi-tenant isolation

    Returns:
        Document if found, None otherwise
    """
    return session.exec(
        select(Document)
        .where(Document.id == str(document_id))
        .where(Document.tenant_id == tenant_id)
        .where(Document.deleted_at.is_(None))
    ).first()


def get_document_with_lock(
    session: Session, document_id: str | UUID, tenant_id: str
) -> Optional[tuple[str, Optional[int]]]:
    """
    Get document version for reindexing (raw SQL for locking).

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID

    Returns:
        Tuple of (document_id, current_version) or None
    """
    result = session.execute(
        text(
            """
            SELECT id, version
            FROM documents
            WHERE id = :document_id AND tenant_id = :tenant_id AND deleted_at IS NULL
            """
        ),
        {"document_id": str(document_id), "tenant_id": tenant_id},
    ).fetchone()
    return result


def list_documents(
    session: Session,
    tenant_id: str,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[Document], int]:
    """
    List documents with filtering.

    Args:
        session: Database session
        tenant_id: Tenant ID
        user_id: Filter by user ID (optional)
        status: Filter by status (optional)
        limit: Maximum results
        offset: Pagination offset

    Returns:
        Tuple of (documents, total_count)
    """
    query = select(Document).where(Document.tenant_id == tenant_id).where(
        Document.deleted_at.is_(None)
    )

    if user_id:
        query = query.where(Document.user_id == user_id)
    if status:
        query = query.where(Document.status == status)

    # Get total count
    count_query = select(text("COUNT(*)")).select_from(
        query.subquery().alias("docs")
    )
    total = session.exec(count_query).one()

    # Get paginated results
    query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    documents = session.exec(query).all()

    return documents, total


def create_document(
    session: Session,
    tenant_id: str,
    user_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    file_format: str,
    metadata: Optional[dict[str, Any]] = None,
) -> Document:
    """
    Create a new document.

    Args:
        session: Database session
        tenant_id: Tenant ID
        user_id: User ID who created the document
        filename: Original filename
        content_type: MIME type
        file_size: File size in bytes
        file_format: File extension
        metadata: Optional metadata dict

    Returns:
        Created Document
    """
    from models.document import DocumentStatus

    document = Document(
        tenant_id=tenant_id,
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        size=file_size,
        status=DocumentStatus.processing,
        format=file_format,
        processing_progress=0,
        total_chunks=0,
        created_by=user_id,
        doc_metadata=metadata or {},
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def update_document_status(
    session: Session,
    document_id: str | UUID,
    status: str,
    error_message: Optional[str] = None,
    processing_progress: Optional[int] = None,
    total_chunks: Optional[int] = None,
) -> Optional[Document]:
    """
    Update document processing status.

    Args:
        session: Database session
        document_id: Document ID
        status: New status
        error_message: Error message if failed
        processing_progress: Processing progress (0-100)
        total_chunks: Total number of chunks

    Returns:
        Updated Document or None
    """
    document = session.get(Document, str(document_id))
    if not document:
        return None

    document.status = status
    if error_message:
        document.error_message = error_message
    if processing_progress is not None:
        document.processing_progress = processing_progress
    if total_chunks is not None:
        document.total_chunks = total_chunks
    document.updated_at = datetime.now(timezone.utc)

    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def soft_delete_document(session: Session, document_id: str | UUID) -> bool:
    """
    Soft delete a document.

    Args:
        session: Database session
        document_id: Document ID

    Returns:
        True if deleted, False if not found
    """
    document = session.get(Document, str(document_id))
    if not document:
        return False

    document.deleted_at = datetime.now(timezone.utc)
    document.updated_at = datetime.now(timezone.utc)

    session.add(document)
    session.commit()
    return True


def increment_document_version(
    session: Session, document_id: str | UUID, tenant_id: str
) -> Optional[int]:
    """
    Increment document and chunk versions for reindexing.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID

    Returns:
        New version number or None if document not found
    """
    # Get current version
    doc_row = get_document_with_lock(session, document_id, tenant_id)
    if not doc_row:
        return None

    old_version = doc_row[1] or 1

    # Update chunk versions
    session.execute(
        text(
            """
            UPDATE document_chunks
            SET chunk_version = COALESCE(chunk_version, 1) + 1
            WHERE document_id = :document_id
            """
        ),
        {"document_id": str(document_id)},
    )

    # Update document version
    session.execute(
        text(
            """
            UPDATE documents
            SET version = COALESCE(version, 1) + 1,
                updated_at = NOW()
            WHERE id = :document_id
            """
        ),
        {"document_id": str(document_id)},
    )

    session.commit()
    return old_version + 1


def get_document_version_chain(
    session: Session, document_id: str | UUID, tenant_id: str
) -> List[dict[str, Any]]:
    """
    Get document version chain using recursive CTE.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID

    Returns:
        List of version history dicts
    """
    rows = session.execute(
        text(
            """
            WITH RECURSIVE chain AS (
                SELECT id, parent_id, version, version_comment, created_at, updated_at
                FROM documents
                WHERE id = :document_id AND tenant_id = :tenant_id
                UNION ALL
                SELECT d.id, d.parent_id, d.version, d.version_comment, d.created_at, d.updated_at
                FROM documents d
                JOIN chain c ON c.parent_id = d.id
            )
            SELECT id, parent_id, version, version_comment, created_at, updated_at
            FROM chain
            ORDER BY version DESC
            """
        ),
        {"document_id": str(document_id), "tenant_id": tenant_id},
    ).fetchall()

    return [
        {
            "id": str(row[0]),
            "parent_id": str(row[1]) if row[1] else None,
            "version": row[2],
            "version_comment": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
        }
        for row in rows
    ]


# ============================================================================
# Document Chunk CRUD
# ============================================================================


def get_chunk(session: Session, chunk_id: str | UUID) -> Optional[DocumentChunk]:
    """Get a chunk by ID."""
    return session.get(DocumentChunk, str(chunk_id))


def list_chunks_by_document(
    session: Session,
    document_id: str | UUID,
    tenant_id: str,
    limit: int = 1000,
    offset: int = 0,
) -> List[DocumentChunk]:
    """
    List all chunks for a document.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID
        limit: Maximum results
        offset: Pagination offset

    Returns:
        List of DocumentChunk
    """
    chunks = session.exec(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == str(document_id))
        .where(DocumentChunk.tenant_id == tenant_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
    ).all()
    return chunks


def create_chunk(
    session: Session,
    document_id: str | UUID,
    tenant_id: str,
    chunk_index: int,
    text: str,
    chunk_type: str = "text",
    page_number: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> DocumentChunk:
    """
    Create a document chunk.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID
        chunk_index: Chunk sequence number
        text: Chunk text content
        chunk_type: Type of chunk (text, table, image, etc.)
        page_number: Page number (optional)
        metadata: Optional metadata

    Returns:
        Created DocumentChunk
    """
    chunk = DocumentChunk(
        document_id=str(document_id),
        tenant_id=tenant_id,
        chunk_index=chunk_index,
        text=text,
        chunk_type=chunk_type,
        page_number=page_number,
        metadata=metadata or {},
    )
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    return chunk


def create_chunks(
    session: Session,
    chunks: List[dict[str, Any]],
) -> int:
    """
    Bulk create chunks for efficiency.

    Args:
        session: Database session
        chunks: List of chunk dicts with keys: document_id, tenant_id,
                chunk_index, text, chunk_type, page_number, metadata

    Returns:
        Number of chunks created
    """
    for chunk_data in chunks:
        chunk = DocumentChunk(**chunk_data)
        session.add(chunk)
    session.commit()
    return len(chunks)


def delete_chunks_by_document(
    session: Session, document_id: str | UUID, tenant_id: str
) -> int:
    """
    Delete all chunks for a document.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID

    Returns:
        Number of chunks deleted
    """
    chunks = list_chunks_by_document(session, document_id, tenant_id, limit=100000)
    for chunk in chunks:
        session.delete(chunk)
    session.commit()
    return len(chunks)


def count_chunks_by_document(
    session: Session, document_id: str | UUID, tenant_id: str
) -> int:
    """
    Count chunks for a document.

    Args:
        session: Database session
        document_id: Document ID
        tenant_id: Tenant ID

    Returns:
        Number of chunks
    """
    from sqlalchemy import func

    count = session.exec(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == str(document_id))
        .where(DocumentChunk.tenant_id == tenant_id)
    ).one()
    return count
