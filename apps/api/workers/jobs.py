from __future__ import annotations

import logging

from core.config import get_settings
from core.db import SessionLocal
from services.document import DocumentIndexService, DocumentProcessingError


def parse_and_index_document(document_id: str) -> dict[str, str]:
    settings = get_settings()
    session = SessionLocal()
    try:
        indexer = DocumentIndexService(session, settings)
        indexer.process(document_id)
        return {"document_id": document_id, "status": "completed"}
    except DocumentProcessingError as exc:
        logging.error("Document %s failed to process: %s", document_id, exc)
        return {"document_id": document_id, "status": "failed", "error": str(exc)}
    except Exception as exc:
        logging.exception(
            "Unexpected failure while processing document %s: %s", document_id, exc
        )
        return {
            "document_id": document_id,
            "status": "failed",
            "error": "internal error",
        }
    finally:
        session.close()
