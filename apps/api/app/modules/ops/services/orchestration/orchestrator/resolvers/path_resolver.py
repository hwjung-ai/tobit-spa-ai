"""Path Resolver module for resolving source to target paths with CI details."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from core.logging import get_logger

from app.modules.ops.services.orchestration import response_builder
from app.modules.ops.services.orchestration.blocks import Block, text_block


class PathResolver:
    """Resolve source to target path with CI details."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def resolve_path(
        self, source: Dict, target: Dict
    ) -> Dict[str, Any]:
        """Resolve path between CIs."""
        return asyncio.run(self.resolve_path_async(source, target))

    async def resolve_path_async(
        self, source: Dict, target: Dict
    ) -> tuple[List[Block], str]:
        """Async resolve path between CIs."""
        path_payload = await self.runner._graph_path_async(
            source["ci_id"], target["ci_id"], self.runner.plan.graph.depth
        )
        blocks = response_builder.build_path_blocks(path_payload)
        answer = f"Path from {source['ci_code']} to {target['ci_code']}"
        self.runner.next_actions.extend(
            self.runner._graph_next_actions(
                (self.runner.plan.view or self.runner.plan.view).value,
                self.runner.plan.graph.depth,
                path_payload.get("truncated", False),
            )
        )
        return blocks, answer

    def resolve_ci_detail(
        self,
        role: str = "primary",
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]] | None, str | None]:
        """Resolve CI detail for path endpoint."""
        return asyncio.run(self.resolve_ci_detail_async(role))

    async def resolve_ci_detail_async(
        self,
        role: str = "primary",
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]] | None, str | None]:
        """Async resolve CI detail."""
        if role == "primary" and self.runner.rerun_context.selected_ci_id:
            detail = await self.runner._ci_get_async(
                self.runner.rerun_context.selected_ci_id
            )
            if not detail:
                message = f"CI {self.runner.rerun_context.selected_ci_id} not found."
                return None, [text_block(message)], message
            return detail, None, None

        # 명시 CI코드 추출 및 정확 매칭 (선호도 높음)
        try:
            from app.modules.ops.services.resolvers.ci_resolver import (
                _extract_codes,
                resolve_ci,
            )

            explicit_codes = _extract_codes(self.runner.question or "")
            if explicit_codes:
                exact_hits = resolve_ci(
                    self.runner.question or "", self.runner.tenant_id, limit=10
                )
                if exact_hits:
                    # 명시 코드로 찾음
                    detail = await self.runner._ci_get_async(exact_hits[0].ci_id)
                    if detail:
                        return detail, None, None
                # 명시 코드가 있는데 찾지 못함 → no-data
                return (
                    None,
                    [text_block(f"CI '{explicit_codes[0]}' not found.")],
                    f"CI {explicit_codes[0]} not found",
                )
        except ImportError:
            # If ci_resolver utilities not available, continue with search
            pass

        requested_keywords = list(self.runner.plan.primary.keywords)
        if not requested_keywords:
            secondary_ids = self.runner._ci_resolver.extract_ci_identifiers(
                self.runner.plan.secondary.keywords or []
            )
            if secondary_ids:
                requested_keywords = secondary_ids

        search_keywords, sanitized_source, before_keywords = (
            self.runner._build_ci_search_keywords()
        )
        self.runner.plan_trace.setdefault("keywords_sanitized", {})
        self.runner.plan_trace["keywords_sanitized"].update(
            {
                "before": before_keywords,
                "after": search_keywords,
                "source": sanitized_source,
            }
        )
        ci_search_trace = self.runner.plan_trace.setdefault("ci_search_trace", [])
        ci_search_trace.append(
            {
                "stage": "initial",
                "keywords": search_keywords,
                "source": sanitized_source,
            }
        )
        candidates = await self.runner._ci_resolver.search_async(
            keywords=search_keywords,
            filters=[filter.dict() for filter in self.runner.plan.primary.filters],
            limit=self.runner.plan.primary.limit,
        )
        ci_search_trace[-1]["row_count"] = len(candidates)
        if not candidates:
            candidates = self.runner._ci_resolver.search_broad_or(
                keywords=search_keywords,
                filters=[filter.dict() for filter in self.runner.plan.primary.filters],
                limit=10,
            )
            ci_search_trace.append(
                {"stage": "broad_or", "keywords": search_keywords}
            )
        if not candidates:
            message = "No CI matches found."
            history_fallback = self.runner._history_fallback_for_question()
            if history_fallback:
                blocks, hist_message = history_fallback
                return None, blocks, hist_message
            return None, [text_block(message, title="Lookup")], message

        if len(candidates) > 1:
            from app.modules.ops.services.orchestration.orchestrator.resolvers.ci_resolver import (
                _find_exact_candidate,
            )

            exact = _find_exact_candidate(candidates, search_keywords)
            if exact:
                self.logger.info(
                    "ci.runner.ci_search_exact_match",
                    extra={
                        "ci_id": exact.get("ci_id"),
                        "ci_code": exact.get("ci_code"),
                    },
                )
                detail = await self.runner._ci_get_async(exact["ci_id"])
                if not detail:
                    message = f"CI {exact.get('ci_code') or exact['ci_id']} not found."
                    return None, [text_block(message)], message
                return detail, None, None
            self.runner._register_ambiguous_candidates(candidates, "primary")
            self.runner.next_actions.extend(
                self.runner._candidate_next_actions(
                    candidates, use_secondary=False, role="primary"
                )
            )
            table = response_builder.build_candidate_table(
                candidates, role="primary"
            )
            return (
                None,
                [text_block("Multiple candidates found"), table],
                "Multiple CI candidates",
            )
        detail = await self.runner._ci_get_async(candidates[0]["ci_id"])
        if not detail:
            message = f"CI {candidates[0]['ci_code']} not found."
            return None, [text_block(message)], message
        return detail, None, None

    def resolve_path_endpoint(
        self,
        role: str,
        keywords: List[str],
        limit: int,
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]] | None, str | None]:
        """Resolve path endpoint."""
        return asyncio.run(
            self.resolve_path_endpoint_async(role, keywords, limit)
        )

    async def resolve_path_endpoint_async(
        self,
        role: str,
        keywords: List[str],
        limit: int,
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]] | None, str | None]:
        """Async resolve path endpoint."""
        selected_id = (
            self.runner.rerun_context.selected_ci_id
            if role == "source"
            else self.runner.rerun_context.selected_secondary_ci_id
        )
        if selected_id:
            detail = await self.runner._ci_get_async(selected_id)
            if not detail:
                message = f"CI {selected_id} not found."
                return None, [text_block(message)], message
            return detail, None, None
        candidates = await self.runner._ci_resolver.search_async(
            keywords=keywords, limit=limit
        )
        if not candidates:
            message = f"Unable to resolve {role} endpoint."
            return None, [text_block(message)], message
        if len(candidates) > 1:
            self.runner._register_ambiguous_candidates(candidates, role)
            use_secondary = role != "source"
            self.runner.next_actions.extend(
                self.runner._candidate_next_actions(
                    candidates, use_secondary=use_secondary, role=role
                )
            )
            table = response_builder.build_candidate_table(candidates, role=role)
            label = f"Multiple {role} candidates"
            return None, [text_block(label), table], label
        return candidates[0], None, None
