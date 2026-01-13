MATCH p = (source:CI {ci_code: $source_ci_code, tenant_id: $tenant_id})-[:DEPENDS_ON*1..$depth]->(target:CI {ci_code: $target_ci_code, tenant_id: $tenant_id})
RETURN p
LIMIT 25
