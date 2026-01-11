from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Tuple

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import delete, func, select

from api.routes.chat import _resolve_identity  # reuse identity resolver
from core.config import AppSettings, get_settings
from core.db import Session, get_session
from models import Document, DocumentChunk, DocumentStatus
from schemas import (
    DocumentChunkDetail,
    DocumentDetail,
    DocumentItem,
    DocumentQueryRequest,
    DocumentUploadResponse,
    ResponseEnvelope,
)
from services.document import DocumentProcessingError, DocumentSearchService, DocumentStorage
from services.orchestrator import OpenAIOrchestrator
from workers.queue import enqueue_parse_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _document_payload(document: Document) -> DocumentItem:
    return DocumentItem.model_validate(document)


def _truncate_snippet(text: str, limit: int = 200) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"



@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")

    content = await file.read()
    document = Document(
        tenant_id=tenant_id,
        user_id=user_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    storage = DocumentStorage(settings)
    storage.path_for(tenant_id, document.id, document.filename).write_bytes(content)
    enqueue_parse_document(document.id)

    payload = DocumentUploadResponse.model_validate(document.model_dump())
    return ResponseEnvelope.success(data={"document": payload.model_dump()})


@router.get("/")
def list_documents(
    tenant_filter: str | None = Query(None, alias="tenant_id"),
    user_filter: str | None = Query(None, alias="user_id"),
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    tenant = tenant_filter or tenant_id
    user = user_filter or user_id
    statement = (
        select(Document)
        .where(Document.deleted_at.is_(None))
        .where(Document.tenant_id == tenant)
        .where(Document.user_id == user)
        .order_by(Document.updated_at.desc())
    )
    documents = session.exec(statement).scalars().all()
    payloads = [DocumentItem.model_validate(doc.model_dump()).model_dump() for doc in documents]
    return ResponseEnvelope.success(data={"documents": payloads})


@router.get("/{document_id}")
def get_document(
    document_id: str,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    document = session.get(Document, document_id)
    if not document or document.deleted_at:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.tenant_id != tenant_id or document.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_count_stmt = select(func.count(DocumentChunk.id)).where(
        DocumentChunk.document_id == document_id
    )
    chunk_count = session.exec(chunk_count_stmt).scalar_one()

    payload = DocumentDetail.model_validate(document.model_dump())
    payload.chunk_count = chunk_count
    return ResponseEnvelope.success(data={"document": payload.model_dump()})


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
    settings: AppSettings = Depends(get_settings),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    document = session.get(Document, document_id)
    if not document or document.deleted_at:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.tenant_id != tenant_id or document.user_id != user_id:
        raise HTTPException(status_code=403, detail="Document not found")

    document.deleted_at = datetime.now(timezone.utc)
    session.add(document)
    session.exec(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    session.commit()
    DocumentStorage(settings).cleanup(document.tenant_id, document.id)
    return ResponseEnvelope.success(data={"document_id": document.id})


@router.get("/{document_id}/viewer")
def document_viewer(
    document_id: str,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
    settings: AppSettings = Depends(get_settings),
) -> FileResponse:
    tenant_id, user_id = identity
    document = session.get(Document, document_id)
    if not document or document.deleted_at:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.tenant_id != tenant_id or document.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    storage = DocumentStorage(settings)
    path = storage.path_for(document.tenant_id, document.id, document.filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document file missing")
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Viewer only supports PDF for now")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.filename,
    )


@router.get("/{document_id}/chunks/{chunk_id}")
def chunk_detail(
    document_id: str,
    chunk_id: str,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
) -> ResponseEnvelope:
    tenant_id, user_id = identity
    document = session.get(Document, document_id)
    if not document or document.deleted_at:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.tenant_id != tenant_id or document.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    chunk = session.get(DocumentChunk, chunk_id)
    if not chunk or chunk.document_id != document_id:
        raise HTTPException(status_code=404, detail="Chunk not found")
    payload = DocumentChunkDetail(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        page=chunk.page,
        text=chunk.text,
        snippet=_truncate_snippet(chunk.text, limit=300),
    )
    return ResponseEnvelope.success(data={"chunk": payload.model_dump()})


@router.post("/{document_id}/query/stream")
async def query_document_stream(
    document_id: str,
    request: DocumentQueryRequest,
    session: Session = Depends(get_session),
    identity: Tuple[str, str] = Depends(_resolve_identity),
    settings: AppSettings = Depends(get_settings),
) -> EventSourceResponse:
    tenant_id, user_id = identity
    document = session.get(Document, document_id)
    if not document or document.deleted_at:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.tenant_id != tenant_id or document.user_id != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != DocumentStatus.done:
        raise HTTPException(status_code=400, detail="Document is still processing")

    try:
        search_service = DocumentSearchService(settings)
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    embedding = search_service.embed_query(request.query)
    chunks = search_service.fetch_top_chunks(session, document_id, request.top_k, embedding)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document has no indexed chunks")

    chunk_meta = [
        {
            "chunk_id": chunk.id,
            "page": chunk.page,
            "snippet": _truncate_snippet(chunk.text),
        }
        for chunk in chunks
    ]
    context_snippets = [
        f"[chunk:{chunk.id} page:{chunk.page}] {chunk.text}"
        for chunk in chunks
    ]
    context = "Document context:\n" + "\n\n".join(context_snippets)
    prompt = f"{context}\n\nQuestion: {request.query}"
    orchestrator = OpenAIOrchestrator(settings)
    references = []
    for chunk in chunks:
        references.append(
            {
                "document_id": document.id,
                "document_title": document.filename,
                "chunk_id": chunk.id,
                "page": chunk.page,
                "score": search_service.score_chunk(chunk, embedding),
                "snippet": _truncate_snippet(chunk.text),
            }
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in orchestrator.stream_chat(prompt):
                payload = dict(chunk)
                payload["meta"] = {"document_id": document.id, "chunks": chunk_meta}
                if chunk.get("type") == "done":
                    payload["meta"]["references"] = references
                payload["document_id"] = document.id
                yield json.dumps(payload)
        except Exception as exc:
            error_payload = {
                "type": "error",
                "text": str(exc),
                "document_id": document.id,
                "meta": {"document_id": document.id, "chunks": chunk_meta},
            }
            yield json.dumps(error_payload)

    return EventSourceResponse(event_generator())
