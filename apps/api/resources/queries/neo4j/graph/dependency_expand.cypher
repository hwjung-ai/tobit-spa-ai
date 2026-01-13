
MATCH (n:CI)
WHERE n.tenant_id = $tenant_id AND n.ci_code = $ci_code
MATCH path = (n)-[r*1..{depth}]-(m:CI)
WHERE m.tenant_id = $tenant_id
RETURN n, relationships(path) AS r, m
LIMIT 300
