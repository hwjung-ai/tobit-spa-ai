# 📘 OPS 오케스트레이션 - 사용자 가이드

> **Last Updated**: 2026-02-15
> **Status**: ✅ **Production Ready**
> **Security Level**: HIGH (P0-4 Query Safety Enforced)

## 문서의 성격

이 가이드는 OPS Orchestration 시스템을 **학습하고 운영하기 위한 완전한 실행 가이드**입니다.

## 테스트 결과 요약

| Category | Success | Total | Accuracy |
|----------|---------|-------|----------|
| Config (Relation) | 25      | 25    | 100%     |
| Graph       | 24      | 24    | 100%     |
| Metric      | 25      | 25    | 100%     |
| History     | 25      | 25    | 100%     |
| **TOTAL**   | **99**  | **99**| **100%** |

본 문서는 다음을 제공합니다:

- **Pipeline 중심 사고방식**: 단순한 기능 나열이 아니라, Stage별 의미와 흐름을 이해
- **Asset-Stage Binding 이해**: Asset이 어떤 Stage에서 어떻게 작동하는지 명확히 파악
- **Test → Inspect → Fix 순환 학습**: UI에서 실험하고 즉시 피드백받는 방법
- **실제 UI 경로 및 파일 위치**: 코드베이스와 연결된 구체적 위치 제시
- **테스트 결과와 검증**: 99개 테스트 케이스 (100% 통과) ✅

### 현재 UI 기준 반영 사항

- Admin 탭은 현재 `Assets`, `Tools`, `Catalogs`, `Screens`, `Explorer`, `Settings`, `Inspector`, `Regression`, `Observability`, `Logs`를 기준으로 설명한다.
- OPS 운영에서 `Tools`와 `Catalogs`는 핵심 경로다.
  - `Tools`: 실행 단위(도구) 정의/테스트/발행
  - `Catalogs`: DB 스키마 스캔/카탈로그 관리 (도구 질의 정확도에 영향)

**중요**: 이것은 유일한 순서가 아니다. 사용자는 언제든 중간 단계부터 시작하거나 일부를 건너뛸 수 있다. 다만 **처음 도입 시 가장 이해하기 쉽고 실패 가능성이 낮은 기준 흐름**이 이 순서다.

---

## 목차

### Core Sections
1. [시작 전 이해: Pipeline과 Asset의 관계](#1-시작-전-이해-pipeline과-asset의-관계)
2. [Implementation Flow (학습 경로)](#2-implementation-flow-학습-경로)
3. [OPS UI 아키텍처 이해](#3-ops-ui-아키텍처-이해)
4. [실습: 첫 질의 실행과 분석](#4-실습-첫-질의-실행과-분석)
5. [Asset 설정 및 Pipeline Binding](#5-asset-설정-및-pipeline-binding)

### New: Security & Operations
- [NEW: Error Handling & Recovery](#new-error-handling--recovery) ⭐
- [NEW: Data Security](#new-data-security-section) ⭐

### Advanced Sections
6. [Test Mode와 Asset Override](#6-test-mode와-asset-override)
7. [Inspector를 통한 Trace 분석](#7-inspector를-통한-trace-분석)
8. [Control Loop 이해 (Replan/Rerun)](#8-control-loop-이해-replanrerun)
9. [문제 해결 패턴](#9-문제-해결-패턴)
10. [종합 실습: E2E 학습 시나리오](#10-종합-실습-e2e-학습-시나리오)
11. [체크리스트](#11-체크리스트)
12. [참고 자료](#12-참고-자료)

---

## 1. 시작 전 이해: Pipeline과 Asset의 관계

### 1.1 Pipeline의 의미

OPS 오케스트레이션은 **5개의 Stage로 구성된 파이프라인**이다. 각 Stage는 명확한 책임과 입출력 계약을 가진다.

```
ROUTE+PLAN → VALIDATE → EXECUTE → COMPOSE → PRESENT
```

#### Stage 의미론 (Semantics)

| Stage | 책임 | 입력 (Input) | 출력 (Output) |
|-------|------|-------------|--------------|
| **ROUTE+PLAN** | 질의 해석, 분기 결정, 실행 계획 생성 | 자연어 질문 | PlanOutput (direct/plan/reject) |
| **VALIDATE** | 정책/보안/예산 검증 | PlanOutput | ValidatedPlan |
| **EXECUTE** | 데이터·문서·그래프 조회 | ValidatedPlan | ToolResults + References |
| **COMPOSE** | 결과 조합/요약 | ToolResults | AnswerBlocks |
| **PRESENT** | UI 렌더링 모델 생성 | AnswerBlocks | ScreenModel |

**핵심 원칙**:
- 각 Stage는 **이전 Stage의 출력을 입력으로 받는다**
- 모든 입출력은 **Execution Trace**에 저장된다
- Stage를 건너뛰거나 순서를 바꿀 수 없다 (Pipeline 고정)

### 1.2 Asset의 의미

**Asset**은 코드를 수정하지 않고 시스템의 동작을 바꾸기 위한 유일한 수단이다.

#### Asset 종류와 Stage Binding

```
[ROUTE+PLAN]  ← Prompt, Policy, SchemaCatalog, Resolver
[VALIDATE]    ← Policy
[EXECUTE]     ← Query, Source
[COMPOSE]     ← Mapping, Prompt(선택사항)
[PRESENT]     ← Screen
```

**Asset-Stage Binding 원칙**:
- Asset은 **Stage에 바인딩되어야만** 의미를 가진다
- 잘못된 바인딩(예: Query를 ROUTE+PLAN에 바인딩)은 시스템이 차단한다
- 동일한 Asset 타입도 버전에 따라 다른 Stage에서 다르게 작동할 수 있다

### 1.3 Direct / Orchestration / Reject의 의미

**ROUTE+PLAN Stage**는 **단일 LLM 호출**로 다음 중 하나를 결정한다:

1. **DirectAnswer**: 데이터 조회 없이 즉시 답변 (예: "너의 이름은?")
   - VALIDATE 이후 Stage를 건너뛰고 바로 종료
   - 단, Trace는 여전히 기록됨

2. **OrchestrationPlan**: 데이터·문서·그래프 조회 필요 (예: "GT-01 CPU 사용률은?")
   - 전체 Pipeline 실행
   - Plan에는 intent, tools, filters 등 포함

3. **Reject**: 정책/보안/범위 위반 (예: "모든 사용자 비밀번호를 보여줘")
   - 즉시 거부 응답
   - Trace에 reject 이유 기록

**왜 중요한가**:
- 초경량 질의도 **동일한 관측/정책/추적 체계** 안에서 처리된다
- "파이프라인을 타지 않는 질의"가 아니라, **ROUTE+PLAN에서 종료되는 파이프라인 실행**이다

---

## 2. Implementation Flow (학습 경로)

> **이 Flow의 성격**: 구성 학습용(User Learning Flow), 도메인 온보딩 기준선(Baseline Setup)

### 2.1 학습 단계 개요

```
1. Source 연결 → 데이터의 물리적 존재 확정
2. SchemaCatalog 구성 → 구조를 사람/LLM이 이해 가능한 언어로 정의
3. Resolver 설정 → 사용자 표현 ↔ 실제 ID 연결
4. Query 작성 + Preview → 조회 로직 정합성 즉시 검증
5. Mapping 작성 → 결과를 응답 블록으로 변환
6. Screen 구성 → 표현 결정
7. OPS End-to-End 테스트 → 실제 사용자 질의 기준 E2E 확인
```

### 2.2 왜 이 순서인가

- **Source 먼저**: 데이터가 없으면 어떤 테스트도 불가능
- **Schema 다음**: LLM이 "무엇을 조회할 수 있는지" 알아야 Plan 생성 가능
- **Resolver 그다음**: 사용자 언어 ↔ 시스템 ID 매핑 확정
- **Query/Mapping 함께**: 데이터 조회와 변환은 밀접하게 연결됨
- **Screen 마지막**: 데이터 흐름이 완성된 후 표현 결정
- **E2E 테스트로 종료**: 전체 흐름 검증

### 2.3 누락처럼 보이는 것들

- **Policy 설정**: 모든 단계의 전제 조건이므로 별도 운영 플로우로 다룸
- **Prompt 튜닝**: 고급 운영/최적화 단계 (기본 Prompt는 이미 제공됨)
- **Control Loop**: 런타임 자동 메커니즘 (사용자가 매번 수행할 작업 아님)

---

## 3. OPS UI 아키텍처 이해

### 3.1 UI 설계 원칙

1. **Guided Flow**: 사용자는 "다음에 무엇을 해야 하는지" 항상 안내받는다
2. **Pipeline 가시성**: 파이프라인은 숨기지 않고 항상 드러낸다
3. **In/Out 우선**: 로그보다 입력/출력이 먼저 보인다
4. **조치 연결(Actionable)**: 모든 화면은 다음 행동으로 이어진다
5. **Test ↔ Inspect ↔ Fix 순환**: UI에서 왕복이 끊기지 않는다

### 3.2 핵심 UI 컴포넌트

#### OPS 메인 페이지 ([/ops](apps/web/src/app/ops/page.tsx:284))

**역할**: 사용자가 질의를 입력하고 실행 → Pipeline Timeline으로 이해 → Test Mode/Override로 개선

**화면 구성**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ OPS Query Interface                                    [Test Mode: OFF]  │
├──────────────┬───────────────────────────────────────────────────────────┤
│ History      │  OpsSummaryStrip                                          │
│ Sidebar      │  Route: ORCH | Tools: 3 | Replans: 1 | Duration: 3.2s    │
│              │                                                           │
│ Recent       │  Mode Selector                                            │
│ Queries      │  [전체] [구성] [수치] [이력] [연결] [문서]               │
│              │    ↑ 기본                                                 │
│ ORCH ✓      │  Question Input                                           │
│ DIRECT ✓    │  [_______________________________________] [메시지 전송]  │
│ REJECT ✗    │                                                           │
│              │  InspectorStagePipeline (조건부 표시*)                    │
│              │  ROUTE+PLAN → VALIDATE → EXECUTE → COMPOSE → PRESENT     │
│              │   120ms✓      15ms✓      450ms⚠       85ms✓      12ms✓   │
│              │  *trace에 stage_outputs 데이터가 있을 때만 표시          │
│              │                                                           │
│              │  [Stage Card 클릭 시 In/Out 표시]                         │
│              │                                                           │
│              │  BlockRenderer (답변 블록)                                │
│              │  * Text Block: "GT-01 CPU 평균 67.3%"                    │
│              │  * Chart Block: [시계열 그래프]                           │
│              │  * Table Block: [상세 데이터]                            │
│              │  * References Block: 데이터 출처                          │
└──────────────┴───────────────────────────────────────────────────────────┘
```

**모드 선택 (하단 버튼)**:

```
[전체] [구성] [수치] [이력] [연결] [문서]
  ↑ 기본 선택
```

- 기본 선택 모드: **전체 (all)** — localStorage에 저장되어 다음 접속 시 유지
- 모드 전환 시 localStorage에 기록되며, 같은 브라우저에서 재접속하면 마지막 모드가 유지됨

**주요 파일**:
- OPS 페이지: [apps/web/src/app/ops/page.tsx:41-48](apps/web/src/app/ops/page.tsx#L41)
- Summary Strip: [apps/web/src/components/ops/OpsSummaryStrip.tsx](apps/web/src/components/ops/OpsSummaryStrip.tsx)
- Stage Pipeline: [apps/web/src/components/ops/InspectorStagePipeline.tsx](apps/web/src/components/ops/InspectorStagePipeline.tsx)

#### Inspector ([/admin/inspector](apps/web/src/app/admin/inspector/page.tsx))

**역할**: Execution Trace 중심 분석 → Asset 수정 → 재실행 연결

**핵심 기능**:
- Trace List 조회 (Route/Replan/Status 필터)
- Pipeline Visualization (Stage별 In/Out)
- Replan Events 타임라인
- Applied Assets 확인 및 수정 링크
- Isolated Stage Test 실행

**주요 파일**:
- Inspector 페이지: [apps/web/src/app/admin/inspector/page.tsx](apps/web/src/app/admin/inspector/page.tsx)
- Trace Service: [apps/api/app/modules/inspector/service.py](apps/api/app/modules/inspector/service.py)

#### Asset Registry ([/admin/assets](apps/web/src/app/admin/assets/page.tsx))

**역할**: Asset 생성/편집/배포 + Pipeline Lens로 Stage Binding 확인

**Pipeline Lens 개념**:
```
Asset List 화면에서 Asset을 선택하면:
→ "Used in Stages" 섹션 표시
→ ROUTE+PLAN, EXECUTE, COMPOSE 등 바인딩된 Stage 목록
→ 각 Stage 클릭 시 → 해당 Stage의 In/Out 예시 표시
```

**주요 파일**:
- Assets 페이지: [apps/web/src/app/admin/assets/page.tsx](apps/web/src/app/admin/assets/page.tsx)
- Asset Table: [apps/web/src/components/admin/AssetTable.tsx](apps/web/src/components/admin/AssetTable.tsx)
- Asset Form: [apps/web/src/components/admin/AssetForm.tsx](apps/web/src/components/admin/AssetForm.tsx)

#### Asset Override Drawer ([AssetOverrideDrawer.tsx](apps/web/src/components/ops/AssetOverrideDrawer.tsx))

**역할**: Test Mode에서 특정 Asset 버전을 Override하여 실행

**사용 시나리오**:
1. OPS 질의 실행 후 결과 불만족
2. Inspector에서 어떤 Asset이 문제인지 파악
3. Asset Override Drawer 열기
4. 문제 Asset의 다른 버전 선택 (또는 draft 버전)
5. "Run Test" 실행 → 새로운 Trace 생성
6. 결과 비교 → 개선 확인 시 Asset 발행

**주요 파일**:
- Asset Override Drawer: [apps/web/src/components/ops/AssetOverrideDrawer.tsx](apps/web/src/components/ops/AssetOverrideDrawer.tsx)

### 3.3 Admin 운영 탭 (현재 기준)

현재 Admin 탭은 다음 순서로 구성된다:

`Assets`, `Tools`, `Catalogs`, `Screens`, `Explorer`, `Settings`, `Inspector`, `Regression`, `Observability`, `Logs`

OPS 운영에서 자주 사용하는 탭:

1. `Assets`: Prompt/Policy/Query/Mapping/Source/Resolver/Screen 자산 관리
2. `Tools`: 실행 도구 생성, 입력 스키마 정의, 테스트, 발행
3. `Catalogs`: DB 스키마 스캔/조회(도구의 SQL 정확도 보조)
4. `Inspector`: trace/stage/tool_calls/references 분석
5. `Regression`: Golden Query 기반 회귀 실행
6. `Observability`: 처리량/지연/오류율 관측
7. `Logs`: query history/execution trace/audit/file logs 확인

---

## 4. 실습: 첫 질의 실행과 분석

> **목표**: 시스템이 이미 동작하는 상태에서 첫 질의를 실행하고, Pipeline의 각 Stage가 무엇을 하는지 이해한다.

### 4.1 OPS 페이지 접속

**경로**: 브라우저에서 `http://your-domain/ops` 접속

**화면 구성 확인**:
- 좌측: Query History (이전 질의 목록)
- 우측 상단: Summary Strip (라우트, 도구, 재계획 요약)
- 우측 중앙: Question Input (질문 입력창)
- 우측 하단: Answer 영역 (결과 표시)

### 4.2 첫 질의 실행

#### 단계

1. **Mode 선택** (하단 Run OPS query 섹션)
   - 6개 모드 중 **"전체 (all)"** 선택 (기본 선택)
   - 모드별 차이:
     - **전체 (all)**: LLM이 자동 판단하여 최적 모드 결정 (기본값)
     - **구성 (config)**: 구성 정보 조회
     - **수치 (metric)**: 메트릭 데이터만 조회 (intent=metric)
     - **이력 (history)**: 이벤트 이력 조회 (intent=history)
     - **연결 (relation)**: 관계 그래프 조회 (intent=graph)
     - **문서 (document)**: 문서 검색/요약

   **API 엔드포인트 라우팅** (중요):

   모드에 따라 호출되는 백엔드 엔드포인트가 다르다.

   | UI 모드 | Backend 모드 | 엔드포인트 | 처리 방식 |
   |---------|-------------|-----------|----------|
   | 전체 (all) | `all` | `POST /ops/ask` | LLM 오케스트레이션 (전체 Pipeline) |
   | 구성 (config) | `config` | `POST /ops/query` | 모드 디스패처 (직접 실행) |
   | 수치 (metric) | `metric` | `POST /ops/query` | 모드 디스패처 (직접 실행) |
   | 이력 (history) | `hist` | `POST /ops/query` | 모드 디스패처 (직접 실행) |
   | 연결 (relation) | `graph` | `POST /ops/query` | 모드 디스패처 (직접 실행) |
   | 문서 (document) | `document` | `POST /ops/query` | 모드 디스패처 (직접 실행) |

   - **"전체" 모드만** `/ops/ask` 엔드포인트를 사용하며, LLM이 질의를 분석하여 최적의 모드를 자동 선택한다.
   - **나머지 5개 모드**는 모두 `/ops/query` 엔드포인트를 사용하며, 지정된 모드로 직접 실행된다.
   - 파일 위치: [apps/web/src/app/ops/page.tsx:266-326](apps/web/src/app/ops/page.tsx#L266)

2. **질문 입력**
   ```
   GT-01이 뭐야?
   ```

3. **실행**
   - **"메시지 전송"** 버튼 클릭
   - 화면에 "Running..." 표시
   - 3~10초 후 결과 표시

### 4.3 결과 분석: Pipeline Timeline 이해

#### Pipeline Timeline 표시 위치

실행 완료 후 **InspectorStagePipeline** 컴포넌트가 표시됩니다. 이 컴포넌트는 **두 곳**에서 확인할 수 있습니다:

**1. OPS 페이지 ([/ops](apps/web/src/app/ops/page.tsx))**
   - 답변 영역 상단에 표시됨 (Answer Blocks 바로 위)
   - 질의 실행 후 자동으로 표시 (trace에 `stage_inputs`/`stage_outputs` 데이터가 있는 경우)

**2. Inspector 페이지의 Trace Overview ([/admin/inspector](apps/web/src/app/admin/inspector/page.tsx))**
   - **"Stage Pipeline"** 섹션 내에 표시됨
   - Plan 섹션 바로 다음에 위치
   - Trace를 선택하면 Trace Overview 드로어가 열리고, 그 안의 "Stage Pipeline" 섹션에서 확인 가능

#### 표시 조건 (중요!)

Pipeline Timeline은 **trace에 `stage_inputs`와 `stage_outputs` 데이터가 있어야만** 표시됩니다.

- ✅ 데이터 있음: Pipeline 시각화 표시
  ```
  각 Stage가 별도의 카드 형태로 표시되며,
  상태(✓, ⚠, ✗)와 실행 시간(ms)을 보여줍니다
  ```

- ❌ 데이터 없음: Pipeline Timeline이 표시되지 않음 (아무것도 안 보임)

**데이터가 없는 경우 원인**:
- 백엔드에서 `stage_inputs`/`stage_outputs`를 반환하지 않음
- Trace가 완료되지 않았거나 저장 실패
- 일부 Route 타입(DIRECT, REJECT)에서는 stage trace가 간소화될 수 있음

#### 실제 UI 구조

Pipeline Timeline은 각 Stage를 **개별 카드** 형태로 표시합니다:

```
┌─────────────────────────────────────────────────────────────┐
│ Stage Pipeline                                     Trace ID │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌────────────┐    ┌────────────┐    ┌────────────┐        │
│ │ROUTE PLAN  │ →  │ VALIDATE    │ →  │ EXECUTE    │  ...   │
│ │  120ms ✓   │    │   15ms ✓    │    │  450ms ⚠   │        │
│ │route_plan  │    │ validate    │    │ execute    │        │
│ └────────────┘    └────────────┘    └────────────┘        │
│                                                             │
│ ※ 각 Stage 카드를 클릭하면 Input/Output 상세 정보 표시       │
└─────────────────────────────────────────────────────────────┘
```

**Stage 색상 및 상태**:
- **ROUTE+PLAN (파란색)**: 질의 분석 및 계획 생성
- **VALIDATE (초록색)**: 정책 및 보안 검증
- **EXECUTE (노란색)**: 데이터 조회 (경고: ⚠)
- **COMPOSE (보라색)**: 결과 조합
- **PRESENT (빨간색)**: UI 렌더링

**상태 아이콘**:
- ✓: 성공 (ok)
- ⚠: 경고 (warning)
- ✗: 에러 (error)
- ⏱: 대기/실행 중 (pending)

#### 각 Stage 클릭하여 이해하기

**ROUTE+PLAN (120ms, 파란색)** 클릭:
```
Status: ok
Duration: 120ms

Applied Assets:
- prompt: ci_planner (v3) [View]
- policy: plan_budget (v1) [View]
- schema: production_catalog (v2) [View]

Input:
{
  "question": "GT-01이 뭐야?",
  "mode": "all"
}

Output (PlanOutput):
{
  "kind": "plan",
  "plan": {
    "intent": "config",
    "view": "DETAIL",
    "scope": {
      "ci_codes": ["GT-01"]
    },
    "tools": ["ci_tool"]
  }
}
```

**의미**:
- LLM(Prompt asset)이 질문을 분석하여 "CI 정보 조회" 계획 생성
- Route: `plan` (오케스트레이션 필요, Direct 아님)
- Intent: `config` (수치나 이력이 아닌 구성 정보)

---

**VALIDATE (15ms, 초록색)** 클릭:
```
Status: ok
Duration: 15ms

Applied Assets:
- policy: plan_budget (v1)

Input:
{
  "plan": {...위의 plan...}
}

Output (ValidatedPlan):
{
  "plan": {...동일...},
  "limits_applied": {
    "max_row_count": 1000,
    "max_query_depth": 3
  },
  "policy_decisions": {
    "allowed": true,
    "budget_ok": true
  }
}
```

**의미**:
- Policy asset이 Plan을 검증
- 제한 적용: 최대 1000행, 쿼리 깊이 3
- 승인: allowed=true

---

**EXECUTE (450ms, 노란색, ⚠ 경고)** 클릭:
```
Status: warning
Duration: 450ms

Applied Assets:
- query: ci_lookup (v5)
- source: postgres_main (v1)

Diagnostics:
- warnings: ["Resolver not configured, using raw ci_code"]
- counts: {"references": 2, "rows": 1}

Input:
{
  "plan": {...},
  "validated_plan": {...}
}

Output (ToolResults):
{
  "tool_results": [
    {
      "tool": "ci_tool",
      "result": {
        "ci_id": "uuid-123",
        "ci_code": "GT-01",
        "ci_name": "Gas Turbine Unit 1",
        "ci_type": "GasTurbine",
        "status": "Operational"
      }
    }
  ],
  "references": [
    {"kind": "row", "title": "ci_master.GT-01", "payload": {...}}
  ]
}
```

**의미**:
- Query asset이 데이터베이스에서 CI 정보 조회
- Source asset이 DB 연결 제공
- ⚠ 경고: Resolver 미설정으로 "GT-01"을 그대로 사용 (변환 없음)

---

**COMPOSE (85ms, 보라색)** 클릭:
```
Status: ok
Duration: 85ms

Applied Assets:
- mapping: default_ci_mapping (v1)

Input:
{
  "tool_results": [...],
  "references": [...]
}

Output (AnswerBlocks):
{
  "blocks": [
    {
      "type": "text",
      "content": "GT-01은 Gas Turbine Unit 1입니다. 현재 Operational 상태입니다."
    },
    {
      "type": "table",
      "headers": ["항목", "값"],
      "rows": [
        ["CI Code", "GT-01"],
        ["CI Name", "Gas Turbine Unit 1"],
        ["CI Type", "GasTurbine"],
        ["Status", "Operational"]
      ]
    }
  ],
  "references": [...]
}
```

**의미**:
- Mapping asset이 ToolResults를 AnswerBlocks로 변환
- Text 블록 + Table 블록 생성

---

**PRESENT (12ms, 빨간색)** 클릭:
```
Status: ok
Duration: 12ms

Applied Assets:
- screen: default (v1)

Input:
{
  "blocks": [...]
}

Output (ScreenModel):
{
  "layout": "vertical",
  "components": [
    {"type": "text", ...},
    {"type": "table", ...}
  ]
}
```

**의미**:
- Screen asset이 블록을 UI 레이아웃으로 변환
- 최종 사용자에게 표시되는 형식 결정

---

### 4.4 결과 확인: Answer 영역

Pipeline 아래 **BlockRenderer**에서 실제 답변 확인:

```
📌 GT-01은 Gas Turbine Unit 1입니다. 현재 Operational 상태입니다.

┌─────────────┬──────────────────────────┐
│ 항목        │ 값                       │
├─────────────┼──────────────────────────┤
│ CI Code     │ GT-01                    │
│ CI Name     │ Gas Turbine Unit 1       │
│ CI Type     │ GasTurbine               │
│ Status      │ Operational              │
└─────────────┴──────────────────────────┘

📊 Data Sources:
• source: postgres_main (v1)
• schema: production_catalog (v2)
```

### 4.5 Trace 정보 확인

화면 하단 **"Trace · plan / policy"** 섹션 펼치기:

```json
{
  "trace_id": "f5e6d7c8-9abc-def0-1234-567890abcdef",
  "route": "orch",
  "pipeline_version": "1.0",
  "applied_assets": {
    "prompt:ci_planner": "uuid-abc:v3",
    "policy:plan_budget": "uuid-def:v1",
    "query:ci_lookup": "uuid-ghi:v5",
    "source:postgres_main": "uuid-jkl:v1",
    "mapping:default_ci_mapping": "uuid-mno:v1",
    "screen:default": "uuid-pqr:v1"
  },
  "stage_inputs": [...],
  "stage_outputs": [...],
  "replan_events": []
}
```

**핵심 이해**:
- `trace_id`: 이 실행의 고유 ID (Inspector에서 분석 가능)
- `applied_assets`: 각 Asset의 정확한 버전 기록 (재현 가능성)
- `replan_events`: 빈 배열 → 재계획 없이 성공

---

## 5. Asset 설정 및 Pipeline Binding

> **목표**: 각 Asset 타입이 어떤 Stage에서 사용되는지 이해하고, 실제로 Asset을 생성/수정하는 방법을 학습한다.

### 5.1 Asset-Stage Binding Map (재확인)

```
[ROUTE+PLAN]  ← Prompt (ci_planner), Policy (plan_budget),
                 SchemaCatalog (production_catalog), Resolver (ci_resolver)
[VALIDATE]    ← Policy (plan_budget)
[EXECUTE]     ← Query (ci_lookup), Source (postgres_main)
[COMPOSE]     ← Mapping (default_ci_mapping), Prompt (선택사항)
[PRESENT]     ← Screen (default)
```

### 5.2 Source Asset 생성

**경로**: Admin → Assets → "+ New Asset"

#### 단계

1. **Asset 생성**
   - Asset Type: **"Source"** 선택
   - Name: `운영DB 프로덕션`
   - Scope: `production`
   - **"Create Asset"** 클릭

2. **연결 정보 입력** (상세 화면으로 자동 이동)
   - **"Edit Connection"** 버튼 클릭
   - Source Type: **PostgreSQL** 선택
   - Host: `db.example.com`
   - Port: `5432`
   - Username: `readonly_user`
   - Database Name: `production_db`
   - Timeout: `30`
   - **"Update Source"** 버튼 클릭

3. **연결 테스트**
   - **"Test Connection"** 버튼 클릭
   - 결과: ✅ "Connection successful" 또는 ❌ 에러 메시지

4. **발행 (Publish)**
   - 우측 하단 **"Publish"** 버튼 클릭
   - 상태 변화: `draft` → `published`
   - **출력**: `asset_id` (예: `uuid-123`), `version: 1`

**파일 위치**:
- Source Form: [apps/web/src/components/admin/SourceAssetForm.tsx:44](apps/web/src/components/admin/SourceAssetForm.tsx#L44)
- Backend Service: [apps/api/app/modules/asset_registry/router.py](apps/api/app/modules/asset_registry/router.py)

**Stage Binding**: EXECUTE Stage에서 사용됨

---

### 5.3 SchemaCatalog Asset 생성 (자동)

**경로**: Admin → Assets → Sources → 방금 만든 Source 선택

#### 단계

1. **Schema 스캔 시작**
   - **"Rescan Schema"** 버튼 클릭
   - 모달 열림

2. **스캔 옵션 설정 (선택사항)**
   - Include Tables: 특정 테이블만 스캔 (비워두면 전체)
     ```
     ci_master
     metric_timeseries
     events
     ```
   - Exclude Tables: 제외할 테이블
     ```
     temp_*
     test_*
     ```
   - **"Start Scan"** 버튼 클릭

3. **스캔 결과 확인**
   ```
   Status: completed
   Tables: 50
   Columns: 300
   Last scanned: 2026-01-25 14:30:00
   ```

4. **자동 생성된 Schema Asset 확인**
   - 좌측 상단 "← Back to Assets" 클릭
   - Asset Type 필터: **"Schemas"** 선택
   - 목록에서 자동 생성된 Schema asset 확인
   - 해당 asset 클릭 → **"Publish"** 버튼 클릭

**파일 위치**:
- Schema Form: [apps/web/src/components/admin/SchemaAssetForm.tsx:50](apps/web/src/components/admin/SchemaAssetForm.tsx#L50)
- Scan API: `POST /asset-registry/schemas/{source_ref}/scan`

**Stage Binding**: ROUTE+PLAN Stage에서 사용됨 (LLM이 테이블 구조를 이해하기 위함)

---

### 5.4 Resolver Asset 생성

**경로**: Admin → Assets → "+ New Asset"

#### 목적
사용자가 입력한 "GT-01"을 데이터베이스의 정규화된 ID로 변환

#### 단계

1. **Asset 생성**
   - Asset Type: **"Resolver"** 선택
   - Name: `CI 코드 리졸버`
   - Scope: `production`
   - **"Create Asset"** 클릭

2. **Resolver 규칙 설정**

   현재 UI에서는 Resolver 규칙을 직접 편집할 수 없으므로, **API를 통해 설정**하거나 **백엔드 파일로 관리**해야 합니다.

   **옵션 1: API 직접 호출** (개발자용)
   ```bash
   curl -X POST http://your-domain/api/asset-registry/resolvers \
     -H "Content-Type: application/json" \
     -d '{
       "name": "CI 코드 리졸버",
       "scope": "production",
       "config": {
         "rules": [
           {
             "rule_type": "alias_mapping",
             "name": "GT-01 매핑",
             "priority": 100,
             "is_active": true,
             "rule_data": {
               "source_entity": "GT-01",
               "target_entity": "gas_turbine_unit_1"
             }
           }
         ]
       }
     }'
   ```

   **옵션 2: 백엔드 Seed 파일 사용**
   - 파일 위치: `apps/api/resources/resolvers/{scope}/ci_resolver.yaml`
   - 내용:
     ```yaml
     name: CI 코드 리졸버
     rules:
       - rule_type: alias_mapping
         name: GT-01 매핑
         priority: 100
         is_active: true
         rule_data:
           source_entity: GT-01
           target_entity: gas_turbine_unit_1
     ```

3. **Resolver 테스트**
   - Admin → Assets → Resolvers → `CI 코드 리졸버` 선택
   - "Test Entities" 입력창에 입력:
     ```
     GT-01
     GT-02
     ```
   - **"Simulate Resolution"** 버튼 클릭
   - 결과 확인:
     ```
     GT-01 → gas_turbine_unit_1 (Confidence: 100%)
     Matched Rules: [GT-01 매핑]
     ```

4. **발행**
   - **"Publish"** 버튼 클릭

**파일 위치**:
- Resolver Form: [apps/web/src/components/admin/ResolverAssetForm.tsx:36](apps/web/src/components/admin/ResolverAssetForm.tsx#L36)
- Resolver Loader: [apps/api/app/modules/asset_registry/loader.py](apps/api/app/modules/asset_registry/loader.py) (lines 584-642)

**Stage Binding**: ROUTE+PLAN Stage에서 사용됨 (Plan 생성 시 엔티티 해석)

---

### 5.5 Query Asset 생성

**경로**: Admin → Assets → "+ New Asset"

#### 단계

1. **Asset 생성**
   - Asset Type: **"Query"** 선택
   - Name: `CI 조회 쿼리`
   - Scope: `ci`
   - **"Create Asset"** 클릭

2. **SQL Query 입력**
   ```sql
   SELECT
     ci_id,
     ci_code,
     ci_name,
     ci_type,
     status,
     created_at
   FROM ci_master
   WHERE ci_code = :ci_code
   LIMIT :limit
   ```

3. **Query Parameters (JSON)**
   ```json
   {
     "ci_code": {
       "type": "string",
       "required": true,
       "description": "CI code to lookup"
     },
     "limit": {
       "type": "integer",
       "default": 1,
       "description": "Maximum rows to return"
     }
   }
   ```

4. **Query Metadata (JSON)**
   ```json
   {
     "read_only": true,
     "max_execution_time_ms": 5000,
     "cache_ttl_seconds": 60
   }
   ```

5. **저장 및 발행**
   - **"Save Draft"** 버튼 클릭
   - **"Publish"** 버튼 클릭

**파일 위치**:
- Asset Form (Query 섹션): [apps/web/src/components/admin/AssetForm.tsx:366](apps/web/src/components/admin/AssetForm.tsx#L366)

**Stage Binding**: EXECUTE Stage에서 사용됨

---

### 5.6 Mapping Asset 생성

**경로**: Admin → Assets → "+ New Asset"

#### 목적
EXECUTE Stage의 ToolResults를 COMPOSE Stage의 AnswerBlocks로 변환

#### 단계

1. **Asset 생성**
   - Asset Type: **"Mapping"** 선택
   - Name: `CI 정보 매핑`
   - Scope: `ci`
   - **"Create Asset"** 클릭

2. **Content (JSON) 입력**
   ```json
   {
     "version": "1.0",
     "mappings": [
       {
         "source_type": "ci_tool",
         "target_block": "table",
         "transform": {
           "headers": ["항목", "값"],
           "row_mapping": [
             {"label": "CI Code", "field": "ci_code"},
             {"label": "CI Name", "field": "ci_name"},
             {"label": "CI Type", "field": "ci_type"},
             {"label": "Status", "field": "status"}
           ]
         }
       },
       {
         "source_type": "ci_tool",
         "target_block": "text",
         "template": "{{ci_name}}({{ci_code}})은 현재 {{status}} 상태입니다."
       }
     ]
   }
   ```

3. **저장 및 발행**
   - **"Save Draft"** 버튼 클릭
   - **"Publish"** 버튼 클릭

**파일 위치**:
- Asset Form (Mapping 섹션): [apps/web/src/components/admin/AssetForm.tsx:338](apps/web/src/components/admin/AssetForm.tsx#L338)

**Stage Binding**: COMPOSE Stage에서 사용됨

---

### 5.7 Prompt Asset (선택사항 - 고급)

**경로**: Admin → Assets → "+ New Asset"

#### 목적
ROUTE+PLAN Stage에서 LLM이 사용할 프롬프트 템플릿

**기본 제공**: 시스템은 이미 `ci:planner` Prompt를 제공하므로, 처음에는 수정 불필요

#### 고급 사용자를 위한 수정

1. **Asset 생성**
   - Asset Type: **"Prompt"** 선택
   - Name: `CI 플래너 v2`
   - Scope: `ci`
   - **"Create Asset"** 클릭

2. **Template 입력**
   ```
   You are an OPS query planner specialized in CI management.

   User Question: {{question}}

   Available Schema:
   {{schema}}

   Available Resolvers:
   {{resolvers}}

   Generate a structured query plan in JSON format:
   {
     "intent": "config" | "metric" | "history" | "graph",
     "ci_codes": [...],
     "filters": {...},
     "tools": [...]
   }

   Important:
   - Use Resolver rules to normalize CI codes
   - Check schema for available columns before planning
   - Respect max_row_count and max_query_depth limits
   ```

3. **Input Schema (JSON)**
   ```json
   {
     "type": "object",
     "properties": {
       "question": {"type": "string"},
       "schema": {"type": "object"},
       "resolvers": {"type": "object"}
     },
     "required": ["question"]
   }
   ```

4. **Output Contract (JSON)**
   ```json
   {
     "type": "object",
     "properties": {
       "intent": {
         "type": "string",
         "enum": ["config", "metric", "history", "graph"]
       },
       "ci_codes": {
         "type": "array",
         "items": {"type": "string"}
       },
       "tools": {
         "type": "array",
         "items": {"type": "string"}
       }
     },
     "required": ["intent"]
   }
   ```

5. **저장 및 발행**
   - **"Save Draft"** → **"Publish"**

**파일 위치**:
- Asset Form (Prompt 섹션): [apps/web/src/components/admin/AssetForm.tsx:297](apps/web/src/components/admin/AssetForm.tsx#L297)
- Prompt Loader: [apps/api/app/modules/asset_registry/loader.py](apps/api/app/modules/asset_registry/loader.py) (lines 25-111)

**Stage Binding**: ROUTE+PLAN Stage에서 사용됨

---

### 5.8 Policy Asset

**경로**: Admin → Assets → "+ New Asset"

#### 목적
VALIDATE Stage에서 Plan 검증 및 제한 적용

#### 단계

1. **Asset 생성**
   - Asset Type: **"Policy"** 선택
   - Name: `기본 OPS 정책`
   - Scope: `production`
   - **"Create Asset"** 클릭

2. **Limits (JSON) 입력**
   ```json
   {
     "max_query_depth": 3,
     "max_row_count": 10000,
     "query_timeout_seconds": 30,
     "allowed_intents": ["config", "metric", "history", "graph"],
     "restricted_tables": ["users", "credentials", "secrets"],
     "rate_limit": {
       "requests_per_minute": 60,
       "requests_per_hour": 1000
     },
     "replan_policy": {
       "max_replans": 3,
       "allowed_triggers": [
         "empty_result",
         "tool_error",
         "timeout"
       ],
       "min_interval_seconds": 60
     }
   }
   ```

3. **저장 및 발행**
   - **"Save Draft"** → **"Publish"**

**파일 위치**:
- Asset Form (Policy 섹션): [apps/web/src/components/admin/AssetForm.tsx:352](apps/web/src/components/admin/AssetForm.tsx#L352)
- Policy Loader: [apps/api/app/modules/asset_registry/loader.py](apps/api/app/modules/asset_registry/loader.py)

**Stage Binding**: ROUTE+PLAN, VALIDATE Stage에서 사용됨

---

### 5.9 Screen Asset (선택사항)

**경로**: Admin → Assets → "+ New Asset"

#### 목적
PRESENT Stage에서 AnswerBlocks를 UI 레이아웃으로 변환

**기본 제공**: `default` Screen이 이미 제공되므로, 커스터마이징이 필요한 경우만 사용

#### 단계

1. **Asset 생성**
   - Asset Type: **"Screen"** 선택
   - Name: `OPS 대시보드 레이아웃`
   - Scope: `production`
   - **"Create Asset"** 클릭

2. **Screen Schema (JSON) 입력**
   ```json
   {
     "layout": "vertical",
     "components": [
       {
         "type": "text",
         "style": {
           "fontSize": "large",
           "fontWeight": "bold"
         }
       },
       {
         "type": "chart",
         "defaultHeight": 400,
         "responsive": true
       },
       {
         "type": "table",
         "pagination": true,
         "pageSize": 20
       },
       {
         "type": "references",
         "collapsible": true
       }
     ]
   }
   ```

3. **저장 및 발행**
   - **"Save Draft"** → **"Publish"**

**파일 위치**:
- Asset Form (Screen 섹션): [apps/web/src/components/admin/AssetForm.tsx:407](apps/web/src/components/admin/AssetForm.tsx#L407)
- Screen Editor: [apps/web/src/app/admin/screens/[screenId]/page.tsx](apps/web/src/app/admin/screens/[screenId]/page.tsx)

**Stage Binding**: PRESENT Stage에서 사용됨

---

### 5.10 Asset 체크리스트

모든 Asset이 올바르게 설정되었는지 확인:

```
✅ SOURCE: 운영DB 프로덕션 (v1, published, connection test: OK)
✅ SCHEMA: 운영DB 프로덕션 Schema (v1, published, scan status: completed)
✅ RESOLVER: CI 코드 리졸버 (v1, published, test: OK)
✅ QUERY: CI 조회 쿼리 (v1, published)
✅ MAPPING: CI 정보 매핑 (v1, published)
✅ PROMPT: ci_planner (v3, published) - 기본 제공
✅ POLICY: 기본 OPS 정책 (v1, published)
✅ SCREEN: default (v1, published) - 기본 제공
```

---

### 5.11 Tool Asset 생성/테스트/발행 (현재 운영 핵심)

`Tool`은 EXECUTE 단계에서 실제 조회/호출을 수행하는 실행 단위다.

**경로**: Admin → Tools (`/admin/tools`)

#### Step 1: Tool 생성

1. `+ New Tool` 클릭
2. 필수 입력:
   - Name: `device_metric_tool`
   - Tool Type: `database_query` (또는 `http_api`, `graph_query`, `python_script`)
   - Description: 검색 키워드 포함 설명(LLM 도구 선택 품질에 직접 영향)
3. 필요 시 `tool_catalog_ref` 연결

#### Step 2: 입력 스키마/설정 정의

1. `tool_config` JSON 작성
2. `tool_input_schema` JSON 작성
3. 문법 오류가 없도록 저장 전 JSON validation 확인

#### Step 3: Tool 테스트

1. 목록에서 Tool 선택
2. 우측 `ToolTestPanel`에서 테스트 payload 입력
3. 실행 결과/오류/응답시간 확인

#### Step 4: 발행

1. 테스트 통과 후 `Publish`
2. 이후 trace에서 해당 Tool 호출 여부 확인

**검증 포인트**:
- Tool 테스트가 동일 입력에서 안정적으로 성공한다.
- Inspector의 `tool_calls`에 신규 Tool명이 노출된다.

---

### 5.12 Catalog 점검 (Tool 품질 보정)

도구가 DB 질의를 수행하는 경우 Catalog 최신성은 정확도에 직접 영향을 준다.

**경로**: Admin → Catalogs (`/admin/catalogs`)

#### Step 1: Catalog 선택

1. source_ref가 올바른 Catalog 선택
2. 상태(`scan_status`) 확인

#### Step 2: 스캔 실행

1. `Scan` 실행
2. table/column 메타데이터 갱신 확인

#### Step 3: 테이블 사용 가능 여부 점검

1. 필요한 테이블이 catalog에 존재하는지 확인
2. 비활성 테이블이면 toggle 상태 점검

**검증 포인트**:
- 도구가 존재하지 않는 테이블/컬럼을 참조하지 않는다.
- 도구 수정 없이도 catalog 갱신 후 질의 정확도가 개선된다.

---

## 6. Test Mode와 Asset Override

> **목표**: Asset 수정 없이 즉시 테스트하여, 어떤 Asset이 결과에 영향을 주는지 이해한다.

### 6.1 Test Mode의 의미

**Test Mode**는 발행(Published) Asset을 수정하지 않고, **특정 버전이나 Draft Asset을 Override하여 실행**하는 기능이다.

**핵심 원칙**:
- 운영 환경에 영향 없음 (Published Asset은 그대로)
- 모든 Override는 **새로운 Trace 생성** → 비교 가능
- Override는 Stage 단위로 영향 범위가 명확함

### 6.2 Asset Override Drawer 사용법

**경로**: /ops 페이지에서 질의 실행 후

#### 시나리오: Resolver 추가 효과 테스트

**상황**:
- 첫 질의에서 EXECUTE Stage가 ⚠ 경고 (Resolver 미설정)
- Resolver를 추가했지만, 발행 전에 효과를 확인하고 싶음

**단계**:

1. **Asset Override Drawer 열기**
   - OPS 페이지 우측 상단 **"Asset Override"** 버튼 클릭 (또는 ⚙ 아이콘)
   - Drawer가 우측에서 슬라이드인

2. **Override 설정**
   ```
   ┌──────────────────────────────────────────┐
   │ Asset Override                            │
   ├──────────────────────────────────────────┤
   │ Quick Presets                             │
   │ ○ Plan Prompt만 변경                     │
   │ ○ Execute Query 변경                     │
   │ ● Custom                                  │
   │                                           │
   │ Custom Override                           │
   │ Resolver  [None → ci_resolver (v1)]       │
   │ ↓ Affected Stages:                        │
   │   ROUTE+PLAN 🔄 → VALIDATE → EXECUTE 🔄  │
   │                                           │
   │ Baseline Trace: abc123 ▼ (자동 선택)     │
   │ [Run Test] [Cancel]                       │
   └──────────────────────────────────────────┘
   ```

3. **Resolver 선택**
   - "Resolver" 드롭다운 클릭
   - `ci_resolver (v1, draft)` 선택
   - Affected Stages 확인: ROUTE+PLAN, EXECUTE 표시

4. **Test 실행**
   - **"Run Test"** 버튼 클릭
   - 질문은 이전과 동일: "GT-01이 뭐야?"
   - 새로운 Trace 생성: `def456`

5. **결과 비교**
   - Inspector 자동 열림
   - Baseline (abc123) vs New (def456) 비교 뷰 표시

   **EXECUTE Stage Diff**:
   ```
   BEFORE (abc123):
   warnings: ["Resolver not configured, using raw ci_code"]

   AFTER (def456):
   warnings: []
   info: ["Resolved GT-01 → gas_turbine_unit_1"]
   ```

6. **Asset 발행 결정**
   - 결과가 개선되었으면 → Resolver Asset 발행
   - Admin → Assets → Resolvers → `ci_resolver` → **"Publish"**

**파일 위치**:
- Asset Override Drawer: [apps/web/src/components/ops/AssetOverrideDrawer.tsx:49](apps/web/src/components/ops/AssetOverrideDrawer.tsx#L49)

---

### 6.3 Isolated Stage Test

**의미**: 전체 Pipeline이 아닌 **특정 Stage만 실행**하여 테스트

**사용 시나리오**:
- COMPOSE Stage의 Mapping만 변경하고 싶음
- EXECUTE Stage의 결과는 그대로 사용하되, Mapping 효과만 확인

**단계**:

1. **Inspector에서 Trace 선택**
   - Admin → Inspector
   - 이전 실행 Trace `abc123` 선택

2. **Stage 선택**
   - Timeline에서 **COMPOSE** Stage 클릭
   - Stage Card 하단 **"Run Isolated Test"** 버튼 클릭

3. **Isolated Test 설정**
   ```
   ┌──────────────────────────────────────────┐
   │ Isolated Stage Test: COMPOSE              │
   ├──────────────────────────────────────────┤
   │ Input Source                              │
   │ Trace: abc123                             │
   │ Input Stage: EXECUTE output (자동 선택)   │
   │                                           │
   │ Input Preview                             │
   │ tool_results: 3 | references: 5           │
   │                                           │
   │ Override                                  │
   │ Mapping: [default_ci_mapping (v1)        │
   │           → ci_mapping_v2 (draft)]        │
   │                                           │
   │ [Run Isolated Test]                       │
   └──────────────────────────────────────────┘
   ```

4. **Mapping 선택**
   - Mapping 드롭다운: `ci_mapping_v2 (draft)` 선택

5. **실행**
   - **"Run Isolated Test"** 버튼 클릭
   - COMPOSE Stage만 재실행 (EXECUTE는 건너뜀)

6. **결과 Diff**
   ```
   BEFORE (v1):
   blocks: [
     {type: "text", content: "GT-01은..."},
     {type: "table", rows: [...]}
   ]

   AFTER (v2):
   blocks: [
     {type: "text", content: "🔧 GT-01은..."},
     {type: "chart", series: [...]},  ← 추가됨
     {type: "table", rows: [...]}
   ]
   ```

7. **적용 결정**
   - **"Apply"** 버튼 클릭 → Mapping v2 발행
   - **"Discard"** 버튼 클릭 → 변경 취소

**핵심 이점**:
- 전체 Pipeline 재실행 불필요 (시간 절약)
- Stage 간 의존성 명확히 이해
- 안전한 실험 (이전 Stage 결과는 불변)

---

### 6.4 Quick Presets 활용

**Asset Override Drawer**의 Quick Presets는 자주 사용하는 Override 패턴을 제공한다.

```
○ Plan Prompt만 변경
  → Affects: ROUTE+PLAN, VALIDATE
  → Use Case: 질의 해석 로직 개선

○ Execute Query 변경
  → Affects: EXECUTE, COMPOSE
  → Use Case: 데이터 조회 로직 수정

○ Screen만 변경
  → Affects: PRESENT
  → Use Case: UI 레이아웃 변경

● Custom
  → 자유로운 조합
```

**사용법**:
1. Preset 선택
2. 자동으로 해당 Asset 드롭다운 활성화
3. 버전 선택
4. "Run Test" 실행

---

## 7. Inspector를 통한 Trace 분석

> **목표**: Execution Trace를 운영 도구로 사용하여, 분석 → 수정 → 재실행 순환을 완성한다.

### 7.1 Inspector 페이지 구조

**경로**: Admin → Inspector 또는 `/admin/inspector`

**화면 구성**:

```
┌──────────────────────────────────────────────────────────────────────┐
│ Inspector                                          [Filter: All ▼]   │
├─────────────────┬────────────────────────────────────────────────────┤
│ Trace List      │  Selected Trace: f5e6d7c8 (2026-01-25 14:30)      │
│                 │                                                    │
│ f5e6d7c8 ORCH✓ │  Pipeline Visualization                            │
│ abc123   DIR ✓ │  ROUTE+PLAN → VALIDATE → EXECUTE → COMPOSE → PRESENT│
│ def456   REJ ✗ │   120ms✓      15ms✓      450ms⚠     85ms✓    12ms✓│
│ ghi789   ORCH⚠ │                     ↳ REPLAN #1 (empty_result)     │
│                 │                                                    │
│                 │  Selected Stage: EXECUTE                           │
│                 │  ┌─────────────────────────────────────────────┐  │
│                 │  │ Input | Output | Diagnostics | Applied Assets│  │
│                 │  ├─────────────────────────────────────────────┤  │
│                 │  │ ... Stage details ...                       │  │
│                 │  └─────────────────────────────────────────────┘  │
│                 │                                                    │
│                 │  Replan Events (1)                                 │
│                 │  #1: empty_result → AUTO_RETRY                     │
│                 │     Trigger: EXECUTE returned 0 rows               │
│                 │     Patch Diff: [View]                             │
│                 │                                                    │
│                 │  [Run with Override] [Open Isolated Test]          │
└─────────────────┴────────────────────────────────────────────────────┘
```

**파일 위치**:
- Inspector 페이지: [apps/web/src/app/admin/inspector/page.tsx](apps/web/src/app/admin/inspector/page.tsx)
- Trace Service: [apps/api/app/modules/inspector/service.py](apps/api/app/modules/inspector/service.py)

---

### 7.2 Trace List 필터링

**Filter 옵션**:

```
Route Filter:
- All
- ORCH (Orchestration)
- DIRECT (Direct Answer)
- REJECT (Rejected)

Status Filter:
- All
- Success
- Warning
- Error

Replan Filter:
- All
- With Replans
- No Replans

Date Range:
- Last 24 hours
- Last 7 days
- Custom range
```

**사용법**:
1. 우측 상단 **"Filter"** 드롭다운 클릭
2. 조건 선택 (예: Route=ORCH, Status=Warning)
3. Trace List 자동 업데이트
4. 분석할 Trace 선택

---

### 7.3 Stage 상세 분석

#### Input 탭

**EXECUTE Stage Input 예시**:

```json
{
  "stage": "execute",
  "applied_assets": {
    "query": "ci_lookup:v5",
    "source": "postgres_main:v1"
  },
  "params": {
    "plan": {
      "intent": "config",
      "ci_codes": ["GT-01"],
      "tools": ["ci_tool"]
    }
  },
  "prev_output": {
    "validated_plan": {...}
  }
}
```

**이해할 점**:
- `applied_assets`: 이 Stage가 사용한 Asset의 **정확한 버전**
- `params.plan`: ROUTE+PLAN Stage의 출력
- `prev_output`: 이전 Stage (VALIDATE)의 출력

#### Output 탭

**EXECUTE Stage Output 예시**:

```json
{
  "stage": "execute",
  "result": {
    "tool_results": [
      {
        "tool": "ci_tool",
        "result": {...}
      }
    ]
  },
  "diagnostics": {
    "status": "warning",
    "warnings": ["Resolver not configured"],
    "errors": [],
    "empty_flags": {"result_empty": false},
    "counts": {"references": 2, "rows": 1}
  },
  "references": [
    {"kind": "row", "title": "ci_master.GT-01", "payload": {...}}
  ],
  "duration_ms": 450
}
```

**이해할 점**:
- `diagnostics.status`: `ok` | `warning` | `error`
- `diagnostics.counts`: 참조 수, 행 수 (빈 결과 판단 기준)
- `references`: **null 금지** (항상 배열)

#### Diagnostics 탭

**경고 및 에러 상세**:

```
Status: warning

Warnings:
- Resolver not configured, using raw ci_code
- Query execution time (450ms) exceeds target (300ms)

Empty Flags:
- result_empty: false
- references_empty: false

Counts:
- references: 2
- rows: 1
- tool_calls: 1
```

**조치**:
- 경고 확인 → Asset 수정 필요성 판단
- Empty Flags 확인 → Replan Trigger 이해
- Counts 확인 → 성능 및 데이터 품질 평가

#### Applied Assets 탭

**사용된 Asset 목록**:

```
Query: ci_lookup (v5)
  → [View Asset] [Edit Asset] [Test with v6]

Source: postgres_main (v1)
  → [View Asset] [Test Connection]

(Other stages)
Prompt: ci_planner (v3)
Mapping: default_ci_mapping (v1)
```

**조치**:
- **[View Asset]**: Asset 상세 보기 (읽기 전용)
- **[Edit Asset]**: Asset 편집 페이지로 이동
- **[Test with vN]**: 다른 버전으로 Override Test

---

### 7.4 Replan Events 분석

**Replan Event 구조**:

```json
{
  "event_type": "replan_execution",
  "stage_name": "execute",
  "trigger": {
    "trigger_type": "empty_result",
    "reason": "CI lookup returned 0 rows for ci_code=GT-01",
    "severity": "medium",
    "timestamp": "2026-01-25T14:35:20Z"
  },
  "patch": {
    "before": {
      "plan.scope.ci_codes": ["GT-01"]
    },
    "after": {
      "plan.scope.ci_codes": ["gas_turbine_unit_1"]
    }
  },
  "decision_metadata": {
    "trace_id": "ghi789",
    "should_replan": true,
    "evaluation_time": 15
  }
}
```

**Replan Timeline 시각화**:

```
Timeline:
─────────────────────────────────────────────────────────────
T+0ms:    ROUTE+PLAN ✓
T+120ms:  VALIDATE ✓
T+135ms:  EXECUTE ⚠ (0 rows)
          ↓
T+150ms:  REPLAN #1 (Trigger: empty_result)
          Patch: ci_codes ["GT-01" → "gas_turbine_unit_1"]
          ↓
T+170ms:  EXECUTE ✓ (1 row)
T+620ms:  COMPOSE ✓
T+705ms:  PRESENT ✓
─────────────────────────────────────────────────────────────
```

**Patch Diff 상세**:

```
Before:
{
  "plan": {
    "scope": {
      "ci_codes": ["GT-01"]
    }
  }
}

After:
{
  "plan": {
    "scope": {
      "ci_codes": ["gas_turbine_unit_1"]
    }
  }
}

Explanation:
Resolver가 "GT-01"을 "gas_turbine_unit_1"로 변환했지만,
첫 실행에서는 적용되지 않았음. Replan에서 적용됨.
```

---

### 7.5 Inspector에서 바로 수정하기

**시나리오**: EXECUTE Stage의 경고를 해결하고 싶음

**경로**: Inspector → Trace 선택 → EXECUTE Stage 클릭

**단계**:

1. **Applied Assets 확인**
   - Query: `ci_lookup (v5)`
   - Diagnostics: `warnings: ["Slow query"]`

2. **Asset 수정**
   - **[Edit Asset]** 버튼 클릭
   - Admin → Assets → Queries → `ci_lookup` 상세 페이지로 이동
   - SQL 최적화 (인덱스 추가, 불필요한 JOIN 제거)
   - **"Save Draft"** 클릭

3. **Isolated Test 실행**
   - Inspector로 돌아가기
   - EXECUTE Stage Card → **"Run Isolated Test"** 버튼
   - Query 드롭다운: `ci_lookup (v6, draft)` 선택
   - **"Run Isolated Test"** 실행

4. **결과 비교**
   ```
   BEFORE (v5):
   duration_ms: 450
   warnings: ["Slow query"]

   AFTER (v6):
   duration_ms: 180
   warnings: []
   ```

5. **발행**
   - 성능 개선 확인 → Admin → Assets → `ci_lookup` → **"Publish"**

**핵심**: Inspector → Edit → Test → Publish 순환이 UI에서 끊기지 않음

---

## 8. Control Loop 이해 (Replan/Rerun)

> **목표**: Replan과 Rerun의 차이를 이해하고, 시스템이 자동으로 보정하는 메커니즘을 학습한다.

### 8.1 Replan vs Rerun

| 구분 | Replan | Rerun |
|------|--------|-------|
| **트리거** | 시스템 자동 (empty_result, tool_error 등) | 사용자 수동 (Override, Isolated Test) |
| **범위** | 특정 Stage만 재실행 | 전체 Pipeline 또는 특정 Stage |
| **목적** | 실행 중 보정/재시도 | 실험 및 검증 |
| **Trace** | 동일 Trace 내 replan_events 기록 | 새로운 Trace 생성 |

### 8.2 Replan Triggers (표준화)

**파일 위치**: [apps/api/app/modules/ops/schemas.py](apps/api/app/modules/ops/schemas.py) (lines 228-244)

| Trigger | Stage | 의미 | Severity |
|---------|-------|------|----------|
| `slot_missing` | ROUTE+PLAN | Plan에 필수 파라미터 누락 | high |
| `empty_result` | EXECUTE | 데이터 조회 결과 0행 | medium |
| `tool_error_retryable` | EXECUTE | 도구 실행 실패 (재시도 가능) | medium |
| `tool_error_fatal` | EXECUTE | 도구 실행 실패 (복구 불가능) | critical |
| `policy_blocked` | VALIDATE | 정책 위반 | high |
| `low_evidence` | COMPOSE | 참조 수 부족 | low |
| `present_limit` | PRESENT | 블록 수 제한 초과 | low |

### 8.3 Replan Limits

**Policy Asset에서 정의**:

```json
{
  "replan_policy": {
    "max_replans": 3,
    "allowed_triggers": [
      "empty_result",
      "tool_error_retryable",
      "timeout"
    ],
    "min_interval_seconds": 60,
    "cooling_period_seconds": 300
  }
}
```

**파일 위치**: [apps/api/app/modules/ops/services/control_loop.py](apps/api/app/modules/ops/services/control_loop.py)

**적용 규칙**:
- `max_replans`: 최대 재계획 횟수 (무한 루프 방지)
- `allowed_triggers`: 허용된 Trigger만 Replan 실행
- `min_interval_seconds`: 연속 Replan 간 최소 간격
- `cooling_period_seconds`: 쿨링 기간 (critical severity는 예외)

### 8.4 Replan Patch Diff 이해

**Patch 구조**:

```json
{
  "before": {
    "plan.scope.ci_codes": ["GT-01"],
    "plan.filters.time_range": "last_24h"
  },
  "after": {
    "plan.scope.ci_codes": ["gas_turbine_unit_1"],
    "plan.filters.time_range": "last_48h"
  }
}
```

**변경 사항 해석**:
- CI 코드가 Resolver에 의해 정규화됨
- 시간 범위가 확장됨 (데이터 부족으로 인한 보정)

**OPS Timeline에서 확인**:

```
Replan #1 (T+150ms)
Trigger: empty_result (medium)
Stage: EXECUTE
Reason: "CI lookup returned 0 rows"

Patch Diff:
  ci_codes: ["GT-01"] → ["gas_turbine_unit_1"]

Decision: AUTO_RETRY
Outcome: Success (1 row)
```

**파일 위치**: [apps/web/src/components/ops/ReplanTimeline.tsx](apps/web/src/components/ops/ReplanTimeline.tsx)

### 8.5 Replan 자동 보정 예시

#### 예시 1: Resolver 자동 적용

**시나리오**: 사용자가 "GT-01"로 질의했지만, DB에는 "gas_turbine_unit_1"로 저장됨

**실행 흐름**:

```
1. ROUTE+PLAN: Plan 생성 (ci_codes: ["GT-01"])
2. VALIDATE: Plan 승인
3. EXECUTE: Query 실행 → 0 rows
4. REPLAN Trigger: empty_result
5. REPLAN Action: Resolver 적용 (GT-01 → gas_turbine_unit_1)
6. EXECUTE (재실행): Query 실행 → 1 row
7. COMPOSE: 결과 조합
8. PRESENT: 답변 표시
```

**Trace 기록**:

```json
{
  "replan_events": [
    {
      "event_type": "replan_execution",
      "stage_name": "execute",
      "trigger": {
        "trigger_type": "empty_result",
        "reason": "CI lookup returned 0 rows for ci_code=GT-01"
      },
      "patch": {
        "before": {"plan.scope.ci_codes": ["GT-01"]},
        "after": {"plan.scope.ci_codes": ["gas_turbine_unit_1"]}
      },
      "decision_metadata": {
        "should_replan": true,
        "resolver_applied": true
      }
    }
  ]
}
```

#### 예시 2: Tool Error Retry

**시나리오**: 데이터베이스 일시적 연결 실패

**실행 흐름**:

```
1-3. (ROUTE+PLAN → VALIDATE → EXECUTE)
4. EXECUTE: Tool 실행 → ConnectionError
5. REPLAN Trigger: tool_error_retryable
6. REPLAN Action: 재시도 (3초 대기)
7. EXECUTE (재실행): Tool 실행 → Success
```

**Replan Event**:

```json
{
  "trigger": {
    "trigger_type": "tool_error_retryable",
    "reason": "Database connection timeout",
    "severity": "medium"
  },
  "patch": {
    "before": {"tool_config.timeout": 5000},
    "after": {"tool_config.timeout": 10000}
  },
  "decision_metadata": {
    "retry_count": 1,
    "max_retries": 3,
    "backoff_ms": 3000
  }
}
```

### 8.6 Replan 무한 루프 방지

**Policy 강제 규칙**:

```python
# apps/api/app/modules/ops/services/control_loop.py

def should_replan(trigger: ReplanTrigger) -> bool:
    # 1. Max replans 초과 확인
    if replan_count >= max_replans:
        return False

    # 2. Allowed triggers 확인
    if trigger.trigger_type not in allowed_triggers:
        return False

    # 3. Minimum interval 확인
    if time_since_last_replan < min_interval_seconds:
        return False

    # 4. Cooling period 확인 (critical severity 예외)
    if time_since_first_replan < cooling_period_seconds:
        if trigger.severity != "critical":
            return False

    return True
```

**실패 시 동작**:
- Replan 거부 → 현재 결과로 종료
- Diagnostics에 "Replan limit exceeded" 기록
- 사용자에게 경고 표시

---

## 9. 문제 해결 패턴

### 9.1 증상: "Route: DIRECT인데 데이터가 없어요"

**원인**: ROUTE+PLAN Stage에서 LLM이 Direct Answer로 분기

**진단**:
1. Inspector → Trace 선택
2. ROUTE+PLAN Stage 클릭
3. Output 확인:
   ```json
   {
     "kind": "direct",
     "direct_answer": "GT-01은 가스터빈입니다."
   }
   ```

**해결**:
- Prompt Asset 수정 필요
- Template에 "항상 데이터를 조회하라" 지시 추가
- 또는 Policy에서 Direct Route 제한

**Asset Override Test**:
1. Asset Override Drawer 열기
2. Prompt: `ci_planner (v3) → v4 (draft)`
3. "Run Test" 실행
4. 결과: Route=ORCH 확인
5. Prompt v4 발행

---

### 9.2 증상: "EXECUTE Stage가 항상 0 rows"

**원인**: Query, Resolver, 또는 데이터 부재

**진단 경로**:

#### 단계 1: Resolver 확인

1. Inspector → EXECUTE Stage
2. Diagnostics: `warnings: ["Resolver not configured"]` 확인
3. Applied Assets: Resolver 없음

**해결**: Resolver Asset 추가 및 발행

#### 단계 2: Query 확인

1. EXECUTE Stage → Applied Assets
2. Query: `ci_lookup (v5)` → **[View Asset]** 클릭
3. SQL 확인:
   ```sql
   WHERE ci_code = :ci_code
   ```
4. Input 확인:
   ```json
   {
     "params": {
       "ci_code": "GT-01"
     }
   }
   ```

**해결**: SQL 또는 파라미터 바인딩 수정

#### 단계 3: 데이터베이스 직접 확인

1. Admin → Assets → Sources → `postgres_main`
2. **"Test Connection"** 클릭 → 연결 확인
3. SQL 클라이언트에서 직접 쿼리:
   ```sql
   SELECT * FROM ci_master WHERE ci_code = 'GT-01';
   ```
4. 결과 없음 → 데이터 입력 필요

---

### 9.3 증상: "Replan이 무한 반복돼요"

**원인**: Replan Limits 미설정 또는 Policy 버그

**진단**:
1. Inspector → Trace 선택
2. Replan Events 확인:
   ```
   Replan #1: empty_result
   Replan #2: empty_result
   Replan #3: empty_result
   (stopped by max_replans=3)
   ```

**해결**:
1. Admin → Assets → Policies → `plan_budget`
2. Limits 확인:
   ```json
   {
     "replan_policy": {
       "max_replans": 3  ← 올바름
     }
   }
   ```
3. Replan Trigger 근본 원인 해결:
   - empty_result → Query 수정
   - tool_error → Source 연결 수정

---

### 9.4 증상: "Asset Override가 적용 안 돼요"

**원인**: Override 형식 오류 또는 Stage 불일치

**진단**:
1. Asset Override Drawer
2. Override 설정 확인:
   ```
   Query: [ci_lookup (v5) → v6 (draft)]
   ```
3. Affected Stages 확인: EXECUTE 🔄

**테스트**:
1. "Run Test" 실행
2. Inspector → 새 Trace
3. EXECUTE Stage → Applied Assets 확인:
   ```
   query: ci_lookup (v5)  ← v6이 아님!
   ```

**원인 파악**:
- Backend 로그 확인:
  ```
  [ERROR] Asset override format invalid: "ci_lookup" → should be "query:ci_lookup"
  ```

**해결**:
- Override 형식: `{asset_type}:{asset_name}` 사용
- 예: `query:ci_lookup`

**파일 위치**: [apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py](apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py) (lines 57-79)

---

### 9.5 증상: "Inspector에서 Trace를 찾을 수 없어요"

**원인**: Trace 저장 실패 또는 Trace ID 불일치

**진단**:
1. OPS 페이지 → 질의 실행 후 Trace ID 복사
2. Inspector 검색창에 Trace ID 붙여넣기
3. "No traces found" 메시지

**해결**:

#### 옵션 1: Trace 저장 확인

- Backend 로그 확인:
  ```
  [INFO] Persisting trace: f5e6d7c8
  [ERROR] Database write failed: connection timeout
  ```
- DB 연결 문제 → Source 수정

#### 옵션 2: Trace 보관 기간 초과

- Policy 확인:
  ```json
  {
    "trace_retention_days": 7
  }
  ```
- 7일 이전 Trace는 자동 삭제됨

#### 옵션 3: Trace ID 형식 오류

- 올바른 형식: `uuid-v4` (예: `f5e6d7c8-9abc-def0-1234-567890abcdef`)
- 짧은 ID (예: `abc123`)는 시스템 내부 ID가 아님

---

## 10. 종합 실습: E2E 학습 시나리오

> **목표**: 처음부터 끝까지 전체 흐름을 실습하여, OPS 오케스트레이션의 완전한 이해를 달성한다.

### 시나리오: 새로운 데이터 소스 추가 및 질의응답 구축

**요구사항**:
- 새로운 TimescaleDB를 추가하여 메트릭 데이터 조회
- 사용자 질의: "최근 1주일 GT-01의 CPU 사용률 평균은?"

---

### Phase 1: 데이터 준비

**Step 1-1: Source Asset 생성**
1. Admin → Assets → "+ New Asset"
2. Type: Source, Name: `Metrics TimescaleDB`, Scope: `metrics`
3. Connection: Host=`metrics-db.internal`, Port=5432, Database=`metrics_production`
4. Test Connection → Publish

**Step 1-2: Schema Scan**
1. Admin → Assets → Sources → `Metrics TimescaleDB` 선택
2. "Rescan Schema" 클릭
3. 결과 확인: 테이블 `metric_timeseries` 발견
4. Schema Asset 자동 생성 → Publish

**Step 1-3: Resolver 설정**
1. 이미 존재하는 `ci_resolver` 사용 (CI 코드 정규화)

---

### Phase 2: Query 및 Mapping 작성

**Step 2-1: Query Asset 생성**
1. Admin → Assets → "+ New Asset"
2. Type: Query, Name: `Metric Average Query`, Scope: `metric`
3. SQL:
   ```sql
   SELECT
     AVG(value) as avg_value,
     metric_name,
     ci_id
   FROM metric_timeseries
   WHERE ci_id = :ci_id
     AND metric_name = :metric_name
     AND timestamp >= NOW() - INTERVAL ':time_range'
   GROUP BY metric_name, ci_id
   ```
4. Parameters:
   ```json
   {
     "ci_id": {"type": "uuid", "required": true},
     "metric_name": {"type": "string", "required": true},
     "time_range": {"type": "string", "default": "7 days"}
   }
   ```
5. Publish

**Step 2-2: Mapping Asset 생성**
1. Admin → Assets → "+ New Asset"
2. Type: Mapping, Name: `Metric Result Mapping`, Scope: `metric`
3. Content:
   ```json
   {
     "mappings": [
       {
         "source_type": "metric_tool",
         "target_block": "text",
         "template": "{{ci_name}}의 최근 {{time_range}} {{metric_name}} 평균은 {{avg_value}}입니다."
       },
       {
         "source_type": "metric_tool",
         "target_block": "number",
         "field_mapping": {
           "label": "metric_name",
           "value": "avg_value",
           "unit": "percent"
         }
       }
     ]
   }
   ```
4. Publish

---

### Phase 3: 첫 테스트 (Test Mode)

**Step 3-1: OPS 질의 실행**
1. /ops 페이지 접속
2. Mode: **"수치 (metric)"** 선택
3. Question: `최근 1주일 GT-01의 CPU 사용률 평균은?`
4. "메시지 전송" 클릭

**Step 3-2: 결과 분석**
```
Pipeline:
ROUTE+PLAN ✓ → VALIDATE ✓ → EXECUTE ⚠ → COMPOSE ✓ → PRESENT ✓

EXECUTE Stage (경고):
warnings: ["Query uses old schema, performance may be slow"]
duration_ms: 1200
```

**Step 3-3: Query 개선**
1. Inspector → EXECUTE Stage → Query: `Metric Average Query (v1)` → **[Edit Asset]**
2. SQL 최적화 (인덱스 활용):
   ```sql
   SELECT
     AVG(value) as avg_value
   FROM metric_timeseries
   WHERE ci_id = :ci_id
     AND metric_name = :metric_name
     AND timestamp >= NOW() - INTERVAL ':time_range'
   GROUP BY metric_name
   ORDER BY timestamp DESC
   ```
3. Save Draft (v2)

**Step 3-4: Isolated Stage Test**
1. Inspector → EXECUTE Stage → "Run Isolated Test"
2. Query: `v1 → v2 (draft)` 선택
3. Run Test

**Step 3-5: 결과 비교**
```
BEFORE (v1):
duration_ms: 1200
warnings: ["Slow query"]

AFTER (v2):
duration_ms: 350
warnings: []
```

**Step 3-6: 발행**
- Query v2 발행

---

### Phase 4: E2E 재검증

**Step 4-1: 동일 질의 재실행**
1. /ops 페이지
2. Question: `최근 1주일 GT-01의 CPU 사용률 평균은?`
3. "메시지 전송"

**Step 4-2: 결과 확인**
```
Pipeline:
ROUTE+PLAN ✓ → VALIDATE ✓ → EXECUTE ✓ → COMPOSE ✓ → PRESENT ✓
  120ms        15ms         350ms       85ms        12ms

Total: 582ms

Answer:
📊 Gas Turbine Unit 1의 최근 7 days CPU 사용률 평균은 67.3%입니다.

┌─────────────────┬──────────┐
│ Metric          │ Value    │
├─────────────────┼──────────┤
│ cpu_usage       │ 67.3%    │
└─────────────────┴──────────┘

Data Sources:
• source: Metrics TimescaleDB (v1)
• query: Metric Average Query (v2)
• mapping: Metric Result Mapping (v1)
```

**Step 4-3: Trace 저장 확인**
- Trace ID 복사
- Inspector → 검색 → Trace 발견
- Applied Assets 확인: 모두 최신 버전 사용

---

### Phase 5: 회귀 테스트 설정 (선택사항)

**Step 5-1: Baseline Trace 설정**
1. Admin → Regression
2. "+ Add Test Case"
3. Name: `Metric Average Test`
4. Baseline Trace: (방금 생성한 Trace ID)
5. Expected:
   ```json
   {
     "route": "orch",
     "stages_ok": ["route_plan", "validate", "execute", "compose", "present"],
     "min_references": 1,
     "max_duration_ms": 1000
   }
   ```
6. Save

**Step 5-2: Asset 수정 후 회귀 테스트**
1. Query Asset 수정 (v3 작성)
2. Admin → Regression → "Run All Tests"
3. 결과:
   ```
   Metric Average Test: PASS
   - Duration: 350ms (baseline: 582ms) ✓
   - References: 1 (expected: min 1) ✓
   - All stages: OK ✓
   ```

---

## 11. 체크리스트

### 11.1 학습 완료 체크리스트

```
□ Pipeline Stage 이해 (ROUTE+PLAN → VALIDATE → EXECUTE → COMPOSE → PRESENT)
□ Direct/Orch/Reject 분기 이해
□ Asset-Stage Binding Map 이해
□ Source, Schema, Resolver, Query, Mapping 각각의 역할 이해
□ OPS 페이지에서 질의 실행 및 Pipeline Timeline 확인
□ Inspector를 통한 Trace 분석
□ Asset Override Drawer 사용
□ Isolated Stage Test 실행
□ Replan Event 이해 및 분석
□ E2E 시나리오 실습 완료
```

---

## 12. 참고 자료

### 12.1 핵심 파일 위치

| 컴포넌트 | 파일 위치 |
|---------|----------|
| **OPS 페이지** | [apps/web/src/app/ops/page.tsx:284](apps/web/src/app/ops/page.tsx#L284) |
| **Inspector** | [apps/web/src/app/admin/inspector/page.tsx](apps/web/src/app/admin/inspector/page.tsx) |
| **Asset Registry** | [apps/web/src/app/admin/assets/page.tsx](apps/web/src/app/admin/assets/page.tsx) |
| **Stage Executor** | [apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py](apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py) |
| **Planner (LLM)** | [apps/api/app/modules/ops/services/ci/planner/planner_llm.py](apps/api/app/modules/ops/services/ci/planner/planner_llm.py) |
| **Control Loop** | [apps/api/app/modules/ops/services/control_loop.py](apps/api/app/modules/ops/services/control_loop.py) |
| **Trace Service** | [apps/api/app/modules/inspector/service.py](apps/api/app/modules/inspector/service.py) |

### 12.2 개념 설계 문서 연결

- **OPS Orchestration Concepts**: 본 가이드의 기준 문서
- **Pipeline Semantics**: Section 2.1
- **Asset Model**: Section 3
- **Pipeline-Asset Binding**: Section 4
- **Execution Trace**: Section 5
- **Control Loop**: Section 2.4

---

## 완료!

이제 OPS 범용 오케스트레이션 시스템을 **Pipeline 중심 사고방식**으로 이해하고 운영할 수 있습니다. 🎉

**핵심 원칙 요약**:
1. **Pipeline은 Stage의 연쇄**이며, 각 Stage는 명확한 In/Out 계약을 가진다
2. **Asset은 Stage에 바인딩**되어야만 의미를 가진다
3. **Trace는 단일 진실 원천**이며, 모든 분석은 Trace에서 시작한다
4. **Test → Inspect → Fix 순환**이 UI에서 끊기지 않는다

질문이나 문제가 있으면 Inspector를 통해 Trace를 분석하고, Asset Override로 즉시 실험하세요!

---

## 부록: 테스트 결과 상세

**Test Date**: 2026-01-27
**Total Questions**: 99

### RELATION Questions (CI Search) - 25개

| # | Question | Trace ID | Result |
|---|----------|----------|--------|
| 1 | ERP 시스템의 모든 서버를 나열해줘 | 3aff1d34f6144b25b6c204dc6eddfc01 | ✅ 검색 결과 |
| 2 | MES 시스템의 웹 서버 목록을 보여줘 | 48442ad165d5465f9058b74aeb8be936 | ✅ 검색 결과 |
| 3 | SCADA 서버를 조회해줘 | f24c5c2943504a8aaa885665c4f90d8e | ✅ 검색 결과 |
| 4 | active 상태인 서버를 찾아줘 | 2be80f7ac79d48ed8de288d57d8190bb | ✅ 검색 결과 |
| 5 | zone-a에 위치한 서버를 나열해줘 | 2ebda3e58dad47e6bd9f13f23f904073 | ✅ 검색 결과 |

*(전체 99개 질문은 UNIVERSAL_ORCHESTRATION_COMPLETE 참조)*

### Inspector Trace 링크

각 trace_id는 Inspector에서 상세 실행 내역을 확인할 수 있습니다:

- Inspector URL: `/admin/inspector?trace_id={trace_id}`
- 예시: `/admin/inspector?trace_id=3aff1d34f6144b25b6c204dc6eddfc01`

### Test Command

```python
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_question(question: str, mode: str):
    """
    mode == "all" 이면 /ops/ask, 나머지는 /ops/query 사용.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        if mode == "all":
            # 전체 모드: 오케스트레이션 엔드포인트
            resp = await client.post(
                f"{BASE_URL}/ops/ask",
                json={"question": question},
            )
        else:
            # 개별 모드: 모드 디스패처 엔드포인트
            resp = await client.post(
                f"{BASE_URL}/ops/query",
                json={"question": question, "mode": mode},
            )
        if resp.status_code == 200:
            data = resp.json()
            meta = data.get("data", {}).get("answer", {}).get("meta", {})
            return not meta.get("fallback", False) and "mock" not in meta.get("used_tools", [])
        return False
```

---

## NEW: Error Handling & Recovery

> **Effective**: 2026-02-14 (P0-4 Deployment)

### What Changed

The OPS system now includes comprehensive error handling and automatic recovery mechanisms. Instead of crashing on transient failures, the system automatically retries and falls back to alternative data sources.

### Error Recovery Patterns

#### 1. LLM Circuit Breaker (Orchestration Mode)

When the LLM service (used for planning in "all" mode) fails:

```
User Question
    ↓
Try LLM Planning (Attempt 1)
    ├─ Success: Continue execution
    └─ Failure (timeout/500): Try Attempt 2
         ├─ Success: Continue execution
         └─ Failure: Try Attempt 3
              ├─ Success: Continue execution
              └─ Failure: Fall back to keyword-based planning
                   ↓
                   Execute with fallback mode
```

**User Experience**: Query takes longer but still returns results (no error shown)

#### 2. Data Source Fallback (All Modes)

When primary data source fails, system automatically tries alternatives:

```
Priority 1: metric_timeseries (PostgreSQL actual data)
    ├─ Available: Use it ✅
    └─ Failed/Unavailable: Try next

Priority 2: tool (Asset Registry tool-based queries)
    ├─ Available: Use it ✅
    └─ Failed/Unavailable: Try next

Priority 3: topology_fallback (Neo4j derived estimates)
    ├─ Available: Use it (marked as fallback)
    └─ Failed: Return error "Unable to retrieve data"
```

**User Experience**: Response includes `data_quality` indicator showing data source used

#### 3. Query Execution Retry (DirectQueryTool)

Each SQL query is attempted up to 3 times:

```
Execute Query
    ├─ Success (status 200): Return results
    └─ Transient Error (timeout/connection reset):
         ├─ Retry 1: Wait 1s, retry
         │   ├─ Success: Return results
         │   └─ Transient Error: Continue
         ├─ Retry 2: Wait 2s, retry
         │   ├─ Success: Return results
         │   └─ Transient Error: Continue
         └─ Retry 3: Wait 4s, retry
             ├─ Success: Return results
             └─ Persistent Error: Return error
```

### Handling Common Error Scenarios

#### Scenario 1: LLM Service Unavailable (Orchestration Mode)

**What User Sees**:
```
Question: "Give me overall system health"
Status: Processing... (takes 5-10 seconds longer than usual)
Result: Returns answer using keyword-based fallback instead of LLM
Meta: { "fallback": true, "fallback_reason": "LLM service unavailable" }
```

**What to Do**:
1. Check `/admin/logs` for error details
2. Verify LLM service is running
3. Retry query (automatic retry may have worked)

#### Scenario 2: Metric Data Source Offline

**What User Sees**:
```
Mode: Metric
Result: Metric query returns with data_source indicator
{
  "data_source": "topology_fallback",
  "data_quality": {
    "metrics_available": false,
    "using_fallback": true,
    "note": "Using estimated metrics from topology"
  }
}
```

**What to Do**:
1. Check metric data source connection in `/admin/catalogs`
2. Verify database is online
3. If offline for extended period, notify ops team

#### Scenario 3: SQL Query Fails (Invalid Syntax, Timeout)

**What User Sees**:
```
{
  "success": false,
  "error": "Query execution failed after 3 retries",
  "error_details": {
    "attempts": 3,
    "final_error": "Query timeout after 30 seconds",
    "sql_preview": "SELECT ... FROM ...",
    "suggestion": "Try with narrower time range or fewer CIs"
  }
}
```

**What to Do**:
1. Check query performance in `/admin/explorer`
2. Add LIMIT clause or time filter
3. If query is too complex, split into smaller queries

### Best Practices

1. **Queries are automatically tenant-scoped for security**
   - Never add `WHERE tenant_id = ...` manually
   - System enforces this at SQL validation level

2. **System retries up to 3 times on transient failures**
   - Don't immediately retry if query fails
   - Check logs first to understand root cause

3. **Partial results are returned when some data sources fail**
   - Check `data_quality` field in response
   - If marked as fallback, results may be estimated

4. **Monitor fallback usage in Admin → Observability**
   - High fallback rates indicate data source issues
   - Plan maintenance accordingly

---

## NEW: Data Security

> **Effective**: 2026-02-14 (P0-4 Query Safety Implementation)

### Fundamental Principle

**ALL SQL queries executed through OPS are validated for safety before execution.** The system enforces:
- ✅ Read-only access (no data modification)
- ❌ DDL statements blocked (no schema changes)
- ❌ DCL statements blocked (no permission changes)
- ✅ Tenant isolation enforced (no cross-tenant access)
- ✅ Row limiting enforced (max 10,000 rows per query)

### What This Means for Users

#### You CAN Run:
```sql
-- ✅ SELECT statements
SELECT * FROM servers WHERE status = 'active'

-- ✅ Parameterized queries
SELECT * FROM ci_items WHERE ci_type = :type AND tenant_id = :tenant_id

-- ✅ Complex joins
SELECT s.*, i.status
FROM servers s
LEFT JOIN incidents i ON s.id = i.server_id
WHERE s.tenant_id = :tenant_id

-- ✅ Aggregations
SELECT ci_type, COUNT(*) as count
FROM ci_items
WHERE tenant_id = :tenant_id
GROUP BY ci_type
```

#### You CANNOT Run:
```sql
-- ❌ Data modification
INSERT INTO servers VALUES (...)
UPDATE servers SET status = 'offline' WHERE id = 1
DELETE FROM servers WHERE id = 1

-- ❌ Schema changes
CREATE TABLE new_ci_items (...)
ALTER TABLE servers ADD COLUMN new_field VARCHAR(100)
DROP TABLE incidents

-- ❌ Permission changes
GRANT SELECT ON servers TO user_role
REVOKE DELETE ON incidents FROM user_role

-- ❌ Transaction control
COMMIT
ROLLBACK
BEGIN TRANSACTION

-- ❌ Stored procedures/functions (dangerous keywords)
EXECUTE sp_SomeStoredProc
CALL ProcessData()
```

### Tenant Isolation

Every query is automatically scoped to the requesting user's tenant:

**Before (Manual)**:
```python
# User had to remember to add WHERE clause
query = "SELECT * FROM servers WHERE tenant_id = '" + user_tenant + "'"
```

**After (Automatic)**:
```python
# System validates and enforces tenant_id automatically
# Query: SELECT * FROM servers
# System checks: Does this query attempt cross-tenant access?
# Result: Query is validated with tenant_id enforcement
```

**If User Tries to Access Another Tenant's Data**:
```python
# Query: SELECT * FROM ci_items WHERE tenant_id = 'other-tenant'
# System detects mismatch
# Result: Error - "Query validation failed: tenant_id mismatch"
```

### Query Validation Workflow

When a user runs a query:

```
User submits query
    ↓
DirectQueryTool.execute()
    ↓
validate_direct_query(query, tenant_id, policies...)
    ├─ Check: Is this a SELECT statement?
    │  └─ If NO: Reject with "INSERT/UPDATE/DELETE not allowed"
    │
    ├─ Check: Does query contain DDL keywords?
    │  └─ If YES: Reject with "CREATE/ALTER/DROP not allowed"
    │
    ├─ Check: Does query contain DCL keywords?
    │  └─ If YES: Reject with "GRANT/REVOKE not allowed"
    │
    ├─ Check: Is tenant_id properly scoped?
    │  └─ If MISSING: Add WHERE tenant_id = :tenant_id
    │
    └─ Check: Estimated rows < 10,000?
        └─ If OVER: Reject with "Query would return too many rows"

If all checks pass:
    ↓
Execute query with actual connection
    ↓
Return results
```

### Error Messages & Responses

#### Validation Failed (Before Execution)

```json
{
  "success": false,
  "error": "Query validation failed: INSERT statements not allowed",
  "error_details": {
    "violation_type": "query_safety",
    "violations": ["INSERT statements not allowed"],
    "sql_preview": "INSERT INTO servers VALUES (...)",
    "tenant_id": "tenant-abc123"
  }
}
```

**Actions to Take**:
1. Review the query - it may be trying to modify data
2. If you need data modification, contact admin to use Data API instead
3. Convert to SELECT-only query if possible

#### Tenant Mismatch

```json
{
  "success": false,
  "error": "Query validation failed: tenant_id mismatch",
  "error_details": {
    "violation_type": "tenant_isolation",
    "violations": ["Attempted cross-tenant access"],
    "sql_preview": "SELECT * FROM ci_items WHERE ...",
    "tenant_id": "tenant-abc123"
  }
}
```

**Actions to Take**:
1. System has prevented unauthorized cross-tenant access
2. This is a security feature, not a bug
3. Contact admin if you need to query data from another tenant (rare)

### What If Data Modification Is Needed?

OPS system is **read-only by design** for operational intelligence. For data modifications, use:

1. **Data Modification API** (`POST /api/data/modify`)
   - For authorized bulk updates
   - Requires special permission
   - Fully audited and logged

2. **UI Forms** (in relevant admin sections)
   - For individual record updates
   - User-friendly and validated
   - Recommended for most users

3. **Custom Workflows** (via workflow system)
   - For complex multi-step modifications
   - Requires workflow permissions
   - Fully orchestrated

### Monitoring & Auditing

All query executions are logged:

**View in `/admin/logs`**:
```
Timestamp | User | Tenant | Query | Result | Notes
----------|------|--------|-------|--------|-------
14:32:05  | alice | tenant-1 | SELECT * FROM servers | ✅ Success | 5 rows
14:32:10  | bob   | tenant-2 | INSERT INTO ... | ❌ Blocked | Validation failure
14:32:15  | alice | tenant-1 | SELECT * FROM other-tenant... | ❌ Blocked | Tenant mismatch
```

**Audit Trail**:
- Every query validation
- Every execution attempt (success/failure)
- Query duration and row count
- User and tenant information

### Summary of Key Changes (P0-4)

| Before (Feb 13) | After (Feb 14) |
|---|---|
| SQL validation manual | SQL validation automatic |
| Developer responsibility | System enforced |
| Tenant isolation optional | Tenant isolation required |
| DDL/DML not blocked | DDL/DML actively blocked |
| Unlimited rows | Max 10,000 rows |
| Limited logging | Comprehensive audit trail |

**Bottom Line**: Your queries are now more secure, and you don't need to worry about accidental data modification or cross-tenant access.

---

### 관련 문서

- [BLUEPRINT_OPS_QUERY](BLUEPRINT_OPS_QUERY.md) - OPS 시스템 설계 문서 (보안 섹션 추가됨)
- [USER_GUIDE_API](USER_GUIDE_API.md) - API 연동 사용자 가이드
- [USER_GUIDE_CEP](USER_GUIDE_CEP.md) - CEP 연동 사용자 가이드
- [USER_GUIDE_SCREEN_EDITOR](USER_GUIDE_SCREEN_EDITOR.md) - Screen 연동 사용자 가이드
- [INDEX](INDEX.md) - 전체 문서 인덱스
