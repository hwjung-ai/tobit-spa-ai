SELECT mv.time, mv.value
FROM metric_value mv
JOIN metric_def md ON mv.metric_id = md.metric_id
WHERE mv.tenant_id = %s AND md.metric_name = %s
  AND mv.ci_id = %s
  AND mv.time >= %s AND mv.time < %s
ORDER BY mv.time DESC
LIMIT %s
