"""
Base Domain Planner - Abstract class for domain-specific planners.

This module defines the interface for domain planners, enabling the system
to support multiple domains (CI, Audit, Finance, etc.) without hardcoding.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.modules.ops.services.ci.planner.plan_schema import Plan, PlanOutput

logger = logging.getLogger(__name__)


@dataclass
class DomainMetadata:
    """Metadata about a domain."""

    name: str
    """Domain name (e.g., 'ci', 'audit', 'finance')"""

    description: str
    """Human-readable description of the domain"""

    keywords: list[str]
    """Keywords that identify questions in this domain"""

    code_patterns: list[str] | None = None
    """Regex patterns for domain-specific codes (e.g., CI codes, audit codes)"""

    confidence_threshold: float = 0.7
    """Minimum confidence for auto-domain detection"""


class BaseDomainPlanner(ABC):
    """
    Abstract base class for domain-specific planners.

    Each domain (CI, Audit, Finance, etc.) should implement this interface
    to provide domain-specific planning logic.
    """

    def __init__(self):
        """Initialize the domain planner."""
        self.logger = logger

    @property
    @abstractmethod
    def domain(self) -> str:
        """
        Return the domain name.

        Returns:
            Domain name (e.g., 'ci', 'audit', 'finance')
        """
        pass

    @property
    @abstractmethod
    def metadata(self) -> DomainMetadata:
        """
        Return domain metadata.

        Returns:
            DomainMetadata with description, keywords, patterns
        """
        pass

    @abstractmethod
    async def should_handle(
        self, question: str
    ) -> bool:
        """
        Determine if this planner should handle the given question.

        Args:
            question: User question to analyze

        Returns:
            True if this domain should handle the question
        """
        pass

    @abstractmethod
    async def create_plan(
        self,
        question: str,
        schema_context: dict[str, Any] | None = None,
        source_context: dict[str, Any] | None = None,
    ) -> PlanOutput:
        """
        Create a domain-specific plan for the given question.

        Args:
            question: User question
            schema_context: Optional schema information
            source_context: Optional source connection information

        Returns:
            PlanOutput with the generated plan
        """
        pass

    async def classify_confidence(
        self, question: str
    ) -> float:
        """
        Return confidence score for this domain handling the question.

        Args:
            question: User question to analyze

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Default implementation: binary decision
        return 1.0 if await self.should_handle(question) else 0.0

    def get_prompt_asset_name(self) -> str:
        """
        Return the name of the prompt asset for this domain.

        Returns:
            Prompt asset name (e.g., 'ci_planner_output_parser')
        """
        return f"{self.domain}_planner_output_parser"

    def get_prompt_scope(self) -> str:
        """
        Return the scope for loading prompt assets.

        Returns:
            Scope string (e.g., 'ci', 'audit')
        """
        return self.domain

    def get_prompt_engine(self) -> str:
        """
        Return the LLM engine for this domain's planner.

        Returns:
            Engine name (default: 'planner')
        """
        return "planner"


class BaseDomainTool(ABC):
    """
    Abstract base class for domain-specific tools.

    Each domain can have its own set of tools for executing domain-specific
    operations (search, aggregate, lookup, etc.).
    """

    def __init__(self):
        """Initialize the domain tool."""
        self.logger = logger

    @property
    @abstractmethod
    def domain(self) -> str:
        """
        Return the domain name for this tool.

        Returns:
            Domain name (e.g., 'ci', 'audit', 'finance')
        """
        pass

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """
        Return the tool name.

        Returns:
            Tool name (e.g., 'ci', 'audit_search', 'metric')
        """
        pass

    @abstractmethod
    async def should_execute(
        self,
        context: Any,  # ToolContext
        params: dict[str, Any],
    ) -> bool:
        """
        Determine if this tool should execute the given operation.

        Args:
            context: Execution context
            params: Operation parameters

        Returns:
            True if this tool can handle the operation
        """
        pass

    @abstractmethod
    async def execute(
        self,
        context: Any,  # ToolContext
        params: dict[str, Any],
    ) -> Any:  # ToolResult
        """
        Execute the tool operation.

        Args:
            context: Execution context
            params: Operation parameters

        Returns:
            ToolResult with execution outcome
        """
        pass
