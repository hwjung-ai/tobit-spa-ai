SELECT event_id, event_type, event_source, event_target,
       event_timestamp, severity, event_status, description
FROM event_log
WHERE ({where_clause})
ORDER BY event_timestamp DESC
LIMIT %s
