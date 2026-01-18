from __future__ import annotations

from typing import Dict, Any

from app.modules.ops.services.ci.orchestrator.tool_composition import CompositionPipeline, CompositionStep
from app.modules.ops.services.ci.tools.base import ToolType


COMPOSITION_SEARCH_WITH_CONTEXT = CompositionPipeline([
    CompositionStep(
        tool_type=ToolType.CI,
        operation="search",
        params_transform=lambda params: params,
        error_handling="fail_fast",
    ),
    CompositionStep(
        tool_type=ToolType.METRIC,
        operation="aggregate",
        params_transform=lambda search_result: {
            "ci_ids": [ci["id"] for ci in search_result.get("records", [])],
            "metric_name": "cpu_usage",
            "agg": "avg",
            "time_range": "last_1h",
        },
        error_handling="skip",
    ),
    CompositionStep(
        tool_type=ToolType.HISTORY,
        operation="event_log",
        params_transform=lambda metric_result: {
            "ci_ids": metric_result.get("ci_ids", []),
            "time_range": "last_1h",
            "limit": 10,
        },
        error_handling="skip",
    ),
])


async def execute_search_with_context(executor, keywords: list[str]):
    return await COMPOSITION_SEARCH_WITH_CONTEXT.execute(
        executor,
        {"keywords": keywords, "limit": 10},
    )
