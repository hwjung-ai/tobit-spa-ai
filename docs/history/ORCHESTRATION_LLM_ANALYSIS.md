# 범용 오케스트레이션 LLM 호출 분석

## 개요

이 문서는 `/ops/ci/ask` 엔드포인트로 질의를 처리하는 범용 오케스트레이션 시스템의 동작 프로세스와 LLM 호출 지점을 상세하게 설명합니다.

---

## 전체 아키텍처

```
HTTP POST /ops/ci/ask
    ↓
1. Router Layer (ops/router.py)
    ↓
2. Planner Layer (planner/planner_llm.py)
    ↓
3. Runner Layer (orchestrator/runner.py)
    ↓
4. Stage Executor Layer (orchestrator/stage_executor.py)
    ↓
5. Tool Executor Layer (tools/executor.py)
```

---

## 상세 처리 프로세스

### 1. Router Layer (`apps/api/app/modules/ops/router.py`)

**엔드포인트**: `@router.post("/ci/ask")`

**주요 동작**:
- 요청 수신 및 History 생성 (QueryHistory 레코드)
- Resolver 규칙 적용 (질문 정규화)
- Asset 로드 (schema, source, mapping, policy, resolver)
- Planner 호출로 Plan 생성
- (rerun이 아닌 경우) Runner 실행으로 Plan 실행

**코드 흐름**:
```python
@router.post("/ci/ask")
def ask_ci(payload: CiAskRequest, request: Request, tenant_id: str = Depends(_tenant_id)):
    # 1. History 생성
    history_entry = QueryHistory(...)
    
    # 2. Asset 로드
    resolver_payload = load_resolver_asset(...)
    schema_payload = load_catalog_asset(...)
    source_payload = load_source_asset(...)
    
    # 3. 질문 정규화
    normalized_question = _apply_resolver_rules(payload.question, resolver_payload)
    
    # 4. Plan 생성 (rerun이 아니면)
    if not payload.rerun:
        plan_output = planner_llm.create_plan_output(
            normalized_question,
            schema_context=schema_payload,
            source_context=source_context,
        )
    
    # 5. Runner 실행
    runner = CIOrchestratorRunner(plan_validated, ...)
    result = runner.run(plan_output)
```

---

### 2. Planner Layer (`apps/api/app/modules/ops/services/ci/planner/planner_llm.py`)

**주요 함수**: `create_plan_output(question, schema_context, source_context)`

#### LLM 호출 지점 #1: Output Parser

**함수**: `_call_output_parser_llm(text, schema_context, source_context)`

**목적**: 사용자 질문을 분석하여:
- Route 결정 (direct/plan/reject/orch)
- Output types 식별 (text/table/chart/network)
- CI identifiers 추출
- 필터 정의

**프롬프트 구조**:
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt_template.replace("{question}", text)}
]
```

**환경 변수**:
- `OPS_CI_OUTPUT_PARSER_MODEL` (기본값: `gpt-4o-mini`)

**응답 형식**:
```json
{
  "route": "orch|direct|reject",
  "output_types": ["text", "table"],
  "ci_identifiers": ["sys-xxx", "srv-yyy"],
  "filters": [...]
}
```

**코드 흐름**:
```python
def create_plan_output(...):
    # LLM 호출하여 route 및 파라미터 추출
    llm_payload = _call_output_parser_llm(normalized, schema_context, source_context)
    
    # Safety check: CI 코드나 인프라 키워드가 있으면 reject/direct → orch로 변경
    if route in ("reject", "direct"):
        if ci_codes or has_infra_keyword:
            route = "orch"
    
    # Route에 따른 PlanOutput 생성
    if route == "direct":
        return PlanOutput(kind=PlanOutputKind.DIRECT, ...)
    elif route == "reject":
        return PlanOutput(kind=PlanOutputKind.REJECT, ...)
    else:
        plan = create_plan(normalized, schema_context, source_context)
        return PlanOutput(kind=PlanOutputKind.PLAN, plan=plan)
```

**Plan 객체 생성 (Heuristic 방식)**:
LLM이 실패하거나 호출되지 않은 경우, Heuristic 방식으로 Plan 생성:
- Intent 결정: LOOKUP/AGGREGATE/PATH/EXPAND
- View 결정: SUMMARY/COMPOSITION/DEPENDENCY/IMPACT/PATH
- Primary/Secondary spec: keywords, filters
- Aggregate spec: group_by, metrics, scope
- Metric spec: metric_name, agg, time_range
- Graph spec: depth, view, limits
- History spec: time_range, limit, scope

---

### 3. Runner Layer (`apps/api/app/modules/ops/services/ci/orchestrator/runner.py`)

**주요 클래스**: `CIOrchestratorRunner`

**주요 메서드**: `run(plan_output)`

#### 실행 흐름

```python
async def _run_async(self) -> Dict[str, Any]:
    # 1. Intent에 따른 routing 결정
    if self.plan.mode == PlanMode.AUTO:
        blocks, answer, auto_trace = await self._run_auto_recipe_async()
    elif self.plan.intent == Intent.LIST:
        blocks, answer = await self._handle_list_preview_async()
    elif self.plan.metric:
        blocks, answer = await self._handle_lookup_async()
    elif self.plan.intent == Intent.LOOKUP:
        blocks, answer = await self._handle_lookup_async()
    elif self.plan.intent == Intent.AGGREGATE:
        blocks, answer = await self._handle_aggregate_async()
    elif self.plan.intent == Intent.PATH:
        blocks, answer = await self._handle_path_async()
    else:
        blocks, answer = await self._handle_lookup_async()
    
    # 2. Trace 및 meta 생성
    trace = {
        "plan_raw": self.plan_raw.model_dump(),
        "plan_validated": self.plan.model_dump(),
        "tool_calls": [call.model_dump() for call in self.tool_calls],
        "references": self.references,
        ...
    }
    
    return {"answer": answer, "blocks": blocks, "trace": trace, ...}
```

#### Tool 실행 (Registry 기반)

Runner는 더 이상 내장 도구(ci_search, ci_get, metric_aggregate 등)를 직접 실행하지 않습니다.

대신 **Tool Registry**를 통한 도구 실행:
```python
async def _ci_search_async(self, keywords, filters, limit, sort):
    result_data = await self._ci_search_via_registry_async(keywords, filters, limit, sort)
    # ToolRegistry에서 등록된 도구 실행
```

**Tool Registry 경로**: `ToolExecutor.execute(tool_type, context, params)`

**도구 타입**:
- `ci_lookup`: CI 검색/상세 조회
- `ci_aggregate`: CI 집계
- `metric`: 메트릭 조회 (aggregate/series)
- `ci_graph`: 그래프 확장/경로
- `history`: 이력 조회
- `event_aggregate`: 이벤트 집계

**참고**: Runner 자체에서는 LLM 호출이 없습니다. 모든 LLM 호출은 Planner와 Stage Executor에서 발생합니다.

---

### 4. Stage Executor Layer (`apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py`)

**주요 클래스**: `StageExecutor`

**실행 스테이지**:
1. `route_plan`: 실행 경로 결정 (이미 완료된 상태)
2. `validate`: Plan 및 Asset 유효성 검사
3. `execute`: 도구 실행
4. `compose`: 실행 결과 요약 (LLM 호출 지점)
5. `present`: 최종 프레젠테이션

#### LLM 호출 지점 #2: Compose Summary

**함수**: `_generate_llm_summary(question, intent, execution_results, composed_result)`

**목적**: 실행 결과를 바탕으로 자연스러운 한국어 요약 생성

**프롬프트 구조**:
```python
def _load_compose_prompt_templates(self):
    # Asset Registry에서 ci_compose_summarize 프롬프트 로드
    prompt_data = load_prompt_asset("ci", "compose", "ci_compose_summary")
    return prompt_data.get("templates", {})
```

**프롬프트 템플릿**:
- System 프롬프트: 요약 작성 지침
- User 프롬프트: `{question}`, `{intent}`, `{evidence}` 플레이스홀더

**환경 변수**:
- `CHAT_MODEL` (기본값: `gpt-4o-mini`)

**코드 흐름**:
```python
async def _execute_compose(self, stage_input: StageInput) -> Dict[str, Any]:
    # 1. Query Asset 실행 (실제 데이터 가져오기)
    real_data_results = await self._execute_query_assets_for_real_data(stage_input)
    
    # 2. 실행 결과 준비 (tool calls → execution_results 변환)
    execution_results = self._convert_tool_calls_to_execution_results(tool_calls)
    
    # 3. Intent에 따라 결과 구성
    if intent == "LOOKUP":
        composed_result["primary_result"] = primary_results[0]
        composed_result["results_summary"] = self._summarize_lookup_results(...)
    elif intent == "AGGREGATE":
        composed_result["aggregate_result"] = aggregate_results[0]
        composed_result["results_summary"] = self._summarize_aggregate_results(...)
    elif intent == "PATH":
        composed_result["path_results"] = path_results
        composed_result["results_summary"] = self._summarize_path_results(...)
    
    # 4. LLM으로 실행 결과 요약 (LLM 호출 #2)
    llm_summary = await self._generate_llm_summary(
        question=question,
        intent=intent,
        execution_results=execution_results,
        composed_result=composed_result,
    )
    composed_result["llm_summary"] = llm_summary
    
    return composed_result
```

**실행 결과 설명 (`_describe_execution_results`)**:
LLM 컨텍스트를 위해 실행 결과를 상세하게 설명:
- Primary result: CI 검색 결과
- Aggregate result: 집계 결과 (count, metrics)
- Path result: 경로 결과 (node_count, edge_count)
- Query Asset result: 쿼리 자산 실행 결과 (SQL, rows)

---

## LLM 호출 총계

### 정상 실행 시나리오

| 단계 | 지점 | 목적 | 모델 | 빈도 |
|------|------|------|------|------|
| 1 | Planner `_call_output_parser_llm()` | 질문 분석, Route 결정 | `OPS_CI_OUTPUT_PARSER_MODEL` (gpt-4o-mini) | **항상** |
| 2 | Stage Executor `_generate_llm_summary()` | 실행 결과 요약 | `CHAT_MODEL` (gpt-4o-mini) | **항상** |

**총 LLM 호출 수**: **2회** (정상 실행 시)

### 예외 시나리오

#### 시나리오 1: Direct Answer Route

```
LLM 호출 #1: route = "direct" 감지
→ Planner에서 direct_answer 생성 (추가 LLM 없음)
→ Stage에서 compose 스킵 (LLM 호출 #2 없음)

총 LLM 호출: 1회
```

#### 시나리오 2: Reject Route

```
LLM 호출 #1: route = "reject" 감지
→ Planner에서 reject_payload 생성 (추가 LLM 없음)
→ Stage에서 compose 스킵 (LLM 호출 #2 없음)

총 LLM 호출: 1회
```

#### 시나리오 3: LLM Parser 실패

```
LLM 호출 #1: 실패 → fallback으로 Heuristic Plan 생성
→ Runner 실행
→ LLM 호출 #2: compose summary (여전히 발생)

총 LLM 호출: 1회 (compose만)
```

---

## LLM 호출 상세 분석

### 호출 #1: Output Parser

**위치**: `planner_llm.py` → `create_plan_output()` → `_call_output_parser_llm()`

**코드**:
```python
def _call_output_parser_llm(text, schema_context=None, source_context=None):
    messages = _build_output_parser_messages(text, schema_context, source_context)
    
    llm = get_llm_client()
    response = llm.create_response(
        model=OUTPUT_PARSER_MODEL,
        input=messages,
        temperature=0,  # Deterministic
    )
    
    content = llm.get_output_text(response)
    json_text = _extract_json_block(content)
    payload = json.loads(json_text)
    
    return payload
```

**입력**:
- System 프롬프트: 질문 분석 및 구조화된 JSON 출력 지침
- User 프롬프트: 질문 + 스키마 컨텍스트 + 소스 컨텍스트

**출력**:
```json
{
  "route": "orch",
  "output_types": ["table", "text"],
  "ci_identifiers": ["sys-prod-web-01"],
  "list": {"enabled": false},
  "filters": []
}
```

**용도**:
- 질문의 실행 경로 결정 (orchestrate vs direct vs reject)
- 필요한 데이터 타입 식별
- CI 코드/식별자 추출
- 필터 조건 추출

### 호출 #2: Compose Summary

**위치**: `stage_executor.py` → `_execute_compose()` → `_generate_llm_summary()`

**코드**:
```python
async def _generate_llm_summary(self, question, intent, execution_results, composed_result):
    # 실행 결과를 설명하는 텍스트 생성
    evidence = self._describe_execution_results(execution_results, composed_result)
    
    # 프롬프트 로드
    templates = self._load_compose_prompt_templates()
    system_prompt = templates.get("system")
    user_template = templates.get("user")
    
    # 프롬프트 빌드
    prompt = user_template.replace("{question}", question)\
                       .replace("{intent}", intent)\
                       .replace("{evidence}", evidence)
    
    # LLM 호출
    llm = get_llm_client()
    response = llm.create_response(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    
    content = llm.get_output_text(response)
    return content.strip()
```

**입력**:
- System 프롬프트: 요약 작성 스타일 및 형식 지침
- User 프롬프트: 
  - `{question}`: 사용자 질문
  - `{intent}`: LOOKUP/AGGREGATE/PATH
  - `{evidence}`: 실행 결과 상세 설명

**Evidence 예시**:
```
Execution Results:

1. PRIMARY Result:
   - Source: ci_lookup
   - Count: 1
   - CI Code: sys-prod-web-01
   - CI Name: Production Web Server 01
   - CI Type: server
   - Subtype: web
   - Status: active
```

**출력**:
자연스러운 한국어 요약 텍스트
```markdown
sys-prod-web-01 서버가 활성 상태입니다. 이 서버는 웹 타입으로, Production 환경에서 운영되고 있습니다.
```

**용도**:
- 도구 실행 결과를 사용자에게 친숙한 형식으로 변환
- 복잡한 JSON 결과를 자연어로 설명
- 중요 정보 강조 (CI 상태, 구성, 메트릭 등)

---

## LLM 호출 없는 부분

### 1. 도구 실행 (Tool Registry)

- **위치**: Runner 및 Stage Executor
- **방식**: Tool Registry에서 등록된 도구 직접 실행
- **이유**: 결정적 실행 필요 (LLM 도입 불필요)
- **도구 예시**:
  - CI Lookup: 데이터베이스 쿼리 실행
  - Metric Query: TimescaleDB 집계 쿼리 실행
  - Graph Expand: Neo4j Cypher 쿼리 실행

### 2. Validator

- **위치**: Planner → `validator.validate_plan()`
- **방식**: Pydantic 스키마 검증 + 정책 검사
- **이유**: 구조적 검증 (LLM 불필요)

### 3. Policy 적용

- **위치**: Planner 및 Validator
- **방식**: 정책 룰 기반 검증 (depth, timeout 등)
- **이유**: 규칙 기반 검증 (LLM 불필요)

---

## 전체 호출 시퀀스 (정상 케이스)

```
1. 사용자 질문: "sys-prod-web-01 서버 상태 확인해줘"

2. Router
   ├─ History 생성 (QueryHistory)
   ├─ Asset 로드 (schema, source, mapping, policy, resolver)
   ├─ 질문 정규화 (resolver 규칙 적용)
   └─ Planner 호출

3. Planner
   ├─ LLM 호출 #1: _call_output_parser_llm()
   │  ├─ 입력: "sys-prod-web-01 서버 상태 확인해줘" + context
   │  └─ 출력: route="orch", output_types=["text", "table"], ci_identifiers=["sys-prod-web-01"]
   ├─ Plan 생성 (Heuristic)
   │  ├─ intent=LOOKUP, view=SUMMARY
   │  ├─ primary.keywords=["sys-prod-web-01"]
   │  └─ metric=null
   └─ PlanOutput 반환

4. Runner (execute stage)
   ├─ Tool Registry 실행: ci_lookup
   │  └─ DB 조회: SELECT * FROM ci WHERE ci_code='sys-prod-web-01'
   ├─ 결과: {ci_code: "sys-prod-web-01", ci_name: "Production Web Server 01", status: "active", ...}
   └─ blocks 생성 (ci_detail, metric, history 등)

5. Stage Executor (compose stage)
   ├─ Query Asset 실행 시도 (실제 데이터 확인)
   ├─ 실행 결과 변환 (tool_calls → execution_results)
   └─ LLM 호출 #2: _generate_llm_summary()
      ├─ 입력: question="sys-prod-web-01 서버 상태 확인해줘", intent="LOOKUP"
      │         evidence="Execution Results:\n1. PRIMARY Result:\n   - CI Code: sys-prod-web-01..."
      └─ 출력: "sys-prod-web-01 서버가 활성 상태입니다. 이 서버는 웹 타입으로..."

6. Stage Executor (present stage)
   └─ LLM summary를 markdown 블록으로 포맷팅

7. Router (완료)
   ├─ History 업데이트
   ├─ Execution Trace 저장
   └─ 응답 반환: {answer, blocks, trace, meta}

총 LLM 호출: 2회
```

---

## 성능 고려사항

### LLM 호출 병렬화

현재 구조에서는 LLM 호출이 순차적입니다:
- 호출 #1 (Planner)이 완료되어야 호출 #2 (Compose)가 가능

### 캐싱 전략

**Tool 결과 캐싱**:
- `ToolResultCache` 클래스로 도구 실행 결과 캐싱
- 동일 파라미터로 반복 호출 시 캐시 사용

**Query Asset 결과 캐싱**:
- `StageExecutor._query_asset_results` 필드로 compose/present 스테이지 간 캐싱
- 동일 질문에 대한 반복 SQL 실행 방지

### 비동기 실행

- 모든 도구 실행은 `asyncio`를 통해 비동기로 수행
- Tool Registry 도구 실행은 비동기 메서드 제공
- 병렬 가능한 작업 (예: metric + history) 동시 실행 가능

---

## 요약

### LLM 호출 총계

| 시나리오 | LLM 호출 수 | 설명 |
|---------|------------|------|
| **정상 Orchestrate** | 2회 | Planner(1) + Compose(1) |
| Direct Answer | 1회 | Planner만 |
| Reject | 1회 | Planner만 |
| LLM Parser 실패 | 1회 | Compose만 |

### 호출 목적

1. **Planner LLM**: 질문 이해 및 구조화된 Plan 생성
2. **Compose LLM**: 실행 결과를 자연어로 변환 및 사용자 친화

### 호출 특성

- **Planner LLM**: Low temperature(0.0)로 결정적 출력
- **Compose LLM**: Low temperature(0.3)으로 창의적이지 않은 자연어 생성
- **모델**: 주로 `gpt-4o-mini` 사용 (경량, 빠른 응답)
- **비용**: 질문당 ~500-1000 토큰 처리 예상

### 개선 방향

1. **Plan 캐싱**: 유사 질문에 대해 Plan 재사용
2. **Summary 캐싱**: 동일 실행 결과에 대해 요약 재사용
3. **Parallel LLM**: 필요 시 다중 LLM 병렬 호출로 대기 시간 단축
4. **Streaming 응답**: 긴 요약의 경우 스트리밍으로 빠른 피드백

---

## 관련 파일

### 핵심 파일

1. **Router Layer**
   - `apps/api/app/modules/ops/router.py`
   - `/ops/ci/ask` 엔드포인트 정의

2. **Planner Layer**
   - `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`
   - 질문 분석 및 Plan 생성

3. **Runner Layer**
   - `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
   - 오케스트레이션 실행 및 도구 조정

4. **Stage Executor Layer**
   - `apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py`
   - 스테이지별 실행 및 LLM 요약

5. **Tool Executor**
   - `apps/api/app/modules/ops/services/ci/tools/executor.py`
   - Tool Registry 기반 도구 실행

6. **Tool Registry**
   - `apps/api/app/modules/ops/services/ci/tools/base.py`
   - 도구 등록 및 실행 인터페이스

### 관련 스키마

1. `app/modules/ops/services/ci/planner/plan_schema.py` - Plan 데이터 모델
2. `app/modules/ops/schemas.py` - StageInput/StageOutput 모델
3. `schemas/tool_contracts.py` - ToolCall 표준 모델

---

## 변경 로그

- 2026-01-29: 초기 버전 작성
- 범용 오케스트레이션 구현 분석 완료
- LLM 호출 지점 2개 식별
- 전체 프로세스 문서화 완료