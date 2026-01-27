from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from core.logging import get_logger
from schemas.tool_contracts import GraphExpandResult, GraphPathResult

from app.modules.ops.services.ci import policy
from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
)
from app.modules.ops.services.ci.tools.query_registry import (
    load_query_asset_with_source,
    create_connection_for_query,
)
from app.modules.ops.services.ci.view_registry import get_view_policy, Direction
from app.shared.config_loader import load_text
from app.modules.asset_registry.loader import load_policy_asset

logger = get_logger(__name__)

# Hardcoded fallback limits - will be loaded from DB via _get_limits()
DEFAULT_LIMITS = {"max_nodes": 200, "max_edges": 400, "max_paths": 25}

# Cache for tool limits loaded from DB
_LIMITS_CACHE: Dict[str, Any] | None = None

_QUERY_BASE = "queries/neo4j/graph"


def _get_limits() -> Dict[str, Any]:
    """
    Load Graph tool limits from policy asset.
    Falls back to hardcoded constants if asset not found.

    Returns:
        Dictionary with limit configuration:
        {
            "max_nodes": 200,
            "max_edges": 400,
            "max_paths": 25
        }
    """
    global _LIMITS_CACHE
    if _LIMITS_CACHE is not None:
        return _LIMITS_CACHE

    try:
        policy = load_policy_asset("tool_limits")
        if policy:
            content = policy.get("content", {})
            graph_limits = content.get("graph", {})
            if graph_limits:
                _LIMITS_CACHE = graph_limits
                logger.info(f"Loaded Graph tool limits from DB: {graph_limits}")
                return _LIMITS_CACHE
    except Exception as e:
        logger.warning(f"Failed to load tool_limits policy for Graph: {e}")

    # Fallback to hardcoded limits
    _LIMITS_CACHE = DEFAULT_LIMITS.copy()
    logger.info("Using hardcoded Graph tool limits (fallback)")
    return _LIMITS_CACHE


def _load_query(name: str) -> str:
    """
    Load a Cypher query for graph operations.

    Tries to load from QueryAssetRegistry first, then falls back to file-based loading.
    """
    # Try QueryAssetRegistry first (tool_type='graph', operation derived from name)
    operation_map = {
        "graph_expand.cypher": "expand",
        "graph_path.cypher": "path",
        "dependency_expand.cypher": "dependency_expand",
        "dependency_paths.cypher": "dependency_paths",
        "component_composition.cypher": "component_composition",
    }

    operation = operation_map.get(name, name.replace(".cypher", ""))

    try:
        from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry

        registry = get_query_asset_registry()
        query_asset = registry.get_query_asset("graph", operation)
        if query_asset and query_asset.get("cypher"):
            return query_asset["cypher"]
    except Exception:
        # Fallback to file-based loading
        pass

    # File-based fallback
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


def _collect_path_entities(
    path,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[str]]:
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


def _gather_unique_entities(
    paths: List[Any], max_nodes: int, max_edges: int
) -> Dict[str, Any]:
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
) -> GraphExpandResult:
    """Expand graph from root CI node using ConnectionFactory."""
    policy_decision = policy.build_policy_trace(view, requested_depth=depth)
    allowed_rel = policy_decision["allowed_rel_types"]
    if not allowed_rel:
        return GraphExpandResult(
            nodes=[],
            edges=[],
            ids=[],
            summary={"rel_type_counts": {}, "node_count": 0, "edge_count": 0},
            truncated=False,
            meta={},
        )
    view_policy = get_view_policy(view.upper())
    if not view_policy:
        raise ValueError(f"Unknown view '{view}'")
    used_depth = policy_decision["clamped_depth"]
    patterns = _pattern_for_direction(view_policy.direction_default, used_depth)
    # Load limits from DB, fallback to hardcoded if not available
    applied_limits = _get_limits().copy()
    if limits:
        applied_limits.update(
            {k: max(1, v) for k, v in limits.items() if v is not None}
        )
    cypher_template = _load_query("graph_expand.cypher")
    cypher = cypher_template.format(patterns=patterns)

    # Use ConnectionFactory instead of get_neo4j_driver
    conn = create_connection_for_query("graph", "expand")
    try:
        results = conn.execute(cypher, {
            "root_ci_id": root_ci_id,
            "tenant_id": tenant_id,
            "allowed_rel": allowed_rel,
            "max_paths": applied_limits["max_paths"],
        })
    finally:
        conn.close()

    # Extract paths from results - Neo4jConnection returns list of dicts
    # The query returns paths, so we need to handle them appropriately
    paths = []
    if results:
        for record in results:
            # Neo4j paths are returned as Path objects in the record
            if "path" in record:
                paths.append(record["path"])

    nodes_payload = _gather_unique_entities(
        paths, applied_limits["max_nodes"], applied_limits["max_edges"]
    )
    meta = {
        "depth": used_depth,
        "limits": applied_limits,
        "rel_types": allowed_rel,
    }
    return GraphExpandResult(
        nodes=nodes_payload["nodes"],
        edges=nodes_payload["edges"],
        ids=nodes_payload["ids"],
        summary=nodes_payload["summary"],
        truncated=nodes_payload["truncated"],
        meta=meta,
    )


def graph_path(
    tenant_id: str,
    source_ci_id: str,
    target_ci_id: str,
    max_hops: int,
) -> GraphPathResult:
    """Find path between two CI nodes using ConnectionFactory."""
    depth = policy.clamp_depth("PATH", max_hops)
    allowed_rel = policy.get_allowed_rel_types("PATH")
    if not allowed_rel:
        return GraphPathResult(
            nodes=[],
            edges=[],
            hop_count=0,
            truncated=False,
            meta={},
        )
    view_policy = get_view_policy("PATH")
    if not view_policy:
        raise ValueError("PATH view is not defined")
    direction_pattern = _pattern_for_direction(view_policy.direction_default, depth)
    cypher_template = _load_query("graph_path.cypher")
    cypher = cypher_template.format(direction_pattern=direction_pattern)

    # Use ConnectionFactory instead of get_neo4j_driver
    conn = create_connection_for_query("graph", "path")
    try:
        results = conn.execute(cypher, {
            "source_ci_id": source_ci_id,
            "target_ci_id": target_ci_id,
            "tenant_id": tenant_id,
            "allowed_rel": allowed_rel,
            "max_hops": depth,
        })
    finally:
        conn.close()

    if not results or len(results) == 0:
        return GraphPathResult(
            nodes=[],
            edges=[],
            hop_count=0,
            truncated=False,
            meta={},
        )
    # Get the first result (single path)
    result = results[0]
    path = result.get("path")
    if not path:
        return GraphPathResult(
            nodes=[],
            edges=[],
            hop_count=0,
            truncated=False,
            meta={},
        )
    nodes, edges, _, _ = _collect_path_entities(path)
    return GraphPathResult(
        nodes=nodes,
        edges=edges,
        hop_count=len(edges),
        truncated=len(edges) > depth,
        meta={"rel_types": allowed_rel, "depth": depth},
    )


# ==============================================================================
# Tool Interface Implementation
# ==============================================================================


class GraphTool(BaseTool):
    """
    Tool for Graph operations.

    Provides methods to explore relationship graphs and find paths between
    configuration items using Neo4j backend.
    """

    @property
    def tool_type(self) -> str:
        """Return the Graph tool type."""
        return "graph"

    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """
        Determine if this tool should execute for the given operation.

        Graph tool handles:
        - Built-in operations: 'expand', 'path'
        - Any operation registered in QueryAssetRegistry with tool_type='graph'

        This allows new operations to be added just by creating Query Assets,
        without any Python code changes.

        Args:
            context: Execution context
            params: Tool parameters

        Returns:
            True if this is a Graph operation, False otherwise
        """
        operation = params.get("operation", "")

        # Built-in operations with custom logic
        builtin_operations = {"expand", "path"}
        if operation in builtin_operations:
            return True

        # Check if operation exists in QueryAssetRegistry for graph tool
        try:
            from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry
            registry = get_query_asset_registry()
            query_asset = registry.get_query_asset("graph", operation)
            return query_asset is not None
        except Exception:
            return False

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a Graph operation.

        Dispatches to the appropriate function based on the 'operation' parameter.

        Parameters:
            operation (str): The operation to perform ('expand' or 'path')
            ci_id (str): Starting CI ID for expand, or source for path
            target_ci_id (str, optional): Target CI ID for path operation
            view (str): Graph view name (e.g., 'COMPOSITION', 'DEPENDENCY')
            depth (int, optional): Traversal depth
            max_hops (int, optional): Maximum hops for path finding
            limits (dict, optional): Node/edge limits

        Returns:
            ToolResult with success status and graph data
        """
        try:
            operation = params.get("operation", "")
            tenant_id = context.tenant_id

            if operation == "expand":
                result = graph_expand(
                    tenant_id=tenant_id,
                    root_ci_id=params["ci_id"],
                    view=params.get("view", "COMPOSITION"),
                    depth=params.get("depth"),
                    limits=params.get("limits"),
                )
            elif operation == "path":
                result = graph_path(
                    tenant_id=tenant_id,
                    source_ci_id=params["ci_id"],
                    target_ci_id=params["target_ci_id"],
                    max_hops=params.get("max_hops", 10),
                )
            else:
                # Generic execution via QueryAssetRegistry
                # This allows any operation to be added just by creating a Query Asset!
                result = await self._execute_generic(operation, params)

            return ToolResult(success=True, data=result)

        except ValueError as e:
            return await self.format_error(context, e, params)
        except Exception as e:
            return await self.format_error(context, e, params)

    async def _execute_generic(self, operation: str, params: Dict[str, Any]) -> dict:
        """
        Execute a generic operation dynamically via QueryAssetRegistry.

        This allows new operations to be added just by creating Query Assets,
        without any Python code changes.

        Args:
            operation: The operation name (must exist in QueryAssetRegistry)
            params: Parameters to pass to the query

        Returns:
            The query result

        Raises:
            ValueError: If operation not found in QueryAssetRegistry
        """
        from app.modules.ops.services.ci.tools.query_registry import get_query_asset_registry

        # Get the Query Asset
        registry = get_query_asset_registry()
        query_asset = registry.get_query_asset("graph", operation)

        if not query_asset:
            raise ValueError(f"Unknown Graph operation: {operation}")

        # Execute using ConnectionFactory
        source_type = query_asset.get("query_metadata", {}).get("source_type", "")
        conn = create_connection_for_query("graph", operation)
        try:
            # Determine query type and execute
            if source_type == "postgresql" and query_asset.get("sql"):
                # SQL query
                sql = query_asset["sql"]
                # Merge query_params and filters for SQL template processor
                execute_params = {
                    "query_params": params.get("query_params", {}),
                    "filters": params.get("filters", []),
                    "limit": params.get("limit"),
                    "offset": params.get("offset"),
                    "order_by": params.get("order_by"),
                    "order_dir": params.get("order_dir"),
                }
                result = conn.execute(sql, execute_params)
            elif source_type == "neo4j" and query_asset.get("cypher"):
                # Cypher query
                cypher = query_asset["cypher"]
                query_params = params.get("query_params", {})
                result = conn.execute(cypher, query_params)
            elif source_type == "rest_api" and query_asset.get("query_http"):
                # REST API query
                http_config = query_asset["query_http"]
                # Build request from params
                request_params = self._build_http_params(http_config, params)
                result = conn.execute(request_params)
            else:
                raise ValueError(f"Unsupported query configuration for operation: {operation}")

            # Normalize result
            if isinstance(result, list):
                return {"data": result, "count": len(result)}
            elif isinstance(result, dict):
                return result
            else:
                return {"data": result}
        finally:
            conn.close()

    def _build_http_params(self, http_config: dict, params: Dict[str, Any]) -> dict:
        """Build HTTP request parameters from config and input params."""
        method = http_config.get("method", "GET")
        path_template = http_config.get("path", "")
        headers = http_config.get("headers", {})

        # Replace path parameters
        path = path_template
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in path:
                path = path.replace(placeholder, str(value))

        return {
            "method": method,
            "path": path,
            "headers": headers,
            "params": params.get("query_params", {}),
        }


# Create and register the Graph tool
_graph_tool = GraphTool()
