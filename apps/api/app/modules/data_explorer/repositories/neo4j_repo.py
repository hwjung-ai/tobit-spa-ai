from __future__ import annotations

from typing import Any

from core.config import AppSettings
from core.db_neo4j import get_neo4j_driver
from neo4j.graph import Node, Relationship


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Node):
        return {
            "__neo4j_type": "node",
            "id": str(value.id),
            "labels": list(value.labels),
            "properties": dict(value.items()),
        }
    if isinstance(value, Relationship):
        return {
            "__neo4j_type": "relationship",
            "id": str(value.id),
            "type": value.type,
            "start": str(value.start_node.id),
            "end": str(value.end_node.id),
            "properties": dict(value.items()),
        }
    if hasattr(value, "to_dict"):
        return getattr(value, "to_dict")()
    return value


def list_labels(settings: AppSettings) -> list[str]:
    driver = get_neo4j_driver(settings)
    try:
        with driver.session() as session:
            result = session.run("CALL db.labels()")
            return [record["label"] for record in result]
    finally:
        driver.close()


def run_query(
    settings: AppSettings,
    cypher: str,
    params: dict[str, Any] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    driver = get_neo4j_driver(settings)
    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            keys = result.keys()
            rows = []
            for record in result:
                serialized = {
                    key: _serialize_value(record[key]) for key in keys
                }
                rows.append(serialized)
            return list(keys), rows
    finally:
        driver.close()
