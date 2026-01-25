
SELECT created_at as start_time, work_type, impact_level, result, summary
FROM work_history
WHERE tenant_id = %s AND ci_id = %s AND created_at >= %s AND created_at < %s
ORDER BY created_at DESC
LIMIT 50
