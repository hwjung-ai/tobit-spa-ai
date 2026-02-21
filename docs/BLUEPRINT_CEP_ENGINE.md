# CEP Engine Blueprint (v2 Final)

> **Last Updated**: 2026-02-20
> **Status**: ✅ **Production Ready**
> **Production Readiness**: 95%

## 1. 목적

Complex Event Processing (CEP) 엔진은 실시간 이벤트 스트림에서 패턴을 감지하고,
조건 기반 알림을 발송하는 이벤트 처리 시스템이다.

핵심 목표:
1. 복합 조건(AND/OR/NOT) 기반 실시간 이벤트 매칭
2. 7가지 집계 함수를 통한 메트릭 분석
3. 5가지 채널을 통한 자동 알림 발송
4. 분산 환경 지원 (Redis 상태 관리)
5. ML 기반 이상 탐지 (Z-Score, IQR, EMA 알고리즘)

---

## 2. 아키텍처

### 2.1 처리 파이프라인

```
Event Input
    ↓
FilterProcessor (조건 필터링: AND/OR/NOT)
    ↓
AggregationProcessor (메트릭 집계: count/sum/avg/min/max/std/percentile)
    ↓
AnomalyDetector (ML 이상 탐지: Z-Score/IQR/EMA)  ← NEW
    ↓
WindowProcessor (시간 윈도우: tumbling/sliding/session)
    ↓
EnrichmentProcessor (데이터 보강)
    ↓
Notification System (5가지 채널 발송)
    ↓
Redis State Manager (분산 상태 저장 + 베이스라인 관리)
```

### 2.2 레이어 구성 (11 모듈 아키텍처)

| 레이어 | 역할 | 주요 파일 |
|--------|------|----------|
| **API - Rules** | 규칙 CRUD operations | `cep_builder/router_rules.py` |
| **API - Events** | 이벤트 관리 & 쿼리 | `cep_builder/router_events.py` |
| **API - Simulation** | 규칙 시뮬레이션 & dry-run | `cep_builder/router_simulation.py` |
| **API - Monitoring** | 성능 모니터링 & 통계 | `cep_builder/router_monitoring.py` |
| **API - Channels** | 알림 채널 관리 | `cep_builder/router_channels.py` |
| **API - Anomaly** | 이상 탐지 엔드포인트 | `cep_builder/router_anomaly.py` |
| **API - Bytewax** | Bytewax 엔진 통합 | `cep_builder/router_bytewax.py` |
| **API - Forms** | UI 폼 ↔ JSON 변환 | `cep_builder/router_forms.py` |
| **API - Templates** | 템플릿 관리 | `cep_builder/router_templates.py` |
| **API - Execute** | 직접 실행 트리거 | `cep_builder/router_execute.py` |
| **API - Health** | 헬스 체크 & 진단 | `cep_builder/router_health.py` |
| **Bytewax 통합** | 규칙 변환, 평가, 이벤트 처리 | `cep_builder/bytewax_executor.py` |
| **엔진 코어** | 프로세서 체인, 규칙 평가 | `cep_builder/bytewax_engine.py` |
| **기존 실행기** | 하위 호환 평가 로직 (+ anomaly) | `cep_builder/executor.py` |
| **이상 탐지** | ML 기반 이상 탐지 (3 알고리즘) | `cep_builder/anomaly_detector.py` |
| **알림** | 5채널 발송, 재시도, 템플릿 | `cep_builder/notification_*.py` |
| **상태 관리** | Redis 분산 상태 | `cep_builder/redis_state_manager.py` |
| **폼 변환** | UI JSON ↔ 규칙 양방향 변환 | `cep_builder/form_converter.py` |

### 2.3 하이브리드 아키텍처

기존 executor와 Bytewax 엔진이 병행 운영되며 점진적 마이그레이션 지원:

```python
def evaluate_rule_with_bytewax(rule_id, trigger_type, trigger_spec, payload):
    # 현재 운영: 기존 executor 로직 사용 + Bytewax에 규칙 등록
    matched, refs = evaluate_trigger(trigger_type, trigger_spec, payload)
    return matched, refs

    # 목표 구조: Bytewax 엔진으로 직접 평가
    # results = engine.process_event(rule_id, event)
```

---

## 3. CEP 규칙 시스템

### 3.1 규칙 구조

```json
{
  "rule_id": "rule-123",
  "rule_name": "CPU Alert",
  "trigger_type": "metric",
  "trigger_spec": {
    "conditions": [
      {"field": "cpu", "op": ">", "value": 80},
      {"field": "memory", "op": ">", "value": 70}
    ],
    "logic": "AND",
    "aggregation": {
      "type": "avg",
      "field": "cpu_percent"
    }
  },
  "action_spec": {
    "endpoint": "https://webhook.example.com/alerts",
    "method": "POST"
  }
}
```

### 3.2 복합 조건

| 연산자 | 설명 | 예시 |
|--------|------|------|
| `AND` | 모든 조건 TRUE | CPU > 80 AND Memory > 70 |
| `OR` | 하나 이상 TRUE | CPU > 90 OR Memory > 90 |
| `NOT` | 모든 조건 FALSE | NOT (status == "healthy") |
| 중첩 | 조건 그룹 중첩 | (CPU > 80 AND Memory > 70) OR Disk > 90 |

### 3.3 비교 연산자

`>`, `>=`, `<`, `<=`, `==`, `!=`, `contains`, `starts_with`, `ends_with`, `in`, `not_in`

### 3.4 Trigger 유형 (4가지)

| 타입 | 설명 | 용도 |
|------|------|------|
| `metric` | 메트릭 임계값 기반 | CPU > 80%, Memory > 90% |
| `event` | 외부 이벤트 기반 | API 호출, 웹훅 수신 |
| `schedule` | 시간 기반 (Cron) | 매일 오전 9시, 매 30분 |
| `anomaly` | ML 이상 탐지 기반 | 통계적 이상치 자동 감지 |

### 3.5 집계 함수 (7가지)

| 함수 | 설명 | 용도 |
|------|------|------|
| `count` | 이벤트 개수 | 발생 빈도 감지 |
| `sum` | 합계 | 누적량 계산 |
| `avg` | 평균 | 평균 부하 감지 |
| `min` | 최소값 | 최저치 감지 |
| `max` | 최대값 | 피크치 감지 |
| `std` | 표준편차 | 변동성 분석 |
| `percentile` | 백분위수 | p95/p99 레이턴시 |

### 3.6 윈도우 처리 (3가지)

| 타입 | 설명 | 용도 |
|------|------|------|
| `tumbling` | 고정 크기 비겹침 윈도우 | 분 단위 집계 |
| `sliding` | 겹치는 슬라이딩 윈도우 | 이동 평균 |
| `session` | 활동 기반 세션 윈도우 | 사용자 세션 분석 |

---

## 4. ML 기반 이상 탐지 (Anomaly Detection)

### 4.1 개요

임계값 기반 규칙(metric trigger) 외에, 통계적 알고리즘으로 데이터의 이상치를 자동 감지하는 기능.
`trigger_type: "anomaly"` 로 설정하면 베이스라인 데이터로부터 자동 학습 후 이상 여부를 판별한다.

### 4.2 탐지 알고리즘 (3가지)

| 알고리즘 | 설명 | 파라미터 | 적합 시나리오 |
|----------|------|----------|--------------|
| **Z-Score** | 이동 평균/표준편차 기반 | `threshold` (기본 3.0) | 정규 분포 메트릭 (CPU, 응답시간) |
| **IQR** | 사분위 범위 기반 | `multiplier` (기본 1.5) | 편향된 분포, 아웃라이어 탐지 |
| **EMA** | 지수 이동 평균 기반 | `alpha` (0.3), `threshold` (3.0) | 트렌드 추적, 점진적 변화 탐지 |

### 4.3 동작 흐름

```
이벤트 수신
    ↓
trigger_type == "anomaly"?
    ↓ Yes
베이스라인 로드 (Redis: cep:anomaly:baseline:{rule_id})
    ↓
현재 값 추출 (value_path 기반)
    ↓
detect_anomaly(values, current, method, config)
    ↓
AnomalyResult(is_anomaly, score, method, details)
    ↓
is_anomaly == True → Action 실행 (알림 등)
    ↓
베이스라인 갱신 (append_baseline, max 1000 포인트)
```

### 4.4 AnomalyResult 구조

```python
@dataclass
class AnomalyResult:
    is_anomaly: bool        # 이상 여부
    score: float            # 이상 점수 (Z-Score, IQR score 등)
    method: str             # 사용된 알고리즘 ("zscore", "iqr", "ema")
    details: Dict[str, Any] # 상세 정보 (mean, std, threshold, q1, q3 등)
```

### 4.5 Redis 베이스라인 관리

| 메서드 | 설명 |
|--------|------|
| `store_baseline(rule_id, values)` | 전체 베이스라인 저장 (TTL 24h) |
| `get_baseline(rule_id)` | 베이스라인 조회 |
| `append_baseline(rule_id, value, max_size=1000)` | 새 값 추가 (FIFO, max 1000) |

키 구조: `cep:anomaly:baseline:{rule_id}` (TTL: 24시간)

### 4.6 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/cep/rules/{rule_id}/anomaly-status` | 베이스라인 상태 조회 (포인트 수, 알고리즘, 통계 요약) |

### 4.7 Anomaly Trigger 설정 예시

```json
{
  "trigger_type": "anomaly",
  "trigger_spec": {
    "anomaly_method": "zscore",
    "anomaly_config": {
      "threshold": 3.0
    },
    "value_path": "cpu_percent",
    "baseline_window": 100,
    "baseline_values": []
  }
}
```

---

## 5. Notification 시스템

### 4.1 채널 (5가지)

| 채널 | 프로토콜 | 설정 | 전송 시간 |
|------|----------|------|----------|
| **Slack** | Webhook | webhook_url, channel | ~200ms |
| **Email** | SMTP | smtp_host, to, from | ~500ms |
| **SMS** | Twilio API | account_sid, auth_token, phone | ~300ms |
| **Webhook** | HTTP | url, method, headers | ~150ms |
| **PagerDuty** | Events API v2 | routing_key, severity | ~250ms |

### 4.2 재시도 메커니즘

- 지수 백오프: `1s → 2s → 4s → 8s`
- 지터: 충돌 방지용 랜덤 지연
- 스마트 판정: HTTP 상태 코드 기반 (4xx 재시도 안 함, 5xx 재시도)
- 최대 재시도: 3회 (설정 가능)
- 자동 폴백: 주 채널 실패 시 대체 채널

### 4.3 템플릿 시스템

- Jinja2 기반 메시지 렌더링
- 4가지 기본 템플릿 (Slack, Email, Webhook, SMS)
- 커스텀 템플릿 추가 가능
- 동적 변수 치환: `{{ alert_title }}`, `{{ severity }}`, `{{ alert_message }}`
- 렌더링 시간: ~5ms

---

## 6. Redis 분산 상태 관리

### 5.1 키 구조

```
cep:retry:<notification_id>:<channel_id>  → 재시도 기록 (TTL: 24h)
cep:rule:<rule_id>:state                  → 규칙 상태 (활성화, 통계)
cep:template:<template_name>              → 템플릿 캐시 (TTL: 24h)
cep:channel:<channel_name>                → Pub/Sub 채널
cep:anomaly:baseline:<rule_id>            → 이상 탐지 베이스라인 (TTL: 24h, max 1000)
```

### 5.2 기능

| 기능 | 설명 |
|------|------|
| 재시도 기록 | 저장/조회/삭제, 자동 만료 |
| 규칙 상태 | 활성화 여부, 실행 통계 |
| 템플릿 캐싱 | 렌더링 성능 최적화 |
| Pub/Sub | 이벤트 발행/구독 (알림 큐) |
| 이상 탐지 베이스라인 | 시계열 데이터 저장/갱신 (max 1000, FIFO) |
| 자동 폴백 | Redis 불가 시 메모리 기반 운영 |

### 5.3 메모리 vs Redis

| 항목 | 메모리 기반 | Redis 기반 |
|------|-----------|-----------|
| 영속성 | 없음 | 있음 |
| 다중 워커 | 불가 | 가능 |
| 자동 만료 | 수동 | TTL |
| 성능 | ~1ms | ~5ms |
| 확장성 | 단일 서버 | 무제한 |

---

## 7. API 엔드포인트 (11 모듈 라우터)

### 7.1 규칙 관리 (router_rules.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/cep/rules` | 규칙 생성 |
| `GET` | `/cep/rules` | 규칙 목록 |
| `GET` | `/cep/rules/{rule_id}` | 규칙 상세 |
| `PUT` | `/cep/rules/{rule_id}` | 규칙 수정 |
| `DELETE` | `/cep/rules/{rule_id}` | 규칙 삭제 |
| `PATCH` | `/cep/rules/{rule_id}/toggle` | 활성화/비활성화 |

### 7.2 이벤트 관리 (router_events.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/cep/events` | 이벤트 목록 |
| `GET` | `/cep/events/summary` | 이벤트 요약 (severity별) |
| `GET` | `/cep/events/{event_id}` | 이벤트 상세 |
| `DELETE` | `/cep/events/{event_id}` | 이벤트 삭제 |

### 7.3 시뮬레이션 (router_simulation.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/cep/rules/{rule_id}/simulate` | 규칙 시뮬레이션 |
| `POST` | `/cep/rules/{rule_id}/dry-run` | 드라이 런 (액션 미실행) |
| `POST` | `/cep/rules/{rule_id}/trigger` | 수동 트리거 |

### 7.4 모니터링 (router_monitoring.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/cep/stats/summary` | 전체 통계 |
| `GET` | `/cep/rules/performance` | 규칙 성능 (top N, 정렬) |
| `GET` | `/cep/rules/{rule_id}/metrics` | 규칙별 메트릭 |

### 7.5 이상 탐지 (router_anomaly.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/cep/rules/{rule_id}/anomaly-status` | 베이스라인 상태 |
| `POST` | `/cep/rules/{rule_id}/anomaly-reset` | 베이스라인 리셋 |

### 7.6 알림 채널 (router_channels.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/cep/channels` | 채널 생성 |
| `GET` | `/cep/channels/types` | 채널 타입 목록 |
| `POST` | `/cep/channels/test` | 채널 테스트 |
| `PATCH` | `/cep/channels/{channel_id}` | 채널 수정 |

### 7.7 폼 & 템플릿 (router_forms.py, router_templates.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/cep/form` | 폼 데이터 → JSON 변환 |
| `GET` | `/cep/templates` | 템플릿 목록 |

### 7.8 헬스 체크 (router_health.py)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/cep/health` | 엔진 상태 |
| `GET` | `/cep/health/redis` | Redis 연결 상태 |
| `GET` | `/cep/health/bytewax` | Bytewax 실행기 상태 |

---

## 8. 예외 처리 & 복구 패턴

### 8.0 Exception Hierarchy

```python
CEPException (base)
├── CEPValidationError (400)
│   ├── InvalidTriggerSpec
│   ├── InvalidActionSpec
│   └── DuplicateRuleName
├── CEPExecutionError (500)
│   ├── FilterProcessorError
│   ├── AggregationError
│   └── AnomalyDetectionError
├── CEPTimeoutError (504)
│   └── ProcessingTimeout
├── CEPChannelError (503)
│   ├── SlackChannelError
│   ├── EmailChannelError
│   └── WebhookChannelError
├── CEPStateError (500)
│   ├── RedisConnectionError
│   └── StateInconsistencyError
└── CEPResourceError (503)
    ├── MemoryExhausted
    └── ProcessorQueueOverflow
```

### 8.1 Circuit Breaker States

**Closed (정상):**
```
Success count: 0/2 ─────────────────────────────────────────
Failure count: 0/5
Request handling: ALLOWED
```

**Open (차단):**
```
Success count: 0/2 ─────────────────────────────────────────
Failure count: 5/5 ◄─── Threshold exceeded
Request handling: REJECTED (401 error returned)
Timeout: 60 seconds ─────────────────────────────────────────
```

**Half-Open (회복 시도):**
```
Success count: 1/2 ◄─── Probing one request
Failure count: 0/5
Request handling: LIMITED (single request allowed)
```

### 8.2 Per-Rule Circuit Breaker

각 규칙마다 독립적인 circuit breaker:
- Rule A 실패 → Rule A만 차단, Rule B는 정상
- 리소스 격리 (noisy neighbor 방지)
- 모니터링: `GET /cep/health` → per-rule 상태

---

## 9. 성능 특성

### 7.1 처리 성능

| 작업 | 시간 | 비고 |
|------|------|------|
| 규칙 등록 | ~5ms | 메모리 기반 |
| 단순 조건 평가 | ~1ms | FilterProcessor |
| 복합 조건 (5개) | ~2ms | AND/OR/NOT |
| 집계 (1000 이벤트) | ~10ms | AggregationProcessor |
| 윈도우 처리 | ~3ms | WindowProcessor |
| **처리량** | **10,000+ events/sec** | 단일 워커 |

### 7.2 알림 성능

| 작업 | 시간 |
|------|------|
| 메시지 렌더링 (Jinja2) | ~5ms |
| Slack 전송 | ~200ms |
| Email 전송 | ~500ms |
| Redis 저장 | ~5ms |

### 7.3 메모리 사용

- 규칙당: ~2KB (메타데이터)
- 프로세서 상태: 10-100KB/규칙
- 전체: 1000개 규칙 시 ~50MB

---

## 10. 모니터링 & 관측성

### 10.1 Observability Dashboard

**경로:** `/admin/cep-monitoring` (Screen Asset)

**표시 항목:**
- **KPI Row**:
  - Active Rules: 활성 규칙 수
  - Execution Count: 총 실행 횟수 (오늘)
  - Avg Latency: 평균 지연시간 (ms)
  - Alert Count: 발송된 알림 수

- **Rules Table** (`/cep/rules`):
  - Rule Name, Trigger Type, Status
  - Last Execution, Execution Count
  - Conditional Styling: active=green, inactive=gray

- **Performance Table** (`/cep/rules/performance`):
  - Rule Name, Avg Latency, Max Latency
  - Success Rate, Recent Errors
  - Sorting: latency, success_rate

- **Events Table** (`/cep/events?limit=100`):
  - Event ID, Severity, Rule Name
  - Timestamp, Message
  - Conditional Styling: severity별 색상
  - Auto-refresh: 15초

### 10.2 Health Check Endpoints

**단순 체크:**
```
GET /cep/health
→ 200 {status: "healthy", timestamp: "2026-02-15T..."}
```

**상세 체크:**
```
GET /cep/health
→ 200 {
  status: "healthy",
  components: {
    redis: {status: "up", latency_ms: 5},
    bytewax: {status: "up", rules_loaded: 24},
    processor_queue: {size: 10, max: 1000}
  }
}
```

**Circuit Breaker 상태:**
```
GET /cep/health/circuit-breakers
→ 200 {
  global: {state: "closed", failures: 0},
  rules: {
    "rule-001": {state: "half-open", failures: 3},
    "rule-002": {state: "closed", failures: 0}
  }
}
```

---

## 11. 프론트엔드 컴포넌트

### 8.1 Notification Channel Builder

7개 React 컴포넌트 (1,115줄):
- `NotificationChannelBuilder.tsx` - 메인 빌더
- `SlackChannelForm.tsx` - Slack 설정
- `EmailChannelForm.tsx` - Email 설정
- `SmsChannelForm.tsx` - SMS 설정
- `WebhookChannelForm.tsx` - Webhook 설정
- `PagerDutyChannelForm.tsx` - PagerDuty 설정

### 8.2 Database Catalogs (`/admin/catalogs`)

Schema 스캔 및 뷰어 (100% 완료):
- `CatalogScanPanel` - Postgres/Neo4j 자동 스캔, 실시간 상태 표시
- `CatalogViewerPanel` - 테이블 구조 시각화, 컬럼 타입/제약조건 표시
- `CreateCatalogModal` - 새 Catalog 생성
- `CatalogTable` - 목록 표시 (status, version, created_at)
- **데모 모드**: API 미연결 시 데모 데이터 자동 표시

### 8.3 Data Explorer (`/admin/explorer`)

다중 데이터 소스 탐색기 (95% 완료):
- **Postgres**: 테이블 브라우징, SQL 쿼리, AG Grid 결과
- **Neo4j**: 라벨 브라우징, Cypher 쿼리, `Neo4jGraphFlow` 그래프 시각화
- **Redis**: Key 스캔 (prefix, pattern), cursor 기반 페이징, Command 실행
- **Inspector 패널**: 선택된 행/노드 상세 정보
- **보안**: `NEXT_PUBLIC_ENABLE_DATA_EXPLORER` 환경변수, Read-only 제한, 최대 200행

### 8.4 CEP Monitoring Screen (Screen Asset)

`cep-monitoring.screen.json` - Direct API Endpoint 방식:
- KPI Row: 규칙 수, 실행 횟수, 성능, 알림
- CEP Rules Table: `/cep/rules` 호출
- CEP Events Table: `/cep/events?limit=100` 호출 (15초 자동 갱신)
- Conditional Styles: severity별 색상 표시

---

## 12. 파일 맵

### 12.1 Backend (11 모듈 구조)

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| **Router Modules (1,100 lines total)** | | |
| `cep_builder/router_rules.py` | 150 | Rule CRUD |
| `cep_builder/router_events.py` | 100 | Event management |
| `cep_builder/router_simulation.py` | 200 | Simulation & triggers |
| `cep_builder/router_monitoring.py` | 150 | Performance monitoring |
| `cep_builder/router_channels.py` | 120 | Channel management |
| `cep_builder/router_anomaly.py` | 100 | Anomaly endpoints |
| `cep_builder/router_bytewax.py` | 100 | Bytewax integration |
| `cep_builder/router_forms.py` | 80 | Form conversion |
| `cep_builder/router_templates.py` | 70 | Template mgmt |
| `cep_builder/router_execute.py` | 90 | Direct execution |
| `cep_builder/router_health.py` | 100 | Health checks |
| **Core Modules** | | |
| `cep_builder/bytewax_executor.py` | 420 | Bytewax 통합 실행기 |
| `cep_builder/bytewax_engine.py` | 410 | Bytewax CEP 엔진 코어 |
| `cep_builder/executor.py` | 840 | 기존 CEP 실행기 (+ anomaly 평가) |
| `cep_builder/anomaly_detector.py` | 190 | ML 이상 탐지 (Z-Score, IQR, EMA) |
| **Notification & State** | | |
| `cep_builder/notification_channels.py` | 800 | 5채널 알림 |
| `cep_builder/notification_retry.py` | 360 | 재시도 + Circuit Breaker |
| `cep_builder/notification_templates.py` | 440 | 템플릿 시스템 |
| `cep_builder/redis_state_manager.py` | 500 | Redis 상태 관리 (+ 베이스라인) |
| `cep_builder/form_converter.py` | 250 | 폼-JSON 변환 |

### 12.2 Frontend

| 파일 | 역할 |
|------|------|
| `components/notification-manager/` | 알림 채널 빌더 (7개 컴포넌트) |
| `lib/ui-screen/screens/cep-monitoring.screen.json` | CEP 모니터링 스크린 (Direct API) |

### 12.3 테스트

| 파일 | 역할 |
|------|------|
| `tests/test_bytewax_executor.py` | Bytewax 통합 테스트 (30+) |
| `tests/test_circuit_breaker.py` | Circuit Breaker 테스트 |

---

## 13. 현재 운영 범위

| 항목 | 상태 | 내용 |
|------|------|------|
| Notification 시스템 | 완료 | 5채널, 재시도, 템플릿 |
| CEP 엔진 코어 | 완료 | 복합 조건, 집계 함수 |
| Bytewax 통합 | 운영 중 | 하이브리드 실행 구조 |
| Redis 분산 상태 | 완료 | 상태 저장/폴백 지원 |
| ML 이상 탐지 | 완료 | Z-Score, IQR, EMA, anomaly trigger |

## 14. 배포 구성

### Docker Compose (기본)

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --appendonly yes
  cep-api:
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on: [redis]
```

### 고가용성 (Redis Cluster)

Redis Master + 2 Slave + Sentinel 구성 지원.
자동 페일오버, 읽기 분산.

---

## 15. 코드 통계

| 영역 | 줄 수 |
|------|-------|
| Backend (Python) | ~6,800 |
| Frontend (React) | ~1,115 |
| 테스트 | ~400 |
| **총합** | **~8,300** |

최종 업데이트: 2026-02-15

---

## 16. 개선/고도화 제안

| 항목 | 우선순위 | 내용 |
|------|----------|------|
| Bytewax 직접 평가 전환 | 중 | 기존 executor 의존 경로를 축소하고 평가 경로 단일화 |
| Circuit Breaker 분산화 | 중 | Kafka/Redis pub-sub 기반 multi-node 동기화 |
| Observability 강화 | 낮 | OpenTelemetry 통합, distributed tracing (Jaeger/Zipkin) |
