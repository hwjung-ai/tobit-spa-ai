MATCH (source:CI {ci_id: $source_ci_id, tenant_id: $tenant_id})
MATCH (target:CI {ci_id: $target_ci_id, tenant_id: $tenant_id})
MATCH path=shortestPath((source){direction_pattern}(target))
WHERE all(rel IN relationships(path) WHERE type(rel) IN $allowed_rel)
  AND length(path) <= $max_hops
  AND all(node IN nodes(path) WHERE node.tenant_id = $tenant_id)
RETURN path
LIMIT 1
