import json
import os
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

import core.db as core_db
from core.config import AppSettings
from models import Document, DocumentChunk, DocumentStatus
import workers.queue

# Ensure uploads go to a temp storage before FastAPI loads settings
storage_root = Path(tempfile.mkdtemp(prefix="codex-docs-"))
os.environ.setdefault("DOCUMENT_STORAGE_ROOT", str(storage_root))

from main import app


@pytest.fixture(autouse=True)
def override_session(monkeypatch: pytest.MonkeyPatch):
    AppSettings.connection_cache.clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

    def get_session_override():
        with SessionLocal() as session:
            yield session

    monkeypatch.setattr(core_db, "SessionLocal", SessionLocal)
    monkeypatch.setattr(core_db, "get_session", get_session_override)
    monkeypatch.setattr(core_db, "engine", engine)
    yield


@pytest.mark.asyncio
async def test_upload_creates_metadata_and_list(monkeypatch: pytest.MonkeyPatch):
    enqueued_ids: list[str] = []

    def fake_enqueue(document_id: str):
        enqueued_ids.append(document_id)
        return {"document_id": document_id}

    monkeypatch.setattr(workers.queue, "enqueue_parse_document", fake_enqueue)
    import api.routes.documents as documents_module
    monkeypatch.setattr(documents_module, "enqueue_parse_document", fake_enqueue)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/documents/upload",
            files={"file": ("notes.txt", b"Hello world", "text/plain")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == 0
    document = payload["data"]["document"]
    assert document["status"] == "queued"
    assert len(enqueued_ids) == 1
    assert enqueued_ids[0] == document["id"]

    stored_path = storage_root / document["tenant_id"] / document["id"] / document["filename"]
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"Hello world"

    with core_db.SessionLocal() as session:
        stored = session.get(Document, document["id"])
        assert stored is not None


@pytest.mark.asyncio
async def test_document_stream_done_contains_references(monkeypatch: pytest.MonkeyPatch):
    from api.routes import documents as documents_module

    class FakeSearchService:
        def __init__(self, settings):
            pass

        def embed_query(self, query: str) -> list[float]:
            return [0.0] * 1536

        def fetch_top_chunks(self, session: Session, document_id: str, top_k: int, embedding: list[float]):
            statement = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            return session.exec(statement).scalars().all()

        def score_chunk(self, chunk: DocumentChunk, query_embedding: list[float]) -> float:
            return 0.5

    class FakeOrchestrator:
        def __init__(self, settings):
            pass

        async def stream_chat(self, prompt: str):
            yield {"type": "answer", "text": "reference answer"}
            yield {"type": "done", "text": "complete"}

    monkeypatch.setattr(documents_module, "DocumentSearchService", FakeSearchService)
    monkeypatch.setattr(documents_module, "OpenAIOrchestrator", FakeOrchestrator)

    session = core_db.SessionLocal()
    document = Document(
        tenant_id="default",
        user_id="default",
        filename="report.pdf",
        content_type="application/pdf",
        size=123,
        status=DocumentStatus.done,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    document_id = document.id
    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        page=2,
        text="Important snippet content for reference testing.",
        embedding=[0.0] * 1536,
    )
    session.add(chunk)
    session.commit()
    chunk_id = chunk.id
    session.close()

    stream_transport = ASGITransport(app=app)
    async with AsyncClient(transport=stream_transport, base_url="http://testserver") as client:
        async with client.stream(
            "POST",
            f"/documents/{document_id}/query/stream",
            json={"query": "test", "top_k": 1},
            headers={"X-Tenant-Id": "default", "X-User-Id": "default"},
            timeout=10,
        ) as response:
            assert response.status_code == 200
            done_payload = None
            async for line in response.aiter_lines():
                if not line.strip().startswith("data:"):
                    continue
                payload = json.loads(line.strip()[len("data:") :].strip())
                if payload.get("type") == "done":
                    done_payload = payload
                    break

    assert done_payload is not None
    references = done_payload.get("meta", {}).get("references")
    assert references
    assert references[0]["document_title"] == "report.pdf"
    assert references[0]["chunk_id"] == chunk_id
