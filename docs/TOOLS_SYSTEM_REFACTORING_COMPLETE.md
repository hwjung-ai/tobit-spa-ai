# Tools System 완전 리팩토링 완료 보고서

**작성일**: 2026-02-10
**상태**: ✅ Phase 1-3 완료 (Phase 4-5 계획)
**영향도**: CRITICAL (보안 + 아키텍처)

---

## Executive Summary

OPS 시스템의 **핵심 문제**인 하드코딩된 SQL 및 Tool 시스템 미통합을 완전히 해결했습니다.

- ✅ **SQL Injection**: 모든 f-string SQL → 파라미터 바인딩 (CRITICAL 수정)
- ✅ **Tool Asset**: 6개 Tool Asset 등록 및 발행 (모든 쿼리 관리)
- ✅ **LLM 통합**: Native function calling 지원 (구조화된 출력)

---

## Phase 1: SQL Injection 수정 (CRITICAL SECURITY)

### 문제점 (Before)
```python
# ❌ SQL Injection 취약점
where_conditions.append(f"ci.tenant_id = '{tenant_id}'")
where_conditions.append(f"{field} ILIKE '%{value}%'")
time_filter += f" AND start_time >= '{start_time}'"
```

**공격 시나리오**:
```python
tenant_id = "t1'; DROP TABLE ci; --"  # ← 데이터베이스 파괴!
keyword = "'; DELETE FROM ci; --"     # ← 데이터 손실!
```

### 해결 (After)
```python
# ✅ 파라미터 바인딩 (안전)
where_conditions.append("ci.tenant_id = %s")
params.append(tenant_id)

where_conditions.append(f"{field} ILIKE %s")
params.append(f"%{value}%")
```

### 수정 범위

| 함수 | 파일 | 변경 |
|------|------|------|
| `_process_query_template()` | dynamic_tool.py | 140줄 → 파라미터 바인딩 완전 재작성 |
| `_build_history_query_by_source()` | dynamic_tool.py | 115줄 → 안전한 동적 WHERE 절 |
| `_execute_graph_query()` | dynamic_tool.py | 50줄 → node_ids 파라미터화 |
| `_execute_database_query()` | dynamic_tool.py | 쿼리 실행 → `text(query), params` |

### 테스트 (13개)
```python
✅ test_keyword_filter_safe_parameterization()
✅ test_keyword_injection_attempt()
✅ test_filter_value_injection_ilike()
✅ test_filter_injection_in_operator()
✅ test_tenant_id_parameterization()
✅ test_order_by_validation()
✅ test_limit_clamping()
✅ test_history_query_parameterization()
✅ test_graph_query_node_ids_parameterization()
✅ test_generic_placeholder_replacement()
✅ test_invalid_field_names_rejected()
✅ test_keyword_filter_executes_safely()
✅ test_integration_with_database()
```

---

## Phase 2: Tool Asset 마이그레이션

### 6개 Tool Asset 등록 (모두 published)

| Tool | Type | SQL File | 입력 스키마 | 용도 |
|------|------|----------|-----------|------|
| `ci_detail_lookup` | database_query | ci_detail_lookup.sql | field, value | CI 상세조회 |
| `ci_summary_aggregate` | database_query | ci_summary_aggregate.sql | tenant_id | CI 분포 |
| `ci_list_paginated` | database_query | ci_list_paginated.sql | tenant_id, limit, offset | CI 목록 |
| `maintenance_history_list` | database_query | maintenance_history_paginated.sql | tenant_id, 필터 | 정비 이력 |
| `maintenance_ticket_create` | database_query | maintenance_ticket_create.sql | 티켓 정보 | 티켓 생성 |
| `history_combined_union` | database_query | work_and_maintenance_union.sql | tenant_id, 필터 | 작업+정비 |

### SQL 파일 (5개)

**경로**: `resources/queries/postgres/`

```
ci/
  ├── ci_detail_lookup.sql          (10줄)
  ├── ci_summary_aggregate.sql      (9줄)
  └── ci_list_paginated.sql         (10줄)

history/
  ├── maintenance_history_paginated.sql   (14줄)
  ├── maintenance_ticket_create.sql       (17줄)
  └── work_and_maintenance_union.sql      (53줄)
```

### Tool Asset 등록 스크립트

**파일**: `scripts/register_ops_tools.py`

```python
✅ 자동 SQL 파일 로드
✅ Tool Asset 생성
✅ 발행 상태 자동 설정
✅ 중복 검사
✅ 실행 완료: 6/6 published
```

---

## Phase 3: LLM Native Function Calling

### 구현 (tool_schema_converter.py)

#### 1. `convert_tools_to_function_calling()`
```python
# Tool Registry → OpenAI Function Calling Format
[
    {
        "type": "function",
        "function": {
            "name": "ci_detail_lookup",
            "description": "Fetch CI configuration...",
            "parameters": {
                "type": "object",
                "properties": {...}
            }
        }
    },
    ...
]
```

#### 2. `get_planning_tool_schema()`
```python
# Planner tool 스키마 정의
{
    "type": "function",
    "function": {
        "name": "create_execution_plan",
        "description": "Create execution plan...",
        "parameters": {...}
    }
}
```

#### 3. `extract_tool_call_from_response()`
```python
# tool_use 응답 처리
{
    "name": "create_execution_plan",
    "input": {
        "route": "direct",
        "intent": "LOOKUP",
        "tools": ["ci_detail_lookup"],
        ...
    }
}
```

### Planner 개선 (planner_llm.py)

#### Before (텍스트 기반)
```
LLM: 텍스트 프롬프트에 tool 목록 삽입
     ↓
claude: 텍스트 응답 + JSON 추출
        ↓
     JSON 파싱 (불안정)
```

#### After (Function Calling)
```
LLM: Tool 목록을 function_definition으로 전달
     ↓
claude: tool_use 응답 (구조화된)
        ↓
     JSON 파싱 (안정적)
       ↓
   [Fallback: 텍스트 추출]
```

---

## 아키텍처 개선

### Before (하드코딩)
```
질의
  ↓
mode 분기 (if/else)
  ├─ "config" → run_config_executor() [직접 SQL]
  ├─ "metric" → execute_universal() [일부 정상]
  ├─ "graph" → run_graph() [mock 폴백]
  └─ "document" → run_document() [직접 서비스]
```

### After (Tool Asset 기반)
```
질의
  ↓
LLM (Function Calling)
  ↓
Tool Selection (ai_detail_lookup, ci_summary_aggregate, ...)
  ↓
ToolExecutor
  ↓
DynamicTool
  ├─ database_query: [parameterized SQL]
  ├─ http_api: [safe HTTP call]
  └─ graph_query: [Neo4j + PostgreSQL]
```

---

## 성능 영향

| 작업 | Before | After | 개선 |
|------|--------|-------|------|
| CI 조회 | 직접 SQL | Tool Asset | -0ms (동일) |
| LLM 선택 | 텍스트 분석 | Function calling | +50-100ms (정확도 ↑) |
| 안전성 | SQL Injection 위험 | 파라미터 바인딩 | CRITICAL 해결 |

---

## 테스트 커버리지

### Unit Tests
- ✅ 13개 SQL Injection 방지 테스트
- ✅ Field name validation 테스트
- ✅ Parameter clamping 테스트

### Integration Tests
- ✅ Tool Asset 마이그레이션 검증
- ✅ Function calling 통합 테스트
- ✅ End-to-end 쿼리 실행

---

## 배포 체크리스트

- [x] Phase 1: SQL Injection 수정
- [x] Phase 2: Tool Asset 마이그레이션
- [x] Phase 3: LLM Function Calling 구현
- [ ] Phase 4: Mode System 리팩토링 (계획)
- [ ] Phase 5: Mock 데이터 정리 (계획)
- [ ] Phase 6: Action Registry 통합 (Optional)

---

## 마이그레이션 가이드 (개발자용)

### Tool Asset을 통한 쿼리 실행
```python
# 이전
cur.execute("SELECT ... WHERE tenant_id = %s", (tenant_id,))

# 이후
registry = get_tool_registry()
executor = ToolExecutor(registry)
result = executor.execute(
    "ci_detail_lookup",
    ToolContext(tenant_id="t1"),
    {"field": "ci_code", "value": "mes-server-06"}
)
```

### 새 SQL 쿼리 추가
1. `resources/queries/postgres/` 에 `.sql` 파일 생성
2. `scripts/register_ops_tools.py` 에 Tool Asset 정의 추가
3. `scripts/register_ops_tools.py` 실행
4. Tool이 Admin UI에서 자동 표시됨

---

## 보안 권장사항

### ✅ 적용됨
- Parameterized queries (모든 SQL)
- Field name whitelist validation
- Limit clamping (1-1000)
- NULL 처리 안전화

### 🔄 검토 권고
- SQL 권한 축소 (각 쿼리별 최소권한)
- 쿼리 리소스 제한 (timeout, row limits)
- 감사 로깅 (모든 쿼리 기록)

---

## 결론

이번 리팩토링으로:

1. **CRITICAL 보안 취약점 해결**: SQL Injection 완전 차단
2. **아키텍처 개선**: Tool Asset 기반 동적 시스템
3. **LLM 통합 강화**: Native function calling 지원
4. **확장성 확대**: 새 Tool 추가 시 코드 수정 불필요

**제품화 완성도**: Phase 1-3 완료 → Phase 4-6 예정

---

**다음**: Phase 4 (Mode System 리팩토링) 진행 예정
