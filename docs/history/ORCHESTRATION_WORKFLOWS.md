# Complex Orchestration Workflows

이 문서는 Tobit SPA AI에서 구현된 복잡한 오케스트레이션 워크플로우 기능을 설명합니다.

---

## 개요

현재 시스템은 단순 도구 호출을 넘어 복잡한 워크플로우를 지원합니다. 이 기능들은 `CIOrchestrator` 내에서 구현되어 있으며, 병렬 실행, 직렬 실행, DAG 기반 실행, 루프 백 등의 고급 패턴을 지원합니다.

---

## 워크플로우 실행 모드

### 1. 병렬 실행 (Parallel Execution)

**위치**: `app/modules/ops/services/ci/orchestrator/chain_executor.py`

```python
# 여러 도구를 동시에 실행
async def execute_parallel(self, steps: List[ToolChainStep]) -> List[ToolCall]:
    tasks = []
    for step in steps:
        task = self._execute_single_step(step)
        tasks.append(task)

    # 모든 작업을 병렬로 실행
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**특징**:
- `asyncio.gather()`를 사용한 완전한 병렬 처리
- 각 도구 독립적 실행
- 에러 격리 (하나의 실패가 다른 것에 영향을 주지 않음)

### 2. 직렬 실행 with 데이터 파이핑

```python
# 도구 간 결과 전달
async def execute_sequential(self, steps: List[ToolChainStep]) -> List[ToolCall]:
    results = []
    shared_data = {}  # 도구 간 공유 데이터

    for step in steps:
        # 이전 도구의 결과를 다음 도구의 입력으로 매핑
        step.input_params = self._map_inputs(step.input_params, shared_data, results)

        result = await self._execute_single_step(step)
        results.append(result)

        # 결과를 공유 데이터에 저장
        shared_data.update(self._extract_result_data(result))

    return results
```

**데이터 매핑 문법**:
```python
# JSONPath 스타일 문법
input_mapping = {
    "ci_id": "previous_tool.output.primary.data.rows[0].ci_id",
    "timestamp": "context.execution_start_time"
}
```

### 3. DAG 기반 실행

```python
# 의존성 기반 실행
async def execute_dag(self, steps: List[ToolChainStep]) -> List[ToolCall]:
    # 1. 의존성 그래프 구축
    graph = self._build_dependency_graph(steps)

    # 2. 위상 정렬
    execution_order = self._topological_sort(graph)

    # 3. 실행 그룹별 병렬 처리
    execution_groups = self._group_by_dependencies(execution_order)

    # 4. 그룹별 순차 실행
    results = []
    for group in execution_groups:
        group_results = await asyncio.gather(*group)
        results.extend(group_results)

    return results
```

**특징**:
- 의존성 관리
- 사이클 감지
- 최적의 병렬 실행 그룹화

---

## 고급 워크플로우 패턴

### 1. 루프 백 메커니즘

**위치**: `app/modules/ops/services/ci/orchestrator/runner.py`

```python
async def _execute_graph_with_loopback(self, question: str, detail: str) -> tuple[List[Block], List[str]]:
    max_iterations = 4
    iteration = 0
    previous_signature = None

    while iteration < max_iterations:
        iteration += 1

        # 현재 뷰로 그래프 블록 빌드
        graph_blocks, graph_payload = await self._build_graph_blocks_async(
            detail, graph_view_for_loop, allow_path=True
        )

        # 시그니처 추적
        current_signature = self._compute_graph_signature(graph_blocks)

        # 변경이 없으면 중단
        if current_signature == previous_signature:
            break

        previous_signature = current_signature

        # 그래프 실행
        result = await self._execute_graph_payload_async(graph_payload)

        # 결과 검증 및 다음 반복 준비
        if self._should_continue_iteration(result):
            detail = self._prepare_next_detail(result)
        else:
            break

    return result
```

**사용 사례**:
- 그래프 깊이 확장
- 반복적 데이터 수집
- 점진적 정밀도 향상

### 2. 조건부 분기

**위치**: `app/modules/ops/services/ci/orchestrator/` 여러 파일

```python
# 플랜 스키마 정의
class PlanBranch(BaseModel):
    condition: StepCondition
    true_path: List[PlanStep]
    false_path: List[PlanStep]
    merge_strategy: str = "concat"  # merge, replace, concatenate

class StepCondition(BaseModel):
    type: str  # llm_decision, regex_match, threshold
    input_key: str
    condition: str  # LLM prompt or regex pattern
    threshold: Optional[float] = None
```

**LLM 기반 중간 결정**:
```python
# 도구 실행 중간에 LLM으로 다음 단결 결정
async def decide_next_step(self, current_context: dict) -> str:
    prompt = f"""
    Current execution context:
    {current_context}

    Based on the results, what should we do next?
    Options: continue, retry_with_different_params, escalate_to_human
    """

    response = await self._call_llm(prompt)
    return response.strip()
```

### 3. 자동 재계획 (Replanning)

**위치**: `app/modules/ops/services/ci/orchestrator/` 관련 파일

```python
class ControlLoopSystem:
    def __init__(self):
        self.max_replans = 3
        self.cooling_period = 60  # seconds
        self.replan_triggers = {
            "error": self._handle_error,
            "timeout": self._handle_timeout,
            "policy_violation": self._handle_policy_violation
        }

    async def monitor_and_replan(self, execution_result: dict):
        if execution_result.get("status") == "failed":
            # 트리거 확인
            trigger_type = self._detect_trigger(execution_result)

            if trigger_type and self._can_replan():
                # 재계획 실행
                new_plan = await self._generate_replan_plan(execution_result)
                return await self._execute_new_plan(new_plan)

        return execution_result
```

---

## 워크플로우 템플릿

### 1. 데이터 파이프라인 템플릿

```python
# 데이터 수집 → 처리 → 분석 → 시각화
pipeline = {
    "type": "sequential",
    "steps": [
        {
            "tool": "ci_detail_lookup",
            "output_mapping": {
                "ci_data": "output.primary.data"
            }
        },
        {
            "tool": "data_processor",
            "input_mapping": {
                "input": "ci_data"
            }
        },
        {
            "tool": "metric_aggregator",
            "input_mapping": {
                "data": "processed_data"
            }
        }
    ]
}
```

### 2. 분석 워크플로우 템플릿

```python
# 병렬 분석 + 결과 병합
analysis_workflow = {
    "type": "parallel",
    "merge_strategy": "merge",
    "steps": [
        {
            "tool": "cpu_analysis",
            "input_params": {"ci_ids": "context.ci_ids"}
        },
        {
            "tool": "memory_analysis",
            "input_params": {"ci_ids": "context.ci_ids"}
        },
        {
            "tool": "network_analysis",
            "input_params": {"ci_ids": "context.ci_ids"}
        }
    ],
    "post_processing": {
        "tool": "result_merger",
        "input_mapping": {
            "cpu_results": "cpu_analysis.output",
            "memory_results": "memory_analysis.output",
            "network_results": "network_analysis.output"
        }
    }
}
```

---

## 설정 및 활성화

### 1. 워크플로우 모드 설정

```python
# orchestrator 실행 시 모드 지정
runner = CIOrchestratorRunner(
    plan=plan,
    plan_raw=plan,
    tenant_id=tenant_id,
    question=question,
    policy_trace={
        "mode": "complex",  # simple, complex, advanced
        "enable_parallel": True,
        "max_iterations": 4,
        "enable_replanning": True
    }
)
```

### 2. 실행 옵션

```python
ExecutionOptions = {
    "parallel_execution": True,      # 병렬 실행 활성화
    "max_concurrent": 10,           # 최대 동시 실행 수
    "enable_data_piping": True,      # 데이터 파이핑 활성화
    "max_loop_iterations": 4,        # 최대 루프 반복
    "enable_retry": False,           # 자동 리트라이 비활성화 (미구현)
    "replan_on_error": True,        # 에러 시 자동 재계획
    "timeout_per_step": 30.0         # 단계별 타임아웃
}
```

---

## 성능 최적화

### 1. 병렬 실행 최적화

- **의존성 분석**: DAG를 통해 병렬 실행 가능 그룹 최적화
- **리소스 제한**: `max_concurrent`로 동시 실행 제어
- **결과 캐싱**: 중간 결과를 캐싱하여 중복 계산 방지

### 2. 메모리 관리

```python
# 메모리 효율적인 데이터 처리
class MemoryEfficientExecutor:
    def __init__(self, max_memory_mb=500):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_usage = 0

    async def execute_with_memory_limit(self, steps):
        results = []
        for step in steps:
            # 메모리 확인
            if self._check_memory_usage(step):
                # 스트리밍 방식으로 실행
                result = await self._execute_streaming(step)
                results.append(result)

        return results
```

---

## 사용 예시

### 1. CI 상세 분석 워크플로우

```python
# 질문: "CI-123의 메트릭 이상을 분석하고 원인을 찾아줘"
question = "CI-123의 메트릭 이상을 분석하고 원인을 찾아줘"

# 워크플로우 실행
plan = create_analysis_plan(ci_id="CI-123")
result = await runner.run(plan)

# 결과: 메트릭 데이터 + 분석 결과 + 원인 + 조치 권장
```

### 2. 대규모 모니터링 워크플로우

```python
# 병렬로 여러 CI 모니터링
question = "최근 1시간 동안 실패한 CI들을 모두 분석해줘"

# 병렬 실행 플랜
parallel_plan = {
    "type": "parallel",
    "steps": [
        {"tool": "failed_ci_lookup", "params": {"time_range": "1h"}},
        {"tool": "root_cause_analyzer", "input": "failed_ci_lookup.output"},
        {"tool": "recommendation_generator", "input": "root_cause_analyzer.output"}
    ]
}
```

---

## 주의사항

1. **복잡도 관리**: 워크플로우가 복잜해질수록 디버깅이 어려워짐
2. **성능 모니터링**: 병렬 실행 시 리소스 사용량 모니터링 필수
3. **에러 처리**: 각 단계별로 적절한 에러 처리 필요
4. **상태 관리**: 장시간 실행 시 상태 저장/복원 메커니즘 필요

이 문서는 지속적으로 업데이트되며, 새로운 워크플로우 패턴이 추가될 때말 갱신됩니다.