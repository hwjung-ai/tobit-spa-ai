SELECT key, COUNT(*) AS cnt
FROM (
    SELECT jsonb_object_keys({column}) AS key
    FROM ci_ext
    WHERE {column} IS NOT NULL
) sub
GROUP BY key
ORDER BY cnt DESC
