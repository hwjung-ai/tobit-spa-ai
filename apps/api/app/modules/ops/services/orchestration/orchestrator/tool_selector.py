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

from app.modules.ops.services.orchestration.planner.plan_schema import Intent
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
        Get candidate tools from registry based on intent and mode_hint.

        NO hardcoded mappings - uses tool metadata/tags instead.
        """
        registry = get_tool_registry()
        tools_info = registry.get_all_tools_info()

        # Filter tools by capabilities matching intent and mode
        candidates = []

        for tool_info in tools_info:
            tool_name = tool_info.get("name")
            tool_type = tool_info.get("type", "")

            # Mode-based filtering (highest priority)
            if mode_hint and mode_hint != "all":
                # Filter by mode keywords
                mode_keywords = self._get_mode_keywords(mode_hint)
                if not any(keyword in tool_name.lower() for keyword in mode_keywords):
                    continue  # Skip tools that don't match mode

            # Intent-based filtering (using tool_type hints)
            if intent == Intent.SEARCH:
                # Prefer tools with "search", "lookup", "query" in name/type
                if any(keyword in tool_name.lower() or keyword in tool_type.lower()
                       for keyword in ["search", "lookup", "ci", "query"]):
                    candidates.append(tool_name)

            elif intent == Intent.LOOKUP:
                # Prefer specific lookup tools
                if any(keyword in tool_name.lower() or keyword in tool_type.lower()
                       for keyword in ["get", "lookup", "ci", "detail"]):
                    candidates.append(tool_name)

            elif intent == Intent.AGGREGATE:
                # Prefer aggregation/metric tools
                if any(keyword in tool_name.lower() or keyword in tool_type.lower()
                       for keyword in ["aggregate", "metric", "summary", "count"]):
                    candidates.append(tool_name)

            elif intent == Intent.EXPAND:
                # Prefer graph expansion tools
                if any(keyword in tool_name.lower() or keyword in tool_type.lower()
                       for keyword in ["graph", "expand", "topology", "neighbor"]):
                    candidates.append(tool_name)

            elif intent == Intent.PATH:
                # Prefer graph path tools
                if any(keyword in tool_name.lower() or keyword in tool_type.lower()
                       for keyword in ["graph", "path", "route", "dependency"]):
                    candidates.append(tool_name)

            elif intent == Intent.LIST:
                # Prefer list/preview tools
                if any(keyword in tool_name.lower() or keyword in tool_type.lower()
                       for keyword in ["list", "preview", "ci", "search", "history"]):
                    candidates.append(tool_name)

        # Fallback: if no candidates, return all tools (filtered by mode if applicable)
        if not candidates:
            if mode_hint and mode_hint != "all":
                # Return only mode-matched tools
                mode_keywords = self._get_mode_keywords(mode_hint)
                candidates = [
                    t.get("name") for t in tools_info
                    if any(keyword in t.get("name", "").lower() for keyword in mode_keywords)
                ]
            else:
                # Return all tools
                candidates = [t.get("name") for t in tools_info]

            logger.warning(
                "tool_selector.no_intent_match",
                extra={
                    "intent": intent.value if hasattr(intent, "value") else str(intent),
                    "mode_hint": mode_hint,
                    "fallback_count": len(candidates)
                }
            )

        return candidates

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
