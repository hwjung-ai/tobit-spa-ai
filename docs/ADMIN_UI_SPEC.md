# Admin UI 3종 최소 기능 명세 (P0)

## 문서 개요

이 문서는 오프라인 납품 환경에서 운영자가 사용할 **관리 UI 3종**의 최소 기능/화면 구성을 정의합니다.

**범위**: P0 운영 UI 노출 (UI Creator 확장 P1은 제외)  
**제약**: AGENTS.md의 프론트엔드 스택 준수 (Next.js, shadcn/ui, TanStack Query)  
**원칙**: 텍스트/테이블 중심 최소 구현, 드래그 디자이너/코드 에디터/복잡한 diff UI 제외  
**권한**: 관리자 전용 (인증/권한 체크는 향후 확장)

---

## 1. Assets (Admin) - 자산 관리 화면

### 1.1 화면 경로
- **URL**: `/admin/assets`
- **네비게이션**: NavTabs에 "Admin" 탭 추가 (adminOnly: true)

### 1.2 화면 섹션 구성

```
┌─────────────────────────────────────────────────────────────┐
│ [Assets Admin]                                              │
├─────────────────────────────────────────────────────────────┤
│ Filter: [All Types ▼] [All Status ▼]  [+ New Asset]        │
├─────────────────────────────────────────────────────────────┤
│ Asset List (Table)                                          │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Name │ Type │ Status │ Version │ Updated │ Actions    │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │ ...                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ [Asset Detail: {name}]                         [← Back]     │
├─────────────────────────────────────────────────────────────┤
│ Basic Info Section                                          │
│ - Name, Type, Description, Status, Version                  │
│                                                             │
│ Content Section (Type-specific)                             │
│ - Prompt: template (textarea), input_schema (JSON)          │
│ - Mapping: content (JSON)                                   │
│ - Policy: limits (JSON)                                     │
│                                                             │
│ Validation Errors (if any)                                  │
│ ⚠️ [Error messages in red alert box]                        │
│                                                             │
│ Actions                                                     │
│ [Save Draft] [Publish] [Rollback]                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 테이블 컬럼 (Asset List)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Name | string | 자산 이름 (클릭 시 상세 페이지) |
| Type | badge | prompt/mapping/policy |
| Status | badge | draft (회색) / published (녹색) |
| Version | number | 현재 버전 번호 |
| Updated | datetime | updated_at (상대 시간 표시) |
| Actions | buttons | View / Edit / Delete (draft만) |

### 1.4 버튼/액션

#### List 화면
- **+ New Asset**: 새 자산 생성 모달 열기
  - Type 선택 (prompt/mapping/policy)
  - Name, Description 입력
  - 생성 시 draft 상태로 생성
  
- **Filter Dropdowns**:
  - Type: All / Prompt / Mapping / Policy
  - Status: All / Draft / Published

#### Detail 화면
- **Save Draft** (draft 상태만):
  - PUT `/asset-registry/assets/{asset_id}`
  - 성공: "Draft saved successfully" 토스트
  - 실패: 에러 메시지 표시
  
- **Publish** (draft 상태만):
  - POST `/asset-registry/assets/{asset_id}/publish`
  - 성공: status → published, version 증가, "Published successfully" 토스트
  - 실패: validation 에러 표시
  
- **Rollback** (published 상태만):
  - 버전 번호 입력 모달 표시
  - POST `/asset-registry/assets/{asset_id}/rollback?to_version={n}`
  - 성공: "Rolled back to version {n}" 토스트
  - 실패: "Version {n} not found" 에러

- **Delete** (draft 상태만):
  - 확인 다이얼로그 표시
  - DELETE 엔드포인트 호출 (향후 구현)

### 1.5 에러/성공 메시지 규칙

#### 성공 메시지 (Toast, 3초 자동 닫힘)
- "Asset created successfully"
- "Draft saved successfully"
- "Asset published successfully"
- "Rolled back to version {n}"

#### 에러 메시지 (Alert Box, 수동 닫기)
- **Validation 에러**: 빨간색 Alert 박스로 상세 페이지 상단에 표시
  ```
  ⚠️ Validation Errors:
  - Template is required for prompt assets
  - Invalid JSON in input_schema
  ```
  
- **API 에러**: HTTPException의 detail을 그대로 표시
  - "Cannot update published asset. Create new draft first."
  - "Asset not found"
  - "Version {n} not found"

### 1.6 상태 전이

```
[Create] → draft
draft → [Publish] → published
published → [Rollback] → published (version 변경)
draft → [Save Draft] → draft (내용 수정)
draft → [Delete] → (삭제)
```

**제약**:
- published 상태에서는 직접 수정 불가
- published → draft 전환 없음 (새 draft 생성 필요, P1 범위)

### 1.7 Type별 Content 필드

#### Prompt
- **template** (textarea, required): 프롬프트 템플릿 텍스트
- **input_schema** (JSON textarea): 입력 스키마
- **output_contract** (JSON textarea): 출력 계약
- **scope** (text, readonly): 스코프
- **engine** (text, readonly): 엔진

#### Mapping
- **mapping_type** (text, readonly): 매핑 타입
- **content** (JSON textarea, required): 매핑 내용

#### Policy
- **policy_type** (text, readonly): 정책 타입
- **limits** (JSON textarea, required): 제한 설정

---

## 2. Settings - 운영 설정 화면

### 2.1 화면 경로
- **URL**: `/settings/operations`
- **기존 네비게이션**: 별도 탭 없음 (Admin 탭 하위 또는 직접 URL 접근)

### 2.2 화면 섹션 구성

```
┌─────────────────────────────────────────────────────────────┐
│ [Operation Settings]                                        │
├─────────────────────────────────────────────────────────────┤
│ ⚠️ Some settings require restart (shown with 🔄 icon)       │
├─────────────────────────────────────────────────────────────┤
│ Settings List (Table)                                       │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Key │ Value │ Source │ Restart │ Actions              │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │ ...                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ [View Change History]                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ [Edit Setting: {key}]                          [× Close]    │
├─────────────────────────────────────────────────────────────┤
│ Key: {setting_key} (readonly)                               │
│ Description: {description}                                  │
│ Default: {default_value}                                    │
│                                                             │
│ Current Value: [input field]                                │
│ Source: {published/env/default}                             │
│                                                             │
│ Allowed Values: {allowed_values if applicable}              │
│                                                             │
│ 🔄 Restart Required: {Yes/No}                               │
│                                                             │
│ Validation Errors:                                          │
│ ⚠️ [Error messages if any]                                  │
│                                                             │
│ [Cancel] [Save]                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 테이블 컬럼 (Settings List)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| Key | string | 설정 키 (예: max_concurrent_jobs) |
| Value | string/number | 현재 유효 값 |
| Source | badge | published (파란색) / env (노란색) / default (회색) |
| Restart | icon | 🔄 (restart_required: true인 경우만) |
| Actions | buttons | Edit / History |

### 2.4 버튼/액션

#### List 화면
- **Edit**: 설정 편집 모달 열기
- **History**: 변경 이력 모달 열기 (P1 가능하면 구현)
- **View Change History**: 전체 변경 이력 페이지로 이동 (P1)

#### Edit 모달
- **Save**:
  - PUT `/settings/operations/{setting_key}` with `{"value": new_value}`
  - 성공: "Setting updated successfully" 토스트
  - restart_required: true인 경우 추가 경고 표시
  - 실패: validation 에러 표시
  
- **Cancel**: 모달 닫기 (변경 취소)

### 2.5 에러/성공 메시지 규칙

#### 성공 메시지 (Toast)
- "Setting updated successfully"
- restart_required: true인 경우:
  ```
  ✅ Setting updated successfully
  🔄 Restart required for this change to take effect
  ```

#### 에러 메시지 (Alert Box)
- **Validation 에러**:
  ```
  ⚠️ Validation Error:
  - Value must be between 1 and 100
  - Invalid value for allowed_values: [...]
  ```
  
- **API 에러**:
  - "Request must include 'value' field"
  - "Setting key not found"

### 2.6 상태 전이

```
default → [Edit + Save] → published (source: published)
env → [Edit + Save] → published (source: published, env 값 override)
published → [Edit + Save] → published (source: published, 새 값)
```

**우선순위**: published > env > default

### 2.7 변경 이력 (P1 가능하면 구현)

#### History 모달 (단일 설정)
```
┌─────────────────────────────────────────────────────────────┐
│ [Change History: {setting_key}]                [× Close]    │
├─────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Time │ Actor │ Old Value │ New Value │ Trace ID       │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │ ...                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**데이터 소스**: 
- GET `/audit-log/resource?resource_type=operation_setting&resource_id={setting_key}`
- (향후 구현 필요)

---

## 3. Inspector - 추적 검색 화면

### 3.1 화면 경로
- **URL**: `/admin/inspector`
- **네비게이션**: Admin 탭 하위 또는 직접 URL 접근

### 3.2 화면 섹션 구성

```
┌─────────────────────────────────────────────────────────────┐
│ [Trace Inspector]                                           │
├─────────────────────────────────────────────────────────────┤
│ Search by Trace ID:                                         │
│ [___________________________________] [Search]              │
├─────────────────────────────────────────────────────────────┤
│ Results (if trace_id found)                                 │
│                                                             │
│ Trace Info                                                  │
│ - Trace ID: {trace_id}                                      │
│ - Parent Trace ID: {parent_trace_id} [View Parent]         │
│                                                             │
│ Audit Logs (Table)                                          │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Time │ Resource │ Action │ Actor │ Changes │ Details  │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │ ...                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ Related Traces (if parent_trace_id exists)                  │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Trace ID │ Resource │ Action │ Time                    │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │ ...                                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                             │
│ OPS History Link (P1 가능하면)                              │
│ 🔗 View in OPS History                                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 테이블 컬럼

#### Audit Logs Table
| 컬럼 | 타입 | 설명 |
|------|------|------|
| Time | datetime | created_at (상대 시간 + 절대 시간) |
| Resource | string | resource_type:resource_id |
| Action | badge | create/update/publish/rollback 등 |
| Actor | string | 작업 수행자 |
| Changes | summary | changes 필드 요약 (클릭 시 상세) |
| Details | button | 상세 보기 (JSON 모달) |

#### Related Traces Table
| 컬럼 | 타입 | 설명 |
|------|------|------|
| Trace ID | link | 클릭 시 해당 trace_id로 검색 |
| Resource | string | resource_type:resource_id |
| Action | badge | action |
| Time | datetime | created_at |

### 3.4 버튼/액션

#### Search
- **Search**:
  - GET `/audit-log/trace/{trace_id}` (향후 구현 필요)
  - 성공: Audit Logs 테이블 표시
  - 실패: "No logs found for trace ID: {trace_id}"
  
- **View Parent** (parent_trace_id 존재 시):
  - 클릭 시 parent_trace_id로 새 검색 수행
  
- **Details** (Audit Log 행):
  - JSON 모달 표시
  - changes, old_values, new_values, metadata 전체 표시

#### Related Traces
- **Trace ID 링크**:
  - 클릭 시 해당 trace_id로 검색 수행

#### OPS History Link (P1)
- **View in OPS History**:
  - `/ops?trace_id={trace_id}` 로 이동
  - (OPS 화면에서 trace_id 필터 기능 필요)

### 3.5 에러/성공 메시지 규칙

#### 성공 메시지
- "Found {n} audit log(s) for trace ID: {trace_id}"

#### 에러 메시지
- "No logs found for trace ID: {trace_id}"
- "Invalid trace ID format"
- "Failed to load audit logs: {error}"

### 3.6 상태 전이

```
[Empty] → [Search] → [Results]
[Results] → [View Parent] → [Results (parent)]
[Results] → [Trace ID Link] → [Results (related)]
```

### 3.7 Details 모달 (JSON 표시)

```
┌─────────────────────────────────────────────────────────────┐
│ [Audit Log Details]                            [× Close]    │
├─────────────────────────────────────────────────────────────┤
│ Audit ID: {audit_id}                                        │
│ Trace ID: {trace_id}                                        │
│ Parent Trace ID: {parent_trace_id}                          │
│ Resource: {resource_type}:{resource_id}                     │
│ Action: {action}                                            │
│ Actor: {actor}                                              │
│ Time: {created_at}                                          │
│                                                             │
│ Changes:                                                    │
│ ```json                                                     │
│ {changes}                                                   │
│ ```                                                         │
│                                                             │
│ Old Values:                                                 │
│ ```json                                                     │
│ {old_values}                                                │
│ ```                                                         │
│                                                             │
│ New Values:                                                 │
│ ```json                                                     │
│ {new_values}                                                │
│ ```                                                         │
│                                                             │
│ Metadata:                                                   │
│ ```json                                                     │
│ {metadata}                                                  │
│ ```                                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 필요한 백엔드 API 추가 구현

### 4.1 Audit Log Router (신규)

**파일**: `apps/api/app/modules/audit_log/router.py`

```python
@router.get("/trace/{trace_id}")
def get_audit_logs_by_trace_endpoint(
    trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get all audit logs for a specific trace ID."""
    logs = get_audit_logs_by_trace(session, trace_id)
    return ResponseEnvelope.success(data={"logs": logs, "count": len(logs)})

@router.get("/parent-trace/{parent_trace_id}")
def get_audit_logs_by_parent_trace_endpoint(
    parent_trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get all audit logs for a specific parent trace ID."""
    logs = get_audit_logs_by_parent_trace(session, parent_trace_id)
    return ResponseEnvelope.success(data={"logs": logs, "count": len(logs)})

@router.get("/resource")
def get_audit_logs_by_resource_endpoint(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get audit logs for a specific resource."""
    logs = get_audit_logs_by_resource(session, resource_type, resource_id, limit, offset)
    return ResponseEnvelope.success(data={"logs": logs, "count": len(logs)})
```

### 4.2 Asset Registry Validation (강화)

**파일**: `apps/api/app/modules/asset_registry/crud.py`

publish_asset 함수에 validation 로직 추가:
- Prompt: template 필수, input_schema/output_contract JSON 유효성
- Mapping: content 필수, JSON 유효성
- Policy: limits 필수, JSON 유효성

---

## 5. 사용자 시나리오 5개

### 시나리오 1: 새 Prompt 자산 생성 및 발행

1. 운영자가 `/admin/assets` 접속
2. **+ New Asset** 클릭
3. Type: "Prompt" 선택, Name: "User Query Analyzer", Description 입력
4. **Create** 클릭 → draft 상태로 생성됨
5. 상세 페이지에서 template 입력:
   ```
   Analyze the following user query: {{query}}
   ```
6. input_schema 입력:
   ```json
   {"query": "string"}
   ```
7. **Save Draft** 클릭 → "Draft saved successfully" 토스트
8. **Publish** 클릭 → status: published, version: 1, "Asset published successfully" 토스트

**결과**: 새 Prompt 자산이 published 상태로 등록됨

---

### 시나리오 2: Published 자산 Rollback

1. 운영자가 `/admin/assets` 접속
2. "User Query Analyzer" (published, version: 3) 클릭
3. **Rollback** 클릭
4. 모달에서 "Roll back to version: 2" 입력
5. **Confirm** 클릭
6. POST `/asset-registry/assets/{id}/rollback?to_version=2`
7. 성공 → "Rolled back to version 2" 토스트, 페이지 새로고침
8. version: 4 (새 버전), content는 version 2의 내용

**결과**: 자산이 이전 버전으로 롤백됨 (새 버전 번호로)

---

### 시나리오 3: 운영 설정 변경 (restart_required: true)

1. 운영자가 `/settings/operations` 접속
2. "max_concurrent_jobs" 행에서 **Edit** 클릭
3. 모달 표시:
   - Current Value: 10 (source: default)
   - Restart Required: Yes 🔄
4. 새 값 입력: 20
5. **Save** 클릭
6. PUT `/settings/operations/max_concurrent_jobs` with `{"value": 20}`
7. 성공 토스트:
   ```
   ✅ Setting updated successfully
   🔄 Restart required for this change to take effect
   ```
8. 테이블에서 source: published (파란색), 🔄 아이콘 표시

**결과**: 설정이 변경되었으나 재시작 필요 경고 표시됨

---

### 시나리오 4: Trace ID로 Audit Log 검색

1. 운영자가 `/admin/inspector` 접속
2. Trace ID 입력: "trace-abc-123"
3. **Search** 클릭
4. GET `/audit-log/trace/trace-abc-123`
5. 결과 표시:
   - Trace Info: trace_id, parent_trace_id (있으면)
   - Audit Logs 테이블: 3개 로그
     - 2026-01-16 10:30 | asset:prompt-001 | publish | admin | {...}
     - 2026-01-16 10:25 | asset:prompt-001 | update | admin | {...}
     - 2026-01-16 10:20 | asset:prompt-001 | create | admin | {...}
6. parent_trace_id가 "trace-parent-456"인 경우 **View Parent** 버튼 표시
7. **View Parent** 클릭 → "trace-parent-456"로 새 검색

**결과**: Trace ID에 연결된 모든 Audit Log 확인 가능

---

### 시나리오 5: Validation 에러 처리

1. 운영자가 새 Mapping 자산 생성 (draft)
2. 상세 페이지에서 content 필드에 잘못된 JSON 입력:
   ```
   {invalid json
   ```
3. **Publish** 클릭
4. 백엔드 validation 실패 → HTTPException(400, detail="Invalid JSON in content field")
5. 화면 상단에 빨간색 Alert 박스 표시:
   ```
   ⚠️ Validation Error:
   Invalid JSON in content field
   ```
6. 운영자가 content 수정:
   ```json
   {"key": "value"}
   ```
7. **Save Draft** 클릭 → 성공
8. **Publish** 클릭 → 성공

**결과**: Validation 에러가 명확히 표시되고 수정 후 발행 가능

---

## 6. 프론트엔드 구현 가이드

### 6.1 디렉토리 구조

```
apps/web/src/app/admin/
├── assets/
│   ├── page.tsx              # Asset List
│   └── [assetId]/
│       └── page.tsx          # Asset Detail
├── inspector/
│   └── page.tsx              # Trace Inspector
└── layout.tsx                # Admin Layout (공통 헤더)

apps/web/src/components/admin/
├── AssetTable.tsx            # Asset List Table
├── AssetForm.tsx             # Asset Edit Form
├── SettingsTable.tsx         # Settings List Table
├── SettingEditModal.tsx      # Setting Edit Modal
├── AuditLogTable.tsx         # Audit Log Table
├── AuditLogDetailsModal.tsx  # Audit Log Details Modal
└── ValidationAlert.tsx       # Validation Error Alert
```

### 6.2 shadcn/ui 컴포넌트 사용

- **Table**: `@/components/ui/table`
- **Badge**: `@/components/ui/badge`
- **Button**: `@/components/ui/button`
- **Dialog/Modal**: `@/components/ui/dialog`
- **Alert**: `@/components/ui/alert`
- **Toast**: `@/components/ui/toast` + `useToast` hook
- **Textarea**: `@/components/ui/textarea`
- **Select**: `@/components/ui/select`

### 6.3 TanStack Query 사용

```typescript
// Asset List
const { data, isLoading } = useQuery({
  queryKey: ['assets', { type, status }],
  queryFn: () => fetchAssets({ type, status }),
});

// Asset Detail
const { data: asset } = useQuery({
  queryKey: ['asset', assetId],
  queryFn: () => fetchAsset(assetId),
});

// Update Asset
const updateMutation = useMutation({
  mutationFn: (data) => updateAsset(assetId, data),
  onSuccess: () => {
    queryClient.invalidateQueries(['asset', assetId]);
    toast({ title: 'Draft saved successfully' });
  },
  onError: (error) => {
    setValidationError(error.response.data.detail);
  },
});
```

### 6.4 네비게이션 추가

**파일**: `apps/web/src/components/NavTabs.tsx`

```typescript
const NAV_ITEMS = [
  // ... 기존 항목들
  { label: "Admin", href: "/admin/assets", adminOnly: true },
];
```

**파일**: `apps/web/src/app/admin/layout.tsx`

```typescript
// Admin 하위 탭 (Assets / Settings / Inspector)
const ADMIN_TABS = [
  { label: "Assets", href: "/admin/assets" },
  { label: "Settings", href: "/settings/operations" },
  { label: "Inspector", href: "/admin/inspector" },
];
```

---

## 7. 구현 우선순위

### P0 (필수)
1. **Assets Admin**: List, Detail, Create, Edit, Publish, Rollback
2. **Settings**: List, Edit, restart_required 표시
3. **Inspector**: Trace ID 검색, Audit Log 표시, parent_trace_id 연결

### P1 (가능하면)
1. **Settings**: 변경 이력 보기 (History 모달)
2. **Inspector**: OPS History 링크
3. **Assets**: 버전 히스토리 UI (현재는 버전 번호 입력 방식)

### P2 (향후)
1. **Assets**: Draft/Published 비교 Diff UI
2. **Assets**: 코드 에디터 (Monaco Editor)
3. **Settings**: 일괄 변경 (Bulk Update)
4. **Inspector**: 고급 필터 (시간 범위, resource_type 등)

---

## 8. 체크리스트

개발자는 구현 완료 후 다음을 확인해야 합니다:

- [ ] Assets List 화면에서 필터링 동작 확인
- [ ] Asset 생성 → 편집 → 발행 → 롤백 전체 플로우 테스트
- [ ] Published 자산 편집 시도 시 에러 메시지 확인
- [ ] Settings 편집 시 restart_required 경고 표시 확인
- [ ] Inspector에서 trace_id 검색 및 parent_trace_id 연결 확인
- [ ] 모든 validation 에러가 명확히 표시되는지 확인
- [ ] Toast 메시지가 3초 후 자동으로 닫히는지 확인
- [ ] 모든 API 호출이 ResponseEnvelope 구조를 따르는지 확인
- [ ] 백엔드 로그에 audit_log 생성 확인 (Settings 변경 시)

---

## 9. 참고 문서

- `AGENTS.md`: 프로젝트 규칙 및 기술 스택
- `apps/api/app/modules/asset_registry/router.py`: Asset API
- `apps/api/app/modules/operation_settings/router.py`: Settings API
- `apps/api/app/modules/audit_log/models.py`: Audit Log 모델
- `apps/web/src/components/NavTabs.tsx`: 네비게이션 구조
