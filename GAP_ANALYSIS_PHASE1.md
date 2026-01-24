# Phase 1 - 현 상태 점검 및 갭 분석 (완료)

**작성일**: 2026-01-24
**분석 범위**: Backend, Inspector, Asset Registry, Frontend
**결과**: 상세한 갭 목록 및 변경 대상 파일 확정

---

## 1. 백엔드 현황

### 1.1 Direct/Reject 분기 - ✅ 완전 구현됨
- **위치**: `app/modules/ops/router.py` (라인 490-596)
- **상태**: PlanOutputKind.DIRECT, REJECT 모두 처리됨
- **동작**:
  - DIRECT: plan_output.direct_answer.answer 반환
  - REJECT: plan_output.reject_payload.reason 반환

### 1.2 Stage 기반 Runner - ✅ 완전 구현됨
- **위치**: `app/modules/ops/router.py` (라인 509-596, 643-774)
- **상태**: 모든 stage (route_plan, validate, execute, compose, present)의 입출력 추적
- **동작**:
  - `StageInput` 객체로 stage 정의
  - `stage_inputs[]`, `stage_outputs[]` 배열로 모든 step 기록
  - `stages[]` 메타정보 (이름, 시간, 상태) 기록

### 1.3 Trace Schema - ✅ 부분 완전
- **ExecutionTraceRead** (inspector/schemas.py):
  - ✅ `route` 필드: str | None
  - ✅ `stage_inputs` 필드: List[Dict[str, Any]]
  - ✅ `stage_outputs` 필드: List[Dict[str, Any]]
  - ✅ `replan_events` 필드: List[Dict[str, Any]]
- **상태**: 모든 필드 선택사항(Optional)으로 정의됨

### 1.4 Replan 메커니즘 - ✅ 구현됨
- **위치**: `app/modules/ops/router.py` (라인 685-772)
- **동작**:
  - Error 감지 시 자동 재계획 트리거
  - Fallback plan으로 재실행
  - `replan_events[]` 배열에 기록

### 1.5 Asset 사용 현황

#### Prompt Asset - ✅ 완전 사용
- **위치**: `app/modules/ops/services/ci/planner/planner_llm.py` (라인 113)
- **사용처**: LLM 기반 output parser
- **Loader**: `load_prompt_asset(scope, engine, name)`

#### Source/Schema/Resolver Asset - ⚠️ 부분 사용
- **로드 위치**: `app/modules/ops/router.py` (라인 377-379)
- **사용**: 라우터에서 로드하지만 planner/validator에서는 미사용
- **상태**: loader.py에서 7가지 타입 모두 지원 (fallback 메커니즘 포함)

---

## 2. Inspector 현황

### 2.1 ExecutionTraceRead Schema - ✅ 완벽
**파일**: `app/modules/inspector/schemas.py`
- ✅ route, stage_inputs, stage_outputs, replan_events 모두 정의됨
- ✅ TbExecutionTrace 모델에 JSONB 타입으로 저장됨

### 2.2 Trace 서비스 - ✅ 완벽
**파일**: `app/modules/inspector/service.py`
- ✅ `persist_execution_trace()`: trace_payload에서 값 추출 및 저장
- ✅ 모든 필드 (route, stage_inputs, stage_outputs, replan_events) 처리

### 2.3 CRUD - ✅ 완벽
**파일**: `app/modules/inspector/crud.py`
- ✅ `list_execution_traces()`: route, replan_count 필터링 지원
- ✅ array_length 기반 replan 이벤트 수 필터링

### 2.4 Regression 분석 - ✅ 완벽
**파일**: `app/modules/inspector/regression/service.py`
- ✅ `_parse_stages_from_trace()`: stage_inputs/outputs 파싱
- ✅ 회귀 감지(regression detection)에 활용

---

## 3. Asset Registry 현황

### 3.1 Models - ✅ 완벽
**파일**: `app/modules/asset_registry/models.py`
- ✅ 8가지 asset_type 지원: prompt, mapping, policy, query, source, schema, resolver, screen
- ✅ 각 타입별 필드 완벽하게 정의됨
- ✅ PostgreSQL JSONB로 저장됨

### 3.2 Loader - ✅ 완벽
**파일**: `app/modules/asset_registry/loader.py`
- ✅ 7개 함수: prompt, mapping, policy, query, source, schema, resolver
- ✅ 3단계 fallback: DB → 파일 → hardcoded defaults
- ✅ 모든 타입에 지원

### 3.3 Validators - ✅ 완벽
**파일**: `app/modules/asset_registry/validators.py`
- ✅ 8가지 타입 모두 검증 함수 정의
- ✅ 필드 유효성, 타입 검사, 값 범위 검증
- ✅ 위험한 SQL 패턴 탐지 (query asset)

### 3.4 CRUD - ✅ 완벽
**파일**: `app/modules/asset_registry/crud.py`
- ✅ list_assets, get_asset, create_asset, update_asset, delete_asset
- ✅ 모든 자산 타입 지원

---

## 4. Frontend 현황

### 4.1 Admin Assets 페이지 - ⚠️ 부분 지원

#### AssetTable - ✅ 완벽
- ✅ 8가지 타입 모두 badge로 표시
- ✅ type 필터링 지원
- ✅ status 필터링 지원

#### AssetForm - ⚠️ 부분 지원
```
✅ 지원: prompt, mapping, policy, query (편집 가능)
❌ 미지원: source, schema, resolver, screen
          → 읽기 전용 + raw content 표시
```

#### CreateAssetModal - ❌ 제한
```
생성 가능: prompt, mapping, policy, query만
생성 불가: source, schema, resolver, screen
```

### 4.2 전문화된 Asset UI - ✅ 완벽

#### `/data/sources` - ✅ 완벽
- Source 관리 전용 UI
- CRUD + Connection Test
- 8가지 source_type 지원

#### `/data/resolvers` - ✅ 완벽
- Resolver 관리 전용 UI
- 3가지 rule_type 지원
- Simulation 기능

#### `/data/catalog` - ✅ 부분 지원
- Schema 조회 + Scan
- Table/Column 메타데이터
- 읽기 전용 (직접 편집 미지원)

### 4.3 Inspector UI - ✅ 완벽
- ✅ ReplanTimeline: replan_events 시각화
- ✅ InspectorStagePipeline: stage 파이프라인 시각화

---

## 5. 미연결 목록 (Gap List)

### Priority 1 - 중요 (기능적 갭)

| # | 항목 | 현재 상태 | 필요한 작업 | 파일 |
|---|------|---------|-----------|------|
| 1 | Source/Schema/Resolver를 planner/validator에서 실제 사용 | Router에서만 로드 | planner_llm, validator 확장 | `planner_llm.py`, `validator.py` |
| 2 | References 생성 규칙 | Tool calls 기반 최소 1건 생성 | References 생성 로직 강화 | `runner.py`, `stage_executor.py` |
| 3 | Asset Override 메커니즘 | 정의만 됨 | stage_executor에서 실제 override 적용 | `stage_executor.py` |
| 4 | Admin Assets에서 source/schema/resolver 편집 | Admin에서 미지원 | AssetForm 확장 또는 대체 UI 제공 | `AssetForm.tsx`, `CreateAssetModal.tsx` |

### Priority 2 - 중간 (구조적 강화)

| # | 항목 | 현재 상태 | 필요한 작업 | 파일 |
|---|------|---------|-----------|------|
| 5 | Screen Asset Loader | Loader에 없음 | loader.py에 load_screen_asset() 추가 | `loader.py` |
| 6 | StageInput/StageOutput 타입 강화 | Dict로 처리 | 타입 모델 사용 (라인 별도 정의) | `schemas.py`, `runner.py` |
| 7 | Replan Event 스키마 정규화 | 백엔드 생성 vs 프론트엔드 타입 불일치 | 스키마 동기화 | `router.py`, `ReplanTimeline.tsx` |
| 8 | Asset Version 선택 | "published"만 사용 | 명시적 버전 선택 지원 | `loader.py`, `service.py` |

### Priority 3 - 선택 (UI/UX 개선)

| # | 항목 | 현재 상태 | 필요한 작업 | 파일 |
|---|------|---------|-----------|------|
| 9 | Catalog 직접 편집 UI | Scan만 가능 | Schema 편집 기능 추가 (선택사항) | `data/catalog/page.tsx` |
| 10 | Data Explorer와 Asset Registry 통합 | 독립적 도구 | 통합 고려 (선택사항) | `data/page.tsx` |

---

## 6. 변경 대상 파일 최종 확정

### Backend 파일 (필수)

```
Priority 1 - 기능:
  ✅ app/modules/ops/services/ci/planner/planner_llm.py
  ✅ app/modules/ops/services/ci/planner/validator.py
  ✅ app/modules/ops/services/ci/orchestrator/runner.py
  ✅ app/modules/ops/services/ci/orchestrator/stage_executor.py
  ✅ app/modules/ops/schemas.py

Priority 2 - 구조:
  ✅ app/modules/asset_registry/loader.py
  ✅ app/modules/inspector/schemas.py
```

### Frontend 파일 (필수)

```
Priority 1 - Admin Assets:
  ✅ components/admin/AssetForm.tsx
  ✅ components/admin/CreateAssetModal.tsx
  ✅ app/admin/assets/page.tsx

Priority 2 - Inspector UI:
  ✅ components/ops/ReplanTimeline.tsx
  ✅ components/ops/InspectorStagePipeline.tsx
```

---

## 7. 현재 상태 요약

### 완전 구현 (No Gap)
- ✅ Direct/Reject 라우팅
- ✅ Stage 기반 Runner
- ✅ ExecutionTrace 스키마 (route, stage_inputs, stage_outputs, replan_events)
- ✅ Trace CRUD & Regression 분석
- ✅ Asset Registry Loader, Validators, Models (모든 타입)
- ✅ Inspector UI Components (ReplanTimeline, StagePipeline)
- ✅ Source/Schema/Resolver 전문화된 관리 UI

### 부분 구현 (Minor Gap)
- ⚠️ Asset Override 메커니즘 (정의O, 적용X)
- ⚠️ Source/Schema/Resolver 자산 사용 (Router에서만 로드)
- ⚠️ Admin Assets에서 source/schema/resolver 편집 (대체 UI 존재)

### 미구현 (Major Gap)
- ❌ Screen Asset Loader
- ❌ References 생성 로직 강화
- ❌ StageInput/StageOutput 타입화
- ❌ Replan Event 스키마 정규화

---

## 8. 다음 단계

**Phase 2 준비**:
1. Backend 연결: Source/Schema/Resolver 자산을 planner/validator에 통합
2. Trace 강화: stage_inputs, stage_outputs, replan_events 필드 채우기
3. References 강화: tool_calls 기반 자동 생성
4. Frontend 연결: Inspector UI를 실제 trace 데이터로 연결

**시작 조건**: 이 문서 검토 및 승인 후 Phase 2 시작

---

## 부록: 아키텍처 다이어그램

```
Backend Data Flow:
─────────────────
OPS Request
  ↓
router.ask_ci()
  ├─ Load assets: source, schema, resolver
  ├─ planner_llm.create_plan_output() [using prompt asset]
  ├─ validator.validate_plan() [정책 제약 적용]
  └─ Route Decision (Direct/Reject/Plan)
     └─ CIOrchestratorRunner
        ├─ StageExecutor
        │  ├─ route_plan stage
        │  ├─ validate stage
        │  ├─ execute stage
        │  ├─ compose stage
        │  └─ present stage
        └─ Collect: stage_inputs[], stage_outputs[], replan_events[]
  ↓
persist_execution_trace()
  ├─ TbExecutionTrace 생성
  └─ Save: route, stage_inputs, stage_outputs, replan_events
  ↓
Frontend Visualization:
  ├─ InspectorStagePipeline (stages)
  ├─ ReplanTimeline (replan_events)
  └─ Regression analysis (stage comparison)
```

---

**문서 작성 완료**: 2026-01-24 14:45 UTC
