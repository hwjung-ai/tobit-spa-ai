"""
Domain Module - Generic domain extension support.

This module provides the base infrastructure for supporting multiple
domains (CI, Audit, Finance, etc.) without hardcoding.

Key components:
- BaseDomainPlanner: Abstract interface for domain planners
- DomainRegistry: Dynamic domain registration and discovery
- BaseDomainTool: Abstract interface for domain tools
- DomainClassifier: LLM-based automatic domain detection
"""

from __future__ import annotations

from .base import BaseDomainPlanner, BaseDomainTool, DomainMetadata
from .classifier import (
    DomainClassifier,
    classify_question_domain,
    get_domain_classifier,
)
from .registry import (
    DomainRegistry,
    find_planner_for_question,
    get_domain_registry,
    register_domain_planner,
)

__all__ = [
    "BaseDomainPlanner",
    "BaseDomainTool",
    "DomainMetadata",
    "DomainRegistry",
    "DomainClassifier",
    "find_planner_for_question",
    "get_domain_registry",
    "register_domain_planner",
    "get_domain_classifier",
    "classify_question_domain",
]
