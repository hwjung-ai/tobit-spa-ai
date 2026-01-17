# CRUD Screen Template (U2)

이 문서는 `Maintenance CRUD` Screen 예시를 제공합니다.

## 1. JSON Template

경로: `apps/web/src/lib/ui-screen/examples/maintenance_crud_v1.json`

구성 요약:
- List: `table` 컴포넌트로 유지보수 티켓 목록 렌더
- Detail: `keyvalue`로 선택된 항목 요약
- Create/Edit: `modal` 내부에 `input` + `button` 배치

## 2. 구조 설명

- List 동작
  - 입력 필드(`filters`)에서 device_id 입력 후 `list_maintenance_filtered` 액션 실행
  - 결과는 `state.results.list_maintenance_filtered`에 저장되고 table과 바인딩
- Modal 동작
  - `open_maintenance_modal` 액션 → `state.modal_open` true
  - Create 버튼 → `create_maintenance_ticket` 실행

## 3. 실행 흐름 예시

1) Screen Asset publish 후 `ui_screen` block에 `screen_id="maintenance_crud_v1"` 포함  
2) UIScreenRenderer가 Screen Schema 로드 및 렌더  
3) Button/Input → `/ops/ui-actions` 호출  
4) result는 `state.results.<action_id>`로 저장

## 4. Trace 예시

- 예시 trace_id: `trace-maintenance-crud-20260118`
- Inspector > Applied Assets > Screens에 `maintenance_crud_v1` 표시됨
