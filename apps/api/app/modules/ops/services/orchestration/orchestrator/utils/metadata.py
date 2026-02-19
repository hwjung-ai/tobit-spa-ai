"""Metadata and asset display utilities.

This module handles asset display formatting, asset resolution,
and metadata logging.
"""

from typing import Any, Dict, List

from app.modules.inspector.asset_context import get_stage_assets
from app.modules.ops.services.orchestration.blocks import Block


def format_asset_display(info: Dict[str, Any]) -> str:
    """Format asset info for user-friendly display.

    Returns a clean string like "asset_name (v1)" or "fallback".

    Args:
        info: Asset information dictionary

    Returns:
        Formatted display string
    """
    name = info.get("name") or info.get("screen_id") or "unknown"
    version = info.get("version")
    source = info.get("source", "asset_registry")

    # For non-asset registry sources, show source info
    if source != "asset_registry":
        return f"{name} (fallback)"

    # For asset registry assets, show name with version
    if version is not None:
        return f"{name} (v{version})"
    return name


def resolve_applied_assets_from_assets(
    assets: Dict[str, Any], asset_overrides: Dict[str, str] | None = None
) -> Dict[str, str]:
    """Resolve applied assets from pre-computed assets dictionary.

    This is similar to resolve_applied_assets() but takes assets as input
    instead of reading from stage context. Used for stage-specific asset tracking.

    Args:
        assets: Dictionary with keys like 'prompt', 'queries', 'screens', etc.
        asset_overrides: Optional overrides to apply

    Returns:
        Dict[str, str] where:
        - Key: asset_type (e.g., "prompt", "catalog", "mapping", "query:name", "screen:id")
        - Value: User-friendly display name like "asset_name (v1)" or "fallback"
    """
    asset_overrides = asset_overrides or {}
    applied: Dict[str, str] = {}

    for key in ("prompt", "policy", "mapping", "source", "catalog", "resolver"):
        info = assets.get(key)
        if not info:
            continue
        applied[key] = format_asset_display(info)
        override_key = f"{key}:{info.get('name')}"
        override = asset_overrides.get(override_key)
        if override:
            # Override can be a direct string value
            applied[key] = str(override)

    # Handle tools array
    for entry in assets.get("tools", []) or []:
        if not entry:
            continue
        name = entry.get("name") or entry.get("tool_name") or entry.get("asset_id") or "tool"
        version = entry.get("version")
        if version is not None:
            display_name = f"{name} (v{version})"
        else:
            display_name = name
        applied[f"tool:{name}"] = display_name
        override_key = f"tool:{name}"
        override = asset_overrides.get(override_key)
        if override:
            applied[f"tool:{name}"] = str(override)

    for entry in assets.get("queries", []) or []:
        if not entry:
            continue
        name = entry.get("name") or entry.get("asset_id") or "query"
        version = entry.get("version")
        if version is not None:
            display_name = f"{name} (v{version})"
        else:
            display_name = name
        applied[f"query:{name}"] = display_name
        override_key = f"query:{name}"
        override = asset_overrides.get(override_key)
        if override:
            applied[f"query:{name}"] = str(override)

    for entry in assets.get("screens", []) or []:
        if not entry:
            continue
        screen_id = entry.get("screen_id") or entry.get("asset_id") or "screen"
        name = entry.get("screen_id") or entry.get("name") or screen_id
        version = entry.get("version")
        if version is not None:
            display_name = f"{name} (v{version})"
        else:
            display_name = name
        applied[f"screen:{screen_id}"] = display_name
        override_key = f"screen:{screen_id}"
        override = asset_overrides.get(override_key)
        if override:
            applied[f"screen:{screen_id}"] = str(override)

    return applied


def resolve_applied_assets(asset_overrides: Dict[str, str] | None = None) -> Dict[str, str]:
    """Resolve applied assets with user-friendly display format.

    Reads assets from stage context.

    Args:
        asset_overrides: Optional overrides to apply

    Returns:
        Dict[str, str] where:
        - Key: asset_type (e.g., "prompt", "catalog", "mapping")
        - Value: User-friendly display name like "asset_name (v1)" or "fallback"
    """
    assets = get_stage_assets()
    return resolve_applied_assets_from_assets(assets, asset_overrides)


def log_metric_blocks_return(blocks: List[Block], logger) -> None:
    """Log block types returned from metric execution.

    Args:
        blocks: List of blocks returned
        logger: Logger instance to use
    """
    types = [
        block.get("type")
        if isinstance(block, dict)
        else getattr(block, "type", None)
        for block in blocks
    ]
    logger.info(
        "ci.metric.blocks_debug", extra={"types": types, "count": len(blocks)}
    )
