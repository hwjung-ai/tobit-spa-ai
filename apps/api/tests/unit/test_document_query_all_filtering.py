from app.modules.document_processor.router import (
    RAG_CONTEXT_TOP_K,
    _build_rag_prompt,
    _compose_fallback_answer,
    _select_relevant_chunks,
)


def test_select_relevant_chunks_relaxes_threshold_when_scores_are_low():
    results = [
        {"document_id": "doc-1", "score": 0.089, "text": "system architecture"},
        {"document_id": "doc-1", "score": 0.082, "text": "system config"},
        {"document_id": "doc-2", "score": 0.075, "text": "system overview"},
    ]

    selected, relaxed = _select_relevant_chunks(
        results=results,
        allowed_document_ids={"doc-1", "doc-2"},
        min_relevance=0.3,
        top_k=2,
    )

    assert relaxed is True
    assert len(selected) == 2
    assert selected[0]["score"] >= selected[1]["score"]
    assert all(item["document_id"] in {"doc-1", "doc-2"} for item in selected)


def test_build_rag_prompt_includes_query_and_reference_context():
    references = [
        {
            "document_title": "manual.pdf",
            "page": 12,
            "snippet": "ip command shows and manipulates routes.",
        }
    ]

    prompt = _build_rag_prompt("ip 옵션 알려줘", references)

    assert "Question:" in prompt
    assert "ip 옵션 알려줘" in prompt
    assert "manual.pdf p.12" in prompt
    assert "ip command shows and manipulates routes." in prompt


def test_compose_fallback_answer_lists_each_reference():
    references = [
        {"document_title": "A", "page": 1, "snippet": "first"},
        {"document_title": "B", "page": None, "snippet": "second"},
    ]

    answer = _compose_fallback_answer("질문", references)

    assert "질문" in answer
    assert "1. A (1페이지)" in answer
    assert "2. B (페이지 미확인)" in answer
    assert "first" in answer
    assert "second" in answer


def test_rag_context_top_k_is_five():
    assert RAG_CONTEXT_TOP_K == 5
