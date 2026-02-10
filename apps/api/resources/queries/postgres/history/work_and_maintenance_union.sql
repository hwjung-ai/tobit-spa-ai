-- Combined Work and Maintenance History
-- Fetches both work_history and maintenance_history in a single UNION query
-- Parameters: tenant_id (work), start_time_wh (optional), end_time_wh (optional), ci_id_wh (optional), limit_wh,
--             tenant_id (maint), start_time_mh (optional), end_time_mh (optional), ci_id_mh (optional), limit_mh,
--             final_limit

(
    SELECT '작업' AS history_type,
           wh.work_type AS type,
           wh.summary,
           wh.detail,
           wh.start_time,
           wh.end_time,
           wh.duration_min,
           wh.result,
           c.ci_name,
           c.ci_code,
           wh.requested_by AS performer,
           wh.impact_level,
           wh.created_at
    FROM work_history wh
    LEFT JOIN ci c ON c.ci_id = wh.ci_id
    WHERE wh.tenant_id = %s
      AND (%s IS NULL OR wh.start_time >= %s::timestamp)
      AND (%s IS NULL OR wh.start_time < %s::timestamp)
      AND (%s IS NULL OR wh.ci_id = %s::uuid)
    ORDER BY wh.start_time DESC
    LIMIT %s
)
UNION ALL
(
    SELECT '점검' AS history_type,
           mh.maint_type AS type,
           mh.summary,
           mh.detail,
           mh.start_time,
           mh.end_time,
           mh.duration_min,
           mh.result,
           c.ci_name,
           c.ci_code,
           mh.performer,
           NULL::text AS impact_level,
           mh.created_at
    FROM maintenance_history mh
    LEFT JOIN ci c ON c.ci_id = mh.ci_id
    WHERE mh.tenant_id = %s
      AND (%s IS NULL OR mh.start_time >= %s::timestamp)
      AND (%s IS NULL OR mh.start_time < %s::timestamp)
      AND (%s IS NULL OR mh.ci_id = %s::uuid)
    ORDER BY mh.start_time DESC
    LIMIT %s
)
ORDER BY start_time DESC
LIMIT %s
