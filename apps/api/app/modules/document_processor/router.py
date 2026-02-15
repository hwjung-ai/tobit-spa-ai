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
from fastapi.responses import FileResponse
from models.document import Document, DocumentChunk, DocumentStatus
from models.history import QueryHistory
from pydantic import BaseModel
from schemas.common import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.auth.models import TbUser

from .crud import (
    count_chunks_by_document,
    create_document,
    get_document,
    get_document_version_chain,
    get_document_with_lock,
    increment_document_version,
    list_chunks_by_document,
)
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


class MultiDocumentQueryRequest(BaseModel):
    """Request for querying multiple documents"""

    query: str
    document_ids: Optional[List[str]] = None  # Specific documents to search (None = all)
    categories: Optional[List[str]] = None    # Filter by category (manual, policy, technical, etc.)
    exclude_document_ids: Optional[List[str]] = None  # Documents to exclude
    tags: Optional[List[str]] = None          # Filter by tags
    top_k: int = 10
    min_relevance: float = 0.3


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
        "status": document.status.value
        if hasattr(document.status, "value")
        else str(document.status),
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

        # Use CRUD to create document
        document = create_document(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            file_format=file_ext,
            metadata={},
        )

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
                "document": _build_document_payload(
                    document, chunk_count=created_chunks
                ),
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


# ==================== Query History APIs (specific routes before generic /{document_id}) ====================


class SaveDocQueryHistoryRequest(BaseModel):
    """Request for saving document query history"""
    query: str
    answer: str
    references: Optional[List[dict]] = None
    document_count: int = 0
    elapsed_ms: int = 0


@router.post("/query-history", response_model=ResponseEnvelope)
async def save_doc_query_history(
    request: SaveDocQueryHistoryRequest,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Save document query history entry

    Uses the existing QueryHistory model with feature='docs'
    """
    try:
        tenant_id = _tenant_id_from_user(current_user)
        user_id = _user_id_from_user(current_user)

        history = QueryHistory(
            tenant_id=tenant_id,
            user_id=user_id,
            feature="docs",  # Document query feature
            question=request.query,
            summary=request.answer[:200] + "..." if len(request.answer) > 200 else request.answer,
            status="ok",
            response={
                "answer": request.answer,
                "references": request.references or [],
            },
            metadata_info={
                "document_count": request.document_count,
                "reference_count": len(request.references) if request.references else 0,
                "elapsed_ms": request.elapsed_ms,
            },
        )
        session.add(history)
        session.commit()
        session.refresh(history)

        return ResponseEnvelope.success(
            data={
                "id": str(history.id),
                "query": history.question,
                "created_at": history.created_at.isoformat(),
            },
            message="Query history saved",
        )

    except Exception as e:
        logger.error(f"Failed to save query history: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/query-history", response_model=ResponseEnvelope)
async def list_doc_query_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    List document query history for current user

    Returns paginated list of past document queries
    """
    try:
        tenant_id = _tenant_id_from_user(current_user)
        user_id = _user_id_from_user(current_user)
        offset = (page - 1) * per_page

        # Get total count
        total_statement = (
            select(QueryHistory)
            .where(QueryHistory.tenant_id == tenant_id)
            .where(QueryHistory.user_id == user_id)
            .where(QueryHistory.feature == "docs")
        )
        total = len(session.exec(total_statement).all())

        # Get paginated results
        statement = (
            select(QueryHistory)
            .where(QueryHistory.tenant_id == tenant_id)
            .where(QueryHistory.user_id == user_id)
            .where(QueryHistory.feature == "docs")
            .order_by(QueryHistory.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        histories = session.exec(statement).all()

        return ResponseEnvelope.success(
            data={
                "page": page,
                "per_page": per_page,
                "total": total,
                "history": [
                    {
                        "id": str(h.id),
                        "query": h.question,
                        "answer": h.response.get("answer", "") if h.response else "",
                        "references": h.response.get("references", []) if h.response else [],
                        "document_count": h.metadata_info.get("document_count", 0) if h.metadata_info else 0,
                        "reference_count": h.metadata_info.get("reference_count", 0) if h.metadata_info else 0,
                        "elapsed_ms": h.metadata_info.get("elapsed_ms", 0) if h.metadata_info else 0,
                        "created_at": h.created_at.isoformat(),
                    }
                    for h in histories
                ],
            }
        )

    except Exception as e:
        logger.error(f"Failed to list query history: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/query-history/{history_id}", response_model=ResponseEnvelope)
async def get_doc_query_history(
    history_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get a specific document query history entry
    """
    import uuid

    try:
        tenant_id = _tenant_id_from_user(current_user)
        user_id = _user_id_from_user(current_user)

        history = session.exec(
            select(QueryHistory)
            .where(QueryHistory.id == uuid.UUID(history_id))
            .where(QueryHistory.tenant_id == tenant_id)
            .where(QueryHistory.user_id == user_id)
            .where(QueryHistory.feature == "docs")
        ).first()

        if not history:
            raise HTTPException(status_code=404, detail="Query history not found")

        return ResponseEnvelope.success(
            data={
                "id": str(history.id),
                "query": history.question,
                "answer": history.response.get("answer", "") if history.response else "",
                "references": history.response.get("references", []) if history.response else [],
                "document_count": history.metadata_info.get("document_count", 0) if history.metadata_info else 0,
                "reference_count": history.metadata_info.get("reference_count", 0) if history.metadata_info else 0,
                "elapsed_ms": history.metadata_info.get("elapsed_ms", 0) if history.metadata_info else 0,
                "created_at": history.created_at.isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query history: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/query-history/{history_id}", response_model=ResponseEnvelope)
async def delete_doc_query_history(
    history_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Delete a document query history entry
    """
    import uuid

    try:
        tenant_id = _tenant_id_from_user(current_user)
        user_id = _user_id_from_user(current_user)

        history = session.exec(
            select(QueryHistory)
            .where(QueryHistory.id == uuid.UUID(history_id))
            .where(QueryHistory.tenant_id == tenant_id)
            .where(QueryHistory.user_id == user_id)
            .where(QueryHistory.feature == "docs")
        ).first()

        if not history:
            raise HTTPException(status_code=404, detail="Query history not found")

        session.delete(history)
        session.commit()

        return ResponseEnvelope.success(
            data={"id": history_id},
            message="Query history deleted",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete query history: {str(e)}")
        raise HTTPException(500, str(e))


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
            data={
                "document": _build_document_payload(document, chunk_count=chunk_count)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/documents/{document_id}/view")
async def get_document_view(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Serve document view page
    """
    try:
        # Get document from database
        document = session.exec(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == _tenant_id_from_user(current_user),
                Document.deleted_at.is_(None),
            )
        ).first()

        if not document:
            raise HTTPException(404, "Document not found")

        # Check if file exists
        file_path = Path(document.file_path)
        if not file_path.exists():
            logger.error(f"Document file not found: {file_path}")
            raise HTTPException(404, "Document file not found")

        # Determine content type and appropriate viewer
        if document.filename.lower().endswith(".pdf"):
            # For PDF, return PDF viewer page
            return {
                "document_id": document_id,
                "filename": document.filename,
                "type": "pdf",
                "url": f"/api/documents/{document_id}/pdf",
            }
        else:
            # For other documents, return text content
            return {
                "document_id": document_id,
                "filename": document.filename,
                "type": "text",
                "url": f"/api/documents/{document_id}/content",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document view: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/documents/{document_id}/pdf")
async def get_pdf_document(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Serve PDF documents for inline viewing
    """
    try:
        # Get document from database
        document = session.exec(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == _tenant_id_from_user(current_user),
                Document.deleted_at.is_(None),
            )
        ).first()

        if not document:
            raise HTTPException(404, "Document not found")

        # Return the PDF file
        file_path = Path(document.file_path)
        if not file_path.exists():
            logger.error(f"PDF file not found: {file_path}")
            raise HTTPException(404, "PDF file not found")

        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=document.filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF document: {str(e)}")
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

        # Convert results to response format with URLs
        result_list = []
        for r in results:
            # Create document URL for the viewer (Next.js frontend route)
            # Format: /documents/{document_id}/viewer?chunkId={chunk_id}&page={page_number}
            document_url = f"/documents/{r.document_id}/viewer"
            params = []
            if r.chunk_id:
                params.append(f"chunkId={r.chunk_id}")
            if r.page_number:
                params.append(f"page={r.page_number}")
            if params:
                document_url += f"?{'&'.join(params)}"

            result_list.append(
                SearchResultResponse(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    document_name=r.document_name,
                    chunk_text=r.chunk_text,
                    page_number=r.page_number,
                    relevance_score=r.relevance_score,
                    chunk_type=r.chunk_type,
                ).model_dump()
                | {"url": document_url}
            )

        return ResponseEnvelope.success(
            data={
                "query": request.query,
                "search_type": request.search_type,
                "total_count": len(result_list),
                "execution_time_ms": execution_time_ms,
                "results": result_list,
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

        suggestions = search_svc.get_search_suggestions(
            prefix, limit, tenant_id=tenant_id
        )

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
        tenant_id = _tenant_id_from_user(current_user)

        # Check document exists
        doc_row = get_document_with_lock(session, document_id, tenant_id)
        if not doc_row:
            raise HTTPException(status_code=404, detail="Document not found")

        # Increment version using CRUD
        new_version = increment_document_version(session, document_id, tenant_id)
        if new_version is None:
            raise HTTPException(status_code=404, detail="Document not found")

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
        tenant_id = _tenant_id_from_user(current_user)

        # Use CRUD to get version chain
        versions = get_document_version_chain(session, document_id, tenant_id)

        if not versions:
            raise HTTPException(status_code=404, detail="Document not found")

        return ResponseEnvelope.success(
            data={
                "document_id": document_id,
                "versions": versions,
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

        # Use CRUD to check document exists
        document = get_document(session, document_id, tenant_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Use CRUD to get chunks
        chunks = list_chunks_by_document(
            session, document_id, tenant_id, limit=per_page, offset=offset
        )
        total_chunks = count_chunks_by_document(session, document_id, tenant_id)

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
    expires_in_days: Optional[int] = Query(
        None, description="Expiration in days (optional)"
    ),
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
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to share this document",
            )

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
            expires_at = datetime.now(timezone.utc) + timezone.timedelta(
                days=expires_in_days
            )

        # Store share metadata in document.doc_metadata
        share_metadata = document.doc_metadata or {}
        shares = share_metadata.get("shares", [])

        # Check if already shared
        existing_share = next((s for s in shares if s.get("user_id") == user_id), None)
        if existing_share:
            # Update existing share
            existing_share["access_type"] = access_type
            existing_share["expires_at"] = (
                expires_at.isoformat() if expires_at else None
            )
            existing_share["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            # Add new share
            shares.append(
                {
                    "user_id": user_id,
                    "user_email": getattr(target_user, "email", ""),
                    "access_type": access_type,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "shared_by": current_user_id,
                    "shared_at": datetime.now(timezone.utc).isoformat(),
                }
            )

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
            message=f"Document shared successfully with user {user_id}",
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
        logger.info(
            f"Exporting document {document_id} as {format} (tenant={tenant_id})"
        )

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
        import io

        from fastapi.responses import StreamingResponse

        if format == "json":
            # JSON format: structured export with metadata
            export_data = {
                "document": {
                    "id": document.id,
                    "filename": document.filename,
                    "format": document.format,
                    "size": document.size,
                    "created_at": document.created_at.isoformat()
                    if document.created_at
                    else None,
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
                ],
            }

            import json

            output = io.StringIO()
            json.dump(export_data, output, ensure_ascii=False, indent=2)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.json"'
                },
            )

        elif format == "csv":
            # CSV format: spreadsheet-friendly
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(
                [
                    "chunk_index",
                    "page_number",
                    "page",
                    "chunk_type",
                    "text",
                    "position_in_doc",
                    "chunk_version",
                ]
            )

            # Rows
            for chunk in chunks:
                writer.writerow(
                    [
                        chunk.chunk_index,
                        chunk.page_number or "",
                        chunk.page or "",
                        chunk.chunk_type,
                        chunk.text.replace("\n", " ").replace(
                            "\r", ""
                        ),  # Escape newlines
                        chunk.position_in_doc,
                        chunk.chunk_version,
                    ]
                )

            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.csv"'
                },
            )

        elif format == "markdown":
            # Markdown format: readable with headers
            output = io.StringIO()

            output.write(f"# {document.filename}\n\n")
            output.write(f"**Format:** {document.format}\n")
            output.write(f"**Size:** {document.size} bytes\n")
            output.write(f"**Total Chunks:** {len(chunks)}\n")
            output.write(
                f"**Created:** {document.created_at.isoformat() if document.created_at else 'N/A'}\n\n"
            )
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
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.md"'
                },
            )

        elif format == "text":
            # Plain text format: simple concatenation
            output = io.StringIO()

            for chunk in chunks:
                output.write(chunk.text)
                output.write("\n\n")

            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode("utf-8")),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f'attachment; filename="{document.filename}.txt"'
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(500, detail=f"Export failed: {str(e)}")


@router.get("/{document_id}/viewer")
async def get_document_viewer(
    document_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get document file for viewer

    Returns the PDF file content for document viewing
    """
    try:
        tenant_id = _tenant_id_from_user(current_user)

        # Get document metadata
        document = session.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Check if file exists
        storage_path = _storage_path_for(document.id, tenant_id, document.filename)
        if not storage_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found")

        # Return file as streaming response
        from fastapi.responses import FileResponse

        return FileResponse(
            path=str(storage_path),
            filename=document.filename,
            media_type=document.content_type or "application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document viewer: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/{document_id}/query/stream")
async def query_document_stream(
    document_id: str,
    request: dict,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Stream RAG-style responses for a specific document.

    This endpoint provides Server-Sent Events (SSE) streaming for
    document Q&A with LLM-generated answers and references.

    Request body:
    - query: The question to ask about the document
    - top_k: Number of chunks to retrieve (default: 3)

    Returns SSE stream with chunks of type:
    - summary: Document summary
    - detail: Detailed content
    - answer: LLM-generated answer
    - done: Final message with references
    - error: Error message
    """
    import json

    from fastapi.responses import StreamingResponse

    from .search_crud import search_chunks_by_text

    async def event_generator():
        try:
            tenant_id = _tenant_id_from_user(current_user)

            # Validate document exists and user has access
            document = session.exec(
                select(Document)
                .where(Document.id == document_id)
                .where(Document.tenant_id == tenant_id)
                .where(Document.deleted_at.is_(None))
            ).first()

            if not document:
                yield f"data: {json.dumps({'type': 'error', 'text': 'Document not found'})}\n\n"
                return

            query = request.get("query", "").strip()
            top_k = min(request.get("top_k", 3), 10)

            if not query:
                yield f"data: {json.dumps({'type': 'error', 'text': 'Query is required'})}\n\n"
                return

            logger.info(
                f"Document query: document_id={document_id}, query='{query[:50]}', top_k={top_k}"
            )

            # Search for relevant chunks in this specific document
            results = search_chunks_by_text(
                session=session,
                query=query,
                tenant_id=tenant_id,
                top_k=top_k * 2,  # Get more, then filter by document
            )

            # Filter to only chunks from this document
            document_results = [r for r in results if r["document_id"] == document_id][
                :top_k
            ]

            if not document_results:
                yield f"data: {json.dumps({'type': 'summary', 'text': f'문서 "{document.filename}"에서 "{query}"에 관한 내용을 찾을 수 없습니다.'})}\n\n"
                yield f"data: {json.dumps({'type': 'detail', 'text': '검색어를 바꾸거나 다른 문서를 시도해보세요.'})}\n\n"
                yield f"data: {json.dumps({'type': 'answer', 'text': '죄송합니다. 검색 결과가 없습니다.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'meta': {'references': [], 'chunks': []}})}\n\n"
                return

            # Build context from chunks
            references = []
            chunk_infos = []

            for row in document_results:
                chunk_text = row["text"]

                chunk_id = row["id"]
                page_number = row["page_number"]

                chunk_infos.append({"chunk_id": chunk_id, "page": page_number})

                references.append(
                    {
                        "document_id": document_id,
                        "document_title": document.filename,
                        "chunk_id": chunk_id,
                        "page": page_number,
                        "snippet": chunk_text[:200] + "..."
                        if len(chunk_text) > 200
                        else chunk_text,
                        "score": row["score"],
                    }
                )

            # Send summary
            yield f"data: {json.dumps({'type': 'summary', 'text': f'문서 "{document.filename}"에서 {len(document_results)}개의 관련 내용을 찾았습니다.'})}\n\n"

            # Send detail
            score_val = document_results[0].get("score", 0.0)
            detail_text = f'검색어: "{query}"\n발견된 청크: {len(document_results)}개\n관련성: {score_val:.2f}'
            yield f"data: {json.dumps({'type': 'detail', 'text': detail_text})}\n\n"

            # Generate answer (simplified RAG without LLM for now)
            answer_template = '문서 "{doc_name}"에서 검색 결과입니다.\n\n'
            answer_parts = [answer_template.format(doc_name=document.filename)]

            for i, ref in enumerate(references, 1):
                page_info = f"{ref['page']}페이지" if ref["page"] else "페이지 미확인"
                answer_parts.append(f"{i}. ({page_info}) {ref['snippet']}\n")

            answer = "".join(answer_parts)

            # Stream answer character by character
            for char in answer:
                yield f"data: {json.dumps({'type': 'answer', 'text': char})}\n\n"

            # Send done with references
            yield f"data: {json.dumps({'type': 'done', 'meta': {'references': references, 'chunks': chunk_infos}})}\n\n"

        except GeneratorExit:
            logger.info("Client disconnected from stream")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document query stream failed: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'text': f'Error: {str(e)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{document_id}/chunks/{chunk_id}", response_model=ResponseEnvelope)
async def get_chunk_detail(
    document_id: str,
    chunk_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get detailed information for a specific chunk

    Returns chunk details including text, position, and metadata
    """
    try:
        tenant_id = _tenant_id_from_user(current_user)

        # Get chunk with document validation
        chunk = session.exec(
            select(DocumentChunk)
            .join(Document)
            .where(DocumentChunk.id == chunk_id)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()

        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")

        return ResponseEnvelope.success(
            data={
                "chunk": {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page": chunk.page,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                    "snippet": chunk.text[:200] + "..."
                    if len(chunk.text) > 200
                    else chunk.text,
                    "chunk_type": chunk.chunk_type,
                    "position_in_doc": chunk.position_in_doc,
                    "created_at": chunk.created_at.isoformat()
                    if chunk.created_at
                    else None,
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunk detail: {str(e)}")
        raise HTTPException(500, str(e))


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


@router.post("/query-all/stream")
async def query_all_documents_stream(
    request: MultiDocumentQueryRequest,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Stream RAG-style responses across multiple documents.

    This endpoint provides Server-Sent Events (SSE) streaming for
    multi-document Q&A with LLM-generated answers and references.

    Request body:
    - query: The question to ask
    - document_ids: Specific documents to search (None = all documents)
    - categories: Filter by category (manual, policy, technical, guide, report, other)
    - exclude_document_ids: Documents to exclude from search
    - tags: Filter by tags
    - top_k: Number of chunks to retrieve per document (default: 10)
    - min_relevance: Minimum relevance score (default: 0.3)

    Returns SSE stream with chunks of type:
    - progress: Processing status updates
    - summary: Document summary
    - detail: Detailed content
    - answer: LLM-generated answer
    - done: Final message with references
    - error: Error message
    """
    import json

    from fastapi.responses import StreamingResponse

    from .search_crud import search_chunks_by_text

    async def event_generator():
        try:
            tenant_id = _tenant_id_from_user(current_user)
            query = request.query.strip()
            top_k = min(request.top_k, 20)
            min_relevance = request.min_relevance

            if not query:
                yield f"event: error\ndata: {json.dumps({'message': 'Query is required', 'stage': 'init', 'elapsed_ms': 0})}\n\n"
                return

            start_time = time.time()
            elapsed_ms = lambda: int((time.time() - start_time) * 1000)

            # Send progress: init
            yield f"event: progress\ndata: {json.dumps({'stage': 'init', 'message': '질의 분석 중...', 'elapsed_ms': elapsed_ms()})}\n\n"

            # Build document filter
            doc_statement = (
                select(Document)
                .where(Document.tenant_id == tenant_id)
                .where(Document.deleted_at.is_(None))
                .where(Document.status == DocumentStatus.done)
            )

            # Apply document ID filter
            if request.document_ids:
                doc_statement = doc_statement.where(Document.id.in_(request.document_ids))

            # Apply exclude filter
            if request.exclude_document_ids:
                doc_statement = doc_statement.where(Document.id.not_in(request.exclude_document_ids))

            # Apply category filter
            if request.categories:
                doc_statement = doc_statement.where(Document.category.in_(request.categories))

            # Apply tag filter (if tags column has any matching tag)
            if request.tags:
                # Note: This is a simple check; for arrays, you might need a more sophisticated query
                doc_statement = doc_statement.where(Document.tags.op('&&')(request.tags))

            documents = session.exec(doc_statement.limit(100)).all()

            if not documents:
                yield f"event: error\ndata: {json.dumps({'message': '검색 가능한 문서가 없습니다.', 'stage': 'init', 'elapsed_ms': elapsed_ms()})}\n\n"
                return

            # Send progress: searching
            yield f"event: progress\ndata: {json.dumps({'stage': 'searching', 'message': f'{len(documents)}개 문서에서 검색 중...', 'elapsed_ms': elapsed_ms()})}\n\n"

            # Search for relevant chunks across all documents
            doc_ids = [doc.id for doc in documents]
            results = search_chunks_by_text(
                session=session,
                query=query,
                tenant_id=tenant_id,
                top_k=top_k * 3,  # Get more, then filter
            )

            # Filter to only chunks from selected documents
            filtered_results = [
                r for r in results 
                if r["document_id"] in doc_ids and r.get("score", 0) >= min_relevance
            ][:top_k]

            if not filtered_results:
                yield f"event: summary\ndata: {json.dumps({'text': '검색 결과가 없습니다.'})}\n\n"
                yield f"event: detail\ndata: {json.dumps({'text': '검색어를 바꾸거나 필터 조건을 조정해보세요.'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'meta': {'references': [], 'chunks': []}})}\n\n"
                return

            # Send progress: composing
            yield f"event: progress\ndata: {json.dumps({'stage': 'composing', 'message': f'{len(filtered_results)}개 관련 내용 발견, 응답 생성 중...', 'elapsed_ms': elapsed_ms()})}\n\n"

            # Build document ID to name mapping
            doc_name_map = {doc.id: doc.filename for doc in documents}

            # Build references
            references = []
            chunk_infos = []

            for row in filtered_results:
                chunk_text = row["text"]
                chunk_id = row["id"]
                page_number = row.get("page_number")
                doc_id = row["document_id"]
                doc_name = doc_name_map.get(doc_id, "Unknown Document")

                chunk_infos.append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "page": page_number,
                })

                references.append({
                    "document_id": doc_id,
                    "document_title": doc_name,
                    "chunk_id": chunk_id,
                    "page": page_number,
                    "snippet": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text,
                    "score": row.get("score", 0),
                })

            # Send summary
            yield f"event: summary\ndata: {json.dumps({'text': f'{len(documents)}개 문서에서 {len(filtered_results)}개의 관련 내용을 찾았습니다.'})}\n\n"

            # Send detail
            score_val = filtered_results[0].get("score", 0.0)
            detail_text = f'검색어: "{query}"\n검색된 문서: {len(documents)}개\n관련성: {score_val:.2f}'
            yield f"event: detail\ndata: {json.dumps({'text': detail_text})}\n\n"

            # Generate answer
            answer_parts = [f"총 {len(documents)}개 문서에서 검색 결과입니다.\n\n"]

            # Group by document
            from collections import defaultdict
            doc_refs = defaultdict(list)
            for ref in references:
                doc_refs[ref["document_id"]].append(ref)

            for i, (doc_id, refs) in enumerate(doc_refs.items(), 1):
                doc_name = refs[0]["document_title"]
                answer_parts.append(f"## {i}. {doc_name}\n")
                for ref in refs[:3]:  # Max 3 refs per document
                    page_info = f"{ref['page']}페이지" if ref["page"] else "페이지 미확인"
                    answer_parts.append(f"- ({page_info}) {ref['snippet'][:100]}...\n")
                answer_parts.append("\n")

            answer = "".join(answer_parts)

            # Send progress: presenting
            yield f"event: progress\ndata: {json.dumps({'stage': 'presenting', 'message': '응답 생성 중...', 'elapsed_ms': elapsed_ms()})}\n\n"

            # Stream answer character by character
            for char in answer:
                yield f"event: answer\ndata: {json.dumps({'text': char})}\n\n"

            # Send done with references
            yield f"event: done\ndata: {json.dumps({'meta': {'references': references, 'chunks': chunk_infos, 'documents_searched': len(documents), 'total_time_ms': elapsed_ms()}})}\n\n"

        except GeneratorExit:
            logger.info("Client disconnected from stream")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Multi-document query stream failed: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': f'Error: {str(e)}', 'stage': 'unknown', 'elapsed_ms': 0})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.patch("/{document_id}/category", response_model=ResponseEnvelope)
async def update_document_category(
    document_id: str,
    category: str = Query(..., description="Category: manual, policy, technical, guide, report, other"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Update document category and tags

    Categories:
    - manual: 매뉴얼
    - policy: 정책
    - technical: 기술문서
    - guide: 가이드
    - report: 보고서
    - other: 기타
    """
    try:
        from models.document import DocumentCategory

        logger.info(f"[update_document_category] Request: document_id={document_id}, category={category}, tags={tags}")

        # Validate category
        valid_categories = [c.value for c in DocumentCategory]
        if category not in valid_categories:
            logger.error(f"[update_document_category] Invalid category: {category}")
            raise HTTPException(
                400,
                f"Invalid category: {category}. Valid options: {', '.join(valid_categories)}"
            )

        tenant_id = _tenant_id_from_user(current_user)
        logger.info(f"[update_document_category] Looking for document: {document_id}, tenant: {tenant_id}")

        document = session.exec(
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        ).first()

        if not document:
            logger.error(f"[update_document_category] Document not found: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")

        logger.info(f"[update_document_category] Found document: {document.filename}, updating category to {category}")

        document.category = category
        if tags:
            document.tags = [t.strip() for t in tags.split(",") if t.strip()]
        document.updated_at = datetime.now(timezone.utc)
        session.add(document)
        session.commit()
        session.refresh(document)

        logger.info(f"[update_document_category] Success: document.category={document.category}")

        return ResponseEnvelope.success(
            data={
                "document_id": document_id,
                "category": document.category,
                "tags": document.tags,
            },
            message=f"Document category updated to {category}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_document_category] Failed to update category: {str(e)}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/categories/list", response_model=ResponseEnvelope)
async def list_categories(
    current_user: TbUser = Depends(get_current_user),
):
    """
    List available document categories

    Returns category list with Korean labels
    """
    from models.document import DocumentCategory

    categories = [
        {"value": c.value, "label": {
            "manual": "매뉴얼",
            "policy": "정책",
            "technical": "기술문서",
            "guide": "가이드",
            "report": "보고서",
            "other": "기타",
        }.get(c.value, c.value)}
        for c in DocumentCategory
    ]

    return ResponseEnvelope.success(data={"categories": categories})


