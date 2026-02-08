# Screen Editor User Guide

**Last Updated**: 2026-02-08

## 1. 목적

이 가이드는 Screen Editor를 사용해 운영 화면을 생성/검증/배포하는 절차를 설명한다.

## 2. 빠른 시작

1. `/admin/screens` 접속
2. 새 Screen 생성 또는 템플릿 복제
3. 컴포넌트 배치(Drag & Drop)
4. 바인딩/액션 연결
5. Preview 확인
6. Publish

## 3. 편집 기본

### 3.1 컴포넌트 배치

- Palette에서 Canvas로 드래그
- 컨테이너 내 중첩 구조 구성
- Properties 패널에서 속성 수정

### 3.2 상태 관리

- `Undo/Redo`
- `Copy/Cut/Paste/Duplicate`
- 멀티 선택 및 일괄 이동

### 3.3 테마 적용

- Light/Dark/Brand 프리셋
- 화면 단위 override

## 4. 데이터 바인딩

### 4.1 바인딩 소스

- `inputs`
- `state`
- `context`
- `trace_id`

### 4.2 표현식 사용

- 안전 함수 기반 표현식 허용
- 동적 코드 실행 금지
- 에러 발생 시 Preview에서 즉시 확인

## 5. 액션 연결

### 5.1 표준 액션

- `/ops/ui-actions` 기반 실행
- 카탈로그에서 action 선택
- 입력 스키마 자동 폼 생성

### 5.2 Direct API 액션

- `endpoint` 직접 호출
- `response_mapping`으로 state 반영

## 6. 검증/배포

### 6.1 Preview

- Mock 데이터 주입
- Desktop/Tablet/Mobile 뷰 확인
- 액션 테스트 실행

### 6.2 Publish Gate

- 스키마 유효성
- 바인딩 경로 유효성
- 권한/보안 규칙
- 성능 경고 확인

## 7. 운영 연계

- `assets`: Screen Asset 버전 관리
- `inspector`: 실행 trace 확인
- `logs`: 렌더/액션 오류 분석
- `observability`: UI 액션 지표 확인

## 8. 체크리스트

- 주요 액션 성공/실패 경로 확인
- 모바일 레이아웃 확인
- 권한 없는 사용자 접근 시 동작 확인
- 민감정보 마스킹 확인
- Publish 후 rollback 경로 확인

## 9. 문제 해결

- 화면이 비어 보임: bindings/state 초기값 확인
- 액션 무응답: endpoint/action_id 및 payload 확인
- 테이블/차트 데이터 미표시: data_key/field 매핑 확인
- publish 차단: gate validation 메시지 기준으로 수정

## 10. 개선/고도화 제안

- CRDT 기반 실시간 협업
- 접근성(a11y) 점검 자동화
- API 요청 모니터링 탭
- 템플릿 라이브러리 고도화
