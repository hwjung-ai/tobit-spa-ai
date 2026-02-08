# Screen Editor User Guide

**Last Updated**: 2026-02-08

## 문서의 성격

이 문서는 Screen Editor를 처음 사용하는 사용자가
빈 화면부터 시작해 실제 배포 가능한 Screen Asset을 완성하도록 돕는 튜토리얼이다.

핵심 목표:
1. 화면 구조를 직접 만든다.
2. bindings/actions를 연결해 동작 화면을 완성한다.
3. preview/publish/rollback까지 운영 흐름을 익힌다.

---

## 0. 시작 전 준비

### 0.1 준비 체크

1. `/admin/screens` 접근 가능
2. 필요한 권한(편집/발행) 보유
3. 연결할 API 또는 `/ops/ui-actions` handler 준비

### 0.2 화면 구조 빠른 이해

- 목록: `/admin/screens`
- 편집기: `/admin/screens/{screen_id}`

편집 탭:
- Visual
- JSON
- Binding
- Action
- Preview
- Diff

---

## 1. Lab 1 - 첫 Screen 생성

목표: 빈 화면에서 초안 Screen을 만든다.

### Step 1. 목록 화면 진입

1. `/admin/screens` 접속
2. 새 Screen 생성 버튼 클릭

### Step 2. 기본 정보 입력

- screen_id: `ops_device_overview`
- title: `Device Overview`
- description: 운영 장비 개요 화면

검증 포인트:
- Draft 상태로 목록에 생성된다.

### Step 3. 편집기 진입

- 생성된 screen 클릭 -> `/admin/screens/{screen_id}`

---

## 2. Lab 2 - Visual 탭으로 레이아웃 만들기

목표: UI 뼈대를 완성한다.

### Step 1. 컴포넌트 배치

1. Container 추가
2. Text, Table, Button 컴포넌트 배치
3. 필요 시 Tabs/Modal 구성

### Step 2. 속성 편집

- 제목 텍스트
- 여백/정렬
- 테이블 컬럼 구조

### Step 3. 편집 생산성 기능 사용

- Undo/Redo
- Copy/Cut/Paste/Duplicate
- Multi-select

검증 포인트:
- 컴포넌트 트리가 의도대로 구성된다.

---

## 3. Lab 3 - JSON 탭으로 스키마 확인

목표: Visual 결과가 스키마에 어떻게 반영되는지 이해한다.

### Step 1. JSON 탭 이동

- screen schema 전체 확인

### Step 2. 핵심 필드 확인

- `layout`
- `components`
- `state`
- `actions`
- `bindings`

### Step 3. 간단 수정

- label/text 값 미세 조정

검증 포인트:
- JSON 수정 후 Visual에 반영된다.

---

## 4. Lab 4 - Binding 탭으로 데이터 연결

목표: 컴포넌트가 정적 UI가 아니라 동적 UI로 동작하도록 만든다.

### Step 1. 기본 바인딩 추가

예시:
- Text.value <- `{{inputs.device_name}}`
- Table.rows <- `{{state.metric_rows}}`
- Text(trace) <- `{{trace_id}}`

### Step 2. 경로 유효성 확인

- 존재하지 않는 경로를 넣었을 때 오류 확인

### Step 3. Binding 평가 확인

- Binding 탭 미리보기로 실제 평가값 점검

검증 포인트:
- 유효 경로는 정상 평가
- 잘못된 경로는 즉시 식별 가능

---

## 5. Lab 5 - Action 탭으로 인터랙션 만들기

목표: 버튼 클릭으로 데이터 갱신/액션 실행.

### Step 1. 액션 추가

1. Button 선택
2. Action 추가
3. handler 선택 (catalog 기반)

### Step 2. 입력 매핑

예시:
- `device_id`: `{{inputs.device_id}}`
- `tenant_id`: `{{context.tenant_id}}`

### Step 3. 응답 매핑

- `state.metric_rows` <- response rows
- `state.last_message` <- response message

검증 포인트:
- 액션 실행 시 state patch 반영
- 오류 시 메시지가 표시

---

## 6. Lab 6 - Preview 탭에서 실사용 검증

목표: 실제 사용 흐름을 미리 검증한다.

### Step 1. Preview overrides 입력

- params JSON
- bindings override JSON

### Step 2. 렌더링 확인

- Desktop/Tablet/Mobile 확인
- 버튼 클릭 액션 실행

### Step 3. 결과 검증

- Latest action result 확인
- 에러 문구 확인

검증 포인트:
- 주요 사용자 흐름이 끊기지 않는다.

---

## 7. Lab 7 - Diff 탭으로 변경점 점검

목표: draft와 published 차이를 정확히 검토한다.

### Step 1. Diff 탭 이동

- 컴포넌트/액션/바인딩/상태 차이 확인

### Step 2. 변경 요약 확인

- added/removed/modified 수치 확인

### Step 3. 의도하지 않은 변경 제거

- 불필요 수정 정리

검증 포인트:
- 발행 전에 변경 범위를 팀이 설명 가능

---

## 8. Lab 8 - Publish와 Rollback

목표: 배포 가능한 상태를 만든다.

### Step 1. Publish Gate 점검

- 스키마 유효성
- binding/action 유효성
- 권한/정책 점검

### Step 2. Publish

- Publish 실행
- 성공 메시지 확인

### Step 3. Runtime 검증

- 실제 호출 경로에서 렌더링 확인

### Step 4. Rollback

- 문제 발생 시 rollback 실행
- 이전 버전 정상동작 확인

검증 포인트:
- publish/rollback 모두 재현 가능

---

## 9. Lab 9 - 협업/Presence 확인

목표: 다중 편집 상황을 안전하게 운영한다.

### Step 1. Presence 표시 확인

- 탭 상단 active editors 확인

### Step 2. heartbeat/stream 동작 확인

- `/ops/ui-editor/presence/heartbeat`
- `/ops/ui-editor/presence/stream`
- `/ops/ui-editor/presence/leave`

검증 포인트:
- 동시 편집 세션이 표시된다.
- 연결 불안정 시 fallback이 동작한다.

---

## 10. 장애 대응 플레이북

### 10.1 화면이 비어 보임

점검 순서:
1. 필수 bindings 존재 여부
2. state 초기값
3. preview overrides 데이터

### 10.2 버튼이 동작하지 않음

점검 순서:
1. handler/action_id 설정
2. payload 매핑
3. 서버 응답/권한 오류

### 10.3 Publish 차단

점검 순서:
1. validation 메시지 확인
2. 잘못된 path/handler 수정
3. 다시 validate 후 publish

### 10.4 diff가 과도함

점검 순서:
1. 불필요 JSON 포맷 변경 제거
2. 의미 없는 속성 변경 되돌리기

---

## 11. 최종 체크리스트

```text
□ 빈 화면에서 Screen을 새로 만들었다.
□ Visual/JSON/Binding/Action/Preview/Diff를 모두 사용했다.
□ 액션 실행으로 state 갱신을 확인했다.
□ Publish와 Rollback을 각각 수행했다.
□ Presence 기반 동시 편집 상황을 확인했다.
```

---

## 12. 참고 파일

- `apps/web/src/app/admin/screens/page.tsx`
- `apps/web/src/app/admin/screens/[screenId]/page.tsx`
- `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx`
- `apps/web/src/components/admin/screen-editor/ScreenEditorTabs.tsx`
- `apps/web/src/components/admin/screen-editor/preview/PreviewTab.tsx`
- `apps/web/src/components/admin/screen-editor/diff/DiffTab.tsx`
- `apps/web/src/components/answer/UIScreenRenderer.tsx`
- `apps/api/app/modules/ops/router.py`


---

## 13. Lab 10 - Table 고급 동작 구성

목표: 테이블을 운영 친화적으로 구성.

### Step 1. 컬럼 정의

- field/header 매핑
- sortable 설정
- 포맷터(number/date/percent)

### Step 2. 페이지네이션

- page_size 설정

### Step 3. 행 클릭 액션

- `row_click_action_index` 지정

검증 포인트:
- 정렬/페이지/행 액션이 모두 동작한다.

---

## 14. Lab 11 - Auto Refresh 구성

목표: 화면이 주기적으로 데이터를 갱신하도록 설정.

### Step 1. auto_refresh 활성화

예시:
```json
{
  "enabled": true,
  "interval_ms": 30000,
  "action_index": 0,
  "max_failures": 3,
  "backoff_ms": 10000
}
```

### Step 2. Preview에서 동작 확인

- 주기 실행 여부
- 실패 시 백오프/중단 확인

검증 포인트:
- 불필요한 과호출 없이 안정적으로 갱신된다.

---

## 15. Lab 12 - Action 체인 구성

목표: 여러 액션을 순서대로 실행하는 화면 구성.

### Step 1. 액션 3개 구성

1. 데이터 조회
2. 상태 병합
3. 사용자 메시지 표시

### Step 2. 실패 정책 설정

- stop_on_error
- continue_on_error
- retry_count/retry_delay

### Step 3. Preview에서 체인 테스트

검증 포인트:
- 성공/실패 경로가 예측 가능하게 동작한다.

---

## 16. Lab 13 - Direct API Endpoint 액션 실습

목표: `/ops/ui-actions` 외 endpoint 직접 호출 흐름 익히기.

### Step 1. 액션 모드 설정

- endpoint: 예 `/admin/system/health`
- method: `GET`

### Step 2. response_mapping 설정

예시:
```json
{
  "cpu_usage": "health.resource.cpu_percent",
  "memory_usage": "health.resource.memory_percent"
}
```

### Step 3. Preview 실행

검증 포인트:
- 응답이 state 키로 매핑된다.
- 경로 오타 시 즉시 에러 확인 가능

---

## 17. Lab 14 - Inspector 연계 디버깅

목표: 화면 액션 실패를 trace로 추적.

### Step 1. 실패 액션 실행

- Preview에서 의도적 잘못된 payload 사용

### Step 2. Inspector 이동

- trace_id 기준 `/admin/inspector` 열기

### Step 3. 확인 항목

- action 요청 payload
- tool_calls/references
- 오류 메시지

검증 포인트:
- UI 오류를 API/액션 레벨 원인으로 설명 가능

---

## 18. Lab 15 - 릴리즈 전 최종 리허설

목표: 발행 직전 최종 점검 루틴 확립.

### 체크 순서

1. Visual에서 레이아웃 깨짐 확인
2. Binding 경로 누락 확인
3. Action 정상/오류 경로 확인
4. Preview 모바일 확인
5. Diff 의도치 않은 변경 제거
6. Publish Gate 통과

### 발행 후 즉시 확인

1. Runtime 렌더링
2. 핵심 액션 1회 실행
3. 로그/오류율 확인

---

## 19. 운영 부록 - 디자인/운영 표준

### 화면 설계 표준

- 핵심 KPI는 상단
- 필터는 좌상단
- 상세 테이블은 중앙
- 에러 메시지는 사용자 행동 근처

### 바인딩 표준

- 긴 경로는 중간 state로 분리
- 공통 경로 네이밍 일관성 유지

### 액션 표준

- handler 이름은 동사형
- payload 키는 snake_case로 통일
- 실패 메시지는 사용자 관점 문구 사용

---

## 20. 운영 부록 - 빠른 복구 체크

문제 발생 시 5분 복구 루틴:

1. Preview에서 재현
2. Action payload 확인
3. Inspector trace 확인
4. 임시 조치(버튼 비활성/조건 완화)
5. rollback 또는 hotfix publish

