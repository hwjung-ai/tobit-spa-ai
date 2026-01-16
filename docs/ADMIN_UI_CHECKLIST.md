# Admin UI 구현 체크리스트

이 문서는 `docs/ADMIN_UI_SPEC.md`에 정의된 관리 UI 3종을 구현할 때 사용하는 개발자 체크리스트입니다.

---

## 🔧 백엔드 작업

### 1. Audit Log Router 추가
[x] `apps/api/app/modules/audit_log/router.py` 파일 생성
[x] GET `/audit-log` 엔드포인트 구현 (resource_type/resource_id 필터)
[x] GET `/audit-log/by-trace/{trace_id}` 엔드포인트 구현
[x] GET `/audit-log/by-parent-trace/{parent_trace_id}` 엔드포인트 구현
[x] `apps/api/main.py`에 router 등록
[x] ResponseEnvelope 구조 준수 확인

### 2. Asset Registry Validation 강화
[x] `apps/api/app/modules/asset_registry/crud.py`의 `publish_asset` 및 `validate_asset` 활용 확인
[x] Prompt 타입: template 필수 검증 (`validators.py` 구현됨)
[x] Prompt 타입: input_schema/output_contract JSON 유효성 검증 (`validators.py` 구현됨)
[x] Mapping 타입: content 필수 검증 (`validators.py` 구현됨)
[x] Mapping 타입: content JSON 유효성 검증 (`validators.py` 구현됨)
[x] Policy 타입: limits 필수 검증 (`validators.py` 구현됨)
[x] Policy 타입: limits JSON 유효성 검증 (`validators.py` 구현됨)
[x] Validation 에러 메시지 명확화

### 3. API 테스트
[x] curl로 `/audit-log/by-trace/{trace_id}` 테스트
[x] curl로 `/audit-log` (resource filter) 테스트
[x] Asset publish validation 서버측 에러 대응 (ValidationAlert 연동)
[x] Asset rollback 테스트 (API 호출부 및 UI 구현 완료)

---

## 🎨 프론트엔드 작업

### 1. 디렉토리 구조 생성
[x] `apps/web/src/app/admin/` 디렉토리 생성
[x] `apps/web/src/app/admin/assets/page.tsx` 생성
[x] `apps/web/src/app/admin/assets/[assetId]/page.tsx` 생성
[x] `apps/web/src/app/admin/inspector/page.tsx` 생성
[x] `apps/web/src/app/admin/layout.tsx` 생성
[x] `apps/web/src/components/admin/` 디렉토리 생성

### 2. UI 컴포넌트 구현 (Tailwind Custom)
[x] Table (AssetTable, SettingsTable, AuditLogTable)
[x] Badge (Status, Type, Source)
[x] Dialog/Modal (AuditDetails, SettingEdit, Rollback, CreateAsset)
[x] Alert (ValidationAlert)
[x] Toast (Success/Warning Notification)
[x] Form controls (Textarea, Select, Input)

### 3. Assets 화면 구현
[x] AssetTable 컴포넌트 구현 (목록 테이블)
[x] AssetForm 컴포넌트 구현 (상세/편집 폼)
[x] Type별 Content 필드 조건부 렌더링
[x] Filter 드롭다운 (Type, Status)
[x] Create Asset 모달 구현 및 연동
[x] Save Draft 버튼 + async fetch
[x] Publish 버튼 + async fetch
[x] Rollback 버튼 + 버전 입력 모달
[x] Validation 에러 Alert 표시
[x] Toast 메시지 (성공/에러)
[x] TanStack Query 설정 (useQuery 연동 완료)

### 4. Settings 화면 구현
[x] SettingsTable 컴포넌트 구현
[x] SettingEditModal 컴포넌트 구현
[x] Source badge 표시 (published/env/default)
[x] Restart required 아이콘 (🔄)
[x] Edit 버튼 + 모달
[x] Save 버튼 + async fetch
[x] restart_required 경고 메시지 고지
[x] Validation 에러 Alert 표시
[x] Toast 메시지
[x] TanStack Query 설정 (useQuery 연동 완료)

### 5. Inspector 화면 구현
[x] AuditLogTable 컴포넌트 구현
[x] AuditLogDetailsModal 컴포넌트 구현
[x] Trace ID 검색 입력 + 버튼
[x] Audit Logs 테이블 렌더링
[x] parent_trace_id 표시 + View Parent 버튼
[x] 세부 정보 JSON 모달
[x] 에러 메시지 표시 (No results/API error)

### 6. 네비게이션 추가
[x] `apps/web/src/components/NavTabs.tsx` 수정
[x] "Admin" 탭 추가 (adminOnly: true)
[x] `apps/web/src/app/admin/layout.tsx`에 하위 탭 구현
  [x] Assets 탭
  [x] Settings 탭
  [x] Inspector 탭

### 7. 공통 컴포넌트
[x] ValidationAlert 컴포넌트 구현
[x] Toast 컴포넌트 구현
[x] 타임스탬프/상대시간 포맷터 등 유틸리티 구현

---

## ✅ 테스트 시나리오 (실제 구현 확인 완료)

### 시나리오 1: 새 Prompt 자산 생성 및 발행
[x] `/admin/assets` 접속 -> New Asset 클릭
[x] Draft 생성 후 상세 페이지 자동 이동 및 편집 확인
[x] Publish 로직 동작 확인

### 시나리오 2: Published 자산 Rollback
[x] Published 자산 선택
[x] Rollback 모달 호출 및 API 연동 확인

### 시나리오 3: 운영 설정 변경
[x] Settings 관리 기능 및 History 조회 확인
[x] 변경 사항 즉시 반영(Refetch) 및 Toast 확인

### 시나리오 4: Trace ID 검색
[x] Inspector Trace ID 검색 기능 및 상세 조회 연동 확인

### 시나리오 5: Validation 에러
[x] 클라이언트/서버 유효성 검사 에러 표시(ValidationAlert) 확인

---

## 🔍 최종 검증

### 기능 검증
[x] Assets 필터링 및 라이프사이클(Draft/Published/Rollback) 지원
[x] Settings Source/Restart 정보 시각화
[x] Trace Inspector를 통한 고해상도 감사 내역 추적

### UI/UX 검증
[x] Toast 자동 dismiss 및 수동 닫기 지원
[x] 로딩 상태 표시 및 반응형 레이아웃 대응
[x] 일관된 디자인 시스템 적용

### 코드 품질
[x] TanStack Query 도입을 통한 데이터 동기화 최적화
[x] TypeScript 타입 안전성 확보
[x] `npm run lint` 통과 확인
