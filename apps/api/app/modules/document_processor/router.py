from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from schemas.common import ResponseEnvelope
from sqlmodel import Session

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


@router.post("/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...), current_user: dict = Depends(get_current_user)
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

    if file_ext not in processor.SUPPORTED_FORMATS:
        raise HTTPException(
            400,
            f"Unsupported format: {file_ext}. "
            f"Supported: {', '.join(processor.SUPPORTED_FORMATS.keys())}",
        )

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        logger.info(
            f"Uploading document: {file.filename} "
            f"({file_size} bytes, user: {current_user.get('id')})"
        )

        # In a real implementation, this would:
        # 1. Save file to storage
        # 2. Create Document record in DB
        # 3. Queue background processing job
        # 4. Return job ID for status tracking

        # For now, return placeholder response
        return {
            "status": "queued",
            "message": "Document queued for processing",
            "filename": file.filename,
            "size": file_size,
            "format": file_ext,
        }

    except DocumentProcessingError as e:
        logger.error(f"Document processing error: {str(e)}")
        raise HTTPException(400, f"Processing failed: {str(e)}")
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/list")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    current_user: dict = Depends(get_current_user),
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
        (page - 1) * per_page

        # In real implementation: db.query(Document).filter(...)
        # For now, return placeholder

        return ResponseEnvelope.success(data={
            "page": page,
            "per_page": per_page,
            "total": 0,
            "documents": [],
        })

    except Exception as e:
        logger.error(f"List failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, current_user: dict = Depends(get_current_user)
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
        # In real implementation: db.get(Document, document_id)
        # For now, return placeholder

        return {
            "id": document_id,
            "filename": f"document_{document_id}.pdf",
            "format": "pdf",
            "processing_status": "done",
            "processing_progress": 100,
            "total_chunks": 42,
            "created_at": "2026-01-18T12:00:00Z",
        }

    except Exception as e:
        logger.error(f"Failed to get document: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/search", response_model=ResponseEnvelope)
async def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
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

        # Get tenant_id from current_user
        tenant_id = getattr(current_user, 'tenant_id', None)
        if not tenant_id:
            tenant_id = current_user.get("tenant_id", "t1") if isinstance(current_user, dict) else "t1"

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
    current_user: dict = Depends(get_current_user),
):
    """
    Get search suggestions based on previous queries

    Returns a list of suggested search terms matching the prefix
    """

    try:
        if not prefix or len(prefix.strip()) < 1:
            return ResponseEnvelope.success(data={"suggestions": []})

        # Get tenant_id
        tenant_id = getattr(current_user, 'tenant_id', None)
        if not tenant_id:
            tenant_id = current_user.get("tenant_id", "t1") if isinstance(current_user, dict) else "t1"

        # Get search service
        search_svc = DocumentSearchService()

        # Get suggestions (currently uses placeholder implementation)
        suggestions = search_svc.get_search_suggestions(prefix, limit)

        return ResponseEnvelope.success(
            data={
                "prefix": prefix,
                "suggestions": suggestions,
            }
        )

    except Exception as e:
        logger.error(f"Suggestions failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{document_id}/chunks", response_model=dict)
async def get_document_chunks(
    document_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
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
        (page - 1) * per_page

        # In real implementation: db.query(DocumentChunk).filter(...)
        # For now, return placeholder

        return {
            "status": "ok",
            "document_id": document_id,
            "page": page,
            "per_page": per_page,
            "total_chunks": 42,
            "chunks": [],
        }

    except Exception as e:
        logger.error(f"Failed to get chunks: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{document_id}/share", response_model=dict)
async def share_document(
    document_id: str,
    user_id: Optional[str] = Query(None),
    access_type: str = Query("read"),
    expires_in_days: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
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
        if not user_id:
            raise HTTPException(400, "user_id required")

        logger.info(
            f"Sharing document {document_id} with user {user_id}, "
            f"access={access_type}, expires_in={expires_in_days} days"
        )

        # In real implementation:
        # - Check permission
        # - Create document_access record
        # - Log audit entry

        return {"status": "ok", "message": f"Document shared with user {user_id}"}

    except Exception as e:
        logger.error(f"Share failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/{document_id}/export")
async def export_document(
    document_id: str,
    format: str = Query("json"),
    current_user: dict = Depends(get_current_user),
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

        logger.info(f"Exporting document {document_id} as {format}")

        # In real implementation:
        # - Get all chunks from DB
        # - Format using export_service
        # - Return as file download

        return {"status": "ok", "format": format, "message": "Export in progress"}

    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Delete (soft delete) a document

    The document and its chunks are marked as deleted
    but remain in the database for audit trail purposes
    """

    try:
        logger.info(f"Deleting document {document_id}")

        # In real implementation:
        # - Update document.deleted_at
        # - Log audit entry
        # - Don't actually delete from DB (soft delete)

        return {"status": "ok", "message": f"Document {document_id} deleted"}

    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))
