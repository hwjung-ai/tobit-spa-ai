# Tobit SPA AI - 테스트 구조 표준 가이드

## 1. 개요

이 문서는 Tobit SPA AI 프로젝트의 전체 테스트 구조, 실행 방법, 결과 저장 위치, `data-testid` 네이밍 규칙을 표준화한 가이드입니다. 모든 테스트는 이 문서의 규칙을 따라야 합니다.

---

## 2. 테스트 구조 (전체 맵)

```
tobit-spa-ai/
├── apps/
│   ├── api/
│   │   ├── tests/                          # 백엔드 유닛 테스트 (FastAPI)
│   │   │   ├── unit/                       # 단위 테스트 (Service, CRUD, Helper)
│   │   │   ├── integration/                # 통합 테스트 (DB, 외부 API 연동)
│   │   │   ├── conftest.py                 # pytest fixtures
│   │   │   ├── test_security*.py           # 보안 테스트
│   │   │   ├── test_ui_contract.py         # UI Contract 테스트
│   │   │   └── ...
│   │   └── pytest.ini                      # pytest 설정 파일
│   │
│   └── web/
│       ├── tests-e2e/                      # 프론트엔드 E2E 테스트 (Playwright)
│       ├── playwright.config.ts            # Playwright 설정 파일
│       └── package.json                    # test:e2e 스크립트 포함
│
├── tests/                                   # 프로젝트 레벨 통합/E2E 테스트
│   ├── ops_ci_api/                         # CI API 통합 테스트
│   └── ops_e2e/                            # OPS E2E 테스트
│
├── artifacts/                              # 테스트 결과 저장소 (JUnit, JSON)
└── test-results/                           # Playwright 테스트 결과
```

---

## 3. 테스트 정의 및 분류

### 3.1 백엔드 유닛 테스트 (Unit Tests)
- **위치**: `apps/api/tests/`
- **목적**: 개별 함수, 클래스, 메서드의 동작을 독립적으로 테스트
- **테스트 대상**:
  - Service 계층 비즈니스 로직
  - CRUD/Repository 계층 데이터 접근 로직
  - Helper/Utility 함수
  - API 엔드포인트 단위 테스트 (Mock 사용)
- **실행 도구**: pytest
- **실행 명령어**:
  ```bash
  # apps/api 디렉토리에서
  pytest tests/                           # 전체 테스트 실행
  pytest tests/unit/                      # 단위 테스트만 실행
  pytest tests/unit/test_api_manager.py   # 특정 파일 테스트
  pytest tests/unit/test_api_manager.py::test_func  # 특정 함수 테스트
  pytest -v                               # Verbose 모드
  pytest -k "test_api"                    # 패턴 매칭 필터링
  pytest --tb=short                       # 간략한 traceback
  ```
- **Makefile 명령어**: `make api-test`

### 3.2 백엔드 통합 테스트 (Integration Tests)
- **위치**: `apps/api/tests/integration/`, `tests/ops_ci_api/`
- **목적**: 여러 컴포넌트/서비스가 함께 동작할 때의 통합 동작을 테스트
- **테스트 대상**:
  - DB 연동 (PostgreSQL, Neo4j, Redis)
  - 외부 API 연동
  - CI Orchestrator 전체 흐름
  - API 엔드포인트 통합 테스트 (실제 DB/Redis 사용)
- **실행 도구**: pytest
- **실행 명령어**:
  ```bash
  # apps/api 디렉토리에서
  pytest tests/integration/                # 통합 테스트만 실행

  # 프로젝트 루트에서
  pytest tests/ops_ci_api/                 # CI API 통합 테스트
  ```
- **Makefile 명령어**: `make api-test`

### 3.3 백엔드 E2E 테스트 (End-to-End Tests)
- **위치**: `tests/ops_e2e/`
- **목적**: 사용자 시나리오 기반 전체 흐름 테스트
- **테스트 대상**:
  - CI Orchestrator 전체 워크플로우
  - 성능 프로파일링
  - 회귀 테스트 (Regression)
  - Stage Executor 동작
- **실행 도구**: pytest
- **실행 명령어**:
  ```bash
  # 프로젝트 루트에서
  pytest tests/ops_e2e/                   # 전체 OPS E2E 테스트
  ```

### 3.4 프론트엔드 E2E 테스트 (Frontend E2E Tests)
- **위치**: `apps/web/tests-e2e/`
- **목적**: 실제 브라우저에서 사용자 상호작용 테스트
- **테스트 대상**:
  - Inspector 흐름 (질문 입력 → 답변 확인)
  - RCA (Root Cause Analysis) 기능
  - UI Screen 렌더링 및 상호작용
  - Screen Editor (편집, 미리보기, 게시)
  - Regression Watch 기능
  - 로그인/인증 흐름
- **실행 도구**: Playwright
- **실행 명령어**:
  ```bash
  # apps/web 디렉토리에서
  npm run test:e2e                        # 전체 E2E 테스트 실행
  npx playwright test inspector_e2e.spec.ts  # 특정 테스트 파일 실행
  npx playwright test --ui                # UI 모드 (디버깅용)
  npx playwright test --headed            # 헤드풀 모드 (브라우저 표시)
  npx playwright test -g "inspector"      # 특정 테스트만 실행
  ```
- **Makefile 명령어**: `make web-test-e2e`

### 3.5 보안 테스트 (Security Tests)
- **위치**: `apps/api/tests/test_security*.py`, `test_encryption.py`, `test_permissions.py`, `test_api_keys.py`
- **목적**: 보안 관련 기능 테스트
- **테스트 대상**:
  - 보안 헤더 (HSTS, CSP, X-Frame-Options, 등)
  - HTTPS/CORS 설정
  - CSRF 보호
  - 암호화/복호화 (이메일, 비밀번호 등 민감정보)
  - 접근 제어 (RBAC)
  - API 키 생성/검증/폐기
  - JWT 토큰 생성/검증
- **실행 도구**: pytest
- **실행 명령어**:
  ```bash
  # apps/api 디렉토리에서
  pytest tests/test_security*.py -v
  ```

---

## 4. 테스트 결과 저장소 (Artifacts)

| 저장소 | 형식 | 용도 |
|--------|------|------|
| `artifacts/junit.xml` | JUnit XML | CI/CD 파이프라인 테스트 결과 통합 |
| `artifacts/ops_ci_api_summary.json` | JSON | CI Orchestrator API 테스트 요약 |
| `artifacts/ops_e2e_summary.json` | JSON | OPS E2E 테스트 요약 |
| `artifacts/ops_ci_api_raw/` | JSON | API 테스트 원시 데이터 (디버깅용) |
| `test-results/playwright/` | HTML/스크린샷/트레이스 | Playwright E2E 테스트 결과 |

---

## 5. 테스트 설정 파일

### 5.1 pytest.ini (`apps/api/pytest.ini`)
```ini
[pytest]
pythonpath = .
testpaths = tests
```

### 5.2 playwright.config.ts (`apps/web/playwright.config.ts`)
```typescript
export default defineConfig({
  testDir: './tests-e2e',
  outputDir: '../../test-results/playwright',
  reporter: 'html',
  timeout: 300000,
});
```

---

## 6. 테스트 실행 가이드 (명령어 정리)

### 6.1 전체 테스트 실행
```bash
make api-test                           # 백엔드 유닛/통합 테스트
make web-test-e2e                       # 프론트엔드 E2E 테스트
pytest tests/ops_e2e/                   # 백엔드 E2E 테스트
```

### 6.2 특정 카테고리 테스트 실행
```bash
cd apps/api && pytest tests/unit/                     # 백엔드 유닛 테스트만
cd apps/api && pytest tests/integration/              # 백엔드 통합 테스트만
pytest tests/ops_ci_api/                              # CI API 통합 테스트만
cd apps/web && npm run test:e2e                       # 프론트엔드 E2E 테스트만
cd apps/api && pytest tests/test_security*.py         # 보안 테스트만
```

### 6.3 디버깅
```bash
pytest -v                               # Verbose 모드
pytest --tb=short                       # 간략한 traceback
pytest --pdb                            # 디버거 실행 (실패 시)
npx playwright test --ui                # Playwright UI 모드
npx playwright test --headed            # Playwright 헤드풀 모드
npx playwright show-report              # Playwright 결과 보기
```

---

## 7. 테스트 작성 규칙

### 7.1 백엔드 테스트 작성 규칙 (pytest)
1. **테스트 파일 명명**: 반드시 `test_*.py` 형식 준수
2. **비동기 함수**: `@pytest.mark.asyncio` 데코레이터 필수
   ```python
   import pytest

   @pytest.mark.asyncio
   async def test_async_function():
       result = await async_function()
       assert result is not None
   ```
3. **Pydantic 모델 테스트**: 실제 필드 구조와 일치하도록 작성
4. **Mock 객체 사용**: `AsyncMock`(비동기) 또는 `Mock`(동기) 사용
5. **Fixture 사용**: `conftest.py`에 공통 fixture 정의
6. **테스트 카테고리 분류**:
   - 단위 테스트: `tests/unit/test_*.py`
   - 통합 테스트: `tests/integration/test_*.py`
   - API 엔드포인트 테스트: `tests/test_*_router.py`
   - 비즈니스 로직 테스트: `tests/test_*_service.py`
   - CRUD 테스트: `tests/test_*_crud.py`

### 7.2 프론트엔드 E2E 테스트 작성 규칙 (Playwright)
1. **테스트 파일 명명**: `*_e2e.spec.ts` 또는 `*.spec.ts` 형식
2. **data-testid 사용**: UI 컴포넌트 식별자는 반드시 `data-testid` 속성 사용 (섹션 8 참조)
   ```typescript
   await page.getByTestId('submit-button').click();
   ```
3. **페이지 객체 모델 (Page Object Model)**: 복잡한 페이지는 별도 파일로 분리
4. **명확한 테스트 이름**: `describe`, `test` 블록에 명확한 이름 사용
5. **적절한 대기 및 확인**: `expect()`를 사용하여 상태 확인
   ```typescript
   await expect(page.getByTestId('answer-block')).toBeVisible();
   await expect(page.getByTestId('loading-spinner')).not.toBeVisible();
   ```
6. **테스트 격리**: 각 테스트는 독립적으로 실행 가능해야 함

### 7.3 테스트 커버리지 목표
- **백엔드**: 주요 비즈니스 로직 80% 이상 커버리지 권장
- **프론트엔드**: 주요 사용자 흐름 100% 커버리지 필수
- **보안**: 모든 보안 관련 기능 100% 커버리지 필수

---

## 8. data-testid 네이밍 규칙

### 네이밍 형식

```
{area}-{component}-{purpose}-{identifier}
```

- **area**: 기능 영역 (e.g., `screen`, `admin`, `component`, `layout`)
- **component**: 컴포넌트 타입 (e.g., `button`, `input`, `table`, `modal`)
- **purpose**: 역할 (e.g., `create`, `edit`, `delete`, `publish`)
- **identifier**: 선택, 특정 식별자 (e.g., asset ID, screen ID)

### 영역별 예시

#### Screen Management
```
screen-asset-{asset_id}           # Screen asset card
link-screen-{asset_id}            # Link to edit screen
btn-edit-{asset_id}               # Edit button
btn-publish-{asset_id}            # Publish button
btn-rollback-{asset_id}           # Rollback to draft button
status-badge-{asset_id}           # Status badge
```

#### Screen Editor
```
input-screen-name                 # Screen name input
textarea-screen-description       # Screen description textarea
textarea-schema-json              # Schema JSON editor
btn-save-draft                    # Save draft button
btn-publish-screen                # Publish button
btn-rollback-screen               # Rollback button
```

#### Admin Panel
```
btn-create-screen                 # Create new screen button
modal-create-screen               # Create screen modal
input-screen-id                   # Screen ID input in create modal
input-screen-name                 # Screen name input in create modal
input-screen-description          # Screen description input
btn-cancel-create                 # Cancel create button
btn-confirm-create                # Confirm create button
input-search-screens              # Search screens input
select-filter-status              # Status filter dropdown
```

#### Layout Renderers
```
layout-grid                       # Grid layout container
layout-stack-vertical             # Vertical stack layout
layout-stack-horizontal           # Horizontal stack layout
layout-list                       # List layout container
layout-modal                      # Modal layout container
layout-default                    # Default/fallback layout
grid-item-{component_id}          # Individual grid item
list-item-{component_id}          # Individual list item
```

#### Components
```
component-text-{component_id}     # Text component
component-markdown-{component_id} # Markdown component
component-button-{component_id}   # Button component
component-input-{component_id}    # Input component
component-table-{component_id}    # Table component
component-chart-{component_id}    # Chart component
component-badge-{component_id}    # Badge component
component-tabs-{component_id}     # Tabs component
component-modal-{component_id}    # Modal component
component-keyvalue-{component_id} # Key-value component
component-divider-{component_id}  # Divider component
```

#### Screen Renderer
```
screen-renderer-{screen_id}       # Main screen renderer container
```

### Playwright에서 사용 예시

```typescript
await page.locator('[data-testid="btn-create-screen"]').click();
await page.locator('[data-testid="input-screen-id"]').fill('dashboard_main');
await page.locator('[data-testid="input-screen-name"]').fill('Main Dashboard');
await page.locator('[data-testid="btn-confirm-create"]').click();
```

### 규칙

1. **소문자 + 하이픈**: camelCase/snake_case 사용 금지
2. **고유성**: 테스트에서 유일하게 식별 가능할 만큼 구체적으로 작성
3. **안정성**: 리렌더링 시 변경되는 인덱스/동적 ID 사용 금지
4. **비간섭**: `data-testid`는 스타일이나 기능에 영향을 주지 않아야 함
