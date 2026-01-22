# OPS Orchestration Core Concepts – Baseline Canvas

## 개요 (Overview)

이 캔버스는 **Tobit SPA AI의 범용 질의 + 오케스트레이션 시스템**을 설계·구현·운영하기 위한 최상위 개념 정의 문서이다.

본 문서는 다음을 명확히 고정한다.

- 사용자 질의를 **단일 LLM 호출**로 분기·계획하는 방식 (Direct / Orchestration / Reject)
- 데이터·문서·그래프를 통합 처리하는 **오케스트레이션 파이프라인 구조**
- 재질의(Replan/Rerun)를 단계가 아닌 **제어 루프(Control Loop)** 로 다루는 원칙
- 고객사가 **UI에서 설정만으로 시스템을 운용**하기 위한 Asset 모델
- 모든 실행을 추적·분석·회귀 검증하기 위한 Observability 기준

이 캔버스는 *설계의 기준점(single source of truth)* 이며, 이후 논의에서는 **새 개념을 추가하기보다 기존 항목을 수정·확장**하는 방식을 따른다.

---

## 목차 (Table of Contents)

1. Query Handling Model
2. Orchestration Pipeline
3. Control Loop (Replan / Rerun)
4. Asset Model (UI Configurable)
5. Pipeline – Asset Binding
6. Execution Trace & Observability
7. Design Principles

---

# OPS Orchestration Core Concepts – Baseline Canvas

> **Purpose** 이 문서는 Tobit SPA AI의 핵심 오케스트레이션 개념을 고정하기 위한 **Baseline Canvas**이다. 이후 모든 아키텍처, UI, 구현 논의는 이 캔버스를 기준으로 수정·확장한다. (대화 중 변경이 필요하면 이 문서를 직접 갱신한다)

---

## 1. Query Handling Model

### 1.1 Single-Call Route + Plan

모든 사용자 질의는 **단일 LLM 호출**에서 다음 중 하나로 분기된다.

- **DirectAnswer**: 데이터 조회 없이 즉시 답변
- **OrchestrationPlan**: 데이터/문서/그래프를 사용하는 실행 계획
- **Reject**: 정책 기반 거절

이 판단은 규칙이 아니라 **LLM 출력 계약**으로 강제된다.

#### 1.1.1 Route+Plan 출력 계약(PlanOutput)

- 출력은 항상 `kind ∈ {direct, plan, reject}` 중 하나이며, **kind와 payload 일관성**을 Validator가 강제한다.
- **DirectAnswer**는 `answer_text + confidence`를 포함하며, 근거를 다음처럼 분리한다.
  - `attributions[]`: 내부 근거(정책/규칙/시스템 지식/캐시 히트 등)
  - `references[]`: 외부 근거(캐시된 이전 조회 결과 등 선택)
- **Reject**는 `reason + (policy_id 등)` 및 `attributions[]`(거부 근거)를 포함한다.
- **OrchestrationPlan**은 기존 Plan 모델(steps 등)을 포함한다.

> 원칙: Direct/Reject도 **Trace에 남고**, (가능하면) 근거(attributions/references)를 남겨 Inspector에서 관측 가능해야 한다.

---

## 2. Orchestration Pipeline

### 2.1 Pipeline Stages (고정)

```
ROUTE+PLAN → VALIDATE → EXECUTE → COMPOSE → PRESENT
```

- **ROUTE+PLAN**

  - 질문 해석 + 처리 경로 결정 + 실행 계획 생성
  - DirectAnswer / OrchestrationPlan / Reject 중 하나를 반드시 반환

- **VALIDATE**

  - 정책, 스키마, Tool 계약 검증

- **EXECUTE**

  - Plan의 step을 deterministic tool로 실행
  - DirectAnswer의 경우 생략됨

- **COMPOSE**

  - Tool 결과를 Answer Block 구조로 조합

- **PRESENT**

  - Screen 정의에 따라 **UI 출력 확정(ui\_model 생성 포함)**
  - Frontend는 ui\_model을 **그대로 렌더링만** 한다

#### 2.1.1 Stage Naming Convention

- 내부/API/Trace 표준 stage key: `snake_case` (`route_plan, validate, execute, compose, present`)
- UI 표기: 사람이 읽기 좋은 표시명(예: `ROUTE+PLAN`)으로 변환하되, **백엔드/Trace에는 snake\_case만 저장**한다.

---

## 3. Control Loop (Replan / Rerun)

### 3.0 Control Loop는 어디에 위치하는가 (중요)

- Control Loop는 **파이프라인의 한 단계가 아니라**, 파이프라인 실행기를 감싸는 **Orchestrator Runtime의 공통 메커니즘**이다.
- 다만, Control Loop의 동작(트리거/스코프/한도/사용자 액션)은 **Pipeline(orch.v1) 정의의 일부로 함께 고정**되어야 한다.
  - 즉, 구현 위치는 Runtime이지만, **정책/규칙/허용 범위는 Pipeline Spec에 포함**된다.

정리하면:

- **Where (구현 위치)**: Orchestrator Runtime (Runner/Engine)
- **What (규칙/한도/UX)**: Pipeline Spec + Policy Asset

---

### 3.1 Control Loop 정의

Replan/Rerun은 파이프라인 단계가 아니라 **제어 루프(Control Loop)** 이다.

- **REPLAN**: 시스템 자동 보정/재시도
- **RERUN**: 사용자 선택 기반 재실행

### 3.2 Replan Scope (되돌림 위치)

- `EXECUTE`: 데이터 재조회 필요
- `COMPOSE`: 조합/요약 개선
- `PRESENT`: 표현/레이아웃 조정

### 3.3 Replan Trigger (대표)

- SLOT\_MISSING
- EMPTY\_RESULT
- TOOL\_ERROR\_RETRYABLE / TOOL\_ERROR\_FATAL
- POLICY\_BLOCKED
- LOW\_EVIDENCE
- PRESENT\_LIMIT

> 표기 원칙: 내부 enum 값은 `snake_case`(예: `tool_error_retryable`)를 사용하고, UI는 표시만 UPPER로 보여줄 수 있다.

### 3.4 Replan Limits

- `max_replans`: 2\~3 (Policy로 제어)
- `max_internal_retries`: 1\~2

### 3.5 Control Loop와 Pipeline 실행의 결합 방식

Pipeline 실행은 아래처럼 **stage 실행 사이사이에** Control Loop가 개입할 수 있다.

- 각 stage는 `StageOutput`에 **diagnostics(empty/warn/error)** 와 **gaps**(가능하면)를 남긴다.
- Orchestrator Runtime은 이를 바탕으로 `ReplanEvent(trigger, scope, patch, decision)`를 생성한다.
- decision에 따라 다음 중 하나를 수행한다.
  - `auto_retry` (REPLAN)
  - `ask_user` (Action Card 생성 후 RERUN 대기)
  - `stop_with_guidance` (정책/한도 초과)

> 이 결합 방식 때문에 Control Loop는 **Pipeline 정의에 포함되되**, 구현은 Runtime에서 공통 처리하는 구조가 된다.

### 3.6 Trigger Normalization (런타임 안전)

- Trigger 문자열은 **반드시 정규화 함수**를 거쳐 enum으로 파싱한다.
  - 예: `TOOL_ERROR_RETRYABLE`, `tool-error-retryable`, `tool error retryable` → `tool_error_retryable`
- 파싱 실패 시 런타임 예외 대신 `unknown`으로 폴백하여 Trace에 남기고, 기본 decision으로 처리한다.

### 3.7 Replan Patch Diff 구조 (Inspector/UI 직접 렌더링)

- ReplanEvent의 `patch`는 임의 dict가 아니라 **before/after diff 구조**를 표준으로 한다.
  - `patch.before`: 패치 적용 전 plan 상태
  - `patch.after`: 패치 적용 후 plan 상태
- Inspector는 이 diff를 그대로 렌더링(Inline Diff)할 수 있어야 한다.

---

## 4. Asset Model (UI Configurable)

### 4.1 Config Assets (UI에서 설정)

1. **Source** – 데이터 소스 시스템
2. **SchemaCatalog** – 엔티티/테이블/문서/그래프 메타
3. **Query** – Query Template (SQL/Cypher/Vector/API)
4. **Mapping** – ResultSet → Block 변환 규칙
5. **Policy** – 제한, 접근, 재질의 규칙
6. **Prompt** – Route+Plan / Compose용
7. **Screen** – Answer UI 구성
8. **ResolverConfig** (권장) – 엔티티/별칭 매칭 규칙

#### 4.1.1 Secret Handling (보안 원칙)

- Source 연결 정보 등 민감 정보(비밀번호/API 키)는 Asset(spec\_json)에 **직접 저장하지 않는다**.
- Asset에는 `secret_key_ref`(Vault/Secret Manager/env 참조)만 저장한다.
- UI는 secret 값을 표시하지 않고 **등록/교체만** 제공한다.

#### 4.1.2 SchemaCatalog Scan Support (MVP 기준)

- 엔진별 자동 스캔 지원 수준을 명시한다.
  - FULL: Postgres/Timescale (`information_schema` 기반)
  - LIMITED: Neo4j (labels/properties 제한)
  - MANUAL: Vector/API (수동 등록)
- 스캔 불가 엔진은 UI에서 “수동 등록 필요”로 안내한다.

### 4.2 Runtime Contracts (읽기 전용)

9. **ToolContracts** – ToolResult / Reference 계약
10. **BlockContracts** (선택) – Block 스키마

---

## 5. Pipeline – Asset Binding

```
[ROUTE+PLAN] Prompts, Policies, SchemaCatalog
[VALIDATE]   Policies, ToolContracts
[EXECUTE]    Queries, Sources
[COMPOSE]    Mappings, (Compose Prompts optional)
[PRESENT]    Screens
[CONTROL]    Policies (Replan/Rerun)
```

---

## 6. Execution Trace & Observability

## 6A. Pipeline Testability & In/Out Inspection (중요)

본 시스템은 **각 파이프라인 단계에서 Asset을 교체/변경하며 테스트**할 수 있어야 하며, 각 단계의 **입력(In) / 출력(Out)** 이 명확히 관측 가능해야 한다. 이는 단순 디버깅을 넘어, *설정 기반 시스템의 품질을 보장하는 핵심 능력*이다.

### 6A.1 Stage-level In / Out Contract

모든 파이프라인 단계는 아래 형태의 계약을 가진다.

- **Stage Input**

  - 적용된 Asset 목록 (id + version)
  - 이전 단계 Output
  - Control Context (replan scope, retry count 등)

- **Stage Output**

  - 표준화된 결과 구조 (Plan / ToolResult / Blocks 등)
  - Diagnostics (warnings, empty flags, counts)
  - References (항상 존재)

이 In/Out은 **Execution Trace에 반드시 저장**되어 Inspector에서 확인 가능해야 한다.

#### 6A.1.1 Null 금지 & 기본값 규칙

- `references`, `warnings`, `errors`, `counts` 등 컬렉션 필드는 **누락/NULL 대신 빈 배열·빈 객체 기본값**을 사용한다.
- Stage별 `result`는 프론트가 렌더링 가능한 **필수 키 기본값**을 보장해야 한다(예: `execute.tool_results=[]`, `compose.blocks=[]`, `present.ui_model={}`).

---

### 6A.2 Asset Swap Test (설정 기반 테스트)

사용자는 UI에서 **특정 Stage에 바인딩된 Asset을 교체하여 테스트 실행**할 수 있어야 한다.

예시:

- Prompt A → Prompt B 로 교체 후 ROUTE+PLAN 결과 비교
- Query v1 → Query v2 로 교체 후 EXECUTE 결과 비교
- Mapping 변경 후 COMPOSE Block 구조 비교
- Screen 변경 후 PRESENT 렌더링 비교

이 테스트는 다음 모드로 실행될 수 있다.

- **Isolated Stage Test**

  - 이전 단계 Output을 입력으로 주고, 특정 Stage만 단독 실행

- **Full Pipeline Test**

  - 전체 파이프라인을 실행하되, 특정 Stage의 Asset만 override

---

### 6A.3 Test Execution Context

테스트 실행 시 다음 Context가 명시적으로 존재한다.

- `test_mode: true`
- `asset_overrides`: { stage → asset\_id }
- `baseline_trace_id` (선택)

모든 테스트 실행 역시 **Execution Trace로 저장**되며, 기존 실행과 동일하게 Inspector/Regression에서 다룰 수 있다.

---

### 6A.4 Inspector에서의 In / Out 확인 방식

Inspector UI는 Stage별로 다음을 제공해야 한다.

- **Stage Input Panel**

  - 사용된 Asset 목록
  - 주요 입력 파라미터 요약

- **Stage Output Panel**

  - 결과 구조 요약 (Plan / ResultSet / Blocks)
  - Empty / Warning / Error 표시

- **Diff View (선택)**

  - baseline\_trace와 현재 실행 결과의 차이 비교

---

### 6A.5 Regression과의 연결

Asset 변경 테스트는 Regression으로 자연스럽게 연결된다.

- 동일 질문 + 다른 Asset 조합 → Trace 비교
- 변경 전/후 Replan 횟수, Empty rate, Reference 수 비교
- 품질 저하 탐지 시 Rollback 판단 근거 제공

---

### 6A.6 왜 이 구조가 중요한가

- 이 시스템은 **코드가 아니라 설정(Asset)으로 동작**한다.
- 따라서 설정 변경이 곧 "배포"이며,
- 배포 전/후 결과를 **파이프라인 단계 단위로 검증**할 수 있어야 한다.

Pipeline Testability는 선택 기능이 아니라, **설정 기반 AI 시스템의 필수 요건**이다.

---

## 6. Execution Trace & Observability

### 6.1 Execution Trace (저장)

모든 요청은 Execution Trace를 남긴다.

- route: direct / orch / reject
- pipeline\_version
- applied\_assets
- stage 결과
- replan\_events (trigger, scope, patch)
- references (항상 존재)
- (선택) attributions (Direct/Reject 및 시스템 근거)
- (선택) cache\_hit/cache\_key (Route+Plan 캐시 사용 시)

### 6.2 Inspector

- 단계별 Timeline
- Replan 이벤트 1급 객체 표시

### 6.3 Regression

- Golden Query 기반 회귀 비교
- Replan 변화 포함

### 6.4 Evaluation

- Direct vs Orchestrated 비율
- Replan rate
- Empty result rate
- Reference coverage

---

## 7. Design Principles (고정 원칙)

1. LLM 호출은 최소화하되, 판단과 답변은 LLM이 수행한다.
2. 모든 응답은 Trace와 Reference를 남긴다.
3. 코드 수정 없이 UI 설정으로 동작해야 한다.
4. Replan은 무한 루프를 허용하지 않는다.
5. Direct Answer도 관측 가능해야 한다.

---

> 이 문서는 이후 논의의 기준점이며, 변경 시 항상 이 캔버스를 갱신한다.

---

## 8. 범용 오케스트레이션 Definition of Done (DoD)

> **중요:** 이 캔버스는 ‘개념 고정’ 문서이므로, 캔버스의 구조/원칙을 구현하는 것은 **필요조건(necessary condition)** 이다. 하지만 범용 오케스트레이션으로 “완성”되었다고 말하려면, 아래 DoD(운영 요구사항/관측/테스트/자동 루프/분기/연계 UI)를 만족하는 **충분조건(sufficient condition)** 까지 구현되어야 한다.

### 8.0 DoD가 커버하는 핵심 범용화 요구

- **자동 Replan(Control Loop 자동화)**: 사용자 rerun만이 아니라 auto\_retry/stop/ask\_user까지 엔진화
- **Stage-level In/Out Trace**: plan/tool\_calls/blocks 중심이 아니라 stage 입력·출력 구조 저장
- **Direct / Orchestration / Reject 분기**: CI 전용이 아니라 단일 호출 기반 분기 + trace 수집
- **범용 Asset Model 확장**: Prompt/Policy/Mapping/Query/Screen뿐 아니라 Source/Schema/Resolver까지 UI 설정
- **Inspector/Regression 연계**: replan/patch/scope, asset 변경 영향이 1급 객체로 비교/검증

> 아래 DoD 항목을 만족해야 ‘범용 오케스트레이션’으로 간주한다.

### 8.1 Runtime 기능 DoD

1. **Stage In/Out 저장**

- ROUTE+PLAN/VALIDATE/EXECUTE/COMPOSE/PRESENT 각각에 대해
  - StageInput(assets + params + prev output)
  - StageOutput(result + diagnostics + references)
  - timings/spans 가 trace에 저장된다.

2. **Control Loop 엔진화**

- trigger 분류(EMPTY\_RESULT/SLOT\_MISSING/…)
- scope 결정(EXECUTE/COMPOSE/PRESENT)
- decision(auto\_retry/ask\_user/stop\_with\_guidance)
- max\_replans/max\_retries 강제
- ReplanEvent가 trace에 1급 객체로 저장

3. **Route+Plan 출력 계약 강제**

- LLM 출력은 DirectAnswer / OrchestrationPlan / Reject 중 하나
- Validator가 kind + 최소 필드를 검증
- DirectAnswer도 trace/references를 남김

4. **ToolResult / Reference 계약 강제**

- 모든 tool 실행은 ToolResult{status,result\_sets,references[]}를 반환
- references는 항상 존재(빈 배열 포함)
- 누락 시 warning/partial 또는 정책 기반 실패로 승격

---

### 8.2 UI 기능 DoD

5. **OPS: Execution Summary + Timeline + Action Cards**

- route, ops\_mode, plan\_mode, used tools, replans, warnings, references count
- Timeline에서 stage별 In/Out 접근
- Action Card에 trigger/scope/선택지/예상 영향 표시

6. **Inspector: Stage별 In/Out + Replan 1급 객체**

- ReplanEvent 목록(이유/스코프/patch diff)
- stage 전후 비교(Diff View) 최소 지원

7. **Admin Assets: Pipeline Lens + Usage**

- asset의 bound\_stage, used\_by, last\_used, deps
- asset override로 test run 실행 진입점

8. **Regression: Asset 변경 영향 비교**

- golden query 실행 결과 비교
- replans 변화, empty/warn 변화, references 변화가 1급 지표

---

### 8.3 Testability DoD

9. **Asset Swap Test 실행**

- Full pipeline override
- Isolated stage test(이전 stage output을 입력으로)
- baseline\_trace\_id와 비교 가능

10. **배포 안전장치**

- published 우선 로딩 + draft 존재
- regression 통과/실패 기준(최소 지표)
- rollback 기준 정의

---

### 8.4 범용성 DoD (데이터 통합)

11. **멀티 소스/멀티 테이블/문서 통합**

- QueryTemplate로 파티션/다중 테이블을 흡수
- doc/vector 검색도 동일한 QueryTemplate/ToolResult/Reference 계약으로 통합
- compose에서 서로 다른 ResultSet을 비교/조합 가능

12. **스키마/엔티티 변화에 대한 내성**

- SchemaCatalog 변경이 plan/validate 단계에 반영
- entity resolver로 식별자 모호성 처리(ask\_user 포함)

---

## 9. Implementation Notes & Known Gaps (현 구현 대비)

> 목적: Canvas/DoD와 **현재 코드 구현 사이의 불일치(갭)** 를 명시적으로 기록하여, 이후 작업이 “개념 논쟁”이 아니라 “갭 해소”로 수렴되도록 한다.

### 9.1 Query Handling Model 갭

- 현재 `/ops/ci/ask`는 **planner → validator → runner**를 항상 수행하며, **CI 전용 오케스트레이션 흐름**이다.
- Canvas의 `DirectAnswer / Reject` 경로는 현 코드에 명시적으로 존재하지 않는다.
- planner는 LLM 실패 시 **규칙 기반 fallback 파싱**을 수행한다.

➡️ 목표 갭: ROUTE+PLAN 단계에서 **단일 출력 계약(kind=direct|plan|reject)** 을 강제하고, direct/reject도 trace 대상으로 포함.

### 9.2 Pipeline Stage 분리 갭

- 현 구조에서 **EXECUTE + COMPOSE가 runner 내부에 혼재**되어 있다.
- PRESENT는 backend stage라기보다 **프론트(UI Screen Renderer) 렌더링**에 위임된다.

➡️ 목표 갭: Stage-level In/Out 저장 관점에서, runner 내부 혼재 구조라도 **논리적 StageOutput(ExecuteOutput / ComposeOutput / PresentOutput)을 trace에 분리 저장**하도록 보완.

### 9.3 Control Loop 갭

- 사용자 `rerun`(plan patch 기반)은 존재하나,
  - **자동 Replan(auto\_retry)**
  - trigger/scope/limit 엔진화
  - ReplanEvent 1급 객체 저장 는 구현되어 있지 않다.

➡️ 목표 갭: Runtime 공통 Control Loop를 도입하고, rerun/auto\_retry를 동일 루프에서 처리.

### 9.4 Asset Model 갭

- Prompt/Policy/Mapping/Query/Screen은 Asset Registry로 존재.
- Source / SchemaCatalog / ResolverConfig는 전용 asset 타입이 없다.
- ToolContracts/BlockContracts는 코드 스키마로 존재하나 **asset 형태(UI 편집/버전관리)** 는 아니다.

➡️ 목표 갭: Source/Schema/Resolver를 UI 관리 asset으로 추가(또는 최소한 읽기 전용 Catalog로 시작).

### 9.5 Trace / References 갭

- trace는 plan\_raw/validated, tool\_calls, blocks 중심.
- **Stage In/Out 분리 저장이 없다.**
- references는 blocks에서 추출되며, **references block이 없으면 빈 배열**이 될 수 있다.

➡️ 목표 갭: ToolResult/Reference 계약을 강제하여 references를 항상 생성/저장(빈 배열 포함, null 금지).

### 9.6 Observability/Regression 갭

- Inspector/Regression/Observability의 기본 틀은 존재.
- 하지만 Canvas에서 요구하는:
  - route(direct/orch/reject) 비율
  - replan rate
  - empty result rate
  - stage별 diff 같은 지표/표현은 완결되지 않았다.

➡️ 목표 갭: DoD 8.x 항목 기준으로 지표/표현을 보강.

---

## 10. Source→Schema→Query→Answer: 사용자 중심 구성(필수)

> 목적: 범용 오케스트레이션은 파이프라인만으로 완성되지 않는다. **사람(사용자)이 데이터 시작점(Source)부터 스키마/쿼리/화면까지** 무리 없이 구성·검증·배포할 수 있어야 한다. 이 섹션은 “사용자 관점의 최소 UX 흐름”을 고정한다.

### 10.1 사용자 작업 흐름 (Happy Path)

1. **Source 연결** (Data/ Admin)

- 엔진 선택(Postgres/Timescale/Neo4j/Vector/API)
- 연결 정보/권한/환경(real/mock)
- 연결 테스트(health check) + 권한/리밋 확인

2. **SchemaCatalog 작성/동기화**

- 테이블/측정치/그래프/문서 컬렉션을 “엔티티/관계/측정치” 관점으로 등록
- (선택) 스키마 자동 스캔 → 사람이 의미(엔티티/시간/단위/키)를 보강
- 엔티티 키/조인 키/시간 컬럼(또는 time 의미) 명시

3. **ResolverConfig 설정(식별자/별칭/모호성 정책)**

- 예: “가스터빈 1호기=GT-01” 별칭 묶음
- 모호성 시 ask\_user(top-k 후보)

4. **QueryTemplate 작성(결정적 실행) + Preview**

- SQL/Cypher/Vector/API 템플릿 등록
- 입력 파라미터 정의(entity\_id/time\_range/metric\_name…)
- Preview 실행(샘플 파라미터로 결과 확인)
- Output schema + Reference 생성 규칙 확인

5. **Mapping 작성(결과→Block) + Preview**

- table/chart/graph/doc\_link 변환
- row/point 제한 정책과 연계

6. **Screen 구성(PRESENT) + Preview**

- blocks 배치/접기/refs 표시 규칙

7. **OPS에서 통합 질문으로 End-to-End 테스트**

- baseline\_trace 저장
- Regression에 golden으로 등록(선택)

---

### 10.2 “사용자에게 보이는” 핵심 UI 컴포넌트(고정)

- **Source Profile Editor**: 엔진/연결/권한/리밋/테스트
- **Schema Catalog Builder**: 엔티티/관계/측정치/문서 카탈로그 편집 + 자동 스캔 보조
- **Query Template Builder**: 입력/쿼리 본문/출력 스키마/Preview
- **Mapping Builder**: ResultSet→Block 규칙 + Preview
- **Screen Builder/Renderer**: Screen 정의 + 실제 렌더 미리보기
- **Asset Binding Lens**: 각 asset이 pipeline stage 어디에 연결되는지 표시
- **Test Runner (Override Run)**: asset\_overrides로 실행 + In/Out + Diff

> 원칙: 새 페이지를 무한히 늘리지 않는다. 기존 `/admin/assets`, `/admin/inspector`, `/admin/regression`, `/ops`, `/ui/screens`, `/data` 메뉴에 **탭/드로어/모달/서브패널 형태로 기능을 결합**하여 재활용한다.

---

## 11. UI & API Delta (최소 변경으로 빈틈없이)

> 목적: 이미 구현된 화면/코드를 재활용하면서도, 범용화에 필요한 “Source/Schema 시작점 + Asset 조합/테스트 + In/Out 관측”을 빠짐없이 추가한다.

### 11.0 v2.2 UX 핵심 원칙 (Guided Flow + 목적 기반 UI + 조치 연결)

#### 11.0.1 Guided Flow: Source → Screen 강제 연결

- 사용자가 막히지 않도록 **각 빌더 화면에 Preview + Next Step 버튼**을 필수로 둔다.
- **Source → Catalog → Query → Mapping → Screen** 순서로, “다음 단계로 이동”을 UI가 안내/강제한다.

필수 버튼/프리뷰(최소):

- Source Editor: **Test Connection** → 상태 판정 + **[Scan to Catalog]**
- Catalog Builder: Entity/Column/Relationship 상세 + **[Create Query for Entity]**
- Query Builder: 샘플 파라미터 실행 **Preview** + **[Create Mapping from Result]**
- Mapping Builder: ResultSet→Blocks **Preview** + **[Attach to Screen] / [Preview in Screen]**
- Screen Builder: 렌더링 **Preview + References 토글** + **[Publish] / [Test in OPS]**

#### 11.0.2 Test Mode: 목적 기반 Override Preset + 영향 범위 표시

- Stage 단위 선택은 사용자가 영향 범위를 모르므로, **목적 기반 프리셋**을 제공한다.
  - 예: “PLAN 프롬프트만 바꾸기(ROUTE+PLAN/VALIDATE 영향)”, “EXECUTE Query만 바꾸기(EXECUTE/COMPOSE 영향)” 등
- 선택 즉시 **Affected Stages Preview**로 rerun/changed/affected를 시각화한다.
- Baseline Trace 선택 후 **Run Test** 실행(자동 diff 연계).

#### 11.0.3 Isolated Stage Test: 입력 trace 선택 + 자동 추천 + 즉시 diff

- 단독 실행 UI는 반드시 다음을 지원한다.
  - Source Trace 선택(⚡ 최근 성공 trace 자동 추천)
  - Input Stage 선택(기본: target stage의 바로 이전 stage output)
  - 입력 요약/전체 JSON 보기
  - 실행 후 baseline(동일 trace의 원래 결과)과 **즉시 diff**(추가/삭제/변경 요약 + 상세 보기)

#### 11.0.4 OPS 결과 화면: Inline Diff (vs baseline)

- baseline 비교는 Inspector로 이동하지 않고, OPS 결과 상단에 **Stage별 diff 요약**을 즉시 표시한다.
- Overall judgment(improved/regressed/unchanged) + 핵심 지표(시간/rows/blocks/refs/replans) 변화 제공.

#### 11.0.5 Inspector는 “로그 뷰어”가 아니라 “조치 허브(Action Hub)”다

- Trace Detail에서 항상 **Action 버튼으로 조치 연결**을 제공한다.
  - [Run with Override] (OPS Test Mode로 이동, baseline 자동 설정)
  - [Run Isolated Test] (해당 stage input으로 단독 실행)
  - ReplanEvent의 patch: [Copy Patch] [Apply Patch to New Test] [View Retry Result]
- Regression 화면에서도 failing stage로 **점프(Deep-link)** 하는 액션을 제공한다.

---

## 11. UI & API Delta (최소 변경으로 빈틈없이)

> 목적: 이미 구현된 화면/코드를 재활용하면서도, 범용화에 필요한 “Source/Schema 시작점 + Asset 조합/테스트 + In/Out 관측”을 빠짐없이 추가한다.

### 11.1 UI 변화 (기존 화면 재활용 중심)

#### 11.1.0 UI 목록 (메뉴/페이지/핵심 컴포넌트)

> 목표: “어디서 무엇을 할 수 있는지”를 한 번에 파악 가능하도록, UI 표면(페이지)과 공통 컴포넌트를 고정한다.

**(1) OPS (/ops)**

- **OPS Query Interface**
  - History Sidebar (최근 질의 + route/status + 필터)
  - Query Panel (mode + question + submit)
  - **Summary Strip** (route/plan\_mode/tools/replans/warnings/refs)
  - **Tabs**: Timeline / Blocks / Actions / Raw
  - **Test Mode**
    - Test Mode Toggle
    - **Override Drawer** (Preset + Custom + Baseline + Affected Stages + Run Test)
  - **Inline Diff Summary** (baseline 대비 stage별 변화 요약)

**(2) Inspector (/admin/inspector)**

- Trace List (route/replan\_count/status/duration/question)
- Trace Detail (expanded)
  - Stage Pipeline Visualization
  - Stage Input/Output Panel
  - Replans Panel (patch before/after diff)
  - Compare Modal (baseline vs candidate)
  - Quick Actions: Run with Override / Run Isolated Test / Copy Patch

**(3) Admin Assets (/admin/assets)**

- Asset Registry Table
- Asset Detail
  - Pipeline Lens View (stage bindings)
  - Usage Summary (Used By/Deps/Dependents/Last Used)
  - Test Run Entry (Override 실행)
  - Version History / Diff

**(4) Data (/data)**

- Tabs: Sources / Catalog / Resolvers / Explorer
  - Sources: Source Editor + Test Connection + Scan to Catalog
  - Catalog: Schema Tree + Entity Detail + Create Query CTA
  - Resolvers: Alias/Pattern Rules + Test Resolution
  - Explorer(선택): ad-hoc query/preview (권한/리밋 정책 적용)

**(5) Screens (/ui/screens)**

- Screen Builder
  - Screen Preview (blocks/references 토글)
  - Publish / Test in OPS

---

#### 11.1.1 OPS Orchestration UI – Wireframes (v2.2 반영)

##### (A) OPS 메인 화면 (실행 + Timeline + Test Mode)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ OPS Query Interface                                      Test Mode: OFF  │
├──────────────────┬───────────────────────────────────────────────────────┤
│ History Sidebar  │  Summary Strip                                         │
│ ┌──────────────┐ │  ┌─────────────────────────────────────────────────┐  │
│ │ Recent       │ │  │ Route: ORCH | Plan: AUTO | Tools: 3 | Replans: 1 │  │
│ │ Queries      │ │  │ Warnings: 0 | Refs: 5 | Total: 1.2s              │  │
│ │              │ │  └─────────────────────────────────────────────────┘  │
│ │ [Filter…]    │ │                                                       │
│ │ ○ q1 ORCH ✓  │ │  Query Panel                                           │
│ │ ○ q2 DIRECT✓ │ │  ┌─────────────────────────────────────────────────┐  │
│ │ ○ q3 REJECT✗ │ │  │ Mode: [구성][수치][이력][연결][전체]              │  │
│ └──────────────┘ │  │ Question: [______________________________]        │  │
│                  │  │ [Submit]  [Test with Override…]                   │  │
│                  │  └─────────────────────────────────────────────────┘  │
│                  │                                                       │
│                  │  Tabs: [Timeline] [Blocks] [Actions] [Raw]            │
│                  │  ┌─────────────────────────────────────────────────┐  │
│                  │  │                TIMELINE TAB                      │  │
│                  │  │ ┌─ ROUTE+PLAN (120ms) ✓ ───────────────────────┐ │  │
│                  │  │ │ kind: plan | cache_hit: false                 │ │  │
│                  │  │ │ [View Input] [View Output]                     │ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  │ ┌─ VALIDATE (15ms) ✓ ──────────────────────────┐ │  │
│                  │  │ │ policy: plan_budget:v2                        │ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  │ ┌─ EXECUTE (450ms) ⚠ empty_result ─────────────┐ │  │
│                  │  │ │ rows: 0 | refs: 2 | tools: ci.search           │ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  │ ┌─ REPLAN #1 auto_retry ────────────────────────┐ │  │
│                  │  │ │ patch: expand_search false→true                │ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  │ ┌─ EXECUTE (retry) (380ms) ✓ rows:15 refs:5 ────┐ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  │ ┌─ COMPOSE (85ms) ✓ blocks:3 ───────────────────┐ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  │ ┌─ PRESENT (12ms) ✓ screen: default ────────────┐ │  │
│                  │  │ └──────────────────────────────────────────────┘ │  │
│                  │  └─────────────────────────────────────────────────┘  │
└──────────────────┴───────────────────────────────────────────────────────┘
```

##### (B) Test Mode – Override Drawer (목적 기반 프리셋 + 영향 범위)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Test Mode: Override Drawer                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Quick Presets ─────────────────────────────────────────────────────────┐ │
│ │ ○ PLAN 프롬프트만 바꾸기   → Affects: [ROUTE+PLAN][VALIDATE]            │ │
│ │ ○ EXECUTE Query만 바꾸기  → Affects: [EXECUTE][COMPOSE]                │ │
│ │ ○ COMPOSE Mapping만 바꾸기→ Affects: [COMPOSE][PRESENT]                │ │
│ │ ○ PRESENT Screen만 바꾸기 → Affects: [PRESENT]                         │ │
│ │ ● Custom (직접 선택)                                                   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ Custom Override ───────────────────────────────────────────────────────┐ │
│ │ ROUTE+PLAN  Prompt: [ci_planner_v3 ▼] → [ci_planner_v4 (draft)]         │ │
│ │ VALIDATE    Policy: [plan_budget_v2 ▼]                                  │ │
│ │ EXECUTE     Query : [ci_lookup_v5 ▼]   Source: [postgres_main ▼]        │ │
│ │ COMPOSE     Mapping: [graph_rel_v2 ▼] → [graph_rel_v3 (draft)]          │ │
│ │ PRESENT     Screen: [default ▼] → [ops_rich_v2 (draft)]                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ Affected Stages Preview ───────────────────────────────────────────────┐ │
│ │ ROUTE+PLAN ─▶ VALIDATE ─▶ EXECUTE ─▶ COMPOSE ─▶ PRESENT                 │ │
│ │    🔄          ✓(rerun)    ✓(rerun)     🔄         🔄                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ Baseline Trace: [abc123… ▼]   [Run Test]   [Cancel]                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### (C) OPS 결과 – Inline Diff Summary (baseline 대비 즉시 표시)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPS Result (Test Mode + Baseline Comparison)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Quick Diff Summary (vs baseline abc123) ───────────────────────────────┐ │
│ │ Stage       | Baseline  | Current   | Diff                               │ │
│ │ ROUTE+PLAN  | 120ms     | 115ms     | ✓ -5ms                             │ │
│ │ EXECUTE     | 450ms     | 380ms     | ✓ -70ms, rows 15→18 (+3)           │ │
│ │ COMPOSE     | 85ms      | 90ms      | ⚠ +5ms, blocks 3→4 (+1 chart)      │ │
│ │ Replans     | 1         | 0         | ✓ -1 (improved)                    │ │
│ │ Overall: ✅ improved                                                     │ │
│ │ [View Detailed Diff in Inspector]                                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### (D) Stage Card – In/Out 토글 (Timeline/Inspector 공통)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Stage: EXECUTE   Status: OK   Duration: 380ms   Rows: 18   Refs: 5          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Applied Assets: query=ci_lookup:v5 | source=postgres_main:v2                 │
│ Tools: ci.search, graph.expand                                              │
│ [View Input] [View Output] [Run Isolated Test] [Open in Inspector]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### (E) Isolated Stage Test (OPS/Inspector 공통 모달)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Isolated Stage Test                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Target Stage: [COMPOSE ▼]                                                    │
│ Source Trace: [abc123 - "GT-01 상태 조회" (5분 전) ▼] (추천: 최근 성공)     │
│ Input Stage : [EXECUTE output ▼]                                             │
│ Input Preview: tool_results=3 | refs=5 | rows=18  [View Full JSON]           │
│ Override: mapping [graph_rel_v2 ▼] → [graph_rel_v3 (draft)]                  │
│ [Run Isolated Test]                                                         │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Result Diff (baseline vs test)                                               │
│  - blocks: 3 → 4 (+1)                                                       │
│  - references: 5 → 5 (0)                                                    │
│  [View Full Diff]  [Apply v3 to Production]  [Discard]                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 11.2 API 변화 (핵심 필드/엔드포인트)

#### 11.2.0 UI가 반드시 필요한 Trace 응답 필드(강제)

- UI가 방어 코드 없이 렌더링하려면 아래 필드/기본값이 **반드시** 존재해야 한다.
- **Null 금지**: `references, warnings, errors, counts, empty_flags` 등은 누락/NULL 대신 빈 배열·빈 객체 기본값.

필수(요약):

- `trace_id`, `route(direct|orch|reject)`
- `stage_outputs[]`: `stage`, `duration_ms`, `diagnostics{status,counts,empty_flags,warnings,errors}`, `references[]`
- `applied_assets{asset_key→{asset_id,name,version,status}}`
- `replan_events[]`: `trigger,scope,decision,attempt,max_attempts,patch.before/after`
- (선택) `cache_info{cache_hit,cache_key}` (route\_plan 캐시 사용 시)

#### (A) Source/Schema/Resolver 자산 API

- Source CRUD + 연결 테스트 endpoint
- SchemaCatalog CRUD + (선택) 스캔/동기화 endpoint
- ResolverConfig CRUD

#### (B) Preview APIs (빌더 UX 필수)

- Query Preview: 샘플 파라미터 실행(dry\_run 포함)
- Mapping Preview: ResultSet → Blocks 변환
- Screen Preview: Blocks/References → ui\_model(선택: SSR HTML)

#### (C) OPS 실행 요청 확장 (테스트/오버라이드)

- `test_mode: bool`
- `asset_overrides: {stage_or_asset_key: asset_version_or_id}`
- `baseline_trace_id?: string`

#### (D) Isolated Stage Test API (단독 실행)

- 입력 trace + input stage output을 snapshot으로 사용
- 실행 결과에 baseline 대비 diff 요약 포함

#### (E) Trace Diff API (OPS Inline Diff)

- `GET /inspector/traces/{trace_id}/diff?baseline=...`
- stage별 duration/rows/blocks/refs/replans 변화 + overall judgment

#### (F) Run with Override API (Inspector → OPS 연결)

- baseline\_trace 재사용(question null 허용)
- 실행 후 auto\_diff 반환

#### (A) Source/Schema/Resolver 자산 API

- Source CRUD + 연결 테스트 endpoint
- SchemaCatalog CRUD + (선택) 스캔/동기화 endpoint
- ResolverConfig CRUD

#### (B) OPS 실행 요청 확장 (테스트/오버라이드)

- `test_mode: bool`
- `asset_overrides: {stage: asset_id}`
- `baseline_trace_id?: string`

#### (C) Trace 스키마 확장 (Stage In/Out)

- `stage_inputs[]`, `stage_outputs[]`
- `replan_events[]` (trigger/scope/decision/patch)
- `route` (direct/orch/reject)

#### (D) Route+Plan 출력 계약 강제

- LLM 출력 `kind=direct|plan|reject`
- validator가 최소 필드/정책 준수 검증

---

## 12. Reuse-first 원칙 (기존 구현 재활용)

- `/admin/assets` : 자산 편집/배포 + Pipeline Lens + Override Test 진입
- `/ops` : End-to-End 실행 + Action Card + Timeline + Override Drawer
- `/admin/inspector` : Stage In/Out + ReplanEvent + Diff
- `/admin/regression` : Golden 비교 + 변경 영향
- `/ui/screens` : Screen 편집/미리보기
- (보강) `/data` : Sources/Catalog/Resolvers 시작점

> 범용 오케스트레이션은 “백엔드 파이프라인”만이 아니라, 사람이 **Source부터 Answer까지** 구성하고 검증하는 UX가 완성돼야 한다.

---

## 13. Codex Practical Addendum (UI/API 업그레이드 항목)

> 목적: Canvas(10\~12)의 방향을 실제 코드베이스 관점에서 더 구체화한다. 아래 항목은 Codex 리포트의 "UI/API 업그레이드 제안" 중 **반영 가치가 높은 것**을 본 캔버스의 요구사항으로 승격한 것이다.

### 13.1 UI 요구사항 보강

A) **Stage Inspector 확장(Inspector/OPS 공통 패턴)**

- Stage Input/Output 패널: ROUTE+PLAN/VALIDATE/EXECUTE/COMPOSE/PRESENT 별 요약
- Diagnostics 표기: empty/warn/error + gaps
- Diff View: baseline trace와 stage별 diff

B) **Asset Swap Test UI(Override Runner)**

- stage별 asset override 선택 UI (Prompt/Query/Mapping/Screen 등)
- 실행 모드
  - Isolated Stage Test
  - Full Pipeline Test
- 결과는 trace 저장 + baseline 비교 진입

C) **Control Loop UX(자동 Replan vs 사용자 Rerun 구분)**

- 자동 Replan 발생 시: Replan reason 카드(트리거/스코프/결정) 표시
- Timeline에서 auto\_retry와 ask\_user(rerun)를 시각적으로 구분

D) **Asset Registry UX 확장(버전/상태/차이)**

- asset 상태: draft/published/rollback
- diff(버전 간 비교) + 변경 영향 링크(regression/last used)

E) **Observability 대시보드 확장(요약 지표)**

- Direct vs Orchestrated 비율
- Replan rate / Empty result rate / Reference coverage
- Regression 결과 요약 및 추이

### 13.2 API 요구사항 보강

A) **Route/Plan 분기 모델(계약) 추가**

- planner 출력: direct|plan|reject
- reject는 정책 사유 + 재시도 가이드 포함
- direct도 trace/references 기록

B) **Pipeline Stage 구조화(최소는 Trace 구조화부터)**

- stage input/output 표준화 + diagnostics/gaps 기록
- UI 렌더링 안정성을 위해 **Null 금지 + 기본값 강제**

C) **Control Loop 자동화**

- replan trigger/scope/limit 정책
- ReplanEvent 누적 저장
- patch는 **before/after diff 구조**로 저장(Inline Diff 직접 렌더)

D) **Asset Model 확장**

- Source/SchemaCatalog/ResolverConfig CRUD + 바인딩 정보 trace 기록
- Asset Usage Summary(Used By/Deps/Dependents) 제공(Pipeline Lens 지원)

E) **Builder Preview / Testability APIs**

- Query/Mapping/Screen preview endpoints
- Isolated Stage Test endpoint
- Trace Diff endpoint
- Run-with-override endpoint

F) **Policy/Security 일관성**

- policy blocked는 항상 reject/trace로 기록
- Data Explorer allowlist/denylist enforcement 강제
- secret 값은 spec\_json에 저장 금지(참조키만)

A) **Route/Plan 분기 모델(계약) 추가**

- planner 출력: direct|plan|reject
- reject는 정책 사유 + 재시도 가이드 포함
- direct도 trace/references 기록

B) **Pipeline Stage 구조화(최소는 Trace 구조화부터)**

- stage input/output 표준화 + diagnostics/gaps 기록

C) **Control Loop 자동화**

- replan trigger/scope/limit 정책
- ReplanEvent 누적 저장

D) **Asset Model 확장**

- Source/SchemaCatalog/ResolverConfig CRUD + 바인딩 정보 trace 기록

E) **Policy/Security 일관성**

- policy blocked는 항상 reject/trace로 기록
- Data Explorer allowlist/denylist enforcement 강제

