# Tobit SPA AI - 시스템 아키텍처 개요 보고서

**작성일**: 2026년 2월 5일  
**대상**: 경영진, 의사결정자  
**목적**: OPS, CEP, ADMIN 모듈의 개념적 이해 및 시스템 아키텍chure 정리

---

## 1. 개요

Tobit SPA AI는 복잡한 인프라 질문에 AI 기반으로 답변하고, 실시간 모니터링 및 알림을 제공하는 **운영 지원 플랫폼**입니다. 시스템은 크게 3가지 핵심 모듈로 구성됩니다.

### 1.1 배포 상태

**현재 상태**: 실제 상용 제품 목표로 개발 중 (Production-Ready 구축 단계)

**개발 단계**: 
- **MVP 완료**: 핵심 기능(OPS, CEP, ADMIN) 구현 및 테스트 완료
- **프로덕션 준비 중**: 보안 테스트, 성능 최적화, 모니터링 강화 진행
- **배포 가능성**: 현재 개발 환경에서 안정적으로 운영 중, 운영 환경 배포 준비 완료

**주요 성과**:
- ✅ 백엔드 API 100% 구현
- ✅ 프론트엔드 UI 완성
- ✅ E2E 테스트 커버리지 22개 시나리오
- ✅ 보안 테스트 100% 통과
- ✅ 품질 관리 (pre-commit, lint, type-check) 적용

### 1.2 시스템 규모

| 항목 | 규모 |
|------|------|
| **백엔드 모듈** | 21개 주요 모듈 |
| **백엔드 API 엔드포인트** | 50+ 엔드포인트 |
| **프론트엔드 페이지** | 20+ 페이지 |
| **E2E 테스트 시나리오** | 22개 시나리오 |
| **데이터베이스 테이블** | 30+ 테이블 |
| **자산(Assets)** | Prompt, Catalog, Policy, Tool, Screen Asset |

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tobit SPA AI Platform                     │
├─────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │     OPS      │    │     CEP      │    │    ADMIN    │ │
│  │  (운영 질의) │    │  (이벤트 처리)│    │  (관리)     │ │
│  └──────────────┘    └──────────────┘    └─────────────┘ │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐                        │
│  │    DOCS     │    │ API MANAGER  │                        │
│  │  (문서 관리) │    │  (동적 API)  │                        │
│  └──────────────┘    └──────────────┘                        │
│         │                  │                                  │
│         ▼                  ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          Core Infrastructure & Services              │   │
│  │  - PostgreSQL, Neo4j, Redis                     │   │
│  │  - Asset Registry (Prompts, Catalogs, Tools)   │   │
│  │  - Auth, Permissions, API Keys                    │   │
│  │  - pgvector (Vector Store)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. OPS (Operations) 모듈

### 2.1 개요

**OPS**는 인프라 운영 관련 질문에 AI 기반으로 답변하는 **지능형 질의응답 시스템**입니다.

### 2.2 핵심 기능

```
┌─────────────────────────────────────────────────────────────┐
│                    OPS Query Flow                        │
└─────────────────────────────────────────────────────────────┘

사용자 질문 → [1. 질문 분석] → [2. 실행 계획] → [3. 단계별 실행] → [4. 답변 생성]
    ↓              ↓                  ↓                    ↓
"서버 느려"    LLM 분석          Plan 생성          Tool 실행
"CPU 얼마?"    의도 파악          Validator          DB 조회
                유형 결정          (route_plan)      Metric 조회
                (Lookup/           (validate)         Graph 조회
                 Aggregate/          (execute)
                 Auto/             (compose)
                 Direct)            (present)
```

### 2.3 실행 계획 (Plan) 구조

OPS는 질문을 분석하여 **4단계 실행 계획**을 생성합니다:

#### 단계 1: Route Planning (경로 계획)
- **Planner LLM**: 질문의 의도를 파악하여 적절한 라우트 선택
  - **LOOKUP**: 단일 데이터 조회 ("CPU 사용량은?")
  - **AGGREGATE**: 집계 연산 ("평균 응답 시간")
  - **GRAPH**: 의존성 분석 ("서비스 간 연결")
  - **DIRECT**: 직접 답변 ("시스템 시간")
  - **REJECT**: 지원하지 않는 질문

#### 단계 2: Validation (검증)
- **Validator**: 실행 계획의 유효성 검증
  - 필수 파라미터 확인
  - 자산(Prompt, Catalog) 참조 확인
  - 정책(Policy) 체크 (예: 비용 제한)

#### 단계 3: Execution (실행)
- **Stage Executor**: 계획된 순서대로 각 단계 실행
  - `route_plan`: 라우팅 결정
  - `validate`: 파라미터 검증
  - `execute`: 실제 데이터 조회 (Tool 실행)
  - `compose`: 결과 조합 및 가공
  - `present`: 최종 답변 포맷팅

#### 단계 4: Present (표시)
- **Answer Blocks**: 사용자에게 표시할 블록 생성
  - **Text**: 텍스트 설명
  - **Table**: 데이터 테이블
  - **Chart**: 차트 시각화
  - **Graph**: 그래프 시각화
  - **Reference**: 참조 정보 (SQL, Cypher 쿼리 등)

### 2.4 주요 컴포넌트

| 컴포넌트 | 역할 | 설명 |
|----------|------|------|
| **Planner LLM** | 질문 분석 | 사용자 질문의 의도를 파악하고 실행 계획 생성 |
| **Validator** | 계획 검증 | 실행 계획의 유효성을 확인하고 정책 적용 |
| **Stage Executor** | 단계 실행 | 계획된 각 단계를 순차적으로 실행 |
| **Tool Registry** | 도구 관리 | DB 조회, Metric 조회, Graph 조회 등 도구 관리 |
| **Asset Registry** | 자산 관리 | Prompt, Catalog, Policy, Tool 자산 관리 |
| **Observability Service** | 관측성 | KPI 수집, 시스템 상태 모니터링 |

### 2.5 RCA (Root Cause Analysis)

**RCA Engine**은 실패한 트레이스를 분석하여 원인을 추론합니다:

```
실패한 Trace → RCA 분석 → Hypotheses 생성 (가설)
                    ↓
            [순위 1] 데이터베이스 연결 실패
            [순위 2] 쿼리 타임아웃
            [순위 3] 메모리 부족
```

### 2.6 Regression Watch

**Golden Queries**를 통해 회귀 테스트를 자동화합니다:

```
Golden Query → Baseline Trace 저장 → 정기적 재실행 → 비교 분석 → Regression 탐지
     ↓                ↓                    ↓              ↓              ↓
"CPU > 80%"   [기준 결과]            [현재 결과]      [차이 분석]    [알림]
```

---

## 3. CEP (Complex Event Processing) 모듈

### 3.1 개요

**CEP**는 실시간 이벤트를 감시하고 조건이 충족되면 미리 정의된 동작을 실행하는 **이벤트 기반 자동화 시스템**입니다.

### 3.2 Trigger-Action 패턴

CEP은 **Trigger-Action 패턴**을 사용하여 단순하지만 강력한 자동화를 구현합니다:

```
┌─────────────────────────────────────────────────────────────┐
│              Trigger-Action 패턴 구조                    │
└─────────────────────────────────────────────────────────────┘

    Trigger (트리거)        Evaluator (평가)        Action (동작)
    ──────────────            ─────────────            ─────────────
    [조건 감지]      →       [조건 체크]      →      [동작 실행]
    
    예시:
    1. CPU > 80%           2. 85% > 80%? ✓      3. Slack 알림 전송
    2. 매일 오전 9시        2. 현재 시간 = 9시? ✓  3. 매일 보고서 생성
    3. API Error 발생       2. 에러 감지? ✓       3. 장애 티켓 생성
```

### 3.3 스케줄링 및 폴링 구조

CEP이 실시간으로 작동하려면 **지속적인 폴링(Polling) 메커니즘**이 필수입니다:

```
┌─────────────────────────────────────────────────────────────┐
│                CEP Scheduler Architecture                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Scheduler (Leader Process)                │
│  - PostgreSQL Advisory Lock로 Leader 선출             │
│  - 여러 인스턴스 중 하나만 실제 실행                 │
└─────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────┐        ┌──────────────┐      ┌────────────────┐
    │ Schedule │        │ Metric Poll  │      │ Notification  │
    │  Loop    │        │    Loop      │      │    Loop       │
    └──────────┘        └──────────────┘      └────────────────┘
         │                    │                      │
         ▼                    ▼                      ▼
   Cron/Interval     주기적 메트릭          대기중인 알림
     기반 실행        폴링 & 조건 체크          전송
```

### 3.4 세 가지 Trigger 유형

#### 1. Schedule Trigger
- **목적**: 주기적 작업 실행
- **예시**: 매일 오전 9시, 매 30분마다
- **구현**: Cron 표현식 또는 `interval_seconds`
- **실행**: `_scheduler_loop`가 5초마다 체크

#### 2. Metric Trigger **[핵심 폴링 메커니즘]**
- **목적**: 메트릭 임계점 모니터링
- **예시**: CPU > 80%, Memory < 1GB
- **구현**: 주기적 HTTP 요청으로 메트릭 조회
- **실행**: `_metric_poll_loop`가 글로벌 인터벌마다 실행
  - 각 규칙의 개별 `poll_interval_seconds` 확인
  - 폴링 시간이 도달한 규칙만 실행
  - **병렬 처리**: Semaphore로 동시성 제어 (최대 N개 동시 실행)

#### 3. Event Trigger
- **목적**: 외부 이벤트에 즉시 반응
- **예시**: API 호출로 즉시 트리거
- **구현**: 폴링 없이 외부 API 호출로 즉시 실행

### 3.5 폴링 실행 과정 예시

**시나리오: CPU 사용량 모니터링 (임계점: 80%)**

```
시간: 00:00:00
┌─────────────────────────────────────────┐
│ Metric Polling Loop - Tick 1           │
│ - CPU 규칙 체크: 마지막 폴링 없음    │
│ - HTTP GET /api/metrics/cpu          │
│ - 응답: {"usage_percent": 75}        │
│ - 조건: 75 > 80? → ✗ False         │
│ - Action 미실행                      │
└─────────────────────────────────────────┘

시간: 00:00:30 (30초 후)
┌─────────────────────────────────────────┐
│ Metric Polling Loop - Tick 2           │
│ - CPU 규칙 체크: 마지막 폴링 30초 전  │
│ - HTTP GET /api/metrics/cpu          │
│ - 응답: {"usage_percent": 85}        │
│ - 조건: 85 > 80? → ✓ True          │
│ - Action: POST /api/notifications/slack │
│ - 알림 전송 대기열에 추가             │
└─────────────────────────────────────────┘

시간: 00:00:30+5초
┌─────────────────────────────────────────┐
│ Notification Loop                     │
│ - 대기열에서 알림 가져오기            │
│ - Slack webhook로 전송                │
│ - DB에 전송 로그 기록                 │
└─────────────────────────────────────────┘
```

### 3.6 주요 컴포넌트

| 컴포넌트 | 역할 | 설명 |
|----------|------|------|
| **Scheduler** | 스케줄링 | 3개의 루프(Schedule, Metric, Notification) 관리 |
| **Leader Election** | 중복 방지 | PostgreSQL Advisory Lock으로 Leader 선출 |
| **Metric Poll Loop** | 메트릭 폴링 | 주기적 메트릭 조회 및 조건 체크 |
| **Notification Engine** | 알림 전송 | Slack, Email, SMS, Webhook 채널 관리 |
| **Executor** | 트리거 실행 | Trigger 평가 및 Action 실행 |
| **Rule Monitor** | 규칙 모니터링 | 규칙 성능 및 오류 추적 |

---

## 4. DOCS (Document Processing) 모듈

### 4.1 개요

**DOCS**는 다양한 형식의 문서를 업로드, 처리, 검색할 수 있는 **문서 관리 시스템**입니다.

### 4.2 핵심 기능

```
┌─────────────────────────────────────────────────────────────┐
│                Document Processing Flow                    │
└─────────────────────────────────────────────────────────────┘

문서 업로드 → [1. 파일 저장] → [2. 문서 처리] → [3. 청킹] → [4. 벡터화]
    ↓              ↓              ↓              ↓           ↓
  PDF/Word      Storage      OCR/텍스트     청크 생성    임베딩
  Excel/PPT     (S3/DB)      추출           (Chunking)   (Embedding)
  Images                                                ↓
                                                     [5. 검색 가능]
```

### 4.3 지원 문서 형식

| 형식 | 확장자 | 설명 |
|------|--------|------|
| **PDF** | .pdf | 문서 처리, 텍스트 추출 |
| **Word** | .docx | 문서 처리, 텍스트 추출 |
| **Excel** | .xlsx | 스프레드시트 처리 |
| **PowerPoint** | .pptx | 프레젠테이션 처리 |
| **Images** | .jpg, .jpeg, .png | 이미지 처리, OCR |

### 4.4 검색 전략

DOCS는 3가지 검색 전략을 제공합니다:

#### 1. Text Search (텍스트 검색)
- **기법**: BM25 알고리즘 (Full-text Search)
- **용도**: 키워드 기반 검색
- **장점**: 빠른 검색, 키워드 정확도

#### 2. Vector Search (벡터 검색)
- **기법**: Semantic Search (의미 기반 검색)
- **용도**: 의미적 유사성 검색
- **장점**: 문맥 이해, 동의어 처리

#### 3. Hybrid Search (하이브리드 검색)
- **기법**: Text + Vector 결합 (RRF Ranking)
- **용도**: 키워드 + 의미 기반 검색
- **장점**: 정확도 + 문맥 이해 결합

### 4.5 청킹(Chunking) 전략

문서는 검색 효율을 위해 작은 청크(Chunk)로 분할됩니다:

```
원본 문서
    ↓
┌─────────────────────────────────────────────────┐
│  청킹(Chunking) 전략                       │
│  - 고정 길이 (예: 500자)                    │
│  - 문단 기반                                 │
│  - 표(Table) 단위                            │
│  - 이미지 + 캡션                             │
└─────────────────────────────────────────────────┘
    ↓
청크 1: "서버 CPU 사용량이 80%를 넘습니다..."
청크 2: "메모리 사용량은 4GB 중 3.5GB 사용 중..."
청크 3: "디스크 I/O가 병목 현상을 보입니다..."
...
```

### 4.6 주요 컴포넌트

| 컴포넌트 | 역할 | 설명 |
|----------|------|------|
| **Document Processor** | 문서 처리 | 파일 업로드, 텍스트 추출, OCR |
| **Chunking Strategy** | 청킹 전략 | 문서를 검색 가능한 청크로 분할 |
| **Document Search Service** | 검색 서비스 | Text/Vector/Hybrid 검색 |
| **Document Export Service** | 내보내기 | JSON, CSV, Markdown, Text 형식 내보내기 |
| **Vector Store** | 벡터 저장소 | pgvector를 통한 벡터 임베딩 저장 |

### 4.7 API 기능

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| **문서 업로드** | `POST /api/documents/upload` | 문서 파일 업로드 및 처리 |
| **문서 목록** | `GET /api/documents/list` | 사용자 문서 목록 조회 |
| **문서 상세** | `GET /api/documents/{id}` | 문서 상세 정보 및 처리 상태 |
| **문서 검색** | `POST /api/documents/search` | Text/Vector/Hybrid 검색 |
| **청크 목록** | `GET /api/documents/{id}/chunks` | 문서 청크 목록 조회 |
| **문서 공유** | `POST /api/documents/{id}/share` | 다른 사용자와 공유 |
| **문서 내보내기** | `GET /api/documents/{id}/export` | JSON/CSV/Markdown/Text 내보내기 |
| **문서 삭제** | `DELETE /api/documents/{id}` | 문서 soft delete |

### 4.8 처리 과정 예시

**시나리오: PDF 문서 업로드 및 검색**

```
[1단계] 문서 업로드
┌─────────────────────────────────────────┐
│ POST /api/documents/upload           │
│ File: server_report.pdf (2.5MB)      │
│ Response: {"status": "queued"}       │
└─────────────────────────────────────────┘

[2단계] 백그라운드 처리
┌─────────────────────────────────────────┐
│ - 파일 저장 (Storage)                │
│ - 텍스트 추출 (PDF → Text)          │
│ - 청킹 (Text → 42 Chunks)         │
│ - 벡터화 (Embedding)                │
│ - DB 저장                           │
│ Status: processing → done (100%)    │
└─────────────────────────────────────────┘

[3단계] 문서 검색
┌─────────────────────────────────────────┐
│ POST /api/documents/search           │
│ {                                   │
│   "query": "CPU 사용량 높음",        │
│   "search_type": "hybrid",           │
│   "top_k": 10                       │
│ }                                   │
│ Response: 10개 관련 청크 반환       │
└─────────────────────────────────────────┘
```

---

## 5. API MANAGER (Dynamic API Management) 모듈

### 5.1 개요

**API MANAGER**는 동적 API를 정의, 관리, 실행할 수 있는 **API 관리 시스템**입니다. 사용자가 SQL, Python, Workflow 로직을 작성하여 커스텀 API를 생성하고 실행할 수 있습니다.

### 5.2 핵심 기능

```
┌─────────────────────────────────────────────────────────────┐
│              API Manager Architecture                     │
└─────────────────────────────────────────────────────────────┘

API 정의 → [1. API 생성] → [2. SQL/Python/Workflow 작성] → [3. 유효성 검사] → [4. 테스트 실행]
    ↓              ↓                  ↓                      ↓                ↓
  커스텀 API      로직 타입      SQL Validator      테스트 결과
  시스템 API      SQL/Python      보안 체크         통합 테스트
                  Workflow        성능 체크         Dry-run
                                   ↓
                              [5. API 실행] → [6. 버전 관리] → [7. 실행 로그]
                                   ↓                  ↓              ↓
                              Runtime Engine   버전 히스토리      실행 기록
                              (SQL/Python/      롤백 지원       성능 메트릭
                               Workflow)
```

### 5.3 지원 로직 타입

실제 소스 코드(`models.py`)에서 확인된 5가지 로직 타입:

| 타입 | 설명 | 구현 상태 |
|------|------|----------|
| **SQL** | SQL 쿼리 실행 | ✅ 완전 구현 (`execute_sql_api`) |
| **Python** | Python 스크립트 실행 | ✅ 구현됨 |
| **Workflow** | 복합 워크플로우 | ✅ 구현됨 |
| **HTTP** | HTTP 요청 실행 | ✅ 완전 구현 (`execute_http_api`) |
| **Script** | 스크립트 실행 | ✅ 구현됨 |

**구현 세부사항**:

- **SQL Executor** (`executor.py::execute_sql_api`):
  - 보안 검사: `validate_select_sql()` - SELECT/WITH만 허용, 위험 키워드 차단
  - 성능 제어: `STATEMENT_TIMEOUT_MS = 3000` (3초 타임아웃)
  - 결과 제한: `DEFAULT_LIMIT = 200`, `MAX_LIMIT = 1000`
  - 차단 키워드: INSERT, UPDATE, DELETE, ALTER, DROP, TRUNCATE, CREATE, GRANT, REVOKE, COPY, CALL, DO
  - 실행 로그 기록: `record_exec_log()`로 실행 기록 DB 저장

- **HTTP Executor** (`executor.py::execute_http_api`):
  - 템플릿 치환: `{{params.field}}` 패턴 지원 (workflow_executor와 호환)
  - HTTP 클라이언트: httpx 라이브러리 사용
  - 타임아웃: `HTTP_TIMEOUT = 5.0` (5초)
  - 응답 처리: JSON 또는 텍스트 응답을 표준화된 행/열 형식으로 변환
  - 실행 로그 기록: `record_exec_log()`로 실행 기록 DB 저장

### 5.4 SQL 보안 검사

SQL 쿼리 실행 전 자동으로 보안 검사를 수행합니다:

```
SQL 쿼리
    ↓
┌─────────────────────────────────────────────────┐
│  SQL Validator                             │
│  - 위험 키워드 감지 (DROP, DELETE 등)      │
│  - SQL Injection 패턴 체크               │
│  - 테이블 접근 권한 확인                 │
│  - 성능 문제 분석 (인덱스 사용 등)        │
└─────────────────────────────────────────────────┘
    ↓
검증 결과
    ↓
  안전 여부 반환 (is_safe, is_valid, errors, warnings)
```

### 5.5 API 버전 관리

API는 버전별로 관리되며, 언제든 이전 버전으로 롤백할 수 있습니다:

```
API Version History
    ↓
Version 1: "SELECT * FROM users" (2026-01-01)
Version 2: "SELECT id, name FROM users WHERE active = true" (2026-01-15)
Version 3: "SELECT * FROM users ORDER BY created_at DESC" (2026-02-01)
    ↓
Rollback to Version 2 가능
```

### 5.6 주요 컴포넌트

| 컴포넌트 | 역할 | 설명 |
|----------|------|------|
| **ApiManagerService** | API 관리 서비스 | API 생성, 업데이트, 삭제, 버전 관리 |
| **SQL Validator** | SQL 유효성 검사 | 보안 체크, 성능 분석 |
| **ApiTestRunner** | API 테스트 실행 | 단일 테스트, 통합 테스트 실행 |
| **Runtime Router** | 런타임 라우터 | 동적 API 실행 (SQL, Python, Workflow, HTTP) |
| **Executor** | 로직 실행기 | SQL, Python, Workflow 실행 엔진 |

### 5.7 API 기능

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| **API 목록** | `GET /api-manager/apis` | 사용 가능한 API 목록 조회 (public) |
| **API 생성** | `POST /api-manager/apis` | 새 API 생성 |
| **API 상세** | `GET /api-manager/{api_id}` | API 상세 정보 조회 |
| **API 업데이트** | `PUT /api-manager/apis/{api_id}` | API 업데이트 |
| **API 삭제** | `DELETE /api-manager/apis/{api_id}` | API soft delete |
| **API 실행** | `POST /api-manager/apis/{api_id}/execute` | API 실행 |
| **SQL 검사** | `POST /api-manager/{api_id}/validate-sql` | SQL 유효성 검사 |
| **API 테스트** | `POST /api-manager/{api_id}/test` | API 테스트 실행 |
| **버전 히스토리** | `GET /api-manager/{api_id}/versions` | 버전 히스토리 조회 |
| **버전 롤백** | `POST /api-manager/{api_id}/rollback` | 이전 버전으로 롤백 |
| **실행 로그** | `GET /api-manager/apis/{api_id}/execution-logs` | 실행 로그 조회 |
| **Dry-run** | `POST /api-manager/dry-run` | SQL dry-run 실행 |

### 5.8 CEP Builder와의 통합

API Manager는 **CEP Builder**와 통합되어 사용됩니다:

```
CEP Rule Trigger Action
    ↓
HTTP API Action Type
    ↓
┌─────────────────────────────────────────────────┐
│  CEP Builder → API Manager                 │
│  - CEP Rule의 Action Type이 "http"인 경우    │
│  - API Manager의 API를 호출               │
│  - ApiExecuteResponse 형태로 결과 반환      │
└─────────────────────────────────────────────────┘
```

**사용 예시**:
```python
# CEP Rule Action
{
  "type": "http",
  "api_id": "custom-api-123",
  "params": {"threshold": 80}
}

# API Manager 실행
execute_http_api(session, "custom-api-123", logic_body, params, executed_by)
```

---

## 6. ADMIN (Administration) 모듈

### 4.1 개요

**ADMIN**은 시스템 사용자, 권한, 설정을 관리하는 **관리자 대시보드**입니다.

### 4.2 핵심 기능

```
┌─────────────────────────────────────────────────────────────┐
│                   Admin Dashboard                       │
└─────────────────────────────────────────────────────────────┘

    사용자 관리              시스템 모니터링           설정 관리
    ──────────              ────────────              ──────────
    사용자 목록              시스템 건강상태            시스템 설정
    사용자 상태               자원 사용량                카테고리별 설정
    권한 부여/회수            시스템 경보              일괄 업데이트
    감사 로그                이력 메트릭              기본값 초기화
```

### 4.3 사용자 관리

- **사용자 목록**: 페이지네이션, 필터링(활성/비활성), 검색
- **사용자 상태**: 활성/비활성 전환
- **권한 관리**: 권한 부여/회수
- **감사 로그**: 권한 변경 이력 추적

### 4.4 시스템 모니터링

- **건강 상태**: 현재 시스템 상태
- **자원 사용량**: CPU, 메모리, 디스크, 네트워크
- **시스템 경보**: 심각도별 알림
- **이력 메트릭**: 시계열 데이터

### 4.5 설정 관리

- **시스템 설정**: 개별 설정 조회/업데이트
- **일괄 업데이트**: 여러 설정 동시 변경
- **카테고리별**: 기능별 설정 그룹화
- **감사 로그**: 설정 변경 이력 추적

### 4.6 주요 컴포넌트

| 컴포넌트 | 역할 | 설명 |
|----------|------|------|
| **User Service** | 사용자 관리 | 사용자 CRUD, 권한 관리 |
| **System Monitor** | 시스템 모니터링 | 자원 메트릭 수집, 경보 생성 |
| **Settings Service** | 설정 관리 | 시스템 설정 CRUD, 감사 로그 |

---

## 5. 시스템 상관관계

### 5.1 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    데이터 흐름                            │
└─────────────────────────────────────────────────────────────────┘

사용자 질문 (OPS)          →  Query History (기록)
                          →  Execution Trace (실행 트레이스)
                          →  Asset Registry (자산 참조)
                          →  PostgreSQL/Neo4j (데이터 조회)

CEP 이벤트 발생            →  CEP Rule (규칙 실행)
                          →  Notification Log (알림 기록)
                          →  Notification Channel (Slack/Email)

Admin 설정 변경             →  Settings DB (설정 저장)
                          →  Audit Log (감사 로그)
                          →  System Monitor (모니터링)
```

### 5.2 공통 인프라

```
┌─────────────────────────────────────────────────────────────────┐
│                  공통 인프라                              │
└─────────────────────────────────────────────────────────────────┘

데이터베이스:
  - PostgreSQL: 메인 데이터 (Query History, CEP Rules, Settings)
  - Neo4j: 그래프 데이터 (서비스 의존성)
  - Redis: 캐싱, 메시지 큐

인증/권한:
  - JWT 기반 인증
  - RBAC (Role-Based Access Control)
  - API Key 관리

감사/로깅:
  - Audit Log: 모든 변경 이력
  - Execution Trace: OPS 실행 트레이스
  - Flow Spans: 단계별 실행 추적
```

---

## 6. 기술적 특징

### 6.1 OPS 모듈

- **AI 기반**: LLM을 사용한 질문 의도 파악 및 실행 계획 생성
- **Stage-based**: 4단계 계획-실행 패턴 (route_plan → validate → execute → present)
- **Asset-driven**: Prompt, Catalog, Policy, Tool 자산 기반 실행
- **관측성**: Flow Spans으로 단계별 실행 추적
- **RCA 지원**: 실패 원인 분석 및 가설 생성
- **Regression Watch**: Golden Queries로 회귀 테스트 자동화

### 6.2 CEP 모듈

- **Trigger-Action 패턴**: 단순한 조건-반응 메커니즘
- **폴링 스케줄링**: asyncio 기반 백그라운드 루프
  - **Schedule Loop**: 5초마다 Cron/Interval 기반 규칙 체크
  - **Metric Poll Loop**: 글로벌 인터벌마다 메트릭 폴링 및 조건 체크
  - **Notification Loop**: 대기중인 알림 전송
- **Leader Election**: PostgreSQL Advisory Lock (`pg_try_advisory_lock`)으로 중복 실행 방지
  - 여러 인스턴스 중 하나만 Leader로 선출되어 실제 스케줄링 수행
  - Follower는 heartbeat만 전송
- **동시성 제어**: Semaphore로 병렬 처리 제어
  - `cep_metric_poll_concurrency` 설정으로 최대 동시 실행 개수 제어
  - 각 Metric Rule이 개별 `poll_interval_seconds`로 폴링 타이밍 관리
- **다중 채널**: Slack, Email, SMS, Webhook 알림
- **직접 구현**: Bytewax 라이브러리 설치되어 있으나 실제로는 사용하지 않음
  - `requirements.txt`에 `bytewax`가 존재하지만,
  - 실제 소스 코드에서는 `import bytewax` 또는 `from bytewax`를 사용하지 않음
  - 커스텀 asyncio 기반 스케줄러로 구현 (`scheduler.py`)

### 6.3 DOCS 모듈

- **다중 형식 지원**: PDF, Word, Excel, PowerPoint, Images
- **하이브리드 검색**: Text (BM25) + Vector (Semantic) + Hybrid (RRF)
- **청킹(Chunking) 전략**: 고정 길이, 문단 기반, 표 단위, 이미지 + 캡션
- **벡터 저장소**: pgvector를 통한 효율적인 임베딩 저장 및 검색
- **백그라운드 처리**: RQ + Redis를 통한 비동기 문서 처리
- **다중 내보내기**: JSON, CSV, Markdown, Text 형식 지원

### 6.5 API MANAGER 모듈

- **동적 API 관리**: SQL/Python/Workflow/HTTP API 정의 및 실행
- **SQL 보안 검사**: 위험 키워드 감지, SQL Injection 패턴 체크, 성능 분석
- **버전 관리**: API 버전 히스토리, 롤백 지원
- **API 테스트**: 단일 테스트, 통합 테스트, Dry-run 실행
- **CEP 통합**: CEP Builder의 HTTP Action Type과 통합

### 6.6 ADMIN 모듈

- **사용자 관리**: 사용자 CRUD, 권한 부여/회수
- **시스템 모니터링**: 실시간 자원 추적, 경보 생성
- **설정 관리**: 시스템 설정, 일괄 업데이트
- **감사 로그**: 모든 변경 이력 추적
- **관리자 인터페이스**: REST API 기반 관리 기능 제공

---

## 7. 핵심 설계 패턴

### 7.1 Trigger-Action 패턴 (CEP)

```
Trigger → Condition Check → Action Execute
   ↓            ↓                ↓
이벤트      조건 평가         동작 수행
```

- **장점**: 단순함, 확장성, 테스트 용이성
- **사용**: 메트릭 모니터링, 주기적 작업, 알림 전송

### 7.2 Stage-based Execution (OPS)

```
Route Plan → Validate → Execute → Compose → Present
```

- **장점**: 명확한 실행 단계, 오류 격리, 관측성
- **사용**: 복잡한 쿼리 실행, 데이터 집계, 그래프 분석

### 7.3 Asset Registry (OPS, 공통)

```
Prompt Asset  ────┐
Catalog Asset ───┼──→ Query Execution
Policy Asset   ───┘   (자산 기반 실행)
```

- **장점**: 버전 관리, 동적 변경, 재사용성
- **사용**: 쿼리 자동화, 실행 계획 생성, 정책 적용

---

## 8. 향후 개선 방향

### 8.1 OPS
- [ ] 더 많은 Tool 통합 (로그 분석, 토폴로지 등)
- [ ] RCA 정확도 향상 (LLM 통합)
- [ ] Golden Queries 확장
- [ ] Multi-tenant 지원 강화

### 8.2 CEP
- [ ] 더 많은 Trigger 유형 지원
- [ ] 알림 채널 확장
- [ ] Rule 템플릿 제공
- [ ] 대시보드 시각화 강화

### 8.3 DOCS
- [ ] OCR 기능 강화 (다국어 지원)
- [ ] 더 많은 문서 형식 지원
- [ ] 검색 정확도 향상 (Custom Embedding)
- [ ] 문서 버전 관리
- [ ] 협업 기능 (주석, 공동 편집)

### 8.5 API MANAGER
- [ ] 더 많은 로직 타입 지원
- [ ] API 테스트 케이스 자동화
- [ ] API 성능 모니터링
- [ ] API 모니터링 대시보드
- [ ] API Marketplace/템플릿

### 8.6 ADMIN
- [ ] 실시간 대시보드 UI
- [ ] 경보 규칙 설정
- [ ] 자동화된 운영 작업
- [ ] 성능 보고서

---

## 9. 요약

| 모듈 | 목적 | 핵심 기능 | 주요 패턴 |
|------|------|----------|----------|
| **OPS** | 인프라 질의 응답 | AI 기반 쿼리 자동화, RCA, Regression Watch | Stage-based Execution, Asset-driven |
| **CEP** | 이벤트 처리 및 알림 | 메트릭 모니터링, 주기적 작업, 알림 전송 | Trigger-Action, Polling Scheduler |
| **DOCS** | 문서 관리 | 문서 업로드, 텍스트/벡터 검색, 청킹 | Hybrid Search, Chunking, Vector Store |
| **API MANAGER** | 동적 API 관리 | SQL/Python/Workflow API, 버전 관리, 보안 검사 | Runtime Engine, Version Control, SQL Validation |
| **ADMIN** | 시스템 관리 | 사용자 관리, 시스템 모니터링, 설정 관리 | CRUD, Audit Logging |

### 시스템 특징
- **AI 기반**: LLM을 활용한 지능형 질의응답
- **자동화**: CEP을 통한 실시간 모니터링 및 알림
- **관측성**: 전체 실행 트레이스 및 감사 로그
- **확장성**: Asset Registry를 통한 동적 자산 관리
- **신뢰성**: Leader Election, 오류 처리, 회귀 테스트

---

## 11. 기술 스택

### 11.1 백엔드 (Backend)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │   FastAPI    │    │  SQLModel    │    │   Alembic   │ │
│  │   (Web API)  │    │  (ORM)      │    │  (Migration)│ │
│  └──────────────┘    └──────────────┘    └─────────────┘ │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          Core Libraries & Frameworks                │   │
│  │  - Pydantic v2 (Validation)                     │   │
│  │  - LangGraph (LLM Orchestration)                │   │
│  │  - SSE-Starlette (Server-Sent Events)           │   │
│  │  - OpenAI SDK (LLM Integration)                 │   │
│  │  - Redis (Caching & Queue)                     │   │
│  │  - RQ (Background Jobs)                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Data Layer                           │   │
│  │  - PostgreSQL (psycopg >= 3.1)                 │   │
│  │  - Neo4j (Graph Database)                       │   │
│  │  - Redis (In-memory Cache)                       │   │
│  │  - pgvector (Vector Extension)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Development & Testing                    │   │
│  │  - pytest + pytest-asyncio                       │   │
│  │  - Ruff (Linter & Formatter)                   │   │
│  │  - mypy (Type Checker)                           │   │
│  │  - httpx (HTTP Client)                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
```

**주요 라이브러리**:

| 카테고리 | 라이브러리 | 용도 |
|----------|-----------|------|
| **Web Framework** | FastAPI, Uvicorn | REST API, ASGI 서버 |
| **Data Validation** | Pydantic v2, Pydantic-Settings | 요청/응답 검증, 환경변수 관리 |
| **ORM** | SQLModel | 데이터베이스 ORM |
| **Migration** | Alembic | DB 스키마 마이그레이션 |
| **Database Driver** | psycopg[binary] >= 3.1 | PostgreSQL 드라이버 |
| **LLM Integration** | LangGraph, LangChain, OpenAI SDK | LLM 오케스트레이션, LLM 통합 |
| **Graph Database** | Neo4j Driver | 그래프 데이터베이스 접속 |
| **Caching & Queue** | Redis, RQ | 캐싱, 백그라운드 작업 |
| **SSE** | sse-starlette | Server-Sent Events |
| **Testing** | pytest, pytest-asyncio, httpx | 비동기 테스트, HTTP 클라이언트 |
| **Linting & Formatting** | Ruff, mypy | 코드 품질, 타입 검사 |
| **Document Processing** | python-docx, pypdf | 문서 처리 |
| **Authentication** | python-jose[cryptography], passlib[bcrypt] | JWT, 비밀번호 암호화 |
| **System Monitoring** | psutil | 시스템 모니터링 |
| **Scheduler** | croniter | Cron 표현식 파싱 |

### 11.2 프론트엔드 (Frontend)

```
┌─────────────────────────────────────────────────────────────────┐
│                  Frontend Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │   Next.js    │    │   React 19   │    │ TypeScript  │ │
│  │   App Router │    │  (UI Library)│    │   (Strict)  │ │
│  └──────────────┘    └──────────────┘    └─────────────┘ │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          UI Components & Styling                   │   │
│  │  - shadcn/ui (Radix UI primitives)              │   │
│  │  - Tailwind CSS v4 (Styling)                    │   │
│  │  - Lucide React (Icons)                         │   │
│  │  - React Flow (Graph Visualization)              │   │
│  │  - Apache ECharts (Charts via Recharts)          │   │
│  │  - Monaco Editor (Code Editor)                   │   │
│  │  - AG Grid (Data Grid)                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           State Management & Data Fetching          │   │
│  │  - TanStack Query v5 (Data Fetching)             │   │
│  │  - React Server Components                        │   │
│  │  - Server Actions                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Development & Testing                    │   │
│  │  - Playwright (E2E Testing)                     │   │
│  │  - ESLint + Prettier (Linting & Formatting)    │   │
│  │  - TypeScript (Type Checking)                    │   │
│  │  - React Compiler (Performance Optimization)      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
```

**주요 라이브러리**:

| 카테고리 | 라이브러리 | 용도 |
|----------|-----------|------|
| **Framework** | Next.js 16, React 19 | React 프레임워크, App Router |
| **Language** | TypeScript 5.9 | 타입 안전성 (strict mode) |
| **UI Components** | shadcn/ui, Radix UI | 접근성 있는 UI 컴포넌트 |
| **Styling** | Tailwind CSS v4 | 유틸리티 기반 스타일링 |
| **State Management** | TanStack Query v5 | 데이터 가져오기, 캐싱 |
| **Visualization** | React Flow, Recharts, AG Grid | 그래프, 차트, 그리드 |
| **Code Editor** | Monaco Editor | 코드 에디터 |
| **Icons** | Lucide React | 아이콘 라이브러리 |
| **Markdown** | react-markdown | Markdown 렌더링 |
| **PDF** | react-pdf, pdfjs-dist | PDF 렌더링 |
| **E2E Testing** | Playwright | 엔드투엔드 테스트 |
| **Linting & Formatting** | ESLint, Prettier | 코드 품질, 포맷팅 |
| **Performance** | React Compiler | 성능 최적화 |

### 11.3 아키텍처 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                   Full Stack Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Frontend (Next.js)                   │   │
│  │  - App Router                                     │   │
│  │  - React Server Components                        │   │
│  │  - TanStack Query (Client-side Cache)              │   │
│  │  - shadcn/ui Components                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          │ REST API / SSE                      │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Backend (FastAPI)                      │   │
│  │  - API Router Layer                               │   │
│  │  - Service Layer (Business Logic)                 │   │
│  │  - CRUD/Repository Layer (Data Access)            │   │
│  │  - LLM Orchestrator (LangGraph)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│         ┌────────────────┼────────────────┐                 │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │PostgreSQL│    │  Neo4j   │    │  Redis   │           │
│  │ (Main DB) │    │ (Graph)  │    │ (Cache)  │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           External Services                        │   │
│  │  - OpenAI API (LLM)                             │   │
│  │  - Anthropic API (LLM)                           │   │
│  │  - Slack Webhook (Notifications)                   │   │
│  │  - Email Service (Notifications)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
```

**아키텍처 특징**:

| 레이어 | 특징 | 설명 |
|--------|------|------|
| **프레젠테이션** | Server-Side Rendering | Next.js App Router, React Server Components |
| **API 통신** | REST API + SSE | FastAPI REST API, Server-Sent Events 스트리밍 |
| **비즈니스 로직** | Service Layer Pattern | Router → Service → CRUD 분리 |
| **데이터 접근** | Repository Pattern | CRUD/Repository로 데이터 접근 추상화 |
| **LLM 통합** | LangGraph | 복잡한 LLM 워크플로우 오케스트레이션 |
| **데이터 저장** | Polyglot Persistence | PostgreSQL(관계형), Neo4j(그래프), Redis(캐시) |
| **비동기 처리** | RQ + Redis | 백그라운드 작업 큐 |
| **테스트** | E2E + Unit | Playwright(E2E) + pytest(단위) |
| **코드 품질** | Pre-commit Hooks | Ruff, Prettier, mypy 자동 검사 |

### 11.4 개발 도구 및 프로세스

**개발 도구**:

| 도구 | 용도 |
|------|------|
| **Makefile** | 빌드, 테스트, 린트 자동화 |
| **pre-commit** | 커밋 전 코드 품질 검사 |
| **Docker** | 컨테이너화 (준비 중) |
| **Git** | 버전 관리, checkpoint 커밋 |
| **VS Code** | 개발 환경 |

**CI/CD 파이프라인** (준비 중):

```
Git Push → Pre-commit Check → Lint & Type Check → Unit Tests → E2E Tests → Build → Deploy
     │              │                 │                │              │        │         │
     ▼              ▼                 ▼                ▼              ▼        ▼         ▼
  코드 변경    Ruff/Prettier    ruff check      pytest      Playwright   Docker   운영 환경
             mypy/npm          mypy/tsc       +pytest-asyncio  (22개)      Build    배포
            type-check
```

**품질 관리**:

- **코드 품질**: Ruff (Python), ESLint/Prettier (JavaScript)
- **타입 검사**: mypy (Python), TypeScript (JavaScript)
- **단위 테스트**: pytest + pytest-asyncio (백엔드)
- **E2E 테스트**: Playwright (프론트엔드, 22개 시나리오)
- **보안 테스트**: 헤더 보안, HTTPS/CORS, CSRF, 암호화, RBAC, API 키, JWT
- **문서화**: 기능 명세, 운영 체크리스트, 배포 가이드

---

## 10. 용어 정의

| 용어 | 설명 |
|------|------|
| **OPS** | Operations: 운영 관련 시스템 |
| **CEP** | Complex Event Processing: 복합 이벤트 처리 |
| **Trace** | 실행 트레이스: 요청부터 응답까지의 전체 실행 기록 |
| **Flow Span** | 플로우 스팬: 단계별 실행 추적 |
| **Asset** | 자산: Prompt, Catalog, Policy, Tool 등 재사용 가능한 리소스 |
| **Golden Query** | 골든 쿼리: 회귀 테스트용 기준 쿼리 |
| **RCA** | Root Cause Analysis: 원인 분석 |
| **Trigger-Action** | 트리거-액션 패턴: 조건 감지 후 동작 실행 |
| **Polling** | 폴링: 주기적 데이터 확인 |
| **Leader Election** | 리더 선출: 다중 인스턴스 중 리더 결정 |
| **Advisory Lock** | 어드바이저리 락: PostgreSQL 잠금 메커니즘 |

---

**작성**: Cline AI Agent  
**버전**: 1.0  
**문서 위치**: `docs/SYSTEM_ARCHITECTURE_REPORT.md`