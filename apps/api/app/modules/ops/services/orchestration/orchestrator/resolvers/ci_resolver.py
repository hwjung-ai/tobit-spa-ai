"""CI Resolver module for CI search, get, and aggregate operations."""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, Iterable, List, Literal, Sequence

from core.logging import get_logger

from app.modules.ops.services.orchestration.planner.planner_llm import (
    _sanitize_korean_particles,
)

# FilterSpec was previously imported from ci.py tool
# Now defined locally as a type alias for filter specifications
FilterSpec = Dict[str, Any]

CI_IDENTIFIER_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9_-])[a-z0-9_]+(?:-[a-z0-9_]+)+(?![a-zA-Z0-9_-])",
    re.IGNORECASE,
)


def _find_exact_candidate(
    candidates: Sequence[dict], identifiers: Sequence[str]
) -> dict | None:
    """Find exact match in candidates based on identifiers."""
    if not candidates or not identifiers:
        return None
    normalized_identifiers: List[str] = []
    for value in identifiers:
        cleaned = (value or "").strip()
        if cleaned:
            normalized_identifiers.append(cleaned.lower())
    if not normalized_identifiers:
        return None
    for candidate in candidates:
        ci_code = (candidate.get("ci_code") or "").strip().lower()
        ci_name = (candidate.get("ci_name") or "").strip().lower()
        if not ci_code and not ci_name:
            continue
        for identifier in normalized_identifiers:
            if identifier and (identifier == ci_code or identifier == ci_name):
                return candidate
    return None


class CIResolver:
    """Resolve CI details via search, get, aggregate operations."""

    def __init__(self, runner):
        self.runner = runner
        self._cache = runner._ci_search_cache
        self.logger = get_logger(__name__)

    def search(
        self,
        keywords: Iterable[str] | None = None,
        filters: Iterable[FilterSpec] | None = None,
        limit: int | None = None,
        sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
    ) -> List[Dict[str, Any]]:
        """CI search via 'ci_search' tool."""
        return asyncio.run(
            self.search_async(keywords, filters, limit, sort)
        )

    async def search_async(
        self,
        keywords: Iterable[str] | None = None,
        filters: Iterable[FilterSpec] | None = None,
        limit: int | None = None,
        sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
    ) -> List[Dict[str, Any]]:
        """Async CI search via 'ci_search' tool."""
        keywords_tuple = tuple(keywords or ())
        filters_tuple = tuple(filters or ())
        input_params = {
            "keywords": list(keywords_tuple),
            "filter_count": len(filters_tuple),
            "limit": limit,
            "sort": sort,
        }

        # Generate cache key and check cache first
        cache_key = self._cache.generate_key(
            keywords=keywords_tuple,
            filters=filters_tuple,
            limit=limit,
            sort=sort,
        )
        cached_results = await self._cache.get(cache_key)
        if cached_results is not None:
            self.logger.debug(
                "ci.search.cache_hit",
                extra={
                    "cache_key": cache_key[:8],
                    "result_count": len(cached_results),
                },
            )
            return cached_results

        with self.runner._tool_context(
            "ci.search",
            input_params=input_params,
            keyword_count=len(keywords_tuple),
            filter_count=len(filters_tuple),
            limit=limit,
            sort_column=sort[0] if sort else None,
            cache_hit=False,
        ) as meta:
            try:
                result_data = await self.runner._ci_search_via_registry_async(
                    keywords=keywords_tuple,
                    filters=filters_tuple,
                    limit=limit,
                    sort=sort,
                )
                meta["row_count"] = len(result_data)
                result_records = result_data
            except Exception as e:
                # NOTE: Built-in ci_tools.ci_search fallback removed for generic orchestration.
                # This functionality should be implemented as a 'ci_search' Tool Asset.
                self.logger.warning(f"CI search via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'ci_search' is no longer available. Please implement as Tool Asset."
                )
                meta["row_count"] = 0
                meta["fallback"] = False
                meta["error"] = f"CI search tool not available: {str(e)}"
                result_records = []

        # Cache successful results
        if result_records:
            await self._cache.set(
                cache_key,
                result_records,
                keywords=keywords_tuple,
                filters=filters_tuple,
            )

        if not result_records and not self.runner._ci_search_recovery:
            recovered = self.runner._recover_ci_identifiers()
            if recovered:
                self.runner._ci_search_recovery = True
                self.logger.info(
                    "ci.runner.ci_search_recovery",
                    extra={"recovery_keywords": recovered},
                )
                self.runner.plan = self.runner.plan.copy(
                    update={
                        "primary": self.runner.plan.primary.copy(
                            update={"keywords": list(recovered)}
                        )
                    }
                )
                return await self.search_async(
                    keywords=recovered, filters=filters, limit=limit, sort=sort
                )
        return result_records

    def search_broad_or(
        self,
        keywords: Sequence[str],
        filters: Sequence[dict] | None,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fallback broad search via OR."""
        tokens: List[str] = []
        for keyword in keywords or ():
            value = (keyword or "").strip()
            if not value:
                continue
            tokens.append(value)
            for part in re.split(r"[\s_\-]+", value):
                part = part.strip()
                if len(part) >= 2:
                    tokens.append(part)
        if self.runner.question:
            for part in re.split(r"[\s_\-]+", self.runner.question):
                part = part.strip()
                if (
                    len(part) >= 2
                    and part.isascii()
                    and any(ch.isalnum() for ch in part)
                ):
                    tokens.append(part)
        deduped: List[str] = []
        seen = set()
        for token in tokens:
            lower = token.lower()
            if lower in seen:
                continue
            seen.add(lower)
            deduped.append(token)
        with self.runner._tool_context(
            "ci.search_broad",
            keyword_count=len(deduped),
            filter_count=len(filters or ()),
            limit=limit,
            sort_column=None,
        ) as meta:
            # NOTE: Built-in ci_tools.ci_search_broad_or removed for generic orchestration.
            # This functionality should be implemented as a 'ci_search_broad' Tool Asset.
            self.logger.error(
                "Tool fallback 'ci_search_broad_or' is no longer available. Please implement as Tool Asset."
            )
            meta["row_count"] = 0
            result = type("Result", (), {"records": []})()
        return [
            r.model_dump() if hasattr(r, "model_dump") else r
            for r in result.records
        ]

    def get(self, ci_id: str) -> Dict[str, Any] | None:
        """Get CI by ID via 'ci_get' tool."""
        return asyncio.run(self.get_async(ci_id))

    async def get_async(self, ci_id: str) -> Dict[str, Any] | None:
        """Async get CI by ID."""
        # Check cache first for CI detail
        cache_key = f"ci.get:{ci_id}"
        cached_detail = await self._cache.get(cache_key)
        if cached_detail is not None:
            self.logger.debug(
                "ci.get.cache_hit",
                extra={"ci_id": ci_id},
            )
            return cached_detail[0] if isinstance(cached_detail, list) else cached_detail

        with self.runner._tool_context(
            "ci.get", input_params={"ci_id": ci_id}, ci_id=ci_id, cache_hit=False
        ) as meta:
            try:
                detail = await self.runner._ci_get_via_registry_async(ci_id)
                meta["found"] = bool(detail)
            except Exception as e:
                # NOTE: Built-in ci_tools.ci_get fallback removed for generic orchestration.
                self.logger.warning(f"CI get via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'ci_get' is no longer available. Please implement as Tool Asset."
                )
                detail = None
                meta["found"] = False
                meta["fallback"] = False
                meta["error"] = f"CI get tool not available: {str(e)}"

        result = detail.dict() if (detail and hasattr(detail, "dict")) else detail

        # Cache successful result
        if result:
            await self._cache.set(
                cache_key,
                [result],  # Wrap in list for consistency with set() interface
                keywords=[ci_id],
                filters=None,
            )

        return result

    def get_by_code(self, ci_code: str) -> Dict[str, Any] | None:
        """Get CI by code via 'ci_get_by_code' tool."""
        return asyncio.run(self.get_by_code_async(ci_code))

    async def get_by_code_async(
        self, ci_code: str
    ) -> Dict[str, Any] | None:
        """Async get CI by code."""
        with self.runner._tool_context(
            "ci.get", input_params={"ci_code": ci_code}, ci_code=ci_code
        ) as meta:
            try:
                detail = await self.runner._ci_get_by_code_via_registry_async(ci_code)
                meta["found"] = bool(detail)
            except Exception as e:
                # NOTE: Built-in ci_tools.ci_get_by_code fallback removed for generic orchestration.
                self.logger.warning(f"CI get_by_code via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'ci_get_by_code' is no longer available. Please implement as Tool Asset."
                )
                detail = None
                meta["found"] = False
                meta["fallback"] = False
                meta["error"] = f"CI get_by_code tool not available: {str(e)}"
        return detail.dict() if (detail and hasattr(detail, "dict")) else detail

    def aggregate(
        self,
        group_by: Iterable[str],
        metrics: Iterable[str],
        filters: Iterable[FilterSpec] | None = None,
        ci_ids: Iterable[str] | None = None,
        top_n: int | None = None,
    ) -> Dict[str, Any]:
        """Aggregate multiple CIs via 'ci_aggregate' tool."""
        return asyncio.run(
            self.aggregate_async(group_by, metrics, filters, ci_ids, top_n)
        )

    async def aggregate_async(
        self,
        group_by: Iterable[str],
        metrics: Iterable[str],
        filters: Iterable[FilterSpec] | None = None,
        ci_ids: Iterable[str] | None = None,
        top_n: int | None = None,
    ) -> Dict[str, Any]:
        """Async aggregate multiple CIs."""
        group_list = tuple(group_by or ())
        metric_list = tuple(metrics or ())
        filters_tuple = tuple(filters or ())
        ci_ids_tuple = tuple(ci_ids or ())

        # Use default group_by if empty
        if not group_list:
            group_list = ("ci_type",)

        input_params = {
            "operation": "database_query",
            "group_by": list(group_list),
            "metrics": list(metric_list),
            "filter_count": len(filters_tuple),
            "ci_ids_count": len(ci_ids_tuple),
            "top_n": top_n or 10,
            "tenant_id": self.runner.tenant_id,
        }
        with self.runner._tool_context(
            "ci.aggregate",
            input_params=input_params,
            group_by=",".join(group_list),
            metrics=",".join(metric_list),
            filter_count=len(filters_tuple),
            ci_ids_count=len(ci_ids_tuple),
            top_n=top_n,
        ) as meta:
            try:
                result = await self.runner._ci_aggregate_via_registry_async(
                    group_by=group_list,
                    metrics=metrics,
                    filters=filters,
                    ci_ids=ci_ids,
                    top_n=top_n,
                )
                meta["row_count"] = len(result.get("rows", []))
            except Exception as e:
                # NOTE: Built-in ci_tools.ci_aggregate fallback removed for generic orchestration.
                self.logger.warning(f"CI aggregate via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'ci_aggregate' is no longer available. Please implement as Tool Asset."
                )
                meta["row_count"] = 0
                meta["fallback"] = False
                meta["error"] = f"CI aggregate tool not available: {str(e)}"
                result = {"rows": [], "column_names": []}
        return result

    def extract_ci_identifiers(self, keywords: Sequence[str]) -> List[str]:
        """Extract CI identifiers from keywords."""
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

    def find_exact_candidate(
        self, candidates: Sequence[dict], identifiers: Sequence[str]
    ) -> dict | None:
        """Find exact match in candidates."""
        return _find_exact_candidate(candidates, identifiers)
