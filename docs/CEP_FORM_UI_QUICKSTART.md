# CEP 폼 기반 UI 빌더 - 빠른 시작 가이드

## 🚀 5분 안에 규칙 만들기

### 1단계: 페이지 접속
```
URL: http://localhost:3000/cep-builder-v2
```

### 2단계: 기본 정보 입력
```
규칙명: "CPU 고가용 모니터링"
설명: "CPU가 80% 이상일 때 Slack 알림 전송"
활성화: ON
```

### 3단계: 트리거 선택
```
타입: 📊 메트릭
메트릭명: cpu_usage
연산자: >
임계값: 80
집계 방식: avg (평균)
시간 윈도우: 5m (5분)
```

### 4단계: 복합 조건 추가 (선택사항)
```
Logic: AND
조건1:
  - 필드: status
  - 연산자: ==
  - 값: running

조건2:
  - 필드: environment
  - 연산자: ==
  - 값: production
```

### 5단계: 액션 설정 (필수)
```
액션1 - Webhook:
  - Endpoint: https://api.example.com/alerts
  - Method: POST

액션2 - Notify:
  - 메시지: "CPU 사용량이 80% 초과했습니다"
  - 채널: Slack 체크
```

### 6단계: 시뮬레이션
```
테스트 데이터 입력:
{
  "cpu_usage": 85,
  "status": "running",
  "environment": "production"
}

🧪 시뮬레이션 실행 → ✅ 조건 일치됨
```

### 7단계: 저장
```
✓ 규칙 저장 버튼 클릭
→ 규칙이 저장되고 /cep-events로 이동
```

---

## 💡 일반적인 규칙 예제

### 예제 1: 메모리 부족 경고
```
트리거:
- 타입: 메트릭
- 메트릭: memory_percent
- 연산자: >
- 임계값: 85

조건:
- server_type == "production"

액션:
- Email: ops-team@company.com
- Slack: #alerts
```

### 예제 2: 에러 이벤트 탐지
```
트리거:
- 타입: 이벤트
- 이벤트 타입: error

조건:
- severity == "critical"
- service == "api-gateway"

액션:
- Webhook: https://pagerduty.com/api/incidents
```

### 예제 3: 정기적 보고서
```
트리거:
- 타입: 스케줄
- Cron: 0 9 * * * (매일 9시)

액션:
- Webhook: https://api.company.com/reports
```

---

## 🎯 트리거 타입별 설정

### 메트릭 트리거 (📊)
메트릭 임계값 기반 규칙

**필수 필드**:
- `metricName`: 모니터링할 메트릭
  - 예: `cpu_usage`, `memory_percent`, `disk_usage`
- `operator`: 비교 연산자
  - 옵션: `>`, `<`, `>=`, `<=`, `==`, `!=`
- `threshold`: 임계값
  - 예: `80`
- `aggregation`: 집계 방식
  - 옵션: `avg` (평균), `max` (최대), `min` (최소), `sum` (합계), `count` (개수)
- `duration`: 시간 윈도우
  - 옵션: `1m`, `5m`, `10m`, `15m`, `30m`, `1h`

**예제**:
```json
{
  "metricName": "cpu_usage",
  "operator": ">",
  "threshold": "80",
  "aggregation": "avg",
  "duration": "5m"
}
```

### 이벤트 트리거 (📢)
특정 이벤트 타입 감지

**필수 필드**:
- `eventType`: 이벤트 타입
  - 예: `error`, `warning`, `alert`, `deployment`

**예제**:
```json
{
  "eventType": "error"
}
```

### 스케줄 트리거 (⏰)
정기적인 실행

**필수 필드**:
- `scheduleExpression`: Cron 표현식
  - 예: `0 9 * * *` = 매일 9시
  - 예: `*/5 * * * *` = 5분마다

**Cron 표현식 참고**:
```
분 시 일 월 요일
 |  |  |  |  |
 |  |  |  |  └─ 요일 (0=일, 1=월, ..., 6=토)
 |  |  |  └───── 월 (1-12)
 |  |  └──────── 일 (1-31)
 |  └─────────── 시 (0-23)
 └────────────── 분 (0-59)

예제:
0 9 * * *      → 매일 9시
0 9 * * 1      → 매주 월요일 9시
0 0 1 * *      → 매월 1일 자정
*/5 * * * *    → 5분마다
0 */2 * * *    → 2시간마다
```

---

## 🔗 복합 조건 사용법

### AND 로직
**모든 조건이 참일 때만 실행**

```
조건1: cpu > 80
AND
조건2: memory > 70
AND
조건3: status == "running"
→ 셋 다 참일 때만 액션 실행
```

### OR 로직
**하나라도 참이면 실행**

```
조건1: memory > 90
OR
조건2: disk > 95
OR
조건3: network_error > 5
→ 하나라도 참이면 액션 실행
```

### NOT 로직
**모든 조건이 거짓일 때만 실행**

```
조건1: status != "healthy"
AND
조건2: cpu > 50
→ status가 healthy가 아니고 cpu가 50 이상일 때
```

---

## 📤 액션 타입별 설정

### Webhook 액션
**외부 API 호출**

필드:
- `endpoint`: API 엔드포인트 URL
- `method`: HTTP 메서드 (GET, POST, PUT, DELETE)

예제:
```
endpoint: https://api.company.com/alerts
method: POST
```

### Notify 액션
**채널별 알림 전송**

필드:
- `message`: 알림 메시지
- `channels`: 알림 채널 (다중 선택)
  - Slack
  - Email
  - SMS
  - Discord

예제:
```
message: "CPU 사용량이 80% 초과했습니다"
channels: [Slack, Email]
```

### Trigger 액션
**다른 규칙 실행**

다른 규칙을 자동으로 실행합니다.

### Store 액션
**데이터 저장**

이벤트 데이터를 저장소에 보관합니다.

---

## 🧪 시뮬레이션 사용법

### 테스트 데이터 입력
```json
{
  "cpu_usage": 85,
  "memory_percent": 72,
  "status": "running",
  "environment": "production"
}
```

### 시뮬레이션 결과
```
✅ 조건 일치됨

조건 결과:
✓ cpu_usage > 80 → 일치 ✓
✓ status == "running" → 일치 ✓
✓ environment == "production" → 일치 ✓

실행될 액션:
📤 Webhook: POST https://api.company.com/alerts
📤 Notify: Slack - "CPU 사용량이 80% 초과했습니다"
```

### 시뮬레이션 팁
1. **엣지 케이스 테스트**: 임계값 근처의 값으로 테스트
2. **여러 조건 테스트**: 각 조건을 ON/OFF로 테스트
3. **타입 확인**: 값의 타입이 메트릭과 일치하는지 확인

---

## 📊 선택 옵션: 고급 기능

### 윈도우 설정
데이터를 시간 단위로 분할하는 방식 선택

**Tumbling Window** (기본):
```
[5m] [5m] [5m] ...
겹치지 않는 윈도우
```

**Sliding Window**:
```
[------5m------]
    [------5m------]
        [------5m------]
겹치는 윈도우 (1m씩 슬라이드)
```

**Session Window**:
```
[----session1----] [----session2----]
10분 동안 활동이 없으면 세션 종료
```

### 집계 설정
윈도우 내에서 데이터 집계 방식

```
필드: cpu_usage
함수: avg (평균)
출력명: avg_cpu
그룹화: region, service
```

### 데이터 보강
외부 데이터로 이벤트 확장

```
타입: lookup
소스: Redis (user_data)
키: user_id
출력: user_name
```

---

## ✨ JSON 미리보기

생성되는 JSON 구조 확인:

```json
{
  "rule_name": "CPU 고가용 모니터링",
  "description": "CPU가 80% 이상일 때 알림",
  "is_active": true,
  "trigger_type": "metric",
  "trigger_spec": {
    "metric_name": "cpu_usage",
    "operator": ">",
    "threshold": "80",
    "aggregation": "avg",
    "duration": "5m"
  },
  "composite_condition": {
    "conditions": [
      { "field": "status", "op": "==", "value": "running" }
    ],
    "logic": "AND"
  },
  "actions": [
    {
      "type": "webhook",
      "endpoint": "https://api.company.com/alerts",
      "method": "POST"
    }
  ]
}
```

---

## 🎯 필드 입력 팁

### 메트릭명 입력
```
공백 없이 snake_case 사용
❌ CPU Usage
❌ cpu usage
✅ cpu_usage

일반적인 메트릭:
- cpu_usage
- memory_percent
- disk_usage
- network_bandwidth
- response_time
- error_rate
```

### 필드명 입력
```
조건의 필드명도 일관되게
❌ Status
❌ status code
✅ status

JSON 경로로 중첩 필드 접근 가능:
✅ data.cpu
✅ metrics.memory
```

### 값 입력
```
숫자: 80, 100.5
문자열: "running", "error"
불리언: true, false (필터링에는 사용 불가)
```

---

## ❓ FAQ

**Q: 규칙을 저장했는데 적용되지 않았어요**
A: `/cep-events` 페이지에서 규칙이 활성화되어 있는지 확인하세요

**Q: 메트릭 이름을 모르는데요?**
A: 시스템의 실제 메트릭을 확인하고 입력하세요. 자동완성이 제공됩니다

**Q: 여러 조건을 AND/OR로 혼합할 수 있나요?**
A: 현재는 모든 조건에 같은 로직(AND/OR/NOT)을 적용합니다

**Q: 규칙을 테스트 후 실제 적용되는지 확인하려면?**
A: `/cep-events`에서 실시간으로 발생하는 이벤트를 모니터링하세요

**Q: 액션이 실행되지 않았어요**
A: 1) 규칙이 활성화되어 있는지 확인
   2) 조건이 실제로 일치하는지 시뮬레이션으로 테스트
   3) 액션의 엔드포인트가 올바른지 확인

---

## 🔗 관련 문서

- **[상세 가이드](./CEP_FORM_UI_GUIDE.md)**: 모든 기능의 상세 설명
- **[구현 계획](./CEP_IMPLEMENTATION_PLAN.md)**: 기술 아키텍처 및 설계
- **[완료 요약](./CEP_PROJECT_COMPLETION_SUMMARY.md)**: 프로젝트 전체 개요

---

## 🚨 주의사항

1. **필수 필드 확인**: 규칙명, 트리거, 최소 1개 액션은 필수
2. **시뮬레이션 권장**: 저장 전에 꼭 시뮬레이션으로 테스트
3. **JSON 검증**: JSON 미리보기에서 구조 확인
4. **중복 규칙**: 같은 이름의 규칙을 여러 개 만들 수 있으므로 주의

---

## 📞 지원

문제가 발생하면:
1. 이 빠른 시작 가이드 다시 읽기
2. 상세 가이드 확인
3. 시뮬레이션으로 규칙 검증
4. 개발팀에 문의

Happy CEP Rule Building! 🎉
