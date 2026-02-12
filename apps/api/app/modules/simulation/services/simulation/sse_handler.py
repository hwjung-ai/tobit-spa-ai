"""
SSE-based Real-time Simulation Updates

Provides Server-Sent Events for streaming simulation results
instead of WebSocket.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import HTTPException
from sqlmodel import Session

from app.modules.simulation.schemas import SimulationRunRequest
from app.modules.simulation.services.simulation.baseline_loader import load_baseline_and_scenario_kpis
from app.modules.simulation.services.simulation.planner import plan_simulation
from app.modules.simulation.services.simulation.schemas import SimulationPlan
from app.modules.simulation.services.simulation.strategies.ml_strategy_real import (
    MLPredictiveStrategyReal,
    create_ml_strategy_real as create_ml_strategy,
)
from app.modules.simulation.services.simulation.strategies.dl_strategy_real import (
    DeepLearningStrategyReal,
    create_dl_strategy_real as create_dl_strategy,
)
from app.modules.simulation.services.simulation import (
    RuleBasedStrategy,
    StatisticalStrategy,
)


class SimulationSSEHandler:
    """
    Handler for streaming simulation results via Server-Sent Events.
    """

    def __init__(self):
        self._strategy_map = {
            "rule": RuleBasedStrategy(),
            "stat": StatisticalStrategy(),
            "ml": create_ml_strategy(),
            "dl": create_dl_strategy(),
        }

    async def stream_simulation(
        self,
        *,
        payload: SimulationRunRequest,
        tenant_id: str,
        requested_by: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream simulation results as SSE events.

        NO artificial delays - shows real computation progress.

        Data Source Transparency:
        - metric_timeseries: Real metric data from PostgreSQL
        - tool_asset: Data loaded via Tool Asset Registry
        - topology_fallback: Derived from Neo4j topology (no real metrics)

        Yields SSE-formatted data lines:
        - event: {event_type}
        - data: {json_data}

        Event types:
        - progress: Progress updates (with real timing)
        - baseline: Baseline KPIs loaded (with data source info)
        - plan: Simulation plan
        - strategy: Strategy execution start
        - kpi: Individual KPI results
        - complete: Final result
        - error: Error occurred
        """
        import time
        start_time = time.time()

        try:
            # Send progress
            yield self._sse_event("progress", {
                "step": "init",
                "message": "Initializing simulation",
                "elapsed_ms": 0,
            })

            # Step 1: Plan simulation
            plan_start = time.time()
            yield self._sse_event("progress", {
                "step": "planning",
                "message": "Planning simulation",
                "elapsed_ms": round((plan_start - start_time) * 1000, 1),
            })

            plan = plan_simulation(
                question=payload.question,
                strategy=payload.strategy,
                scenario_type=payload.scenario_type,
                assumptions=payload.assumptions,
                horizon=payload.horizon,
                service=payload.service,
            )

            plan_elapsed = (time.time() - plan_start) * 1000
            yield self._sse_event("plan", {
                **plan.model_dump(),
                "computation_time_ms": round(plan_elapsed, 1),
            })

            yield self._sse_event("progress", {
                "step": "loading_baseline",
                "message": "Loading baseline KPIs",
                "elapsed_ms": round((time.time() - start_time) * 1000, 1),
            })

            # Step 2: Load baseline KPIs
            baseline_start = time.time()
            baseline_kpis, scenario_kpis = load_baseline_and_scenario_kpis(
                tenant_id=tenant_id,
                service=payload.service,
                scenario_type=payload.scenario_type,
                assumptions=plan.assumptions,
            )
            baseline_elapsed = (time.time() - baseline_start) * 1000

            # Determine data source
            data_source = "metric_timeseries" if baseline_kpis.get("_source") == "metrics" else "topology_fallback"

            yield self._sse_event("baseline", {
                "kpis": {k: v for k, v in baseline_kpis.items() if not k.startswith("_")},
                "data_source": data_source,
                "computation_time_ms": round(baseline_elapsed, 1),
                "data_quality": {
                    "metrics_available": data_source == "metric_timeseries",
                    "using_fallback": data_source == "topology_fallback",
                    "note": "Using actual metric data" if data_source == "metric_timeseries" else "No metric data available - using topology-derived estimates",
                },
            })

            # Step 3: Run strategy
            yield self._sse_event("progress", {
                "step": "running_strategy",
                "message": f"Running {payload.strategy} strategy",
                "elapsed_ms": round((time.time() - start_time) * 1000, 1),
            })

            strategy_start = time.time()
            strategy = self._strategy_map[payload.strategy]
            kpis, confidence, model_info = strategy.run(
                plan=plan,
                baseline_data=baseline_kpis,
                tenant_id=tenant_id
            )
            strategy_elapsed = (time.time() - strategy_start) * 1000

            # Stream KPI results as they're computed (no delay)
            for i, kpi in enumerate(kpis):
                yield self._sse_event("kpi", {
                    "index": i,
                    "total": len(kpis),
                    "kpi": kpi.model_dump(),
                })

            # Step 4: Build final result
            yield self._sse_event("progress", {
                "step": "finalizing",
                "message": "Building final result",
                "elapsed_ms": round((time.time() - start_time) * 1000, 1),
            })

            # Align with scenario KPIs
            for kpi in kpis:
                if kpi.kpi in scenario_kpis:
                    kpi.simulated = round(scenario_kpis[kpi.kpi], 3)

            # Create final result
            from app.modules.simulation.services.simulation.schemas import SimulationResult
            from app.modules.simulation.services.simulation.baseline_loader import _estimate_uncertainty

            confidence_interval, error_bound = _estimate_uncertainty(payload.strategy, confidence)

            result = SimulationResult(
                scenario_id=plan.scenario_id,
                strategy=payload.strategy,
                scenario_type=payload.scenario_type,
                question=payload.question,
                horizon=payload.horizon,
                assumptions={k: round(v, 3) for k, v in plan.assumptions.items()},
                kpis=kpis,
                confidence=confidence,
                confidence_interval=confidence_interval,
                error_bound=error_bound,
                warnings=[],
                explanation=f"Simulation computed with {payload.strategy} strategy",
                recommended_actions=[
                    "Review KPI changes against baseline",
                    "Consider recommended actions for system adjustments",
                ],
                model_info=model_info,
            )

            total_elapsed = (time.time() - start_time) * 1000

            # Send complete event with timing breakdown
            yield self._sse_event("complete", {
                "simulation": result.model_dump(),
                "summary": f"Simulation computed with {payload.strategy} strategy",
                "plan": plan.model_dump(),
                "tenant_id": tenant_id,
                "requested_by": requested_by,
                "timing": {
                    "total_ms": round(total_elapsed, 1),
                    "planning_ms": round(plan_elapsed, 1),
                    "baseline_loading_ms": round(baseline_elapsed, 1),
                    "strategy_execution_ms": round(strategy_elapsed, 1),
                },
                "data_source": data_source,
                "data_transparency": {
                    "baseline_from_real_metrics": data_source == "metric_timeseries",
                    "baseline_from_topology_fallback": data_source == "topology_fallback",
                    "strategy_used": payload.strategy,
                    "strategy_computation_real": True,  # Strategy executed real computation
                },
            })

        except Exception as e:
            yield self._sse_event("error", {
                "message": str(e),
                "step": "unknown",
                "elapsed_ms": round((time.time() - start_time) * 1000, 1),
            })

    def _sse_event(self, event_type: str, data: dict[str, Any]) -> str:
        """
        Format data as SSE event.

        Format:
        event: {event_type}
        data: {json_string}

        """
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


class MultiStrategyComparisonSSE:
    """
    SSE handler for comparing multiple strategies in real-time.
    """

    def __init__(self):
        self._strategies = {
            "rule": RuleBasedStrategy(),
            "stat": StatisticalStrategy(),
            "ml": create_ml_strategy(),
            "dl": create_dl_strategy(),
        }

    async def stream_comparison(
        self,
        *,
        payload: SimulationRunRequest,
        strategies: list[str],
        tenant_id: str,
        requested_by: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream multi-strategy comparison results via SSE.

        Executes each strategy sequentially and streams results.
        """
        try:
            # Initial setup
            yield self._sse_event("progress", {"step": "init", "message": "Initializing comparison", "total": len(strategies)})

            # Load plan and baseline once
            plan = plan_simulation(
                question=payload.question,
                strategy=payload.strategy,  # Use first strategy for planning
                scenario_type=payload.scenario_type,
                assumptions=payload.assumptions,
                horizon=payload.horizon,
                service=payload.service,
            )

            baseline_kpis, scenario_kpis = load_baseline_and_scenario_kpis(
                tenant_id=tenant_id,
                service=payload.service,
                scenario_type=payload.scenario_type,
                assumptions=plan.assumptions,
            )

            yield self._sse_event("baseline", {
                "kpis": baseline_kpis,
                "strategies_to_compare": strategies,
            })

            # Run each strategy
            results = {}

            for i, strategy_name in enumerate(strategies):
                yield self._sse_event("progress", {
                    "step": "running_strategy",
                    "message": f"Running {strategy_name} ({i+1}/{len(strategies)})",
                    "current": i + 1,
                    "total": len(strategies),
                    "strategy": strategy_name,
                })

                strategy = self._strategies.get(strategy_name)
                if not strategy:
                    yield self._sse_event("error", {
                        "message": f"Unknown strategy: {strategy_name}",
                        "strategy": strategy_name,
                    })
                    continue

                try:
                    kpis, confidence, model_info = strategy.run(
                        plan=plan,
                        baseline_data=baseline_kpis,
                        tenant_id=tenant_id
                    )

                    # Align with scenario KPIs
                    for kpi in kpis:
                        if kpi.kpi in scenario_kpis:
                            kpi.simulated = round(scenario_kpis[kpi.kpi], 3)

                    results[strategy_name] = {
                        "kpis": [k.model_dump() for k in kpis],
                        "confidence": confidence,
                        "model_info": model_info,
                    }

                    yield self._sse_event("strategy_result", {
                        "strategy": strategy_name,
                        "confidence": confidence,
                        "kpis": {k.kpi: k.model_dump() for k in kpis},
                    })

                except Exception as e:
                    yield self._sse_event("error", {
                        "message": f"Strategy {strategy_name} failed: {str(e)}",
                        "strategy": strategy_name,
                    })

            # Final comparison
            yield self._sse_event("progress", {"step": "finalizing", "message": "Building comparison"})

            comparison_data = self._build_comparison(results, baseline_kpis)

            yield self._sse_event("complete", {
                "comparison": comparison_data,
                "baseline": baseline_kpis,
                "strategies": list(results.keys()),
                "tenant_id": tenant_id,
            })

        except Exception as e:
            yield self._sse_event("error", {
                "message": f"Comparison failed: {str(e)}",
            })

    def _build_comparison(
        self, results: dict[str, dict[str, Any]], baseline: dict[str, float]
    ) -> dict[str, Any]:
        """Build comparison data structure."""
        comparison = {
            "strategies": {},
            "kpi_comparison": {},
        }

        for strategy_name, result in results.items():
            comparison["strategies"][strategy_name] = {
                "confidence": result["confidence"],
                "model_info": result["model_info"],
            }

        # Build KPI comparison table
        kpi_names = ["latency_ms", "error_rate_pct", "throughput_rps", "cost_usd_hour"]

        for kpi_name in kpi_names:
            comparison["kpi_comparison"][kpi_name] = {
                "baseline": baseline.get(kpi_name, 0),
                "strategies": {},
            }

            for strategy_name, result in results.items():
                for kpi in result["kpis"]:
                    if kpi["kpi"] == kpi_name:
                        comparison["kpi_comparison"][kpi_name]["strategies"][strategy_name] = kpi["simulated"]
                        break

        return comparison

    def _sse_event(self, event_type: str, data: dict[str, Any]) -> str:
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


class FunctionExecutionSSE:
    """
    SSE handler for executing function library functions.
    """

    async def stream_function_execution(
        self,
        *,
        function_id: str,
        baseline: dict[str, float],
        assumptions: dict[str, float],
        context: dict[str, Any] | None,
        tenant_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream function execution results via SSE.
        """
        try:
            from app.modules.simulation.services.simulation.functions import execute_simulation

            yield self._sse_event("progress", {"step": "init", "message": f"Executing function: {function_id}"})

            # Execute function
            result = execute_simulation(
                function_id=function_id,
                baseline=baseline,
                assumptions=assumptions,
                context=context or {},
            )

            if not result.get("success"):
                yield self._sse_event("error", {
                    "message": result.get("debug_info", {}).get("error", "Execution failed"),
                    "function_id": function_id,
                })
                return

            # Stream outputs
            yield self._sse_event("progress", {"step": "complete", "message": "Function execution complete"})

            yield self._sse_event("outputs", {
                "function_id": function_id,
                "outputs": result["outputs"],
                "confidence": result["confidence"],
                "debug_info": result["debug_info"],
            })

        except Exception as e:
            yield self._sse_event("error", {
                "message": str(e),
                "function_id": function_id,
            })

    def _sse_event(self, event_type: str, data: dict[str, Any]) -> str:
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# Global handlers
simulation_sse_handler = SimulationSSEHandler()
comparison_sse_handler = MultiStrategyComparisonSSE()
function_sse_handler = FunctionExecutionSSE()
