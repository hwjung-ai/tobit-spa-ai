# Pipeline & Assets - 기술 아키텍처 가이드

## 1. Stage Pipeline (5단계)

### 1.1 전체 목록

| 순서 | Stage | 역할 | 실행 시간 예시 |
|------|-------|------|--------------|
| 1 | **route_plan** | 질의 분석 및 실행 계획 생성 | 100-200ms |
| 2 | **validate** | Plan 검증 및 정책 적용 | 10-50ms |
| 3 | **execute** | 실제 데이터 조회 실행 | 300-1500ms |
| 4 | **compose** | 결과 조합 및 블록 생성 | 50-300ms |
| 5 | **present** | 최종 응답 포맷팅 | 50-150ms |

### 1.2 각 Stage 상세

#### 1단계: route_plan

**담당 모듈**: `planner_llm.py::create_plan_output()`

**역할**: 
- 사용자 질의를 분석하여 실행 경로 결정
- 경로 타입: `direct`, `orch`, `reject`

**입력**:
```python
{
  "question": "srv-erp-01의 구성정보는?",
  "mode": "all"
}
```

**출력 (PlanOutput)**:
```python
{
  "kind": "plan",  # "direct" | "plan" | "reject"
  "plan": {
    "intent": "lookup",
    "view": "SUMMARY",
    "scope": {
      "ci_codes": ["srv-erp-01"]
    },
    "tools": ["ci.search", "ci.get"]
  }
}
```

**주요 작업**:
1. LLM 기반 질의 분석 (Prompt Asset 사용)
2. 경로 결정 (direct/orch/reject)
3. CI 식별자 추출 (정규식 패턴 매칭)
4. Intent 결정 (LOOKUP, AGGREGATE, PATH, LIST 등)
5. View 결정 (SUMMARY, DEPENDENCY, IMPACT 등)
6. Metric/History/Graph Spec 생성 (필요시)

**사용되는 Assets**:
- **Prompt**: `ci:planner:ci_planner_output_parser`
- **Schema**: SchemaCatalog (LLM이 데이터 구조 이해용)
- **Resolver**: 식별자 정규화

---

#### 2단계: validate

**담당 모듈**: `runner.py::_run_async_with_stages()`

**역할**:
- Plan의 유효성 검증
- 정책 적용 (depth, time_range, data_size 등)

**입력**:
```python
{
  "plan": { ...위의 Plan... }
}
```

**출력 (ValidatedPlan)**:
```python
{
  "plan": { ...수정된 Plan... },
  "limits_applied": {
    "max_row_count": 1000,
    "max_query_depth": 3,
    "max_time_range_days": 90
  },
  "policy_decisions": {
    "allowed": true,
    "budget_ok": true,
    "depth_clamped": False
  },
  "is_valid": True
}
```

**주요 작업**:
1. Plan 필드 유효성 검증
2. Depth 제한 적용 (`clamp_depth`)
3. 시간범위 제한 (최대 90일)
4. CI 식별자 정규화 (`_sanitize_korean_particles`)
5. 데이터 크기 제한 적용

**사용되는 Assets**:
- **Policy**: `ci:policy:plan_budget`, `ci:policy:view_depth`

---

#### 3단계: execute

**담당 모듈**: `runner.py::_handle_lookup_async()` 및 `_execute_tool()`

**역할**:
- Plan에 따라 실제 데이터 조회 실행
- Tool Registry를 통한 도구 호출

**입력**:
```python
{
  "plan": { ...ValidatedPlan... },
  "validated_plan": { ... }
}
```

**출력 (ToolResults)**:
```python
{
  "base_result": {
    "answer": "Lookup result for srv-erp-01",
    "blocks": [ ... ],
    "results": [],
    "meta": {
      "used_tools": ["ci.search", "ci.get"]
    }
  },
  "tool_calls": [
    {
      "tool": "ci.search",
      "elapsed_ms": 120,
      "input_params": {"keywords": ["srv-erp-01"]},
      "output_summary": "Found 1 CI",
      "error": False
    }
  ],
  "used_tools": ["ci.search", "ci.get"],
  "blocks_count": 3,
  "ci_detail": {
    "ci_id": "...",
    "ci_code": "srv-erp-01",
    "ci_name": "ERP Application Server 01",
    ...
  }
}
```

**주요 작업**:
1. CI 식별자 추출 (정규식 패턴)
2. CI 검색 (`ci.search`)
3. CI 상세 조회 (`ci.get`)
4. 추가 섹션 실행 (필요시):
   - Metric 블록: `_metric_blocks_async()`
   - History 블록: `_history_blocks_async()`
   - Graph 블록: `_build_graph_blocks_async()`
   - CEP 블록: `_cep_blocks_async()`
5. References 추출

**사용되는 Assets**:
- **Query**: `ci:query:ci_search`, `ci:query:ci_get`, `ci:query:metric_aggregate`
- **Source**: 데이터베이스 연결 설정
- **Mapping**: 필드 매핑 규칙

---

#### 4단계: compose

**담당 모듈**: `runner.py::StageExecutor.execute_stage()`

**역할**:
- 실행 결과를 사용자 친화적 형태로 변환
- 다양한 블록 타입 생성

**입력**:
```python
{
  "plan_output": { ... },
  "base_result": { ...execute 결과... }
}
```

**출력 (AnswerBlocks)**:
```python
{
  "answer": "srv-erp-01 ERP Application Server 01의 구성 정보입니다.",
  "blocks": [
    {
      "type": "text",
      "content": "srv-erp-01 ERP Application Server 01의 구성 정보입니다."
    },
    {
      "type": "table",
      "headers": ["항목", "값"],
      "rows": [
        ["CI Code", "srv-erp-01"],
        ["CI Name", "ERP Application Server 01"],
        ...
      ]
    },
    {
      "type": "number",
      "label": "CPU Usage",
      "value": 67.3,
      "unit": "%"
    }
  ],
  "references": [
    {
      "kind": "row",
      "title": "ci_master.srv-erp-01",
      "payload": {...}
    }
  ],
  "next_actions": [
    {"type": "metric", "label": "메트릭 보기"},
    {"type": "history", "label": "이력 보기"}
  ]
}
```

**주요 작업**:
1. Block 생성:
   - **Text Block**: 텍스트 설명
   - **Table Block**: 데이터 테이블
   - **Chart Block**: 시계열 차트 (Apache ECharts)
   - **Network Block**: 그래프 시각화 (React Flow)
   - **Number Block**: 숫자 강조
2. Reference 정리:
   - SQL 쿼리: `kind="sql"`
   - Cypher 쿼리: `kind="cypher"`
   - Tool Call: `kind="row"`
3. Next Actions 생성

**사용되는 Assets**:
- **Prompt**: `ci:compose:ci_compose_summary` (요약 생성)
- **Mapping**: `ci:mapping:*` (블록 변환 규칙)

---

#### 5단계: present

**담당 모듈**: `runner.py::StageExecutor.execute_stage()`

**역할**:
- 최종 응답 포맷팅
- 사용자에게 표시할 준비

**입력**:
```python
{
  "plan_output": { ... },
  "base_result": { ...compose 결과... },
  "question": "srv-erp-01의 구성정보는?"
}
```

**출력 (FinalResponse)**:
```python
{
  "answer": "srv-erp-01 ERP Application Server 01의 구성 정보입니다.",
  "blocks": [ ... ],
  "trace": {
    "route": "orch",
    "plan_raw": { ... },
    "plan_validated": { ... },
    "stage_inputs": [ ... ],
    "stage_outputs": [ ... ],
    "tool_calls": [ ... ],
    "references": [ ... ],
    "trace_id": "f5e6d7c8-9abc-def0-1234-567890abcdef"
  },
  "meta": {
    "route": "orch",
    "route_reason": "Stage-based execution",
    "timing_ms": 582,
    "summary": "...",
    "used_tools": ["ci.search", "ci.get"],
    "trace_id": "..."
  }
}
```

**주요 작업**:
1. LLM 기반 자연어 요약 생성
2. 최종 응답 구조 조합
3. Trace 정보 최종화
4. 메타데이터 추가

**사용되는 Assets**:
- **Prompt**: `ci:present:*` (응답 포맷팅)

---

## 2. Assets (7가지 타입)

### 2.1 전체 목록

| Asset 타입 | 역할 | 사용 Stage | 데이터 형식 |
|-----------|------|-----------|----------|
| **query** | 각 Tool이 사용하는 쿼리 템플릿 (SQL/Cypher/HTTP) | execute (Tool 내부 사용) | SQL/Cypher text + JSON metadata |
| **source** | 데이터베이스/API 연결 설정 (PostgreSQL/Neo4j/REST) | execute (Tool 내부 사용) | JSON (connection info) |
| **policy** | 실행 정책 및 제한 | route_plan, validate | JSON (limits) |
| **prompt** | LLM 프롬프트 템플릿 | route_plan, compose, present | YAML/JSON (system/user templates) |
| **schema** | 데이터 구조 카탈로그 | route_plan | JSON (catalog) |
| **mapping** | 데이터 변환 규칙 | compose, execute | JSON (mappings) |
| **resolver** | 식별자 해석 규칙 | route_plan | JSON (rules) |

### 2.2 참고: Tool Registry (Asset 아님)

**중요**: Tool Registry는 Asset이 아니라, 코드 레벨의 런타임 레지스트리입니다.

**Tool Registry 역할**:
- 각 Tool(CI, Graph, Metric, History, CEP) 클래스를 등록하고 관리
- 실행 시점에 적절한 Tool을 동적으로 선택하고 실행
- Registry Pattern 구현 (디자인 패턴)

**Tool Registry와 Asset의 관계**:

```
┌─────────────────────────────────────────────────────────────┐
│ Tool Registry (코드 레벨)                            │
│                                                         │
│  등록된 Tools:                                           │
│  - CI Tool      → QueryAssetRegistry 사용               │
│  - Graph Tool   → QueryAssetRegistry 사용               │
│  - Metric Tool  → QueryAssetRegistry 사용               │
│  - History Tool → QueryAssetRegistry 사용               │
│  - CEP Tool     → QueryAssetRegistry 사용               │
└─────────────────────────────────────────────────────────────┘
              ↓ QueryAssetRegistry 통해 조회
┌─────────────────────────────────────────────────────────────┐
│ Asset Registry (DB 레벨)                              │
│                                                         │
│  Query Assets (쿼리 템플릿):                             │
│  - ci_search (SQL)      → source_ref: primary_postgres  │
│  - graph_expand (Cypher) → source_ref: primary_neo4j    │
│  - metric_aggregate (SQL) → source_ref: primary_postgres│
│  - history_events (SQL)   → source_ref: primary_postgres│
│                                                         │
│  Source Assets (연결 설정):                             │
│  - primary_postgres (PostgreSQL)                        │
│  - primary_neo4j (Neo4j)                                │
│  - external_api (REST API)                              │
│                                                         │
│  다른 Assets:                                           │
│  - policy: plan_budget, view_depth                      │
│  - prompt: planner, compose, present                     │
│  - schema: production_catalog                            │
│  - mapping: ci_fields, metric_fields                    │
│  - resolver: ci_resolver                               │
└─────────────────────────────────────────────────────────────┘
              ↓ ConnectionFactory가 연결 생성
┌─────────────────────────────────────────────────────────────┐
│ ConnectionFactory (코드 레벨)                       │
│                                                         │
│  Source Asset 기반 동적 연결:                            │
│  - PostgreSQLConnection → PostgreSQL DB                  │
│  - Neo4jConnection       → Neo4j DB                      │
│  - RestAPIConnection     → REST API                      │
└─────────────────────────────────────────────────────────────┘
```

**핵심 차이점**:
- **Tool Registry**: 도구들의 "인덱스/매니저" (코드 레벨, 런타임)
- **Query Asset**: 각 도구가 사용하는 "쿼리 템플릿" (DB 레벨, Asset)
- **Source Asset**: 각 도구가 사용하는 "연결 설정" (DB 레벨, Asset)
- **ConnectionFactory**: Source Asset을 기반으로 동적 연결 생성 (코드 레벨)

**예시**:
```python
# Execute Stage에서 CI Tool 실행
registry = get_tool_registry()
ci_tool = registry.get_tool(ToolType.CI)

# CI Tool 내부에서 Query Asset + Source Asset 사용
registry = get_query_asset_registry()
query_asset = registry.get_query_asset("ci", "search")  # Asset에서 쿼리 로드
source_ref = query_asset["query_metadata"]["source_ref"]  # "primary_postgres"

# ConnectionFactory로 동적 연결 생성
conn = create_connection_for_query("ci", "search")
try:
    result = conn.execute(query_asset["sql"], {"ci_code": "srv-erp-01"})
finally:
    conn.close()
```

### 2.2 각 Asset 상세

#### 2.2.1 Query Asset

**용도**: SQL/Cypher 쿼리 템플릿 정의

**데이터 구조**:
```python
{
  "sql": "SELECT * FROM ci_master WHERE ci_code = :ci_code LIMIT :limit",
  "cypher": "MATCH (ci:CI) WHERE ci.ci_code = $ci_code RETURN ci LIMIT $limit",
  "http": {"method": "GET", "path": "/api/v1/cis/{ci_code}"},
  "params": {
    "ci_code": {
      "type": "string",
      "required": True,
      "description": "CI code to lookup"
    },
    "limit": {
      "type": "integer",
      "default": 1,
      "description": "Maximum rows"
    }
  },
  "query_metadata": {
    "tool_type": "ci",
    "operation": "search",
    "source_ref": "primary_postgres",
    "source_type": "postgresql"
  }
}
```

**사용 예시**:
- `ci:query:ci_search`: CI 검색 SQL 쿼리 (PostgreSQL)
- `ci:query:ci_get`: CI 상세 조회 SQL 쿼리 (PostgreSQL)
- `ci:query:metric_aggregate`: 메트릭 집계 SQL 쿼리 (PostgreSQL)
- `graph:query:expand`: 그래프 확장 Cypher 쿼리 (Neo4j)
- `graph:query:path`: 경로 찾기 Cypher 쿼리 (Neo4j)
- `ci:query:history_events`: 이력 조회 SQL 쿼리 (PostgreSQL)

**로드 함수**: `load_query_asset(scope, name, version)`

---

#### 2.2.2 Policy Asset

**용도**: 실행 정책 및 제한 설정

**데이터 구조**:
```python
{
  "max_query_depth": 5,
  "max_row_count": 10000,
  "max_time_range_days": 90,
  "query_timeout_seconds": 30,
  "allowed_intents": ["lookup", "aggregate", "path", "list"],
  "restricted_tables": ["users", "credentials", "secrets"],
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
  },
  "replan_policy": {
    "max_replans": 3,
    "allowed_triggers": ["empty_result", "tool_error_retryable"],
    "min_interval_seconds": 60
  }
}
```

**사용 예시**:
- `ci:policy:plan_budget`: Plan 예산 및 제한 정책
- `ci:policy:view_depth`: 뷰 깊이 제한 정책

**로드 함수**: `load_policy_asset(policy_type, version)`

---

#### 2.2.3 Prompt Asset

**용도**: LLM 프롬프트 템플릿 (system/user)

**데이터 구조**:
```python
{
  "templates": {
    "system": "You are an OPS query planner specialized in CI management...",
    "user": "User Question: {{question}}\nAvailable Schema: {{schema}}"
  },
  "params": ["question", "schema", "resolvers"],
  "output_contract": {
    "type": "object",
    "properties": {
      "intent": {"type": "string"},
      "ci_codes": {"type": "array"}
    }
  }
}
```

**사용 예시**:
- `ci:planner:ci_planner_output_parser`: 질의 파싱 프롬프트
- `ci:compose:ci_compose_summary`: 요약 생성 프롬프트
- `ci:present:*`: 응답 포맷팅 프롬프트

**로드 함수**: `load_prompt_asset(scope, engine, name, version)`

---

#### 2.2.4 Schema Asset

**용도**: 데이터베이스 구조 카탈로그

**데이터 구조**:
```python
{
  "name": "production_catalog",
  "source_ref": "postgres_main",
  "catalog": {
    "tables": [
      {
        "name": "ci_master",
        "columns": [
          {"name": "ci_id", "type": "uuid", "nullable": False},
          {"name": "ci_code", "type": "varchar(50)", "nullable": False},
          {"name": "ci_name", "type": "varchar(200)", "nullable": True}
        ]
      }
    ]
  }
}
```

**사용 예시**:
- `production_catalog`: 프로덕션 DB 스키마
- `metrics_catalog`: 메트릭 DB 스키마

**로드 함수**: `load_schema_asset(name, version)`

---

#### 2.2.5 Source Asset

**용도**: 데이터베이스 연결 설정

**데이터 구조**:
```python
# PostgreSQL 예시
{
  "source_type": "postgresql",
  "connection": {
    "host": "db.example.com",
    "port": 5432,
    "username": "readonly_user",
    "database": "production_db",
    "secret_key_ref": "env:DB_PASSWORD"  # 환경변수 참조
  },
  "spec": {
    "pool_size": 10,
    "max_overflow": 20,
    "timeout": 30
  }
}

# Neo4j 예시
{
  "source_type": "neo4j",
  "connection": {
    "uri": "bolt://neo4j.example.com:7687",
    "username": "neo4j",
    "database": "neo4j",
    "secret_key_ref": "env:NEO4J_PASSWORD"
  },
  "spec": {
    "version": "5.x",
    "max_connections": 50
  }
}

# REST API 예시
{
  "source_type": "rest_api",
  "connection": {
    "base_url": "https://api.example.com",
    "auth_token": "env:API_TOKEN",
    "timeout": 30
  },
  "spec": {
    "version": "v1",
    "rate_limit": 1000
  }
}
```

**사용 예시**:
- `primary_postgres`: 메인 PostgreSQL DB
- `timescale_metrics`: TimescaleDB (메트릭용)
- `primary_neo4j`: Neo4j (그래프용)
- `external_api`: REST API (외부 연동용)

**로드 함수**: `load_source_asset(name, version)`

---

#### 2.2.6 Mapping Asset

**용도**: 데이터 변환 규칙 (execute → compose)

**데이터 구조**:
```python
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
          {"label": "CI Type", "field": "ci_type"}
        ]
      }
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

**사용 예시**:
- `ci:mapping:ci_fields`: CI 필드 매핑
- `ci:mapping:metric_fields`: 메트릭 필드 매핑
- `graph_relation`: 그래프 관계 매핑

**로드 함수**: `load_mapping_asset(mapping_type, version)`

---

#### 2.2.7 Resolver Asset

**용도**: 식별자 해석 규칙 (사용자 입력 → 시스템 ID)

**데이터 구조**:
```python
{
  "name": "CI 코드 리졸버",
  "rules": [
    {
      "rule_type": "alias_mapping",
      "name": "GT-01 매핑",
      "priority": 100,
      "is_active": True,
      "rule_data": {
        "source_entity": "GT-01",
        "target_entity": "gas_turbine_unit_1"
      }
    },
    {
      "rule_type": "pattern_match",
      "name": "서버 패턴",
      "priority": 50,
      "is_active": True,
      "rule_data": {
        "pattern": r"^(srv|server)-[\w-]+$",
        "entity_type": "server"
      }
    }
  ],
  "default_namespace": "ci"
}
```

**사용 예시**:
- `ci_resolver`: CI 코드 리졸버
- `security_resolver`: 보안 식별자 리졸버

**로드 함수**: `load_resolver_asset(name, version)`

---

## 3. 질의 처리 흐름 (전체 시나리오)

### 3.1 예시 질의: "srv-erp-01의 구성정보는?"

```
사용자 질의
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. ROUTE_PLAN (120ms)                                    │
├─────────────────────────────────────────────────────────────┤
│ 사용 Assets:                                               │
│   - Prompt: ci:planner:ci_planner_output_parser (v3)     │
│   - Schema: production_catalog (v2)                       │
│   - Resolver: ci_resolver (v1)                           │
│                                                            │
│ 작업:                                                      │
│   1. LLM 호출하여 질의 분석                               │
│   2. 경로 결정: orch (데이터 조회 필요)                    │
│   3. CI 식별자 추출: srv-erp-01                         │
│   4. Intent: LOOKUP                                      │
│   5. View: SUMMARY                                       │
│                                                            │
│ 출력:                                                      │
│   {                                                       │
│     "kind": "plan",                                       │
│     "plan": {                                             │
│       "intent": "lookup",                                 │
│       "view": "SUMMARY",                                  │
│       "scope": {"ci_codes": ["srv-erp-01"]},             │
│       "tools": ["ci.search", "ci.get"]                    │
│     }                                                     │
│   }                                                       │
└─────────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. VALIDATE (15ms)                                        │
├─────────────────────────────────────────────────────────────┤
│ 사용 Assets:                                               │
│   - Policy: ci:policy:plan_budget (v1)                   │
│                                                            │
│ 작업:                                                      │
│   1. Plan 유효성 검증                                     │
│   2. Depth 제한: SUMMARY → depth=2 (원래 3, clamp됨)     │
│   3. 시간범위 확인: 문제없음                             │
│   4. CI 식별자 정규화: srv-erp-01 (변경없음)            │
│                                                            │
│ 출력:                                                      │
│   {                                                       │
│     "plan": { ... },                                      │
│     "limits_applied": {                                    │
│       "max_depth": 2,                                     │
│       "max_row_count": 1000                                │
│     },                                                     │
│     "policy_decisions": {                                  │
│       "allowed": true,                                     │
│       "depth_clamped": true                                │
│     }                                                      │
│   }                                                       │
└─────────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. EXECUTE (450ms)                                        │
├─────────────────────────────────────────────────────────────┤
│ 사용 Assets:                                               │
│   - Query: ci:query:ci_search (v5)                        │
│   - Query: ci:query:ci_get (v3)                           │
│   - Source: postgres_main (v1)                            │
│   - Mapping: ci:mapping:ci_fields (v1)                    │
│                                                            │
│ 작업:                                                      │
│   1. CI 식별자 추출: srv-erp-01                         │
│   2. CI 검색 (ci.search):                                 │
│      - SQL: SELECT * FROM ci_master WHERE ci_code = ?      │
│      - Param: srv-erp-01                                 │
│      - Result: 1 row found                                │
│   3. CI 상세 조회 (ci.get):                               │
│      - SQL: SELECT * FROM ci_master WHERE ci_id = ?        │
│      - Param: uuid-123                                    │
│      - Result: 상세 데이터                                │
│   4. References 추출:                                     │
│      - kind="row", title="ci_master.srv-erp-01"           │
│   5. Mapping 적용: 데이터 필드 변환                        │
│                                                            │
│ Tool Calls:                                                │
│   [                                                       │
│     {                                                     │
│       "tool": "ci.search",                                │
│       "elapsed_ms": 120,                                  │
│       "input_params": {"keywords": ["srv-erp-01"]},        │
│       "output_summary": "Found 1 CI",                      │
│       "error": false                                      │
│     },                                                    │
│     {                                                     │
│       "tool": "ci.get",                                   │
│       "elapsed_ms": 80,                                   │
│       "input_params": {"ci_id": "uuid-123"},             │
│       "output_summary": "CI detail loaded",               │
│       "error": false                                      │
│     }                                                     │
│   ]                                                       │
│                                                            │
│ 출력:                                                      │
│   {                                                       │
│     "ci_detail": {                                        │
│       "ci_id": "uuid-123",                                │
│       "ci_code": "srv-erp-01",                            │
│       "ci_name": "ERP Application Server 01",              │
│       "ci_type": "server",                                │
│       "status": "Operational"                             │
│     },                                                     │
│     "used_tools": ["ci.search", "ci.get"],                │
│     "blocks_count": 3                                     │
│   }                                                       │
└─────────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. COMPOSE (85ms)                                         │
├─────────────────────────────────────────────────────────────┤
│ 사용 Assets:                                               │
│   - Prompt: ci:compose:ci_compose_summary (v2)            │
│   - Mapping: ci:mapping:* (v1)                            │
│                                                            │
│ 작업:                                                      │
│   1. LLM 요약 생성:                                       │
│      - Input: "srv-erp-01의 구성정보는?" + CI detail      │
│      - Output: "srv-erp-01 ERP Application Server 01의 구성 정보입니다." │
│   2. Block 생성:                                           │
│      - Text Block: 요약 텍스트                            │
│      - Table Block: CI 상세 정보 테이블                   │
│      - (Metric 있는 경우) Number Block: CPU 사용률         │
│   3. Reference 정리                                       │
│   4. Next Actions 생성                                    │
│                                                            │
│ 출력:                                                      │
│   {                                                       │
│     "answer": "srv-erp-01 ERP Application Server 01의 구성 정보입니다.", │
│     "blocks": [                                           │
│       {                                                   │
│         "type": "text",                                   │
│         "content": "srv-erp-01 ERP Application Server 01의 구성 정보입니다." │
│       },                                                  │
│       {                                                   │
│         "type": "table",                                  │
│         "headers": ["항목", "값"],                        │
│         "rows": [                                         │
│           ["CI Code", "srv-erp-01"],                      │
│           ["CI Name", "ERP Application Server 01"],         │
│           ["CI Type", "server"],                          │
│           ["Status", "Operational"]                        │
│         ]                                                 │
│       }                                                   │
│     ],                                                    │
│     "references": [                                       │
│       {                                                   │
│         "kind": "row",                                    │
│         "title": "ci_master.srv-erp-01",                  │
│         "payload": {...}                                  │
│       }                                                   │
│     ],                                                    │
│     "next_actions": [                                    │
│       {"type": "metric", "label": "메트릭 보기"},          │
│       {"type": "history", "label": "이력 보기"}           │
│     ]                                                     │
│   }                                                       │
└─────────────────────────────────────────────────────────────┘
   ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. PRESENT (12ms)                                         │
├─────────────────────────────────────────────────────────────┤
│ 사용 Assets:                                               │
│   - (특별한 Asset 없음)                                   │
│                                                            │
│ 작업:                                                      │
│   1. 최종 응답 구조 조합                                  │
│   2. Trace 정보 최종화                                     │
│   3. 메타데이터 추가                                      │
│                                                            │
│ 출력:                                                      │
│   {                                                       │
│     "answer": "srv-erp-01 ERP Application Server 01의 구성 정보입니다.", │
│     "blocks": [ ... ],                                     │
│     "trace": {                                            │
│       "route": "orch",                                     │
│       "plan_raw": { ... },                                 │
│       "plan_validated": { ... },                           │
│       "stage_inputs": [ ... ],                             │
│       "stage_outputs": [ ... ],                            │
│       "tool_calls": [ ... ],                               │
│       "references": [ ... ],                               │
│       "trace_id": "f5e6d7c8-9abc-def0-1234-567890abcdef" │
│     },                                                     │
│     "meta": {                                             │
│       "route": "orch",                                     │
│       "timing_ms": 582,                                   │
│       "used_tools": ["ci.search", "ci.get"],               │
│       "stages_executed": 5                                │
│     }                                                      │
│   }                                                       │
└─────────────────────────────────────────────────────────────┘
   ↓
최종 사용자 응답 표시
```

---

## 4. Asset-Stage Binding 매트릭스

| Stage | Query | Policy | Prompt | Schema | Source | Mapping | Resolver |
|-------|-------|--------|--------|--------|--------|---------|----------|
| **route_plan** | - | ✓ | ✓ | ✓ | - | - | ✓ |
| **validate** | - | ✓ | - | - | - | - | - |
| **execute** | ✓ | - | - | - | ✓ | ✓ | - |
| **compose** | - | - | ✓ | - | - | ✓ | - |
| **present** | - | - | ✓ | - | - | - | - |

---

## 5. Asset 로드 우선순위

모든 Asset은 다음 우선순위로 로드됩니다:

1. **DB (Asset Registry)**: 특정 버전 또는 Published 버전
2. **파일 (resources/)**: Seed 파일 또는 Fallback 파일
3. **하드코딩 기본값**: Policy만 해당

**실제 모드 (real mode)**:
- DB에서만 로드 (fallback 불가)
- Asset이 없으면 에러 발생

**개발/테스트 모드**:
- DB → 파일 → 기본값 순으로 fallback

---

## 6. Inspector에서의 Asset 추적

### 6.1 추적 메커니즘

**위치**: `apps/api/app/modules/inspector/asset_context.py`

**기술**: ContextVar 기반 실행 컨텍스트별 추적

### 6.2 추적되는 Asset 정보

각 Asset 로드 시 자동으로 다음 정보가 추적됩니다:

```python
{
  "asset_id": "uuid-123",
  "name": "ci_planner_output_parser",
  "version": 3,
  "source": "asset_registry",
  "scope": "ci",
  "engine": "planner"
}
```

### 6.3 Inspector 표시

**Trace 구조**:
```python
{
  "trace_id": "f5e6d7c8-...",
  "stages": [
    {
      "stage": "route_plan",
      "duration_ms": 120,
      "diagnostics": {"status": "ok", ...},
      "applied_assets": {
        "prompt": "ci:planner:ci_planner_output_parser:v3",
        "schema": "production_catalog:v2",
        "resolver": "ci_resolver:v1"
      }
    },
    {
      "stage": "validate",
      "duration_ms": 15,
      "diagnostics": {"status": "ok", ...},
      "applied_assets": {
        "policy": "ci:policy:plan_budget:v1"
      }
    },
    {
      "stage": "execute",
      "duration_ms": 450,
      "diagnostics": {"status": "ok", ...},
      "applied_assets": {
        "query": ["ci:query:ci_search:v5", "ci:query:ci_get:v3"],
        "source": "postgres_main:v1",
        "mapping": "ci:mapping:ci_fields:v1"
      },
      "tool_calls": [...]
    },
    {
      "stage": "compose",
      "duration_ms": 85,
      "diagnostics": {"status": "ok", ...},
      "applied_assets": {
        "prompt": "ci:compose:ci_compose_summary:v2",
        "mapping": "ci:mapping:*"
      }
    },
    {
      "stage": "present",
      "duration_ms": 12,
      "diagnostics": {"status": "ok", ...},
      "applied_assets": {}
    }
  ]
}
```

---

## 7. 요약

### 7.1 핵심 원칙

1. **Pipeline 순차 실행**: route_plan → validate → execute → compose → present
2. **Asset-Stage Binding**: 각 Asset은 특정 Stage에서만 의미를 가짐
3. **데이터 흐름**: 이전 Stage 출력 → 다음 Stage 입력
4. **추적 가능성**: 모든 Asset 사용이 Trace에 기록됨

### 7.2 질의 처리 핵심 로직

```
질의 분석 (LLM + Prompt + Schema + Resolver)
  → Plan 생성
     → 정책 검증 (Policy)
        → 데이터 조회 (Query + Source + Mapping)
           → 결과 조합 (Prompt + Mapping)
              → 최종 응답 (Prompt)
```

### 7.3 Asset 로더 함수 정리

| Asset 타입 | 로드 함수 | 키 파라미터 |
|-----------|----------|-----------|
| query | `load_query_asset(scope, name, version)` | scope, name |
| policy | `load_policy_asset(policy_type, version)` | policy_type |
| prompt | `load_prompt_asset(scope, engine, name, version)` | scope, engine, name |
| schema | `load_schema_asset(name, version)` | name |
| source | `load_source_asset(name, version)` | name |
| mapping | `load_mapping_asset(mapping_type, version)` | mapping_type |
| resolver | `load_resolver_asset(name, version)` | name |

---

## 8. 추가 참고 자료

- **OPS 오케스트레이션 가이드**: `docs/OPS_ORCHESTRATION_USER_GUIDE_v2.md`
- **CI 질의 흐름 가이드**: `docs/CI_QUERY_FLOW_AND_DOMAIN_EXTENSION_GUIDE.md`
- **Asset Registry**: `apps/api/app/modules/asset_registry/`
- **Inspector**: `apps/api/app/modules/inspector/`
- **Runner**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`