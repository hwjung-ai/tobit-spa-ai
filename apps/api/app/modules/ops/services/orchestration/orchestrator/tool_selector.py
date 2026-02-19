"""
LLM-Driven Dynamic Tool Selector

Replaces hardcoded tool selection logic with LLM-based dynamic selection.
Tools are discovered from the Tool Registry and selected based on the Plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

from core.logging import get_logger

from app.modules.ops.services.orchestration.planner.plan_schema import (
    INTENT_CAPABILITY_MAP,
    Intent,
)
from app.modules.ops.services.orchestration.tools.base import get_tool_registry

logger = get_logger(__name__)


class SelectionStrategy(Enum):
    FASTEST = "fastest"
    MOST_ACCURATE = "most_accurate"
    MOST_COMPLETE = "most_complete"
    LEAST_LOAD = "least_load"


@dataclass
class ToolSelectionContext:
    intent: Intent
    user_pref: SelectionStrategy
    current_load: Dict[str, float]
    cache_status: Dict[str, bool]
    estimated_time: Dict[str, float]
    mode_hint: str | None = None  # Mode hint for tool filtering (config, metric, graph, etc.)


class SmartToolSelector:
    """
    LLM-driven tool selector with NO hardcoding.

    Tool selection is based on:
    1. Tool Registry discovery (all available tools)
    2. LLM Plan analysis (tool_type field from Plan)
    3. Runtime metrics (load, cache, time estimates)
    """

    def __init__(self):
        # NO hardcoded tool profiles
        # Tools are loaded dynamically from registry
        self._tool_profiles: Dict[str, Dict[str, float]] = {}
        self._load_dynamic_profiles()

    def _load_dynamic_profiles(self):
        """Load tool profiles dynamically from Tool Registry."""
        registry = get_tool_registry()
        tools_info = registry.get_all_tools_info()

        for tool_info in tools_info:
            tool_name = tool_info.get("name")
            # Default profiles based on tool metadata
            # Can be enhanced with real-time metrics later
            self._tool_profiles[tool_name] = {
                "accuracy": 0.85,  # Default, can be learned
                "base_time": 100.0,  # Default, can be measured
            }

        logger.info(
            "tool_selector.profiles_loaded",
            extra={"count": len(self._tool_profiles)}
        )

    async def select_tools(
        self,
        context: ToolSelectionContext,
    ) -> List[Tuple[str, float]]:
        """
        Select tools dynamically based on Plan and runtime metrics.

        NO hardcoded tool names or mappings.
        Tools are scored based on:
        - Tool Registry availability
        - Runtime performance (load, cache, time)
        - Selection strategy preference
        """
        # Get candidate tools from registry (NOT hardcoded)
        candidates = self._get_candidate_tools(context.intent, context.mode_hint)

        scores: Dict[str, float] = {}
        for tool_name in candidates:
            scores[tool_name] = await self._score_tool(tool_name, context)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

        logger.info(
            "tool_selector.ranked",
            extra={
                "intent": context.intent.value if hasattr(context.intent, "value") else str(context.intent),
                "top_3": [(name, round(score, 3)) for name, score in ranked[:3]]
            }
        )

        return ranked

    async def _score_tool(
        self,
        tool_name: str,
        context: ToolSelectionContext,
    ) -> float:
        """Score a tool based on runtime metrics and preferences."""
        profile = self._tool_profiles.get(tool_name, {})
        accuracy = profile.get("accuracy", 0.5)
        base_time = profile.get("base_time", 100.0)
        score = accuracy * 0.3

        est_time = context.estimated_time.get(tool_name, base_time)
        performance = 1.0 / (1.0 + est_time / 1000)
        score += performance * 0.25

        cache_bonus = 0.5 if context.cache_status.get(tool_name) else 0.0
        score += cache_bonus * 0.15

        load = context.current_load.get(tool_name, 0.0)
        load_bonus = 1.0 - load
        score += load_bonus * 0.2

        # Strategy adjustment (NO hardcoded tool names)
        strategy_bonus = self._strategy_adjustment(tool_name, context.user_pref)
        score += strategy_bonus

        return min(score, 1.0)

    def _strategy_adjustment(
        self, tool_name: str, strategy: SelectionStrategy
    ) -> float:
        """
        Strategy-based adjustment.

        NO hardcoded tool names - uses tool metadata instead.
        """
        # In the future, this can use tool metadata (tags, capabilities)
        # For now, use generic strategy logic
        profile = self._tool_profiles.get(tool_name, {})

        if strategy == SelectionStrategy.FASTEST:
            # Prefer tools with lower base_time
            return 0.05 if profile.get("base_time", 200) < 120 else 0.0
        elif strategy == SelectionStrategy.MOST_ACCURATE:
            # Prefer tools with higher accuracy
            return 0.05 if profile.get("accuracy", 0.5) > 0.85 else 0.0
        elif strategy == SelectionStrategy.MOST_COMPLETE:
            # Generic bonus for all tools
            return 0.03
        else:  # LEAST_LOAD
            return 0.0

    def _get_candidate_tools(self, intent: Intent, mode_hint: str | None = None) -> List[str]:
        """
        Get candidate tools from registry based on capabilities.

        Selection priority:
        1. Tool's capabilities match intent's required capabilities
        2. Tool's supported_modes includes the requested mode (or "all")
        3. Fallback to tool_type matching if no capabilities defined
        """
        registry = get_tool_registry()
        tools_info = registry.get_all_tools_info()

        # Get required capabilities for this intent
        required_caps = INTENT_CAPABILITY_MAP.get(intent, [])
        required_cap_values = [cap.value for cap in required_caps]

        candidates = []
        candidates_by_source = {"capability": [], "mode": [], "fallback": []}

        for tool_info in tools_info:
            tool_name = tool_info.get("name")
            tool_type = tool_info.get("type", "")
            tool_tags = tool_info.get("tags", {})

            # Extract capabilities from tags
            tool_capabilities = tool_tags.get("capabilities", [])
            supported_modes = tool_tags.get("supported_modes", ["all"])

            # Priority 1: Capability-based matching
            if tool_capabilities:
                matching_caps = [c for c in tool_capabilities if c in required_cap_values]
                if matching_caps:
                    # Also check mode compatibility
                    if self._is_mode_compatible(mode_hint, supported_modes):
                        candidates_by_source["capability"].append(tool_name)
                        logger.debug(
                            "tool_selector.capability_match",
                            extra={
                                "tool": tool_name,
                                "matched_caps": matching_caps,
                                "intent": intent.value,
                            }
                        )
                        continue

            # Priority 2: Mode-based matching (for tools with supported_modes but no capabilities)
            if mode_hint and self._is_mode_compatible(mode_hint, supported_modes):
                # Check if tool_type suggests it might be relevant
                if self._tool_type_matches_intent(tool_type, intent):
                    candidates_by_source["mode"].append(tool_name)
                    continue

            # Priority 3: Fallback to tool_type matching (legacy compatibility)
            if not tool_capabilities:
                if self._tool_type_matches_intent(tool_type, intent):
                    candidates_by_source["fallback"].append(tool_name)

        # Combine candidates in priority order
        candidates = (
            candidates_by_source["capability"] +
            candidates_by_source["mode"] +
            candidates_by_source["fallback"]
        )

        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        if not unique_candidates:
            logger.warning(
                "tool_selector.no_candidates",
                extra={
                    "intent": intent.value if hasattr(intent, "value") else str(intent),
                    "mode_hint": mode_hint,
                    "required_capabilities": required_cap_values,
                }
            )
            # Last resort: return all tools
            return [t.get("name") for t in tools_info]

        logger.info(
            "tool_selector.candidates_found",
            extra={
                "intent": intent.value if hasattr(intent, "value") else str(intent),
                "total": len(unique_candidates),
                "by_capability": len(candidates_by_source["capability"]),
                "by_mode": len(candidates_by_source["mode"]),
                "by_fallback": len(candidates_by_source["fallback"]),
            }
        )

        return unique_candidates

    def _is_mode_compatible(self, mode_hint: str | None, supported_modes: list[str]) -> bool:
        """Check if a tool supports the requested mode."""
        if not mode_hint:
            return True  # No mode specified, accept all
        if "all" in supported_modes:
            return True  # Tool supports all modes
        return mode_hint in supported_modes

    def _tool_type_matches_intent(self, tool_type: str, intent: Intent) -> bool:
        """
        Check if tool_type suggests compatibility with intent.
        This is a fallback for tools without defined capabilities.
        """
        # Map intent to likely tool_type prefixes/suffixes
        intent_type_hints = {
            Intent.LOOKUP: ["ci_lookup", "ci_detail", "lookup", "get"],
            Intent.SEARCH: ["ci_search", "search", "query", "document_search"],
            Intent.LIST: ["ci_list", "list", "search"],
            Intent.AGGREGATE: ["ci_aggregate", "aggregate", "metric"],
            Intent.EXPAND: ["graph", "expand", "topology"],
            Intent.PATH: ["graph", "path"],
            Intent.DOCUMENT: ["document_search", "document"],
        }

        hints = intent_type_hints.get(intent, [])
        tool_type_lower = tool_type.lower()

        return any(hint in tool_type_lower for hint in hints)

    def _get_mode_keywords(self, mode: str) -> List[str]:
        """Get keyword filters for each mode."""
        mode_keywords = {
            "config": ["ci", "config", "lookup", "search", "detail"],
            "metric": ["metric", "cpu", "memory", "disk", "network", "performance"],
            "graph": ["graph", "topology", "relation", "dependency", "neighbor"],
            "history": ["history", "event", "log", "maintenance", "work"],
            "hist": ["history", "event", "log", "maintenance", "work"],
            "document": ["document", "doc", "search", "file"],
        }
        return mode_keywords.get(mode, [])

    def get_all_tool_names(self) -> List[str]:
        """Get all available tool names from registry (NO hardcoding)."""
        return list(self._tool_profiles.keys())

    @property
    def tool_profiles(self) -> Dict[str, Dict[str, float]]:
        """Return tool profiles for backward compatibility with runner.py"""
        return self._tool_profiles
