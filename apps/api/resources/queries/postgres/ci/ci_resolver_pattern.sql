SELECT ci_id, ci_code, ci_name, ci_type, ci_subtype, ci_category
FROM ci
WHERE tenant_id = %s AND deleted_at IS NULL AND {field} ILIKE %s
LIMIT %s
