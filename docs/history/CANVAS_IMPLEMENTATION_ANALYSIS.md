# OPS Orchestration Canvas - 구현 분석 보고서

> **작성일**: 2026-01-22  
> **목적**: Baseline Canvas 대비 현재 구현 상태 분석 및 우선순위 기반 구현 계획 수립

---

## 1. 요약 (Executive Summary)

### 1.1 핵심 발견

| 영역 | Canvas 요구 | 현재 구현 | 상태 |
|------|------------|-----------|------|
| **Query Handling** | Single LLM → Direct/Orch/Reject 분기 | 항상 CI Orchestration만 수행 | ❌ 미구현 |
| **Pipeline Stage** | 5개 Stage 분리 + Stage In/Out 저장 | Runner 내부에 EXECUTE/COMPOSE 혼재 | ⚠️ 부분 구현 |
| **Control Loop** | 자동 Replan/Rerun + Trigger/Scope 제어 | 사용자 Rerun만 존재 | ❌ 미구현 |
| **Asset Model** | Source/Schema/Resolver 포함 전체 Asset | Prompt/Policy/Query/Screen만 존재 | ⚠️ 부분 구현 |
| **Trace & Observability** | Stage별 In/Out + ReplanEvent 1급 객체 | plan/tool_calls/blocks 중심 | ⚠️ 부분 구현 |
| **Testability** | Asset Swap + Isolated Stage Test | ❌ 미구현 | ❌ 미구현 |

### 1.2 전체 구현률

- **필수조건 (Necessary)**: ~35% (CI 전용 기능만 구현)
- **충분조건 (Sufficient)**: ~15% (범용 오케스트레이션 핵심 미구현)

---

## 2. 상세 분석 (Detailed Analysis)

### 2.1 Query Handling Model

#### Canvas 요구
- **Single LLM Call**로 세 가지 경로 분기:
  - `DirectAnswer`: 데이터 조회 없이 즉시 답변
  - `OrchestrationPlan`: 데이터/문서/그래프 사용하는 실행 계획
  - `Reject`: 정책 기반 거절
- LLM 출력 계약으로 `kind` 필드 강제

#### 현재 구현 상태
```python
# apps/api/app/modules/ops/router.py - ask_ci()
def ask_ci(payload: CiAskRequest):
    # 항상 planner → validator → runner 실행
    plan_raw = planner_llm.create_plan(payload.question)
    plan_validated, plan_trace = validator.validate_plan(plan_raw)
    runner = CIOrchestratorRunner(...)
    result = runner.run()
```

**문제점**:
1. `DirectAnswer`/`Reject` 경로가 없음
2. 항상 CI 전용 오케스트레이션만 실행
3. `planner_llm.create_plan()`이 실패 시 규칙 기반 fallback 수행 (LLM 의도와 다름)

#### 갭 해석
- Canvas는 "범용 질의 처리"를 전제하지만, 현재는 **CI 도메인 전용**으로 구현됨
- Direct Answer 경로는 간단한 Q&A나 일반 질문에 대응하기 위한 것인데 현재 없음
- Reject는 정책 위반 시 명확한 거절 메시지를 위한 것인데 현재 없음

---

### 2.2 Orchestration Pipeline

#### Canvas 요구
고정된 5개 Stage:
```
ROUTE+PLAN → VALIDATE → EXECUTE → COMPOSE → PRESENT
```

각 Stage는:
- **Stage Input**: Asset 목록 + 이전 Stage Output + Control Context
- **Stage Output**: 결과 구조 + Diagnostics + References
- Trace에 In/Out이 분리 저장됨

#### 현재 구현 상태
```python
# runner.py - CIOrchestratorRunner
class CIOrchestratorRunner:
    def run(self):
        # ROUTE+PLAN: planner_llm.create_plan() 호출
        # VALIDATE: validator.validate_plan() 호출
        # EXECUTE + COMPOSE: runner 내부에서 툴 실행 + 블록 조합이 혼재
        # PRESENT: 프론트엔드 (UIScreenRenderer)에 위임
```

**문제점**:
1. **EXECUTE와 COMPOSE가 runner 내부에서 혼재**
   - `_handle_lookup()`, `_handle_aggregate()` 등이 툴 실행과 블록 생성을 동시에 수행
2. **Stage별 In/Out 구조가 없음**
   - Trace에는 `plan_raw`, `plan_validated`, `tool_calls`, `blocks`만 저장
   - Stage 입력/출력이 분리되지 않음
3. **PRESENT가 Backend Stage가 아님**
   - 실제 UI 렌더링은 프론트엔드 `UIScreenRenderer`에서 수행

#### 갭 해석
- 논리적으로는 5개 Stage가 존재하지만, **물리적 구현은 runner 내부에 통합**되어 있음
- Stage별 테스트나 Asset Swap이 불가능한 구조
- PRESENT는 프론트엔드 렌더링으로 분리되는 것이 맞으나, **Stage Output으로서의 trace 기록이 없음**

---

### 2.3 Control Loop (Replan / Rerun)

#### Canvas 요구
- **Control Loop는 Orchestrator Runtime의 공통 메커니즘**
- Replan (시스템 자동 보정/재시도):
  - Trigger: `SLOT_MISSING`, `EMPTY_RESULT`, `TOOL_ERROR_RETRYABLE`, `POLICY_BLOCKED`, `LOW_EVIDENCE`
  - Scope: `EXECUTE`, `COMPOSE`, `PRESENT`
  - Limit: `max_replans` (2~3), `max_internal_retries` (1~2)
- Rerun (사용자 선택 기반 재실행):
  - Replan과 동일 루프에서 처리
- ReplanEvent가 trace에 1급 객체로 저장됨

#### 현재 구현 상태
```python
# router.py - ask_ci()
def ask_ci(payload: CiAskRequest):
    if payload.rerun:
        # plan patch 적용 후 재실행
        patched_plan = _apply_patch(payload.rerun.base_plan, payload.rerun.patch)
        plan_validated, plan_trace = validator.validate_plan(patched_plan)
        runner = CIOrchestratorRunner(...)
        result = runner.run()
```

**문제점**:
1. **자동 Replan이 없음**
   - 사용자가 rerun 버튼을 눌러야만 재실행 가능
   - 에러나 빈 결과 시 자동 재시도 로직 없음
2. **Trigger/Scope/Limit 제어가 없음**
   - 어떤 상황에서 Replan할지, 어디서 다시 시작할지 정의 없음
   - 무한 루프 방지 정책 없음
3. **ReplanEvent가 없음**
   - Replan/Rerun 이벤트가 trace에 별도로 기록되지 않음

#### 갭 해석
- 현재는 **사용자 주도 Rerun만 존재**하고, 시스템 자동 보정 기능은 없음
- Canvas의 "Control Loop는 Runtime 공통 메커니즘"이라는 설계가 구현되지 않음

---

### 2.4 Asset Model

#### Canvas 요구
Config Assets (UI에서 설정):
1. **Source** – 데이터 소스 시스템
2. **SchemaCatalog** – 엔티티/테이블/문서/그래프 메타
3. **Query** – Query Template (SQL/Cypher/Vector/API)
4. **Mapping** – ResultSet → Block 변환 규칙
5. **Policy** – 제한, 접근, 재질의 규칙
6. **Prompt** – Route+Plan / Compose용
7. **Screen** – Answer UI 구성
8. **ResolverConfig** – 엔티티/별칭 매칭 규칙

Runtime Contracts (읽기 전용):
9. **ToolContracts** – ToolResult / Reference 계약
10. **BlockContracts** – Block 스키마

#### 현재 구현 상태
```python
# apps/api/app/modules/asset_registry/models.py
class TbAsset(Base):
    kind: Literal["prompt", "policy", "query", "mapping", "screen"]
```

**구현된 Asset**:
- ✅ **Prompt**: Route+Plan/Compose용 프롬프트
- ✅ **Policy**: 제한, 접근 규칙
- ✅ **Query**: SQL/Cypher 템플릿
- ✅ **Mapping**: ResultSet → Block 변환
- ✅ **Screen**: UI Screen 정의

**미구현된 Asset**:
- ❌ **Source**: 데이터 소스 연결 정보
- ❌ **SchemaCatalog**: 엔티티/테이블 메타데이터
- ❌ **ResolverConfig**: 엔티티/별칭 매칭 규칙
- ❌ **ToolContracts/BlockContracts**: Asset 형태가 아님 (코드 스키마로만 존재)

#### 갭 해석
- Asset Registry는 CI 도메인에 필요한 Asset만 구현됨
- **Source/SchemaCatalog/ResolverConfig는 범용 오케스트레이션의 핵심**이므로 반드시 필요
- 현재는 "데이터 소스부터 답변까지"를 구성할 수 없음

---

### 2.5 Execution Trace & Observability

#### Canvas 요구
- **Stage In/Out 계약**: 각 Stage의 입력/출력이 Trace에 저장됨
- **References 항상 존재**: 모든 실행에 references가 포함됨 (빈 배열 포함)
- **ReplanEvent 1급 객체**: trigger/scope/decision/patch가 trace에 저장됨
- **Inspector**: Stage별 In/Out 확인 + Diff View
- **Regression**: Replan 변화, empty/warn 변화 비교

#### 현재 구현 상태
```python
# apps/api/app/modules/inspector/service.py
def persist_execution_trace(...):
    trace = TbExecutionTrace(
        plan_raw=plan_raw,
        plan_validated=plan_validated,
        tool_calls=tool_calls,
        references=references,
        blocks=blocks,
        # stage_inputs, stage_outputs, replan_events는 없음
    )
```

**Trace 저장 필드**:
- ✅ `plan_raw`, `plan_validated`
- ✅ `tool_calls` (ToolCall 형식)
- ⚠️ `references` (blocks에서 추출, 존재하지 않을 수 있음)
- ✅ `blocks`
- ✅ `flow_spans` (span tracking)
- ❌ `stage_inputs`, `stage_outputs`
- ❌ `replan_events`

**문제점**:
1. **Stage In/Out이 없음**
   - 각 Stage의 입력/출력을 검사할 수 없음
   - Asset Swap 테스트 불가능
2. **References가 항상 존재하지 않음**
   - `blocks`에서 `references` block이 없으면 빈 배열이 됨
   - Canvas의 "References 항상 존재" 원칙 위반
3. **ReplanEvent가 없음**
   - Replan/Rerun 이벤트가 trace에 기록되지 않음

#### 갭 해석
- 현재 Trace는 **plan/tool_calls/blocks 중심**
- Canvas는 **Stage 관점의 trace**를 요구하므로 구조적 차이가 큼

---

## 3. 사용자 중심 구성 (User-Centric Configuration)

### 3.1 Happy Path: Source → Schema → Query → Answer

Canvas 섹션 10에서 정의한 사용자 작업 흐름 (7단계):

1. **Source 연결** (Data/Admin)
   - 엔진 선택 (Postgres/Timescale/Neo4j/Vector/API)
   - 연결 정보/권한/환경 설정 (real/mock)
   - 연결 테스트 (health check) + 권한/리밋 확인

2. **SchemaCatalog 작성/동기화**
   - 테이블/측정치/그래프/문서 컬렉션을 "엔티티/관계/측정치" 관점으로 등록
   - (선택) 스키마 자동 스캔 → 사람이 의미(엔티티/시간/단위/키)를 보강
   - 엔티티 키/조인 키/시간 컬럼(또는 time 의미) 명시

3. **ResolverConfig 설정** (식별자/별칭/모호성 정책)
   - 예: "가스터빈 1호기=GT-01" 별칭 묶음
   - 모호성 시 ask_user(top-k 후보)

4. **QueryTemplate 작성** (결정적 실행) + Preview
   - SQL/Cypher/Vector/API 템플릿 등록
   - 입력 파라미터 정의 (entity_id/time_range/metric_name...)
   - Preview 실행 (샘플 파라미터로 결과 확인)
   - Output schema + Reference 생성 규칙 확인

5. **Mapping 작성** (결과→Block) + Preview
   - table/chart/graph/doc_link 변환
   - row/point 제한 정책과 연계

6. **Screen 구성** (PRESENT) + Preview
   - blocks 배치/접기/refs 표시 규칙

7. **OPS에서 통합 질문으로 End-to-End 테스트**
   - baseline_trace 저장
   - Regression에 golden으로 등록 (선택)

### 3.2 핵심 UI 컴포넌트 (고정)

1. **Source Profile Editor**
   - 엔진/연결/권한/리밋/테스트

2. **Schema Catalog Builder**
   - 엔티티/관계/측정치/문서 카탈로그 편집 + 자동 스캔 보조

3. **Query Template Builder**
   - 입력/쿼리 본문/출력 스키마/Preview

4. **Mapping Builder**
   - ResultSet→Block 규칙 + Preview

5. **Screen Builder/Renderer**
   - Screen 정의 + 실제 렌더 미리보기

6. **Asset Binding Lens**
   - 각 asset이 pipeline stage 어디에 연결되는지 표시

7. **Test Runner (Override Run)**
   - asset_overrides로 실행 + In/Out + Diff

### 3.3 Reuse-first 원칙

**원칙**: 새 페이지를 무한히 늘리지 않는다. 기존 메뉴에 탭/드로어/모달/서브패널 형태로 기능을 결합하여 재활용한다.

기존 메뉴 재활용 전략:
- `/admin/assets`: 자산 편집/배포 + Pipeline Lens + Override Test 진입
- `/ops`: End-to-End 실행 + Action Card + Timeline + Override Drawer
- `/admin/inspector`: Stage In/Out + ReplanEvent + Diff
- `/admin/regression`: Golden 비교 + 변경 영향
- `/ui/screens`: Screen 편집/미리보기
- `(보강) /data`: Sources/Catalog/Resolvers 시작점

---

## 4. UI & API Delta (최소 변경으로 빈틈없이)

### 4.1 UI 변화 (기존 화면 재활용 중심)

#### (A) Data 메뉴 강화 (Source/Schema 시작점)

`/data` 하위에 탭(또는 좌측 서브메뉴)로 제공:

- **Sources**: Source Profile 목록/편집/연결 테스트
- **Catalog**: SchemaCatalog 빌더(스캔+보강)
- **Resolvers**: ResolverConfig 관리

#### (B) Admin > Assets를 "Pipeline Lens"로 재구성

기존 목록 UI에 다음 추가:

- asset 상세에 **Bound Stage**, **Used By**, **Last Used**, **Deps**
- **Run Test(Override)** 버튼: 특정 stage asset 교체 후 실행
- Preview 패널: Query/Mapping/Screen 각각 결과 미리보기

#### (C) OPS(/ops)에서 사람 중심 실행/재질의/테스트

- 상단 Summary Strip: route/ops_mode/plan_mode/replans/warnings/refs
- Timeline 탭: stage별 In/Out 열람
- Action Cards: trigger/scope/선택지/예상 영향
- **Test Mode 토글 + Override Drawer**
  - 현재 실행에 사용할 asset overrides 선택
  - baseline_trace 선택 후 diff 보기

#### (D) Inspector/Regression을 "비교/검증 도구"로 강화

**Inspector**:
- stage input/output 패널
- ReplanEvent 1급 객체 + patch diff

**Regression**:
- golden 실행 결과의 stage/refs/replan/empty 변화 비교

### 4.2 API 변화 (핵심 필드/엔드포인트)

#### (A) Source/Schema/Resolver 자산 API

- Source CRUD + 연결 테스트 endpoint
- SchemaCatalog CRUD + (선택) 스캔/동기화 endpoint
- ResolverConfig CRUD

#### (B) OPS 실행 요청 확장 (테스트/오버라이드)

```python
class ExecutionRequest(BaseModel):
    question: str
    test_mode: bool = False
    asset_overrides: Dict[str, str] = {}  # stage -> asset_id
    baseline_trace_id: Optional[str] = None
```

#### (C) Trace 스키마 확장 (Stage In/Out)

- `stage_inputs[]`, `stage_outputs[]`
- `replan_events[]` (trigger/scope/decision/patch)
- `route` (direct/orch/reject)

#### (D) Route+Plan 출력 계약 강제

- LLM 출력 `kind=direct|plan|reject`
- validator가 최소 필드/정책 준수 검증

---

## 5. 우선순위 기반 구현 계획 (Priority-Based Implementation Plan)

### 5.1 Phase 1: Route+Plan 분기 완결성 (P0 - 최우선)

#### 목표
Single LLM 호출로 `DirectAnswer`/`OrchestrationPlan`/`Reject`를 명시적으로 반환

#### Canvas DoD 요구 (8.1-3)
- LLM 출력은 DirectAnswer / OrchestrationPlan / Reject 중 하나
- Validator가 kind + 최소 필드를 검증
- DirectAnswer도 trace/references를 남김

#### 작업 항목
1. **Planner 출력 계약 변경**
   - `plan_schema.py`에 `RouteKind` enum 추가:
     ```python
     class RouteKind(str, Enum):
         DIRECT = "direct"
         ORCHESTRATION = "orchestration"
         REJECT = "reject"
     ```
   - `Plan` 모델에 `kind: RouteKind` 필드 추가
   - `planner_llm.create_plan()`이 `kind`를 포함한 Plan을 반환하도록 수정
   - DirectAnswer인 경우 `answer` 필드 필수화
   - Reject인 경우 `reject_reason` 필드 필수화

2. **Validator 확장**
   - `kind` 필드 검증
   - `REJECT`인 경우 `reject_reason` 필드 필수화 + 정책 사유 포함
   - `DIRECT`인 경우 `answer` 필드 필수화

3. **Router 로직 분기**
   - `ask_ci()`에서 `kind`에 따라 분기:
     ```python
     if plan.kind == RouteKind.REJECT:
         return reject_response(plan.reject_reason, retry_guide=plan.retry_guide)
     elif plan.kind == RouteKind.DIRECT:
         return direct_answer_response(plan.answer, references=plan.references)
     else:
         # 기존 orchestration 로직
     ```

4. **Trace 확장**
   - `route` 필드 저장 (`direct`/`orchestration`/`reject`)
   - Direct/Reject도 trace/references 기록 (빈 배열 포함)

#### 예상 작업량
- 백엔드: 3-4일
- 테스트: 2일
- **총계: 5-6일**

---

### 5.2 Phase 2: Stage In/Out 저장 구조화 (P1 - 높은 우선순위)

#### 목표
각 Stage의 입력/출력을 Trace에 분리 저장

#### Canvas DoD 요구 (8.1-1, 6A)
- ROUTE+PLAN/VALIDATE/EXECUTE/COMPOSE/PRESENT 각각에 대해 StageInput/StageOutput/timings/spans이 trace에 저장됨
- Stage Output에는 표준화된 결과 구조 + Diagnostics + References (항상 존재)
- Inspector에서 Stage별 In/Out 확인 + Diff View 지원

#### 작업 항목
1. **Stage In/Out 모델 정의**
   ```python
   class AssetRef(BaseModel):
       asset_id: str
       asset_kind: str
       version: int
       status: Literal["draft", "published", "rollback"]

   class StageInput(BaseModel):
       stage_name: str
       assets: List[AssetRef]
       input_params: Dict[str, Any]
       prev_output: Optional[Dict[str, Any]]
       control_context: Optional[Dict[str, Any]]  # replan scope, retry count 등

   class StageDiagnostics(BaseModel):
       status: Literal["ok", "warn", "error"]
       warnings: List[str] = []
       errors: List[str] = []
       empty_flags: Dict[str, bool] = {}
       gaps: Dict[str, Any] = {}  # 가능하면
       timing_ms: int

   class StageOutput(BaseModel):
       stage_name: str
       result: Dict[str, Any]  # Plan / ToolResult / Blocks 등
       diagnostics: StageDiagnostics
       references: List[ReferenceItem]  # 항상 존재 (빈 배열 포함)
   ```

2. **Runner 수정**
   - 각 Stage 실행 전 `StageInput` 생성 (적용된 Asset 목록 + 이전 Output)
   - 각 Stage 실행 후 `StageOutput` 생성 (result + diagnostics + references)
   - Trace에 `stage_inputs[]`, `stage_outputs[]`로 저장
   - `flow_spans`와 통합하여 timing/spans 기록

3. **References 강제화**
   - 각 Stage Output에 references 항상 포함 (빈 배열 포함)
   - blocks에서 references를 추출하는 것이 아니라, Stage에서 직접 생성

4. **Inspector API 확장**
   - Stage별 In/Out 조회 엔드포인트 (`GET /inspector/{trace_id}/stage/{stage_name}`)
   - Diff View 지원 (baseline vs current)
   - Stage Input Panel: 사용된 Asset 목록 + 주요 입력 파라미터 요약
   - Stage Output Panel: 결과 구조 요약 + Empty/Warning/Error 표시

#### 예상 작업량
- 백엔드: 4-5일
- 프론트엔드: 3-4일
- 테스트: 2일
- **총계: 9-11일**

---

### 5.3 Phase 3: Asset Model 범용화 (P1 - 높은 우선순위)

#### 목표
Source/SchemaCatalog/ResolverConfig를 Asset Registry에 추가

#### Canvas DoD 요구 (8.4, 10, 11)
- Source/SchemaCatalog/ResolverConfig까지 UI 기반 Asset 관리
- Asset의 bound_stage, used_by, last_used, deps 표시
- Data 메뉴에 Sources/Catalog/Resolvers 시작점 제공

#### 작업 항목
1. **Source Asset 추가**
   - `kind: "source"` 추가
   - 필드: 
     ```python
     engine: Literal["postgres", "timescale", "neo4j", "vector", "api"]
     connection_params: Dict[str, Any]  # host, port, database, credentials 등
     permissions: Dict[str, Any]  # read_only, tables, operations 등
     environment: Literal["real", "mock"]
     health_check_config: Dict[str, Any]  # timeout, retry_count 등
     ```
   - Health check endpoint (`POST /assets/sources/{asset_id}/health-check`)

2. **SchemaCatalog Asset 추가**
   - `kind: "schema_catalog"` 추가
   - 필드:
     ```python
     entities: List[Dict[str, Any]]  # 엔티티/관계/측정치
     tables: List[Dict[str, Any]]  # 테이블/컬럼/타입
     relationships: List[Dict[str, Any]]  # 엔티티 간 관계
     graph_collections: List[Dict[str, Any]]  # 그래프 노드/엣지/속성
     time_columns: Dict[str, str]  # 테이블별 시간 컬럼
     join_keys: Dict[str, List[str]]  # 조인 키 정의
     ```
   - Schema scan/sync endpoint (`POST /assets/schema-catalogs/{asset_id}/scan`)

3. **ResolverConfig Asset 추가**
   - `kind: "resolver_config"` 추가
   - 필드:
     ```python
     entity_mappings: List[Dict[str, Any]]  # 엔티티 매핑 규칙
     alias_groups: List[Dict[str, List[str]]]  # 별칭 묶음 (예: {"GT-01": ["가스터빈 1호기", "turbine-01"]})
     ambiguity_policy: Literal["ask_user", "first_match", "top_k"]  # 모호성 처리 정책
     top_k_limit: int = 5  # ask_user 시 후보 수
     ```
   - Resolver 로직 통합 (기존 CI resolver 확장)

4. **Admin UI 확장 (Pipeline Lens)**
   - `/admin/assets`에 다음 필드 추가:
     - **Bound Stage**: 이 Asset이 바인딩된 pipeline stage
     - **Used By**: 이 Asset을 사용하는 다른 Asset 목록
     - **Last Used**: 마지막으로 사용된 trace_id/timestamp
     - **Deps**: 의존하는 Asset 목록
   - **Run Test(Override)** 버튼: 특정 stage asset 교체 후 실행 진입
   - Preview 패널: Query/Mapping/Screen 각각 결과 미리보기

5. **Data 메뉴 강화**
   - `/data` 하위에 탭 제공:
     - **Sources**: Source Profile 목록/편집/연결 테스트
     - **Catalog**: SchemaCatalog 빌더(스캔+보강)
     - **Resolvers**: ResolverConfig 관리

#### 예상 작업량
- 백엔드: 5-6일
- 프론트엔드: 4-5일
- 테스트: 3일
- **총계: 12-14일**

---

### 5.4 Phase 4: Control Loop 자동화 (P2 - 중간 우선순위)

#### 목표
자동 Replan 엔진 구현 + 사용자 Rerun과 동일 루프에서 처리

#### Canvas DoD 요구 (8.1-2, 8.2-5, 8.2-8)
- Trigger 분류 (EMPTY_RESULT/SLOT_MISSING/...)
- Scope 결정 (EXECUTE/COMPOSE/PRESENT)
- Decision (auto_retry/ask_user/stop_with_guidance)
- max_replans/max_retries 강제
- ReplanEvent가 trace에 1급 객체로 저장
- Action Card에 trigger/scope/선택지/예상 영향 표시
- Regression에서 replans 변화가 1급 지표로 비교

#### 작업 항목
1. **Replan Engine 구현**
   ```python
   class ReplanTrigger(str, Enum):
       SLOT_MISSING = "slot_missing"
       EMPTY_RESULT = "empty_result"
       TOOL_ERROR_RETRYABLE = "tool_error_retryable"
       TOOL_ERROR_FATAL = "tool_error_fatal"
       POLICY_BLOCKED = "policy_blocked"
       LOW_EVIDENCE = "low_evidence"
       PRESENT_LIMIT = "present_limit"

   class ReplanScope(str, Enum):
       EXECUTE = "execute"
       COMPOSE = "compose"
       PRESENT = "present"
       FULL_PIPELINE = "full_pipeline"

   class ReplanDecision(str, Enum):
       AUTO_RETRY = "auto_retry"
       ASK_USER = "ask_user"
       STOP_WITH_GUIDANCE = "stop_with_guidance"

   class ReplanEvent(BaseModel):
       event_id: str
       trigger: ReplanTrigger
       scope: ReplanScope
       decision: ReplanDecision
       patch: Optional[Dict[str, Any]]  # plan patch 등
       expected_impact: str  # 예상 영향 설명
       timestamp: datetime

   class ReplanEngine:
       def evaluate_triggers(self, stage_output: StageOutput) -> List[ReplanTrigger]
       def determine_scope(self, trigger: ReplanTrigger) -> ReplanScope
       def make_decision(self, triggers: List[ReplanTrigger], replan_count: int) -> ReplanDecision
       def check_limits(self, replan_count: int, internal_retry_count: int) -> bool
       def create_replan_event(self, ...) -> ReplanEvent
   ```

2. **Policy Asset 확장** (Control Loop 제어)
   ```python
   class ReplanPolicy(BaseModel):
       max_replans: int = 3  # Policy로 제어
       max_internal_retries: int = 2
       trigger_sensitivities: Dict[str, float]  # trigger별 민감도
       scope_rules: Dict[str, ReplanScope]  # trigger별 기본 scope
   ```

3. **Runner에 Control Loop 통합**
   - 각 Stage 실행 후 Replan Engine 호출
   - ReplanEvent 생성 및 trace에 `replan_events[]`로 저장
   - max_replans, max_internal_retries 강제
   - 사용자 Rerun(auto_retry/ask_user)과 동일 루프에서 처리

4. **Action Cards 확장** (OPS UI)
   - 자동 Replan 발생 시 Replan reason 카드 (트리거/스코프/결정) 표시
   - Timeline에서 auto_retry와 ask_user(rerun)를 시각적으로 구분
   - Action Card에 trigger/scope/선택지/예상 영향 표시

5. **Regression 연계**
   - Golden Query 실행 결과 비교 시 replans 변화 포함
   - Replan 횟수, trigger 종류, decision 종류가 1급 지표로 비교

#### 예상 작업량
- 백엔드: 6-7일
- 프론트엔드: 3-4일
- 테스트: 3일
- **총계: 12-14일**

---

### 5.5 Phase 5: Asset Swap Testability (P2 - 중간 우선순위)

#### 목표
Stage별 Asset override 테스트 + Isolated Stage Test + 배포 안전장치

#### Canvas DoD 요구 (8.3, 6A.2, 6A.3, 8.2-7)
- Asset Swap Test 실행 (Full pipeline override, Isolated stage test)
- Test Execution Context (test_mode, asset_overrides, baseline_trace_id)
- 배포 안전장치 (published 우선 로딩 + draft 존재, regression 통과/실패 기준, rollback 기준)
- Admin Assets에서 asset override로 test run 실행 진입점

#### 작업 항목
1. **Test Context 정의**
   ```python
   class TestContext(BaseModel):
       test_mode: bool = True
       asset_overrides: Dict[str, str]  # stage_name -> asset_id
       baseline_trace_id: Optional[str] = None
       test_type: Literal["full_pipeline", "isolated_stage"] = "full_pipeline"
       target_stage: Optional[str] = None  # isolated stage일 때
   ```

2. **Test Runner 구현**
   - Full pipeline override: 전체 pipeline 실행하되 특정 Stage의 Asset만 override
   - Isolated stage test: 이전 Stage output을 입력으로 특정 Stage만 단독 실행
   - Asset 우선순위: test overrides > published > draft (실패 시 fallback)
   - 모든 테스트 실행도 Execution Trace로 저장

3. **Admin Assets UI 확장** (Pipeline Lens)
   - Asset 상세에 **Run Test(Override)** 버튼: 특정 stage asset 교체 후 실행 진입
   - Preview 패널: Query/Mapping/Screen 각각 결과 미리보기
   - Test 실행 결과 trace로 저장 → Inspector/Regression에서 다룰 수 있음

4. **OPS UI 추가** (Test Mode)
   - Test Mode 토글 + Override Drawer
   - 현재 실행에 사용할 asset overrides 선택 (stage별 드롭다운)
   - baseline_trace 선택 후 diff 보기

5. **배포 안전장치 구현**
   - Asset 로딩 우선순위: published 우선, draft 존재 시 warning 표시
   - Regression 통과/실패 기준:
     ```python
     class RegressionCriteria(BaseModel):
         max_replan_increase: float = 1.5  # replan 횟수 50% 증가까지 허용
         max_empty_rate: float = 0.1  # empty result rate 10%까지 허용
         min_reference_coverage: float = 0.8  # reference coverage 80% 이상
     ```
   - Rollback 기준: regression 실패 시 자동 rollback 요청 + 수동 승인 필요

6. **Diff View 확장**
   - baseline_trace와 현재 실행 결과의 stage별 diff
   - Replan 수 변화, empty/warn 변화, references 변화 시각화

#### 예상 작업량
- 백엔드: 5-6일
- 프론트엔드: 4-5일
- 테스트: 3일
- **총계: 12-14일**

---

## 4. 총 작업량 및 일정 (Total Effort & Schedule)

| Phase | 우선순위 | 백엔드 | 프론트엔드 | 테스트 | 총계 | 누적 |
|-------|----------|---------|-----------|--------|------|------|
| Phase 1 | P0 | 3-4일 | 1일 | 2일 | 6-7일 | 6-7일 |
| Phase 2 | P1 | 4-5일 | 3-4일 | 2일 | 9-11일 | 15-18일 |
| Phase 3 | P1 | 5-6일 | 4-5일 | 3일 | 12-14일 | 27-32일 |
| Phase 4 | P2 | 6-7일 | 3-4일 | 3일 | 12-14일 | 39-46일 |
| Phase 5 | P2 | 5-6일 | 4-5일 | 3일 | 12-14일 | 51-60일 |

### 최소 기능 완성 (MVP)
- **Phase 1 + Phase 2**: 15-18일
  - Route+Plan 분기
  - Stage In/Out 저장
  - Inspector 기본 기능

### 범용 오케스트레이션 완성 (Full)
- **Phase 1~5**: 51-60일 (약 2.5~3개월)

---

## 5. 위험 요소 및 완화책 (Risks & Mitigations)

### 5.1 기술적 위험
1. **Stage 분리 시 성능 저하**
   - 완화책: 병렬화 가능성 검토, lazy loading
2. **Replan 무한 루프**
   - 완화책: strict limit enforcement, timeout
3. **Asset Swap으로 인한 trace 용량 증가**
   - 완화책: trace retention policy, pruning

### 5.2 일정 위험
1. **요구사항 변경**
   - 완화책: Canvas를 Source of Truth로 고정, 변경 시 Canvas 우선 업데이트
2. **리소스 부족**
   - 완화책: Phase별 우선순위 명확화, P0/P1 먼저 완성

### 5.3 품질 위험
1. **테스트 커버리지 부족**
   - 완화책: 각 Phase마다 테스트 의무화, E2E 테스트 추가
2. **기존 기능 회귀**
   - 완화책: Regression Watch 강화, Golden Query 확보

---

## 6. 결론 (Conclusion)

### 6.1 현재 상태
- CI 전용 오케스트레이션은 **안정적으로 구현됨**
- 하지만 범용 오케스트레이션 요구사항은 **약 35%만 구현됨**

### 6.2 우선순위
1. **Phase 1 (P0)**: Route+Plan 분기 - 없으면 범용성 확보 불가
2. **Phase 2 (P1)**: Stage In/Out - 관측 가능성 및 테스트 기반
3. **Phase 3 (P1)**: Asset 범용화 - 사용자 중심 구성 가능

### 6.3 다음 단계
1. Phase 1부터 시작하여 1주 내에 Route+Plan 분기 완성
2. Phase 2와 병행하여 Stage In/Out 구조화
3. 각 Phase 완료 시마다 Canvas와 비교 검증

---

**작성자**: AI Agent  
**승인자**: [승인 필요]  
**버전**: 1.0
