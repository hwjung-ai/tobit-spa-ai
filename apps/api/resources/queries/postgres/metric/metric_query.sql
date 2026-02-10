
SELECT
    m.metric_id,
    m.metric_name,
    mv.ci_id,
    c.ci_code,
    c.ci_name,
    mv.time,
    mv.value,
    m.unit
FROM metric_value mv
JOIN metric m ON m.metric_id = mv.metric_id
JOIN ci c ON c.ci_id = mv.ci_id
WHERE mv.tenant_id = %s
  AND c.ci_code = %s
  AND m.metric_name = %s
  AND mv.time >= %s
  AND mv.time < %s
ORDER BY mv.time DESC
LIMIT %s
