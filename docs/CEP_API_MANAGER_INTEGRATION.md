# CEP 엔진과 API Manager 통합 가이드

## 개요

이 문서는 CEP (Complex Event Processing) 엔진에서 API Manager를 통합하여 규칙 실행 시 다양한 액션을 수행하는 방법을 설명합니다.

**최종 업데이트**: 2026-02-06

## 주요 기능

### 지원되는 액션 타입 (Action Types)

CEP 규칙의 `action_spec`에서 다음 3가지 액션 타입을 지원합니다:

#### 1. webhook (기존)
HTTP 웹훅을 호출합니다.

**스펙 구조:**
```json
{
  "type": "webhook",
  "endpoint": "https://webhook.example.com/alert",
  "method": "POST",
  "params": {
    "severity": "high",
    "timestamp": "2026-02-06T10:30:00Z"
  },
  "body": {
    "alert_id": "alert-123",
    "message": "Critical CPU usage"
  }
}
```

**특징:**
- HTTP GET/POST 지원
- URL 파라미터 및 JSON 바디 지원
- 외부 시스템 통지에 최적

---

#### 2. api_script (신규)
API Manager의 Python 스크립트 타입 API를 실행합니다.

**스펙 구조:**
```json
{
  "type": "api_script",
  "api_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "params": {
    "user_id": "user-123",
    "alert_level": "critical",
    "event_type": "cpu_spike"
  },
  "input": {
    "cpu_value": 95.5,
    "memory_usage": 82.3,
    "process_name": "database"
  }
}
```

**필수 필드:**
- `api_id`: 실행할 API의 UUID

**선택 필드:**
- `params`: API에 전달할 파라미터 (딕셔너리)
- `input`: 스크립트의 입력 데이터

**반환값:**
```json
{
  "output": {
    "notification_sent": true,
    "escalation_level": "L2",
    "assigned_to": "ops-team@example.com"
  },
  "logs": [
    "[INFO] Processing alert for user-123",
    "[INFO] Escalation triggered"
  ],
  "references": {
    "execution_time": 245,
    "api_version": 1
  }
}
```

**사용 시나리오:**
- 복잡한 비즈니스 로직 실행
- 데이터 검증 및 변환
- 외부 시스템 통합 (데이터베이스, API 호출 등)
- 스크립트로 작성된 규칙 로직

---

#### 3. trigger_rule (신규)
다른 CEP 규칙을 동적으로 트리거합니다.

**스펙 구조:**
```json
{
  "type": "trigger_rule",
  "rule_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  "payload": {
    "event_type": "cascading_alert",
    "parent_rule": "parent-rule-id",
    "severity": "critical",
    "context": {
      "source_service": "api-gateway",
      "error_code": "500"
    }
  }
}
```

**필수 필드:**
- `rule_id`: 트리거할 대상 규칙의 UUID

**선택 필드:**
- `payload`: 대상 규칙에 전달할 이벤트 페이로드

**반환값:**
```json
{
  "trigger_result": {
    "status": "success",
    "condition_met": true,
    "duration_ms": 342,
    "references": {
      "trigger": {...},
      "action": {...}
    }
  }
}
```

**사용 시나리오:**
- 규칙 연쇄 실행 (Rule Chaining)
- 계단식 알림 (Cascading Alerts)
- 복합 이벤트 처리
- 우선순위 기반 처리

---

## 구현 상세

### executor.py의 주요 함수

#### `execute_action(action_spec, session=None)`

모든 액션 타입을 처리하는 메인 함수입니다.

```python
def execute_action(
    action_spec: Dict[str, Any],
    session: Session | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    액션 타입에 따라 적절한 핸들러를 호출합니다.

    반환값:
    - (result_payload, references): 실행 결과와 메타데이터
    """
```

**액션 타입별 라우팅:**
- `webhook` → `_execute_webhook_action()`
- `api_script` → `_execute_api_script_action()`
- `trigger_rule` → `_execute_trigger_rule_action()`

#### `_execute_webhook_action(action_spec)`

기존 웹훅 실행 로직 (하위 호환성 유지)

#### `_execute_api_script_action(action_spec, session)`

API Manager 스크립트 실행:
1. API 정의를 데이터베이스에서 조회
2. 스크립트 타입 API 검증
3. `execute_script_api()` 호출
4. 결과 및 로그 반환

#### `_execute_trigger_rule_action(action_spec, session)`

대상 규칙 트리거:
1. 대상 규칙을 데이터베이스에서 조회
2. 규칙 활성화 상태 확인
3. `manual_trigger()` 재귀 호출
4. 트리거 결과 반환

### manual_trigger() 함수의 업데이트

```python
def manual_trigger(
    rule: TbCepRule,
    payload: Dict[str, Any] | None = None,
    executed_by: str = "cep-builder",
    session: Session | None = None,
) -> Dict[str, Any]:
```

**변경사항:**
- `session` 파라미터 추가 (옵션)
- 세션이 없으면 자동 생성
- `execute_action()`에 세션 전달

---

## 사용 예제

### 예제 1: 웹훅 액션 (기존)

```json
{
  "rule_id": "alert-cpu-spike",
  "rule_name": "High CPU Alert",
  "trigger_type": "event",
  "trigger_spec": {
    "field": "cpu_percent",
    "op": ">",
    "value": 85
  },
  "action_spec": {
    "type": "webhook",
    "endpoint": "https://alerts.example.com/webhook",
    "method": "POST",
    "params": {"channel": "alerts"}
  }
}
```

### 예제 2: API 스크립트 액션 (신규)

```json
{
  "rule_id": "auto-remediate-disk-space",
  "rule_name": "Auto Disk Space Cleanup",
  "trigger_type": "event",
  "trigger_spec": {
    "field": "disk_usage_percent",
    "op": ">",
    "value": 90
  },
  "action_spec": {
    "type": "api_script",
    "api_id": "cleanup-old-logs-api",
    "params": {
      "retention_days": 30,
      "force": false
    }
  }
}
```

### 예제 3: 규칙 트리거 액션 (신규)

```json
{
  "rule_id": "primary-alert",
  "rule_name": "Primary Service Down Alert",
  "trigger_type": "event",
  "trigger_spec": {
    "conditions": [
      {"field": "service_status", "op": "==", "value": "down"},
      {"field": "retry_count", "op": ">=", "value": 3}
    ],
    "logic": "AND"
  },
  "action_spec": {
    "type": "trigger_rule",
    "rule_id": "escalation-alert",
    "payload": {
      "severity": "critical",
      "escalation_reason": "service_down_with_retries",
      "timestamp": "2026-02-06T10:30:00Z"
    }
  }
}
```

### 예제 4: 규칙 연쇄 실행

**Parent Rule:**
```json
{
  "rule_id": "parent-rule",
  "action_spec": {
    "type": "trigger_rule",
    "rule_id": "child-rule-1",
    "payload": {"cascade_level": 1}
  }
}
```

**Child Rule 1:**
```json
{
  "rule_id": "child-rule-1",
  "action_spec": {
    "type": "trigger_rule",
    "rule_id": "child-rule-2",
    "payload": {"cascade_level": 2}
  }
}
```

**Child Rule 2:**
```json
{
  "rule_id": "child-rule-2",
  "action_spec": {
    "type": "api_script",
    "api_id": "final-notification-api",
    "params": {"priority": "high"}
  }
}
```

---

## API Manager 스크립트 API 작성 가이드

CEP에서 호출할 스크립트 API를 작성할 때 다음을 고려하세요:

### 스크립트 입력 구조

```python
# input_payload에는 다음이 포함됩니다:
input_payload = {
    "event_data": {...},      # CEP 이벤트 페이로드
    "user_id": "...",         # 규칙 생성자
    # 기타 컨텍스트
}

# params에는 다음이 포함됩니다:
params = {
    "user_id": "user-123",    # action_spec의 params에서 전달
    "alert_level": "critical"
}
```

### 스크립트 반환값

```python
# 반드시 다음 구조로 반환해야 합니다:
output = {
    "status": "success",      # 또는 "error"
    "result": {...},          # 실행 결과
    "message": "...",         # 설명 메시지
}
```

### 예제 스크립트 API

```python
# API 로직:
# 입력: event_data, user_id, alert_level
# 출력: escalation_ticket

def main(params, input_payload):
    event_data = input_payload.get("event_data", {})
    user_id = params.get("user_id")
    alert_level = params.get("alert_level", "info")

    # 비즈니스 로직 실행
    ticket_id = create_escalation_ticket(
        user_id=user_id,
        severity=alert_level,
        event_summary=event_data.get("message")
    )

    return {
        "status": "success",
        "result": {
            "ticket_id": ticket_id,
            "assigned_to": "ops-team",
            "estimated_resolution_time": "2 hours"
        }
    }
```

---

## 에러 처리

### API 스크립트 액션 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `api_id is required` | api_id 미지정 | action_spec에 api_id 추가 |
| `API definition not found` | 존재하지 않는 API | api_id 확인 |
| `API is not a script type` | 스크립트 타입이 아님 | SQL/HTTP 타입 API는 사용 불가 |
| `Script execution timed out` | 스크립트 실행 시간 초과 | 타임아웃 값 증가 또는 스크립트 최적화 |

### 규칙 트리거 액션 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `rule_id is required` | rule_id 미지정 | action_spec에 rule_id 추가 |
| `Target rule not found` | 존재하지 않는 규칙 | rule_id 확인 |
| `Target rule is not active` | 비활성 규칙 | 대상 규칙 활성화 |
| `rule already running` | 규칙이 이미 실행 중 | 중복 트리거 방지 (SKIP) |

---

## 성능 고려사항

### 규칙 연쇄 실행

```
Parent Rule (100ms)
  ↓
Child Rule 1 (150ms)
  ↓
Child Rule 2 (200ms)
─────────────────────
Total: ~450ms
```

**권장사항:**
- 3단계 이상의 깊은 연쇄는 피하기
- 각 규칙의 처리 시간 모니터링
- 타임아웃 값 조정

### 스크립트 실행

- 기본 타임아웃: 5초
- `runtime_policy.script.timeout_ms`에서 조정 가능
- 장시간 작업은 비동기 처리 고려

---

## 모니터링 및 로깅

### 실행 로그 구조

```json
{
  "rule_id": "...",
  "status": "success",
  "duration_ms": 345,
  "references": {
    "trigger": {...},
    "action": {
      "action_type": "api_script",
      "api_id": "...",
      "api_name": "...",
      "duration_ms": 245,
      "references": {...},
      "logs_count": 3
    }
  }
}
```

### 조회 방법

```python
# CEP 실행 로그 조회
from app.modules.cep_builder.crud import get_exec_logs

logs = get_exec_logs(session, rule_id="...", limit=50)
for log in logs:
    print(f"Status: {log.status}, Duration: {log.duration_ms}ms")
```

---

## 테스트

### 단위 테스트

```python
from app.modules.cep_builder.executor import execute_action
from unittest.mock import MagicMock

# API 스크립트 액션 테스트
action_spec = {
    "type": "api_script",
    "api_id": "test-api",
    "params": {"key": "value"}
}

mock_session = MagicMock()
try:
    payload, refs = execute_action(action_spec, session=mock_session)
except Exception as e:
    print(f"Error: {e}")
```

### 통합 테스트

```python
# apps/api/tests/test_bytewax_executor.py 참고
pytest apps/api/tests/test_bytewax_executor.py::TestActionExecution -v
pytest apps/api/tests/test_bytewax_executor.py::TestManualTriggerWithActions -v
```

---

## FAQ

**Q: 규칙을 자기 자신으로 트리거할 수 있나요?**
A: 기술적으로는 가능하지만, 무한 루프 방지를 위해 깊이 제한을 권장합니다.

**Q: 웹훅과 API 스크립트를 함께 실행할 수 있나요?**
A: 현재는 하나의 action_spec만 지원하므로, 둘 다 실행하려면 스크립트 API 내에서 웹훅을 호출하세요.

**Q: 트리거된 규칙의 결과를 원래 규칙에서 사용할 수 있나요?**
A: 트리거 결과는 `references.trigger_result`에 포함되므로, 다음 단계에서 참고 가능합니다.

**Q: 세션 없이 manual_trigger()를 호출할 수 있나요?**
A: 네, 세션을 전달하지 않으면 자동으로 생성됩니다. 단, API 스크립트나 규칙 트리거 액션을 사용하면 실패합니다.

---

## 관련 파일

- **executor.py**: `/home/spa/tobit-spa-ai/apps/api/app/modules/cep_builder/executor.py`
- **테스트**: `/home/spa/tobit-spa-ai/apps/api/tests/test_bytewax_executor.py`
- **모델**: `/home/spa/tobit-spa-ai/apps/api/app/modules/cep_builder/models.py`
- **API Manager 스크립트**: `/home/spa/tobit-spa-ai/apps/api/app/modules/api_manager/script_executor.py`

---

## 변경 이력

| 날짜 | 버전 | 변경사항 |
|------|------|---------|
| 2026-02-06 | 1.0 | 초판 작성 - API Manager 통합 완료 |

---

**작성자**: Claude Code
**최종 검토**: 2026-02-06
