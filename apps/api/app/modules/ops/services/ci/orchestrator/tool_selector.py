from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

from app.modules.ops.services.ci.planner.plan_schema import Intent


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


class SmartToolSelector:
    def __init__(self):
        self._tool_profiles = self._load_tool_profiles()

    async def select_tools(
        self,
        context: ToolSelectionContext,
    ) -> List[Tuple[str, float]]:
        candidates = self._get_candidate_tools(context.intent)

        scores: Dict[str, float] = {}
        for tool_name in candidates:
            scores[tool_name] = await self._score_tool(tool_name, context)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return ranked

    async def _score_tool(
        self,
        tool_name: str,
        context: ToolSelectionContext,
    ) -> float:
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

        intent_bonus = self._get_intent_bonus(tool_name, context.intent)
        score += intent_bonus * 0.1

        strategy_bonus = self._strategy_adjustment(tool_name, context.user_pref)
        score += strategy_bonus

        return min(score, 1.0)

    def _strategy_adjustment(
        self, tool_name: str, strategy: SelectionStrategy
    ) -> float:
        adjustments = {
            SelectionStrategy.FASTEST: {"CI_SEARCH": 0.05, "METRIC_AGGREGATE": 0.03, "DOCUMENT_SEARCH": 0.04},
            SelectionStrategy.MOST_ACCURATE: {"CI_GET": 0.05, "GRAPH_EXPAND": 0.04, "DOCUMENT_SEARCH": 0.03},
            SelectionStrategy.MOST_COMPLETE: {"GRAPH_PATH": 0.05, "CEP_SIMULATE": 0.04},
            SelectionStrategy.LEAST_LOAD: {},
        }
        return adjustments.get(strategy, {}).get(tool_name, 0.0)

    def _get_candidate_tools(self, intent: Intent) -> List[str]:
        mapping = {
            Intent.SEARCH: ["CI_SEARCH", "CI_GET", "DOCUMENT_SEARCH"],
            Intent.LOOKUP: ["CI_GET", "CI_GET_BY_CODE", "DOCUMENT_SEARCH"],
            Intent.AGGREGATE: ["CI_AGGREGATE", "METRIC_AGGREGATE"],
            Intent.EXPAND: ["GRAPH_EXPAND"],
            Intent.PATH: ["GRAPH_PATH"],
            Intent.LIST: ["CI_LIST_PREVIEW", "CI_SEARCH"],
        }
        return mapping.get(intent, ["CI_SEARCH"])

    def _get_intent_bonus(self, tool_name: str, intent: Intent) -> float:
        intent_map = {
            Intent.SEARCH: {"CI_SEARCH": 0.2, "DOCUMENT_SEARCH": 0.18},
            Intent.LOOKUP: {"CI_GET": 0.2, "CI_GET_BY_CODE": 0.15, "DOCUMENT_SEARCH": 0.12},
            Intent.AGGREGATE: {"CI_AGGREGATE": 0.2, "METRIC_AGGREGATE": 0.15},
            Intent.EXPAND: {"GRAPH_EXPAND": 0.2},
            Intent.PATH: {"GRAPH_PATH": 0.2},
            Intent.LIST: {"CI_LIST_PREVIEW": 0.15},
        }
        return intent_map.get(intent, {}).get(tool_name, 0.0)

    def _load_tool_profiles(self) -> Dict[str, Dict[str, float]]:
        return {
            "CI_SEARCH": {"accuracy": 0.9, "base_time": 120.0},
            "CI_GET": {"accuracy": 0.85, "base_time": 80.0},
            "CI_GET_BY_CODE": {"accuracy": 0.8, "base_time": 90.0},
            "CI_AGGREGATE": {"accuracy": 0.88, "base_time": 140.0},
            "CI_LIST_PREVIEW": {"accuracy": 0.75, "base_time": 150.0},
            "METRIC_AGGREGATE": {"accuracy": 0.92, "base_time": 110.0},
            "METRIC_SERIES": {"accuracy": 0.86, "base_time": 130.0},
            "GRAPH_EXPAND": {"accuracy": 0.84, "base_time": 160.0},
            "GRAPH_PATH": {"accuracy": 0.8, "base_time": 190.0},
            "HISTORY_EVENT_LOG": {"accuracy": 0.78, "base_time": 120.0},
            "CEP_SIMULATE": {"accuracy": 0.79, "base_time": 200.0},
            "DOCUMENT_SEARCH": {"accuracy": 0.82, "base_time": 100.0},
        }

    @property
    def tool_profiles(self) -> Dict[str, Dict[str, float]]:
        return self._tool_profiles
