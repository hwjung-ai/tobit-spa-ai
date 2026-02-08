# API User Guide

**Last Updated**: 2026-02-08

## 1. 목적과 대상

이 문서는 API Manager를 사용해 동적 API를 설계, 테스트, 배포, 운영하는 전 과정을 따라할 수 있도록 구성한 실습 가이드다.

대상 사용자:
- API 설계자
- 백엔드/플랫폼 엔지니어
- 운영자(장애 대응 및 실행 로그 확인)

---

## 2. 시작 전 준비

### 2.1 필수 확인

1. `/api-manager` 접근 가능한 계정
2. 테넌트/권한이 올바르게 설정됨
3. 테스트용 입력 파라미터 준비
4. 외부 HTTP 대상 API를 사용하는 경우 테스트 endpoint 준비

### 2.2 API Logic Type 이해

- `sql`: 조회 중심 쿼리 실행
- `http`: 외부/내부 HTTP 호출
- `script`: Python `main(params, input_payload)` 실행
- `workflow`: 여러 단계(node)를 순차 실행

---

## 3. 튜토리얼 A: SQL API 만들기

목표: 특정 장비의 최근 메트릭을 조회하는 API를 생성한다.

### Step 1. 새 API 생성

1. `/api-manager` 접속
2. `Create API` 클릭
3. 기본 정보 입력
- Name: `get_device_metrics`
- Method: `POST`
- Endpoint: `/runtime/get-device-metrics`
- Logic Type: `sql`

검증 포인트:
- 목록에서 새 API가 보이고 상태가 저장된다.

### Step 2. SQL 작성

예시:
```sql
SELECT device_id, metric_name, metric_value, collected_at
FROM tb_metrics
WHERE tenant_id = :tenant_id
  AND device_id = :device_id
ORDER BY collected_at DESC
LIMIT 100
```

규칙:
- 파라미터 바인딩(`:tenant_id`, `:device_id`) 사용
- row limit 명시
- 위험 구문(쓰기/삭제) 사용 금지

### Step 3. 파라미터 스키마 작성

- `tenant_id`: string, required
- `device_id`: string, required

### Step 4. Test 실행

입력 예시:
```json
{
  "tenant_id": "t1",
  "device_id": "GT-01"
}
```

검증 포인트:
- 응답 코드 200
- 결과 배열 반환
- 실행 로그에 쿼리 시간 기록

---

## 4. 튜토리얼 B: HTTP API 만들기

목표: 외부 상태 API를 호출해 내부에서 표준 포맷으로 반환한다.

### Step 1. 기본 정보

- Name: `fetch_external_status`
- Logic Type: `http`

### Step 2. HTTP 정의

- Method: `GET`
- URL: `https://example.internal/status`
- Headers: 인증 헤더(환경변수 기반)
- Params: `service={{params.service_name}}`

### Step 3. Test 실행

입력:
```json
{
  "service_name": "ops-core"
}
```

검증 포인트:
- 타임아웃/4xx/5xx 처리 메시지가 명확하다.
- 실패 시 오류가 execution log에 남는다.

---

## 5. 튜토리얼 C: Script API 만들기

목표: 입력값을 가공해 표준 결과를 반환하는 스크립트 API를 만든다.

### Step 1. 기본 정보

- Name: `normalize_metrics_payload`
- Logic Type: `script`

### Step 2. Script 작성

```python
def main(params, input_payload):
    device_id = params.get("device_id", "unknown")
    values = input_payload.get("values", [])
    avg = sum(values) / len(values) if values else 0
    return {
        "device_id": device_id,
        "count": len(values),
        "avg": avg,
    }
```

### Step 3. Test 실행

입력:
```json
{
  "params": {"device_id": "GT-01"},
  "input_payload": {"values": [10, 20, 30]}
}
```

검증 포인트:
- `avg=20` 반환
- 예외 발생 시 사용자 메시지와 로그가 확인 가능

---

## 6. 튜토리얼 D: Workflow API 만들기

목표: SQL -> Script 단계를 연결한 간단한 워크플로우를 구성한다.

### Step 1. Workflow 생성

- Name: `device_metrics_pipeline`
- Logic Type: `workflow`

### Step 2. Node 1 (SQL)

- 목적: 원본 데이터 조회
- 출력 키: `steps.fetch.raw_rows`

### Step 3. Node 2 (Script)

- 입력 매핑: `{{steps.fetch.raw_rows}}`
- 목적: 집계/정규화
- 출력 키: `steps.transform.summary`

### Step 4. Test 실행

검증 포인트:
- 노드 실행 순서가 맞다.
- 단계별 입출력이 로그에 보인다.
- 실패 노드가 있으면 어떤 단계인지 즉시 식별 가능하다.

---

## 7. 운영 화면별 사용법

### 7.1 Definition 탭

- API 메타데이터, 설명, 파라미터 스키마 관리

### 7.2 Logic 탭

- SQL/HTTP/Script/Workflow 로직 편집
- 타입별 빌더 또는 원본 편집

### 7.3 Test 탭

- 샘플 입력으로 즉시 실행
- 응답/오류/실행 시간 확인

### 7.4 Logs 패널

- 실행 이력, 실패 원인, 지연 시간 확인

---

## 8. 장애 대응 플레이북

### 시나리오 1. `Failed to load API definitions`

1. `GET /api-manager/apis` 응답 코드 확인
2. 백엔드 로그(`apps/api/logs/api.log`) 확인
3. 마이그레이션 적용 여부 확인
4. 인증/권한/tenant 헤더 확인

### 시나리오 2. 실행 시 500 오류

1. 로직 본문 문법 확인
2. 파라미터 스키마와 입력 payload 정합성 확인
3. script/workflow 노드 매핑 확인

### 시나리오 3. 타임아웃

1. 외부 endpoint 응답 시간 확인
2. SQL 성능(인덱스/limit) 확인
3. runtime policy timeout 조정

---

## 9. 배포 전 체크리스트

- 정상/실패 케이스를 각각 테스트했다.
- 실행 로그에서 원인 추적이 가능하다.
- tenant 필터와 권한 검증이 동작한다.
- timeout/limit/rate 정책을 점검했다.
- 사용자용 설명(파라미터/예시)을 업데이트했다.

---

## 10. 참고 API

- `GET /api-manager/apis`
- `POST /api-manager/apis`
- `PUT /api-manager/apis/{api_id}`
- `DELETE /api-manager/apis/{api_id}`
- `POST /api-manager/apis/{api_id}/execute`
- `GET /api-manager/apis/{api_id}/execution-logs`
- `POST /api-manager/dry-run`

---

## 11. 향후 고도화 과제

- Workflow DAG/부분 재시도 정책 고도화
- 분산 Rate Limiting
- 캐시 통계 UI 강화
- Script Sandbox 격리 강화
