from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Literal

from neo4j import Driver

from app.modules.ops.services.ci import policy
from app.modules.ops.services.ci.view_registry import Direction, VIEW_REGISTRY

from apps.api.scripts.seed.utils import get_neo4j_driver
from app.shared.config_loader import load_text

DEFAULT_LIMITS = {"max_nodes": 200, "max_edges": 400, "max_paths": 25}

_QUERY_BASE = "queries/neo4j/graph"


def _load_query(name: str) -> str:
    query = load_text(f"{_QUERY_BASE}/{name}")
    if not query:
        raise ValueError(f"Graph query '{name}' not found")
    return query


def _pattern_for_direction(direction: Direction, depth: int) -> str:
    if direction == Direction.OUT:
        return f"-[rels*1..{depth}]->"
    if direction == Direction.IN:
        return f"<-[rels*1..{depth}]-"
    return f"-[rels*1..{depth}]-"


def _collect_path_entities(path) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[str]]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids: List[str] = []
    rel_types: List[str] = []
    for node in getattr(path, "nodes", []):
        node_id = node.get("ci_id")
        if not node_id:
            continue
        nodes.append(
            {
                "id": node_id,
                "code": node.get("ci_code"),
                "ci_type": node.get("ci_type"),
                "ci_subtype": node.get("ci_subtype"),
                "ci_category": node.get("ci_category"),
            }
        )
        if node_id not in node_ids:
            node_ids.append(node_id)
    for rel in getattr(path, "relationships", []):
        rel_types.append(rel.type)
        edges.append(
            {
                "source": rel.start_node.get("ci_id"),
                "target": rel.end_node.get("ci_id"),
                "type": rel.type,
            }
        )
    return nodes, edges, node_ids, rel_types


def _gather_unique_entities(paths: List[Any], max_nodes: int, max_edges: int) -> Dict[str, Any]:
    unique_nodes: Dict[str, Dict[str, Any]] = {}
    unique_edges: List[Dict[str, Any]] = []
    rel_type_counter = Counter()
    for path in paths:
        nodes, edges, node_ids, rel_types = _collect_path_entities(path)
        for node in nodes:
            unique_nodes[node["id"]] = node
        for edge in edges:
            unique_edges.append(edge)
        rel_type_counter.update(rel_types)
    truncated = False
    node_list = list(unique_nodes.values())
    if len(node_list) > max_nodes:
        truncated = True
        node_list = node_list[:max_nodes]
    if len(unique_edges) > max_edges:
        truncated = True
        unique_edges = unique_edges[:max_edges]
    return {
        "nodes": node_list,
        "edges": unique_edges,
        "ids": list(unique_nodes.keys()),
        "summary": {
            "rel_type_counts": dict(rel_type_counter),
            "node_count": len(node_list),
            "edge_count": len(unique_edges),
        },
        "truncated": truncated,
    }


def graph_expand(
    tenant_id: str,
    root_ci_id: str,
    view: str,
    depth: int | None = None,
    limits: Dict[str, int] | None = None,
) -> Dict[str, Any]:
    policy_decision = policy.build_policy_trace(view, requested_depth=depth)
    allowed_rel = policy_decision["allowed_rel_types"]
    if not allowed_rel:
        return {
            "nodes": [],
            "edges": [],
            "ids": [],
            "summary": {"rel_type_counts": {}, "node_count": 0, "edge_count": 0},
            "truncated": False,
        }
    view_policy = VIEW_REGISTRY.get(view.upper())
    if not view_policy:
        raise ValueError(f"Unknown view '{view}'")
    used_depth = policy_decision["clamped_depth"]
    patterns = _pattern_for_direction(view_policy.direction_default, used_depth)
    applied_limits = DEFAULT_LIMITS.copy()
    if limits:
        applied_limits.update({k: max(1, v) for k, v in limits.items() if v is not None})
    cypher_template = _load_query("graph_expand.cypher")
    cypher = cypher_template.format(patterns=patterns)
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            results = session.execute_read(
                lambda tx: tx.run(
                    cypher,
                    {
                        "root_ci_id": root_ci_id,
                        "tenant_id": tenant_id,
                        "allowed_rel": allowed_rel,
                        "max_paths": applied_limits["max_paths"],
                    },
                ).data()
            )
    finally:
        driver.close()
    paths = [record["path"] for record in results if "path" in record]
    nodes_payload = _gather_unique_entities(paths, applied_limits["max_nodes"], applied_limits["max_edges"])
    nodes_payload["meta"] = {
        "depth": used_depth,
        "limits": applied_limits,
        "rel_types": allowed_rel,
    }
    return nodes_payload


def graph_path(
    tenant_id: str,
    source_ci_id: str,
    target_ci_id: str,
    max_hops: int,
) -> Dict[str, Any]:
    depth = policy.clamp_depth("PATH", max_hops)
    allowed_rel = policy.get_allowed_rel_types("PATH")
    if not allowed_rel:
        return {"nodes": [], "edges": [], "hop_count": 0, "truncated": False}
    view_policy = VIEW_REGISTRY.get("PATH")
    if not view_policy:
        raise ValueError("PATH view is not defined")
    direction_pattern = _pattern_for_direction(view_policy.direction_default, depth)
    cypher_template = _load_query("graph_path.cypher")
    cypher = cypher_template.format(direction_pattern=direction_pattern)
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.execute_read(
                lambda tx: tx.run(
                    cypher,
                    {
                        "source_ci_id": source_ci_id,
                        "target_ci_id": target_ci_id,
                        "tenant_id": tenant_id,
                        "allowed_rel": allowed_rel,
                        "max_hops": depth,
                    },
                ).single()
            )
    finally:
        driver.close()
    if not result:
        return {"nodes": [], "edges": [], "hop_count": 0, "truncated": False}
    path = result["path"]
    nodes, edges, _, _ = _collect_path_entities(path)
    return {
        "nodes": nodes,
        "edges": edges,
        "hop_count": len(edges),
        "truncated": len(edges) > depth,
        "meta": {"rel_types": allowed_rel, "depth": depth},
    }
