# Tobit SPA AI - 프로젝트 규칙 (AI 에이전트 필독)

## 1. 문서 개요

이 문서는 Tobit SPA AI 프로젝트의 기본 원칙, 고정 스택, 개발 워크플로우를 정의하는 **최상위 규칙**입니다. AI 에이전트는 모든 작업을 수행할 때 이 문서를 반드시 준수해야 합니다.

---

## 2. 기본 원칙

1. **실제 제품 지향**: 이 프로젝트는 실제 상용 제품을 목표로 합니다. 임시방편의 코드를 작성하지 않습니다.
2. **기술 스택 준수**: 정해진 기술 스택 안에서만 솔루션을 찾습니다. 임의로 새로운 라이브러리를 추가하지 않습니다.
3. **표준화**: 도메인 로직, 도구 계약(Tool Contract), 참조(Reference) 등의 표준 스키마를 준수합니다. (`schemas/tool_contracts.py`, `schemas/answer_blocks.py` 참조)
4. **보안**: DB, Redis, Neo4j 등 외부 서비스 접속 정보는 환경 변수로만 관리하며, 코드에 하드코딩하지 않습니다.
5. **버전 관리**: 큰 규모의 변경 전후에는 `checkpoint` 커밋을 통해 작업 단계를 명확히 남깁니다.
6. **경로 명확성**: 파일 경로는 프로젝트 루트 기준 절대 경로를 사용합니다. 문맥상 명확한 경우에만 제한적으로 상대 경로를 사용합니다./

---

## 3. 기술 스택 (변경 불가)

- **Frontend**: Next.js 16 (App Router), React 19, TypeScript 5.9, Tailwind CSS v4, shadcn/ui, TanStack Query v5, Zustand (Screen Editor), Recharts, React Flow, AG Grid, Radix UI, Lucide React (icons), Monaco Editor, react-pdf
- **Backend**: FastAPI, Pydantic v2, SQLModel, Alembic, LangGraph, LangChain, OpenAI SDK, Redis, RQ, httpx, croniter, sse-starlette
- **Database Driver**: psycopg (>=3.1) - PostgreSQL 접근의 필수 드라이버
- **Data**: PostgreSQL, pgvector, Neo4j, Redis
- **Observability**: LangSmith (선택 사항)
- **Testing Stack**:
  - **Backend Unit Testing**: pytest, pytest-asyncio (비동기 테스트)
  - **Backend Lint**: Ruff (Python linter/formatter)
  - **Frontend E2E Testing**: Playwright (@playwright/test)
  - **Frontend Lint**: ESLint, Prettier, TypeScript strict mode
  - **Test Coverage**: 
    - Backend 유닛 테스트: `apps/api/tests/`
    - Backend 통합/E2E 테스트: `tests/ops_ci_api/`, `tests/ops_e2e/`
    - Frontend E2E 테스트: `apps/web/tests-e2e/`

---

## 4. 프로젝트 구조 (변경 불가)

- `apps/web`: Next.js 프론트엔드
- `apps/api`: FastAPI 백엔드

### 백엔드 구조 권장사항
- **Router (`api/` 또는 `app/modules/<...>/router.py`)**: API 경로 정의와 요청/응답 형식만 담당하며, 비즈니스 로직을 포함하지 않습니다.
- **Service (`app/modules/<...>/services.py`)**: 여러 데이터 소스나 모듈을 조합하여 비즈니스 로직과 정책을 구현합니다.
- **CRUD/Repository (`app/modules/<...>/crud.py`)**: 데이터베이스 접근(읽기, 쓰기, 수정, 삭제)만을 담당합니다.

### OPS 모듈 구조 (CI Orchestrator)
- **6개 쿼리 모드**: config, metric, hist, graph, document, all
- **엔드포인트**: `/ops/query` (단순 모드) + `/ops/ask` (전체 오케스트레이션)
- **Planner** (`services/ci/planner/`): 사용자 질문을 분석하여 실행 계획(Plan)을 생성합니다.
  - `planner_llm.py`: LLM을 사용한 질의 의도 분석
  - `plan_schema.py`: Plan 데이터 모델 정의
  - `validator.py`: Plan 검증 및 정책 적용 (timeout_seconds, max_depth 등)
- **Runner** (`services/ci/orchestrator/runner.py`): 계획된 작업을 실행하고 결과를 생성합니다.
  - Tool 호출 추적: 모든 도구 호출은 `ToolCall` 모델로 표준화
  - Reference 누적: 실행 중 생성되는 모든 참조는 `trace["references"]`에 수집
  - Block 생성: 사용자에게 표시할 블록들을 생성
- **Executors** (`services/executors/`): 특정 도메인의 작업을 실행합니다.
  - `metric_executor.py`: 메트릭 조회
  - `hist_executor.py`: 이력(History) 조회
  - `graph_executor.py`: 그래프/의존성 조회
  - 모두 `(blocks: List[Block], references: List[Reference])` 형태의 표준 출력을 반환합니다.

### API Engine 모듈 구조
- **Router/API** (`app/modules/api_manager/router.py`): 13개 엔드포인트 (CRUD, 실행, 검증, 버전, 롤백)
- **Executors** (`app/modules/api_manager/`):
  - `executor.py`: SQL Executor (SELECT/WITH만 허용, 인젝션 감지)
  - `script_executor.py`: Python Executor (main(params, input_payload) 패턴)
  - `workflow_executor.py`: Workflow Executor (다중 노드 순차 실행)
  - HTTP Executor: httpx 기반, 템플릿 치환
- **Runtime** (`app/modules/api_manager/runtime_router.py`): `/runtime/{path}` 동적 API 실행
- **Frontend**: `/api-manager/page.tsx` (2,996줄)

### Screen Editor 모듈 구조
- **Editor** (`apps/web/src/lib/ui-screen/`):
  - `editor-state.ts`: Zustand 스토어 (Undo/Redo, Multi-Select, Copy/Paste)
  - `screen.schema.ts`: JSON Schema V1 정의
  - `binding-engine.ts`: 바인딩 엔진
  - `expression-parser.ts` / `expression-evaluator.ts`: Expression Engine v2
  - `design-tokens.ts`: Theme System (Light/Dark/Brand)
- **Visual Editor** (`apps/web/src/components/admin/screen-editor/visual/`):
  - `VisualEditor.tsx`, `Canvas.tsx`, `CanvasComponent.tsx`, `BindingEditor.tsx`
- **Runtime** (`apps/web/src/components/answer/UIScreenRenderer.tsx`): 화면 렌더링
- **Backend**: Asset Registry 기반 Screen Asset CRUD + RBAC (5개 권한)

---

## 5. API 설계 규칙

- **공통 응답 구조**: 모든 REST API 응답은 아래의 `ResponseEnvelope` 구조를 따라야 합니다. (단, SSE 스트리밍은 예외)
  ```json
  {
    "time": "...",
    "code": 0,
    "message": "OK",
    "data": { ... }
  }
  ```
- **예외 처리**: FastAPI의 `HTTPException`을 사용하여 명확한 에러 상태 코드와 메시지를 반환합니다. 프론트엔드는 응답의 `detail` 필드를 사용자에게 표시합니다.
- **DTO (Data Transfer Object) 분리**:
  - Request DTO와 Response DTO를 분리합니다.
  - DB 모델(SQLModel)과 API DTO(Pydantic)를 분리하여 각 계층의 역할을 명확히 합니다.
  - 데이터 유효성 검사는 DTO (Pydantic) 계층에서 수행합니다.

---

## 6. 환경변수 규칙

- 코드 내 환경변수 값을 하드코딩하는 것을 금지합니다.
- `.env` 파일은 Git에 커밋하지 않습니다.
- 모든 환경변수는 `.env.example` 파일에 반드시 예시와 함께 기록해야 합니다.

---

## 7. 실시간 및 관측성 규칙

- **실시간 통신**: SSE(Server-Sent Events) 요구사항이 있는 경우, 주기적인 DB 폴링(Polling)으로 대체하지 않습니다.
- **SSE 브로드캐스터**: 현재 구현은 단일 프로세스 메모리 기반입니다. 운영 환경에서는 `uvicorn --workers 1`로 실행하거나, Redis Pub/Sub 기반으로 전환할 준비가 되어 있어야 합니다 (인터페이스 분리 원칙).
- **SSE 연결 유지**: 서버는 `ping` 이벤트를 주기적으로 보내 연결을 유지해야 하며, 클라이언트는 `EventSource.onerror` 핸들러에서 재연결 로직을 구현해야 합니다.

---

## 8. 주요 기능별 규칙

### Tool Contract & References 표준화
- **Tool Contract** (`schemas/tool_contracts.py::ToolCall`):
  - 모든 도구(Tool) 호출은 `ToolCall` Pydantic 모델로 표준화되어야 합니다.
  - 필수 필드: `tool` (도구명), `elapsed_ms` (실행시간), `input_params` (입력), `output_summary` (출력 요약), `error` (에러 여부)
  - 특히 orchestrator, runner, executor에서 도구 호출 시 반드시 `ToolCall` 구조를 사용합니다.
  - 예: CI Runner의 `_tool_context()` 메서드는 모든 호출을 자동으로 `ToolCall`로 변환합니다.

- **References** (`schemas/answer_blocks.py::ReferenceItem`, `ReferenceBlock`):
  - 데이터 조회, 쿼리 실행 등에서 생성되는 모든 참조(Reference)는 `ReferenceItem`으로 표준화합니다.
  - 필수 필드: `kind` (참조 타입: "sql", "cypher" 등), `title`, `payload` (본문)
  - 블록 반환 시 `ReferenceBlock` 타입의 블록으로 분리하여 제공합니다.
  - Executor와 Runner는 실행 중 수집된 모든 참조를 `trace["references"]`에 누적합니다.

- **UI Screen Contract** (Phase 1-4):
  - **UIScreenBlock** (`schemas/answer_blocks.py::UIScreenBlock`):
    - `type: "ui_screen"` (고정), `screen_id` (필수), `params` (선택), `bindings` (선택)
    - Answer block에서 Published Screen Asset을 참조하는 트리거 역할
    - Applied Assets에 `screen_id`, `version`, `status` 기록 필수

  - **Screen Asset** (`app/modules/asset_registry`):
    - Prompt/Policy와 동일한 생명주기: draft → published → rollback
    - DB 필드: `screen_id` (stable key), `schema_json` (UI 정의), `tags` (메타데이터)
    - 마이그레이션: `0029_add_screen_asset_fields.py`

  - **Binding Engine** (`app/modules/ops/services/binding_engine.py`):
    - 템플릿 표현식: `{{inputs.x}}`, `{{state.x}}`, `{{context.x}}`, `{{trace_id}}`
    - Dot-path only (표현식/계산 불가)
    - 민감정보 마스킹: password, secret, token, api_key 등

  - **Action Handler Registry** (`app/modules/ops/services/action_registry.py`):
    - `/ops/ui-actions` 단일 엔드포인트
    - Deterministic executor로 라우팅
    - 모든 핸들러는 `ExecutorResult` (blocks, tool_calls, references, summary) 반환

- **Data Explorer (데이터 탐색기)**:
  - 조회 전용(Read-only)으로만 동작해야 합니다.
  - SQL, Cypher, Redis에서 데이터 변경을 유발하는 위험한 명령어 사용을 금지하고, 허용된 명령어 목록(allowlist)을 강제해야 합니다.

### 보안 테스트 (Security Testing)
- **Backend Security Test**:
  - 모든 보안 관련 변경은 반드시 보안 테스트를 포함해야 합니다.
  - 테스트 위치: `apps/api/tests/test_security*.py`, `test_encryption.py`, `test_permissions.py`, `test_api_keys.py`
  - **테스트 범위**:
    - **보안 헤더**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
    - **HTTPS/CORS**: HTTPS 리다이렉트, CORS 설정, 신뢰할 수 있는 오리진 검증
    - **CSRF 보호**: CSRF 토큰 생성, 검증, 미스매치 거부
    - **암호화**: 민감정보 암호화/복호화 (이메일, 비밀번호 등)
    - **접근 제어 (RBAC)**: 역할 기반 권한 확인, 사용자 권한 조회
    - **API 키**: 키 생성, 검증, 스코프 관리, 폐기
    - **인증**: JWT 토큰 생성/검증, 사용자 인증
  - 실행: `pytest tests/test_security*.py -v`

---

## 9. 개발 워크플로우 (필독)

AI 에이전트는 이 문서(`AGENTS.md`)만 참조하더라도 아래의 모든 개발 리소스와 절차를 숙지하고 준수해야 합니다.

### 1) 핵심 문서
   - `README.md`: 프로젝트 설치, 실행, 구조 등 가장 기본적인 정보를 담은 **Source of Truth**입니다.
   - `DEV_ENV.md`: 개발 환경의 DB(Postgres/Neo4j/Redis) 접속 정보 설정 가이드입니다.
   - `docs/FEATURES.md`: 각 기능의 상세 명세, API 노트, 사용 예시를 담고 있습니다. (기능 변경 시 반드시 업데이트)
   - `docs/TESTING_STRUCTURE.md`: 테스트 구조 표준 가이드입니다. (`data-testid` 네이밍 규칙 포함, UI 컴포넌트 추가 시 반드시 준수)

### 1-0) 아키텍처 문서 (6개 모듈)
   - `docs/SYSTEM_ARCHITECTURE_REPORT.md`: **시스템 전체 아키텍처 개요** (경영진/의사결정자 대상, v1.6)
   - `docs/OPS_QUERY_BLUEPRINT.md`: OPS 쿼리 시스템 상세 설계 (6개 모드, CI Orchestrator, Document Search)
   - `docs/CEP_ENGINE_BLUEPRINT.md`: CEP 엔진 상세 설계 (Trigger-Action, 5채널 알림, Redis 분산 상태)
   - `docs/API_ENGINE_BLUEPRINT.md`: API Engine 상세 설계 (SQL/HTTP/Python/WF 실행기, 보안, CEP 통합)
   - `docs/SCREEN_EDITOR_BLUEPRINT.md`: Screen Editor 상세 설계 (15 컴포넌트, Expression, Theme, RBAC)

### 2) 로그 위치
   - **Backend**: `apps/api/logs/api.log`
   - **Frontend**: `apps/web/logs/web.log`

### 3) 단축 명령어 (`Makefile` 기반)
   - `make dev`: 전체 개발 환경을 실행합니다. (가장 추천)
   - `make api-dev` / `make web-dev`: 백엔드 또는 프론트엔드를 개별적으로 실행합니다.
   - `make api-lint` / `make web-lint`: 각 파트의 코드 품질을 검사합니다.
   - `make api-migrate`: DB 마이그레이션(`alembic upgrade head`)을 실행합니다. **DB 스키마 변경 시 AI가 직접 실행해야 합니다.**

### 3-1) 테스트 실행 (필독)
   **코드를 수정한 후에는 반드시 아래 테스트를 실행하여 변경사항을 검증해야 합니다.**

   - **Backend 유닛 테스트 (pytest)**:
     ```bash
     # apps/api 디렉토리에서 실행
     pytest tests/                           # 전체 테스트 실행
     pytest tests/unit/                      # 단위 테스트만 실행
     pytest tests/integration/               # 통합 테스트만 실행
     pytest tests/test_specific.py          # 특정 파일 테스트
     pytest tests/test_specific.py::test_func  # 특정 함수 테스트
     pytest -v                               # Verbose 모드 (상세 출력)
     pytest -k "pattern"                     # 패턴 매칭으로 테스트 필터링
     pytest --tb=short                       # 간략한 traceback 출력

     # 또는 프로젝트 루트에서
     make api-test                           # 전체 백엔드 테스트 실행
     make api-test-unit                      # 단위 테스트만 실행
     make api-test-integration               # 통합 테스트만 실행
     make api-test-security                  # 보안 테스트만 실행
     ```

     **테스트 작성 규칙**:
     - 비동기 함수는 `@pytest.mark.asyncio` 데코레이터 필수
     - 모든 Pydantic 모델은 실제 필드 구조와 일치해야 함
     - Mock 객체는 `AsyncMock`(비동기) 또는 `Mock`(동기) 사용
     - 테스트 파일명은 반드시 `test_*.py` 형식 준수

     **주요 테스트 카테고리**:
     - 비즈니스 로직 테스트: `tests/test_*_service.py`
     - API 엔드포인트 테스트: `tests/test_*_router.py`
     - 데이터베이스 CRUD 테스트: `tests/test_*_crud.py`
     - 통합 테스트: `tests/test_*_integration.py`

   - **Frontend E2E 테스트 (Playwright)**:
     ```bash
     npm run test:e2e          # apps/web 디렉토리에서 실행
     # 또는
     make web-test-e2e         # 프로젝트 루트에서 실행

     # 특정 테스트만 실행
     npx playwright test ui-screen.spec.ts

     # UI 모드로 실행 (디버깅용)
     make web-test-e2e-ui
     # 또는
     npx playwright test --ui

     # 헤드풀 모드 (브라우저 표시)
     make web-test-e2e-headed
     # 또는
     npx playwright test --headed
     ```
     UI 컴포넌트, 사용자 흐름, 대화 상자, 버튼 동작 등 변경 시 필수 실행
     - **테스트 파일 위치**: `apps/web/tests-e2e/*.spec.ts` (22개 테스트 파일)
     - **주요 테스트**: Inspector 흐름, RCA 실행, Regression Watch 기능, UI Screen 렌더링, Screen Editor, Diff Compare, Publish Gate

   - **Backend API 수동 테스트**:
     ```bash
     # Python 스크립트로 엔드포인트 검증
     python3 << 'EOF'
     import requests
     response = requests.post("http://localhost:8000/ops/endpoint-path", json={...})
     print(response.json())
     EOF

     # 또는 curl 사용
     curl -X POST http://localhost:8000/ops/endpoint-path \
       -H "Content-Type: application/json" \
       -d '{"key": "value"}'
     ```
     새로운 API 엔드포인트 추가 또는 응답 형식 변경 시 실행

   - **코드 품질 검사** (pre-commit 훅과 동일):
     ```bash
     # Backend: Linting & Formatting
     make api-lint              # Backend: Ruff (linter + formatter)
     ruff check . --fix         # apps/api 디렉토리에서 실행 (자동 수정)
     ruff format .              # 코드 포맷팅

     # Backend: Type Checking
     mypy .                     # apps/api 디렉토리에서 실행 (타입 검사)

     # Frontend: Linting & Formatting
     make web-lint              # Frontend: ESLint, Prettier
     npm run lint -- --fix      # 자동 수정 (apps/web 디렉토리)
     npm run format             # Prettier 포맷팅 (apps/web 디렉토리)

     # Frontend: Type Checking
     npm run type-check         # TypeScript strict mode 검사 (apps/web 디렉토리)
     ```

### 4) 품질 관리
   - 모든 코드는 `pre-commit` 훅(Ruff, Prettier)의 검사를 통과해야 합니다.
   - 핵심 로직을 수정할 경우, 반드시 `pytest`(백엔드) 또는 관련 UI 테스트(프론트엔드)를 통해 검증해야 합니다.
   - **소스 코드 변경 시 테스트 동반 수정은 필수**입니다. 동작/계약/스키마/API 응답이 변경되면 관련 테스트 파일을 반드시 함께 수정하거나 신규 추가해야 합니다.
   - **버그 수정 시 회귀 방지 테스트는 필수**입니다. 동일 이슈가 재발하지 않도록 최소 1개 이상의 재현 테스트 케이스를 추가해야 합니다.
   - **리팩토링(동작 동일)이라도 기존 테스트는 반드시 통과**해야 하며, 테스트가 깨지면 소스 또는 테스트를 즉시 정합성 있게 수정해야 합니다.
   - **Frontend UI 변경 시**: Playwright E2E 테스트(`make web-test-e2e` 또는 `npm run test:e2e`)를 실행하여 사용자 흐름이 정상 작동하는지 확인합니다.
   - **Frontend UI 변경 시 테스트 코드 갱신 의무**: 선택자(`data-testid`), 사용자 플로우, 문구/상태 변경이 있으면 관련 Playwright 테스트를 함께 수정해야 합니다.
   - **Backend API 변경 시**: `curl` 또는 Python 스크립트로 엔드포인트를 테스트하여 응답 형식과 에러 처리가 올바른지 확인합니다.
   - **Backend API 변경 시 테스트 코드 갱신 의무**: Request/Response 계약, 상태코드, 에러 형식이 변경되면 관련 pytest(API/router/service) 테스트를 함께 수정해야 합니다.
   - **Backend 신규 기능 추가 시**:
     - 반드시 `tests/test_*.py` 유닛 테스트를 작성합니다.
     - pytest 비동기 테스트는 `@pytest.mark.asyncio` 데코레이터 사용
     - Pydantic 모델 테스트는 실제 필드 구조와 일치하도록 작성
     - 모든 테스트는 `pytest -v` 실행 시 100% 통과해야 함
   - **Tool Contract 변경 시**: `ToolCall`, `ReferenceItem` 등의 스키마 수정 후에는 반드시 관련 executor/runner 테스트를 실행합니다.
   - **Database 드라이버 변경 시**: psycopg 버전 업그레이드 시 모든 DB 호출 코드를 검증하고, SQLAlchemy/SQLModel 마이그레이션이 필요한지 확인합니다.
   - **Lint 및 Type Check 오류 대응**:
     - Backend Lint: `ruff check . --fix`로 자동 수정 가능한 문제는 즉시 수정
     - Backend Type Check: `mypy .` 실행 후 타입 오류 반드시 수정
     - Frontend Lint: `npm run lint -- --fix`로 자동 수정 가능한 문제는 즉시 수정
     - Frontend Type Check: `npm run type-check` 실행 후 TypeScript 오류 반드시 수정
     - Ruff 경고: E402 (import not at top), F841 (unused variable) 등은 개발 중 허용 가능
     - Ruff 오류: E741 (ambiguous variable name `l`), F821 (undefined name) 등은 반드시 수정

---

## 10. 인증 & 세션 & Tenant_ID 규칙 (필독)

모든 API 엔드포인트에서 **반드시** 다음 규칙을 준수하세요. 이를 어기면 조회 오류, 권한 오류, 테넌트 데이터 누락 등이 발생합니다.

### 0. 전역 인증 정책 (필수)

- 기본 정책: 모든 API는 JWT 인증(`get_current_user`)을 적용합니다.
- 공개 엔드포인트 예외: `POST /auth/login`, `POST /auth/refresh`만 인증 없이 허용합니다.
- FastAPI 라우터를 추가할 때는 `apps/api/main.py`의 전역 인증 의존성 정책을 따라야 하며, 예외 엔드포인트를 임의로 늘리지 않습니다.
- 개발 모드 예외: `ENABLE_AUTH=false`이면 JWT 검증을 우회하고 디버그 사용자 컨텍스트로 동작할 수 있습니다.

### 1. 로그인 세션 처리

#### 1-1. 현재 사용자 정보 조회

**필수 파일**: `core/auth.py`

```python
from fastapi import Depends
from core.auth import get_current_user
from app.modules.auth.models import TbUser

@router.get("/api/endpoint")
def my_endpoint(
    current_user: TbUser = Depends(get_current_user)  # ← 반드시 추가
) -> ResponseEnvelope:
    """
    Requirements:
    1. current_user: 항상 추가해야 함
    2. Type: TbUser (dict가 아님!)
    3. 자동 처리: 토큰 검증, 사용자 조회, 권한 확인
    """
    user_id = current_user.id  # UUID
    tenant_id = current_user.tenant_id  # 테넌트 ID (중요!)
    role = current_user.role  # UserRole enum
    return ResponseEnvelope.success(data={"user_id": user_id})
```

**문제점과 해결방안**:

| 문제 | 원인 | 해결방법 |
|------|------|--------|
| `AttributeError: 'NoneType' has no attribute 'id'` | `current_user` 미전달 | `Depends(get_current_user)` 추가 |
| `AttributeError: 'dict' object has no attribute 'role'` | `current_user: dict` 사용 | `current_user: TbUser` 로 변경 |
| 401 Unauthorized 반복 | JWT 토큰 만료/무효 | 새로운 토큰 발급 받기 |
| `enable_auth=False` 개발 모드에서 사용자 없음 | 디버그 사용자 미생성 | DB에 `admin@tobit.local` 사용자 생성 |

#### 1-2. API 키 인증 (선택)

```python
from core.auth import get_current_user_from_api_key

@router.get("/api/endpoint")
def my_endpoint(
    current_user: TbUser = Depends(get_current_user_from_api_key)
) -> ResponseEnvelope:
    """API 키 기반 인증 (Bearer 토큰 대신 사용)"""
    pass
```

**API 키 사용 방법**:
```bash
# Header
curl -H "Authorization: Bearer <api_key>" http://localhost:8000/api/endpoint

# 또는 Query Parameter
curl http://localhost:8000/api/endpoint?api_key=<api_key>
```

### 2. 데이터베이스 세션 관리

**필수 파일**: `core/db.py`

```python
from core.db import get_session
from sqlmodel import Session

@router.get("/api/endpoint")
def my_endpoint(
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session)  # ← DB 조회 필요시 추가
) -> ResponseEnvelope:
    """
    Database operations must use get_session()
    FastAPI는 자동으로 트랜잭션 관리 (commit/rollback)
    """
    # DB 조회 (session 필수)
    user = session.get(TbUser, current_user.id)

    # DB 쓰기
    session.add(user)
    session.commit()  # ← session.flush() 호출 가능하지만 commit은 불필요 (자동)
```

**주의**:
- `session`은 **요청 범위** (request scope)에서만 유효
- 요청 종료 후 자동 정리 (컨텍스트 매니저)
- 비동기 함수에서는 `get_session_context()` 사용 (실제 사용 예시 없음 - 동기만 권장)

### 3. Tenant_ID 처리 (중요!)

#### 3-1. Tenant_ID 자동 주입

**필수 파일**: `core/middleware.py`, `core/tenant.py`

```python
# middleware.py에서 자동 설정
# ↓ request.headers에서 'x-tenant-id' 추출
# ↓ 없으면 기본값 'default' 사용
# ↓ request.state.tenant_id 에 저장

# Router에서 접근
from core.tenant import get_tenant_id

@router.get("/api/endpoint")
def my_endpoint(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)  # ← Tenant_ID 자동 조회
) -> ResponseEnvelope:
    """
    Tenant_ID는 두 가지 방법으로 획득:
    1. current_user.tenant_id (사용자의 테넌트)
    2. get_tenant_id() (HTTP 헤더에서)

    보통 둘이 같아야 함. 다르면 권한 오류.
    """
    # current_user.tenant_id와 동일해야 함
    assert current_user.tenant_id == tenant_id

    # 데이터 조회시 반드시 tenant_id로 필터링
    return ResponseEnvelope.success(data={"tenant_id": tenant_id})
```

#### 3-2. 데이터 조회 시 Tenant 필터링 (필수!)

```python
# ❌ 잘못된 예 (보안 위험!)
@router.get("/api/users")
def get_users(session: Session = Depends(get_session)):
    # tenant_id 필터 없음 → 다른 테넌트 데이터도 조회됨
    users = session.exec(select(TbUser)).all()
    return ResponseEnvelope.success(data={"users": users})

# ✅ 올바른 예
@router.get("/api/users")
def get_users(
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # tenant_id로 필터링
    users = session.exec(
        select(TbUser).where(TbUser.tenant_id == current_user.tenant_id)
    ).all()
    return ResponseEnvelope.success(data={"users": users})
```

#### 3-3. HTTP 헤더에서 Tenant_ID 전송

프론트엔드에서:
```javascript
// apps/web/src/lib/api.ts
fetch("/api/endpoint", {
    headers: {
        "x-tenant-id": "default",  // ← 테넌트 ID 추가
        "Authorization": "Bearer <token>"
    }
})

// 또는 Axios/TanStack Query에서 인터셉터 설정
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            queryFn: async ({ queryKey }) => {
                const response = await fetch(queryKey[0], {
                    headers: {
                        "x-tenant-id": localStorage.getItem("tenant_id") || "default"
                    }
                });
                return response.json();
            }
        }
    }
});
```

### 4. 인증 설정 (환경변수)

**필수 파일**: `.env`

```bash
# 인증 활성화 (프로덕션)
ENABLE_AUTH=true

# 인증 비활성화 (개발 모드 - 주의!)
ENABLE_AUTH=false  # ← 개발 중에만 사용

# 권한(RBAC) 검사 비활성화 (개발 모드 - 주의!)
ENABLE_PERMISSION_CHECK=false  # ← 개발 중에만 사용

# JWT 설정
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# 기본 테넌트
DEFAULT_TENANT_ID=default
```

**개발 모드 활성화 확인**:
```python
# apps/api/main.py
from core.config import get_settings

settings = get_settings()
if not settings.enable_auth:
    print("⚠️  Authentication DISABLED - Dev Mode Only")
```

### 5. 테스트에서 인증 처리

```python
# apps/api/tests/test_endpoint.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_authenticated_endpoint():
    """현재 사용자 필수 엔드포인트 테스트"""
    # Case 1: 토큰 없음 → 401 Unauthorized
    response = client.get("/api/endpoint")
    assert response.status_code == 401

    # Case 2: 유효한 토큰 → 200 OK
    # (enable_auth=False일 때 자동으로 debug 사용자 사용)
    response = client.get(
        "/api/endpoint",
        headers={"x-tenant-id": "default"}  # 테넌트 ID 추가
    )
    assert response.status_code == 200

def test_tenant_isolation():
    """테넌트 격리 테스트"""
    # default 테넌트 데이터
    response1 = client.get(
        "/api/users",
        headers={"x-tenant-id": "default"}
    )

    # t2 테넌트 데이터
    response2 = client.get(
        "/api/users",
        headers={"x-tenant-id": "t2"}
    )

    # 다른 데이터 확인
    assert response1.json()["data"] != response2.json()["data"]
```

### 6. 일반적인 오류와 해결방법

| 오류 메시지 | 원인 | 해결방법 |
|-----------|------|--------|
| `401 Unauthorized` | 토큰 없음/만료 | JWT 토큰 재발급 또는 `ENABLE_AUTH=false` |
| `AttributeError: 'NoneType'` | `current_user` None | `Depends(get_current_user)` 필수 추가 |
| `AttributeError: 'dict' object` | 타입 오류 | `current_user: TbUser` 명시 |
| 다른 테넌트 데이터 조회됨 | Tenant 필터 누락 | WHERE 절에 `tenant_id` 필터 추가 |
| `get_current_user()` 호출 안됨 | `Depends()` 미사용 | FastAPI `Depends()` 반드시 사용 |
| 테넌트 헤더 무시됨 | 미들웨어 미등록 | `core/middleware.py` 확인 |

### 7. 체크리스트 (엔드포인트 추가 시)

- [ ] `current_user: TbUser = Depends(get_current_user)` 추가?
- [ ] 데이터 조회 시 `tenant_id` 필터링?
- [ ] DB 접근 시 `session: Session = Depends(get_session)` 추가?
- [ ] Type hint 정확함? (`dict` 아닌 `TbUser`)
- [ ] 테스트에서 `x-tenant-id` 헤더 추가?
- [ ] `.env`에 `ENABLE_AUTH`, `ENABLE_PERMISSION_CHECK`, `JWT_SECRET_KEY` 설정?

---

## 11. 작업 완료의 정의 (Definition of Done)

AI 에이전트는 모든 작업을 종료하기 전, 다음 네 가지 기준을 충족했는지 스스로 확인해야 합니다.

1.  **검증 (Verification)**
    - 단순 코드 생성을 넘어, 실제 동작을 확인했습니까? (`curl` 테스트, `pytest` 실행 결과, UI 동작 스크린샷, Playwright E2E 테스트 등)
    - 변경된 소스와 1:1로 대응되는 테스트 파일(신규/수정)을 함께 반영했습니까?
    - 버그 수정의 경우, 동일 이슈 재발 방지 테스트(회귀 테스트)를 추가했습니까?
    - 백엔드 로직 수정 시, `tests/`에 관련 테스트 케이스를 추가하거나 `curl` 스크립트 실행 결과를 제시했습니까?
    - Frontend UI 변경 시, Playwright E2E 테스트(`npm run test:e2e` 또는 `make web-test-e2e`)를 실행하여 사용자 흐름을 검증했습니까?
    - Backend 코드 변경 시: `mypy .` (타입 검사) 실행 후 모든 타입 오류가 해결되었습니까?
    - Frontend 코드 변경 시: `npm run type-check` (TypeScript 검사) 실행 후 모든 타입 오류가 해결되었습니까?
    - Tool Contract/Reference 관련 변경: 해당 스키마를 사용하는 모든 서비스(executor, runner 등)에서 정상 작동 확인했습니까?
    - DB 드라이버/마이그레이션: `make api-migrate` 실행 후 DB 스키마가 정상 생성되었는지 확인했습니까?
    - 보안 관련 변경 (인증, 암호화, 권한, API 키): `apps/api/tests/test_security*.py` 테스트 실행 후 100% 통과했습니까?

2.  **문서 최신화 (Documentation)**
    - 변경된 기능, API, 환경변수가 `README.md`, `docs/FEATURES.md`, `docs/OPERATIONS.md` 등 관련 문서에 모두 반영되었습니까?
    - Tool Contract/Reference 표준화 관련: 해당 스키마 변경이 `AGENTS.md`의 표준화 섹션에 반영되었습니까?
    - 기술 스택 업그레이드(예: DB 드라이버): 이 `AGENTS.md` 문서의 "기술 스택" 및 "품질 관리" 섹션을 최신화했습니까?

3.  **버전 관리 (Version Control)**
    - 작업 단위에 맞는 명확한 커밋 메시지를 작성했습니까?
    - 필요한 경우, 작업 전후로 `checkpoint` 커밋을 남겼습니까?
    - 커밋 메시지에 변경 사항의 이유(Why)와 영향 범위(Scope)를 포함했습니까?

4.  **표준 준수 (Standards Compliance)**
    - 코드가 `schemas/tool_contracts.py`, `schemas/answer_blocks.py` 등의 표준 스키마를 준수했습니까?
    - 도구 호출(Tool execution)이 있는 경우, `ToolCall` Pydantic 모델을 사용했습니까?
    - 데이터 조회 시 생성되는 참조가 `ReferenceItem` 표준을 따랐습니까?
