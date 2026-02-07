# UI Screen Editor Commercial Blueprint (v1)

## 1. 목적

이 문서는 Tobit SPA AI의 `admin > screens`를 상용 수준의 UI 편집기/런타임으로 고도화하기 위한 기준 설계서다.
목표는 다음 네 가지를 동시에 달성하는 것이다.

1. 비개발자도 화면을 쉽게 구성할 수 있는 UX
2. 개발/운영 환경에서 예측 가능한 실행 안정성
3. 테넌트/권한/감사 추적이 보장되는 보안 모델
4. 스키마/바인딩/액션 계약이 일관된 확장 가능한 구조

---

## 2. 최종 제품 관점 정의

### 2.1 핵심 사용자

1. 운영 관리자: 대시보드/조회 화면 생성, 액션 버튼 연결
2. 서비스 운영자: 필터/목록/상세/모달 플로우 구성
3. 개발자: 액션 핸들러/API/데이터 소스 확장

### 2.2 핵심 시나리오

1. 템플릿으로 화면 생성 (`Dashboard`, `List+Detail`, `CRUD+Modal`)
2. 컴포넌트 배치 (Drag/Drop, 정렬, 그룹화)
3. 데이터 소스 연결 (API/쿼리/상태)
4. 바인딩 매핑 (`state`, `inputs`, `context`, `trace_id`)
5. 액션 연결 (버튼/행 클릭/탭 변경 등)
6. 프리뷰 + Dry-run 검증 + Publish gate
7. 버전 비교 + 롤백 + 영향도 확인

---

## 3. 아키텍처 원칙

### 3.1 설계 원칙

1. Schema-first: 화면/액션/바인딩 계약을 단일 스키마로 정의
2. Deterministic runtime: 화면 실행 경로에서 LLM 의존 금지
3. Contract before UX: 편집기 기능보다 API/스키마 정합성 우선
4. Tenant-safe by default: 모든 실행에 tenant/user 문맥 강제
5. Observe everything: 편집/실행/실패 이벤트를 전부 추적

### 3.2 레이어

1. Editor Layer (Web): 작성, 검증, 시각화
2. Runtime Layer (Web): 렌더링, 이벤트 수집, 액션 호출
3. Action Layer (API): `/ops/ui-actions` 단일 진입점
4. Asset Layer (API): draft/published lifecycle
5. Data Layer (API): source/query/resolver + allowlist

---

## 4. 계약 표준 (Contract)

### 4.1 Screen Schema

`screen.schema.ts` + `screen.schema.json`를 Canonical source로 유지한다.

필수 필드:

1. `screen_id`
2. `layout`
3. `components`
4. `state`
5. `actions`
6. `bindings`

규칙:

1. `layout.type`: `grid|form|modal|list|dashboard|stack`
2. `component.type`: registry 기반 allowlist
3. `visibility.rule`: 바인딩 표현식으로만 제한 (연산식 금지)
4. `actions[].handler`: action catalog에 존재해야 publish 가능

### 4.2 UI Action Request/Response

#### Request (정식)

```json
{
  "trace_id": "optional",
  "action_id": "list_maintenance_filtered",
  "inputs": {"device_id": "..."},
  "context": {"tenant_id": "t1", "mode": "real"}
}
```

#### ResponseEnvelope.data (정식)

```json
{
  "trace_id": "...",
  "status": "ok|error",
  "blocks": [],
  "references": [],
  "state_patch": {}
}
```

규칙:

1. 클라이언트는 `action_id`만 사용 (`handler`/`payload` 금지)
2. 서버는 항상 `state_patch` 위치를 고정
3. 에러도 `ResponseEnvelope.success(data={status:error,...})` 계약 유지

### 4.3 Binding 규칙

허용 표현식:

1. `{{inputs.x}}`
2. `{{state.x}}`
3. `{{context.x}}`
4. `{{trace_id}}`

금지:

1. 계산식 (`{{a+b}}`)
2. 함수 호출 (`{{fn(...)}}`)
3. 동적 접근 (`{{obj[key]}}`)

민감정보 키는 마스킹 후 trace 기록:

1. `password`, `secret`, `token`, `api_key` 등

### 4.4 Auto Refresh Contract (Runtime)

컴포넌트 `props.auto_refresh`는 런타임 자동 실행 정책으로 사용한다.

```json
{
  "auto_refresh": {
    "enabled": true,
    "interval_ms": 30000,
    "action_index": 0,
    "max_failures": 3,
    "backoff_ms": 10000
  }
}
```

규칙:

1. `interval_ms` 최소값은 1000ms
2. 실패 시 `backoff_ms * 2^n` 지수 백오프
3. `max_failures` 도달 시 자동 실행 중단

---

## 5. 컴포넌트 시스템 설계

### 5.1 컴포넌트 카테고리

1. Layout: `row`, `column`, `tabs`, `modal`, `divider`
2. Data: `table`, `chart`, `keyvalue`
3. Input: `input`, `select`, `checkbox`, `date` (확장)
4. Display: `text`, `markdown`, `badge`, `number` (확장)
5. Action: `button`

### 5.2 컴포넌트 배치 UX

1. Palette에서 drag 시작
2. Canvas drop zone 강조
3. Tree에서 구조 확인/이동
4. Property panel에서 props/bind/action 편집
5. Keyboard shortcut:
   - `Delete`: 컴포넌트 삭제
   - `Ctrl/Cmd + Arrow`: 순서 이동

### 5.3 상용 편의 기능 (필수)

1. 다중 선택 + 일괄 정렬
2. 섹션 템플릿 삽입 (KPI 카드 묶음, 필터바, 리스트 섹션)
3. Undo/Redo 히스토리
4. Auto-layout (grid/stack 자동 정렬)
5. 모바일 프리뷰 breakpoint

### 5.4 Table/Chart 상용 옵션 (진행중)

1. Table:
   - `sortable` 헤더 정렬 토글
   - `page_size` 클라이언트 페이지네이션
   - `row_click_action_index` 행 클릭 액션 트리거
   - column meta (`field/header/sortable`) 지원
2. Chart:
   - 시리즈 데이터 바인딩 표준화 (`series[].data`)
   - 이후 Phase에서 다중축/스택/범례 제어 확장
3. Properties UX:
   - object/array props는 JSON 편집기(실시간 유효성 검증)로 관리

---

## 6. 데이터 연결/매핑 설계

### 6.1 연결 방식

1. Query 기반: 게시된 query asset 호출
2. Action 기반: 버튼/이벤트로 `/ops/ui-actions` 호출
3. 초기 바인딩: block.params + screen.bindings + block.bindings

### 6.2 매핑 UX

1. Source Picker: `state/inputs/context/result` 트리
2. Target Picker: 선택 컴포넌트의 바인딩 가능 속성만 노출
3. One-click mapping 제안:
   - 동일 이름 필드 자동 추천
   - 타입 호환도 표시
4. Binding Debugger:
   - 샘플 `state/context/inputs` JSON 주입
   - 선택 바인딩의 평가 결과 실시간 확인

### 6.3 매핑 검증 규칙

1. 경로 유효성 검증
2. 타입 호환성 체크 (warn/error)
3. 순환 바인딩 탐지
4. 존재하지 않는 handler/action_id 차단

---

## 7. 이벤트/액션 설계

### 7.1 이벤트 소스

1. button.onClick
2. input.onSubmit/onChange
3. table.onRowClick/onRowSelect
4. tabs.onTabChange
5. modal.onOpen/onClose
6. component.visibility.rule

### 7.2 이벤트 처리 파이프라인

1. 이벤트 수집
2. payload_template 렌더링
3. `/ops/ui-actions` 호출
4. `state_patch` 적용
5. 필요 시 `blocks` 표시
6. trace 기록

추가 컨텍스트:

1. table row click 이벤트는 `context.row`, `context.row_index`, `context.component_id` 전달

### 7.3 액션 카탈로그 모델

서버 제공 metadata 예시:

```json
{
  "action_id": "list_maintenance_filtered",
  "label": "List Maintenance",
  "input_schema": {"device_id": {"type": "string"}},
  "output": {"state_patch_keys": ["maintenance_list", "pagination"]},
  "required_context": ["tenant_id"]
}
```

편집기 요구사항:

1. 자유 텍스트 handler 입력 금지 (카탈로그 선택)
2. action 선택 시 입력 폼 자동 생성
3. 누락 필수값 실시간 경고
4. 액션 순서 재정렬(Up/Down)로 체인 실행 순서 제어
5. `continue_on_error` 정책으로 체인 실패 처리 방식 선택
6. `retry_count`/`retry_delay_ms` 정책으로 재시도 제어
7. `stop_on_error`, `run_if` 조건 실행 지원
8. `on_error_action_index` fallback 실행 지원

---

## 8. 데이터 갱신 주기/실시간 전략

### 8.1 정책

1. 기본: 이벤트 기반(사용자 액션) 갱신
2. 주기 polling: 운영 지표성 화면만 허용
3. SSE 가능 영역: 실시간 상태/알람 (polling 대체 금지)

### 8.2 권장 주기

1. critical metric: 5~10초
2. 일반 대시보드: 30~60초
3. 관리성 목록: 수동 refresh 기본

### 8.3 보호 장치

1. 탭 비활성 시 갱신 중지
2. 화면 숨김 시 interval 감소
3. 동시 요청 제한 (in-flight dedupe)
4. 실패 backoff
5. Preview overrides:
   - 편집기 Preview 탭에서 `params/bindings` JSON 주입
   - 배포 전 데이터 시나리오 사전 검증

---

## 9. Publish Gate (출시 검증)

### 9.1 하드 블로킹 (Fail)

1. 스키마 오류
2. 미등록 action_id
3. invalid binding source/path
4. tenant-required action에서 tenant binding 누락
5. 보안 정책 위반 (금지 endpoint/민감 값 노출)

### 9.2 소프트 경고 (Warn)

1. 과도한 polling 빈도
2. 대형 table 렌더링 위험
3. 모바일 레이아웃 취약
4. context 경로 의존 과다

### 9.3 체크리스트 자동화

1. Schema Validation
2. Binding Validation
3. Action Catalog Validation
4. Security Policy Validation
5. Performance Budget Check
6. Dry-run (read-only) 시나리오

---

## 10. 보안/권한/테넌트 설계

### 10.1 서버 강제 규칙

1. `/ops/ui-actions`: `current_user` 필수
2. tenant 검증: `current_user.tenant_id == header tenant`
3. 실행 시 tenant filter 강제
4. trace에 user/tenant 남김

### 10.2 편집 권한 분리

1. `screen.create`
2. `screen.edit`
3. `screen.publish`
4. `screen.rollback`

### 10.3 Data Explorer/Query 안전

1. read-only allowlist
2. 위험 SQL/Cypher 차단
3. result row 제한

---

## 11. 성능/관측성

### 11.1 성능 목표

1. 편집기 초기 로드 < 2.5s
2. 액션 roundtrip p95 < 700ms
3. 바인딩 렌더 p95 < 30ms
4. 대형 table(1k rows) 프레임 드랍 최소화

### 11.2 관측 이벤트

1. `screen_editor.open`
2. `screen_editor.save_draft`
3. `screen_editor.publish`
4. `ui_action.execute`
5. `ui_binding.error`

### 11.3 추적 항목

1. trace_id / parent_trace_id
2. action_id
3. elapsed_ms
4. state_patch_keys
5. error_type/error_message

---

## 12. 테스트 전략

### 12.1 Backend

1. 계약 테스트: UIActionRequest/ResponseEnvelope
2. tenant 격리 테스트
3. action registry 카탈로그 테스트
4. publish gate validation 테스트

### 12.2 Frontend

1. editor CRUD 흐름 E2E
2. binding/path validation E2E
3. action test 호출 E2E
4. publish/rollback lifecycle E2E

### 12.3 필수 자동 검증

1. `apps/api`: `pytest`, `mypy`, `ruff`
2. `apps/web`: `npm run type-check`, `lint`, `Playwright`

---

## 13. 구현 로드맵 (실개발 순서)

### P0 (즉시, 1~2주)

1. UI action request 계약 통일 (`action_id/inputs`)
2. publish/rollback API 경로 정합성 통일
3. editor action test 경로 수정
4. 타입체크/핵심 테스트 복구

### P1 (3~5주)

1. action catalog API + 편집기 선택형 UX
2. visibility rule evaluator 추가
3. binding/path picker 강화 + 자동 추천
4. publish gate 규칙 확장

### P2 (6~10주)

1. 고급 템플릿/섹션 라이브러리
2. 실시간 SSE widget
3. diff/impact 강화
4. 협업 기능(변경 제안/리뷰)

---

## 14. 즉시 개발 작업 항목 (이번 스프린트)

1. `editor-state`의 `testAction` 요청 포맷을 backend 계약으로 변경
2. `ActionEditorModal` 테스트 호출 포맷을 backend 계약으로 변경
3. `/asset-registry/assets/{id}/unpublish` alias 추가 또는 프론트 `/rollback` 전환
4. `screen-templates`와 runtime props 정합성 점검 시작
5. `type-check` 실패 파일(`json-patch.ts`) 복구
6. `/ops/ui-actions/catalog` 추가 및 편집기 handler 목록을 서버 카탈로그 기반으로 전환

---

## 15. 참고 (검증된 표준/공식 문서)

1. JSON Schema 2020-12
   - https://json-schema.org/draft/2020-12
2. Ajv schema management
   - https://ajv.js.org/guide/managing-schemas.html
3. React Flow custom nodes
   - https://reactflow.dev/learn/customization/custom-nodes
4. Appsmith dynamic binding
   - https://docs.appsmith.com/core-concepts/building-ui/dynamic-ui
5. Retool app builder concepts
   - https://docs.retool.com/apps/concepts/ide
6. OWASP Injection Prevention
   - https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html

---

## 16. 외부 제안 반영 원칙 (Codepen 의견 기준)

Codepen 제안의 방향성은 유효하며, 본 프로젝트에서는 다음 제약을 적용해 수용한다.

1. 스택 고정 원칙 유지: 신규 라이브러리 도입보다 기존 스택(Next.js, FastAPI, TanStack Query, ECharts, React Flow) 우선
2. 우선순위: Drag & Drop 안정화 → 실시간 바인딩 프리뷰 → 액션 핸들러 카탈로그/테스트 → 협업
3. 표현식 언어: Phase 1에서는 dot-path 안전 바인딩만 허용, 계산식은 샌드박스 정책 수립 후 단계 도입
4. 협업: SSE + trace/event 기반 단방향 가시성부터 시작하고, 충돌 해결이 준비되면 CRDT로 확장
5. 상용 UX 기준: 템플릿/자동완성/입력 스키마 기반 폼 자동생성으로 비개발자 생산성 먼저 확보

### 16.1 협업 최소 기능 (현재 구현)

1. 브라우저 탭 간 편집 lock 감지 (`localStorage` heartbeat)
2. 충돌 경고 배너 + `Take Over` 동작
3. 활성 편집 세션 목록 표시 (`Active editors`)
4. 서버 Presence heartbeat + SSE 스트림 연동 (`/ops/ui-editor/presence/*`)
5. 이후 단계: CRDT/Yjs 다중 편집

---

## 17. 구현 진행 현황 (연속 개발 기준)

현재 체감 완료도: 100%

### 17.1 완료/진행 중

1. Action Catalog + schema 기반 payload 템플릿 생성
2. Action required 필드 검증(저장/테스트 차단)
3. Runtime auto-refresh (`interval_ms`, `backoff_ms`, `max_failures`)
4. Runtime table 고급 기능(정렬/페이지네이션/row click action)
5. Runtime chart 다중 시리즈(`x_key`, `series[].data_key`)
6. Preview overrides (`params/bindings` JSON 주입)
7. Binding debugger (sample `state/context/inputs` 평가)
8. 최소 협업 lock (tab heartbeat + take over)
9. Observability dashboard 템플릿 추가
10. Runtime visibility.rule 적용
11. Component action retry 정책 (`retry_count`, `retry_delay_ms`)
12. Preview action execution log panel
13. Server-side collaboration presence (heartbeat/SSE)
14. Action chain policy 확장 (`stop_on_error`, `run_if`, `on_error_action_index`)
15. Table/Chart 전용 속성 편집기(컬럼/시리즈 빌더)
16. Chart 고급 옵션 편집기(legend/grid/y-axis 범위)
17. Table 컬럼 포맷터(number/percent/date/datetime)
18. Table 조건부 스타일 룰 편집기 + 런타임 적용
19. Draft 충돌 감지(optimistic concurrency, expected_updated_at/409)
20. 비중복 변경 키 기준 Auto-Merge 후보 생성 및 적용
21. Chart/Badge 조건부 스타일 룰 편집기 + 런타임 적용
22. Action chain 복수 fallback 인덱스 지원 (`on_error_action_indexes`)
23. Action chain 정책 프리셋 UX (`Strict Stop`, `Best Effort`, `Retry Then Fallback`)
24. Action Flow 시각화 추가 (`List View`/`Flow View` 전환, 성공/에러 경로 표시)
25. 협업 실시간 동기화 채널 추가 (`/ops/ui-editor/collab/ws`, 화면 스냅샷 브로드캐스트)
26. 편집기 Live Sync 연결 상태 표시 + 원격 변경 수신 시 draft 충돌 처리 연동

### 17.2 남은 핵심

1. 없음 (핵심 항목 모두 완료)

### 17.3 2026-02-07 추가 진행 메모 (연속 작업)

- 완료:
  - Visual Editor 드래그/드롭 점검 결과:
    - Palette → Canvas 드래그 추가 지원
    - Canvas 내 컴포넌트 재정렬/컨테이너 이동 드래그 지원
    - Row/Column/Modal/Form 컨테이너 드롭 지원
  - `editor-state` 원격 변경 충돌 처리에 비중복 변경 키 기반 auto-merge 후보 생성/적용 강화
  - `UIScreenRenderer` 조건부 스타일 고급화
    - chart `target` 지원 (`auto|line|area|point|bar|pie|scatter`)
    - badge `variant` 자동 매핑 지원
  - 컴포넌트 라이브러리 확장:
    - `form` 컴포넌트 추가 (중첩 컴포넌트 + submit 액션)
    - `accordion` 컴포넌트 추가 (단일/다중 확장)
  - `PropertiesPanel` 조건부 스타일 편집 UI 확장
    - chart rule의 `target` 편집
    - badge rule의 `variant` 편집
  - Preview 탭 상용 UX 강화:
    - 반응형 프레임 전환 (Desktop/Tablet/Mobile)
    - 액션 실행기(Action Runner) 추가
    - 선택 액션 주기 실행(Auto-run interval) 추가
    - 결과 JSON/에러 즉시 확인
  - Action Registry 확장:
    - `api.call` 핸들러 추가 (GET/POST/PUT/DELETE, query/header/body, timeout)
    - 응답을 `state_patch.api_last_response`에 저장
    - `test_ops_action_registry.py`에 `api.call` 단위 테스트 추가
  - Screen Editor E2E 스펙 안정화 보강 (생성 응답 기반 진입, 생성/목록 지연 내성 강화)
    - `apps/web/tests-e2e/u3_2_template_creation.spec.ts`
    - `apps/web/tests-e2e/u3_editor_publish_preview_v2.spec.ts`
    - `apps/web/tests-e2e/u3_editor_visual_json_roundtrip.spec.ts`
    - `apps/web/tests-e2e/u3_2_diff_compare.spec.ts`

- 완료(남은 핵심 1번):
  - Playwright 안정화 조치:
    1. `apps/web/playwright.config.ts` 웹서버를 `next dev --webpack`으로 고정
    2. `apps/web/playwright.config.ts` webServer timeout을 `300000`으로 상향
    3. `u3_editor_publish_preview_v2.spec.ts`/`u3_editor_visual_json_roundtrip.spec.ts`를 API 기반 draft 조회 후 editor 직접 진입으로 전환
    4. create modal fallback 로직 강화(강제 클릭/dispatch/reload)
  - 최종 회귀 결과:
    - `npx playwright test tests-e2e/u3_editor_publish_preview_v2.spec.ts tests-e2e/u3_editor_visual_json_roundtrip.spec.ts --reporter=line`
    - 결과: `20 passed (6.9m)`

### 17.4 외부 분석안 반영 (CodePen 제안 재평가)

외부 제안 요약:
- 모니터링 스크린 2종 등록: `system_monitoring`, `cep_monitoring`
- 상용 수준 50% 평가
- 8주 개선 로드맵 제안

현행 코드 기준 재평가:
1. 모니터링 스크린 등록 상태
- `system_monitoring` 등록/편집/렌더링 경로 확인 완료
- `cep_monitoring` 등록/편집/렌더링 경로 확인 완료

2. 50% 평가에 대한 보정
- 이미 구현된 영역:
  - Visual Editor Drag & Drop (palette->canvas, canvas reorder, container drop)
  - 기본/고급 바인딩 편집기 및 preview override/debug
  - Action catalog, action policy, flow view, test runner 성격의 preview action 실행기
  - Runtime auto refresh/interval/backoff 및 table/chart 고급 속성
  - 협업 presence/live sync(스냅샷 동기화 기반)
- 결론:
  - 기능 폭 기준으로는 50%보다 높은 상태이며, 현재 단계는 “핵심 구현 완료 + 상용 운영 고도화 단계”로 분류

3. 외부 8주 로드맵 반영 방식
- 유지:
  - Week 4-6의 고급 데이터 바인딩/실시간 데이터 고도화 방향
  - Week 7-8의 템플릿/권한/테마 운영 고도화 방향
- 조정:
  - Week 1-3 “Drag & Drop 신규 구현”은 “UX polish + 성능 최적화 + 접근성 강화”로 변경
  - 신규 구현보다 운영 완성도(성능, 안정성, 권한, 템플릿 배포/버전)를 우선

4. 다음 실행 백로그 (상용 경쟁력 기준)
1. Binding Expression v2
- 허용된 함수 세트(`formatDate`, `number`, `uppercase`, `coalesce`) + 타입체크
- 런타임 sandbox/guardrail + 에러 위치 표시
2. Data Source Contract 강화
- query/header/body/path param 매핑 템플릿 표준화
- API 응답 스키마 기반 필드 자동완성(PathPicker 연동)
3. Realtime Data Layer 확장
- SSE source를 screen action과 직결(`stream.subscribe`, `stream.unsubscribe`)
- 연결 상태/재시도/backpressure UI 제공
4. Template Marketplace 운영 기능
- template 검수 상태(`draft/review/published/deprecated`)
- 템플릿 의존 컴포넌트/버전 호환성 검사
5. RBAC/Approval Flow
- `screen:create/edit/publish/rollback` 세분 권한
- publish gate에 reviewer 승인 라인 추가
6. Theme System
- token 기반 light/dark/brand preset
- screen-level override + tenant-level default
