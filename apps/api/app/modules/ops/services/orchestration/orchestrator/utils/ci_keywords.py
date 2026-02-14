"""CI keyword utilities for orchestration.

This module handles CI identifier extraction, keyword sanitization,
and CI search keyword building.
"""

import re
from typing import Any, Dict, List, Sequence

from app.modules.ops.services.orchestration.planner.planner_llm import (
    ISO_DATE_PATTERN,
    _sanitize_korean_particles,
)

# CI Identifier pattern - matches patterns like "os-erp-02", "apm_app_scheduler_05-1"
CI_IDENTIFIER_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9_-])[a-z0-9_]+(?:-[a-z0-9_]+)+(?![a-zA-Z0-9_-])",
    re.IGNORECASE,
)


def recover_ci_identifiers(question: str) -> tuple[str, ...] | None:
    """Recover CI identifiers from question text.

    Extracts patterns like "os-erp-02", "apm_app_scheduler_05-1" from the question.

    Args:
        question: User question text

    Returns:
        Tuple of recovered CI identifiers (up to 5), or None if none found
    """
    if not question:
        return None
    normalized = question.lower()
    matches = CI_IDENTIFIER_PATTERN.findall(normalized)
    unique = []
    for match in matches:
        sanitized = _sanitize_korean_particles(match)
        if sanitized not in unique:
            unique.append(sanitized)
    if unique:
        return tuple(unique[:5])
    return None


def sanitize_ci_keywords(keywords: Sequence[str]) -> List[str]:
    """Sanitize CI keywords by removing domain-specific keywords.

    Filters out metric names, aggregation keywords, time range keywords, etc.

    Args:
        keywords: Raw keywords from plan

    Returns:
        Filtered keywords suitable for CI search
    """
    # Import functions locally to avoid circular dependency
    from app.modules.ops.services.orchestration.mappings.compat import (
        _get_agg_keywords,
        _get_history_keywords,
        _get_list_keywords,
        _get_metric_aliases,
        _get_series_keywords,
    )

    filtered = set()

    # Get metric aliases and extract keywords
    metric_aliases = _get_metric_aliases()
    metric_keywords = set(metric_aliases.get("aliases", {}).keys()) | set(
        metric_aliases.get("keywords", [])
    )
    filtered.update(k.lower() for k in metric_keywords)
    filtered.update(k.lower() for k in metric_aliases.get("aliases", {}).keys())

    # Get agg keywords
    agg_keywords = _get_agg_keywords()
    filtered.update(k.lower() for k in agg_keywords.keys())

    # Get time range map from history keywords
    history_keywords = _get_history_keywords()
    time_map = history_keywords.get("time_map", {})
    filtered.update(k.lower() for k in time_map.keys())

    # Get series and list keywords
    series_keywords = _get_series_keywords()
    filtered.update(k.lower() for k in series_keywords)
    list_keywords = _get_list_keywords()
    filtered.update(k.lower() for k in list_keywords)

    sanitized: List[str] = []
    for token in keywords:
        normalized = token.lower().strip()
        if not normalized:
            continue
        if normalized in filtered:
            continue
        if ISO_DATE_PATTERN.search(normalized):
            continue
        sanitized.append(token)
        if len(sanitized) >= 5:
            break

    return sanitized


def build_ci_search_keywords(
    question: str, plan_primary_keywords: Sequence[str], plan_secondary_keywords: Sequence[str] | None
) -> tuple[List[str], str, List[str]]:
    """Build CI search keywords with priority-based selection.

    Priority order:
    1. Recovered CI identifiers from question
    2. Sanitized primary keywords
    3. Sanitized secondary keywords
    4. Fallback to first 2 primary or secondary keywords

    Args:
        question: User question
        plan_primary_keywords: Primary keywords from plan
        plan_secondary_keywords: Secondary keywords from plan

    Returns:
        Tuple of (selected_keywords, source, original_keywords)
    """
    before = list(plan_primary_keywords)
    recovered = recover_ci_identifiers(question)

    if recovered:
        return list(recovered[:5]), "recover_ci_identifiers", before

    primary_sanitized = sanitize_ci_keywords(plan_primary_keywords)
    if primary_sanitized:
        return primary_sanitized, "plan_primary", before

    secondary_sanitized = sanitize_ci_keywords(plan_secondary_keywords or [])
    if secondary_sanitized:
        return secondary_sanitized, "plan_secondary", before

    fallback = before[: min(2, len(before))] or (plan_secondary_keywords or [])[:2]
    return fallback, "fallback", before


def extract_ci_identifiers(keywords: Sequence[str]) -> List[str]:
    """Extract CI identifiers from keywords.

    Matches patterns like "os-erp-02", "apm_app_scheduler_05-1".

    Args:
        keywords: Keywords to search

    Returns:
        List of matching CI identifiers
    """
    identifiers: List[str] = []
    for token in keywords:
        if not token:
            continue
        # Sanitize Korean particles before matching
        sanitized = _sanitize_korean_particles(token.lower())
        match = CI_IDENTIFIER_PATTERN.fullmatch(sanitized)
        if match:
            identifiers.append(sanitized)
    return identifiers


def has_ci_identifier_in_keywords(
    plan_primary_keywords: Sequence[str],
    plan_secondary_keywords: Sequence[str] | None,
) -> bool:
    """Check if CI identifier exists in primary or secondary keywords.

    Args:
        plan_primary_keywords: Primary keywords from plan
        plan_secondary_keywords: Secondary keywords from plan

    Returns:
        True if any CI identifier found
    """
    if extract_ci_identifiers(plan_primary_keywords):
        return True
    if extract_ci_identifiers(plan_secondary_keywords or []):
        return True
    return False


def routing_identifiers(
    plan_primary_keywords: Sequence[str],
    plan_secondary_keywords: Sequence[str] | None,
    question: str,
) -> List[str]:
    """Collect all CI identifiers from keywords and question for routing.

    Args:
        plan_primary_keywords: Primary keywords from plan
        plan_secondary_keywords: Secondary keywords from plan
        question: User question

    Returns:
        List of unique CI identifiers
    """
    identifiers: List[str] = []
    for source in (
        plan_primary_keywords,
        plan_secondary_keywords or [],
        recover_ci_identifiers(question) or (),
    ):
        for token in extract_ci_identifiers(source):
            if token not in identifiers:
                identifiers.append(token)
    return identifiers
