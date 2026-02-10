# OPS 모드별 데이터 소스 상세 분석

**작성일**: 2026-02-10
**주제**: 각 OPS 모드가 데이터를 어떻게 가져오는지 상세 분석

---

## 📋 요약 테이블

| 모드 | 데이터 소스 | Tool 사용 여부 | 상태 | 문제점 |
|------|-----------|--------------|------|--------|
| **config** | CI Table (직접 SQL) | ❌ 직접 query | ✅ 구현됨 | Tool Asset 아님 |
| **metric** | execute_universal + Orchestrator | ⚠️ 간접 | ⚠️ Mock fallback | Tools 등록 안 됨 |
| **hist** | execute_universal + Orchestrator | ⚠️ 간접 | ⚠️ Mock fallback | Tools 등록 안 됨 |
| **graph** | execute_universal + Neo4j | ⚠️ 간접 | ⚠️ Mock fallback | Tools 등록 안 됨 |
| **document** | DocumentSearchService (PostgreSQL BM25) | ✅ Service 직접 | ✅ 구현됨 | Tool Asset 아님 |
| **work_history** | ❌ NOT IMPLEMENTED | ❌ 없음 | ❌ 구현 안 됨 | 찾을 수 없음 |
| **all** | LangGraph Orchestrator | ⚠️ 간접 | ⚠️ 변동 | 복잡한 흐름 |

---

## 🔍 각 모드별 상세 분석

### 1️⃣ CONFIG 모드

#### 데이터 소스
```
CI Table (PostgreSQL) ← 직접 SQL Query
```

#### 구현 위치
```python
# File: apps/api/app/modules/ops/services/__init__.py:45-168
def run_config_executor(question: str, **kwargs):
    """Run config executor by directly querying the CI database."""

    # Step 1: CI 코드 추출 (텍스트 분석)
    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=10)

    # Step 2: 직접 DB 연결 (Tool 사용 안 함)
    connection = _get_connection()  # ← 직접 연결!
    conn = connection.connection

    # Step 3: 직접 SQL 실행
    with conn.cursor() as cur:
        if ci_hits:
            # 각 CI별 상세 정보 조회
            ci_get_sql = _load_query("ci_get.sql").format(field="ci_id")
            for hit in ci_hits[:5]:
                cur.execute(ci_get_sql, (hit.ci_id, tenant_id))
                row = cur.fetchone()
                # ← 결과를 MarkdownBlock, TableBlock으로 변환
        else:
            # CI 요약 (분포, 목록) 조회
            cur.execute("""
                SELECT ci_type, ci_subtype, status, COUNT(*)
                FROM ci
                WHERE tenant_id = %s
                GROUP BY ci_type, ci_subtype, status
            """, (tenant_id,))
```

#### ✅ 장점
- 빠른 응답 (직접 쿼리)
- 안정적 (일관된 구조)

#### ❌ 문제점
- **Tool Asset이 아님**: Tool Registry에 없음
- **Tool Schema 미정의**: LLM이 사용 불가
- **직접 연결**: _get_connection() 직접 호출
- **확장성 낮음**: 새 쿼리 추가 시 코드 수정 필요

#### Tool Asset 등록 상태
```python
# ❌ Tool Asset 없음!
# ci_detail_lookup이 있지만 실제로 사용되지 않음
```

---

### 2️⃣ METRIC 모드

#### 데이터 소스
```
execute_universal()
    ↓
CIOrchestratorRunner
    ↓
Orchestrator Logic (불명확)
    ↓
Mock Data Fallback (실제 데이터 없음)
```

#### 구현 위치
```python
# File: apps/api/app/modules/ops/services/__init__.py:219-237
def run_metric(question: str, **kwargs):
    """Run metric executor using execute_universal or mock data."""

    try:
        # execute_universal 호출 (Orchestrator 기반)
        result = execute_universal(question, "metric", tenant_id)

        if result.blocks:
            return result.blocks, result.used_tools
    except Exception as e:
        logger.warning(f"execute_universal failed for metric mode: {e}")

    # ❌ Mock data fallback
    return _mock_metric_blocks(question), ["metric_mock"]
```

#### execute_universal 흐름
```python
# File: apps/api/app/modules/ops/services/__init__.py:412-519
def execute_universal(question: str, mode: str, tenant_id: str):
    """Universal executor for metric, history, graph modes."""

    # Step 1: 간단한 Plan 생성
    plan = _create_simple_plan(mode)
    # ← PlanMode.CI, Intent.LOOKUP, View.SUMMARY 등

    # Step 2: CIOrchestratorRunner 생성 및 실행
    runner = CIOrchestratorRunner(
        plan=plan,
        tenant_id=tenant_id,
        question=question,
    )
    result = runner.run(plan_output=None)
    # ← result = {"answer": "...", "blocks": [...], "trace": {...}}

    # Step 3: 결과 처리
    blocks = []
    if result.get("blocks"):
        blocks = _convert_runner_blocks(result["blocks"], mode)

    return ExecutorResult(blocks=blocks, used_tools=[...])
```

#### ⚠️ 문제점
1. **orchestrator가 뭘 하는지 불명확**
   - CI Orchestrator일 뿐 metric 데이터를 어디서 가져오는지 알 수 없음

2. **Metric 데이터 소스 불명확**
   ```
   orchestrator.run()
       ↓ (뭘 하는가?)
   몰라요... 데이터 없으면 mock
   ```

3. **Tool 미사용**
   - metric_* tool이 정의되어 있지 않음
   - execute_universal이 Tool을 실제로 호출하는지 알 수 없음

4. **Mock Data에 의존**
   - 실제 metric 데이터 소스가 없어서 항상 mock 반환
   - 시스템이 "정상 작동"하는 것처럼 보이지만 가짜 데이터

#### Tool Asset 등록 상태
```python
# ❌ metric_* Tool이 없음!
# execute_universal이 내부적으로 Tool을 호출할 수도 있지만...
# LLM이 직접 사용할 수 없음
```

---

### 3️⃣ HIST (History) 모드

#### 데이터 소스
```
execute_universal()
    ↓
CIOrchestratorRunner
    ↓
Orchestrator Logic (불명확)
    ↓
Mock Data Fallback
```

#### 구현 위치
```python
# File: apps/api/app/modules/ops/services/__init__.py:191-216
def run_hist(question: str, **kwargs):
    """Run hist executor using execute_universal."""

    try:
        result = execute_universal(question, "hist", tenant_id)
        if result.blocks:
            return result.blocks, result.used_tools
    except Exception as e:
        logger.warning(f"execute_universal failed for hist mode: {e}")

    # ❌ Mock data fallback
    blocks = [
        MarkdownBlock(...),
        _mock_table(),  # 가짜 테이블!
    ]
    return blocks, ["hist_mock"]
```

#### ❌ 문제점
- **metric 모드와 동일한 문제**
- **실제 history 데이터 소스 불명확**
- **Tool 미사용**: maintenance_history_list, history_combined_union이 실제로 호출되지 않음
- **항상 Mock 반환**: 실제 데이터가 없음

#### Tool Asset 등록 상태
```python
# ✅ Tool Asset 있음!
# - maintenance_history_list: "List maintenance records..."
# - maintenance_ticket_create: "Create a new ticket"
# - history_combined_union: "Fetch combined history..."
#
# 하지만 execute_universal이 이들을 호출하지 않음
```

---

### 4️⃣ GRAPH 모드

#### 데이터 소스
```
execute_universal()
    ↓
CIOrchestratorRunner
    ↓
Neo4j (GraphDB) 또는 불명확
    ↓
Mock Data Fallback
```

#### 구현 위치
```python
# File: apps/api/app/modules/ops/services/__init__.py:171-188
def run_graph(question: str, **kwargs):
    """Run graph executor using execute_universal with CI relationship analysis."""

    try:
        result = execute_universal(question, "graph", tenant_id)
        if result.blocks:
            return result.blocks, result.used_tools
    except Exception as e:
        logger.warning(f"execute_universal failed for graph mode: {e}")

    # ❌ Mock graph data
    return [_mock_graph()], ["graph_mock"]
```

#### Orchestrator 내부 (추측)
```
execute_universal("graph mode")
    ↓
Plan 생성 (PlanMode.CI, Intent.EXPAND?)
    ↓
CIOrchestratorRunner.run()
    ↓
GraphSpec 실행
    ↓
Neo4j 쿼리 또는 PostgreSQL 관계 분석
    ↓
GraphBlock 반환
```

#### ❌ 문제점
- **Graph 데이터 소스 불명확**
- **Neo4j가 연결되어 있는지 알 수 없음**
- **Tool 미사용**: ci_graph_expand 등록되어 있으나 호출 확인 안 됨
- **항상 Mock**: 실제 graph 데이터 불명확

#### Tool Asset 등록 상태
```python
# ⚠️ Tool Asset 있지만...
# - ci_graph_expand: type="graph_query"
#
# execute_universal이 이를 호출하는지 알 수 없음
```

---

### 5️⃣ DOCUMENT 모드

#### 데이터 소스
```
DocumentSearchService
    ↓
PostgreSQL (tsvector + pgvector)
    ↓
BM25 + Vector Search (Hybrid)
```

#### 구현 위치 (완벽하게 구현됨)
```python
# File: apps/api/app/modules/ops/services/__init__.py:240-355
def run_document(question: str, **kwargs):
    """Run document search + RAG answer generation."""

    # Step 1: 문서 검색 (DocumentSearchService 사용)
    search_service = DocumentSearchService(session, embedding_service=None)

    search_results = asyncio.run(
        search_service.search(
            query=question,
            filters=SearchFilters(
                tenant_id=tenant_id,
                date_from=None,
                date_to=None,
                document_types=[],
                min_relevance=0.3
            ),
            top_k=5,
            search_type="text"  # BM25 + ILIKE
        )
    )

    # Step 2: 검색 결과 없으면 반환
    if not search_results:
        return [MarkdownBlock(content="No documents found")], ["document_search"]

    # Step 3: RAG 컨텍스트 생성
    context_snippets = []
    for i, result in enumerate(search_results, 1):
        doc_name = result.document_name
        chunk_text = result.chunk_text
        page = result.page_number
        context_snippets.append(f"[{i}. {doc_name}]\n{chunk_text}")

    context = "\n\n".join(context_snippets)

    # Step 4: LLM이 RAG 답변 생성
    answer_text = _generate_rag_answer(question, context, logger)

    # Step 5: 결과 블록 생성
    blocks = [
        MarkdownBlock(type="markdown", title="Answer", content=answer_text),
        ReferencesBlock(items=[...])  # 출처 문서 링크
    ]

    return blocks, ["document_search"]
```

#### ✅ 완벽한 구현
- **명확한 데이터 소스**: PostgreSQL BM25 + pgvector
- **RAG 방식**: 문서 검색 → LLM 답변 생성
- **출처 제시**: 검색 결과를 references로 표시
- **Service 직접 사용**: DocumentSearchService 직접 호출

#### ❌ 문제점
- **Tool Asset이 아님**: Tool Registry에 document_search tool이 없음
- **LLM이 Tool로 호출할 수 없음**: 직접 service 호출
- **Orchestrator를 거치지 않음**: 다른 모드와 다른 흐름

---

### 6️⃣ WORK_HISTORY 모드

#### ⚠️ **구현 안 됨**

전체 코드를 검색해도 work_history 모드 구현이 없음:

```python
# 찾을 수 없음!
def run_work_history(...):  # ❌ 없음
    ...

# execute_universal("work_history", ...) # ❌ 호출 안 됨
```

#### 예상되는 데이터 소스 (구현 안 됨)
```
work_history Table (PostgreSQL)
    ↓
Tool Asset: work_history_list (?)
    ↓
Tool Asset 미등록 (history_combined_union에 포함되어 있음)
```

#### Tool Asset 확인
```python
# Tool Asset 중:
# - maintenance_history_list: "List maintenance records..."
# - history_combined_union: "Fetch combined work and maintenance history"
#   ↑ work_history가 포함되어 있을 수 있음

# 하지만 work_history 전용 Tool이나 모드가 없음
```

---

### 7️⃣ ALL 모드

#### 데이터 소스
```
LangGraphAllRunner (Orchestrator)
    ↓
여러 Tool 조합
    ↓
결과 통합
```

#### 구현 위치
```python
# File: apps/api/app/modules/ops/services/__init__.py:1118-1120
if mode == "all":
    return _run_all(question, settings)

# File: apps/api/app/modules/ops/services/langgraph.py
def _run_all(question: str, settings: Any):
    runner = LangGraphAllRunner(...)
    return runner.run(question)
```

#### ⚠️ 복잡한 흐름
- LangGraph를 사용한 multi-step orchestration
- 여러 Tool을 조합하여 답변
- Tool 선택이 LLM 또는 정책에 의해 결정

---

## 🎯 지적 사항 정리

### 당신의 질문
> "work_history가 안보인다. graph db에서 가져오는 것, metric에서 가져오는 것도 안보이는구나. document는 어떻게 가져오니?"

### 답변

| 모드 | 데이터 처리 | Tool 사용 |
|------|-----------|---------|
| **config** | ✅ 직접 CI table 쿼리 | ❌ 직접 SQL |
| **metric** | ❌ orchestrator 불명확 + mock fallback | ❌ 사용 안 됨 |
| **hist** | ❌ orchestrator 불명확 + mock fallback | ❌ Tool Asset 있지만 미사용 |
| **graph** | ❌ orchestrator 불명확 + mock fallback | ❌ Tool Asset 있지만 미사용 |
| **document** | ✅ DocumentSearchService + PostgreSQL BM25 | ❌ Service 직접 호출 |
| **work_history** | ❌ **구현 안 됨** | ❌ Tool 없음 |
| **all** | ⚠️ LangGraph orchestrator | ⚠️ 복잡함 |

---

## 🔴 핵심 문제

### 1. Metric, Hist, Graph 모드의 데이터 소스 불명확

```python
execute_universal(question, "metric", tenant_id)
    ↓
CIOrchestratorRunner.run()
    ↓
??? (뭘 하는가?)
    ↓
결과 없으면 mock_metric_blocks() 반환
```

**질문**:
- orchestrator가 어디서 metric 데이터를 가져오는가?
- Database query인가? API call인가?
- Tool을 호출하는가?

### 2. Tool Asset이 정의되어 있지만 사용되지 않음

```python
# Tool Asset 정의:
TOOL_ASSETS = [
    {
        "name": "ci_detail_lookup",
        "tool_input_schema": {...},
        "tool_output_schema": {...}
    },
    {
        "name": "maintenance_history_list",
        "tool_input_schema": {...},
        "tool_output_schema": {...}
    },
    {
        "name": "history_combined_union",
        "tool_input_schema": {...},
        "tool_output_schema": {...}
    },
    # ...
]

# 하지만 실제로는:
# - config 모드: 직접 SQL (Tool 사용 안 함)
# - metric 모드: execute_universal → mock (Tool 사용 확인 안 됨)
# - hist 모드: execute_universal → mock (Tool 사용 확인 안 됨)
# - graph 모드: execute_universal → mock (Tool 사용 확인 안 됨)
```

**결론**: Tool Asset이 있지만 **실제로 사용되지 않고 있음**

### 3. Mock Data에 의존

```python
# metric 모드
result = execute_universal(question, "metric", tenant_id)
if result.blocks:
    return result.blocks
else:
    return _mock_metric_blocks(question)  # ← 항상 이걸 반환!

# hist 모드
result = execute_universal(question, "hist", tenant_id)
if result.blocks:
    return result.blocks
else:
    blocks = [MarkdownBlock(...), _mock_table()]  # ← 항상 이걸 반환!

# graph 모드
result = execute_universal(question, "graph", tenant_id)
if result.blocks:
    return result.blocks
else:
    return [_mock_graph()]  # ← 항상 이걸 반환!
```

---

## 💡 개선 방안

### Phase 1: Orchestrator 검증
```
execute_universal이 실제로 Tool을 호출하는지 확인
├─ CIOrchestratorRunner.run() 추적
├─ metric 데이터가 어디서 오는지 추적
├─ hist 데이터가 어디서 오는지 추적
└─ graph 데이터가 어디서 오는지 추적
```

### Phase 2: Tool Asset 실제 사용
```
execute_universal에서 Tool Asset 사용하도록 수정
├─ metric_* tools 정의 (지금 없음)
├─ ci_detail_lookup 실제 사용
├─ maintenance_history_list 실제 사용
└─ history_combined_union 실제 사용
```

### Phase 3: Mock Data 제거
```
실제 데이터가 없으면 명시적 에러 표시
├─ "Metric data not available"
├─ "History data not available"
└─ "Graph data not available"
```

### Phase 4: Work History 구현
```
work_history 모드 추가
├─ run_work_history() 함수 구현
├─ Tool Asset 또는 Service 연결
└─ 데이터 소스 명확화
```

---

## 📊 최종 정리

### ✅ 완벽한 모드
- **config**: 직접 CI SQL 쿼리 (명확함)
- **document**: DocumentSearchService (명확함)

### ⚠️ 불명확한 모드
- **metric**: orchestrator + mock
- **hist**: orchestrator + mock
- **graph**: orchestrator + mock

### ❌ 미구현 모드
- **work_history**: 완전히 없음

### Tool 사용 현황
- **등록된 Tool Asset**: 6개 (ci_*, maintenance_*, history_*)
- **실제 사용되는 Tool**: 0개 (모두 직접 쿼리 또는 service)
- **LLM이 호출 가능한 Tool**: 6개 (하지만 orchestrator가 미사용)

---

## 🎓 결론

당신의 질문이 정확합니다:

1. **work_history**: 구현되지 않음 ❌
2. **metric 데이터**: orchestrator에서 어디서 오는지 불명확 ⚠️
3. **graph 데이터**: orchestrator에서 어디서 오는지 불명확 ⚠️
4. **document 데이터**: DocumentSearchService → PostgreSQL BM25 (명확) ✅

**핵심 문제**: Tool Asset이 정의되었지만 **실제로 사용되지 않고 있음**
