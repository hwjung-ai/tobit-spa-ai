# UI Screen Editor Commercial Blueprint (v2 Final)

> 최종 업데이트: 2026-02-08
> 상용 준비도: **95%** (단일 사용자 편집 기준 Production Ready)

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
3. Action Layer (API): `/ops/ui-actions` 단일 진입점 + Direct API endpoint 모드
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

#### 모드 1: Standard Action (via `/ops/ui-actions`)

```json
{
  "trace_id": "optional",
  "action_id": "list_maintenance_filtered",
  "inputs": {"device_id": "..."},
  "context": {"tenant_id": "t1", "mode": "real"}
}
```

#### 모드 2: Direct API Endpoint (via `action.endpoint`)

```json
{
  "endpoint": "/admin/system/health",
  "method": "GET",
  "response_mapping": {
    "cpu_usage": "health.resource.cpu_percent",
    "memory_usage": "health.resource.memory_percent"
  }
}
```

Direct API 모드는 Screen Editor에서 사용자가 기존 REST API를 자유롭게 호출할 수 있게 한다.
`response_mapping`으로 API 응답의 중첩 경로를 screen state 키에 매핑한다.

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

1. Standard 모드: 클라이언트는 `action_id`만 사용 (`handler`/`payload` 금지)
2. Direct API 모드: `endpoint` + `method` + `response_mapping` 조합 사용
3. 서버는 항상 `state_patch` 위치를 고정
4. 에러도 `ResponseEnvelope.success(data={status:error,...})` 계약 유지

### 4.3 Binding 규칙

허용 표현식 (v2 - Advanced Expression Engine):

1. `{{inputs.x}}` - 사용자 입력 참조
2. `{{state.x}}` - 화면 상태 참조
3. `{{context.x}}` - 실행 컨텍스트 참조
4. `{{trace_id}}` - 추적 ID
5. `{{sum(state.items, 'value')}}` - 안전한 함수 호출
6. `{{state.count > 10 ? 'high' : 'low'}}` - 삼항 연산자
7. `{{formatDate(state.date, 'YYYY-MM-DD')}}` - 포맷 함수
8. 산술/비교/논리 연산: `+`, `-`, `*`, `/`, `%`, `>`, `>=`, `<`, `<=`, `==`, `!=`, `&&`, `||`, `!`
9. 배열 리터럴: `[1, 2, 3]`

안전 제한:

1. 화이트리스트 함수만 허용 (`SAFE_FUNCTIONS` in `safe-functions.ts`)
2. AST 깊이 제한 (최대 10), 토큰 수 제한 (보안)
3. 배열 원소 10,000개 제한
4. 동적 코드 실행 (`eval`, `Function`) 금지

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

### 5.1 컴포넌트 카테고리 (15종 완성)

1. Layout: `row`, `column`, `tabs`, `modal`, `divider`, `accordion`
2. Data: `table`, `chart`, `keyvalue`
3. Input: `input`, `select`, `checkbox`, `form`
4. Display: `text`, `markdown`, `badge`, `image`
5. Action: `button`

### 5.2 컴포넌트 배치 UX

1. Palette에서 drag 시작
2. Canvas drop zone 강조
3. Tree에서 구조 확인/이동
4. Property panel에서 props/bind/action 편집
5. Keyboard shortcut:
   - `Delete`: 컴포넌트 삭제
   - `Ctrl+Z`/`Ctrl+Shift+Z`: Undo/Redo
   - `Ctrl+C`/`Ctrl+X`/`Ctrl+V`: Copy/Cut/Paste
   - `Ctrl+D`: Duplicate
   - `Ctrl+A`: Select All
   - `Escape`: Deselect
   - `Ctrl/Cmd + Arrow`: 순서 이동

### 5.3 상용 편의 기능 (완료)

1. 다중 선택 + 일괄 삭제/이동 (Ctrl+Click 토글, Shift+Click 범위 선택)
2. 섹션 템플릿 삽입 (KPI 카드 묶음, 필터바, 리스트 섹션)
3. Undo/Redo 히스토리 (50단계, `mutateWithHistory` 래퍼)
4. Clipboard 지원 (깊은 복제 + ID 재생성)
5. 모바일 프리뷰 breakpoint (Desktop/Tablet/Mobile)

### 5.4 Table/Chart 상용 옵션 (완료)

1. Table:
   - `sortable` 헤더 정렬 토글
   - `page_size` 클라이언트 페이지네이션
   - `row_click_action_index` 행 클릭 액션 트리거
   - column meta (`field/header/sortable`) 지원
   - 컬럼 포맷터 (`number/percent/date/datetime`)
   - 조건부 스타일 룰 편집기 + 런타임 적용
2. Chart:
   - 시리즈 데이터 바인딩 표준화 (`series[].data_key`)
   - 다중축/범례/grid/y-axis 범위 편집기
   - 조건부 스타일 `target` 지원 (`auto|line|area|point|bar|pie|scatter`)
3. Badge:
   - 조건부 `variant` 자동 매핑
4. Properties UX:
   - object/array props는 JSON 편집기(실시간 유효성 검증)로 관리

---

## 6. 데이터 연결/매핑 설계

### 6.1 연결 방식

1. Query 기반: 게시된 query asset 호출
2. Action 기반: 버튼/이벤트로 `/ops/ui-actions` 호출
3. Direct API 기반: `action.endpoint`로 기존 REST API 직접 호출 + `response_mapping` 적용
4. 초기 바인딩: block.params + screen.bindings + block.bindings

### 6.2 매핑 UX

1. Source Picker: `state/inputs/context/result` 트리
2. Target Picker: 선택 컴포넌트의 바인딩 가능 속성만 노출
3. One-click mapping 제안:
   - 동일 이름 필드 자동 추천
   - 타입 호환도 표시
4. Binding Debugger:
   - 샘플 `state/context/inputs` JSON 주입
   - 선택 바인딩의 평가 결과 실시간 확인
   - 표현식 에러 위치 표시

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
2. payload_template 렌더링 (Expression Engine v2)
3. 라우팅 분기:
   - `action.endpoint` 존재 시 → Direct API 호출
   - 그 외 → `/ops/ui-actions` 호출
4. `response_mapping` 또는 `state_patch` 적용
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
8. `on_error_action_index` / `on_error_action_indexes` fallback 실행 지원
9. Action Flow 시각화 (`List View`/`Flow View` 전환, 성공/에러 경로 표시)
10. 정책 프리셋 UX (`Strict Stop`, `Best Effort`, `Retry Then Fallback`)

### 7.4 내장 액션 핸들러 (Action Registry)

| Handler | 설명 |
|---------|------|
| `state.set` | 단일 상태 키 설정 |
| `state.merge` | 상태 병합 |
| `nav.go_to` | 화면 이동 |
| `api.call` | 외부 API 호출 (GET/POST/PUT/DELETE, query/header/body, timeout) |
| `workflow.run` | 워크플로우 실행 |
| `form.submit` | 폼 제출 |
| `fetch_device_detail` | 장비 상세 조회 |
| `list_maintenance_filtered` | 유지보수 필터 목록 |
| `create_maintenance_ticket` | 유지보수 티켓 생성 |
| `open_maintenance_modal` | 유지보수 모달 열기 |
| `close_maintenance_modal` | 유지보수 모달 닫기 |

---

## 8. 데이터 갱신 주기/실시간 전략

### 8.1 정책

1. 기본: 이벤트 기반(사용자 액션) 갱신
2. 주기 polling: 운영 지표성 화면만 허용
3. SSE 스트리밍: 실시간 상태/알람 (StreamManager 기반)

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

### 8.4 SSE Real-time Data Binding (완료)

1. `stream-binding.ts`: StreamManager (EventSource 관리, 자동 재연결, 백프레셔)
2. `stream.subscribe`/`stream.unsubscribe` 액션 타입
3. UIScreenRenderer 통합: 스트림 라이프사이클 관리, 상태 자동 업데이트
4. 연결 상태 표시기 (Connected/Reconnecting/Error)

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

### 10.2 편집 권한 분리 (RBAC 완료)

1. `screen:create` - 화면 생성
2. `screen:edit` - 화면 편집
3. `screen:publish` - 화면 배포
4. `screen:rollback` - 배포 롤백
5. `screen:delete` - 화면 삭제

권한 적용 위치:
- Backend: `asset_registry/router.py` 각 엔드포인트에 `ResourcePermission` 체크
- Frontend: 역할 기반 버튼/메뉴 노출 제어

### 10.3 Data Explorer/Query 안전

1. read-only allowlist
2. 위험 SQL/Cypher 차단
3. result row 제한

---

## 11. 테마 시스템 (완료)

### 11.1 Design Tokens

- `design-tokens.ts`: light/dark/brand 프리셋
- CSS 변수 기반, Tailwind 연동
- `tokensToCSSVariables()` 자동 변환

### 11.2 ThemeProvider

- `ThemeContext.tsx`: React 컨텍스트
- localStorage 저장 (`tobit-theme-preset`)
- 헤더 토글 UI
- `data-theme` 속성 자동 설정

### 11.3 Screen-Level Override

- `screen.schema.ts`에 `theme` 필드 추가
- 개별 화면이 전역 테마를 오버라이드 가능
- tenant-level default 지원

---

## 12. 성능/관측성

### 12.1 성능 목표

1. 편집기 초기 로드 < 2.5s
2. 액션 roundtrip p95 < 700ms
3. 바인딩 렌더 p95 < 30ms
4. 대형 table(1k rows) 프레임 드랍 최소화

### 12.2 관측 이벤트

1. `screen_editor.open`
2. `screen_editor.save_draft`
3. `screen_editor.publish`
4. `ui_action.execute`
5. `ui_binding.error`

### 12.3 추적 항목

1. trace_id / parent_trace_id
2. action_id
3. elapsed_ms
4. state_patch_keys
5. error_type/error_message

---

## 13. 테스트 전략

### 13.1 Backend

1. 계약 테스트: UIActionRequest/ResponseEnvelope
2. tenant 격리 테스트
3. action registry 카탈로그 테스트 (`test_ops_action_registry.py`)
4. publish gate validation 테스트
5. `api.call` 핸들러 단위 테스트

### 13.2 Frontend

1. editor CRUD 흐름 E2E
2. binding/path validation E2E
3. action test 호출 E2E
4. publish/rollback lifecycle E2E
5. Visual-JSON roundtrip E2E
6. Template creation E2E
7. Diff compare E2E

### 13.3 필수 자동 검증

1. `apps/api`: `pytest`, `mypy`, `ruff`
2. `apps/web`: `npm run type-check`, `lint`, `Playwright`

### 13.4 E2E 테스트 현황 (Playwright)

| 스펙 파일 | 상태 | 설명 |
|-----------|------|------|
| `u3_editor_publish_preview_v2.spec.ts` | Pass | 발행/프리뷰 라이프사이클 |
| `u3_editor_visual_json_roundtrip.spec.ts` | Pass | 비주얼↔JSON 동기화 |
| `u3_2_template_creation.spec.ts` | Pass | 템플릿 생성/복제 |
| `u3_2_diff_compare.spec.ts` | Pass | 버전 비교 |
| `u3_2_publish_gate.spec.ts` | Pass | 배포 게이트 검증 |

최종 회귀 결과: `20 passed (6.9m)`

---

## 14. 구현 완료 현황 (최종)

### 14.1 Phase 1: UX Polish (100% 완료)

| 항목 | 상태 | 상세 |
|------|------|------|
| Undo/Redo | 완료 | 50단계 히스토리, `mutateWithHistory()` 래퍼 |
| Multi-Select | 완료 | Ctrl+Click 토글, Shift+Click 범위 선택 |
| Copy/Paste | 완료 | 깊은 복제 + ID 재생성, Cut/Duplicate 지원 |
| 단축키 | 완료 | Ctrl+Z/Shift+Z, Ctrl+A, Escape, Ctrl+C/X/V/D, Delete |

### 14.2 Phase 2: Advanced Binding Expressions (100% 완료)

| 항목 | 상태 | 상세 |
|------|------|------|
| Expression Parser | 완료 | 토크나이저 + 재귀 하강 파서 → AST |
| Safe Functions | 완료 | 화이트리스트 함수 (string/number/date/collection/utility) |
| Expression Evaluator | 완료 | AST 평가 (깊이 10, 배열 10000 제한) |
| Binding Engine 통합 | 완료 | 기존 dot-path 100% 호환, 표현식 자동 감지 |

### 14.3 Phase 3: Theme System (100% 완료)

| 항목 | 상태 | 상세 |
|------|------|------|
| Design Tokens | 완료 | light/dark/brand 프리셋 |
| ThemeProvider | 완료 | React 컨텍스트, localStorage 저장 |
| Screen-Level Override | 완료 | schema에 `theme` 필드 추가 |

### 14.4 Phase 4: RBAC + Template Gallery (100% 완료)

| 항목 | 상태 | 상세 |
|------|------|------|
| Screen Permissions | 완료 | screen:create/edit/publish/rollback/delete |
| Template Gallery | 완료 | 태그 기반 필터링, 게시된 스크린 복제 |
| Draft/Publish Workflow | 완료 | 충돌 감지, Auto-merge, Rollback |

### 14.5 Phase 5: SSE Real-time Data Binding (100% 완료)

| 항목 | 상태 | 상세 |
|------|------|------|
| StreamManager | 완료 | EventSource 관리, 재연결, 백프레셔 |
| UIScreenRenderer 통합 | 완료 | 스트림 라이프사이클, 상태 자동 업데이트 |
| 연결 상태 표시 | 완료 | Connected/Reconnecting/Error 인디케이터 |

### 14.6 추가 완료 항목

| 항목 | 상태 | 상세 |
|------|------|------|
| Direct API Endpoint | 완료 | `action.endpoint` + `response_mapping`으로 기존 REST API 직접 호출 |
| Monitoring Screens | 완료 | `system_monitoring`, `cep_monitoring` 2종 (Direct API 방식) |
| Action Flow Visualizer | 완료 | List/Flow View 전환, 성공/에러 경로 표시 |
| Action Chain Policy | 완료 | Strict Stop, Best Effort, Retry Then Fallback 프리셋 |
| Conditional Styles | 완료 | Table, Chart, Badge 조건부 스타일 편집기 + 런타임 |
| `api.call` Handler | 완료 | GET/POST/PUT/DELETE, query/header/body, timeout |
| Collaboration Presence | 완료 | 서버 heartbeat + SSE 스트림, 편집 lock 감지 |

---

## 15. 외부 제안 반영 (CodePen 의견 최종 평가)

### 15.1 Codepen 원래 평가 및 대응

Codepen은 Screen Editor를 **상용 수준 50%**로 평가하고 8주 개선 로드맵을 제안했다.

**보정된 평가: 95% (단일 사용자 편집 기준)**

Codepen 평가 시점 이후 5개 Phase 구현이 완료되었으며, 실제 코드 기반 점검 결과 50% 평가는 구현 전 상태에 대한 것이었다.

### 15.2 Codepen 제안별 대응 현황

| Codepen 제안 | 대응 | 상태 |
|-------------|------|------|
| **Week 1-3: Drag & Drop 구현** | 이미 구현 완료 → UX polish + 성능 최적화로 변경 | 완료 |
| **Week 4-6: 고급 데이터 바인딩** | Expression Parser v2, Safe Functions, 표현식 평가기 | 완료 |
| **Week 7-8: 템플릿/권한/테마** | Template Gallery, RBAC, Theme System | 완료 |
| **모니터링 스크린 2종 등록** | Direct API Endpoint 방식으로 재작성 | 완료 |
| **실시간 협업 (CRDT)** | Presence 기반 기본 협업 구현, CRDT는 미래 과제 | 부분 |
| **AI Copilot** | 미구현 (미래 과제) | 미구현 |

### 15.3 Codepen 방향성 수용 원칙

1. 스택 고정 원칙 유지: 신규 라이브러리 도입보다 기존 스택(Next.js, FastAPI, TanStack Query, ECharts, React Flow) 우선
2. 우선순위: Drag & Drop 안정화 → 실시간 바인딩 프리뷰 → 액션 핸들러 카탈로그/테스트 → 협업
3. 표현식 언어: 안전한 파서/평가기 기반 화이트리스트 함수 세트 완성 (Phase 2에서 해결)
4. 협업: SSE + trace/event 기반 단방향 가시성 + Presence 기반 lock 구현, CRDT는 이후 확장
5. 상용 UX 기준: 템플릿/자동완성/입력 스키마 기반 폼 자동생성으로 비개발자 생산성 확보

---

## 16. 최종 완성도 종합 (2026-02-08)

### 16.1 기능별 완료도

| 카테고리 | 완료도 | 비고 |
|---------|--------|------|
| 컴포넌트 시스템 (15종) | 100% | text, button, table, chart, keyvalue, input, select, checkbox, image, badge, row, column, tabs, accordion, modal, form, markdown, divider |
| Drag & Drop 편집 | 100% | Palette→Canvas, 재정렬, 컨테이너 중첩 |
| 상태 관리 (Undo/Redo/Clipboard) | 100% | 50단계, Multi-Select, Copy/Cut/Paste/Duplicate |
| Advanced Binding Engine | 100% | Expression Parser + Safe Functions + Evaluator |
| Action System | 100% | Catalog, Chain, Policy, Flow View, Direct API |
| Draft/Publish/Rollback | 100% | 충돌 감지, Auto-merge, 버전 비교 |
| Template Gallery | 100% | 태그 필터링, 복제, 검색 |
| RBAC 권한 | 100% | screen:create/edit/publish/rollback/delete |
| Theme System | 100% | Light/Dark/Brand, Screen Override |
| SSE Streaming | 100% | StreamManager, 자동 재연결, 백프레셔 |
| Auto Refresh | 100% | interval, backoff, max_failures |
| Direct API Endpoint | 100% | endpoint + response_mapping |
| Monitoring Screens | 100% | system_monitoring, cep_monitoring |
| Preview & Debug | 100% | Mock Data, 반응형 뷰포트, Action Runner |
| E2E 테스트 | 100% | 5개 스펙, 20 테스트 통과 |
| 실시간 협업 (Multi-user) | 30% | Presence lock 기본, CRDT 미연동 |
| 접근성 (a11y) | 10% | 기본 HTML 시맨틱만, ARIA 미검증 |
| AI Copilot | 0% | 미래 과제 |

### 16.2 강점

1. **15종 컴포넌트 + 완전한 Drag & Drop**: 컨테이너 중첩, 순서 변경, 속성 편집
2. **강력한 Expression Engine**: 안전한 파서/평가기, 화이트리스트 함수, AST 기반
3. **유연한 데이터 연결**: Action Registry + Direct API Endpoint 이중 모드
4. **상용 편집 UX**: Undo/Redo, Clipboard, Multi-Select, 키보드 단축키
5. **완전한 배포 라이프사이클**: Draft, Publish, Rollback, 충돌 감지, Auto-merge
6. **RBAC + Theme + Template**: 권한/테마/템플릿 3종 세트 완비
7. **실시간 데이터**: SSE StreamManager + Auto Refresh + Direct API polling

### 16.3 개선 가능 영역 (Optional / Future)

| 항목 | 우선순위 | 예상 규모 | 설명 |
|------|----------|----------|------|
| 실시간 협업 (CRDT) | 중 | 3-5일 | WebSocket/CRDT 기반 동시 편집 (현재는 Presence lock) |
| 기본 템플릿 DB 시딩 | 낮 | 0.5일 | monitoring 스크린 2종 DB 자동 등록 스크립트 |
| 네트워크 요청 모니터링 | 낮 | 1-2일 | API 호출 로그 탭 (요청/응답 상세) |
| 권한 에러 UX | 낮 | 0.5일 | 권한 부족 시 사용자 피드백 UI 개선 |
| 접근성 (a11y) | 낮 | 2-3일 | ARIA 속성, 키보드 네비게이션, 스크린리더 테스트 |
| AI Copilot | 미래 | 5-7일 | 자연어 UI 생성, 코드 제안, AI 최적화 |

---

## 17. 구현 이력 (연대기)

### 17.1 Phase 0: 기본 구현 (Codex)

- Screen Editor 기본 골격 구현
- 컴포넌트 팔레트, 캔버스, 속성 패널
- JSON 편집기, 기본 프리뷰

### 17.2 Phase 1-5: 상용 고도화 (커밋: 8cb64b7)

- Phase 1: UX Polish (Undo/Redo, Multi-Select, Copy/Paste, 단축키)
- Phase 2: Advanced Binding Expressions (Parser, Evaluator, Safe Functions)
- Phase 3: Theme System (Design Tokens, ThemeProvider, Screen Override)
- Phase 4: RBAC + Template Gallery (Permissions, Templates)
- Phase 5: SSE Real-time Data Binding (StreamManager, Stream Actions)

### 17.3 Monitoring Screen 수정

- 문제: monitoring 스크린 2종이 미등록 action handler 참조로 에러 발생
- 잘못된 접근: Backend에 hardcoded handler 추가 → **사용자 거부** (Screen Editor 철학 위반)
- 올바른 해결: UIScreenRenderer에 `endpoint` + `response_mapping` Direct API 모드 추가
- 스크린 JSON을 기존 REST API (`/admin/system/*`, `/cep/*`) 직접 호출 방식으로 재작성

### 17.4 기타 안정화

- Playwright E2E 안정화 (웹서버 설정, timeout, API 기반 진입)
- Action Registry `api.call` 핸들러 추가
- Preview 탭 상용 UX 강화 (반응형, Auto-run, Action Runner)
- Table/Chart 조건부 스타일 고급화
- Draft 충돌 감지 및 Auto-merge

---

## 18. 참고 (검증된 표준/공식 문서)

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

## 19. 주요 파일 맵

### 19.1 Frontend (Editor)

| 파일 | 역할 |
|------|------|
| `apps/web/src/lib/ui-screen/editor-state.ts` | Zustand 상태 관리 (핵심) |
| `apps/web/src/lib/ui-screen/screen.schema.ts` | ScreenSchemaV1 타입 정의 |
| `apps/web/src/lib/ui-screen/component-registry.ts` | 15종 컴포넌트 레지스트리 |
| `apps/web/src/lib/ui-screen/expression-parser.ts` | 표현식 파서 (AST) |
| `apps/web/src/lib/ui-screen/expression-evaluator.ts` | 표현식 평가기 |
| `apps/web/src/lib/ui-screen/safe-functions.ts` | 화이트리스트 함수 |
| `apps/web/src/lib/ui-screen/validation-utils.ts` | 스키마 검증 유틸 |
| `apps/web/src/lib/ui-screen/design-tokens.ts` | 테마 디자인 토큰 |
| `apps/web/src/lib/ui-screen/stream-binding.ts` | SSE StreamManager |
| `apps/web/src/contexts/ThemeContext.tsx` | 테마 프로바이더 |
| `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx` | 편집기 메인 |
| `apps/web/src/components/admin/screen-editor/visual/CanvasComponent.tsx` | 캔버스 컴포넌트 |
| `apps/web/src/components/admin/screen-editor/visual/ComponentPalette.tsx` | 팔레트 |
| `apps/web/src/components/admin/screen-editor/visual/PropertiesPanel.tsx` | 속성 패널 |
| `apps/web/src/components/admin/screen-editor/actions/ActionTab.tsx` | 액션 탭 |
| `apps/web/src/components/admin/screen-editor/actions/ActionFlowVisualizer.tsx` | 액션 흐름 시각화 |
| `apps/web/src/components/admin/screen-editor/binding/BindingTab.tsx` | 바인딩 탭 |
| `apps/web/src/components/admin/screen-editor/preview/PreviewTab.tsx` | 프리뷰 탭 |
| `apps/web/src/components/admin/screen-editor/templates/TemplateGallery.tsx` | 템플릿 갤러리 |

### 19.2 Frontend (Runtime)

| 파일 | 역할 |
|------|------|
| `apps/web/src/components/answer/UIScreenRenderer.tsx` | 스크린 렌더러 (핵심) |

### 19.3 Backend

| 파일 | 역할 |
|------|------|
| `apps/api/app/modules/ops/services/action_registry.py` | 액션 핸들러 레지스트리 |
| `apps/api/app/modules/ops/services/ui_actions.py` | 액션 실행 서비스 |
| `apps/api/app/modules/ops/services/binding_engine.py` | 서버사이드 바인딩 엔진 |
| `apps/api/app/modules/ops/routes/ui_actions.py` | `/ops/ui-actions` 라우트 |
| `apps/api/app/modules/asset_registry/router.py` | Asset CRUD + 권한 |
| `apps/api/app/modules/asset_registry/schemas.py` | Asset 스키마 |
| `apps/api/app/modules/permissions/models.py` | ResourcePermission 열거형 |

### 19.4 Screen Assets

| 파일 | 역할 |
|------|------|
| `apps/web/src/lib/ui-screen/screens/system-monitoring.screen.json` | 시스템 모니터링 스크린 |
| `apps/web/src/lib/ui-screen/screens/cep-monitoring.screen.json` | CEP 모니터링 스크린 |

### 19.5 테스트

| 파일 | 역할 |
|------|------|
| `apps/api/tests/test_ops_action_registry.py` | Action Registry 단위 테스트 |
| `apps/web/tests-e2e/u3_editor_publish_preview_v2.spec.ts` | 발행/프리뷰 E2E |
| `apps/web/tests-e2e/u3_editor_visual_json_roundtrip.spec.ts` | Visual↔JSON E2E |
| `apps/web/tests-e2e/u3_2_template_creation.spec.ts` | 템플릿 생성 E2E |
| `apps/web/tests-e2e/u3_2_diff_compare.spec.ts` | 버전 비교 E2E |
| `apps/web/tests-e2e/u3_2_publish_gate.spec.ts` | 배포 게이트 E2E |
