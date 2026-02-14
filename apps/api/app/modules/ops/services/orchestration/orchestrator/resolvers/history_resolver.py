"""History Resolver module for history and CEP simulation."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from core.logging import get_logger


class HistoryResolver:
    """Resolve history and CEP simulation data."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def recent(
        self,
        history_spec: Any,
        ci_context: Dict[str, Any],
        ci_ids: list[str] | None = None,
        time_range: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Get recent history via 'history_recent' tool."""
        return asyncio.run(
            self.recent_async(
                history_spec, ci_context, ci_ids, time_range, limit
            )
        )

    async def recent_async(
        self,
        history_spec: Any,
        ci_context: Dict[str, Any],
        ci_ids: list[str] | None = None,
        time_range: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Async get recent history."""
        final_time_range = (
            time_range or getattr(history_spec, "time_range", None) or "last_7d"
        )
        final_limit = limit or getattr(history_spec, "limit", None) or 50
        scope = getattr(history_spec, "scope", "ci")
        input_params = {
            "time_range": final_time_range,
            "scope": scope,
            "limit": final_limit,
            "ci_ids_count": len(ci_ids) if ci_ids else 0,
        }
        with self.runner._tool_context(
            "history.recent",
            input_params=input_params,
            time_range=final_time_range,
            scope=scope,
            limit=final_limit,
        ) as meta:
            try:
                result = await self.runner._history_recent_via_registry_async(
                    history_spec=history_spec,
                    ci_context=ci_context,
                    ci_ids=ci_ids,
                    time_range=final_time_range,
                    limit=final_limit,
                )
                meta["row_count"] = len(result.get("rows", []))
                meta["warnings_count"] = len(result.get("warnings", []))
                meta["available"] = result.get("available")
            except Exception as e:
                self.logger.warning(
                    f"History recent via registry failed: {e}"
                )
                # NOTE: Built-in history_tools.event_log_recent fallback removed for generic orchestration.
                self.logger.error(
                    "Tool fallback 'event_log_recent' is no longer available. Please implement as Tool Asset."
                )
                result = {"rows": [], "warnings": [], "available": False}
                meta["row_count"] = 0
                meta["warnings_count"] = 0
                meta["available"] = False
                meta["fallback"] = False
                meta["error"] = f"History tool not available: {str(e)}"
        return result

    def simulate_cep(
        self,
        rule_id: str | None,
        ci_context: Dict[str, Any],
        metric_context: Dict[str, Any] | None,
        history_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """Simulate CEP rules via 'cep_simulate' tool."""
        return asyncio.run(
            self.simulate_cep_async(
                rule_id, ci_context, metric_context, history_context
            )
        )

    async def simulate_cep_async(
        self,
        rule_id: str | None,
        ci_context: Dict[str, Any],
        metric_context: Dict[str, Any] | None,
        history_context: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        """Async simulate CEP rules."""
        input_params = {
            "rule_id": rule_id,
            "ci_context_keys": list(ci_context.keys()) if ci_context else [],
            "metric_context_present": bool(metric_context),
            "history_context_present": bool(history_context),
        }
        with self.runner._tool_context(
            "cep.simulate", input_params=input_params, rule_id=rule_id
        ) as meta:
            try:
                result = await self.runner._cep_simulate_via_registry_async(
                    rule_id=rule_id,
                    ci_context=ci_context,
                    metric_context=metric_context,
                    history_context=history_context,
                )
                meta["success"] = bool(result.get("success"))
                meta["exec_log_present"] = bool(result.get("exec_log_id"))
            except Exception as e:
                # NOTE: Built-in cep_tools.cep_simulate fallback removed for generic orchestration.
                self.logger.warning(f"CEP simulate via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'cep_simulate' is no longer available. Please implement as Tool Asset."
                )
                result = {"success": False, "exec_log_id": None}
                meta["success"] = False
                meta["exec_log_present"] = False
                meta["fallback"] = False
                meta["error"] = f"CEP tool not available: {str(e)}"
        return result
