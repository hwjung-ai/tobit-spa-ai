Screen Advanced Plan
0. 목적 (Goal)

본 문서는 UI Creator를 제거하고 Admin > Screen을 단일 편집·운영 진입점으로 승격하기 위한 실행 계획서이다.

최종 목표는 다음 한 문장으로 요약된다.

운영자가 Admin > Screen에서 화면(Screen Asset)을 전문적으로 편집·검증·배포하고, 배포된 화면이 실제 UI에 노출되며, 모든 변경과 실행이 trace로 증명되는 상태

본 계획서는 Codex(또는 다른 코드 분석 도구)가 참조 문서로 사용되며, 각 단계는 체크리스트 기반으로 완료 여부를 판단한다.

1. 전체 전략 요약
핵심 원칙

Single Source of Truth

Screen Asset의 정본은 tb_asset_registry (asset_type=screen) 단 하나

/ui-defs, /ui-creator 기반 저장소는 단계적으로 제거

편집과 실행의 분리

편집/검증/배포: Admin > Screen (Control Plane)

실행/노출: UI Runtime (Data Plane)

Copilot은 편집 보조자

Copilot은 Screen을 직접 저장/배포하지 않음

항상 patch 제안 → preview → apply → gate → publish 흐름을 따른다

2. 단계 구성 개요

S1: 정본 단일화 & 위험 제거

S2: Screen Editor 전문화 (UX/편집 강화)

S3: UI 노출 & 운영 완결

각 단계는 Sx-y 형식의 상세 단계로 구성된다.

3. S1 – 정본 단일화 & 위험 제거
목표

Screen Asset의 Source of Truth를 기술적으로 단일화

UI Creator 및 /ui-defs가 운영 경로에 개입하지 못하도록 차단

S1-0. UI Creator 쓰기 차단

설명

/ui-creator 페이지를 Read-only 또는 Redirect 처리

Admin > Screen으로 이동 유도

작업 내용

UI Creator 페이지 상단 배너 추가 또는 즉시 redirect

"This feature is deprecated" 메시지 표시

체크리스트




테스트 결과

(기입)

S1-1. /ui-defs write 차단

설명

UI Creator가 사용하는 /ui-defs API를 더 이상 write 불가 상태로 전환

작업 내용

POST/PUT/PATCH 차단 또는 권한 제한

필요 시 Read-only 유지

체크리스트




S1-2. ScreenEditor의 /ui-defs 우선 로드 제거

설명

ScreenEditor가 /ui-defs를 먼저 로드하는 로직 제거

작업 내용

editor-state.loadScreen에서 /asset-registry만 사용

체크리스트




S1-3. Publish Gate 서버 강제 검증 확인

설명

Publish 시 서버에서 validate_screen_asset이 반드시 실행되도록 보장

체크리스트




S1-4. UI Runtime은 published screen만 로드

설명

UI에서 draft screen이 노출되지 않도록 차단

체크리스트




4. S2 – Screen Editor 전문화
목표

Visual Editor가 간이 도구처럼 보이지 않도록 개선

1920px 환경에 맞는 레이아웃 편집 가능

Copilot을 통한 고급 편집 보조

S2-0. Copilot 패널 추가

설명

ScreenEditor 우측에 Copilot 패널 추가 (탭 아님)

체크리스트




S2-1. Canvas 레이아웃 확장 (Container / Horizontal Stack)

설명

단일 세로 스택에서 탈피

좌/우 분할 및 중첩 가능

체크리스트




S2-2. Properties 패널 재설계

설명

텍스트 입력 중심 UI 제거

의미 기반 컨트롤 제공

체크리스트




S2-3. Component Tree View 추가

설명

레이아웃 계층 구조를 명확히 표현

체크리스트




S2-4. Copilot → Patch → Preview → Apply 흐름 완성

설명

Copilot 제안은 즉시 저장되지 않음

체크리스트




5. S3 – UI 노출 & 운영 완결
목표

배포된 Screen이 실제 UI에 노출됨을 증명

운영 루프 완결

S3-0. UI에 Published Screens 목록 제공

체크리스트




S3-1. Screen 메타데이터 정비

체크리스트




S3-2. Admin → UI 바로가기 제공

체크리스트




S3-3. Regression / Inspector 연계 CTA 강화

체크리스트




S3-4. 운영 시나리오 문서화

체크리스트




6. Codex 사용 가이드

본 문서를 항상 참조 문서로 제공

Codex에는 다음만 요청:

특정 Sx-y 단계의 영향 범위 분석

변경 후 정합성 검증

체크리스트 충족 여부 확인

7. 완료 기준 (Definition of Done)

UI Creator 제거

Admin > Screen 단일 편집 경로

Copilot 포함 전문 편집 경험

Published Screen이 UI에 노출

모든 변경/실행이 trace로 증명됨

(끝)