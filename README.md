## README.md (최소 실행 안내서)

# Tobit SPA AI

## Structure
- apps/api: FastAPI backend
- apps/web: Next.js frontend

## Structure Rules
Backend (FastAPI):
- apps/api/main.py: app entrypoint; only wiring (middleware, router include)
- apps/api/api: router-only (core/legacy endpoints); no business logic or DB access
- apps/api/app/modules/<domain>: domain modules (router/schemas/crud/services/models)
- apps/api/services: cross-module orchestration/policy logic
- apps/api/core: config/infra (settings, DB/Redis/Neo4j, logging, middleware)

Frontend (Next.js):
- apps/web/src/app: App Router pages/layouts
- apps/web/src/components: reusable UI blocks
- apps/web/src/lib: shared client utilities and thin API clients
- apps/web/public: static assets

## Project Documents
- [README.md](./README.md): Project install/run/structure troubleshooting guide (Source of Truth)
- [DEV_ENV.md](./DEV_ENV.md): 개발 환경 구축 및 DB 접속 정보 가이드
- [AGENTS.md](./AGENTS.md): AI 어시스턴트(에이전트)가 준수해야 할 프로젝트 규칙 및 고정 스택
- [docs/FEATURES.md](./docs/FEATURES.md): Feature specs, API notes, examples
- [docs/OPERATIONS.md](./docs/OPERATIONS.md): Operations and verification checklists
- [docs/PRODUCTION_GAPS.md](./docs/PRODUCTION_GAPS.md): MVP → 프로덕션 전환을 위한 TODO 리스트 (기능별 필수 보완 사항)

## Quick Start (dev)
1) apps/api/.env 생성 (.env.example 참고)
2) apps/web/.env.local 생성 (.env.example 참고)

Backend:
- create venv
- install deps
- run uvicorn

Frontend:
- install deps
- run dev server

## Dev Commands (Makefile)
- backend: `make api-dev`, `make api-test`, `make api-lint`, `make api-format`, `make api-migrate`
- frontend: `make web-dev`, `make web-lint`, `make web-format`, `make web-test`
- full dev: `make dev`

## Lint/Format & pre-commit
- Python: ruff check/format via pre-commit
- Frontend: eslint + prettier
- pre-commit 설치 후 `pre-commit install` 실행

## Troubleshooting
- `NEXT_PUBLIC_API_BASE_URL` 미설정 시 프론트 fetch 실패 → `apps/web/.env.local`에 API base URL 추가
- `alembic upgrade head` 미실행 시 테이블 누락 오류
- `ruff` 미설치 시 `pip install -r apps/api/requirements.txt` 재실행

## Git rule (vibe coding)
- before big change: `checkpoint` commit
- after success: commit again
