"""Event handlers for OPS orchestration.

This module contains handler classes extracted from runner.py:
- AggregationHandler: Handle aggregation operations
- ListPreviewHandler: Handle list preview operations
- PathHandler: Handle path resolution
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from core.logging import get_logger
from app.modules.ops.services.orchestration.blocks import (
    Block,
    table_block,
    text_block,
)
from app.modules.ops.services.orchestration.response_builder import (
    build_aggregate_block,
    build_aggregate_summary_block,
    build_sql_reference_block,
)


class AggregationHandler:
    """Handle aggregation operations."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def handle_aggregate(self) -> tuple[List[Block], str]:
        """Handle aggregation (wrapper)."""
        return asyncio.run(self.handle_aggregate_async())

    async def handle_aggregate_async(self) -> tuple[List[Block], str]:
        """Execute aggregation query asynchronously."""
        agg_filters = [filter.dict() for filter in self.runner.plan.aggregate.filters]

        # Check scope for appropriate tool
        aggregate_scope = self.runner.plan.aggregate.scope or "ci"

        if aggregate_scope == "event":
            # Use event_aggregate tool
            agg = await self.runner._execute_tool_with_tracing(
                "event_aggregate",
                "aggregate",
                group_by=(
                    list(self.runner.plan.aggregate.group_by)
                    if self.runner.plan.aggregate.group_by
                    else []
                ),
                metrics=(
                    list(self.runner.plan.aggregate.metrics)
                    if self.runner.plan.aggregate.metrics
                    else []
                ),
                filters=agg_filters or None,
                top_n=self.runner.plan.aggregate.top_n,
            )
        elif aggregate_scope == "metric":
            # Use metric tool
            agg = await self.runner._execute_tool_with_tracing(
                "metric",
                "aggregate",
                group_by=(
                    list(self.runner.plan.aggregate.group_by)
                    if self.runner.plan.aggregate.group_by
                    else []
                ),
                metrics=(
                    list(self.runner.plan.aggregate.metrics)
                    if self.runner.plan.aggregate.metrics
                    else []
                ),
                filters=agg_filters or None,
                top_n=self.runner.plan.aggregate.top_n,
            )
        else:
            # Use ci_aggregate
            agg = await self.runner._ci_aggregate_async(
                self.runner.plan.aggregate.group_by,
                self.runner.plan.aggregate.metrics,
                filters=agg_filters or None,
                top_n=self.runner.plan.aggregate.top_n,
            )

        blocks: List[Block] = []
        total_count = agg.get("total_count")
        if isinstance(total_count, int):
            blocks.append(build_aggregate_summary_block(total_count))
            self.runner.aggregation_summary = {
                "total_count": total_count,
                "group_by": list(self.runner.plan.aggregate.group_by),
            }

        block = build_aggregate_block(agg)
        blocks.append(block)

        query = agg.get("query")
        params = agg.get("params")
        if query and params is not None:
            blocks.append(build_sql_reference_block(query, params))

        answer = f"Aggregated {len(agg.get('rows', []))} groups"
        blocks.extend(await self.build_list_preview_blocks_async())

        return (blocks, answer)

    async def build_list_preview_blocks_async(self) -> List[Block]:
        """Build list preview blocks for aggregation."""
        if not self.runner.list_paging_info:
            return []

        paging_info = self.runner.list_paging_info
        count = paging_info.get("row_count")
        rows = paging_info.get("preview_rows", [])
        columns = paging_info.get("columns", [])

        if not rows or not columns:
            return []

        return [table_block(columns, rows, title="Recent items (preview)")]


class ListPreviewHandler:
    """Handle list preview operations."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def handle_list_preview(self) -> tuple[List[Block], str]:
        """Handle list preview (wrapper)."""
        return asyncio.run(self.handle_list_preview_async())

    async def handle_list_preview_async(self) -> tuple[List[Block], str]:
        """Execute list preview asynchronously."""
        blocks = await self.build_list_preview_blocks_async()
        answer = "Retrieved list items"
        return (blocks, answer)

    async def build_list_preview_blocks_async(self) -> List[Block]:
        """Build list preview blocks."""
        if not self.runner.list_paging_info:
            return []

        paging_info = self.runner.list_paging_info
        count = paging_info.get("row_count")
        rows = paging_info.get("preview_rows", [])
        columns = paging_info.get("columns", [])

        if not rows or not columns:
            return []

        blocks: List[Block] = []

        # Add count summary
        if count:
            blocks.append(
                text_block(
                    f"Found {count} items",
                    title="List summary",
                )
            )

        # Add preview table
        blocks.append(table_block(columns, rows, title="List items (preview)"))

        # Log preview
        self.runner._apply_list_trace(paging_info)

        return blocks


class PathHandler:
    """Handle path resolution operations."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def handle_path(self) -> tuple[List[Block], str]:
        """Handle path resolution (wrapper)."""
        return asyncio.run(self.handle_path_async())

    async def handle_path_async(self) -> tuple[List[Block], str]:
        """Execute path resolution asynchronously."""
        path_spec = self.runner.plan.path
        if not path_spec:
            return ([], "No path specification provided")

        # Resolve CI details for source and target
        source_detail, _, _ = await self.runner._resolve_ci_detail_async()

        if not source_detail:
            return (
                [text_block("Could not resolve source CI", title="Path")],
                "Failed to resolve source CI",
            )

        # Get target CI info
        target_ci_code = getattr(path_spec, "target_ci_code", None)
        target_detail = None

        if target_ci_code:
            target_detail = self.runner._ci_detail_by_code(target_ci_code)

        if not target_detail:
            return (
                [text_block("Could not resolve target CI", title="Path")],
                "Failed to resolve target CI",
            )

        # Find path
        try:
            hops = self.runner._auto_path_hops(self.runner.plan.auto) if self.runner.plan.auto else 5
            path_result = await self.runner._graph_path_async(
                source_detail["ci_id"],
                target_detail["ci_id"],
                hops,
            )
        except Exception as exc:
            self.logger.error("Path resolution failed", extra={"error": str(exc)})
            return (
                [text_block(f"Path resolution failed: {str(exc)}", title="Path")],
                "Path resolution error",
            )

        # Build path blocks
        blocks = await self._build_path_blocks(
            source_detail, target_detail, path_result
        )

        answer = f"Path from {source_detail.get('ci_code')} to {target_detail.get('ci_code')}"
        return (blocks, answer)

    async def _build_path_blocks(
        self,
        source_detail: Dict[str, Any],
        target_detail: Dict[str, Any],
        path_result: Dict[str, Any],
    ) -> List[Block]:
        """Build blocks for path visualization."""
        blocks: List[Block] = []

        if not path_result.get("path"):
            blocks.append(
                text_block(
                    f"No path found from {source_detail.get('ci_code')} to {target_detail.get('ci_code')}",
                    title="Path",
                )
            )
            return blocks

        path = path_result.get("path", [])
        blocks.append(
            text_block(
                f"Path length: {len(path)} hops",
                title="Path",
            )
        )

        # Build path table
        path_rows = []
        for i, node in enumerate(path):
            path_rows.append(
                [
                    str(i),
                    node.get("ci_code", ""),
                    node.get("ci_type", ""),
                    node.get("relation", ""),
                ]
            )

        blocks.append(
            table_block(
                ["hop", "ci_code", "ci_type", "relation"],
                path_rows,
                title="Path details",
            )
        )

        return blocks
