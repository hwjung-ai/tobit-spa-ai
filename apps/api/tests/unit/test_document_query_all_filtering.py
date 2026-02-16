from app.modules.document_processor.router import _select_relevant_chunks


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
