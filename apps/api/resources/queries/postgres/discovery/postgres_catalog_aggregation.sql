SELECT {column} AS value, COUNT(*) AS cnt
FROM ci
GROUP BY {column}
ORDER BY cnt DESC
LIMIT %s
