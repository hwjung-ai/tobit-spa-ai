# Tobit SPA AI - 기능

> 최종 업데이트: 2026-02-15
> **전체 완성도: 95%**

## 1. 문서 개요

이 문서는 원래 README에 있던 기능 스펙, API 노트, 예시를 모았습니다.

### 제품 완성도 요약

| 메뉴 | 완성도 | 상태 |
|------|--------|------|
| **Ops Query System** | 88% | ✅ 상용 가능 |
| **SIM Workspace** | 91% | ✅ 상용 가능 |
| **Docs** | 100% | ✅ 상용 완료 |
| **API Manager** | 95% | ✅ 상용 가능 |
| **Screens** | 94% | ✅ 상용 가능 |
| **CEP Builder** | 100% | ✅ 상용 완료 |
| **Admin** | 95% | ✅ 상용 가능 |
| **CEP Events** | 92% | ✅ 상용 가능 |
| **Chat** | 92% | ✅ 상용 가능 |

### Frontend ESLint 정리 (2026-02-15)
- ✅ ESLint 경고: 87개 → 32개 (63% 감소)
- ✅ 타이포그래피 정규화: 14개 인스턴스
- ✅ CSS 변수 bracket 제거: 118개 → 0개
- ✅ 하드코딩된 색상 제거: 10개 이상
- ✅ Spacing 표준화: 73개+ 인스턴스

### 공통 인증 정책 (2026-02-11)
- 기본 정책: 모든 API는 JWT 인증을 거친다.
- 공개 엔드포인트: `POST /auth/login`, `POST /auth/refresh`만 허용한다.
- 개발 예외: `ENABLE_AUTH=false`일 때는 `get_current_user`가 JWT를 우회하고 디버그 사용자로 동작한다.
- 권한 개발 예외: `ENABLE_PERMISSION_CHECK=false`일 때는 RBAC 권한 검사(`check_permission`, `require_role`)를 우회한다.
- 회귀 테스트: `apps/api/tests/test_api_auth_unification.py`에서 공개 엔드포인트 외 인증 누락을 차단한다.


### 문서 읽는 법
- 각 기능 섹션 상단의 `소스 맵`은 프로젝트 루트 기준 경로를 제공합니다.
- Backend / Frontend / 설정 / DB / API 기준으로 분류되어 바로 코드 위치를 찾을 수 있습니다.
- 기능 수정이나 화면 보강 시 해당 섹션의 `소스 맵`부터 확인하세요.

## 2. UI/화면 기준 기능 맵

- API Manager UI (`/api-manager`, `/api-manager/chat`)
  - API 정의/관리 (`tb_api_def`, param_schema/runtime_policy/logic_spec)
  - 시스템 API dev 뷰 (flagged)
  - 워크플로 실행/로그, `/runtime/{path}` 연동
- UI Creator UI (`/ui-creator`, `/ui-creator/chat`)
  - UI 정의(`tb_ui_def`) 관리 + 런타임 엔드포인트 바인딩
  - Grid/Chart/Dashboard 스키마 + Preview
  - Dashboard 위젯 refresh/last updated
  - **Screen Editor Operations (U3-2)**:
    - Screen Diff / Compare UI (Draft vs Published)
    - Safe Publish Gate (4-step validation)
    - Regression Hook (post-publish testing)
    - Template-based Creation (8 templates + Blank)
    - **AI Copilot** (2026-02-14 NEW):
      - POST /ai/screen-copilot API
      - 자연어 → JSON Patch 변환
      - 신뢰도 점수, 설명, 제안
      - 빠른 액션 버튼 6개
    - **온보딩 시스템** (2026-02-14 NEW):
      - 7단계 튜토리얼 (환영, 컴포넌트, 속성, 액션, 바인딩, Copilot, 미리보기)
      - localStorage 완료 상태 저장
      - 빈 상태 안내 컴포넌트
- Data Explorer UI (`/data`)
  - Postgres/Neo4j/Redis 조회 전용 탭
  - Allowlist/limit 정책, AG Grid + 인스펙터
- CEP Builder UI (`/cep-builder`, `/cep-builder/chat`)
  - Rule 저장/시뮬레이션/수동 트리거
  - Scheduler 관측(status/instances)
  - Metric polling/telemetry, 스냅샷, 알림
- CEP Event Browser UI (`/cep-events`)
  - 이벤트 목록/상세/ACK, SSE 스트림
  - 필터 상태 URL 동기화, CSV/JSON 내보내기
  - Event run 조회(`/cep/events/run`)
- OPS/CI UI (`/ops`)
  - CI 디스커버리/정책 + `/ops/ask` 질문/답변
  - 그래프/메트릭/히스토리/시리즈 조회
  - AUTO 모드(레시피/동적/PATH/인사이트)
  - CEP simulate 연계 + Event Browser 링크
  - CI 목록 미리보기
  - 선택적 Asset 바인딩: `source_asset`, `schema_asset`, `resolver_asset`를 통해 질문 정규화/trace 적용
  - `schema_asset` 미지정 시 `source_asset` 기준으로 게시된 catalog를 자동 해석해 planner context에 주입 (source-schema 불일치 시 source 우선으로 catalog 재해석)
- SIM UI (`/sim`)
  - 시나리오 빌더(질문/서비스/전략/가정값/기간)
  - 전략 실행: Rule/Stat/ML/DL (`/api/sim/query`, `/api/sim/run`)
  - 결과: KPI 요약, 비교 차트, 토폴로지 맵, 알고리즘 근거
  - 부가 기능: 백테스트(`/api/sim/backtest`), CSV 내보내기(`/api/sim/export`)
  - 서비스 자동 초기값: `/api/sim/services` 조회 후 데이터 존재 서비스 우선 선택
- Admin UI (`/admin/assets`, `/settings/operations`, `/admin/inspector`)
  - Assets: Prompt/Mapping/Policy/Query 자산 관리 (draft, publish, rollback, SQL read-only 보기, thread-safe delete)
  - Catalog Scan API (`POST /asset-registry/catalogs/{asset_id}/scan`)는 JSON body `{ "schema_names": string[] | null, "include_row_counts": boolean }` 계약을 사용
  - Catalog Schema Discovery 실패는 브라우저 `alert()` 대신 Admin 표준 에러 UI(ValidationAlert + Toast)로 노출
  - Settings: 운영 설정 편집 (restart_required 표시)
  - LLM Settings 탭: provider(`openai|internal`), base URL, default/fallback model, timeout/retry, routing policy를 런타임 운영값으로 관리
  - LLM Runtime: `app/llm/client.py`가 operation settings의 published value를 우선 사용하고, 미설정 시 `.env` 값을 fallback으로 사용
  - Inspector: Trace ID 검색/필터, parent_trace 연결, Applied Assets · Plan · Execution · References · Answer Blocks · UI Render 섹션으로 전체 흐름 확인, UI Render telemetry/동작 상태 보기, Audit Log 추적
  - Inspector Trace 목록 검색은 `asset_id` 대신 `asset_name` 기준 필터를 사용하며, 그리드의 Applied Assets는 Asset ID 대신 등록된 Asset 이름으로 우선 표시
  - 상세 명세: `docs/ADMIN_UI_SPEC.md`, `docs/QUERY_ASSET_OPERATION_GUIDE.md`

### Copilot 안정화 (2026-02-10)
- 공통 JSON 파싱 유틸 추가: `apps/web/src/lib/copilot/json-utils.ts`
- 공통 Contract 검증/자동복구 유틸 추가: `apps/web/src/lib/copilot/contract-utils.ts`
- Copilot 메트릭 로깅 유틸 추가: `apps/web/src/lib/copilot/metrics.ts`
- API Manager/CEP 파서가 공통 유틸을 사용하도록 정리
- CEP Copilot은 스트리밍 중간 chunk를 즉시 오류로 처리하지 않도록 개선
- Screen Editor Copilot은 code-block 전용 파서에서 다중 JSON 후보 파싱으로 강화
- Builder별 contract 강제(`api_draft`, `cep_draft`, `screen_patch`) 및 1회 자동 복구(repair prompt) 지원
- Admin API 유틸은 non-JSON 응답(HTML/plain text)에서 JSON 강제 파싱을 피하도록 개선
- 상세 계획 문서: `docs/AI_COPILOT_IMPLEMENTATION_PLAN.md`

## 2-1. 공통 UI 표준

### 타임존 (Timezone)
- **Data (Backend)**: 모든 시간 데이터는 UTC로 저장되고 전송됩니다.
- **Display (Frontend)**: 화면에 표시될 때는 브라우저에서 `Asia/Seoul` (KST) 타임존으로 변환하여 표시합니다. 백엔드 데이터에 타임존 정보가 누락된 경우에도 강제로 UTC로 해석하여 KST 변환을 보장합니다.

### UI 스타일 (Styling)
- **Scrollbar**: OS 기본 스크롤바 대신 프로젝트 전역 `custom-scrollbar` 스타일(얇은 디자인, 다크 테마)을 적용합니다. 모든 스크롤 가능한 영역(OPS 히스토리, 그리드, JSON 뷰어 등)에 일관되게 적용됩니다.

## 2-2. SIM Workspace

### 소스 맵
- Frontend Page: `apps/web/src/app/sim/page.tsx`
- Topology 컴포넌트: `apps/web/src/components/simulation/TopologyMap.tsx`
- Backend Router: `apps/api/app/modules/simulation/api/router.py`
- Simulation Executor: `apps/api/app/modules/simulation/services/simulation/simulation_executor.py`
- Topology Loader: `apps/api/app/modules/simulation/services/topology_service.py`
- Baseline Loader: `apps/api/app/modules/simulation/services/simulation/baseline_loader.py`
- 테스트(Backend): `apps/api/tests/test_simulation_router.py`, `apps/api/tests/test_simulation_executor.py`, `apps/api/tests/test_simulation_rule_strategy.py`, `apps/api/tests/test_simulation_tenant_isolation.py`, `apps/api/tests/test_simulation_dl_strategy.py`
- 테스트(Frontend): `apps/web/tests-e2e/simulation.spec.ts`

### 제공 기능
- 메인 메뉴 `SIM`에서 시나리오 기반 What-if/Stress/Capacity 분석
- Rule/Stat/ML/DL 전략 선택 실행
- KPI 결과(기준값/시뮬레이션값/변화율)와 confidence, confidence interval 표시
- 토폴로지 맵에서 노드/링크 변화 시각화
- 백테스트 지표(`R2`, `MAPE`, `RMSE`, `Coverage@90`) 조회
- CSV export 제공

### 문서
- 사용자 가이드: `docs/USER_GUIDE_SIM.md`
- 아키텍처/설계: `docs/BLUEPRINT_SIM.md`
- 구현 상세: `docs/history/SIMULATION_IMPLEMENTATION_GUIDE.md`

## 3. API Manager (API 매니저)

### 런타임 & 개발 도구

#### 런타임 라우터

##### 소스 맵
- Backend 라우터: `apps/api/app/modules/api_manager/runtime_router.py`
- 실행기: `apps/api/app/modules/api_manager/executor.py`, `apps/api/app/modules/api_manager/script_executor.py`, `apps/api/app/modules/api_manager/workflow_executor.py`, `apps/api/app/modules/api_manager/script_executor_runner.py`
- 모델/CRUD: `apps/api/app/modules/api_manager/models.py`, `apps/api/app/modules/api_manager/crud.py`
- 라우터 등록: `apps/api/main.py`

- 저장된 API 정의는 `/runtime/{path}`로 호출할 수 있다. 저장된 `endpoint` 값은 요청이 올바르게 라우팅되도록 `/runtime/` prefix를 포함해야 한다.
- 사용 예:
  ```sh
  curl "http://localhost:8000/runtime/config-inventory?tenant_id=t1&limit=50"
  curl -X POST "http://localhost:8000/runtime/metrics-summary" \
    -H "Content-Type: application/json" \
    -d '{"params":{"metric_name":"cpu_usage"},"limit":100,"executed_by":"ops-bot"}'
  ```

### API Manager (API 매니저) - 정의/관리

#### 소스 맵
- Backend API: `apps/api/app/modules/api_manager/router.py`, `apps/api/app/modules/api_manager/schemas.py`
- 저장/모델: `apps/api/app/modules/api_manager/crud.py`, `apps/api/app/modules/api_manager/models.py`
- Frontend: `apps/web/src/app/api-manager/page.tsx`, `apps/web/src/app/api-manager/chat/page.tsx`
- UI 공통: `apps/web/src/components/builder/BuilderShell.tsx`, `apps/web/src/components/chat/BuilderCopilotPanel.tsx`

- `tb_api_def`는 `param_schema`, `runtime_policy`, `logic_spec` 3개의 JSON 컬럼을 노출한다. 기본값은 `'{}'::jsonb`이며 API 입력, 런타임 가드레일(timeout/limits), 워크플로/스크립트 메타데이터를 설명한다.
- 초기에는 `logic_type = sql` 정의만 `/api-manager/apis/{api_id}/execute` 또는 `/runtime/{path}`로 실행되었고, workflow/script 정의는 Builder UI로 저장만 가능하며 실행은 비활성화되어 있었다.
- API Definition 버전 이력은 `api_definition_versions` 테이블에 스냅샷(JSONB) 형태로 저장된다.
  - 생성/수정 시 자동 스냅샷 기록
  - 조회: `GET /api-manager/{api_id}/versions`
  - 롤백: `POST /api-manager/{api_id}/rollback?version=<n>` (version 미지정 시 직전 버전)
- 파라미터 스키마 예시:
  ```json
  {
    "tenant_id": {
      "type": "text",
      "required": true,
      "default": "t1",
      "description": "Tenant scope"
    },
    "start_time": {
      "type": "timestamptz",
      "description": "Begin lookback window"
    }
  }
```

프론트엔드 작업: `/api-manager`와 `BuilderShell` 패널을 수정해 JSON 편집기와 logic-type selector를 노출하고, SQL/workflow/script 대상은 편집 가능하게 유지하면서 실행은 안전하게 제한한다.
- `logic_type`에 `http`가 추가되어 JSON으로 구성된 외부 HTTP 요청을 실행할 수 있다. `logic_body`에는 최소 `url` 필드가 필요하며, `method`, `params`(쿼리스트링), `headers`, `body`(JSON payload)가 임의로 포함될 수 있다. 실행 시 server-side `httpx` 클라이언트가 해당 스펙을 호출하고 응답(JSON이나 텍스트)을 `rows` 컬렉션으로 변환하여 `ApiExecuteResponse`에 담는다. 실패/타임아웃은 502로 노출되며, `executed_sql`은 `HTTP <METHOD> <URL>` 형식으로 기록돼 Builder evidence 패널에 참고된다.

### API Manager Dev: 시스템 API (flagged)

#### 소스 맵
- Backend: `apps/api/app/modules/api_manager/router.py` (system endpoints)
- 설정: `apps/api/core/config.py` (`enable_system_apis`), `apps/api/.env` (`ENABLE_SYSTEM_APIS`)
- Frontend: `apps/web/src/app/api-manager/page.tsx`
- Frontend 플래그: `apps/web/.env.local` (`NEXT_PUBLIC_ENABLE_SYSTEM_APIS`)

- System APIs 목록은 FastAPI가 노출하는 OpenAPI 정의 라우트(예: `/data/*`, `/cep/*`, `/ops/*`)를 보여주는 dev 전용 뷰이다.
- 활성화: `apps/web/.env.local`
  ```
  NEXT_PUBLIC_ENABLE_SYSTEM_APIS=true
  ```
- 데이터 소스:
  1. UI는 `/api-manager/system/endpoints`를 조회해 OpenAPI `paths` 트리를 렌더링한다. 스키마에 정의된 HTTP verb만 표시되므로 RPC 스타일 엔드포인트는 목록이 의도적으로 작게 보인다.
  2. 각 엔드포인트 카드는 OpenAPI `summary`(테이블에 표시)와 확장된 `description` 텍스트를 상세 패널에 노출한다. 여기에는 read-only, LIMIT 200, timeout, allowlist, banned commands 등의 제약이 열거되어 `/data/postgres/query`나 `/data/redis/command`가 “기능이 부족해 보이는” 인상을 줄인다.
  3. 상세 카드는 supported actions/constraints 섹션을 강조 표시하여 각 RPC 엔드포인트의 가능/불가 항목을 빠르게 확인하게 한다.
  4. 설명 하단의 runtime policy textarea는 Discovered 항목에서는 비활성화되고, “System > Registered” 또는 Custom API 선택 시 UI 툴팁 안내대로 편집 가능해진다.
  5. 시스템 뷰의 `discovered`/`registered` 탭은 출처가 다릅니다.
     - **Discovered** 탭은 FastAPI가 노출하는 OpenAPI 경로(`/api-manager/system/endpoints`)를 불러와서 화면에 보여줍니다. 자동 수집된 경로이므로 편집/저장은 불가능합니다.
     - **Registered** 탭은 실제 DB의 `tb_api_def` 테이블(`api_type = "system"`)에 저장된 API 정의로, `logic_type`, `logic_body`, `runtime_policy` 같은 실체가 있습니다. 초기 마이그레이션에서 등록된 기본 `system` API(예: `/api-manager/metrics-summary`)도 여기에 포함되므로 Builder에서 직접 저장해본 적이 없어도 항목이 보일 수 있습니다.
- 활성화되면 API 목록에 `system` 탭이 나타난다. UI는 `/api-manager/apis`를 계속 호출해 등록된 API를 채우며, HTTP 호출 실패 시 로컬 캐시(`api-manager:api:*`)를 사용한다.

### API Manager (API 매니저) - 워크플로 실행

#### 소스 맵
- Backend 실행: `apps/api/app/modules/api_manager/workflow_executor.py`, `apps/api/app/modules/api_manager/executor.py`, `apps/api/app/modules/api_manager/script_executor.py`
- Backend API: `apps/api/app/modules/api_manager/router.py`, `apps/api/app/modules/api_manager/runtime_router.py`
- Frontend: `apps/web/src/app/api-manager/page.tsx`
- 모델/로그: `apps/api/app/modules/api_manager/models.py`

- 워크플로 실행(`logic_type = workflow`)은 `/api-manager/apis/{api_id}/execute`와 `/runtime/{path}`에서 모두 지원된다. 각 워크플로는 UUID로 저장된 SQL 또는 script API를 참조하며, 간단한 템플릿(`"{{params.X}}"`, `"{{steps.n1.rows}}"`, `"{{steps.n1.output}}"`)으로 노드 파라미터를 구성한다.
- 실행 로그는 전체 실행(`tb_api_exec_log`)과 각 노드의 상태/지속시간(`tb_api_exec_step_log`)을 모두 기록한다. 런타임 응답에는 노드별 breakdown과 집계된 reference 리스트가 포함되어 Builder shell의 evidence 패널에 활용된다.
- 워크플로 스펙 예시:
  ```json
  {
    "version": 1,
    "nodes": [
      {
        "id": "collect",
        "type": "sql",
        "api_id": "00000000-0000-0000-0000-000000000001",
        "params": {
          "tenant_id": "{{params.tenant_id}}"
        },
        "limit": 100
      },
      {
        "id": "summarize",
        "type": "script",
        "api_id": "00000000-0000-0000-0000-000000000002",
        "input": "{{steps.collect.rows}}",
        "params": {
          "mode": "digest"
        }
      }
    ]
  }
  ```
- 워크플로 실행 curl 예시:
  ```bash
  curl -X POST "http://localhost:8000/api-manager/apis/<workflow-id>/execute" \
    -H "Content-Type: application/json" \
    -d '{"params":{"tenant_id":"t1"},"limit":20,"input":{"extra":"value"}}'
  ```
- Builder shell의 Test 탭은 워크플로 실행 성공 시 step 요약, 최종 출력, reference 개수를 표시한다.

### Document Search (검색 제안/재색인)

#### 소스 맵
- Backend API: `apps/api/app/modules/document_processor/router.py`
- Search Service: `apps/api/app/modules/document_processor/services/search_service.py`
- 마이그레이션: `apps/api/alembic/versions/0048_add_p0_p1_foundation_tables.py`

- 검색 로그는 `document_search_log`에 저장되며, 자동완성 제안 API에서 활용된다.
  - 제안 조회: `GET /api/documents/search/suggestions?prefix=<text>&limit=5`
- 문서 재색인(경량): 문서의 `version`과 청크 `chunk_version`을 증가시킨다.
  - 재색인 실행: `POST /api/documents/{document_id}/reindex`
- 문서 버전 체인 조회:
  - 버전 조회: `GET /api/documents/{document_id}/versions`

## 4. UI Creator (UI 크리에이터)

### UI Creator (UI 크리에이터)

#### 소스 맵
- Backend API: `apps/api/app/modules/ui_creator/router.py`, `apps/api/app/modules/ui_creator/schemas.py`
- 저장/모델: `apps/api/app/modules/ui_creator/crud.py`, `apps/api/app/modules/ui_creator/models.py`
- Frontend: `apps/web/src/app/ui-creator/page.tsx`, `apps/web/src/app/ui-creator/chat/page.tsx`
- UI 공통: `apps/web/src/components/builder/BuilderShell.tsx`, `apps/web/src/components/chat/BuilderCopilotPanel.tsx`
- 런타임 연동: `apps/api/app/modules/api_manager/runtime_router.py`, `apps/api/app/modules/api_manager/router.py`

#### UIScreen Assets (U1-U2)
- Screen Schema v1: `apps/web/src/lib/ui-screen/screen.schema.ts`, `apps/web/src/lib/ui-screen/screen.schema.json`
- Component Registry v1: `apps/web/src/lib/ui-screen/component-registry.ts`
- Runtime Renderer: `apps/web/src/components/answer/UIScreenRenderer.tsx`
- Screen Asset CRUD: `apps/api/app/modules/asset_registry/router.py`, `docs/UI_SCREEN_ASSET_CRUD.md`
- Inspector 적용 자산 기록: `apps/api/app/modules/inspector/service.py`

- `tb_ui_def`는 런타임 엔드포인트 응답을 렌더링하는 UI 정의를 보관한다:
  - 컬럼: `ui_id`, `ui_name`, `ui_type` (`grid`/`chart`/`dashboard`), `schema`, `description`, `tags`, `is_active`, `created_by`, timestamps.
  - `schema.data_source.endpoint`는 반드시 `/runtime/...`를 가리켜야 하며 method와 선택적 `default_params`를 포함한다.
  - `schema.layout`가 렌더링을 주도한다. `type`이 컴포넌트(`grid` 또는 `chart`)를 선택하고, 추가 키(columns/xKey/yKey/title)가 뷰를 조정한다.
- API 라우트:
  - `GET /ui-defs`
  - `GET /ui-defs/{ui_id}`
  - `POST /ui-defs`
  - `PUT /ui-defs/{ui_id}`
각 응답은 `ResponseEnvelope`로 감싼다.
- Builder UI `/ui-creator`는 `BuilderShell`과 `ChatPanel`을 재사용하며 다음을 제공한다:
  - 탐색기 목록(좌측)
  - schema 및 preview/params 토글용 JSON 편집기(중앙)
  - 설정된 `/runtime/...` 엔드포인트를 호출해 테이블/차트를 렌더링하는 Preview 패널
  - Runtime URL 힌트 + 새로고침 컨트롤
- 그리드 스키마 예시:
  ```json
  {
    "data_source": {
      "endpoint": "/runtime/config-inventory",
      "method": "GET",
      "default_params": {
        "tenant_id": "t1",
        "limit": 10
      }
    },
    "layout": {
      "type": "grid",
      "columns": ["tenant_id", "ci_count"],
      "title": "Config inventory"
    }
  }
  ```
- 차트 스키마 예시(`"/runtime/metrics-summary"` 호출):
  ```json
  {
    "data_source": {
      "endpoint": "/runtime/metrics-summary",
      "method": "GET",
      "default_params": {
        "limit": 30
      }
    },
    "layout": {
      "type": "chart",
      "chartType": "line",
      "xKey": "metric_name",
      "yKey": "peak",
      "title": "Metric peaks"
    }
  }
  ```

## 5. Data Explorer (데이터 탐색기)

### Data Explorer (데이터 탐색기, 조회 전용, dev 전용)

#### 소스 맵
- Backend: `apps/api/app/modules/data_explorer/router.py`, `apps/api/app/modules/data_explorer/services/*.py`
- Schemas: `apps/api/app/modules/data_explorer/schemas.py`
- 설정: `apps/api/core/config.py`, `apps/api/.env` (`ENABLE_DATA_EXPLORER`, `DATA_*`)
- Frontend: `apps/web/src/app/data/page.tsx`, `apps/web/src/components/data/Neo4jGraphFlow.tsx`
- Frontend 플래그: `apps/web/.env.local` (`NEXT_PUBLIC_ENABLE_DATA_EXPLORER`)

- UI 경로: `/data` (상단 DATA 메뉴)
- 활성화:
  - `apps/api/.env`: `ENABLE_DATA_EXPLORER=true`
  - `apps/web/.env.local`: `NEXT_PUBLIC_ENABLE_DATA_EXPLORER=true`
- 기능:
  - Postgres / Neo4j / Redis 탭
  - 탐색 + Query/Command 모드
  - 결과 그리드(AG Grid) + 인스펙터
- 제한:
  - 모든 실행은 read-only
  - SQL은 SELECT만 허용, LIMIT 강제
  - Cypher는 MATCH/RETURN만 허용
  - Redis는 allowlist 명령만 허용
  - Redis scan 시 prefix/pattern은 `DATA_REDIS_ALLOWED_PREFIXES`로 시작해야 함
- 관련 명령:
  - `apps/api/scripts/seed/seed_redis.py`로 테스트 데이터 자동 생성
  - `npm run web-dev` 이후 `/data`로 접속하여 Scan/Query/Redis Command 확인
- UI 노트:
  - AG Grid를 community legacy theme로 등록했고 column reorder/resize/filter/sort를 켰습니다.
  - TanStack Query는 polling 없이 SSE/new_event/ack_event summary로만 업데이트합니다.
  - `apps/web/src/app/data/page.tsx`에 `runQueryMutation`과 `renderExplorer` 함수가 데이터 소스를 포괄합니다.

## 6. CEP

### CEP Builder (CEP 빌더)

#### 소스 맵
- Backend API: `apps/api/app/modules/cep_builder/router.py`, `apps/api/app/modules/cep_builder/schemas.py`
- 저장/모델: `apps/api/app/modules/cep_builder/crud.py`, `apps/api/app/modules/cep_builder/models.py`
- 실행기: `apps/api/app/modules/cep_builder/executor.py`, `apps/api/app/modules/cep_builder/notification_engine.py`
- 스케줄러: `apps/api/app/modules/cep_builder/scheduler.py`, `apps/api/app/modules/cep_builder/event_broadcaster.py`
- Frontend: `apps/web/src/app/cep-builder/page.tsx`, `apps/web/src/app/cep-builder/chat/page.tsx`


- **Rule 저장**: `tb_cep_rule`는 rule 이름, trigger/action 스펙, 활성화 플래그, 타임스탬프를 저장한다. `tb_cep_exec_log`는 각 실행을 `status`(success/fail/dry_run), duration, `references`와 함께 기록해 추후 검사할 수 있게 한다.
- **시뮬레이션 + 수동 트리거**: `/cep/rules/{rule_id}/simulate`는 액션을 실행하지 않고 trigger(페이로드 메트릭 사용)를 평가하며, `/cep/rules/{rule_id}/trigger`는 조건이 충족되면 runtime `action_spec`을 실행한다. 두 엔드포인트 모두 `ResponseEnvelope`를 반환한다.
- **스케줄러**: `"trigger_type": "schedule"` 규칙만 background scheduler(`croniter`)에서 자동 실행된다. Metric/event 규칙은 수동으로 트리거할 수 있다.

#### 규칙 예시

1. **Metric 규칙** – `cpu_usage`가 80%를 초과하면 `/runtime/config-inventory`를 호출한다.

```json
{
  "rule_name": "CPU spike trace",
  "trigger_type": "metric",
  "trigger_spec": { "field": "cpu_usage", "op": ">", "value": 80 },
  "action_spec": {
    "endpoint": "/runtime/config-inventory",
    "method": "GET",
    "params": { "tenant_id": "t1" }
  },
  "is_active": true
}
```

2. **Schedule 규칙** – 5분마다 실행되어 metrics digest API를 호출한다.

```json
{
  "rule_name": "Digest ticker",
  "trigger_type": "schedule",
  "trigger_spec": { "interval_seconds": 300 },
  "action_spec": {
    "endpoint": "/runtime/metrics-summary",
    "method": "GET"
  },
  "is_active": true
}
```

#### CLI 예시

```bash
# simulate (payload에 metrics 포함)
curl -s -X POST http://localhost:8000/cep/rules/<rule_id>/simulate \
  -H "Content-Type": application/json" \
  -d '{"test_payload":{"metrics":{"cpu_usage":85}}}'

# 수동 트리거
curl -s -X POST http://localhost:8000/cep/rules/<rule_id>/trigger \
  -H "Content-Type": application/json" \
  -d '{"payload":{"metrics":{"cpu_usage":85}}}'

# 로그 조회
curl -s http://localhost:8000/cep/rules/<rule_id>/exec-logs
```

### CEP Event Browser (End-to-End 관측)

#### 소스 맵
- Backend API: `apps/api/app/modules/cep_builder/router.py` (`/cep/events*`, `/cep/events/stream`)
- 이벤트 처리: `apps/api/app/modules/cep_builder/crud.py`, `apps/api/app/modules/cep_builder/event_broadcaster.py`
- Frontend: `apps/web/src/app/cep-events/page.tsx`, `apps/web/src/components/CepEventBell.tsx`, `apps/web/src/app/layout.tsx`
- 마이그레이션: `apps/api/alembic/versions/0019_add_cep_event_ack_fields.py`

- 데이터 소스: `tb_cep_notification_log` + `tb_cep_notification` + `tb_cep_rule`
- 이벤트 필드:
  - event_id = notification_log.log_id (이벤트 ID)
  - triggered_at = fired_at (발생 시간)
  - rule_id/rule_name = notification.rule_id → tb_cep_rule (룰 정보)
  - summary = reason 우선, 없으면 payload 요약
  - condition_evaluated/extracted_value = payload 우선, 없으면 exec_log 보완
- ACK 처리: `tb_cep_notification_log.ack`, `ack_at`, `ack_by` (마이그레이션 0019)
- UI 진입: 헤더 알림 아이콘 → `/cep-events`
- 갱신: SSE(`/cep/events/stream`)로 summary/new_event/ack_event 수신 (DB polling 없음)
- 필터 공유: `ack`, `severity`, `rule_id`, `since`, `until` 쿼리스트링 유지
- 내보내기: 현재 필터 결과를 CSV/JSON으로 다운로드
- 주의: SSE 브로드캐스터는 단일 프로세스 메모리 기반입니다. 운영에서는 `uvicorn --workers 1` 권장 또는 Redis PubSub로 교체 필요.
- SSE keepalive: 서버가 `ping` 이벤트를 주기적으로 전송.

#### API
- `GET /cep/events`
- `GET /cep/events/{event_id}`
- `POST /cep/events/{event_id}/ack`
- `GET /cep/events/summary`
- `GET /cep/events/stream` (SSE)

#### 마이그레이션
- `apps/api/alembic/versions/0019_add_cep_event_ack_fields.py`
- 적용: `cd apps/api` → `alembic upgrade head`

#### 노트

- `action_spec.endpoint`는 `/runtime/...` 경로를 가리켜 기존 런타임 라우터를 활용해야 한다.
- 시뮬레이션/수동 트리거는 관측을 위해 `references` + status를 반환한다. rule이 실행되면(수동 또는 scheduler) exec log row가 기록되어 Builder UI가 결과를 노출할 수 있다.
- 현재 `schedule` 규칙만 자동 실행되며 metric/event 규칙은 수동 시뮬레이션 또는 트리거가 필요하다.
- **Dashboard schema 지원**: 이제 `ui_type: "dashboard"` 정의를 저장할 수 있다. Dashboard 스키마는 `widgets` 배열이 필요하며, 각 위젯은 `id`, `layout`(`x,y,w,h`), `data_source.endpoint`, `render.type`(`grid`, `chart_line`, `json`)를 지정해야 한다. UI Creator는 대시보드를 미리보기에서 직접 렌더링한다.
- **Dashboard preview 업데이트**: 모든 위젯이 자체 REFRESH 버튼과 “last updated” 타임스탬프를 보여주며, 페이지를 다시 로드하지 않고 선택한 런타임 호출을 재실행할 수 있다.

- **Dashboard 스키마 리프레셔**

- 위젯이 반드시 정의해야 하는 항목:
  - `data_source.endpoint` (absolute 또는 `/runtime...`/`/cep...`)
  - `data_source.method` (`GET`/`POST`)
  - `render.type` (`grid`, `chart_line`, `json`) + ResponseEnvelope 내부의 dot-path (`rowsPath`/`path`) (예: `data.result.rows`, `data.logs`)
  - 12컬럼 그리드의 `layout` 좌표(`x,y,w,h`)
- 각 위젯은 독립적으로 런타임 데이터를 가져오며, 로딩/에러 상태를 가지고, 성공 시 “last updated”(KST) 타임스탬프와 Refresh 버튼을 노출한다. Preview 헤더는 “Refresh all widgets”를 제공해 페이지 재로드 없이 모든 요청을 재실행할 수 있다.

#### 대시보드 스키마 예시

```json
{
  "version": 1,
  "ui_type": "dashboard",
  "title": "CEP + Ops Overview",
  "grid": { "cols": 12, "rowHeight": 80 },
  "widgets": [
    {
      "id": "leader",
      "title": "CEP Leader",
      "layout": { "x": 0, "y": 0, "w": 6, "h": 2 },
      "data_source": { "endpoint": "/cep/scheduler/status", "method": "GET" },
      "render": { "type": "json", "path": "data.status" }
    },
    {
      "id": "logs",
      "title": "Recent CEP logs",
      "layout": { "x": 6, "y": 0, "w": 6, "h": 4 },
      "data_source": { "endpoint": "/cep/rules/<rule_id>/exec-logs", "method": "GET" },
      "render": { "type": "grid", "rowsPath": "data.logs" }
    },
    {
      "id": "inventory",
      "title": "Configuration inventory",
      "layout": { "x": 0, "y": 2, "w": 12, "h": 4 },
      "data_source": {
        "endpoint": "/runtime/api-manager/config-inventory",
        "method": "GET",
        "default_params": { "tenant_id": "t1" }
      },
      "render": { "type": "grid", "rowsPath": "data.result.rows" }
    },
    {
      "id": "cpu-trend",
      "title": "CPU Trend",
      "layout": { "x": 0, "y": 6, "w": 12, "h": 4 },
      "data_source": { "endpoint": "/runtime/metrics-summary", "method": "GET" },
      "render": {
        "type": "chart_line",
        "rowsPath": "data.result.rows",
        "xKey": "metric_name",
        "yKey": "peak"
      }
    }
  ]
}
```

- 렌더링이 활성화되어 각 위젯이 자체 런타임 호출을 수행하고, grid/json 렌더러가 rows/objects를 표시하며, `chart_line` 렌더러가 지원된다.
- **Dashboard widget refresh**: 모든 위젯이 “last updated”(KST)와 Refresh 버튼을 표시하며, Preview 헤더에는 “Refresh all widgets” 컨트롤이 있어 페이지 재로드 없이 모든 요청을 재실행할 수 있다.
- **중복 실행 방지**: scheduler나 trigger가 같은 rule_id를 동시에 실행하지 않도록 per-rule advisory lock을 사용합니다. 이미 실행 중이면 status가 `skipped`가 되고 `error_message`에 `"rule already running"`이 기록됩니다. 이를 통해 scheduler와 수동 trigger가 충돌할 때 한 번만 실행됩니다.
- **skipped 예시**:
  ```bash
  curl -s -X POST http://localhost:8000/cep/rules/<rule_id>/trigger \
    -H "Content-Type: application/json" \
    -d '{"payload":{"metrics":{"cpu_usage":85}}}'

  curl -s -X POST http://localhost:8000/cep/rules/<rule_id>/trigger \
    -H "Content-Type: application/json" \
    -d '{"payload":{"metrics":{"cpu_usage":85}}}'
  ```
  두 번째 호출은 `{"status":"skipped","references":{"skipped_reason":"rule already running",...}}`를 반환하고 `tb_cep_exec_log.status`에 `skipped`로 남습니다.
### CEP Scheduler 관측

#### 소스 맵
- 스케줄러: `apps/api/app/modules/cep_builder/scheduler.py`
- 상태 API: `apps/api/app/modules/cep_builder/router.py` (`/cep/scheduler/*`)
- 모델/상태 테이블: `apps/api/app/modules/cep_builder/models.py` (`tb_cep_scheduler_state`)
- 설정: `apps/api/core/config.py` (`ops_enable_cep_scheduler`, `cep_*`)


- **왜 필요한가?** 멀티호스트/멀티프로세스 환경에서 scheduler가 동시에 실행되면 rule이 중복 실행되고 로그가 꼬이므로, PG advisory lock을 통해 단일 리더만 루프를 돌립니다. 동시에 락을 든 프로세스는 상태 테이블에 heartbeat를 기록하여 운영자가 상태를 확인할 수 있게 합니다.
- **상태 API**: `/cep/scheduler/status`에서 현재 leader와 마지막 heartbeat, `/cep/scheduler/instances`에서 모든 인스턴스의 상태를 조회할 수 있습니다.
- **기동 제어**: CEP Scheduler는 기본적으로 비활성화되어 있습니다. `apps/api/.env` (또는 `.env.example`)에 `OPS_ENABLE_CEP_SCHEDULER=true`를 설정해야만 `/cep/scheduler/...` 루프가 시작됩니다. 환경변수가 `true`일 때만 `[CEP] Scheduler enabled (OPS_ENABLE_CEP_SCHEDULER=true)` 로그가 찍히고 leader 락/metric polling/notification loop가 실행됩니다. 기본 `false` 상태에서는 `[CEP] Scheduler disabled by environment variable` 로그만 찍히고 loop는 생성되지 않습니다.
- **metric polling 상태**: `cep_enable_metric_polling`이 켜진 leader 프로세스는 metric rules를 주기적으로 평가/실행하며 `/cep/scheduler/status`에 `metric_polling_enabled`, `last_metric_poll_at`, `polled_rule_count_last_tick` 필드를 통해 마지막 tick의 상태를 확인할 수 있습니다.
- ** heartbeat 주기**: leader는 10초마다 `tb_cep_scheduler_state`에 `last_heartbeat_at`을 갱신하고, leader가 아닌 프로세스도 시작 시 상태를 남겨 운영자에게 “leader가 없다”는 사실을 알립니다.

#### 상태 API 예시

```bash
curl -s http://localhost:8000/cep/scheduler/status
```
응답 예시:
```json
  {
    "time": "...",
    "code": 0,
    "message": "OK",
    "data": {
      "status": {
        "instance_id": "host:12345:abcd",
        "is_leader": true,
        "leader_instance_id": "host:12345:abcd",
        "last_heartbeat_at": "2025-12-31T22:50:10.123Z",
        "started_at": "2025-12-31T22:49:55.123Z",
        "updated_at": "2025-12-31T22:50:10.123Z",
        "leader_stale": false,
        "metric_polling_enabled": false,
        "last_metric_poll_at": null,
        "polled_rule_count_last_tick": 0
      }
    }
  }
  ```

### 메트릭 폴링

#### 소스 맵
- 스케줄러/루프: `apps/api/app/modules/cep_builder/scheduler.py`
- Telemetry API: `apps/api/app/modules/cep_builder/router.py` (`/cep/scheduler/metric-polling`)
- 룰/스냅샷 접근: `apps/api/app/modules/cep_builder/crud.py`, `apps/api/app/modules/cep_builder/models.py`
- 설정: `apps/api/core/config.py` (`cep_enable_metric_polling`, `cep_metric_*`)


- **개요**: `cep_enable_metric_polling` 플래그가 켜진 leader에서 metric rules를 주기적으로 evaluate/trigger하며 `/cep/scheduler/metric-polling`으로 상태·매치·실패 요약을 조회합니다.
- **설정 플래그**:
  - `cep_enable_metric_polling`: polling 전체를 토글합니다.
  - `cep_metric_poll_global_interval_seconds`: polling tick 간격(초).
  - `cep_metric_poll_concurrency`: 동시에 평가 가능한 rule 수(세마포어).
  - `cep_metric_http_timeout_seconds`: runtime fetch시 HTTP 타임아웃(초).
- **운영 확인 순서**:
  1. `/cep/scheduler/status`에서 leader 여부와 `metric_polling_enabled`/`metric_poll_last_tick_*` 필드를 확인합니다.
  2. `/cep/scheduler/metric-polling`에서 `telemetry`와 `recent_matches`/`recent_failures`를 확인합니다.
  3. metric rule의 `/cep/rules/{id}/exec-logs`로 실행 결과(success/fail/skipped)와 기간을 검토합니다.
  4. UI Creator의 “Insert Metric Polling Template” 버튼으로 대시보드 정의를 불러온 뒤 `<METRIC_RULE_ID>`를 올바른 rule ID로 교체하고 저장합니다.

#### 대시보드 스키마 샘플

```json
{
  "version": 1,
  "ui_type": "dashboard",
  "widgets": [
    {
      "id": "metric-status",
      "title": "Metric polling status",
      "layout": { "x": 0, "y": 0, "w": 6, "h": 6 },
      "data_source": { "endpoint": "/cep/scheduler/status", "method": "GET" },
      "render": { "type": "json", "path": "data.status" }
    },
    {
      "id": "metric-instances",
      "title": "Scheduler instances",
      "layout": { "x": 6, "y": 0, "w": 6, "h": 6 },
      "data_source": { "endpoint": "/cep/scheduler/instances", "method": "GET" },
      "render": {
        "type": "grid",
        "rowsPath": "data.instances",
        "columns": ["instance_id", "is_leader", "last_heartbeat_at", "leader_stale"]
      }
    },
    {
      "id": "metric-matches",
      "title": "Recent metric matches",
      "layout": { "x": 0, "y": 6, "w": 12, "h": 5 },
      "data_source": { "endpoint": "/cep/scheduler/metric-polling", "method": "GET" },
      "render": {
        "type": "grid",
        "rowsPath": "data.telemetry.recent_matches",
        "columns": ["rule_name", "actual_value", "threshold", "op", "matched_at"]
      }
    },
    {
      "id": "metric-logs",
      "title": "Metric rule exec logs",
      "layout": { "x": 0, "y": 11, "w": 12, "h": 6 },
      "data_source": { "endpoint": "/cep/rules/<METRIC_RULE_ID>/exec-logs", "method": "GET" },
      "render": {
        "type": "grid",
        "rowsPath": "data.logs",
        "columns": ["status", "duration_ms", "triggered_at", "error_message"]
      }
    }
  ]
}
```

#### cURL 예시

1. scheduler 상태
```bash
curl -s http://localhost:8000/cep/scheduler/status
```
2. metric polling telemetry 조회
```bash
curl -s http://localhost:8000/cep/scheduler/metric-polling
```
3. metric rule 생성
```bash
curl -s -X POST http://localhost:8000/cep/rules \
  -H "Content-Type: application/json" \
  -d '{ 
    "rule_name": "High CPU",
    "trigger_type": "metric",
    "trigger_spec": {
      "source": "runtime",
      "endpoint": "/runtime/ops/metrics-latest",
      "method": "GET",
      "params": { "metric_name": "cpu_usage", "tenant_id": "t1" },
      "value_path": "data.result.rows.0.value",
      "op": ">",
      "threshold": 80,
      "poll_interval_seconds": 30
    },
    "action_spec": {
      "endpoint": "/runtime/ops/alert",
      "method": "POST",
      "params": { "subject": "cpu" }
    }
  }'
```
4. simulate (dry run) 실행
```bash
curl -s -X POST http://localhost:8000/cep/rules/<RULE_ID>/simulate \
  -H "Content-Type: application/json" \
  -d '{ 
    "test_payload": {
      "data": { "result": { "rows": [{ "value": 85 }] } }
    }
  }'
```
5. exec logs 조회
```bash
curl -s http://localhost:8000/cep/rules/<RULE_ID>/exec-logs
```

### 메트릭 폴링 스냅샷

#### 소스 맵
- 스냅샷 저장/조회: `apps/api/app/modules/cep_builder/scheduler.py`, `apps/api/app/modules/cep_builder/crud.py`
- 모델/테이블: `apps/api/app/modules/cep_builder/models.py` (`tb_cep_metric_poll_snapshot`)
- API: `apps/api/app/modules/cep_builder/router.py` (`/cep/scheduler/metric-polling/snapshots*`)
- 설정: `apps/api/core/config.py` (`cep_metric_poll_snapshot_interval_seconds`)


- **설정**: `cep_metric_poll_snapshot_interval_seconds`(기본 60초)마다 leader가 `tb_cep_metric_poll_snapshot`에 telemetry를 저장합니다.
- **필요성**: leader 교체/재시작 후에도 최근 tick을 복구하고, 장기 추이·장애 분석·failover 복구·감사 보고를 위해 상태를 유지할 수 있습니다.
- **조회 API**
  1. 히스토리: `/cep/scheduler/metric-polling/snapshots?limit=200&since_minutes=60`
  2. 최근 tick: `/cep/scheduler/metric-polling/snapshots/latest`
- **대시보드 위젯 예시**
  ```json
  {
    "id": "metric-snapshots",
    "title": "Metric polling snapshots",
    "layout": { "x": 0, "y": 17, "w": 12, "h": 6 },
    "data_source": { "endpoint": "/cep/scheduler/metric-polling/snapshots?since_minutes=120", "method": "GET" },
    "render": {
      "type": "grid",
      "rowsPath": "data.snapshots",
      "columns": ["tick_at", "rule_count", "matched_count", "fail_count", "last_error"]
    }
  }
  ```

#### cURL 예시 (snapshot)

1. latest 조회
```bash
curl -s http://localhost:8000/cep/scheduler/metric-polling/snapshots/latest
```
2. range 조회
```bash
curl -s "http://localhost:8000/cep/scheduler/metric-polling/snapshots?limit=200&since_minutes=60"
```

2. instances 조회
```bash
curl -s http://localhost:8000/cep/scheduler/instances
```
응답 예시:
```json
{
  "data": {
    "instances": [
      {
        "instance_id": "host:12345:abcd",
        "is_leader": true,
        "last_heartbeat_at": "...",
        "started_at": "...",
        "updated_at": "...",
        "notes": "scheduler started"
      },
      {
        "instance_id": "host:12345:ef12",
        "is_leader": false,
        "last_heartbeat_at": "...",
        "started_at": "...",
        "updated_at": "...",
        "notes": "leader unavailable"
      }
    ]
  }
}
```

### 메트릭 폴링 알림

#### 소스 맵
- 알림 엔진: `apps/api/app/modules/cep_builder/notification_engine.py`
- API/저장소: `apps/api/app/modules/cep_builder/router.py`, `apps/api/app/modules/cep_builder/crud.py`
- 모델: `apps/api/app/modules/cep_builder/models.py` (`tb_cep_notification*`)
- 설정: `apps/api/core/config.py` (`cep_enable_notifications`, `cep_notification_interval_seconds`)


- **왜 필요한가?** metric snapshot/telemetry를 주기적으로 감시하면서 조건을 만족하면 외부 webhook으로 운영 알림을 보내고 cooldown/max_per_hour 정책으로 폭주와 중복을 막습니다.
- **설정 플래그**:
  - `cep_enable_notifications`: webhook 알림 루프를 켜는 스위치(leader만 실행).
  - `cep_notification_interval_seconds`: notification loop 간격(초).
- **trigger 예시** (`trigger.type = "snapshot_threshold"`):
  ```json
  {
    "type": "snapshot_threshold",
    "field": "matched_count",
    "op": ">=",
    "value": 1,
    "window_minutes": 5
  }
  ```
  - `field`: `tb_cep_metric_poll_snapshot` 컬럼 (`matched_count`, `fail_count`, 등).
  - `window_minutes`: 조회할 snapshot window(분).
- **policy 예시**:
  ```json
  {
    "cooldown_seconds": 300,
    "max_per_hour": 20
  }
  ```
  - `cooldown_seconds`: 동일 dedup key(기본 `notification_id:type:field:op:value`)로 쿨다운.
  - `max_per_hour`: 지난 60분 동안 `sent` 상태 로그 개수가 이 개수를 넘으면 발송을 스킵.
- **채널/보안**: 현재 `"webhook"`만 지원하며 127.0.0.0/8 · 10/8 · 172.16/12 · 192.168/16 · 169.254/16 · ::1 등 private/metadata IP로의 호출은 차단됩니다.
- **운영 확인 순서**:
  1. `/cep/scheduler/status`에서 leader/metric polling 상태를 확인.
  2. `/cep/scheduler/metric-polling`에서 최근 매치/실패/telemetry를 점검.
  3. `/cep/scheduler/metric-polling/snapshots`로 pre-condition 스냅샷을 확인.
  4. `/cep/notifications/{notification_id}/logs`로 실제 webhook 발송·스킵·실패 기록을 봅니다.
- **UI Creator 위젯 예시**:
  ```json
  {
    "id": "notification-logs",
    "title": "Metric notification history",
    "layout": { "x": 0, "y": 23, "w": 12, "h": 6 },
    "data_source": {
      "endpoint": "/cep/notifications/<NOTIFICATION_ID>/logs",
      "method": "GET"
    },
    "render": {
      "type": "grid",
      "rowsPath": "data.logs",
      "columns": ["status", "reason", "fired_at", "dedup_key"]
    }
  }
  ```
- **cURL 예시**:
  1. notification 생성
  ```bash
  curl -s -X POST http://localhost:8000/cep/notifications \
    -H "Content-Type: application/json" \
    -d '{ 
      "name": "Metric match alert",
      "channel": "webhook",
      "webhook_url": "https://example.com/webhook",
      "trigger": {
        "type": "snapshot_threshold",
        "field": "matched_count",
        "op": ">=",
        "value": 1,
        "window_minutes": 5
      },
      "policy": {
        "cooldown_seconds": 300,
        "max_per_hour": 20
      }
    }'
  ```
  2. logs 조회
  ```bash
  curl -s http://localhost:8000/cep/notifications/<NOTIFICATION_ID>/logs
  ```

## 7. OPS/CI

### CI 디스커버리 & 정책

#### 소스 맵
- Discovery 스크립트: `apps/api/app/modules/ops/services/ci/discovery/postgres_catalog.py`, `apps/api/app/modules/ops/services/ci/discovery/neo4j_catalog.py`
- 정책/뷰: `apps/api/app/modules/ops/services/ci/policy.py`, `apps/api/app/modules/ops/services/ci/view_registry.py`, `apps/api/app/modules/ops/services/ci/relation_mapping.yaml`
- 산출물: `apps/api/app/modules/ops/services/ci/catalog/*.json`


> 참고: OPS CI 구현은 `apps/api/app/modules/ops/services/ci` 하위에 통합되어 있으며, 루트 `ops` 패키지는 제거되었습니다. 모든 import, 스크립트, `python -m` 호출은 이 경로를 기준으로 작성하세요.
- Frontend: `apps/web/src/app/ops/nextActions.ts`, `apps/web/src/components/answer/BlockRenderer.tsx`


#### 개요
- CI 탭은 질문이 모호한 CI 후보, truncated 그래프, 대체 뷰를 만들 때마다 결정적 `next_actions`를 노출하여 LLM을 다시 호출하지 않고도 재실행할 수 있게 한다.
- Trace 데이터(`trace.plan_validated`, `trace.policy_decisions`, `trace.tool_calls`)는 히스토리 엔트리별로 저장되어 rerun 요청을 구동한다(UI는 선택된 `ci_id`/patch와 함께 `trace.plan_validated`를 `rerun.base_plan`으로 전송).
- next actions는 `ops/ci/actions.py`와 프론트엔드 `apps/web/src/app/ops/nextActions.ts`에 정의된 typed contract를 따르며, `rerun`, `open_trace`, `copy_payload` 변형이 policy guardrails를 유지한 채 depth/view/aggregate 변경을 가능하게 한다.

#### 실행
1. Step 1 discovery와 Step 2 catalog/policy refresh를 수행한다.
2. 백엔드 + web UI를 실행하고 OPS CI 탭을 선택한 뒤 자연어 질문을 입력한다.
3. 답변 하단의 `next_actions` 버튼(또는 후보 테이블 내부 “선택” 버튼)으로 CI를 확정하거나 depth를 확장/뷰를 전환한다. UI는 `trace.plan_validated`를 재사용하므로 새 LLM plan을 생성하지 않는다.
4. Trace 패널에서 `policy_decisions.allowed_rel_types`, `graph.depth` clamp, `/ops/ask`로 보낼 `rerun.base_plan` payload를 확인한다.
5. 필요하면 아래 예시처럼 rerun curl을 호출해 동일한 trace + policy 정보가 반환되는지 확인한다.

#### Next-action 계약
- `NextAction` 타입:
  - `{ type: "rerun", label, payload: { selected_ci_id?: string, selected_secondary_ci_id?: string, patch?: { view?, graph?, aggregate?, output? } } }`
  - `{ type: "open_trace", label }` (trace 패널 열기)
  - `{ type: "copy_payload", label, payload }` (rerun payload 복사)
- rerun 요청 payload 형태:
  ```bash
  curl -s -X POST http://localhost:8000/ops/ask \
    -H "Content-Type: application/json" \
    -d '{ 
      "question": "시스템 뭐야",
      "rerun": {
        "base_plan": { ...trace.plan_validated... },
        "selected_ci_id": "sys-erp",
        "patch": { "graph": { "depth": 3 } }
      }
    }'
  ```
  서버는 `apps.api.app.modules.ops.services.ci.planner.validator`를 통해 patched plan을 재검증한 뒤 orchestrator를 실행한다.

### OPS 그래프 시각화

#### 소스 맵
- Frontend Component: `apps/web/src/components/data/Neo4jGraphFlow.tsx` (Use reusable component)
- Logic/Renderer: `apps/web/src/components/answer/BlockRenderer.tsx` (`GraphFlowRenderer`)

#### 개요
- Data Explorer의 Neo4j 탭에서 사용되는 `ReactFlow` 기반의 그래프 시각화 엔진을 OPS CI 응답에도 동일하게 적용했습니다.
- **주요 기능**:
  - **인터랙티브 조작**: 노드 드래그, 줌, 패닝 지원.
  - **하이라이트**: 노드 클릭 시 해당 노드와 연결된 엣지를 강조 표시(Highlight)하여 복잡한 그래프에서도 관계를 명확히 파악 가능.
  - **일관된 UX**: DATA 메뉴와 OPS 메뉴에서 동일한 그래프 조작 경험 제공.

### 메트릭 조회

#### 소스 맵
- 메트릭 도구: `apps/api/app/modules/ops/services/ci/tools/metric.py`
- 플랜/실행: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- DB 테이블: `metric_def`, `metric_value`


#### 개요
- CI 탭은 확정된 CI에 대해 메트릭 특화 질문을 처리한다. planner는 CPU/memory/latency/count/추이 등의 키워드를 감지해 plan에 `metric` 스펙을 붙이고, orchestrator는 렌더링 전에 `apps.api.app.modules.ops.services.ci.tools.metric`을 실행한다.
- 지원 time range는 `last_1h`, `last_24h`, `last_7d`로 고정되며, aggregate는 `count`, `max`, `min`, `avg`로 제한된다. “trend/시계열/추이” 키워드가 있으면 mode는 `series`, 기본은 `aggregate`다.
- 잘못된 메트릭 이름은 후보 테이블(available metrics)로 fallback되며, trace에 missing metric이 기록되어 유효한 이름으로 rerun할 수 있다.

#### 실행
1. `metric_def`/`metric_value`가 존재하도록 metric discovery(Step 1)를 수행한다.
2. `/ops/ask`(CI 탭)로 메트릭 질문을 보낸다. 응답에는 기존 CI 상세 + aggregate/series 결과를 요약한 metric 테이블이 포함된다.
3. 메트릭 테이블 하단의 “최근 1시간/24시간/7일” next-action 버튼으로 동일 메트릭을 다른 윈도우로 rerun한다.

#### 샘플 질문
1. “sys-erp 지난 24시간 CPU 최대”
2. “srv-erp-01 최근 1시간 메모리 평균”
3. “sys-apm 최근 7일 error count”
4. “sys-erp 응답시간 추이 최근 24시간”
5. “sys-erp metric cpu_usage max last_24h”
6. “sys-erp 지표 목록”

### 이벤트 로그 히스토리
#### 소스 맵
- 히스토리 도구: `apps/api/app/modules/ops/services/ci/tools/history.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- DB 테이블: `event_log`


#### 개요
- “이벤트/알람/로그/event” 키워드가 포함된 질문은 `plan.history.enabled = true`를 켠다. orchestrator는 `apps.api.app.modules.ops.services.ci.tools.history.event_log_recent`를 호출하며, 이 함수는 `event_log`의 CI 참조 및 타임스탬프 컬럼을 자동 탐지해 스키마와 무관하게 안전한 쿼리를 보장한다.
- 고정 윈도우는 `last_24h`, `last_7d`, `last_30d`이며 row limit는 200이다. 테이블 블록 제목은 `Recent events (last_<window>)`로 표시되고 trace에는 요청 window가 기록된다.
- CI를 명시하지 않은 “작업 이력”, “유지보수” 질문은 `apps.api.app.modules.ops.services.ci.tools.history.recent_work_and_maintenance` fallback을 사용하여 maintenance/work 테이블을 각기 분리 조회한다. runner는 텍스트 키워드(`작업`, `deployment`, `maintenance`, `점검` 등)를 통해 필요한 섹션만 포함시키며, 각 테이블에는 `ci_code`/`ci_name`을 보여줘 어느 CI의 기록인지 명확히 한다.
- `apps.api.app/modules/ops/services/resolvers/time_range_resolver.resolve_time_range`는 기존 강제 윈도우 외에 “n개월”, “n년”, “YYYY년 MM월 첫주/둘째 주” 같은 표현도 인식하므로, “최근 6개월” 또는 “2025년 12월 첫주”처럼 구체적인 시간 범위를 요청해도 runner가 정확한 start/end를 계산해 event/work/maintenance 쿼리에 전달한다.
- `event_log` 또는 필수 컬럼이 없더라도 CI 블록은 유지되며, 텍스트 경고 + trace warning으로 문제를 알린다.

#### 샘플 질문
1. `sys-erp 최근 이벤트`
2. `srv-erp-01 최근 24시간 알람`
3. `sys-erp 최근 30일 이벤트 100개`
4. `sys-erp 로그 최근 50개`

### 그래프 범위 메트릭 집계

#### 소스 맵
- 그래프/메트릭 도구: `apps/api/app/modules/ops/services/ci/tools/graph.py`, `apps/api/app/modules/ops/services/ci/tools/metric.py`
- 정책/뷰: `apps/api/app/modules/ops/services/ci/policy.py`, `apps/api/app/modules/ops/services/ci/view_registry.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`


#### 개요
- “범위/의존/영향/주변/연관” 키워드를 포함한 질문은 `metric.scope = "graph"`를 활성화하고, `metric_aggregate` 실행 전에 선택된 CI를 `graph.expand`하도록 orchestrator에 요청한다. 이는 관계 depth, 허용 관계 타입, policy trace 데이터를 기반 뷰(DEPENDENCY/NEIGHBORS/IMPACT)와 정렬하여 모든 집계가 뷰별 depth clamp를 준수하게 한다.
- 응답은 단일 `table` 블록(`scope, view, depth, ci_count, metric_name, agg, time_from, time_to, value`)과 time range/agg type/depth bump/view swap을 위한 `next_actions`를 반환한다. trace는 그래프 확장 요약, 집계 결과, policy 결정을 기록하여 LLM 재호출 없이 rerun할 수 있게 한다.
- 이 단계는 그래프 스코프 aggregate 메트릭(`metric.mode = "aggregate"`)만 지원하며, `patch.graph.depth`, `patch.view`, `patch.metric.{time_range,agg}`를 수정하는 rerun 버튼을 노출한다. 차트/시리즈/히스토리는 여기서 수행하지 않는다.

#### 샘플 질문
1. “sys-erp 의존 범위 지난 24시간 CPU max”
2. “sys-erp 주변 CI 최근 7일 error count”
3. “sys-apm 영향 범위 last_1h rps avg”
4. “sys-mon 의존 범위 last_24h latency max”
5. “sys-erp 의존 범위 metric cpu_usage max last_24h”
6. “sys-erp 주변 범위 error count last_7d”

### 그래프 범위 히스토리

#### 소스 맵
- 그래프/히스토리 도구: `apps/api/app/modules/ops/services/ci/tools/graph.py`, `apps/api/app/modules/ops/services/ci/tools/history.py`
- 정책/뷰: `apps/api/app/modules/ops/services/ci/policy.py`, `apps/api/app/modules/ops/services/ci/view_registry.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`


#### 개요
- “이벤트/로그/알람/event”와 그래프 키워드를 모두 포함한 질문은 `history.scope = "graph"`를 활성화한다. runner는 뷰 정책에 따라 CI를 확장(DEPENDENCY/NEIGHBORS/IMPACT)하고, 확장된 CI 리스트를 `event_log_recent`에 전달해 모든 행이 동일한 relation allowlist, 테넌트 스코프, depth clamp를 준수하도록 한다.
- 응답은 `Recent events (graph scope, <VIEW>, depth=<DEPTH>, <window>)` 제목의 단일 `table` 블록을 반환하며, `trace.history.graph`는 확장 요약을 기록한다. `next_actions`는 `time_range`, `depth`, view swap rerun을 제공하며 이 과정에서 새 planner 호출은 없다.
- 이 단계는 `event_log.recent`만 지원한다. maintenance/work history, `count_by_type`, 차트는 범위 밖이다.

#### 샘플 질문
1. “sys-erp 의존 범위 최근 7일 이벤트”
2. “sys-erp 주변 범위 최근 24시간 알람 100개”
3. “sys-apm 영향 범위 last_30d 이벤트”
4. “sys-erp 의존 범위 로그 최근 50개”
5. “sys-mon 주변 범위 최근 7일 이벤트”
6. “sys-erp 의존 범위 이벤트 depth 3”

### 메트릭 시리즈 차트

#### 소스 맵
- 메트릭 시리즈: `apps/api/app/modules/ops/services/ci/tools/metric.py`
- 블록 렌더링: `apps/web/src/components/answer/BlockRenderer.tsx`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`


#### 개요
- CI 스코프 메트릭 시리즈 쿼리가 최소 2포인트를 만들면 `chart` 블록이 생성된다. runner는 기존 `table` 블록도 반환하므로, 단순 `<svg>` 차트 렌더링이 불가능해도 UI는 테이블로 fallback 할 수 있다.
- 차트 블록은 `chart` 타입에 단일 `line` 시리즈와 CI/metric/time range 메타를 포함한다. 그래프 스코프 쿼리, 집계 결과, 시리즈 데이터 누락은 차트 생성을 피한다.
- 사용자는 기존 “최근 1시간 / 24시간 / 7일” next actions로 시간 윈도우를 전환할 수 있고(planner 재호출 없음), 차트 블록은 항상 첫 요소로 유지되어 테이블이 뒤따르게 된다.

#### 샘플 질문
1. “sys-erp 최근 24시간 CPU 추이”
2. “srv-erp-01 최근 7일 latency 시계열”
3. “sys-apm rps 추이 지난 24시간”
4. “sys-erp metric cpu_usage series last_24h”

### CEP 시뮬레이션 참고

#### 소스 맵
- CEP 도구: `apps/api/app/modules/ops/services/ci/tools/cep.py`
- CEP 실행/로그: `apps/api/app/modules/cep_builder/executor.py`, `apps/api/app/modules/cep_builder/crud.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`


#### 개요
- 시뮬레이션 키워드(`simulate`, `시뮬`, `rule`, `cep`)와 rule UUID가 함께 언급되면 CI 응답에 CEP simulate 데이터가 붙는다. planner가 CEP 스펙을 추가하고, orchestrator가 CEP simulate helper를 호출하며, 요약 테이블 + 텍스트 블록이 추가된다. 기존 CI/graph/metric/history 블록은 유지된다.
- CEP simulate는 여전히 dry-run(`mode=simulate`, `dry_run=true`)이며 유효한 rule_id가 필요하다. 오류가 있어도 “CEP simulate failed: …” 같은 텍스트 블록과 trace 메타데이터(`cep_requested`, `rule_id_parsed`, `cep_error`)를 반환한다.
- simulate 테이블에는 `rule_id`, 조건 평가 여부, triggered 플래그, operator/threshold, extracted value가 포함되며 텍스트 블록은 evaluated/triggered 상태를 강조한다.

#### 샘플 질문
1. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate”
2. “sys-erp 최근 24시간 CPU max + rule 123e4567-e89b-12d3-a456-426614174000 simulate”
3. “srv-erp-01 시뮬레이션 rule 123e4567-e89b-12d3-a456-426614174000”
4. “sys-erp simulate”

### CEP 테스트 페이로드 생성

#### 소스 맵
- 페이로드 생성: `apps/api/app/modules/ops/services/ci/tools/cep.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`


#### 개요
- CEP simulate helper는 `test_payload`가 없을 때 필터링된 CI 식별자, 최신 metric summary, 최신 history snippet을 결합해 자동 생성한다. 이 방식은 payload를 작게(~16KB) 유지하고 위험한 긴 텍스트/허용되지 않은 tag/attribute를 피한다.
- payload 메타데이터(`trace.cep.test_payload_built`, `test_payload_size_bytes`, `test_payload_sources`, `payload_truncated`)는 포함된 입력을 보여주며, metrics/history가 없으면 CI-only payload로 자연스럽게 fallback한다.
- payload 생성은 CEP trigger가 사람이 지정한 runtime 데이터 없이도 value path를 평가할 확률을 높이면서, dry-run-only 제한을 유지한다.

#### 샘플 질문
1. “sys-erp rule <uuid> simulate”
2. “sys-erp 최근 24시간 CPU max rule <uuid> simulate”
3. “sys-erp 최근 7일 이벤트 rule <uuid> simulate”
4. “sys-erp rule <uuid> simulate” (no prior metrics/history)

### CEP 런타임 Fetch 증거

#### 소스 맵
- 증거/마스킹: `apps/api/app/modules/ops/services/ci/tools/cep.py`
- CEP 평가: `apps/api/app/modules/cep_builder/executor.py`
- 블록 빌더: `apps/api/app/modules/ops/services/ci/response_builder.py`


#### 개요
- 시뮬레이션이 runtime fetch 데이터에 의존할 때, fetch 증거(endpoint, method, params, value_path, op, threshold, extracted_value, condition)를 정규화해 응답 테이블과 trace(`trace.cep.evidence`, `trace.cep.params_masked`, `trace.cep.extracted_value_truncated`)에 함께 포함한다.
- token/password/key가 포함된 params는 자동으로 마스킹(`***`)되며, 추출된 JSON blob은 200자로 truncate 후 표시된다.
- 증거는 새로운 “CEP simulate evidence” 테이블로 노출되며 simulate 실패 시에도 확인 가능하다.

#### 샘플 질문
1. “sys-erp rule <uuid> simulate” (runtime fetch rule)
2. “sys-erp cpu max + rule <uuid> simulate”
3. “sys-erp 최근 7일 이벤트 rule <uuid> simulate”
4. “sys-erp rule <uuid> simulate” (ensure evidence table still shows CI context)

### CEP 런타임 파라미터 정책

#### 소스 맵
- 정책 파일: `apps/api/app/modules/ops/services/ci/cep/param_mapping.yaml`
- 정책 적용: `apps/api/app/modules/ops/services/ci/tools/cep.py`


#### 개요
- runtime fetch params는 `ops/ci/cep/param_mapping.yaml`로 구동되며, simulate가 주입할 수 있는 CI 유래 키, 차단된 secret, size limit을 노출한다.
- CEP helper는 이 정책을 로드하고(YAML이 없거나 잘못되면 이전 하드코딩 allowlist로 fallback), 모든 simulate 실행에 `runtime_params_meta`, `runtime_params_keys`, `runtime_params_policy_source`를 주석으로 남긴다.
- evidence 테이블은 `params_keys` 컬럼을 포함해 runtime fetch에 전달된 필드를 확인할 수 있으며, trace는 정책 소스와 마스킹/크기 메타를 보관한다.

#### 샘플 질문
1. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate”
2. “sys-erp cpu max + rule 123e4567-e89b-12d3-a456-426614174000 simulate”
3. “sys-erp 최근 7일 이벤트 rule 123e4567-e89b-12d3-a456-426614174000 simulate”
4. “시뮬 rule 123e4567-e89b-12d3-a456-426614174000” (param table should show allowed keys)
5. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate” (repeat with modified `param_mapping.yaml` to drop `location`)
6. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate” (rule returns blocked `token` - ensure it disappears)

### CEP 페이로드 요약

#### 소스 맵
- 페이로드 요약/트렁케이션: `apps/api/app/modules/ops/services/ci/tools/cep.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`


#### 개요
- 자동 생성된 `test_payload`는 metric/history 요약을 정규화하여 모든 simulate 실행에 표준 경로(`metric.metric_name`, `metric.time_range`, `metric.agg`, `metric.value`, `history.source`, `history.time_range`, `history.count`, `history.recent[*].ts`, `history.recent[*].summary`)를 포함한다. 값이 없더라도 키는 유지되어 CEP 규칙이 안정적으로 참조할 수 있다.
- payload 크기는 여전히 16KB로 제한된다. shrinker는 먼저 history 행(최대 3 → 1)과 메타를 줄이고, 그 다음 metric/history 데이터를 숨긴 뒤(키는 유지) 필요 시 전체 섹션을 제거한다. 이때 `trace.cep.payload_truncated`가 표시되며 trace는 남은 섹션(`test_payload_sections`)과 metric/history 키 존재 여부를 기록한다.
- history snippet은 섹션당 최대 3개를 유지하고, 각 summary는 120자로 truncate해 과도한 payload를 방지하면서 CEP value path 컨텍스트를 유지한다.

#### 샘플 질문
1. “sys-erp 최근 24시간 cpu max + rule 123e4567-e89b-12d3-a456-426614174000 simulate”
2. “sys-erp 최근 7일 이벤트 + rule 123e4567-e89b-12d3-a456-426614174000 simulate”
3. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate” (confirm history keys exist even if there is no recent data)

### CEP 이벤트 브라우저 링크

#### 소스 맵
- next_action 생성: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- 액션 계약: `apps/api/app/modules/ops/services/ci/actions.py`
- Frontend 이동: `apps/web/src/app/ops/nextActions.ts`, `apps/web/src/app/ops/page.tsx`
- 대상 화면: `apps/web/src/app/cep-events/page.tsx`


#### 개요
- 모든 CEP simulate는 이제 백엔드가 `tb_cep_exec_log`에 저장한 `exec_log_id`(항상 `simulation_id` 포함)를 반환한다. orchestrator는 이 ID를 `trace.cep.exec_log_id`/`trace.cep.simulation_id`로 복사하고, “Event Browser로 보기”라는 non-rerun next action을 추가해 운영자가 CEP Event Browser로 바로 이동할 수 있게 한다.
- 요약 테이블은 `exec_log_id`(또는 exec log를 찾지 못한 경우 `simulation_id`)를 표시해 실행 ID를 인라인으로 노출하며, next action은 `/cep-events?exec_log_id=...`(또는 `simulation_id`)로 ID를 전달해 동일 실행을 포커스한다.
- trace 및 블록 메타데이터는 기존 CEP 상세를 유지하며, 이는 기존 dry-run 흐름을 변경하지 않는 링크 레이어다.

#### 샘플 질문
1. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate”
2. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate”
3. “sys-erp 최근 24시간 CPU max + rule 123e4567-e89b-12d3-a456-426614174000 simulate”
4. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate” (when exec_log_id is generated but may not yet be associated with an event)

### 이벤트 브라우저 실행 조회

#### 소스 맵
- Backend API: `apps/api/app/modules/cep_builder/router.py` (`/cep/events/run`)
- Frontend: `apps/web/src/app/cep-events/page.tsx`


#### 개요
- CEP Event Browser는 query string의 `exec_log_id` 또는 `simulation_id`를 받아 `GET /cep/events/run`을 호출해 매칭되는 exec log를 조회한다(simulation ID fallback 포함). 응답에는 실행 식별자, 타이밍, condition/extracted value,정규화된 evidence가 포함되어 CI 탭 블록과 동일한 정보를 보여준다.
- exec log가 존재하면 Event Browser는 요약 카드 + 표준 evidence 테이블(`endpoint`, `method`, `value_path` 등)과 큰 JSON을 truncate하는 접이식 raw references snippet을 표시한다.
- 레코드가 없거나 ID가 없으면 UI는 “not found” 메시지로 대체하되 테넌트/exec/simulation ID를 표시하고 소스 쿼리 확인을 유도한다.

### AUTO 모드 레시피

#### 소스 맵
- Auto 플랜: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`
- 오케스트레이터: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- Frontend: `apps/web/src/app/ops/page.tsx`, `apps/web/src/components/answer/BlockRenderer.tsx`


#### 개요
- “상태 점검”, “요약”, “진단”, “health”, “overview” 요청은 plan을 `mode=auto`로 전환한다. runner는 고정 레시피를 따라 CI를 해석하고 표준 상세 블록을 출력한 뒤, `NEIGHBORS` depth=1 확장, cpu_usage/latency/error 집계, 최근 7일 이벤트 로그(limit 20) 조회를 수행하며, 필요 시 CEP simulate 결과(rule UUID 제공 시)를 포함한다. 템플릿 텍스트 블록이 성공 섹션을 요약해 정규 블록 전에 “AUTO 점검 결과”를 제공한다.
- Auto mode는 `trace.auto.auto_recipe_applied`를 기록하고 시도한 메트릭을 남기며 graph/history/CEP 단계 성공 여부를 표시한다. 도구 실패가 있어도 CI detail은 유지되고 실패는 텍스트 블록으로 노출된다.

#### 샘플 질문
1. “sys-erp 상태 점검해줘”
2. “srv-erp-01 요약”
3. “sys-mon health check”
4. “sys-erp 진단 rule 123e4567-e89b-12d3-a456-426614174000 simulate” (auto + CEP)

### AUTO 동적 선택

#### 소스 맵
- Auto 의도 판단: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`
- 실행/정책: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`, `apps/api/app/modules/ops/services/ci/policy.py`
- Frontend: `apps/web/src/app/ops/page.tsx`


#### 개요
- `mode=auto`는 이제 고정 레시피 대신 경량 결정 트리를 따른다. planner는 키워드 조합으로 원하는 뷰(COMPOSITION/DEPENDENCY/IMPACT/NEIGHBORS/PATH)를 추론하고, depth 힌트(1‑3)를 정책 모듈로 clamp하며, 질문에 `cpu`/`latency`/`error`/`이벤트`/`로그`/`simulate` 등이 명시될 때만 metrics/history/CEP를 활성화한다. 요약 블록은 항상 첫 블록으로 포함되며, runner는 요청된 그래프 뷰를 순회하고 trace에 실제 실행 섹션(`trace.auto.views`, `trace.auto.metrics`, `trace.auto.history`, `trace.auto.cep`)을 기록한다.
- 메트릭 키워드는 일반 metric 스펙 흐름을 트리거한다. 명시적 메트릭이 없더라도 metrics가 활성화되어 있으면 cpu_usage/latency/error 후보로 fallback한다. 시리즈 힌트(`추이`, `그래프`)는 planner가 `mode=series`를 요청하도록 한다(CI 스코프에만 적용). History/CEP는 게이트되어 history는 CI 스코프 이벤트 로그만, CEP는 rule_id가 있을 때만 실행한다.
- “깊게 3단계” 같은 depth 힌트는 확장을 조정하되 `apps.api.app/modules/ops/services/ci/policy.clamp_depth`로 clamp된다. runner는 각 그래프 뷰를 확장하고 depth bump/view swap/metric time_range 토글 등 next actions를 시드하며, 요약 텍스트는 성공/실패 섹션을 나열한다.

#### 샘플 질문
1. “sys-erp 의존 관계 알려줘”
2. “sys-erp 구성 요소 보여줘”
3. “sys-erp 최근 24시간 cpu 추이”
4. “sys-erp 최근 7일 이벤트”
5. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate” (auto + CEP)
6. “sys-erp 와 sys-apm 어떻게 연결돼?”

### AUTO PATH 완성 & 그래프 스코프 혼합

#### 소스 맵
- PATH/그래프 도구: `apps/api/app/modules/ops/services/ci/tools/graph.py`
- Auto 실행: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- Frontend: `apps/web/src/app/ops/page.tsx`, `apps/web/src/components/answer/BlockRenderer.tsx`


#### 개요
- AUTO 모드는 이제 PATH 요청을 완성한다. 두 CI 코드가 있으면 runner가 양쪽 엔드포인트를 해석하고 `graph_path` 헬퍼를 실행해 최단 경로 블록을 반환한다. 대상이 없으면 “대상 선택” 후보 테이블 + rerun 버튼을 제공해 planner 재호출 없이 대상 선택이 가능하다.
- dependency/impact 질문이 성능 또는 이벤트 키워드를 포함하면 runner는 동일 그래프 뷰를 자동 확장하고, 확장된 CI ID를 capturing(300 ID cap 준수)한 뒤 그래프 스코프 메트릭 집계 + 이벤트 히스토리 테이블을 실행한다. trace는 사용된 CI 수/트렁케이션을 기록하고, “Graph-scope …” 블록은 메트릭/히스토리 데이터가 확장된 dependency 세트를 커버함을 명시한다.

#### 샘플 질문
1. “sys-erp 와 sys-apm 어떻게 연결돼?”
2. “sys-erp 경로 알려줘”
3. “sys-erp 의존 범위 성능도 같이 보여줘”
4. “sys-erp 영향 범위 최근 이벤트도 같이”
5. “sys-erp 영향 범위 성능+이벤트 같이”
6. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate”

### AUTO 인사이트 & 추천 액션

#### 소스 맵
- 인사이트/추천 생성: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- 액션 계약: `apps/api/app/modules/ops/services/ci/actions.py`
- Frontend: `apps/web/src/app/ops/nextActions.ts`, `apps/web/src/components/answer/BlockRenderer.tsx`


#### 개요
- AUTO 응답은 최상단에 “AUTO Insights” 카드를 추가한다. 이는 새 쿼리 없이 기존 block/trace 데이터를 재사용해 CI code/type/status, 주요 그래프 뷰, node/depth 카운트, 이벤트, 메트릭 하이라이트, CEP 결과를 간결히 요약한다. 텍스트 블록 + 숫자 타일 형태로 구성해 운영자가 downstream 블록을 이끄는 헬스 메트릭을 즉시 확인할 수 있다.
- 이어서 추천 액션(최대 5개)을 휴리스틱으로 생성한다. truncation 감지는 depth/view 전환을 제안하고, 누락된 metrics/history는 time-range/limit 조정을 제안한다. PATH 후보는 액션 리스트 상단에 유지되며, CEP 실행은 Event Browser 링크를 상단에 올리고, rule 없이 simulate 힌트가 있으면 복사 가능한 샘플을 제안한다. 추천은 기존 rerun 계약을 존중하며 `trace.auto.recommendations`에 기록된다.

#### 샘플 질문
1. “sys-erp 상태 점검해줘”
2. “sys-erp 의존 범위 성능+이벤트 같이”
3. “sys-erp 와 sys-apm 어떻게 연결돼?”
4. “sys-erp rule 123e4567-e89b-12d3-a456-426614174000 simulate”

### CI 목록 미리보기

#### 소스 맵
- 리스트 도구: `apps/api/app/modules/ops/services/ci/tools/ci.py`, `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- 플랜/검증: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/planner/validator.py`
- Frontend: `apps/web/src/components/answer/BlockRenderer.tsx`


#### 개요
- 사용자가 “목록”, “리스트”, “list” 등 목록 키워드를 명시하면 planner는 `plan.list.enabled=true`(최대 50행)를 설정한다. validator는 요청된 limit을 50으로 clamp하고 요청/적용 값을 `trace.list`에 기록한다. 키워드는 aggregate/count 요청과 함께 올 수 있으므로 `Intent.AGGREGATE` plan에서도 목록 미리보기가 추가된다.
- 새로운 `ci_list_preview` 도구는 테넌트 스코프를 준수하며 aggregate에 사용될 동일 필터를 적용하고, `created_at` 내림차순으로 정렬한다. runner는 “CI 목록 (미리보기)” 테이블을 반환하고 limit/offset/total 메타데이터를 태깅하며, “총 N개 중 50개 표시” 같은 짧은 텍스트 블록을 이어서 출력한다.
- 집계 결과는 변경되지 않는다. AGGREGATE plan에서는 집계 테이블 뒤에 목록 미리보기가 붙어 “목록 50개 + 전체 CI 갯수”를 동시에 반환한다.

#### 샘플 질문
1. “전체 CI 목록 50개 보여줘, 그리고 전체 CI 갯수는?”
2. “CI 목록 보여줘”
3. “SYSTEM CI 목록 20개”
