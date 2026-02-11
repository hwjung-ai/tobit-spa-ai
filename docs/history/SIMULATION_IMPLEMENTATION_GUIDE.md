# Simulation Implementation Guide (OPS What-If)

> 최종 업데이트: 2026-02-11  
> 상태: Implemented (Archived)  
> 요구사항 매핑: 26. 시뮬레이션

## 1. 목적

본 문서는 Tobit SPA AI에서 "시뮬레이션" 기능을 실제 제품 수준으로 구현하기 위한 기준 설계서다.
초기에는 **규칙 기반 What-if 시뮬레이션**으로 시작하고, 이후 **통계/ML/DL 기반 데이터 시뮬레이션**으로 확장한다.

핵심 목표:
1. 사용자가 가정(What-if)을 입력하면 예상 결과를 계산한다.
2. 결과를 수치/차트/근거(Reference)로 설명 가능하게 반환한다.
3. OPS Orchestrator, ToolCall/Reference 표준, Tenant 보안 규칙을 준수한다.

---

## 2. 용어 정의

- **Simulation**: 사용자 가정을 입력받아 모델(규칙/통계/ML/DL)로 결과를 계산하는 기능
- **Prediction(예측)**: 특정 미래 값을 추정하는 계산
- **Inference(추론)**: 결과가 나온 이유/기여도를 해석
- **Scenario**: 가정 + 대상 + 기간 + 목표 지표를 묶은 실행 단위
- **Strategy**: 시뮬레이션 알고리즘 구현체(규칙/통계/ML/DL)

정리:
- 시뮬레이션은 "가정 + 예측 + 해석"을 포괄하는 상위 개념으로 운영한다.

---

## 3. CEP와의 경계

| 구분 | Simulation | CEP |
|------|------------|-----|
| 목적 | 사전 의사결정 지원 | 실시간 이벤트 대응 |
| 입력 | 사용자 가정 + 과거 데이터 | 실시간 이벤트 스트림 |
| 출력 | 예상 결과, 비교 차트, 권고안 | 알림/액션 실행 |
| 시간축 | 계획/검토 | 즉시 처리 |
| 핵심 질문 | "이렇게 바꾸면 어떻게 되나?" | "지금 조건이 충족됐나?" |

연계 방식:
1. 시뮬레이션으로 임계치/정책 후보를 검증
2. 검증 결과를 CEP 룰 설정에 반영
3. 운영 중 CEP 결과를 다시 시뮬레이션 데이터로 환류

---

## 4. 범위 (Scope)

### 4.1 Phase 1 (필수)

- 규칙 기반 What-if 시뮬레이션
- 메인 메뉴 `SIM` 전용 라우트 및 전용 API 도입
- 표준 Answer Block + Reference Block 반환
- 시나리오 템플릿/룰셋 버전 관리 (draft/published)
- Tenant 격리 + 인증 + 감사 추적

### 4.2 Phase 2 (확장)

- 통계 기반 전략 추가 (이동평균/회귀/계절성)
- 결과에 신뢰구간/오차범위 표시
- 백테스트/성능 평가 리포트

### 4.3 Phase 3 (선택)

- ML 전략(XGBoost/RandomForest 등) + 모델 레지스트리
- DL 전략(LSTM/Transformer 등) + MLOps 파이프라인

### 4.4 Non-goal (초기 제외)

- 완전 자동 의사결정/자동 배포
- 학습 파이프라인 대규모 자동화
- 실시간 CEP 대체

---

## 4.5 진행 체크리스트 (업데이트용)

- [x] 메인 메뉴에 `SIM` 추가 (`apps/web/src/components/NavTabs.tsx`, `apps/web/src/components/MobileBottomNav.tsx`)
- [x] `SIM` 전용 페이지 라우트 생성 (`apps/web/src/app/sim/page.tsx`)
- [x] SIM 전용 API 경로 구현 (`apps/api/app/modules/simulation/api/router.py`, `/sim/templates`, `/sim/query`, `/sim/run`)
- [x] Simulation 전용 DTO 실제 코드 반영 (`apps/api/app/modules/simulation/schemas.py`)
- [x] Rule Strategy 구현 (`apps/api/app/modules/simulation/services/simulation/strategies/rule_strategy.py`)
- [x] Stat Strategy 구현 (`apps/api/app/modules/simulation/services/simulation/strategies/stat_strategy.py`)
- [x] ML Strategy 구현 (`apps/api/app/modules/simulation/services/simulation/strategies/ml_strategy.py`)
- [x] DL Strategy 구현 (`apps/api/app/modules/simulation/services/simulation/strategies/dl_strategy.py`)
- [x] SIM 결과 블록(요약/표/차트/근거) 정식화 (`apps/api/app/modules/simulation/services/simulation/presenter.py`)
- [x] SIM 전용 Frontend 화면(폼/카드/차트/근거 패널) 구현 (`apps/web/src/app/sim/page.tsx`)
- [x] Backtest 리포트 API/화면 구현 (`/sim/backtest`, `apps/web/src/app/sim/page.tsx`)
- [x] CSV Export 구현 (`/sim/export`, `apps/web/src/app/sim/page.tsx`)
- [x] Backend pytest + Frontend e2e + type/lint 검증 완료

진행 규칙:
1. 작업 완료 즉시 `[ ] -> [x]`로 변경
2. 체크된 항목은 관련 파일 경로를 괄호로 명시
3. 체크 후 테스트 실행 결과를 함께 기록

검증 기록:
1. `apps/api`: `pytest tests/test_simulation_router.py tests/test_simulation_executor.py tests/test_simulation_rule_strategy.py tests/test_simulation_tenant_isolation.py tests/test_simulation_dl_strategy.py -q` -> `11 passed`
2. `apps/web`: `npm run type-check` -> `tsc --noEmit` 통과
3. `apps/web`: `npx playwright test tests-e2e/simulation.spec.ts` -> `2 passed`
4. `apps/api`: `ruff check app/modules/simulation tests/test_simulation_router.py tests/test_simulation_executor.py tests/test_simulation_rule_strategy.py tests/test_simulation_tenant_isolation.py tests/test_simulation_dl_strategy.py` -> `All checks passed`
5. `apps/web`: `npx eslint src/app/sim/page.tsx src/components/NavTabs.tsx src/components/MobileBottomNav.tsx` -> 통과

---

## 5. 아키텍처 (권장)

## 5.1 백엔드 모듈 구조

```text
apps/api/app/modules/simulation/
  api/
    router.py                        # /sim/query, /sim/run
  services/
    simulation/
      planner.py                     # 자연어 질의 -> SimulationPlan
      schemas.py                     # Request/Response DTO + 내부 모델
      strategy_base.py               # 공통 인터페이스
      strategies/
        rule_strategy.py             # Phase 1
        stat_strategy.py             # Phase 2
        ml_strategy.py               # Phase 3
        dl_strategy.py               # Phase 3
      rule_registry.py               # 룰셋 조회/버전 선택
      scenario_templates.py          # 템플릿/파라미터 정의
      simulation_executor.py         # 실행 오케스트레이션
      presenter.py                   # Answer Block 구성
      validators.py                  # 입력 검증/정책 검증
```

## 5.2 처리 흐름

```text
User Question
  -> Planner (scenario, assumptions, target_kpis, horizon)
  -> Validator (tenant/auth/param guardrails)
  -> Strategy Selector (rule/stat/ml/dl)
  -> Simulation Executor
  -> Block Presenter (summary/table/timeseries/reference/toolcalls)
  -> ResponseEnvelope
```

## 5.3 독립 SIM 서비스 통합 포인트

- 메인 메뉴 `/sim`에서 SIM 전용 API 호출
- 필요 시 OPS/CEP에서 SIM 결과를 참조할 수 있도록 인터페이스만 제공
- 모든 도구 호출은 `ToolCall`로 trace 저장
- 모든 근거 데이터는 `ReferenceItem`으로 누적

---

## 6. API 계약 (Contract)

## 6.1 엔드포인트

### A안 (권장): 전용 실행 엔드포인트

`POST /sim/run`

```json
{
  "mode": "simulation",
  "question": "트래픽이 20% 증가하면 API 응답시간이 얼마나 늘어나나?",
  "context": {
    "service": "api-gateway",
    "time_window": "last_30d"
  },
  "simulation": {
    "scenario_type": "what_if",
    "assumptions": {
      "traffic_change_pct": 20,
      "cpu_limit_pct": 85
    },
    "horizon": "7d",
    "strategy": "rule"
  }
}
```

### B안: 조회/실행 분리

- `POST /sim/query` (계획/검증)
- `POST /sim/run` (실행)

## 6.2 응답 형식

모든 REST 응답은 `ResponseEnvelope` 준수:

```json
{
  "time": "2026-02-10T12:00:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "mode": "simulation",
    "summary": "...",
    "blocks": [],
    "trace_id": "...",
    "tool_calls": [],
    "references": []
  }
}
```

## 6.3 블록 구성 원칙

최소 블록 세트:
1. `MarkdownBlock`: 시나리오 요약/해석
2. `TableBlock`: KPI baseline vs scenario 비교
3. `TimeSeriesBlock` 또는 `Bar/Waterfall`: 변화 추이/기여도
4. `ReferenceBlock`: 적용 규칙/조회 쿼리/데이터 근거

---

## 7. 스키마 설계

## 7.1 요청 DTO

```python
class SimulationSpec(BaseModel):
    scenario_type: Literal["what_if", "stress_test", "capacity"] = "what_if"
    assumptions: dict[str, Any] = Field(default_factory=dict)
    horizon: str = "7d"
    strategy: Literal["rule", "stat", "ml", "dl"] = "rule"

class OpsSimulationRequest(BaseModel):
    mode: Literal["simulation"]
    question: str
    context: dict[str, Any] = Field(default_factory=dict)
    simulation: SimulationSpec
```

## 7.2 내부 계획 모델

```python
class SimulationPlan(BaseModel):
    scenario_id: str
    scenario_name: str
    target_entities: list[str]
    target_kpis: list[str]
    assumptions: dict[str, Any]
    baseline_window: str
    horizon: str
    strategy: str
```

## 7.3 결과 모델

```python
class SimulationResult(BaseModel):
    scenario_id: str
    strategy: str
    kpi_delta: dict[str, Any]
    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    explanation: str
```

---

## 8. 전략(알고리즘/함수) 구조

## 8.1 공통 인터페이스

```python
class SimulationStrategy(Protocol):
    name: str

    def run(
        self,
        *,
        plan: SimulationPlan,
        baseline_data: dict[str, Any],
        tenant_id: str,
    ) -> SimulationResult:
        ...
```

## 8.2 Rule Strategy (Phase 1 필수)

특징:
- 빠른 구현
- 설명 가능성 높음
- 비즈니스 룰 통제 쉬움

권장 룰 타입:
1. 선형식: `y = a*x + b`
2. 구간식: threshold band
3. if-then 매핑
4. 가중합 영향도

룰 JSON 예시:

```json
{
  "rule_id": "sim_rule_cpu_latency_v1",
  "name": "CPU 대비 Latency 영향",
  "version": 1,
  "status": "published",
  "inputs": ["cpu_change_pct"],
  "output": "latency_change_pct",
  "formula": "0.8 * cpu_change_pct",
  "constraints": {
    "cpu_change_pct": {"min": -50, "max": 200}
  },
  "metadata": {
    "owner": "ops",
    "updated_at": "2026-02-10T00:00:00Z"
  }
}
```

## 8.3 Stat Strategy (Phase 2)

추천 알고리즘:
- 이동평균
- 단순/다중 회귀
- 계절성 보정
- 신뢰구간 계산

출력 추가:
- `confidence_interval`
- `error_bound`

## 8.4 ML/DL Strategy (Phase 3)

운영 원칙:
- 예측 함수는 공통 인터페이스 유지
- 모델 버전과 feature schema를 reference에 포함
- 백테스트 실패 시 rule/stat로 fallback

---

## 9. 데이터 소스 정책

1. PostgreSQL: KPI baseline, 이력 데이터
2. Neo4j: 의존성/영향 전파 경로
3. Redis: 단기 캐시, 최근 계산 결과
4. **Mock 데이터 사용 금지**: SIM 모듈은 고정 샘플/가짜 데이터 경로를 사용하지 않으며, 실데이터 조회 실패 시 명시적 오류를 반환한다.

보안/격리:
- `current_user: TbUser = Depends(get_current_user)` 필수
- `tenant_id` 필터 없는 조회 금지
- 민감 키(`password`, `secret`, `token`, `api_key`) 마스킹

---

## 10. ToolCall / Reference 표준 적용

모든 실행 단위에서 다음을 강제:

1. ToolCall
- `tool`
- `elapsed_ms`
- `input_params`
- `output_summary`
- `error`

2. ReferenceItem
- `kind` (예: `sql`, `cypher`, `rule`, `model`)
- `title`
- `payload`

권장 Reference 예시:
- 적용 룰 ID/버전
- SQL/Cypher 질의 요약
- 모델 버전 및 feature 목록
- 계산식/가정값

---

## 11. UI/UX 설계

## 11.1 IA / 라우팅

- 권장 라우트: `apps/web/src/app/sim/page.tsx`
- 메인 메뉴(`NavTabs`, `MobileBottomNav`)에서 직접 진입
- URL Query 동기화:
1. `scenario`
2. `strategy`
3. `horizon`
4. `service`

## 11.2 화면 레이아웃 (Desktop / Mobile)

Desktop (12-column):
1. 좌측 4칸: Scenario Builder
2. 우측 8칸 상단: KPI Summary Cards
3. 우측 8칸 중단: Comparison Charts
4. 우측 8칸 하단: Evidence / References

Mobile (단일 컬럼):
1. Scenario Builder (Accordion)
2. KPI Summary
3. Comparison Charts (Swipe Tabs)
4. Evidence

권장 최소 높이:
- Builder: `min-h-[320px]`
- Chart Area: `min-h-[420px]`
- Evidence: `min-h-[220px]`

## 11.3 사용자 플로우

1. 질문 입력 또는 템플릿 선택
2. 가정값 편집(증감률/임계치/기간)
3. 전략 선택(rule/stat/ml)
4. 실행 클릭
5. 결과 확인(요약 -> 차트 -> 근거)
6. 가정값 수정 후 재실행(compare 반복)
7. 결과 저장/공유(Phase 2)

## 11.4 컴포넌트 트리 (MVP)

`apps/web/src/components/sim/`

1. `SimulationPage.tsx`
2. `SimulationScenarioPanel.tsx`
3. `SimulationTemplateSelector.tsx`
4. `SimulationAssumptionForm.tsx`
5. `SimulationStrategySelector.tsx`
6. `SimulationRunButton.tsx`
7. `SimulationKpiSummary.tsx`
8. `SimulationComparisonCharts.tsx`
9. `SimulationResultTable.tsx`
10. `SimulationEvidencePanel.tsx`
11. `SimulationWarnings.tsx`
12. `SimulationEmptyState.tsx`
13. `SimulationErrorState.tsx`
14. `SimulationLoadingState.tsx`

## 11.5 데이터 계약 (Frontend 타입)

```ts
export type SimulationStrategy = "rule" | "stat" | "ml";

export interface SimulationRequestPayload {
  mode: "simulation";
  question: string;
  context?: Record<string, unknown>;
  simulation: {
    scenario_type: "what_if" | "stress_test" | "capacity";
    assumptions: Record<string, unknown>;
    horizon: string;
    strategy: SimulationStrategy;
  };
}

export interface SimulationKpiDelta {
  kpi: string;
  baseline: number;
  simulated: number;
  change_pct: number;
  unit?: string;
}
```

## 11.6 차트 규격 (Recharts 기준)

1. TimeSeries Line
- X: timestamp
- Y1: baseline
- Y2: simulated
- 용도: 시간축 변화 비교

2. KPI Delta Bar
- X: KPI명
- Y: change_pct
- 색상: 증가/감소 분리

3. Contribution Waterfall
- 항목별 기여도(+/-)
- 모델/룰 해석 결과 연동

차트 카드 공통:
- 제목
- 기간
- 단위
- 범례 토글
- export 버튼(Phase 2)

## 11.7 상태 설계

TanStack Query 키:
1. `["sim-run", tenantId, hash(payload)]`

UI 상태:
1. `idle`: 빈 상태 + 템플릿 추천
2. `loading`: skeleton + 직전 결과 유지
3. `success`: 결과 렌더링
4. `error`: 사용자 친화 메시지 + 재시도 버튼

에러 메시지 규칙:
- API `detail` 우선 표시
- 기술 메시지와 사용자 메시지 분리

## 11.8 상호작용 규칙

1. Enter 실행: 질문 input에서 `Enter`, textarea는 `Cmd/Ctrl+Enter`
2. 재실행: 가정값 변경 시 `Run` 활성화
3. 비교 고정: 직전 실행 결과와 현재 결과 2-way compare
4. 전략 전환: 동일 가정 유지, 결과만 재계산
5. 신뢰도 배지:
- High: `>=0.8`
- Medium: `0.6~0.79`
- Low: `<0.6`

## 11.9 접근성 / 테스트 식별자

필수 `data-testid`:
1. `simulation-question-input`
2. `simulation-template-select`
3. `simulation-strategy-select`
4. `simulation-run-button`
5. `simulation-kpi-summary`
6. `simulation-chart-timeseries`
7. `simulation-chart-delta`
8. `simulation-evidence-panel`
9. `simulation-warning-list`
10. `simulation-error-banner`

접근성:
- 모든 입력에 label 연결
- 차트 대체 텍스트/테이블 제공
- 키보드 탭 순서 보장

## 11.10 UI에서 반드시 노출할 근거

1. 적용 전략/룰/모델 버전
2. 주요 가정값
3. 데이터 기준 기간(`baseline_window`, `horizon`)
4. 경고/한계(데이터 부족, 외삽, fallback 여부)

## 11.11 디자인 원칙

1. 요약 먼저, 근거는 즉시 접근 가능
2. 차트 1개만 강조하지 말고 비교 표를 항상 같이 제공
3. 결과 숫자에는 단위와 기준선(baseline)을 같이 표시
4. \"시뮬레이션 결과\"임을 명확히 표시(실측 데이터와 구분)

---

## 12. 테스트 전략

## 12.1 Backend (필수)

경로:
- `apps/api/tests/test_simulation_router.py`
- `apps/api/tests/test_simulation_executor.py`
- `apps/api/tests/test_simulation_rule_strategy.py`
- `apps/api/tests/test_simulation_tenant_isolation.py`

검증 항목:
1. 입력 검증 실패(범위/타입) 처리
2. tenant_id 격리
3. ToolCall/Reference 생성
4. 동일 입력 재현성(규칙 기반 deterministic)
5. 에러 fallback 동작

## 12.2 Frontend (필수)

경로:
- `apps/web/tests-e2e/simulation.spec.ts`

검증 항목:
1. 시나리오 입력 -> 실행 -> 결과 표시
2. 가정값 변경 -> 결과 차이 확인
3. 근거 패널 노출
4. API 에러 메시지 표시

---

## 13. 단계별 구현 로드맵

## Sprint 1 (1주)

1. API/DTO/플래너/룰전략 뼈대
2. `/sim/run` 연결
3. 기본 블록 출력
4. 백엔드 단위 테스트

## Sprint 2 (1주)

1. UI 시나리오 폼 + 결과 뷰
2. 차트/근거 패널
3. E2E 테스트

## Sprint 3 (1주)

1. 통계 전략 추가
2. 신뢰구간/경고체계
3. 백테스트 리포트

## Sprint 4+ (선택)

1. ML/DL 전략 추가
2. 모델 레지스트리/버전 관리
3. 운영 모니터링

---

## 14. 멀티-AI 개발 분업 가이드

다수 AI에 병렬로 지시할 때 아래 Work Package(WP) 단위로 분할한다.

### WP-1: Backend Contract

목표:
- `simulation/schemas.py`, `planner.py`, `validators.py` 구현

산출물:
- DTO + 내부 Plan 모델
- 입력 검증 로직
- router 연결 포인트

완료 기준:
- `pytest apps/api/tests/test_simulation_router.py -v` 통과

### WP-2: Strategy Engine

목표:
- `strategy_base.py`, `strategies/rule_strategy.py`, `rule_registry.py` 구현

산출물:
- 공통 인터페이스
- 룰 실행 엔진
- 룰 버전 선택 로직

완료 기준:
- 동일 입력에 대해 동일 출력
- ToolCall/Reference 포함

### WP-3: OPS Integration

목표:
- `/sim/run` 통합
- `simulation_executor.py`, `presenter.py`

산출물:
- Answer Block 변환
- trace 연결

완료 기준:
- 기존 모드(config/metric/hist/graph/document/all) 회귀 없음

### WP-4: Frontend UX

목표:
- 시나리오 입력 + 결과 대시보드 UI 구현

산출물:
- simulation 컴포넌트 5종
- TanStack Query 연동

완료 기준:
- `npm run type-check`
- `npx playwright test simulation.spec.ts`

### WP-5: Quality & Docs

목표:
- 테스트/문서/운영가이드 정리

산출물:
- pytest + e2e + lint/type-check 결과
- `docs/FEATURES.md` 업데이트

완료 기준:
- 회귀 테스트 통과
- 문서 최신화 완료

---

## 15. AI 지시 템플릿 (복붙용)

```text
당신의 작업 범위는 [WP-X] 입니다.

필수 준수:
1) AGENTS.md 기술 스택/아키텍처/ResponseEnvelope/ToolCall/Reference 규칙 준수
2) 인증/tenant_id/get_session 규칙 준수
3) 기존 동작 회귀 금지
4) 코드 변경 시 테스트 동반 수정

산출:
- 변경 파일 목록
- 핵심 구현 요약
- 실행한 검증 명령 및 결과
- 남은 리스크
```

---

## 16. 리스크 및 대응

1. 룰 난립/일관성 저하
- 대응: rule registry + 버전 정책 + 승인 프로세스

2. 설명 불충분
- 대응: reference 강제 + 계산식 노출

3. 과도한 복잡도(초기 ML/DL)
- 대응: Phase 1 rule-only 고정, 통계 이후 확장

4. 테넌트 데이터 혼선
- 대응: tenant 필터 테스트를 CI 필수 게이트로 설정

---

## 17. 완료 정의 (Simulation 전용)

아래 조건을 모두 만족하면 시뮬레이션 기능을 완료로 본다.

1. 기능
- `/sim/run` 요청/응답 동작
- baseline vs scenario 비교 결과 제공
- 근거(Reference) 노출

2. 품질
- backend pytest 통과
- frontend e2e 통과
- lint/type-check 통과

3. 표준
- ResponseEnvelope 준수
- ToolCall/Reference 표준 준수
- tenant/auth/session 규칙 준수

4. 문서
- 본 문서 + `docs/FEATURES.md` + 사용자 가이드 반영
