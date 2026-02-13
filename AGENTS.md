# Tobit SPA AI - 에이전트 규칙 (정본)

## 1. 목적
이 문서는 이 저장소에서 작업하는 AI 에이전트가 반드시 지켜야 하는 최소 비타협 규칙을 정의합니다.

- 범위: 실행 정책, 아키텍처 가드레일, 검증 정책, 완료 기준
- 설정/기능/테스트의 세부 내용은 전용 문서에 있으며, 여기서 참조합니다.

---

## 2. 문서 우선순위
다음 순서로 문서를 사용합니다.

1. `AGENTS.md` (이 파일): 필수 규칙 및 정책
2. `README.md`: 프로젝트 개요, 실행 명령, 상위 구조
3. `DEV_ENV.md`: 환경 변수 및 로컬 인프라 설정
4. `docs/FEATURES.md`: 기능/API 동작 및 제품 수준 계약
5. `docs/TESTING_STRUCTURE.md`: 테스트 구성 및 test-id 규칙
6. `docs/UI_DESIGN_SYSTEM_GUIDE.md`: UI 디자인 시스템 정본 (공통 스타일/컴포넌트 기준)
7. 아키텍처 문서:
   - `docs/SYSTEM_ARCHITECTURE_REPORT.md`
   - `docs/BLUEPRINT_PRODUCT_COMPLETENESS.md`
   - `docs/BLUEPRINT_OPS_QUERY.md`
   - `docs/BLUEPRINT_CEP_ENGINE.md`
   - `docs/BLUEPRINT_API_ENGINE.md`
   - `docs/BLUEPRINT_SCREEN_EDITOR.md`
   - `docs/BLUEPRINT_ADMIN.md`
   - `docs/BLUEPRINT_SIM.md`

규칙: 이 파일과 상세 문서가 충돌하면, 명시적 개정이 없는 한 이 파일이 우선합니다.

---

## 3. 핵심 비타협 규칙

### 3.1 제품 및 코드 품질
- 프로덕션 수준 코드를 작성합니다. 임시 해킹 금지.
- 고정 스택 외 미승인 라이브러리 도입 금지.
- 모듈 경계(router/service/repository 분리) 유지.
- 문서/스크립트에서 모호성이 있으면 프로젝트 루트 절대 경로 사용.

### 3.2 고정 기술 스택 (변경 금지)
- Frontend: Next.js 16, React 19, TypeScript 5.9, Tailwind v4, shadcn/ui, TanStack Query v5, Zustand, Recharts, React Flow, AG Grid, Monaco, react-pdf.
- Backend: FastAPI, Pydantic v2, SQLModel, Alembic, LangGraph/LangChain/OpenAI SDK, Redis/RQ/httpx/croniter/sse-starlette.
- Data: PostgreSQL + pgvector, Neo4j, Redis.
- PostgreSQL 드라이버: `psycopg>=3.1` 필수.

### 3.3 API 및 계약 표준
- REST 응답은 반드시 `ResponseEnvelope` 사용:
  - `{ "time": "...", "code": 0, "message": "OK", "data": ... }`
  - 예외: SSE 스트림 응답
- API 오류는 명시적 `HTTPException`으로 처리.
- DB 모델과 API DTO(요청/응답) 분리.
- Tool call 및 reference 표준화 필수:
  - `schemas/tool_contracts.py::ToolCall`
  - `schemas/answer_blocks.py::ReferenceItem`, `ReferenceBlock`
- UI 화면 플로우는 `UIScreenBlock` 및 스크린 자산 생명주기/바인딩 정책을 스키마 계약과 일치시킵니다.

### 3.4 보안 및 멀티테넌트 규칙
- 코드에 자격 증명 하드코딩 금지.
- `.env` 커밋 금지.
- 코드에서 사용하는 모든 환경 변수는 `.env.example`에 반영.
- 기본 API 정책: 아래를 제외한 모든 엔드포인트에 JWT 필수
  - `POST /auth/login`
  - `POST /auth/refresh`
- 사용자 컨텍스트가 필요한 엔드포인트는 다음 사용:
  - `current_user: TbUser = Depends(get_current_user)`
- 테넌트 격리 필수:
  - 테넌트 소유 데이터는 `tenant_id`로 필터링
  - `x-tenant-id` 및 미들웨어 테넌트 컨텍스트 준수

### 3.5 실시간 / SSE
- SSE가 필요한 경우 폴링으로 대체 금지.
- ping + reconnect 동작 유지.

---

## 4. 필수 프로젝트 구조
- Frontend: `apps/web`
- Backend: `apps/api`

백엔드 계층:
- Router: API 형태/라우팅만 담당
- Service: 비즈니스 로직/오케스트레이션 담당
- CRUD/Repository: DB I/O만 담당

---

## 5. 실행 워크플로 (에이전트)

### 5.1 코드 변경 전
- 다음 문서의 관련 섹션을 읽습니다:
  - `README.md` (실행 흐름)
  - `docs/FEATURES.md` (동작/계약)
  - `docs/TESTING_STRUCTURE.md` (테스트 위치 및 selector 정책)

### 5.2 코드 변경 후 (필수 검증)
- 백엔드 변경:
  - `make api-lint`
  - `mypy .` (`apps/api`에서 실행)
  - 관련 `pytest` 범위(단위/통합/보안)
- 프론트엔드 변경:
  - `make web-lint`
  - `npm run type-check` (`apps/web`에서 실행)
  - 영향 범위에 맞는 Playwright E2E
- API 계약 변경:
  - 관련 백엔드 테스트 갱신 및 검증 + 수동 API 확인(`curl`/스크립트)
- 보안 관련 변경(인증/암호화/RBAC/API 키):
  - 보안 테스트(`test_security*.py` 스위트) 실행

규칙: 버그 수정에는 반드시 회귀 방지 테스트 1개 이상 포함.

### 5.3 문서 업데이트
동작/계약/설정이 바뀌면 같은 PR/커밋 세트에서 관련 문서를 함께 업데이트합니다.
- 실행/설정 또는 상위 흐름 변경: `README.md`
- 환경/인프라 변경: `DEV_ENV.md`
- 기능/API 동작 변경: `docs/FEATURES.md`
- 테스트 구조/selector 정책 변경: `docs/TESTING_STRUCTURE.md`
- 정책/표준 자체 변경 시에만: `AGENTS.md`

### 5.4 버전 관리
- Why + Scope를 포함한 명확한 커밋 메시지 사용.
- 필요 시 큰 전환점마다 체크포인트 커밋 사용.

---

## 6. 완료 기준 (DoD)
작업 완료 전 아래 조건을 모두 만족해야 합니다.

1. 검증
- 변경 코드는 범위에 맞는 lint/type-check/tests로 검증됨.
- 버그 수정에 회귀 테스트가 추가됨.
- 계약/스키마/tool-reference 변경이 의존 모듈에서 검증됨.

2. 문서
- 동작/API/env/testing 변경 사항이 관련 문서에 반영됨.

3. 표준
- 아키텍처 경계가 유지됨.
- Response/ToolCall/Reference 표준이 유지됨.
- 인증 + 테넌트 격리 규칙이 유지됨.

4. 전달
- 변경 의도와 영향이 명확한 커밋으로 전달됨.

---

## 7. 빠른 명령어 참고
주요 명령어(세부는 `README.md` / `docs/TESTING_STRUCTURE.md` 참고):

```bash
make dev
make api-dev
make web-dev

make api-lint
make web-lint

make api-test
make api-test-security
make web-test-e2e
```

---

## 8. 참고
- 로그 파일:
  - Backend: `apps/api/logs/api.log`
  - Frontend: `apps/web/logs/web.log`
- 이 파일은 정책 중심으로 유지하고, 구현 세부 내용은 참조 문서에 둡니다.
- Claude 전용 스킬 파일(`.claude/skills/*`)은 자동화 실행을 위한 보조 문서이며, 정책/가이드 정본은 반드시 `docs/`에 둡니다.
