from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class DocumentItem(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    filename: str
    content_type: str
    size: int
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentItem):
    deleted_at: datetime | None = None
    chunk_count: int = 0


class DocumentQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class DocumentUploadResponse(DocumentItem):
    pass


class DocumentChunkDetail(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None
    text: str
    snippet: str

    model_config = ConfigDict(from_attributes=True)
