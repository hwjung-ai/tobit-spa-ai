MATCH (root:CI {ci_id: $root_ci_id, tenant_id: $tenant_id})
MATCH path=(root){patterns}()
WHERE all(rel IN relationships(path) WHERE type(rel) IN $allowed_rel)
  AND all(node IN nodes(path) WHERE node.tenant_id = $tenant_id)
RETURN path
LIMIT $max_paths
