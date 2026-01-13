SELECT metric_id, metric_name
FROM metric_def
WHERE metric_name = %s
LIMIT 1
