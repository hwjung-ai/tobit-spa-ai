"""Orchestrator utilities package.

This package contains utility modules extracted from runner.py,
organized by functional area.
"""

from .blocks import (
    build_graph_payload_from_tool_data,
    build_history_blocks_from_data,
    build_metric_blocks_from_data,
)
from .ci_keywords import (
    build_ci_search_keywords,
    extract_ci_identifiers,
    has_ci_identifier_in_keywords,
    recover_ci_identifiers,
    routing_identifiers,
    sanitize_ci_keywords,
)
from .graph_utils import (
    is_graph_requested,
    should_list_fallthrough_to_lookup,
)
from .history import history_fallback_for_question
from .metadata import (
    format_asset_display,
    log_metric_blocks_return,
    resolve_applied_assets,
    resolve_applied_assets_from_assets,
)
from .next_actions import NextActionsHelper
from .references import (
    ensure_reference_fallback,
    extract_references_from_blocks,
    reference_from_tool_call,
)

__all__ = [
    "build_graph_payload_from_tool_data",
    "build_history_blocks_from_data",
    "build_metric_blocks_from_data",
    "build_ci_search_keywords",
    "extract_ci_identifiers",
    "has_ci_identifier_in_keywords",
    "recover_ci_identifiers",
    "routing_identifiers",
    "sanitize_ci_keywords",
    "is_graph_requested",
    "should_list_fallthrough_to_lookup",
    "history_fallback_for_question",
    "format_asset_display",
    "log_metric_blocks_return",
    "resolve_applied_assets",
    "resolve_applied_assets_from_assets",
    "ensure_reference_fallback",
    "extract_references_from_blocks",
    "reference_from_tool_call",
    "NextActionsHelper",
]
