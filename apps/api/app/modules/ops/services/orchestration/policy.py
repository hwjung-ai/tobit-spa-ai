from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import yaml
from core.config import get_settings
from core.logging import get_logger

from app.modules.asset_registry.loader import load_mapping_asset
from app.modules.ops.services.orchestration.view_registry import (
    get_view_policy,
    get_view_registry,
)

logger = get_logger(__name__)

# System-required mapping asset names (hardcoded - not configurable)
GRAPH_RELATION_MAPPING_NAME = "graph_relation"
GRAPH_RELATION_ALLOWLIST_NAME = "graph_relation_allowlist"

RELATION_MAPPING_PATH = Path(__file__).resolve().parent / "relation_mapping.yaml"
CATALOG_DIR = Path(__file__).resolve().parent / "catalog"
POSTGRES_CATALOG_PATH = CATALOG_DIR / "postgres_catalog.json"
NEO4J_CATALOG_PATH = CATALOG_DIR / "neo4j_catalog.json"
COMBINED_CATALOG_PATH = CATALOG_DIR / "combined_catalog.json"


def _load_relation_mapping() -> dict[str, object]:
    """Load relation mapping from Asset Registry only.

    No hardcoded fallback - mapping must be configured via Mapping Assets.
    """
    try:
        from app.modules.asset_registry.loader import load_mapping_asset

        mapping_data, _ = load_mapping_asset(GRAPH_RELATION_MAPPING_NAME)
        if mapping_data:
            return mapping_data
    except Exception as e:
        logger.warning(f"Failed to load mapping asset '{GRAPH_RELATION_MAPPING_NAME}': {e}")

    raise FileNotFoundError(
        f"No relation mapping found. "
        f"Please create a mapping asset with mapping_type='{GRAPH_RELATION_MAPPING_NAME}'."
    )


# Lazy loading caches (avoid circular imports and DB access at module load time)
_RELATION_MAPPING_CACHE = None
_VIEW_RELATION_MAPPING_CACHE = None
_EXCLUDE_REL_TYPES_CACHE = None
_SUMMARY_NEIGHBORS_ALLOWLIST_CACHE = None
_STATIC_VIEW_NAMES_CACHE = None
_SUMMARY_NEIGHBORS_VIEWS_CACHE = None


def _get_static_view_names() -> set[str]:
    """Get view names that use static relation types (loaded from view registry)."""
    global _STATIC_VIEW_NAMES_CACHE
    if _STATIC_VIEW_NAMES_CACHE is None:
        # Views that don't need dynamic discovery - configured via view registry
        registry = get_view_registry()
        # Default static views if not in registry
        _STATIC_VIEW_NAMES_CACHE = {"COMPOSITION", "DEPENDENCY", "IMPACT", "PATH"}
        # Could be extended from registry if needed
    return _STATIC_VIEW_NAMES_CACHE


def _get_summary_neighbors_views() -> set[str]:
    """Get view names that use summary/neighbors allowlist (loaded from view registry)."""
    global _SUMMARY_NEIGHBORS_VIEWS_CACHE
    if _SUMMARY_NEIGHBORS_VIEWS_CACHE is None:
        # Views that use summary_neighbors_allowlist for relation filtering
        registry = get_view_registry()
        # Default views if not in registry
        _SUMMARY_NEIGHBORS_VIEWS_CACHE = {"SUMMARY", "NEIGHBORS"}
        # Could be extended from registry if needed
    return _SUMMARY_NEIGHBORS_VIEWS_CACHE


def _ensure_relation_mapping() -> dict[str, object]:
    """Lazy load relation mapping on first access"""
    global _RELATION_MAPPING_CACHE
    if _RELATION_MAPPING_CACHE is None:
        _RELATION_MAPPING_CACHE = _load_relation_mapping()
    return _RELATION_MAPPING_CACHE


def _ensure_view_relation_mapping() -> dict[str, List[str]]:
    """Lazy load view relation mapping on first access"""
    global _VIEW_RELATION_MAPPING_CACHE
    if _VIEW_RELATION_MAPPING_CACHE is None:
        mapping = _ensure_relation_mapping()
        _VIEW_RELATION_MAPPING_CACHE = {
            view_name.upper(): config.get("rel_types", []) or []
            for view_name, config in (mapping.get("views") or {}).items()
        }
    return _VIEW_RELATION_MAPPING_CACHE


def _ensure_exclude_rel_types() -> set[str]:
    """Lazy load exclude rel types on first access"""
    global _EXCLUDE_REL_TYPES_CACHE
    if _EXCLUDE_REL_TYPES_CACHE is None:
        mapping = _ensure_relation_mapping()
        _EXCLUDE_REL_TYPES_CACHE = set(mapping.get("exclude_rel_types") or [])
    return _EXCLUDE_REL_TYPES_CACHE


def _ensure_summary_neighbors_allowlist() -> List[str]:
    """
    Lazy load SUMMARY/NEIGHBORS allowlist from mapping asset.
    No hardcoded fallback - must be configured via Mapping Assets.
    """
    global _SUMMARY_NEIGHBORS_ALLOWLIST_CACHE
    if _SUMMARY_NEIGHBORS_ALLOWLIST_CACHE is None:
        try:
            mapping_asset, _ = load_mapping_asset(GRAPH_RELATION_ALLOWLIST_NAME)
            if mapping_asset:
                content = mapping_asset.get("content", {})
                allowlist = content.get("summary_neighbors_allowlist", [])
                if allowlist:
                    _SUMMARY_NEIGHBORS_ALLOWLIST_CACHE = allowlist
                    logger.info(f"Loaded {len(allowlist)} allowed relation types from mapping asset")
                    return _SUMMARY_NEIGHBORS_ALLOWLIST_CACHE
        except Exception as e:
            logger.warning(f"Failed to load '{GRAPH_RELATION_ALLOWLIST_NAME}' asset: {e}")

        # No fallback - return empty list
        logger.warning(
            f"No summary_neighbors_allowlist found. "
            f"Please create a mapping asset with mapping_type='{GRAPH_RELATION_ALLOWLIST_NAME}' "
            f"and content.summary_neighbors_allowlist defined."
        )
        _SUMMARY_NEIGHBORS_ALLOWLIST_CACHE = []
    return _SUMMARY_NEIGHBORS_ALLOWLIST_CACHE


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_rel_types_from_neo4j(neo4j_data: dict[str, object]) -> List[str]:
    counts = neo4j_data.get("relationship_type_counts", [])
    rel_types: List[str] = []
    for entry in counts:
        if not isinstance(entry, dict):
            continue
        rel_type = entry.get("rel_type")
        if rel_type and rel_type not in rel_types:
            rel_types.append(rel_type)
    return rel_types


def _ensure_combined_catalog() -> dict[str, object]:
    postgres = _load_json(POSTGRES_CATALOG_PATH)
    neo4j = _load_json(NEO4J_CATALOG_PATH)
    if not postgres and not neo4j:
        return {}
    rel_types = _extract_rel_types_from_neo4j(neo4j)
    combined = {
        "postgres": postgres,
        "neo4j": neo4j,
        "meta": {
            "generated_at": datetime.now(get_settings().timezone_offset).isoformat(),
            "discovered_rel_types": rel_types,
        },
    }
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    with COMBINED_CATALOG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(combined, fh, ensure_ascii=False, indent=2)
    return combined


def _normalized_discovered(discovered: Iterable[str] | None) -> List[str]:
    source = list(discovered) if discovered is not None else DISCOVERED_REL_TYPES
    return list(dict.fromkeys([rel for rel in source if rel]))


def _load_discovered_rel_types() -> List[str]:
    combined_meta = COMBINED_CATALOG.get("meta", {}) if COMBINED_CATALOG else {}
    catalog_rel_types = combined_meta.get("discovered_rel_types") or []
    if catalog_rel_types:
        return catalog_rel_types
    neo4j = _load_json(NEO4J_CATALOG_PATH)
    return _extract_rel_types_from_neo4j(neo4j)


COMBINED_CATALOG = _ensure_combined_catalog()
DISCOVERED_REL_TYPES = _load_discovered_rel_types()


def get_allowed_rel_types(
    view: str, discovered: Iterable[str] | None = None
) -> List[str]:
    view_key = view.upper()
    registry = get_view_registry()
    if view_key not in registry:
        raise ValueError(f"Unknown view '{view}'")
    # Use lazy-loaded view relation mapping
    view_mapping = _ensure_view_relation_mapping()
    mapped_rel_types = view_mapping.get(view_key, [])
    discovered_list = _normalized_discovered(discovered)
    if view_key in _get_static_view_names():
        return [rel for rel in mapped_rel_types if rel]
    if mapped_rel_types:
        return [rel for rel in mapped_rel_types if rel]
    # Use lazy-loaded exclude rel types
    exclude_types = _ensure_exclude_rel_types()
    filtered = [rel for rel in discovered_list if rel not in exclude_types]
    if view_key in _get_summary_neighbors_views():
        allowlist = _ensure_summary_neighbors_allowlist()
        controlled = [rel for rel in filtered if rel in allowlist]
        return controlled or filtered
    return filtered


def clamp_depth(view: str, requested: int | None = None) -> int:
    view_key = view.upper()
    policy = get_view_policy(view_key)
    if not policy:
        raise ValueError(f"Unknown view '{view}'")
    depth = requested if requested is not None else policy.default_depth
    depth = max(1, depth)
    return min(depth, policy.max_depth)


def build_policy_trace(
    view: str,
    requested_depth: int | None = None,
    discovered: Iterable[str] | None = None,
) -> dict[str, object]:
    allowed = get_allowed_rel_types(view, discovered)
    trace = {
        "view": view.upper(),
        "requested_depth": requested_depth,
        "clamped_depth": clamp_depth(view, requested_depth),
        "allowed_rel_types": allowed,
        "discovered_rel_types": _normalized_discovered(discovered),
    }
    return trace


def refresh_combined_catalog() -> dict[str, object]:
    return _ensure_combined_catalog()


if __name__ == "__main__":
    combined = refresh_combined_catalog()
    rel_types = combined.get("meta", {}).get("discovered_rel_types", [])
    print(
        f"Wrote combined catalog with {len(rel_types)} discovered rel_types to {COMBINED_CATALOG_PATH}"
    )
