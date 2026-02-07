# Tobit SPA AI

## 개요
Tobit SPA AI는 복잡한 인프라 질문에 AI 기반으로 답변하고, 실시간 모니터링 및 알림을 제공하며, 문서 기반 의사결정을 지원하고, 운영 화면을 시각적으로 편집/배포하는 **운영 지원 플랫폼**입니다.

AI 에이전트는 `AGENTS.md`에 정의된 **프로젝트 규칙, 기술 스택, Tool Contract/Reference 표준**을 반드시 준수해야 합니다.

## 6개 핵심 모듈

| 모듈 | 목적 | 상용 준비도 |
|------|------|------------|
| **OPS** | 인프라 질의 응답 (6개 쿼리 모드) | 90% |
| **CEP** | 실시간 이벤트 처리 및 알림 (5채널) | 90% |
| **DOCS** | 문서 관리 및 하이브리드 검색 | 85% |
| **API Engine** | 동적 API 정의/실행 (SQL/HTTP/Python/WF) | 80% |
| **ADMIN** | 시스템 관리, 관측성 | 85% |
| **Screen Editor** | 로우코드 UI 빌더 (15개 컴포넌트) | 95% |

## 구조
- `apps/api`: FastAPI + SQLModel 기반 백엔드 (router/service/crud 분리, ToolCall/ReferenceItem 적용)
- `apps/web`: Next.js 16 App Router 기반 프론트엔드 (shadcn/ui, TanStack Query v5, React 19)
- `docs/`: 아키텍처 Blueprint, 기능 명세, 운영 문서

## 핵심 문서

### 필독
1. `AGENTS.md` - AI 에이전트 필독 규칙 및 검증 워크플로우 (source of truth)
2. `DEV_ENV.md` - 로컬 DB/Redis/Neo4j 설정 가이드

### 아키텍처 (6개 모듈 설계서)
3. `docs/SYSTEM_ARCHITECTURE_REPORT.md` - 시스템 전체 아키텍처 (v1.6)
4. `docs/OPS_QUERY_BLUEPRINT.md` - OPS 쿼리 시스템 (6개 모드, CI Orchestrator)
5. `docs/CEP_ENGINE_BLUEPRINT.md` - CEP 엔진 (Trigger-Action, 알림, Redis)
6. `docs/API_ENGINE_BLUEPRINT.md` - API Engine (4가지 실행기, 보안)
7. `docs/SCREEN_EDITOR_BLUEPRINT.md` - Screen Editor (15 컴포넌트, Expression, RBAC)

### 기능/운영
8. `docs/FEATURES.md` - 기능 명세서
9. `docs/TESTIDS.md` - E2E 테스트 data-testid 표준

## 빠른 시작
1. **공통**
   - `make dev`로 전체 개발 서버 실행
   - `.env`는 커밋 불가, `.env.example`을 참고하여 환경변수 설정
2. **백엔드** (`apps/api`)
   - `cp .env.example .env` 후 PostgreSQL/Redis/Neo4j 정보 입력
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `make api-migrate`로 DB 마이그레이션 실행
3. **프론트엔드** (`apps/web`)
   - `cp .env.example .env.local` 후 API 설정
   - `npm install`
   - `npx playwright install` (E2E 테스트 전 필수)

## 주요 명령어 (`Makefile`)
- `make dev`, `make api-dev`, `make web-dev`
- `make api-migrate`, `make api-lint`, `make web-lint`
- `make api-test`, `make api-test-security`, `make web-test-e2e`
- `npm run lint`, `npm run type-check`, `npm run test:e2e`

## 테스트 & 검증
- **Backend**: `pytest tests/` + `make api-test(-unit|-integration|-security)`
- **Frontend**: `make web-test-e2e` (UI 변경 시 Playwright 실행)
- **보안**: `apps/api/tests/test_security*.py` (헤더, CORS, CSRF, 암호화, RBAC, JWT)
- **타입 검사**: `mypy .` (백엔드), `npm run type-check` (프론트엔드)

## 기술 스택

### Backend
FastAPI, Pydantic v2, SQLModel, Alembic, LangGraph, LangChain, OpenAI SDK, Redis, RQ, httpx, croniter, sse-starlette, psycopg >=3.1

### Frontend
Next.js 16, React 19, TypeScript 5.9, Tailwind CSS v4, shadcn/ui, TanStack Query v5, Zustand, Recharts, React Flow, AG Grid, Monaco Editor, react-pdf, Playwright

### Data
PostgreSQL + pgvector (1536-dim), Neo4j, Redis

## 안정성 및 품질
- ToolCall/Reference, UIScreen/Screen Asset, Binding Engine, Action Registry 등은 `schemas/` 기준 준수
- Data Explorer는 Read-only, 위험 명령어 allowlist 강제
- pre-commit (Ruff/Prettier) + ESLint + mypy + TypeScript strict mode
- E2E 테스트 22개 시나리오 (Playwright)

## 참고
- `AGENTS.md` 기준으로 작업, 변경 전후 checkpoint 커밋 고려
- 새로운 API 변경은 DTO/모델/문서/테스트 동시 변경, `ResponseEnvelope` 구조 준수
- 민감 정보/환경변수 코드 하드코딩 금지, `.env.example`에 예시 기입
