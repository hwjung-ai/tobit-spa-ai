WITH RECURSIVE graph_path AS (
  SELECT source_ci_id, target_ci_id, relation_type, depth, 1 as level
  FROM ci_graph
  WHERE source_ci_id = %s AND depth <= %s
  UNION ALL
  SELECT g.source_ci_id, g.target_ci_id, g.relation_type, g.depth, gp.level + 1
  FROM ci_graph g
  INNER JOIN graph_path gp ON g.source_ci_id = gp.target_ci_id
  WHERE gp.level < %s
)
SELECT DISTINCT source_ci_id, target_ci_id, relation_type, depth
FROM graph_path
ORDER BY depth, relation_type
