from __future__ import annotations

import logging
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import docx
from app.llm.client import get_llm_client
from core.config import AppSettings
from models import Document, DocumentChunk, DocumentStatus
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlmodel import Session

MAX_CHUNK_CHARS = 1100
EMBED_BATCH_SIZE = 16


class DocumentStorage:
    def __init__(self, settings: AppSettings):
        self._base = settings.document_storage_path
        self._base.mkdir(parents=True, exist_ok=True)

    def path_for(self, tenant_id: str, document_id: str, filename: str) -> Path:
        target_dir = self._base / tenant_id / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    def cleanup(self, tenant_id: str, document_id: str) -> None:
        target_dir = self._base / tenant_id / document_id
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)


@dataclass
class ChunkCandidate:
    text: str
    page: int | None


class DocumentProcessingError(Exception):
    pass


class DocumentIndexService:
    def __init__(self, session: Session, settings: AppSettings):
        self.session = session
        self.settings = settings
        self.storage = DocumentStorage(settings)
        if not settings.openai_api_key:
            raise DocumentProcessingError("OpenAI API key is required for embeddings")
        if not settings.embed_model:
            raise DocumentProcessingError("EMBED_MODEL is required for embeddings")
        self._llm = get_llm_client()

    def process(self, document_id: str) -> None:
        document = self.session.get(Document, document_id)
        if not document:
            raise DocumentProcessingError(f"Document '{document_id}' not found")

        document.status = DocumentStatus.processing
        document.error_message = None
        document.updated_at = datetime.now(timezone.utc)
        self.session.add(document)
        self.session.commit()

        try:
            path = self.storage.path_for(document.tenant_id, document.id, document.filename)
            if not path.exists():
                raise DocumentProcessingError("Uploaded document is missing on disk")

            chunks = list(self._extract_chunks(path))
            if not chunks:
                raise DocumentProcessingError("Document contains no parsable text")

            embeddings = self._embed_chunks([chunk.text for chunk in chunks])
            self._overwrite_chunks(document, chunks, embeddings)

            document.status = DocumentStatus.done
            document.updated_at = datetime.now(timezone.utc)
            self.session.add(document)
            self.session.commit()
        except Exception as exc:
            document.status = DocumentStatus.failed
            document.error_message = str(exc)
            document.updated_at = datetime.now(timezone.utc)
            self.session.add(document)
            self.session.commit()
            logging.exception("Document %s failed to index: %s", document_id, exc)
            raise

    def _embed_chunks(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for batch_start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[batch_start : batch_start + EMBED_BATCH_SIZE]
            response = self._llm.embed(
                model=self.settings.embed_model,
                input=batch,
            )
            for item in response.data:
                embeddings.append(list(item.embedding))
        return embeddings

    def _overwrite_chunks(
        self,
        document: Document,
        chunks: list[ChunkCandidate],
        embeddings: list[list[float]],
    ) -> None:
        assert len(chunks) == len(embeddings)
        self.session.exec(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        self.session.commit()

        new_chunks = []
        for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            new_chunks.append(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    page=chunk.page,
                    text=chunk.text,
                    embedding=vector,
                )
            )
        self.session.add_all(new_chunks)
        self.session.commit()

    def _extract_chunks(self, path: Path) -> Iterator[ChunkCandidate]:
        for block, page in self._extract_blocks(path):
            yield from self._chunk_paragraph(block, page)

    def _extract_blocks(self, path: Path) -> Iterator[tuple[str, int | None]]:
        suffix = path.suffix.lower()
        if suffix == ".txt":
            content = path.read_text(encoding="utf-8", errors="ignore")
            for block in content.split("\n\n"):
                text = block.strip()
                if text:
                    yield text, None
        elif suffix == ".pdf":
            reader = PdfReader(path)
            for idx, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    yield text, idx
        elif suffix == ".docx":
            doc = docx.Document(path)
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    yield text, None
        else:
            raise DocumentProcessingError(f"Unsupported file type: {suffix}")

    def _chunk_paragraph(self, text: str, page: int | None) -> Iterator[ChunkCandidate]:
        buffer: list[str] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            prospective = " ".join(buffer + [line]).strip()
            if buffer and len(prospective) > MAX_CHUNK_CHARS:
                yield ChunkCandidate(text=" ".join(buffer).strip(), page=page)
                buffer = [line]
            else:
                buffer.append(line)
        if buffer:
            yield ChunkCandidate(text=" ".join(buffer).strip(), page=page)


class DocumentSearchService:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        if not settings.openai_api_key:
            raise DocumentProcessingError("OpenAI API key is required for queries")
        if not settings.embed_model:
            raise DocumentProcessingError("EMBED_MODEL is required for queries")
        self._llm = get_llm_client()

    def embed_query(self, query: str) -> list[float]:
        response = self._llm.embed(
            model=self.settings.embed_model,
            input=query,
        )
        if not response.data:
            raise DocumentProcessingError("OpenAI embedding response was empty")
        return list(response.data[0].embedding)

    def fetch_top_chunks(
        self,
        session: Session,
        document_id: str,
        top_k: int,
        embedding: list[float],
    ) -> list[DocumentChunk]:
        vector = embedding
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.embedding.cosine_distance(vector))
            .limit(top_k)
        )
        return session.exec(statement).scalars().all()

    def score_chunk(self, chunk: DocumentChunk, query_embedding: list[float]) -> float:
        if chunk.embedding is None or len(chunk.embedding) == 0:
            return 0.0
        return self._cosine_similarity(chunk.embedding, query_embedding)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
