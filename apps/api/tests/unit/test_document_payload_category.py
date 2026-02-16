from models.document import Document, DocumentStatus

from app.modules.document_processor.router import _build_document_payload


def test_build_document_payload_includes_category_and_tags():
    document = Document(
        id="doc-1",
        tenant_id="default",
        user_id="u1",
        filename="manual.pdf",
        content_type="application/pdf",
        size=1234,
        status=DocumentStatus.done,
        format="pdf",
        category="manual",
        tags=["linux", "systemd"],
    )

    payload = _build_document_payload(document, chunk_count=5)

    assert payload["category"] == "manual"
    assert payload["tags"] == ["linux", "systemd"]
    assert payload["chunk_count"] == 5
