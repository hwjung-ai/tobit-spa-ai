
SELECT
    COUNT(*) as total_count,
    COUNT(DISTINCT ci_type) as ci_type_count,
    COUNT(DISTINCT ci_subtype) as ci_subtype_count,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count,
    COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_count,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count
FROM ci
WHERE tenant_id = %s
  AND deleted_at IS NULL
