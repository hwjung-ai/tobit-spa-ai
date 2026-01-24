# Screen Editor Authentication & API Fixes - Summary

## Problem Statement
사용자가 Screen Editor에서 Save Draft를 시도할 때 "Missing authorization header" 에러가 발생했습니다.

## Root Cause Analysis
1. **유효하지 않은 토큰**: localStorage에 access_token이 없어서 API 요청이 토큰 없이 전송됨
2. **Fallback 엔드포인트 문제**: loadScreen에서 `/ui-defs` 실패 시 fallback이 bare `fetch()`를 사용해 토큰이 전송되지 않음
3. **Publish/Rollback 엔드포인트**: bare `fetch()` 사용으로 토큰이 전송되지 않음

## Changes Made

### 1. Frontend API Client Enhancement (`apps/web/src/lib/adminUtils.ts`)
**목적**: 모든 API 요청에 Authorization header 추가

```typescript
// Before: 토큰 없음
const response = await fetch(url, {
  headers: { "Content-Type": "application/json" }
});

// After: 토큰 포함
const token = localStorage.getItem("access_token");
if (token) {
  headers["Authorization"] = `Bearer ${token}`;
}
```

**추가 기능**:
- 401 Unauthorized 에러 시 상세한 진단 메시지 출력
- 토큰 부재 시 명확한 경고 메시지
- 스테일 토큰 자동 정리

### 2. Screen Editor State Management (`apps/web/src/lib/ui-screen/editor-state.ts`)

**수정 1**: Publish 엔드포인트에 fetchApi 사용
```typescript
// Before
const response = await fetch(`/asset-registry/assets/${currentAssetId}/publish`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({}),
});

// After
await fetchApi(`/asset-registry/assets/${currentAssetId}/publish`, {
  method: "POST",
  body: JSON.stringify({}),
});
```

**수정 2**: Rollback 엔드포인트에 fetchApi 사용
```typescript
// Before
await fetch(`/asset-registry/assets/${currentAssetId}/unpublish`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({}),
});

// After
await fetchApi(`/asset-registry/assets/${currentAssetId}/unpublish`, {
  method: "POST",
  body: JSON.stringify({}),
});
```

**수정 3**: LoadScreen Fallback에 fetchApi 사용
```typescript
// Before
const response = await fetch(`/asset-registry/assets/${assetId}`);

// After
const response = await fetchApi(`/asset-registry/assets/${assetId}`);
```

### 3. ScreenEditor Component (`apps/web/src/components/admin/screen-editor/ScreenEditor.tsx`)
**수정**: useAuth 훅 제거

- 컴포넌트가 AuthProvider 내부에 있으므로 불필요
- 불필요한 복잡성 제거
- isDirty, canPublish, canRollback 상태는 editorState에서 직접 계산

## 인증 흐름

```
1. 사용자 로그인 (/login)
   ↓
2. POST /auth/login → access_token 반환
   ↓
3. localStorage에 token 저장
   ↓
4. API 요청 시 fetchApi() 사용
   ↓
5. Authorization: Bearer {token} header 자동 추가
   ↓
6. 백엔드에서 토큰 검증
   ↓
7. 요청 처리 또는 401 반환
```

## 테스트

### Playwright E2E Tests (`apps/web/tests-e2e/screen-editor.spec.ts`)
✓ 스크린 로드 테스트
✓ 비주얼 에디터 오픈 테스트
✓ 인증 상태 로깅 검증
✓ Save Draft 기능 테스트
✓ 미인증 사용자 처리 테스트
✓ 토큰 부재 시 에러 처리 테스트

### Pytest Backend Tests (`apps/api/tests/test_screen_editor_auth.py`)
✓ 토큰 없이 요청 시 401 반환
✓ 유효한 토큰으로 요청 성공
✓ 잘못된 토큰 거부
✓ 누락된 Authorization header 에러 메시지
✓ Bearer 토큰 형식 검증

## 사용자 실행 단계

### 1단계: 로그인 확인
```
URL: http://localhost:3000/login
Email: admin@tobit.local
Password: admin123
```

### 2단계: 토큰 저장 확인
```javascript
// 브라우저 DevTools Console에서:
localStorage.getItem('access_token')
// JWT 토큰 출력 확인 (eyJhbGc...)
```

### 3단계: 스크린 편집
1. `/admin/screens`로 이동
2. 스크린 선택
3. Visual Editor 클릭
4. 컴포넌트 수정
5. "Save Draft" 클릭

### 4단계: 콘솔 로그 확인
```
[API] Adding Authorization header with token
[API] Fetching: /asset-registry/assets/... with method: PUT
[EDITOR] Screen saved successfully
```

## 진단 로그

### API 요청 성공 시
```
[API] Adding Authorization header with token
[API] Fetching: /asset-registry/assets/screen-123 with method: POST
```

### 토큰 부재 시
```
[API] ⚠️ No token found in localStorage for endpoint: /asset-registry/assets
[API] User may not be logged in. Visit /login to authenticate.
```

### 인증 실패 시
```
[API] ❌ Authentication failed (401 Unauthorized)
[API] Possible causes:
[API]   1. User not logged in - visit /login
[API]   2. Token expired - log in again
[API]   3. Invalid token in localStorage
```

## 주요 개선사항

| 항목 | Before | After |
|------|--------|-------|
| Save Draft 인증 | ❌ 토큰 없음 | ✅ Bearer token 포함 |
| Publish 인증 | ❌ 토큰 없음 | ✅ Bearer token 포함 |
| Rollback 인증 | ❌ 토큰 없음 | ✅ Bearer token 포함 |
| Fallback 로드 | ❌ 토큰 없음 | ✅ Bearer token 포함 |
| 에러 메시지 | ❌ 불명확 | ✅ 명확한 진단 정보 |
| 테스트 커버리지 | ❌ 없음 | ✅ E2E + Unit tests |

## 파일 변경 사항

```
apps/web/src/lib/adminUtils.ts                    (Enhanced authentication)
apps/web/src/lib/ui-screen/editor-state.ts       (Fixed publish/rollback/fallback)
apps/web/src/components/admin/screen-editor/ScreenEditor.tsx (Removed useAuth)
apps/web/tests-e2e/screen-editor.spec.ts         (New E2E tests)
apps/api/tests/test_screen_editor_auth.py        (New backend tests)
```

## 다음 단계

1. ✅ 콘솔 로그로 인증 상태 확인
2. ✅ 테스트 실행: `npm run test:e2e` (프론트엔드)
3. ✅ 테스트 실행: `pytest tests/test_screen_editor_auth.py` (백엔드)
4. ✅ 수동 테스트: Save Draft → Publish → Rollback 전체 흐름 확인

## 트러블슈팅

### 여전히 401 에러가 나는 경우
1. 로그아웃 후 다시 로그인
2. 브라우저 캐시 삭제
3. `localStorage.clear()` 실행 후 재로그인

### 토큰이 저장되지 않는 경우
1. 프라이빗/시크릿 모드 사용 중인지 확인
2. 브라우저 개발자 도구 → Application → Storage에서 localStorage 확인
3. 로그인 응답 200 상태 확인

### 스크린이 로드되지 않는 경우
1. 네트워크 탭에서 API 요청 확인
2. 요청 헤더에 Authorization 있는지 확인
3. 백엔드 로그에서 토큰 검증 에러 확인
