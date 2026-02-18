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


# System-required policy asset name (hardcoded - not configurable)
VIEW_POLICY_NAME = "view_depth"


def get_view_registry() -> Dict[str, ViewPolicy]:
    """
    Load view policies from asset registry.
    No hardcoded fallback - views must be configured via Policy Assets.
    """
    try:
        policy_asset = load_policy_asset(VIEW_POLICY_NAME)
        if not policy_asset:
            logger.error(
                f"View policy asset '{VIEW_POLICY_NAME}' not found. "
                "Please create a policy asset with policy_type='view_depth' and content.views defined."
            )
            return {}

        # Support two data structures:
        # 1. New structure: content.views (direct)
        # 2. Old structure: content.limits.views (nested)
        content = policy_asset.get("content", {})
        views_config = content.get("views")
        if not views_config:
            # Try old structure: content.limits.views
            views_config = content.get("limits", {}).get("views", {})

        if not views_config:
            logger.error(
                f"No views found in policy asset '{VIEW_POLICY_NAME}'. "
                "Please define content.views in your policy asset."
            )
            return {}

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
            logger.error(f"Failed to parse any views from asset '{VIEW_POLICY_NAME}'")

        logger.info(f"Loaded {len(registry)} view policies from asset registry")
        return registry

    except Exception as e:
        logger.error(f"Failed to load view policy asset '{VIEW_POLICY_NAME}': {e}")
        return {}


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
