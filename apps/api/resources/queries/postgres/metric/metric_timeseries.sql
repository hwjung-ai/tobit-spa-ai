
SELECT time_bucket(%s, time) AS bucket_time, AVG(value) AS value
FROM metric_value
WHERE tenant_id = %s
  AND ci_id = %s
  AND metric_id = %s
  AND time >= %s
  AND time < %s
GROUP BY bucket_time
ORDER BY bucket_time
