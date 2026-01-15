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
6. **경로 명확성**: 파일 경로는 프로젝트 루트 기준 절대 경로를 사용합니다. 문맥상 명확한 경우에만 제한적으로 상대 경로를 사용합니다.

---

## 3. 기술 스택 (변경 불가)

- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Apache ECharts, React Flow
- **Backend**: FastAPI, Pydantic v2, SQLModel, Alembic, LangGraph, Redis, RQ
- **Database Driver**: psycopg (>=3.1) - PostgreSQL 접근의 필수 드라이버
- **Data**: PostgreSQL, pgvector, TimescaleDB, Neo4j, Redis
- **Observability**: LangSmith (선택 사항)

---

## 4. 프로젝트 구조 (변경 불가)

- `apps/web`: Next.js 프론트엔드
- `apps/api`: FastAPI 백엔드

### 백엔드 구조 권장사항
- **Router (`api/` 또는 `app/modules/<...>/router.py`)**: API 경로 정의와 요청/응답 형식만 담당하며, 비즈니스 로직을 포함하지 않습니다.
- **Service (`app/modules/<...>/services.py`)**: 여러 데이터 소스나 모듈을 조합하여 비즈니스 로직과 정책을 구현합니다.
- **CRUD/Repository (`app/modules/<...>/crud.py`)**: 데이터베이스 접근(읽기, 쓰기, 수정, 삭제)만을 담당합니다.

### OPS 모듈 구조 (CI Orchestrator)
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

- **Data Explorer (데이터 탐색기)**:
  - 조회 전용(Read-only)으로만 동작해야 합니다.
  - SQL, Cypher, Redis에서 데이터 변경을 유발하는 위험한 명령어 사용을 금지하고, 허용된 명령어 목록(allowlist)을 강제해야 합니다.

---

## 9. 개발 워크플로우 (필독)

AI 에이전트는 이 문서(`AGENTS.md`)만 참조하더라도 아래의 모든 개발 리소스와 절차를 숙지하고 준수해야 합니다.

### 1) 핵심 문서
   - `README.md`: 프로젝트 설치, 실행, 구조 등 가장 기본적인 정보를 담은 **Source of Truth**입니다.
   - `DEV_ENV.md`: 개발 환경의 DB(Postgres/Neo4j/Redis) 접속 정보 설정 가이드입니다.
   - `docs/FEATURES.md`: 각 기능의 상세 명세, API 노트, 사용 예시를 담고 있습니다. (기능 변경 시 반드시 업데이트)
   - `docs/OPERATIONS.md`: 기능 검증을 위한 운영 체크리스트입니다. (운영 절차 변경 시 반드시 업데이트)
   - `docs/PRODUCTION_GAPS.md`: 프로덕션 전환을 위해 필요한 작업 목록(TODO)입니다.

### 2) 로그 위치
   - **Backend**: `apps/api/logs/api.log`
   - **Frontend**: `apps/web/logs/web.log`

### 3) 단축 명령어 (`Makefile` 기반)
   - `make dev`: 전체 개발 환경을 실행합니다. (가장 추천)
   - `make api-dev` / `make web-dev`: 백엔드 또는 프론트엔드를 개별적으로 실행합니다.
   - `make api-lint` / `make web-lint`: 각 파트의 코드 품질을 검사합니다.
   - `make api-migrate`: DB 마이그레이션(`alembic upgrade head`)을 실행합니다. **DB 스키마 변경 시 AI가 직접 실행해야 합니다.**

### 4) 품질 관리
   - 모든 코드는 `pre-commit` 훅(Ruff, Prettier)의 검사를 통과해야 합니다.
   - 핵심 로직을 수정할 경우, 반드시 `pytest`(백엔드) 또는 관련 UI 테스트(프론트엔드)를 통해 검증해야 합니다.
   - **Tool Contract 변경 시**: `ToolCall`, `ReferenceItem` 등의 스키마 수정 후에는 반드시 관련 executor/runner 테스트를 실행합니다.
   - **Database 드라이버 변경 시**: psycopg 버전 업그레이드 시 모든 DB 호출 코드를 검증하고, SQLAlchemy/SQLModel 마이그레이션이 필요한지 확인합니다.

---

## 10. 작업 완료의 정의 (Definition of Done)

AI 에이전트는 모든 작업을 종료하기 전, 다음 네 가지 기준을 충족했는지 스스로 확인해야 합니다.

1.  **검증 (Verification)**
    - 단순 코드 생성을 넘어, 실제 동작을 확인했습니까? (`curl` 테스트, `pytest` 실행 결과, UI 동작 스크린샷 등)
    - 백엔드 로직 수정 시, `tests/`에 관련 테스트 케이스를 추가하거나 `curl` 스크립트 실행 결과를 제시했습니까?
    - Tool Contract/Reference 관련 변경: 해당 스키마를 사용하는 모든 서비스(executor, runner 등)에서 정상 작동 확인했습니까?
    - DB 드라이버/마이그레이션: `make api-migrate` 실행 후 DB 스키마가 정상 생성되었는지 확인했습니까?

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
