# CEP User Guide

**Last Updated**: 2026-02-08

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

처리 흐름:

`Event -> Filter -> Aggregation -> Anomaly(optional) -> Window -> Action -> Notification`

Trigger 타입:
- `metric`
- `event`
- `schedule`
- `anomaly`

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

- Rule Name: `critical_error_event`
- Trigger Type: `event`
- event_type: `error`

### Step 2. 조건 추가

- severity == `critical`
- service == `api-gateway`
- logic: `AND`

### Step 3. 액션 구성

- Webhook -> PagerDuty endpoint
- Notify -> Slack channel

### Step 4. Trigger 테스트

`POST /cep/rules/{rule_id}/trigger` 또는 simulate payload 실행

검증 포인트:
- critical 이벤트만 매칭된다.
- warning 이벤트는 제외된다.

---

## 3. Lab 3 - Schedule Rule 만들기

목표: 매 5분 상태 점검 작업 실행.

### Step 1. Trigger 설정

- Trigger Type: `schedule`
- cron: `*/5 * * * *`

### Step 2. Action 설정

- API call / webhook로 상태 점검 API 호출

### Step 3. 검증

- 시뮬레이션/수동 trigger로 동작 확인
- `/cep-events`에서 주기 실행 확인

검증 포인트:
- 주기 실행 누락이 없다.

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

예시:
- `(cpu > 80 AND memory > 70) OR disk > 90`

### Step 2. 집계 설정

- aggregation: `avg`
- field: `cpu_percent`
- window: `5m`

### Step 3. 시뮬레이션

조건별 true/false를 확인하며 payload 조정

검증 포인트:
- 조건 논리 오해 없이 의도대로 실행된다.

---

## 6. Lab 6 - 채널 테스트와 알림 신뢰성 점검

목표: 채널별 전달 실패를 사전에 줄인다.

### Step 1. 채널 테스트 API

- `POST /cep/channels/test`

### Step 2. 채널 타입 확인

- `GET /cep/channels/types`
- `GET /cep/channels/status`

### Step 3. 실패 대응 점검

- endpoint timeout
- auth 오류
- 메시지 템플릿 누락

검증 포인트:
- 채널 테스트가 최소 1회 성공
- 실패 원인이 재현 가능하게 기록

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

목표: form 작성과 JSON preview를 함께 사용해 규칙 정합성 확보.

### Step 1. 폼 작성

- 기본 정보
- trigger spec
- conditions
- actions

### Step 2. 미리보기

- `POST /cep/rules/preview`
- UI Preview JSON 확인

### Step 3. Form 저장

- `POST /cep/rules/form`

검증 포인트:
- 폼 데이터와 저장된 규칙 구조가 일치한다.

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
□ metric/event/schedule/anomaly 규칙을 각각 1개 이상 만들어봤다.
□ simulate와 실제 trigger를 모두 수행했다.
□ events 목록/상세/ack 흐름을 수행했다.
□ channels test를 통과했다.
□ 장애 대응 시나리오를 재현하고 복구했다.
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
□ 룰 5개가 활성 상태에서 정상 동작
□ 실패 주입 테스트 5개 완료
□ 채널 테스트 성공률 기준 충족
□ ack 운영 루틴 정착
□ 룰 인수인계 문서 완성
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

