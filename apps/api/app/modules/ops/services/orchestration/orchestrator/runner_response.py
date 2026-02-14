"""
Response Builder Module - Phase 9

Extracts response building logic from runner.py including:
- Response composition from blocks
- Answer generation and formatting
- Reference aggregation from execution
- Structured result formatting
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.logging import get_logger

from app.modules.ops.services.orchestration.blocks import Block
from app.modules.ops.services.orchestration.actions import NextAction

MODULE_LOGGER = get_logger(__name__)


class ResponseBuilder:
    """
    Builds structured responses from execution results.

    Responsibilities:
    - Compose blocks into response
    - Generate natural language answers
    - Aggregate references and metadata
    - Format final response payload
    - Handle error responses
    """

    def __init__(self, tenant_id: str, logger: Any = None):
        """
        Initialize ResponseBuilder.

        Args:
            tenant_id: Current tenant ID
            logger: Logger instance
        """
        self.tenant_id = tenant_id
        self.logger = logger or MODULE_LOGGER

    def build_success_response(
        self,
        blocks: List[Block],
        answer: str,
        references: List[Dict[str, Any]] | None = None,
        next_actions: List[NextAction] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Build successful response with blocks and answer.

        Args:
            blocks: List of response blocks
            answer: Natural language answer
            references: List of references used
            next_actions: Recommended next actions
            metadata: Additional metadata

        Returns:
            Structured response payload
        """
        return {
            "success": True,
            "answer": answer,
            "blocks": blocks,
            "references": references or [],
            "next_actions": [
                action.model_dump() if hasattr(action, "model_dump") else action
                for action in (next_actions or [])
            ],
            "metadata": metadata or {},
        }

    def build_error_response(
        self,
        error: str,
        error_code: str | None = None,
        details: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Build error response.

        Args:
            error: Error message
            error_code: Error code for classification
            details: Additional error details

        Returns:
            Error response payload
        """
        return {
            "success": False,
            "answer": f"Error: {error}",
            "blocks": [],
            "references": [],
            "next_actions": [],
            "error": error,
            "error_code": error_code or "UNKNOWN_ERROR",
            "details": details or {},
        }

    def compose_answer_from_blocks(self, blocks: List[Block]) -> str:
        """
        Generate natural language answer from blocks.

        Args:
            blocks: List of response blocks

        Returns:
            Composed answer text
        """
        if not blocks:
            return "No results found"

        # Extract text from first text block
        for block in blocks:
            if hasattr(block, "type") and block.type == "text":
                if hasattr(block, "content"):
                    return block.content
                if hasattr(block, "text"):
                    return block.text

        # Fallback: generic answer based on block types
        block_types = [
            getattr(block, "type", "unknown") for block in blocks
        ]
        return f"Results include: {', '.join(set(block_types))}"

    def aggregate_references(
        self,
        execution_results: List[Dict[str, Any]] | None = None,
        explicit_references: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate references from execution and explicit sources.

        Args:
            execution_results: Results from tool execution
            explicit_references: Explicitly provided references

        Returns:
            Aggregated list of references
        """
        references = []

        # Extract references from execution results
        if execution_results:
            for result in execution_results:
                if isinstance(result, dict):
                    if "references" in result:
                        refs = result["references"]
                        if isinstance(refs, list):
                            references.extend(refs)

        # Add explicit references
        if explicit_references:
            references.extend(explicit_references)

        # Deduplicate by reference ID or URL
        seen = set()
        unique_refs = []
        for ref in references:
            if isinstance(ref, dict):
                # Use either id, url, or the full dict as dedupe key
                key = ref.get("id") or ref.get("url") or str(ref)
                if key not in seen:
                    seen.add(key)
                    unique_refs.append(ref)
            else:
                unique_refs.append(ref)

        return unique_refs

    def format_metadata(
        self,
        execution_time_ms: float | None = None,
        tool_calls: int | None = None,
        blocks_count: int | None = None,
        used_assets: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Format execution metadata.

        Args:
            execution_time_ms: Total execution time in milliseconds
            tool_calls: Number of tool calls made
            blocks_count: Number of result blocks
            used_assets: List of assets used

        Returns:
            Formatted metadata dict
        """
        metadata = {}

        if execution_time_ms is not None:
            metadata["execution_time_ms"] = int(execution_time_ms)

        if tool_calls is not None:
            metadata["tool_calls"] = tool_calls

        if blocks_count is not None:
            metadata["blocks_count"] = blocks_count

        if used_assets:
            metadata["used_assets"] = used_assets

        return metadata

    def combine_responses(
        self,
        responses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Combine multiple responses into one.

        Args:
            responses: List of response dicts

        Returns:
            Combined response
        """
        if not responses:
            return self.build_error_response("No responses to combine")

        if len(responses) == 1:
            return responses[0]

        # Merge all blocks
        combined_blocks = []
        for response in responses:
            if response.get("blocks"):
                combined_blocks.extend(response["blocks"])

        # Use first non-empty answer
        combined_answer = next(
            (r.get("answer") for r in responses if r.get("answer")),
            "Combined results ready",
        )

        # Merge references
        combined_references = []
        for response in responses:
            if response.get("references"):
                combined_references.extend(response["references"])

        # Merge next actions
        combined_actions = []
        for response in responses:
            if response.get("next_actions"):
                combined_actions.extend(response["next_actions"])

        return {
            "success": all(r.get("success", False) for r in responses),
            "answer": combined_answer,
            "blocks": combined_blocks,
            "references": combined_references,
            "next_actions": combined_actions,
            "metadata": {
                "combined_from": len(responses),
            },
        }
