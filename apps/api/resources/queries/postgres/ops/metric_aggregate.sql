SELECT metric_name, metric_type, COUNT(*) as count,
       AVG(metric_value) as avg_value,
       MIN(metric_value) as min_value,
       MAX(metric_value) as max_value
FROM metrics
WHERE ({where_clause})
GROUP BY metric_name, metric_type
ORDER BY count DESC
