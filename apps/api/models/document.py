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

    # Task 5: Document Search Enhancement fields
    format: str | None = Field(default='pdf', max_length=20)  # pdf, docx, xlsx, pptx, image
    processing_progress: int | None = Field(default=0)  # 0-100
    total_chunks: int | None = Field(default=0)
    error_details: dict | None = None  # JSON error information
    metadata: dict | None = None  # JSON metadata (pages, word_count, extraction_method, language)
    created_by: str | None = None  # User ID who created the document


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

    # Task 5: Document Search Enhancement fields
    chunk_version: int = Field(default=1)  # For incremental updates
    chunk_type: str = Field(default='text', max_length=50)  # text, table, image, mixed
    position_in_doc: int | None = None  # Chunk order in document
    page_number: int | None = None  # For PDF/PPTX
    slide_number: int | None = None  # For PPTX
    table_data: dict | None = None  # Structured table data
    source_hash: str | None = None  # For change detection
    relevance_score: float | None = None  # For search results
