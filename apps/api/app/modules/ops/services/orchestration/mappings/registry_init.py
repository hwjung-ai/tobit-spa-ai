"""
Mapping registry initialization module.

Loads mapping assets from Asset Registry only.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


MAPPING_NAMES: list[str] = [
    "planner_keywords",
    "planner_defaults",
    "graph_relation",
    "graph_relation_allowlist",
    "default_output_format",
]


def _load_mapping_from_db(mapping_name: str):
    """Load a single mapping from Asset Registry."""
    from app.modules.asset_registry.loader import load_mapping_asset

    mapping_data, metadata = load_mapping_asset(mapping_name)
    if mapping_data is None:
        raise ValueError(f"Mapping asset not found: {mapping_name}")

    logger.info(
        "Loaded mapping '%s' from Asset Registry: %s",
        mapping_name,
        metadata,
    )
    return mapping_data
def initialize_mappings() -> None:
    """Initialize and register all required mappings from Asset Registry."""
    from .registry import get_mapping_registry

    registry = get_mapping_registry()
    loaded_count = 0
    errors: list[str] = []

    for mapping_name in MAPPING_NAMES:
        try:
            mapping_data = _load_mapping_from_db(mapping_name)
            registry.register_mapping(
                mapping_name,
                mapping_data,
                source="asset_registry",
            )
            loaded_count += 1
        except Exception as exc:
            errors.append(f"{mapping_name}: {exc}")

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(
            f"Mapping registry initialization failed ({loaded_count}/{len(MAPPING_NAMES)} loaded): {joined}"
        )

    logger.info(
        "Successfully loaded %d/%d mappings from Asset Registry",
        loaded_count,
        len(MAPPING_NAMES),
    )
