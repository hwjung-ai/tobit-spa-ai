from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict

from core.config import get_settings
from core.logging import get_logger
from neo4j import Driver

from app.shared.config_loader import load_text
from app.modules.asset_registry.loader import load_policy_asset, load_source_asset
from app.modules.ops.services.connections import ConnectionFactory

logger = get_logger(__name__)

CATALOG_DIR = Path(__file__).resolve().parents[1] / "catalog"
OUTPUT_PATH = CATALOG_DIR / "neo4j_catalog.json"

# Hardcoded fallback configurations - will be loaded from DB via _get_discovery_config()
EXPECTED_CI_PROPERTIES = {"ci_id", "ci_code", "tenant_id"}

# Cache for discovery config loaded from DB
_DISCOVERY_CONFIG_CACHE: Dict[str, Any] | None = None

_QUERY_BASE = "queries/neo4j/discovery"


def _get_discovery_config() -> Dict[str, Any]:
    """
    Load Neo4j discovery configuration from policy asset.
    Falls back to hardcoded constants if asset not found.

    Returns:
        Dictionary with discovery configuration:
        {
            "expected_ci_properties": {...}
        }
    """
    global _DISCOVERY_CONFIG_CACHE
    if _DISCOVERY_CONFIG_CACHE is not None:
        return _DISCOVERY_CONFIG_CACHE

    try:
        policy = load_policy_asset("discovery_config")
        if policy:
            content = policy.get("content", {})
            neo4j_config = content.get("neo4j", {})
            if neo4j_config:
                _DISCOVERY_CONFIG_CACHE = {
                    "expected_ci_properties": set(neo4j_config.get("expected_ci_properties", list(EXPECTED_CI_PROPERTIES))),
                }
                logger.info(f"Loaded Neo4j discovery config from DB: {len(_DISCOVERY_CONFIG_CACHE['expected_ci_properties'])} expected properties")
                return _DISCOVERY_CONFIG_CACHE
    except Exception as e:
        logger.warning(f"Failed to load discovery_config policy for Neo4j: {e}")

    # Fallback to hardcoded config
    _DISCOVERY_CONFIG_CACHE = {
        "expected_ci_properties": EXPECTED_CI_PROPERTIES,
    }
    logger.info("Using hardcoded Neo4j discovery config (fallback)")
    return _DISCOVERY_CONFIG_CACHE


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
        "neo4j_uri": _mask_sensitive(os.environ.get("NEO4J_URI")),  # For backward compatibility
        "source_asset": "primary_neo4j (from DB)",  # New: indicate source from DB
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
        result = session.execute_read(lambda tx: tx.run(query).data())
        return [{"rel_type": row["rel_type"], "count": row["cnt"]} for row in result]


def _fetch_labels(driver: Driver) -> list[str]:
    query = _load_query("labels.cypher")
    with driver.session() as session:
        return session.execute_read(
            lambda tx: [record["label"] for record in tx.run(query)]
        )


def _fetch_ci_properties(driver: Driver) -> tuple[list[str], list[str]]:
    # Load discovery config
    discovery_config = _get_discovery_config()
    expected_properties = discovery_config["expected_ci_properties"]

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
    missing = [prop for prop in expected_properties if prop not in ci_props]
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
            "generated_at": datetime.now(get_settings().timezone_offset).isoformat(),
            "warnings": warnings,
            "environment": _build_environment_context(),
        },
    }


def _write_catalog(payload: dict[str, object]) -> None:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def main() -> None:
    """
    Generate Neo4j catalog using connection from source asset.

    Uses primary_neo4j source asset from database instead of environment variables.
    """
    # Load source asset from DB
    source_asset = load_source_asset("primary_neo4j")
    if not source_asset:
        _exit_error("Source asset 'primary_neo4j' not found. Ensure it exists in Asset Registry.")
        return

    try:
        # Create connection using ConnectionFactory
        connection = ConnectionFactory.create(source_asset)
        driver = connection.driver  # Neo4jConnection exposes driver

        catalog = _build_catalog(driver)
        _write_catalog(catalog)
        print(f"Wrote Neo4j catalog to {OUTPUT_PATH}")
    except Exception as exc:
        _exit_error(str(exc))
    finally:
        if 'driver' in locals() and driver:
            driver.close()


if __name__ == "__main__":
    main()
