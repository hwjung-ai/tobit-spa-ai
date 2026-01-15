from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed import seed_ci, seed_events, seed_history, seed_metrics, seed_neo4j
from scripts.seed.utils import get_neo4j_driver, get_postgres_conn


def main() -> None:
    steps = [
        ("CI", seed_ci),
        ("metrics", seed_metrics),
        ("events", seed_events),
        ("history", seed_history),
        ("neo4j", seed_neo4j),
    ]

    for label, module in steps:
        print(f"Running seed_{label}...")
        module.main()

    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ci_type, ci_subtype, COUNT(*) FROM ci GROUP BY ci_type, ci_subtype ORDER BY ci_type, ci_subtype"
            )
            ci_summary = cur.fetchall()

            cur.execute("SELECT COUNT(*) FROM metric_value")
            metric_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM event_log")
            event_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM maintenance_history")
            maint_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM work_history")
            work_count = cur.fetchone()[0]

    driver = get_neo4j_driver()
    with driver.session() as session:
        node_count = session.execute_read(lambda tx: tx.run("MATCH (n:CI) RETURN count(n) AS count").single())["count"]
        rel_count = session.execute_read(lambda tx: tx.run("MATCH ()-[r]->() RETURN count(r) AS count").single())["count"]
    driver.close()

    print("\nCI counts (type/subtype):")
    for ci_type, ci_subtype, count in ci_summary:
        print(f"- {ci_type}/{ci_subtype}: {count}")
    print(f"Metric rows: {metric_count}")
    print(f"Event rows: {event_count}")
    print(f"History rows: {maint_count + work_count} (maintenance {maint_count}, work {work_count})")
    print(f"Neo4j nodes: {node_count}, relationships: {rel_count}")

    print("\nSample SQL/Cypher queries:")
    print("1. SQL: SELECT ci_type, ci_subtype, COUNT(*) FROM ci WHERE status = 'active' GROUP BY ci_type, ci_subtype;")
    print("2. SQL: SELECT m.metric_name, COUNT(*) FROM metric_value mv JOIN metric_def m USING(metric_id) WHERE mv.time >= '2025-12-15' GROUP BY m.metric_name;")
    print("3. Cypher: MATCH (s:CI {ci_type:'SYSTEM'})-[:COMPOSED_OF]->(c) RETURN s.ci_code, collect(c.ci_code) LIMIT 5;")


if __name__ == "__main__":
    main()
