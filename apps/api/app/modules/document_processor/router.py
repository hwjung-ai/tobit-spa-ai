from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from core.auth import get_current_user
from core.config import get_settings
from core.db import get_session
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from models.document import Document, DocumentChunk, DocumentStatus
from pydantic import BaseModel
from schemas.common import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.auth.models import TbUser

from .services import (
    ChunkingStrategy,
    DocumentExportService,
    DocumentProcessingError,
    DocumentProcessor,
    DocumentSearchService,
    SearchFilters,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentUploadRequest(BaseModel):
    """Request for document upload"""

    pass


class DocumentResponse(BaseModel):
    """Response for document"""

    id: str
    filename: str
    format: Optional[str]
    processing_status: Optional[str]
    processing_progress: int
    total_chunks: int
    created_at: str

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Request for document search"""

    query: str
    search_type: str = "hybrid"  # text, vector, hybrid
    top_k: int = 10
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    document_types: Optional[List[str]] = None
    min_relevance: float = 0.5


class SearchResultResponse(BaseModel):
    """Response for search result"""

    chunk_id: str
    document_id: str
    document_name: str
    chunk_text: str
    page_number: Optional[int]
    relevance_score: float
    chunk_type: str


class ChunkResponse(BaseModel):
    """Response for document chunk"""

    id: str
    document_id: str
    chunk_index: int
    page_number: Optional[int]
    text: str
    chunk_type: str
    relevance_score: Optional[float]

    class Config:
        from_attributes = True


# Initialize services
processor = DocumentProcessor()
search_service = DocumentSearchService()
chunking = ChunkingStrategy()
export_service = DocumentExportService()


def _tenant_id_from_user(current_user: TbUser) -> str:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context is missing")
    return tenant_id


def _user_id_from_user(current_user: TbUser) -> str:
    user_id = getattr(current_user, "id", None)
    if not user_id:
        raise HTTPException(status_code=400, detail="User context is missing")
    return str(user_id)


def _storage_path_for(document_id: str, tenant_id: str, filename: str) -> Path:
    settings = get_settings()
    return settings.document_storage_path / tenant_id / document_id / filename


def _build_document_payload(document: Document, chunk_count: int = 0) -> dict:
    return {
        "id": document.id,
        "tenant_id": document.tenant_id,
        "user_id": document.user_id,
        "filename": document.filename,
        "content_type": document.content_type,
        "size": document.size,
        "status": document.status.value if hasattr(document.status, "value") else str(document.status),
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "deleted_at": document.deleted_at.isoformat() if document.deleted_at else None,
        "chunk_count": chunk_count,
        "format": document.format,
        "processing_progress": document.processing_progress or 0,
        "total_chunks": document.total_chunks or 0,
    }


@router.post("/upload", response_model=ResponseEnvelope)
async def upload_document(
    file: UploadFile = File(...),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload document for processing

    Supported formats:
    - PDF (.pdf)
    - Word (.docx)
    - Excel (.xlsx)
    - PowerPoint (.pptx)
    - Images (.jpg, .jpeg, .png)

    The document will be processed asynchronously in the background.
    """

    if not file.filename:
        raise HTTPException(400, "No filename provided")

    # Get file extension
    file_ext = file.filename.split(".")[-1].lower()

    supported_formats = set(processor.SUPPORTED_FORMATS.keys()) | {"txt"}
    if file_ext not in supported_formats:
        raise HTTPException(
            400,
            f"Unsupported format: {file_ext}. "
            f"Supported: {', '.join(sorted(supported_formats))}",
        )

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        tenant_id = _tenant_id_from_user(current_user)
        user_id = _user_id_from_user(current_user)
        logger.info(
            f"Uploading document: {file.filename} ({file_size} bytes, user: {user_id}, tenant: {tenant_id})"
        )

        document = Document(
            tenant_id=tenant_id,
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size=file_size,
            status=DocumentStatus.processing,
            format=file_ext,
            processing_progress=0,
            total_chunks=0,
            created_by=user_id,
            doc_metadata={},
        )
        session.add(document)
        session.commit()
        session.refresh(document)

        storage_path = _storage_path_for(document.id, tenant_id, file.filename)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(file_content)

        page_chunks: list[tuple[int | None, str]] = []
        if file_ext == "txt":
            extracted = file_content.decode("utf-8", errors="ignore")
            if extracted.strip():
                page_chunks.append((1, extracted))
            processing_meta = {"format": "txt", "extraction_method": "plain_text"}
        else:
            processed = processor.process(str(storage_path), file_ext)
            pages = processed.get("pages", [])
            for page in pages:
                if not isinstance(page, dict):
                    continue
                text = page.get("text", "")
                page_num = page.get("page_num")
                if text and text.strip():
                    page_chunks.append(
                        ((page_num + 1) if isinstance(page_num, int) else None, text)
                    )
            processing_meta = processed.get("metadata", {})

        created_chunks = 0
        for page_number, page_text in page_chunks:
            text_chunks = chunking.chunk_text(page_text, chunk_size=300, overlap=50)
            for chunk_text in text_chunks:
                if not chunk_text.strip():
                    continue
                chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=created_chunks,
                    page=page_number,
                    text=chunk_text,
                    embedding=[0.0] * 1536,
                    chunk_type="text",
                    position_in_doc=created_chunks,
                    page_number=page_number,
                    source_hash=chunking.compute_source_hash(chunk_text),
                    chunk_version=1,
                )
                session.add(chunk)
                created_chunks += 1

        document.status = DocumentStatus.done
        document.processing_progress = 100
        document.total_chunks = created_chunks
        document.doc_metadata = {
            "storage_path": str(storage_path),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            **(processing_meta or {}),
        }
        document.updated_at = datetime.now(timezone.utc)
        session.add(document)
        session.commit()
        session.refresh(document)

        return ResponseEnvelope.success(
            data={
                "document": _build_document_payload(document, chunk_count=created_chunks),
                "status": "done",
            }
        )

    except DocumentProcessingError as e:
        logger.error(f"Document processing error: {str(e)}")
        raise HTTPException(400, f"Processing failed: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/", response_model=ResponseEnvelope)
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    List all documents for current user

    Returns:
    - Document metadata
    - Processing status
    - Number of chunks
    - Created date
    """

    try:
        tenant_id = _tenant_id_from_user(current_user)
        offset = (page - 1) * per_page
        sort_column = {
            "created_at": Document.created_at,
            "updated_at": Document.updated_at,
            "filename": Document.filename,
            "status": Document.status,
        }.get(sort_by, Document.created_at)

        statement = (
            select(Document)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
            .order_by(sort_column.desc())
            .offset(offset)
            .limit(per_page)
        )
        documents = session.exec(statement).all()
        total = len(
            session.exec(
                select(Document)
                .where(Document.tenant_id == tenant_id)
                .where(Document.deleted_at.is_(None))
            ).all()
        )

        return ResponseEnvelope.success(
            data={
                "page": page,
                "per_page": per_page,
                "total": total,
                "documents": [_build_document_payload(doc) for doc in documents],
            }
        )

    except Exception as e:
        logger.error(f"List failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/list", response_model=ResponseEnvelope)
async def list_documents_legacy(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Legacy list endpoint. Prefer GET /api/documents/."""
    return await list_documents(page, per_page, sort_by, current_user, session)


@router.get("/{document_id}", response_model=ResponseEnvelope)
async def get_document(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get document details and processing status

    Shows:
    - File format and size
    - Processing progress (0-100%)
    - Number of chunks created
    - Error messages if processing failed
    """

    try:
        tenant_id = _tenant_id_from_user(current_user)
        statement = (
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        )
        document = session.exec(statement).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        chunk_count = len(
            session.exec(
                select(DocumentChunk).where(DocumentChunk.document_id == document.id)
            ).all()
        )
        return ResponseEnvelope.success(
            data={"document": _build_document_payload(document, chunk_count=chunk_count)}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/search", response_model=ResponseEnvelope)
async def search_documents(
    request: SearchRequest,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Advanced document search with multiple strategies

    Search Types:
    - text: Full-text search (BM25)
    - vector: Semantic search (vector similarity)
    - hybrid: Combine both (RRF ranking)

    Returns top matching chunks with relevance scores
    """

    try:
        # Validate query length
        if not request.query or len(request.query.strip()) < 2:
            raise HTTPException(400, "Query must be at least 2 characters")

        logger.info(
            f"Search: query='{request.query[:50]}', "
            f"type={request.search_type}, top_k={request.top_k}"
        )

        tenant_id = _tenant_id_from_user(current_user)

        # Parse dates if provided
        date_from = None
        date_to = None
        try:
            if request.date_from:
                date_from = datetime.fromisoformat(request.date_from)
            if request.date_to:
                date_to = datetime.fromisoformat(request.date_to)
        except ValueError as e:
            raise HTTPException(400, f"Invalid date format: {str(e)}")

        # Create filters
        filters = SearchFilters(
            tenant_id=tenant_id,
            date_from=date_from,
            date_to=date_to,
            document_types=request.document_types or [],
            min_relevance=request.min_relevance,
        )

        # Initialize search service with session
        search_svc = DocumentSearchService(db_session=session, embedding_service=None)

        # Perform search
        start_time = time.time()
        results = await search_svc.search(
            query=request.query,
            filters=filters,
            top_k=min(request.top_k, 100),  # Cap at 100
            search_type=request.search_type,
        )
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Convert results to response format
        result_list = [
            SearchResultResponse(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_name=r.document_name,
                chunk_text=r.chunk_text,
                page_number=r.page_number,
                relevance_score=r.relevance_score,
                chunk_type=r.chunk_type,
            )
            for r in results
        ]

        return ResponseEnvelope.success(
            data={
                "query": request.query,
                "search_type": request.search_type,
                "total_count": len(result_list),
                "execution_time_ms": execution_time_ms,
                "results": [r.model_dump() for r in result_list],
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Search failed: {str(e)}")


@router.get("/search/suggestions", response_model=ResponseEnvelope)
async def search_suggestions(
    prefix: str = Query("", min_length=1),
    limit: int = Query(5, ge=1, le=20),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get search suggestions based on previous queries

    Returns a list of suggested search terms matching the prefix
    """

    try:
        if not prefix or len(prefix.strip()) < 1:
            return ResponseEnvelope.success(data={"suggestions": []})

        tenant_id = _tenant_id_from_user(current_user)

        # Get search service
        search_svc = DocumentSearchService(db_session=session)

        suggestions = search_svc.get_search_suggestions(prefix, limit, tenant_id=tenant_id)

        return ResponseEnvelope.success(
            data={
                "prefix": prefix,
                "suggestions": suggestions,
            }
        )

    except Exception as e:
        logger.error(f"Suggestions failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{document_id}/reindex", response_model=ResponseEnvelope)
async def reindex_document(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Reindex document chunks.
    Current implementation increments chunk_version and updates document timestamp.
    """
    try:
        from sqlalchemy import text

        tenant_id = _tenant_id_from_user(current_user)

        doc_row = session.execute(
            text(
                """
                SELECT id, version
                FROM documents
                WHERE id = :document_id AND tenant_id = :tenant_id AND deleted_at IS NULL
                """
            ),
            {"document_id": document_id, "tenant_id": tenant_id},
        ).fetchone()
        if not doc_row:
            raise HTTPException(status_code=404, detail="Document not found")

        session.execute(
            text(
                """
                UPDATE document_chunks
                SET chunk_version = COALESCE(chunk_version, 1) + 1
                WHERE document_id = :document_id
                """
            ),
            {"document_id": document_id},
        )
        session.execute(
            text(
                """
                UPDATE documents
                SET version = COALESCE(version, 1) + 1,
                    updated_at = NOW()
                WHERE id = :document_id
                """
            ),
            {"document_id": document_id},
        )
        session.commit()

        new_version = int(doc_row[1] or 1) + 1
        return ResponseEnvelope.success(
            data={
                "document_id": document_id,
                "version": new_version,
                "status": "reindexed",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/versions", response_model=ResponseEnvelope)
async def get_document_versions(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return document version chain (parent + current)."""
    try:
        from sqlalchemy import text

        tenant_id = _tenant_id_from_user(current_user)

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
            {"document_id": document_id, "tenant_id": tenant_id},
        ).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="Document not found")

        return ResponseEnvelope.success(
            data={
                "document_id": document_id,
                "versions": [
                    {
                        "id": str(row[0]),
                        "parent_id": str(row[1]) if row[1] else None,
                        "version": int(row[2] or 1),
                        "version_comment": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "updated_at": row[5].isoformat() if row[5] else None,
                    }
                    for row in rows
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document versions failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks", response_model=ResponseEnvelope)
async def get_document_chunks(
    document_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get all chunks for a document with pagination

    Returns chunks in order with metadata:
    - Chunk index and position
    - Page number (for PDFs)
    - Chunk type (text, table, image)
    - Relevance scores for search results
    """

    try:
        tenant_id = _tenant_id_from_user(current_user)
        offset = (page - 1) * per_page

        document = session.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        chunks = session.exec(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .offset(offset)
            .limit(per_page)
        ).all()
        total_chunks = len(
            session.exec(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            ).all()
        )

        return ResponseEnvelope.success(
            data={
                "document_id": document_id,
                "page": page,
                "per_page": per_page,
                "total_chunks": total_chunks,
                "chunks": [
                    {
                        "id": chunk.id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "page": chunk.page,
                        "page_number": chunk.page_number,
                        "text": chunk.text,
                        "chunk_type": chunk.chunk_type,
                        "chunk_version": chunk.chunk_version,
                        "position_in_doc": chunk.position_in_doc,
                        "created_at": chunk.created_at.isoformat()
                        if chunk.created_at
                        else None,
                    }
                    for chunk in chunks
                ],
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunks: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{document_id}/share", response_model=ResponseEnvelope)
async def share_document(
    document_id: str,
    user_id: str = Query(..., description="Target user ID to share with"),
    access_type: str = Query("read", description="Access level: read, download, share"),
    expires_in_days: Optional[int] = Query(None, description="Expiration in days (optional)"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Share document with another user

    Access types:
    - read: View only
    - download: Read + download
    - share: Read + download + share

    Optionally set expiration time
    """

    try:
        # Validate inputs
        if not user_id:
            raise HTTPException(400, detail="user_id required")
        
        if access_type not in ["read", "download", "share"]:
            raise HTTPException(400, detail=f"Invalid access_type: {access_type}")

        tenant_id = _tenant_id_from_user(current_user)
        current_user_id = _user_id_from_user(current_user)
        
        logger.info(
            f"Sharing document {document_id} with user {user_id}, "
            f"access={access_type}, expires_in={expires_in_days} days"
        )

        # Check document ownership
        document = session.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to share this document")

        # Check if target user exists and is in same tenant
        from app.modules.auth.models import TbUser
        target_user = session.get(TbUser, user_id)
        
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")
        
        if target_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Cannot share across tenants")

        # Calculate expiration date
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timezone.timedelta(days=expires_in_days)

        # Store share metadata in document.doc_metadata
        share_metadata = document.doc_metadata or {}
        shares = share_metadata.get("shares", [])
        
        # Check if already shared
        existing_share = next((s for s in shares if s.get("user_id") == user_id), None)
        if existing_share:
            # Update existing share
            existing_share["access_type"] = access_type
            existing_share["expires_at"] = expires_at.isoformat() if expires_at else None
            existing_share["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            # Add new share
            shares.append({
                "user_id": user_id,
                "user_email": getattr(target_user, "email", ""),
                "access_type": access_type,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "shared_by": current_user_id,
                "shared_at": datetime.now(timezone.utc).isoformat(),
            })
        
        document.doc_metadata = {
            **share_metadata,
            "shares": shares,
        }
        document.updated_at = datetime.now(timezone.utc)
        session.add(document)
        session.commit()

        return ResponseEnvelope.success(
            data={
                "document_id": document_id,
                "shared_with_user_id": user_id,
                "shared_with_email": getattr(target_user, "email", ""),
                "access_type": access_type,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
            message=f"Document shared successfully with user {user_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Share failed: {str(e)}")
        raise HTTPException(500, detail=str(e))


@router.get("/{document_id}/export")
async def export_document(
    document_id: str,
    format: str = Query("json", description="Export format: json, csv, markdown, text"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Export document chunks in specified format

    Supported formats:
    - json: Structured JSON with metadata
    - csv: Spreadsheet format
    - markdown: Markdown text with headers
    - text: Plain text
    """

    try:
        if format not in ["json", "csv", "markdown", "text"]:
            raise HTTPException(400, f"Unsupported format: {format}")

        tenant_id = _tenant_id_from_user(current_user)
        logger.info(f"Exporting document {document_id} as {format} (tenant={tenant_id})")

        # Get document
        document = session.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get all chunks
        chunks = session.exec(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
        
        if not chunks:
            raise HTTPException(404, detail="No chunks found for this document")

        # Export based on format
        from fastapi.responses import StreamingResponse
        import io
        
        if format == "json":
            # JSON format: structured export with metadata
            export_data = {
                "document": {
                    "id": document.id,
                    "filename": document.filename,
                    "format": document.format,
                    "size": document.size,
                    "created_at": document.created_at.isoformat() if document.created_at else None,
                    "total_chunks": len(chunks),
                },
                "chunks": [
                    {
                        "id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "page": chunk.page,
                        "text": chunk.text,
                        "chunk_type": chunk.chunk_type,
                        "position_in_doc": chunk.position_in_doc,
                        "chunk_version": chunk.chunk_version,
                    }
                    for chunk in chunks
                ]
            }
            
            import json
            output = io.StringIO()
            json.dump(export_data, output, ensure_ascii=False, indent=2)
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.json"'
                }
            )
        
        elif format == "csv":
            # CSV format: spreadsheet-friendly
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "chunk_index", "page_number", "page", 
                "chunk_type", "text", "position_in_doc", "chunk_version"
            ])
            
            # Rows
            for chunk in chunks:
                writer.writerow([
                    chunk.chunk_index,
                    chunk.page_number or "",
                    chunk.page or "",
                    chunk.chunk_type,
                    chunk.text.replace("\n", " ").replace("\r", ""),  # Escape newlines
                    chunk.position_in_doc,
                    chunk.chunk_version,
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.csv"'
                }
            )
        
        elif format == "markdown":
            # Markdown format: readable with headers
            output = io.StringIO()
            
            output.write(f"# {document.filename}\n\n")
            output.write(f"**Format:** {document.format}\n")
            output.write(f"**Size:** {document.size} bytes\n")
            output.write(f"**Total Chunks:** {len(chunks)}\n")
            output.write(f"**Created:** {document.created_at.isoformat() if document.created_at else 'N/A'}\n\n")
            output.write("---\n\n")
            
            for chunk in chunks:
                header = f"## Chunk {chunk.chunk_index}"
                if chunk.page_number:
                    header += f" (Page {chunk.page_number})"
                output.write(f"{header}\n\n")
                output.write(f"{chunk.text}\n\n")
                output.write("---\n\n")
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.md"'
                }
            )
        
        elif format == "text":
            # Plain text format: simple concatenation
            output = io.StringIO()
            
            for chunk in chunks:
                output.write(chunk.text)
                output.write("\n\n")
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.txt"'
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(500, detail=f"Export failed: {str(e)}")


@router.delete("/{document_id}", response_model=ResponseEnvelope)
async def delete_document(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Delete (soft delete) a document

    The document and its chunks are marked as deleted
    but remain in the database for audit trail purposes
    """

    try:
        tenant_id = _tenant_id_from_user(current_user)
        document = session.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        logger.info(f"Deleting document {document_id} (tenant={tenant_id})")
        document.deleted_at = datetime.now(timezone.utc)
        document.updated_at = datetime.now(timezone.utc)
        session.add(document)
        session.commit()

        return ResponseEnvelope.success(
            data={"document_id": document_id},
            message=f"Document {document_id} deleted",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))
