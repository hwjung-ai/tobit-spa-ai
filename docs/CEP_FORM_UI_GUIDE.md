# CEP 폼 기반 UI 빌더 가이드

## 📋 개요

CEP (Complex Event Processing) 엔진을 위한 **완전한 폼 기반 UI 빌더**가 완성되었습니다. 기존 JSON 직접 편집 방식에서 **직관적인 폼 인터페이스**로 규칙을 만들 수 있습니다.

**URL**: `/cep-builder-v2`

---

## 🎨 컴포넌트 구조

### 1. **BasicInfoSection** - 기본 정보
규칙의 기본 메타데이터 입력:
- `ruleName` (필수): 규칙 이름
- `description` (선택): 규칙 설명
- `isActive`: 규칙 활성화 여부

```typescript
<BasicInfoSection
  ruleName={formData.ruleName}
  description={formData.description}
  isActive={formData.isActive}
  onRuleNameChange={(name) => setFormData({...formData, ruleName: name})}
  onDescriptionChange={(desc) => setFormData({...formData, description: desc})}
  onActiveChange={(active) => setFormData({...formData, isActive: active})}
/>
```

### 2. **TriggerSection** - 트리거 설정 (필수)
규칙이 발동되는 조건:

#### 메트릭 트리거 (📊)
메트릭 임계값 기반:
- `metricName`: 모니터링할 메트릭 (예: `cpu_usage`)
- `operator`: 비교 연산자 (`>`, `<`, `>=`, `<=`, `==`, `!=`)
- `threshold`: 임계값 (예: `80`)
- `aggregation`: 집계 방식 (`avg`, `max`, `min`, `sum`, `count`)
- `duration`: 시간 윈도우 (`1m`, `5m`, `10m`, `30m`, `1h`)

#### 이벤트 트리거 (📢)
특정 이벤트 타입 감지:
- `eventType`: 이벤트 타입 (예: `error`, `warning`, `alert`)

#### 스케줄 트리거 (⏰)
정기적인 실행:
- `scheduleExpression`: Cron 표현식 (예: `0 9 * * *` = 매일 9시)

```typescript
<TriggerSection
  triggerType={formData.triggerType}
  triggerSpec={formData.triggerSpec}
  onTriggerTypeChange={(type) => setFormData({...formData, triggerType: type})}
  onTriggerSpecChange={(spec) => setFormData({...formData, triggerSpec: spec})}
/>
```

### 3. **ConditionsSection** - 복합 조건 (선택사항)
AND/OR/NOT 로직으로 복합 조건 정의:

```typescript
<ConditionsSection
  conditions={formData.conditions}
  logic={formData.conditionLogic}
  onConditionsChange={(conds) => setFormData({...formData, conditions: conds})}
  onLogicChange={(logic) => setFormData({...formData, conditionLogic: logic})}
/>
```

**조건 구조**:
```typescript
interface Condition {
  id: string;           // 고유 ID
  field: string;        // 필드명 (예: "cpu_usage", "status")
  op: string;           // 연산자: >, <, >=, <=, ==, !=, in, contains
  value: string;        // 비교값 (예: "80", "error")
}
```

**예제 - AND 로직**:
```
[조건1] cpu_usage > 80  AND  [조건2] status == "error"
```

**예제 - OR 로직**:
```
[조건1] memory > 70  OR  [조건2] disk > 85
```

### 4. **WindowingSection** - 윈도우 설정 (선택사항)
데이터를 시간 단위로 분할:

#### Tumbling Window
고정 크기의 겹치지 않는 윈도우:
```
[----5m----] [----5m----] [----5m----]
```

#### Sliding Window
겹치는 윈도우 (Slide 간격만큼 이동):
```
[----5m----]
    [----5m----]
        [----5m----]
```
- `size`: 윈도우 크기 (예: `5m`)
- `slide`: 이동 간격 (예: `1m`)

#### Session Window
사용자 세션 기반:
- `size`: 윈도우 크기
- `timeout`: 세션 만료 시간 (예: `10m`)

```typescript
<WindowingSection
  windowConfig={formData.windowConfig}
  onWindowConfigChange={(config) => setFormData({...formData, windowConfig: config})}
/>
```

### 5. **AggregationSection** - 집계 (선택사항)
데이터 집계 함수 정의:

```typescript
<AggregationSection
  aggregations={formData.aggregations}
  groupByFields={formData.groupByFields}
  onAggregationsChange={(aggs) => setFormData({...formData, aggregations: aggs})}
  onGroupByChange={(fields) => setFormData({...formData, groupByFields: fields})}
/>
```

**집계 함수**:
- `avg`: 평균
- `sum`: 합계
- `min`: 최소값
- `max`: 최대값
- `count`: 개수
- `stddev`: 표준편차

**구조**:
```typescript
interface Aggregation {
  type: "avg" | "sum" | "min" | "max" | "count" | "stddev";
  field?: string;          // 집계할 필드 (count 제외)
  outputAlias?: string;    // 출력 필드명 (예: "avg_cpu")
}
```

**예제**:
- 필드: `cpu_usage`, 함수: `avg`, 출력명: `avg_cpu`
- 그룹화: `region, service_name`

### 6. **EnrichmentSection** - 데이터 보강 (선택사항)
외부 데이터로 이벤트 확장:

#### Lookup 보강
외부 데이터 소스에서 조회:
```
이벤트의 user_id → Redis 조회 → user_name 추가
```

#### Aggregate 보강
과거 집계 데이터 추가:
```
현재 이벤트 + 지난 1시간 통계 추가
```

#### ML Model 보강
머신러닝 모델 적용:
```
이벤트 데이터 → 이상탐지 모델 → anomaly_score 추가
```

```typescript
<EnrichmentSection
  enrichments={formData.enrichments}
  onEnrichmentsChange={(enr) => setFormData({...formData, enrichments: enr})}
/>
```

### 7. **ActionsSection** - 액션 (필수)
조건 일치 시 실행할 작업:

#### Webhook 액션
외부 API 호출:
```typescript
{
  type: "webhook",
  endpoint: "https://api.example.com/alerts",
  method: "POST"  // GET, POST, PUT, DELETE
}
```

#### Notify 액션
채널별 알림:
```typescript
{
  type: "notify",
  message: "CPU 사용량이 80% 초과했습니다",
  channels: ["Slack", "Email", "SMS"]  // 선택: Slack, Email, SMS, Discord
}
```

#### Trigger 액션
다른 규칙 실행:
```typescript
{
  type: "trigger"
  // 다른 규칙 ID 지정
}
```

#### Store 액션
데이터 저장:
```typescript
{
  type: "store"
  // 저장소 지정
}
```

```typescript
<ActionsSection
  actions={formData.actions}
  onActionsChange={(acts) => setFormData({...formData, actions: acts})}
/>
```

### 8. **SimulationPanel** - 시뮬레이션
규칙 저장 전에 테스트:

```typescript
<SimulationPanel
  isLoading={isLoading}
  onSimulate={async (testPayload) => {
    const response = await fetch("/api/cep/rules/preview", {
      method: "POST",
      body: JSON.stringify({...})
    });
    return response.json();
  }}
/>
```

**입력**: JSON 테스트 데이터
**출력**:
- 조건 일치 여부
- 조건별 평가 결과
- 실행될 액션 목록
- 상세 설명

### 9. **JsonPreview** - JSON 미리보기
생성되는 JSON 구조 확인:

```typescript
<JsonPreview
  data={buildJsonPreview()}
  title="JSON 미리보기"
  copyable={true}
/>
```

클립보드로 복사 가능합니다.

### 10. **FormFieldGroup** - 폼 필드 래퍼
일관된 폼 필드 스타일:

```typescript
<FormFieldGroup
  label="필드명"
  required={true}
  error={validationError}
  help="도움말 텍스트"
>
  <input type="text" />
</FormFieldGroup>
```

### 11. **CepRuleFormPage** - 메인 페이지
모든 섹션을 조정하는 메인 폼 페이지:

```typescript
<CepRuleFormPage
  onSave={async (data) => {
    const response = await fetch("/api/cep/rules", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }}
  onCancel={() => router.back()}
  initialData={existingRule}
  isLoading={isLoading}
/>
```

---

## 📊 전체 흐름

```
1. BasicInfoSection (규칙명, 설명)
      ↓
2. TriggerSection (메트릭/이벤트/스케줄 선택)
      ↓
3. ConditionsSection (AND/OR/NOT 복합 조건)
      ↓
4. WindowingSection (옵션: 윈도우 설정)
      ↓
5. AggregationSection (옵션: 집계 함수)
      ↓
6. EnrichmentSection (옵션: 데이터 보강)
      ↓
7. ActionsSection (Webhook/Notify/Trigger/Store)
      ↓
8. SimulationPanel (규칙 테스트)
      ↓
9. JSON 미리보기
      ↓
10. 저장 / 취소
```

---

## 🔄 데이터 흐름

### 폼 → JSON 변환

```typescript
// 폼 데이터
{
  ruleName: "CPU 고가용 모니터링",
  description: "CPU가 80% 이상일 때 알림",
  isActive: true,
  triggerType: "metric",
  triggerSpec: {
    metricName: "cpu_usage",
    operator: ">",
    threshold: "80",
    aggregation: "avg",
    duration: "5m"
  },
  conditions: [
    { field: "memory", op: ">", value: "70" }
  ],
  conditionLogic: "AND",
  actions: [
    {
      type: "webhook",
      endpoint: "https://api.example.com/alerts",
      method: "POST"
    }
  ]
}

// ↓ 변환 ↓

// 백엔드로 전송되는 JSON
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
      { "field": "memory", "op": ">", "value": "70" }
    ],
    "logic": "AND"
  },
  "actions": [
    {
      "type": "webhook",
      "endpoint": "https://api.example.com/alerts",
      "method": "POST"
    }
  ]
}
```

### 백엔드 API

**POST `/api/cep/rules`** - 규칙 저장
```json
{
  "rule_name": "...",
  "trigger_type": "metric",
  "trigger_spec": {...},
  "composite_condition": {...},
  "actions": [...]
}
```

**POST `/api/cep/rules/preview`** - 규칙 시뮬레이션
```json
{
  "trigger_spec": {...},
  "conditions": [...],
  "condition_logic": "AND",
  "test_payload": {"cpu_usage": 85}
}
```

---

## 💡 사용 예제

### 예제 1: CPU 모니터링 규칙

**목표**: CPU 사용량이 5분간 평균 80% 이상일 때 Slack 알림 + Webhook 호출

```
기본 정보
├─ 규칙명: CPU 고가용 모니터링
└─ 설명: 5분간 평균 CPU 80% 이상 모니터링

트리거
├─ 타입: 메트릭
├─ 메트릭명: cpu_usage
├─ 연산자: >
├─ 임계값: 80
├─ 집계: avg
└─ 시간 윈도우: 5m

조건 (AND)
├─ 조건1: status == "running"
└─ 조건2: environment == "production"

액션
├─ Webhook: POST https://api.example.com/alerts
└─ Notify: Slack 채널에 "CPU 사용량 경고" 메시지
```

### 예제 2: 복합 조건 규칙

**목표**: 메모리와 디스크 중 하나라도 높을 때 알림 (OR 로직)

```
트리거: 메트릭 (memory_percent)

조건 (OR)
├─ 조건1: memory_percent > 80
└─ 조건2: disk_usage > 85

액션: Email 알림
```

### 예제 3: 이벤트 기반 규칙

**목표**: 에러 이벤트 발생 시 자동으로 사건 기록

```
트리거: 이벤트 (error)

조건 (AND)
├─ 조건1: severity == "critical"
└─ 조건2: service == "api-gateway"

집계: 10분 내 error_count > 5

액션
├─ Store: 사건 DB에 저장
└─ Webhook: PagerDuty API 호출
```

---

## 🧪 시뮬레이션 예제

### 입력 (테스트 데이터)
```json
{
  "cpu_usage": 85,
  "memory_percent": 72,
  "status": "running",
  "environment": "production"
}
```

### 출력 (시뮬레이션 결과)
```
✅ 조건 일치됨

조건 결과:
✓ status == "running" → 일치
✓ environment == "production" → 일치

실행될 액션:
📤 Webhook: POST https://api.example.com/alerts
📤 Notify: Slack - "CPU 사용량이 80% 초과했습니다"
```

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| **폼 기반 UI** | JSON 대신 직관적인 폼 인터페이스 |
| **복합 조건** | AND/OR/NOT 로직으로 복잡한 조건 정의 |
| **다중 트리거** | 메트릭, 이벤트, 스케줄 지원 |
| **윈도우** | Tumbling, Sliding, Session 윈도우 |
| **집계** | avg, sum, min, max, count, stddev |
| **데이터 보강** | 외부 데이터, 집계, ML 모델 지원 |
| **다중 액션** | Webhook, 알림, 규칙 트리거, 데이터 저장 |
| **시뮬레이션** | 저장 전 규칙 테스트 |
| **JSON 미리보기** | 생성되는 JSON 구조 확인 및 복사 |
| **클라이언트 검증** | 필수 필드 검증 및 사용자 피드백 |

---

## 🚀 시작하기

### 새 규칙 만들기
```
1. `/cep-builder-v2` 페이지 접속
2. 기본 정보 입력 (규칙명, 설명)
3. 트리거 타입 선택 (메트릭/이벤트/스케줄)
4. 트리거 설정 (메트릭명, 임계값, 시간 윈도우 등)
5. 옵션: 복합 조건 추가 (AND/OR/NOT)
6. 옵션: 윈도우, 집계, 데이터 보강 설정
7. 액션 추가 (최소 1개)
8. 테스트 데이터로 시뮬레이션 실행
9. JSON 미리보기 확인
10. "규칙 저장" 버튼 클릭
```

### 기존 규칙 편집
```
1. 규칙 목록에서 기존 규칙 선택
2. `/cep-builder-v2?id={ruleId}` 페이지 접속
3. initialData에 기존 데이터 로드
4. 필요한 부분 수정
5. 시뮬레이션으로 검증
6. 저장
```

---

## 📝 기술 스택

- **프론트엔드**: React 18 + TypeScript
- **스타일링**: Tailwind CSS
- **상태 관리**: React useState
- **폼 처리**: 수동 관리 (react-hook-form 통합 가능)
- **검증**: 클라이언트 사이드 검증

---

## 🔗 관련 파일

### 컴포넌트
- `apps/web/src/components/cep-builder-v2/BasicInfoSection.tsx`
- `apps/web/src/components/cep-builder-v2/TriggerSection.tsx`
- `apps/web/src/components/cep-builder-v2/ConditionsSection.tsx`
- `apps/web/src/components/cep-builder-v2/WindowingSection.tsx`
- `apps/web/src/components/cep-builder-v2/AggregationSection.tsx`
- `apps/web/src/components/cep-builder-v2/EnrichmentSection.tsx`
- `apps/web/src/components/cep-builder-v2/ActionsSection.tsx`
- `apps/web/src/components/cep-builder-v2/SimulationPanel.tsx`
- `apps/web/src/components/cep-builder-v2/FormFieldGroup.tsx`
- `apps/web/src/components/cep-builder-v2/JsonPreview.tsx`
- `apps/web/src/components/cep-builder-v2/CepRuleFormPage.tsx`

### 페이지
- `apps/web/src/app/cep-builder-v2/page.tsx`

### 백엔드 API
- `apps/api/app/modules/cep_builder/router.py`
- `apps/api/app/modules/cep_builder/schemas.py`
- `apps/api/app/modules/cep_builder/executor.py`

---

## 🎯 다음 단계

1. **form validation 강화**: react-hook-form + Zod 통합
2. **규칙 편집 기능**: GET `/api/cep/rules/{id}` 연동
3. **AI 드래프트 적용**: 생성된 JSON을 자동으로 폼에 채우기
4. **다국어 지원**: i18n 추가
5. **접근성 개선**: WCAG 2.1 준수
6. **테스트**: Playwright E2E 테스트 추가

---

## 📞 지원

질문이나 버그 리포트는 GitHub Issues를 통해 등록해주세요.
