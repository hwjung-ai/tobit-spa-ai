"""
Generic Planner for Universal Data Orchestration.

This module implements a domain-agnostic planner that uses LLM-based tool
selection to handle questions across any domain. It serves as a fallback
planner when no domain-specific planner matches the question.
"""

from __future__ import annotations

from typing import Any

from core.logging import get_logger
from pydantic import BaseModel, Field

from app.modules.ops.services.orchestration.tools.base import ToolContext
from app.modules.ops.services.domain.base import BaseDomainPlanner, DomainMetadata
from app.modules.ops.services.domain.tool_selector_llm import (
    ToolSelection,
    ToolSelectionResult,
    get_tool_selector,
)

logger = get_logger(__name__)


class GenericPlan(BaseModel):
    """Execution plan for generic queries."""

    question: str = Field(..., description="Original question")
    selected_tools: list[ToolSelection] = Field(
        default_factory=list, description="Selected tools with parameters"
    )
    execution_order: str = Field(
        default="sequential", description="sequential or parallel"
    )
    chain_config: dict[str, Any] | None = Field(
        default=None, description="Tool chaining configuration"
    )

    @property
    def primary_tool(self) -> ToolSelection | None:
        """Get the highest confidence tool."""
        if not self.selected_tools:
            return None
        return max(self.selected_tools, key=lambda t: t.confidence)

    @property
    def tool_names(self) -> list[str]:
        """Get list of selected tool names."""
        return [t.tool_name for t in self.selected_tools]


class GenericPlanner(BaseDomainPlanner):
    """
    Generic domain planner.

    Uses LLM-based tool selection to handle questions across any domain.
    Acts as a fallback when no specific domain planner matches.
    """

    def __init__(self):
        """Initialize the generic planner."""
        self._tool_selector = get_tool_selector()
        self._metadata = DomainMetadata(
            domain="generic",
            description="범용 오케스트레이션 플래너 - 모든 도메인 처리",
            keywords=["검색", "조회", "찾기", "목록", "리스트", "search", "find", "list"],
            priority=0,  # Lowest priority - fallback
        )

    @property
    def domain(self) -> str:
        """Return domain identifier."""
        return "generic"

    @property
    def metadata(self) -> DomainMetadata:
        """Return domain metadata."""
        return self._metadata

    async def classify_confidence(self, question: str) -> float:
        """
        Return classification confidence for the question.

        Generic planner always returns a base confidence (0.3) as fallback.
        """
        # Always available as fallback, but with low confidence
        return 0.3

    async def should_handle(self, question: str) -> bool:
        """
        Check if this planner should handle the question.

        Generic planner can handle any question as fallback.
        """
        return True

    async def create_plan(
        self,
        question: str,
        context: ToolContext,
        options: dict[str, Any] | None = None,
    ) -> GenericPlan:
        """
        Create an execution plan for the question.

        Uses LLM tool selector to find appropriate tools.

        Args:
            question: User question
            context: Execution context
            options: Additional options

        Returns:
            GenericPlan with selected tools
        """
        logger.info(f"GenericPlanner creating plan for: {question[:50]}...")

        # Use LLM to select tools
        selection_result: ToolSelectionResult = await self._tool_selector.select_tools(
            question=question,
            context={"tenant_id": context.tenant_id} if context else None,
        )

        # Analyze for potential chaining
        chain_config = self._analyze_chaining(
            selection_result.tools, question
        )

        plan = GenericPlan(
            question=question,
            selected_tools=selection_result.tools,
            execution_order=selection_result.execution_order,
            chain_config=chain_config,
        )

        logger.info(
            f"GenericPlan created: {len(plan.selected_tools)} tools, "
            f"order={plan.execution_order}"
        )

        return plan

    def _analyze_chaining(
        self, tools: list[ToolSelection], question: str
    ) -> dict[str, Any] | None:
        """
        Analyze if tools should be chained.

        Args:
            tools: Selected tools
            question: Original question

        Returns:
            Chain configuration or None
        """
        if len(tools) <= 1:
            return None

        # Check for chaining keywords
        chaining_keywords = [
            "그리고", "이후", "다음", "결과로", "연결",
            "and then", "after", "with", "using result"
        ]

        question_lower = question.lower()
        has_chaining = any(kw in question_lower for kw in chaining_keywords)

        if not has_chaining:
            return None

        # Build simple sequential chain config
        chain_steps = []
        for i, tool in enumerate(tools):
            step = {
                "step_id": f"step_{i}",
                "tool_name": tool.tool_name,
                "parameters": tool.parameters,
            }
            if i > 0:
                step["depends_on"] = [f"step_{i-1}"]
            chain_steps.append(step)

        return {
            "chain_id": "auto_chain",
            "steps": chain_steps,
            "execution_mode": "sequential",
        }


# Global planner instance
_global_generic_planner: GenericPlanner | None = None


def get_generic_planner() -> GenericPlanner:
    """Get the global generic planner instance."""
    global _global_generic_planner
    if _global_generic_planner is None:
        _global_generic_planner = GenericPlanner()
    return _global_generic_planner
