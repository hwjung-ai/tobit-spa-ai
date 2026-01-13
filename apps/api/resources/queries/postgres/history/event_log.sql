
SELECT el.time, el.severity, el.event_type, el.source, el.title, c.ci_code, c.ci_name
FROM event_log AS el
LEFT JOIN ci AS c ON c.ci_id = el.ci_id
WHERE el.tenant_id = %s AND el.ci_id = %s AND el.time >= %s AND el.time < %s
ORDER BY el.severity DESC, el.time DESC
LIMIT 50
