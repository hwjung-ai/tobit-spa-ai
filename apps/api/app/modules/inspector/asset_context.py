from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict, List

AssetInfo = Dict[str, Any]


_ASSET_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar("inspector_asset_context", default=None)


def _initial_context() -> Dict[str, Any]:
    return {"prompt": None, "policy": None, "mapping": None, "queries": [], "screens": []}


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
        "policy": context.get("policy"),
        "mapping": context.get("mapping"),
        "queries": list(context.get("queries", [])),
        "screens": list(context.get("screens", [])),
    }


def track_prompt_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["prompt"] = info
    _ASSET_CONTEXT.set(context)


def track_policy_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["policy"] = info
    _ASSET_CONTEXT.set(context)


def track_mapping_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    context["mapping"] = info
    _ASSET_CONTEXT.set(context)


def track_query_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    queries = list(context.get("queries", []))
    queries.append(info)
    context["queries"] = queries
    _ASSET_CONTEXT.set(context)


def track_screen_asset(info: AssetInfo) -> None:
    context = _ensure_context()
    screens = list(context.get("screens", []))
    screens.append(info)
    context["screens"] = screens
    _ASSET_CONTEXT.set(context)
