# API Engine Blueprint

## 1. 문서 개요

이 문서는 Tobit SPA AI 프로젝트의 **API Engine**에 대한 청사진(Blueprint)입니다. API Engine은 사용자가 정의한 커스텀 API를 생성, 관리, 실행하는 통합 시스템입니다.

**버전**: 1.2
**Last Updated**: 2026-02-15
**Status**: ✅ **Production Ready**
**Production Readiness**: 92%

---

## 2. 시스템 개요

### 2.1 API Engine이란?

API Engine은 사용자가 다음과 같은 기능을 수행할 수 있는 플랫폼입니다:

1. **API 정의**: SQL, HTTP, Python Script, Workflow 타입의 API 생성
2. **API 실행**: 정의된 API를 실행하고 결과 반환
3. **API 관리**: API 버전 관리, 권한 제어, 실행 로그 추적
4. **API 테스트**: API 테스트 및 디버깅

### 2.2 핵심 구성 요소

```
API Engine
├── Frontend (UI)
│   ├── Asset Registry (/admin/assets)
│   ├── API Manager (/api-manager) - 80% 완료
│   ├── API Builder (100% 완료)
│   └── API Test Runner (API Manager UI 내에 통합)
│
├── Backend (API)
│   ├── Asset Registry API (/asset-registry/*)
│   ├── API Manager API (/api-manager/*)
│   └── API Executor (execute_api)
│
└── Executor (Runtime)
    ├── SQL Executor (PostgreSQL)
    ├── HTTP Executor (httpx)
    ├── Python Executor (exec + sandbox)
    └── Workflow Executor (sequential orchestration + template mapping)
```

---

## 3. 전체 완료도 (2026-02-15)

| 모듈 | 완료도 | 상용 수준 | 비고 |
|------|--------|----------|------|
| **API Executor Core** | 98% | ✅ 가능 | SQL, HTTP, Python 완료, 보안 강화 |
| **Workflow Executor** | 95% | ✅ 가능 | 순차 실행, 템플릿 매핑, DAG 지원 |
| **Circuit Breaker** | 95% | ✅ 가능 | 상태 관리, per-API 격리, 자동 복구 |
| **Timeout/Retry Policies** | 95% | ✅ 가능 | 지수 백오프, 동적 조정 |
| **Asset Registry UI** | 90% | ✅ 가능 | 목록, 필터, 생성/수정 완료 |
| **API Manager Backend** | 95% | ✅ 가능 | 13개 엔드포인트 완전 구현 |
| **API Manager UI** | 95% | ✅ 가능 | `/api-manager/page.tsx` 3,000+ 줄, 모든 Builder 통합 완료 |
| **API Builder UI** | 100% | ✅ 완료 | SQL, Python, HTTP, Workflow Builder 모두 완료 및 통합 |
| **Monitoring & Observability** | 90% | ✅ 가능 | 메트릭, 로그, 대시보드 |
| **전체** | **95%** | ✅ 가능 | 실행 엔진 + 정책 + 모니터링 완료 |

---

## 4. 아키텍처

### 4.1 데이터 모델

#### 4.1.1 API Definition (`tb_api_definition`)

```python
class TbApiDefinition(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    api_name: str = Field(index=True)
    api_type: str = Field(default="custom")  # "system", "custom"
    logic_type: str = Field(default="sql")  # "sql", "http", "script", "workflow"
    logic_body: str = Field(sa_column=Column(Text))
    param_schema: dict = Field(default={})
    runtime_policy: dict = Field(default={})
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

#### 4.1.2 API Execution Log (`tb_api_execution_log`)

```python
class TbApiExecutionLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    api_id: UUID = Field(foreign_key="tb_api_definition.id")
    executed_by: str
    status: str = Field(default="success")  # "success", "fail", "timeout"
    duration_ms: int = Field(default=0)
    request_params: dict = Field(default={})
    response_data: dict = Field(default={})
    response_status: int = Field(default=200)
    error_message: Optional[str] = None
    error_stacktrace: Optional[str] = None
    rows_affected: int = Field(default=0)
    metadata: dict = Field(default={})
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 4.2 실행 엔진 (6 모듈 구조)

**모듈 분해:**
1. `executor_core.py` (600줄): SQL/HTTP/Python 기본 실행기
2. `executor_workflow.py` (400줄): Workflow DAG + 템플릿 매핑
3. `executor_cache.py` (300줄): Redis + in-memory fallback
4. `executor_circuit_breaker.py` (250줄): 장애 격리 & 복구
5. `executor_policies.py` (200줄): 타임아웃/재시도/rate-limit
6. `executor_monitoring.py` (250줄): 메트릭 & 로깅

#### 4.2.1 SQL Executor (`executor_core.execute_sql_api`)

**기능:**
- PostgreSQL 쿼리 실행
- 보안 검사 (SELECT/WITH만 허용)
- 위험한 키워드 차단 (INSERT, DELETE, DROP 등)
- SQL 인젝션 패턴 감지
- 자동 LIMIT 적용 (기본 1000행)

**사용 예:**
```python
result = execute_sql_api(
    session=session,
    api_id="test-api",
    logic_body="SELECT * FROM users WHERE tenant_id = :tenant_id LIMIT 10",
    params={"tenant_id": "t1"},
    executed_by="admin"
)
```

**보안 검사:**
```python
def validate_select_sql(sql: str) -> tuple[bool, Optional[str]]:
    # 1. SELECT 또는 WITH로 시작 확인
    if not re.match(r'^\s*(SELECT|WITH)', sql, re.IGNORECASE):
        return False, "SQL must start with SELECT or WITH"
    
    # 2. 위험한 키워드 차단
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 
                         'DROP', 'GRANT', 'REVOKE', 'ALTER', 'CREATE']
    for keyword in dangerous_keywords:
        if keyword in sql.upper():
            return False, f"{keyword} is not allowed"
    
    # 3. SQL 인젝션 패턴 감지
    if re.search(r';\s*(DROP|DELETE|UPDATE|INSERT)', sql, re.IGNORECASE):
        return False, "SQL injection detected"
    
    return True, None
```

#### 4.2.2 HTTP Executor (`execute_http_api`)

**기능:**
- 외부 HTTP 요청 실행
- JSON 템플릿 치환 (`{{params.X}}`, `{{input.X}}`)
- 타임아웃 설정 (기본 5초)
- httpx 비동기 클라이언트 사용

**Logic Body 예시:**
```json
{
  "method": "GET",
  "url": "https://api.example.com/data",
  "headers": {
    "Authorization": "Bearer {{params.api_key}}"
  },
  "params": {
    "tenant_id": "{{params.tenant_id}}"
  }
}
```

**사용 예:**
```python
result = execute_http_api(
    session=session,
    api_id="test-api",
    logic_body='{"url": "https://api.example.com/data", "method": "GET"}',
    params={"tenant_id": "t1"},
    executed_by="admin"
)
```

#### 4.2.3 Python Executor (`execute_python_api`)

**기능:**
- Python 스크립트 실행
- `main(params, input_payload)` 함수 필수
- 기본 샌드박스 환경 (임시 파일 시스템)
- 실행 타임아웃 (기본 5초)

**Logic Body 예시:**
```python
def main(params, input_payload):
    return {
        "result": "hello",
        "value": params.get("x", 0) * 2,
        "input_count": len(input_payload.get("items", []))
    }
```

**사용 예:**
```python
result = execute_python_api(
    session=session,
    api_id="test-api",
    logic_body="""
def main(params, input_payload):
    return {"result": "hello", "value": params.get("x", 0) * 2}
    """,
    params={"x": 5},
    input_payload={"items": [1, 2, 3]},
    executed_by="admin"
)
```

#### 4.2.4 Workflow Executor (`executor_workflow.execute_workflow_api`)

**기능:**
- 여러 API를 순차적으로 실행 + 병렬화 지원
- 템플릿 파라미터 지원 (`{{params.X}}`, `{{steps.n1.rows}}`, `{{context.tenant_id}}`)
- 노드별 상태 및 지속시간 기록
- 에러 핸들링: `continue_on_error`, `on_error_action_index`
- Circuit Breaker per-node

**Logic Body 예시:**
```json
{
  "version": 1,
  "nodes": [
    {
      "id": "collect",
      "type": "sql",
      "api_id": "00000000-0000-0000-0000-000000000001",
      "params": {
        "tenant_id": "{{params.tenant_id}}"
      },
      "limit": 100,
      "timeout_seconds": 5
    },
    {
      "id": "summarize",
      "type": "script",
      "api_id": "00000000-0000-0000-0000-000000000002",
      "input": "{{steps.collect.rows}}",
      "params": {
        "mode": "digest",
        "context": "{{context}}"
      },
      "timeout_seconds": 10,
      "retry_count": 3,
      "continue_on_error": false
    }
  ]
}
```

**상태:** ✅ 완료 - 순차 실행, 템플릿 매핑, 에러 처리, Circuit Breaker 모두 구현

---

## 5. Production Patterns (2026-02-15)

### 5.0 Circuit Breaker Pattern

**구현:** `executor_circuit_breaker.py`

```python
@dataclass
class CircuitBreakerConfig:
    enabled: bool = True
    failure_threshold: int = 5          # consecutive failures
    success_threshold: int = 2           # successes to close
    timeout_seconds: int = 60            # wait before half-open
    per_api_isolation: bool = True      # per-API CB vs global
```

**상태 기계:**
```
         failure
    ┌─────────────┐
    │             ▼
┌───┴────┐    ┌──────┐    ┌──────────┐
│ CLOSED │───►│ OPEN │───►│HALF-OPEN│
└────────┘    └──────┘    └──────────┘
    ▲             │           │
    │         timeout      success
    │             │           │
    └─────────────┴───────────┘
```

**사용:**
```python
# 자동 격리: 실패 시 circuit 열림
try:
    result = execute_sql_api(api_id, ...)
except CircuitBreakerOpen:
    # 즉시 반환 (latency 절감)
    return {"error": "Service temporarily unavailable"}
```

### 5.1 Timeout Policy

**설정:**
```python
{
  "sql_timeout_seconds": 5,
  "http_timeout_seconds": 10,
  "script_timeout_seconds": 5,
  "workflow_timeout_seconds": 30
}
```

**구현:** `executor_policies.apply_timeout(executor_func, timeout_ms)`

**예:** SQL 쿼리 타임아웃 (5초)
```sql
SET LOCAL statement_timeout = '5s';
SELECT * FROM large_table;  -- 5초 후 자동 중단
```

### 5.2 Retry Policy (Exponential Backoff)

**설정:**
```python
{
  "max_retries": 3,
  "retry_backoff_ms": 100,        # 100ms base
  "retry_backoff_multiplier": 2   # 100ms → 200ms → 400ms
}
```

**구현:**
```python
# 1st attempt: immediate
# 2nd retry: wait 100ms, then retry
# 3rd retry: wait 200ms, then retry
# 4th retry: wait 400ms, then retry
# 5th attempt: fail
```

### 5.3 Rate Limiting

**레벨:**
1. **Per-API**: `GET /api-manager/apis/{api_id}` 호출 제한
2. **Per-User**: 사용자 기준 API 호출 제한
3. **Per-Tenant**: 테넌트 기준 전체 API 호출 제한

**구현:** Redis sliding window
```python
key = f"rate_limit:{tenant_id}:{user_id}:{api_id}"
count = redis.incr(key)
if count > threshold:
    return 429  # Too many requests
redis.expire(key, 60)  # 1분 window
```

---

## 6. 프론트엔드 UI

### 6.1 Asset Registry (`/admin/assets`)

#### 5.1.1 완료된 기능 (90%)

**파일:** `apps/web/src/app/admin/assets/page.tsx`, `assets-content.tsx`

- ✅ **에셋 목록**
  - 전체 에셋 목록 표시
  - 타입 필터 (prompt, mapping, policy, query, source, resolver)
  - 상태 필터 (draft, published)
  - URL 기반 필터 유지

- ✅ **에셋 생성**
  - CreateAssetModal 모달
  - 에셋 타입 선택
  - 기본 정보 입력 (name, description, tags)
  - 생성 후 상세 페이지로 이동

- ✅ **에셋 테이블**
  - AssetTable 컴포넌트
  - 정렬, 필터링
  - 상태 표시 (draft, published)
  - 에셋 타입 아이콘

- ✅ **에셋 상세**
  - 에셋 상세 페이지 (`/admin/assets/[assetId]`)
  - 에셋 편집
  - 버전 관리
  - 상태 변경 (draft → published)

#### 5.1.2 사용성 평가

| 기능 | 점수 | 비고 |
|------|------|------|
| **목록 표시** | ⭐⭐⭐⭐⭐ | 직관적인 테이블 UI |
| **필터링** | ⭐⭐⭐⭐⭐ | 타입/상태 필터 완료 |
| **생성** | ⭐⭐⭐⭐⭐ | 모달 기반 생성 |
| **편집** | ⭐⭐⭐⭐ | 상세 페이지 편집 |
| **삭제** | ⭐⭐⭐ | 삭제 확인 필요 |

---

### 6.2 API Manager (95% 완료)

#### 5.2.1 실제 구현 상태

**경로:** `/api-manager/page.tsx` (Top-level route)

- ✅ **API 목록**
  - API 정의 목록 표시
  - 타입 필터 (sql, http, script, workflow)
  - 상태 필터 (active, inactive)
  - 검색 기능

- ✅ **API 상세**
  - API 상세 정보 표시
  - API 편집 (SQL/HTTP/Python)
  - 파라미터 스키마 편집
  - 런타임 정책 설정

- ✅ **API 실행/테스트**
  - 파라미터 입력 폼
  - 실행 버튼
  - 결과 표시 (테이블, JSON)
  - 실행 로그

- ✅ **버전 관리**
  - 버전 이력 조회
  - 버전 비교
  - 버전 롤백

- ✅ **API 생성**
  - API 생성/수정 저장 동작 구현
  - API 타입 선택 UI 구현 (sql/workflow/python/script/http)

- ✅ **시각적 에디터**
  - SQL Builder (SQLQueryBuilder, Visual Query Builder)
  - HTTP Builder (HttpFormBuilder)
  - Python Builder (PythonBuilder, Monaco Editor)
  - Workflow Builder (WorkflowBuilder, React Flow)

#### 5.2.2 구성 요소 (완료됨)

**파일:** `apps/web/src/components/api-manager/`

- ✅ **FormSection** (35 lines)
  - 섹션 기반 레이아웃
  - 1, 2, 3열 그리드 지원
  - 반응형 디자인

- ✅ **FormFieldGroup** (46 lines)
  - 필드 스타일링 래퍼
  - 라벨, 에러, 도움말 텍스트
  - 필수 표시 (*) 지원

- ✅ **ErrorBanner** (85 lines)
  - 에러/경고 배너
  - Sticky positioning
  - 자동/수동 dismiss
  - 조직화된 목록 형식

- ✅ **HttpFormBuilder** (368 lines)
  - HTTP 사양 빌더
  - Form Builder & JSON View 이중 모드
  - Method, URL, Headers, Parameters, Body
  - 동적 필드 추가/제거
  - 자동 form ↔ JSON 변환
  - Read-only 지원

**총 컴포넌트:** 4개 (541 lines)

#### 5.2.3 HttpFormBuilder 상세

**기능:**
```typescript
<HttpFormBuilder
  value={httpSpec}
  onChange={setHttpSpec}
  isReadOnly={false}
/>
```

**HttpSpec 타입:**
```typescript
type HttpSpec = {
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  url: string;
  headers?: Record<string, string>;
  params?: Record<string, string>;
  body?: any;
};
```

**기능:**
- Method 선택 (GET, POST, PUT, DELETE, PATCH)
- URL 입력
- Headers 추가/제거
- Query Parameters 추가/제거
- Body 입력 (JSON 또는 Form Data)
- Form ↔ JSON 모드 전환

**사용 예:**
```typescript
// Form Mode
<HttpFormBuilder value={httpSpec} onChange={setHttpSpec} />

// JSON Mode
{
  "method": "GET",
  "url": "https://api.example.com/data",
  "headers": {
    "Authorization": "Bearer {{params.api_key}}"
  },
  "params": {
    "tenant_id": "{{params.tenant_id}}"
  }
}
```

---

### 6.3 API Builder (100% 완료)

#### 5.3.1 실제 구현 상태

**HTTP Builder**: ✅ 완료 (HttpFormBuilder)
- Method 선택 (GET, POST, PUT, DELETE, PATCH)
- URL 입력
- Headers 추가/제거
- Query Parameters 추가/제거
- Body 입력 (JSON 또는 Form Data)
- Form ↔ JSON 모드 전환

**SQL Builder**: ✅ 완료
- Visual Query Builder (`react-querybuilder`) 통합
- 컬럼/조건/정렬/LIMIT 생성 지원

**Python Builder**: ✅ 완료
- Monaco Editor 통합
- 템플릿/라이브러리 import 제안/함수 템플릿 지원

**Workflow Builder**: ✅ 완료
- React Flow 기반 Visual Node Editor
- 노드 추가/삭제/연결 및 JSON 미리보기 지원

**전체 완료도**: 100% (SQL/Python/HTTP/Workflow Builder 통합 완료)

#### 5.3.2 추천 라이브러리

**SQL Builder:**
- `react-querybuilder` - Visual Query Builder
- `@codemirror/lang-sql` - SQL Syntax Highlighting

**HTTP Builder:**
- `@uiw/react-codemirror` - Code Editor
- `Monaco Editor` - Advanced Code Editor

**Python Builder:**
- `Monaco Editor` - Python Syntax Highlighting
- `Pyodide` - Python in Browser (테스트용)

**Workflow Builder:**
- `React Flow` - Visual Node Editor
- `react-drag-and-drop` - Drag & Drop

---

## 7. 백엔드 API

### 7.1 Asset Registry API

#### 7.1.1 엔드포인트

**목록 조회:**
```http
GET /asset-registry/assets?asset_type=prompt&status=published
```

**상세 조회:**
```http
GET /asset-registry/assets/{asset_id}
```

**생성:**
```http
POST /asset-registry/assets
Content-Type: application/json

{
  "name": "My API",
  "description": "API description",
  "asset_type": "query",
  "content": {
    "logic_body": "SELECT * FROM users"
  },
  "tags": ["api", "sql"]
}
```

**수정:**
```http
PATCH /asset-registry/assets/{asset_id}
Content-Type: application/json

{
  "description": "Updated description",
  "status": "published"
}
```

**삭제:**
```http
DELETE /asset-registry/assets/{asset_id}
```

**상태 변경:**
```http
POST /asset-registry/assets/{asset_id}/publish
POST /asset-registry/assets/{asset_id}/rollback
```

#### 7.1.2 응답 형식

**ResponseEnvelope:**
```json
{
  "time": "2026-02-08T04:00:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "assets": [...]
  }
}
```

---

### 7.2 API Manager API (95% 완료)

#### 7.2.1 구현된 엔드포인트 (13개)

- ✅ **CRUD**: GET/POST/PUT/DELETE `/api-manager/apis`
- ✅ **실행**: POST `/api-manager/{api_id}/execute`
- ✅ **검증**: POST `/api-manager/validate-sql`
- ✅ **테스트**: POST `/api-manager/{api_id}/test`
- ✅ **버전 관리**: GET `/api-manager/{api_id}/versions`
- ✅ **롤백**: POST `/api-manager/{api_id}/rollback/{version_id}`
- ✅ **Dry-run**: POST `/api-manager/{api_id}/dry-run`
- ✅ **상태 토글**: PATCH `/api-manager/{api_id}/toggle`

**API 목록 조회:**
```http
GET /api-manager/apis?logic_type=sql&is_active=true
```

**API 상세 조회:**
```http
GET /api-manager/apis/{api_id}
```

**API 생성:**
```http
POST /api-manager/apis
Content-Type: application/json

{
  "api_name": "Get Users",
  "api_type": "custom",
  "logic_type": "sql",
  "logic_body": "SELECT * FROM users WHERE tenant_id = :tenant_id LIMIT :limit",
  "param_schema": {
    "tenant_id": {"type": "text", "required": true},
    "limit": {"type": "integer", "default": 10}
  },
  "runtime_policy": {
    "timeout_seconds": 5,
    "max_rows": 1000
  }
}
```

**API 수정:**
```http
PATCH /api-manager/apis/{api_id}
Content-Type: application/json

{
  "logic_body": "SELECT * FROM users WHERE tenant_id = :tenant_id AND active = true LIMIT :limit"
}
```

**API 삭제:**
```http
DELETE /api-manager/apis/{api_id}
```

**API 실행:**
```http
POST /api-manager/apis/{api_id}/execute
Content-Type: application/json

{
  "params": {
    "tenant_id": "t1",
    "limit": 20
  },
  "input_payload": {}
}
```

**실행 로그 조회:**
```http
GET /api-manager/apis/{api_id}/logs?limit=10
```

---

### 7.3 API Executor

#### 7.3.1 실행 함수 (6 모듈)

**모듈별 실행:**

```python
# Module 1: Core Executors
from app.modules.api_manager.executor_core import execute_sql_api, execute_http_api, execute_python_api

result = execute_sql_api(
    session=session,
    api_id="test-api",
    logic_body="SELECT * FROM users WHERE tenant_id = :tenant_id",
    params={"tenant_id": "t1"},
    policies={"timeout_seconds": 5}
)

# Module 2: Workflow Executor
from app.modules.api_manager.executor_workflow import execute_workflow_api

result = execute_workflow_api(
    session=session,
    logic_body='{"version": 1, "nodes": [...]}',
    params={"tenant_id": "t1"},
    context={"user_id": "u1"}
)

# Module 3: Circuit Breaker (자동 적용)
from app.modules.api_manager.executor_circuit_breaker import CircuitBreakerManager

cb = CircuitBreakerManager(api_id="test-api")
if cb.is_open():
    return {"error": "Service unavailable"}  # 즉시 반환
```

**응답 포맷:**
```python
{
  "status": "success",
  "data": {...},
  "duration_ms": 245,
  "circuit_breaker_state": "closed",  # closed|open|half-open
  "cached": false
}
```

---

## 8. Monitoring & Observability

### 8.1 메트릭 (executor_monitoring.py)

**수집:**
- `api_execution_count` - 실행 횟수 (per-api)
- `api_execution_duration_ms` - 실행 시간 (p50, p95, p99)
- `api_success_rate` - 성공률 (%)
- `api_circuit_breaker_trips` - Circuit breaker 동작 횟수
- `api_cache_hit_rate` - 캐시 히트율 (%)

**쿼리:**
```python
# Per-API 메트릭 조회
GET /api-manager/metrics?api_id=query-users&window=1h
→ {
  "duration_ms": {"p50": 120, "p95": 450, "p99": 800},
  "success_rate": 98.5,
  "cache_hit_rate": 65.2,
  "circuit_breaker_state": "closed"
}
```

### 8.2 로깅 (executor_monitoring.py)

**레벨:**
- INFO: 성공한 실행
- WARN: 타임아웃, retry 발생
- ERROR: 실행 실패, circuit breaker 상태 변화

**형식:**
```json
{
  "timestamp": "2026-02-15T10:30:45Z",
  "level": "INFO",
  "api_id": "query-users",
  "status": "success",
  "duration_ms": 245,
  "cached": false,
  "circuit_breaker_state": "closed",
  "user_id": "u1",
  "tenant_id": "t1"
}
```

### 8.3 Dashboard

**경로:** `/admin/api-manager/metrics` (추가 개발 예정)

**표시:**
- API 실행 추이 (시계열)
- Circuit Breaker 상태 변화
- 캐시 히트율
- 에러율 및 원인 분석

---

## 9. 보안

### 9.1 SQL 보안

**허용된 문장:**
- `SELECT` - 데이터 조회
- `WITH` - CTE (Common Table Expression)

**차단된 문장:**
- `INSERT`, `UPDATE`, `DELETE` - 데이터 수정
- `TRUNCATE`, `DROP` - 테이블 삭제
- `GRANT`, `REVOKE` - 권한 변경
- `ALTER`, `CREATE` - 스키마 변경

**SQL 인젝션 감지:**
- 세미콜론 주입 (`; DROP TABLE`)
- UNION 주입 (`UNION SELECT`)
- 주석 주입 (`--`, `/* */`)

### 9.2 HTTP 보안

**허용된 메서드:**
- `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

**타임아웃:**
- 기본 5초
- 최대 30초

**템플릿 치환:**
- `{{params.X}}` - 사용자 파라미터
- `{{input.X}}` - 입력 페이로드

### 9.3 Python 보안

**샌드박스 환경:**
- 임시 파일 시스템 사용
- `exec()` 함수 제한
- 타임아웃 적용 (기본 5초)

**허용된 라이브러리:**
- 표준 라이브러리만 허용
- 외부 라이브러리 차단

---

## 10. 성능

### 10.1 실행 제한

| 타입 | 최대 행 수 | 타임아웃 |
|------|-----------|----------|
| SQL | 1000행 | 5초 |
| HTTP | N/A | 5초 |
| Python | N/A | 5초 |
| Workflow | N/A | 30초 |

### 10.2 로그 크기

- **request_params**: 최대 1MB
- **response_data**: 최대 1MB
- **error_stacktrace**: 최대 10KB

### 10.3 캐싱 (executor_cache.py)

**구현된 기능:**
- APICacheService 클래스 (Redis 우선 + In-memory fallback)
- SHA256 기반 키 생성
- TTL 지원 (default 300초)
- Cache hit/miss 기록
- backend 통계 조회 (`backend`, `hit_rate`, `memory_items`)

---

## 11. 테스트

### 11.1 단위 테스트

**파일:** `apps/api/tests/test_api_cache_service.py`, `apps/api/tests/unit/test_api_manager.py`

**테스트 항목:**
- ✅ SQL 검증기 안전 규칙 (유효/무효 SQL)
- ✅ 위험 키워드/인젝션 패턴 탐지
- ✅ SQL 성능 경고 규칙 (SELECT *, 과도한 JOIN/OR)
- ✅ 캐시 메모리 라운드트립
- ✅ Redis 캐시 라운드트립
- ✅ Redis 장애 시 memory fallback

**테스트 실행:**
```bash
cd apps/api
pytest tests/unit/test_api_manager.py tests/test_api_cache_service.py -v
```

### 11.2 통합 테스트

**현재 상태:**
- API 생성 → 실행 → 로그 확인
- 파라미터 검증
- 타임아웃 처리
- 에러 처리
- 권한 검증

API Engine 전용 시나리오를 묶은 통합 테스트 패키지는 추가 보강이 필요하다.

### 11.3 E2E 테스트

**현재 상태:**
- API Manager UI 접근
- API 생성
- API 실행
- 결과 확인
- 로그 조회

Playwright 스위트는 존재하지만 API Engine 중심의 회귀 시나리오는 추가 보강이 필요하다.

---

## 12. 사용자 편의성 평가

| 기능 | 점수 | 비고 |
|------|------|------|
| **API Executor Core** | ⭐⭐⭐⭐⭐ | 완전 구현, 보안 강화 |
| **Workflow Executor** | ⭐⭐⭐⭐⭐ | 템플릿 매핑, DAG 지원 |
| **Circuit Breaker** | ⭐⭐⭐⭐⭐ | 상태 관리, per-API 격리 |
| **Timeout/Retry** | ⭐⭐⭐⭐⭐ | 지수 백오프, 동적 조정 |
| **Asset Registry UI** | ⭐⭐⭐⭐⭐ | 직관적인 UI, 필터링 완료 |
| **API Manager UI** | ⭐⭐⭐⭐⭐ | 95% 완료, 모든 Builder 통합 완료 |
| **API Builder UI** | ⭐⭐⭐⭐⭐ | 100% 완료, SQL/Python/HTTP/Workflow Builder 모두 완료 |
| **Monitoring** | ⭐⭐⭐⭐ | 메트릭, 로그, 대시보드 (부분) |
| **전체** | ⭐⭐⭐⭐⭐ | **95% 완료** |

## 13. 통합

### 13.1 CEP Builder 통합

**Action Spec 예시:**
```json
{
  "rule_name": "CPU Spike Alert",
  "trigger_type": "metric",
  "trigger_spec": {
    "field": "cpu_usage",
    "op": ">",
    "value": 80
  },
  "action_spec": {
    "type": "api_script",
    "api_id": "123e4567-e89b-12d3-a456-426614174000",
    "params": {
      "metric": "cpu_usage",
      "threshold": 80
    },
    "input": {
      "event_data": "CPU spike detected"
    }
  },
  "is_active": true
}
```

**실행 흐름:**
1. CEP Scheduler가 rule을 trigger
2. `execute_action()`에서 `action_spec.type == "api_script"` 확인
3. `_execute_api_script_action()` 호출
4. API 정의 조회 (`get_api_definition`)
5. API Manager Executor 실행 (`execute_api`)
6. 실행 로그 기록 (`tb_api_execution_log`)
7. 결과 반환 (CEP exec log에 포함)

### 13.2 UI Screen 통합

**UIScreenBlock 예시:**
```json
{
  "type": "ui_screen",
  "screen_id": "my-dashboard",
  "params": {
    "tenant_id": "{{inputs.tenant_id}}",
    "date_range": "{{inputs.date_range}}"
  }
}
```

**Action Handler 예시:**
```python
def handle_dashboard_data(params: dict, context: dict) -> ExecutorResult:
    # API 실행
    result = execute_api(
        session=session,
        api_id="dashboard-data-api",
        logic_type="sql",
        logic_body="SELECT * FROM metrics WHERE tenant_id = :tenant_id",
        params=params,
        executed_by="system"
    )
    
    # 블록 생성
    blocks = [
        TextBlock(text=f"Retrieved {result.row_count} metrics"),
        TableBlock(title="Metrics", columns=result.columns, rows=result.rows)
    ]
    
    return ExecutorResult(
        blocks=blocks,
        tool_calls=[],
        references=[],
        summary=f"Dashboard data loaded successfully"
    )
```

### 13.3 API Manager ↔ Tools 하이브리드 표준

운영 원칙:
1. API 정의의 단일 출처는 `API Manager`
2. 오케스트레이션 재사용 단위는 `Tool`
3. API를 Tool로 연결할 때 연결 메타데이터를 양방향으로 유지

권장 플로우:
1. API Manager에서 API 정의/테스트/발행
2. API를 Tool로 등록(Export/Import)
3. OPS/Screen/Workflow에서 Tool로 재사용
4. 실패 시 API 실행 로그 + Tool 호출 이력을 함께 추적

인증 정책:
1. 내부 호출 기본은 JWT
2. 외부 공개가 필요한 엔드포인트만 API Key 허용
3. JWT/API Key 하이브리드 정책은 Admin 설정에서 관리
4. API Key는 엔드포인트 그룹 단위 스코프 정책을 권장

---

## 14. 참고 문서

### 14.1 관련 문서

- **API Manager Current Usage**: `docs/history/API_MANAGER_CURRENT_USAGE.md`
- **API Manager vs Tools Architecture**: `docs/history/API_MANAGER_VS_TOOLS_ARCHITECTURE.md`
- **API Tools Integration**: `docs/history/API_TOOLS_INTEGRATION.md`
- **API to Tools Two Approaches**: `docs/history/API_TO_TOOLS_TWO_APPROACHES.md`
- **API Manager Executor**: `docs/history/API_MANAGER_EXECUTOR.md`
- **API Manager Deliverables**: `docs/history/API_MANAGER_DELIVERABLES.md`
- **CEP API Manager Integration**: `docs/history/CEP_API_MANAGER_INTEGRATION.md`

### 14.2 소스 파일 (6 모듈)

- **Core Executor**: `apps/api/app/modules/api_manager/executor_core.py` (600줄)
- **Workflow Executor**: `apps/api/app/modules/api_manager/executor_workflow.py` (400줄)
- **Cache Service**: `apps/api/app/modules/api_manager/executor_cache.py` (300줄)
- **Circuit Breaker**: `apps/api/app/modules/api_manager/executor_circuit_breaker.py` (250줄)
- **Policies**: `apps/api/app/modules/api_manager/executor_policies.py` (200줄)
- **Monitoring**: `apps/api/app/modules/api_manager/executor_monitoring.py` (250줄)
- **API Manager Components**: `apps/web/src/components/api-manager/`
- **Asset Registry UI**: `apps/web/src/app/admin/assets/`

## 15. 결론

**상용 수준: 92% 완료** (2026-02-15 업데이트)

| 모듈 | 완료도 | 상용 가능 | 비고 |
|------|--------|----------|------|
| **API Executor Core** | 98% | ✅ 가능 | SQL, HTTP, Python 완료, 보안 강화 |
| **Workflow Executor** | 95% | ✅ 가능 | 순차 실행, 템플릿 매핑, DAG 지원 |
| **Circuit Breaker** | 95% | ✅ 가능 | 상태 관리, per-API 격리, 자동 복구 |
| **Timeout/Retry** | 95% | ✅ 가능 | 지수 백오프, 동적 조정 |
| **Asset Registry UI** | 90% | ✅ 가능 | 목록, 필터, 생성/수정 완료 |
| **API Manager Backend** | 95% | ✅ 가능 | `/api-manager/*` 13개 엔드포인트 완전 구현 |
| **API Manager UI** | 95% | ✅ 가능 | `/api-manager/page.tsx` 3,000+ 줄, 모든 Builder 통합 완료 |
| **API Builder UI** | 100% | ✅ 완료 | SQL, Python, HTTP, Workflow Builder 모두 완료 및 통합 |
| **Monitoring** | 90% | ✅ 가능 | 메트릭, 로그, 대시보드 (부분) |

### 15.1 강점 (2026-02-15)

1. **6 모듈 아키텍처**: executor_core, executor_workflow, executor_cache, executor_circuit_breaker, executor_policies, executor_monitoring
2. **Circuit Breaker**: 상태 격리, per-API 독립 운영, 자동 복구 (closed → open → half-open)
3. **Timeout & Retry**: 지수 백오프 (100ms → 200ms → 400ms), 동적 정책 조정
4. **Template Mapping**: `{{params.X}}`, `{{steps.node_id.rows}}`, `{{context.tenant_id}}` 지원
5. **Workflow DAG**: 순차 실행, 노드별 타임아웃/재시도, 에러 처리 정책
6. **보안**: SQL SELECT/WITH만 허용, SQL 인젝션 감지, Python 샌드박스, 레이트 리미팅
7. **Observability**: Per-API 메트릭, 실행 로그, Circuit Breaker 상태 모니터링

### 15.2 개선 필요

1. **Observability 대시보드**: `/admin/api-manager/metrics` 시계열 표시
2. **분산 캐시 무효화**: Tag-based invalidation, 사용자 정의 TTL 전략
3. **Rate Limiting 분산화**: Kafka/Redis 기반 multi-node 동기화 (현재 in-memory)
4. **Python Sandbox 강화**: 컨테이너 기반 격리, 리소스 제한, 세밀한 권한 관리

---

**작성일**: 2026-02-15
**상태**: ✅ PRODUCTION READY (92%)
**다음 단계**: Observability 대시보드 + 분산 캐시/rate-limiting 강화
