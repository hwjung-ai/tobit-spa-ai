"""
CI Domain Planner - Planner for CI (Configuration Item) domain.

This module implements the CI-specific planner by wrapping the existing
planner_llm.py functions into a BaseDomainPlanner interface.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.modules.ops.services.domain.base import BaseDomainPlanner, DomainMetadata
from app.modules.ops.services.orchestration.planner.plan_schema import PlanOutput

logger = logging.getLogger(__name__)

# Import the existing CI planner functions
from app.modules.ops.services.orchestration.planner import planner_llm


class CIPlanner(BaseDomainPlanner):
    """
    CI Domain Planner.

    Handles questions related to IT infrastructure, Configuration Items (CI),
    servers, applications, and their metrics and relationships.
    """

    # CI-specific patterns
    CI_CODE_PATTERN = re.compile(
        r"\b(?:sys|srv|app|was|storage|sec|db)[-\w]+\b",
        re.IGNORECASE
    )

    INFRA_KEYWORDS = {
        "구성", "구성정보", "상태", "정보", "메트릭", "cpu", "memory",
        "서버", "server", "database", "db", "app", "application",
        "인프라", "infrastructure", "장비", "equipment"
    }

    METRIC_KEYWORDS = {
        "cpu", "사용량", "memory", "메모리", "disk", "디스크",
        "traffic", "트래픽", "response", "응답", "latency", "지연"
    }

    @property
    def domain(self) -> str:
        """Return the domain name."""
        return "ci"

    @property
    def metadata(self) -> DomainMetadata:
        """Return CI domain metadata."""
        return DomainMetadata(
            name="ci",
            description="IT 인프라, 서버, 애플리케이션 구성 정보 및 메트릭",
            keywords=list(self.INFRA_KEYWORDS) + list(self.METRIC_KEYWORDS),
            code_patterns=[self.CI_CODE_PATTERN.pattern],
            confidence_threshold=0.7,
        )

    async def should_handle(self, question: str) -> bool:
        """
        Determine if this is a CI domain question.

        Checks for:
        1. CI code patterns (sys-xxx, srv-xxx, etc.)
        2. Infrastructure keywords
        3. Metric keywords

        Args:
            question: User question to analyze

        Returns:
            True if this appears to be a CI question
        """
        normalized = question.lower()

        # Check for CI code patterns
        if self.CI_CODE_PATTERN.search(normalized):
            return True

        # Check for infrastructure keywords
        if any(kw in normalized for kw in self.INFRA_KEYWORDS):
            return True

        # Check for metric keywords
        if any(kw in normalized for kw in self.METRIC_KEYWORDS):
            return True

        return False

    async def create_plan(
        self,
        question: str,
        schema_context: dict[str, Any] | None = None,
        source_context: dict[str, Any] | None = None,
    ) -> PlanOutput:
        """
        Create a CI-specific plan using the existing planner_llm functions.

        Args:
            question: User question
            schema_context: Optional schema catalog information
            source_context: Optional source connection information

        Returns:
            PlanOutput with the generated CI plan
        """
        # Delegate to the existing CI planner function
        return planner_llm.create_plan_output(
            question=question,
            schema_context=schema_context,
            source_context=source_context,
        )

    async def classify_confidence(self, question: str) -> float:
        """
        Return confidence score for CI domain handling this question.

        Higher confidence if:
        - CI code pattern matches
        - Multiple infrastructure/ metric keywords match

        Args:
            question: User question to analyze

        Returns:
            Confidence score between 0.0 and 1.0
        """
        normalized = question.lower()
        confidence = 0.0

        # CI code pattern match = high confidence
        if self.CI_CODE_PATTERN.search(normalized):
            confidence += 0.5

        # Infrastructure keyword matches
        kw_count = sum(1 for kw in self.INFRA_KEYWORDS if kw in normalized)
        confidence += min(kw_count * 0.15, 0.3)

        # Metric keyword matches
        metric_count = sum(1 for kw in self.METRIC_KEYWORDS if kw in normalized)
        confidence += min(metric_count * 0.1, 0.2)

        return min(confidence, 1.0)

    def get_prompt_asset_name(self) -> str:
        """Return the CI planner prompt asset name."""
        return "ci_planner_output_parser"

    def get_prompt_scope(self) -> str:
        """Return the prompt scope for CI domain."""
        return "ci"

    def get_prompt_engine(self) -> str:
        """Return the LLM engine for CI planner."""
        return "planner"


# Create singleton instance for registration
_ci_planner_instance = CIPlanner()


def get_ci_planner() -> CIPlanner:
    """Get the CI planner singleton instance."""
    return _ci_planner_instance
