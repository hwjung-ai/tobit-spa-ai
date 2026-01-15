from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from neo4j import Driver

from scripts.seed.utils import get_neo4j_driver

from app.shared.config_loader import load_text

CATALOG_DIR = Path(__file__).resolve().parents[1] / "catalog"
OUTPUT_PATH = CATALOG_DIR / "neo4j_catalog.json"
EXPECTED_CI_PROPERTIES = {"ci_id", "ci_code", "tenant_id"}

_QUERY_BASE = "queries/neo4j/discovery"


def _load_query(name: str) -> str:
    query = load_text(f"{_QUERY_BASE}/{name}")
    if not query:
        raise ValueError(f"Neo4j catalog query '{name}' not found")
    return query


def _mask_sensitive(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _exit_error(message: str) -> None:
    print(f"[neo4j_catalog] ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _build_environment_context() -> dict[str, str | None]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "neo4j_uri": _mask_sensitive(os.environ.get("NEO4J_URI")),
        "neo4j_user": _mask_sensitive(os.environ.get("NEO4J_USER")),
    }


def _fetch_relationship_types(driver: Driver) -> list[str]:
    query = _load_query("relationship_types.cypher")
    with driver.session() as session:
        return session.execute_read(
            lambda tx: [record["relationshipType"] for record in tx.run(query)]
        )


def _fetch_relationship_counts(driver: Driver) -> list[dict[str, object]]:
    query = _load_query("relationship_counts.cypher")
    with driver.session() as session:
        result = session.execute_read(
            lambda tx: tx.run(query).data()
        )
        return [{"rel_type": row["rel_type"], "count": row["cnt"]} for row in result]


def _fetch_labels(driver: Driver) -> list[str]:
    query = _load_query("labels.cypher")
    with driver.session() as session:
        return session.execute_read(lambda tx: [record["label"] for record in tx.run(query)])


def _fetch_ci_properties(driver: Driver) -> tuple[list[str], list[str]]:
    query = _load_query("ci_properties.cypher")
    with driver.session() as session:
        result = session.execute_read(lambda tx: tx.run(query).data())
    ci_props: list[str] = []
    for row in result:
        node_type = row.get("nodeType")
        property_name = row.get("propertyName")
        if isinstance(node_type, str) and ":CI" in node_type and property_name:
            if property_name not in ci_props:
                ci_props.append(property_name)
    missing = [prop for prop in EXPECTED_CI_PROPERTIES if prop not in ci_props]
    warnings: list[str] = []
    if missing:
        warnings.append(f"Missing expected CI properties: {', '.join(missing)}")
    return ci_props, warnings


def _build_catalog(driver: Driver) -> dict[str, object]:
    rel_types = _fetch_relationship_types(driver)
    rel_type_counts = _fetch_relationship_counts(driver)
    labels = _fetch_labels(driver)
    ci_props, warnings = _fetch_ci_properties(driver)
    return {
        "relationship_types": rel_types,
        "relationship_type_counts": rel_type_counts,
        "labels": labels,
        "ci_node_properties": ci_props,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "warnings": warnings,
            "environment": _build_environment_context(),
        },
    }


def _write_catalog(payload: dict[str, object]) -> None:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def main() -> None:
    driver: Driver | None = None
    try:
        driver = get_neo4j_driver()
        catalog = _build_catalog(driver)
        _write_catalog(catalog)
        print(f"Wrote Neo4j catalog to {OUTPUT_PATH}")
    except Exception as exc:
        _exit_error(str(exc))
    finally:
        if driver:
            driver.close()


if __name__ == "__main__":
    main()
