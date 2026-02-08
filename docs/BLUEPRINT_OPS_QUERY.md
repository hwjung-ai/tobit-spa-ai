# OPS Query System Blueprint (v2 Final)

> 최종 업데이트: 2026-02-08
> 상태: **Production Ready**

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

## 4. OPS Orchestrator

### 4.1 실행 단계 (Stage Pipeline)

```
route_plan → validate → execute → compose → present
```

| 단계 | 역할 |
|------|------|
| **route_plan** | Plan Output Kind 결정 (DIRECT/PLAN/REJECT) |
| **validate** | Plan 유효성 검사, 정책 적용 |
| **execute** | Tool Registry 기반 도구 실행 |
| **compose** | 결과 합성 및 형식화 |
| **present** | 최종 Answer Blocks 생성 |

### 4.2 Tool Registry

| 도구 타입 | 용도 |
|-----------|------|
| `ci_lookup` | CI 검색 |
| `ci_aggregate` | CI 집계 |
| `ci_graph` | 그래프 확장 |
| `metric` | 메트릭 조회 |
| `event_log` | 이력 검색 |
| `document_search` | 문서 검색 |

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

## 7. 보안/테넌트

### 7.1 테넌트 격리

- 모든 SQL 쿼리에 `WHERE tenant_id = :tenant_id` 강제
- 삭제 확인: `AND deleted_at IS NULL`
- 요청 헤더: `X-Tenant-Id`, `X-User-Id`

### 7.2 Document Search 보안

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
| `ops/routes/query.py` | `/ops/query` 엔드포인트 (5개 모드) |
| `ops/routes/ci_ask.py` | `/ops/ask` 엔드포인트 (전체 모드) |
| `ops/routes/ui_actions.py` | `/ops/ui-actions` 엔드포인트 |

### 10.2 Backend (Services)

| 파일 | 역할 |
|------|------|
| `ops/services/__init__.py` | 모드별 Executor 라우팅 |
| `ops/services/ci/orchestrator/runner.py` | OPS Orchestrator 실행 엔진 (구현 경로: `ci/*`) |
| `ops/services/ci/planner/plan_schema.py` | Plan 데이터 모델 |
| `ops/services/langgraph.py` | LangGraph All Runner |
| `ops/services/action_registry.py` | UI Action 핸들러 레지스트리 |
| `ops/services/ui_actions.py` | UI Action 실행 서비스 |
| `ops/services/binding_engine.py` | 서버사이드 바인딩 엔진 |
| `ops/schemas.py` | OPS Request/Response 스키마 |

### 10.3 Document Search

| 파일 | 역할 |
|------|------|
| `document_processor/router.py` | Document Search API |
| `document_processor/services/search_service.py` | DocumentSearchService |
| `tools/init_document_search_tool.py` | Tool Asset 등록 스크립트 |
| `alembic/versions/0045_*.py` | 검색 인덱스 마이그레이션 |

### 10.4 Frontend

| 파일 | 역할 |
|------|------|
| `app/ops/page.tsx` | OPS 메인 페이지 (모드 선택/질의) |
| `components/ops/OpsSummaryStrip.tsx` | 요약 스트립 |

### 10.5 테스트

| 파일 | 역할 |
|------|------|
| `tests/test_document_search.py` | Document Search 테스트 |
| `tests/test_ops_action_registry.py` | Action Registry 테스트 |

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

## 12. 향후 과제

| 항목 | 우선순위 | 설명 |
|------|----------|------|
| Config 모드 데이터 연결 | 높 | CI lookup 데이터 소스 확인 |
| Metric 모드 데이터 연결 | 높 | 시계열 메트릭 데이터 소스 확인 |
| 대시보드 데이터 다운로드 | 중 | CSV/JSON/Excel 다운로드 기능 |
| 자동 회귀 테스트 스케줄링 | 중 | Golden Queries 주기적 자동 실행 |
| 다언어 BM25 | 중 | 한국어 형태소 분석 지원 |
| 검색 캐싱 (Redis) | 낮 | 반복 검색 성능 최적화 |
| 실시간 문서 인덱싱 | 낮 | 문서 업로드 시 즉시 검색 가능 |
