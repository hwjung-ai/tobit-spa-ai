# OPS 오케스트레이션 사용자 가이드

## 문서 개요

본 문서는 **Tobit SPA AI OPS 오케스트레이션 시스템**의 사용자 가이드입니다. OPS 시스템의 핵심 개념, 아키텍처, 실제 운영 방법을 체계적으로 설명합니다.

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [핵심 개념](#2-핵심-개념)
3. [오케스트레이션 파이프라인](#3-오케스트레이션-파이프라인)
4. [Asset 모델](#4-asset-모델)
5. [실행 추적 (Execution Trace)](#5-실행-추적-execution-trace)
6. [운영 워크플로우](#6-운영-워크플로우)
7. [API 사용법](#7-api-사용법)

---

## 1. 시스템 개요

### 1.1 OPS 오케스트레이션의 목적

OPS(Orchestration & Production System) 오케스트레이션은 **사용자 질의를 자동으로 분석하고, 필요한 데이터를 조회하여 응답을 생성하는 범용 시스템**입니다.

- **단일 진입점**: `/ops/ci/ask` API를 통해 모든 질의가 처리됩니다.
- **LLM 기반 분류**: 질의를 Direct(즉시 답변), Orchestration(데이터 조회), Reject(거절)로 자동 분류합니다.
- **Pipeline 기반 실행**: 5단계 파이프라인(Route+Plan → Validate → Execute → Compose → Present)을 통해 체계적으로 처리합니다.
- **완전 추적 가능**: 모든 실행 과정이 Execution Trace로 기록되어 분석과 디버깅이 가능합니다.

### 1.2 진입 지점

OPS 오케스트레이션의 주요 진입 지점은 다음과 같습니다:

| 진입점 | 설명 | API 경로 |
|--------|------|----------|
| **CI Ask** | CI 질의 처리 (주요 진입점) | `POST /ops/ci/ask` |
| **Standard OPS Query** | 일반 OPS 질의 처리 | `POST /ops/query` |
| **UI Actions** | UI에서 트리거되는 결정적 액션 | `POST /ops/ui-actions` |
| **Isolated Stage Test** | 개별 스테이지 테스트 | `POST /ops/stage-test` |
| **RCA** | 원인 분석 (Root Cause Analysis) | `POST /ops/rca` |

---

## 2. 핵심 개념

### 2.1 Route (라우팅)

질의가 시스템에 진입하는 시점에서 **어떤 방식으로 처리할지 결정**하는 것입니다.

| Route 타입 | 설명 | 예시 |
|------------|------|------|
| **direct** | 데이터/도구 사용 없이 즉시 답변 | "너의 이름은?", "오늘 날짜는?" |
| **orch** | 오케스트레이션 파이프라인 실행 필요 | "서버 A의 CPU 사용량", "CI 빌드 실패 원인" |
| **reject** | 정책/보안/범위 위반으로 거절 | 비밀번호 요청, 허용되지 않은 데이터 접근 |

### 2.2 Stage (스테이지)

파이프라인을 구성하는 **최소 책임 단위**입니다. 각 Stage는 명확한 입력/출력 계약을 가집니다.

| Stage | 책임 | 주요 산출물 |
|-------|------|-----------|
| **ROUTE+PLAN** | 질의 해석, 라우팅 결정, 실행 계획 생성 | PlanOutput |
| **VALIDATE** | 정책/보안/예산 검증 | ValidatedPlan |
| **EXECUTE** | 데이터·문서·그래프 조회 | ToolResults + References |
| **COMPOSE** | 결과 조합/요약 | AnswerBlocks |
| **PRESENT** | UI 렌더링 모델 생성 | ScreenModel |

### 2.3 Plan (계획)

`orch` 라우팅 시 생성되는 **실행 계획**입니다.

```python
class Plan:
    intent: Intent  # LOOKUP, SEARCH, LIST, AGGREGATE, EXPAND, PATH
    view: View      # SUMMARY, COMPOSITION, DEPENDENCY, IMPACT, PATH, NEIGHBORS
    primary: PrimarySpec    # 주요 검색 조건
    secondary: SecondarySpec  # 보조 검색 조건
    graph: GraphSpec        # 그래프 조회 설정 (depth, limits)
    metric: MetricSpec      # 메트릭 조회 설정
    history: HistorySpec    # 이력 조회 설정
    output: OutputSpec      # 출력 형식 (blocks, primary)
```

### 2.4 Replan (재계획)

실행 중 문제가 발생했을 때 **자동으로 보정/재시도하는 메커니즘**입니다.

- **Trigger**: `slot_missing`, `empty_result`, `tool_error_retryable`, `tool_error_fatal`, `policy_blocked`, `low_evidence`, `present_limit`
- **Scope**: EXECUTE, COMPOSE, PRESENT
- **Limits**: `max_replans`, `max_internal_retries`

---

## 3. 오케스트레이션 파이프라인

### 3.1 Pipeline 전체 흐름

```
사용자 질의
    ↓
[ROUTE+PLAN] → Plan 생성 (Direct/Orch/Reject 결정)
    ↓ (orch인 경우만)
[VALIDATE] → 정책/보안/예산 검증
    ↓
[EXECUTE] → 데이터·문서·그래프 조회
    ↓
[COMPOSE] → 결과 조합/요약
    ↓
[PRESENT] → UI 렌더링 모델 생성
    ↓
응답 블록 (Answer Blocks)
```

### 3.2 Stage별 상세 동작

#### 3.2.1 ROUTE+PLAN Stage

**책임**: 질의 해석, 라우팅 결정, 실행 계획 생성

**입력**:
- 사용자 질의
- SchemaCatalog (스키마 컨텍스트)
- Resolver (이름/식별자 해석 규칙)

**출력**:
```python
PlanOutput:
  kind: "direct" | "plan" | "reject"
  
  # kind=direct인 경우
  direct_answer: DirectAnswerPayload
    answer: str
    confidence: float
    references: List[Dict]
  
  # kind=plan인 경우
  plan: Plan
  
  # kind=reject인 경우
  reject_payload: RejectPayload
    reason: str
    policy: str
```

**동작**:
1. Resolver 규칙 적용 (Alias, Pattern, Transformation)
2. LLM을 사용하여 질의 의도 파악
3. Route 결정 (direct/orch/reject)
4. `plan`인 경우 실행 계획 생성

#### 3.2.2 VALIDATE Stage

**책임**: 정책/보안/예산 검증

**입력**:
- Plan (ROUTE+PLAN에서 생성)
- Policy Asset

**출력**:
- ValidatedPlan (검증된 Plan)
- PolicyDecisions (정책 결정 내역)

**동작**:
1. Budget 검증 (max_steps, max_depth, timeout_seconds)
2. 보안 검증 (허용된 필드, 쿼리 allowlist)
3. 정책 검증 (RBAC, 데이터 접근 권한)

#### 3.2.3 EXECUTE Stage

**책임**: 데이터·문서·그래프 조회

**입력**:
- ValidatedPlan
- Query Asset
- Source Asset

**출력**:
- ToolResults (각 Executor의 실행 결과)
- References (근거 목록)

**동작**:
1. Plan을 기반으로 Executor 생성
2. 각 Executor 실행:
   - `metric_executor`: 메트릭 조회 (TimescaleDB)
   - `hist_executor`: 이력 조회
   - `graph_executor`: 그래프 조회 (Neo4j)
3. Tool Contract 형식으로 결과 표준화
4. References 누적

#### 3.2.4 COMPOSE Stage

**책임**: 결과 조합/요약

**입력**:
- ToolResults (EXECUTE에서 생성)
- Mapping Asset
- Prompt Asset (선택)

**출력**:
- AnswerBlocks (최종 응답 블록)

**동작**:
1. ToolResults → AnswerBlocks 변환
2. LLM을 사용한 요약 (선택)
3. 블록 구성 (text, table, chart, network, etc.)

#### 3.2.5 PRESENT Stage

**책임**: UI 렌더링 모델 생성

**입력**:
- AnswerBlocks
- Screen Asset

**출력**:
- ScreenModel (UI 렌더링용 모델)

**동작**:
1. AnswerBlocks → UI Screen 변환
2. 사용자 액션 정의 (Action Handlers)
3. 화면 구성 요소 결정

### 3.3 Control Loop (재계획 루프)

**Trigger 발생 시**:
1. Trigger 유형 분석 (fatal/retryable/policy)
2. Replan 결정 (evaluate_replan)
3. Patch 생성 (before/after)
4. 재실행
5. Replan Event 기록

**예시**:
```python
# EXECUTE Stage에서 empty_result 발생
trigger = ReplanTrigger(
    trigger_type="empty_result",
    stage_name="execute",
    severity="medium",
    reason="No data found for primary query",
    timestamp="2026-01-25T10:30:00Z"
)

# Replan 결정
patch_diff = ReplanPatchDiff(
    before=plan_validated.model_dump(),
    after=fallback_plan.model_dump()
)

should_replan = evaluate_replan(trigger, patch_diff)
```

---

## 4. Asset 모델

### 4.1 Asset 개요

Asset은 **코드를 수정하지 않고 시스템의 동작을 바꾸기 위한 유일한 수단**입니다. 사용자는 UI에서 Asset을 조합하여 오케스트레이션을 정의합니다.

### 4.2 Asset 종류

| Asset 타입 | 설명 | 바인딩되는 Stage |
|------------|------|------------------|
| **Source** | 데이터/문서/그래프의 물리적 시작점 | EXECUTE |
| **SchemaCatalog** | 논리적 구조 정의 | ROUTE+PLAN, EXECUTE |
| **Resolver** | 이름/식별자 해석 규칙 | ROUTE+PLAN |
| **Query** | 데이터 조회 방법 정의 | EXECUTE |
| **Mapping** | ResultSet → AnswerBlocks 변환 | COMPOSE |
| **Prompt** | LLM 판단/요약/계획 생성 | ROUTE+PLAN, COMPOSE |
| **Policy** | 실행 제한, 보안, 예산 | VALIDATE, CONTROL |
| **Screen** | 최종 사용자 표현(UI 구성) | PRESENT |

### 4.3 Asset 바인딩 구조

```
[ROUTE+PLAN]  → Prompt, Policy, SchemaCatalog, Resolver
[VALIDATE]    → Policy
[EXECUTE]     → Query, Source
[COMPOSE]     → Mapping, Prompt(optional)
[PRESENT]     → Screen
[CONTROL]     → Policy
```

### 4.4 Asset 예시

#### 4.4.1 Source Asset
```json
{
  "name": "postgres_main",
  "type": "postgres",
  "connection": {
    "host": "localhost",
    "port": 5432,
    "database": "tobit_spa",
    "user_ref": "db_user_secret"
  },
  "permissions": {
    "read_only": true,
    "schema_allowlist": ["public", "monitoring"]
  },
  "limits": {
    "max_rows": 10000,
    "max_duration_seconds": 30
  }
}
```

#### 4.4.2 SchemaCatalog Asset
```json
{
  "name": "ci_schema",
  "entities": [
    {
      "name": "ci_server",
      "display_name": "CI Server",
      "fields": [
        {"name": "ci_code", "type": "string", "primary_key": true},
        {"name": "server_name", "type": "string", "display_name": "서버명"},
        {"name": "status", "type": "string", "enum": ["running", "stopped", "error"]},
        {"name": "cpu_usage", "type": "float", "unit": "%"}
      ],
      "relationships": [
        {"target": "ci_metric", "type": "one_to_many", "foreign_key": "ci_code"}
      ]
    }
  ]
}
```

#### 4.4.3 Resolver Asset
```json
{
  "name": "ci_resolver",
  "rules": [
    {
      "rule_type": "alias_mapping",
      "name": "서버별명매핑",
      "rule_data": {
        "source_entity": "서버A",
        "target_entity": "ci_code:SVR001"
      }
    },
    {
      "rule_type": "pattern_rule",
      "name": "공백제거",
      "rule_data": {
        "pattern": "\\s+",
        "replacement": " "
      }
    }
  ]
}
```

#### 4.4.4 Policy Asset
```json
{
  "name": "ci_policy",
  "budget": {
    "max_steps": 10,
    "max_depth": 3,
    "timeout_seconds": 60
  },
  "security": {
    "allowed_operations": ["SELECT"],
    "blocked_tables": ["users", "credentials"]
  },
  "replan": {
    "max_replans": 3,
    "auto_retry": true
  }
}
```

---

## 5. 실행 추적 (Execution Trace)

### 5.1 Trace 개요

Execution Trace는 **오케스트레이션의 단일 진실 원천(Single Source of Truth)**입니다. 모든 실행은 Trace로 기록되며, Trace를 통해서만 재현·분석·비교할 수 있습니다.

### 5.2 Trace 구조

```python
{
  "trace_id": "abc123...",
  "parent_trace_id": "parent...",
  "feature": "ci",
  "endpoint": "/ops/ci/ask",
  "method": "POST",
  "ops_mode": "real",
  "question": "서버A의 CPU 사용량",
  "status": "success",
  "duration_ms": 1250,
  
  "route": "orch",
  "route_output": {
    "route": "orch",
    "plan_raw": { ... },
    "plan_validated": { ... }
  },
  "route_decision": {
    "route": "orch",
    "reason": "Orchestration plan created",
    "confidence": 0.95,
    "metadata": { ... }
  },
  
  "applied_assets": {
    "source": "postgres_main",
    "schema": "ci_schema",
    "resolver": "ci_resolver",
    "policy": "ci_policy"
  },
  
  "stage_inputs": [
    {
      "stage": "route_plan",
      "applied_assets": { ... },
      "params": { ... },
      "prev_output": null
    },
    ...
  ],
  
  "stage_outputs": [
    {
      "stage": "route_plan",
      "result": { ... },
      "diagnostics": {
        "status": "ok",
        "warnings": [],
        "errors": [],
        "counts": { ... }
      },
      "references": [ ... ],
      "duration_ms": 120
    },
    ...
  ],
  
  "replan_events": [
    {
      "event_type": "replan_decision",
      "stage_name": "execute",
      "trigger": { ... },
      "patch": { ... },
      "timestamp": "2026-01-25T10:30:00Z",
      "decision_metadata": { ... }
    }
  ],
  
  "tool_calls": [
    {
      "tool": "metric_executor",
      "elapsed_ms": 150,
      "input_params": { ... },
      "output_summary": "15 rows returned",
      "error": null
    },
    ...
  ],
  
  "references": [
    {
      "kind": "sql",
      "title": "CPU Usage Query",
      "payload": "SELECT * FROM ci_metric WHERE ci_code = 'SVR001' ..."
    },
    ...
  ],
  
  "answer": {
    "meta": { ... },
    "blocks": [ ... ]
  }
}
```

### 5.3 Trace 활용

1. **Inspector**: Timeline 시각화, In/Out 비교, Replan 분석
2. **RCA**: 원인 분석, 가설 생성, 검증 단계 제시
3. **Regression Watch**: Golden Query와 비교하여 회귀 감지
4. **Isolated Stage Test**: 개별 Stage 단위 테스트

---

## 6. 운영 워크플로우

### 6.1 기본 설정 흐름 (Implementation Flow)

#### 단계 1: Source 연결

데이터의 물리적 존재 확정

```bash
# Admin UI에서 Source Asset 생성
# 1. 연결 정보 설정 (Secret은 참조로만)
# 2. 권한 설정 (Read-only, allowlist)
# 3. Health Check 테스트
```

#### 단계 2: SchemaCatalog 구성

구조를 사람/LLM이 이해 가능한 언어로 정의

```bash
# Admin UI에서 SchemaCatalog Asset 생성
# 1. 엔티티 메타데이터 정의
# 2. 컬럼 의미(semantic type) 설정
# 3. 관계(join, graph edge) 정의
# 4. Schema Scan 실행
```

#### 단계 3: Resolver 설정

사용자 표현 ↔ 실제 ID 연결

```bash
# Admin UI에서 Resolver Asset 생성
# 1. Alias 규칙 추가 (예: "서버A" → "ci_code:SVR001")
# 2. Pattern 규칙 추가 (예: 정규표현식 변환)
# 3. Transformation 규칙 추가 (예: 대소문자 변환)
```

#### 단계 4: Query 작성 + Preview

조회 로직 정합성 즉시 검증

```bash
# Admin UI에서 Query Asset 생성
# 1. Query 작성 (SQL, Cypher, Redis)
# 2. Parameter Binding 설정
# 3. Preview 실행 (실제 데이터 조회 테스트)
# 4. 결과 확인
```

#### 단계 5: Mapping 작성

결과를 응답 블록으로 변환

```bash
# Admin UI에서 Mapping Asset 생성
# 1. ResultSet → AnswerBlocks 변환 규칙 정의
# 2. Column Mapping 설정
# 3. Block Type 결정 (text, table, chart, etc.)
```

#### 단계 6: Screen 구성

표현 결정

```bash
# Admin UI에서 Screen Asset 생성
# 1. UI 구성 요소 정의
# 2. Action Handler 등록
# 3. Publish Gate 검증
```

#### 단계 7: OPS End-to-End 테스트

실제 사용자 질의 기준 E2E 확인

```bash
# OPS UI에서 질의 실행
# 1. 질의 입력
# 2. Timeline 확인 (각 Stage의 In/Out)
# 3. Replan Event 확인
# 4. References 확인
```

### 6.2 일일 운영 흐름

#### 1. 질의 실행

```bash
# OPS Query Interface
POST /ops/ci/ask
{
  "question": "서버A의 CPU 사용량은?",
  "mode": "real",
  "rerun": null
}
```

#### 2. 실행 추적 (Inspector)

```bash
# Inspector UI에서 Trace 확인
# 1. Timeline 시각화
# 2. 각 Stage의 In/Out 비교
# 3. Replan Event 분석
# 4. References 확인
```

#### 3. 문제 분석 (RCA)

```bash
# RCA 실행
POST /ops/rca
{
  "mode": "single",
  "trace_id": "abc123...",
  "options": {
    "max_hypotheses": 5,
    "use_llm": true
  }
}

# 또는 Diff 분석
{
  "mode": "diff",
  "baseline_trace_id": "base123...",
  "candidate_trace_id": "cand456..."
}
```

#### 4. 회귀 감지 (Regression Watch)

```bash
# Golden Query 실행
POST /ops/golden-queries/{query_id}/run-regression

# 결과 확인
# - judgment: "pass" | "fail" | "warning"
# - verdict_reason: 회귀 원인
# - diff_summary: 변경 사항 요약
```

### 6.3 Asset 변경 흐름

#### 1. Asset Draft 생성

```bash
# Admin UI에서 Asset Draft 생성
# 1. 기존 Asset 복사
# 2. 수정
# 3. Draft 상태로 저장
```

#### 2. Isolated Stage Test

```bash
# 개별 Stage 테스트
POST /ops/stage-test
{
  "stage": "execute",
  "question": "서버A의 CPU 사용량은?",
  "asset_overrides": {
    "query": "ci_lookup_v6(draft)",
    "source": "postgres_main"
  },
  "baseline_trace_id": "abc123..."
}

# 결과 확인
# - Result Diff
# - Diagnostics
# - References
```

#### 3. Full Pipeline Test (Test Mode)

```bash
# Test Mode로 전체 파이프라인 실행
POST /ops/ci/ask
{
  "question": "서버A의 CPU 사용량은?",
  "mode": "mock",
  "rerun": null
}
```

#### 4. Publish Gate 검증

```bash
# Publish Gate 실행
# 1. Golden Query Test 통과
# 2. Regression Check 통과
# 3. Peer Review 승인
# 4. Publish
```

---

## 7. API 사용법

### 7.1 CI Ask API

**진입점**: `POST /ops/ci/ask`

**Request**:
```json
{
  "question": "서버A의 CPU 사용량은?",
  "mode": "real",
  "rerun": null,
  "resolver_asset": "ci_resolver",
  "schema_asset": "ci_schema",
  "source_asset": "postgres_main",
  "asset_overrides": {}
}
```

**Response**:
```json
{
  "time": "2026-01-25T10:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "answer": "서버A(SVR001)의 현재 CPU 사용량은 45.2%입니다.",
    "blocks": [
      {
        "type": "text",
        "content": "서버A(SVR001)의 현재 CPU 사용량은 45.2%입니다."
      },
      {
        "type": "table",
        "data": {
          "columns": ["ci_code", "server_name", "cpu_usage"],
          "rows": [
            ["SVR001", "서버A", 45.2]
          ]
        }
      }
    ],
    "trace": {
      "trace_id": "abc123...",
      "route": "orch",
      "stage_outputs": [ ... ],
      "replan_events": [ ... ],
      "tool_calls": [ ... ],
      "references": [ ... ]
    },
    "meta": {
      "trace_id": "abc123...",
      "route": "orch",
      "timing_ms": 1250,
      "used_tools": ["metric_executor"]
    },
    "next_actions": []
  }
}
```

### 7.2 Rerun API

**Request**:
```json
{
  "question": "서버A의 CPU 사용량은?",
  "mode": "real",
  "rerun": {
    "base_plan": { ... },
    "patch": {
      "metric": {
        "time_range": "last_24h",
        "agg": "avg"
      }
    },
    "selected_ci_id": "SVR001",
    "selected_secondary_ci_id": null
  }
}
```

### 7.3 UI Actions API

**진입점**: `POST /ops/ui-actions`

**Request**:
```json
{
  "trace_id": "abc123...",
  "action_id": "load_more_rows",
  "inputs": {
    "offset": 50,
    "limit": 50
  },
  "context": {
    "mode": "real",
    "ci_code": "SVR001"
  }
}
```

**Response**:
```json
{
  "time": "2026-01-25T10:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "trace_id": "def456...",
    "status": "ok",
    "blocks": [
      {
        "type": "table",
        "data": {
          "columns": ["ci_code", "server_name", "cpu_usage"],
          "rows": [
            ...
          ]
        }
      }
    ],
    "references": [ ... ],
    "state_patch": {
      "table_offset": 100
    }
  }
}
```

### 7.4 Isolated Stage Test API

**진입점**: `POST /ops/stage-test`

**Request**:
```json
{
  "stage": "execute",
  "question": "서버A의 CPU 사용량은?",
  "test_plan": {
    "metric": {
      "metric_name": "cpu_usage",
      "agg": "avg",
      "time_range": "last_24h"
    }
  },
  "asset_overrides": {
    "query": "ci_lookup_v6(draft)",
    "source": "postgres_main"
  },
  "baseline_trace_id": "abc123..."
}
```

**Response**:
```json
{
  "time": "2026-01-25T10:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "stage": "execute",
    "result": {
      "metric_results": [ ... ]
    },
    "duration_ms": 150,
    "diagnostics": {
      "status": "ok",
      "warnings": [],
      "errors": [],
      "counts": {
        "rows": 15,
        "blocks": 2,
        "references": 3
      }
    },
    "references": [ ... ],
    "asset_overrides_used": {
      "query": "ci_lookup_v6(draft)",
      "source": "postgres_main"
    },
    "baseline_trace_id": "abc123...",
    "trace_id": "xyz789..."
  }
}
```

### 7.5 RCA API

**진입점**: `POST /ops/rca`

**Request (Single Trace Mode)**:
```json
{
  "mode": "single",
  "trace_id": "abc123...",
  "options": {
    "max_hypotheses": 5,
    "include_snippets": true,
    "use_llm": true
  }
}
```

**Request (Diff Mode)**:
```json
{
  "mode": "diff",
  "baseline_trace_id": "base123...",
  "candidate_trace_id": "cand456...",
  "options": {
    "max_hypotheses": 7,
    "include_snippets": true,
    "use_llm": true
  }
}
```

**Response**:
```json
{
  "time": "2026-01-25T10:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "trace_id": "rca789...",
    "status": "ok",
    "blocks": [
      {
        "type": "markdown",
        "title": "RCA Analysis Summary",
        "content": "**Mode:** single\n**Traces Analyzed:** abc123...\n**Hypotheses Found:** 3"
      },
      {
        "type": "markdown",
        "title": "Hypothesis 1",
        "content": "**Rank 1: Empty Result in EXECUTE Stage**\n\n**Confidence:** HIGH\n\n**Description:** The primary query returned no results..."
      }
    ],
    "rca": {
      "mode": "single",
      "source_traces": ["abc123..."],
      "hypotheses": [ ... ],
      "total_hypotheses": 3,
      "analysis_duration_ms": 850
    }
  }
}
```

---

## 8. 부록

### 8.1 용어 사전

| 용어 | 설명 |
|------|------|
| **Route** | 질의의 처리 경로 결정 (direct/orch/reject) |
| **Stage** | 파이프라인을 구성하는 최소 책임 단위 |
| **Plan** | `orch` 라우팅 시 생성되는 실행 계획 |
| **Replan** | 실행 중 문제 발생 시 자동 보정/재시도 |
| **Asset** | 시스템 동작을 제어하는 설정 (Source, Schema, Query, etc.) |
| **Trace** | 모든 실행 과정의 기록 (단일 진실 원천) |
| **Tool Contract** | 도구 호출의 표준화된 형식 |
| **Reference** | 데이터 조회, 쿼리 실행 등에서 생성되는 근거 |
| **RCA** | Root Cause Analysis (원인 분석) |
| **Regression Watch** | Golden Query와 비교하여 회귀 감지 |

### 8.2 관련 문서

- **개념설계**: `OPS_ORCHESTRATION_CONCEPTS.md`
- **API 명세**: `docs/FEATURES.md` (OPS 섹션)
- **운영 체크리스트**: `docs/OPERATIONS.md`
- **테스트 가이드**: `docs/TESTING_STRUCTURE.md`

### 8.3 지원 기능

1. **Inspector UI**: Timeline, In/Out 비교, Replan 분석
2. **RCA Engine**: 자동 원인 분석, 가설 생성
3. **Regression Watch**: Golden Query 기반 회귀 감지
4. **Asset Registry**: Asset 관리, 버전 관리
5. **Isolated Stage Test**: 개별 Stage 테스트

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0 | 2026-01-25 | 초안 작성 | AI Agent |