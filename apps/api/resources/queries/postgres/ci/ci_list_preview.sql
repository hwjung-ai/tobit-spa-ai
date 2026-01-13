SELECT ci.ci_id, ci.ci_code, ci.ci_name, ci.ci_type, ci.ci_subtype, ci.status, ci.owner, ci.location, ci.created_at
FROM ci
WHERE {where_clause}
ORDER BY ci.created_at DESC, ci.ci_code ASC
LIMIT %s
OFFSET %s
