# CEP User Guide

**Last Updated**: 2026-02-15
**Production Readiness**: 85%

## 문서의 성격

이 문서는 CEP를 처음 도입하는 운영자가
빈 화면에서 규칙을 만들고, 시뮬레이션하고, 이벤트를 검증하고,
실패 시 복구까지 수행할 수 있게 만든 실습 튜토리얼이다.

---

## 0. 시작 전 준비

### 0.1 준비 체크

1. `/cep-builder` 접속 가능
2. 알림 채널 테스트용 수신 대상 준비
3. tenant/권한 확인
4. 이벤트 확인용 `/cep-events` 접근 가능

### 0.2 핵심 개념 2분 요약

#### 처리 흐름

```
Event -> Filter -> Aggregation -> Anomaly(optional) -> Window -> Action -> Notification
```

전체 흐름: 이벤트가 CEP 엔진에 입수되면 조건 필터를 거치고, 집계 함수가 적용되며,
윈도우 내에서 결과가 평가된 뒤 액션이 실행된다. 선택적으로 이상 탐지(Anomaly)가
집계 직후에 수행될 수 있다.

#### 아키텍처 개요

```
+-------------------+     +------------------+     +------------------+
|   Data Source     |     |   CEP Engine     |     |   Notification   |
|                   |     |  (Bytewax 기반)   |     |   System         |
|  - Metric API     | --> |  - Filter        | --> |  - Slack         |
|  - Event Stream   |     |  - Aggregate     |     |  - Email         |
|  - Scheduler      |     |  - Window        |     |  - SMS           |
|                   |     |  - Anomaly       |     |  - Discord       |
+-------------------+     +------------------+     |  - Webhook       |
                                 |                 +------------------+
                                 v
                          +------------------+
                          |  Redis 상태 저장소  |
                          |  - 윈도우 상태     |
                          |  - 집계 중간값     |
                          |  - Pub/Sub 큐     |
                          +------------------+
```

#### CEP Builder UI 탭 구성

CEP Builder(`/cep-builder`)는 4개 탭으로 구성된다.

| 탭 | 설명 |
|---|---|
| **JSON Editor** | Trigger Spec과 Action Spec을 JSON으로 직접 편집한다 |
| **Form Builder** | 폼 UI로 BasicInfo, Trigger, Conditions, Windowing, Aggregation, Enrichment, Actions를 설정한다 |
| **Test** | Simulate(조건 평가)와 Manual Trigger(실제 실행)를 수행한다 |
| **Logs** | 규칙별 실행 로그(exec_id, status, duration_ms, error)를 조회한다 |

#### Trigger 타입 (3 + 1)

| 타입 | 용도 | 예시 |
|---|---|---|
| `metric` | 메트릭 값이 임계값을 넘으면 발동 | CPU > 85%, Memory > 70% |
| `event` | 특정 이벤트 패턴이 수신되면 발동 | error 이벤트, severity=critical |
| `schedule` | cron 기반 주기적 실행 | 매 5분 상태 점검, 매일 9시 리포트 |
| `anomaly` | 통계 기반 이상치 감지 (내부적으로 metric 타입 활용) | z-score > 3.0 탐지 |

참고: `anomaly`는 Form Builder에서 선택 가능하지만 내부적으로 metric 타입의 변형으로 처리된다.

#### 조건(Condition) 연산자

조건은 field-operator-value 삼중값으로 구성되며, AND/OR/NOT 논리로 결합된다.

| 연산자 | 의미 | 예시 |
|---|---|---|
| `>` | 초과 | `cpu_usage > 85` |
| `<` | 미만 | `response_time < 100` |
| `>=` | 이상 | `memory_percent >= 70` |
| `<=` | 이하 | `disk_usage <= 90` |
| `==` | 일치 | `status == "error"` |
| `!=` | 불일치 | `service != "test"` |
| `in` | 목록 포함 | `region in ["us-east", "eu-west"]` |
| `contains` | 문자열 포함 | `message contains "timeout"` |

논리 결합:
- `AND`: 모든 조건이 참이어야 발동
- `OR`: 하나 이상의 조건이 참이면 발동
- `NOT`: 조건이 거짓일 때 발동 (부정)

#### 윈도우 타입

윈도우는 이벤트를 시간 단위로 분할하여 집계하는 메커니즘이다.

```
[Tumbling Window]  고정 크기, 겹치지 않음
|----5m----|----5m----|----5m----|
|  Window1 |  Window2 |  Window3 |

[Sliding Window]   고정 크기, 일정 간격으로 이동하며 겹침
|--------5m--------|
     |--------5m--------|
          |--------5m--------|
<--1m--> slide 간격

[Session Window]   활동 기반, 비활동 timeout 시 종료
|--활동--|      |--활동--|--활동--|     |--활동--|
         timeout          timeout        timeout
```

| 타입 | 파라미터 | 적합한 상황 |
|---|---|---|
| `tumbling` | size (예: 5m) | 일정 주기 집계가 필요한 경우 |
| `sliding` | size (예: 5m), slide (예: 1m) | 실시간에 가까운 이동 평균이 필요한 경우 |
| `session` | timeout (예: 10m) | 사용자 활동 기반 분석이 필요한 경우 |

크기 선택 가능 값: 1s, 10s, 30s, 1m, 5m, 10m, 30m, 1h

#### 집계 타입 (6가지)

| 타입 | 설명 | 필드 필요 여부 |
|---|---|---|
| `avg` | 평균값 | 필요 |
| `sum` | 합계 | 필요 |
| `min` | 최소값 | 필요 |
| `max` | 최대값 | 필요 |
| `count` | 개수 | 불필요 |
| `stddev` | 표준편차 | 필요 |

#### 액션 타입 (4가지)

| 타입 | 설명 | 필수 설정 |
|---|---|---|
| `webhook` | 외부 HTTP 엔드포인트 호출 | endpoint URL, method (GET/POST/PUT/DELETE) |
| `notify` | 알림 채널로 메시지 전송 | 채널 선택, 메시지 내용 |
| `trigger` | 다른 CEP 규칙 연쇄 실행 | 대상 규칙 ID |
| `store` | 이벤트 데이터 저장 | 저장 대상 |

알림 채널:
- **Slack**: Incoming Webhook URL 기반 전송
- **Email**: SMTP 서버 경유 전송
- **SMS**: SMS Provider API 경유 전송
- **Discord**: Discord Webhook URL 기반 전송

#### 데이터 보강(Enrichment) 타입

| 타입 | 설명 | 용도 |
|---|---|---|
| `lookup` | 외부 데이터 소스 조회 | Redis/DB에서 부가 정보 조회 |
| `aggregate` | 과거 집계 데이터 추가 | 최근 1시간 평균값 등 |
| `ml_model` | 머신러닝 모델 적용 | 이상 탐지 모델 추론 |

---

## 1. Lab 1 - 첫 Metric Rule 만들기

목표: CPU 85% 초과 시 알림을 보내는 규칙 완성.

### Step 1. 새 규칙 생성

1. `/cep-builder` 접속
2. `New Rule` 클릭
3. 입력
   - Rule Name: `cpu_high_alert`
   - Description: `CPU > 85 for 5m`
   - Active: OFF

검증 포인트:
- 목록에 Draft 규칙이 생성된다.

### Step 2. Trigger 설정

- Trigger Type: `metric`
- metric_name: `cpu_usage`
- operator: `>`
- threshold: `85`
- duration/window: `5m`

검증 포인트:
- 조건식이 의도대로 표시된다.

### Step 3. Action 설정

- Action 1: `notify`
  - channel: Slack(또는 Email)
  - message: `CPU threshold exceeded`
- Action 2(선택): `webhook`

검증 포인트:
- 필수 항목 누락 경고가 없다.

### Step 4. Simulate

테스트 payload:
```json
{
  "cpu_usage": 92,
  "host": "gt-01",
  "severity": "high"
}
```

검증 포인트:
- 조건 매칭 `true`
- 실행될 액션 목록이 출력

### Step 5. 활성화

1. Rule 활성화 ON
2. `/cep-events`에서 이벤트 생성 확인

검증 포인트:
- rule_id가 이벤트 목록에 표시
- 발생 시각/상태/채널 결과 확인 가능

---

## 2. Lab 2 - Event Rule 만들기

목표: 특정 에러 이벤트 발생 시 경보 발송.

### Step 1. Rule 생성

1. `/cep-builder` 접속
2. `New Rule` 클릭
3. 기본 정보 입력:
   - Rule Name: `critical_error_event`
   - Description: `API Gateway critical error detection`
   - Trigger Type: `event`

4. JSON Editor 탭에서 Trigger Spec 입력:

```json
{
  "event_type": "error",
  "source": "api-gateway"
}
```

검증 포인트:
- 좌측 규칙 목록에 `critical_error_event`가 표시된다.
- Trigger Type이 `event`로 표시된다.

### Step 2. 조건 추가

복합 조건을 설정한다. Form Builder 탭 또는 JSON Editor에서 설정 가능.

**Form Builder 방식**:
1. Form Builder 탭 클릭
2. 조건 설정 섹션에서 `+ 조건 추가` 2회 클릭
3. 첫 번째 조건: 필드 `severity`, 연산자 `==`, 값 `critical`
4. 두 번째 조건: 필드 `service`, 연산자 `==`, 값 `api-gateway`
5. 논리 연산 드롭다운에서 `AND` 선택

**JSON Editor 방식** (동일한 조건을 JSON으로 표현):

```json
{
  "event_type": "error",
  "conditions": [
    { "field": "severity", "op": "==", "value": "critical" },
    { "field": "service", "op": "==", "value": "api-gateway" }
  ],
  "logic": "AND"
}
```

검증 포인트:
- 조건 2개가 AND로 결합되어 표시된다.
- Form Builder에서 JSON 미리보기와 입력값이 일치한다.

### Step 3. 액션 구성

두 가지 액션을 설정한다.

**Action 1 - Webhook (PagerDuty)**:
```json
{
  "type": "webhook",
  "endpoint": "https://events.pagerduty.com/v2/enqueue",
  "method": "POST"
}
```

**Action 2 - Notify (Slack)**:
```json
{
  "type": "notify",
  "channels": ["Slack"],
  "message": "[CRITICAL] API Gateway error detected: {{severity}} - {{summary}}"
}
```

전체 Action Spec 예시:
```json
{
  "type": "multi_action",
  "actions": [
    {
      "type": "webhook",
      "endpoint": "https://events.pagerduty.com/v2/enqueue",
      "method": "POST"
    },
    {
      "type": "notify",
      "channels": ["Slack"],
      "message": "[CRITICAL] API Gateway error detected: {{severity}} - {{summary}}"
    }
  ]
}
```

검증 포인트:
- Action Spec JSON이 유효하다 (빨간 에러 없음).
- 액션 2개가 모두 등록되었다.

### Step 4. 시뮬레이션 실행

1. 규칙을 먼저 저장한다 (`Create rule` 또는 `Update rule` 클릭).
2. Test 탭으로 이동한다.
3. Payload 입력란에 매칭될 이벤트를 입력:

```json
{
  "severity": "critical",
  "service": "api-gateway",
  "summary": "Connection pool exhausted",
  "timestamp": "2026-02-08T10:30:00Z"
}
```

4. `Simulate` 버튼 클릭

기대 출력 (Simulation result 패널):
```json
{
  "matched": true,
  "condition_evaluated": true,
  "triggered_actions": ["webhook", "notify"],
  "extracted_value": "critical"
}
```

5. 비매칭 이벤트로 재검증:

```json
{
  "severity": "warning",
  "service": "api-gateway",
  "summary": "High latency detected",
  "timestamp": "2026-02-08T10:31:00Z"
}
```

기대 출력:
```json
{
  "matched": false,
  "condition_evaluated": false,
  "triggered_actions": []
}
```

검증 포인트:
- critical 이벤트만 매칭된다.
- warning 이벤트는 제외된다.
- 시뮬레이션 결과의 matched 값이 의도와 일치한다.

### Step 5. Manual Trigger 와 이벤트 확인

1. Test 탭에서 매칭될 payload를 입력한 상태로 `Manual trigger` 버튼 클릭.
2. Manual trigger result 패널에서 실행 결과를 확인한다.
3. Logs 탭으로 이동하여 exec_id, status, duration_ms를 확인한다.

4. `/cep-events` 페이지로 이동한다.
5. 필터 설정:
   - ACK 필터: `Unacked`
   - Severity 필터: `critical`
6. 그리드에서 해당 이벤트 행을 클릭한다.
7. 우측 상세 패널에서 확인:
   - Summary 내용
   - Severity 값
   - Condition evaluated: true
   - Payload JSON 내용

검증 포인트:
- 이벤트가 `/cep-events` 목록에 나타난다.
- 이벤트 상세에서 rule_name이 `critical_error_event`이다.
- ACK 상태가 `UNACK`이다.

---

## 3. Lab 3 - Schedule Rule 만들기

목표: 매 5분 상태 점검 작업 실행.

### Step 1. Rule 생성 및 Trigger 설정

1. `/cep-builder` 접속, `New Rule` 클릭
2. 기본 정보:
   - Rule Name: `health_check_5min`
   - Description: `5분 간격 서비스 상태 점검`
   - Active: OFF (설정 완료 후 활성화)
3. Trigger Type: `schedule`
4. Trigger Spec에 cron 표현식 입력:

```json
{
  "scheduleExpression": "*/5 * * * *"
}
```

#### Cron 표현식 참조표

| 표현식 | 의미 | 사용 예 |
|---|---|---|
| `*/5 * * * *` | 매 5분 | 상태 점검, 메트릭 수집 |
| `*/15 * * * *` | 매 15분 | 중간 빈도 점검 |
| `0 * * * *` | 매 시간 정각 | 시간별 리포트 |
| `0 */2 * * *` | 매 2시간 | 주기적 데이터 정리 |
| `0 9 * * *` | 매일 09:00 | 일일 리포트 |
| `0 9 * * 1` | 매주 월요일 09:00 | 주간 리포트 |
| `0 0 1 * *` | 매월 1일 00:00 | 월간 정산 |
| `0 9 * * 1-5` | 평일 09:00 | 근무일 알림 |

Cron 표현식 형식: `분 시 일 월 요일`

| 필드 | 범위 | 특수문자 |
|---|---|---|
| 분 | 0-59 | * , - / |
| 시 | 0-23 | * , - / |
| 일 | 1-31 | * , - / |
| 월 | 1-12 | * , - / |
| 요일 | 0-7 (0,7=일) | * , - / |

#### Timezone 참고

- CEP 스케줄러는 서버 시간대 기준으로 동작한다.
- 서버 시간대가 UTC인 경우, KST(한국 표준시)는 UTC+9이므로 시간 변환이 필요하다.
- 예: KST 09:00에 실행하려면 `0 0 * * *` (UTC 00:00)으로 설정한다.
- 운영 환경의 시간대를 확인한 후 cron을 설정해야 한다.

검증 포인트:
- Trigger Type이 `schedule`로 표시된다.
- cron 표현식이 저장되었다.

### Step 2. Action 설정

상태 점검 API를 호출하는 webhook 액션을 구성한다.

```json
{
  "type": "multi_action",
  "actions": [
    {
      "type": "webhook",
      "endpoint": "https://api.internal.example.com/health/check",
      "method": "GET"
    },
    {
      "type": "notify",
      "channels": ["Slack"],
      "message": "5분 주기 상태 점검 실행 완료. 결과를 확인하세요."
    }
  ],
  "description": "5분 간격 서비스 상태 점검"
}
```

검증 포인트:
- Action Spec JSON이 유효하다.
- webhook endpoint URL이 올바르다.
- 알림 채널과 메시지가 설정되었다.

### Step 3. 시뮬레이션 및 수동 실행

1. 규칙을 저장한다 (`Create rule` 클릭).
2. Test 탭으로 이동한다.
3. schedule 규칙은 payload 없이도 동작한다. 빈 payload `{}` 로 Simulate를 실행한다.
4. `Manual trigger` 버튼으로 1회 수동 실행한다.
5. Logs 탭에서 실행 기록을 확인한다:
   - status: `success` 또는 `dry_run`
   - duration_ms 확인
   - error_message: null (정상)

검증 포인트:
- Manual Trigger 결과에 오류가 없다.
- Logs에 실행 기록이 생성되었다.

### Step 4. 활성화 및 스케줄러 검증

1. Rule 활성화 ON
2. 스케줄러 상태 확인:
   - `GET /cep/scheduler/status`
   - `GET /cep/scheduler/instances`
3. `/cep-events`에서 주기 실행 확인:
   - 5분 간격으로 이벤트가 생성되는지 확인
   - 최소 2회 이상 연속 실행을 기다려 주기성을 검증

검증 포인트:
- 주기 실행 누락이 없다.
- 이벤트 간 시간 간격이 약 5분이다.
- 스케줄러 상태가 정상이다.

---

## 4. Lab 4 - Anomaly Rule 만들기

목표: 임계값 없이 이상치를 감지한다.

### Step 1. Rule 생성

- Trigger Type: `anomaly`
- value_path: 예 `cpu_percent`
- anomaly_method: `zscore` (초기)
- threshold: `3.0`

### Step 2. 베이스라인 확보

1. 초기 데이터로 이벤트 여러 건 입력
2. baseline 상태 확인
   - `GET /cep/rules/{rule_id}/anomaly-status`

### Step 3. 이상치 테스트

테스트 payload 예:
```json
{"cpu_percent": 99}
```

검증 포인트:
- `is_anomaly=true`
- score/method/details 확인 가능

---

## 5. Lab 5 - 복합 조건(AND/OR/NOT)과 집계

목표: 다중 조건과 집계를 함께 사용.

### Step 1. 조건 구성

복합 조건 예시:
- `(cpu > 80 AND memory > 70) OR disk > 90`

이 조건을 CEP Builder에서 설정하는 방법:

**방법 A - Form Builder 사용**:

1. Form Builder 탭 클릭
2. 조건 설정 섹션에서 `+ 조건 추가` 3회 클릭
3. 조건 입력:
   - 조건 1: 필드 `cpu`, 연산자 `>`, 값 `80`
   - 조건 2: 필드 `memory`, 연산자 `>`, 값 `70`
   - 조건 3: 필드 `disk`, 연산자 `>`, 값 `90`
4. 논리 연산: `OR` 선택 (최상위 논리)

참고: 현재 Form Builder는 단일 레벨의 AND/OR/NOT을 지원한다.
중첩 논리가 필요한 경우 JSON Editor에서 직접 편집한다.

**방법 B - JSON Editor로 중첩 조건 작성**:

```json
{
  "conditions": [
    { "field": "cpu", "op": ">", "value": 80 },
    { "field": "memory", "op": ">", "value": 70 },
    { "field": "disk", "op": ">", "value": 90 }
  ],
  "logic": "OR"
}
```

검증 포인트:
- 조건 3개가 올바르게 표시된다.
- 논리 연산자가 `OR`로 설정되었다.

### Step 2. 집계 설정

#### 6가지 집계 타입 상세

| 타입 | 한글명 | 설명 | 사용 예 |
|---|---|---|---|
| `avg` | 평균 | 윈도우 내 값의 산술 평균 | 5분간 CPU 평균 사용률 |
| `sum` | 합계 | 윈도우 내 값의 총합 | 1시간 총 요청 수 |
| `min` | 최소값 | 윈도우 내 최소값 | 응답 시간 최소값 |
| `max` | 최대값 | 윈도우 내 최대값 | 메모리 사용 최대값 |
| `count` | 개수 | 윈도우 내 이벤트 수 (필드 불필요) | 에러 발생 횟수 |
| `stddev` | 표준편차 | 윈도우 내 값의 분산 정도 | CPU 사용률 변동성 |

집계 설정 예시 (Form Builder):
1. 집계 설정 섹션에서 `+ 집계 추가` 클릭
2. 집계 타입: `avg` 선택
3. 필드명: `cpu_percent`
4. 출력명: `avg_cpu` (선택)
5. 그룹화 필드: `region, service_name` (선택, 쉼표 구분)

검증 포인트:
- 집계 함수가 올바른 필드에 적용되었다.
- 출력명이 결과에 반영된다.

#### 윈도우 타입 선택 가이드

| 상황 | 권장 윈도우 | 이유 |
|---|---|---|
| "5분 평균 CPU가 80% 초과" | tumbling 5m | 정확한 5분 단위 집계 |
| "실시간 이동 평균 모니터링" | sliding 5m, slide 1m | 1분마다 최근 5분 평균 재계산 |
| "사용자 세션 중 에러 집계" | session timeout 10m | 비활동 10분 후 세션 종료 |
| "1분 내 에러 5건 이상" | tumbling 1m | 짧은 주기 count 집계 |

윈도우 설정 예시 (Form Builder):
1. 윈도우 설정 섹션에서 `Tumbling Window` 선택
2. 윈도우 크기: `5m`

### Step 3. 시뮬레이션

1. 규칙을 저장한다.
2. Test 탭에서 여러 payload로 조건별 true/false를 확인한다.

테스트 payload 1 (cpu와 memory 모두 초과):
```json
{
  "cpu": 85,
  "memory": 75,
  "disk": 50
}
```
기대 결과: matched = true (cpu > 80 AND memory > 70 을 만족, OR 이므로 전체 true)

테스트 payload 2 (disk만 초과):
```json
{
  "cpu": 60,
  "memory": 50,
  "disk": 95
}
```
기대 결과: matched = true (disk > 90을 만족)

테스트 payload 3 (모두 정상):
```json
{
  "cpu": 60,
  "memory": 50,
  "disk": 70
}
```
기대 결과: matched = false

### Step 4. 전체 규칙 JSON 미리보기

Form Builder에서 설정을 완료하면, 하단의 "JSON 미리보기" 섹션에서 전체 규칙 구조를 확인할 수 있다.

완성된 규칙의 전체 JSON 구조 예시:

```json
{
  "rule_name": "system_resource_alert",
  "description": "CPU/Memory/Disk 복합 조건 모니터링",
  "is_active": true,
  "trigger_type": "metric",
  "trigger_spec": {
    "endpoint": "/api/metrics/system",
    "value_path": "data.metrics",
    "method": "GET"
  },
  "composite_condition": {
    "conditions": [
      { "field": "cpu", "op": ">", "value": 80 },
      { "field": "memory", "op": ">", "value": 70 },
      { "field": "disk", "op": ">", "value": 90 }
    ],
    "logic": "OR"
  },
  "window_config": {
    "type": "tumbling",
    "size": "5m"
  },
  "aggregation": {
    "type": "avg",
    "field": "cpu_percent",
    "outputAlias": "avg_cpu"
  },
  "actions": [
    {
      "type": "webhook",
      "endpoint": "https://api.internal.example.com/alerts",
      "method": "POST"
    },
    {
      "type": "notify",
      "channels": ["Slack", "Email"],
      "message": "시스템 자원 임계치 초과: cpu={{cpu}}, memory={{memory}}, disk={{disk}}"
    }
  ]
}
```

검증 포인트:
- 조건 논리 오해 없이 의도대로 실행된다.
- JSON 미리보기의 composite_condition, window_config, aggregation이 폼 입력과 일치한다.
- 매칭/비매칭 payload에 대해 시뮬레이션 결과가 예상과 일치한다.

---

## 6. Lab 6 - 채널 테스트와 알림 신뢰성 점검

목표: 채널별 전달 실패를 사전에 줄인다.

### Step 1. 채널 타입 확인

먼저 사용 가능한 채널과 현재 상태를 조회한다.

```
GET /cep/channels/types
```

응답 예시:
```json
{
  "channels": ["Slack", "Email", "SMS", "Discord"]
}
```

```
GET /cep/channels/status
```

응답 예시:
```json
{
  "channels": {
    "Slack": { "configured": true, "last_test": "2026-02-08T09:00:00Z", "status": "ok" },
    "Email": { "configured": true, "last_test": null, "status": "untested" },
    "SMS": { "configured": false, "last_test": null, "status": "not_configured" },
    "Discord": { "configured": true, "last_test": "2026-02-07T15:00:00Z", "status": "ok" }
  }
}
```

검증 포인트:
- 사용하려는 채널이 `configured: true` 상태인지 확인한다.
- `untested` 또는 `not_configured` 채널은 테스트가 필요하다.

### Step 2. 채널별 설정 가이드 및 테스트

#### Slack 채널 설정

사전 준비:
1. Slack App에서 Incoming Webhook 활성화
2. 채널에 Webhook URL 생성 (형식: `https://hooks.slack.com/services/T.../B.../xxx`)

테스트 요청:
```
POST /cep/channels/test
Content-Type: application/json

{
  "channel": "Slack",
  "config": {
    "webhook_url": "https://hooks.slack.com/services/T.../B.../xxx"
  },
  "test_message": "CEP 채널 테스트: Slack 알림이 정상 수신되면 성공입니다."
}
```

성공 응답:
```json
{
  "channel": "Slack",
  "status": "ok",
  "message": "Test message delivered successfully",
  "latency_ms": 245
}
```

실패 응답 (잘못된 URL):
```json
{
  "channel": "Slack",
  "status": "error",
  "message": "HTTP 404: Webhook URL not found",
  "latency_ms": 120
}
```

검증 포인트:
- Slack 채널에 테스트 메시지가 수신되었다.
- latency_ms가 합리적인 범위 내이다 (보통 500ms 이하).

#### Email 채널 설정

사전 준비:
1. SMTP 서버 주소, 포트, 인증 정보 확인
2. 발신자/수신자 이메일 주소 준비

테스트 요청:
```
POST /cep/channels/test
Content-Type: application/json

{
  "channel": "Email",
  "config": {
    "smtp_host": "smtp.company.com",
    "smtp_port": 587,
    "username": "cep-alerts@company.com",
    "password": "****",
    "from": "cep-alerts@company.com",
    "to": ["ops-team@company.com"]
  },
  "test_message": "CEP 채널 테스트: Email 알림 테스트입니다."
}
```

검증 포인트:
- 수신자 메일함에 테스트 메일이 도착했다.
- SMTP 인증 오류가 없다.

#### SMS 채널 설정

사전 준비:
1. SMS Provider API key 확인 (예: Twilio, NHN Cloud)
2. 발신 번호, 수신 번호 준비

테스트 요청:
```
POST /cep/channels/test
Content-Type: application/json

{
  "channel": "SMS",
  "config": {
    "provider": "twilio",
    "api_key": "****",
    "from_number": "+821012345678",
    "to_numbers": ["+821087654321"]
  },
  "test_message": "CEP 채널 테스트: SMS 알림입니다."
}
```

검증 포인트:
- SMS가 수신 번호로 전달되었다.
- API key 인증이 정상 통과했다.

#### Discord 채널 설정

사전 준비:
1. Discord 서버 > 채널 설정 > 연동 > Webhook 생성
2. Webhook URL 복사 (형식: `https://discord.com/api/webhooks/xxx/yyy`)

테스트 요청:
```
POST /cep/channels/test
Content-Type: application/json

{
  "channel": "Discord",
  "config": {
    "webhook_url": "https://discord.com/api/webhooks/xxx/yyy"
  },
  "test_message": "CEP 채널 테스트: Discord 알림이 정상 수신되면 성공입니다."
}
```

검증 포인트:
- Discord 채널에 테스트 메시지가 나타났다.

### Step 3. 실패 대응 점검 및 재시도 메커니즘

채널 전송 실패 시 CEP 시스템은 지수 백오프(Exponential Backoff) 재시도를 수행한다.

#### 재시도 메커니즘 상세

```
1차 시도 실패 -> 1초 대기 -> 2차 시도
2차 시도 실패 -> 2초 대기 -> 3차 시도
3차 시도 실패 -> 4초 대기 -> 4차 시도
4차 시도 실패 -> 8초 대기 -> 최종 시도 (5차)
5차 시도 실패 -> 최종 실패 기록, 폴백 채널로 전환 (설정된 경우)
```

재시도 간격: 1s -> 2s -> 4s -> 8s (지수 백오프)
최대 재시도 횟수: 기본 4회 (총 5회 시도)

#### 실패 유형별 점검 항목

| 실패 유형 | 원인 | 점검 항목 |
|---|---|---|
| Connection timeout | 네트워크 문제 또는 엔드포인트 다운 | endpoint URL 접근성, 방화벽 규칙 |
| HTTP 401/403 | 인증 실패 | API key, token, 인증 헤더 |
| HTTP 404 | 잘못된 URL | webhook URL 재확인 |
| HTTP 429 | Rate limit 초과 | 전송 빈도 조절, 백오프 간격 증가 |
| Template error | 메시지 템플릿 변수 미정의 | 메시지 내 {{변수}} 이름 확인 |
| SMTP error | 메일 서버 인증 실패 | SMTP 설정 값 재확인 |

#### 점검 절차

1. endpoint timeout 확인:
   - 네트워크 연결이 가능한지 확인
   - 방화벽 규칙에서 아웃바운드가 허용되는지 확인

2. auth 오류 확인:
   - API key 또는 token이 유효한지 확인
   - webhook URL이 최신 상태인지 확인

3. 메시지 템플릿 누락 확인:
   - 메시지에 사용된 {{변수명}}이 이벤트 payload에 존재하는지 확인
   - 정의되지 않은 변수가 있으면 템플릿 렌더링이 실패할 수 있음

검증 포인트:
- 채널 테스트가 최소 1회 성공
- 실패 원인이 재현 가능하게 기록
- 재시도 횟수와 최종 성공/실패 결과가 로그에 남아 있다

---

## 7. Lab 7 - 이벤트 관제와 ACK 운영

목표: 발생 이벤트를 운영 프로세스로 처리한다.

### Step 1. 이벤트 목록

- `GET /cep/events`
- 필터: rule_id, severity, 시간 범위

### Step 2. 이벤트 상세

- `GET /cep/events/{event_id}`

### Step 3. ACK 처리

- `POST /cep/events/{event_id}/ack`

검증 포인트:
- ACK 전/후 상태 변화가 기록된다.

---

## 8. Lab 8 - Form 기반 규칙 작성

목표: Form Builder를 사용하여 GUI로 규칙을 작성하고, JSON 미리보기로 정합성을 검증한다.

### 전체 워크플로우

```
Form Builder 탭 선택
  -> BasicInfo 입력
  -> Trigger 설정
  -> Conditions 설정
  -> Windowing 설정
  -> Aggregation 설정
  -> Enrichment 설정 (선택)
  -> Actions 설정
  -> JSON 미리보기 확인
  -> 규칙 생성/수정
```

### Step 1. 폼 작성 - 기본 정보 (BasicInfo)

1. `/cep-builder` 접속
2. `New Rule` 클릭
3. **Form Builder** 탭 클릭 (상단 탭 중 두 번째)
4. 기본 정보 섹션 입력:
   - 규칙명 (필수): `production_server_monitor`
   - 설명: `프로덕션 서버 CPU/Memory 임계치 모니터링`
   - 규칙 활성화: 체크 해제 (설정 완료 후 활성화)

검증 포인트:
- 규칙명이 빈 칸이면 "규칙명을 입력하세요" 에러가 표시된다.
- 활성화 상태가 "비활성"으로 표시된다.

### Step 2. 폼 작성 - 트리거 설정 (Trigger)

트리거 설정 섹션에서 타입을 선택한다.

1. 트리거 타입: `메트릭` 버튼 클릭
2. 메트릭 트리거 설정 폼이 나타난다:
   - 메트릭명 (필수): `cpu_usage`
   - 연산자 (필수): `>` 선택
   - 임계값 (필수): `85`
   - 집계 방식 (필수): `avg` 선택
   - 시간 윈도우 (필수): `5m` 선택

만약 이벤트 트리거를 선택하면:
- 이벤트 타입 (필수): 예 `error`, `warning`, `alert`

만약 스케줄 트리거를 선택하면:
- Cron 표현식 (필수): 예 `*/5 * * * *` (도움말: "예: 0 9 * * * (매일 9시)")

검증 포인트:
- 선택한 트리거 타입 버튼이 하이라이트된다.
- 트리거 타입에 맞는 입력 필드가 표시된다.

### Step 3. 폼 작성 - 조건 설정 (Conditions)

1. 조건 설정 섹션 (선택사항)에서 `+ 조건 추가` 2회 클릭
2. 각 조건 입력:

   | 순서 | 필드 | 연산자 | 값 |
   |---|---|---|---|
   | 1 | `cpu_usage` | `>` | `85` |
   | 2 | `memory_percent` | `>` | `70` |

3. 논리 연산 드롭다운에서 `AND` 선택

사용 가능한 연산자 목록:
`>`, `<`, `>=`, `<=`, `==`, `!=`, `in`, `contains`

검증 포인트:
- 조건 2개가 AND로 결합되어 표시된다.
- 삭제 버튼으로 개별 조건을 제거할 수 있다.
- 논리 연산 변경 시 즉시 반영된다.

### Step 4. 폼 작성 - 윈도우 설정 (Windowing)

1. 윈도우 설정 섹션 (선택사항)에서 윈도우 타입 선택
2. `Tumbling Window` 라디오 버튼 클릭
   - 설명: "고정 크기의 겹치지 않는 시간 윈도우"
3. 윈도우 크기: `5m` 선택
4. 하단에 확인 문구가 표시된다: "5m 크기의 윈도우로 데이터를 분할합니다"

Sliding Window를 선택하는 경우:
- 윈도우 크기: `5m`
- Slide 간격: `1m` (추가 필드가 나타남)

Session Window를 선택하는 경우:
- Session Timeout: `10m` (추가 필드가 나타남)

검증 포인트:
- 선택한 윈도우 타입에 맞는 추가 필드가 나타난다.
- 확인 문구가 설정값을 정확히 반영한다.

### Step 5. 폼 작성 - 집계 설정 (Aggregation)

1. 집계 설정 섹션에서 `+ 집계 추가` 클릭
2. 집계 타입: `avg` (평균) 선택
3. 필드명: `cpu_usage`
4. 출력명: `avg_cpu`
5. 그룹화 필드 (선택): `host` (쉼표로 여러 필드 구분 가능)

참고: `count` 타입을 선택하면 필드명 입력란이 나타나지 않는다 (개수 집계이므로 특정 필드 불필요).

검증 포인트:
- 집계 타입 변경 시 필드명 입력란 표시/숨김이 정상 동작한다.
- 그룹화 필드에 쉼표로 구분한 값이 올바르게 파싱된다.

### Step 6. 폼 작성 - 데이터 보강 (Enrichment, 선택)

1. 데이터 보강 섹션에서 `+ 보강 추가` 클릭
2. 타입: `lookup` (데이터 조회) 선택
3. 데이터 소스: `redis://server-metadata`
4. 조회 키: `host`
5. 출력 필드명: `server_info`

검증 포인트:
- 보강 항목이 추가되었다.
- 타입 변경 시 입력 필드가 적절히 변경된다.

### Step 7. 폼 작성 - 액션 설정 (Actions)

1. 액션 설정 섹션 (필수)에서 `+ 액션 추가` 2회 클릭

**액션 1 - Webhook**:
- 타입: `Webhook 호출` 선택
- 엔드포인트 URL: `https://api.internal.example.com/alerts/cpu`
- Method: `POST`

**액션 2 - Notify**:
- 타입: `알림 전송` 선택
- 알림 메시지: `서버 CPU 사용률이 임계치를 초과했습니다. host={{host}}, cpu={{cpu_usage}}%`
- 채널 체크박스 선택: Slack (체크), Email (체크)

검증 포인트:
- 액션 2개가 표시된다.
- Webhook 선택 시 URL과 Method 입력란이 나타난다.
- Notify 선택 시 메시지와 채널 체크박스가 나타난다.
- 액션이 0개이면 "규칙 생성" 버튼이 비활성화된다.

### Step 8. JSON 미리보기 확인

Form Builder 하단의 "JSON 미리보기" 섹션을 확인한다.

생성되는 규칙 JSON 예시:
```json
{
  "rule_name": "production_server_monitor",
  "description": "프로덕션 서버 CPU/Memory 임계치 모니터링",
  "is_active": false,
  "trigger_type": "metric",
  "trigger_spec": {
    "metricName": "cpu_usage",
    "operator": ">",
    "threshold": "85",
    "aggregation": "avg",
    "duration": "5m"
  },
  "composite_condition": {
    "conditions": [
      { "field": "cpu_usage", "op": ">", "value": "85" },
      { "field": "memory_percent", "op": ">", "value": "70" }
    ],
    "logic": "AND"
  },
  "window_config": {
    "type": "tumbling",
    "size": "5m"
  },
  "actions": [
    {
      "type": "webhook",
      "endpoint": "https://api.internal.example.com/alerts/cpu",
      "method": "POST"
    },
    {
      "type": "notify",
      "channels": ["Slack", "Email"],
      "message": "서버 CPU 사용률이 임계치를 초과했습니다. host={{host}}, cpu={{cpu_usage}}%"
    }
  ]
}
```

JSON Editor 탭으로 전환하여 동일한 구조가 Trigger Spec/Action Spec에 반영되어 있는지 대조한다.

검증 포인트:
- 폼 데이터와 JSON 미리보기의 모든 값이 일치한다.
- JSON 미리보기에서 Copy 기능으로 클립보드에 복사할 수 있다.

### Step 9. Copilot 패널 활용

화면 우측의 Copilot 패널을 활용하면 자연어로 규칙을 생성할 수 있다.

1. Copilot 입력란에 규칙을 자연어로 설명:
   `"CPU가 90% 넘고 메모리가 80% 넘으면 Slack으로 알림 보내줘"`
2. Copilot이 CEP Draft JSON을 생성한다.
3. 우측 패널에서 Draft status를 확인:
   - `Draft 준비됨`: Draft가 생성되었다
4. `Preview` 버튼: Draft JSON을 미리 확인
5. `Test` 버튼: Draft 구조 유효성 검증
6. `Apply` 버튼: Draft를 폼에 적용 (Test 통과 후에만 활성화)
7. `Save` 버튼: 적용된 Draft를 서버에 저장 (Test 통과 후에만 활성화)

Draft 적용 후 Form Builder에서 값이 자동으로 채워진 것을 확인한다.

검증 포인트:
- Copilot이 생성한 Draft JSON이 `type: "cep_draft"` 형식이다.
- Apply 후 Form Builder의 각 섹션에 값이 반영되었다.
- 폼 수정 시 Draft status가 "드래프트 오래됨"으로 변경된다.

### Step 10. Form 저장

1. 모든 섹션 설정을 확인한 뒤 `규칙 생성` 버튼 클릭
2. API 호출: `POST /cep/rules/form`
3. 성공 시 좌측 규칙 목록에 새 규칙이 추가된다
4. 상태 메시지: "Rule created from form."

검증 포인트:
- 폼 데이터와 저장된 규칙 구조가 일치한다.
- 좌측 목록에서 규칙을 다시 선택하면 JSON Editor에 저장된 값이 표시된다.
- `GET /cep/rules/{rule_id}` API로 조회한 결과가 폼 입력과 일치한다.

---

## 9. 장애 대응 플레이북

### 9.1 증상: 규칙이 동작하지 않음

점검 순서:
1. rule active 상태
2. trigger spec 필드명 오타
3. payload path 불일치
4. simulate 결과와 실데이터 차이

### 9.2 증상: 알림이 오지 않음

점검 순서:
1. 채널 테스트 성공 여부
2. webhook URL/auth
3. timeout/네트워크
4. retry 로그

### 9.3 증상: 이벤트 폭주

점검 순서:
1. threshold 상향
2. window/aggregation 적용
3. suppress 정책 도입
4. 임시 비활성화

### 9.4 증상: anomaly 오탐 다수

점검 순서:
1. threshold 조정
2. method 변경(zscore -> iqr/ema)
3. baseline 데이터 품질 점검

---

## 10. 운영 체크리스트

```text
[ ] metric/event/schedule/anomaly 규칙을 각각 1개 이상 만들어봤다.
[ ] simulate와 실제 trigger를 모두 수행했다.
[ ] events 목록/상세/ack 흐름을 수행했다.
[ ] channels test를 통과했다.
[ ] 장애 대응 시나리오를 재현하고 복구했다.
```

---

## 11. 참고 파일

- `apps/web/src/app/cep-builder/page.tsx`
- `apps/api/app/modules/cep_builder/router.py`
- `apps/api/app/modules/cep_builder/executor.py`
- `apps/api/app/modules/cep_builder/bytewax_engine.py`
- `apps/api/app/modules/cep_builder/anomaly_detector.py`


---

## 12. Lab 9 - Scheduler/운영 상태 점검

목표: 스케줄러 기반 규칙 운영 상태를 주기적으로 점검.

### Step 1. 스케줄러 상태 조회

- `GET /cep/scheduler/status`
- `GET /cep/scheduler/instances`

### Step 2. metric polling 상태 조회

- `GET /cep/scheduler/metric-polling`
- `GET /cep/scheduler/metric-polling/snapshots/latest`

### Step 3. 이상 징후 확인

- 실행 누락
- 지연 증가
- 특정 인스턴스 편중

검증 포인트:
- 운영 지표를 근거로 규칙 지연을 설명할 수 있다.

---

## 13. Lab 10 - SSE 이벤트 스트림 확인

목표: 실시간 이벤트 관찰 루틴 익히기.

### Step 1. 스트림 구독

- `GET /cep/events/stream`

### Step 2. 클라이언트 처리

1. open 이벤트 처리
2. message 이벤트 파싱
3. error 시 재연결

### Step 3. 운영 포인트

- 연결 유지(ping)
- 브라우저 탭 전환 시 복구
- 네트워크 불안정 시 backoff 재접속

검증 포인트:
- 이벤트 발생 즉시 스트림 반영
- 연결 오류 후 재연결 성공

---

## 14. Lab 11 - 규칙 Form 입력과 API 입력 동기화

목표: UI Form과 API 모델의 불일치를 줄인다.

### Step 1. Form으로 규칙 생성

- `/cep-builder`에서 작성 후 저장

### Step 2. API 조회로 구조 확인

- `GET /cep/rules/{rule_id}`

### Step 3. 비교 항목

- trigger_type
- trigger_spec
- conditions
- action_spec

검증 포인트:
- 폼 입력과 저장 모델의 필드가 일치한다.

---

## 15. Lab 12 - 채널 실패 주입 테스트

목표: 운영 중 채널 장애를 미리 경험하고 대응 절차 고정.

### 시나리오 A: 잘못된 webhook URL

1. webhook endpoint를 존재하지 않는 URL로 설정
2. 규칙 trigger 실행
3. 실패 로그 확인

### 시나리오 B: 인증 누락

1. auth 헤더 제거
2. trigger 실행
3. 401/403 처리 확인

### 시나리오 C: timeout

1. timeout 짧게 설정
2. 응답 느린 endpoint 호출
3. retry 기록 확인

복구 공통 절차:
1. 채널 설정 수정
2. channels test 재실행
3. rule 재trigger

---

## 16. Lab 13 - Anomaly 튜닝 실습

목표: 오탐과 미탐을 균형 있게 조정.

### Step 1. 기준치 확인

- 최근 1일 이벤트 수
- anomaly score 분포

### Step 2. 파라미터 튜닝

- zscore threshold 상향/하향
- iqr multiplier 조정
- ema alpha 조정

### Step 3. 재평가

- 동일 데이터 구간에서 재시뮬레이션
- 오탐 비율 비교

검증 포인트:
- 튜닝 전후 이벤트 품질 차이를 수치로 설명 가능

---

## 17. Lab 14 - 운영용 Rule 세트 구축

목표: 단일 규칙이 아니라 운영 규칙 세트를 설계.

권장 분류:
1. Critical Alert Rule
2. Warning Trend Rule
3. Daily Report Rule
4. Auto Trigger Rule

각 Rule 공통 체크:
- owner 지정
- 설명 필수
- simulate 기록
- rollback 전략

---

## 18. 운영 부록 - Rule 리뷰 템플릿

배포 전 리뷰 질문:

1. 이 규칙이 얼마나 자주 발동될 것으로 예상되는가?
2. 오탐/미탐 시 운영 영향은 무엇인가?
3. 채널 장애 시 대체 경로가 있는가?
4. ACK 없이 방치되는 이벤트가 생길 수 있는가?
5. 규칙 비활성화 기준이 문서화되어 있는가?

---

## 19. 운영 부록 - 장애 대응 시간 단축 체크

장애 발생 시 5분 루틴:

1. events 목록에서 영향 범위 확인
2. rule 상세에서 trigger/action 설정 확인
3. channels test 즉시 실행
4. 실패 유형 분류(권한/네트워크/설정)
5. 임시 완화(비활성화/임계치 상향) 후 영구 수정


---

## 20. 완성 프로젝트 트랙 - 운영 CEP 룰팩 구축

목표: 단일 룰이 아니라 운영에 필요한 룰 세트를 완성한다.

룰팩 구성:
1. Critical Metric Rule
2. Error Event Rule
3. Schedule Health Rule
4. Anomaly Rule
5. Escalation Rule

### 20.1 룰 설계표 만들기

| Rule | Trigger | 조건 | 액션 | 우선순위 |
|---|---|---|---|---|
| critical_cpu | metric | cpu > 90 | notify+webhook | P1 |
| critical_error | event | severity=critical | webhook | P1 |
| health_check | schedule | 5분 주기 | api call | P2 |
| latency_anomaly | anomaly | zscore | notify | P2 |
| escalation | event | retry>3 | pager channel | P1 |

검증 포인트:
- 중복 룰이 없다.
- 룰 간 충돌(중복 알림)이 최소화된다.

### 20.2 단계별 구축

#### 단계 A: P1 룰 2개 먼저 배포

1. critical_cpu
2. critical_error

실행 후 확인:
- 이벤트 생성 여부
- 채널 발송 성공률

#### 단계 B: P2 룰 2개 배포

1. health_check
2. latency_anomaly

실행 후 확인:
- false positive 비율
- scheduler 안정성

#### 단계 C: escalation 룰 연계

1. 기존 이벤트를 trigger로 연결
2. 누적 실패 기준치 정의

검증 포인트:
- 중복 폭주 없이 escalation만 별도 동작

### 20.3 실패 주입 테스트 세트

아래 5개를 반드시 수행한다.

1. 잘못된 threshold
2. 잘못된 field path
3. 채널 인증 실패
4. webhook timeout
5. anomaly baseline 부족

기록표:

| 시나리오 | 기대 실패 | 실제 실패 | 복구 조치 | 재검증 |
|---|---|---|---|---|
| threshold typo | no match |  |  |  |
| field path error | eval fail |  |  |  |
| channel auth fail | notify fail |  |  |  |
| webhook timeout | retry |  |  |  |
| baseline 부족 | anomaly disabled |  |  |  |

### 20.4 운영 대시보드 점검 루틴

매일 점검:
1. events count
2. ack backlog
3. failed notifications
4. scheduler health
5. anomaly precision

주간 점검:
1. 룰별 발동 수 top5
2. 오탐 룰 top5
3. 채널 실패율
4. 평균 복구 시간

### 20.5 인수인계 산출물

각 Rule마다 작성:
1. 목적
2. 트리거/조건
3. 액션 경로
4. 실패 시 조치
5. 비활성화 기준

### 20.6 완료 판정

```text
[ ] 룰 5개가 활성 상태에서 정상 동작
[ ] 실패 주입 테스트 5개 완료
[ ] 채널 테스트 성공률 기준 충족
[ ] ack 운영 루틴 정착
[ ] 룰 인수인계 문서 완성
```

---

## 21. 실습 기록 시트

```text
[CEP 실습 기록]
날짜:
작성자:

1) 생성 룰 수:
2) simulate 성공률:
3) false positive 관찰:
4) channel 실패 건수:
5) 개선 항목:
```

---

## 22. 팀 운영 규칙 샘플

1. Rule 배포 전 simulate 3회 이상
2. 채널 테스트 통과 없는 배포 금지
3. P1 룰은 owner/backup owner 필수
4. anomaly 룰은 baseline 확보 전 활성화 금지
5. 이벤트 ACK SLA를 운영 규칙으로 관리

---

## 23. Recent Changes (2026-02-14 to 2026-02-15)

### 예외 처리 프레임워크 통합
- ✅ Circuit Breaker 패턴 구현 (closed/open/half-open 상태)
- ✅ Retry 메커니즘 (exponential backoff: 1s → 2s → 4s → 8s)
- ✅ 타임아웃 정책 (CEP 규칙 실행: 5s, HTTP webhook: 10s)
- ✅ Admin Observability Dashboard 통합 (규칙 성능/실패율 모니터링)

### Production Readiness 향상
- CEP 규칙 실행 안정성 75% → 85%
- 채널 실패 복구율 90% 이상
- 장애 자동 감지/로깅 완비

---

## 24. Error Handling & Recovery

### Circuit Breaker 상태 관리

```
[Closed]                 # 정상 상태 (요청 통과)
  │ (3회 연속 실패)
  ↓
[Open]                   # 차단 상태 (즉시 실패 응답)
  │ (30초 경과)
  ↓
[Half-Open]              # 복구 테스트 상태 (1회 요청만 시도)
  │ (성공 또는 실패)
  ↓
[Closed] 또는 [Open]     # 상태 전환
```

**적용 대상**:
- 채널별 webhook 호출 (Slack, Email, Discord 등)
- 외부 API 호출 (HTTP 액션)
- DB 연결 (메트릭 폴링)

**설정 방법**:
1. CEP Rule에 `action_config` 추가:
   ```json
   {
     "action": "webhook",
     "circuit_breaker": {
       "failure_threshold": 3,
       "timeout_seconds": 30,
       "half_open_max_requests": 1
     }
   }
   ```

### Retry 정책 (지수 백오프)

```
1차 시도 실패 → 1초 대기 → 2차 시도
2차 시도 실패 → 2초 대기 → 3차 시도
3차 시도 실패 → 4초 대기 → 4차 시도
4차 시도 실패 → 8초 대기 → 5차 시도 (최종)
5차 시도 실패 → 최종 실패 기록 + 폴백 액션 실행
```

**설정**:
- 최대 재시도: 4회 (총 5회 시도)
- 초기 간격: 1초
- 최대 간격: 8초
- 백오프 배수: 2배

### 실패 유형별 복구 체크리스트

| 실패 유형 | 원인 | 자동 복구 | 수동 조치 |
|---------|------|---------|---------|
| **Webhook Timeout** | 네트워크 지연/엔드포인트 느림 | Retry 3회 후 포기 | 엔드포인트 성능 점검 |
| **Authentication Failure** | API 키/토큰 만료 | ❌ (즉시 실패) | 인증 정보 갱신 |
| **Rate Limit** (429) | 요청 폭주 | Retry 3회 후 포기 | 송신 빈도 조절 |
| **Network Unreachable** | 방화벽/DNS 문제 | Retry 3회 후 포기 | 네트워크 설정 확인 |
| **Database Connection Loss** | DB 다운/네트워크 끊김 | Circuit Breaker open | DB 상태 복구 대기 |
| **Template Rendering Error** | 메시지 템플릿 변수 미정의 | ❌ (즉시 실패) | 템플릿 변수 확인 |

---

## 25. Production Best Practices

### 1. Exception Handling 패턴

**Pattern A: 안전한 Fallback**
```python
# CEP 규칙이 기본 채널 실패 시 백업 채널로 자동 전환
{
  "actions": [
    {
      "type": "notify",
      "channels": ["Slack"],
      "fallback_channel": "Email",  # 기본 실패 시 이메일로 자동 전환
      "message": "중요 경보: {{severity}}"
    }
  ]
}
```

**Pattern B: 실패 로깅 + 복구 알림**
```
1. 채널 전송 실패 → 상세 에러 로그 기록
2. 3회 재시도 모두 실패 → Circuit Breaker open
3. 관리자에게 "채널 Slack 다운" 알림 (우회 채널로)
4. 30초 후 자동 복구 테스트 (half-open)
```

### 2. Monitoring 규칙 설정

**Admin > Observability**에서 다음 메트릭 모니터링:

1. **Rule 성능**:
   - Average duration: < 500ms (정상)
   - p95 latency: < 2s
   - p99 latency: < 5s

2. **채널 신뢰도**:
   - Success rate: > 95%
   - Fallback rate: < 10%
   - Circuit breaker open 횟수: 0 (정상)

3. **이벤트 품질**:
   - False positive rate: < 5%
   - ACK 대기 시간: < 1시간 (SLA)
   - 미응답 이벤트: 0

### 3. Debugging 워크플로우

**증상: 규칙 trigger되지 않음**
1. `/cep-builder` → 규칙 선택 → Test 탭
2. 시뮬레이션 실행 (matched=true 여부 확인)
3. Manual trigger로 1회 테스트
4. `/cep-events`에서 이벤트 생성 여부 확인
5. Logs 탭에서 exec_id, status, error_message 확인

**증상: 채널 전송 실패**
1. Channels > Test Panel에서 채널 개별 테스트
2. API 키/URL/인증 정보 확인
3. Admin > Observability에서 채널별 success rate 확인
4. 최근 이벤트 로그에서 실패 패턴 분석 (timeout/auth/rate-limit)

**증상: 이벤트 폭주**
1. Rule threshold 상향 (예: CPU > 85 → CPU > 90)
2. Window/Aggregation 적용 (tumbling 5m)
3. Suppress 정책 추가 (같은 rule 1시간에 1회만)
4. 임시 비활성화 후 진단
