# 관리 UI 3종 명세 요약

## 📋 개요

오프라인 납품 환경에서 운영자가 사용할 **최소 기능 관리 UI 3종**을 설계했습니다.

**핵심 원칙**:
- ✅ 텍스트/테이블 중심 최소 구현
- ✅ shadcn/ui + TanStack Query 사용
- ✅ 기존 네비게이션 구조 준수
- ❌ 드래그 디자이너/코드 에디터/복잡한 diff UI 제외

---

## 🎯 3개 화면 구성

### 1️⃣ Assets (Admin) - `/admin/assets`

**목적**: Prompt/Mapping/Policy 자산 관리

**핵심 기능**:
- 자산 목록 조회 (타입/상태 필터링)
- 자산 생성 (draft 상태)
- 자산 편집 (draft만 가능)
- 자산 발행 (draft → published, 버전 증가)
- 자산 롤백 (버전 번호 입력 방식)
- Validation 에러 표시

**상태 전이**:
```
생성 → draft
draft → [편집] → draft
draft → [발행] → published (v1)
published → [롤백] → published (v2, 이전 내용)
```

**제약**:
- Published 자산은 직접 수정 불가
- 롤백은 버전 번호 입력 방식 (히스토리 API 없음)

---

### 2️⃣ Settings - `/settings/operations`

**목적**: 운영 설정 관리

**핵심 기능**:
- 전체 설정 목록 조회
- 설정 편집 (published 값 생성)
- restart_required 표시 (🔄 아이콘)
- Validation 에러 표시
- (P1) 변경 이력 보기

**우선순위**:
```
published > env > default
```

**특징**:
- 설정 변경 시 자동으로 audit_log 생성
- restart_required: true인 경우 경고 메시지 표시
- Source 표시 (published/env/default)

---

### 3️⃣ Inspector - `/admin/inspector`

**목적**: Trace ID로 Audit Log 검색

**핵심 기능**:
- Trace ID 검색
- 관련 Audit Log 테이블 표시
- parent_trace_id 연결 표시 (View Parent 버튼)
- Audit Log 상세 보기 (JSON 모달)
- (P1) OPS History 링크

**검색 흐름**:
```
Trace ID 입력 → 검색 → Audit Logs 표시
                    ↓
            parent_trace_id 있으면
                    ↓
            [View Parent] 클릭 → 부모 Trace 검색
```

---

## 🔧 필요한 백엔드 작업

### 신규 API 엔드포인트

#### Audit Log Router (신규 파일 필요)
```python
# apps/api/app/modules/audit_log/router.py

GET  /audit-log?resource_type=...&resource_id=...
GET  /audit-log/by-trace/{trace_id}
GET  /audit-log/by-parent-trace/{parent_trace_id}
```

#### Asset Registry Validation 강화
- Publish 시 타입별 필수 필드 검증
- JSON 유효성 검사

---

## 📱 프론트엔드 구조

### 디렉토리
```
apps/web/src/app/admin/
├── assets/
│   ├── page.tsx              # 목록
│   └── [assetId]/page.tsx    # 상세
├── inspector/
│   └── page.tsx              # 검색
└── layout.tsx                # Admin 공통 레이아웃

apps/web/src/components/admin/
├── AssetTable.tsx
├── AssetForm.tsx
├── SettingsTable.tsx
├── SettingEditModal.tsx
├── AuditLogTable.tsx
└── ValidationAlert.tsx
```

### 네비게이션 추가
```typescript
// NavTabs.tsx에 추가
{ label: "Admin", href: "/admin/assets", adminOnly: true }
```

---

## 📝 사용자 시나리오 5개

### 시나리오 1: 새 Prompt 자산 생성 및 발행
1. `/admin/assets` 접속
2. **+ New Asset** → Type: Prompt, Name 입력
3. Template, input_schema 입력
4. **Save Draft** → 성공
5. **Publish** → published, version 1

### 시나리오 2: Published 자산 Rollback
1. Published 자산 (v3) 선택
2. **Rollback** → 버전 2 입력
3. 확인 → version 4 (내용은 v2)

### 시나리오 3: 운영 설정 변경 (restart_required)
1. `/settings/operations` 접속
2. "max_concurrent_jobs" 편집
3. 10 → 20 변경
4. 저장 → 성공 + 🔄 재시작 필요 경고

### 시나리오 4: Trace ID로 Audit Log 검색
1. `/admin/inspector` 접속
2. Trace ID 입력 → 검색
3. Audit Logs 테이블 표시
4. parent_trace_id 있으면 **View Parent** 클릭

### 시나리오 5: Validation 에러 처리
1. Mapping 자산 생성
2. 잘못된 JSON 입력 → **Publish**
3. 에러 Alert 표시
4. JSON 수정 → **Save Draft** → **Publish** 성공

---

## ✅ 구현 우선순위

### P0 (필수 - 이번 범위)
- ✅ Assets: List, Detail, Create, Edit, Publish, Rollback
- ✅ Settings: List, Edit, restart_required 표시
- ✅ Inspector: Trace 검색, Audit Log 표시, parent 연결

### P1 (가능하면)
- Settings 변경 이력 보기
- Inspector OPS History 링크
- Assets 버전 히스토리 UI

### P2 (향후)
- Assets Diff UI
- 코드 에디터
- 고급 필터

---

## 🎨 UI 디자인 원칙

### 테이블 중심
- shadcn/ui Table 컴포넌트 사용
- 필터링: Select 드롭다운
- 액션: Button (Edit, Delete, Publish 등)

### 상태 표시
- Badge: draft (회색), published (녹색)
- Icon: 🔄 (restart_required)
- Alert: ⚠️ (validation 에러)

### 메시지
- 성공: Toast (3초 자동 닫힘)
- 에러: Alert Box (수동 닫기)
- 경고: Toast + Icon

---

## 🔍 검증 체크리스트

개발 완료 후 확인:

- [ ] Assets 필터링 동작
- [ ] 생성 → 편집 → 발행 → 롤백 전체 플로우
- [ ] Published 자산 편집 시도 시 에러
- [ ] restart_required 경고 표시
- [ ] Trace 검색 및 parent 연결
- [ ] Validation 에러 명확히 표시
- [ ] Toast 자동 닫힘
- [ ] ResponseEnvelope 구조 준수
- [ ] Audit log 생성 확인

---

## 📚 참고 문서

- **상세 명세**: `docs/ADMIN_UI_SPEC.md`
- **프로젝트 규칙**: `AGENTS.md`
- **기존 API**: 
  - `apps/api/app/modules/asset_registry/router.py`
  - `apps/api/app/modules/operation_settings/router.py`
  - `apps/api/app/modules/audit_log/models.py`

---

## 💡 핵심 포인트

1. **최소 구현**: 복잡한 UI 없이 텍스트/테이블로만 구성
2. **명확한 에러**: Validation 에러를 사용자가 이해하기 쉽게 표시
3. **상태 전이**: draft ↔ published 명확히 구분
4. **추적 가능**: Audit Log로 모든 변경 이력 추적
5. **재시작 경고**: restart_required 설정 변경 시 명확히 표시

이 명세는 **개발자가 그대로 구현할 수 있도록** 작성되었습니다.
