# Tobit SPA AI

## 개요
- Tobit SPA AI는 실제 상용 제품을 목표로 하며, API/프론트엔드, OPS/CI 흐름까지 포함하는 종합 플랫폼입니다.
- AI 에이전트는 `AGENTS.md`에 정의된 **프로젝트 규칙, 기술 스택, Tool Contract/Reference 표준**을 반드시 준수해야 합니다.

## 구조
- `apps/api`: FastAPI + SQLModel 기반 백엔드 (router/service/crud 분리, ToolCall/ReferenceItem 적용).
- `apps/web`: Next.js App Router 기반 프론트엔드 (shadcn/ui, TanStack Query, ECharts, Playwright E2E).
- `docs`: 프로젝트 운영·기술 기록, UI Creator Contract, 테스트 명세, 보안 체크리스트 등.

## 핵심 문서
1. `AGENTS.md` ‑ AI 에이전트 필독 규칙 및 검증 워크플로우. (source of truth)
2. `docs/README.md` ‑ 시스템 완성도 검증 프로젝트 정리.
3. `docs/DEV_ENV.md` ‑ 로컬 DB/Redis/Neo4j 설정 가이드.
4. `docs/FEATURES.md`, `docs/OPERATIONS.md`, `docs/PRODUCTION_GAPS.md` ‑ 기능·운영·배포 요약.
5. `docs/TESTIDS.md`, `docs/TESTING_STRUCTURE.md` ‑ 테스트 표준, data-testid 규칙.
6. UI Creator Contract 문서들 (`CONTRACT_UI_CREATOR_V1.md`, `PHASE_*_SUMMARY.md`, `DEPLOYMENT_GUIDE_PHASE_4.md`).

## 빠른 시작
1. **공통**
   - `make dev`로 전체 개발 서버 실행.
   - `.env`는 커밋 불가, `.env.example`을 참고하여 환경변수를 설정.
2. **백엔드** (`apps/api`)
   - `cp .env.example .env` 후 PostgreSQL/Redis/Neo4j 정보 입력.
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `make api-migrate`로 `alembic upgrade head` 실행 (DB 스키마 변경 시 AI 직접 수행).
3. **프론트엔드** (`apps/web`)
   - `cp .env.example .env.local` 후 API/Playwright 설정.
   - `npm install`
   - `npx playwright install` (E2E 테스트 전 필수).

## 주요 명령어 (`Makefile` 기반)
- `make dev`, `make api-dev`, `make web-dev`
- `make api-migrate`, `make api-lint`, `make web-lint`
- `make api-test`, `make api-test-security`, `make web-test-e2e`
- `npm run lint`, `npm run type-check`, `npm run test:e2e`

## 테스트 & 검증
- **Backend**: `pytest tests/` + `make api-test(-unit|-integration|-security)`; 비동기 테스트는 `@pytest.mark.asyncio` 필수.
- **Frontend**: `make web-test-e2e` 또는 `npm run test:e2e` (UI 변경 시 Playwright 실행).
- **보안 테스트**: `apps/api/tests/test_security*.py` (헤더, HTTPS/CORS, CSRF, 암호화, RBAC, API 키, JWT).
- **추가 검증**: `mypy .` (백엔드 타입), `npm run type-check` (프론트 엔드 타입).

## 안정성 및 품질
- ToolCall/Reference, UIScreen/Screen Asset, Binding Engine, Action Registry 등은 `schemas/` 및 `app/modules` 기준을 준수.
- Data Explorer는 Read-only, 위험 명령어 allowlist 강제.
- 변경 완료 전 `pre-commit`(Ruff/Prettier)과 `ruff check . --fix`, `npm run lint -- --fix` 등을 통과.
- 모든 문서/기능 변경은 `docs/` 내 관련 파일에 반영 (FEATURES/OPERATIONS/PRODUCTION_GAPS 등).

## 운영 체크
- 로그 위치: `apps/api/logs/api.log`, `apps/web/logs/web.log`.
- SSE는 단일 프로세스(uvicorn --workers 1) 또는 Redis Pub/Sub 준비; 클라이언트 재연결( `EventSource.onerror`) 권장.
- Binding/Action 관련 템플릿 표현식은 `{{inputs.x}}`, `{{state.x}}`, `{{context.x}}`, `{{trace_id}}`만 허용.

## 문서·배포 참고
- `docs/SYSTEM_TEST_ANALYSIS_REPORT.md`, `docs/DETAILED_SYSTEM_ANALYSIS.md`는 종합 보고서.
- 필요한 테스트 결과는 `docs/20_TEST_QUERIES_IMPROVED_RESULTS.json`에서 요약 확인.
- 권장 향후 작업 목록과 도구/오퍼레이션 체크리스트를 `docs/OPS_*`에서 확인.

## 참고
- 언제나 `AGENTS.md` 기준으로 작업하면서 변경사항 전후에 checkpoint 커밋을 고민할 것.
- 새로운 API/데이터 변경은 DTO/모델/문서/테스트를 변경하고, `ResponseEnvelope` 구조(`time`, `code`, `message`, `data`)를 따를 것.
- 민감 정보/환경변수는 코드에 하드코딩 금지, `.env.example`에 무조건 예시 기입.
