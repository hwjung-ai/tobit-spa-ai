# Tobit SPA AI - 시스템 아키텍처 보고서

**작성일**: 2026-02-05 (최종 갱신: 2026-02-08)
**대상**: 경영진, 의사결정자
**목적**: 시스템 전체 구조와 핵심 모듈의 아키텍처 이해

---

## 1. 개요

Tobit SPA AI는 AI 기반 인프라 운영 지원 플랫폼입니다. 운영자의 자연어 질문에 답변하고, 실시간 이벤트를 감시하며, 문서 검색과 동적 API 실행, 운영 화면 편집/배포를 제공합니다.

### 1.1 핵심 모듈

| 모듈 | 역할 |
|------|------|
| **OPS** | AI 기반 인프라 질의응답 (6개 쿼리 모드) |
| **CEP** | 실시간 이벤트 처리 및 알림 (4가지 트리거, 5채널 알림) |
| **DOCS** | 문서 관리 및 하이브리드 검색 (BM25 + pgvector) |
| **API Engine** | 동적 API 정의/실행 (5가지 실행 엔진) |
| **ADMIN** | 시스템 관리 (10개 관리 탭) |
| **Screen Editor** | 로우코드 UI 빌더 (15개 컴포넌트, 6탭 편집기) |

### 1.2 시스템 규모

| 항목 | 규모 |
|------|------|
| 백엔드 API 엔드포인트 | 60+ |
| 프론트엔드 페이지 | 20+ |
| DB 마이그레이션 | 49개 |
| DB 테이블 | 32+ |
| E2E 테스트 시나리오 | 22개 |

### 1.3 시스템 구성도

```
┌──────────────────────────────────────────────────────────────────┐
│                     Tobit SPA AI Platform                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────┐                  │
│  │  OPS (운영 질의) - 6개 모드               │                  │
│  │  구성 │ 수치 │ 이력 │ 연결 │ 문서 │ 전체  │                  │
│  │  /ops/query (단순모드) │ /ops/ci/ask (전체)│                  │
│  └───────────────────────────────────────────┘                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    CEP       │  │    DOCS      │  │  API Engine  │          │
│  │ 이벤트 처리  │  │ 문서 검색    │  │ SQL/HTTP/    │          │
│  │ 4 Triggers   │  │ BM25+pgvec   │  │ Python/WF    │          │
│  │ 5채널 알림   │  │ OPS 통합     │  │ 버전/롤백    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌───────────────────────────────┐  ┌──────────────┐           │
│  │   ADMIN (관리 - 10개 탭)     │  │Screen Editor │           │
│  │  Assets, Catalogs, Tools     │  │ 15 컴포넌트  │           │
│  │  Inspector, Regression       │  │ 6탭 편집기   │           │
│  │  Observability, Logs         │  │ AI Copilot   │           │
│  │  Explorer, Screens, Settings │  │ RBAC + Theme │           │
│  └───────────────────────────────┘  └──────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  공통 인프라                                         │      │
│  │  PostgreSQL + pgvector │ Neo4j │ Redis               │      │
│  │  Asset Registry │ JWT + RBAC │ SSE Streaming         │      │
│  └──────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. OPS 모듈

### 2.1 개요

OPS는 인프라 운영 질문에 AI로 답변하는 질의응답 시스템입니다. 6개 쿼리 모드를 제공하며, 각 모드별 전용 실행기가 데이터를 조회·가공하여 답변을 생성합니다.

### 2.2 쿼리 모드

| UI 라벨 | 백엔드 모드 | 엔드포인트 | 설명 |
|---------|------------|-----------|------|
| 전체 (기본) | `all` | `POST /ops/ci/ask` | 모든 모드 통합 오케스트레이션 |
| 구성 | `config` | `POST /ops/query` | CI 구성 정보 조회 |
| 수치 | `metric` | `POST /ops/query` | 성능 메트릭 조회 |
| 이력 | `hist` | `POST /ops/query` | 이벤트/변경 이력 조회 |
| 연결 | `graph` | `POST /ops/query` | 서비스/장비 관계도 (Neo4j) |
| 문서 | `document` | `POST /ops/query` | 문서 검색 (하이브리드) |

프론트엔드 기본 모드는 `all`(전체)이며, 전체 모드만 `/ops/ci/ask` 엔드포인트를 사용합니다. 나머지 5개 모드는 `/ops/query`에 `mode` 파라미터로 분기합니다.

### 2.3 라우팅 구조

```
사용자 질문
    ↓
프론트엔드 모드 선택
    ├─ "전체" 모드 → POST /ops/ci/ask
    └─ 기타 모드   → POST /ops/query { mode, question }
                        ↓
                   handle_ops_query() 디스패처
                        ├─ config   → run_config_executor()  (CI DB 직접 조회)
                        ├─ metric   → run_metric()           (execute_universal)
                        ├─ hist     → run_hist()             (execute_universal)
                        ├─ graph    → run_graph()            (execute_universal)
                        └─ document → run_document()         (DocumentSearchService)
```

### 2.4 CI Orchestrator

전체(all) 모드에서 사용되는 CI Orchestrator는 복잡한 운영 질문을 4단계로 처리합니다.

```
사용자 질문 → Planner LLM → Validator → Stage Executor → Response Builder
                ↓              ↓             ↓                ↓
           의도 파악        계획 검증     Tool 실행         답변 생성
           Plan 생성       Policy 적용    DB/Graph 조회     블록 조립
```

**Planner LLM**: 질문의 의도(LOOKUP, AGGREGATE, GRAPH 등)를 파악하고 실행 계획 생성
**Validator**: CI 존재 여부, 그래프 확장 깊이 제한, 타임아웃 설정 등 정책 적용
**Stage Executor**: route_plan → validate → execute → compose → present 5단계 실행
**Response Builder**: TextBlock, TableBlock, ChartBlock, GraphBlock 등으로 답변 구성

### 2.5 주요 백엔드 엔드포인트

| 엔드포인트 | 용도 |
|-----------|------|
| `POST /ops/ci/ask` | CI Orchestrator 통합 질의 |
| `POST /ops/query` | 모드별 단순 질의 |
| `GET /ops/observability/kpis` | KPI 데이터 조회 |
| `POST /ops/rca/analyze-trace` | Root Cause Analysis |
| `POST /ops/golden-queries` | 회귀 테스트 Golden Query |
| `POST /ops/ui-actions` | Screen UI 액션 실행 |

### 2.6 부가 기능

- **RCA (Root Cause Analysis)**: 실패한 트레이스를 분석하여 원인 가설을 순위별로 제시
- **Regression Watch**: Golden Queries 기반 회귀 테스트 자동화 (PASS/WARN/FAIL)
- **Debug/Rollback**: 에러/느린 스텝 진단, 원본 payload 재실행

---

## 3. CEP 모듈

### 3.1 개요

CEP(Complex Event Processing)는 실시간 이벤트를 감시하고, 조건 충족 시 알림이나 API 호출 등 자동화된 동작을 실행하는 시스템입니다.

### 3.2 Trigger-Action 구조

```
Trigger (조건 감지) → Evaluator (조건 체크) → Action (동작 실행)

예시:
  CPU > 80%           85% > 80%? ✓        Slack 알림 전송
  매 5분 스케줄       cron 매칭? ✓         상태 점검 API 호출
  에러 이벤트 수신    severity=critical? ✓  PagerDuty 알림
  이상치 감지         Z-Score > 3? ✓       경고 알림
```

### 3.3 4가지 Trigger 유형

| 유형 | 용도 | 구현 |
|------|------|------|
| **schedule** | 주기적 작업 실행 | Cron 표현식 기반, 스케줄러 루프가 5초마다 체크 |
| **metric** | 메트릭 임계점 감시 | HTTP 엔드포인트 폴링, 값 추출 후 연산자 비교 (>, <, >=, <=, ==) |
| **event** | 외부 이벤트 반응 | 복합 조건 평가 (AND/OR/NOT), 단일 조건도 지원 |
| **anomaly** | 통계적 이상치 감지 | Z-Score, IQR, EMA 3가지 알고리즘 |

**Anomaly Detection 알고리즘**:
- **Z-Score**: 표준편차 기반 (기본 임계값 3σ, 최소 2개 샘플)
- **IQR**: 사분위 범위 기반 (기본 배수 1.5, 최소 4개 샘플)
- **EMA**: 지수이동평균 기반 (기본 α=0.3, 최소 2개 샘플)

### 3.4 알림 시스템 (5채널)

| 채널 | 프로토콜 | 재시도 |
|------|----------|--------|
| **Slack** | Incoming Webhook | 지수 백오프 |
| **Email** | SMTP | 지수 백오프 |
| **SMS** | Twilio API | 지수 백오프 |
| **Webhook** | HTTP POST | 지수 백오프 |
| **PagerDuty** | Events API v2 | 지수 백오프 |

재시도 정책: 1s → 2s → 4s → 8s (최대 4회 재시도, 총 5회 시도)

### 3.5 스케줄링 및 운영

- **Scheduler**: Schedule, Metric, Notification 3개 루프 관리
- **Leader Election**: PostgreSQL Advisory Lock으로 중복 실행 방지
- **Metric Polling**: Semaphore 기반 동시성 제어, 규칙별 개별 poll_interval
- **Snapshot/Telemetry**: Metric polling 상태 주기적 저장, Dashboard 위젯 연동

### 3.6 주요 엔드포인트 (36개)

| 그룹 | 주요 엔드포인트 |
|------|----------------|
| Rules | `GET/POST /cep/rules`, `PUT /cep/rules/{id}`, `POST /cep/rules/form` |
| Execution | `POST /cep/rules/{id}/simulate`, `POST /cep/rules/{id}/trigger` |
| Events | `GET /cep/events`, `POST /cep/events/{id}/ack`, `GET /cep/events/stream` |
| Notifications | `GET/POST /cep/notifications`, `POST /cep/channels/test` |
| Scheduler | `GET /cep/scheduler/status`, `GET /cep/scheduler/metric-polling` |
| Anomaly | `GET /cep/rules/{id}/anomaly-status` |

---

## 4. DOCS 모듈

### 4.1 개요

DOCS는 다양한 형식의 문서를 업로드, 처리, 검색하는 문서 관리 시스템입니다. BM25 + pgvector 하이브리드 검색으로 텍스트와 의미 기반 검색을 동시에 지원합니다.

### 4.2 처리 흐름

```
문서 업로드 → 파일 저장 → 텍스트 추출 → 청킹 → 벡터 임베딩 → 검색 가능
(PDF/Word/    (Storage)    (OCR/파서)    (분할)   (1536-dim)
 Excel/PPT/
 Images)
```

### 4.3 검색 전략

| 검색 타입 | 엔진 | 인덱스 | 성능 |
|----------|------|--------|------|
| Text (BM25) | PostgreSQL tsvector | GIN | < 50ms |
| Vector | pgvector 1536-dim cosine | IVFFLAT | < 100ms |
| Hybrid (RRF) | 텍스트+벡터 결합 | GIN + IVFFLAT | < 150ms |

### 4.4 핵심 기능

- **하이브리드 검색**: `POST /api/documents/search` (text, vector, hybrid 모드)
- **검색 제안**: `GET /api/documents/search/suggestions` (자동완성)
- **문서 뷰어**: PDF 인증된 Blob 로드, 청크 하이라이트, 키보드 내비게이션
- **공유/내보내기**: 링크 공유 + JSON/CSV/Markdown/Text 내보내기
- **재색인/버전관리**: 청크 재생성, 재귀 CTE 기반 버전 체인

### 4.5 OPS 통합

문서 검색을 Tool Asset으로 등록하여 OPS의 "문서" 모드에서 자동 활용합니다. 사용자가 문서 관련 질문을 하면 DocumentSearchService가 하이브리드 검색을 수행하고, 결과를 LLM 컨텍스트에 포함하여 답변을 생성합니다.

---

## 5. API Engine 모듈

### 5.1 개요

API Engine은 사용자가 커스텀 API를 정의하고 실행하는 동적 API 관리 시스템입니다. 5가지 로직 타입을 지원하며, 버전 관리와 롤백을 제공합니다.

### 5.2 5가지 실행 엔진

| 로직 타입 | 설명 | 타임아웃 |
|----------|------|----------|
| **sql** | PostgreSQL SELECT/WITH 쿼리 실행, 위험 키워드 차단 | 3초 |
| **http** | 외부 HTTP API 호출, 템플릿 파라미터 치환 | 5초 |
| **python** | Python 스크립트 실행, `main(params, input_payload)` 진입점 | 5초 |
| **script** | Python/JavaScript 선택 실행, 별도 프로세스 격리 | 5초 |
| **workflow** | 다중 노드 순차 실행 (SQL + Script), 노드간 데이터 전달 | 30초 |

### 5.3 아키텍처

```
API 정의 → Logic Type 분기 → Executor 실행 → 결과 + 로그 기록
                ├─ sql      → execute_sql_api()      (PostgreSQL)
                ├─ http     → execute_http_api()      (httpx)
                ├─ python   → execute_script_api()    (subprocess)
                ├─ script   → execute_script_api()    (subprocess)
                └─ workflow → execute_workflow_api()   (순차 DAG)
```

### 5.4 보안

- **SQL 보안**: SELECT/WITH만 허용, INSERT/DELETE/DROP 등 12개 위험 키워드 차단, 세미콜론 금지, 자동 LIMIT 적용
- **Script 보안**: `runtime_policy.allow_runtime` 필수, 별도 프로세스 격리 실행, 출력 크기 제한 (1MB)
- **Runtime 제한**: IP당 60초에 120건 속도 제한

### 5.5 버전/롤백

- API 생성/수정 시 자동 버전 스냅샷 저장 (`api_definition_versions` 테이블)
- `GET /api-manager/{api_id}/versions`: 버전 히스토리 조회
- `POST /api-manager/{api_id}/rollback?version=N`: 특정 버전 롤백
- 롤백도 새 버전으로 기록되어 추적 가능

### 5.6 주요 엔드포인트

| 엔드포인트 | 용도 |
|-----------|------|
| `GET /api-manager/apis` | API 목록 조회 |
| `POST /api-manager/apis` | API 생성/수정 |
| `POST /api-manager/apis/{id}/execute` | API 실행 |
| `POST /api-manager/dry-run` | Dry-run 실행 (SQL, HTTP만 지원) |
| `GET /api-manager/{id}/versions` | 버전 히스토리 |
| `POST /api-manager/{id}/rollback` | 버전 롤백 |
| `GET /api-manager/apis/{id}/execution-logs` | 실행 로그 |
| `GET/POST /runtime/{path}` | 저장된 API 직접 호출 |

### 5.7 CEP 통합

CEP Rule의 Action Type이 `api_script`인 경우 API Engine을 호출하여 Python 스크립트를 실행할 수 있습니다.

---

## 6. ADMIN 모듈

### 6.1 개요

ADMIN은 시스템 운영, 모니터링, 설정을 관리하는 관리자 대시보드입니다. 10개 탭으로 구성됩니다.

### 6.2 탭 구조

```
Admin Dashboard (/admin)
├── OPS 지원
│   ├── Assets     - Prompt, Catalog, Policy, Tool, Screen 자산 CRUD
│   ├── Catalogs   - CI 카탈로그 관리
│   ├── Tools      - 도구 자산 관리 (database_query, http_api, graph_query 등)
│   ├── Inspector  - Trace ID 검색/상세 분석 (Plan, Execution, References)
│   └── Regression - Golden Queries 기반 회귀 테스트 (PASS/WARN/FAIL)
│
├── Screen 생성
│   └── Screens    - Screen Asset 목록/CRUD
│
├── 모니터링/로깅
│   ├── Observability - KPI (Success Rate, Failure Rate, Latency), Regression Trend
│   └── Logs          - 실행 로그, 감사 로그
│
├── DB 조회
│   └── Explorer   - PostgreSQL, Neo4j, Redis 데이터 소스 탐색
│
└── 설정
    └── Settings   - 시스템 설정 (OPS/CEP/DOCS/API/Screen/System 카테고리)
```

### 6.3 Asset Registry

시스템의 핵심 자산을 통합 관리합니다.

**자산 타입**: prompt, mapping, policy, query, source, catalog, resolver, tool, screen
**생명주기**: Draft → Published → Rollback
**엔드포인트**: `/asset-registry/assets` (CRUD + publish + rollback)
**DB 테이블**: `tb_asset` (메타데이터), `tb_asset_version` (버전 스냅샷)

### 6.4 Observability

- **KPI**: Success Rate (≥96% 목표), Failure Rate, No-data Ratio, 24h 요청 수
- **Latency**: p50, p95 백분위수
- **Regression Trend**: 최근 7일 PASS/WARN/FAIL 추이, RCA Top Causes

---

## 7. Screen Editor 모듈

### 7.1 개요

Screen Editor는 비개발자도 운영 대시보드와 조회 화면을 시각적으로 편집하고 배포할 수 있는 로우코드 UI 빌더입니다.

### 7.2 편집기 구조 (6탭)

| 탭 | 기능 |
|----|------|
| **Visual** | 드래그&드롭 컴포넌트 배치, Properties Panel, Component Tree |
| **JSON** | Screen 스키마 전체 JSON 직접 편집 |
| **Binding** | 컴포넌트 속성 ↔ 상태 데이터 바인딩 설정 |
| **Action** | 버튼 클릭 등 이벤트 → API 호출 액션 설정 |
| **Preview** | 실제 렌더링 미리보기, 뷰포트 전환 (Desktop/Tablet/Mobile) |
| **Diff** | Draft vs Published 변경점 비교 |

### 7.3 15개 UI 컴포넌트

| 카테고리 | 컴포넌트 |
|----------|----------|
| 텍스트/표시 | Text, Markdown, Badge, KeyValue, Divider |
| 입력 | Input, Form |
| 데이터 | Table (DataTable), Chart |
| 레이아웃 | Row, Column, Tabs, Accordion, Modal |
| 인터랙션 | Button |

### 7.4 레이아웃 타입 (5종)

grid, form, modal, list, dashboard

### 7.5 핵심 기능

| 기능 | 설명 |
|------|------|
| Undo/Redo | 50 히스토리, Ctrl+Z/Shift+Z |
| Copy/Paste | 깊은 복제 + ID 재생성 |
| AI Copilot | 자연어 → JSON Patch 생성, Apply/Discard |
| Template Gallery | 내장 템플릿 + 발행된 화면 복제 |
| RBAC | screen:create/edit/publish/rollback/delete 5개 권한 |
| Theme | Light/Dark/Brand 3가지 프리셋 |
| Expression Engine | 재귀 하강 파서, 화이트리스트 함수 |
| SSE Streaming | 실시간 데이터 바인딩, 자동 재연결 |
| Publish Gate | 4-step 검증 후 배포 |

### 7.6 Screen Runtime

```
Screen Asset JSON → UIScreenRenderer
    ├─ Binding Engine: {{state.xxx}} → 실제 값 치환
    ├─ Action Executor: 버튼 클릭 → /ops/ui-actions API 호출
    ├─ SSE Manager: 실시간 데이터 스트림
    └─ Direct API: 컴포넌트별 REST API 직접 호출
```

---

## 8. 시스템 상관관계

### 8.1 데이터 흐름

```
OPS 질의     → PostgreSQL/Neo4j 조회, Asset Registry 참조, Execution Trace 기록
CEP 이벤트   → Rule 평가, 5채널 알림, API Engine 연동 (api_script Action)
API Engine   → SQL/HTTP/Python/Workflow 실행, 로그 기록, 캐싱
Screen Editor → Asset Registry 저장, /ops/ui-actions API 호출, SSE 스트림
DOCS 검색    → BM25+pgvector 하이브리드, OPS Tool Asset으로 통합
Admin 설정   → Settings DB 저장, Audit Log 기록
```

### 8.2 공통 인프라

| 인프라 | 용도 |
|--------|------|
| **PostgreSQL + pgvector** | 메인 DB, 벡터 검색 (1536-dim 임베딩) |
| **Neo4j** | 서비스/장비 간 관계 그래프 |
| **Redis** | 캐싱, CEP 분산 상태 관리, Pub/Sub |
| **JWT + RBAC** | 인증, 역할 기반 권한 (5개 API Key 스코프) |
| **Asset Registry** | 9가지 자산 타입 통합 관리 (Draft → Published → Rollback) |
| **SSE** | Server-Sent Events 실시간 데이터 스트리밍 |

---

## 9. 핵심 설계 패턴

| 패턴 | 적용 모듈 | 설명 |
|------|----------|------|
| **Trigger-Action** | CEP | 조건 감지 → 자동 동작 실행 |
| **Stage-based Execution** | OPS | route → validate → execute → compose → present |
| **Asset Registry** | 공통 | 9가지 자산 타입의 버전 관리 (Draft → Published → Rollback) |
| **Schema-first** | Screen Editor | JSON Schema V1이 편집기/런타임/검증의 단일 진실 원천 |
| **Runtime Engine** | API Engine | Logic Type 분기 → 전용 Executor 실행 → 로그 기록 |
| **Leader Election** | CEP | PostgreSQL Advisory Lock으로 다중 인스턴스 중복 방지 |

---

## 10. 기술 스택

### 10.1 백엔드

| 카테고리 | 라이브러리 |
|----------|-----------|
| Web Framework | FastAPI, Uvicorn |
| ORM | SQLModel, Alembic (마이그레이션) |
| DB Driver | psycopg (PostgreSQL), neo4j, redis |
| LLM | LangGraph, LangChain, OpenAI SDK |
| SSE | sse-starlette |
| HTTP Client | httpx |
| 문서 처리 | python-docx, pypdf |
| 인증 | python-jose (JWT), passlib (bcrypt) |
| 스케줄러 | croniter |
| 스트림 처리 | Bytewax |
| 테스트 | pytest, pytest-asyncio |

### 10.2 프론트엔드

| 카테고리 | 라이브러리 |
|----------|-----------|
| Framework | Next.js 16, React 19, TypeScript |
| UI | shadcn/ui, Radix UI, Tailwind CSS v4 |
| 상태 관리 | TanStack Query v5, Zustand |
| 시각화 | React Flow, Recharts, AG Grid |
| 코드 편집 | Monaco Editor |
| PDF | react-pdf, pdfjs-dist |
| E2E 테스트 | Playwright |

### 10.3 아키텍처 레이어

```
Frontend (Next.js App Router)
    │ REST API / SSE
    ▼
Backend (FastAPI)
    ├─ Router Layer (API 엔드포인트)
    ├─ Service Layer (비즈니스 로직)
    ├─ CRUD Layer (데이터 접근)
    ├─ LLM Orchestrator (LangGraph)
    ├─ CEP Scheduler (asyncio)
    └─ API Engine Executors
    │
    ├──────────┼──────────┐
    ▼          ▼          ▼
PostgreSQL   Neo4j     Redis
+ pgvector  (Graph)   (Cache)
```

---

## 11. 요약

| 모듈 | 핵심 기능 | 상태 |
|------|----------|------|
| **OPS** | 6개 쿼리 모드, CI Orchestrator, RCA, Regression Watch | 운영 중 |
| **CEP** | 4가지 Trigger, 5채널 알림, ML 이상 탐지 | 운영 중 |
| **DOCS** | BM25+pgvector 하이브리드 검색, OPS 통합 | 운영 중 |
| **API Engine** | 5가지 실행 엔진, 버전/롤백, 캐싱 | 운영 중 |
| **ADMIN** | 10개 관리 탭, Asset Registry, Observability | 운영 중 |
| **Screen Editor** | 15개 컴포넌트, 6탭 편집기, AI Copilot, RBAC | 운영 중 |

**시스템 특징**:
- AI 기반 질의응답 (Planner LLM, AI Copilot)
- 로우코드 화면 편집/배포 (Screen Editor)
- 실시간 이벤트 처리 및 자동 알림 (CEP)
- 동적 API 정의/실행 (API Engine)
- 전체 실행 트레이스 및 감사 로그
- Asset Registry를 통한 자산 생명주기 관리
- ML 기반 이상 탐지 (Z-Score, IQR, EMA)

---

## 12. 용어 정의

| 용어 | 설명 |
|------|------|
| **CI** | Configuration Item - 구성 항목 (서버, 장비, 네트워크 등) |
| **CEP** | Complex Event Processing - 복합 이벤트 처리 |
| **Asset** | 재사용 가능한 시스템 리소스 (Prompt, Tool, Screen 등) |
| **Trace** | 요청부터 응답까지의 전체 실행 기록 |
| **Golden Query** | 회귀 테스트용 기준 쿼리 |
| **RCA** | Root Cause Analysis - 원인 분석 |
| **pgvector** | PostgreSQL 벡터 확장 (고차원 임베딩 검색) |
| **RRF** | Reciprocal Rank Fusion - 다중 검색 결과 결합 |
| **BM25** | 전문 검색 알고리즘 (PostgreSQL tsvector 기반) |
| **RBAC** | Role-Based Access Control - 역할 기반 접근 제어 |

---

## 13. 관련 문서

| 문서 | 설명 |
|------|------|
| [BLUEPRINT_OPS_QUERY.md](BLUEPRINT_OPS_QUERY.md) | OPS 쿼리 시스템 상세 설계 |
| [BLUEPRINT_CEP_ENGINE.md](BLUEPRINT_CEP_ENGINE.md) | CEP 엔진 상세 설계 |
| [BLUEPRINT_API_ENGINE.md](BLUEPRINT_API_ENGINE.md) | API Engine 상세 설계 |
| [BLUEPRINT_SCREEN_EDITOR.md](BLUEPRINT_SCREEN_EDITOR.md) | Screen Editor 상세 설계 |
| [USER_GUIDE_OPS.md](USER_GUIDE_OPS.md) | OPS 사용자 가이드 |
| [USER_GUIDE_CEP.md](USER_GUIDE_CEP.md) | CEP 사용자 가이드 |
| [USER_GUIDE_API.md](USER_GUIDE_API.md) | API Manager 사용자 가이드 |
| [USER_GUIDE_SCREEN_EDITOR.md](USER_GUIDE_SCREEN_EDITOR.md) | Screen Editor 사용자 가이드 |

---

**버전**: 3.0
**문서 위치**: `docs/SYSTEM_ARCHITECTURE_REPORT.md`
