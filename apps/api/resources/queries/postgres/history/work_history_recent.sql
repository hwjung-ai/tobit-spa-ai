SELECT wh.created_at as start_time, c.ci_code, c.ci_name, wh.work_type, wh.impact_level, wh.result, wh.summary
FROM work_history AS wh
LEFT JOIN ci AS c ON c.ci_id = wh.ci_id
WHERE wh.tenant_id = %s AND wh.created_at >= %s AND wh.created_at < %s
ORDER BY wh.created_at DESC
LIMIT %s
