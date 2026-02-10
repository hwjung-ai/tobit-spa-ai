-- Maintenance History List Query with Pagination
-- Lists maintenance records with optional filtering
-- Parameters: tenant_id, ci_id (optional), start_time (optional), end_time (optional), offset, limit

SELECT mh.id,
       mh.start_time,
       mh.maint_type,
       mh.duration_min,
       mh.result,
       mh.summary,
       mh.detail,
       mh.performer,
       c.ci_code,
       c.ci_name,
       c.ci_type
FROM maintenance_history mh
LEFT JOIN ci c ON c.ci_id = mh.ci_id
WHERE mh.tenant_id = %s
  AND (%s IS NULL OR mh.ci_id = %s::uuid)
  AND (%s IS NULL OR mh.start_time >= %s::timestamp)
  AND (%s IS NULL OR mh.start_time < %s::timestamp)
ORDER BY mh.start_time DESC
LIMIT %s
OFFSET %s
