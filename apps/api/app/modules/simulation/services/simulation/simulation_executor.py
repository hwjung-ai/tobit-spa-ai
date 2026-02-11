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
from app.modules.simulation.services.simulation.schemas import KpiResult, SimulationResult
from app.modules.simulation.services.simulation.strategies import (
    DeepLearningStrategy,
    MLPredictiveStrategy,
    RuleBasedStrategy,
    StatisticalStrategy,
)
from app.modules.simulation.services.simulation.strategy_base import (
    SimulationStrategyExecutor,
)

_STRATEGY_MAP: dict[str, SimulationStrategyExecutor] = {
    "rule": RuleBasedStrategy(),
    "stat": StatisticalStrategy(),
    "ml": MLPredictiveStrategy(),
    "dl": DeepLearningStrategy(),
}


def _estimate_uncertainty(strategy: str, confidence: float) -> tuple[tuple[float, float], float]:
    margin = {
        "rule": 0.12,
        "stat": 0.09,
        "ml": 0.07,
        "dl": 0.06,
    }.get(strategy, 0.1)
    lower = max(0.0, confidence - margin)
    upper = min(0.99, confidence + margin)
    return (round(lower, 3), round(upper, 3)), round(margin, 3)


def run_simulation(*, payload: SimulationRunRequest, tenant_id: str, requested_by: str) -> dict[str, Any]:
    plan = plan_simulation(
        question=payload.question,
        strategy=payload.strategy,
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
    warnings: list[str] = []
    explanation_by_strategy = {
        "rule": "Rule 전략은 사전 정의 가중식(선형/임계)으로 KPI 변화를 계산합니다.",
        "stat": "Stat 전략은 EMA + 회귀식 기반으로 추세 영향을 반영해 KPI를 계산합니다.",
        "ml": "ML 전략은 surrogate 추론식으로 비선형 상호작용을 반영합니다.",
        "dl": "DL 전략은 시퀀스형 surrogate 추론식으로 비선형/상호작용 영향을 계산합니다.",
        "custom": "Custom 전략은 사용자가 등록한 Python 함수(main contract)로 KPI를 계산합니다.",
    }
    actions = [
        "Latency 임계치(예: 250ms) 초과 시 스케일아웃 트리거를 준비하세요.",
        "Error Rate 상승 구간에서는 배포 속도와 트래픽 가중치를 보수적으로 조정하세요.",
        "비용 증가가 큰 경우 캐시 정책/쿼리 최적화를 선행 검토하세요.",
    ]

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
        strategy = _STRATEGY_MAP[payload.strategy]
        kpis, confidence, model_info = strategy.run(
            plan=plan, baseline_data=baseline_kpis, tenant_id=tenant_id
        )
        # Align strategy output around real observed scenario baseline from data source.
        for kpi in kpis:
            if kpi.kpi in scenario_kpis:
                kpi.simulated = round(scenario_kpis[kpi.kpi], 3)

    if plan.assumptions.get("traffic_change_pct", 0.0) > 150:
        warnings.append("High extrapolation: traffic_change_pct > 150")

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
            },
            output_summary={
                "kpi_count": len(result.kpis),
                "confidence": result.confidence,
                "confidence_interval": result.confidence_interval,
                "scenario_id": result.scenario_id,
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
