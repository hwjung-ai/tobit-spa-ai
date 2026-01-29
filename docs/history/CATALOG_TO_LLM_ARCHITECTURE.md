# LLM-Based Tool Selection & Parameter Definition Architecture

## 개요

현재 시스템에서 LLM(Planner)은 사용자 쿼리를 받아 Plan을 생성합니다. 이 Plan에는 Intent, Keywords, Filters, Time Range, Scope 등이 포함됩니다.

**현재 문제점**:
- Tool 선택이 하드코딩되어 있음 (execute 단계에서 항상 "ci_lookup" 사용)
- 쿼리 파라미터 정의가 고정된 Plan 스키마로만 가능
- LLM이 실제 데이터베이스 구조 정보 없이 작업

**목표**:
LLM이 다음 정보를 모두 받아 Tool을 선택하고 파라미터를 정의하도록 변경
1. **Available Tools Info** - Tool Registry의 모든 tool 정보
2. **Tool Input Schemas** - 각 tool이 요구하는 파라미터 스키마
3. **Database Catalog Info** - 실제 테이블, 컬럼, 설명 메타데이터

---

## 1. 현재 데이터 흐름 (Before)

```
User Query
    ↓
Planner LLM (Context: Prompt + Mappings)
    ↓
Plan {
    intent: "查询",
    primary: {
        keywords: ["cpu"],
        filters: {},
        limit: 10
    },
    metric: {
        metric_name: "cpu_usage",
        agg: "avg",
        time_range: { ... }
    }
}
    ↓
Stage Executor
    ↓
Execute Stage (HARDCODED tool_type="ci_lookup")
    ↓
Tool Execution (Sequential)
```

**문제점**:
- `tool_type`이 execute stage에서 하드코딩됨
- LLM은 사용 가능한 tools 정보 없음
- LLM은 데이터베이스 구조 정보 없음

---

## 2. 목표 데이터 흐름 (After)

```
User Query
    ↓
Load Context Information:
├─ Available Tools (from Tool Registry)
├─ Tool Input Schemas (from Tool Registry)
└─ Database Catalog (from Asset Registry)
    ↓
Planner LLM (Context: All Info Above + Prompt + Mappings)
    ↓
Plan {
    intent: "查询",
    primary: {
        keywords: ["cpu"],
        filters: {},
        limit: 10,
        tool_type: "ci_lookup"      ← LLM이 선택
    },
    metric: {
        metric_name: "cpu_usage",
        agg: "avg",
        time_range: { ... },
        tool_type: "metric_query"   ← LLM이 선택
    }
}
    ↓
Stage Executor
    ↓
Execute Stage (Dynamic tool_type from Plan)
    ↓
Tool Execution (Parallel with asyncio.gather)
```

**개선점**:
- LLM이 tool_type을 선택
- LLM이 tool의 input_schema 기반으로 파라미터 정의
- LLM이 catalog 정보 기반으로 filters, scope 결정 가능
- 여러 tools을 병렬 실행

---

## 3. 데이터 구조 상세

### 3.1 Tool Registry 정보 (execute stage에서 필요)

```python
# Tool Registry에서 제공할 정보
{
    "tools": [
        {
            "name": "ci_lookup",
            "description": "CI 인프라 자산 조회",
            "input_schema": {
                "keywords": {
                    "type": "list",
                    "items": {"type": "string"},
                    "description": "검색 키워드"
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "type": {"type": "string"}
                    }
                },
                "limit": {"type": "integer", "default": 10}
            }
        },
        {
            "name": "metric_query",
            "description": "메트릭 데이터 조회",
            "input_schema": {
                "metric_name": {"type": "string"},
                "agg": {"type": "string", "enum": ["avg", "max", "min", "sum"]},
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"}
                    }
                }
            }
        },
        {
            "name": "graph_analysis",
            "description": "구성도/의존성/영향도 분석",
            "input_schema": {
                "scope": {"type": "string"},
                "view": {"type": "string", "enum": ["composition", "dependency", "impact"]},
                "depth": {"type": "integer"}
            }
        }
    ]
}
```

### 3.2 Catalog 정보 (LLM Prompt에 포함)

```python
# Asset Registry에서 가져올 Catalog 예시
{
    "source_ref": "postgres_prod",
    "tables": [
        {
            "name": "servers",
            "description": "서버 정보",
            "columns": [
                {
                    "name": "server_id",
                    "data_type": "VARCHAR",
                    "description": "서버 고유 ID (sys-xxx 형식)",
                    "is_primary_key": True
                },
                {
                    "name": "status",
                    "data_type": "VARCHAR",
                    "description": "서버 상태 (running, stopped, error)"
                },
                {
                    "name": "environment",
                    "data_type": "VARCHAR",
                    "description": "환경 (prod, staging, dev)"
                }
            ]
        },
        {
            "name": "metrics",
            "description": "성능 메트릭",
            "columns": [
                {
                    "name": "metric_name",
                    "data_type": "VARCHAR",
                    "description": "메트릭 이름 (cpu_usage, memory_usage, disk_io_read, disk_io_write)",
                },
                {
                    "name": "value",
                    "data_type": "NUMERIC",
                    "description": "메트릭 값"
                },
                {
                    "name": "timestamp",
                    "data_type": "TIMESTAMP",
                    "description": "데이터 수집 시간"
                }
            ]
        }
    ]
}
```

---

## 4. Prompt 구성 (LLM에게 전달)

### 4.1 System Prompt (기존 + 추가)

```
You are a CI/OPS query planner. Your job is to:
1. Understand user queries about infrastructure and metrics
2. Select appropriate tools for execution
3. Define query parameters based on available data

Available tools you can select:
[Tool Registry Information - JSON format]

Available data sources:
[Catalog Information - Table/Column descriptions]

Available keywords and mappings:
[Mapping Assets - keyword translations]

Generate a Plan JSON with:
- intent: Query intent
- primary/secondary/metric specs with:
  - keywords: Extracted keywords
  - filters: Based on catalog information
  - tool_type: Selected tool name (must match available tools)
  - other parameters as needed
```

### 4.2 User Context in Prompt

```python
def build_planner_prompt(
    user_query: str,
    tool_registry_info: dict,        # ← NEW
    catalog_info: dict,              # ← NEW
    mapping_assets: dict,
    recent_context: list = None
) -> str:
    """Build complete prompt for Planner LLM"""

    prompt = f"""
User Query: {user_query}

Available Tools:
{json.dumps(tool_registry_info, indent=2)}

Database Schema (Catalog):
{json.dumps(catalog_info, indent=2)}

Available Mappings:
{json.dumps(mapping_assets, indent=2)}

Please generate a Plan JSON with:
1. intent: Understood intent
2. Select appropriate tool_type for each spec
3. Define filters and parameters based on catalog information
4. Extract keywords using mapping assets

Your response should be valid JSON matching the Plan schema.
"""
    return prompt
```

---

## 5. Plan 스키마 확장

### 5.1 현재 Plan 스키마 (plan_schema.py)

```python
class PrimarySpec(SQLModel):
    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    # tool_type 없음 ← 문제
```

### 5.2 확장된 Plan 스키마

```python
class PrimarySpec(SQLModel):
    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    tool_type: str = Field(default="ci_lookup")  # ← LLM이 선택

class MetricSpec(SQLModel):
    metric_name: str
    agg: str
    time_range: TimeRangeSpec
    mode: str = "metric"
    scope: Optional[str] = None
    tool_type: str = Field(default="metric_query")  # ← LLM이 선택

class GraphSpec(SQLModel):
    scope: str
    view: View
    depth: int = 2
    tool_type: str = Field(default="graph_analysis")  # ← LLM이 선택
```

---

## 6. 실행 흐름 상세 예시

### 6.1 User Query 예시

```
"지난 주 prod 환경의 서버들 중 CPU 사용률이 높은 top 5개를 보여줘"
```

### 6.2 LLM에게 전달되는 Context

```json
{
  "user_query": "지난 주 prod 환경의 서버들 중 CPU 사용률이 높은 top 5개를 보여줘",

  "available_tools": [
    {
      "name": "ci_lookup",
      "description": "CI 인프라 자산 조회",
      "input_schema": { ... }
    },
    {
      "name": "metric_query",
      "description": "메트릭 데이터 조회",
      "input_schema": { ... }
    }
  ],

  "catalog": {
    "tables": [
      {
        "name": "servers",
        "columns": [
          {"name": "server_id", "data_type": "VARCHAR", "description": "서버 ID"},
          {"name": "environment", "data_type": "VARCHAR", "description": "prod/staging/dev"},
          {"name": "status", "data_type": "VARCHAR", "description": "running/stopped"}
        ]
      },
      {
        "name": "metrics",
        "columns": [
          {"name": "metric_name", "data_type": "VARCHAR"},
          {"name": "value", "data_type": "NUMERIC"},
          {"name": "timestamp", "data_type": "TIMESTAMP"}
        ]
      }
    ]
  }
}
```

### 6.3 LLM이 생성하는 Plan

```json
{
  "intent": "QueryMetrics",
  "mode": "complete",
  "primary": {
    "keywords": ["server", "prod"],
    "filters": {
      "environment": "prod"
    },
    "limit": 5,
    "tool_type": "ci_lookup"
  },
  "metric": {
    "metric_name": "cpu_usage",
    "agg": "avg",
    "time_range": {
      "start": "2024-01-22T00:00:00Z",
      "end": "2024-01-29T00:00:00Z"
    },
    "mode": "metric",
    "scope": "server",
    "tool_type": "metric_query"
  }
}
```

### 6.4 Execute Stage가 Plan으로부터 실행

```python
# stage_executor.py의 _execute_execute() 메서드

async def _execute_execute(self, plan: Plan) -> ExecuteOutput:
    # Extract tool_type from Plan (이전: 하드코딩)
    primary_tool_type = plan.primary.get("tool_type", "ci_lookup")
    metric_tool_type = plan.metric.get("tool_type", "metric_query")

    # Parallel execution (이전: Sequential)
    tasks = []

    # Primary query task
    if plan.primary:
        task = execute_tool(
            tool_type=primary_tool_type,  # ← Dynamic
            params={
                "keywords": plan.primary.keywords,
                "filters": plan.primary.filters,
                "limit": plan.primary.limit,
            }
        )
        tasks.append(task)

    # Metric query task
    if plan.metric:
        task = execute_tool(
            tool_type=metric_tool_type,  # ← Dynamic
            params={
                "metric_name": plan.metric.metric_name,
                "agg": plan.metric.agg,
                "time_range": plan.metric.time_range,
                "scope": plan.metric.scope,
            }
        )
        tasks.append(task)

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return ExecuteOutput(
        primary_results=results[0] if len(results) > 0 else None,
        metric_results=results[1] if len(results) > 1 else None,
    )
```

---

## 7. 구현 단계

### Step 1: Plan 스키마 확장 (plan_schema.py)
- PrimarySpec, MetricSpec, GraphSpec에 `tool_type` 필드 추가

### Step 2: Tool Registry 개선 (tools/registry.py)
- `get_tool_info()` 메서드 추가 (name, description, input_schema 포함)
- `get_all_tools_info()` 메서드 추가

### Step 3: Catalog 로더 함수 추가 (asset_registry/loader.py)
- `load_catalog_for_source()` 함수 추가
- Catalog 정보를 간단한 JSON으로 변환

### Step 4: Planner Prompt 개선 (planner_llm.py)
- `build_planner_prompt()` 함수 수정
- Tool Registry info 포함
- Catalog info 포함
- LLM이 tool_type을 선택하도록 prompt 지시

### Step 5: Stage Executor 수정 (stage_executor.py)
- `_execute_execute()` 메서드 수정
- Plan에서 tool_type 읽기
- asyncio.gather()로 병렬 실행

---

## 8. 구현 우선순위

### 높음 (즉시)
1. Plan 스키마에 tool_type 필드 추가
2. Planner Prompt에 Tool info 추가
3. Stage Executor 병렬 실행 구현

### 중간 (1주일 내)
4. Catalog 정보 Prompt에 포함
5. Tool input_schema Prompt에 포함
6. LLM 지시사항 개선

### 낮음 (점진적)
7. 추가 tool 타입 지원
8. Tool 실행 결과 합성 로직 개선
9. 성능 최적화

---

## 9. 이점

### 기능적
- ✅ Tool 선택이 동적
- ✅ 새로운 tool 추가 시 코드 변경 불필요
- ✅ LLM이 실제 데이터베이스 구조 고려 가능
- ✅ 파라미터 정의가 유연해짐

### 성능적
- ✅ 병렬 tool 실행으로 응답 시간 단축
- ✅ 불필요한 tool 실행 스킵 가능

### 유지보수성
- ✅ 각 레이어의 책임이 명확
- ✅ Tool 추가/변경이 용이

---

## 10. 위험 요소 및 완화 방법

### 위험: LLM이 존재하지 않는 tool_type 선택

**완화**:
```python
# Prompt에 반드시 포함
"You MUST select tool_type from this list only: [ci_lookup, metric_query, graph_analysis]"

# Validation in code
def validate_tool_type(tool_type: str) -> bool:
    valid_tools = get_mapping_registry().list_available_tools()
    return tool_type in valid_tools
```

### 위험: Catalog 정보가 너무 많아서 Token 초과

**완화**:
```python
# Summarize catalog for large databases
def summarize_catalog(catalog: SchemaCatalog, max_tables: int = 5) -> dict:
    """Only include most relevant tables"""
    # Filter by relevance/frequency
    return {
        "source_ref": catalog.source_ref,
        "tables": catalog.tables[:max_tables]  # Limit size
    }
```

### 위험: LLM이 파라미터를 잘못 정의

**완화**:
```python
# Type validation
def validate_plan(plan: Plan) -> bool:
    errors = []
    if plan.metric and not isinstance(plan.metric.metric_name, str):
        errors.append("metric_name must be string")
    if plan.primary and not isinstance(plan.primary.keywords, list):
        errors.append("keywords must be list")
    return len(errors) == 0

# If validation fails, return error to user with prompt to retry
```

---

## 11. 다음 단계

1. **즉시**: Plan 스키마에 tool_type 추가 + Prompt 수정
2. **이번 주**: Stage Executor 병렬 실행 구현
3. **다음 주**: Catalog 정보 Prompt 통합
4. **테스트**: 실제 쿼리로 End-to-End 검증
