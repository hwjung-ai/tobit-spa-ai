# BOOTSTRAP_PROMPT.md
다음 지시를 그대로 수행하라.

- Docker 사용 금지. 서버에 설치된 Postgres/pgvector/Timescale/Neo4j/Redis에 환경변수로만 접속한다.
- Frontend: Next.js(App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + ECharts + React Flow
- Backend: FastAPI + Pydantic v2 + SQLModel + Alembic + RQ + LangGraph
- 응답 포맷: 모든 REST 응답은 {time, code, message, data}로 통일(SSE 제외)
- 아래 구조 고정:
  - apps/web
  - apps/api
- .env는 커밋 금지. .env.example만 제공.
- lint/test 기본 세팅 포함(최소: ruff+pytest, eslint+prettier)
- 최소 동작 코드 포함:
  - API: /health, /hello, /chat/stream(SSE)
  - Web: 채팅 UI에서 SSE 수신해 답/요약/상세를 렌더링

작업 결과는:
1) 생성/수정 파일 목록
2) 각 파일의 전체 내용
3) 실행 순서
를 제공하라.
