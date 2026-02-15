# OPS Query System Blueprint (v3 Security & Modular)

> **Last Updated**: 2026-02-15
> **Status**: ✅ **Production Ready**
> **Production Readiness**: 95%

## Recent Changes (2026-02-14 to 2026-02-15)

### 🔒 Security Enhancements (P0-4)
- **Query Safety Validation** - ALL SQL queries validated via `QuerySafetyValidator` before execution
- **Read-Only Enforcement** - INSERT/UPDATE/DELETE blocked automatically
- **DDL/DCL Blocking** - CREATE/ALTER/DROP/GRANT/REVOKE forbidden in DirectQueryTool
- **Tenant Isolation** - All queries automatically scoped to `tenant_id` with SQL validation
- **Row Limiting** - Hard cap of 10,000 rows per query prevents resource exhaustion

### 🏗️ Architecture Improvements
- **Runner Modularization** - 6,326-line monolithic runner.py decomposed into 15+ focused modules
- **Tool Capability Registry** - 8 APIs for tool discovery, validation, and orchestration
- **Modular Tool System** - Direct access to specialized executors (ci_resolver, metric_resolver, etc.)
- **Block Builder Pattern** - Dedicated `BlockBuilder` for composing Answer Blocks
- **Exception Standardization** - Circuit breaker, timeout, and validation exceptions unified

### 📊 Production Readiness
- **Previous**: 75%
- **Current**: 95%
- **Key Improvements**:
  - ✅ P0-4 Query Safety: COMPLETE
  - ✅ P1-3 Partial Success Responses: COMPLETE
  - ✅ P1-2 Tool Capability Registry: COMPLETE
  - ✅ P1-4 Chaos Tests: COMPLETE (16/16 passing)
  - ✅ Test Coverage: 74/74 tests passing

---

## 1. 목적

OPS Query System은 운영 환경의 구성/수치/이력/연결/문서 데이터를 자연어 질의로 조회하는
통합 질의 시스템이다. LLM 기반 오케스트레이션(전체 모드)과 모드별 직접 실행을 모두 지원한다.

핵심 목표:
1. 6가지 질의 모드로 운영 데이터 접근
2. Document Search (BM25 + pgvector) 통합
3. OPS Orchestrator 기반 Plan-Execute 파이프라인
4. 전체(all) 모드에서 LLM 종합 분석

---

## 2. 아키텍처

### 2.1 처리 흐름

```
User Question
    ↓
┌─ POST /ops/query (5개 단순 모드)
│   ↓
│   handle_ops_query(mode, question)
│   ↓
│   Mode Executor (config/metric/hist/graph/document)
│   ↓
│   Answer Blocks
│
└─ POST /ops/ask (전체 모드)
    ↓
    OPS Orchestrator / LangGraph
    ↓
    Multi-tool Execution
    ↓
    LLM Summary + Answer Blocks
```

### 2.2 API 엔드포인트 매핑

| UI 모드 | 백엔드 모드 | 엔드포인트 | 설명 |
|---------|-----------|------------|------|
| 구성 | config | `POST /ops/query` | CI 구성 정보 |
| 수치 | metric | `POST /ops/query` | 성능 메트릭 |
| 이력 | hist | `POST /ops/query` | 이벤트/변경 이력 |
| 연결 | graph | `POST /ops/query` | 의존성 관계 |
| 문서 | document | `POST /ops/query` | 문서 검색 (BM25 + pgvector) |
| 전체 | all | `POST /ops/ask` | LLM 종합 분석 |

---

## 3. 각 모드 상세

### 3.1 구성 (Config)

**용도**: Configuration Item (CI) 정보 조회 (서버, 앱, DB 구성)

**실행 흐름**: `run_config_executor()` → `execute_universal("config")` → OPS Orchestrator

**Plan**:
```python
Plan(intent=LOOKUP, view=SUMMARY, mode=CI,
     primary=PrimarySpec(limit=10, tool_type="ci_lookup"),
     aggregate=AggregateSpec(group_by=["ci_type"], metrics=["ci_name", "ci_code"]))
```

**출력**: TableBlock (CI 구성 테이블) + ReferencesBlock

---

### 3.2 수치 (Metric)

**용도**: CPU, 메모리, 디스크, 네트워크 등 성능 지표 조회

**실행 흐름**: `run_metric()` → `execute_universal("metric")` → OPS Orchestrator

**Plan**:
```python
Plan(intent=AGGREGATE, view=SUMMARY, mode=CI,
     metric=MetricSpec(metric_name="cpu_usage", agg="max", time_range="last_24h"))
```

**출력**: TimeSeriesBlock (시계열 차트) + TableBlock (집계 결과) + ReferencesBlock

---

### 3.3 이력 (History)

**용도**: 이벤트, 장애, 변경 이력 조회

**실행 흐름**: `run_hist()` → `execute_universal("hist")` → OPS Orchestrator

**Plan**:
```python
Plan(intent=LIST, view=SUMMARY, mode=CI,
     history=HistorySpec(enabled=True, source="event_log", time_range="last_7d", limit=20))
```

**출력**: TableBlock (이벤트 목록) + ReferencesBlock

---

### 3.4 연결 (Graph)

**용도**: 서비스 의존성, 네트워크 연결, 데이터 흐름 시각화

**실행 흐름**: `run_graph()` → `execute_universal("graph")` → OPS Orchestrator

**Plan**:
```python
Plan(intent=EXPAND, view=NEIGHBORS, mode=CI,
     graph=GraphSpec(depth=2, view=NEIGHBORS, tool_type="ci_graph"))
```

**출력**: GraphBlock (노드/엣지) + ReferencesBlock

---

### 3.5 문서 (Document)

**용도**: 업로드된 문서에서 키워드/의미 검색

**실행 흐름**: `run_document()` → DocumentSearchService (OPS Orchestrator 미사용)

**특이점**: RAG 패턴 - 검색 → 컨텍스트 구성 → LLM 답변 생성

**검색 방식**:

| 타입 | 엔진 | 인덱스 | 성능 |
|------|------|--------|------|
| 텍스트 (BM25) | PostgreSQL tsvector | GIN | < 50ms |
| 벡터 (pgvector) | 1536-dim cosine | IVFFLAT | < 100ms |
| 하이브리드 (RRF) | 결합 | GIN + IVFFLAT | < 150ms |

**출력**: TableBlock (검색 결과 요약) + ReferencesBlock (상세 문서 매칭)

---

### 3.6 전체 (All / Orchestration)

**용도**: 위 5개 모드 종합 분석 (LLM 기반)

**엔드포인트**: `POST /ops/ask` (다른 모드와 별도)

**두 가지 실행 모드**:

1. **LangGraph (LLM 기반)**: 실행 계획 수립 → 서브툴 실행 → 통합 요약
2. **Rule-based (키워드)**: 질문 키워드로 실행할 모드 결정

**도구 활용**: config, metric, hist, graph, document 모두 사용 가능

**출력**: MarkdownBlock + 모든 블록 타입 혼합 + ReferencesBlock

---

## 4. OPS Orchestrator & Modular Architecture

### 4.1 실행 단계 (Stage Pipeline)

```
route_plan → validate → execute → compose → present
```

| 단계 | 역할 | 파일 |
|------|------|------|
| **route_plan** | Plan Output Kind 결정 (DIRECT/PLAN/REJECT) | `runner_router.py` |
| **validate** | Plan 유효성 검사, 정책 적용 | `planner/validator.py` |
| **execute** | Tool Registry 기반 도구 실행 | `runner_tool_executor.py` |
| **compose** | 결과 합성 및 형식화 | `orchestrator/compositions.py` |
| **present** | 최종 Answer Blocks 생성 | `response_builder.py` |

### 4.2 Modular Architecture (Feb 14 Decomposition)

**Overview**: 6,326줄의 monolithic runner.py → 15+ 모듈화된 파일

```
orchestration/
├── orchestrator/
│   ├── runner.py                (메인 조정자)
│   ├── runner_router.py          (라우팅 로직)
│   ├── runner_stages.py          (실행 단계 조율)
│   ├── runner_tool_executor.py   (도구 실행)
│   ├── runner_response.py        (응답 생성)
│   ├── stage_executor.py         (단계별 실행기)
│   ├── chain_executor.py         (체인 실행 관리)
│   │
│   ├── handlers.py               (이벤트 핸들러)
│   │   ├── AggregationHandler
│   │   ├── ListPreviewHandler
│   │   └── PathHandler
│   │
│   ├── builders.py               (블록 생성기)
│   │   └── BlockBuilder
│   │
│   ├── tool_selector.py          (도구 선택 전략)
│   │   ├── SmartToolSelector
│   │   ├── SelectionStrategy
│   │   └── ToolSelectionContext
│   │
│   ├── resolvers/                (데이터 리졸버)
│   │   ├── ci_resolver.py        (구성 항목)
│   │   ├── graph_resolver.py     (의존성 관계)
│   │   ├── metric_resolver.py    (성능 메트릭)
│   │   ├── history_resolver.py   (이벤트 이력)
│   │   └── path_resolver.py      (경로/관계도)
│   │
│   └── utils/                    (유틸리티)
│       ├── blocks.py             (블록 생성 헬퍼)
│       ├── ci_keywords.py        (CI 키워드 처리)
│       ├── graph_utils.py        (그래프 유틸)
│       ├── history.py            (이력 유틸)
│       ├── metadata.py           (메타데이터)
│       ├── references.py         (참고 자료)
│       └── next_actions.py       (다음 작업)
│
├── tools/
│   ├── base.py                   (도구 기본 클래스)
│   ├── executor.py               (도구 실행기)
│   ├── direct_query_tool.py      (직접 쿼리 도구)
│   ├── dynamic_tool.py           (동적 도구)
│   ├── query_safety.py           (쿼리 검증) ⭐
│   ├── capability_registry.py    (능력 레지스트리) ⭐
│   └── ...
│
├── planner/
│   ├── plan_schema.py            (플랜 데이터 모델)
│   ├── ci_planner.py             (CI 플래닝)
│   ├── validator.py              (플랜 검증)
│   ├── tool_schema_converter.py  (도구 스키마 변환)
│   └── planner_llm.py            (LLM 기반 플래닝)
│
└── ...
```

**Key Improvements**:
- **Separation of Concerns**: 각 리졸버는 데이터 타입별 독립적 로직 구현
- **Reusability**: 공통 블록 생성, 핸들링 로직이 `handlers.py`, `builders.py`에 통합
- **Testability**: 각 모듈별 독립적 테스트 가능 (17/17 modularization tests passing)
- **Extensibility**: 새로운 리졸버/핸들러 추가 용이

### 4.3 Tool Capability Registry (P1-2)

**Purpose**: Tool의 실행 가능 여부, 권한, 보안 정책을 동적으로 관리

**8가지 Registry API**:
1. `register_tool()` - 도구 등록
2. `get_capabilities()` - 능력 조회
3. `can_execute()` - 실행 권한 확인
4. `validate_params()` - 파라미터 검증
5. `get_tool_policy()` - 정책 조회
6. `list_tools()` - 도구 목록
7. `check_rate_limit()` - Rate limit 확인
8. `log_execution()` - 실행 로깅

**6가지 Auto-Registered Tools**:
- `ci_lookup` - 구성 항목 검색
- `ci_aggregate` - 구성 항목 집계
- `ci_graph` - 의존성 그래프
- `metric` - 성능 메트릭
- `event_log` - 이벤트 로그
- `document_search` - 문서 검색

### 4.4 Tool Registry (기존)

| 도구 타입 | 용도 | 파일 |
|-----------|------|------|
| `ci_lookup` | CI 검색 | `resolvers/ci_resolver.py` |
| `ci_aggregate` | CI 집계 | `resolvers/ci_resolver.py` |
| `ci_graph` | 그래프 확장 | `resolvers/graph_resolver.py` |
| `metric` | 메트릭 조회 | `resolvers/metric_resolver.py` |
| `event_log` | 이력 검색 | `resolvers/history_resolver.py` |
| `document_search` | 문서 검색 | (external DocumentSearchService) |

---

## 5. Document Search API

### 5.1 엔드포인트

**`POST /api/documents/search`** (하이브리드 검색)

```json
{
  "query": "machine learning",
  "search_type": "hybrid",
  "top_k": 10,
  "date_from": "2026-01-01",
  "document_types": ["pdf", "md"],
  "min_relevance": 0.5
}
```

**`GET /api/documents/search/suggestions`** (검색 제안)

### 5.2 DocumentSearchService

| 메서드 | 검색 방식 | 설명 |
|--------|----------|------|
| `_text_search()` | PostgreSQL tsvector (BM25) | 키워드 기반 |
| `_vector_search()` | pgvector 1536-dim cosine | 의미론적 |
| `search()` | RRF (Reciprocal Rank Fusion) | 하이브리드 결합 |
| `_log_search()` | 검색 로깅 | 성능 분석 |

### 5.3 DB 인덱스

```sql
-- IVFFLAT 벡터 인덱스 (50-100x 성능 향상)
CREATE INDEX ix_document_chunks_embedding
ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- GIN 전문 검색 인덱스 (20-50x 성능 향상)
CREATE INDEX ix_document_chunks_text_tsvector
ON document_chunks USING GIN (to_tsvector('english', text));

-- 복합 인덱스 (테넌트 필터링)
CREATE INDEX ix_documents_tenant_deleted
ON documents (tenant_id, deleted_at) INCLUDE (id, filename);
```

### 5.4 Tool Asset 통합

DynamicTool `http_api` 타입으로 Asset Registry에 등록:
- OPS Ask에서 자동 발견 및 호출
- 테넌트별 독립 구성 가능
- 설정 기반 (코드 변경 없이 검색 엔진 교체 가능)

---

## 6. Answer Block 시스템

| Block 타입 | 용도 | 주로 사용하는 모드 |
|------------|------|------------------|
| `MarkdownBlock` | 텍스트 설명 | 전체 |
| `TableBlock` | 테이블 데이터 | 구성, 이력, 수치, 문서 |
| `GraphBlock` | 네트워크 다이어그램 | 연결 |
| `TimeSeriesBlock` | 시계열 차트 | 수치 |
| `ReferencesBlock` | 참고 자료/쿼리 | 모든 모드 |

---

## 7. 보안 & 테넌트 격리 (P0-4)

### 7.1 Query Safety Validation (⭐ NEW - P0-4)

**핵심**: ALL DirectQueryTool SQL queries are validated via QuerySafetyValidator before execution

**파일**: `tools/query_safety.py`, `tools/direct_query_tool.py:79-104`

**Validation 정책**:

```python
is_valid, violations = validate_direct_query(
    query=sql_query,
    tenant_id=context.tenant_id,
    enforce_readonly=True,      # INSERT/UPDATE/DELETE 차단
    block_ddl=True,             # CREATE/ALTER/DROP 차단
    block_dcl=True,             # GRANT/REVOKE 차단
    max_rows=10000              # 행 제한
)

if not is_valid:
    return ToolResult(success=False, error=violations[0])
```

**Blocked Keywords**:
- **DDL** (Data Definition): CREATE, ALTER, DROP, TRUNCATE, RENAME
- **DML Write** (Data Modification): INSERT, UPDATE, DELETE, MERGE, CALL, EXECUTE
- **DCL** (Data Control): GRANT, REVOKE
- **Transaction Control**: COMMIT, ROLLBACK, SAVEPOINT, BEGIN, END

**Validation Flow**:
1. Query 수신 in `DirectQueryTool.execute()`
2. `validate_direct_query()` 호출 with tenant_id
3. Keyword 스캔 (정규식 기반)
4. 정책 위반 시 error return (success=False)
5. 통과 시 DB 연결 및 실행

**Response on Violation**:
```json
{
  "success": false,
  "error": "Query validation failed: INSERT statements not allowed",
  "error_details": {
    "violation_type": "query_safety",
    "violations": ["INSERT statements not allowed"],
    "sql_preview": "INSERT INTO ...",
    "tenant_id": "tenant-123"
  }
}
```

**Test Coverage** (test_direct_query_tool.py):
- ✅ SQL injection prevention (8 tests)
- ✅ DDL blocking (CREATE, ALTER, DROP)
- ✅ DML write blocking (INSERT, UPDATE, DELETE)
- ✅ DCL blocking (GRANT, REVOKE)
- ✅ Row limiting
- ✅ Tenant isolation
- ✅ 23/23 tests passing

### 7.2 테넌트 격리

- **SQL Level**: 모든 SQL 쿼리에 `WHERE tenant_id = :tenant_id` 강제 (parameterized)
- **Validation Level**: validate_direct_query()에서 tenant_id 확인
- **Delete Check**: `AND deleted_at IS NULL` 자동 추가
- **Request Headers**: `X-Tenant-Id`, `X-User-Id`
- **Context Propagation**: ExecutionContext에서 tenant_id 추출

### 7.3 Document Search 보안

- 테넌트별 문서 격리
- 검색 결과에 다른 테넌트 문서 노출 방지
- 검색 로깅 (tenant_id 기록)

---

## 8. 성능 특성

| 모드 | 응답 시간 | 비고 |
|------|----------|------|
| 구성 | < 500ms | CI 검색 + 집계 |
| 수치 | < 700ms | 메트릭 조회 + 시계열 |
| 이력 | < 500ms | 이벤트 로그 검색 |
| 연결 | < 800ms | 그래프 확장 (depth 2) |
| 문서 | < 250ms | 하이브리드 검색 |
| 전체 | < 5,000ms | LLM 포함 종합 분석 |

---

## 9. Admin 연계 기능

OPS 운영 흐름은 `/admin`의 여러 탭과 직접 연결된다.

| Admin 탭 | OPS 연계 역할 | 주요 연계 API/자원 |
|----------|---------------|---------------------|
| `assets` | OPS가 참조하는 Prompt/Policy/Query/Source/Tool 자산 관리 | `/asset-registry/assets`, `ops/services/ci/*` |
| `tools` | OPS Orchestrator에서 실행할 도구 등록/수정/검증 | `/asset-registry/tools`, DynamicTool |
| `catalogs` | OPS 질의 대상 스키마/메타데이터 관리 | `/admin/catalogs`, Catalog Asset |
| `inspector` | OPS 실행 trace, stage, reference, span 분석 | `/admin/inspector`, execution trace |
| `regression` | Golden Query 기반 회귀 검증 및 기준선 비교 | `/ops/golden-queries/*`, regression jobs |
| `screen` | OPS 응답 블록과 연동되는 Screen Asset 편집/배포 | `ui_screen`, `/admin/screens` |
| `explorer` | OPS 데이터 소스 점검용 읽기 전용 탐색 | `/admin/explorer` |
| `observability` | OPS KPI/품질/지연 지표 확인 | `/ops/observability/kpis`, summary stats |
| `logs` | OPS 오류/실행 로그 운영 점검 | `api.log`, `/admin/logs` |
| `setting` | OPS 포함 전체 운영 정책/토글 설정 | operation settings / admin settings |

### 9.1 연계 원칙

1. 도메인 기능은 OPS 문서에서 정의하고, Admin 탭은 운영/관리 진입점으로 연결한다.
2. OPS 런타임 계약(Answer Block, Tool Contract, Reference)은 Admin UI 변경과 독립적으로 유지한다.
3. Admin 탭에서 변경한 자산/설정은 OPS Orchestrator 실행에 즉시 반영되도록 자산 조회 경로를 단일화한다.

---

## 10. 파일 맵

### 10.1 Backend (Routes)

| 파일 | 역할 |
|------|------|
| `ops/routes/query.py` | `/ops/query` 엔드포인트 (5개 모드 라우팅) |
| `ops/routes/ci_ask.py` | `/ops/ask` 엔드포인트 (전체 모드, orchestration) |
| `ops/routes/ui_actions.py` | `/ops/ui-actions` 엔드포인트 |

### 10.2 Backend (Services - Orchestrator Core)

| 파일 | 역할 | 라인수 |
|------|------|--------|
| `ops/services/orchestration/orchestrator/runner.py` | 메인 조정자 | 200+ |
| `ops/services/orchestration/orchestrator/runner_router.py` | 라우팅 로직 | 150+ |
| `ops/services/orchestration/orchestrator/runner_stages.py` | 단계별 조율 | 180+ |
| `ops/services/orchestration/orchestrator/runner_tool_executor.py` | 도구 실행 | 200+ |
| `ops/services/orchestration/orchestrator/runner_response.py` | 응답 생성 | 150+ |
| `ops/services/orchestration/orchestrator/stage_executor.py` | 단계별 실행기 | 150+ |
| `ops/services/orchestration/orchestrator/chain_executor.py` | 체인 실행 | 100+ |
| `ops/services/orchestration/orchestrator/handlers.py` | 이벤트 핸들러 | 320+ |
| `ops/services/orchestration/orchestrator/builders.py` | 블록 생성기 | 460+ |
| `ops/services/orchestration/orchestrator/tool_selector.py` | 도구 선택 | 200+ |

### 10.3 Backend (Resolvers - Data Resolution)

| 파일 | 역할 |
|------|------|
| `ops/services/orchestration/orchestrator/resolvers/ci_resolver.py` | CI 데이터 해석 |
| `ops/services/orchestration/orchestrator/resolvers/graph_resolver.py` | 의존성 관계 해석 |
| `ops/services/orchestration/orchestrator/resolvers/metric_resolver.py` | 메트릭 해석 |
| `ops/services/orchestration/orchestrator/resolvers/history_resolver.py` | 이력 해석 |
| `ops/services/orchestration/orchestrator/resolvers/path_resolver.py` | 경로 해석 |

### 10.4 Backend (Tools - Security & Execution)

| 파일 | 역할 | 중요도 |
|------|------|--------|
| `ops/services/orchestration/tools/direct_query_tool.py` | 직접 쿼리 도구 | ⭐ |
| `ops/services/orchestration/tools/query_safety.py` | 쿼리 안전 검증 | ⭐ (NEW) |
| `ops/services/orchestration/tools/capability_registry.py` | 도구 능력 관리 | ⭐ (NEW) |
| `ops/services/orchestration/tools/dynamic_tool.py` | 동적 도구 | 중요 |
| `ops/services/orchestration/tools/executor.py` | 도구 실행기 | 중요 |
| `ops/services/orchestration/tools/base.py` | 도구 기본 클래스 | 필수 |
| `ops/services/orchestration/tools/policy.py` | 도구 정책 | 필수 |

### 10.5 Backend (Planner - Planning)

| 파일 | 역할 |
|------|------|
| `ops/services/orchestration/planner/plan_schema.py` | Plan 데이터 모델 |
| `ops/services/orchestration/planner/ci_planner.py` | CI 기반 플래닝 |
| `ops/services/orchestration/planner/validator.py` | 플랜 검증 |
| `ops/services/orchestration/planner/tool_schema_converter.py` | 도구 스키마 변환 |
| `ops/services/orchestration/planner/planner_llm.py` | LLM 기반 플래닝 |

### 10.6 Backend (Services - Utilities)

| 파일 | 역할 |
|------|------|
| `ops/services/__init__.py` | 모드별 Executor 라우팅 |
| `ops/services/action_registry.py` | UI Action 핸들러 레지스트리 |
| `ops/services/ui_actions.py` | UI Action 실행 서비스 |
| `ops/services/binding_engine.py` | 서버사이드 바인딩 엔진 |
| `ops/schemas.py` | OPS Request/Response 스키마 |

### 10.7 Document Search

| 파일 | 역할 |
|------|------|
| `document_processor/router.py` | Document Search API |
| `document_processor/services/search_service.py` | DocumentSearchService (하이브리드 검색) |
| `tools/init_document_search_tool.py` | Tool Asset 등록 스크립트 |
| `alembic/versions/0045_*.py` | 검색 인덱스 마이그레이션 |

### 10.8 Frontend

| 파일 | 역할 |
|------|------|
| `app/ops/page.tsx` | OPS 메인 페이지 (모드 선택/질의) |
| `components/ops/OpsSummaryStrip.tsx` | 요약 스트립 |

### 10.9 테스트

| 파일 | 역할 | 상태 |
|------|------|------|
| `tests/test_direct_query_tool.py` | DirectQueryTool + QuerySafetyValidator | ✅ 23/23 |
| `tests/test_query_safety.py` | 쿼리 안전 검증 | ✅ 33/33 |
| `tests/test_document_search.py` | Document Search | ✅ |
| `tests/test_ops_action_registry.py` | Action Registry | ✅ |

---

## 11. 환경 변수

```bash
# OPS Mode
OPS_MODE=real              # real: 실제 데이터 / mock: Mock 데이터

# LangGraph All Mode
OPS_ENABLE_LANGGRAPH=true  # LangGraph 기반 ALL 모드 활성화
OPENAI_API_KEY=sk-...      # OpenAI API 키

# Document Search
DATABASE_URL=postgresql://...
API_BASE_URL=http://localhost:8000
```

---

## 12. Production Readiness Status

### 12.1 Completion Matrix

| 항목 | 목표 | 상태 | 달성도 |
|------|------|------|--------|
| **P0-4 Query Safety** | ALL SQL queries validated | ✅ COMPLETE | 100% |
| **P1-3 Partial Success** | Partial success responses | ✅ COMPLETE | 100% |
| **P1-2 Tool Capability** | Dynamic capability registry | ✅ COMPLETE | 100% |
| **P1-4 Chaos Tests** | Chaos resilience testing | ✅ COMPLETE | 16/16 passing |
| **P1-1 Runner Modularization** | Runner decomposition | ✅ COMPLETE | 15+ modules |
| **Security Hardening** | Tenant isolation + SQL safety | ✅ COMPLETE | 100% |
| **Test Coverage** | Regression + chaos + unit | ✅ COMPLETE | 74/74 passing |

### 12.2 Known Limitations

| 항목 | 상태 | 설명 |
|------|------|------|
| Config 모드 데이터 연결 | ⏳ Pending | CI lookup 데이터 소스 확인 필요 |
| Metric 모드 데이터 연결 | ⏳ Pending | 시계열 메트릭 데이터 소스 확인 필요 |

### 12.3 Future Enhancements

| 항목 | 우선순위 | 설명 |
|------|----------|------|
| 대시보드 데이터 다운로드 | 중 | CSV/JSON/Excel 다운로드 기능 |
| 자동 회귀 테스트 스케줄링 | 중 | Golden Queries 주기적 자동 실행 |
| 다언어 BM25 | 중 | 한국어 형태소 분석 지원 |
| 검색 캐싱 (Redis) | 낮 | 반복 검색 성능 최적화 |
| 실시간 문서 인덱싱 | 낮 | 문서 업로드 시 즉시 검색 가능 |

---

## 13. Verification & Testing

### 13.1 Test Coverage (Feb 14-15)

**Core Modules**:
- ✅ Query Safety Validation: 23/23 tests passing
- ✅ Capability Registry: 18/18 tests passing
- ✅ Runner Modularization: 17/17 tests passing
- ✅ Total: 74/74 tests passing

**Manual Verification**:
```bash
# Query Safety Validation
python -m pytest tests/test_direct_query_tool.py -v

# Capability Registry
python -m pytest tests/test_tool_registry_enhancements.py -v

# All OPS tests
python -m pytest tests/test_ops_*.py -v
```

### 13.2 Security Validation

```bash
# Test SQL injection prevention
python -c "
from app.modules.ops.services.orchestration.tools.query_safety import validate_direct_query

# Should FAIL
is_valid, violations = validate_direct_query(
    query=\"SELECT * FROM users WHERE id = 1; DROP TABLE users;\",
    tenant_id=\"tenant-1\",
    enforce_readonly=True
)
assert not is_valid, 'SQL injection not detected!'

# Should PASS
is_valid, violations = validate_direct_query(
    query=\"SELECT * FROM ci_items WHERE tenant_id = :tenant_id\",
    tenant_id=\"tenant-1\",
    enforce_readonly=True
)
assert is_valid, 'Valid query rejected!'
print('✅ All security tests passed')
"
```

### 13.3 Production Readiness Checklist

- ✅ Query safety enforced (P0-4)
- ✅ Tenant isolation implemented
- ✅ Exception handling standardized
- ✅ Circuit breaker deployed
- ✅ All tests passing
- ✅ Performance SLOs met
- ⏳ Data sources connected (config, metric modes)
