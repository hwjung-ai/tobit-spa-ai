# 인증 & 권한 관리 시스템 구현 가이드

**작성일**: 2026-01-18
**상태**: Implementation In Progress
**예상 기간**: 2-3주

---

## 목차

1. [개요](#개요)
2. [현재 상태](#현재-상태)
3. [상세 구현 계획](#상세-구현-계획)
4. [각 Phase별 검증 절차](#각-phase별-검증-절차)
5. [트러블슈팅](#트러블슈팅)
6. [중단/재개 가이드](#중단재개-가이드)

---

## 개요

현재 프로젝트는 클라이언트가 제공하는 헤더를 무조건 신뢰하는 방식으로 운영 중입니다.
본 문서는 JWT 기반 인증과 RBAC(역할 기반 접근 제어)를 단계적으로 추가하는 방법을 설명합니다.

### 주요 특징

- **JWT 기반 인증**: Access Token (30분) + Refresh Token (7일)
- **RBAC**: Admin, Manager, Developer, Viewer 4가지 역할
- **Multi-tenancy**: 기존 `tenant_id` 활용
- **단계적 적용**: 필수 모듈부터 점진적 확산
- **개발 편의성**: 기본 테스트 계정 자동 생성

### 적용 범위

| 항목 | 현황 | 변경 후 |
|------|------|--------|
| DB | tenant_id, user_id 저장만 함 | **검증된** tenant_id, user_id |
| API | 모든 헤더 신뢰 | JWT 토큰 검증 필수 |
| 권한 | 없음 | 역할별 세분화 (4단계) |
| 로그인 | 없음 | JWT 기반 로그인 |

---

## 현재 상태

### 기존 인프라

✅ Multi-tenancy 인식 구조
✅ Request tracing (X-Trace-Id)
✅ Audit logging 시스템
✅ Middleware 기반 구조
✅ Database migration 시스템
✅ ResponseEnvelope 표준화

### 보안 취약점

❌ 클라이언트 헤더 무조건 신뢰
❌ 권한 검증 없음
❌ 사용자 관리 시스템 없음
❌ 로그인 UI 없음

---

## 상세 구현 계획

### Phase 1: Backend - 인증 기반 구축 (1주일)

#### 1.1 데이터베이스 모델 생성

**파일**: `apps/api/app/modules/auth/models.py`

**생성 항목**:
- `TbUser`: 사용자 계정 (email, password_hash, role, tenant_id)
- `TbRefreshToken`: Refresh token 저장소 (만료 관리)

**설계 요점**:
- email: unique index (사용자 식별)
- password_hash: bcrypt 해싱
- role: enum (ADMIN, MANAGER, DEVELOPER, VIEWER)
- tenant_id: multi-tenancy 격리
- is_active: soft delete 대신 사용
- last_login_at: 마지막 로그인 시간 추적

**스키마**:
```
TbUser
├─ id (UUID, PK)
├─ email (unique)
├─ username
├─ password_hash
├─ role (enum)
├─ tenant_id (FK index)
├─ is_active (bool)
├─ created_at
├─ updated_at
└─ last_login_at (nullable)

TbRefreshToken
├─ id (UUID, PK)
├─ user_id (FK)
├─ token_hash
├─ expires_at
├─ created_at
└─ revoked_at (nullable, soft delete)
```

#### 1.2 마이그레이션 파일

**파일**: `apps/api/alembic/versions/0031_add_auth_tables.py`

**작업**:
1. `tb_user` 테이블 생성
2. `tb_refresh_token` 테이블 생성
3. 기본 admin 사용자 생성 (email: admin@tobit.local, password: admin123)
4. 인덱스 생성 (email, tenant_id, user_id)

**실행**:
```bash
cd apps/api
alembic upgrade head
```

**검증**:
```bash
# PostgreSQL에서 테이블 확인
SELECT * FROM tb_user;
SELECT * FROM tb_refresh_token;
```

#### 1.3 보안 유틸리티

**파일**: `apps/api/core/security.py`

**기능**:
- `verify_password()`: 비밀번호 검증 (bcrypt)
- `get_password_hash()`: 비밀번호 해싱
- `create_access_token()`: JWT 생성 (30분 유효)
- `create_refresh_token()`: Refresh token 생성 (7일 유효)
- `decode_token()`: JWT 검증 및 디코딩

**설정값** (core/config.py에 추가):
```python
jwt_secret_key: str  # 환경변수로 관리
jwt_algorithm: str = "HS256"
access_token_expire_minutes: int = 30
refresh_token_expire_days: int = 7
```

#### 1.4 인증 의존성

**파일**: `apps/api/core/auth.py`

**기능**:
- `get_current_user()`: Authorization 헤더에서 토큰 추출 및 검증
- `get_current_active_user()`: 활성 사용자만 통과
- `require_role()`: 역할 기반 접근 제어 (데코레이터)

**사용 예시**:
```python
# 모든 인증된 사용자
@router.get("/data")
def get_data(user: TbUser = Depends(get_current_user)):
    pass

# DEVELOPER 이상 권한 필요
@router.post("/apis")
def create_api(user: TbUser = Depends(require_role(UserRole.DEVELOPER))):
    pass
```

**역할 계층**:
```
ADMIN (3) > MANAGER (2) > DEVELOPER (1) > VIEWER (0)
```

#### 1.5 인증 라우터

**파일**: `apps/api/app/modules/auth/router.py`

**엔드포인트**:

| 메서드 | 경로 | 요청 | 응답 | 설명 |
|-------|------|------|------|------|
| POST | `/auth/login` | email, password | access_token, refresh_token, user | 로그인 |
| POST | `/auth/refresh` | refresh_token | access_token | 토큰 갱신 |
| POST | `/auth/logout` | (Bearer token) | message | 로그아웃 |
| GET | `/auth/me` | (Bearer token) | user | 현재 사용자 정보 |

**로직**:
- `/login`: 이메일/비밀번호 검증 → 토큰 생성 → refresh token DB 저장 → last_login_at 갱신
- `/refresh`: refresh token 검증 → 새 access token 발급
- `/logout`: 모든 active refresh token 무효화
- `/me`: 현재 사용자 정보 반환

#### 1.6 Main 앱 등록

**파일**: `apps/api/main.py`

**추가 사항**:
```python
from apps.api.app.modules.auth import router as auth_router

app.include_router(auth_router.router)
```

#### 1.7 Middleware 업데이트

**파일**: `apps/api/core/middleware.py`

**변경 사항**:
- Authorization 헤더에서 토큰 추출
- 토큰 검증 성공 시 `tenant_id`, `user_id`를 로깅 컨텍스트에 설정
- 검증 실패해도 동작 계속 (비로그인 엔드포인트 지원)

#### 1.8 기존 라우터에 인증 적용

**적용 순서**:
1. **필수**: `/auth` (자체 인증 라우터)
2. **우선**: `/api-manager`, `/ui-creator`, `/cep-builder` (Builder 모듈)
3. **중요**: `/ops/ci/ask` (OPS AI)
4. **관리**: `/admin/*` (관리자 화면)
5. **일반**: `/documents`, `/threads` (Chat)
6. **선택**: `/data` (Data Explorer)

**적용 패턴**:
```python
# 읽기: 모든 인증된 사용자
@router.get("/apis")
def list_apis(user: TbUser = Depends(get_current_user)):
    # tenant_id = user.tenant_id 자동 사용

# 쓰기: DEVELOPER 이상
@router.post("/apis")
def create_api(user: TbUser = Depends(require_role(UserRole.DEVELOPER))):
    pass

# 관리: MANAGER 이상
@router.delete("/apis/{api_id}")
def delete_api(user: TbUser = Depends(require_role(UserRole.MANAGER))):
    pass
```

### Phase 2: Frontend - 인증 UI 구현 (1주일)

#### 2.1 Auth Context

**파일**: `apps/web/src/contexts/AuthContext.tsx`

**기능**:
- `user`: 현재 로그인 사용자 정보
- `isAuthenticated`: 인증 여부
- `login()`: 로그인 함수
- `logout()`: 로그아웃 함수
- `refreshToken()`: 토큰 갱신

**상태 관리**:
- localStorage에 `access_token`, `refresh_token` 저장
- 페이지 로드 시 토큰 확인

#### 2.2 API Client

**파일**: `apps/web/src/lib/apiClient.ts`

**기능**:
- `authenticatedFetch()`: 토큰 자동 추가
- 401 에러 시 자동 토큰 갱신 및 재시도
- 갱신 실패 시 로그인 페이지 리다이렉트

#### 2.3 로그인 페이지

**파일**: `apps/web/src/app/login/page.tsx`

**기능**:
- Email/Password 입력
- 로그인 버튼
- 에러 메시지 표시
- 성공 시 홈으로 리다이렉트

**기본 계정**:
- Email: admin@tobit.local
- Password: admin123

#### 2.4 Route Protection

**파일**: `apps/web/src/middleware.ts`

**동작**:
- 토큰 없음 + 로그인 페이지 아님 → /login 리다이렉트
- 토큰 있음 + 로그인 페이지 → / 리다이렉트

#### 2.5 Layout 업데이트

**파일**: `apps/web/src/app/layout.tsx`

**변경 사항**:
- 헤더에 사용자 정보 표시 (username, role)
- Logout 버튼 추가

#### 2.6 기존 페이지 업데이트

**변경 사항**:
- `normalizeHeaders()` 제거 (하드코딩된 X-Tenant-Id, X-User-Id)
- `fetch()` → `authenticatedFetch()` 교체
- 모든 API 호출에 토큰 자동 포함

**영향 파일**:
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/ops/page.tsx`
- `apps/web/src/app/documents/page.tsx`
- `apps/web/src/lib/adminUtils.ts`
- 기타 API 호출하는 모든 파일

### Phase 3: 통합 테스트 및 검증 (3-5일)

#### 3.1 Backend 테스트

**로그인 흐름**:
```bash
# 1. 로그인
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@tobit.local", "password": "admin123"}'
# 응답: access_token, refresh_token

# 2. 토큰으로 API 호출
TOKEN="<access_token>"
curl http://localhost:8000/api-manager/apis \
  -H "Authorization: Bearer $TOKEN"

# 3. 토큰 갱신
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# 4. 로그아웃
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

**권한 테스트**:
```bash
# VIEWER 토큰으로 쓰기 시도 → 403 Forbidden
curl -X POST http://localhost:8000/api-manager/apis \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**테넌트 격리 테스트**:
```bash
# t1 사용자가 t2 데이터 접근 → 403 또는 빈 결과
```

#### 3.2 Frontend 테스트

**로그인 플로우**:
1. http://localhost:3000 접속
2. /login 리다이렉트 확인
3. admin@tobit.local / admin123 로그인
4. / 리다이렉트 확인
5. 헤더에 사용자 정보 표시 확인

**토큰 저장**:
1. DevTools → Application → Local Storage
2. `access_token`, `refresh_token` 확인

**API 호출**:
1. Network 탭 열기
2. API 요청 확인
3. Authorization 헤더 포함 확인

**토큰 갱신**:
1. localStorage에서 access_token 제거 (만료 시뮬레이션)
2. API 호출 → 자동 갱신 확인

**로그아웃**:
1. Logout 버튼 클릭
2. /login 리다이렉트 확인
3. localStorage 비움 확인

#### 3.3 E2E 테스트

```bash
cd apps/web
npm run test:e2e
```

**테스트 시나리오**:
1. 로그인 → 홈으로 리다이렉트
2. API 호출 성공
3. 로그아웃 → 로그인 페이지로 리다이렉트
4. 로그인 없이 접근 → /login 리다이렉트

---

## 각 Phase별 검증 절차

### Phase 1 검증 (Backend)

**필수 확인 사항**:
- [ ] 마이그레이션 성공 (alembic upgrade head)
- [ ] admin 사용자 자동 생성
- [ ] /auth/login 엔드포인트 동작
- [ ] 토큰 생성 확인
- [ ] /auth/me 엔드포인트 동작
- [ ] /auth/refresh 엔드포인트 동작
- [ ] /auth/logout 엔드포인트 동작
- [ ] 권한 검증 (403 에러)

**검증 스크립트**:
```bash
# scripts/test_auth_backend.sh 작성 예정
```

### Phase 2 검증 (Frontend)

**필수 확인 사항**:
- [ ] 로그인 페이지 렌더링
- [ ] 로그인 성공 → 홈 리다이렉트
- [ ] 토큰 localStorage 저장
- [ ] API 요청에 Authorization 헤더 포함
- [ ] 401 시 자동 갱신
- [ ] 로그아웃 → /login 리다이렉트

### Phase 3 검증 (통합)

**필수 확인 사항**:
- [ ] E2E 테스트 모두 통과
- [ ] 권한별 접근 제어 동작
- [ ] 테넌트 격리 동작
- [ ] 기존 기능 모두 동작

---

## 트러블슈팅

### Backend 문제

**문제**: 마이그레이션 실패
```
알렉믹 오류: revision xxxxx not found
```
**해결**: 현재 최신 버전 확인 후 down_revision 수정
```bash
alembic current  # 현재 버전 확인
```

**문제**: `ModuleNotFoundError: No module named 'passlib'`
**해결**: 의존성 설치
```bash
pip install passlib python-jose
```

**문제**: JWT 토큰 검증 실패
**해결**: SECRET_KEY 확인
```bash
# .env 파일에서 JWT_SECRET_KEY 설정
JWT_SECRET_KEY=your-secret-key-here
```

### Frontend 문제

**문제**: CORS 에러
**해결**: API 서버의 CORS 설정 확인
```python
# apps/api/main.py에서 CORS 미들웨어 설정
```

**문제**: 토큰이 localStorage에 저장 안 됨
**해결**: 개발자 도구 → Application → Storage 확인

**문제**: 자동 토큰 갱신이 안 됨
**해결**: apiClient.ts의 401 처리 로직 확인

---

## 중단/재개 가이드

### 중단 전 체크리스트

1. **현재 진행 상황 기록**
   ```
   예: "Phase 1-2까지 완료, Phase 1-3 보안 유틸리티 구현 중"
   ```

2. **생성한 파일 목록**
   ```
   - apps/api/app/modules/auth/models.py ✅
   - apps/api/app/modules/auth/router.py ✅
   - apps/api/core/security.py ✅
   - apps/api/core/auth.py ✅
   - apps/api/alembic/versions/0031_add_auth_tables.py ✅
   ```

3. **진행 중인 파일**
   ```
   (현재 편집 중인 파일 기록)
   ```

4. **다음 할 일**
   ```
   (중단 시점 다음 단계 명시)
   ```

### 재개 방법

1. **진행 상황 확인**
   ```bash
   ls -la apps/api/app/modules/auth/
   git status  # 변경 사항 확인
   ```

2. **마이그레이션 상태 확인**
   ```bash
   cd apps/api
   alembic current  # 현재 버전 확인
   ```

3. **테스트 서버 시작**
   ```bash
   cd apps/api
   python -m uvicorn apps.api.main:app --reload
   ```

4. **진행 상황 문서 업데이트**
   ```
   이 파일의 "현재 진행 상황" 섹션 업데이트
   ```

---

## 현재 진행 상황

**최종 업데이트**: 2026-01-18
**상태**: Phase 1 & Phase 2 구현 완료 (100%), 테스트 단계 진입

### 완료된 항목 ✅

#### Phase 1: Backend (완료)
- [x] 상세 설계안 작성 (`docs/AUTH_IMPLEMENTATION_GUIDE.md`)
- [x] 데이터베이스 모델 생성 (`apps/api/app/modules/auth/models.py`)
  - TbUser: 사용자 계정 테이블 모델
  - TbRefreshToken: Refresh token 저장소 모델
  - UserRole enum: ADMIN, MANAGER, DEVELOPER, VIEWER
- [x] 마이그레이션 파일 생성 (`apps/api/alembic/versions/0031_add_auth_tables.py`)
  - tb_user, tb_refresh_token 테이블 생성
  - 기본 admin 사용자 자동 생성 (admin@tobit.local / admin123)
  - 인덱스 생성 (email unique, tenant_id, user_id)
- [x] 보안 유틸리티 구현 (`apps/api/core/security.py`)
  - verify_password(), get_password_hash() - bcrypt 기반
  - create_access_token(), create_refresh_token() - JWT
  - decode_token() - 토큰 검증
- [x] 인증 의존성 구현 (`apps/api/core/auth.py`)
  - get_current_user() - HTTPBearer 토큰 검증
  - require_role() - 역할 기반 접근 제어
  - 자동 권한 계층화 (ADMIN > MANAGER > DEVELOPER > VIEWER)
- [x] 인증 라우터 구현 (`apps/api/app/modules/auth/router.py`)
  - POST /auth/login (email, password) → access_token, refresh_token, user
  - POST /auth/refresh (refresh_token) → 새 access_token
  - POST /auth/logout → refresh token 무효화
  - GET /auth/me → 현재 사용자 정보
- [x] Config 업데이트 (`apps/api/core/config.py`)
  - JWT 설정 추가 (secret_key, algorithm, expiry)
  - auth_enabled 플래그
- [x] Main.py 업데이트
  - auth router 등록
  - 마이그레이션 버전 0031로 업데이트
- [x] Requirements.txt 업데이트
  - passlib[bcrypt]
  - python-jose[cryptography]

#### Phase 2: Frontend (완료)
- [x] Auth Context 구현 (`apps/web/src/contexts/AuthContext.tsx`)
  - useAuth() hook - 전역 인증 상태
  - 토큰 저장/로드 (localStorage)
  - login(), logout(), refreshToken() 함수
  - isLoading, isAuthenticated 상태
  - 페이지 로드 시 토큰 자동 검증
- [x] API Client 구현 (`apps/web/src/lib/apiClient.ts`)
  - authenticatedFetch() - 토큰 자동 추가
  - 401 응답 시 자동 토큰 갱신 + 재시도
  - 갱신 실패 시 로그인 페이지 리다이렉트
  - fetchApi() - 공개 엔드포인트용 (로그인 전)
- [x] 로그인 페이지 (`apps/web/src/app/login/page.tsx`)
  - Email/Password 입력 폼
  - 로그인 버튼 및 로딩 상태
  - 에러 메시지 표시
  - 데모 자격증명 표시
- [x] Providers 업데이트 (`apps/web/src/app/providers.tsx`)
  - AuthProvider 통합
  - QueryClientProvider 안에 AuthProvider 포함
- [x] Layout 업데이트 (`apps/web/src/app/layout.tsx`)
  - HeaderUserMenu 컴포넌트 임포트 및 추가
  - 헤더에 사용자 메뉴 표시
- [x] HeaderUserMenu 컴포넌트 생성 (`apps/web/src/components/HeaderUserMenu.tsx`)
  - 사용자 이름, 역할 표시
  - 드롭다운 메뉴 (Radix UI)
  - 로그아웃 버튼
  - 역할별 컬러 표시
  - 미인증 사용자는 자동 숨김
- [x] 기존 페이지 API 호출 모두 업데이트 ✅
  - `apps/web/src/app/page.tsx` - authenticatedFetch 전환
  - `apps/web/src/app/documents/page.tsx` - authenticatedFetch 전환
  - `apps/web/src/app/ops/page.tsx` - authenticatedFetch 전환
  - normalizeHeaders 함수 모두 제거
  - 하드코딩된 X-Tenant-Id, X-User-Id 헤더 제거
  - EventSource 스트리밍에 토큰 추가

### 진행 중 항목 🔄
- [🔄] Backend: 마이그레이션 실행 및 검증
- [ ] Backend: curl로 인증 테스트
- [ ] Frontend: E2E 로그인 플로우 검증

### 다음 단계
1. Backend 마이그레이션 실행 및 검증
2. curl 스크립트로 전체 인증 플로우 테스트
3. 프론트엔드 로그인 플로우 테스트
4. 최종 E2E 검증

---

## 참고 자료

- JWT: https://tools.ietf.org/html/rfc7519
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- SQLModel: https://sqlmodel.tiangolo.com/
- Passlib: https://passlib.readthedocs.io/

