
SELECT
    wh.work_id,
    wh.work_type,
    wh.summary,
    wh.detail,
    wh.start_time,
    wh.end_time,
    wh.duration_min,
    wh.result,
    c.ci_id,
    c.ci_code,
    c.ci_name
FROM work_history wh
LEFT JOIN ci c ON c.ci_id = wh.ci_id
WHERE wh.tenant_id = %s
  AND (%s IS NULL OR c.ci_code = %s)
  AND (%s IS NULL OR wh.start_time >= %s)
  AND (%s IS NULL OR wh.start_time < %s)
  AND wh.deleted_at IS NULL
ORDER BY wh.start_time DESC
LIMIT %s
