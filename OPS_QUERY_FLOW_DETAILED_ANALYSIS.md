# 🔄 OPS 질의 처리 전체 흐름 상세 분석

**작성일**: 2026-02-16
**범위**: 질의 입수부터 응답까지 전체 처리 과정

---

## 📍 시작: HTTP 요청 진입점

### 1️⃣ **HTTP 엔드포인트**

```
POST /ops/ask
```

**파일**: `apps/api/app/modules/ops/routes/ci_ask.py:72-78`

```python
@router.post("/ops/ask")
def ask_ops(
    payload: CiAskRequest,          # 사용자의 질의 입력
    request: Request,                # HTTP 요청 객체
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

---

## 🔄 전체 처리 흐름 (6단계)

### **Phase 1️⃣: 질의 정규화 (Question Normalization)**

```
HTTP Request /ops/ask
    ↓
[진입점] ask_ops() 함수 시작
    ↓
RESOLVER Assets 로드
```

**처리 내용**:
- 사용자 입력 정규화 (공백 제거, 대소문자 통일 등)
- RESOLVER Asset 활용: 환경 변수 호환성 확인

**사용되는 Assets**:
- **Prompt**: (이 단계에서는 아직 프롬프트 미사용)
- **Resolver**: `default_resolver` (ID: 92406ef9...)
  - 환경 변수 폴백 규칙 적용

**결과**:
```json
{
  "normalized_question": "CI MES-06의 최근 30일 이력 조회",
  "question_metadata": {
    "length": 20,
    "entity": "MES-06",
    "time_range": "30 days"
  }
}
```

---

### **Phase 2️⃣: 계획 생성 (Plan Generation with LLM)**

```
정규화된 질의
    ↓
[PROMPT 호출 #1] ops_all_router 또는 특정 모드 라우터
    ↓
Claude LLM이 실행할 도구 선택
    ↓
Plan 생성 (어떤 도구를 어떤 순서로 실행할 것인가?)
```

**단계별 상세 분석**:

#### **2-1. 라우터 선택**

**현재 상황**: 사용자가 어떤 모드인지 결정
- `mode = "all"` (기본값)

**사용되는 Prompts** (22개 중 선택):

| 모드 | Prompt Asset | 역할 |
|------|-------------|------|
| all | ops_all_router | 전체 모드 라우팅 (모든 도구 병렬 실행) |
| config | ops_planner | 설정 분석 (구성 정보 조회) |
| metric | ops_metric_router | 메트릭 조회 (성능 지표 분석) |
| history | ops_history_router | 이력 조회 (변경 로그 검색) |
| graph | ops_graph_router | 그래프 관계 (CI 관계도 표시) |
| document | ops_normalizer / DocumentSearchService | 문서 검색 (하이브리드 검색: BM25 + pgvector) |

---

### 📄 Document 모드 상세 설명

**Document 모드**는 질의와 관련된 문서를 검색하고 정보를 제공하는 모드입니다.

#### 처리 흐름:

```
사용자 질의
    ↓
ops_normalizer (Prompt Asset)
    ↓
DocumentSearchService.search()
    ├─ _text_search()     → PostgreSQL tsvector (BM25 전문검색)
    ├─ _vector_search()   → pgvector (semantic search, 1536-dim)
    └─ 결과 병합: RRF (Reciprocal Rank Fusion)
    ↓
문서 목록 + 요약 반환
```

#### 구현 위치:

- **Backend**: `apps/api/app/modules/document_processor/services/search_service.py`
- **API Router**: `apps/api/app/modules/document_processor/router.py`
  - Endpoint: `POST /api/documents/search`
- **OPS Integration**: `apps/api/app/modules/ops/services/__init__.py:run_document()`

#### 검색 전략:

1. **Text Search (BM25)**
   - 문서 제목, 내용에서 키워드 매칭
   - PostgreSQL tsvector 사용
   - 정확도: 높음, 속도: 빠름 (<50ms)

2. **Vector Search (Semantic)**
   - 문서의 의미론적 유사성 검색
   - pgvector (1536차원 embedding)
   - 정확도: 높음, 속도: 중간 (~100ms)

3. **Hybrid Fusion (RRF)**
   - 두 검색 결과의 순위 통합
   - Reciprocal Rank Fusion 알고리즘
   - 최적의 결과 도출 (<150ms)

#### 예시:

```json
{
  "question": "ECS 배포 가이드에서 권장 사항은?",
  "mode": "document",
  "tools": ["DocumentSearchService"],
  "result": {
    "documents": [
      {
        "id": "doc-001",
        "title": "AWS ECS 배포 가이드",
        "excerpt": "ECS 클러스터 배포 시 다음을 권장합니다...",
        "relevance_score": 0.92
      },
      {
        "id": "doc-002",
        "title": "ECS 보안 best practices",
        "excerpt": "보안 관점에서 다음을 권장합니다...",
        "relevance_score": 0.85
      }
    ],
    "summary": "ECS 배포에 관련된 2개의 문서를 찾았습니다."
  }
}
```

---

**예시: 이력 조회 모드 선택 시**

```python
# ci_ask.py:200-250 (가상 코드)

# Step 1: 질의 분석
question = "CI 'MES-06'의 최근 30일 이력"

# Step 2: Prompt Asset 로드
prompt_asset = load_catalog_asset("ops_history_router")
# ID: 47991817... (Published) ✅

# Step 3: LLM에 프롬프트 전달
llm_response = planner_llm.analyze(
    prompt_template=prompt_asset.template,
    question=question,
    mode="history"
)

# Step 4: 계획 생성
plan = Plan(
    intent=Intent(
        mode="history",
        action="retrieve",
        target_entity="MES-06"
    ),
    tools=[
        {
            "name": "work_history_query",
            "params": {
                "ci_code": "MES-06",
                "start_time": "2026-01-17",
                "end_time": "2026-02-16"
            }
        }
    ],
    views=["table", "timeline"]
)
```

#### **2-2. LLM 프롬프트 상세**

**Prompt Asset: ops_history_router**
- **ID**: 47991817...
- **Status**: Published ✅
- **역할**: 이력 모드 분석

```
[System Prompt Content - 가상]
당신은 IT 운영 전문가입니다.
사용자 질의를 분석하여 다음을 결정하세요:
1. 쿼리 유형: work_history? event_log? maintenance_history?
2. 필터링 조건: CI, 시간 범위
3. 출력 형식: table? timeline?

사용자 질의: "{question}"
답변: JSON 형식의 plan
```

---

### **Phase 3️⃣: 계획 검증 및 라우팅 (Validation & Routing)**

```
생성된 Plan
    ↓
[검증자 호출] validator
    ↓
3가지 경로 중 선택:
  - direct: 직접 실행
  - reject: 거부
  - orchestration: 오케스트레이션 실행
```

**처리 코드** (`ci_ask.py:300-400` 가상):

```python
# Step 1: 계획 검증
is_valid = validator.validate(plan)

if not is_valid:
    return CiAskResponse(
        answer="질의를 처리할 수 없습니다.",
        status="rejected",
        reason="Invalid plan"
    )

# Step 2: 경로 결정
route = determine_route(plan)
# → "orchestration" (도구 실행 필요)

# Step 3: 정책 로드
policies = load_policy_asset("tool_limits")
# ID: 70e97812... (Published) ✅
# max_rows: 1000, max_retries: 3
```

---

### **Phase 4️⃣: 단계별 실행 (Stage Execution)**

```
Orchestration 경로 선택됨
    ↓
4개 Stage 순차 실행:
  1. Validate Stage
  2. Execute Stage  ← [TOOL & QUERY 호출]
  3. Compose Stage  ← [MAPPING & PROMPT 호출]
  4. Present Stage  ← [PROMPT 호출]
```

#### **4-1. Validate Stage**

```python
# 계획이 실행 가능한지 최종 검증

# Assets 사용:
# - Policy: ci_column_allowlist (ID: 34bee1cf...)
# - Policy: time_ranges (ID: df4778a9...)

def validate_execution_plan(plan: Plan, policies: List[Policy]):
    # 요청된 CI가 allowlist에 있나?
    if plan.params['ci_code'] not in policies['ci_column_allowlist']:
        raise ValidationError("CI not allowed")

    # 시간 범위가 policy를 초과하나?
    lookback_days = 30
    max_lookback = policies['time_ranges']['max_lookback']  # 90 days

    if lookback_days > max_lookback:
        raise ValidationError("Time range exceeds limit")

    return True
```

**Result**: ✅ Plan validated

---

#### **4-2. Execute Stage** ⭐ **핵심 단계**

```python
# TOOL과 QUERY Assets가 실제로 실행되는 지점
```

**2-1단계에서 생성된 Plan**:
```json
{
  "tools": [
    {
      "name": "work_history_query",
      "params": {
        "ci_code": "MES-06",
        "start_time": "2026-01-17",
        "end_time": "2026-02-16"
      }
    }
  ]
}
```

**실행 흐름**:

```
┌─ TOOL Asset 선택 ────────────────────────┐
│ work_history_query (ID: ad89c4ec...)     │
│ Type: database_query                     │
│ Status: Published ✅                      │
│ Data Source: default_postgres            │
└──────────────────────────────────────────┘
    ↓
┌─ QUERY Asset 로드 ────────────────────────┐
│ work_history_recent (ID: 6534d352...)    │
│ SELECT wh.* FROM work_history            │
│ WHERE ci_code = {ci_code}                │
│ AND start_time >= {start_time}           │
└──────────────────────────────────────────┘
    ↓
┌─ SOURCE Asset 확인 ────────────────────────┐
│ default_postgres (ID: a8d63836...)        │
│ Host: localhost:5432                      │
│ Database: spa                             │
│ Status: Connected ✅                       │
└──────────────────────────────────────────┘
    ↓
┌─ POLICY 적용 ─────────────────────────────┐
│ tool_limits:                              │
│   max_rows: 1000                          │
│   max_retries: 3                          │
│ time_ranges:                              │
│   max_lookback: 90 days                   │
└──────────────────────────────────────────┘
    ↓
[SQL 실행]

SELECT
    wh.id,
    wh.work_type,
    wh.summary,
    wh.detail,
    wh.start_time,
    wh.end_time,
    c.ci_code,
    c.ci_name
FROM work_history AS wh
LEFT JOIN ci AS c ON c.ci_id = wh.ci_id
WHERE c.ci_code = 'MES-06'
  AND wh.start_time >= '2026-01-17'
  AND wh.start_time < '2026-02-16'
ORDER BY wh.start_time DESC
LIMIT 1000

    ↓
[결과 반환]
{
  "rows": [
    {
      "id": "work_12345",
      "work_type": "maintenance",
      "summary": "정기 점검",
      "detail": "...",
      "start_time": "2026-02-15",
      "ci_code": "MES-06",
      "ci_name": "MES Server 06"
    },
    ...
  ],
  "row_count": 47
}
```

**Output from Execute Stage**:
```python
execution_result = {
    "tool_name": "work_history_query",
    "status": "success",
    "data": [...47개 행],
    "metadata": {
        "query_time_ms": 125,
        "row_count": 47
    }
}
```

---

#### **4-3. Compose Stage** ⭐ **데이터 변환**

```
실행 결과 (47개 행)
    ↓
[MAPPING Assets 적용]
    ↓
[PROMPT로 결과 합성]
    ↓
구조화된 응답 블록 생성
```

**처리 단계**:

```python
# Step 1: MAPPING Assets 로드
mapping_assets = {
    "history_keywords": load_mapping_asset("history_keywords"),
    # ID: 25047100... (Published) ✅

    "table_hints": load_mapping_asset("table_hints"),
    # ID: d367ff32... (Published) ✅
}

# history_keywords 매핑 예시:
# "change" → event_type = "change"
# "maintenance" → event_type = "maintenance"
# "recent" → ORDER BY created_at DESC

# table_hints 매핑 예시:
# "summary" → show_summary_column
# "timeline" → render_as_timeline_chart

# Step 2: 데이터 변환
transformed_data = []
for row in execution_result['data']:
    transformed_row = {
        "date": row['start_time'],
        "type": mapping['history_keywords'].get(row['work_type']),
        "description": row['summary'],
        "duration": calculate_duration(row),
        "source": "work_history"
    }
    transformed_data.append(transformed_row)

# Step 3: PROMPT로 합성
prompt_asset = load_catalog_asset("ci_compose_summary")
# ID: 347ce84d... (Published) ✅

llm_response = planner_llm.compose(
    prompt_template=prompt_asset.template,
    data=transformed_data,
    format="summary"
)

# Step 4: 블록 생성
compose_result = {
    "blocks": [
        {
            "type": "table",
            "title": "MES-06 작업 이력",
            "data": transformed_data[:20],  # 상위 20개
            "columns": ["date", "type", "description", "duration"]
        },
        {
            "type": "timeline",
            "title": "작업 타임라인",
            "data": transformed_data,
            "events": [
                {"date": "2026-02-15", "label": "정기 점검"},
                {"date": "2026-02-10", "label": "유지보수"},
                ...
            ]
        }
    ],
    "summary": "MES-06은 최근 30일간 총 47개의 작업 기록이 있습니다..."
}
```

**Output from Compose Stage**:
```json
{
  "blocks": [
    {
      "type": "table",
      "title": "MES-06 작업 이력",
      "data": [...],
      "rowCount": 20
    },
    {
      "type": "timeline",
      "title": "작업 타임라인",
      "data": [...]
    },
    {
      "type": "summary",
      "content": "MES-06은 최근 30일간..."
    }
  ]
}
```

---

#### **4-4. Present Stage** ⭐ **최종 응답 포맷팅**

```
구조화된 블록
    ↓
[PROMPT로 최종 포맷팅]
    ↓
사용자 친화적 응답 생성
```

**처리**:

```python
# Step 1: PROMPT 로드
prompt_asset = load_catalog_asset("ci_universal_present")
# ID: d5478b27... (Published) ✅

# Step 2: 최종 포맷팅
final_response = planner_llm.present(
    prompt_template=prompt_asset.template,
    blocks=compose_result['blocks'],
    question=original_question,
    format="markdown_with_json"
)

# Step 3: 응답 생성
present_result = {
    "answer": """
    # MES-06의 최근 30일 이력

    **요약**: MES-06은 지난 30일간 총 47개의 작업 기록이 있습니다.

    ## 주요 활동
    - 정기 점검 (2026-02-15): 시스템 정상
    - 유지보수 (2026-02-10): 패치 적용
    - ...

    자세한 내용은 아래 표를 참고하세요.
    """,
    "blocks": compose_result['blocks'],
    "metadata": {
        "response_time_ms": 456,
        "blocks_count": 3
    }
}
```

**Output from Present Stage**:
```json
{
  "answer": "최종 마크다운 형식 답변",
  "blocks": [
    { "type": "table", ... },
    { "type": "timeline", ... },
    { "type": "summary", ... }
  ],
  "status": "success",
  "metadata": { ... }
}
```

---

### **Phase 5️⃣: 오류 처리 및 재계획 (Error Handling & Fallback)**

```
Execute/Compose/Present 중 오류 발생
    ↓
[오류 감지]
    ↓
evaluate_replan() 호출
    ↓
오류 유형별 처리
```

**오류 시나리오**:

```python
try:
    execution_result = execute_tools(plan)
except ToolExecutionError as e:
    logger.error(f"Tool execution failed: {e}")

    # Fallback 1: 계획 수정 및 재시도
    modified_plan = evaluate_replan(
        original_plan=plan,
        error=e,
        retry_count=1
    )

    if modified_plan:
        # 다른 도구로 재시도
        execution_result = execute_tools(modified_plan)
    else:
        # Fallback 2: Mock 데이터 제공
        execution_result = get_mock_data(plan)

except PlanningError as e:
    logger.error(f"Planning failed: {e}")
    # Fallback 3: 간단한 응답 제공
    return CiAskResponse(
        answer="상세 분석을 수행할 수 없습니다. 다시 시도해주세요.",
        status="degraded",
        blocks=[text_block("오류가 발생했습니다.")]
    )
```

---

### **Phase 6️⃣: 응답 및 이력 저장 (Response & Persistence)**

```
최종 응답 생성
    ↓
[응답 직렬화]
    ↓
[실행 흔적 저장]
    ↓
[쿼리 이력 업데이트]
    ↓
HTTP 응답 반환
```

**처리**:

```python
# Step 1: 응답 직렬화
response_envelope = ResponseEnvelope(
    time=datetime.now().isoformat(),
    code=0,
    message="OK",
    data=present_result
)

# Step 2: 실행 흔적 저장 (Inspector)
all_spans = get_all_spans()
persist_execution_trace(
    trace={
        "spans": all_spans,
        "plan": plan,
        "execution_result": execution_result,
        "response": present_result
    },
    history_id=history_id
)

# Step 3: 쿼리 이력 업데이트
update_query_history(
    history_id=history_id,
    status="completed",
    response=present_result,
    summary="MES-06 최근 30일 이력: 47개 기록",
    execution_time_ms=time.perf_counter() - start
)

# Step 4: HTTP 응답 반환
return JSONResponse(
    status_code=200,
    content=jsonable_encoder(response_envelope.dict())
)
```

**최종 HTTP 응답**:
```json
{
  "time": "2026-02-16T12:45:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "answer": "MES-06의 최근 30일...",
    "blocks": [...],
    "metadata": {
      "execution_time_ms": 456,
      "tools_called": 1,
      "rows_returned": 47,
      "status": "completed"
    }
  }
}
```

---

## 📊 22개 Prompt Assets의 역할 분류

### **1. 라우팅 Prompts (4개)**

```
이 프롬프트들은 질의가 들어오면 가장 먼저 호출됨
```

| Prompt | ID | 역할 |
|--------|-----|------|
| **ops_all_router** | 8af5fa0d... | 전체 모드 (모든 도구 동원) |
| **ops_metric_router** | 7be0f699... | 메트릭 모드 (메트릭만 조회) |
| **ops_graph_router** | 96338acf... | 그래프 모드 (관계도만 조회) |
| **ops_history_router** | 47991817... | 이력 모드 (이력만 조회) |

**호출 시점**: Phase 2-1 (계획 생성)

**역할**:
```
질의 분석 → 어떤 도구를 사용할 것인가? → 도구 선택
```

---

### **2. 계획/검증 Prompts (2개)**

| Prompt | ID | 역할 |
|--------|-----|------|
| **ci_planner_output_parser** | 6b3e95c3... | 계획 출력 파싱 |
| **ci_universal_planner** | ed13a98e... | 범용 계획 수립 |

**호출 시점**: Phase 2 (계획 생성)

---

### **3. 합성 Prompts (4개)**

| Prompt | ID | 역할 |
|--------|-----|------|
| **ci_compose_summary** | 347ce84d... | 결과 요약 합성 |
| **ci_universal_compose** | 670ef710... | 범용 결과 합성 |
| **ops_composer** | e6f15250... | OPS 결과 합성 |
| **ops_langgraph** | ff9836dc... | LangGraph 기반 합성 |

**호출 시점**: Phase 4-3 (합성)

**역할**:
```
실행 결과 → 변환 및 정렬 → 구조화된 블록
```

---

### **4. 제시 Prompts (2개)**

| Prompt | ID | 역할 |
|--------|-----|------|
| **ci_universal_present** | d5478b27... | 범용 최종 제시 |
| **ci_response_builder** | c3379121... | 응답 구축 |

**호출 시점**: Phase 4-4 (제시)

**역할**:
```
구조화된 블록 → 사용자 친화적 최종 응답 포맷팅
```

---

### **5. 유틸리티 Prompts (10개)**

| Prompt | 역할 |
|--------|------|
| **ci_validator** | 응답 검증 |
| **ops_metric_router** | 메트릭 라우팅 |
| **ops_graph_router** | 그래프 라우팅 |
| 기타 | 특화된 분석/합성 |

---

## 🎯 전체 흐름 시각화

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 사용자 질의: "CI 'MES-06' 최근 30일 이력"                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: 정규화 (Normalization)                                                │
│ - Resolver Assets 로드                                                          │
│ - 환경 변수 호환성 확인                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: 계획 생성 (Planning) ← [PROMPT 호출 #1]                                │
│                                                                                 │
│ Step 1: 라우터 선택                                                             │
│   → ops_history_router (PROMPT #1)                                            │
│      Decide: "이력 모드 사용"                                                  │
│                                                                                 │
│ Step 2: 도구 선택                                                              │
│   → ci_universal_planner (PROMPT #2)                                          │
│      Select: "work_history_query 도구 사용"                                    │
│                                                                                 │
│ Step 3: 계획 파싱                                                              │
│   → ci_planner_output_parser (PROMPT #3)                                      │
│      Parse: {tools: [work_history_query], params: {...}}                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: 검증 & 라우팅 (Validation & Routing)                                  │
│ - Plan 유효성 검증                                                              │
│ - Route 결정: "orchestration" (도구 실행 경로)                                  │
│ - Policy 로드                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 4: 단계별 실행 (Stage Execution)                                         │
│                                                                                 │
│ [Stage 1] Validate: ci_column_allowlist, time_ranges Policy 확인              │
│                                                                                 │
│ [Stage 2] Execute ← [TOOL & QUERY 호출]  ★ 핵심 단계                          │
│   - TOOL: work_history_query (database_query)                                │
│   - QUERY: work_history_recent (SELECT ... FROM work_history ...)            │
│   - SOURCE: default_postgres (연결 확인)                                      │
│   - POLICY 적용: max_rows=1000, max_retries=3                                │
│   → Result: 47개 행 반환                                                      │
│                                                                                 │
│ [Stage 3] Compose ← [MAPPING & PROMPT #4 호출]                               │
│   - MAPPING: history_keywords, table_hints 로드                              │
│   - PROMPT: ci_compose_summary (#4) → 데이터 변환                            │
│   - PROMPT: ci_universal_compose (#5) → 블록 생성                            │
│   → Result: 테이블, 타임라인, 요약 블록 생성                                   │
│                                                                                 │
│ [Stage 4] Present ← [PROMPT #6 호출]                                         │
│   - PROMPT: ci_universal_present (#6) → 최종 포맷팅                          │
│   → Result: 마크다운 형식의 최종 응답                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 5: 오류 처리 (Error Handling)                                            │
│ - 오류 감지 시 재계획 (Fallback)                                               │
│ - Mock 데이터 제공                                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Phase 6: 응답 및 저장 (Response & Persistence)                                │
│ - ResponseEnvelope 직렬화                                                       │
│ - 실행 흔적 저장 (Inspector)                                                   │
│ - 쿼리 이력 업데이트                                                            │
│ - HTTP 응답 반환 (200 OK)                                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                        ┌──────────────────────┐
                        │  최종 응답 (JSON)     │
                        │ {                     │
                        │   answer: "...",      │
                        │   blocks: [...],      │
                        │   metadata: {...}     │
                        │ }                     │
                        └──────────────────────┘
```

---

## 📊 Assets 호출 순서 및 빈도

### **반드시 호출되는 Assets** (모든 질의에서)

```
1. Prompt #1: 라우터 (ops_*_router)
   ├─ Resolver: default_resolver

2. Prompt #2: 계획자 (ci_universal_planner)
   ├─ Tool: 선택된 도구
   │  ├─ Query: 해당 쿼리
   │  └─ Source: 데이터베이스 연결
   ├─ Policy: tool_limits, time_ranges
   └─ Mapping: 자연어 처리

3. Prompt #3: 파서 (ci_planner_output_parser)

4. Prompt #4-5: 합성 (ci_compose_summary, ci_universal_compose)
   └─ Mapping: history_keywords, table_hints 등

5. Prompt #6: 제시 (ci_universal_present)

6. Inspector: 실행 흔적 저장
```

### **조건부 호출되는 Assets**

```
- 오류 발생: evaluate_replan() → 계획 재구성
- 메타데이터: ci_aggregate, metric_aggregate
- 보안: ci_column_allowlist, view_depth_policies
```

---

## 🔍 핵심 통찰

### ✅ **왜 22개의 Prompt Assets이 필요한가?**

1. **모드별 라우팅** (4개)
   - 각 모드(all, metric, history, graph)마다 고유한 라우팅 로직

2. **다양한 도메인** (6개)
   - CI 분석, 메트릭, 그래프, 이력 등 각각 특화된 프롬프트

3. **파이프라인 단계** (6개)
   - 계획 → 검증 → 합성 → 제시 각 단계의 고유 프롬프트

4. **재사용 및 특화** (6개)
   - 범용(universal) 프롬프트 + 특화된 프롬프트

### ✅ **Prompts가 언제 호출되는가?**

```
Phase 2 (계획):    Prompts #1-3 호출 (라우팅, 계획, 파싱)
Phase 4-3 (합성):  Prompts #4-5 호출 (데이터 변환)
Phase 4-4 (제시):  Prompts #6+ 호출 (최종 포맷팅)
```

### ✅ **Assets 간 의존성**

```
Prompt (의사결정)
  ↓
Tool (실행 지점)
  ↓
Query (데이터 접근)
  ↓
Source (DB 연결)
  ↓
← Policy (제약 조건)
← Mapping (자연어)
← Resolver (규칙)
```

---

## 🎯 다음 단계

1. **Prompt 최적화**
   - 22개 Prompts 중 실제 사용되는 것 측정
   - 불필요한 Prompts 통합

2. **Query Draft 정리**
   - 140개 Query 중 72% Draft 상태
   - PostgreSQL Catalog 쿼리 활성화

3. **성능 개선**
   - Prompts 캐싱
   - 병렬 실행 가능 부분 식별

---

**이 문서는 OPS 질의 처리의 모든 단계를 상세히 설명합니다.**

*생성일: 2026-02-16*
