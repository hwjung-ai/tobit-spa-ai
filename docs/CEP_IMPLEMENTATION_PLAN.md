# CEP 엔진 완전 개선 계획서: Bytewax 중심 + 폼 기반 UI

## 📋 프로젝트 개요

**목표**: 직접 구현한 CEP 엔진 → **Bytewax 엔진 중심 + 폼 기반 UI + 실시간 이벤트브라우저 연동**

**기대 효과**:
- JSON 편집 → 폼 기반 설정 (사용성 ↑)
- 단순 조건 → 복합 조건 (AND/OR/NOT)
- 메모리 기반 → Redis 기반 상태 관리 (안정성 ↑)
- 30초 폴링 → 실시간 이벤트 처리 (반응성 ↑)

---

## 🎯 전체 구현 로드맵 (4주)

```
Week 1 (Phase 1)  → Bytewax 엔진 강화 + 복합 조건 지원
Week 2 (Phase 2)  → 폼 기반 UI 빌더 구현
Week 3 (Phase 3)  → 이벤트브라우저 실시간 연동
Week 4 (Phase 4)  → AI 코파일럿 + 테스트 + 배포
```

---

## 🔧 Phase 1: Bytewax 엔진 강화 (1주)

### 1.1 복합 조건 지원 (Higher Priority)

**파일**: `apps/api/app/modules/cep_builder/executor.py`

**변경사항**:
```python
# 현재 (단일 조건)
trigger_spec = {
    "field": "cpu",
    "op": ">",
    "value": 80
}

# 개선 (복합 조건)
trigger_spec = {
    "conditions": [
        {"field": "cpu", "op": ">", "value": 80},
        {"field": "memory", "op": ">", "value": 70}
    ],
    "logic": "AND"  # OR, NOT
}
```

**구현**:
1. `_evaluate_composite_conditions()` 함수 추가
   - 조건 배열 순회
   - AND: 모두 True
   - OR: 하나라도 True
   - NOT: 모두 False
2. `evaluate_trigger()` 함수 개선
   - 기존 단일 조건 호환성 유지
   - 새로운 복합 조건 지원
3. 유효성 검사 추가

**테스트 케이스**:
- [ ] AND 조건: 모두 매치
- [ ] AND 조건: 하나 미스매치
- [ ] OR 조건: 하나 매치
- [ ] OR 조건: 모두 미스매치
- [ ] NOT 조건: 역논리
- [ ] 중첩 조건: (A AND B) OR C

**영향 범위**: 매우 낮음 (기존 코드 호환)

---

### 1.2 Bytewax 엔진 통합 (Lower Priority - Phase 2에서)

**파일**: `apps/api/app/modules/cep_builder/bytewax_engine.py`

**현황**: 현재 미사용 상태

**개선 방향**:
- Phase 1: 복합 조건만 executor에서 처리
- Phase 2: Window/Aggregation UI 구현 후 실제 사용

---

## 🎨 Phase 2: 폼 기반 UI 빌더 (1.5주)

### 2.1 새 컴포넌트 구조

**경로**: `apps/web/src/components/cep-builder-v2/`

```
CepBuilderV2/
├── CepRuleFormPage.tsx (새 페이지, 기존과 병행)
│   ├── BasicInfoSection.tsx ✨ NEW
│   │   ├─ ruleName (TextInput)
│   │   ├─ description (TextArea)
│   │   └─ isActive (Checkbox)
│   │
│   ├── TriggerSection.tsx ✨ NEW
│   │   ├─ TriggerTypeSelector.tsx (metric/event/schedule)
│   │   └─ TriggerSpecBuilder.tsx (동적 폼)
│   │       ├─ TriggerSpecForm_Metric.tsx
│   │       ├─ TriggerSpecForm_Event.tsx
│   │       └─ TriggerSpecForm_Schedule.tsx
│   │
│   ├── ConditionsSection.tsx ✨ NEW (복합 조건)
│   │   ├─ ConditionBuilder.tsx
│   │   │   ├─ ConditionCard.tsx (단일 조건)
│   │   │   ├─ LogicSelector.tsx (AND/OR/NOT)
│   │   │   └─ AddConditionButton.tsx
│   │   └─ ConditionPreview.tsx (JSON 미리보기)
│   │
│   ├── WindowingSection.tsx ✨ NEW (선택사항)
│   │   ├─ WindowTypeSelector.tsx (tumbling/sliding/session)
│   │   ├─ WindowSizeInput.tsx
│   │   └─ WindowPreview.tsx
│   │
│   ├── AggregationSection.tsx ✨ NEW (선택사항)
│   │   ├─ AggregationTypeSelector.tsx
│   │   ├─ FieldSelector.tsx
│   │   └─ GroupBySelector.tsx
│   │
│   ├── EnrichmentSection.tsx ✨ NEW (선택사항)
│   │   ├─ EnrichmentBuilder.tsx
│   │   └─ EnrichmentCard.tsx
│   │
│   ├── ActionSection.tsx ✨ NEW
│   │   ├─ ActionBuilder.tsx
│   │   └─ ActionCard.tsx (webhook, notify, etc)
│   │
│   ├── SimulationPanel.tsx ✨ NEW
│   │   ├─ TestPayloadEditor.tsx (JSON)
│   │   ├─ SimulateButton.tsx
│   │   └─ SimulationResult.tsx
│   │
│   └── shared/
│       ├─ FormFieldGroup.tsx (라벨+입력+에러)
│       ├─ FieldSelector.tsx (필드 자동완성)
│       ├─ OperatorSelector.tsx (연산자 드롭다운)
│       ├─ FormToJsonToggle.tsx (폼 ↔ JSON 전환)
│       └─ FormToJsonConverter.ts (변환 유틸)
```

### 2.2 상태 관리 구조

**기술**: `react-hook-form` + `Zod` (스키마 검증)

```typescript
// CepRuleFormData 스키마
const cepRuleSchema = z.object({
  ruleName: z.string().min(1, "필수 입력"),
  description: z.string().optional(),
  isActive: z.boolean().default(true),
  triggerType: z.enum(["metric", "event", "schedule"]),
  triggerSpec: z.record(z.unknown()),
  conditions: z.array(z.object({
    field: z.string(),
    op: z.enum([">", "<", ">=", "<=", "==", "!="]),
    value: z.unknown()
  })).optional(),
  conditionLogic: z.enum(["AND", "OR", "NOT"]).default("AND"),
  windowConfig: z.object({...}).optional(),
  aggregation: z.object({...}).optional(),
  enrichments: z.array(z.object({...})).default([]),
  actions: z.array(z.object({...})).min(1, "최소 1개 액션 필요")
});

type CepRuleFormData = z.infer<typeof cepRuleSchema>;
```

### 2.3 API 엔드포인트 추가

**새로 추가할 엔드포인트**:

```python
# apps/api/app/modules/cep_builder/router.py

# 1. 조건 검증
@router.post("/cep/validate/condition")
def validate_condition(condition: ConditionSpec, payload: dict) -> ValidationResult:
    """단일 조건 검증"""
    pass

# 2. 조건 템플릿
@router.get("/cep/condition-templates")
def get_condition_templates() -> List[ConditionTemplate]:
    """조건 템플릿 조회 (필드 제안)"""
    pass

# 3. 규칙 미리보기
@router.post("/cep/rules/preview")
def preview_rule(
    trigger_spec: dict,
    conditions: List[dict],
    test_payload: dict
) -> PreviewResult:
    """조건 평가만 수행"""
    pass

# 4. 드래프트 저장 (로컬 아님, 서버에 임시 저장)
@router.post("/cep/drafts")
def save_draft(draft: CepDraft) -> DraftSaved:
    """AI 생성 드래프트 임시 저장"""
    pass

# 5. 필드 제안
@router.get("/cep/field-suggestions")
def get_field_suggestions(search: str = "") -> List[FieldInfo]:
    """자동완성용 필드 제안"""
    pass
```

### 2.4 폼 컴포넌트 상세 (예시)

**ConditionsSection.tsx**:
```typescript
// 상태: react-hook-form의 FieldArray 사용
export function ConditionsSection() {
  const { control, watch, setValue } = useFormContext<CepRuleFormData>();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "conditions"
  });

  const conditionLogic = watch("conditionLogic");

  return (
    <FormFieldGroup label="조건 설정" help="여러 조건을 AND/OR로 조합">
      <div className="flex gap-2 mb-4">
        <select value={conditionLogic}
          onChange={(e) => setValue("conditionLogic", e.target.value as any)}>
          <option>AND</option>
          <option>OR</option>
          <option>NOT</option>
        </select>
        <button onClick={() => append({field: "", op: "==", value: ""})}>
          + 조건 추가
        </button>
        <button onClick={handleAiGenerate}>🤖 AI로 생성</button>
      </div>

      {fields.map((field, index) => (
        <ConditionCard key={field.id} index={index} onRemove={remove} />
      ))}
    </FormFieldGroup>
  );
}
```

**폼 UI 레이아웃** (Figma 같은 느낌):
```
┌────────────────────────────────────────────────────┐
│ CEP 규칙 빌더 (폼 기반)                            │
├────────────────────────────────────────────────────┤
│ 📌 기본 정보                                       │
│   규칙명: [________________]                     │
│   설명: [______________________]               │
│   활성화: [✓]                                    │
│                                                  │
│ 🎯 트리거 타입                                    │
│   [Metric ▼]  [Event]  [Schedule]               │
│   ┌──────────────────────────────────────────┐ │
│   │ 메트릭: [cpu_usage ▼]                    │ │
│   │ 연산자: [> ▼]                            │ │
│   │ 임계값: [80]                             │ │
│   │ 경로: [data.cpu]                        │ │
│   │ 지속시간: [5분 ▼]                       │ │
│   │ 집계: [avg ▼]                           │ │
│   └──────────────────────────────────────────┘ │
│                                                  │
│ 📝 복합 조건 (선택사항)                          │
│   Logic: [AND ▼]  [+ 추가]  [🤖 AI 생성]       │
│   ┌──────────────────────────────────────────┐ │
│   │ 필드: [status ▼]  Op: [== ▼]  값: [error] │ │
│   │ [삭제]                                     │ │
│   └──────────────────────────────────────────┘ │
│   ┌──────────────────────────────────────────┐ │
│   │ 필드: [count ▼]  Op: [>= ▼]  값: [5]     │ │
│   │ [삭제]                                     │ │
│   └──────────────────────────────────────────┘ │
│                                                  │
│ 📢 액션                                         │
│   [+ Webhook 추가]  [+ Slack 추가]             │
│   ┌──────────────────────────────────────────┐ │
│   │ Endpoint: [https://api.example.com/...]   │ │
│   │ Method: [POST ▼]                         │ │
│   │ [Header 편집]  [Body 편집]               │ │
│   │ [삭제]                                     │ │
│   └──────────────────────────────────────────┘ │
│                                                  │
│ 🧪 시뮬레이션                                    │
│   [테스트 데이터 입력] → [실행]                 │
│   ✅ 조건 매칭됨 → 액션 실행 예상               │
│                                                  │
│ [폼으로 보기] [JSON으로 보기]                   │
│ [저장] [적용] [시뮬레이션]                      │
└────────────────────────────────────────────────────┘
```

### 2.5 스키마 업데이트

**파일**: `apps/api/app/modules/cep_builder/schemas.py`

```python
# 새로운 스키마 추가 (기존과 별도 유지)
class ConditionSpec(BaseModel):
    field: str
    op: Literal["==", "!=", ">", ">=", "<", "<=", "in", "contains"]
    value: Any

class CompositeCondition(BaseModel):
    conditions: List[ConditionSpec]
    logic: Literal["AND", "OR", "NOT"] = "AND"

class CepRuleFormData(BaseModel):
    """폼 기반 규칙 데이터"""
    rule_name: str
    description: Optional[str] = None
    is_active: bool = True
    trigger_type: Literal["metric", "event", "schedule"]
    trigger_spec: Dict[str, Any]

    # 복합 조건 (선택사항)
    composite_condition: Optional[CompositeCondition] = None

    # 기타 설정
    window_config: Optional[Dict[str, Any]] = None
    aggregation: Optional[Dict[str, Any]] = None
    enrichments: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(min_items=1)

class ValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

---

## 📡 Phase 3: 이벤트브라우저 실시간 연동 (1주)

### 3.1 Redis Pub/Sub 통합

**파일**: `apps/api/app/modules/cep_builder/event_broadcaster.py`

**변경사항**:
```python
# 현재: asyncio.Queue만 사용
# 개선: Redis + asyncio.Queue 하이브리드

class CepEventBroadcaster:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis = None
        if redis_url:
            self.redis = redis.asyncio.from_url(redis_url)
        self.queues = []  # 로컬 subscribers (개발용)

    async def publish(self, event_type: str, data: dict):
        if self.redis:
            # Redis에 발행
            await self.redis.publish(f"cep:{event_type}", json.dumps(data))

        # 로컬 queues에도 발행 (호환성)
        for queue in self.queues:
            await queue.put({"type": event_type, "data": data})
```

### 3.2 API 개선

**파일**: `apps/api/app/modules/cep_builder/router.py`

```python
# 1. SSE 엔드포인트 개선
@router.get("/cep/events/stream")
async def event_stream(request: Request, session: Session):
    """
    SSE 스트림

    이벤트 타입:
    - "summary": 이벤트 요약 (unacked_count, by_severity)
    - "new_event": 새 이벤트 발생
    - "ack_event": 이벤트 ACK됨

    클라이언트가 최초 연결할 때 지난 1시간 이벤트 재전송
    """

    # 초기 로드백 데이터 (최근 1시간)
    LOOKBACK_MINUTES = 60
    recent = session.exec(
        select(TbCepNotificationLog)
        .where(TbCepNotificationLog.fired_at >=
               datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES))
        .order_by(TbCepNotificationLog.fired_at.desc())
        .limit(100)
    ).all()

    # 초기 스냅샷 전송
    summary = generate_event_summary(session)
    yield {"event": "summary", "data": json.dumps(summary)}

    # 최근 이벤트 전송
    for event in reversed(recent):
        yield {"event": "historical", "data": json.dumps(event_to_dict(event))}

    # 라이브 구독 시작
    queue = event_broadcaster.subscribe()
    try:
        while True:
            message = await asyncio.wait_for(queue.get(), timeout=1.0)
            yield {"event": message["type"], "data": json.dumps(message["data"])}
    finally:
        event_broadcaster.unsubscribe(queue)

# 2. 이벤트 그룹핑 API
@router.get("/cep/events/grouped")
def get_grouped_events(
    session: Session,
    group_by: str = "rule_id",  # rule_id, severity
    limit: int = 50
) -> List[EventGroup]:
    """
    유사 이벤트를 그룹핑해서 반환

    group_by="rule_id": 규칙별로 최근 N개 이벤트를 1개로 표시
    group_by="severity": 심각도별로 그룹화
    """
    pass

# 3. 통계 API
@router.get("/cep/events/stats")
def get_event_stats(
    session: Session,
    period: str = "24h"  # 1h, 6h, 24h, 7d
) -> EventStats:
    """
    이벤트 통계
    - total_count: 총 이벤트 수
    - ack_rate: 확인률
    - avg_time_to_ack: 평균 확인 시간
    - by_severity: 심각도별 분포
    - by_rule: 규칙별 분포
    - by_hour: 시간별 발생 추이
    """
    pass

# 4. 검색 강화
@router.get("/cep/events/search")
def search_events(
    session: Session,
    q: str,  # 전문 검색
    rule_id: Optional[str] = None,
    severity: Optional[str] = None,
    acked: Optional[bool] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100
) -> List[EventRead]:
    """
    고급 검색
    - q: rule_name, summary, payload 전문 검색
    - rule_id: 규칙 필터
    - severity: CRITICAL, HIGH, MEDIUM, LOW
    - acked: 확인 상태 필터
    - 날짜 범위 필터
    """
    pass
```

### 3.3 프론트엔드 개선

**파일**: `apps/web/src/app/cep-events/page.tsx`

```typescript
// 1. 실시간 구독 강화
const useEventStream = () => {
  const queryClient = useQueryClient();

  useEffect(() => {
    const eventSource = new EventSource('/api/cep/events/stream');

    // 요약 업데이트
    eventSource.addEventListener('summary', (event) => {
      const summary = JSON.parse(event.data);
      queryClient.setQueryData(['cep', 'events', 'summary'], summary);
    });

    // 새 이벤트
    eventSource.addEventListener('new_event', (event) => {
      const newEvent = JSON.parse(event.data);
      queryClient.setQueryData(['cep', 'events', 'list'], (old: any) => [
        newEvent,
        ...old
      ]);
    });

    // 과거 이벤트 (초기 로드)
    eventSource.addEventListener('historical', (event) => {
      const historicalEvent = JSON.parse(event.data);
      // 캐시에 추가 (중복 제거)
    });

    // ACK 업데이트
    eventSource.addEventListener('ack_event', (event) => {
      const { event_id, ack, ack_at } = JSON.parse(event.data);
      queryClient.setQueryData(['cep', 'events', event_id], (old: any) => ({
        ...old,
        ack,
        ack_at
      }));
    });

    return () => eventSource.close();
  }, [queryClient]);
};

// 2. 고급 필터링 UI
export function EventBrowserPage() {
  const [filters, setFilters] = useState({
    severity: null,
    ruleId: null,
    acked: false,
    since: null,
    until: null,
    search: ""
  });

  const { data: events } = useQuery({
    queryKey: ['cep', 'events', filters],
    queryFn: () => searchEvents(filters),
    staleTime: 5000
  });

  return (
    <div>
      {/* 필터 바 */}
      <FilterBar value={filters} onChange={setFilters} />

      {/* 요약 */}
      <EventSummary />

      {/* 이벤트 테이블 (ag-Grid) */}
      <EventTable events={events} />

      {/* 상세보기 */}
      <EventDetailPanel />
    </div>
  );
}

// 3. 일괄 작업
const handleBatchAck = async (eventIds: string[]) => {
  await fetch('/api/cep/events/batch-ack', {
    method: 'POST',
    body: JSON.stringify({ event_ids: eventIds })
  });
};
```

### 3.4 데이터베이스 최적화

**파일**: `apps/api/alembic/versions/00XX_optimize_cep_events.py`

```python
def upgrade():
    # 1. 풀텍스트 검색 인덱스
    op.execute('''
        CREATE INDEX idx_cep_notification_log_fts
        ON tb_cep_notification_log USING GIN (
            to_tsvector('english', payload::text)
        )
    ''')

    # 2. 성능 인덱스
    op.execute('''
        CREATE INDEX idx_cep_notification_log_compound
        ON tb_cep_notification_log(
            notification_id,
            fired_at DESC
        ) WHERE status = 'sent'
    ''')

    # 3. 파티셔닝 (대규모 데이터용, 선택사항)
    # ALTER TABLE tb_cep_notification_log
    # PARTITION BY RANGE (fired_at)
```

---

## 🤖 Phase 4: AI 코파일럿 + 완성 (1주)

### 4.1 AI 프롬프트 확장

**파일**: `apps/web/src/app/cep-builder/chat/page.tsx`

```typescript
const ENHANCED_COPILOT_INSTRUCTION = `
You are a CEP Rule Generator for Tobit's monitoring system.
Generate rules using form-friendly JSON format (NOT arrays).

ALWAYS return exactly one JSON object with type=cep_draft. NO markdown.

Guidelines for better form generation:
1. For conditions: Always use composite_condition with array of conditions
2. For actions: Provide specific endpoint URLs
3. For triggers: Include all required fields for the UI form

Example output:
{
  "type": "cep_draft",
  "draft": {
    "rule_name": "CPU High Alert",
    "description": "Alert when CPU exceeds 80%",
    "trigger_type": "metric",
    "trigger_spec": {
      "endpoint": "/api/metrics/cpu",
      "value_path": "data.avg",
      "op": ">",
      "threshold": 80,
      "duration": "5m",
      "aggregation": "avg"
    },
    "composite_condition": {
      "conditions": [
        {"field": "cpu", "op": ">", "value": 80},
        {"field": "memory", "op": ">", "value": 70}
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
}
`;
```

### 4.2 드래프트 자동 폼 채우기

```typescript
const applyCepDraftToForm = (draft: CepDraft, form: UseFormReturn) => {
  const { setValue } = form;

  // 기본 필드
  setValue("ruleName", draft.draft.rule_name);
  setValue("description", draft.draft.description ?? "");
  setValue("isActive", true);

  // 트리거
  setValue("triggerType", draft.draft.trigger_type);
  setValue("triggerSpec", draft.draft.trigger_spec);

  // 복합 조건
  if (draft.draft.composite_condition) {
    setValue("conditions", draft.draft.composite_condition.conditions);
    setValue("conditionLogic", draft.draft.composite_condition.logic);
  }

  // 액션
  setValue("actions", draft.draft.actions);

  // 상태 업데이트
  setDraftStatus("applied");
};
```

### 4.3 테스트 전략

**유닛 테스트**:
```python
# test_executor.py
def test_composite_conditions_and():
    trigger_spec = {
        "conditions": [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70}
        ],
        "logic": "AND"
    }
    payload = {"cpu": 85, "memory": 75}
    result = evaluate_trigger(trigger_spec, payload)
    assert result == (True, {})

def test_composite_conditions_or():
    trigger_spec = {
        "conditions": [
            {"field": "cpu", "op": ">", "value": 80},
            {"field": "memory", "op": ">", "value": 70}
        ],
        "logic": "OR"
    }
    payload = {"cpu": 75, "memory": 75}
    result = evaluate_trigger(trigger_spec, payload)
    assert result == (True, {})

# test_event_flow.py
@pytest.mark.asyncio
async def test_event_realtime_streaming():
    """SSE 스트림에 이벤트가 실시간으로 전송되는지 확인"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/cep/events/stream") as response:
            # 첫 번째 메시지: summary
            message = await response.aiter_lines().__anext__()
            assert "summary" in message

            # 트리거 발생
            await trigger_rule(rule_id)

            # 두 번째 메시지: new_event
            message = await response.aiter_lines().__anext__()
            assert "new_event" in message
```

**E2E 테스트**:
```typescript
// e2e/cep-flow.spec.ts
describe('CEP Complete Flow', () => {
  test('should create rule via form and trigger it', async ({ page }) => {
    // 1. 규칙 생성 (폼)
    await page.goto('/cep-builder');
    await page.fill('input[name="ruleName"]', 'Test Rule');
    await page.selectOption('select[name="triggerType"]', 'metric');
    await page.fill('input[name="threshold"]', '80');

    // 2. 조건 추가 (복합)
    await page.click('button:has-text("+ 조건 추가")');
    await page.fill('input[name="conditions.0.field"]', 'cpu');

    // 3. 저장
    await page.click('button:has-text("저장")');

    // 4. 이벤트브라우저 모니터링
    await page.goto('/cep-events');

    // 5. 규칙 트리거 (시뮬레이션)
    const response = await fetch('/api/cep/rules/{ruleId}/simulate', {
      method: 'POST',
      body: JSON.stringify({ test_payload: { cpu: 85 } })
    });

    // 6. 이벤트 나타남 확인
    await expect(page.locator('text=Test Rule')).toBeVisible();
  });
});
```

---

## 📋 체크리스트

### Phase 1 (복합 조건)
- [ ] executor.py에 `_evaluate_composite_conditions()` 함수 추가
- [ ] `evaluate_trigger()` 함수 개선 (기존 호환성 유지)
- [ ] 유효성 검사 추가
- [ ] 단위 테스트 작성 (AND/OR/NOT/중첩)
- [ ] 기존 기능 회귀 테스트

### Phase 2 (폼 UI)
- [ ] CepRuleFormPage.tsx 레이아웃 설계
- [ ] FormFieldGroup 컴포넌트 구현
- [ ] TriggerTypeSelector 구현
- [ ] ConditionsSection 구현 (복합 조건)
- [ ] ActionSection 구현
- [ ] SimulationPanel 구현
- [ ] react-hook-form + Zod 통합
- [ ] 새 API 엔드포인트 구현 (validate, templates, preview)
- [ ] JSON ↔ 폼 양방향 변환
- [ ] 기존 JSON 에디터 모드와 호환성

### Phase 3 (실시간 연동)
- [ ] event_broadcaster.py에 Redis 지원 추가
- [ ] SSE 초기 로드백 구현 (최근 1시간)
- [ ] 고급 필터링 API 추가 (search, grouped, stats)
- [ ] 이벤트브라우저 UI 개선 (필터, 검색, 일괄 작업)
- [ ] 데이터베이스 인덱스 생성 (성능 최적화)
- [ ] 통합 테스트

### Phase 4 (AI + 배포)
- [ ] AI 프롬프트 확장
- [ ] 드래프트 자동 폼 채우기
- [ ] 전체 기능 테스트 (단위 + E2E)
- [ ] 성능 벤치마크
- [ ] 문서 작성
- [ ] 배포 및 마이그레이션

---

## 🧪 테스트 계획

### 단위 테스트 (기존 + 신규)
```
복합 조건 평가
├─ AND 로직 (모두 True)
├─ AND 로직 (하나 False)
├─ OR 로직 (하나 True)
├─ OR 로직 (모두 False)
├─ NOT 로직
└─ 중첩 조건

폼 검증
├─ 필드 검증 (required, min, max)
├─ 트리거 타입별 검증
├─ 액션 검증
└─ 복합 조건 검증

API 엔드포인트
├─ POST /validate/condition
├─ GET /condition-templates
├─ POST /rules/preview
├─ GET /field-suggestions
└─ GET /events/search
```

### 통합 테스트
```
규칙 생성 → 트리거 → 이벤트 발생 → 이벤트브라우저 표시
├─ 단일 조건
├─ 복합 조건 (AND)
├─ 복합 조건 (OR)
└─ 복합 조건 (NOT)
```

### E2E 테스트
```
폼 UI에서 규칙 생성
├─ 기본 정보 입력
├─ 트리거 설정
├─ 복합 조건 추가
├─ 액션 설정
└─ 시뮬레이션 + 저장

이벤트브라우저 모니터링
├─ 실시간 이벤트 수신
├─ 필터링 및 검색
├─ ACK 처리
└─ 일괄 작업
```

---

## 🎯 성공 기준

| 항목 | 현재 | 목표 | 확인 방법 |
|------|------|------|---------|
| **조건 복잡도** | 단일 | AND/OR/NOT | 단위 테스트 |
| **UI 진입 장벽** | JSON 직접 편집 | 폼 기반 | 사용자 테스트 |
| **실시간성** | 30초 폴링 | <1초 | SSE 메시지 지연 측정 |
| **검색 기능** | rule_id만 | 전문 검색 | API 테스트 |
| **이벤트 재현** | 없음 | 최근 1시간 로드백 | 클라이언트 재연결 테스트 |
| **폼 검증** | 기본 | Zod 스키마 | 폼 테스트 |
| **AI 드래프트** | 기존 | 폼 자동 채우기 | E2E 테스트 |

---

## 🔑 핵심 파일 수정 목록

### Backend
1. **executor.py** - 복합 조건 평가 함수 추가
2. **schemas.py** - 새로운 스키마 정의
3. **router.py** - 새로운 API 엔드포인트
4. **event_broadcaster.py** - Redis Pub/Sub 통합
5. **models.py** - 필요시 새로운 필드 추가

### Frontend
1. **cep-builder/page.tsx** - 새로운 폼 기반 페이지
2. **components/cep-builder-v2/** - 새 컴포넌트 구조
3. **cep-events/page.tsx** - 이벤트브라우저 개선
4. **app/cep-builder/chat/page.tsx** - AI 프롬프트 확장

### Database
1. **alembic/versions/00XX_add_composite_conditions.py** - 스키마 변경 (선택사항)
2. **alembic/versions/00XX_optimize_cep_events.py** - 인덱스 추가

---

## 📊 예상 영향도

| 항목 | 영향도 | 비고 |
|------|--------|------|
| 기존 규칙 호환성 | 낮음 | 복합 조건은 선택사항, 기존 단일 조건도 지원 |
| 데이터베이스 변경 | 매우 낮음 | JSONB만 사용하므로 스키마 변경 최소 |
| API 호환성 | 낮음 | 새 엔드포인트만 추가, 기존 엔드포인트 유지 |
| 성능 영향 | 중간 | Redis 추가로 브로드캐스팅 성능 향상 |
| 복잡도 증가 | 중간 | 폼 UI로 사용성은 향상되지만 코드 복잡도 증가 |

---

## ⚠️ 리스크 및 완화

| 리스크 | 확률 | 영향 | 완화책 |
|--------|------|------|-------|
| 기존 규칙 깨짐 | 낮음 | 높음 | backward compatibility 테스트 |
| 성능 저하 | 중간 | 중간 | Redis 인덱싱, 쿼리 최적화 |
| UI 복잡성 | 낮음 | 낮음 | 폼 단순화, 기본값 제공 |
| Redis 의존성 | 중간 | 중간 | 폴백 메커니즘 (메모리 모드) |

---

## 📅 예상 일정

```
Week 1 (Phase 1: 복합 조건)
├─ Mon-Tue: executor.py 함수 추가 + 테스트
├─ Wed-Thu: 기존 기능 회귀 테스트
└─ Fri: 코드 리뷰 + 병합

Week 2 (Phase 2: 폼 UI)
├─ Mon-Tue: 컴포넌트 구조 설계 + 기본 구현
├─ Wed-Thu: ConditionsSection, ActionSection 완성
└─ Fri: react-hook-form 통합 + 테스트

Week 3 (Phase 3: 실시간 연동)
├─ Mon-Tue: Redis Pub/Sub, SSE 개선
├─ Wed: 이벤트브라우저 UI 개선
└─ Thu-Fri: 데이터베이스 최적화 + 통합 테스트

Week 4 (Phase 4: AI + 배포)
├─ Mon-Tue: AI 프롬프트 + 드래프트 자동 채우기
├─ Wed: 전체 E2E 테스트
├─ Thu: 성능 벤치마크 + 문서
└─ Fri: 배포 준비
```

---

## ✅ 다음 단계

1. **이 계획 승인** (당신의 피드백)
2. **Phase 1 시작**: executor.py 수정 시작
3. **GitHub Issues 생성**: 각 Phase별 태스크
4. **팀 공유**: 구현 진행 상황 공유

