from __future__ import annotations

from core.auth import get_current_user
from core.db import get_session
from core.tenant import get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.auth.models import TbUser
from app.modules.simulation.schemas import (
    SimulationBacktestRequest,
    SimulationFunctionExecuteRequest,
    SimulationFunctionValidateRequest,
    SimulationQueryRequest,
    SimulationRunRequest,
)
from app.modules.simulation.services.simulation.custom_function_runner import (
    execute_custom_function,
)
from app.modules.simulation.services.simulation.backtest import run_backtest
from app.modules.simulation.services.simulation.planner import plan_simulation
from app.modules.simulation.services.simulation.scenario_templates import get_templates
from app.modules.simulation.services.simulation.simulation_executor import (
    run_simulation,
)
from app.modules.simulation.services.topology_service import (
    get_topology_data,
    list_available_services,
)

router = APIRouter(prefix="/sim", tags=["simulation"])


@router.get("/templates", response_model=ResponseEnvelope)
def list_simulation_templates(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    templates = get_templates()
    return ResponseEnvelope.success(
        data={
            "templates": [t.model_dump() for t in templates],
            "user_id": current_user.id,
            "tenant_id": current_user.tenant_id,
        }
    )


@router.post("/query", response_model=ResponseEnvelope)
def query_simulation(
    payload: SimulationQueryRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    plan = plan_simulation(
        question=payload.question,
        strategy=payload.strategy,
        scenario_type=payload.scenario_type,
        assumptions=payload.assumptions,
        horizon=payload.horizon,
        service=payload.service,
    )
    return ResponseEnvelope.success(
        data={
            "plan": plan.model_dump(),
            "tenant_id": tenant_id,
            "requested_by": str(current_user.id),
        }
    )


@router.post("/run", response_model=ResponseEnvelope)
def run_simulation_endpoint(
    payload: SimulationRunRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    _ = session
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    result = run_simulation(payload=payload, tenant_id=tenant_id, requested_by=str(current_user.id))

    return ResponseEnvelope.success(data=result)


@router.post("/functions/validate", response_model=ResponseEnvelope)
def validate_custom_function_endpoint(
    payload: SimulationFunctionValidateRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    result = execute_custom_function(
        function=payload.function,
        params=payload.sample_params,
        input_payload=payload.sample_input,
    )
    return ResponseEnvelope.success(
        data={
            "valid": True,
            "duration_ms": result["duration_ms"],
            "logs": result["logs"],
            "preview_output": result["output"],
        }
    )


@router.post("/functions/execute", response_model=ResponseEnvelope)
def execute_custom_function_endpoint(
    payload: SimulationFunctionExecuteRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    result = execute_custom_function(
        function=payload.function,
        params=payload.params,
        input_payload=payload.input_payload,
    )
    return ResponseEnvelope.success(
        data={
            "output": result["output"],
            "duration_ms": result["duration_ms"],
            "logs": result["logs"],
            "references": result["references"],
            "executed_by": str(current_user.id),
            "tenant_id": tenant_id,
        }
    )


@router.post("/backtest", response_model=ResponseEnvelope)
def run_backtest_endpoint(
    payload: SimulationBacktestRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    assumptions = {k: float(v) for k, v in payload.assumptions.items()}
    report = run_backtest(
        strategy=payload.strategy,
        service=payload.service,
        horizon=payload.horizon,
        assumptions=assumptions,
    )
    return ResponseEnvelope.success(data={"backtest": report, "tenant_id": tenant_id})


@router.post("/export", response_class=PlainTextResponse)
def export_simulation_csv(
    payload: SimulationRunRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> PlainTextResponse:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    result = run_simulation(payload=payload, tenant_id=tenant_id, requested_by=str(current_user.id))
    rows = result["simulation"]["kpis"]
    lines = ["kpi,baseline,simulated,change_pct,unit"]
    for row in rows:
        change_pct = row.get("change_pct", 0)
        lines.append(f'{row["kpi"]},{row["baseline"]},{row["simulated"]},{change_pct},{row["unit"]}')
    csv_text = "\n".join(lines)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=simulation_export.csv"},
    )


@router.get("/topology", response_model=ResponseEnvelope)
def get_topology(
    request: Request,
    service: str,
    scenario_type: str = "what_if",
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """
    시스템 토폴로지 데이터 조회
    
    Neo4j에서 시스템 의존성과 가상 시뮬레이션 결과를 반환합니다.
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    
    assumptions: dict[str, float] = {}
    for key in ("traffic_change_pct", "cpu_change_pct", "memory_change_pct"):
        raw = request.query_params.get(key)
        if raw is not None:
            try:
                assumptions[key] = float(raw)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid numeric assumption: {key}") from None
    
    topology = get_topology_data(
        tenant_id=tenant_id,
        service=service,
        scenario_type=scenario_type,
        assumptions=assumptions
    )
    
    return ResponseEnvelope.success(data={"topology": topology})


@router.get("/services", response_model=ResponseEnvelope)
def get_simulation_services(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    services = list_available_services(tenant_id=tenant_id)
    return ResponseEnvelope.success(data={"services": services})
