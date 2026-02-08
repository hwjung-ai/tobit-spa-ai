# API User Guide

**Last Updated**: 2026-02-08

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

화면은 크게 3개 영역으로 구성된다.

1. Left Pane
   - API 목록
   - `New API` 버튼
   - 검색/필터
2. Center Pane
   - `Definition` / `Logic` / `Test` 탭
   - 하단 `Create API`/`Update API`, `Test ... (Dry-run)` 버튼
3. Bottom/Right 정보
   - 실행 결과, 메타데이터, 로그 요약

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

목표: Script 타입의 기본 실행 구조를 익힌다.

### Step 1. New API

- API Name: `script_transform_demo`
- Method: `POST`
- Endpoint: `/runtime/script-transform-demo`
- Logic Type: `script`

### Step 2. Script language 선택

- `python` 또는 `javascript`

### Step 3. 기본 로직 작성

팀 표준에 맞춰 main 함수 중심으로 작성한다.

검증 포인트:
- Script 타입은 실행/지원 범위를 팀 정책과 함께 운영한다.
- 저장/버전 관리는 동일하게 동작한다.

---

## 6. Lab 6 - Workflow API 만들기 (순차 파이프라인)

목표: SQL -> Python -> HTTP를 연결한 Workflow를 만든다.

### Step 1. New API

- API Name: `device_metrics_pipeline`
- Method: `POST`
- Endpoint: `/runtime/device-metrics-pipeline`
- Logic Type: `workflow`

### Step 2. WorkflowBuilder 노드 구성

1. Node A (SQL)
2. Node B (Python)
3. Node C (HTTP)

### Step 3. 노드 매핑

예시:
- Node B input: `{{steps.node_a.rows}}`
- Node C params: `{{steps.node_b.summary_id}}`

### Step 4. Dry-run

검증 포인트:
- 노드 순서대로 실행
- 실패 노드가 명확히 표시
- 각 노드 duration/status 확인 가능

### Step 5. Test 탭 실행

- Params JSON과 Input JSON을 함께 넣어 실행

검증 포인트:
- 최종 결과와 중간 스텝 데이터 모두 확인 가능

---

## 7. Lab 7 - System API(Discovered/Registered) 가져와 Custom으로 전환

목표: 읽기 전용 시스템 엔드포인트를 Custom API로 가져와 편집한다.

### Step 1. Scope 전환

1. Left Pane에서 `System` 선택
2. `discovered` 또는 `registered` 탭 확인

### Step 2. 엔드포인트 선택

1. 테이블에서 대상 endpoint 선택
2. 요약/제약 정보를 확인

### Step 3. Import

1. `Import to Custom` 클릭
2. Scope를 `Custom`으로 전환
3. Definition/Logic 값이 채워졌는지 확인

### Step 4. 수정 후 저장

검증 포인트:
- 원본 시스템 API는 read-only
- Custom 복제본만 수정 가능

---

## 8. Lab 8 - 버전 관리와 롤백

목표: 변경 후 문제를 재현하고 이전 버전으로 복구한다.

### Step 1. API 수정

1. 기존 API 선택
2. Logic에서 의도적 변경
3. `Update API`

### Step 2. 오류 재현

1. Test 탭에서 오류 케이스 실행
2. execution logs에서 에러 확인

### Step 3. 롤백

1. `GET /api-manager/{api_id}/versions`로 버전 확인
2. `POST /api-manager/{api_id}/rollback` 실행
3. 동일 입력 재실행

검증 포인트:
- 이전 정상 동작으로 복구
- 로그에 롤백 후 실행 기록이 남음

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

- `apps/web/src/app/api-manager/page.tsx`
- `apps/web/src/components/api-manager/SQLQueryBuilder.tsx`
- `apps/web/src/components/api-manager/HttpFormBuilder.tsx`
- `apps/web/src/components/api-manager/PythonBuilder.tsx`
- `apps/web/src/components/api-manager/WorkflowBuilder.tsx`
- `apps/api/app/modules/api_manager/router.py`
- `apps/api/app/modules/api_manager/executor.py`
- `apps/api/app/modules/api_manager/script_executor.py`
- `apps/api/app/modules/api_manager/workflow_executor.py`
- `apps/api/app/modules/api_manager/runtime_router.py`


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

