from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel


class DocumentStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class DocumentBase(SQLModel):
    tenant_id: str
    user_id: str
    filename: str
    content_type: str
    size: int
    status: DocumentStatus = Field(default=DocumentStatus.queued)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None


class Document(DocumentBase, table=True):
    __tablename__ = "documents"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=36)


class DocumentChunkBase(SQLModel):
    document_id: str = Field(foreign_key="documents.id")
    chunk_index: int
    page: int | None = None
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentChunk(DocumentChunkBase, table=True):
    __tablename__ = "document_chunks"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=36)
    embedding: list[float] = Field(sa_column=Column(Vector(1536), nullable=False))
