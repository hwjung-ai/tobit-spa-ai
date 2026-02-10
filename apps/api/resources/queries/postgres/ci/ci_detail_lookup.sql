-- CI Detail Lookup Query
-- Fetches detailed CI configuration including extended attributes and tags
-- Parameters: field (ci_id or ci_code), value, tenant_id

SELECT ci.ci_id,
       ci.ci_code,
       ci.ci_name,
       ci.ci_type,
       ci.ci_subtype,
       ci.ci_category,
       ci.status,
       ci.location,
       ci.owner,
       ci_ext.tags,
       ci_ext.attributes,
       ci.created_at,
       ci.updated_at
FROM ci
LEFT JOIN ci_ext ON ci.ci_id = ci_ext.ci_id
WHERE ci.{field} = %s
  AND ci.tenant_id = %s
  AND ci.deleted_at IS NULL
