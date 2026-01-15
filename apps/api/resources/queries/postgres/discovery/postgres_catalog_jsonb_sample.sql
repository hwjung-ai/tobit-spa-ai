SELECT DISTINCT jsonb_extract_path_text({column}, %s) AS value
FROM ci_ext
WHERE {column} ? %s
LIMIT %s
