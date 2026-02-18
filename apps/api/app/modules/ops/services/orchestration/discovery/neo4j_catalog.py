from __future__ import annotations

import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.config import get_settings
from core.logging import get_logger

from app.modules.asset_registry.loader import load_policy_asset
from app.modules.ops.services.orchestration.tools.base import (
    ToolContext,
    get_tool_registry,
)
from app.modules.ops.services.orchestration.tools.executor import get_tool_executor
from app.modules.ops.services.orchestration.tools.registry_init import initialize_tools

logger = get_logger(__name__)

# System-required policy asset name (hardcoded - not configurable)
DISCOVERY_POLICY_NAME = "discovery_config"

CATALOG_DIR = Path(__file__).resolve().parents[1] / "catalog"
OUTPUT_PATH = CATALOG_DIR / "neo4j_catalog.json"

# Cache for discovery config loaded from DB
_DISCOVERY_CONFIG_CACHE: Dict[str, Any] | None = None

# Default expected properties if not configured
_DEFAULT_CI_PROPERTIES = {"ci_id", "ci_code", "tenant_id"}


def _get_discovery_config() -> Dict[str, Any]:
    """
    Load Neo4j discovery configuration from policy asset.
    No hardcoded fallback - configuration must be set via Policy Assets.
    """
    global _DISCOVERY_CONFIG_CACHE
    if _DISCOVERY_CONFIG_CACHE is not None:
        return _DISCOVERY_CONFIG_CACHE

    try:
        policy = load_policy_asset(DISCOVERY_POLICY_NAME)
        if policy:
            content = policy.get("content", {})
            neo4j_config = content.get("neo4j", {})
            if neo4j_config:
                _DISCOVERY_CONFIG_CACHE = {
                    "expected_ci_properties": set(
                        neo4j_config.get(
                            "expected_ci_properties", list(_DEFAULT_CI_PROPERTIES)
                        )
                    ),
                }
                logger.info(
                    "Loaded Neo4j discovery config from DB: %s expected properties",
                    len(_DISCOVERY_CONFIG_CACHE["expected_ci_properties"]),
                )
                return _DISCOVERY_CONFIG_CACHE
    except Exception as e:
        logger.warning(f"Failed to load '{DISCOVERY_POLICY_NAME}' policy for Neo4j: {e}")

    logger.warning(
        "Discovery policy '%s' not found. Using minimal default properties.",
        DISCOVERY_POLICY_NAME,
    )
    _DISCOVERY_CONFIG_CACHE = {"expected_ci_properties": _DEFAULT_CI_PROPERTIES}
    return _DISCOVERY_CONFIG_CACHE


def _exit_error(message: str) -> None:
    print(f"[neo4j_catalog] ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _build_environment_context(tool_name: str) -> dict[str, str | None]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "tool_asset": tool_name,
        "execution_mode": "tool_orchestration",
    }


def _resolve_graph_tool_name() -> str:
    initialize_tools()
    registry = get_tool_registry()

    for capability in ("graph_expand", "graph_query", "graph_topology"):
        candidate = registry.find_tool_by_capability(capability)
        if candidate:
            return getattr(candidate, "tool_name")

    matches = registry.find_tools_by_type("graph_query")
    if matches:
        return getattr(matches[0], "tool_name")

    raise ValueError("No graph tool found in registry for Neo4j catalog discovery")


def _execute_graph_tool(tool_name: str) -> dict[str, Any]:
    settings = get_settings()
    tenant_id = getattr(settings, "default_tenant_id", None) or "default"
    context = ToolContext(
        tenant_id=tenant_id,
        user_id="system",
        metadata={"source": "neo4j_catalog_discovery"},
    )
    result = get_tool_executor().execute(
        tool_name,
        context,
        {
            "tenant_id": tenant_id,
            "limit": 2000,
            "ci_ids": [],
        },
    )
    if not result.success:
        raise ValueError(result.error or f"Tool execution failed: {tool_name}")
    if not isinstance(result.data, dict):
        raise ValueError(f"Unexpected tool response type from {tool_name}")
    return result.data


def _build_catalog(tool_data: dict[str, Any], tool_name: str) -> dict[str, object]:
    discovery_config = _get_discovery_config()
    expected_properties = discovery_config["expected_ci_properties"]

    edges = tool_data.get("edges", []) if isinstance(tool_data.get("edges"), list) else []
    nodes = tool_data.get("nodes", []) if isinstance(tool_data.get("nodes"), list) else []

    rel_counts: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        rel_type = edge.get("relation") or edge.get("type") or edge.get("label")
        rel_type_str = str(rel_type).strip() if rel_type is not None else ""
        if not rel_type_str:
            continue
        rel_counts[rel_type_str] = rel_counts.get(rel_type_str, 0) + 1

    relationship_types = sorted(rel_counts.keys())
    relationship_type_counts = [
        {"rel_type": rel_type, "count": rel_counts[rel_type]}
        for rel_type in relationship_types
    ]

    labels_set: set[str] = set()
    ci_props_set: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if node_type:
            labels_set.add(str(node_type))
        ci_props_set.update(str(k) for k in node.keys())

    ci_node_properties = sorted(ci_props_set)
    missing = [prop for prop in expected_properties if prop not in ci_props_set]
    warnings: list[str] = []
    if missing:
        warnings.append(f"Missing expected CI properties: {', '.join(missing)}")

    return {
        "relationship_types": relationship_types,
        "relationship_type_counts": relationship_type_counts,
        "labels": sorted(labels_set),
        "ci_node_properties": ci_node_properties,
        "meta": {
            "generated_at": datetime.now(get_settings().timezone_offset).isoformat(),
            "warnings": warnings,
            "environment": _build_environment_context(tool_name),
        },
    }


def _write_catalog(payload: dict[str, object]) -> None:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def main() -> None:
    """Generate Neo4j catalog through graph tool orchestration."""
    try:
        tool_name = _resolve_graph_tool_name()
        tool_data = _execute_graph_tool(tool_name)
        catalog = _build_catalog(tool_data, tool_name)
        _write_catalog(catalog)
        print(f"Wrote Neo4j catalog to {OUTPUT_PATH} via tool '{tool_name}'")
    except Exception as exc:
        _exit_error(str(exc))


if __name__ == "__main__":
    main()
