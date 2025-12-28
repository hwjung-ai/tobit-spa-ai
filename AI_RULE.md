# AI_RULES.md
# Tobit SPA AI – Project Constitution (AI MUST FOLLOW)

## 0. 최우선 원칙
1) 이 프로젝트는 실제 제품이다. 임시 해킹 코드 금지.
2) 선택지를 늘리지 말고, 정한 스택 안에서만 작업한다.
3) DB/Redis/Neo4j 접속정보는 환경변수로만 처리한다.
4) 큰 작업 전후에는 checkpoint 커밋을 권장한다.

## 1. 고정 스택 (변경 금지)
Frontend: Next.js(App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + ECharts + React Flow  
Backend: FastAPI + Pydantic v2 + SQLModel + Alembic + LangGraph + (LangSmith Optional) + Redis + RQ  
Data: Postgres + pgvector + TimescaleDB + Neo4j + Redis  
금지: Docker/compose, GraphQL/Hasura/PostgREST(이번 범위)

## 2. 프로젝트 구조 (고정)
apps/web = Next.js 프론트  
apps/api = FastAPI 백엔드

권장 백엔드 구조:
- api(router)는 얇게
- services는 정책/조합
- repositories는 DB 접근만

## 3. API 계약
모든 REST 응답은 아래 형식:
{ "time": "...", "code": 0, "message": "OK", "data": ... }
(SSE 스트리밍 제외)

## 4. DTO 규칙
- Request DTO / Response DTO 분리
- DB Model(SQLModel) / DTO 분리
- Validation은 DTO(Pydantic)에서 처리

## 5. 환경변수 규칙
- 하드코딩 금지
- .env 커밋 금지
- .env.example 제공 필수
