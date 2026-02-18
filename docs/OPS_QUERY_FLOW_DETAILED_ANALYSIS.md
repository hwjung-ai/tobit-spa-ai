# 🔄 OPS 질의 처리 전체 흐름 상세 분석

**작성일**: 2026-02-16 (최종 수정: 2026-02-16)
**범위**: 질의 입수부터 응답까지 전체 처리 과정

---

## ⚠️ 핵심: 세 개의 엔드포인트, 두 가지 아키텍처

OPS에는 **완전히 다른 2가지 실행 아키텍처**가 있습니다:

| 엔드포인트 | 도구 선택 방식 | Plan 생성 | 소스 위치 |
|-----------|-------------|---------|---------|
| **`POST /ops/ask`** | ✅ **LLM이 Tool description 읽고 동적 선택** | LLM Function Calling | `ci_ask.py` |
| **`POST /ops/ask/stream`** | ✅ **동일 (SSE 스트리밍 버전)** | LLM Function Calling | `ask_stream.py` |
| **`POST /ops/query`** | ❌ **모드별 하드코딩 Plan** | `_create_simple_plan(mode)` | `query.py` |

### Frontend에서의 라우팅

```
UI 모드 선택
├── "전체(all)" 모드 → POST /ops/ask 또는 /ops/ask/stream
└── 개별 모드 (config, metric, history, graph, document) → POST /ops/query
```

---

## 🅰️ `/ops/ask` — LLM 기반 범용 오케스트레이션

### 진입점

**파일**: `apps/api/app/modules/ops/routes/ci_ask.py:72-78`

```python
@router.post("/ask")
def ask_ops(
    payload: CiAskRequest,          # question, rerun, resolver_asset, schema_asset, ...
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
):
```

**입력**:
```json
{
  "question": "CI 'MES-06'의 최근 30일 이력 조회",
  "rerun": null
}
```

### 전체 처리 흐름 (6단계)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: 질의 정규화 (Normalization)                                    │
│ ci_ask.py:247-271                                                      │
│ - Resolver/Schema/Source/Mapping/Policy Asset 로드                     │
│ - _apply_resolver_rules() → alias_mapping, pattern_rule, transformation│
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 2: 계획 생성 (LLM Function Calling)                              │
│ ci_ask.py:340-392                                                      │
│                                                                        │
│ planner_llm.create_plan_output(question, schema, source)               │
│   → _call_output_parser_llm()  (planner_llm.py:280)                   │
│     → build_tools_for_llm_prompt()  (tool_schema_converter.py:160)     │
│       → convert_tools_to_function_calling()  (tool_schema_converter.py:17)│
│         → registry.get_available_tools()  ← ✅ Tool Registry 동적 로드  │
│     → llm.create_response(tools=tools)  ← ✅ LLM Function Calling      │
│     → extract_tool_call_from_response()  ← tool_use 추출               │
│                                                                        │
│ 결과: PlanOutput (kind=PLAN/DIRECT/REJECT)                             │
│ - PLAN → Phase 3으로 진행                                               │
│ - DIRECT → 직접 답변 반환 (도구 실행 없음)                               │
│ - REJECT → 거부 응답 반환                                               │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 3: 계획 검증 (Validation)                                        │
│ ci_ask.py:372-392                                                      │
│                                                                        │
│ validator.validate_plan(plan_raw, resolver_payload)                     │
│ - 도구 존재 여부 확인                                                    │
│ - 파라미터 유효성 검증                                                    │
│ - Policy 제약 조건 적용                                                  │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 4: 단계별 실행 (OpsOrchestratorRunner)                           │
│ ci_ask.py:456-476                                                      │
│                                                                        │
│ runner = OpsOrchestratorRunner(plan_validated, plan_raw, tenant_id, ...)│
│ result = runner.run(plan_output)                                       │
│                                                                        │
│ [Stage 1] Validate: Policy 확인 (tool_limits, time_ranges)            │
│ [Stage 2] Execute: Tool & Query 실행 (DB 조회)                         │
│ [Stage 3] Compose: Mapping 적용 + 블록 생성                            │
│ [Stage 4] Present: 최종 포맷팅 (마크다운)                               │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 5: 오류 처리 (Fallback)                                          │
│ ci_ask.py:479-520                                                      │
│                                                                        │
│ evaluate_replan() → 계획 수정 및 재시도                                  │
│ build_fallback_plan() → 단순화된 plan으로 재시도                         │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 6: 응답 및 저장 (Response & Persistence)                         │
│                                                                        │
│ - persist_execution_trace() → Inspector에 실행 흔적 저장               │
│ - QueryHistory 업데이트 (status, response, summary, trace_id)          │
│ - ResponseEnvelope 직렬화 → HTTP 응답 반환                              │
└────────────────────────────────────────────────────────────────────────┘
```

### 🎯 핵심: LLM 기반 Dynamic Tool Selection

**실제 소스 코드 (3단계 증명)**:

**Step 1: Tool Registry 동적 로드** (`tool_schema_converter.py:17-65`)
```python
def convert_tools_to_function_calling() -> List[Dict[str, Any]]:
    """Convert all available tools from ToolRegistry to function calling format."""
    tools = []
    registry = get_tool_registry()

    for name, tool in registry.get_available_tools().items():  # ✅ 동적 로드
        tool_function_spec = {
            "type": "function",
            "function": {
                "name": name,
                "description": tool.description or f"Execute {name} tool",  # ✅ description 사용
                "parameters": tool.input_schema or {...},  # ✅ input_schema 사용
            },
        }
        tools.append(tool_function_spec)
```

**Step 2: LLM에 Tools 전달** (`tool_schema_converter.py:160-194`)
```python
def build_tools_for_llm_prompt(include_planner: bool = True):
    """Build complete tools list and a descriptive text for LLM prompt."""
    available_tools = convert_tools_to_function_calling()  # ✅ Tool Registry 기반
    all_tools.extend(available_tools)
```

**Step 3: LLM Function Calling** (`planner_llm.py:280-340`)
```python
def _call_output_parser_llm(...):
    tools, _ = build_tools_for_llm_prompt(include_planner=True)  # 라인 311
    response = llm.create_response(
        model=OUTPUT_PARSER_MODEL,
        input=messages,
        tools=tools if tools else None,  # ✅ Function calling
        temperature=0,
    )
    tool_call = extract_tool_call_from_response(response)  # 라인 326
    if tool_call and tool_call.get("name") == "create_execution_plan":
        payload = tool_call.get("input", {})  # ✅ LLM이 선택한 plan
```

**동작 요약**:
```
사용자 질의 → Tool Registry에서 25개 Tool 동적 로드
  → 각 Tool의 description + input_schema를 LLM에 전달
  → LLM이 description 분석하여 최적 Tool 선택
  → Tool 추가 = Asset Registry 추가만 하면 됨 (코드 변경 불필요)
```

---

## 🅱️ `/ops/query` — 모드별 하드코딩 Plan

### 진입점

**파일**: `apps/api/app/modules/ops/routes/query.py:39-45`

```python
@router.post("/query", response_model=ResponseEnvelope)
def query_ops(
    payload: OpsQueryRequest,       # mode + question
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
):
```

**입력**:
```json
{
  "question": "CI 'MES-06'의 최근 30일 이력 조회",
  "mode": "history"
}
```

### 전체 처리 흐름 (단순화)

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. 라우팅                                                              │
│ query.py:105                                                           │
│                                                                        │
│ envelope, trace_data = handle_ops_query(payload.mode, payload.question)│
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ 2. 모드별 디스패치                                                      │
│ __init__.py:809-900 (handle_ops_query)                                 │
│                                                                        │
│ → _execute_real_mode(mode, question, settings)  (__init__.py:955)      │
│   → execute_universal(question, mode, tenant_id) (__init__.py:94)      │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ 3. 하드코딩 Plan 생성 ← ❌ LLM 미사용                                  │
│ __init__.py:230-334 (_create_simple_plan)                              │
│                                                                        │
│ mode == "config":                                                      │
│   → PrimarySpec(limit=10, tool_type="ci_lookup")                      │
│                                                                        │
│ mode == "graph":                                                       │
│   → GraphSpec(depth=2, view=NEIGHBORS, tool_type="ci_graph")          │
│                                                                        │
│ mode == "document":                                                    │
│   → PrimarySpec(limit=5, tool_type="document_search")                 │
│                                                                        │
│ mode in ("metric", "all"):                                             │
│   → MetricSpec(metric_name="cpu_usage", agg="max", time_range="last_24h")│
│                                                                        │
│ mode in ("hist", "history"):                                           │
│   → HistorySpec(enabled=True, source="work_and_maintenance", limit=30)│
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ 4. OpsOrchestratorRunner 실행                                          │
│ __init__.py:117-130                                                    │
│                                                                        │
│ runner = OpsOrchestratorRunner(plan, plan, tenant_id, question, ...)   │
│ result = runner.run(plan_output=None)                                  │
│ → 고정된 Plan에 따라 Tool 실행 (LLM 선택 없음)                          │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│ 5. 응답 반환                                                           │
│ query.py:107-143                                                       │
│                                                                        │
│ ResponseEnvelope.success(data={answer, trace})                         │
│ QueryHistory 업데이트                                                   │
└────────────────────────────────────────────────────────────────────────┘
```

### 특징

- ❌ **LLM 미사용**: `_create_simple_plan()`이 모드에 따라 고정된 Plan 생성
- ❌ **Tool description 미참조**: 모드 → tool_type 매핑이 코드에 하드코딩
- ✅ **동일한 Runner 사용**: OpsOrchestratorRunner는 `/ops/ask`와 동일
- ✅ **빠른 응답**: LLM 호출 없이 바로 실행

---

## 🅲 `/ops/ask/stream` — SSE 스트리밍 버전

### 진입점

**파일**: `apps/api/app/modules/ops/routes/ask_stream.py:81-106`

```python
@router.post("/ask/stream")
async def ask_ops_stream(
    payload: CiAskRequest,
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
) -> StreamingResponse:
```

### 처리 흐름

`/ops/ask`와 **동일한 아키텍처** (LLM Function Calling)를 사용하되, SSE 이벤트로 진행 상황을 실시간 전달합니다.

**SSE 이벤트 타입**:
- `progress`: 현재 단계 (init → resolving → planning → executing → composing → presenting → complete)
- `tool_complete`: 도구 실행 완료
- `block`: 개별 응답 블록
- `complete`: 최종 결과
- `error`: 오류 발생

**처리 단계** (`ask_stream.py:130-411`):
```
Stage 1 (init)      → history entry 생성, SSE progress 전송
Stage 2 (resolving) → Asset 로드 (resolver, schema, source, mapping, policy)
Stage 3 (planning)  → planner_llm.create_plan_output() ← ✅ LLM Function Calling
Stage 4 (executing) → OpsOrchestratorRunner.run()
Stage 5 (composing) → 블록별 SSE block 이벤트 전송
Stage 6 (presenting)→ complete 이벤트 전송
```

---

## 📊 두 아키텍처 비교

| 항목 | `/ops/ask` (LLM 범용) | `/ops/query` (모드별 고정) |
|------|----------------------|--------------------------|
| **Tool 선택 주체** | Claude LLM | 코드 (`_create_simple_plan`) |
| **Tool description 활용** | ✅ Registry에서 읽어 LLM에 전달 | ❌ 미사용 |
| **새 Tool 추가 시** | Asset Registry에 추가만 하면 됨 | 코드 수정 필요 |
| **LLM 호출** | ✅ 1회 이상 (planner) | ❌ 없음 |
| **응답 속도** | 느림 (LLM 호출 포함) | 빠름 (직접 실행) |
| **유연성** | 높음 (질의에 따라 동적) | 낮음 (모드에 고정) |
| **사용 모드** | "전체(all)" | config, metric, history, graph, document |
| **Plan 유형** | PlanOutput (PLAN/DIRECT/REJECT) | Plan (고정 spec) |
| **오류 복구** | evaluate_replan() 재계획 | 없음 |
| **Runner** | OpsOrchestratorRunner (동일) | OpsOrchestratorRunner (동일) |

### 핵심 차이

```
/ops/ask:
  사용자 질의 → LLM이 25개 Tool의 description 분석 → 최적 Tool 선택 → 실행

/ops/query:
  사용자 질의 + mode → 코드가 mode에 따라 고정 tool_type 선택 → 실행
```

---

## 📋 사용되는 Asset 유형별 정리

### Published Tools (25개) — `/ops/ask`에서 LLM이 동적 선택

Tool Registry에 등록된 모든 Tool의 `name`, `description`, `input_schema`가 LLM에 전달됩니다.

주요 Tool 예시:
- `work_history_query`: "Query work history records for a CI with optional time range filtering"
- `maintenance_history_list`: "List maintenance records with optional filtering and pagination"
- `ci_detail_lookup`: "Fetch CI configuration details"
- `metric_series`: "Fetch time series metric data"
- `ci_graph_query`: "Query CI relationships and topology"
- `document_search`: "Search documents with hybrid BM25 + vector search"

### Published Prompts (14개)

| 분류 | Prompt | 역할 |
|------|--------|------|
| **라우팅** | ops_all_router | 전체 모드 라우팅 |
| **라우팅** | ops_metric_router | 메트릭 모드 라우팅 |
| **라우팅** | ops_graph_router | 그래프 모드 라우팅 |
| **라우팅** | ops_history_router | 이력 모드 라우팅 |
| **계획** | ci_universal_planner | 범용 계획 수립 |
| **계획** | ci_planner_output_parser | 계획 출력 파싱 |
| **합성** | ci_compose_summary | 결과 요약 합성 |
| **합성** | ci_universal_compose | 범용 결과 합성 |
| **합성** | ops_composer | OPS 결과 합성 |
| **제시** | ci_universal_present | 범용 최종 제시 |
| **제시** | ci_response_builder | 응답 구축 |
| **유틸** | ops_normalizer | 질의 정규화 |
| **유틸** | ci_validator | 응답 검증 |
| **유틸** | ops_langgraph | LangGraph 기반 합성 |

### 기타 Assets

| 유형 | 예시 | 역할 |
|------|------|------|
| **Resolver** | default_resolver | 환경 변수 폴백, alias mapping |
| **Schema** | ops_default_schema | 스키마 컨텍스트 |
| **Source** | default_postgres | DB 연결 정보 |
| **Mapping** | graph_relation, history_keywords, table_hints | 데이터 변환 규칙 |
| **Policy** | plan_budget, tool_limits, time_ranges | 제약 조건 |

---

## 🔄 `/ops/ask` Phase별 상세

### Phase 1: 질의 정규화 (ci_ask.py:247-271)

```python
# Asset 로드
resolver_payload = load_resolver_asset(resolver_asset_name)
schema_payload = load_catalog_asset(schema_asset_name)
source_payload = load_source_asset(source_asset_name)
mapping_payload, _ = load_mapping_asset("graph_relation", scope="ops")
load_policy_asset("plan_budget", scope="ops")

# Resolver 규칙 적용
normalized_question, resolver_rules_applied = _apply_resolver_rules(
    payload.question, resolver_payload
)
```

**Resolver 규칙 유형** (`ci_ask.py:180-225`):
- `alias_mapping`: 엔티티명 치환 (예: "MES서버" → "MES-06")
- `pattern_rule`: 정규식 기반 변환
- `transformation`: lowercase, uppercase, strip

### Phase 2: 계획 생성 (ci_ask.py:340-392)

```python
# 정상 경로 (rerun이 아닌 경우)
plan_output = planner_llm.create_plan_output(
    normalized_question,
    schema_context=schema_payload,
    source_context=source_payload,
)
# → 내부적으로 LLM Function Calling 실행
# → Tool Registry에서 모든 Tool 동적 로드
# → LLM이 Tool description 분석하여 최적 선택

# 검증
if plan_output.kind == PlanOutputKind.PLAN and plan_output.plan:
    plan_validated, plan_trace = validator.validate_plan(
        plan_raw, resolver_payload=resolver_payload
    )
```

**PlanOutput 3가지 경로**:
- `PLAN` → 도구 실행이 필요 → Phase 4로 진행
- `DIRECT` → LLM이 직접 답변 가능 → 바로 응답 (ci_ask.py:410-451)
- `REJECT` → 처리 불가 → 거부 응답 반환

### Phase 3: 계획 검증 (ci_ask.py:372-392)

```python
plan_validated, plan_trace = validator.validate_plan(
    plan_raw, resolver_payload=resolver_payload
)
plan_output = plan_output.model_copy(update={"plan": plan_validated})
```

### Phase 4: 단계별 실행 (ci_ask.py:456-476)

```python
runner = OpsOrchestratorRunner(
    plan_validated,   # 검증된 Plan
    plan_raw,         # 원본 Plan
    tenant_id,
    normalized_question,
    plan_trace,
    rerun_context=rerun_ctx,
    asset_overrides=payload.asset_overrides,
)
runner._flow_spans_enabled = True
runner._runner_span_id = runner_span
result = runner.run(plan_output)
```

**Runner 내부 4단계**:
1. **Validate Stage**: Policy 확인 (ci_column_allowlist, time_ranges)
2. **Execute Stage**: Tool 실행 → Query Asset으로 SQL 조회 → Source Asset으로 DB 연결
3. **Compose Stage**: Mapping Asset 적용 → 데이터 변환 → 블록 생성
4. **Present Stage**: Prompt Asset으로 최종 마크다운 포맷팅

### Phase 5: 오류 처리 (ci_ask.py 내부)

```python
# 오류 발생 시 재계획
replan_result = evaluate_replan(...)
# 또는 단순화된 fallback plan
fallback_plan = build_fallback_plan(source_plan)
```

### Phase 6: 응답 및 저장

```python
# Inspector에 실행 흔적 저장
persist_execution_trace(
    session=session,
    trace_id=active_trace_id,
    feature="ops",
    endpoint="/ops/ask",
    ...
)

# QueryHistory 업데이트
history_entry.status = status
history_entry.response = result
history_entry.summary = meta.get("summary")
```

---

## 🔄 `/ops/query` Phase별 상세

### 1. 모드 디스패치 (query.py:105)

```python
envelope, trace_data = handle_ops_query(payload.mode, payload.question)
```

### 2. handle_ops_query (__init__.py:809-900)

```python
def handle_ops_query(mode, question):
    settings = get_settings()
    # → _execute_real_mode(mode, question, settings)
```

### 3. 하드코딩 Plan 생성 (__init__.py:230-334)

```python
def _create_simple_plan(mode: str, question: str = "") -> Plan:
    if mode == "config":
        primary = PrimarySpec(limit=10, tool_type="ci_lookup")
    elif mode == "graph":
        graph = GraphSpec(depth=2, view=View.NEIGHBORS, tool_type="ci_graph")
    elif mode == "document":
        primary = PrimarySpec(limit=5, tool_type="document_search", keywords=[question])
    elif mode in ("metric", "all"):
        metric = MetricSpec(metric_name="cpu_usage", agg="max", time_range="last_24h")
    elif mode in ("hist", "history"):
        history = HistorySpec(enabled=True, source="work_and_maintenance", limit=30)

    return Plan(
        intent=intent, view=view, mode=plan_mode,
        primary=primary, aggregate=aggregate, graph=graph,
        metric=metric, history=history, output=output,
        execution_strategy=ExecutionStrategy.SERIAL,
        mode_hint=mode,
    )
```

### 4. OpsOrchestratorRunner 실행 (__init__.py:117-130)

```python
runner = OpsOrchestratorRunner(
    plan=plan, plan_raw=plan, tenant_id=tenant_id,
    question=question, policy_trace=policy_trace,
)
result = runner.run(plan_output=None)  # plan_output=None → DIRECT/REJECT 경로 없음
```

### 5. 응답 (query.py:107-143)

```python
response_payload = ResponseEnvelope.success(data={"answer": answer_dict, "trace": trace_data})
# QueryHistory 업데이트
```

---

## 📄 Document 모드 상세

Document 모드는 두 경로 모두에서 사용됩니다:

### `/ops/ask`에서 Document 처리
- LLM이 `document_search` Tool의 description을 분석
- 질의가 문서 관련이면 LLM이 자동으로 `document_search` 선택
- 다른 Tool과 병렬 실행 가능

### `/ops/query`에서 Document 처리
- `mode="document"` → `_create_simple_plan("document", question)`
- `PrimarySpec(limit=5, tool_type="document_search", keywords=[question])`

### DocumentSearchService 내부 흐름

```
질의
  ├─ _text_search()     → PostgreSQL tsvector (BM25 전문검색)
  ├─ _vector_search()   → pgvector (semantic search, 1536-dim)
  └─ 결과 병합: RRF (Reciprocal Rank Fusion)
```

**구현 위치**:
- Service: `apps/api/app/modules/document_processor/services/search_service.py`
- API: `apps/api/app/modules/document_processor/router.py` → `POST /api/documents/search`
- OPS 통합: `apps/api/app/modules/ops/services/__init__.py:_run_document()`

---

## 🎯 전체 시각화

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 질의                                │
│                   "CI 'MES-06' 최근 30일 이력"                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │  Frontend 모드 선택  │
                    └─────────┬─────────┘
              ┌───────────────┼───────────────┐
              ↓                               ↓
    ┌─────────────────┐             ┌─────────────────┐
    │  "전체(all)" 모드  │             │   개별 모드 선택   │
    │  → POST /ops/ask │             │  → POST /ops/query│
    └────────┬────────┘             └────────┬────────┘
             ↓                               ↓
    ┌─────────────────┐             ┌─────────────────┐
    │ Phase 1: 정규화   │             │ handle_ops_query │
    │ Resolver 적용     │             │ mode dispatch    │
    └────────┬────────┘             └────────┬────────┘
             ↓                               ↓
    ┌─────────────────┐             ┌─────────────────┐
    │ Phase 2: LLM     │             │ _create_simple_  │
    │ Function Calling │             │ plan(mode)       │
    │ Tool Registry    │             │ ❌ 하드코딩       │
    │ ✅ 동적 선택      │             └────────┬────────┘
    └────────┬────────┘                      │
             ↓                               │
    ┌─────────────────┐                      │
    │ Phase 3: 검증    │                      │
    │ validator        │                      │
    └────────┬────────┘                      │
             ↓                               ↓
    ┌─────────────────────────────────────────────────┐
    │         OpsOrchestratorRunner.run()              │
    │  (동일한 Runner가 양쪽 경로 모두 실행)              │
    │                                                   │
    │  [Validate] → [Execute] → [Compose] → [Present]  │
    │       ↓           ↓           ↓           ↓       │
    │    Policy      Tool/Query   Mapping     Prompt    │
    │    Assets      Assets       Assets      Assets    │
    └────────────────────┬────────────────────────────┘
                         ↓
    ┌─────────────────────────────────────────────────┐
    │              최종 응답 (JSON)                      │
    │  {                                               │
    │    answer: "MES-06의 최근 30일...",                │
    │    blocks: [table, timeline, summary],           │
    │    trace: {...},                                  │
    │    meta: {timing_ms, summary, trace_id}          │
    │  }                                               │
    └─────────────────────────────────────────────────┘
```

---

## 🔍 핵심 통찰

### 1. 두 아키텍처가 공존하는 이유

- `/ops/ask`: **범용성** — 어떤 질의든 LLM이 최적 Tool 조합을 찾아냄
- `/ops/query`: **속도** — 모드가 이미 정해져 있으므로 LLM 호출 없이 바로 실행
- 공통점: 최종 실행은 동일한 `OpsOrchestratorRunner`가 담당

### 2. Tool 추가 시 영향

- `/ops/ask` 경로: **코드 변경 불필요** — Asset Registry에 Tool 추가만 하면 LLM이 자동으로 인식
- `/ops/query` 경로: **코드 수정 필요** — `_create_simple_plan()`에 새 모드/tool_type 추가 필요

### 3. Streaming 엔드포인트

- `/ops/ask/stream`은 `/ops/ask`와 동일한 LLM 기반 아키텍처
- SSE로 실시간 진행 상황 전달 (ChatGPT 스타일 상태 표시)

---

## 📁 주요 소스 파일

| 파일 | 역할 |
|------|------|
| `routes/ci_ask.py` | `/ops/ask` 엔드포인트 (LLM 범용) |
| `routes/ask_stream.py` | `/ops/ask/stream` SSE 스트리밍 |
| `routes/query.py` | `/ops/query` 엔드포인트 (모드별 고정) |
| `services/__init__.py` | `handle_ops_query()`, `_create_simple_plan()`, `execute_universal()` |
| `services/orchestration/planner/planner_llm.py` | LLM Function Calling |
| `services/orchestration/planner/tool_schema_converter.py` | Tool Registry → LLM 도구 변환 |
| `services/orchestration/planner/validator.py` | Plan 검증 |
| `services/orchestration/orchestrator/runner.py` | OpsOrchestratorRunner (공용) |
| `services/control_loop.py` | evaluate_replan() 오류 복구 |

---

*이 문서의 모든 코드 참조는 실제 소스 코드 기반입니다.*
*생성일: 2026-02-16*
