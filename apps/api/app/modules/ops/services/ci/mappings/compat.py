"""
Backward compatibility layer for mapping functions.

Provides the same function signatures as the old hardcoded functions,
but loads data from the mapping registry instead.
"""
from __future__ import annotations

import re

from app.modules.ops.services.ci.planner.plan_schema import View

from .registry import get_mapping

# Cache variables (maintain same interface as old code)
_METRIC_ALIASES_CACHE = None
_AGG_KEYWORDS_CACHE = None
_SERIES_KEYWORDS_CACHE = None
_HISTORY_KEYWORDS_CACHE = None
_LIST_KEYWORDS_CACHE = None
_TABLE_HINTS_CACHE = None
_CEP_KEYWORDS_CACHE = None
_GRAPH_SCOPE_KEYWORDS_CACHE = None
_AUTO_KEYWORDS_CACHE = None
_FILTERABLE_FIELDS_CACHE = None


def _get_metric_aliases():
    """Get metric aliases mapping from registry (uses active version)."""
    global _METRIC_ALIASES_CACHE
    if _METRIC_ALIASES_CACHE is not None:
        return _METRIC_ALIASES_CACHE

    # Get the active mapping name (default: "metric_aliases", or custom like "metric_aliases_v2")
    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("metric_aliases")

    mapping = get_mapping(active_name)
    _METRIC_ALIASES_CACHE = mapping
    return _METRIC_ALIASES_CACHE


def _get_agg_keywords():
    """Get aggregation keywords mapping from registry (uses active version)."""
    global _AGG_KEYWORDS_CACHE
    if _AGG_KEYWORDS_CACHE is not None:
        return _AGG_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("agg_keywords")
    mapping = get_mapping(active_name)
    _AGG_KEYWORDS_CACHE = mapping.get("mappings", {})
    return _AGG_KEYWORDS_CACHE


def _get_series_keywords():
    """Get series keywords from registry (uses active version)."""
    global _SERIES_KEYWORDS_CACHE
    if _SERIES_KEYWORDS_CACHE is not None:
        return _SERIES_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("series_keywords")
    mapping = get_mapping(active_name)
    _SERIES_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _SERIES_KEYWORDS_CACHE


def _get_history_keywords():
    """Get history keywords from registry (uses active version)."""
    global _HISTORY_KEYWORDS_CACHE
    if _HISTORY_KEYWORDS_CACHE is not None:
        return _HISTORY_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("history_keywords")
    mapping = get_mapping(active_name)
    _HISTORY_KEYWORDS_CACHE = {
        "keywords": set(mapping.get("keywords", [])),
        "time_map": mapping.get("time_map", {}),
    }
    return _HISTORY_KEYWORDS_CACHE


def _get_list_keywords():
    """Get list keywords from registry (uses active version)."""
    global _LIST_KEYWORDS_CACHE
    if _LIST_KEYWORDS_CACHE is not None:
        return _LIST_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("list_keywords")
    mapping = get_mapping(active_name)
    _LIST_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _LIST_KEYWORDS_CACHE


def _get_table_hints():
    """Get table hint keywords from registry (uses active version)."""
    global _TABLE_HINTS_CACHE
    if _TABLE_HINTS_CACHE is not None:
        return _TABLE_HINTS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("table_hints")
    mapping = get_mapping(active_name)
    _TABLE_HINTS_CACHE = set(mapping.get("keywords", []))
    return _TABLE_HINTS_CACHE


def _get_cep_keywords():
    """Get CEP keywords from registry (uses active version)."""
    global _CEP_KEYWORDS_CACHE
    if _CEP_KEYWORDS_CACHE is not None:
        return _CEP_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("cep_keywords")
    mapping = get_mapping(active_name)
    _CEP_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _CEP_KEYWORDS_CACHE


def _get_graph_scope_keywords():
    """Get graph scope keywords from registry (uses active version)."""
    global _GRAPH_SCOPE_KEYWORDS_CACHE
    if _GRAPH_SCOPE_KEYWORDS_CACHE is not None:
        return _GRAPH_SCOPE_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("graph_scope_keywords")
    mapping = get_mapping(active_name)
    _GRAPH_SCOPE_KEYWORDS_CACHE = {
        "scope_keywords": set(mapping.get("scope_keywords", [])),
        "metric_keywords": set(mapping.get("metric_keywords", [])),
    }
    return _GRAPH_SCOPE_KEYWORDS_CACHE


def _get_auto_keywords():
    """Get auto keywords from registry (uses active version)."""
    global _AUTO_KEYWORDS_CACHE
    if _AUTO_KEYWORDS_CACHE is not None:
        return _AUTO_KEYWORDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("auto_keywords")
    mapping = get_mapping(active_name)
    _AUTO_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _AUTO_KEYWORDS_CACHE


def _get_filterable_fields():
    """Get filterable fields from registry (BUG FIX #1, uses active version)."""
    global _FILTERABLE_FIELDS_CACHE
    if _FILTERABLE_FIELDS_CACHE is not None:
        return _FILTERABLE_FIELDS_CACHE

    from .registry import get_mapping_registry
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name("filterable_fields")
    mapping = get_mapping(active_name)
    # FIX: Use consistent key names (tag_filter_keys, attr_filter_keys)
    _FILTERABLE_FIELDS_CACHE = {
        "tag_filter_keys": set(mapping.get("tag_filter_keys", [])),
        "attr_filter_keys": set(mapping.get("attr_filter_keys", [])),
    }
    return _FILTERABLE_FIELDS_CACHE


def _get_ci_code_patterns():
    """Get CI code pattern from registry."""
    mapping = get_mapping("ci_code_patterns")
    patterns = mapping.get("patterns", [])
    if patterns:
        return re.compile(patterns[0], re.IGNORECASE)
    # Fallback pattern
    return re.compile(r"\b(?:sys|srv|app|was|storage|sec|db)[-\w]+\b", re.IGNORECASE)


def _get_graph_view_keyword_map():
    """Get graph view keyword mapping from registry."""
    mapping = get_mapping("graph_view_keywords")
    keyword_map = mapping.get("view_keyword_map", {})

    # Convert string view names to View enum
    view_map = {}
    for keyword, view_name in keyword_map.items():
        try:
            view_map[keyword] = View[view_name]
        except (KeyError, TypeError):
            pass

    return view_map


def _get_graph_view_default_depth():
    """Get graph view default depths from registry."""
    mapping = get_mapping("graph_view_keywords")
    depths = mapping.get("default_depths", {})

    # Convert string view names to View enum
    depth_map = {}
    for view_name, depth in depths.items():
        try:
            depth_map[View[view_name]] = depth
        except (KeyError, TypeError):
            pass

    return depth_map


def _get_auto_view_preferences():
    """Get auto view preferences from registry."""
    mapping = get_mapping("auto_view_preferences")
    preferences = mapping.get("preferences", [])

    result = []
    for pref in preferences:
        keywords = pref.get("keywords", [])
        views = pref.get("views", [])

        # Convert string view names to View enum
        view_enums = []
        for view_name in views:
            try:
                view_enums.append(View[view_name])
            except (KeyError, TypeError):
                pass

        if keywords and view_enums:
            result.append((keywords, view_enums))

    return result


def _get_output_type_priorities():
    """Get output type priorities from registry."""
    mapping = get_mapping("output_type_priorities")
    return mapping.get("global_priorities", [])


def _get_graph_scope_views():
    """Get graph scope views from registry."""
    mapping = get_mapping("graph_view_keywords")
    force_keywords = mapping.get("force_keywords", [])
    return set(force_keywords)
