"""Graph Resolver module for graph expansion, normalization, and path resolution."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from core.logging import get_logger


class GraphResolver:
    """Resolve graph relationships and paths."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def expand(
        self, ci_id: str, view: str, depth: int, limits: dict[str, int]
    ) -> Dict[str, Any]:
        """Expand relationship graph."""
        return asyncio.run(self.expand_async(ci_id, view, depth, limits))

    async def expand_async(
        self, ci_id: str, view: str, depth: int, limits: dict[str, int]
    ) -> Dict[str, Any]:
        """Async expand relationship graph."""
        input_params = {
            "ci_id": ci_id,
            "view": view,
            "depth": depth,
            "limits": limits,
        }
        with self.runner._tool_context(
            "graph.expand", input_params=input_params, view=view, depth=depth
        ) as meta:
            try:
                raw_payload = await self.runner._graph_expand_via_registry_async(
                    ci_id=ci_id, view=view, depth=depth, limits=limits
                )
            except Exception as e:
                # NOTE: Built-in graph_tools.graph_expand fallback removed for generic orchestration.
                self.logger.warning(f"Graph expand via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'graph_expand' is no longer available. Please implement as Tool Asset."
                )
                raw_payload = None
                meta["fallback"] = False
                meta["error"] = f"Graph expand tool not available: {str(e)}"
            payload_type = (
                type(raw_payload).__name__ if raw_payload is not None else "NoneType"
            )
            raw_extra: Dict[str, Any] = {
                "type": payload_type,
                "preview": str(raw_payload)[:200],
            }
            if isinstance(raw_payload, dict):
                raw_extra["keys"] = list(raw_payload.keys())
            elif isinstance(raw_payload, list):
                raw_extra["list_len"] = len(raw_payload)
            else:
                raw_extra["attrs"] = [
                    attr for attr in dir(raw_payload) if not attr.startswith("_")
                ]
            self.logger.info("ci.graph.expand_return_debug", extra=raw_extra)
            normalized = self.normalize_payload(raw_payload, payload_type, meta)
        return normalized

    def normalize_payload(
        self, raw_payload: Any, payload_type: str, meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize graph payload to standard format."""
        normalized: Dict[str, Any] = {
            "nodes": [],
            "edges": [],
            "summary": {},
            "meta": {},
            "truncated": False,
        }
        if isinstance(raw_payload, dict):
            normalized.update(raw_payload)
        elif isinstance(raw_payload, list):
            normalized["nodes"] = list(raw_payload)
        else:
            normalized.update(
                {
                    "nodes": getattr(raw_payload, "nodes", []) or [],
                    "edges": getattr(raw_payload, "edges", []) or [],
                    "summary": getattr(raw_payload, "summary", {}) or {},
                    "meta": getattr(raw_payload, "meta", {}) or {},
                    "truncated": bool(getattr(raw_payload, "truncated", False)),
                }
            )
        nodes = normalized.get("nodes")
        normalized["nodes"] = list(nodes) if isinstance(nodes, list) else []
        edges = normalized.get("edges")
        normalized["edges"] = list(edges) if isinstance(edges, list) else []
        summary = normalized.get("summary")
        normalized["summary"] = summary if isinstance(summary, dict) else {}
        meta_value = normalized.get("meta")
        normalized["meta"] = meta_value if isinstance(meta_value, dict) else {}
        normalized["truncated"] = bool(normalized.get("truncated", False))
        meta["payload_type"] = payload_type
        meta["node_count"] = len(normalized["nodes"])
        meta["edge_count"] = len(normalized["edges"])
        meta["truncated"] = normalized["truncated"]
        self.logger.info(
            "ci.graph.expand_normalized_debug",
            extra={
                "nodes_len": len(normalized["nodes"]),
                "edges_len": len(normalized["edges"]),
                "keys": list(normalized.keys()),
            },
        )
        return normalized

    def find_path(
        self, source_id: str, target_id: str, hops: int
    ) -> Dict[str, Any]:
        """Find path between nodes."""
        return asyncio.run(self.find_path_async(source_id, target_id, hops))

    async def find_path_async(
        self, source_id: str, target_id: str, hops: int
    ) -> Dict[str, Any]:
        """Async find path between nodes."""
        input_params = {
            "source_id": source_id,
            "target_id": target_id,
            "hops": hops,
        }
        with self.runner._tool_context(
            "graph.path", input_params=input_params, hop_count=hops
        ) as meta:
            try:
                payload = await self.runner._graph_path_via_registry_async(
                    source_id=source_id, target_id=target_id, hops=hops
                )
            except Exception as e:
                # NOTE: Built-in graph_tools.graph_path fallback removed for generic orchestration.
                self.logger.warning(f"Graph path via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'graph_path' is no longer available. Please implement as Tool Asset."
                )
                payload = {"nodes": [], "edges": [], "hop_count": 0}
                meta["fallback"] = False
                meta["error"] = f"Graph path tool not available: {str(e)}"
            meta["node_count"] = len(payload.get("nodes", []))
            meta["edge_count"] = len(payload.get("edges", []))
            meta["hop_count"] = payload.get("hop_count")
        return payload
