# Tobit SPA AI - 운영

## 1. 문서 개요

이 문서는 원래 README에 있던 스모크 테스트와 수동 검증 체크리스트를 모았습니다.

### 문서 읽는 법
- 각 섹션에 `소스 맵`과 `검증 절차`를 함께 정리했습니다.
- 경로는 프로젝트 루트 기준이며, 기능 수정·테스트 시 해당 섹션부터 확인합니다.
- OPS/CI Step/Hotfix는 실제 파이프라인 단계에 맞춰 소스와 연결했습니다.

## 2. UI/화면 기준 검증 맵

- API Manager UI (`/api-manager`, `/api-manager/chat`)
  - Builder 공통 Copilot 스모크 테스트
  - System APIs (flagged)
- UI Creator UI (`/ui-creator`, `/ui-creator/chat`)
  - Builder 공통 Copilot 스모크 테스트
- Data Explorer UI (`/data`)
  - Postgres/Neo4j/Redis 탭 로딩 확인
  - Read-only 정책/allowlist 동작 확인
- CEP Builder UI (`/cep-builder`, `/cep-builder/chat`)
  - Builder 공통 Copilot 스모크 테스트
  - CEP Scheduler 관측
- CEP Event Browser UI (`/cep-events`)
  - CEP Event Browser (End-to-End 관측)
- OPS/CI UI (`/ops`)
  - CI 디스커버리 & 정책
  - /ops/ci/ask & CI 도구
  - 모호성 해소 & 재실행
  - 메트릭/히스토리/그래프 범위/시리즈
  - CEP 시뮬레이션/페이로드/증거/정책/링크
  - AUTO 모드 + CI 목록 미리보기

## 3. Builder 공통

### Copilot 스모크 테스트 (Builder 공통)

#### 소스 맵
- Frontend: `apps/web/src/app/api-manager/page.tsx`, `apps/web/src/app/ui-creator/page.tsx`, `apps/web/src/app/cep-builder/page.tsx`
- Copilot UI: `apps/web/src/components/chat/BuilderCopilotPanel.tsx`, `apps/web/src/components/chat/ChatExperience.tsx`
- 공통 레이아웃: `apps/web/src/components/builder/BuilderShell.tsx`
- Backend API: `apps/api/app/modules/api_manager/router.py`, `apps/api/app/modules/ui_creator/router.py`, `apps/api/app/modules/cep_builder/router.py`

#### 검증 절차

1) 각 Builder 우측 Copilot에 요청 입력
   - API Manager: “설비 구성 목록 조회 API 만들어줘. endpoint는 /api-manager/config-inventory”
   - UI Creator: “설비 요약 대시보드 UI 만들어줘”
   - CEP Builder: “cpu_usage 80% 넘으면 알람 룰 만들어줘”
2) Debug(개발 모드)에서 parse status와 draft JSON 확인
3) Preview → Test → Apply 순서로 동작 확인
4) Save 눌러 server/local 저장 메시지 확인
5) 새로고침 후 저장된 항목 복원 여부 확인

### UI 표준 검증 (타임존/스크롤바)

#### 검증 절차
1) **타임존**:
   - OPS 이력, CEP 이벤트 상세, Documents 목록 등 날짜가 표시되는 곳을 확인합니다.
   - 표시된 시간이 **한국 시간 (KST, UTC+9)**에 맞는지 확인합니다. (예: DB에 09:00Z로 저장된 데이터가 화면에 18:00로 표시되어야 함)
2) **스크롤바**:
   - OPS Query History, Grid, JSON Viewer 등 스크롤이 생기는 영역을 확인합니다.
   - OS 기본 스크롤바가 아닌, **얇고 어두운 테마의 Custom Scrollbar**가 적용되었는지 확인합니다.

## 4. API Manager

### API Manager Dev: 시스템 API (flagged)

#### 소스 맵
- Backend: `apps/api/app/modules/api_manager/router.py` (system endpoints)
- 설정: `apps/api/core/config.py` (`enable_system_apis`), `apps/api/.env` (`ENABLE_SYSTEM_APIS`)
- Frontend: `apps/web/src/app/api-manager/page.tsx`
- Frontend 플래그: `apps/web/.env.local` (`NEXT_PUBLIC_ENABLE_SYSTEM_APIS`)

#### 검증 절차

1) API Manager의 `system` 탭을 클릭하고 `/data/postgres/query`를 로드한다.
2) 상세 카드에 OpenAPI 요약과 “Supported actions / constraints” 블록이 표시되고, read-only 정책/강제 LIMIT/timeout/allowlist가 포함됐는지 확인한다.
3) `/data/redis/command`를 열어 설명에 안전한 명령과 금지 작업이 언급되는지 확인한다.

### API Manager: HTTP logic type

#### 소스 맵
- Backend: `apps/api/app/modules/api_manager/router.py` (`/api-manager/apis/*/execute`, `/runtime/*`) + `apps/api/app/modules/api_manager/executor.py` (`execute_http_api`)
- Schema/validation: `apps/api/app/modules/api_manager/schemas.py` (`LogicType`, `ApiDefinition*`)
- Frontend: `apps/web/src/app/api-manager/page.tsx` (Builder logic-type selector + HTTP spec editor), `apps/web/src/components/builder/BuilderShell.tsx`

#### 검증 절차
1) Builder에서 새 API를 만들 때 `logic_type`을 `http`로 선택하고 `logic_body`에 JSON로 `{ "url": "https://httpbin.org/get", "method": "GET", "params": { "foo": "bar" } }`처럼 외부 HTTP 스펙을 저장한다. 저장 후 `/api-manager/apis`와 `/runtime/{endpoint}`에서 `http` 정의가 목록 및 `logic_spec` JSON에 존재하는지 확인한다.
2) 동일 API에 대해 `/api-manager/apis/{api_id}/dry-run` 또는 `/api-manager/apis/{api_id}/execute`를 호출하여 `ResponseEnvelope.success.data.result.executed_sql`에 `HTTP GET https://httpbin.org/get` 형식이 나오고 `rows`에 JSON 혹은 텍스트 응답이 들어오는지, `row_count`가 1개 이상인지 확인한다.
3) API 실행 로그(`tb_api_exec_log`, `apps/api/logs/api.log`)에 `External HTTP request failed` 오류 없이 `status=success`가 기록되고, `params`에 Builder에서 입력한 파라미터가 그대로 남는지 확인한다.

## 5. CEP

### CEP Event Browser (End-to-End 관측)

#### 소스 맵
- Backend API: `apps/api/app/modules/cep_builder/router.py` (`/cep/events*`, `/cep/events/stream`)
- 이벤트 처리: `apps/api/app/modules/cep_builder/crud.py`, `apps/api/app/modules/cep_builder/event_broadcaster.py`
- Frontend: `apps/web/src/app/cep-events/page.tsx`, `apps/web/src/components/CepEventBell.tsx`
- 마이그레이션: `apps/api/alembic/versions/0019_add_cep_event_ack_fields.py`

#### 검증 절차

1) 알림 로그가 생성되도록 metric rule + notification 실행
2) `/cep/events`에서 이벤트 목록 확인
3) 상세에서 ACK → 미ACK 필터에서 제거 확인
4) SSE로 헤더 뱃지 카운트 감소 확인

### CEP Scheduler 관측

#### 소스 맵
- 스케줄러: `apps/api/app/modules/cep_builder/scheduler.py`
- 상태 API: `apps/api/app/modules/cep_builder/router.py` (`/cep/scheduler/*`)
- 설정: `apps/api/core/config.py` (`ops_enable_cep_scheduler`, `cep_*`)
- 로그: `apps/api/logs/api.log`

#### 검증 절차

1) `OPS_ENABLE_CEP_SCHEDULER=false`로 앱을 시작 → `[CEP] Scheduler disabled by environment variable` 로그만 확인, heartbeat/metric polling/notification 로그 없음.
2) `OPS_ENABLE_CEP_SCHEDULER=true`로 앱을 시작 → `[CEP] Scheduler enabled (OPS_ENABLE_CEP_SCHEDULER=true)` 로그가 나오고 기존 동작(leader 정리, metric polling, notification loop)이 그대로 작동합니다.

## 6. OPS/CI

### CI 디스커버리 & 정책

#### 소스 맵
- Discovery: `apps/api/app/modules/ops/services/ci/discovery/postgres_catalog.py`, `apps/api/app/modules/ops/services/ci/discovery/neo4j_catalog.py`
- 정책/뷰: `apps/api/app/modules/ops/services/ci/policy.py`, `apps/api/app/modules/ops/services/ci/view_registry.py`, `apps/api/app/modules/ops/services/ci/relation_mapping.yaml`
- 산출물: `apps/api/app/modules/ops/services/ci/catalog/*.json`

#### 검증 절차

- `python -m apps.api.app.modules.ops.services.ci.discovery.postgres_catalog` / 기대: `apps/api/app/modules/ops/services/ci/catalog/postgres_catalog.json` 생성, 스키마/`stats.ci_counts.total` 채워짐, `stats.ci_counts.breakdowns.ci_type` 비어있지 않음, `jsonb_catalog.tags_keys`와 `attributes_keys` 포함 (`host_server`, `runs_on`, `connected_servers` 등 확인) / 실패 가능성: Postgres 환경변수 누락, `ci`/`ci_ext` 테이블 없음, JSONB 컬럼 누락, 권한 오류.
- `python -m apps.api.app.modules.ops.services.ci.discovery.neo4j_catalog` / 기대: `apps/api/app/modules/ops/services/ci/catalog/neo4j_catalog.json` 생성, `relationship_types`에 시드 관계가 나열되고 `relationship_type_counts`에 관계별 카운트가 있음, `labels` 존재, `ci_node_properties`에 `ci_id`, `ci_code`, `tenant_id` 포함(경고는 누락을 표시) / 실패 가능성: Neo4j 환경변수 누락, DB 접근 불가, 프로시저 비활성화(`db.relationshipTypes`, `db.labels`, `db.schema.nodeTypeProperties`), 권한 부족.
- `python -m apps.api.app.modules.ops.services.ci.policy` / 기대: `relation_mapping.yaml` 로드, view helpers import, `policy.get_allowed_rel_types("SUMMARY")`/`clamp_depth("PATH", 4)`가 정상 반환, `apps/api/app/modules/ops/services/ci/catalog/combined_catalog.json`이 `meta.discovered_rel_types`로 갱신 / 실패 가능성: YAML 문법 오류, catalog JSON 누락, 쓰기 권한 오류.
- `python -c "from apps.api.app.modules.ops.services.ci.view_registry import VIEW_REGISTRY; print(sorted(VIEW_REGISTRY))"` / 기대: 6개 뷰(SUMMARY, COMPOSITION, DEPENDENCY, IMPACT, PATH, NEIGHBORS)가 설정값과 함께 정의됨 / 실패 가능성: `view_registry.py` 누락, import 오류, dataclass 오류.
- `python -c "from apps.api.app.modules.ops.services.ci.policy import get_allowed_rel_types, clamp_depth; print(get_allowed_rel_types('DEPENDENCY'), clamp_depth('DEPENDENCY', 2))"` / 기대: dependency 뷰가 매핑된 관계만 허용하고 최대 depth로 clamp / 실패 가능성: 매핑 조회 실패, view registry 불일치, 예기치 않은 relation 노출.

### CI 도구 & /ops/ci/ask

#### 소스 맵
- API 라우터: `apps/api/app/modules/ops/router.py`
- 도구/플래너/오케스트레이터: `apps/api/app/modules/ops/services/ci/tools/*.py`, `apps/api/app/modules/ops/services/ci/planner/*`, `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- 블록/응답: `apps/api/app/modules/ops/services/ci/blocks.py`, `apps/api/app/modules/ops/services/ci/response_builder.py`
- Frontend: `apps/web/src/app/ops/page.tsx`, `apps/web/src/components/answer/BlockRenderer.tsx`

#### 검증 절차

- `curl -s -X POST http://localhost:8000/ops/ci/ask -H "Content-Type: application/json" -d '{"question":"sys-erp 뭐야"}'` / 기대: `answer`, 타입별 `blocks`, `trace.plan_validated`, `meta.used_tools`, `next_actions` 반환 / 실패 가능성: API 오류, blocks 형식 오류, trace 누락.
- “sys-erp 구성 보여줘” / 기대: 구성 네트워크 블록 또는 테이블 대체가 표시되고 `trace.policy_decisions.allowed_rel_types`에 `COMPOSED_OF` 포함 / 실패 가능성: graph 쿼리 실패, policy allowlist 차단.
-- “sys-erp 의존하는 시스템” / 기대: dependency edge와 `trace.policy_decisions.view = DEPENDENCY` / 실패 가능성: 매핑 구버전 또는 Neo4j 관계 누락.
- “srv-erp-01 네트워크 연결” / 기대: `CONNECTED_TO` 엣지/호스트, 제한 도달 시 truncated 플래그 설정 / 실패 가능성: JSONB 태그 누락, 테넌트 불일치.
- “srv-erp-01 사용하는 storage” / 기대: `USES` 관계로 storage 노드 + CI 상세 테이블 / 실패 가능성: storage 노드 미시드 또는 graph 필터 문제.
- “srv-erp-01 protected by 뭐야” / 기대: `PROTECTED_BY` 엣지 데이터 / 실패 가능성: policy에 관계 미포함 또는 CI 노드 누락.
- “was-erp-01 어디서 실행돼” / 기대: `RUNS_ON` 호스트 정보가 text/number 블록으로 요약 / 실패 가능성: `runs_on` 태그 부재 또는 graph 관계 누락.
- “system=erp 서버 목록” / 기대: `tags.system = erp` 필터가 적용된 `ci.search` 테이블 / 실패 가능성: 필터 거부 또는 결과 없음.
- “CI 타입별 카운트” / 기대: 전체 CI 수를 담은 number 블록이 집계 테이블 앞에 표시되고, 테이블에 `count`와 `count_distinct`가 포함되며, `trace.plan.aggregation.total_count`와 `trace.plan.aggregation.group_by`가 기록되고 `trace.tool_calls`에 `ci_aggregate`가 포함됨 / 실패 가능성: group_by/metrics 오류 또는 plan 분류 오류.
- “sys-erp 와 sys-apm 연결 경로” / 기대: hop 정보를 담은 PATH 블록, `trace.policy_decisions.depth`가 clamp 제한 이내, truncation 시 `meta.fallback` / 실패 가능성: 한쪽 엔드포인트 미해결 또는 관계 allowlist 차단.
- 테넌트 격리: `curl -s -X POST http://localhost:8000/ops/ci/ask -H "Content-Type: application/json" -H "X-Tenant-Id: t2" -d '{"question":"sys-erp 뭐야"}'` / 기대: `trace.tenant_id === "t2"`이고 교차 테넌트 데이터 없음 / 실패 가능성: 테넌트 헤더 무시 또는 필터 누락.

### 모호성 해소 & 재실행

#### 소스 맵
- 액션 계약: `apps/api/app/modules/ops/services/ci/actions.py`
- rerun 검증: `apps/api/app/modules/ops/services/ci/planner/validator.py`
- Frontend: `apps/web/src/app/ops/nextActions.ts`, `apps/web/src/components/answer/BlockRenderer.tsx`

#### 검증 절차

- `erp 서버 보여줘` / 기대: 후보 테이블 + `selected_ci_id` 버튼이 있는 `next_actions`, trace에 `ambiguous_roles`/`candidates` 기록, 선택 시 안정적인 상세 블록으로 재조회 / 실패 가능성: 검색 결과 0건, 프론트에서 next actions 부착 실패.
- `sys-erp 의존 관계` / 기대: `truncated`가 표시된 network/path 블록 + `depth +1` 버튼, trace의 `policy_decisions.depth`가 clamp와 일치, 클릭 시 depth가 증가된 rerun(`clamped_depth`, `tool_calls.graph_expand` 확인) / 실패 가능성: repository가 depth patch 차단, Neo4j 관계 누락.
- `sys-erp 뭐야` → `View DEPENDENCY로 보기` / 기대: `next_actions`에 view 변경이 있고, 실행 시 `view=DEPENDENCY`로 rerun되며 trace에 `policy_decisions.view = "DEPENDENCY"` 기록.
- `sys-erp 와 sys-apm 연결 경로` / 기대: 양쪽 엔드포인트가 모두 매칭되면 secondary 후보가 노출되고 `next_actions`에 `selected_secondary_ci_id` 포함, 클릭 시 rerun으로 PATH 블록 생성(trace에 `graph_path`, `clamped_depth` 기록), ReactFlow 미지원 시 테이블 대체 표시.
- `Next-action rerun copy` / 기대: `copy_payload` 버튼으로 rerun JSON을 복사해 curl body에 붙여도 동일한 trace/policy 결정이 확인됨 / 실패 가능성: 클립보드 API 차단.

### 메트릭 조회

#### 소스 맵
- 메트릭 도구: `apps/api/app/modules/ops/services/ci/tools/metric.py`
- 플랜/실행: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- DB: `metric_def`, `metric_value`

#### 검증 절차

- 메트릭 집계: “sys-erp 지난 24시간 CPU 최대” / 기대: `metric_name`, `agg`, `time_from`, `time_to`, `value` 컬럼이 있는 테이블과 3개 time range `next_actions` / 실패 가능성: metric_value 행 누락 또는 필터/테넌트 문제.
- 메트릭 시리즈: “sys-erp 응답시간 추이 최근 24시간” / 기대: `ts`, `value` 시리즈 테이블이 최신순으로 정렬 / 실패 가능성: `series` 키워드 무시 또는 데이터 없음.
- 시간 범위 rerun: “최근 1시간” 클릭 / 기대: `/ops/ci/ask`가 `metric.time_range = last_1h`로 rerun되고 trace에 patched plan이 기록 / 실패 가능성: validator가 patch 거부 또는 trace 누락.
- 잘못된 메트릭명: “sys-erp foo_metric” / 기대: 사용 가능한 메트릭 목록을 담은 fallback 테이블과 `trace.metric.status = "missing"` / 실패 가능성: 잘못된 이름인데도 빈 결과만 반환.
- 테넌트 격리: `X-Tenant-Id: t2`로 메트릭 질문 / 기대: 메트릭 테이블과 후보 목록에 교차 테넌트 데이터 없음 / 실패 가능성: metric_value가 다른 테넌트에서 누출.

### 이벤트 로그 히스토리

#### 소스 맵
- 히스토리 도구: `apps/api/app/modules/ops/services/ci/tools/history.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- DB: `event_log`

#### 검증 절차

- 히스토리 테이블: “sys-erp 최근 이벤트” / 기대: `Recent events (last_7d)` 테이블과 다른 윈도우 rerun 버튼 / 실패 가능성: 컬럼 누락 또는 테넌트 범위 누락.
- 시간 범위 rerun: “최근 24시간” 클릭 / 기대: `patch.history.time_range = last_24h`가 trace에 기록되고 테이블 갱신 / 실패 가능성: rerun patch 무시.
- event_log 누락: 테이블 임시 rename/drop / 기대: 경고 text 블록 + trace 엔트리, CI 요약은 유지 / 실패 가능성: CI 요약까지 소실.
- 테넌트 격리: `X-Tenant-Id: t2`로 동일 질문 / 기대: `t2` 범위 행만 반환(또는 테넌트 컬럼 누락 시 경고) / 실패 가능성: 교차 테넌트 누출.

### 그래프 범위 메트릭 집계

#### 소스 맵
- 그래프/메트릭: `apps/api/app/modules/ops/services/ci/tools/graph.py`, `apps/api/app/modules/ops/services/ci/tools/metric.py`
- 정책/뷰: `apps/api/app/modules/ops/services/ci/policy.py`, `apps/api/app/modules/ops/services/ci/view_registry.py`

#### 검증 절차

- `sys-erp 의존 범위 지난 24시간 CPU max` / 기대: `Graph metric (...)` 테이블, `trace.metric.scope = "graph"`, `trace.tool_calls`에 `graph_expand` + `metric_aggregate`, time range/agg `next_actions` / 실패 가능성: graph 키워드 누락, 메트릭 조회 실패, `metric.scope` 미적용.
- `sys-erp 주변 CI 최근 7일 error count` / 기대: `trace.policy_decisions.view = "NEIGHBORS"`, `trace.policy_decisions.clamped_depth` 기록, neighbor 집합(CI count > 1)으로 채운 테이블 / 실패 가능성: policy clamp 차단 또는 Neo4j 뷰 차단.
- Depth clamp / “의존 3단계” / 기대: `trace.policy_decisions.clamped_depth` ≤ max(DEPENDS max=3), `graph_payload.truncated`가 true일 때만 `depth +1` 버튼 표시 / 실패 가능성: 허용 depth 초과 또는 next action 누락.
- `sys-erp 의존 범위 metric cpu_usage max last_24h` (확장 CI >300) / 기대: `trace.metric.result.ci_ids_truncated = true`, `trace.metric.result.ci_requested` 기록, `ci_count` 컬럼이 300 반영 / 실패 가능성: truncation 기록 없이 결과가 줄어듦.
- Next-action coverage / graph metric 응답의 “depth +1”, “View IMPACT로 보기”, “집계: avg”, “최근 1시간” 클릭 / 기대: `/ops/ci/ask`가 `rerun.patch`로 `graph`/`view`/`metric`을 조정하고 trace에 업데이트된 `plan_validated` 기록(새 planner 호출 없음) / 실패 가능성: rerun patch 무시 또는 planner 재호출.
- 테넌트 격리 / `curl -s -X POST http://localhost:8000/ops/ci/ask ... -H "X-Tenant-Id: t2"` / 기대: 결과와 trace가 `t2`만 포함하고 `trace.tenant_id == "t2"` / 실패 가능성: 교차 테넌트 데이터 누출.

### 그래프 범위 히스토리

#### 소스 맵
- 그래프/히스토리: `apps/api/app/modules/ops/services/ci/tools/graph.py`, `apps/api/app/modules/ops/services/ci/tools/history.py`
- 정책/뷰: `apps/api/app/modules/ops/services/ci/policy.py`, `apps/api/app/modules/ops/services/ci/view_registry.py`

#### 검증 절차

- `sys-erp 의존 범위 최근 7일 이벤트` / 기대: `/ops/ci/ask`가 DEPENDENCY + depth clamp로 `graph_expand`를 호출(trace), 결과 CI IDs로 `event_log_recent` 실행, time range/depth/view `next_actions`가 있는 테이블 반환 / 실패 가능성: graph expand 생략 또는 테넌트 누출.
- `sys-erp 주변 범위 최근 24시간 알람 100개` / 기대: `history.meta.ci_count_used > 1`인 히스토리 테이블, Neo4j truncated 시 `history_trace.graph.truncated`, CI IDs >300일 때 `history_trace.ci_ids_truncated` 표시.
- `sys-apm 영향 범위 last_30d 이벤트` / 기대: `trace.policy_decisions.view = "IMPACT"`, depth clamp 적용, “depth +1”과 “View DEPENDENCY/NEIGHBORS” rerun 제공.
- `sys-erp 의존 범위 이벤트 depth 3` / 기대: `trace.history.graph.depth_requested = 3`, `depth_applied`가 policy max 이하, policy 한도 도달 시 “depth +1” 버튼 비활성화.
- Next-action coverage / graph history 블록의 “최근 1시간”, “View NEIGHBORS로 보기”, “depth +1” 클릭 / 기대: `rerun.patch`가 `history.time_range` 또는 `graph`를 변경한 rerun이 수행되고 `plan_validated`가 업데이트됨(새 planner 호출 없음).
- 테넌트 격리 / `X-Tenant-Id: t2`로 동일 질문 / 기대: rows/meta/trace가 `t2`만 반영(`trace.tenant_id == "t2"`), `event_log_recent` 테넌트 필터로 교차 누출 없음.

### 메트릭 시리즈 차트

#### 소스 맵
- 메트릭 시리즈: `apps/api/app/modules/ops/services/ci/tools/metric.py`
- UI 렌더링: `apps/web/src/components/answer/BlockRenderer.tsx`

#### 검증 절차

- 시리즈 차트 + 테이블: “sys-erp 최근 24시간 CPU 추이” / 기대: `chart` 블록(라인 시리즈)과 `table` 대체가 모두 표시 / 실패 가능성: 2포인트 이상인데 차트 누락.
- 최소 데이터: “sys-erp metric cpu_usage series last_24h”가 1포인트뿐 / 기대: 차트는 숨겨지고 테이블만 표시 / 실패 가능성: 1포인트로 차트 렌더 시도.
- 차트 실패 복원: 렌더 오류(예: 잘못된 timestamp) 시뮬레이션 / 기대: 차트 블록은 placeholder 안내를 보여주고 테이블은 유지 / 실패 가능성: 차트 오류로 페이지 크래시 또는 테이블 숨김.
- 시간 범위 rerun: 시리즈 응답의 “최근 1시간” next-action 클릭 / 기대: `/ops/ci/ask`가 `patch.metric.time_range = last_1h`로 rerun, 차트/테이블이 동시에 갱신되고 planner는 재호출되지 않음.
- 테넌트 격리: `X-Tenant-Id: t2`로 시리즈 질문 / 기대: 차트와 테이블 행이 `t2`에 스코프되고 `trace.tenant_id == "t2"` / 실패 가능성: 교차 테넌트 데이터 누출.

### CEP 시뮬레이션

#### 소스 맵
- CEP 도구: `apps/api/app/modules/ops/services/ci/tools/cep.py`
- CEP 실행/로그: `apps/api/app/modules/cep_builder/executor.py`, `apps/api/app/modules/cep_builder/crud.py`
- 실행기: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

#### 검증 절차

- Rule 제공: `sys-erp rule <uuid> simulate` / 기대: `rule_id`, condition summary, operator/threshold, extracted value가 포함된 CEP simulate 블록(text + table) / 실패 가능성: CEP 블록 누락.
- Rule ID 누락: “sys-erp simulate” / 기대: rule ID를 요청하는 안내 텍스트 블록 / 실패 가능성: ID 없이 CEP tool 실행.
- Simulate 실패: 비활성화 rule 또는 잘못된 trigger / 기대: CI 블록 유지 + CEP 실패 설명 텍스트, `trace.cep.error` 설정 / 실패 가능성: CI 응답 소실.
- Trace 커버리지: rerun/debug 시 `trace.cep.rule_id_parsed`, `trace.cep.result`, `cep_error`가 기록됨.
- 테넌트 격리: `X-Tenant-Id: t2`로 동일 질문 / 기대: CEP 블록과 테이블이 `t2` 컨텍스트로 실행되고 `trace.tenant_id == "t2"`.

### CEP 테스트 페이로드 생성

#### 소스 맵
- 페이로드 생성: `apps/api/app/modules/ops/services/ci/tools/cep.py`

#### 검증 절차

- payload 미제공 시에도 `test_payload_built=true`와 payload size 정보가 trace에 포함.
- payload truncation: CI tag 블록을 크게 만들어 `trace.cep.payload_truncated=true`가 찍히고 simulate는 계속 실행됨.
- metric/history 컨텍스트가 없어도 auto-built payload로 simulate가 CI 정보만으로 동작.
- CEP 실패 복원 유지: 잘못된 rule에서도 실패 텍스트 블록과 `trace.cep.error`가 유지됨.

### CEP 런타임 Fetch 증거

#### 소스 맵
- 증거/마스킹: `apps/api/app/modules/ops/services/ci/tools/cep.py`
- CEP 평가: `apps/api/app/modules/cep_builder/executor.py`

#### 검증 절차

- CEP simulate 응답에 `"endpoint","method","value_path","op","threshold","extracted_value","evaluated","status","error"` 컬럼의 evidence 테이블이 포함됨.
- token/secret/password 류 키가 있으면 trace/evidence의 params가 `***`로 마스킹됨.
- runtime fetch 오류 시 evidence 행에 `status=error`와 `error` 텍스트가 표시되고 CI/metric/history 블록은 영향 없음.
- `trace.cep.evidence`, `trace.cep.params_masked`, `trace.cep.extracted_value_truncated`가 렌더링 결과를 정확히 반영.

### CEP 런타임 파라미터 정책

#### 소스 맵
- 정책 파일: `apps/api/app/modules/ops/services/ci/cep/param_mapping.yaml`
- 정책 적용: `apps/api/app/modules/ops/services/ci/tools/cep.py`

#### 검증 절차

- `ops/ci/cep/param_mapping.yaml`을 수정(예: `location` 제거)해 `trace.cep.runtime_params_keys`가 allowlist 변경을 반영하고 `runtime_params_policy_source = "yaml"`인지 확인.
- blocked 필드(`token`/`secret`)가 있는 runtime fetch rule을 제공하고 evidence 테이블이 허용된 키만 표시하며 `trace.cep.runtime_params_meta.blocked_removed`에 제거 항목이 기록되는지 확인.
- `trace.cep.runtime_params_meta`에 `built`, `size_bytes`, `policy_source`, `truncated`, `keys_added`, `final_keys`가 포함되고 evidence 행의 `params_keys`와 `trace.cep.runtime_params_keys`가 일치함을 확인.
- YAML 파일이 없거나 잘못된 경우에도 runner는 동작(정책 소스 `fallback`)하며 evidence/trace에 `params_keys`가 표시됨.
- param mapping 변경과 무관하게 기존 CI/metric/history/CEP 블록은 유지되고 runtime param 메타데이터만 갱신됨.

### CEP 페이로드 요약

#### 소스 맵
- 페이로드 요약/트렁케이션: `apps/api/app/modules/ops/services/ci/tools/cep.py`

#### 검증 절차

- metric+history 질문 실행 후 `trace.cep.test_payload_sections`를 확인하고, 두 요약이 모두 있으면 `"ci","metric","history"`가 포함되며 `test_payload_metric_keys_present`/`test_payload_history_keys_present`가 true인지 확인.
- 반환된 `test_payload`(trace 또는 log)에서 `metric.metric_name`, `metric.agg`, `metric.time_range`, `metric.value`, `history.source`, `history.time_range`, `history.count`, `history.recent[0].summary` 키가 항상 존재하는지 확인(값은 `null`일 수 있음).
- history/metric을 크게 만들어 payload가 16KB를 넘도록 하고 `trace.cep.payload_truncated=true`, `history.recent`가 ≤3개(반복 truncation 후 1개)로 줄며 `test_payload_sections`가 남은 섹션을 정확히 반영하는지 확인.
- 기존 params/evidence 메타데이터는 유지(`params_table`의 `params_keys` 컬럼, `runtime_params_meta`/`runtime_params_keys` 등)되어야 함.

### CEP 이벤트 브라우저 링크

#### 소스 맵
- next_action 생성: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- 액션 계약: `apps/api/app/modules/ops/services/ci/actions.py`
- Frontend 이동: `apps/web/src/app/ops/nextActions.ts`, `apps/web/src/app/ops/page.tsx`
- 이벤트 브라우저 화면: `apps/web/src/app/cep-events/page.tsx`

#### 검증 절차

- CEP simulate 후 `trace.cep.exec_log_id`(및 `trace.cep.simulation_id`)가 trace에 나타나고 요약 테이블의 `exec_log_id` 컬럼에 동일 ID가 표시되는지 확인.
- “Event Browser로 보기” next-action 버튼을 눌러 `/cep-events`로 이동하고 query string에 `exec_log_id`(또는 `simulation_id`)가 붙는지 확인; Event Browser가 해당 ID를 수용해야 함.
- next action 이후 `/cep-events`가 열리면 동일 실행을 하이라이트/필터(또는 최소한 `exec_log_id` 필터 노출)해야 하며 planner rerun이 없어야 함.
- exec log 행이 없는 경우에도 버튼이 표시되고 `simulation_id`가 전달되어 네비게이션이 일관되어야 함.

### 이벤트 브라우저 실행 조회

#### 소스 맵
- Backend API: `apps/api/app/modules/cep_builder/router.py` (`/cep/events/run`)
- Frontend: `apps/web/src/app/cep-events/page.tsx`

#### 검증 절차

- CI → CEP simulate → “Event Browser로 보기” 클릭 / 기대: `/cep-events?exec_log_id=...`(또는 `simulation_id`)로 이동하고 exec log ID, simulation ID, rule ID, created time, condition flag, tenant가 포함된 요약 카드 표시.
- Event Browser의 evidence 테이블이 `endpoint`, `method`, `value_path`, `op`, `threshold`, `extracted_value`, `evaluated`, `status`, `error` 컬럼을 동일하게 갖는지 확인.
- exec log가 존재하지만 Event Browser가 찾지 못하는 상황(예: 로그 행 삭제)에서 “CEP run not found” 안내와 함께 테넌트/요청 ID가 표시되는지 확인.
- raw references 섹션이 큰 JSON을 truncation 처리하며 UI가 반응성을 유지하는지 확인.

### AUTO 모드 레시피

#### 소스 맵
- Auto 플랜: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`
- 오케스트레이터: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- Frontend: `apps/web/src/app/ops/page.tsx`

#### 검증 절차

- `X-Tenant-Id: t1`으로 “sys-erp 상태 점검해줘” / 기대: “AUTO 점검” 텍스트 블록으로 시작하고 CI detail 블록, NEIGHBORS 그래프, metric aggregate 테이블(cpu_usage/latency/error), 최근 이벤트 테이블, CEP 블록(rule_id 있을 때)이 이어짐; `trace.auto.auto_recipe_applied`는 true.
- 메트릭이 없을 때는 AUTO metrics 블록이 누락 후보를 설명하고 `trace.auto.metrics.candidates`에 시도된 이름이 기록됨.
- graph/metric/history 오류(예: Neo4j 비활성화, metric_def 삭제, event fetch 오류) 시 AUTO 요약 텍스트가 “N/A”/“failed”로 표시되고 실패 텍스트 블록이 추가되며 나머지 블록은 유지됨.
- rule UUID 포함 시 auto recipe 이후에도 CEP simulate 블록과 “Event Browser로 보기”가 유지되어야 함.

### AUTO 동적 선택

#### 소스 맵
- Auto 판단/정책: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`, `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`, `apps/api/app/modules/ops/services/ci/policy.py`
- 오케스트레이터: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- Frontend: `apps/web/src/app/ops/page.tsx`

#### 검증 절차

- `sys-erp 의존 관계 알려줘` / 기대: `trace.auto.views.applied`에 DEPENDENCY 포함, `trace.auto.depths`에 clamped depth 기록, DEPENDENCY 그래프 + 요약 블록 표시 / 실패 가능성: 이유 없이 NEIGHBORS로 디폴트.
- `sys-erp 구성 요소 보여줘` / 기대: COMPOSITION 뷰 실행, graph next-actions에 view/depth 조정 제공, `trace.auto.views`에 node/edge 카운트 포함 / 실패 가능성: 요약에 view 누락.
- `sys-erp 최근 24시간 cpu 추이` / 기대: `trace.auto.metrics.status`가 `spec` 또는 `ok`, 시리즈 차트/테이블 표시, time-range rerun이 planner 출력은 유지하면서 `metric.time_range`만 업데이트.
- `sys-erp 최근 7일 이벤트` / 기대: history 실행, 이벤트 테이블 행 수와 `trace.auto.history.rows` 일치, 다른 time range/depth next actions 제공.
- `sys-erp rule <uuid> simulate` / 기대: CEP 실행, `trace.auto.cep.rule_id` 일치, dynamic auto selection이라도 “Event Browser로 보기” next action 유지.
- `sys-erp 와 sys-apm 어떻게 연결돼?` / 기대: PATH 질문이면 cached PATH 또는 후보 메시지 노출(`trace.auto.views`에 PATH skip 표시), SUMMARY는 항상 유지.

### AUTO PATH 완성 & 그래프 스코프 혼합

#### 소스 맵
- PATH/그래프 도구: `apps/api/app/modules/ops/services/ci/tools/graph.py`
- 오케스트레이터: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- Frontend: `apps/web/src/components/answer/BlockRenderer.tsx`

#### 검증 절차

- `sys-erp 와 sys-apm 어떻게 연결돼?` / 기대: 요약에 PATH 언급, `trace.auto.path.status = "ok"`, graph path 블록 표시 / 실패 가능성: path 후보 흐름 미동작 또는 planner 재호출.
- `sys-erp 경로 알려줘` / 기대: CI 한 개만 있을 때 후보 테이블과 “대상 선택” next actions 표시, 후보 클릭 시 `patch.auto.path.target_ci_code`로 rerun되어 planner 호출 없이 path 반환(`trace.plan_validated` 유지).
- `sys-erp 의존 범위 성능도 같이 보여줘` / 기대: dependency 그래프 노드, “Graph-scope metrics” 테이블, `trace.auto.graph_scope.metric`에 CI count/truncated 표시, `trace.auto.metrics`에 추가 스코프 반영.
- `sys-erp 영향 범위 최근 이벤트도 같이` / 기대: “Graph-scope events…” 테이블, `trace.auto.graph_scope.history.rows`가 row count와 일치, `trace.auto.history`가 graph 확장 trace와 일치.
- `sys-erp 영향 범위 성능+이벤트 같이` / 기대: graph-scope metric/history 테이블 모두 표시, 실패 시 텍스트로 실패 표기하되 CI detail과 다른 블록은 유지.
- ci_ids cap/truncation / 기대: >300 노드 확장 시 `trace.auto.graph_scope.ci_ids_count`, `ci_ids_truncated`, history 메타데이터에 truncation 기록, metric/history 호출은 truncated set으로 실행.

### AUTO 인사이트 & 추천 액션

#### 소스 맵
- 추천/인사이트 생성: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- 액션 계약: `apps/api/app/modules/ops/services/ci/actions.py`
- Frontend: `apps/web/src/components/answer/BlockRenderer.tsx`

#### 검증 절차

- “sys-erp 상태 점검해줘” / 기대: “AUTO Insights” 텍스트 카드 + 숫자 타일(노드 수, depth, events, metric)로 시작, `trace.auto.recommendations`에 선택 사유 기록.
- “sys-erp 의존 범위 성능+이벤트 같이” / 기대: metric/highlight 타일이 graph-scope 값을 언급하고, 추천 액션이 metric/time-range/history limit 조정을 제안하며, 클릭 시 `/ops/ci/ask`가 patched plan으로 rerun됨.
- “sys-erp 와 sys-apm 어떻게 연결돼?” / 기대: insight 카드에 PATH 언급, 추천 액션이 대상 후보 버튼을 상단에 배치, path rerun이 planner 재호출 없이 수행(`trace.plan_validated` 유지).
- “sys-erp rule <uuid> simulate” / 기대: CEP insight가 rule ID 언급, `trace.auto.recommendations`에 Event Browser 힌트 포함(액션 리스트 최상단), 이미 CEP 블록이 있어도 액션 동작.

### CI 목록 미리보기

#### 소스 맵
- 리스트 도구: `apps/api/app/modules/ops/services/ci/tools/ci.py`
- 실행/플랜: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`, `apps/api/app/modules/ops/services/ci/planner/validator.py`
- Frontend: `apps/web/src/components/answer/BlockRenderer.tsx`

#### 검증 절차

- “전체 CI 목록 50개 + 개수” → 기대: 집계 테이블과 목록 미리보기 테이블(50 rows) 모두 표시, 텍스트 힌트에 총 개수 언급, trace에 `trace.list.requested`/`trace.list.applied` 포함.
- “CI 목록 20개” → 기대: 20 rows만 표시, planner가 50으로 clamp하더라도 `trace.list.limit`가 적용값을 보여줌.
- `trace.list`가 모든 목록 요청에 존재하고 50개 초과 요청 시 `limit_clamped`가 기록되는지 확인.
