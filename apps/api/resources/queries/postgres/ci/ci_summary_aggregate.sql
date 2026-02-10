-- CI Summary Aggregation Query
-- Aggregates CI distribution by type, subtype, and status
-- Parameters: tenant_id

SELECT ci_type,
       ci_subtype,
       status,
       COUNT(*) as cnt
FROM ci
WHERE tenant_id = %s
  AND deleted_at IS NULL
GROUP BY ci_type, ci_subtype, status
ORDER BY cnt DESC
