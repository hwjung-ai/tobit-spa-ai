
MATCH (sys:CI)
WHERE sys.tenant_id = $tenant_id AND sys.ci_code = $ci_code AND sys.ci_type = 'SYSTEM'
MATCH (sys)-[:COMPOSED_OF]->(c:CI)
WHERE c.tenant_id = $tenant_id
RETURN sys, c
LIMIT 300
