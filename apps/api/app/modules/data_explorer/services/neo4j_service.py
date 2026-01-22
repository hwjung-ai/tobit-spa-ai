from __future__ import annotations

import re
from typing import Any

from core.config import AppSettings

from app.modules.data_explorer.repositories import neo4j_repo

_FORBIDDEN_CYPHER = (
    "create",
    "merge",
    "delete",
    "set",
    "call",
    "load",
    "drop",
    "detach",
    "remove",
)


def list_labels(settings: AppSettings) -> list[str]:
    return neo4j_repo.list_labels(settings)


def run_query(
    settings: AppSettings,
    cypher: str,
    params: dict[str, Any] | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    normalized = _sanitize_cypher(cypher)
    normalized = _ensure_limit(normalized, settings.data_max_rows)
    return neo4j_repo.run_query(settings, normalized, params)


def _sanitize_cypher(value: str) -> str:
    cypher = value.strip().rstrip(";")
    lowered = cypher.lower()
    if not lowered.startswith(("match", "with")):
        raise ValueError("Only MATCH/RETURN queries are allowed")
    if "return" not in lowered:
        raise ValueError("RETURN clause is required")
    if ";" in cypher:
        raise ValueError("Multiple statements are not allowed")
    if any(re.search(rf"\\b{keyword}\\b", lowered) for keyword in _FORBIDDEN_CYPHER):
        raise ValueError("Forbidden Cypher keyword detected")
    return cypher


def _ensure_limit(cypher: str, limit: int) -> str:
    if re.search(r"\blimit\b", cypher, re.IGNORECASE):
        return cypher
    return f"{cypher} LIMIT {limit}"
