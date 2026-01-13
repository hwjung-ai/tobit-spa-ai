
SELECT start_time, work_type, impact_level, result, summary
FROM work_history
WHERE tenant_id = %s AND ci_id = %s AND start_time >= %s AND start_time < %s
ORDER BY start_time DESC
LIMIT 50
