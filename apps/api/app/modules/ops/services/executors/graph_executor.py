from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable

from app.shared.config_loader import load_text
from app.modules.asset_registry.loader import load_query_asset
from core.db_neo4j import get_neo4j_driver
from schemas import (
    AnswerBlock,
    GraphBlock,
    GraphEdge,
    GraphNode,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
)
from schemas.answer_blocks import GraphPosition
from schemas.tool_contracts import ExecutorResult, ToolCall

from ..resolvers import resolve_ci, resolve_time_range


def _load_query_sql(scope: str, name: str) -> str | None:
    """Load query SQL with DB priority fallback to file."""
    asset = load_query_asset(scope, name)
    if asset:
        return asset.get("sql")
    return None


def run_graph(question: str, tenant_id: str = "t1") -> ExecutorResult:
    start_time = perf_counter()
    tool_calls: list[ToolCall] = []
    references_list: list[dict] = []
    used_tools = ["neo4j", "postgres"]

    base_graph_query_template = _load_query_sql("graph", "dependency_expand") or load_text("queries/neo4j/graph/dependency_expand.cypher")
    component_query = _load_query_sql("graph", "component_composition") or load_text("queries/neo4j/graph/component_composition.cypher")

    if not base_graph_query_template or not component_query:
        error_block = MarkdownBlock(
            type="markdown",
            title="Error",
            content="### 쿼리 파일 로드 실패\n- Graph 관련 Cypher 파일을 찾을 수 없거나 읽는 데 실패했습니다.",
        )
        return ExecutorResult(
            blocks=[error_block.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references_list,
            summary={"status": "error", "reason": "query_load_failed"},
        )

    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        markdown = MarkdownBlock(
            type="markdown",
            title="Graph 결과 없음",
            content="CI를 찾을 수 없습니다.",
        )
        return ExecutorResult(
            blocks=[markdown.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references_list,
            summary={"status": "no_ci"},
        )
    ci = ci_hits[0]

    time_range = resolve_time_range(question, datetime.now(timezone.utc))
    depth = 3 if any(keyword in question for keyword in ("영향", "의존", "경로")) else 2
    include_components = any(keyword in question for keyword in ("구성", "구성요소"))
    driver = get_neo4j_driver()
    query_start = perf_counter()
    try:
        records = _run_graph_query(driver, base_graph_query_template, tenant_id, ci.ci_code, depth)
        comp_records = _run_component_query(driver, component_query, tenant_id, ci.ci_code) if include_components else []
    finally:
        driver.close()
    query_elapsed_ms = int((perf_counter() - query_start) * 1000)

    # Record graph.expand tool call
    tool_calls.append(
        ToolCall(
            tool="graph.expand",
            elapsed_ms=query_elapsed_ms,
            input_params={
                "ci_code": ci.ci_code,
                "depth": depth,
                "include_components": include_components,
            },
            output_summary={
                "nodes": len(records) + len(comp_records),
                "edges": len(records),  # Simplified
            },
        )
    )

    nodes, edges = _build_graph(records, comp_records)
    if not nodes:
        nodes = [
            GraphNode(
                id=ci.ci_code,
                data={"label": f"{ci.ci_code}\n{ci.ci_name or ''}\n({ci.ci_subtype or ''})"},
                position=GraphPosition(x=0.0, y=0.0),
            )
        ]

    top_relations = _format_relation_summary(edges)
    markdown = MarkdownBlock(
        type="markdown",
        title="Graph overview",
        content=(
            f"CI: {ci.ci_code} ({ci.ci_name})\n"
            f"Depth: {depth}\n"
            f"Time range: {time_range.start.isoformat()} ~ {time_range.end.isoformat()}\n"
            f"Nodes: {len(nodes)}, Edges: {len(edges)}\n"
            f"Top relations: {top_relations}"
        ),
    )
    references_block = _build_references(
        base_graph_query_template, component_query, tenant_id, ci.ci_code, depth, include_components
    )

    # Extract references from references_block
    if isinstance(references_block, ReferencesBlock):
        for item in references_block.items:
            references_list.append(item.dict())

    graph_block = GraphBlock(type="graph", title="Dependency graph", nodes=nodes, edges=edges)
    blocks = [markdown, graph_block, references_block]

    # Convert blocks to dicts
    blocks_dict = [block.dict() if hasattr(block, "dict") else block for block in blocks]

    elapsed_ms = int((perf_counter() - start_time) * 1000)
    return ExecutorResult(
        blocks=blocks_dict,
        used_tools=used_tools,
        tool_calls=tool_calls,
        references=references_list,
        summary={
            "status": "success",
            "ci_code": ci.ci_code,
            "nodes": len(nodes),
            "edges": len(edges),
            "depth": depth,
        },
    )


def _run_graph_query(driver, query_template: str, tenant_id: str, ci_code: str, depth: int):
    query = query_template.format(depth=depth)
    with driver.session() as session:
        result = session.run(query, tenant_id=tenant_id, ci_code=ci_code, depth=depth)
        return list(result)


def _run_component_query(driver, query: str, tenant_id: str, ci_code: str):
    with driver.session() as session:
        result = session.run(query, tenant_id=tenant_id, ci_code=ci_code)
        return list(result)


def _build_graph(records, comp_records):
    node_map = {}
    edges = []
    for record in records:
        _add_node(record["n"], node_map)
        _add_node(record["m"], node_map)
        for rel in record["r"]:
            start_node = getattr(rel, "start_node", None)
            end_node = getattr(rel, "end_node", None)
            if not start_node or not end_node:
                continue
            source = start_node.get("ci_code")
            target = end_node.get("ci_code")
            if not source or not target:
                continue
            _add_node(start_node, node_map)
            _add_node(end_node, node_map)
            edges.append(_create_edge(source, target, rel.type))
    for record in comp_records:
        _add_node(record["sys"], node_map)
        _add_node(record["c"], node_map)
        edges.append(_create_edge(record["sys"]["ci_code"], record["c"]["ci_code"], "COMPOSED_OF"))
    if records:
        root = records[0]["n"]["ci_code"]
    elif comp_records:
        root = comp_records[0]["sys"]["ci_code"]
    else:
        root = None
    levels = _assign_levels(node_map, edges, root)
    return _layout_graph(node_map, edges, levels)


def _add_node(node, node_map):
    ci_code = node["ci_code"]
    if ci_code in node_map:
        return
    node_map[ci_code] = {
        "ci_name": node.get("ci_name"),
        "ci_subtype": node.get("ci_subtype"),
    }


def _create_edge(source: str, target: str, label: str | None):
    return GraphEdge(id=f"{source}-{label}-{target}", source=source, target=target, label=label)


def _assign_levels(node_map, edges, root_code):
    if not root_code:
        return {}
    adj = defaultdict(set)
    for edge in edges:
        adj[edge.source].add(edge.target)
        adj[edge.target].add(edge.source)
    levels = {root_code: 0}
    queue = deque([root_code])
    while queue:
        current = queue.popleft()
        level = levels[current]
        for neighbor in adj[current]:
            if neighbor in levels:
                continue
            levels[neighbor] = level + 1
            queue.append(neighbor)
    return levels


def _layout_graph(node_map, edges, levels):
    for node_id in node_map:
        levels.setdefault(node_id, 0)
    level_order = defaultdict(list)
    for node_id, level in levels.items():
        level_order[level].append(node_id)
    nodes = []
    for level in sorted(level_order):
        for idx, node_id in enumerate(level_order[level]):
            pos = GraphPosition(x=float(level) * 280.0, y=float(idx) * 90.0)
            data = node_map[node_id]
            nodes.append(
                GraphNode(
                    id=node_id,
                    data={"label": f"{node_id}\n{data['ci_name'] or ''}\n({data['ci_subtype'] or ''})"},
                    position=pos,
                )
            )
    return nodes, edges


def _format_relation_summary(edges: Iterable[GraphEdge]) -> str:
    counts = Counter(edge.label for edge in edges if edge.label)
    if not counts:
        return "none"
    return ", ".join(f"{label}:{count}" for label, count in counts.most_common(3))


def _build_references(
    base_graph_query_template: str,
    component_query: str,
    tenant_id: str,
    ci_code: str,
    depth: int,
    include_components: bool,
):
    items = []
    query_text = base_graph_query_template.format(depth=depth).strip()
    items.append(
        ReferenceItem(
            kind="cypher",
            title="graph query",
            payload={
                "cypher": query_text,
                "params": {"tenant_id": tenant_id, "ci_code": ci_code, "depth": depth},
            },
        )
    )
    if include_components:
        items.append(
            ReferenceItem(
                kind="cypher",
                title="component query",
                payload={"cypher": component_query.strip(), "params": {"tenant_id": tenant_id, "ci_code": ci_code}},
            )
        )
    return ReferencesBlock(type="references", title="Graph queries", items=items)
