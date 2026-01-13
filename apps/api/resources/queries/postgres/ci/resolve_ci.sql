
SELECT ci_code, ci_name, ci_type, ci_subtype, status, criticality, owner, location, updated_at
FROM ci
WHERE tenant_id = %s
  AND ci_id = %s
  AND deleted_at IS NULL
