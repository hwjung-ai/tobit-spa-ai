
SELECT start_time, maint_type, duration_min, result, summary
FROM maintenance_history
WHERE tenant_id = %s AND ci_id = %s AND start_time >= %s AND start_time < %s
ORDER BY start_time DESC
LIMIT 50
