. # Tobit SPA AI - 테스트 구조 표준 가이드

## 1. 개요

이 문서는 Tobit SPA AI 프로젝트의 전체 테스트 구조, 실행 방법, 결과 저장 위치 등을 표준화한 가이드입니다. 모든 테스트는 이 문서의 규칙을 따라야 합니다.

---

## 2. 테스트 구조 (전체 맵)

```
tobit-spa-ai/
├── apps/
│   ├── api/
│   │   ├── tests/                          # 백엔드 유닛 테스트 (FastAPI)
│   │   │   ├── unit/                       # 단위 테스트 (Service, CRUD, Helper)
│   │   │   │   ├── test_api_manager.py
│   │   │   │   └── test_document_processor.py
│   │   │   ├── integration/                # 통합 테스트 (DB, 외부 API 연동)
│   │   │   │   └── __init__.py             # (비어 있음 - 향후 추가 예정)
│   │   │   ├── conftest.py                 # pytest fixtures
│   │   │   ├── test_api_keys.py            # API 키 관리 테스트
│   │   │   ├── test_audit_log.py           # 감사 로그 테스트
│   │   │   ├── test_ci_ask_pipeline.py     # CI Ask 파이프라인 테스트
│   │   │   ├── test_ci_runner_tool_contracts.py  # Tool Contract 테스트
│   │   │   ├── test_encryption.py          # 암호화 테스트
│   │   │   ├── test_health.py              # 헬스 체크 테스트
│   │   │   ├── test_ops_executor_tool_contracts.py  # Executor Tool Contract
│   │   │   ├── test_permissions.py         # 권한 관리 테스트
│   │   │   ├── test_security_headers.py    # 보안 헤더 테스트
│   │   │   ├── test_ui_contract.py         # UI Contract 테스트 (20개)
│   │   │   └── ... (기타 테스트 파일)
│   │   └── pytest.ini                      # pytest 설정 파일
│   │
│   └── web/
│       ├── tests-e2e/                      # 프론트엔드 E2E 테스트 (Playwright)
│       │   ├── inspector_e2e.spec.ts       # Inspector 흐름 테스트
│       │   ├── rca_comprehensive_test.spec.ts  # RCA 종합 테스트
│       │   ├── screen-editor.spec.ts       # Screen Editor 테스트
│       │   ├── u3_2_publish_gate.spec.ts   # Publish Gate 테스트
│       │   ├── ui_screen_with_actions_e2e.spec.ts  # UI Screen Actions 테스트
│       │   └── ... (22개 테스트 파일)
│       ├── playwright.config.ts            # Playwright 설정 파일
│       └── package.json                    # test:e2e 스크립트 포함
│
├── tests/                                   # 프로젝트 레벨 통합/E2E 테스트
│   ├── test_asset_importers.py              # Asset Importer 테스트
│   ├── ops_ci_api/                         # CI API 통합 테스트
│   │   ├── conftest.py
│   │   ├── test_ops_ci_api.py              # CI Orchestrator API 테스트
│   │   └── test_ops_ci_ask_api.py          # CI Ask API 테스트
│   └── ops_e2e/                            # OPS E2E 테스트
│       ├── conftest.py
│       ├── test_orchestration_e2e.py       # 오케스트레이션 E2E 테스트
│       ├── test_performance_profiling.py   # 성능 프로파일링 테스트
│       ├── test_regression_e2e.py          # 회귀 테스트
│       └── test_stage_executor.py          # Stage Executor 테스트
│
├── artifacts/                              # 테스트 결과 저장소 (JUnit, JSON)
│   ├── junit.xml                           # JUnit 형식 테스트 결과 (CI 통합용)
│   ├── ops_ci_api_summary.json             # CI API 테스트 요약
│   ├── ops_e2e_summary.json                # OPS E2E 테스트 요약
│   ├── ops_ci_api_raw/                     # CI API 원시 데이터
│   │   ├── ambiguous_integration.json
│   │   ├── history_events.json
│   │   ├── list_servers.json
│   │   ├── metric_cpu_usage.json
│   │   ├── multi_step_app_history.json
│   │   └── ...
│   └── e2e_raw/                            # E2E 테스트 원시 데이터
│
└── test-results/                           # Playwright 테스트 결과
    └── playwright/                         # Playwright HTML 리포트, 스크린샷, 트레이스
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
  pytest tests/ops_ci_api/test_ops_ci_api.py
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
  pytest tests/ops_e2e/test_orchestration_e2e.py
  pytest tests/ops_e2e/test_performance_profiling.py
  ```
- **Makefile 명령어**: (추가 필요)

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
  
  # 특정 테스트 파일 실행
  npx playwright test inspector_e2e.spec.ts
  npx playwright test ui_screen_with_actions_e2e.spec.ts
  
  # UI 모드 (디버깅용)
  npx playwright test --ui
  
  # 헤드풀 모드 (브라우저 표시)
  npx playwright test --headed
  
  # 특정 테스트만 실행
  npx playwright test -g "inspector"
  ```
- **Makefile 명령어**: `make web-test` (현재는 npm test와 동일, 개선 필요)

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
  pytest tests/test_encryption.py -v
  pytest tests/test_permissions.py -v
  pytest tests/test_api_keys.py -v
  ```

---

## 4. 테스트 결과 저장소 (Artifacts)

### 4.1 JUnit XML (`artifacts/junit.xml`)
- **용도**: CI/CD 파이프라인 테스트 결과 통합
- **형식**: JUnit XML 형식
- **생성 명령어**:
  ```bash
  # apps/api 디렉토리에서
  pytest --junitxml=../../artifacts/junit.xml tests/
  ```

### 4.2 CI API 테스트 결과 (`artifacts/ops_ci_api_summary.json`)
- **용도**: CI Orchestrator API 테스트 요약
- **형식**: JSON
- **생성**: 자동 생성 (pytest 플러그인 또는 커스텀 리포터)

### 4.3 OPS E2E 테스트 결과 (`artifacts/ops_e2e_summary.json`)
- **용도**: OPS E2E 테스트 요약
- **형식**: JSON
- **생성**: 자동 생성

### 4.4 원시 데이터 (`artifacts/ops_ci_api_raw/`, `artifacts/e2e_raw/`)
- **용도**: 테스트 실행 중 생성된 원시 데이터 저장 (디버깅용)
- **형식**: JSON
- **내용**: 
  - API 요청/응답 로그
  - 테스트 시나리오 데이터
  - 추적 로그

### 4.5 Playwright 결과 (`test-results/playwright/`)
- **용도**: Playwright E2E 테스트 결과
- **형식**: HTML 리포트, 스크린샷, 트레이스 파일
- **생성 명령어**:
  ```bash
  # apps/web 디렉토리에서
  npm run test:e2e
  
  # 결과 보기
  npx playwright show-report test-results/playwright
  ```
- **설정**: `playwright.config.ts`의 `outputDir` 설정

---

## 5. 테스트 설정 파일

### 5.1 pytest.ini (`apps/api/pytest.ini`)
```ini
[pytest]
pythonpath = .
testpaths = tests
```
- **현재 문제**: `testpaths = tests`로 설정되어 있어 `apps/api/tests/`가 아닌 프로젝트 루트 `tests/`를 실행 대상으로 인식
- **개선 필요**: `testpaths = apps/api/tests`로 변경하여 명확성 확보

### 5.2 playwright.config.ts (`apps/web/playwright.config.ts`)
```typescript
export default defineConfig({
  testDir: './tests-e2e',              // 테스트 파일 위치
  outputDir: '../../test-results/playwright',  // 결과 저장 위치
  reporter: 'html',                    // 리포트 형식
  timeout: 300000,                     // 5분 타임아웃
  // ...
});
```

---

## 6. 테스트 실행 가이드 (명령어 정리)

### 6.1 전체 테스트 실행 (모든 테스트)
```bash
# 프로젝트 루트에서
make api-test                           # 백엔드 유닛/통합 테스트
npm run test:e2e                        # 프론트엔드 E2E 테스트 (apps/web 디렉토리)
pytest tests/ops_e2e/                   # 백엔드 E2E 테스트
```

### 6.2 특정 카테고리 테스트 실행
```bash
# 백엔드 유닛 테스트만
cd apps/api && pytest tests/unit/

# 백엔드 통합 테스트만
cd apps/api && pytest tests/integration/
pytest tests/ops_ci_api/

# 백엔드 E2E 테스트만
pytest tests/ops_e2e/

# 프론트엔드 E2E 테스트만
cd apps/web && npm run test:e2e

# 보안 테스트만
cd apps/api && pytest tests/test_security*.py tests/test_encryption.py tests/test_permissions.py tests/test_api_keys.py

# UI Contract 테스트만
cd apps/api && pytest tests/test_ui_contract.py
```

### 6.3 특정 테스트 파일/함수 실행
```bash
# 특정 파일
pytest tests/test_ui_contract.py

# 특정 함수
pytest tests/test_ui_contract.py::test_screen_lifecycle

# 패턴 매칭
pytest -k "screen"
pytest -k "encryption"
```

### 6.4 디버깅 및 상세 출력
```bash
# Verbose 모드
pytest -v

# 간략한 traceback
pytest --tb=short

# 디버거 실행 (실패 시)
pytest --pdb

# 테스트 건너뛰기
pytest --skip-slow

# 병렬 실행 (pytest-xdist 필요)
pytest -n auto
```

### 6.5 Playwright 디버깅
```bash
# UI 모드 (브라우저에서 테스트 단계별 실행 가능)
npx playwright test --ui

# 헤드풀 모드 (브라우저 표시)
npx playwright test --headed

# 특정 테스트만 실행
npx playwright test inspector_e2e.spec.ts

# 테스트 결과 보기
npx playwright show-report
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
   ```python
   def test_user_model():
       user = User(name="John", email="john@example.com")
       assert user.name == "John"
       assert user.email == "john@example.com"
   ```
4. **Mock 객체 사용**: `AsyncMock`(비동기) 또는 `Mock`(동기) 사용
   ```python
   from unittest.mock import AsyncMock, Mock
   
   def test_with_mock():
       mock_func = Mock(return_value="test")
       result = mock_func()
       assert result == "test"
   ```
5. **Fixture 사용**: `conftest.py`에 공통 fixture 정의
   ```python
   @pytest.fixture
   def sample_user():
       return User(name="Test User", email="test@example.com")
   
   def test_with_fixture(sample_user):
       assert sample_user.name == "Test User"
   ```
6. **테스트 카테고리 분류**:
   - 단위 테스트: `tests/unit/test_*.py`
   - 통합 테스트: `tests/integration/test_*.py`
   - API 엔드포인트 테스트: `tests/test_*_router.py`
   - 비즈니스 로직 테스트: `tests/test_*_service.py`
   - CRUD 테스트: `tests/test_*_crud.py`
   - 통합 테스트: `tests/test_*_integration.py`

### 7.2 프론트엔드 E2E 테스트 작성 규칙 (Playwright)
1. **테스트 파일 명명**: `*_e2e.spec.ts` 또는 `*.spec.ts` 형식
2. **data-testid 사용**: UI 컴포넌트 식별자는 반드시 `data-testid` 속성 사용 (`docs/TESTIDS.md` 참조)
   ```typescript
   await page.getByTestId('submit-button').click();
   ```
3. **페이지 객체 모델 (Page Object Model)**: 복잡한 페이지는 별도 파일로 분리
   ```typescript
   // pages/inspector-page.ts
   export class InspectorPage {
     constructor(private page: Page) {}
     
     async typeQuery(query: string) {
       await this.page.getByTestId('query-input').fill(query);
       await this.page.getByTestId('submit-button').click();
     }
     
     async getAnswer() {
       return await this.page.getByTestId('answer-block').textContent();
     }
   }
   ```
4. **명확한 테스트 이름**: `describe`, `test` 블록에 명확한 이름 사용
   ```typescript
   test.describe('Inspector Flow', () => {
     test('should display answer after submitting query', async ({ page }) => {
       // ...
     });
   });
   ```
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

## 8. 개선 필요 항목

### 8.1 pytest.ini 설정 수정
```ini
[pytest]
pythonpath = .
testpaths = apps/api/tests  # tests → apps/api/tests로 변경
```

### 8.2 Makefile 테스트 명령어 개선
```makefile
# 기존
api-test:
	cd apps/api && .venv/bin/pytest

web-test:
	cd apps/web && npm run test

# 개선안
api-test:
	cd apps/api && .venv/bin/pytest tests/

api-test-unit:
	cd apps/api && .venv/bin/pytest tests/unit/

api-test-integration:
	cd apps/api && .venv/bin/pytest tests/integration/
	
api-test-security:
	cd apps/api && .venv/bin/pytest tests/test_security*.py tests/test_encryption.py tests/test_permissions.py tests/test_api_keys.py

web-test-e2e:
	cd apps/web && npm run test:e2e

web-test-e2e-ui:
	cd apps/web && npx playwright test --ui

web-test-e2e-headed:
	cd apps/web && npx playwright test --headed

e2e-test:
	pytest tests/ops_e2e/
```

### 8.3 테스트 폴더 구조 개선
- `apps/api/tests/integration/` 폴더에 통합 테스트 추가
- `apps/api/tests/` 하위에 카테고리별 폴더 구조 정리:
  - `apps/api/tests/unit/`: 단위 테스트
  - `apps/api/tests/integration/`: 통합 테스트
  - `apps/api/tests/security/`: 보안 테스트 (test_security*.py, test_encryption.py, 등)
  - `apps/api/tests/ui/`: UI Contract 관련 테스트

### 8.4 테스트 결과 통합 리포트
- JUnit XML 통합: `artifacts/junit.xml`
- Playwright HTML 리포트: `test-results/playwright/`
- CI/CD 파이프라인 통합을 위한 표준화된 리포트 형식

---

## 9. CI/CD 연동 가이드

### 9.1 GitHub Actions (예시)
```yaml
name: Test

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd apps/api
          python -m venv .venv
          .venv/bin/pip install -r requirements.txt
      - name: Run backend tests
        run: |
          cd apps/api
          .venv/bin/pytest tests/ --junitxml=../../artifacts/junit.xml
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: backend-test-results
          path: artifacts/junit.xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd apps/web
          npm install
      - name: Run E2E tests
        run: |
          cd apps/web
          npm run test:e2e
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: frontend-test-results
          path: test-results/playwright/
```

---

## 10. 참고 문서

- **AGENTS.md**: 프로젝트 기본 규칙 및 테스트 관련 섹션
- **README.md**: 프로젝트 설치, 실행 가이드
- **docs/TESTIDS.md**: E2E 테스트 data-testid 속성 명명 규칙 (UI 컴포넌트 개발 시 참조)
  - 이 문서는 TESTING_STRUCTURE.md의 "프론트엔드 E2E 테스트" 섹션에서 사용하는 `data-testid` 속성의 명명 규칙을 정의합니다.
  - UI 컴포넌트 개발 시 TESTIDS.md를 참조하여 올바른 `data-testid`를 부여하고, TESTING_STRUCTURE.md를 참조하여 테스트를 실행하세요.
- **pytest 문서**: https://docs.pytest.org/
- **Playwright 문서**: https://playwright.dev/

---

## 11. 변경 이력

- **2026-01-24**: 테스트 구조 표준화 문서 최초 작성
  - 전체 테스트 폴더 구조 정의
  - 테스트 카테고리 분류 및 실행 명령어 정리
  - 테스트 작성 규칙 표준화
  - 개선 필요 항목 식별