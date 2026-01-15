SELECT ci_id, ci_code, ci_name, ci_type, ci_subtype, ci_category
FROM ci
WHERE ci_code = %s AND tenant_id = %s AND deleted_at IS NULL
LIMIT %s
