from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict

AssetInfo = Dict[str, Any]


_ASSET_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar(
    "inspector_asset_context", default=None
)
_STAGE_ASSET_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar(
    "inspector_stage_asset_context", default=None
)


def _initial_context() -> Dict[str, Any]:
    return {
        "prompt": None,
        "prompts": [],
        "policy": None,
        "policies": [],
        "mapping": None,
        "mappings": [],
        "source": None,
        "catalog": None,
        "resolver": None,
        "tools": [],
    }


def _ensure_context() -> Dict[str, Any]:
    context = _ASSET_CONTEXT.get()
    if context is None:
        context = _initial_context()
        _ASSET_CONTEXT.set(context)
    return context


def reset_asset_context() -> None:
    """Clear tracked asset usage for the current execution context."""
    _ASSET_CONTEXT.set(_initial_context())


def get_tracked_assets() -> Dict[str, Any]:
    """Return a copy of the tracked asset usage."""
    context = _ensure_context()
    return {
        "prompt": context.get("prompt"),
        "prompts": list(context.get("prompts", [])),
        "policy": context.get("policy"),
        "policies": list(context.get("policies", [])),
        "mapping": context.get("mapping"),
        "mappings": list(context.get("mappings", [])),
        "source": context.get("source"),
        "catalog": context.get("catalog"),
        "resolver": context.get("resolver"),
        "tools": list(context.get("tools", [])),
    }


def track_prompt_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["prompt"] = info
    prompts = list(context.get("prompts", []))
    prompts.append(info)
    context["prompts"] = prompts
    _ASSET_CONTEXT.set(context)


def track_policy_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["policy"] = info
    policies = list(context.get("policies", []))
    policies.append(info)
    context["policies"] = policies
    _ASSET_CONTEXT.set(context)


def track_mapping_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["mapping"] = info
    mappings = list(context.get("mappings", []))
    mappings.append(info)
    context["mappings"] = mappings
    _ASSET_CONTEXT.set(context)


def track_source_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["source"] = info
    _ASSET_CONTEXT.set(context)


def track_resolver_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["resolver"] = info
    _ASSET_CONTEXT.set(context)


def track_tool_asset(info: AssetInfo) -> None:
    """Track a tool asset that was used during execution."""
    context = _ensure_context()
    tools = list(context.get("tools", []))
    tools.append(info)
    context["tools"] = tools
    _ASSET_CONTEXT.set(context)


def track_catalog_asset(info: AssetInfo) -> None:
    """Track a catalog asset that was used during execution."""
    context = _ensure_context()
    context["catalog"] = info
    _ASSET_CONTEXT.set(context)


def begin_stage_asset_tracking() -> None:
    """Reset asset tracking for a new stage.

    This should be called at the beginning of each stage to ensure
    only assets used in this stage are tracked.
    """
    _STAGE_ASSET_CONTEXT.set(_initial_context())


def end_stage_asset_tracking() -> Dict[str, Any]:
    """Capture stage-specific assets and reset stage context.

    Returns the assets tracked during this stage.
    """
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()

    # Copy stage assets to return
    stage_assets = {
        "prompt": stage_context.get("prompt"),
        "prompts": list(stage_context.get("prompts", [])),
        "policy": stage_context.get("policy"),
        "policies": list(stage_context.get("policies", [])),
        "mapping": stage_context.get("mapping"),
        "mappings": list(stage_context.get("mappings", [])),
        "source": stage_context.get("source"),
        "catalog": stage_context.get("catalog"),
        "resolver": stage_context.get("resolver"),
        "tools": list(stage_context.get("tools", [])),
    }

    # Reset stage context
    _STAGE_ASSET_CONTEXT.set(_initial_context())
    return stage_assets


def get_stage_assets() -> Dict[str, Any]:
    """Return assets tracked for the current stage only."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
        _STAGE_ASSET_CONTEXT.set(stage_context)

    return {
        "prompt": stage_context.get("prompt"),
        "prompts": list(stage_context.get("prompts", [])),
        "policy": stage_context.get("policy"),
        "policies": list(stage_context.get("policies", [])),
        "mapping": stage_context.get("mapping"),
        "mappings": list(stage_context.get("mappings", [])),
        "source": stage_context.get("source"),
        "catalog": stage_context.get("catalog"),
        "resolver": stage_context.get("resolver"),
        "tools": list(stage_context.get("tools", [])),
    }


def track_prompt_asset_to_stage(info: AssetInfo) -> None:
    """Track prompt asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    stage_context["prompt"] = info
    prompts = list(stage_context.get("prompts", []))
    prompts.append(info)
    stage_context["prompts"] = prompts
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_prompt_asset(info)


def track_policy_asset_to_stage(info: AssetInfo) -> None:
    """Track policy asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    stage_context["policy"] = info
    policies = list(stage_context.get("policies", []))
    policies.append(info)
    stage_context["policies"] = policies
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_policy_asset(info)


def track_mapping_asset_to_stage(info: AssetInfo) -> None:
    """Track mapping asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    stage_context["mapping"] = info
    mappings = list(stage_context.get("mappings", []))
    mappings.append(info)
    stage_context["mappings"] = mappings
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_mapping_asset(info)


def track_source_asset_to_stage(info: AssetInfo) -> None:
    """Track source asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    stage_context["source"] = info
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_source_asset(info)


def track_resolver_asset_to_stage(info: AssetInfo) -> None:
    """Track resolver asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    stage_context["resolver"] = info
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_resolver_asset(info)


def track_tool_asset_to_stage(info: AssetInfo) -> None:
    """Track tool asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    tools = list(stage_context.get("tools", []))
    tools.append(info)
    stage_context["tools"] = tools
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_tool_asset(info)


def track_catalog_asset_to_stage(info: AssetInfo) -> None:
    """Track catalog asset to stage context (in addition to global context)."""
    stage_context = _STAGE_ASSET_CONTEXT.get()
    if stage_context is None:
        stage_context = _initial_context()
    stage_context["catalog"] = info
    _STAGE_ASSET_CONTEXT.set(stage_context)
    # Also track globally
    track_catalog_asset(info)
