# Phase 5: Orchestration과 Inspector Trace 매핑

## 문제: 현재 Flow와 Inspector 매핑 불일치

### 현재 상황
- **Stage Executor**: Hard-coded sequential execution (primary → secondary → aggregate → graph)
- **Inspector**: 각 stage의 asset 사용을 추적 (route_plan → validate → execute → compose → present)
- **Phase 5 Orchestration**: PARALLEL/SERIAL/DAG 동적 실행 전략

**문제**: Inspector가 hard-coded flow를 가정하고 있어서 orchestration의 동적 실행을 제대로 추적하지 못함

---

## 해결방안: Orchestration-Aware Trace 체계

### 1. 현재 Inspector Trace 구조

```python
# apps/api/app/modules/ops/services/ci/tools/observability.py

@dataclass
class ToolExecutionTrace:
    tool_type: str              # "ci_lookup", "ci_aggregate", etc.
    operation: str              # "primary", "secondary", "aggregate", etc.
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error: Optional[str]
    cache_hit: bool
    input_params: Dict[str, Any]
    result_size_bytes: int
    result_count: Optional[int]
    metadata: Dict[str, Any]    # ← 여기에 orchestration 정보 추가!
    retry_count: int
    fallback_used: bool
```

### 2. Phase 5: 확장된 Trace 정보

```python
# metadata에 추가할 orchestration 정보

execution_trace_metadata = {
    # ✅ 기존
    "tool_type": "ci_lookup",
    "operation": "primary",

    # ✅ Phase 5: 추가
    "orchestration": {
        "execution_strategy": "parallel",  # PARALLEL/SERIAL/DAG
        "execution_group": 0,               # 0 = Level 0, 1 = Level 1, etc.
        "parallel_with": ["secondary"],     # 같은 그룹에서 병렬 실행되는 도구들
        "depends_on": [],                   # 의존성 있는 도구들
        "data_flow_inputs": {               # output_mapping 결과
            "ci_type": "{primary.data.rows[0].ci_type}",
            "resolved_ci_type": "Server"    # 실제 값
        },
        "execution_order_index": 0,         # 전체 실행 순서 (0=첫번째)
    },
    "stage": "execute",                     # ROUTE+PLAN/VALIDATE/EXECUTE/COMPOSE/PRESENT
    "asset_id": "ci_lookup:v1:published",   # 사용된 Asset
}
```

### 3. ToolOrchestrator에서 Trace 생성

```python
# app/modules/ops/services/ci/orchestrator/tool_orchestration.py

class ToolOrchestrator:
    async def execute(self) -> Dict[str, Any]:
        # Step 1: 의존성 분석
        dependencies = self.dependency_analyzer.extract_dependencies(self.plan)

        # Step 2: 전략 결정
        strategy = self.execution_planner.determine_strategy(dependencies)

        # Step 3: 실행 그룹 생성
        groups = self.execution_planner.create_execution_groups(dependencies, strategy)
        # 예: [["primary", "secondary"], ["aggregate"]]

        # Step 4: 실행 그룹별로 Trace 메타데이터 생성
        execution_plan_trace = self._create_execution_plan_trace(
            strategy=strategy,
            groups=groups,
            dependencies=dependencies
        )
        # 결과:
        # {
        #   "execution_strategy": "dag",
        #   "execution_groups": [
        #     {
        #       "group_index": 0,
        #       "execution_mode": "parallel",
        #       "tools": ["primary", "secondary"],
        #       "can_run_in_parallel": True,
        #       "expected_duration_ms": 1000  # 예상값
        #     },
        #     {
        #       "group_index": 1,
        #       "execution_mode": "serial",
        #       "tools": ["aggregate"],
        #       "depends_on_groups": [0],
        #       "expected_duration_ms": 500
        #     }
        #   ]
        # }

        # Step 5: ToolChainExecutor에 Trace 메타데이터 전달
        results = await self.chain_executor.execute_chain(
            tool_chain,
            self.context,
            execution_plan_trace=execution_plan_trace  # ✅ NEW
        )

        return results
```

### 4. ToolChainExecutor에서 각 도구별 Trace 저장

```python
# app/modules/ops/services/ci/orchestrator/chain_executor.py

class ToolChainExecutor:
    async def execute_chain(self, tool_chain: ToolChain, context: ToolContext,
                          execution_plan_trace: Dict[str, Any] = None):
        tracer = ExecutionTracer()
        execution_order = 0

        for group_index, group in enumerate(execution_groups):
            # 동시 또는 순차 실행
            tasks = []
            for tool_id in group:
                task = self._execute_and_trace(
                    tool_id=tool_id,
                    group_index=group_index,
                    execution_order=execution_order,
                    execution_plan_trace=execution_plan_trace,
                    tracer=tracer
                )
                tasks.append(task)
                execution_order += 1

            # 그룹 내 도구 실행
            if tool_chain.execution_mode == "parallel":
                await asyncio.gather(*tasks)
            else:
                for task in tasks:
                    await task

    async def _execute_and_trace(self, tool_id, group_index, execution_order,
                                 execution_plan_trace, tracer):
        trace_id = tracer.start_trace(tool_type, operation, params)

        try:
            result = await execute_tool(...)

            tracer.end_trace(
                trace_id,
                success=result["success"],
                # ✅ Phase 5: Orchestration 메타데이터
                orchestration={
                    "execution_strategy": execution_plan_trace["execution_strategy"],
                    "execution_group": group_index,
                    "execution_order_index": execution_order,
                    "parallel_with": group,  # 같은 그룹의 다른 도구들
                    "depends_on": step.depends_on,
                    "data_flow_inputs": resolved_mappings,
                },
                stage="execute",
                asset_id=asset_id
            )
        except Exception as e:
            tracer.end_trace(trace_id, success=False, error=str(e))
```

---

## 5. Inspector UI에서 Orchestration 표시

### A) Trace Detail View

```
╔═════════════════════════════════════════════════════════════╗
║                    Execution Trace                          ║
╠═════════════════════════════════════════════════════════════╣
║                                                             ║
║  Execution Strategy: DAG  [조회]                            ║
║  Total Duration: 2.5s                                       ║
║                                                             ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ Level 0 (Parallel): 1.0s                            │  ║
║  ├─────────────────────────────────────────────────────┤  ║
║  │ ✅ primary [0.8s]                                   │  ║
║  │    Tool: ci_lookup                                  │  ║
║  │    Asset: ci_lookup:v1:published                    │  ║
║  │    Params: keywords=["server"]                      │  ║
║  │    Result: 42 rows                                  │  ║
║  │                                                     │  ║
║  │ ✅ secondary [0.9s] (parallel with primary)        │  ║
║  │    Tool: ci_lookup                                  │  ║
║  │    Asset: ci_lookup:v1:published                    │  ║
║  │    Params: keywords=["network"]                     │  ║
║  │    Result: 28 rows                                  │  ║
║  └─────────────────────────────────────────────────────┘  ║
║                                                             ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ Level 1 (Serial): 1.5s                              │  ║
║  ├─────────────────────────────────────────────────────┤  ║
║  │ ✅ aggregate [1.5s]                                 │  ║
║  │    Tool: ci_aggregate                               │  ║
║  │    Asset: ci_aggregate:v2:published                 │  ║
║  │    Depends on: [primary, secondary]                 │  ║
║  │    Data Flow:                                        │  ║
║  │      primary_count: {primary.data.rows[0].count}    │  ║
║  │      → Resolved to: 42                              │  ║
║  │      secondary_count: {secondary.data.rows[0].count}│  ║
║  │      → Resolved to: 28                              │  ║
║  │    Params: group_by=["ci_type"], metrics=["count"]  │  ║
║  │    Result: 2 rows                                   │  ║
║  └─────────────────────────────────────────────────────┘  ║
║                                                             ║
╚═════════════════════════════════════════════════════════════╝
```

### B) Timeline View

```
Timeline
────────────────────────────────────────────────────────────

0ms ┌─ primary (0.8s) ────┐
    │                     │
    ├─ secondary (0.9s) ──┤  ← Parallel
    │                     │
1000ms│                    └─ aggregate (1.5s) ────┐
      │                                            │
2500ms└────────────────────────────────────────────┘

Execution Strategy: DAG
Total Time: 2.5s (vs 3.2s if serial)
Time Saved: 0.7s (22% faster)
```

---

## 6. Stage Executor 통합 포인트

### A) _execute_execute에서 Orchestration Trace 저장

```python
# stage_executor.py의 _execute_execute()

async def _execute_execute(self, stage_input: StageInput) -> Dict[str, Any]:
    plan_dict = stage_input.params.get("plan_output").get("plan")
    plan = Plan(**plan_dict)

    # ✅ Phase 5: Orchestration 확인
    use_orchestration = stage_input.params.get("enable_orchestration", False) or \
                        (plan.execution_strategy is not None)

    if use_orchestration:
        from app.modules.ops.services.ci.orchestrator.tool_orchestration import ToolOrchestrator

        tool_context = ToolContext(
            tenant_id=self.context.tenant_id,
            trace_id=stage_input.trace_id,
        )

        orchestrator = ToolOrchestrator(plan=plan, context=tool_context)

        # ✅ NEW: Orchestration plan trace 생성
        execution_plan = orchestrator._create_execution_plan_trace()

        results = await orchestrator.execute(
            execution_plan_trace=execution_plan
        )

        # ✅ NEW: Inspector에 orchestration 정보 저장
        stage_input.params["orchestration_trace"] = {
            "strategy": plan.execution_strategy.value,
            "groups": execution_plan["execution_groups"],
            "tools_executed": list(results.keys()),
            "total_duration_ms": orchestrator.execution_time_ms
        }

        return {
            "execution_results": results,
            "references": [...],
            "orchestration_trace": stage_input.params["orchestration_trace"],
            "executed_at": time.time(),
        }
```

### B) Runner에서 Trace 병합

```python
# runner.py의 execute() 메서드

async def execute(self) -> Dict[str, Any]:
    # ... 기존 코드 ...

    stage_output = await stage_executor.execute_stage(stage_input)

    # ✅ NEW: Orchestration trace 저장
    if "orchestration_trace" in stage_output:
        self.plan_trace["orchestration"] = stage_output["orchestration_trace"]

    # 최종 result 반환
    return {
        "plan_trace": self.plan_trace,  # orchestration 정보 포함!
        "answer": final_answer,
        "blocks": blocks,
    }
```

---

## 7. 매핑 테이블: Stage와 Asset과 Orchestration

### Stage별 Asset 사용

| Stage | Asset Type | Orchestration Role | Inspector Trace |
|-------|------------|-------------------|-----------------|
| **ROUTE+PLAN** | Prompt + Resolver | Plan 생성 + execution_strategy 결정 | plan_output + execution_strategy |
| **VALIDATE** | Policy | Plan 검증 | validation_result |
| **EXECUTE** | Query/Source | Tool orchestration | orchestration_trace (NEW) |
| **COMPOSE** | Mapping + Prompt | 결과 요약 | composition_result |
| **PRESENT** | Screen | UI 렌더링 | screen_model |

### Orchestration이 추가되는 곳

```
User Query
    ↓
[ROUTE+PLAN]
    ├─ Prompt Asset: "적절한 실행 전략은?"
    ├─ LLM: execution_strategy 결정 (PARALLEL/SERIAL/DAG)
    └─ Output: Plan with execution_strategy ✅ NEW
    ↓
[VALIDATE]
    ├─ Policy Asset: execution_strategy 유효성 검증
    └─ Output: ValidatedPlan ✅ NEW
    ↓
[EXECUTE] ← ✅ Phase 5가 이 부분을 개선
    ├─ Query/Source Asset: Tool 실행
    ├─ ToolOrchestrator:
    │   ├─ DependencyAnalyzer: 의존성 추출
    │   ├─ ExecutionPlanner: 실행 그룹 결정
    │   ├─ DataFlowMapper: 데이터 흐름 준비
    │   └─ ToolChainExecutor: 실제 실행 (병렬/순차/DAG)
    └─ Output: execution_results with orchestration_trace ✅ NEW
    ↓
[COMPOSE]
    ├─ Mapping Asset: 결과 조합
    └─ Output: AnswerBlocks ✅ Orchestration trace 참조 가능
    ↓
[PRESENT]
    ├─ Screen Asset: UI 모델 생성
    └─ Output: ScreenModel with inspector links ✅ Orchestration 시각화
```

---

## 8. 구현 체크리스트

### Backend

- [ ] **ToolOrchestrator에 `_create_execution_plan_trace()` 메서드 추가**
  - 실행 계획 메타데이터 생성
  - Execution groups 정보 포함

- [ ] **ToolChainExecutor에 trace metadata 전달**
  - `execute_and_trace()` 메서드 수정
  - Orchestration 정보를 metadata에 저장

- [ ] **stage_executor._execute_execute() 수정**
  - Orchestration trace 저장
  - stage_input.params에 orchestration 정보 포함

- [ ] **runner.execute() 수정**
  - plan_trace에 orchestration 정보 병합
  - Inspector에 완전한 정보 제공

- [ ] **observability.py 수정**
  - ToolExecutionTrace.metadata에 orchestration 필드 추가

### Inspector (UI)

- [ ] **Trace Detail View 업데이트**
  - Execution strategy 표시
  - Execution groups 시각화
  - Data flow mapping 표시

- [ ] **Timeline View 업데이트**
  - 병렬 실행 구간 표시
  - 순차 실행 구간 표시
  - 레벨별 색상 구분

- [ ] **Performance Analysis 업데이트**
  - 병렬 vs 순차 비교
  - 시간 절약 계산
  - 최적화 제안

---

## 9. 구체적인 구현 예시

### ToolOrchestrator._create_execution_plan_trace()

```python
def _create_execution_plan_trace(self) -> Dict[str, Any]:
    """Create trace metadata for execution plan."""

    dependencies = self.dependency_analyzer.extract_dependencies(self.plan)
    strategy = self.execution_planner.determine_strategy(dependencies)
    groups = self.execution_planner.create_execution_groups(dependencies, strategy)

    execution_groups = []
    for group_index, group in enumerate(groups):
        group_deps = [d for d in dependencies if d.tool_id in group]
        group_info = {
            "group_index": group_index,
            "execution_mode": "parallel" if len(group) > 1 else "serial",
            "tools": group,
            "depends_on_groups": self._get_dependency_groups(group_index, groups, dependencies),
            "expected_duration_ms": 0,  # 예측 가능
            "tools_info": [
                {
                    "tool_id": tool_id,
                    "tool_type": self._get_tool_type(tool_id),
                    "depends_on": next((d.depends_on for d in group_deps if d.tool_id == tool_id), []),
                    "output_mapping": next((d.output_mapping for d in group_deps if d.tool_id == tool_id), {})
                }
                for tool_id in group
            ]
        }
        execution_groups.append(group_info)

    return {
        "execution_strategy": strategy.value,
        "execution_groups": execution_groups,
        "total_expected_duration_ms": sum(g["expected_duration_ms"] for g in execution_groups),
        "is_optimized": len(execution_groups) > 1  # DAG이면 최적화됨
    }
```

---

## ✅ 결론

현재 구현:
1. **Phase 5**: PARALLEL/SERIAL/DAG 자동 선택 ✅
2. **Orchestration**: ToolOrchestrator에서 동적 실행 ✅
3. **Trace**: ToolExecutionTrace에 metadata 저장 ✅ (구현 필요)
4. **Inspector**: Orchestration 정보 시각화 ✅ (구현 필요)

**다음 단계**:
- ToolOrchestrator에 trace 생성 로직 추가
- Inspector UI에 orchestration 시각화 추가
- 성능 분석 기능 추가
