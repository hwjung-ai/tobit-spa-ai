"""Metric Resolver module for metric aggregation and series data retrieval."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Iterable

from core.logging import get_logger


class MetricResolver:
    """Resolve metric data and aggregations."""

    def __init__(self, runner):
        self.runner = runner
        self.logger = get_logger(__name__)

    def aggregate(
        self,
        metric_name: str,
        agg: str,
        time_range: str,
        ci_id: str | None = None,
        ci_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Get metric data via 'metric_aggregate' tool."""
        return asyncio.run(
            self.aggregate_async(metric_name, agg, time_range, ci_id, ci_ids)
        )

    async def aggregate_async(
        self,
        metric_name: str,
        agg: str,
        time_range: str,
        ci_id: str | None = None,
        ci_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Async get metric data."""
        ci_ids_tuple = tuple(ci_ids or ())

        # Convert time_range to start_time and end_time
        end_time = datetime.utcnow()
        if time_range == "last_24h":
            start_time = end_time - timedelta(hours=24)
        elif time_range == "last_7d":
            start_time = end_time - timedelta(days=7)
        elif time_range == "last_30d":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=24)

        input_params = {
            "operation": "database_query",
            "metric_name": metric_name,
            "function": agg.upper(),  # Map agg to function
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "ci_id": ci_id,
            "ci_ids": list(ci_ids_tuple),  # Convert to list
            "tenant_id": self.runner.tenant_id,
            "limit": 10,
        }
        with self.runner._tool_context(
            "metric.aggregate",
            input_params=input_params,
            metric=metric_name,
            agg=agg,
            time_range=time_range,
            ci_ids_count=len(ci_ids_tuple),
        ) as meta:
            try:
                result = await self.runner._metric_aggregate_via_registry_async(
                    metric_name=metric_name,
                    agg=agg,
                    time_range=time_range,
                    ci_id=ci_id,
                    ci_ids=ci_ids_tuple or None,
                )
                meta["value_present"] = result.get("value") is not None
                meta["ci_count_used"] = result.get("ci_count_used")
            except Exception as e:
                # NOTE: Built-in metric_tools.metric_aggregate fallback removed for generic orchestration.
                self.logger.warning(f"Metric aggregate via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'metric_aggregate' is no longer available. Please implement as Tool Asset."
                )
                meta["value_present"] = False
                meta["ci_count_used"] = 0
                meta["fallback"] = False
                meta["error"] = f"Metric aggregate tool not available: {str(e)}"
                result = {"value": None, "unit": None, "ci_count_used": 0}
        return result

    def series_table(
        self,
        ci_id: str,
        metric_name: str,
        time_range: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Get metric series via 'metric_series_table' tool."""
        return asyncio.run(
            self.series_table_async(ci_id, metric_name, time_range, limit)
        )

    async def series_table_async(
        self,
        ci_id: str,
        metric_name: str,
        time_range: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Async get metric series."""
        input_params = {
            "ci_id": ci_id,
            "metric_name": metric_name,
            "time_range": time_range,
            "limit": limit,
        }
        with self.runner._tool_context(
            "metric.series",
            input_params=input_params,
            metric=metric_name,
            time_range=time_range,
            limit=limit,
        ) as meta:
            try:
                result = await self.runner._metric_series_table_via_registry_async(
                    ci_id=ci_id,
                    metric_name=metric_name,
                    time_range=time_range,
                    limit=limit,
                )
                meta["rows_count"] = len(result.get("rows", []))
            except Exception as e:
                # NOTE: Built-in metric_tools.metric_series_table fallback removed for generic orchestration.
                self.logger.warning(f"Metric series via registry failed: {e}")
                self.logger.error(
                    "Tool fallback 'metric_series_table' is no longer available. Please implement as Tool Asset."
                )
                meta["rows_count"] = 0
                meta["fallback"] = False
                meta["error"] = f"Metric series tool not available: {str(e)}"
                result = {"rows": [], "column_names": []}
        return result
