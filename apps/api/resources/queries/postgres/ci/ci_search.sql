-- CI 키워드 검색
SELECT
    ci.ci_id,
    ci.ci_code,
    ci.ci_name,
    ci.ci_type,
    ci.ci_subtype,
    ci.ci_category,
    ci.status,
    ci.location,
    ci.owner,
    ci.description,
    ci.created_at,
    ci.updated_at
FROM ci
LEFT JOIN ci_ext ON ci.ci_id = ci_ext.ci_id
WHERE ci.tenant_id = %s
  AND ci.deleted_at IS NULL
  AND (
    ci.ci_name ILIKE %s OR
    ci.ci_code ILIKE %s OR
    ci.ci_type ILIKE %s OR
    ci.ci_subtype ILIKE %s OR
    ci.ci_category ILIKE %s OR
    ci.description ILIKE %s
  )
ORDER BY
    CASE
        WHEN ci.ci_name ILIKE %s THEN 1
        WHEN ci.ci_code ILIKE %s THEN 2
        ELSE 3
    END,
    ci.ci_code
LIMIT %s