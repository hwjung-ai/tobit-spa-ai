from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import yaml

from app.modules.ops.services.ci.view_registry import VIEW_REGISTRY

RELATION_MAPPING_PATH = Path(__file__).resolve().parent / "relation_mapping.yaml"
CATALOG_DIR = Path(__file__).resolve().parent / "catalog"
POSTGRES_CATALOG_PATH = CATALOG_DIR / "postgres_catalog.json"
NEO4J_CATALOG_PATH = CATALOG_DIR / "neo4j_catalog.json"
COMBINED_CATALOG_PATH = CATALOG_DIR / "combined_catalog.json"
SUMMARY_NEIGHBORS_ALLOWLIST = [
    "COMPOSED_OF",
    "DEPENDS_ON",
    "RUNS_ON",
    "DEPLOYED_ON",
    "USES",
    "PROTECTED_BY",
    "CONNECTED_TO",
]
STATIC_VIEW_NAMES = {"COMPOSITION", "DEPENDENCY", "IMPACT", "PATH"}
SUMMARY_NEIGHBORS_VIEWS = {"SUMMARY", "NEIGHBORS"}


def _load_relation_mapping() -> dict[str, object]:
    if not RELATION_MAPPING_PATH.exists():
        raise FileNotFoundError(f"Missing relation mapping file at {RELATION_MAPPING_PATH}")
    with RELATION_MAPPING_PATH.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    return payload


RELATION_MAPPING = _load_relation_mapping()
VIEW_RELATION_MAPPING: dict[str, List[str]] = {
    view_name.upper(): config.get("rel_types", []) or []
    for view_name, config in (RELATION_MAPPING.get("views") or {}).items()
}
EXCLUDE_REL_TYPES = set(RELATION_MAPPING.get("exclude_rel_types") or [])


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
            "generated_at": datetime.now(timezone.utc).isoformat(),
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


def get_allowed_rel_types(view: str, discovered: Iterable[str] | None = None) -> List[str]:
    view_key = view.upper()
    if view_key not in VIEW_REGISTRY:
        raise ValueError(f"Unknown view '{view}'")
    mapped_rel_types = VIEW_RELATION_MAPPING.get(view_key, [])
    discovered_list = _normalized_discovered(discovered)
    if view_key in STATIC_VIEW_NAMES:
        return [rel for rel in mapped_rel_types if rel]
    if mapped_rel_types:
        return [rel for rel in mapped_rel_types if rel]
    filtered = [rel for rel in discovered_list if rel not in EXCLUDE_REL_TYPES]
    if view_key in SUMMARY_NEIGHBORS_VIEWS:
        controlled = [rel for rel in filtered if rel in SUMMARY_NEIGHBORS_ALLOWLIST]
        return controlled or filtered
    return filtered


def clamp_depth(view: str, requested: int | None = None) -> int:
    view_key = view.upper()
    policy = VIEW_REGISTRY.get(view_key)
    if not policy:
        raise ValueError(f"Unknown view '{view}'")
    depth = requested if requested is not None else policy.default_depth
    depth = max(1, depth)
    return min(depth, policy.max_depth)


def build_policy_trace(
    view: str, requested_depth: int | None = None, discovered: Iterable[str] | None = None
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
    print(f"Wrote combined catalog with {len(rel_types)} discovered rel_types to {COMBINED_CATALOG_PATH}")
