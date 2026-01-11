# AGENTS.md
# Tobit SPA AI – Project Constitution (AI MUST FOLLOW)

## 0. 최우선 원칙
1) 이 프로젝트는 실제 제품이다. 임시 해킹 코드 금지.
2) 선택지를 늘리지 말고, 정한 스택 안에서만 작업한다.
3) DB/Redis/Neo4j 접속정보는 환경변수로만 처리한다.
4) 큰 작업 전후에는 checkpoint 커밋을 권장한다.
5) 파일 경로는 프로젝트 루트 기준 절대 경로를 사용하거나, 문맥이 명확한 경우에만 상대 경로를 사용한다.

## 1. 고정 스택 (변경 금지)
Frontend: Next.js(App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + ECharts + React Flow  
Backend: FastAPI + Pydantic v2 + SQLModel + Alembic + LangGraph + (LangSmith Optional) + Redis + RQ  
Data: Postgres + pgvector + TimescaleDB + Neo4j + Redis  

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

예외 처리:
- FastAPI의 `HTTPException`을 사용하여 에러를 발생시킨다.
- 프론트엔드는 응답의 `detail` 필드(또는 `message`)를 사용자에게 표시한다.

## 4. DTO 규칙
- Request DTO / Response DTO 분리
- DB Model(SQLModel) / DTO 분리
- Validation은 DTO(Pydantic)에서 처리

## 5. 환경변수 규칙
- 하드코딩 금지
- .env 커밋 금지
- .env.example 제공 필수

## 6. 관측/실시간 규칙
- SSE 요구사항이 있는 경우, 주기 DB polling으로 대체 금지
- SSE 브로드캐스터는 단일 프로세스 메모리 기반입니다. 운영에서는 `uvicorn --workers 1` 또는 Redis Pub/Sub 전환 준비 (interface 분리) 필요합니다.
- SSE 스트림은 `ping` 이벤트로 keepalive를 제공하며, 클라이언트는 `EventSource.onerror` 핸들러에서 재연결/에러 상태를 표시해야 합니다.

## 7. Data Explorer 규칙
- DATA Explorer는 read-only(조회 전용)만 허용
- SQL/Cypher/Redis 위험 명령 금지 및 allowlist 강제

## 8. 개발 리소스 및 워크플로우 (필독)
이 파일(AGENTS.md)만 언급해도 아래 내용을 모두 준수해야 한다.

1) **문서 참조**:
   - `README.md`: 프로젝트 설치/실행/구조/트러블슈팅의 진실 공급원(Source of Truth)
   - `DEV_ENV.md`: 서버 DB(Postgres/Neo4j/Redis) 접속 정보 세팅 가이드
   - `docs/FEATURES.md`: 기능 스펙/API/예시(기능 변경 시 업데이트)
   - `docs/OPERATIONS.md`: 운영/검증 체크리스트(운영 절차 변경 시 업데이트)
2) **로그 위치 (디버깅 시 확인)**:
   - Backend: `apps/api/logs/api.log`
   - Frontend: `apps/web/logs/web.log`
3) **단축 명령어 (Makefile)**:
   - `make dev`: 전체 실행 (추천)
   - `make api-dev`, `make web-dev`: 개별 실행
   - `make api-lint`, `make web-lint`: 코드 품질 검사
   - `make api-migrate`: DB 마이그레이션 (`alembic upgrade head`) - **AI가 직접 실행할 것**
4) **품질 관리**:
   - `pre-commit` (Ruff/Prettier) 규칙 자동 준수
   - 주요 로직 수정 시 `pytest` 및 UI 테스트 검증 필수

## 9. 작업 완료 기준 (Definition of Done)
AI는 모든 작업 종료 시 다음 3가지를 확인해야 한다.
1) **검증 (Verification)**:
    - 단순 코드 생성이 아니라, 실제 동작(Curl/Test/UI) 확인 결과를 사용자에게 제시했는가?
    - 백엔드 로직 수정 시: `tests/`에 테스트 케이스 추가 또는 `curl` 스크립트 실행 결과 포함 필수.
2) **문서 최신화 (Documentation)**: 변경된 기능/API/환경변수가 `README.md`, `DEV_ENV.md`, `docs/FEATURES.md`, `docs/OPERATIONS.md`에 반영되었는가?
3) **Git 정리 (Version Control)**: 작업 단위별로 적절한 커밋 메시지를 생성하거나 체크포인트를 만들었는가?
