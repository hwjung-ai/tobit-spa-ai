from __future__ import annotations

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
_PLANNER_KEYWORDS_CACHE = None
_PLANNER_DEFAULTS_CACHE = None


def _active_mapping(mapping_type: str) -> dict:
    registry = get_mapping_registry()
    active_name = registry.get_active_mapping_name(mapping_type)
    mapping = get_mapping(active_name)
    if not isinstance(mapping, dict):
        raise ValueError(f"Invalid mapping payload for '{active_name}'")
    return mapping


def _get_planner_keywords() -> dict:
    global _PLANNER_KEYWORDS_CACHE
    if _PLANNER_KEYWORDS_CACHE is not None:
        return _PLANNER_KEYWORDS_CACHE
    mapping = get_mapping("planner_keywords")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'planner_keywords'")
    _PLANNER_KEYWORDS_CACHE = mapping
    return mapping


def _get_planner_defaults() -> dict:
    global _PLANNER_DEFAULTS_CACHE
    if _PLANNER_DEFAULTS_CACHE is not None:
        return _PLANNER_DEFAULTS_CACHE
    mapping = get_mapping("planner_defaults")
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'planner_defaults'")
    _PLANNER_DEFAULTS_CACHE = mapping
    return mapping


def _get_metric_aliases():
    global _METRIC_ALIASES_CACHE
    if _METRIC_ALIASES_CACHE is not None:
        return _METRIC_ALIASES_CACHE
    planner_keywords = _get_planner_keywords()
    payload = planner_keywords.get("metric_aliases", {})
    if not isinstance(payload, dict):
        payload = {}
    _METRIC_ALIASES_CACHE = payload
    return _METRIC_ALIASES_CACHE


def _get_agg_keywords():
    global _AGG_KEYWORDS_CACHE
    if _AGG_KEYWORDS_CACHE is not None:
        return _AGG_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("agg_keywords", {})
    if isinstance(mapping, dict):
        _AGG_KEYWORDS_CACHE = mapping.get("mappings", mapping)
    else:
        _AGG_KEYWORDS_CACHE = {}
    return _AGG_KEYWORDS_CACHE


def _get_series_keywords():
    global _SERIES_KEYWORDS_CACHE
    if _SERIES_KEYWORDS_CACHE is not None:
        return _SERIES_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("series_keywords", {})
    if isinstance(mapping, dict):
        values = mapping.get("keywords", [])
    elif isinstance(mapping, list):
        values = mapping
    else:
        values = []
    _SERIES_KEYWORDS_CACHE = set(values)
    return _SERIES_KEYWORDS_CACHE


def _get_history_keywords():
    global _HISTORY_KEYWORDS_CACHE
    if _HISTORY_KEYWORDS_CACHE is not None and _HISTORY_KEYWORDS_CACHE.get("keywords"):
        return _HISTORY_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("history_keywords", {})
    if not isinstance(mapping, dict):
        mapping = {}
    _HISTORY_KEYWORDS_CACHE = {
        "keywords": set(mapping.get("keywords", [])),
        "time_map": mapping.get("time_map", {}),
    }
    return _HISTORY_KEYWORDS_CACHE


def _get_list_keywords():
    global _LIST_KEYWORDS_CACHE
    if _LIST_KEYWORDS_CACHE is not None:
        return _LIST_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("list_keywords", {})
    if isinstance(mapping, dict):
        values = mapping.get("keywords", [])
    elif isinstance(mapping, list):
        values = mapping
    else:
        values = []
    _LIST_KEYWORDS_CACHE = set(values)
    return _LIST_KEYWORDS_CACHE


def _get_table_hints():
    global _TABLE_HINTS_CACHE
    if _TABLE_HINTS_CACHE is not None:
        return _TABLE_HINTS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("table_hints", {})
    if isinstance(mapping, dict):
        values = mapping.get("keywords", [])
    elif isinstance(mapping, list):
        values = mapping
    else:
        values = []
    _TABLE_HINTS_CACHE = set(values)
    return _TABLE_HINTS_CACHE


def _get_cep_keywords():
    global _CEP_KEYWORDS_CACHE
    if _CEP_KEYWORDS_CACHE is not None:
        return _CEP_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("cep_keywords", {})
    if isinstance(mapping, dict):
        values = mapping.get("keywords", [])
    elif isinstance(mapping, list):
        values = mapping
    else:
        values = []
    _CEP_KEYWORDS_CACHE = set(values)
    return _CEP_KEYWORDS_CACHE


def _get_graph_scope_keywords():
    global _GRAPH_SCOPE_KEYWORDS_CACHE
    if _GRAPH_SCOPE_KEYWORDS_CACHE is not None:
        return _GRAPH_SCOPE_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("graph_scope_keywords", {})
    if not isinstance(mapping, dict):
        mapping = {}
    _GRAPH_SCOPE_KEYWORDS_CACHE = {
        "scope_keywords": set(mapping.get("scope_keywords", [])),
        "metric_keywords": set(mapping.get("metric_keywords", [])),
    }
    return _GRAPH_SCOPE_KEYWORDS_CACHE


def _get_auto_keywords():
    global _AUTO_KEYWORDS_CACHE
    if _AUTO_KEYWORDS_CACHE is not None:
        return _AUTO_KEYWORDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("auto_keywords", {})
    if isinstance(mapping, dict):
        values = mapping.get("keywords", [])
    elif isinstance(mapping, list):
        values = mapping
    else:
        values = []
    _AUTO_KEYWORDS_CACHE = set(values)
    return _AUTO_KEYWORDS_CACHE


def _get_filterable_fields():
    global _FILTERABLE_FIELDS_CACHE
    if _FILTERABLE_FIELDS_CACHE is not None:
        return _FILTERABLE_FIELDS_CACHE
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("filterable_fields", {})
    if not isinstance(mapping, dict):
        mapping = {}
    _FILTERABLE_FIELDS_CACHE = {
        "tag_filter_keys": set(mapping.get("tag_filter_keys", [])),
        "attr_filter_keys": set(mapping.get("attr_filter_keys", [])),
    }
    return _FILTERABLE_FIELDS_CACHE


def _get_graph_view_keyword_map():
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("graph_view_keywords", {})
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
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("graph_view_keywords", {})
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
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("auto_view_preferences", {})
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
    defaults = _get_planner_defaults()
    mapping = defaults.get("output_type_priorities", {})
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'output_type_priorities'")
    return mapping.get("global_priorities", [])


def _get_graph_scope_views():
    planner_keywords = _get_planner_keywords()
    mapping = planner_keywords.get("graph_view_keywords", {})
    if not isinstance(mapping, dict):
        raise ValueError("Invalid mapping payload for 'graph_view_keywords'")
    force_keywords = mapping.get("force_keywords", [])
    return set(force_keywords)
