SELECT mv.ci_id, {function} AS value
FROM metric_value mv
JOIN metric_def md ON mv.metric_id = md.metric_id
WHERE mv.tenant_id = %s AND md.metric_name = %s
  AND mv.ci_id = ANY(%s)
  AND mv.time >= %s AND mv.time < %s
GROUP BY mv.ci_id
ORDER BY value DESC
LIMIT %s
