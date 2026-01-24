from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

from neo4j import Driver

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed.utils import get_neo4j_driver, get_postgres_conn

SYSTEM_DEPENDENCIES = {
    "erp": ["cmdb", "apm"],
    "mes": ["erp", "scada"],
    "scada": ["mes"],
    "mon": ["scada", "apm"],
    "analytics": ["erp", "mes"],
    "cmdb": ["mon", "apm"],
    "apm": ["cmdb", "mon"],
    "secops": ["mon", "apm"],
}


def _load_ci_rows() -> list[dict]:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ci.ci_id, ci.tenant_id, ci.ci_code, ci.ci_type, ci.ci_subtype, ci.ci_category, ci_ext.tags "
                "FROM ci LEFT JOIN ci_ext ON ci.ci_id = ci_ext.ci_id"
            )
            rows = []
            for (
                ci_id,
                tenant_id,
                ci_code,
                ci_type,
                ci_subtype,
                ci_category,
                tags,
            ) in cur.fetchall():
                if not tags:
                    parsed_tags = {}
                elif isinstance(tags, (str, bytes, bytearray)):
                    parsed_tags = json.loads(tags)
                else:
                    parsed_tags = tags
                rows.append(
                    {
                        "ci_id": str(ci_id),
                        "tenant_id": tenant_id,
                        "ci_code": ci_code,
                        "ci_type": ci_type,
                        "ci_subtype": ci_subtype,
                        "ci_category": ci_category,
                        "tags": parsed_tags,
                    }
                )
        return rows


def _system_code(ci_code: str) -> str | None:
    parts = ci_code.split("-")
    if len(parts) >= 2:
        return parts[1]
    return None


def _merge_nodes(driver: Driver, records: Iterable[dict]) -> None:
    def _merge(tx, params):
        tx.run(
            "MERGE (n:CI {ci_id: $ci_id})"
            " SET n.ci_code = $ci_code, n.ci_type = $ci_type, n.ci_subtype = $ci_subtype,"
            " n.ci_category = $ci_category, n.tenant_id = $tenant_id",
            **params,
        )

    with driver.session() as session:
        session.execute_write(lambda tx: tx.run("MATCH (n:CI) DETACH DELETE n"))
        for record in records:
            params = {
                "ci_id": record["ci_id"],
                "ci_code": record["ci_code"],
                "ci_type": record["ci_type"],
                "ci_subtype": record["ci_subtype"],
                "ci_category": record["ci_category"],
                "tenant_id": record["tenant_id"],
            }
            session.execute_write(_merge, params)


def _create_relationships(driver: Driver, records: list[dict]) -> None:
    code_index = {record["ci_code"]: record for record in records}
    system_nodes = {
        record["ci_code"].split("-")[1]: record["ci_code"]
        for record in records
        if record["ci_type"] == "SYSTEM"
    }

    with driver.session() as session:
        for record in records:
            if record["ci_type"] != "SYSTEM":
                system_code = _system_code(record["ci_code"])
                system_ci = system_nodes.get(system_code) if system_code else None
                if system_ci:
                    session.execute_write(
                        lambda tx, child=record["ci_code"], parent=system_ci: tx.run(
                            "MATCH (p:CI {ci_code: $parent}), (c:CI {ci_code: $child}) "
                            "MERGE (p)-[:COMPOSED_OF]->(c)",
                            parent=parent,
                            child=child,
                        )
                    )

            tags = record.get("tags", {})
            host_server = tags.get("host_server")
            if host_server:
                session.execute_write(
                    lambda tx, child=record["ci_code"], server=host_server: tx.run(
                        "MATCH (s:CI {ci_code: $server}), (c:CI {ci_code: $child}) "
                        "MERGE (c)-[:DEPLOYED_ON]->(s)",
                        server=server,
                        child=child,
                    )
                )

            runs_on = tags.get("runs_on")
            if runs_on:
                rel_type = {
                    "was": "RUNS_ON",
                    "db": "RUNS_ON",
                    "web": "RUNS_ON",
                    "app": "RUNS_ON",
                    "os": None,
                }.get(record["ci_subtype"], "RUNS_ON")
                if rel_type:
                    session.execute_write(
                        lambda tx, source=record["ci_code"], target=runs_on: tx.run(
                            "MATCH (src:CI {ci_code: $source}), (target:CI {ci_code: $target}) "
                            "MERGE (src)-[r:%s]->(target)" % rel_type,
                            source=source,
                            target=target,
                        )
                    )

        for record in records:
            if record["ci_subtype"] == "server":
                server_code = record["ci_code"]
                system_code = _system_code(server_code)
                storage_code = f"storage-{system_code}"
                security_code = f"sec-{system_code}"
                if storage_code in code_index and security_code in code_index:
                    session.execute_write(
                        lambda tx, server=server_code, storage=storage_code: tx.run(
                            "MATCH (s:CI {ci_code: $server}), (storage:CI {ci_code: $storage}) "
                            "MERGE (s)-[:USES]->(storage)",
                            server=server,
                            storage=storage,
                        )
                    )
                    session.execute_write(
                        lambda tx, server=server_code, sec=security_code: tx.run(
                            "MATCH (s:CI {ci_code: $server}), (sec:CI {ci_code: $sec}) "
                            "MERGE (s)-[:PROTECTED_BY]->(sec)",
                            server=server,
                            sec=security_code,
                        )
                    )

        for record in records:
            if record["ci_subtype"] == "network":
                connected = record.get("tags", {}).get("connected_servers", [])
                for server_code in connected:
                    session.execute_write(
                        lambda tx,
                        server=server_code,
                        network=record["ci_code"]: tx.run(
                            "MATCH (s:CI {ci_code: $server}), (n:CI {ci_code: $network}) "
                            "MERGE (s)-[:CONNECTED_TO]->(n)",
                            server=server,
                            network=network,
                        )
                    )

        for subject, targets in SYSTEM_DEPENDENCIES.items():
            parent_code = f"sys-{subject}"
            for dependency in targets:
                dependent_code = f"sys-{dependency}"
                if parent_code in code_index and dependent_code in code_index:
                    session.execute_write(
                        lambda tx, parent=parent_code, child=dependent_code: tx.run(
                            "MATCH (p:CI {ci_code: $parent}), (c:CI {ci_code: $child}) "
                            "MERGE (p)-[:DEPENDS_ON]->(c)",
                            parent=parent,
                            child=child,
                        )
                    )


def main() -> None:
    records = _load_ci_rows()
    driver = get_neo4j_driver()
    _merge_nodes(driver, records)
    _create_relationships(driver, records)
    with driver.session() as session:
        node_count = session.execute_read(
            lambda tx: tx.run("MATCH (n:CI) RETURN count(n) AS count").single()
        )["count"]
        rel_count = session.execute_read(
            lambda tx: tx.run("MATCH ()-[r]->() RETURN count(r) AS count").single()
        )["count"]
    print(f"Seeded Neo4j with {node_count} nodes and {rel_count} relationships")
    driver.close()


if __name__ == "__main__":
    main()
