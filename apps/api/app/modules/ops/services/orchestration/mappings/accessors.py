from __future__ import annotations

import re

from app.modules.ops.services.orchestration.planner.plan_schema import View

from .registry import get_mapping, get_mapping_registry

# Runtime caches
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


def _active_mapping(mapping_type: str) -> dict:
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name(mapping_type)
    mapping = get_mapping(active_name)
    if not isinstance(mapping, dict):
        raise ValueError(f"Invalid mapping payload for '{active_name}'")
    return mapping


def _get_metric_aliases():
    global _METRIC_ALIASES_CACHE
    if _METRIC_ALIASES_CACHE is not None:
        return _METRIC_ALIASES_CACHE
    _METRIC_ALIASES_CACHE = _active_mapping("metric_aliases")
    return _METRIC_ALIASES_CACHE


def _get_agg_keywords():
    global _AGG_KEYWORDS_CACHE
    if _AGG_KEYWORDS_CACHE is not None:
        return _AGG_KEYWORDS_CACHE
    mapping = _active_mapping("agg_keywords")
    _AGG_KEYWORDS_CACHE = mapping.get("mappings", {})
    return _AGG_KEYWORDS_CACHE


def _get_series_keywords():
    global _SERIES_KEYWORDS_CACHE
    if _SERIES_KEYWORDS_CACHE is not None:
        return _SERIES_KEYWORDS_CACHE
    mapping = _active_mapping("series_keywords")
    _SERIES_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _SERIES_KEYWORDS_CACHE


def _get_history_keywords():
    global _HISTORY_KEYWORDS_CACHE
    if _HISTORY_KEYWORDS_CACHE is not None and _HISTORY_KEYWORDS_CACHE.get("keywords"):
        return _HISTORY_KEYWORDS_CACHE
    mapping = _active_mapping("history_keywords")
    _HISTORY_KEYWORDS_CACHE = {
        "keywords": set(mapping.get("keywords", [])),
        "time_map": mapping.get("time_map", {}),
    }
    return _HISTORY_KEYWORDS_CACHE


def _get_list_keywords():
    global _LIST_KEYWORDS_CACHE
    if _LIST_KEYWORDS_CACHE is not None:
        return _LIST_KEYWORDS_CACHE
    mapping = _active_mapping("list_keywords")
    _LIST_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _LIST_KEYWORDS_CACHE


def _get_table_hints():
    global _TABLE_HINTS_CACHE
    if _TABLE_HINTS_CACHE is not None:
        return _TABLE_HINTS_CACHE
    mapping = _active_mapping("table_hints")
    _TABLE_HINTS_CACHE = set(mapping.get("keywords", []))
    return _TABLE_HINTS_CACHE


def _get_cep_keywords():
    global _CEP_KEYWORDS_CACHE
    if _CEP_KEYWORDS_CACHE is not None:
        return _CEP_KEYWORDS_CACHE
    mapping = _active_mapping("cep_keywords")
    _CEP_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _CEP_KEYWORDS_CACHE


def _get_graph_scope_keywords():
    global _GRAPH_SCOPE_KEYWORDS_CACHE
    if _GRAPH_SCOPE_KEYWORDS_CACHE is not None:
        return _GRAPH_SCOPE_KEYWORDS_CACHE
    mapping = _active_mapping("graph_scope_keywords")
    _GRAPH_SCOPE_KEYWORDS_CACHE = {
        "scope_keywords": set(mapping.get("scope_keywords", [])),
        "metric_keywords": set(mapping.get("metric_keywords", [])),
    }
    return _GRAPH_SCOPE_KEYWORDS_CACHE


def _get_auto_keywords():
    global _AUTO_KEYWORDS_CACHE
    if _AUTO_KEYWORDS_CACHE is not None:
        return _AUTO_KEYWORDS_CACHE
    mapping = _active_mapping("auto_keywords")
    _AUTO_KEYWORDS_CACHE = set(mapping.get("keywords", []))
    return _AUTO_KEYWORDS_CACHE


def _get_filterable_fields():
    global _FILTERABLE_FIELDS_CACHE
    if _FILTERABLE_FIELDS_CACHE is not None:
        return _FILTERABLE_FIELDS_CACHE
    mapping = _active_mapping("filterable_fields")
    _FILTERABLE_FIELDS_CACHE = {
        "tag_filter_keys": set(mapping.get("tag_filter_keys", [])),
        "attr_filter_keys": set(mapping.get("attr_filter_keys", [])),
    }
    return _FILTERABLE_FIELDS_CACHE


def _get_ci_code_patterns():
    mapping = get_mapping("ci_code_patterns")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'ci_code_patterns'")
    patterns = mapping.get("patterns", [])
    if not patterns:
        raise ValueError("Missing patterns in 'ci_code_patterns' mapping")
    return re.compile(patterns[0], re.IGNORECASE)


def _get_graph_view_keyword_map():
    mapping = get_mapping("graph_view_keywords")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'graph_view_keywords'")
    keyword_map = mapping.get("view_keyword_map", {})
    view_map = {}
    for keyword, view_name in keyword_map.items():
        try:
            view_map[keyword] = View[view_name]
        except (KeyError, TypeError):
            continue
    return view_map


def _get_graph_view_default_depth():
    mapping = get_mapping("graph_view_keywords")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'graph_view_keywords'")
    depths = mapping.get("default_depths", {})
    depth_map = {}
    for view_name, depth in depths.items():
        try:
            depth_map[View[view_name]] = depth
        except (KeyError, TypeError):
            continue
    return depth_map


def _get_auto_view_preferences():
    mapping = get_mapping("auto_view_preferences")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'auto_view_preferences'")
    preferences = mapping.get("preferences", [])

    result = []
    for pref in preferences:
        keywords = pref.get("keywords", [])
        views = pref.get("views", [])
        view_enums = []
        for view_name in views:
            try:
                view_enums.append(View[view_name])
            except (KeyError, TypeError):
                continue
        if keywords and view_enums:
            result.append((keywords, view_enums))
    return result


def _get_output_type_priorities():
    mapping = get_mapping("output_type_priorities")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'output_type_priorities'")
    return mapping.get("global_priorities", [])


def _get_graph_scope_views():
    mapping = get_mapping("graph_view_keywords")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'graph_view_keywords'")
    force_keywords = mapping.get("force_keywords", [])
    return set(force_keywords)
