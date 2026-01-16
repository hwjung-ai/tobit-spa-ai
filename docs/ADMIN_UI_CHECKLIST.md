# Admin UI 구현 체크리스트

이 문서는 `docs/ADMIN_UI_SPEC.md`에 정의된 관리 UI 3종을 구현할 때 사용하는 개발자 체크리스트입니다.

---

## 🔧 백엔드 작업

### 1. Audit Log Router 추가
- [ ] `apps/api/app/modules/audit_log/router.py` 파일 생성
- [ ] GET `/audit-log` 엔드포인트 구현 (resource_type/resource_id 필터)
- [ ] GET `/audit-log/by-trace/{trace_id}` 엔드포인트 구현
- [ ] GET `/audit-log/by-parent-trace/{parent_trace_id}` 엔드포인트 구현
- [ ] `apps/api/main.py`에 router 등록
- [ ] ResponseEnvelope 구조 준수 확인

### 2. Asset Registry Validation 강화
- [ ] `apps/api/app/modules/asset_registry/crud.py`의 `publish_asset` 함수 수정
- [ ] Prompt 타입: template 필수 검증
- [ ] Prompt 타입: input_schema/output_contract JSON 유효성 검증
- [ ] Mapping 타입: content 필수 검증
- [ ] Mapping 타입: content JSON 유효성 검증
- [ ] Policy 타입: limits 필수 검증
- [ ] Policy 타입: limits JSON 유효성 검증
- [ ] Validation 에러 메시지 명확화

### 3. API 테스트
- [ ] curl로 `/audit-log/by-trace/{trace_id}` 테스트
- [ ] curl로 `/audit-log` (resource filter) 테스트
- [ ] Asset publish validation 에러 테스트
- [ ] Asset rollback 테스트

---

## 🎨 프론트엔드 작업

### 1. 디렉토리 구조 생성
- [ ] `apps/web/src/app/admin/` 디렉토리 생성
- [ ] `apps/web/src/app/admin/assets/page.tsx` 생성
- [ ] `apps/web/src/app/admin/assets/[assetId]/page.tsx` 생성
- [ ] `apps/web/src/app/admin/inspector/page.tsx` 생성
- [ ] `apps/web/src/app/admin/layout.tsx` 생성
- [ ] `apps/web/src/components/admin/` 디렉토리 생성

### 2. shadcn/ui 컴포넌트 설치 (필요시)
- [ ] `npx shadcn-ui@latest add table`
- [ ] `npx shadcn-ui@latest add badge`
- [ ] `npx shadcn-ui@latest add dialog`
- [ ] `npx shadcn-ui@latest add alert`
- [ ] `npx shadcn-ui@latest add toast`
- [ ] `npx shadcn-ui@latest add textarea`
- [ ] `npx shadcn-ui@latest add select`

### 3. Assets 화면 구현
- [ ] AssetTable 컴포넌트 구현 (목록 테이블)
- [ ] AssetForm 컴포넌트 구현 (상세/편집 폼)
- [ ] Type별 Content 필드 조건부 렌더링
- [ ] Filter 드롭다운 (Type, Status)
- [ ] Create Asset 모달
- [ ] Save Draft 버튼 + mutation
- [ ] Publish 버튼 + mutation
- [ ] Rollback 버튼 + 버전 입력 모달
- [ ] Validation 에러 Alert 표시
- [ ] Toast 메시지 (성공/에러)
- [ ] TanStack Query 설정 (useQuery, useMutation)

### 4. Settings 화면 구현
- [ ] SettingsTable 컴포넌트 구현
- [ ] SettingEditModal 컴포넌트 구현
- [ ] Source badge 표시 (published/env/default)
- [ ] Restart required 아이콘 (🔄)
- [ ] Edit 버튼 + 모달
- [ ] Save 버튼 + mutation
- [ ] restart_required 경고 메시지
- [ ] Validation 에러 Alert 표시
- [ ] Toast 메시지

### 5. Inspector 화면 구현
- [ ] AuditLogTable 컴포넌트 구현
- [ ] AuditLogDetailsModal 컴포넌트 구현
- [ ] Trace ID 검색 입력 + 버튼
- [ ] Audit Logs 테이블 렌더링
- [ ] parent_trace_id 표시 + View Parent 버튼
- [ ] Related Traces 테이블
- [ ] Details 버튼 + JSON 모달
- [ ] 에러 메시지 표시

### 6. 네비게이션 추가
- [ ] `apps/web/src/components/NavTabs.tsx` 수정
- [ ] "Admin" 탭 추가 (adminOnly: true)
- [ ] `apps/web/src/app/admin/layout.tsx`에 하위 탭 구현
  - [ ] Assets 탭
  - [ ] Settings 탭
  - [ ] Inspector 탭

### 7. 공통 컴포넌트
- [ ] ValidationAlert 컴포넌트 구현
- [ ] Toast provider 설정 확인
- [ ] 에러 핸들링 유틸리티

---

## ✅ 테스트 시나리오

### 시나리오 1: 새 Prompt 자산 생성 및 발행
- [ ] `/admin/assets` 접속
- [ ] + New Asset 클릭
- [ ] Type: Prompt, Name/Description 입력
- [ ] Create 클릭 → draft 생성 확인
- [ ] Template, input_schema 입력
- [ ] Save Draft → 성공 토스트 확인
- [ ] Publish → published 상태 확인, version 1 확인

### 시나리오 2: Published 자산 Rollback
- [ ] Published 자산 (v3) 선택
- [ ] Rollback 클릭
- [ ] 버전 2 입력
- [ ] 확인 → version 4 생성, 내용은 v2 확인

### 시나리오 3: 운영 설정 변경
- [ ] `/settings/operations` 접속
- [ ] 설정 Edit 클릭
- [ ] 값 변경
- [ ] Save → 성공 토스트 확인
- [ ] restart_required: true인 경우 경고 확인
- [ ] Source: published 확인

### 시나리오 4: Trace ID 검색
- [ ] `/admin/inspector` 접속
- [ ] Trace ID 입력
- [ ] Search 클릭
- [ ] Audit Logs 테이블 표시 확인
- [ ] parent_trace_id 있으면 View Parent 버튼 확인
- [ ] View Parent 클릭 → 부모 Trace 검색 확인

### 시나리오 5: Validation 에러
- [ ] 새 Mapping 자산 생성
- [ ] 잘못된 JSON 입력
- [ ] Publish 클릭
- [ ] 에러 Alert 표시 확인
- [ ] JSON 수정
- [ ] Save Draft → Publish → 성공 확인

---

## 🔍 최종 검증

### 기능 검증
- [ ] Assets 필터링 동작 확인
- [ ] 생성 → 편집 → 발행 → 롤백 전체 플로우 테스트
- [ ] Published 자산 편집 시도 시 에러 메시지 확인
- [ ] Settings restart_required 경고 표시 확인
- [ ] Trace 검색 및 parent 연결 확인
- [ ] 모든 validation 에러 명확히 표시 확인

### UI/UX 검증
- [ ] Toast 메시지 3초 후 자동 닫힘 확인
- [ ] 모든 버튼 클릭 시 로딩 상태 표시
- [ ] 테이블 정렬/필터링 동작 확인
- [ ] 모달 열기/닫기 동작 확인
- [ ] 반응형 레이아웃 확인 (모바일/태블릿)

### 백엔드 검증
- [ ] 모든 API 호출이 ResponseEnvelope 구조 준수
- [ ] Settings 변경 시 audit_log 생성 확인
- [ ] Asset publish/rollback 시 audit_log 생성 확인
- [ ] 백엔드 로그에 에러 없음 확인

### 코드 품질
- [ ] `make web-lint` 통과
- [ ] `make api-lint` 통과
- [ ] TypeScript 타입 에러 없음
- [ ] Console 에러/경고 없음

---

## 📚 참고 문서

- **상세 명세**: `docs/ADMIN_UI_SPEC.md`
- **요약 (한글)**: `docs/ADMIN_UI_SUMMARY_KR.md`
- **프로젝트 규칙**: `AGENTS.md`
- **기능 문서**: `docs/FEATURES.md`

---

## 💡 구현 팁

1. **단계별 구현**: Assets → Settings → Inspector 순서로 구현
2. **컴포넌트 재사용**: 공통 컴포넌트 먼저 구현 (ValidationAlert, Toast 등)
3. **API 먼저**: 백엔드 API 완성 후 프론트엔드 구현
4. **타입 안전성**: API 응답 타입 정의 후 사용
5. **에러 핸들링**: 모든 API 호출에 try-catch 또는 onError 핸들러 추가
6. **사용자 피드백**: 모든 액션에 로딩 상태 + 성공/에러 메시지 표시

---

## 🚀 배포 전 체크리스트

- [ ] 모든 기능 테스트 시나리오 통과
- [ ] 백엔드 마이그레이션 실행 확인
- [ ] 환경변수 `.env.example` 업데이트 (필요시)
- [ ] `docs/FEATURES.md` 업데이트 완료
- [ ] `docs/OPERATIONS.md` 업데이트 (필요시)
- [ ] Git 커밋 메시지 명확히 작성
- [ ] PR 생성 및 리뷰 요청
