"""
Domain Registry Initialization.

This module initializes and registers all domain planners when imported.
Import this module early in your application startup to initialize all domains.
"""

from __future__ import annotations

import logging

from app.modules.ops.services.ci.planner.ci_planner import get_ci_planner
from app.modules.ops.services.domain import register_domain_planner, get_domain_registry

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


# Auto-initialize domains when this module is imported
initialize_domain_planners()
