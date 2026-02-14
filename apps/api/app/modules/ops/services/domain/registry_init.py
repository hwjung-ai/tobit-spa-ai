"""
Domain Registry Initialization.

This module provides domain planner registration helpers.
Call ``initialize_domain_planners()`` explicitly during application startup.
"""

from __future__ import annotations

import logging

from app.modules.ops.services.domain import get_domain_registry, register_domain_planner
from app.modules.ops.services.orchestration.planner.ci_planner import get_ci_planner

logger = logging.getLogger(__name__)


def initialize_domain_planners() -> None:
    """
    Initialize and register all available domain planners.

    This function registers all domain planner classes with the global
    DomainRegistry, making them available for dynamic selection and
    routing by the orchestrator.

    Should be called once during application startup.
    """
    # Register CI domain planner
    ci_planner = get_ci_planner()
    register_domain_planner(ci_planner)

    logger.info(
        f"Domain registry initialized with {get_domain_registry().get_planner_count()} domain(s)"
    )

    # Log all registered domains
    for domain in get_domain_registry().list_domains():
        metadata = get_domain_registry().get_metadata(domain)
        if metadata:
            logger.info(f"  - {domain}: {metadata.description}")
