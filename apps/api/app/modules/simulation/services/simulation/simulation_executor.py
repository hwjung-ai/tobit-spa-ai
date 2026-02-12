from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from schemas.tool_contracts import ToolCall

from app.modules.simulation.schemas import SimulationRunRequest
from app.modules.simulation.services.simulation.custom_function_runner import (
    execute_custom_function,
)
from app.modules.simulation.services.simulation.baseline_loader import (
    load_baseline_and_scenario_kpis,
)
from app.modules.simulation.services.simulation.planner import plan_simulation
from app.modules.simulation.services.simulation.presenter import (
    build_blocks,
    build_references,
)
from app.modules.simulation.services.simulation.schemas import KpiResult, SimulationPlan, SimulationResult
from app.modules.simulation.services.simulation.strategies.ml_strategy_real import (
    MLPredictiveStrategyReal,
    create_ml_strategy_real as create_ml_strategy,
)
from app.modules.simulation.services.simulation.strategies.dl_strategy_real import (
    DeepLearningStrategyReal,
    create_dl_strategy_real as create_dl_strategy,
)
from app.modules.simulation.services.simulation.strategies import (
    RuleBasedStrategy,
    StatisticalStrategy,
)
from app.modules.simulation.services.simulation.strategy_base import (
    SimulationStrategyExecutor,
)
from app.modules.simulation.services.simulation.backtest_real import run_backtest_real


# Strategy map with real ML/DL implementations
_STRATEGY_MAP: dict[str, SimulationStrategyExecutor] = {
    "rule": RuleBasedStrategy(),
    "stat": StatisticalStrategy(),
    "ml": create_ml_strategy(),  # Real ML-based strategy
    "dl": create_dl_strategy(),  # Real DL-based strategy
}


def _estimate_uncertainty(strategy: str, confidence: float) -> tuple[tuple[float, float], float]:
    """
    Estimate uncertainty bounds for prediction confidence.

    Args:
        strategy: Strategy name (rule, stat, ml, dl)
        confidence: Confidence score (0-1)

    Returns:
        Tuple of (confidence_interval, error_bound)
    """
    # Real strategies have tighter bounds than formula-based ones
    margin = {
        "rule": 0.12,
        "stat": 0.09,
        "ml": 0.05,  # Tighter for real ML
        "dl": 0.04,  # Tightest for real DL
    }.get(strategy, 0.1)
    lower = max(0.0, confidence - margin)
    upper = min(0.99, confidence + margin)
    return (round(lower, 3), round(upper, 3)), round(margin, 3)


def run_simulation(*, payload: SimulationRunRequest, tenant_id: str, requested_by: str) -> dict[str, Any]:
    """
    Run simulation with real metric data and ML/DL models.

    Flow:
    1. Plan simulation (analyze question, generate plan)
    2. Load baseline KPIs from actual metric timeseries (PostgreSQL)
    3. Calculate scenario KPIs with assumptions applied
    4. Run strategy (rule/stat/ml/dl) for prediction
    5. Align output to actual observed scenario KPIs
    6. Build result with blocks, references, tool_calls
    """
    plan = plan_simulation(
        question=payload.question,
        strategy=payload.strategy,
        scenario_type=payload.scenario_type,
        assumptions=payload.assumptions,
        horizon=payload.horizon,
        service=payload.service,
    )

    # Load baseline and scenario KPIs
    # Priority: 1) Actual metric data (PostgreSQL), 2) Topology fallback (Neo4j)
    baseline_kpis, scenario_kpis = load_baseline_and_scenario_kpis(
        tenant_id=tenant_id,
        service=payload.service,
        scenario_type=payload.scenario_type,
        assumptions=plan.assumptions,
    )

    warnings: list[str] = []

    # Strategy explanations
    explanation_by_strategy = {
        "rule": "Rule 전략은 사전 정의 가중식(선형/임계)으로 KPI 변화를 계산합니다.",
        "stat": "Stat 전략은 EMA + 회귀식 기반으로 추세 영향을 반영해 KPI를 계산합니다.",
        "ml": "ML 전략은 실제 sklearn/LightGBM surrogate 모델로 비선형 상호작용을 반영합니다.",
        "dl": "DL 전략은 실제 LSTM/Transformer 시계열 모델로 시퀀스 패턴을 반영합니다.",
        "custom": "Custom 전략은 사용자가 등록한 Python 함수(main contract)로 KPI를 계산합니다.",
    }

    actions = [
        "Latency 임계치(예: 250ms) 초과 시 스케일아웃 트리거를 준비하세요.",
        "Error Rate 상승 구간에서는 배포 속도와 트래픽 가중치를 보수적으로 조정하세요.",
        "비용 증가가 큰 경우 캐시 정책/쿼리 최적화를 선행 검토하세요.",
    ]

    # Run strategy
    if payload.strategy == "custom":
        if payload.custom_function is None:
            raise HTTPException(status_code=400, detail="custom_function is required when strategy='custom'")
        func_result = execute_custom_function(
            function=payload.custom_function,
            params={
                "tenant_id": tenant_id,
                "service": payload.service,
                "scenario_type": payload.scenario_type,
                "horizon": payload.horizon,
                "assumptions": plan.assumptions,
            },
            input_payload={
                "question": payload.question,
                "custom_input": payload.custom_input,
                "baseline_kpis": baseline_kpis,
                "scenario_kpis": scenario_kpis,
            },
        )
        raw_output = func_result.get("output")
        if not isinstance(raw_output, dict):
            raise HTTPException(status_code=500, detail="Custom function output must be object")
        raw_kpis = raw_output.get("kpis")
        if not isinstance(raw_kpis, list):
            raise HTTPException(status_code=500, detail="Custom function output.kpis must be list")

        kpis = []
        for item in raw_kpis:
            if not isinstance(item, dict):
                raise HTTPException(status_code=500, detail="Each custom KPI item must be object")
            kpi = item.get("kpi")
            baseline = item.get("baseline")
            simulated = item.get("simulated")
            unit = item.get("unit")
            if not isinstance(kpi, str) or not isinstance(unit, str):
                raise HTTPException(status_code=500, detail="Custom KPI requires string kpi and unit")
            if not isinstance(baseline, (int, float)) or not isinstance(simulated, (int, float)):
                raise HTTPException(status_code=500, detail="Custom KPI baseline/simulated must be numeric")
            kpis.append(KpiResult(kpi=kpi, baseline=float(baseline), simulated=float(simulated), unit=unit))

        confidence = float(raw_output.get("confidence", 0.7))
        model_info = raw_output.get("model_info", {})
        if not isinstance(model_info, dict):
            model_info = {}
        if isinstance(raw_output.get("warnings"), list):
            warnings.extend([str(w) for w in raw_output["warnings"]])
        if isinstance(raw_output.get("recommended_actions"), list):
            actions = [str(a) for a in raw_output["recommended_actions"]]
        custom_explanation = raw_output.get("explanation")
        if isinstance(custom_explanation, str) and custom_explanation.strip():
            explanation_by_strategy["custom"] = custom_explanation.strip()
    else:
        # Use real ML/DL strategies
        strategy = _STRATEGY_MAP[payload.strategy]
        kpis, confidence, model_info = strategy.run(
            plan=plan, baseline_data=baseline_kpis, tenant_id=tenant_id
        )

        # Keep strategy output as primary prediction and expose observed scenario as context.
        # Overwriting simulated values makes all strategies converge to the same result.
        observed_scenario = {
            kpi_name: round(float(value), 3)
            for kpi_name, value in scenario_kpis.items()
            if isinstance(value, (int, float))
        }
        model_info = {
            **model_info,
            "observed_scenario_kpis": observed_scenario,
        }

    # Add warnings for extreme assumptions
    if plan.assumptions.get("traffic_change_pct", 0.0) > 150:
        warnings.append("High extrapolation: traffic_change_pct > 150 (prediction uncertainty increases)")

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
        warnings=warnings,
        explanation=explanation_by_strategy[payload.strategy],
        recommended_actions=actions,
        model_info=model_info,
    )

    data_source = "metric_timeseries" if baseline_kpis.get("_source") == "metrics" else "topology_fallback"
    data_points = int(baseline_kpis.get("_count", 0)) if isinstance(baseline_kpis.get("_count"), int) else 0

    tool_calls = [
        ToolCall(
            tool=f"simulation.{payload.strategy}",
            elapsed_ms=3,
            input_params={
                "scenario_type": payload.scenario_type,
                "horizon": payload.horizon,
                "assumptions": result.assumptions,
                "service": payload.service,
                "custom_function": payload.custom_function.name if payload.custom_function else None,
                "data_source": data_source,
            },
            output_summary={
                "kpi_count": len(result.kpis),
                "confidence": result.confidence,
                "confidence_interval": result.confidence_interval,
                "scenario_id": result.scenario_id,
                "data_points": data_points,
            },
            error=None,
        )
    ]

    return {
        "simulation": result.model_dump(),
        "summary": f"Simulation computed with {payload.strategy} strategy",
        "plan": plan.model_dump(),
        "blocks": build_blocks(plan=plan, result=result, baseline_data=baseline_kpis),
        "references": build_references(plan=plan, result=result, baseline_data=baseline_kpis),
        "tool_calls": [t.model_dump() for t in tool_calls],
        "tenant_id": tenant_id,
        "requested_by": requested_by,
    }
