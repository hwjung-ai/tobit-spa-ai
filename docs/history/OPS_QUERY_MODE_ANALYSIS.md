# OPS Query Mode 분석 보고서

## 개요

본 문서는 OPS 메뉴에서 사용자가 질의할 때 각 모드(구성, 이력, 수치, 문서, 연결, 전체)가 내부적으로 어떻게 처리되어 답을 생성하는지 분석한 결과입니다.

---

## 1. 아키텍처 개요

### 1.1 처리 흐름

```
User Question
    ↓
POST /ops/query (routes/query.py)
    ↓
handle_ops_query(mode, question) (services/__init__.py)
    ↓
Mode-specific Executor
    ↓
CI Orchestrator Runner (services/ci/orchestrator/runner.py)
    ↓
Tool Registry Execution
    ↓
Answer Blocks Generation
```

### 1.2 핵심 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|----------|------|------|
| **Query Route** | `routes/query.py` | HTTP 요청 처리, History 저장 |
| **handle_ops_query** | `services/__init__.py` | 모드별 Executor 라우팅 |
| **CI Orchestrator Runner** | `services/ci/orchestrator/runner.py` | Plan 기반 오케스트레이션 |
| **Tool Registry** | `services/ci/tools/` | 도구 실행 및 결과 표준화 |
| **Plan Schema** | `services/ci/planner/plan_schema.py` | 실행 계획 데이터 모델 |

---

## 2. 각 모드별 처리 방식

### 2.1 구성 (Config)

**라우팅**: `handle_ops_query()` → `run_config_executor()` → `execute_universal(question, "config", tenant_id)`

**Plan 설정**:
```python
Plan(
    intent=Intent.LOOKUP,
    view=View.SUMMARY,
    mode=PlanMode.CI,
    primary=PrimarySpec(limit=10, tool_type="ci_lookup"),
    aggregate=AggregateSpec(
        group_by=["ci_type"],
        metrics=["ci_name", "ci_code"],
        filters=[],
        top_n=20,
    ),
)
```

**실행 흐름**:
1. `CIOrchestratorRunner` 생성
2. `tool_type="ci_lookup"`으로 CI 검색
3. `ci_type`으로 그룹화하여 집계
4. 결과를 `TableBlock`으로 변환
5. References 생성 (SQL, Cypher 쿼리)

**출력 예시**:
- MarkdownBlock: 요약 설명
- TableBlock: CI 구성 정보 (ci_type, ci_name, ci_code)
- ReferencesBlock: CI 조회 관련 쿼리

---

### 2.2 이력 (History)

**라우팅**: `handle_ops_query()` → `run_hist()` → `execute_universal(question, "hist", tenant_id)`

**Plan 설정**:
```python
Plan(
    intent=Intent.LIST,
    view=View.SUMMARY,
    mode=PlanMode.CI,
    aggregate=AggregateSpec(
        group_by=["ci_type"],
        metrics=["ci_name"],
        filters=[],
        top_n=10,
    ),
    history=HistorySpec(
        enabled=True,
        source="event_log",
        time_range="last_7d",
        limit=20,
    ),
)
```

**실행 흐름**:
1. `CIOrchestratorRunner` 생성
2. `tool_type="event_log"`으로 이력 검색
3. 시간 범위 (default: last_7d)로 필터링
4. 최근 N개 이벤트 반환 (default: 20개)
5. 결과를 `TableBlock`으로 변환

**출력 예시**:
- MarkdownBlock: "Event History"
- TableBlock: 이벤트 목록 (timestamp, ci_code, event_type, description)
- ReferencesBlock: 이력 조회 관련 쿼리

---

### 2.3 수치 (Metric)

**라우팅**: `handle_ops_query()` → `run_metric()` → `execute_universal(question, "metric", tenant_id)`

**Plan 설정**:
```python
Plan(
    intent=Intent.AGGREGATE,
    view=View.SUMMARY,
    mode=PlanMode.CI,
    aggregate=AggregateSpec(
        group_by=["ci_type"],
        metrics=["ci_name"],
        filters=[],
        top_n=10,
    ),
    metric=MetricSpec(
        metric_name="cpu_usage",
        agg="max",
        time_range="last_24h",
        mode="aggregate",
    ),
)
```

**실행 흐름**:
1. `CIOrchestratorRunner` 생성
2. `tool_type="metric"`으로 메트릭 조회
3. 시간 범위 (default: last_24h)로 필터링
4. 집계 함수 (count/max/min/avg) 적용
5. 결과를 `TimeSeriesBlock` 또는 `TableBlock`으로 변환

**출력 예시**:
- MarkdownBlock: Metric 요약
- TimeSeriesBlock: 시계열 데이터 (timestamp, value)
- TableBlock: 집계 결과 (metric_name, agg, value)
- ReferencesBlock: 메트릭 조회 관련 쿼리

---

### 2.4 문서 (Document)

**라우팅**: `handle_ops_query()` → `run_document(question, tenant_id, settings)`

**특이점**: 다른 모드와 달리 **CI Orchestrator를 사용하지 않고 별도로 처리**

**실행 흐름**:
```python
# Step 1: 문서 검색 (BM25 + ILIKE)
DocumentSearchService.search(
    query=question,
    filters=SearchFilters(tenant_id, ...),
    top_k=5,
    search_type="text"
)

# Step 2: RAG 컨텍스트 구성
context = "\n\n".join([chunk for chunk in search_results])

# Step 3: LLM 기반 답변 생성
llm.create_response(
    input=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ],
    model=settings.chat_model
)

# Step 4: 응답 구성
blocks = [
    MarkdownBlock(title="Answer", content=answer_text),
    ReferencesBlock(title="Source Documents", items=[...])
]
```

**출력 예시**:
- MarkdownBlock: LLM이 생성한 답변
- ReferencesBlock: 소스 문서 목록 (document_name, page, relevance, viewer_url)

---

### 2.5 연결 (Relation/Graph)

**라우팅**: `handle_ops_query()` → `run_graph()` → `execute_universal(question, "graph", tenant_id)`

**Plan 설정**:
```python
Plan(
    intent=Intent.EXPAND,
    view=View.NEIGHBORS,
    mode=PlanMode.CI,
    primary=PrimarySpec(limit=5, tool_type="ci_lookup"),
    graph=GraphSpec(
        depth=2,
        view=View.NEIGHBORS,
        tool_type="ci_graph"
    ),
)
```

**실행 흐름**:
1. `CIOrchestratorRunner` 생성
2. `tool_type="ci_graph"`으로 그래프 확장
3. CI 조회 후 연관된 노드/엣지 탐색
4. Depth로 확장 범위 제어 (default: 2)
5. 결과를 `GraphBlock`으로 변환

**출력 예시**:
- MarkdownBlock: "Dependency Analysis"
- GraphBlock: 노드/엣지 데이터 (nodes, edges)
- ReferencesBlock: 그래프 조회 관련 쿼리

---

### 2.6 전체 (All)

**라우팅**: `handle_ops_query()` → `_run_all()`

**두 가지 실행 모드**:

#### Mode 1: LangGraph (LLM 기반)
```python
if settings.ops_enable_langgraph and settings.openai_api_key:
    LangGraphAllRunner.run(question)
```

**실행 흐름**:
1. LLM으로 실행 계획 수립 (`_plan()`)
   - 어떤 서브툴 실행할지 결정 (run_metric, run_hist, run_graph)
   - CI/Metric/Time 힌트 추출
2. 계획된 서브툴 순차 실행
3. LLM으로 최종 요약 생성 (`_build_final_summary()`)

**Plan 예시**:
```json
{
  "run_metric": true,
  "run_hist": true,
  "run_graph": false,
  "metric_hint": "cpu",
  "time_hint": "last_24h"
}
```

#### Mode 2: Rule-based (키워드 기반)
```python
_determine_all_executors(question) → ["metric", "hist", "graph", "config"]
```

**키워드 매칭**:
```python
METRIC_KEYWORDS = {"온도", "temp", "temperature", "cpu", "사용률", "추이", ...}
HIST_KEYWORDS = {"정비", "유지보수", "작업", "변경", "이력", ...}
GRAPH_KEYWORDS = {"영향", "의존", "경로", "연결", "토폴로지", ...}
```

**실행 순서**: `ALL_EXECUTOR_ORDER = ("metric", "hist", "graph", "config")`

**출력 예시**:
- MarkdownBlock: 실행한 서브툴 요약
- Metric 블록들
- History 블록들
- Graph 블록들
- Config 블록들
- ReferencesBlock

---

## 3. CI Orchestrator Runner 상세

### 3.1 실행 단계 (Stage-based)

```python
route_plan → validate → execute → compose → present
```

| 단계 | 역할 | 설명 |
|------|------|------|
| **route_plan** | 경로 결정 | Plan Output Kind 결정 (DIRECT/PLAN/REJECT) |
| **validate** | 검증 | Plan 유효성 검사, 정책 적용 |
| **execute** | 실행 | Tool Registry를 통한 도구 실행 |
| **compose** | 구성 | 결과를 합성하여 형식화 |
| **present** | 표현 | 최종 Answer Blocks 생성 |

### 3.2 Tool Registry 기반 실행

**도구 타입**:
```python
ToolType = "ci" | "metric" | "history" | "graph" | "event" | "cep"
```

**실행 메서드**:
```python
CIOrchestratorRunner._execute_tool_with_tracing(
    tool_type="ci",
    operation="search",  # 또는 "aggregate", "get", "list_preview"
    keywords=[...],
    filters=[...],
    limit=10,
)
```

**Tool Call 표준화**:
```python
ToolCall(
    tool="ci.search",
    elapsed_ms=150,
    input_params={"keywords": [...], "limit": 10},
    output_summary={"row_count": 5},
    error=None,
)
```

### 3.3 Plan to Blocks 변환

```python
result = runner.run(plan_output)
blocks = _convert_result_to_blocks(result, mode)
```

**변환 로직**:
1. `execution_results`에서 각 툴 결과 추출
2. 데이터 타입별 블록 생성:
   - Graph → `GraphBlock`
   - Table → `TableBlock`
   - TimeSeries → `TimeSeriesBlock`
   - Text → `MarkdownBlock`
3. References 누적
4. Final Blocks 반환

---

## 4. 답변 구조 (Answer Blocks)

### 4.1 Block 타입

| Block 타입 | 용도 | 필드 |
|-------------|------|------|
| **MarkdownBlock** | 텍스트 설명 | type, title, content |
| **TableBlock** | 테이블 데이터 | type, title, columns, rows |
| **GraphBlock** | 그래프 시각화 | type, title, nodes, edges |
| **TimeSeriesBlock** | 시계열 데이터 | type, title, series (name, data) |
| **ReferencesBlock** | 참조 문서/쿼리 | type, title, items (kind, url, payload) |

### 4.2 응답 포맷

```json
{
  "answer": {
    "meta": {
      "route": "config",
      "route_reason": "OPS config real mode",
      "timing_ms": 1500,
      "summary": "Configuration items for...",
      "used_tools": ["ci.search", "ci.aggregate"],
      "fallback": false,
      "trace_id": "uuid",
      "parent_trace_id": null
    },
    "blocks": [
      {"type": "markdown", ...},
      {"type": "table", ...},
      {"type": "references", ...}
    ]
  },
  "trace": {
    "plan_validated": {...},
    "tool_calls": [...],
    "references": [...],
    "stage_inputs": [...],
    "stage_outputs": [...]
  }
}
```

---

## 5. 환경 변수 설정

### 5.1 OPS Mode

```bash
# .env
OPS_MODE=real  # 실제 데이터 조회 (default)
OPS_MODE=mock  # Mock 데이터 사용 (개발용)
```

### 5.2 LangGraph All Mode

```bash
OPS_ENABLE_LANGGRAPH=true  # LangGraph 기반 ALL 모드 활성화
OPENAI_API_KEY=sk-...     # OpenAI API 키 필요
```

---

## 6. 요약 비교표

| 모드 | Intent | View | Tool | 주요 작업 | Block 타입 |
|------|--------|------|------|----------|------------|
| **구성** | LOOKUP | SUMMARY | ci_lookup, ci_aggregate | CI 검색 + 그룹화 | Table, Markdown, References |
| **이력** | LIST | SUMMARY | event_log | 이벤트 검색 | Table, Markdown, References |
| **수치** | AGGREGATE | SUMMARY | metric | 메트릭 집계/시계열 | TimeSeries, Table, References |
| **문서** | - | - | document_search | RAG (검색 + LLM) | Markdown, References |
| **연결** | EXPAND | NEIGHBORS | ci_graph | 그래프 확장 | Graph, Markdown, References |
| **전체** | - | - | metric/hist/graph/config | 다중 툴 실행 | All block types |

---

## 7. 핵심 차이점

### 7.1 Document 모드의 특수성

1. **CI Orchestrator 미사용**: 별도의 DocumentSearchService 사용
2. **RAG 패턴**: 검색 → 컨텍스트 구성 → LLM 생성
3. **Embedding**: 현재는 텍스트 검색(BM25+ILIKE)만 사용 (Embedding 서비스 미사용)

### 7.2 All 모드의 특수성

1. **두 가지 실행 모드**: LangGraph(LLM) vs Rule-based(키워드)
2. **서브툴 조합**: metric/hist/graph/config 중 선택적 실행
3. **요약 생성**: LLM으로 통합 요약 (LangGraph 모드)

### 7.3 공통 패턴

1. **Plan 기반 실행**: 모든 모드(except Document)가 Plan Schema 사용
2. **Tool Registry**: 도구 실행의 표준화 계층
3. **Stage-based Orchestration**: route → validate → execute → compose → present
4. **Block-based Response**: 모든 답변이 표준화된 Block 형태

---

## 8. 참고 파일 목록

| 파일 | 설명 |
|------|------|
| `apps/api/app/modules/ops/routes/query.py` | HTTP 요청 처리 |
| `apps/api/app/modules/ops/services/__init__.py` | 모드별 Executor 라우팅 |
| `apps/api/app/modules/ops/services/ci/orchestrator/runner.py` | CI Orchestrator 실행 엔진 |
| `apps/api/app/modules/ops/services/ci/planner/plan_schema.py` | Plan 데이터 모델 |
| `apps/api/app/modules/ops/services/langgraph.py` | LangGraph All Runner |
| `apps/api/app/modules/ops/schemas.py` | OPS Request/Response 스키마 |

---

## 9. 추가 분석 필요 항목

1. **Query Asset 실행 로직**: `_try_execute_query_assets()` 메서드 상세 분석
2. **CEP Simulation**: `cep_spec` 처리 방식 (현재는 placeholder)
3. **Fallback 로직**: 각 모드별 실패시 대응 전략
4. **캐싱 전략**: ToolResultCache, CICache 활용 방식

---

**작성일**: 2026-02-07  
**버전**: 1.0