# Orchestrator Tool Asset 완전 리팩토링 계획

**작성일**: 2026-02-10
**상태**: 🔴 CRITICAL - 즉시 실행 필요
**목표**: Orchestrator를 Tool Asset 기반으로 완전히 리팩토링

---

## 🎯 목표

**현재 문제**:
```
Orchestrator (CI Orchestrator Runner)
    ├─ _handle_lookup_async()
    ├─ _handle_aggregate_async()
    ├─ _handle_list_preview_async()
    ├─ _handle_path_async()
    └─ ...

    ↓ (내부적으로 Tool 호출하지만 외부에서 불명확)

Tool이 사용되는지 알 수 없음
LLM이 호출할 수 없음
확장 불가능
```

**목표 상태**:
```
LLM이 Tool을 선택
    ↓
Tool Asset을 사용하여 실행
    ├─ ci_detail_lookup
    ├─ ci_summary_aggregate
    ├─ maintenance_history_list
    ├─ history_combined_union
    └─ ...

    ↓ (명시적 Tool 호출)

결과 반환 (원활한 확장)
```

---

## 📋 현재 상태 분석

### Orchestrator의 내부 구조

```python
# runner.py:1680
async def _handle_lookup_async(self):
    detail = await self._resolve_ci_detail_async()  # ← CI 상세 조회
    blocks = response_builder.build_ci_detail_blocks(detail)
    blocks.extend(await self._metric_blocks_async(detail))  # ← 메트릭
    blocks.extend(await self._history_blocks_async(detail))  # ← 이력
    blocks.extend(await self._build_graph_blocks_async(detail))  # ← 그래프
    return blocks, answer

async def _handle_aggregate_async(self):
    # CI 분포 조회
    ...

async def _handle_list_preview_async(self):
    # CI 목록 조회
    ...

async def _handle_path_async(self):
    # 경로 분석
    ...
```

**문제점**:
1. ❌ orchestrator 내부에서 직접 데이터 조회
2. ❌ Tool Asset을 호출하지 않음 (또는 불명확)
3. ❌ 새로운 Tool 추가 시 orchestrator 수정 필요
4. ❌ LLM이 어떤 Tool을 사용하는지 알 수 없음

---

## 🔧 리팩토링 전략

### Phase 1: Tool Asset 확장 (긴급)

**지금까지 정의된 Tool Assets** (6개):
- ✅ ci_detail_lookup
- ✅ ci_summary_aggregate
- ✅ ci_list_paginated
- ✅ maintenance_history_list
- ✅ maintenance_ticket_create
- ✅ history_combined_union

**추가로 필요한 Tool Assets**:

#### 1. Metric Tools (새로 만들어야 함)
```python
{
    "name": "metric_query",
    "tool_type": "database_query",
    "description": "Query metrics for a specific CI (CPU, memory, latency, etc.)",
    "tool_input_schema": {
        "type": "object",
        "required": ["ci_id", "metric_names", "time_range"],
        "properties": {
            "ci_id": {"type": "string", "description": "CI ID"},
            "metric_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Metric names to query (cpu_usage, memory, latency, etc.)"
            },
            "time_range": {
                "type": "string",
                "description": "Time range (e.g., '1h', '24h', '7d')"
            },
            "aggregation": {
                "type": "string",
                "enum": ["avg", "max", "min", "sum", "count"],
                "description": "Aggregation function"
            }
        }
    },
    "tool_output_schema": {
        "type": "object",
        "properties": {
            "metrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "metric_name": {"type": "string"},
                        "value": {"type": "number"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "unit": {"type": "string"}
                    }
                }
            }
        }
    }
}
```

#### 2. Graph/Relationship Tools (새로 만들어야 함)
```python
{
    "name": "ci_graph_query",
    "tool_type": "database_query",
    "description": "Query CI relationships and dependencies",
    "tool_input_schema": {
        "type": "object",
        "required": ["ci_id", "relationship_type"],
        "properties": {
            "ci_id": {"type": "string"},
            "relationship_type": {
                "type": "string",
                "enum": ["depends_on", "depends_on_by", "all", "composition", "impact"]
            },
            "depth": {"type": "integer", "minimum": 1, "maximum": 5, "default": 2}
        }
    },
    "tool_output_schema": {
        "type": "object",
        "properties": {
            "nodes": {"type": "array"},
            "edges": {"type": "array"},
            "meta": {"type": "object"}
        }
    }
}
```

#### 3. History/Event Tools (이미 있지만 확장 필요)
```python
# history_combined_union (이미 있음)
# 추가 필요:
{
    "name": "work_history_query",
    "tool_type": "database_query",
    "description": "Query work/change history",
    "tool_input_schema": {...}
}
```

#### 4. Aggregation Tools
```python
{
    "name": "ci_aggregation",
    "tool_type": "database_query",
    "description": "Aggregate CIs by type, status, location, etc.",
    "tool_input_schema": {
        "type": "object",
        "required": ["group_by"],
        "properties": {
            "group_by": {
                "type": "array",
                "items": {"type": "string"},
                "description": ["ci_type", "status", "location", "owner"]
            },
            "filter": {"type": "object", "description": "Optional filters"}
        }
    }
}
```

---

### Phase 2: Orchestrator 리팩토링

#### 현재 구조
```python
# runner.py:1680
async def _handle_lookup_async(self):
    detail = await self._resolve_ci_detail_async()  # ← 직접 조회
    blocks.extend(await self._metric_blocks_async(detail))  # ← 직접 조회
    blocks.extend(await self._history_blocks_async(detail))  # ← 직접 조회
    ...
```

#### 목표 구조
```python
# runner.py (리팩토링 후)
async def _handle_lookup_async(self):
    # Step 1: CI 상세 조회 (Tool 사용)
    detail = await self._execute_tool_async(
        tool_name="ci_detail_lookup",
        params={
            "field": "ci_id",
            "value": self.ci_id,
            "tenant_id": self.tenant_id
        }
    )

    # Step 2: 메트릭 조회 (Tool 사용)
    if self.plan.metric:
        metrics = await self._execute_tool_async(
            tool_name="metric_query",
            params={
                "ci_id": self.ci_id,
                "metric_names": self.plan.metric.metrics,
                "time_range": self.plan.metric.time_range,
                "aggregation": self.plan.metric.aggregation
            }
        )

    # Step 3: 이력 조회 (Tool 사용)
    if self.plan.history.enabled:
        history = await self._execute_tool_async(
            tool_name="history_combined_union",
            params={
                "ci_id": self.ci_id,
                "start_time": self.plan.history.start_time,
                "end_time": self.plan.history.end_time
            }
        )

    # Step 4: 그래프 조회 (Tool 사용)
    if self.plan.graph:
        graph = await self._execute_tool_async(
            tool_name="ci_graph_query",
            params={
                "ci_id": self.ci_id,
                "relationship_type": self.plan.graph.view,
                "depth": self.plan.graph.depth
            }
        )

    # Step 5: 결과를 Block으로 변환
    blocks = self._build_blocks_from_tool_results(detail, metrics, history, graph)
    return blocks, answer

async def _execute_tool_async(self, tool_name: str, params: dict):
    """Execute a Tool Asset"""
    from app.modules.ops.services.ci.tools import ToolContext, get_tool_executor

    context = ToolContext(
        tenant_id=self.tenant_id,
        user_id=self.user_id,
        ci_id=self.ci_id
    )

    executor = get_tool_executor()
    result = await executor.execute(
        tool_name=tool_name,
        context=context,
        params=params
    )

    # Tool call 기록
    self.tool_calls.append(ToolCall(tool=tool_name, params=params, result=result))

    return result
```

---

### Phase 3: Mock 제거

#### 현재 (execute_universal)
```python
def run_metric(question, ...):
    result = execute_universal(question, "metric", tenant_id)
    if result.blocks:
        return result.blocks  # ← 데이터 있으면 반환
    else:
        return _mock_metric_blocks(question)  # ❌ Mock 반환
```

#### 목표
```python
def run_metric(question, ...):
    # 직접 Tool 사용
    result = await self._execute_tool_async(
        tool_name="metric_query",
        params={...}
    )

    if result.data:
        return _build_blocks_from_metric(result.data)  # ✅ 실제 데이터
    else:
        # ✅ 명시적 에러 (Mock 아님)
        return [MarkdownBlock(content="No metric data available")]
```

---

## 📝 구현 로드맵

### Week 1: Tool Asset 확장

**Day 1-2**: Metric Tools 생성
```
1. SQL 파일 생성: resources/queries/postgres/metrics/*.sql
   - metric_by_ci.sql
   - metric_aggregation.sql
   - metric_summary.sql

2. Tool Asset 등록
   - metric_query
   - metric_aggregation

3. 테스트 작성
```

**Day 3-4**: Graph Tools 생성
```
1. SQL 파일 생성: resources/queries/postgres/graph/*.sql
   - ci_dependencies.sql
   - ci_impact.sql
   - ci_composition.sql

2. Tool Asset 등록
   - ci_graph_query

3. 테스트 작성
```

**Day 5**: Aggregation Tools
```
1. SQL 파일 생성
2. Tool Asset 등록
```

### Week 2: Orchestrator 리팩토링

**Day 1-2**: _handle_lookup_async 수정
```python
async def _handle_lookup_async(self):
    # Tool 기반으로 변경
    detail = await self._execute_tool_async("ci_detail_lookup", {...})
    metrics = await self._execute_tool_async("metric_query", {...})
    ...
```

**Day 3-4**: 다른 handlers (_handle_aggregate_async, etc.) 수정

**Day 5**: Tool 호출 추적 개선

### Week 3: 통합 및 테스트

**Day 1-2**: execute_universal 단순화
```python
def execute_universal(question, mode, tenant_id):
    # Orchestrator가 Tool을 사용하므로 이제 간단함
    runner = CIOrchestratorRunner(...)
    return runner.run()  # ← Tool Asset 기반으로 동작
```

**Day 3-4**: 전체 통합 테스트

**Day 5**: 배포 및 검증

---

## 🎯 최종 결과

### Before (현재)
```
사용자 질의
    ↓
execute_universal()
    ↓
CIOrchestratorRunner.run()
    ├─ _handle_lookup_async()
    │  ├─ 직접 DB 쿼리
    │  ├─ 직접 API 호출
    │  └─ 내부 로직 (Tool 미사용 또는 불명확)
    ├─ _handle_aggregate_async()
    ├─ _handle_list_preview_async()
    └─ ...
    ↓
데이터 반환 (또는 Mock)
```

**문제**:
- ❌ Tool Asset이 정의되어 있지만 미사용
- ❌ 확장 불가능 (새 기능 추가 시 orchestrator 수정 필요)
- ❌ LLM이 Tool 호출 불가
- ❌ 데이터 소스 불명확

### After (리팩토링 후)
```
사용자 질의
    ↓
LLM이 의도 파악
    ↓
LLM이 Tool을 선택
    ├─ ci_detail_lookup
    ├─ metric_query
    ├─ history_combined_union
    ├─ ci_graph_query
    └─ ...
    ↓
Orchestrator (Tool 기반 실행)
    ├─ _execute_tool_async("ci_detail_lookup", {...})
    ├─ _execute_tool_async("metric_query", {...})
    ├─ _execute_tool_async("history_combined_union", {...})
    └─ _execute_tool_async("ci_graph_query", {...})
    ↓
Tool Asset 실행
    ├─ SQL 쿼리 (parameterized, 안전)
    ├─ 데이터 반환
    └─ 결과 추적
    ↓
Block으로 변환 및 반환
```

**장점**:
- ✅ Tool Asset 명시적 사용
- ✅ 데이터 소스 명확 (어떤 Tool을 사용했는지 기록)
- ✅ 확장 가능 (새 Tool 추가 시 orchestrator 수정 불필요)
- ✅ LLM 호출 가능 (Tool을 LLM이 선택)
- ✅ 완전한 추적 가능

---

## 💡 핵심 변경 사항

### 1. Tool Asset 추가

**새로 추가할 Tool Assets** (11개 총):
```
현재: 6개 (ci_*, maintenance_*, history_combined_union)
추가: 5개
  - metric_query
  - metric_aggregation
  - ci_graph_query
  - work_history_query
  - ci_aggregation

최종: 11개 Tool Asset
```

### 2. Orchestrator 메서드 추가

```python
async def _execute_tool_async(
    self,
    tool_name: str,
    params: dict
) -> ToolResult:
    """
    Execute a Tool Asset and track the call
    """
    context = ToolContext(
        tenant_id=self.tenant_id,
        user_id=self.user_id
    )

    executor = get_tool_executor()
    result = await executor.execute(
        tool_name=tool_name,
        context=context,
        params=params
    )

    # Track tool call
    self.tool_calls.append(ToolCall(
        tool=tool_name,
        params=params,
        result=result
    ))

    return result
```

### 3. Handler 메서드 수정

```python
# Before
async def _handle_lookup_async(self):
    detail = await self._resolve_ci_detail_async()  # ← 내부 구현

# After
async def _handle_lookup_async(self):
    detail = await self._execute_tool_async(  # ← Tool 사용
        tool_name="ci_detail_lookup",
        params={...}
    )
```

---

## 📊 예상 영향

### 코드량
- **Tool Asset 정의**: +500줄 (새 Tool 5개)
- **Orchestrator 수정**: +200줄 (새 메서드 + 수정)
- **SQL 파일**: +200줄 (새 쿼리)

### 성능
- **변화**: 거의 없음 (같은 SQL을 Tool로 변환할 뿐)
- **추적 오버헤드**: +5-10ms (Tool Call 기록)

### 테스트
- **새 테스트**: +20개 (각 Tool별 1-2개)
- **회귀 테스트**: 기존 모두 유지

---

## 🎓 결론

**당신의 요청이 정확합니다**:
> "orchestrator가 작동되도록 해주라. tools로 모두 꺼내서 제대로 제품처럼 작동되게 해주라."

이 리팩토링이 완료되면:
1. ✅ Orchestrator가 Tool Asset을 명시적으로 사용
2. ✅ 데이터 소스가 명확 (Tool → SQL)
3. ✅ LLM이 Tool을 호출할 수 있음
4. ✅ 새 기능 추가 시 Tool Asset만 추가하면 됨 (orchestrator 수정 불필요)
5. ✅ 완전한 제품화 (확장 가능한 구조)

**예상 기간**: 2-3주 (풀타임 작업 시)

이 계획에 동의하시면 즉시 구현을 시작하겠습니다. 🚀
