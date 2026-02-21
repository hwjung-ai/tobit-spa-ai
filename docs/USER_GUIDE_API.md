# API User Guide

**Last Updated**: 2026-02-20
**Production Readiness**: 92%

## 문서의 성격

이 문서는 API Manager를 처음 사용하는 사용자가
아무 것도 없는 상태에서 API를 하나씩 만들어
실제 실행 가능한 운영 자산으로 완성하도록 돕는 튜토리얼이다.

목표:
1. 완전 신규 API를 직접 만든다.
2. SQL/HTTP/Python/Workflow를 각각 실습한다.
3. 테스트/로그/버전/롤백까지 운영 흐름을 익힌다.

---

## 0. 시작 전 준비

### 0.1 준비 체크

1. 프론트엔드 실행 확인
   - `http://localhost:3000/api-manager` 접속
2. 백엔드 실행 확인
   - `http://localhost:8000/health` 또는 API 호출 가능한 상태
3. 로그인/권한 확인
4. tenant 헤더가 누락되지 않도록 클라이언트 설정 확인

### 0.2 API Manager 화면 빠른 지도

화면은 크게 3개 영역으로 구성된다. 아래 다이어그램은 전체 레이아웃을 보여준다.

```
+----------------------------------------------------------------------+
|  API Manager                                                         |
+-------------------+--------------------------------------------------+
| LEFT PANE         | CENTER PANE                                      |
|                   |                                                  |
| [Custom] [System] | [Definition] [Logic] [Test]   <- 3개 탭         |
|  ^scope 선택      |                                                  |
|                   | +----------------------------------------------+ |
| -- System일 때 -- | |                                              | |
| [Discovered]      | |  Definition: 메타/정책                       | |
| [Registered]      | |  Logic: sql/http/python/script/workflow       | |
|  ^sub-view 전환   | |  Test: 실행 + 결과 + 로그                    | |
|                   | |                                              | |
| +---------------+ | +----------------------------------------------+ |
| | 검색 필터     | |                                                  |
| | 로직타입 필터 | | [Create API] / [Update API]   [Test (Dry-run)]   |
| +---------------+ |                                                  |
|                   +--------------------------------------------------+
| API 목록 리스트   | RIGHT PANE (Draft Assistant)                      |
| - 이름            |                                                  |
| - method          | [BuilderCopilotPanel]                            |
| - endpoint        |  - AI 프롬프트로 API 드래프트 생성               |
| - logic_type      |  - Draft Status 표시                             |
| - source 표시     |  - [Preview] [Test] [Apply] [Save Local] 버튼    |
|                   |  - 드래프트 오류/경고 표시                       |
| [+ New API]       |  - Debug 패널 (접이식)                           |
+-------------------+--------------------------------------------------+
```

**1. Left Pane -- API 목록 영역**

- API 목록: 서버에서 불러온 API와 로컬 저장 API가 함께 표시된다.
- `New API` 버튼: 하단에 위치, 새 API 폼을 초기화한다.
- 검색/필터: API 이름으로 텍스트 검색, 로직 타입별 필터(`all`, `sql`, `http`, `python`, `script`, `workflow`) 지원.
- Scope 선택기: Left Pane 상단에 `Custom`과 `System` 버튼이 표시된다.
  - `Custom` (기본값): 사용자가 직접 생성/편집하는 API 목록. 전체 CRUD 가능.
  - `System`: 환경변수 `NEXT_PUBLIC_ENABLE_SYSTEM_APIS=true`일 때만 표시. 읽기 전용.

- System Scope 진입 시 Sub-View 전환 버튼이 나타난다:
  - `Discovered`: OpenAPI 등 외부 소스에서 자동 수집된 엔드포인트 목록. DB에 등록되지 않은 상태.
  - `Registered`: 서버 DB에 등록된 시스템 API 목록. 서버 연결 실패 시 로컬 캐시에서 표시.

검증 포인트:
- Scope 버튼 클릭 시 목록이 즉시 교체된다.
- System > Discovered 선택 시 "Discovered endpoints are read-only" 안내 메시지가 표시된다.
- System > Registered 선택 시 서버 연결 오류가 있으면 "Server list unavailable. Showing local cache only" 배너가 표시된다.

**2. Center Pane -- 편집/실행 영역**

3개 탭으로 구성된다:

| 탭 | 역할 | 주요 입력 항목 |
|---|---|---|
| Definition | 메타데이터와 정책 설정 | API Name, Method, Endpoint, Description, Tags, Param Schema, Runtime Policy, Active, Created By |
| Logic | 실행 로직 작성 | Logic Type 선택 후 해당 Builder 사용 (SQLQueryBuilder, HttpFormBuilder, PythonBuilder, WorkflowBuilder, Script 에디터) |
| Test | 런타임 실행 및 검증 | Params JSON, Input JSON, Limit, Executed By, Execute/Dry-run 버튼, 실행 로그 리스트 |

- 5가지 Logic Type: `sql`, `http`, `python`, `script`, `workflow`
- Logic 탭에서 타입 버튼 클릭으로 전환. 각 타입별 전용 Builder UI가 표시된다.
- Test 탭의 실행 로그는 최근 20건까지 페이징으로 표시된다 (`limit=20`).
- 하단 버튼: 신규 API면 `Create API`, 기존 API면 `Update API` 표시. Logic 탭에서는 `Test {타입} (Dry-run)` 버튼 사용 가능.

**3. Right Pane -- Draft Assistant (AI 드래프팅)**

`DraftAssistantPanel` 컴포넌트는 AI 기반 API 드래프트 생성을 지원한다.

- 입력: 자연어로 원하는 API를 설명한다 (예: "디바이스 목록을 조회하는 SQL API를 만들어줘").
- AI가 JSON 형태의 ApiDraft를 생성하여 반환한다.
- Draft 상태 표시: 대기 중, 드래프트 준비됨, 미리보기, 테스트 중, 폼 적용됨, 로컬 저장됨, 오래됨, 오류 중 하나.
- 4개 액션 버튼:
  - `Preview`: 드래프트 JSON과 요약을 미리 본다.
  - `Test (Dry-run)`: 드래프트를 바로 테스트한다.
  - `Apply`: 드래프트를 Center Pane의 폼에 반영한다. Test 성공 후에만 활성화.
  - `Save (Local)`: 드래프트를 localStorage에 저장한다. Test 성공 후에만 활성화.
- 오류/경고가 있으면 빨간색/노란색 배너로 표시된다.
- Debug 접이식 패널에서 파싱 상태, 원본 AI 응답, 드래프트 JSON을 확인할 수 있다.

**4. Local Storage 구조**

API Manager는 서버 저장 외에 localStorage를 활용해 드래프트와 최종 API를 로컬에 보관한다.

| 키 접두사 | 용도 | 예시 |
|---|---|---|
| `api-manager:draft:{id}` | 작업 중인 드래프트 임시 저장 | `api-manager:draft:new` |
| `api-manager:api:{id}` | 최종 확정된 API 정의 로컬 백업 | `api-manager:api:/runtime/my-api` |

검증 포인트:
- 브라우저 DevTools > Application > Local Storage에서 위 키를 확인할 수 있다.
- 페이지를 새로고침해도 미적용 드래프트가 복원된다.

### 0.3 튜토리얼에서 사용할 기준 명칭

- Definition: 메타데이터와 정책
- Logic: 실제 실행 로직
- Test: 런타임 실행 검증

---

## 1. Lab 1 - 첫 API를 10분 안에 만들기 (SQL)

목표: `device_metrics_list` API를 생성하고 테스트까지 성공한다.

### Step 1. 신규 API 시작

1. `/api-manager` 접속
2. 왼쪽 하단 `New API` 클릭
3. Center 상단 탭이 `Definition`인지 확인

검증 포인트:
- Name/Endpoint 입력창이 비어 있는 상태로 초기화된다.

### Step 2. Definition 입력

다음 값을 그대로 입력한다.

- API Name: `device_metrics_list`
- HTTP Method: `POST`
- Endpoint Path: `/runtime/device-metrics-list`
- Description: `List latest metrics by device`
- Tags: `metrics,device,ops`
- Active: 체크
- Created By: `ops-builder`

검증 포인트:
- 입력값이 하단 Metadata 미리보기에도 반영된다.

### Step 3. Param Schema 입력

`Param Schema (JSON)`에 아래 입력:

```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string"},
    "device_id": {"type": "string"}
  },
  "required": ["tenant_id", "device_id"]
}
```

### Step 4. Runtime Policy 입력

`Runtime Policy (JSON)`에 아래 입력:

```json
{
  "timeout_ms": 5000,
  "max_rows": 200,
  "allow_runtime": true
}
```

검증 포인트:
- JSON 문법 에러 없이 저장 가능 상태가 된다.

### Step 5. Logic 탭 이동

1. `Logic` 탭 클릭
2. Logic Type 버튼에서 `SQL` 선택
3. SQLQueryBuilder에 다음 SQL 입력

```sql
SELECT device_id, metric_name, metric_value, collected_at
FROM tb_metrics
WHERE tenant_id = :tenant_id
  AND device_id = :device_id
ORDER BY collected_at DESC
LIMIT 100
```

검증 포인트:
- SQL 박스에 쿼리가 저장된다.

### Step 6. Dry-run

1. 우측 하단 `Test SQL (Dry-run)` 클릭
2. 결과 패널에서 Rows/Duration 확인

검증 포인트:
- 에러 없이 결과가 표시된다.
- JSON 보기로 columns/rows를 확인할 수 있다.

### Step 7. 저장

1. `Create API` 클릭
2. 상태 메시지 `API created` 확인

검증 포인트:
- Left Pane 목록에 `device_metrics_list`가 생성된다.

---

## 2. Lab 2 - Test 탭에서 실제 실행 검증

목표: 실행 파라미터를 넣고 런타임 실행을 성공시킨다.

### Step 1. Test 탭 이동

1. 생성한 API 선택
2. `Test` 탭 클릭

### Step 2. Params JSON 입력

```json
{
  "tenant_id": "t1",
  "device_id": "GT-01"
}
```

- Limit: `100`
- Executed by: `ops-builder`

### Step 3. Execute

1. `Execute API` 버튼 클릭
2. 결과/로그 영역 확인

검증 포인트:
- status `success`
- row count가 0 이상
- duration_ms가 기록됨

### Step 4. 로그 확인

1. 실행 로그 목록에서 최근 로그 클릭
2. request_params/response/error_message 확인

검증 포인트:
- 입력값이 정확히 기록된다.
- 에러 시 원인을 바로 파악 가능하다.

---

## 3. Lab 3 - HTTP API 만들기

목표: 외부 API를 프록시하는 `http` 타입 API를 만든다.

### Step 1. New API

- API Name: `external_status_proxy`
- Method: `GET`
- Endpoint: `/runtime/external-status`
- Logic Type: `http`

### Step 2. HttpFormBuilder 입력

- URL: `https://example.internal/status`
- Method: `GET`
- Query Params:
  - `service`: `{{params.service_name}}`
- Headers:
  - `X-Tenant-Id`: `{{params.tenant_id}}`

### Step 3. Dry-run

`Test HTTP (Dry-run)` 실행

검증 포인트:
- 2xx일 때 응답 본문이 표시된다.
- 4xx/5xx면 에러 메시지가 보인다.

### Step 4. 저장 후 Test 탭 실행

Params JSON:

```json
{
  "tenant_id": "t1",
  "service_name": "ops-core"
}
```

검증 포인트:
- 응답시간이 과도하게 길지 않다.
- 실패 시 재현 가능한 로그가 남는다.

---

## 4. Lab 4 - Python API 만들기

목표: 입력 배열을 집계하는 Python API를 만든다.

### Step 1. New API

- API Name: `metrics_normalizer`
- Method: `POST`
- Endpoint: `/runtime/metrics-normalizer`
- Logic Type: `python`

### Step 2. PythonBuilder 작성

```python
def main(params, input_payload):
    device_id = params.get("device_id", "unknown")
    values = input_payload.get("values", []) if input_payload else []

    if not isinstance(values, list):
        raise ValueError("values must be list")

    avg = sum(values) / len(values) if values else 0
    return {
        "device_id": device_id,
        "count": len(values),
        "avg": avg,
        "max": max(values) if values else 0,
        "min": min(values) if values else 0
    }
```

검증 포인트:
- `main(params, input_payload)` 시그니처 준수
- 반환값이 JSON 직렬화 가능

### Step 3. Dry-run

`Test Python (Dry-run)` 실행

### Step 4. Test 탭 실행

Params JSON:
```json
{"device_id": "GT-01"}
```

Input JSON:
```json
{"values": [10, 20, 30, 40]}
```

검증 포인트:
- `avg=25`, `count=4`로 출력

---

## 5. Lab 5 - Script API 만들기 (language 선택)

목표: Script 타입의 기본 실행 구조를 익힌다. Python 또는 JavaScript 언어를 선택하여 데이터 변환 스크립트를 작성하고 테스트까지 완료한다.

### Script 타입과 Python 타입의 차이

- `python` 타입: PythonBuilder (Monaco 에디터)를 사용하며, `main(params, input_payload)` 시그니처가 고정이다.
- `script` 타입: 언어 선택이 가능하고 (`python` 또는 `javascript`), 저장 시 `logic_spec`에 `{ language: "python" }` 또는 `{ language: "javascript" }`가 기록된다.
- 백엔드에서 script 타입은 `script_executor.py`를 통해 별도 프로세스(`script_executor_runner.py`)로 격리 실행된다.
- 실행 타임아웃은 `runtime_policy.script.timeout_ms` (기본 5000ms), 최대 응답 크기는 `runtime_policy.script.max_response_bytes` (기본 1MB)로 제한된다.

### Step 1. New API

1. `/api-manager` 접속
2. 왼쪽 하단 `New API` 클릭
3. Definition 탭에 아래 값 입력

- API Name: `script_transform_demo`
- Method: `POST`
- Endpoint: `/runtime/script-transform-demo`
- Description: `JSON 입력을 정규화하고 통계를 계산하는 스크립트`
- Tags: `script,transform,demo`
- Active: 체크
- Created By: `ops-builder`

검증 포인트:
- Name과 Endpoint가 모두 입력된 상태에서 하단에 오류가 없다.

### Step 2. Param Schema 및 Runtime Policy 입력

Param Schema:
```json
{
  "type": "object",
  "properties": {
    "device_id": {"type": "string"},
    "normalize": {"type": "boolean", "default": true}
  },
  "required": ["device_id"]
}
```

Runtime Policy -- script 타입 전용 설정을 포함한다:
```json
{
  "timeout_ms": 5000,
  "allow_runtime": true,
  "script": {
    "timeout_ms": 3000,
    "max_response_bytes": 524288
  }
}
```

검증 포인트:
- `allow_runtime: true`가 반드시 있어야 한다. 없으면 실행 시 "Script execution is disabled for this API" 오류가 발생한다.

### Step 3. Logic 탭 이동 및 Script language 선택

1. `Logic` 탭 클릭
2. Logic Type 버튼에서 `Script` 선택
3. Language 선택 드롭다운에서 `python` 선택

언어 선택 지침:
- `python`: pandas/numpy 등 데이터 라이브러리 활용이 필요할 때, 또는 팀 표준이 Python인 경우 선택.
- `javascript`: 경량 JSON 변환이나 문자열 처리가 주 목적일 때 선택.
- 저장 시 `logic_spec: { language: "python" }` 형태로 기록되어, 백엔드가 실행 환경을 결정한다.

### Step 4. Script 코드 작성

아래 코드를 Script 에디터에 입력한다.

```python
import json
import math

def main(params, input_payload):
    """
    입력 센서 데이터를 정규화하고 통계를 계산한다.

    params: {"device_id": str, "normalize": bool}
    input_payload: {"readings": [{"ts": str, "value": float}, ...]}

    반환: {"device_id", "count", "mean", "std", "min", "max", "normalized": [...]}
    """
    device_id = params.get("device_id", "unknown")
    normalize = params.get("normalize", True)
    readings = []

    if input_payload and isinstance(input_payload.get("readings"), list):
        readings = input_payload["readings"]

    if not readings:
        return {
            "device_id": device_id,
            "count": 0,
            "mean": 0,
            "std": 0,
            "min": 0,
            "max": 0,
            "normalized": []
        }

    values = [float(r.get("value", 0)) for r in readings]
    count = len(values)
    mean = sum(values) / count
    variance = sum((v - mean) ** 2 for v in values) / count
    std = math.sqrt(variance)

    result = {
        "device_id": device_id,
        "count": count,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": min(values),
        "max": max(values),
    }

    if normalize and std > 0:
        result["normalized"] = [
            {"ts": r.get("ts"), "z_score": round((float(r.get("value", 0)) - mean) / std, 4)}
            for r in readings
        ]
    else:
        result["normalized"] = [
            {"ts": r.get("ts"), "z_score": 0.0}
            for r in readings
        ]

    return result
```

입출력 계약 (I/O Contract):
- 입력 `params`: `device_id` (필수 문자열), `normalize` (선택 불리언, 기본 true)
- 입력 `input_payload`: `readings` 배열 -- 각 원소는 `{"ts": "타임스탬프", "value": 숫자}`
- 출력: JSON 직렬화 가능한 dict. `device_id`, `count`, `mean`, `std`, `min`, `max`, `normalized` 배열 포함.
- 반환값이 dict가 아니거나 JSON 직렬화 불가하면 "Invalid JSON from script runner" 오류가 발생한다.

검증 포인트:
- `main(params, input_payload)` 시그니처를 준수한다 (script 타입도 동일).
- 외부 라이브러리 import는 런타임 환경에 설치된 패키지만 사용 가능하다.

### Step 5. Dry-run 실행

1. Logic 탭 하단의 `Test Script (Dry-run)` 클릭
2. 결과 패널에서 실행 성공 여부 확인

검증 포인트:
- 에러 없이 실행 완료된다.
- duration_ms가 `script.timeout_ms` (3000) 이내이다.

### Step 6. 저장

1. `Create API` 클릭
2. 상태 메시지 `API created` 확인

검증 포인트:
- Left Pane 목록에 `script_transform_demo`가 표시된다.
- 저장 payload에 `logic_spec: { language: "python" }`이 포함된다.

### Step 7. Test 탭 실행

1. Test 탭 이동
2. 아래 값 입력

Params JSON:
```json
{
  "device_id": "SENSOR-07",
  "normalize": true
}
```

Input JSON:
```json
{
  "readings": [
    {"ts": "2026-02-08T10:00:00Z", "value": 22.5},
    {"ts": "2026-02-08T10:05:00Z", "value": 23.1},
    {"ts": "2026-02-08T10:10:00Z", "value": 21.8},
    {"ts": "2026-02-08T10:15:00Z", "value": 24.0},
    {"ts": "2026-02-08T10:20:00Z", "value": 22.0}
  ]
}
```

- Limit: `200`
- Executed by: `ops-builder`

3. `Execute API` 클릭

기대 출력:
```json
{
  "device_id": "SENSOR-07",
  "count": 5,
  "mean": 22.68,
  "std": 0.7918,
  "min": 21.8,
  "max": 24.0,
  "normalized": [
    {"ts": "2026-02-08T10:00:00Z", "z_score": -0.2273},
    {"ts": "2026-02-08T10:05:00Z", "z_score": 0.5306},
    {"ts": "2026-02-08T10:10:00Z", "z_score": -1.1116},
    {"ts": "2026-02-08T10:15:00Z", "z_score": 1.6664},
    {"ts": "2026-02-08T10:20:00Z", "z_score": -0.8589}
  ]
}
```

검증 포인트:
- status가 `success`이다.
- `count`가 5, `mean`이 약 22.68이다.
- `normalized` 배열의 길이가 readings 배열과 동일하다.
- 실행 로그 목록에 새 항목이 추가된다.
- Script 타입은 실행/지원 범위를 팀 정책과 함께 운영한다.
- 저장/버전 관리는 다른 로직 타입과 동일하게 동작한다.

---

## 6. Lab 6 - Workflow API 만들기 (순차 파이프라인)

목표: SQL -> Script(Python) -> Script(HTTP 호출)를 연결한 Workflow를 만든다. WorkflowBuilder의 시각적 노드 편집과 JSON 스펙 구조를 이해하고, 노드 간 데이터 전달 방식을 실습한다.

### Workflow 실행 구조 이해

Workflow는 `logic_spec`에 정의된 노드 배열을 순차적으로 실행한다. 핵심 규칙:
- 노드 타입은 현재 `sql`과 `script` 두 가지만 지원된다 (HTTP 호출이 필요하면 script 안에서 처리).
- 각 노드는 `api_id`로 기존에 저장된 API를 참조한다. 즉 노드가 실행할 로직은 미리 등록된 API에서 가져온다.
- 노드 간 데이터 전달은 `{{steps.{node_id}.rows}}` 또는 `{{steps.{node_id}.output.{key}}}` 템플릿으로 수행한다.
- 실패 전파: 어떤 노드에서 오류가 발생하면 즉시 전체 워크플로우가 중단된다 (fail-fast). 이후 노드는 실행되지 않는다.

### Step 1. 사전 준비 -- 참조할 API 3개 생성

Workflow 노드가 참조할 API를 먼저 생성해야 한다. Lab 1 (SQL), Lab 4 (Python)에서 생성한 API를 사용하거나, 아래 3개를 새로 만든다.

| 순서 | API Name | Logic Type | 용도 |
|---|---|---|---|
| A | `wf_fetch_metrics` | sql | 디바이스별 원본 메트릭 조회 |
| B | `wf_summarize` | script (python) | 조회 결과를 집계 변환 |
| C | `wf_notify_webhook` | script (python) | 집계 결과를 외부 webhook으로 전송 |

각 API 생성 후 `api_id`를 기록해 둔다 (Left Pane 목록에서 확인 또는 API 생성 응답에서 추출).

검증 포인트:
- 3개 API 모두 Test 탭에서 개별 실행이 성공한다.
- 각 API의 `api_id`를 메모해 둔다.

### Step 2. New Workflow API 생성

1. `New API` 클릭
2. Definition 입력:

- API Name: `device_metrics_pipeline`
- Method: `POST`
- Endpoint: `/runtime/device-metrics-pipeline`
- Description: `SQL 조회 -> Python 집계 -> Webhook 전송 3단계 파이프라인`
- Tags: `workflow,pipeline,metrics`
- Active: 체크
- Created By: `ops-builder`

Param Schema:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string"},
    "device_id": {"type": "string"}
  },
  "required": ["tenant_id", "device_id"]
}
```

Runtime Policy:
```json
{
  "timeout_ms": 15000,
  "allow_runtime": true,
  "max_rows": 500
}
```

### Step 3. Logic 탭 -- WorkflowBuilder 노드 구성

1. `Logic` 탭 클릭
2. Logic Type에서 `Workflow` 선택
3. WorkflowBuilder 캔버스가 표시된다.

WorkflowBuilder 조작법:
- `+ SQL`, `+ HTTP`, `+ Python` 버튼으로 노드를 추가한다.
- 노드를 드래그하여 위치를 조정한다.
- 노드의 핸들(연결점)을 드래그하여 다른 노드에 연결한다 (화살표 엣지 생성).
- 노드를 클릭하면 하단에 설정 패널이 나타난다 (Label, SQL Query/Python Code/URL 편집).
- Delete 키로 선택된 노드나 엣지를 삭제한다.
- `Save` 버튼으로 현재 캔버스를 JSON으로 직렬화한다.

4. 노드 3개 추가: SQL 1개, Python 2개
5. 노드를 순서대로 연결: A -> B -> C

### Step 4. Workflow Spec JSON 직접 편집

WorkflowBuilder에서 생성된 JSON을 확인하거나, 아래 JSON을 Logic Body에 직접 입력한다.

`{api_id}` 부분을 Step 1에서 기록한 실제 api_id로 교체한다.

```json
{
  "name": "device_metrics_pipeline",
  "version": 1,
  "nodes": [
    {
      "id": "fetch_metrics",
      "type": "sql",
      "api_id": "{wf_fetch_metrics의 api_id}",
      "params": {
        "tenant_id": "{{params.tenant_id}}",
        "device_id": "{{params.device_id}}"
      },
      "limit": 200
    },
    {
      "id": "summarize",
      "type": "script",
      "api_id": "{wf_summarize의 api_id}",
      "params": {
        "device_id": "{{params.device_id}}"
      },
      "input": {
        "rows": "{{steps.fetch_metrics.rows}}"
      }
    },
    {
      "id": "notify",
      "type": "script",
      "api_id": "{wf_notify_webhook의 api_id}",
      "params": {
        "webhook_url": "https://example.internal/webhook/metrics"
      },
      "input": {
        "summary": "{{steps.summarize.output}}"
      }
    }
  ],
  "edges": [
    {"source": "fetch_metrics", "target": "summarize"},
    {"source": "summarize", "target": "notify"}
  ]
}
```

노드 매핑 구문 상세:

| 패턴 | 설명 | 예시 |
|---|---|---|
| `{{params.field}}` | 워크플로우 호출 시 전달된 파라미터 참조 | `{{params.tenant_id}}` -> "t1" |
| `{{steps.{node_id}.rows}}` | 이전 SQL 노드의 전체 결과 행 참조 | `{{steps.fetch_metrics.rows}}` -> [{...}, ...] |
| `{{steps.{node_id}.output}}` | 이전 Script 노드의 전체 출력 참조 | `{{steps.summarize.output}}` -> {"count": 5, ...} |
| `{{steps.{node_id}.output.key}}` | 이전 Script 노드 출력에서 특정 키 참조 | `{{steps.summarize.output.count}}` -> 5 |

검증 포인트:
- `version`은 반드시 `1`이어야 한다 (다른 값은 "Unsupported workflow spec version" 오류).
- 모든 노드에 고유한 `id`가 있어야 한다 (중복 시 "Duplicate node id" 오류).
- 모든 노드에 `api_id`가 있어야 한다 (누락 시 "Node missing api_id" 오류).
- 노드 타입은 `sql` 또는 `script`만 허용된다 ("Unsupported node type" 오류).

### Step 5. 오류 전파 동작 이해

Workflow는 fail-fast 방식으로 동작한다:

1. Node A (fetch_metrics) 실행 성공 -> `steps_context["fetch_metrics"]`에 결과 저장
2. Node B (summarize) 실행 중 오류 발생 -> 즉시 HTTPException 발생
3. Node C (notify)는 실행되지 않음
4. 전체 Workflow 상태: `fail`, error_message에 실패 노드 정보 기록

각 노드의 실행 결과는 `record_exec_step()`으로 개별 기록되므로, 어떤 노드에서 실패했는지 실행 로그에서 정확히 확인할 수 있다.

검증 포인트:
- 중간 노드 실패 시 이후 노드가 실행되지 않는다.
- 실행 로그에 실패 노드의 `node_id`, `error_message`, `duration_ms`가 기록된다.

### Step 6. Dry-run 실행

1. Logic 탭 하단 `Test Workflow (Dry-run)` 클릭
2. 결과 패널에서 각 노드의 상태 확인

검증 포인트:
- 노드가 `fetch_metrics` -> `summarize` -> `notify` 순서로 실행된다.
- 각 노드의 `status`, `duration_ms`가 표시된다.
- 실패 노드가 있으면 해당 노드의 `error_message`가 명확히 표시된다.

### Step 7. 저장

1. `Create API` 클릭
2. `API created` 확인

### Step 8. Test 탭 실행

1. Test 탭 이동
2. 아래 값 입력

Params JSON:
```json
{
  "tenant_id": "t1",
  "device_id": "GT-01"
}
```

Input JSON:
```json
{}
```

- Limit: `200`
- Executed by: `ops-builder`

3. `Execute API` 클릭

기대 출력 구조 (WorkflowExecuteResult):
```json
{
  "steps": [
    {
      "node_id": "fetch_metrics",
      "node_type": "sql",
      "status": "success",
      "duration_ms": 45,
      "row_count": 100,
      "columns": ["device_id", "metric_name", "metric_value", "collected_at"]
    },
    {
      "node_id": "summarize",
      "node_type": "script",
      "status": "success",
      "duration_ms": 120,
      "row_count": 0,
      "output": {"device_id": "GT-01", "count": 100, "mean": 45.3, "std": 12.1}
    },
    {
      "node_id": "notify",
      "node_type": "script",
      "status": "success",
      "duration_ms": 230,
      "row_count": 0,
      "output": {"webhook_status": 200, "message": "OK"}
    }
  ],
  "final_output": {"webhook_status": 200, "message": "OK"},
  "references": [
    {"node_id": "fetch_metrics", "node_type": "sql", "params": {"tenant_id": "t1", "device_id": "GT-01"}},
    {"node_id": "summarize", "node_type": "script"},
    {"node_id": "notify", "node_type": "script"}
  ]
}
```

검증 포인트:
- `steps` 배열에 3개 노드 결과가 순서대로 포함된다.
- `final_output`은 마지막 노드(notify)의 출력과 동일하다.
- `references` 배열에 각 노드의 실행 참조 정보가 기록된다.
- 중간 노드 실패 시 `steps`에는 실패 노드까지만 포함되고, 이후 노드는 없다.

---

## 7. Lab 7 - System API(Discovered/Registered) 가져와 Custom으로 전환

목표: 읽기 전용 시스템 엔드포인트를 Custom API로 가져와 편집한다. Discovered와 Registered의 차이를 이해하고, Import 시 어떤 메타데이터가 보존되는지 확인한다.

### Discovered vs Registered 개념 정리

| 구분 | Discovered | Registered |
|---|---|---|
| 데이터 출처 | OpenAPI 스펙 또는 라우터 스캔에서 자동 수집 | 서버 DB에 등록된 시스템 API (`scope=system`) |
| DB 저장 여부 | 저장되지 않음 (메모리/캐시에만 존재) | DB 테이블에 저장됨 |
| 편집 가능 여부 | 읽기 전용 (모든 필드 비활성) | 읽기 전용 (단, Param Schema/Runtime Policy는 Registered에서 편집 가능) |
| 표시 정보 | method, path, operationId, summary, description, tags, parameters, requestBody, responses | 전체 API 정의 (name, logic_body 포함) |
| source 필드 | `"openapi"` 또는 `"router"` | `"server"` 또는 `"local"` |
| Import 시 보존 항목 | method, path, description, tags, parameters, requestBody, responses | 전체 정의 복사 |
| 주 사용 목적 | 백엔드에 어떤 엔드포인트가 존재하는지 탐색 | 이미 등록된 시스템 API 확인 및 Custom으로 복제 |

### 언제 Import하고 언제 새로 만드는가

**Import를 권장하는 경우:**
- 기존 시스템 엔드포인트의 파라미터/응답 구조를 그대로 활용하면서 로직만 커스텀하려 할 때
- Discovered 엔드포인트의 OpenAPI 메타데이터(parameters, requestBody, responses)를 Param Schema에 자동 반영하고 싶을 때
- 팀에서 운영 중인 시스템 API를 개인 작업공간에서 실험하고 싶을 때

**새로 만드는 것이 나은 경우:**
- 기존 엔드포인트와 전혀 다른 파라미터/로직이 필요할 때
- 시스템 엔드포인트가 존재하지 않는 완전 신규 기능일 때
- Import 후 Definition을 대부분 수정해야 할 때 (오히려 작업이 더 많아짐)

### Step 1. System Scope 활성화 확인

1. 환경변수 `NEXT_PUBLIC_ENABLE_SYSTEM_APIS=true`가 설정되어 있는지 확인
2. 미설정 시 `.env.local` 파일에 추가 후 프론트엔드 재시작

검증 포인트:
- Left Pane 상단에 `Custom`과 `System` 두 버튼이 모두 표시된다.

### Step 2. Scope 전환 및 Sub-View 선택

1. Left Pane에서 `System` 클릭
2. 하위 탭에서 `Discovered` 선택

검증 포인트:
- "Discovered endpoints are read-only" 안내 문구가 표시된다.
- "Discovered from source (OpenAPI). These are not DB-registered APIs." 설명이 표시된다.
- Last fetch 시각과 Status가 표시된다 (정상이면 `ok`).
- Discovered 목록에 백엔드에서 스캔된 엔드포인트들이 나열된다.

### Step 3. 엔드포인트 탐색 및 선택

1. 검색 필드에 대상 경로의 일부를 입력한다 (예: `/health` 또는 `/api-manager`)
2. 목록에서 대상 엔드포인트를 클릭한다
3. Center Pane에 해당 엔드포인트의 상세 정보가 표시된다:
   - Summary (요약 설명)
   - Description의 각 줄 (제약/조건 정보)
   - `Import to Custom` 버튼

검증 포인트:
- 선택한 엔드포인트의 method와 path가 정확히 표시된다.
- Summary나 Description에 해당 엔드포인트의 사용 제약이 설명된다.

### Step 4. Import to Custom 실행

1. `Import to Custom` 버튼 클릭
2. 자동으로 Scope가 `Custom`으로 전환된다
3. Definition 탭이 자동으로 활성화된다

Import 시 자동으로 채워지는 필드:

| 필드 | 값 출처 | 예시 |
|---|---|---|
| API Name | endpoint의 summary 또는 `"{method} {path}"` | "Health Check" 또는 "GET /health" |
| Method | endpoint의 method (POST이면 POST, 나머지는 GET) | POST |
| Endpoint | `/api-manager/imported{원본 path}` 접두사 추가 | `/api-manager/imported/health` |
| Description | `"Imported from discovered endpoint {method} {path}"` | "Imported from discovered endpoint GET /health" |
| Tags | endpoint의 tags 배열 | ["system", "health"] |
| Param Schema | `{ parameters, requestBody, responses, source: "discovered" }` | OpenAPI 파라미터 구조 전체 보존 |
| Runtime Policy | `{}` (비어 있음 -- 수동 설정 필요) | {} |
| Logic Body | `SELECT 1` (플레이스홀더) | SELECT 1 |
| Logic Type | `sql` (기본값) | sql |
| Created By | `"imported"` | imported |

검증 포인트:
- "System API imported into Custom (unsaved)." 상태 메시지가 표시된다.
- Definition 폼에 위 필드들이 자동으로 채워져 있다.
- Param Schema에 원본 엔드포인트의 parameters, requestBody, responses 정보가 `source: "discovered"` 태그와 함께 보존되어 있다.
- 아직 저장되지 않은 상태이다 (unsaved).

### Step 5. 커스텀 로직 작성

Import된 API의 Logic Body는 `SELECT 1` 플레이스홀더이므로, 실제 로직으로 교체한다.

1. `Logic` 탭 이동
2. Logic Type을 목적에 맞게 변경 (sql, http, python, script, workflow)
3. 실제 로직을 작성

예시 -- Import한 `/health` 엔드포인트를 HTTP 프록시로 전환:
- Logic Type: `http`
- URL: `http://localhost:8000/health`
- Method: `GET`
- Headers: `{}`
- Body: `{}`

### Step 6. Runtime Policy 설정 및 저장

Import 시 Runtime Policy가 비어 있으므로 반드시 설정한다:

```json
{
  "timeout_ms": 5000,
  "allow_runtime": true,
  "max_rows": 200
}
```

1. Definition 탭에서 Runtime Policy 입력
2. `Create API` 클릭 (새 API로 생성)
3. `API created` 확인

### Step 7. Test 탭에서 동작 확인

1. Test 탭 이동
2. Params JSON 입력 후 Execute API 실행

검증 포인트:
- Import된 API가 Custom 목록에 표시된다.
- 원본 시스템 API는 여전히 System > Discovered에 읽기 전용으로 남아 있다.
- Custom 복제본만 수정 및 실행 가능하다.
- 원본의 OpenAPI 파라미터 정보가 Param Schema에 보존되어 있어, 향후 파라미터 검증에 활용 가능하다.

---

## 8. Lab 8 - 버전 관리와 롤백

목표: 변경 후 문제를 재현하고 이전 버전으로 복구한다. 버전 히스토리 조회, 비교, 롤백 절차를 curl 명령어로 직접 실습한다.

### 버전 관리 구조

API를 생성하거나 수정할 때마다 `ApiDefinitionVersion` 레코드가 자동으로 생성된다. 각 버전 레코드에는:
- `version`: 순차 증가 정수 (1, 2, 3, ...)
- `change_type`: `"create"`, `"update"`, `"rollback"` 중 하나
- `change_summary`: 변경 내용 요약 (롤백 시 "Rolled back from vN to vM" 형태)
- `snapshot`: 해당 시점의 전체 API 정의 스냅샷 (name, method, path, logic, runtime_policy 등)
- `created_by`: 변경 수행자
- `created_at`: 변경 시각

### Step 1. 정상 상태 확인 (기준선 설정)

1. Lab 1에서 생성한 `device_metrics_list` API를 선택한다
2. Test 탭에서 정상 실행을 확인한다
3. 이 시점의 버전이 기준선(baseline)이 된다

검증 포인트:
- Test 실행이 `success`로 완료된다.
- 현재 버전 번호를 기록한다.

### Step 2. 의도적 변경 (오류 유발)

1. Logic 탭 이동
2. SQL 쿼리를 의도적으로 오류가 나도록 수정한다:

```sql
SELECT device_id, metric_name, metric_value, collected_at
FROM tb_metrics_WRONG_TABLE
WHERE tenant_id = :tenant_id
  AND device_id = :device_id
ORDER BY collected_at DESC
LIMIT 100
```

3. `Update API` 클릭
4. `API updated` 확인

검증 포인트:
- 저장이 성공한다 (SQL 검증은 Dry-run에서 수행되므로 저장 자체는 가능).
- 새 버전이 자동으로 생성된다.

### Step 3. 오류 재현

1. Test 탭에서 동일 파라미터로 실행

Params JSON:
```json
{
  "tenant_id": "t1",
  "device_id": "GT-01"
}
```

2. `Execute API` 클릭
3. 오류 확인

검증 포인트:
- status가 `fail`이다.
- error_message에 테이블 미존재 관련 에러가 표시된다.
- execution logs에 실패 기록이 남는다.

### Step 4. 버전 히스토리 조회 (curl)

```bash
# {api_id}를 실제 값으로 교체한다
curl -s "http://localhost:8000/api-manager/{api_id}/versions" | python3 -m json.tool
```

기대 응답 구조:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "api_id": "{api_id}",
    "versions": [
      {
        "version": 2,
        "change_type": "update",
        "change_summary": null,
        "created_by": "user-uuid",
        "created_at": "2026-02-08T14:30:00",
        "is_current": true,
        "snapshot": {
          "id": "{api_id}",
          "name": "device_metrics_list",
          "logic": "SELECT ... FROM tb_metrics_WRONG_TABLE ...",
          "mode": "sql",
          "...": "..."
        }
      },
      {
        "version": 1,
        "change_type": "create",
        "change_summary": null,
        "created_by": "user-uuid",
        "created_at": "2026-02-08T14:00:00",
        "is_current": false,
        "snapshot": {
          "id": "{api_id}",
          "name": "device_metrics_list",
          "logic": "SELECT ... FROM tb_metrics ...",
          "mode": "sql",
          "...": "..."
        }
      }
    ]
  }
}
```

검증 포인트:
- `versions` 배열이 최신 버전부터 내림차순으로 정렬된다.
- `is_current: true`인 항목이 현재 적용 중인 버전이다.
- 각 버전의 `snapshot.logic`을 비교하여 어떤 변경이 있었는지 확인한다.

### Step 5. 버전 비교 가이드

두 버전의 `snapshot`을 비교하여 변경점을 파악한다:

1. 위 응답에서 version 1과 version 2의 `snapshot.logic`을 비교한다:
   - v1: `"SELECT ... FROM tb_metrics ..."`
   - v2: `"SELECT ... FROM tb_metrics_WRONG_TABLE ..."`
2. 차이점: 테이블 이름이 변경된 것을 확인한다.

비교 시 주요 확인 필드:
- `snapshot.logic`: 실행 로직 변경 여부
- `snapshot.runtime_policy`: 정책 변경 여부
- `snapshot.method` / `snapshot.path`: 엔드포인트 변경 여부
- `snapshot.is_enabled`: 활성화 상태 변경 여부

언제 버전 히스토리를 사용하는가:
- 최근 변경으로 인한 오류 원인을 추적할 때
- 어떤 시점에 누가 무엇을 변경했는지 감사(audit)할 때
- 롤백 대상 버전을 선택하기 전에 내용을 확인할 때

### Step 6. 롤백 실행 (curl)

버전을 지정하지 않으면 바로 이전 버전으로 롤백한다. 특정 버전으로 롤백하려면 `?version=N`을 사용한다.

```bash
# 방법 1: 바로 이전 버전으로 롤백 (version 파라미터 생략)
curl -s -X POST "http://localhost:8000/api-manager/{api_id}/rollback" | python3 -m json.tool

# 방법 2: 특정 버전으로 롤백
curl -s -X POST "http://localhost:8000/api-manager/{api_id}/rollback?version=1" | python3 -m json.tool
```

기대 응답:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "api_id": "{api_id}",
    "rolled_back_to_version": 1,
    "new_version": 3,
    "snapshot": {
      "id": "{api_id}",
      "name": "device_metrics_list",
      "logic": "SELECT ... FROM tb_metrics ...",
      "mode": "sql",
      "...": "..."
    }
  }
}
```

검증 포인트:
- `rolled_back_to_version`이 대상 버전 번호와 일치한다.
- `new_version`이 기존 최신 버전 + 1이다 (롤백도 새 버전 레코드를 생성한다).
- `snapshot`이 대상 버전의 내용과 동일하다.

### Step 7. 롤백 후 검증

1. Test 탭에서 동일 파라미터로 재실행

```json
{
  "tenant_id": "t1",
  "device_id": "GT-01"
}
```

2. `Execute API` 클릭

검증 포인트:
- status가 다시 `success`로 복귀한다.
- 결과 데이터가 정상적으로 반환된다.
- execution logs에 롤백 후 성공 실행 기록이 남는다.

### Step 8. 롤백 후 버전 히스토리 재확인

```bash
curl -s "http://localhost:8000/api-manager/{api_id}/versions" | python3 -m json.tool
```

기대 결과:
- version 3 (`change_type: "rollback"`, `change_summary: "Rolled back from v2 to v1"`, `is_current: true`)
- version 2 (`change_type: "update"`, `is_current: false`)
- version 1 (`change_type: "create"`, `is_current: false`)

검증 포인트:
- 롤백도 버전 히스토리에 기록되어 추적 가능하다.
- `change_summary`에 어디서 어디로 롤백했는지 명시된다.
- 이전 정상 동작으로 복구되었다.
- 로그에 롤백 후 실행 기록이 남는다.

### 언제 롤백을 사용하는가

| 상황 | 권장 조치 |
|---|---|
| 로직 변경 후 즉시 오류 발견 | 즉시 롤백 (version 미지정으로 바로 이전 복구) |
| 여러 번 수정 후 특정 시점으로 복구 필요 | 버전 히스토리 조회 후 `?version=N`으로 지정 롤백 |
| 설정(runtime_policy) 변경만 문제 | Definition에서 수동 수정이 롤백보다 빠를 수 있음 |
| 롤백 후 추가 수정이 필요 | 롤백 후 Logic 수정 -> Update API (새 버전 생성) |

---

## 9. 운영 표준

### 9.1 저장 전 체크

- Param Schema와 실제 입력이 일치한다.
- Runtime Policy에 timeout/max_rows가 있다.
- 로직 타입이 목적과 맞다.

### 9.2 배포 전 체크

- Dry-run 성공
- Test 탭 정상/오류 케이스 각각 검증
- execution logs에 관측 가능한 데이터 존재

### 9.3 운영 중 체크

- 실패율/지연 추세 관찰
- 에러 로그 주기 점검
- 버전/롤백 절차 문서화

---

## 10. 장애 대응 플레이북

### 10.1 증상: `Failed to load API definitions`

점검 순서:
1. `GET /api-manager/apis` 응답 코드
2. `apps/api/logs/api.log`
3. 인증 토큰/tenant 헤더
4. DB 상태 및 마이그레이션

### 10.2 증상: Dry-run 실패

점검 순서:
1. Logic JSON/코드 문법
2. Param Schema 유효성
3. runtime_policy 파싱 오류

### 10.3 증상: 실행은 되는데 결과가 비정상

점검 순서:
1. request_params 실제 값
2. SQL/HTTP 템플릿 변수 치환 결과
3. workflow 단계별 출력 검토

### 10.4 증상: 응답 지연 증가

점검 순서:
1. SQL 인덱스/실행계획
2. 외부 HTTP 지연
3. timeout 설정 및 한도 재조정

---

## 11. 최종 체크리스트

```text
□ New API에서 정의를 직접 생성했다.
□ SQL/HTTP/Python/Workflow를 각각 1회 이상 실행했다.
□ Dry-run과 Execute의 차이를 이해했다.
□ execution logs에서 실패 원인을 추적할 수 있다.
□ 버전 조회와 롤백 절차를 수행했다.
□ 운영 체크리스트를 팀 표준으로 정리했다.
```

---

## 12. 참고 파일

### Frontend (Next.js)

| 파일 | 줄 수 | 역할 | 주요 함수/위치 |
|---|---|---|---|
| `apps/web/src/app/api-manager/page.tsx` | 2264 | API Manager 메인 페이지. 전체 상태 관리, 3개 탭 렌더링, Scope 전환, CRUD, 실행, 로그 조회를 포함하는 단일 컴포넌트. | `buildSavePayload()` (L201): 저장 페이로드 구성. `saveApiToServer()` (L266): 서버 저장/업데이트. `handleExecute()` (L1075): API 실행. `handleImportDiscoveredEndpoint()` (L1010): System -> Custom Import. `fetchExecLogs()` (L518): 실행 로그 조회 (limit=20). |
| `apps/web/src/components/api-manager/SQLQueryBuilder.tsx` | 389 | SQL 로직 편집기. Monaco 에디터 기반. SQL 문법 하이라이팅, 자동완성, 기본 템플릿 제공. | SQL 에디터 컴포넌트, 템플릿 선택 UI. |
| `apps/web/src/components/api-manager/HttpFormBuilder.tsx` | 338 | HTTP 로직 편집기. URL, Method, Headers, Query Params, Body를 폼으로 입력. 템플릿 변수 `{{params.field}}` 사용 가능. | HttpSpec 인터페이스 (url, method, headers, body, params). |
| `apps/web/src/components/api-manager/PythonBuilder.tsx` | 300 | Python 로직 편집기. Monaco 에디터 기반. `main(params, input_payload)` 시그니처의 기본/고급 템플릿 제공. | `PYTHON_TEMPLATES` (L13): basic, data_analysis 등 사전 정의 템플릿. |
| `apps/web/src/components/api-manager/WorkflowBuilder.tsx` | 467 | Workflow 시각적 편집기. ReactFlow 기반. 노드(SQL/HTTP/Python) 추가, 드래그 연결, JSON 직렬화. | `generateWorkflowJSON()` (L137): 캔버스를 JSON으로 변환. `parseWorkflowJSON()` (L161): JSON을 캔버스로 로드. `WorkflowNodeData` 인터페이스 (L28): 노드 데이터 구조. |
| `apps/web/src/components/api-manager/DraftAssistantPanel.tsx` | 187 | AI 드래프트 어시스턴트 패널. BuilderCopilotPanel을 내장하여 자연어로 API 드래프트 생성. Preview/Test/Apply/Save 버튼 제공. | Draft 상태 표시, 오류/경고 배너, Debug 접이식 패널. |

### Frontend 유틸리티

| 파일 | 역할 |
|---|---|
| `apps/web/src/lib/api-manager/types.ts` | 타입 정의. `ScopeType`, `CenterTab`, `LogicType`, `SystemView`, `ApiDefinitionItem`, `DiscoveredEndpoint`, `ExecuteResult`, `WorkflowExecuteResult`, `ApiDraft`, `DraftStatus` 등. |
| `apps/web/src/lib/api-manager/utils.ts` | 상수 및 유틸. `DEFAULT_SCOPE` ("custom"), `SCOPE_LABELS`, `logicTypeLabels` (5종), `DRAFT_STORAGE_PREFIX`, `FINAL_STORAGE_PREFIX`, `tabOptions` (3탭), `draftStatusLabels` (8종). |

### Backend (FastAPI / Python)

| 파일 | 줄 수 | 역할 | 주요 함수/위치 |
|---|---|---|---|
| `apps/api/app/modules/api_manager/router.py` | 901 | API Manager REST 라우터. CRUD, 실행, 버전 관리, 롤백, SQL 검증, Dry-run 엔드포인트 전체 정의. | `list_apis()` (L117): API 목록 조회. `create_or_update_api()` (L178): 생성/업데이트. `execute_api()` (L579): API 실행 (SQL/HTTP/Script/Workflow 분기). `rollback_api()` (L431): 버전 롤백. `get_versions()` (L510): 버전 히스토리. `get_logs()` (L793): 실행 로그 조회. `dry_run()` (L849): Dry-run 실행. |
| `apps/api/app/modules/api_manager/executor.py` | 279 | SQL/HTTP 실행기. SQL 금지 키워드 검사 (INSERT, DELETE 등 차단), 파라미터 바인딩, HTTP 템플릿 렌더링, 실행 로그 기록. | `execute_sql_api()` (L139): SQL 실행. `execute_http_api()` (L200): HTTP 프록시 실행. `validate_select_sql()` (L122): SQL 금지 키워드 검증. `BANNED_KEYWORDS` (L19): 차단 키워드 세트. |
| `apps/api/app/modules/api_manager/script_executor.py` | 119 | Script/Python 실행기. 별도 프로세스(`script_executor_runner.py`)에서 격리 실행. 타임아웃 및 응답 크기 제한. | `execute_script_api()` (L35): 스크립트 실행 진입점. `DEFAULT_SCRIPT_TIMEOUT_MS` (L19): 기본 5000ms. `DEFAULT_OUTPUT_BYTES` (L20): 최대 1MB. |
| `apps/api/app/modules/api_manager/workflow_executor.py` | 314 | Workflow 실행기. 노드 배열 순차 실행, 템플릿 변수 해석 (`{{steps.node_id.rows}}`), 실패 시 즉시 중단 (fail-fast), 노드별 실행 로그 기록. | `execute_workflow_api()` (L35): 워크플로우 실행 진입점. `_render_templates()` (L238): 템플릿 변수 치환. `_evaluate_expression()` (L264): `params.*` / `steps.*` 경로 해석. `PLACEHOLDER_PATTERN` (L19): `{{...}}` 정규식. |
| `apps/api/app/modules/api_manager/runtime_router.py` | 252 | Runtime 라우터. `/runtime/{path}` 경로로 저장된 API를 직접 호출. 슬라이딩 윈도우 속도 제한 (IP당 60초에 120건). | `handle_runtime_request()` (L60): 런타임 요청 핸들러. `_check_rate_limit()` (L33): 속도 제한 검사. `RATE_LIMIT_MAX_REQUESTS` (L26): 120건/분. |


---

## 13. Lab 9 - 실패를 의도적으로 만들고 복구하기

목표: 장애 상황을 안전하게 재현하고 즉시 복구하는 훈련.

### 시나리오 A: SQL 인젝션성 구문 차단 확인

1. SQL Logic에 아래처럼 금지 구문을 추가한다.
```sql
SELECT * FROM tb_metrics; DELETE FROM tb_metrics
```
2. Dry-run 실행

기대 결과:
- 실행 거부
- 금지 키워드/정책 위반 메시지 확인

복구:
1. 쿼리를 SELECT-only로 되돌린다.
2. 재실행 후 정상 결과 확인

### 시나리오 B: Param Schema 불일치

1. schema에 `device_id` required 유지
2. Test Params에서 `device_id`를 제거
3. Execute API 실행

기대 결과:
- validation 실패
- 어떤 필드가 누락됐는지 메시지로 확인 가능

복구:
1. Params JSON에 누락 필드 추가
2. 재실행 성공 확인

### 시나리오 C: HTTP Timeout

1. timeout이 짧은 runtime_policy로 변경
2. 응답이 느린 endpoint 호출
3. Execute API 실행

기대 결과:
- timeout 오류 발생
- execution log에 실패 원인 기록

복구:
1. timeout 상향
2. endpoint 응답시간 점검
3. 재실행 성공 확인

---

## 14. Lab 10 - API를 실제 Runtime 경로로 호출하기

목표: API Manager 내부 테스트를 넘어 실제 런타임 경로를 검증.

### Step 1. Runtime URL 확인

Test 탭 상단 `Runtime URL` 확인.

### Step 2. curl 호출

예시:
```bash
curl -X POST "http://localhost:8000/runtime/device-metrics-list" \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: t1" \
  -d '{"tenant_id":"t1","device_id":"GT-01"}'
```

### Step 3. 응답 확인

검증 포인트:
- `ResponseEnvelope` 형식 유지
- code/message/data 구조 확인

---

## 15. Lab 11 - 실행 로그를 통한 원인 분석 루틴

목표: 실패 원인을 3분 안에 찾는 루틴 체득.

### Step 1. 로그 리스트에서 실패 건 선택

- status: fail
- duration_ms 과다 건 우선 확인

### Step 2. 다음 필드 순서로 확인

1. `request_params`
2. `error_message`
3. `response_status`
4. `duration_ms`
5. logic_type

### Step 3. 원인 카테고리 분류

- 입력 스키마 문제
- 로직 문법 문제
- 외부 endpoint 문제
- 성능/timeout 문제
- 권한/tenant 문제

### Step 4. 수정 후 재검증

- Dry-run -> Test -> Runtime 호출 순서로 재확인

---

## 16. Lab 12 - Workflow 품질 검증 표준

목표: Workflow를 운영 가능한 수준으로 검증.

### 필수 검증 항목

1. 노드 순서 검증
2. 매핑 키 검증 (`params`, `steps.*`)
3. 실패 전파 방식 검증
4. 각 노드 duration 비교
5. 최종 출력 구조 검증

### 권장 테스트 세트

- 정상 입력
- 필수 파라미터 누락
- 중간 노드 실패
- 외부 API timeout
- 빈 결과 입력

### 완료 기준

- 각 테스트 케이스의 기대 결과가 문서화됨
- 실패 케이스에서 운영자가 즉시 조치 가능

---

## 17. Lab 13 - 팀 표준 API 템플릿 만들기

목표: 신규 API 생성 속도와 품질을 동시에 확보.

### 템플릿 필수 항목

1. 표준 Param Schema
2. 표준 Runtime Policy
3. 에러 응답 형태
4. 태그 규칙
5. 로그 필수 필드

### 템플릿 예시 (조회 API)

```json
{
  "param_schema": {
    "type": "object",
    "properties": {
      "tenant_id": {"type": "string"},
      "limit": {"type": "integer", "minimum": 1, "maximum": 1000}
    },
    "required": ["tenant_id"]
  },
  "runtime_policy": {
    "timeout_ms": 5000,
    "max_rows": 500,
    "allow_runtime": true
  }
}
```

---

## 18. 운영 부록 - API 타입별 빠른 점검표

### SQL API 점검표

- SELECT/WITH만 사용
- limit 존재
- tenant 필터 존재
- 파라미터 바인딩 사용

### HTTP API 점검표

- URL/Method 정확
- 인증 헤더 누락 없음
- timeout 정책 존재
- 4xx/5xx 처리 명확

### Python/Script 점검표

- 진입 함수 명확
- 예외 처리 존재
- 반환 구조 일관
- 직렬화 가능 타입만 반환

### Workflow 점검표

- 노드 ID 중복 없음
- 매핑 경로 유효
- 실패 지점 식별 가능
- 최종 출력 검증 완료

---

## 19. 운영 부록 - 권장 질문/검증 시나리오

신규 API 배포 전 아래 질문으로 자체 점검한다.

1. 이 API는 어떤 실패를 가장 자주 겪을까?
2. 실패 로그만 보고 원인을 3분 내 찾을 수 있는가?
3. 롤백 없이 수정 가능한 문제와 즉시 롤백해야 할 문제를 구분했는가?
4. tenant 경계가 깨질 여지가 없는가?
5. 호출량이 늘었을 때 timeout/limit 정책이 충분한가?


---

## 20. 완성 프로젝트 트랙 - 현업용 API 세트 구축

이 섹션은 단일 API가 아니라 실제 운영에 투입할 API 세트를 완성하는 실습이다.

구축 목표:
1. 조회 API 2개
2. 집계 API 1개
3. 워크플로우 API 1개
4. 장애 대응용 보조 API 1개

### 20.1 프로젝트 구조 설계

먼저 아래 표를 그대로 만든다.

| API Name | Type | Endpoint | 목적 |
|---|---|---|---|
| `device_metrics_list` | sql | `/runtime/device-metrics-list` | 원본 조회 |
| `device_metrics_summary` | python | `/runtime/device-metrics-summary` | 집계 변환 |
| `device_health_proxy` | http | `/runtime/device-health-proxy` | 외부 상태 연계 |
| `device_pipeline` | workflow | `/runtime/device-pipeline` | 다단계 처리 |
| `device_diag_helper` | script | `/runtime/device-diag-helper` | 장애 진단 보조 |

검증 포인트:
- Endpoint 네이밍이 일관된다.
- 목적이 겹치지 않는다.

### 20.2 공통 Definition 템플릿 적용

모든 API에 공통으로 아래 정책을 적용한다.

```json
{
  "timeout_ms": 5000,
  "allow_runtime": true,
  "max_rows": 300,
  "audit_enabled": true
}
```

공통 Param Schema 최소 구조:

```json
{
  "type": "object",
  "properties": {
    "tenant_id": {"type": "string"},
    "trace_id": {"type": "string"}
  },
  "required": ["tenant_id"]
}
```

검증 포인트:
- 팀 표준 정책이 API마다 누락되지 않는다.

### 20.3 개발 순서 (권장)

1. SQL API 먼저 완성
2. Python/Script로 가공 API 완성
3. HTTP API 완성
4. Workflow로 통합

왜 이 순서인가:
- 데이터 소스 -> 가공 -> 외부연계 -> 통합 순으로 디버깅이 쉽다.

### 20.4 단계별 구현

#### 단계 A: `device_metrics_list` 생성

1. Lab 1 절차대로 생성
2. 샘플 입력 3종으로 실행
   - 정상 장비
   - 존재하지 않는 장비
   - tenant 누락

검증 포인트:
- 정상/오류 응답이 구분된다.

#### 단계 B: `device_metrics_summary` 생성

입력은 `device_metrics_list` 결과를 가정한다.

예시 코드:
```python
def main(params, input_payload):
    rows = input_payload.get("rows", []) if input_payload else []
    if not rows:
        return {"count": 0, "avg": 0, "max": 0, "min": 0}

    values = [float(r.get("metric_value", 0)) for r in rows]
    return {
        "count": len(values),
        "avg": sum(values) / len(values),
        "max": max(values),
        "min": min(values)
    }
```

검증 포인트:
- 빈 배열/문자열 값에서도 예외 없이 반환.

#### 단계 C: `device_health_proxy` 생성

외부 API 장애를 고려해 timeout을 명시한다.

검증 포인트:
- 2xx/4xx/5xx 각각 로그가 남는다.

#### 단계 D: `device_pipeline` 생성

workflow 순서:
1. SQL fetch
2. Python summarize
3. HTTP enrich

검증 포인트:
- steps 출력이 연쇄적으로 이어진다.
- 중간 실패 지점을 식별 가능.

### 20.5 프로젝트 통합 테스트

아래 테스트 케이스를 순서대로 실행한다.

1. 정상 흐름
2. SQL 결과 없음
3. Python 입력 비정상
4. HTTP timeout
5. workflow 중간 실패

각 케이스 기록표:

| Case | 기대 결과 | 실제 결과 | 조치 |
|---|---|---|---|
| 정상 | success |  |  |
| SQL empty | graceful empty |  |  |
| Python invalid | validation error |  |  |
| HTTP timeout | timeout logged |  |  |
| workflow fail | failed node identified |  |  |

### 20.6 운영 인수인계 패키지 만들기

각 API마다 아래를 남긴다.

1. 목적
2. 입력 예시
3. 출력 예시
4. 대표 에러 3개
5. 복구 절차

### 20.7 완료 판정

```text
□ API 5개가 모두 생성/저장/실행 가능
□ 실패 케이스 재현 및 복구 확인
□ rollback 1회 이상 수행
□ 운영 인수인계 문서까지 작성 완료
```

---

## 21. 튜토리얼 확장 - 실습 기록 시트

아래 템플릿을 복사해서 실습할 때 채운다.

```text
[API 실습 기록]
날짜:
작성자:

1) 생성 API:
2) 테스트 케이스 수:
3) 실패 재현 케이스:
4) 복구 소요 시간:
5) 잔여 이슈:
```

---

## 22. 팀 운영 규칙 샘플

1. API 생성 시 최소 테스트 3개 필수
2. Update 전 baseline 로그 캡처
3. Rollback 절차를 Release Note에 포함
4. runtime_policy 없는 API 배포 금지
5. tenant_id 필터 누락 SQL 배포 금지

---

## 23. API Manager와 Tools 연동 운영 기준

### 23.1 API를 사용하는 대표 경로

1. Runtime API: `/runtime/{path}` 직접 호출
2. Screen/UI 액션: 화면 액션 핸들러에서 API 실행
3. OPS UI-Actions: 운영 액션 플로우에서 API 실행

### 23.2 API 등록 방식

1. 방식 A (권장): `API Manager`에서 API 정의 후 `Tools`로 등록
2. 방식 B: `Admin > Tools`에서 HTTP Tool 직접 생성

권장 기준:
1. 재사용/표준화가 중요한 API는 방식 A 사용
2. 외부 단일 HTTP 연동은 방식 B 허용
3. 운영 배포 전에는 Tool 연결 상태와 실행 로그를 반드시 검증

### 23.3 API-Key/JWT 인증 운영 포인트

1. 기본은 JWT 기반 내부 호출
2. 외부 공개 API는 정책에 따라 API Key 스코프를 분리
3. API Key는 키 발급/폐기/스코프를 운영 정책으로 관리
4. 인증 모드(JWT 전용/API Key 전용/Hybrid)는 Admin 설정 기준으로 통제

---

## 24. Tool 등록 필수 정보 체크리스트

API를 Tool로 등록할 때는 아래 항목을 반드시 점검한다.

1. `name`
- 호출 의도가 드러나는 동사형 이름 사용
- 예: `get_device_status`, `search_documents`

2. `description`
- Tool 선택 근거가 되므로 목적/입력/출력을 명확히 기술
- 모호한 문구(`tool1`, `helper`) 사용 금지

3. `tool_type`
- `http_api`, `database_query`, `graph_query`, `python_script`, `builtin` 중 목적에 맞게 선택

4. `tool_config`
- 실제 호출 정보(url/method/headers/body_template/timeout/retry) 지정
- 동적 값은 템플릿 치환 규칙을 사용

5. `tool_input_schema`
- JSON Schema로 입력 타입/필수값/범위를 선언
- `description`, `required`, `enum/default/min/max`를 구체화

6. `tool_output_schema`
- 응답 형태를 JSON Schema로 명시
- LLM/상위 모듈이 결과 구조를 예측 가능하도록 유지

7. `tags` / `created_by` (권장)
- 분류/추적/감사 대응을 위해 메타데이터 포함

운영 규칙:
1. Tool 등록 후 반드시 dry-run/test 실행
2. 실행 로그에서 latency/error를 확인한 뒤 발행
3. 인증/tenant 정책을 충족하지 않으면 배포 금지

관련 상세 문서:
1. `docs/history/TOOLS_REGISTRATION_DETAILED_INFO.md`

---

## 25. Recent Changes (2026-02-14 to 2026-02-15)

### Workflow Template Mapping 기능 추가
- ✅ 템플릿 변수 매핑: `{{params.*}}`, `{{steps.*.output}}` 자동 치환
- ✅ 워크플로우 전체 데이터 흐름 추적 가능
- ✅ 중간 노드 실패 시 명확한 에러 메시지

### Production Timeout/Retry 정책 내장
- ✅ SQL Tool: 5초 타임아웃
- ✅ HTTP Tool: 10초 타임아웃
- ✅ Workflow Tool: 30초 타임아웃 (노드 시간 포함)
- ✅ Circuit Breaker 패턴 지원 (자동 복구)

### Production Readiness 향상
- API Manager 프로덕션 준비도: 85% → 92%
- 워크플로우 안정성 강화 (fail-fast 명확화)

---

## 26. Workflow Template Mapping 가이드

### 매핑 규칙 상세

| 패턴 | 설명 | 유효성 | 예시 |
|-----|------|--------|------|
| `{{params.field}}` | 워크플로우 입력 파라미터 참조 | Always | `{{params.tenant_id}}` → "t1" |
| `{{steps.{node_id}.rows}}` | SQL 노드 결과 행 배열 | SQL 노드만 | `{{steps.fetch_metrics.rows}}` → [...] |
| `{{steps.{node_id}.output}}` | Script 노드 전체 출력 | Script 노드만 | `{{steps.summarize.output}}` → {...} |
| `{{steps.{node_id}.output.key}}` | Script 노드 출력 특정 키 | Script 노드만 | `{{steps.summarize.output.count}}` → 5 |
| `{{steps.{node_id}.error}}` | 노드 실행 오류 메시지 | 오류 발생 시만 | Error handling에서 사용 |

**매핑 검증 규칙**:
- 참조 노드 ID가 workflow의 선행 노드여야 함
- `steps.*` 참조는 해당 노드가 성공적으로 실행된 후에만 유효
- 실패 노드는 이후 노드에서 참조 불가 (fail-fast)

### 실패 시나리오별 대응

**Scenario A: 중간 노드 실패 시 데이터 전달 불가**

```
fetch_metrics (success)
    ↓
summarize (failure)  ← 여기서 실패 시
    ↓
notify (not executed)  ← 자동으로 실행 안 됨
```

**Remedy**:
1. summarize 노드 파라미터/input 재확인
2. fetch_metrics output 구조 확인 (`{{steps.fetch_metrics.rows}}` 형식)
3. Test 탭에서 동일 입력으로 단계별 재실행

**Scenario B: 템플릿 변수 오타로 인한 null/undefined 참조**

```json
{
  "input": {
    "rows": "{{steps.fetch_metrix.rows}}"  ← 오타 (metrix → metrics)
  }
}
```

**Result**: `null` 전달 → summarize 입력 검증 실패

**Remedy**:
1. 모든 node_id 철저히 검토
2. Test 탭에서 실제 매핑값 확인 후 저장

---

## 27. Production Policies for Workflows

### Timeout 정책

| 노드 타입 | 기본 타임아웃 | 권장 범위 | 조정 기준 |
|----------|-------------|---------|----------|
| **SQL** | 5s | 2s ~ 30s | Query 복잡도에 따라 |
| **HTTP** | 10s | 5s ~ 60s | 외부 API 응답 시간 |
| **Script (Python)** | 3s | 1s ~ 10s | 계산 복잡도에 따라 |
| **Workflow (총합)** | 30s | 10s ~ 120s | 모든 노드 합산 + 여유 |

**설정 방법** (Workflow Definition):
```json
{
  "runtime_policy": {
    "timeout_ms": 30000,
    "allow_runtime": true,
    "max_rows": 500,
    "nodes": [
      {
        "node_id": "fetch_metrics",
        "timeout_ms": 5000
      },
      {
        "node_id": "summarize",
        "timeout_ms": 3000
      }
    ]
  }
}
```

### Retry 정책

**기본 재시도 구성**:
- 최대 재시도: 2회 (총 3회 시도)
- 초기 간격: 500ms
- 최대 간격: 5s
- 지수 백오프 배수: 2배

**설정 예시**:
```json
{
  "nodes": [
    {
      "node_id": "fetch_metrics",
      "retry": {
        "max_attempts": 3,
        "backoff": "exponential",
        "initial_delay_ms": 500,
        "max_delay_ms": 5000
      }
    }
  ]
}
```

### 오류 처리 정책

| 오류 타입 | Retry 여부 | 전파 | 로깅 |
|---------|----------|------|------|
| **SQL: Connection Timeout** | ✅ Yes (3회) | ❌ Fail fast | ERROR |
| **SQL: Row Limit Exceeded** | ❌ No | ❌ Fail fast | WARN |
| **HTTP: Connection Refused** | ✅ Yes (3회) | ❌ Fail fast | ERROR |
| **HTTP: 4xx Client Error** | ❌ No (즉시 실패) | ❌ Fail fast | ERROR |
| **Script: Timeout** | ✅ Yes (2회) | ❌ Fail fast | ERROR |
| **Script: Invalid JSON Output** | ❌ No | ❌ Fail fast | ERROR |

---

## 26. Workflow Template Mapping

### 26.1 파라미터 전달 문법

Workflow의 각 노드 간 데이터 전달은 다음 세 가지 방식으로 수행됩니다:

#### 1. `{{params.X}}` - 사용자 입력 파라미터

사용자가 API 호출 시 전달한 파라미터에 접근합니다.

```json
{
  "nodes": [
    {
      "node_id": "fetch_by_filter",
      "type": "sql",
      "query": "SELECT * FROM devices WHERE region = :region LIMIT :limit",
      "input": {
        "region": "{{params.region}}",
        "limit": "{{params.limit}}"
      }
    }
  ]
}
```

**사용자 호출 예시**:
```bash
POST /api/execute/device_workflow
Content-Type: application/json

{
  "region": "us-east",
  "limit": 100
}
```

#### 2. `{{steps.node_id.rows}}` - 이전 노드 출력 (행 데이터)

이전 노드가 반환한 행 데이터(배열)에 접근합니다.

```json
{
  "nodes": [
    {
      "node_id": "fetch_devices",
      "type": "sql",
      "query": "SELECT device_id, metrics FROM devices LIMIT 10"
    },
    {
      "node_id": "summarize_metrics",
      "type": "script",
      "language": "python",
      "code": "import json\ndevices = {{steps.fetch_devices.rows}}\ntotal = len(devices)\nreturn {\"count\": total, \"devices\": devices}"
    }
  ]
}
```

**데이터 구조 예시**:
```json
// fetch_devices의 output
{
  "rows": [
    {"device_id": "d1", "metrics": {"cpu": 45}},
    {"device_id": "d2", "metrics": {"cpu": 78}}
  ]
}

// summarize_metrics의 script 내부
devices = [
  {"device_id": "d1", "metrics": {"cpu": 45}},
  {"device_id": "d2", "metrics": {"cpu": 78}}
]
```

#### 3. `{{context.X}}` - 실행 컨텍스트 변수

실행 시점의 시스템 정보 (사용자, 테넌트, 시간 등)에 접근합니다.

```json
{
  "nodes": [
    {
      "node_id": "audit_log",
      "type": "sql",
      "query": "INSERT INTO audit_log (executed_by, tenant_id, executed_at, action) VALUES (:user, :tenant, :time, :action)",
      "input": {
        "user": "{{context.user_id}}",
        "tenant": "{{context.tenant_id}}",
        "time": "{{context.execution_time}}",
        "action": "device_fetch"
      }
    }
  ]
}
```

**context 변수 목록**:
- `context.user_id`: 실행 사용자 ID
- `context.tenant_id`: 테넌트 ID
- `context.execution_time`: ISO 8601 형식 실행 시간
- `context.request_id`: 요청 추적 ID

### 26.2 Template 변수 Best Practices

#### Best Practice 1: 명시적 타입 선언

```json
// ❌ 나쁜 예: 문자열과 숫자 혼재
{
  "query": "SELECT * FROM devices WHERE id = {{params.device_id}} AND active = {{params.active}}"
}

// ✅ 좋은 예: 파라미터 스키마 명시
{
  "definition": {
    "param_schema": {
      "device_id": {"type": "string", "description": "Device ID"},
      "active": {"type": "boolean", "description": "Active filter"}
    }
  },
  "nodes": [
    {
      "query": "SELECT * FROM devices WHERE id = :device_id AND active = :active",
      "input": {
        "device_id": "{{params.device_id}}",
        "active": "{{params.active}}"
      }
    }
  ]
}
```

#### Best Practice 2: 단계별 검증

```json
{
  "nodes": [
    {
      "node_id": "validate_input",
      "type": "script",
      "code": "import json\nif not {{params.region}}:\n  raise ValueError('region is required')\nreturn {'status': 'valid'}"
    },
    {
      "node_id": "fetch_data",
      "type": "sql",
      "depends_on": ["validate_input"],
      "query": "SELECT * FROM data WHERE region = :region",
      "input": {"region": "{{params.region}}"}
    }
  ]
}
```

#### Best Practice 3: 출력 구조 문서화

```python
# script 노드에서 출력 구조 명시
def execute():
    """
    Return structure:
    {
        "total_devices": int,
        "summary": {
            "online": int,
            "offline": int
        },
        "devices": [
            {"id": str, "status": str, "metrics": dict}
        ]
    }
    """
    return {
        "total_devices": 42,
        "summary": {"online": 38, "offline": 4},
        "devices": [...]
    }
```

---

## 27. Production Policies

### 27.1 타임아웃 설정 (Timeout Configuration)

Workflow 내 각 노드별 타임아웃 정책을 설정합니다. 타임아웃 초과 시 해당 노드는 즉시 실패하고, 재시도 정책이 있으면 재시도됩니다.

**노드 타입별 권장 타임아웃**:

| 노드 타입 | 기본값 | 권장 범위 | 조정 기준 |
|----------|-------|---------|----------|
| **SQL 쿼리** | 5초 | 2s ~ 30s | Query 복잡도: Index 없음/JOIN 많음 → 상향 |
| **HTTP 호출** | 10초 | 5s ~ 60s | 외부 API 응답 시간 + 네트워크 지연 |
| **Python Script** | 5초 | 1s ~ 10s | 계산 복잡도: 대규모 배열 처리 → 상향 |
| **Workflow 전체** | 30초 | 10s ~ 120s | 모든 노드 합산 + 30% 여유 |

**타임아웃 설정 방법**:

```json
{
  "definition": {
    "runtime_policy": {
      "timeout_ms": 30000,
      "nodes": [
        {
          "node_id": "fetch_metrics",
          "timeout_ms": 5000
        },
        {
          "node_id": "http_call",
          "timeout_ms": 10000
        }
      ]
    }
  }
}
```

### 27.2 Retry 정책 (재시도)

실패한 노드를 자동으로 재시도합니다. 연결 오류, 일시적 서비스 오류 등에 효과적입니다.

**재시도 규칙**:

| 오류 타입 | Retry 가능 | 최대 재시도 | 백오프 간격 |
|----------|-----------|-----------|----------|
| **SQL: Connection timeout** | ✅ Yes | 3회 | 100ms → 200ms → 400ms |
| **SQL: Deadlock (40P01)** | ✅ Yes | 2회 | 500ms → 1s |
| **HTTP: 5xx (서버 오류)** | ✅ Yes | 3회 | 100ms → 200ms → 400ms |
| **HTTP: 429 (Rate Limit)** | ✅ Yes | 2회 | 1s → 2s |
| **HTTP: 4xx (클라이언트 오류)** | ❌ No | - | - |
| **Script: Runtime exception** | ✅ Yes | 1회 | 200ms |

**재시도 설정**:

```json
{
  "nodes": [
    {
      "node_id": "fetch_metrics",
      "type": "sql",
      "retry": {
        "max_attempts": 3,
        "backoff_strategy": "exponential",
        "initial_delay_ms": 100,
        "max_delay_ms": 2000,
        "multiplier": 2
      }
    }
  ]
}
```

### 27.3 Circuit Breaker 정책

외부 API 호출 시 연속 실패를 감지하면 자동으로 차단했다가 시간 경과 후 복구를 시도합니다.

**설정 파라미터**:
- **failure_threshold**: 차단하기까지의 연속 실패 횟수 (기본: 5회)
- **recovery_timeout_seconds**: Open 상태에서 복구 시도까지의 대기 시간 (기본: 60s)
- **success_threshold**: Half-Open에서 Closed로 전환하기 위한 연속 성공 횟수 (기본: 2회)

**Circuit Breaker 상태 전환**:

```
[Closed]          # 정상 (모든 요청 통과)
  ↓ (5회 연속 실패)
[Open]            # 차단 (모든 요청 즉시 실패)
  ↓ (60초 경과)
[Half-Open]       # 복구 테스트 (1회만 시도)
  ↓ (성공/실패)
[Closed] 또는 [Open]
```

**설정 예시**:

```json
{
  "nodes": [
    {
      "node_id": "external_api_call",
      "type": "http",
      "endpoint": "https://api.external.com/data",
      "circuit_breaker": {
        "failure_threshold": 5,
        "recovery_timeout_seconds": 60,
        "success_threshold": 2
      }
    }
  ]
}
```

---

## 28. Troubleshooting Workflows

### 문제 1: "Expected array but got null"

**원인**: `{{steps.fetch_metrics.rows}}` 참조 노드가 실행되지 않음

**해결**:
1. fetch_metrics 노드 상태 확인 (success/failure)
2. Test 탭에서 fetch_metrics 단독 실행 재확인
3. node_id 철자 검증

### 문제 2: "Circuit breaker open - retries exhausted"

**원인**: 외부 API 연속 실패로 Circuit breaker 차단 상태

**해결**:
1. 외부 API 상태 점검 (방화벽/DNS/서버 다운)
2. Admin > Observability에서 tool 성공률 확인
3. Timeout 정책 상향 (HTTP timeout 10s → 20s)
4. 30초 대기 후 자동 복구 시도

### 문제 3: "Template variable not found in output"

**원인**: 이전 노드 출력 구조 변경

**예**: `{{steps.summarize.output.count}}` 참조인데, summarize output에 `count` 키 없음

**해결**:
1. Test 탭에서 summarize 노드 단독 실행 → 실제 output 확인
2. Workflow 정의에서 매핑 경로 수정
3. 코드 review: script 출력 계약 확인 (return dict 구조)
