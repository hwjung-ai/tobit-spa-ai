# Phase 3 구현 지시문

## 지시문 요약

**목표**: OPS Orchestration Inspector/Regression 강화를 위한 Phase 3 작업 수행

**기반 문서**: AGENTS.md, OPS_ORCHESTRATION_IMPLEMENTATION_PLAN.md

**우선순위**: Backend → Frontend 순차적 구현

---

## 기본 지침 (AGENTS.md 준수)

**파일 우선 읽기**: 코드 수정/작성 전 관련 파일 먼저 읽기

**기존 패턴 따르기**:
- FastAPI: SQLModel, Pydantic, CRUD 패턴
- Next.js: TypeScript, Tailwind CSS, shadcn/ui
- 컴포넌트 재사용 및 일관성 유지
- 에러 처리: 적절한 HTTP 상태 코드와 예외 처리
- 테스트 포함: 단위 테스트 작성 권장
- 문서 업데이트: 관련 문서 갱신

---

## Phase 3 상세 구현 계획

### Week 5: Inspector Enhancement 작업

#### **Task 3.1: Stage In/Out Panel 구현**

**파일**: `apps/web/src/components/ops/InspectorStagePipeline.tsx` 수정

**내용**:
- 각 stage (route_plan, validate, execute, compose, present)별 collapsible section 추가
- JSON viewer with syntax highlighting 구현
- stage execution metadata 표시 (duration_ms, status, timestamp)
- input/output side-by-side comparison
- diagnostics 표시 (warnings[], errors[], empty_flags{}, counts{})
- large payload 지원 with expand/collapse

**컴포넌트**: `StageInOutPanel.tsx` 신규 생성

#### **Task 3.2: ReplanEvent Timeline 구현**

**파일**: `apps/web/src/components/ops/OpsTimelineTab.tsx` 수정

**내용**:
- horizontal timeline visualization for replan events
- trigger type별 color coding
- scope (execute/compose/present) and decision 표시
- interactive tooltips with event details
- patch diff visualization (side-by-side comparison)
- filter by trigger type and time range

**컴포넌트**: `ReplanTimeline.tsx` 신규 생성

#### **Task 3.3: Asset Override Test UI 구현**

**파일**: `apps/web/src/components/ops/StageCard.tsx` 수정

**내용**:
- test mode toggle in Inspector interface
- asset selection modal with search/filtering
- baseline comparison between current and test runs
- side-by-side diff view of results
- test execution with selected asset overrides

**API 엔드포인트**:
- `POST /inspector/{trace_id}/test-override`
- `GET /assets/{asset_type}/versions`

**컴포넌트**: `AssetOverrideModal.tsx` 신규 생성

### Week 6: Regression Analysis Enhancement 작업

#### **Task 3.4: Stage-level Regression 구현**

**Backend**: `apps/api/app/modules/inspector/regression/` 신규 생성

**내용**:
- `/regression/stage-compare` 엔드포인트 구현
- stage outputs 간 statistical analysis
- performance metrics comparison
- regression score calculation (0-100)
- regression report generator

**Frontend**: `apps/web/src/components/ops/StageDiffViewer.tsx` 신규 생성

#### **Task 3.5: Asset Impact Analysis 구현**

**파일**: `apps/web/src/components/admin/assets/` 확장

**내용**:
- asset version comparison interface
- quality metrics before/after changes
- impact heatmap visualization
- related assets mapping graph
- regression risk assessment

**컴포넌트**: `AssetImpactAnalyzer.tsx` 신규 생성

---

## P0 일관성 사항 반드시 적용

1. **Trigger 정규화**: `safe_parse_trigger()` 함수 사용
2. **Patch 구조**: `ReplanPatchDiff(before, after)` 구조 적용
3. **Naming**: snake_case for internal/API, UPPER for UI
4. **Null 방지**: Pydantic 기본값 + validator 적용
5. **JSON viewer**: 기존 컴포넌트 사용, 새로 생성 금지

---

## 구현 순서 엄격 준수

1. Backend 5개 항목 전체 완료 → Frontend 5개 항목 순차적 구현
2. 각 Task 완료 시 `OPS_ORCHESTRATION_IMPLEMENTATION_PLAN.md` 체크리스트 업데이트
3. 테스트 작성과 병행 진행
4. 기존 코드와의 충돌 없이 통합

---

## 검증 점검 리스트

- [ ] 모든 Backend API 테스트 통과
- [ ] 프론트엔드 라우팅 정상 작동
- [ ] Inspector 기능 완벽히 동작
- [ ] Regression analysis 정확도 검증
- [ ] P0 사항 100% 적용
- [ ] 기존 Phase 1/2 기능에 영향 없음

---

## 최종 요구사항

**완료 시 반드시 수행할 사항**:
1. `OPS_ORCHESTRATION_IMPLEMENTATION_PLAN.md` Phase 3 체크리스트 모두 체크
2. `PHASE_3_IMPLEMENTATION_SUMMARY.md` 문서 생성
3. 모든 기능이 500ms 이내 성능 만족 확인
4. E2E 테스트 통과 확인

이 지시문에 따라 Phase 3를 시작하시오. 각 Task 완료마다 진행 상황 보고할 것.