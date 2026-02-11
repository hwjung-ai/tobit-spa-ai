"""
Domain Registry - Dynamic domain planner registration and discovery.

This module provides a registry for managing domain-specific planners,
enabling the system to dynamically discover and route questions to the
appropriate domain without hardcoding.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from app.modules.ops.services.domain.base import BaseDomainPlanner, DomainMetadata

logger = logging.getLogger(__name__)


class DomainRegistry:
    """
    Registry for domain-specific planners.

    Manages registration and discovery of domain planners, enabling
    the system to route questions to the appropriate domain handler.
    """

    def __init__(self):
        """Initialize an empty domain registry."""
        self._planners: Dict[str, BaseDomainPlanner] = {}
        self._metadata: Dict[str, DomainMetadata] = {}
        self._initialized = False

    def register(self, planner: BaseDomainPlanner) -> None:
        """
        Register a domain planner.

        Args:
            planner: Domain planner instance to register

        Raises:
            ValueError: If a planner for this domain is already registered
        """
        domain = planner.domain

        if domain in self._planners:
            logger.warning(
                f"Domain planner '{domain}' already registered; skipping re-registration"
            )
            return

        self._planners[domain] = planner
        self._metadata[domain] = planner.metadata

        logger.info(
            f"Registered domain planner: {domain} - {planner.metadata.description}"
        )

    def get_planner(self, domain: str) -> BaseDomainPlanner | None:
        """
        Get a planner by domain name.

        Args:
            domain: Domain name (e.g., 'ci', 'audit', 'finance')

        Returns:
            BaseDomainPlanner instance or None if not found
        """
        return self._planners.get(domain)

    def get_metadata(self, domain: str) -> DomainMetadata | None:
        """
        Get metadata for a domain.

        Args:
            domain: Domain name

        Returns:
            DomainMetadata or None if not found
        """
        return self._metadata.get(domain)

    def list_domains(self) -> List[str]:
        """
        List all registered domain names.

        Returns:
            List of domain names
        """
        return list(self._planners.keys())

    def list_metadata(self) -> Dict[str, DomainMetadata]:
        """
        Get metadata for all registered domains.

        Returns:
            Dictionary mapping domain names to DomainMetadata
        """
        return self._metadata.copy()

    async def find_planner_for_question(
        self, question: str, min_confidence: float = 0.5
    ) -> BaseDomainPlanner | None:
        """
        Find the best planner for a given question.

        Evaluates all registered planners and returns the one with the
        highest confidence score above the minimum threshold.

        Args:
            question: User question to analyze
            min_confidence: Minimum confidence threshold (default: 0.5)

        Returns:
            Best matching BaseDomainPlanner or None if no match
        """
        best_planner: BaseDomainPlanner | None = None
        best_confidence = 0.0

        for planner in self._planners.values():
            confidence = await planner.classify_confidence(question)

            if confidence > best_confidence:
                best_confidence = confidence
                best_planner = planner

        if best_confidence >= min_confidence:
            logger.debug(
                f"Found planner for question: {best_planner.domain} "
                f"(confidence: {best_confidence:.2f})"
            )
            return best_planner

        logger.debug(
            f"No planner found with confidence >= {min_confidence} "
            f"(best: {best_confidence:.2f})"
        )
        return None

    async def find_planner_by_keywords(
        self, question: str
    ) -> BaseDomainPlanner | None:
        """
        Find planner by keyword matching.

        Faster heuristic method that checks if any domain keywords
        appear in the question.

        Args:
            question: User question to analyze

        Returns:
            First matching BaseDomainPlanner or None
        """
        question_lower = question.lower()

        for planner in self._planners.values():
            metadata = planner.metadata

            # Check keywords
            for keyword in metadata.keywords:
                if keyword.lower() in question_lower:
                    logger.debug(
                        f"Found planner by keyword '{keyword}': {planner.domain}"
                    )
                    return planner

        return None

    def is_registered(self, domain: str) -> bool:
        """
        Check if a domain is registered.

        Args:
            domain: Domain name

        Returns:
            True if domain is registered
        """
        return domain in self._planners

    def get_default_domain(self) -> str | None:
        """
        Get the default domain name.

        Returns the first registered domain, which is typically CI.

        Returns:
            Default domain name or None if no domains registered
        """
        domains = self.list_domains()
        return domains[0] if domains else None

    def get_planner_count(self) -> int:
        """
        Get the number of registered planners.

        Returns:
            Number of registered domain planners
        """
        return len(self._planners)

    def __repr__(self) -> str:
        domains_str = ", ".join(self.list_domains())
        return f"DomainRegistry([{domains_str}])"


# Global registry instance
_global_domain_registry: DomainRegistry | None = None


def get_domain_registry() -> DomainRegistry:
    """
    Get the global domain registry, creating it if necessary.

    Returns:
        Global DomainRegistry instance
    """
    global _global_domain_registry
    if _global_domain_registry is None:
        _global_domain_registry = DomainRegistry()
    return _global_domain_registry


def register_domain_planner(planner: BaseDomainPlanner) -> None:
    """
    Register a domain planner with the global registry.

    This is a convenience function for registering planners at module import time.

    Args:
        planner: Domain planner instance to register
    """
    registry = get_domain_registry()
    registry.register(planner)


async def find_planner_for_question(
    question: str, min_confidence: float = 0.5
) -> BaseDomainPlanner | None:
    """
    Find the best planner for a question using the global registry.

    This is a convenience function for finding planners without directly
    accessing the registry.

    Args:
        question: User question to analyze
        min_confidence: Minimum confidence threshold

    Returns:
        Best matching BaseDomainPlanner or None
    """
    registry = get_domain_registry()
    return await registry.find_planner_for_question(question, min_confidence)
