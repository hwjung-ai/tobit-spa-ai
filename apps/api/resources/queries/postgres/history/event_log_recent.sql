SELECT {columns} FROM event_log
LEFT JOIN ci ON ci.ci_id = event_log.ci_id
WHERE {where_clause}
ORDER BY {time_col} DESC LIMIT %s
