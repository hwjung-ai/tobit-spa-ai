SELECT ci_id, ci_code, ci_name, ci_type, ci_subtype, ci_category, status, location, owner
FROM ci
WHERE tenant_id = %s AND deleted_at IS NULL
ORDER BY ci_code
LIMIT %s OFFSET %s
