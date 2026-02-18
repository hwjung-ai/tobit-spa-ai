# Comprehensive Module Improvement Plan

## 개요

CEP Builder, API Manager, SIM, Screen Editor 4개 모듈에 대한 종합 개선 계획.
**기능성(Functionality)**, **사용자 편의성(Usability)**, **AI Copilot** 3가지 측면 모두 포괄.

---

## 모듈별 현재 상태 요약

### CEP Builder (`apps/web/src/app/cep-builder/page.tsx`, 1,400줄)
| 영역 | 현재 상태 | 점수 |
|------|----------|------|
| 핵심 기능 | 4종 트리거, 복합조건, 윈도잉, 이상탐지 | 8/10 |
| UI/UX | 3패널 레이아웃, 듀얼 편집 모드 | 8/10 |
| Copilot | 메타데이터만 전달 (이름/타입) | 2/10 |
| 버전 관리 | 없음 | 0/10 |
| 템플릿 | 없음 | 0/10 |

### API Manager (`apps/web/src/app/api-manager/page.tsx`, 2,600줄)
| 영역 | 현재 상태 | 점수 |
|------|----------|------|
| 핵심 기능 | 5종 로직, SQL 보안, 버전 관리 | 8/10 |
| UI/UX | 3패널, 5종 전용 빌더 | 8/10 |
| Copilot | 메타데이터만 전달, 백엔드 미사용 | 3/10 |
| 템플릿 | 없음 | 0/10 |
| Import/Export | 없음 | 0/10 |

### SIM (`apps/web/src/app/sim/page.tsx`, 1,258줄)
| 영역 | 현재 상태 | 점수 |
|------|----------|------|
| 핵심 기능 | 4전략, 22함수, 3-tier 데이터, 백테스트 | 8/10 |
| UI/UX | 리사이즈 패널, 슬라이더, SSE 스트리밍 | 9/10 |
| Copilot | 컨텍스트 잘 전달, 분석 모드 없음 | 7/10 |
| 템플릿 | 4종 있음 | 10/10 |
| 결과 영속화 | 없음 | 0/10 |

### Screen Editor (`apps/web/src/components/admin/screen-editor/`, 모듈화됨)
| 영역 | 현재 상태 | 점수 |
|------|----------|------|
| 핵심 기능 | 6탭, 19종 컴포넌트, 버전 관리 | 9/10 |
| UI/UX | 협업, Presence, CRDT | 9/10 |
| Copilot | 백엔드 완비, 프론트엔드 미연결 | 5/10 |
| 템플릿 | 갤러리 존재하나 접근성 낮음 | 5/10 |

---

## P0: Critical Improvements (최우선)

### P0.1 CEP Builder

#### P0.1.1 Copilot Full Context Passing
**파일**: `apps/web/src/app/cep-builder/page.tsx`
- `copilotBuilderContext`에 전체 룰 정보 전달
- `trigger_spec`, `action_spec`, `conditions`, `actions`, `windowing`, `aggregation` 포함

#### P0.1.2 Inline Form Validation
**파일**: `apps/web/src/components/cep-form-builder/*.tsx`
- 각 필드별 실시간 검증 메시지
- 필수 필드 인라인 표시

#### P0.1.3 Rule Duplicate 기능
**파일**: `apps/web/src/app/cep-builder/page.tsx`
- 기존 룰 복제 버튼 추가
- `duplicateRule()` 함수 구현

### P0.2 API Manager

#### P0.2.1 Copilot Full Context Passing
**파일**: `apps/web/src/app/api-manager/page.tsx`
- `logic_body`, `param_schema`, `runtime_policy` 전달

#### P0.2.2 API Duplicate 기능
**파일**: `apps/web/src/app/api-manager/page.tsx`
- API 복제 버튼 및 함수 구현

#### P0.2.3 Logic Type 전환 시 데이터 보존
**파일**: `apps/web/src/app/api-manager/page.tsx`
- sql → http 전환 시 이전 데이터 임시 저장
- 복원 옵션 제공

### P0.3 SIM

#### P0.3.1 Copilot Analysis Mode
**파일**: `apps/web/src/app/sim/page.tsx`
- `sim_analysis` 타입 추가
- 결과 해석/인사이트 생성 가능하도록 프롬프트 수정

#### P0.3.2 Simulation Result Persistence
**파일**: `apps/api/app/modules/simulation/` + `apps/web/src/app/sim/`
- 실행 결과 DB 저장
- 이력 조회 UI

### P0.4 Screen Editor

#### P0.4.1 ChatExperience → Backend Copilot 전환
**파일**: `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx`
- `/ai/screen-copilot` 백엔드 호출로 전환
- Confidence, Suggestions UI 표시

---

## P1: High Priority Improvements

### P1.1 Backend Copilot Services

#### P1.1.1 CEP Copilot Service (NEW)
**파일**:
- `apps/api/app/modules/ai/cep_copilot_service.py`
- `apps/api/app/modules/ai/cep_copilot_schemas.py`
- `apps/api/app/modules/ai/cep_copilot_prompts.py`

**엔드포인트**:
- `POST /ai/cep-copilot`
- `POST /ai/cep-copilot/validate`

#### P1.1.2 SIM Copilot Service (NEW)
**파일**:
- `apps/api/app/modules/ai/sim_copilot_service.py`
- `apps/api/app/modules/ai/sim_copilot_schemas.py`
- `apps/api/app/modules/ai/sim_copilot_prompts.py`

**엔드포인트**:
- `POST /ai/sim-copilot`
- `POST /ai/sim-copilot/analyze`

### P1.2 Version Control for CEP

#### P1.2.1 CEP Rule Versioning
**파일**:
- `apps/api/app/modules/cep_builder/models.py` - TbCepRuleVersion 모델 추가
- `apps/api/app/modules/cep_builder/crud.py` - 버전 관리 CRUD
- `apps/api/app/modules/cep_builder/router/rules.py` - 버전 엔드포인트

### P1.3 Incremental Modification (Patch Mode)

#### P1.3.1 CEP Patch Mode
**파일**: `apps/web/src/lib/cep-builder/utils.ts`
- `mode: "patch"` 지원
- JSON Patch 기반 증분 수정

#### P1.3.2 SIM Patch Mode
**파일**: `apps/web/src/app/sim/page.tsx`
- 시나리오 파라미터 증분 수정 지원

### P1.4 ML/DL Model Loading

#### P1.4.1 Model Registry Integration
**파일**: `apps/api/app/modules/simulation/services/simulation/strategies/ml_strategy_real.py`
- 학습된 모델 로딩 구현
- Fallback 유지

---

## P2: Medium Priority Improvements

### P2.1 Shared Copilot UI Components

#### P2.1.1 CopilotResponseDisplay (NEW)
**파일**: `apps/web/src/components/copilot/CopilotResponseDisplay.tsx`
```typescript
interface CopilotResponseDisplayProps {
  explanation?: string;
  confidence?: number;
  suggestions?: string[];
  warnings?: string[];
  errors?: string[];
}
```

#### P2.1.2 CopilotStatusBadge (NEW)
**파일**: `apps/web/src/components/copilot/CopilotStatusBadge.tsx`
- Confidence 점수 시각화 (색상 코딩)

### P2.2 Example Prompts UI

#### P2.2.1 CEP Example Prompts
**파일**: `apps/web/src/components/cep-builder/ExamplePrompts.tsx`
- 12개 예시 프롬프트 클릭 가능 칩으로 표시

#### P2.2.2 API Manager Example Prompts
**파일**: `apps/web/src/components/api-manager/ExamplePrompts.tsx`
- SQL/HTTP/Python/Workflow별 예시

### P2.3 Onboarding Tours

#### P2.3.1 CEP Onboarding
**파일**: `apps/web/src/components/cep-builder/OnboardingTour.tsx`
- 5단계 투어: 트리거 → 조건 → 윈도잉 → 액션 → 테스트

#### P2.3.2 API Manager Onboarding
**파일**: `apps/web/src/components/api-manager/OnboardingTour.tsx`
- 4단계 투어: Definition → Logic → Test → Save

### P2.4 Rule/API Import/Export

#### P2.4.1 CEP JSON Import/Export
**파일**: `apps/web/src/app/cep-builder/page.tsx`
- 룰 JSON 다운로드
- JSON 파일 업로드로 룰 가져오기

#### P2.4.2 API Definition Import/Export
**파일**: `apps/web/src/app/api-manager/page.tsx`
- API 정의 JSON 다운로드/업로드

---

## P3: Lower Priority Improvements

### P3.1 Multi-turn Conversation

#### P3.1.1 Conversation Context Preservation
**파일**: `apps/web/src/lib/copilot/conversation-context.ts`
- 마지막 N개 메시지 요약을 컨텍스트에 포함
- "그 버튼 색상 바꿔줘" 같은 후속 요청 처리

### P3.2 Advanced Features

#### P3.2.1 CEP Rule Templates Gallery
**파일**: `apps/web/src/components/cep-builder/TemplatesGallery.tsx`
- CPU 알림, 메모리 경고, 에러율 급증 등 사전 정의 템플릿

#### P3.2.2 API Manager Workflow Conditions
**파일**: `apps/web/src/components/api-manager/WorkflowBuilder.tsx`
- if/else 분기 노드 지원

#### P3.2.3 SIM Strategy Recommendation
**파일**: `apps/web/src/app/sim/page.tsx`
- 백테스트 결과 기반 전략 추천

---

## 구현 순서 및 병렬 작업 계획

### Phase 1: P0 (4개 모듈 병렬)
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  CEP Builder    │  │  API Manager    │  │      SIM        │  │ Screen Editor   │
│  P0.1.1-3       │  │  P0.2.1-3       │  │  P0.3.1-2       │  │  P0.4.1         │
│  Agent 1        │  │  Agent 2        │  │  Agent 3        │  │  Agent 4        │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Phase 2: P1 (백엔드 + 프론트엔드 병렬)
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  CEP Backend    │  │  SIM Backend    │  │  Frontend       │
│  Copilot P1.1.1 │  │  Copilot P1.1.2 │  │  Patch Mode     │
│  Agent 5        │  │  Agent 6        │  │  P1.3 Agent 7   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Phase 3: P2 (공유 컴포넌트 + 온보딩)
```
┌─────────────────┐  ┌─────────────────┐
│  Shared Copilot │  │  Onboarding     │
│  Components     │  │  Tours          │
│  Agent 8        │  │  Agent 9        │
└─────────────────┘  └─────────────────┘
```

### Phase 4: P3 + 통합 테스트
```
┌─────────────────┐  ┌─────────────────┐
│  P3 Advanced    │  │  Integration    │
│  Features       │  │  Testing        │
│  Agent 10       │  │  Agent 11       │
└─────────────────┘  └─────────────────┘
```

---

## 테스트 계획

### Unit Tests
- 각 모듈별 Copilot 컨텍스트 전달 함수
- Patch mode 적용 로직
- Import/Export 파싱

### Integration Tests
- Frontend → Backend Copilot flow
- Draft → Apply → Save flow
- Version history → Rollback

### E2E Tests
- CEP: 자연어로 룰 생성 → 수정 → 저장 → 실행
- API Manager: 자연어로 API 생성 → 테스트 → 저장
- SIM: 시나리오 생성 → 실행 → 결과 분석
- Screen Editor: 자연어로 화면 수정 → 미리보기 → 적용

---

## 파일 변경 요약

### NEW Files (18개)
1. `apps/api/app/modules/ai/cep_copilot_service.py`
2. `apps/api/app/modules/ai/cep_copilot_schemas.py`
3. `apps/api/app/modules/ai/cep_copilot_prompts.py`
4. `apps/api/app/modules/ai/sim_copilot_service.py`
5. `apps/api/app/modules/ai/sim_copilot_schemas.py`
6. `apps/api/app/modules/ai/sim_copilot_prompts.py`
7. `apps/web/src/components/copilot/CopilotResponseDisplay.tsx`
8. `apps/web/src/components/copilot/CopilotStatusBadge.tsx`
9. `apps/web/src/components/cep-builder/ExamplePrompts.tsx`
10. `apps/web/src/components/cep-builder/OnboardingTour.tsx`
11. `apps/web/src/components/cep-builder/TemplatesGallery.tsx`
12. `apps/web/src/components/api-manager/ExamplePrompts.tsx`
13. `apps/web/src/components/api-manager/OnboardingTour.tsx`
14. `apps/web/src/lib/copilot/conversation-context.ts`
15. `apps/api/app/modules/simulation/models/simulation_result.py`
16. `apps/api/alembic/versions/XXXX_add_simulation_result_table.py`
17. `apps/api/app/modules/cep_builder/models/version.py`
18. `apps/api/alembic/versions/XXXX_add_cep_rule_version_table.py`

### MODIFY Files (12개)
1. `apps/web/src/app/cep-builder/page.tsx` - Context, Duplicate, Import/Export
2. `apps/web/src/app/api-manager/page.tsx` - Context, Duplicate, Logic preservation
3. `apps/web/src/app/sim/page.tsx` - Analysis mode, Result persistence
4. `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx` - Backend copilot
5. `apps/web/src/lib/cep-builder/utils.ts` - Patch mode
6. `apps/api/app/modules/ai/router.py` - New endpoints
7. `apps/api/app/modules/cep_builder/router/rules.py` - Version endpoints
8. `apps/api/app/modules/cep_builder/crud.py` - Version CRUD
9. `apps/api/app/modules/simulation/api/router.py` - Result persistence
10. `apps/api/app/modules/simulation/services/simulation/strategies/ml_strategy_real.py` - Model loading
11. `apps/api/app/modules/simulation/services/simulation/strategies/dl_strategy_real.py` - Model loading
12. `apps/api/app/modules/simulation/crud.py` - Result CRUD
