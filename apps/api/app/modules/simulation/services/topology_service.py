from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import AppSettings, get_settings
from core.db_neo4j import get_neo4j_driver
from fastapi import HTTPException


@dataclass
class TopologyData:
    nodes: list[dict[str, Any]]
    links: list[dict[str, Any]]


def list_available_services(tenant_id: str) -> list[str]:
    settings = get_settings()
    driver = get_neo4j_driver(settings)
    try:
        with driver.session() as session:
            query = """
            MATCH (n:CI)
            WHERE n.tenant_id = $tenant_id
              AND (n.ci_type = "SERVICE" OR n.ci_subtype IN ["was", "web", "app"])
            RETURN DISTINCT n.ci_code AS service
            ORDER BY service
            """
            rows = session.run(query, {"tenant_id": tenant_id})
            return [r["service"] for r in rows if r.get("service")]
    finally:
        driver.close()


def get_topology_data(
    tenant_id: str,
    service: str,
    scenario_type: str = "what_if",
    assumptions: dict[str, Any] | None = None,
) -> TopologyData:
    assumptions = assumptions or {}
    base_topology = _get_real_topology(tenant_id, service, get_settings())
    if not base_topology["nodes"]:
        raise HTTPException(
            status_code=404,
            detail=f"No topology data found for service='{service}' tenant='{tenant_id}'. Please ensure Neo4j has topology data for this service.",
        )
    return _apply_simulation(base_topology, assumptions, scenario_type)


def _get_real_topology(tenant_id: str, service: str, settings: AppSettings) -> dict[str, Any]:
    driver = get_neo4j_driver(settings)
    try:
        with driver.session() as session:
            query = """
            MATCH (s:CI {ci_code: $service, tenant_id: $tenant_id})
            OPTIONAL MATCH path = (s)<-[:DEPENDS_ON|RUNS_ON|DEPLOYED_ON|COMPOSED_OF*0..5]-(n:CI)
            WITH collect(DISTINCT n) + [s] AS raw_nodes
            UNWIND raw_nodes AS node
            WITH collect(DISTINCT node) AS all_nodes
            UNWIND all_nodes AS n1
            OPTIONAL MATCH (n1)-[r:DEPENDS_ON|RUNS_ON|DEPLOYED_ON|COMPOSED_OF]->(n2:CI)
            WHERE n2 IN all_nodes
            RETURN
              collect(DISTINCT {
                id: toString(n1.ci_id),
                name: coalesce(n1.ci_code, toString(n1.ci_id)),
                type: toLower(coalesce(n1.ci_subtype, n1.ci_type, "service")),
                ci_type: n1.ci_type,
                ci_subtype: n1.ci_subtype,
                baseline_load: toFloat(coalesce(n1.baseline_load, 50.0))
              }) AS nodes,
              collect(DISTINCT CASE
                WHEN r IS NULL THEN NULL
                ELSE {
                  source: toString(startNode(r).ci_id),
                  target: toString(endNode(r).ci_id),
                  type: toLower(type(r)),
                  baseline_traffic: toFloat(coalesce(r.baseline_traffic, 100.0))
                }
              END) AS links
            """
            record = session.run(query, {"service": service, "tenant_id": tenant_id}).single()
            if not record:
                return {"service": service, "nodes": [], "links": []}
            nodes = [n for n in (record["nodes"] or []) if n]
            links = [link for link in (record["links"] or []) if link]
            return {"service": service, "nodes": nodes, "links": links}
    finally:
        driver.close()


def _apply_simulation(base_topology: dict[str, Any], assumptions: dict[str, Any], scenario_type: str) -> TopologyData:
    _ = scenario_type
    traffic_delta = float(assumptions.get("traffic_change_pct", 0.0)) / 100.0
    cpu_delta = float(assumptions.get("cpu_change_pct", 0.0)) / 100.0
    memory_delta = float(assumptions.get("memory_change_pct", 0.0)) / 100.0

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    for node_data in base_topology.get("nodes", []):
        baseline_load = float(node_data.get("baseline_load", 50.0))
        node_type = str(node_data.get("type", "service")).lower()

        # ci_subtype mapping: was, web, app → service; db → db; server → server; os → server; network → network
        if node_type in ("was", "web", "app", "service"):
            simulated_load = baseline_load * (1 + traffic_delta + cpu_delta * 0.5)
        elif node_type == "server":
            simulated_load = baseline_load * (1 + cpu_delta + memory_delta * 0.3)
        elif node_type == "db":
            simulated_load = baseline_load * (1 + traffic_delta * 0.8 + cpu_delta * 0.4)
        elif node_type == "network":
            simulated_load = baseline_load * (1 + traffic_delta)
        else:
            simulated_load = baseline_load * (1 + traffic_delta * 0.5 + cpu_delta * 0.2)

        if simulated_load >= 90:
            status = "critical"
        elif simulated_load >= 70:
            status = "warning"
        else:
            status = "healthy"

        change_pct = ((simulated_load - baseline_load) / baseline_load) * 100 if baseline_load > 0 else 0.0
        nodes.append(
            {
                "id": node_data["id"],
                "name": node_data["name"],
                "type": node_type,
                "status": status,
                "baseline_load": round(baseline_load, 2),
                "simulated_load": round(simulated_load, 2),
                "load_change_pct": round(change_pct, 2),
            }
        )

    for link_data in base_topology.get("links", []):
        baseline_traffic = float(link_data.get("baseline_traffic", 100.0))
        link_type = str(link_data.get("type", "depends_on")).lower()
        if link_type == "traffic":
            simulated_traffic = baseline_traffic * (1 + traffic_delta)
        else:
            simulated_traffic = baseline_traffic * (1 + traffic_delta * 0.5)
        change_pct = ((simulated_traffic - baseline_traffic) / baseline_traffic) * 100 if baseline_traffic > 0 else 0.0
        links.append(
            {
                "source": link_data["source"],
                "target": link_data["target"],
                "type": link_type,
                "baseline_traffic": round(baseline_traffic, 2),
                "simulated_traffic": round(simulated_traffic, 2),
                "traffic_change_pct": round(change_pct, 2),
            }
        )

    return TopologyData(nodes=nodes, links=links)
