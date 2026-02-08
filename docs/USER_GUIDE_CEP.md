# CEP User Guide

**Last Updated**: 2026-02-08

## 1. 목적과 대상

이 문서는 CEP(Complex Event Processing)를 처음 운영하는 사용자가 실제로 규칙을 만들고, 시뮬레이션하고, 배포 후 모니터링까지 끝낼 수 있도록 작성한 따라하기 가이드다.

대상 사용자:
- 운영자 (알림/장애 대응 담당)
- 백엔드 엔지니어 (규칙/액션 연동 담당)
- SRE/온콜 (이상 이벤트 분석 담당)

---

## 2. 시작 전 준비

### 2.1 필수 확인

1. 백엔드와 프론트엔드가 실행 중인지 확인
2. 로그인 가능한 계정과 테넌트(`x-tenant-id`) 준비
3. 알림 채널(웹훅/이메일/슬랙 등) 테스트 대상 준비

### 2.2 핵심 개념 (실습 전에 3분)

처리 파이프라인:

`Event Input -> Filter -> Aggregation -> Anomaly(optional) -> Window -> Action -> Notification`

- Trigger: 언제 규칙을 시작할지 정의 (`metric`, `event`, `schedule`, `anomaly`)
- Condition: 어떤 경우에만 통과시킬지 정의
- Action: 통과된 이벤트에 대해 무엇을 실행할지 정의
- Event Log: 실행 결과와 실패 원인을 남기는 운영 근거

---

## 3. 튜토리얼 A: 첫 규칙 만들기 (Metric 임계치)

목표: CPU 사용률이 85%를 넘으면 알림을 보내는 규칙 1개를 배포한다.

### Step 1. Rule 생성

1. `/cep-builder` 접속
2. `New Rule` 클릭
3. 아래 값 입력
- Rule Name: `cpu_high_alert`
- Description: `CPU > 85 for 5m`
- Enabled: `OFF` (초기에는 비활성)

검증 포인트:
- 저장 후 목록에서 Draft 상태로 보인다.

### Step 2. Trigger 설정

1. Trigger Type: `metric`
2. Metric Key: `cpu_usage`
3. Operator: `>`
4. Threshold: `85`
5. Window: `5m`

검증 포인트:
- Trigger 미리보기(있다면)에서 조건식이 `cpu_usage > 85`로 표시된다.

### Step 3. Action 설정

1. Action Type: `notification` 또는 `webhook`
2. 채널/URL 입력
3. Payload 템플릿 설정
- rule_id
- severity
- metric_value
- occurred_at

검증 포인트:
- 필수 필드 누락 경고 없이 저장된다.

### Step 4. Simulate 실행

1. `Simulate` 클릭
2. 테스트 입력값 `cpu_usage=92`로 실행
3. 결과에서 Condition 통과 여부 확인

검증 포인트:
- `passed=true`
- Action 실행 성공
- 이벤트 로그 생성

### Step 5. 활성화 및 관측

1. Rule을 `Enabled=ON`으로 변경
2. `/cep-events`로 이동
3. 최근 10분 필터에서 이벤트 생성 여부 확인

검증 포인트:
- 이벤트 목록에 `cpu_high_alert`가 나타난다.
- 상세에서 payload와 action 결과를 확인할 수 있다.

---

## 4. 튜토리얼 B: Schedule 기반 점검 규칙 만들기

목표: 매 5분마다 상태 점검 API를 호출하는 규칙을 구성한다.

### Step 1. Trigger 선택

- Trigger Type: `schedule`
- Cron: `*/5 * * * *`

### Step 2. Action 연결

- Action Type: `API Engine`
- 대상 API: 상태 점검용 API ID 선택
- 입력 매핑: `tenant_id`, `trace_id`

### Step 3. Simulate로 사전 검증

- 즉시 실행(simulate)
- API 응답코드와 실행 시간 확인

### Step 4. 활성화

- Rule 활성화 후 `/cep-events`에서 5분 주기로 이벤트 생성 확인

검증 포인트:
- 실패 이벤트가 반복되면 API 타임아웃/권한을 먼저 점검한다.

---

## 5. 튜토리얼 C: 이상 탐지(Anomaly) 규칙 조정

목표: 오탐(false positive)을 줄이도록 민감도를 조정한다.

### 기본 절차

1. Trigger Type `anomaly` 선택
2. 초기값 적용
- alpha: 기본값
- multiplier: 기본값
- threshold: 기본값
3. 최근 1일 이벤트 확인
4. 오탐이 많으면 민감도 완화
- threshold 상향
- multiplier 상향
- window 확대

검증 포인트:
- 조정 전후 이벤트 발생 건수/실제 장애 적중률을 비교한다.

---

## 6. 운영 중 필수 화면 사용법

### 6.1 `/cep-builder`

주요 사용 시점:
- 규칙 생성/수정/시뮬레이션/활성화

확인할 항목:
- Rule 상태(Draft/Enabled)
- Trigger/Action 정합성
- 시뮬레이션 결과 로그

### 6.2 `/cep-events`

주요 사용 시점:
- 발생 이벤트 분석
- 실패 이벤트 분류
- ACK 처리

확인할 항목:
- severity, rule, timestamp
- 실패 사유(권한/타임아웃/외부 오류)

### 6.3 Admin 연계

- `/admin/observability`: 처리량/오류율/지연 추세
- `/admin/logs`: 예외 스택, 외부 호출 오류
- `/admin/assets`: 관련 정책/템플릿 자산 관리

---

## 7. 장애 대응 플레이북

### 시나리오 1. 규칙은 동작했는데 알림이 오지 않음

1. `/cep-events`에서 action 결과 확인
2. 채널 credential/endpoint/timeout 점검
3. 웹훅 대상 서버 상태 확인
4. 재시도 정책 확인

### 시나리오 2. 이벤트 폭주

1. threshold 상향
2. aggregation/window 적용
3. suppress/debounce 정책 추가
4. 임시로 규칙 비활성화 후 재조정

### 시나리오 3. UI에 이벤트가 비어 보임

1. 시간 필터 확인
2. 테넌트 헤더(`x-tenant-id`) 확인
3. 권한/인증 토큰 만료 여부 확인

---

## 8. 배포 전 체크리스트

- Simulate가 성공했고 결과가 기대와 일치한다.
- 알림 채널 테스트를 최소 1회 통과했다.
- 폭주 방지 조건(window/aggregation/suppress)을 검토했다.
- 테넌트 격리 조건이 보장된다.
- 장애 시 롤백/비활성화 절차를 팀이 공유했다.

---

## 9. 참고 API

- `POST /cep/rules`
- `GET /cep/rules`
- `PUT /cep/rules/{rule_id}`
- `PATCH /cep/rules/{rule_id}/toggle`
- `POST /cep/rules/{rule_id}/simulate`
- `POST /cep/rules/{rule_id}/trigger`
- `GET /cep/events`
- `GET /cep/events/summary`

---

## 10. 향후 고도화 과제

- 규칙별 Rate Limit 정책 표준화
- 이벤트 리플레이/백필 기능
- 채널별 QoS 분리
- 규칙 성능 랭킹 대시보드 강화
