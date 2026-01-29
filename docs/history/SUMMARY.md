# LLM-Based Tool Selection & Parallel Execution - Summary

## 현재 상황 분석

당신의 통찰에 따르면:
1. **Tool 선택이 아직 하드코딩** - Execute 단계에서 항상 특정 tool만 사용
2. **LLM이 필요한 정보를 못 받음** - Tool options, Catalog 정보 없음
3. **Catalog 정보가 필요** - DB 구조(테이블, 컬럼, 설명)를 LLM이 알아야 함
4. **병렬 실행 필요** - 여러 tool을 동시에 실행해서 성능 향상

## 구현하려는 것

### 핵심 변화

#### Before (현재)
```
User Query
    ↓
Planner LLM (Context 부족: Prompt + Mappings만)
    ↓
Plan { keywords, filters, intent, ... }  ← tool_type 없음
    ↓
Execute Stage
    ↓
HARDCODED tool_type="ci_lookup"  ← 항상 같은 tool 사용
    ↓
Sequential Tool Execution (순차)
```

#### After (목표)
```
User Query
    ↓
Load:
├─ Tools Info (이름, 설명, input_schema)
├─ Catalog Info (테이블, 컬럼, 설명)
└─ Mappings
    ↓
Planner LLM (완전한 Context 포함)
    ↓
Plan { keywords, filters, intent, tool_type }  ← LLM이 선택
    ↓
Execute Stage
    ↓
Dynamic tool_type from Plan
    ↓
Parallel Tool Execution (asyncio.gather)
```

## 3가지 핵심 개선사항

### 1️⃣ LLM이 Tool을 선택 (Tool Selection)
- **What**: Plan에 `tool_type` 필드 추가
- **How**: Planner Prompt에 available tools 정보 포함
- **Result**: LLM이 Tool 선택 → Plan에 tool_type 저장

### 2️⃣ LLM이 Catalog 정보 활용 (Intelligent Parameters)
- **What**: Database 구조 정보를 LLM Prompt에 포함
- **How**: Asset Registry에서 catalog 로드 → 간단하게 정리 → Prompt에 추가
- **Result**: LLM이 실제 테이블/컬럼 이름으로 필터 정의 가능

### 3️⃣ 병렬 실행 (Parallel Execution)
- **What**: asyncio.gather()로 여러 tool 동시 실행
- **How**: Sequential execution 제거 → 모든 tasks을 gather에 전달
- **Result**: 응답 시간 단축 (예: 2 tools는 절반 시간)

## 6단계 구현 계획

### 📋 Phase 1: Plan 스키마 확장 (HIGH 우선순위)
- [ ] Plan의 모든 Spec에 `tool_type: str = Field(default="...")` 추가
  - PrimarySpec
  - SecondarySpec
  - MetricSpec
  - AggregateSpec
  - 기타

**파일**: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`

```python
# Example
class PrimarySpec(SQLModel):
    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    tool_type: str = Field(default="ci_lookup")  # ← ADD THIS
```

---

### 🔧 Phase 2: Tool Registry 개선 (HIGH 우선순위)
- [ ] Tool 클래스에 `input_schema` 필드 추가
- [ ] ToolRegistry에 메서드 추가:
  - `get_tool_info(tool_name)` - 단일 tool 정보
  - `get_all_tools_info()` - 모든 tool 정보
  - `validate_tool_type(tool_type)` - tool_type 유효성 검사

**파일**:
- `apps/api/app/modules/ops/services/ci/tools/base.py` (Tool 클래스)
- `apps/api/app/modules/ops/services/ci/tools/registry.py` (ToolRegistry)

```python
# Example Tool info for LLM
{
    "name": "ci_lookup",
    "description": "CI 인프라 자산 조회",
    "input_schema": {
        "keywords": {"type": "list", "items": {"type": "string"}},
        "filters": {"type": "object"},
        "limit": {"type": "integer"}
    }
}
```

---

### 📚 Phase 3: Catalog 로더 (MEDIUM 우선순위)
- [ ] `load_catalog_for_source(source_ref)` 함수 추가
- [ ] Catalog를 LLM 친화적으로 간단하게 변환
- [ ] Caching으로 성능 향상

**파일**: `apps/api/app/modules/asset_registry/loader.py`

```python
# Example catalog for LLM
{
    "source_ref": "postgres_prod",
    "tables": [
        {
            "name": "servers",
            "description": "서버 정보",
            "columns": [
                {"name": "server_id", "data_type": "VARCHAR", "description": "서버 ID"},
                {"name": "environment", "data_type": "VARCHAR", "description": "prod/staging/dev"}
            ]
        },
        {
            "name": "metrics",
            "description": "성능 메트릭",
            "columns": [...]
        }
    ]
}
```

---

### 💬 Phase 4: Planner Prompt 개선 (HIGH 우선순위)
- [ ] `build_planner_prompt()` 함수 수정:
  - tool_registry_info 매개변수 추가
  - catalog_info 매개변수 추가
- [ ] Prompt에 다음 정보 포함:
  - Available tools 목록 + 설명
  - Tool input schemas
  - Database catalog (테이블/컬럼)
  - Tool selection 지시사항
- [ ] `plan_llm_query()`에서 context 로드 후 전달

**파일**: `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`

```python
# Example enhanced prompt
"""
You are a CI/OPS Query Planner.

User Query: {user_query}

AVAILABLE TOOLS:
- ci_lookup: CI 자산 조회 (keywords, filters, limit)
- metric_query: 메트릭 조회 (metric_name, agg, time_range)
- graph_analysis: 그래프 분석 (scope, view, depth)

DATABASE SCHEMA:
- servers table: server_id (VARCHAR), environment (VARCHAR), status (VARCHAR)
- metrics table: metric_name, value (NUMERIC), timestamp

SELECT TOOLS and DEFINE PARAMETERS:
1. Analyze user query
2. Choose tool_type from available tools
3. Define filters using database columns
4. Return Plan JSON with tool_type field
"""
```

---

### ⚡ Phase 5: Stage Executor 병렬 실행 (HIGH 우선순위)
- [ ] `_execute_execute()` 메서드 수정:
  - Plan의 tool_type 동적으로 읽기 (hardcoded 제거)
  - Sequential execution → asyncio.gather() 병렬 실행
- [ ] `_execute_tool_async()` helper 메서드 추가
- [ ] 에러 처리 강화

**파일**: `apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py`

```python
# Example parallel execution
async def _execute_execute(self, plan: Plan) -> ExecuteOutput:
    tasks = []

    # Create tasks for all needed tools
    if plan.primary:
        tasks.append(self._execute_tool_async(
            tool_type=plan.primary.tool_type,  # ← Dynamic
            params={...}
        ))

    if plan.metric:
        tasks.append(self._execute_tool_async(
            tool_type=plan.metric.tool_type,  # ← Dynamic
            params={...}
        ))

    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return ExecuteOutput(...)
```

---

### ✅ Phase 6: 테스트 & 검증 (MEDIUM 우선순위)
- [ ] Unit tests:
  - Plan schema with tool_type
  - Tool validation
- [ ] Integration tests:
  - Planner with tools info
  - Planner output includes valid tool_type
  - Parallel execution timing
- [ ] E2E tests:
  - Full query → plan → execution flow
  - Multiple tool selections work correctly

**파일들**:
- `apps/api/tests/test_plan_schema.py` - Plan schema tests
- `apps/api/tests/test_planner_with_tools.py` - Planner tests
- `apps/api/tests/test_parallel_execution.py` - Execution tests
- `apps/api/tests/test_e2e_tool_selection.py` - E2E tests

---

## 구현 우선순위

### 🔴 IMMEDIATE (이번 주)
1. **Plan 스키마** - tool_type 필드 추가 (Phase 1)
2. **Planner Prompt** - tools info + catalog 포함 (Phase 4)
3. **Parallel Execution** - stage_executor 수정 (Phase 5)

### 🟠 SHORT-TERM (다음 주)
4. Tool Registry 개선 (Phase 2)
5. Catalog 로더 (Phase 3)
6. Plan 검증 로직

### 🟡 MEDIUM-TERM (2-3주)
7. 포괄적 테스트
8. 문서화
9. 성능 최적화

---

## 예상 효과

### 기능적 개선
- ✅ Tool 선택이 동적 → 새로운 tool 추가 시 코드 변경 불필요
- ✅ LLM이 실제 DB 구조 고려 → 더 정확한 파라미터 정의
- ✅ 병렬 실행 → 응답 시간 단축 (2 tools는 2배 빠름)

### 아키텍처 개선
- ✅ Tool 선택과 실행이 분리됨
- ✅ 각 레이어의 책임이 명확
- ✅ 확장성 향상

### 사용자 경험
- ✅ 같은 intent의 다양한 쿼리를 자동으로 처리
- ✅ Tool별 최적의 파라미터 자동 설정
- ✅ 빠른 응답 시간

---

## 위험 요소 및 완화 방법

### 위험 1: LLM이 존재하지 않는 tool_type 선택
**완화**:
- Prompt에 명확한 tool 목록 제시
- `_validate_plan()`에서 검증 후 기본값으로 교체

### 위험 2: Catalog 정보가 Token 초과
**완화**:
- Catalog 간단히 정리 (중요 테이블/컬럼만)
- 필요시 요약 및 페이징

### 위험 3: 병렬 실행에서 일부 tool 실패
**완화**:
- `return_exceptions=True` 사용
- 각 결과를 개별적으로 검증
- 부분 결과 반환

### 위험 4: 기존 코드와 호환성
**완화**:
- tool_type에 기본값 설정
- Execute stage에서 기본값 처리
- Backward compatibility 테스트

---

## 다음 단계

### 즉시 (오늘/내일)
1. ✅ 아키텍처 문서 작성 (완료)
2. ✅ 체크리스트 문서 작성 (완료)
3. ➡️ Phase 1 시작 - Plan 스키마 수정

### 이번 주
4. ➡️ Phase 4 시작 - Planner Prompt 개선
5. ➡️ Phase 5 시작 - Parallel execution 구현
6. ➡️ 기본 테스트 작성

### 다음 주
7. ➡️ Phase 2, 3 완성
8. ➡️ 포괄적 테스트
9. ➡️ 배포 준비

---

## 참고 파일

### 작성된 설계 문서
- `docs/CATALOG_TO_LLM_ARCHITECTURE.md` - 상세 아키텍처 (실행 흐름, 데이터 구조, 예시)
- `docs/IMPLEMENTATION_CHECKLIST.md` - 단계별 구현 체크리스트 (Phase 1-8)
- `docs/SUMMARY.md` - 이 파일 (개요 및 다음 단계)

### 참고 코드 구조
- `apps/api/app/modules/ops/services/ci/planner/plan_schema.py` - Plan 정의
- `apps/api/app/modules/ops/services/ci/planner/planner_llm.py` - Planner LLM
- `apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py` - Execute stage
- `apps/api/app/modules/ops/services/ci/tools/base.py` - Tool 기본 클래스
- `apps/api/app/modules/ops/services/ci/tools/registry.py` - Tool Registry
- `apps/api/app/modules/asset_registry/schema_models.py` - Catalog 모델

---

## 질문 및 의사결정

현재까지의 분석에서:

1. ✅ **LLM이 Tool을 선택해야 하는가?** → YES
   - Plan에 tool_type 저장

2. ✅ **LLM에게 Catalog 정보를 보내야 하는가?** → YES
   - DB 구조를 알아야 정확한 filter 정의 가능

3. ✅ **Tool을 병렬로 실행해야 하는가?** → YES
   - asyncio.gather()로 성능 향상

4. ⏳ **Tool input_schema를 Prompt에 포함할까?** → OPTIONAL
   - 우선순위는 낮음, 나중에 추가 가능

5. ⏳ **기존 hardcoded tool selection을 어떻게?** → REPLACE
   - Plan의 tool_type으로 교체

---

## 실행 준비 완료

위의 두 상세 문서를 참고하여:
- `docs/CATALOG_TO_LLM_ARCHITECTURE.md` - 이게 무엇인지 이해
- `docs/IMPLEMENTATION_CHECKLIST.md` - 이걸 어떻게 구현할지 실행

Phase 1부터 시작하면 됩니다!
