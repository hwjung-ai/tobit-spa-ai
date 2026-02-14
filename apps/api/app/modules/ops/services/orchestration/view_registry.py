from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from core.logging import get_logger

from app.modules.asset_registry.loader import load_policy_asset

logger = get_logger(__name__)


class Direction(Enum):
    OUT = "out"
    IN = "in"
    BOTH = "both"


@dataclass(frozen=True)
class ViewPolicy:
    name: str
    description: str
    default_depth: int
    max_depth: int
    direction_default: Direction
    output_defaults: List[str]
    notes: str | None = None
    max_hops: int | None = None


VIEW_REGISTRY: Dict[str, ViewPolicy] = {
    "SUMMARY": ViewPolicy(
        name="SUMMARY",
        description="Top-level overview of a CI with immediate key statistics.",
        default_depth=1,
        max_depth=1,
        direction_default=Direction.BOTH,
        output_defaults=["overviews", "counts"],
    ),
    "COMPOSITION": ViewPolicy(
        name="COMPOSITION",
        description="System/component composition that highlights parent/child links.",
        default_depth=2,
        max_depth=3,
        direction_default=Direction.OUT,
        output_defaults=["hierarchy", "children"],
    ),
    "DEPENDENCY": ViewPolicy(
        name="DEPENDENCY",
        description="Bidirectional dependency relationships for the selected CI.",
        default_depth=2,
        max_depth=3,
        direction_default=Direction.BOTH,
        output_defaults=["dependency_graph", "counts"],
    ),
    "IMPACT": ViewPolicy(
        name="IMPACT",
        description="Propagated impact along dependencies (assumption-based).",
        default_depth=2,
        max_depth=2,
        direction_default=Direction.OUT,
        output_defaults=["impact_summary"],
        notes="IMPACT는 의존 기반 영향(가정)으로 정의합니다.",
    ),
    "PATH": ViewPolicy(
        name="PATH",
        description="Path discovery capped by a maximum hop limit.",
        default_depth=3,
        max_depth=6,
        direction_default=Direction.BOTH,
        output_defaults=["path_segments"],
        max_hops=6,
    ),
    "NEIGHBORS": ViewPolicy(
        name="NEIGHBORS",
        description="Immediate neighbors for the selected CI.",
        default_depth=1,
        max_depth=2,
        direction_default=Direction.BOTH,
        output_defaults=["neighbors"],
    ),
}

VIEW_NAMES: List[str] = list(VIEW_REGISTRY.keys())


def get_view_registry() -> Dict[str, ViewPolicy]:
    """
    Load view policies from asset registry.
    Falls back to hardcoded VIEW_REGISTRY if asset not found.
    """
    try:
        # Use correct policy_type "view_depth" (not "view_depth_policies")
        policy_asset = load_policy_asset("view_depth")
        if not policy_asset:
            logger.warning("view_depth policy asset not found, using hardcoded VIEW_REGISTRY")
            return VIEW_REGISTRY

        # Support two data structures:
        # 1. New structure: content.views (direct)
        # 2. Old structure: content.limits.views (nested)
        content = policy_asset.get("content", {})
        views_config = content.get("views")
        if not views_config:
            # Try old structure: content.limits.views
            views_config = content.get("limits", {}).get("views", {})

        if not views_config:
            logger.warning("No views in policy asset, using hardcoded VIEW_REGISTRY")
            return VIEW_REGISTRY

        # Build registry from asset
        registry = {}
        for name, config in views_config.items():
            try:
                # Handle direction_default - convert to uppercase if needed
                direction_str = config.get("direction_default", "BOTH")
                if isinstance(direction_str, str):
                    direction_str = direction_str.upper()

                registry[name] = ViewPolicy(
                    name=name,
                    description=config.get("description", ""),
                    default_depth=config.get("default_depth", 1),
                    max_depth=config.get("max_depth", 3),
                    direction_default=Direction[direction_str],
                    output_defaults=config.get("output_defaults", []),
                    notes=config.get("notes"),
                    max_hops=config.get("max_hops"),
                )
            except Exception as e:
                logger.error(f"Failed to parse view policy '{name}': {e}")
                continue

        if not registry:
            logger.warning("Failed to parse any views from asset, using hardcoded VIEW_REGISTRY")
            return VIEW_REGISTRY

        logger.info(f"Loaded {len(registry)} view policies from asset registry")
        return registry

    except Exception as e:
        logger.error(f"Failed to load view_depth_policies asset: {e}, using hardcoded VIEW_REGISTRY")
        return VIEW_REGISTRY


# Cached registry
_VIEW_REGISTRY_CACHE: Dict[str, ViewPolicy] | None = None


def get_view_policy(view_name: str) -> ViewPolicy | None:
    """
    Get a specific view policy by name.
    Loads from asset registry with caching.
    """
    global _VIEW_REGISTRY_CACHE
    if _VIEW_REGISTRY_CACHE is None:
        _VIEW_REGISTRY_CACHE = get_view_registry()
    return _VIEW_REGISTRY_CACHE.get(view_name)
