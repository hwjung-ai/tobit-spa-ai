-- CI List Query with Pagination
-- Lists all CIs with optional pagination
-- Parameters: tenant_id, limit, offset

SELECT ci_id,
       ci_code,
       ci_name,
       ci_type,
       ci_subtype,
       ci_category,
       status,
       location,
       owner,
       created_at
FROM ci
WHERE tenant_id = %s
  AND deleted_at IS NULL
ORDER BY ci_code
LIMIT %s
OFFSET %s
