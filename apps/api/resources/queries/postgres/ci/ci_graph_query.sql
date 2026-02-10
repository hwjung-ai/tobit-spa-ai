
SELECT
    c1.ci_id as from_ci_id,
    c1.ci_code as from_ci_code,
    c1.ci_name as from_ci_name,
    r.relationship_type,
    c2.ci_id as to_ci_id,
    c2.ci_code as to_ci_code,
    c2.ci_name as to_ci_name,
    r.strength,
    r.created_at
FROM ci_relationship r
JOIN ci c1 ON c1.ci_id = r.from_ci_id
JOIN ci c2 ON c2.ci_id = r.to_ci_id
WHERE r.tenant_id = %s
  AND (%s IS NULL OR c1.ci_code = %s)
  AND (%s IS NULL OR c1.ci_id = %s)
  AND r.relationship_type IN (%s)
  AND r.deleted_at IS NULL
ORDER BY r.strength DESC
LIMIT %s
