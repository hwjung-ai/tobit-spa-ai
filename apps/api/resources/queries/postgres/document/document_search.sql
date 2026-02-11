-- Document Search Tool
-- Purpose: Search documents using vector and text search

SELECT
    d.id as document_id,
    d.filename as document_name,
    dc.id as chunk_id,
    dc.text as chunk_text,
    dc.page_number,
    'document' as chunk_type,
    -- Calculate relevance score based on multiple factors
    CASE
        WHEN d.filename ILIKE '%' || :query || '%' THEN 1.0
        WHEN dc.text ILIKE '%' || :query || '%' THEN 0.8
        ELSE 0.5
    END as relevance_score
FROM documents d
JOIN document_chunks dc ON d.id = dc.document_id
WHERE d.tenant_id = :tenant_id
AND (
    dc.text ILIKE '%' || :query || '%'
    OR d.filename ILIKE '%' || :query || '%'
)
ORDER BY
    relevance_score DESC,
    d.filename,
    dc.page_number
LIMIT :limit;