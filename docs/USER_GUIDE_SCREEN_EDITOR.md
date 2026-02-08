# Screen Editor User Guide

**Last Updated**: 2026-02-08

## 1. 목적과 대상

이 문서는 Screen Editor를 이용해 운영 화면을 설계, 바인딩, 액션 연결, 검증, 배포까지 수행하는 따라하기 가이드다.

대상 사용자:
- 운영 화면 제작자
- 프론트엔드 엔지니어
- OPS/API 연동 담당자

---

## 2. 시작 전 준비

### 2.1 필수 확인

1. `/admin/screens` 접근 권한 확인
2. 테스트용 데이터(입력/상태/context) 준비
3. 연결할 액션(`/ops/ui-actions` 또는 API endpoint) 준비
4. Publish 권한(RBAC) 확인

### 2.2 핵심 개념

- Screen Asset: 배포 가능한 화면 단위
- Component Tree: 화면 구조(컨테이너/위젯)
- Binding: 화면 데이터 연결 (`inputs`, `state`, `context`, `trace_id`)
- Action: 버튼/이벤트로 실행되는 동작
- Publish Gate: 배포 전 자동 검증

---

## 3. 튜토리얼 A: 첫 화면 만들기

목표: 장비 상태 요약 화면을 10분 안에 구성한다.

### Step 1. 새 Screen 생성

1. `/admin/screens` 접속
2. `New Screen` 클릭
3. 정보 입력
- screen_id: `ops_device_overview`
- title: `Device Overview`

검증 포인트:
- 목록에서 Draft 상태로 화면이 생성된다.

### Step 2. 기본 레이아웃 배치

1. Palette에서 `Container` 드래그
2. 내부에 `Text`, `Table`, `Button` 배치
3. Properties에서 제목/정렬/간격 설정

검증 포인트:
- Canvas에서 컴포넌트 구조가 트리로 보인다.

### Step 3. Undo/Redo와 멀티 선택 익히기

1. 요소 여러 개 선택 후 이동
2. `Undo` -> `Redo` 수행
3. `Duplicate`로 반복 요소 생성

검증 포인트:
- 변경 이력이 정상 동작한다.

---

## 4. 튜토리얼 B: 데이터 바인딩 연결

목표: 입력값과 상태값을 컴포넌트에 연결한다.

### Step 1. Text 바인딩

- Text 컴포넌트 값: `{{inputs.device_name}}`

### Step 2. Table 바인딩

- rows: `{{state.metric_rows}}`
- 컬럼 매핑: `name`, `value`, `collected_at`

### Step 3. Context/trace 표시

- 보조 Text에 `{{trace_id}}` 연결

검증 포인트:
- Preview에서 mock input/state 주입 시 값이 즉시 표시된다.
- 잘못된 경로는 Preview 에러로 노출된다.

---

## 5. 튜토리얼 C: 액션 연결

목표: 버튼 클릭 시 서버 액션을 호출하고 결과를 화면 상태에 반영한다.

### Step 1. 버튼 액션 추가

1. Button 선택
2. Action Type: `catalog action` 또는 `direct api`
3. Action ID/Endpoint 입력

### Step 2. 입력 매핑

- `device_id`: `{{inputs.device_id}}`
- `tenant_id`: `{{context.tenant_id}}`

### Step 3. 응답 매핑

- response rows -> `state.metric_rows`
- status message -> `state.last_message`

검증 포인트:
- Preview에서 버튼 클릭 후 Table 데이터가 갱신된다.
- 실패 시 에러 메시지가 사용자에게 보인다.

---

## 6. 튜토리얼 D: 검증과 배포

목표: Publish Gate를 통과해 배포 가능한 상태로 만든다.

### Step 1. Preview 점검

1. Desktop/Tablet/Mobile 확인
2. 핵심 액션 정상/실패 흐름 테스트
3. 민감정보 마스킹 확인

### Step 2. Publish Gate 확인

자동 검증 항목:
- 스키마 유효성
- 바인딩 경로 유효성
- 권한/보안 정책
- 성능 경고

### Step 3. Publish

1. `Publish` 실행
2. 버전 생성 확인
3. Runtime 화면에서 실제 렌더링 확인

검증 포인트:
- Published 상태에서 동일 동작이 재현된다.

---

## 7. 운영 연계 (문제 발생 시)

### 7.1 `/admin/assets`

- Screen Asset 버전/상태 확인
- 필요 시 이전 버전 rollback

### 7.2 `/admin/inspector`

- 실행 trace에서 화면/액션 흐름 분석
- 어떤 입력으로 실패했는지 확인

### 7.3 `/admin/logs` / `/admin/observability`

- 렌더링 오류, 액션 실패 로그 분석
- 액션 지연/오류율 모니터링

---

## 8. 장애 대응 플레이북

### 시나리오 1. 화면이 비어 보임

1. 필수 bindings 경로 확인
2. state 초기값 확인
3. preview input/context 주입 확인

### 시나리오 2. 버튼이 동작하지 않음

1. action_id/endpoint 오타 확인
2. 요청 payload 매핑 확인
3. 서버 응답/권한 오류 확인

### 시나리오 3. Publish 차단

1. Gate 메시지 기준으로 바인딩/스키마 수정
2. 미사용/충돌 속성 정리
3. 다시 Validate 후 Publish

---

## 9. 배포 전 체크리스트

- 주요 사용자 흐름을 Preview로 검증했다.
- 모바일 레이아웃까지 점검했다.
- 실패 메시지와 폴백 UI가 준비됐다.
- RBAC 권한별 접근을 확인했다.
- 배포 후 rollback 절차를 팀과 공유했다.

---

## 10. 향후 고도화 과제

- 실시간 협업(CRDT) 도입
- 접근성(a11y) 자동 점검
- 템플릿 라이브러리 고도화
- 화면별 성능 진단 리포트 강화
