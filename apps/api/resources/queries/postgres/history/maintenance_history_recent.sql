SELECT mh.start_time, c.ci_code, c.ci_name, mh.maint_type, mh.duration_min, mh.result, mh.summary
FROM maintenance_history AS mh
LEFT JOIN ci AS c ON c.ci_id = mh.ci_id
WHERE mh.tenant_id = %s AND mh.start_time >= %s AND mh.start_time < %s
ORDER BY mh.start_time DESC
LIMIT %s
