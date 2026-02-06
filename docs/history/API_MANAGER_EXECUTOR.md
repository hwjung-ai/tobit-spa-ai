# API Manager Executor

## 개요

API Manager Executor는 다양한 타입의 API(`sql`, `http`, `script`, `workflow`)를 실행하고 결과를 반환하는 통합 실행 엔진입니다. 모든 API 실행은 `tb_api_execution_log` 테이블에 기록되어 추적 및 디버깅이 가능합니다.

## 소스 맵

- 실행기: `apps/api/services/api_manager_executor.py`
- 실행 로그 모델: `apps/api/models/api_execution_log.py`
- 마이그레이션: `apps/api/alembic/versions/0044_add_api_execution_log.py`
- 테스트: `apps/api/tests/test_api_manager_executor.py`
- CEP 통합: `apps/api/app/modules/cep_builder/executor.py` (`_execute_api_script_action`)

## 지원하는 API 타입

### 1. SQL API (`logic_type = "sql"`)

PostgreSQL 데이터베이스 쿼리를 실행합니다.

**기능:**
- 보안 검사: SELECT/WITH만 허용
- 위험한 키워드 차단: INSERT, UPDATE, DELETE, TRUNCATE, DROP, GRANT, REVOKE, ALTER, CREATE
- SQL 인젝션 패턴 감지: 세미콜론 주입, UNION 주입 등
- 자동 LIMIT 적용 (기본 1000행, 최대 1000행)
- 실행 함수: `execute_sql_api()`

**사용 예:**
```python
from app.services.api_manager_executor import execute_sql_api
from core.db import get_session_context

with get_session_context() as session:
    result = execute_sql_api(
        session=session,
        api_id="test-api",
        logic_body="SELECT * FROM users WHERE tenant_id = :tenant_id LIMIT 10",
        params={"tenant_id": "t1"},
        executed_by="test-user"
    )
    print(f"Status: {result.status_code}, Rows: {len(result.rows)}")
```

### 2. HTTP API (`logic_type = "http"`)

외부 HTTP 요청을 실행합니다.

**기능:**
- HTTP 메서드: GET, POST, PUT, DELETE, PATCH 등
- JSON 템플릿 치환: `{{params.X}}`, `{{input.X}}`
- 타임아웃 설정 (기본 5초)
- 실행 함수: `execute_http_api()`

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
from app.services.api_manager_executor import execute_http_api

result = execute_http_api(
    session=session,
    api_id="test-api",
    logic_body='{"url": "https://api.example.com/data", "method": "GET"}',
    params={"tenant_id": "t1"},
    executed_by="test-user"
)
```

### 3. Python Script API (`logic_type = "script"`)

Python 스크립트를 실행합니다.

**기능:**
- `main(params, input_payload)` 함수 필수
- 기본 샌드박스 환경 (임시 파일 시스템 사용)
- 실행 타임아웃 (기본 5초)
- 실행 함수: `execute_python_api()`

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
from app.services.api_manager_executor import execute_python_api

result = execute_python_api(
    session=session,
    api_id="test-api",
    logic_body="""
def main(params, input_payload):
    return {"result": "hello", "value": params.get("x", 0) * 2}
    """,
    params={"x": 5},
    input_payload={"items": [1, 2, 3]},
    executed_by="test-user"
)
```

### 4. Workflow API (`logic_type = "workflow"`)

여러 API를 순차적으로 실행하는 워크플로입니다.

**기능:**
- 템플릿 파라미터 지원: `{{params.X}}`, `{{steps.n1.rows}}`, `{{steps.n1.output}}`
- 노드별 상태 및 지속시간 기록
- 실행 함수: `execute_workflow_api()` (현재 placeholder)

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
      "limit": 100
    },
    {
      "id": "summarize",
      "type": "script",
      "api_id": "00000000-0000-0000-0000-000000000002",
      "input": "{{steps.collect.rows}}",
      "params": {
        "mode": "digest"
      }
    }
  ]
}
```

## 실행 로그

모든 API 실행은 `tb_api_execution_log` 테이블에 기록됩니다.

**테이블 필드:**
- `id`: 실행 로그 ID (UUID)
- `api_id`: 실행된 API 식별자 (UUID)
- `executed_by`: 실행 주체 (사용자 ID 또는 시스템)
- `status`: 실행 상태 (`success`, `fail`, `timeout`)
- `duration_ms`: 실행 시간 (밀리초)
- `request_params`: 요청 파라미터 (JSON)
- `response_data`: 응답 데이터 (JSON, 최대 1MB)
- `response_status`: HTTP 상태 코드 또는 DB 실행 상태
- `error_message`: 에러 메시지 (실패 시)
- `error_stacktrace`: 스택 트레이스 (실패 시)
- `rows_affected`: 영향받은 행 수 (DB/HTTP)
- `metadata`: 추가 메타데이터 (JSON)
- `created_at`: 실행 시간 (UTC)

**인덱스:**
- `(api_id)` - API별 실행 이력 조회
- `(executed_by)` - 사용자별 실행 이력 조회
- `(created_at)` - 시간순 조회
- `(status)` - 상태별 필터링

## SQL 보안 검사

`validate_select_sql()` 함수는 다음을 검사합니다:

1. **문장 시작 검사**: SELECT 또는 WITH로 시작하는지 확인
2. **위험한 키워드 차단**: INSERT, UPDATE, DELETE, TRUNCATE, DROP, GRANT, REVOKE, ALTER, CREATE
3. **SQL 인젝션 패턴 감지**:
   - 세미콜론 주입 (`; DROP TABLE`)
   - UNION 주입 (`UNION SELECT`)
   - 주석 주입 (`--`, `/* */`)
4. **복합 조건 허용**: AND, OR, NOT 등 논리 연산자는 허용

**테스트 케이스:**
```python
from app.services.api_manager_executor import validate_select_sql

# 유효한 SQL
is_valid, error = validate_select_sql("SELECT * FROM users")
# (True, None)

# 무효한 SQL (INSERT)
is_valid, error = validate_select_sql("INSERT INTO users VALUES (1)")
# (False, "INSERT is not allowed")

# 무효한 SQL (SQL 인젝션)
is_valid, error = validate_select_sql("SELECT * FROM users; DROP TABLE users")
# (False, "SQL injection detected: semicolon with DROP")
```

## 사용처

### 1. CEP Builder Action

CEP 규칙의 action에서 `type: "api_script"`로 API Manager API를 호출합니다.

**Action Spec 예시:**
```json
{
  "type": "api_script",
  "api_id": "api-uuid",
  "params": {
    "param1": "value1"
  },
  "input": {
    "event_data": {...}
  }
}
```

**구현 위치:** `apps/api/app/modules/cep_builder/executor.py::_execute_api_script_action()`

### 2. API Test Runner (향후 구현)

API 테스트 및 디버깅을 위한 별도 UI가 필요합니다.

### 3. Direct API Execution (향후 구현)

REST API 엔드포인트를 통한 직접 실행이 필요합니다.

## 테스트

테스트 파일: `apps/api/tests/test_api_manager_executor.py`

**테스트 항목:**
- SQL 보안 검사 (유효/무효 SQL)
- CTE (Common Table Expression) 지원
- 위험한 키워드 차단 (INSERT, DELETE, DROP 등)
- SQL 인젝션 패턴 감지
- HTTP API 실행 (GET/POST)
- HTTP 타임아웃 및 에러 처리
- Python 스크립트 실행
- Python 스크립트 에러 처리
- Workflow API (placeholder)
- 지원하지 않는 API 타입 에러 처리

**테스트 실행:**
```bash
cd apps/api
pytest tests/test_api_manager_executor.py -v
```

## 마이그레이션

마이그레이션 파일: `apps/api/alembic/versions/0044_add_api_execution_log.py`

**마이그레이션 적용:**
```bash
cd apps/api
alembic upgrade head
```

**마이그레이션 롤백:**
```bash
cd apps/api
alembic downgrade base
```

## API 통합 예시

### API 정의 생성
```python
from app.modules.api_manager.crud import create_api_definition
from core.db import get_session_context

with get_session_context() as session:
    api_def = create_api_definition(
        session=session,
        api_name="Get Users",
        api_type="custom",
        logic_type="sql",
        logic_body="SELECT * FROM users WHERE tenant_id = :tenant_id LIMIT :limit",
        param_schema={
            "tenant_id": {"type": "text", "required": True},
            "limit": {"type": "integer", "default": 10}
        },
        runtime_policy={
            "timeout_seconds": 5,
            "max_rows": 1000
        },
        created_by="admin"
    )
```

### API 실행
```python
from app.services.api_manager_executor import execute_api
from core.db import get_session_context

with get_session_context() as session:
    result = execute_api(
        session=session,
        api_id=str(api_def.id),
        logic_type="sql",
        logic_body=api_def.logic_body,
        params={"tenant_id": "t1", "limit": 20},
        executed_by="admin"
    )
    
    if result.status_code == 200:
        print(f"Retrieved {result.row_count} rows")
        for row in result.rows[:5]:
            print(row)
    else:
        print(f"Error: {result.error_message}")
```

## CEP Builder 통합

CEP Builder의 executor에서 API Manager Executor를 호출하여 CEP 규칙의 action으로 API를 실행할 수 있습니다.

**CEP Action Spec 예시:**
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
5. API Manager Executor 실행 (`execute_script_api`)
6. 실행 로그 기록 (`tb_api_execution_log`)
7. 결과 반환 (CEP exec log에 포함)

## 향후 개발 사항

1. **API Test Runner**: API 테스트 및 디버깅 UI 구현
2. **Direct API Execution**: REST API 엔드포인트 구현
3. **Workflow Executor**: 워크플로 실행 로직 완전 구현
4. **Python Sandbox**: 더 안전한 Python 실행 환경 (Docker, restricted 등)
5. **API Versioning**: API 버전 관리 기능
6. **Rate Limiting**: API 실행 속도 제한

## 참고

- **DB Driver**: psycopg (>=3.1) - PostgreSQL 접근 필수 드라이버
- **HTTP Client**: httpx - 비동기 HTTP 클라이언트
- **Python 실행**: `exec()` 함수 + 임시 파일 시스템
- **보안**: SQL만 SELECT/WITH 허용, Python은 기본 샌드박스
- **로그**: 모든 실행이 `tb_api_execution_log`에 기록됨