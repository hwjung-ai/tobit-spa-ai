from __future__ import annotations

import asyncio

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
    SimulationRealtimeRunRequest,
    SimulationRunRequest,
)
from app.modules.simulation.services.simulation.custom_function_runner import (
    execute_custom_function,
)
from app.modules.simulation.services.simulation.backtest_real import run_backtest_real
from app.modules.simulation.services.simulation.planner import plan_simulation
from app.modules.simulation.services.simulation.scenario_templates import get_templates
from app.modules.simulation.services.simulation.simulation_executor import (
    run_simulation,
)
from app.modules.simulation.services.simulation.realtime_executor import (
    run_realtime_simulation,
)
from app.modules.simulation.services.topology_service import (
    get_topology_data,
    list_available_services,
)
from app.modules.simulation.services.simulation.functions import (
    FunctionCategory,
    FunctionComplexity,
    FunctionRegistry,
    execute_simulation,
    get_function_info,
    list_functions,
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
    """
    **DB MODE**: Run simulation using stored metrics.

    Use this when:
    - Scheduled data collection is running
    - Historical data is available
    - Fast response time is important

    Request body should NOT include `source_config`.
    """
    _ = session
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    result = run_simulation(payload=payload, tenant_id=tenant_id, requested_by=str(current_user.id))

    return ResponseEnvelope.success(data=result)


@router.post("/run/realtime", response_model=ResponseEnvelope)
async def run_simulation_realtime_endpoint(
    payload: SimulationRealtimeRunRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """
    **REAL-TIME MODE**: Run simulation with live metrics.

    Fetches metrics directly from CloudWatch without using database.

    Use this when:
    - Latest metrics are needed (no scheduled collection)
    - No historical data in database
    - Freshness is more important than speed

    Request body:
    - Standard SimulationRunRequest fields
    - `source_config`: {
        "source": "cloudwatch",
        "cloudwatch_region": "...",
        "query": JSON
      }

    Example:
    POST /api/sim/run/realtime
    {
      "question": "What happens if traffic increases 20%?",
      "scenario_type": "what_if",
      "strategy": "ml",
      "service": "api-server",
      "horizon": "24h",
      "assumptions": {"traffic_change_pct": 20},
      "source_config": {
        "source": "cloudwatch",
        "cloudwatch_region": "us-east-1",
        "query": "{\"namespace\": \"AWS/EC2\", \"metric_name\": \"CPUUtilization\"}"
      }
    }
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    try:
        result = await run_realtime_simulation(
            payload=payload,
            tenant_id=tenant_id,
            requested_by=str(current_user.id),
        )
        return ResponseEnvelope.success(data=result)

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Real-time simulation failed: {str(e)}. "
                   f"Ensure {payload.source_config.source} is accessible."
        )


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
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run backtest using actual metric data with train/test split.

    Calculates real R², MAPE, RMSE, Coverage@90 metrics.
    """
    _ = session
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    assumptions = {k: float(v) for k, v in payload.assumptions.items()}
    report = run_backtest_real(
        strategy=payload.strategy,
        service=payload.service,
        horizon=payload.horizon,
        assumptions=assumptions,
        tenant_id=tenant_id,
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


# =============================================================================
# Function Library Endpoints
# =============================================================================

@router.get("/functions", response_model=ResponseEnvelope)
def list_function_library(
    category: str | None = None,
    complexity: str | None = None,
    tags: str | None = None,
    search: str | None = None,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    List available simulation functions from the function library.

    Query Parameters:
    - category: Filter by category (rule, statistical, ml, domain)
    - complexity: Filter by complexity (basic, intermediate, advanced)
    - tags: Filter by tags (comma-separated, e.g., "forecast,regression")
    - search: Search in name, description, ID

    Returns list of function metadata with parameters and outputs.
    """
    # Parse filters
    cat_filter = FunctionCategory(category) if category else None
    complexity_filter = FunctionComplexity(complexity) if complexity else None
    tag_filter = tags.split(",") if tags else None

    # Get functions
    functions = list_functions(
        category=cat_filter,
        complexity=complexity_filter,
        tags=tag_filter,
        search=search,
    )

    # Format response
    function_list = [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category.value,
            "complexity": f.complexity.value,
            "description": f.description,
            "confidence": f.confidence,
            "tags": f.tags,
            "assumptions": f.assumptions,
            "references": f.references,
            "version": f.version,
            "parameter_count": len(f.parameters),
            "output_count": len(f.outputs),
        }
        for f in functions
    ]

    return ResponseEnvelope.success(
        data={
            "functions": function_list,
            "total_count": len(function_list),
            "filters": {
                "category": category,
                "complexity": complexity,
                "tags": tags,
                "search": search,
            },
        }
    )


@router.get("/functions/categories", response_model=ResponseEnvelope)
def get_function_categories(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Get all available function categories."""
    categories = [c.value for c in FunctionCategory]
    return ResponseEnvelope.success(
        data={
            "categories": categories,
            "count": len(categories),
        }
    )


@router.get("/functions/complexities", response_model=ResponseEnvelope)
def get_function_complexities(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Get all available complexity levels."""
    complexities = [c.value for c in FunctionComplexity]
    return ResponseEnvelope.success(
        data={
            "complexities": complexities,
            "count": len(complexities),
        }
    )


@router.get("/functions/tags", response_model=ResponseEnvelope)
def get_function_tags(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Get all unique tags across all functions."""
    tags = FunctionRegistry.get_all_tags()
    return ResponseEnvelope.success(
        data={
            "tags": tags,
            "count": len(tags),
        }
    )


@router.get("/functions/{function_id}", response_model=ResponseEnvelope)
def get_function_detail(
    function_id: str,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get detailed information about a specific function.

    Includes full parameter definitions, output definitions,
    assumptions, and references.
    """
    info = get_function_info(function_id)

    if not info:
        raise HTTPException(status_code=404, detail=f"Function not found: {function_id}")

    return ResponseEnvelope.success(data=info)


@router.post("/functions/{function_id}/execute", response_model=ResponseEnvelope)
def execute_function_endpoint(
    function_id: str,
    payload: dict,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """
    Execute a simulation function from the library.

    Request body should contain:
    - baseline: Dict of baseline KPI values
    - assumptions: Dict of input assumption values
    - context: Optional additional context
    """
    _ = tenant_id  # Context may be used in the future

    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    baseline = payload.get("baseline", {})
    assumptions = payload.get("assumptions", {})
    context = payload.get("context")

    result = execute_simulation(
        function_id=function_id,
        baseline=baseline,
        assumptions=assumptions,
        context=context,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("debug_info", {}).get("error", "Execution failed"))

    return ResponseEnvelope.success(data=result)


# =============================================================================
# User Function Registration Endpoints
# =============================================================================

@router.post("/functions/user/register", response_model=ResponseEnvelope)
def register_user_function(
    payload: dict,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """
    Register a user-defined simulation function.

    Request body should contain:
    - name: Function name
    - description: Function description
    - category: rule, statistical, ml, or domain
    - complexity: basic, intermediate, or advanced
    - code: Python function code
    - parameters: List of parameter definitions
    - outputs: List of output definitions
    - tags: Optional list of tags
    """
    from app.modules.simulation.services.simulation.user_functions import register_user_function_from_spec

    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    try:
        result = register_user_function_from_spec(
            user_id=str(current_user.id),
            tenant_id=tenant_id,
            spec=payload,
        )

        return ResponseEnvelope.success(
            data={
                "function": result,
                "tenant_id": tenant_id,
                "registered_by": str(current_user.id),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Function registration failed: {str(e)}")


@router.get("/functions/user/template", response_model=ResponseEnvelope)
def get_user_function_template(
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Get a template for user-defined functions.

    Returns example code and structure for creating custom simulation functions.
    """
    from app.modules.simulation.services.simulation.user_functions import USER_FUNCTION_TEMPLATE

    return ResponseEnvelope.success(
        data={
            "template_code": USER_FUNCTION_TEMPLATE,
            "required_structure": {
                "name": "My Custom Function",
                "description": "Function description",
                "category": "rule",
                "complexity": "basic",
                "code": "# Python function code here",
                "parameters": [
                    {
                        "name": "traffic_change_pct",
                        "type": "number",
                        "default": 0.0,
                        "min": -50.0,
                        "max": 200.0,
                        "description": "Traffic change percentage",
                        "unit": "%",
                        "required": True,
                    }
                ],
                "outputs": [
                    {
                        "name": "latency_ms",
                        "unit": "ms",
                        "description": "Predicted latency",
                    }
                ],
                "tags": ["custom", "user-defined"],
            },
            "guidelines": [
                "Function must set 'result' variable with outputs dict",
                "Use baseline and assumptions as input parameters",
                "Return confidence score between 0 and 1",
                "Include debug_info for troubleshooting",
            ],
        }
    )


# =============================================================================
# SSE (Server-Sent Events) Endpoints
# =============================================================================

from fastapi.responses import StreamingResponse


async def _with_keepalive(stream, interval_seconds: float = 15.0):
    iterator = stream.__aiter__()
    while True:
        try:
            event = await asyncio.wait_for(anext(iterator), timeout=interval_seconds)
        except StopAsyncIteration:
            break
        except TimeoutError:
            yield "event: ping\ndata: {}\n\n"
            continue
        yield event


@router.get("/stream/run")
async def stream_simulation_run(
    request: SimulationRunRequest,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> StreamingResponse:
    """
    Stream simulation results using Server-Sent Events (SSE).

    This endpoint provides real-time updates as the simulation progresses.

    SSE Events:
    - progress: Progress updates (step, message)
    - baseline: Baseline KPIs loaded
    - plan: Simulation plan generated
    - kpi: Individual KPI results
    - complete: Final simulation result
    - error: Error occurred

    Usage in frontend:
    const eventSource = new EventSource('/api/sim/stream/run?...');
    eventSource.addEventListener('progress', (e) => { ... });
    eventSource.addEventListener('kpi', (e) => { ... });
    eventSource.addEventListener('complete', (e) => { ... });
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    from app.modules.simulation.services.simulation.sse_handler import simulation_sse_handler

    async def event_generator():
        stream = simulation_sse_handler.stream_simulation(
            payload=request,
            tenant_id=tenant_id,
            requested_by=str(current_user.id),
        )
        async for event in _with_keepalive(stream):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/comparison")
async def stream_strategy_comparison(
    request: SimulationRunRequest,
    strategies: str = "rule,stat,ml,dl",
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> StreamingResponse:
    """
    Stream multi-strategy comparison using Server-Sent Events.

    Query Parameters:
    - strategies: Comma-separated list of strategies to compare (default: rule,stat,ml,dl)

    SSE Events:
    - progress: Progress updates (current, total, strategy)
    - baseline: Baseline KPIs loaded
    - strategy_result: Individual strategy results
    - complete: Final comparison data
    - error: Error occurred
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    strategy_list = [s.strip() for s in strategies.split(",") if s.strip()]

    from app.modules.simulation.services.simulation.sse_handler import comparison_sse_handler

    async def event_generator():
        stream = comparison_sse_handler.stream_comparison(
            payload=request,
            strategies=strategy_list,
            tenant_id=tenant_id,
            requested_by=str(current_user.id),
        )
        async for event in _with_keepalive(stream):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/function/{function_id}")
async def stream_function_execution(
    function_id: str,
    baseline: str,
    assumptions: str,
    context: str | None = None,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> StreamingResponse:
    """
    Stream function library execution using Server-Sent Events.

    Query Parameters:
    - baseline: JSON string of baseline KPIs
    - assumptions: JSON string of assumptions
    - context: Optional JSON string for context

    SSE Events:
    - progress: Progress updates
    - outputs: Function execution results
    - error: Error occurred
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    import json

    baseline_data = json.loads(baseline) if baseline else {}
    assumptions_data = json.loads(assumptions) if assumptions else {}
    context_data = json.loads(context) if context else None

    from app.modules.simulation.services.simulation.sse_handler import function_sse_handler

    async def event_generator():
        stream = function_sse_handler.stream_function_execution(
            function_id=function_id,
            baseline=baseline_data,
            assumptions=assumptions_data,
            context=context_data,
            tenant_id=tenant_id,
        )
        async for event in _with_keepalive(stream):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
