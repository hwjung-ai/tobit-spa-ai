# OPS Orchestration: Production Integration Gap Analysis

**작성일**: 2026-02-14
**상태**: ⚠️ **CRITICAL INTEGRATION GAPS IDENTIFIED**

---

## 🔴 Executive Summary

**문제**: 모듈은 생성되고 단위 테스트는 통과하지만, **프로덕션 코드에 실제로 통합되지 않음**

**영향도**:
- **BLOCKER**: SQL Query Safety 검증 미실행 (보안 위험)
- **HIGH**: Runner 모듈화 미완료 (6,326줄 monolithic 파일)
- **MEDIUM**: Tool Capability 미구현
- **MEDIUM**: PartialSuccess 응답 미구현
- **MEDIUM**: Chaos 테스트 미작성

**근본 원인**: 테스트 단계에서 모듈 검증만 하고, 실제 프로덕션 코드 경로에 통합하지 않음

---

## 1. CRITICAL: P0-4 Query Safety Validation - NOT INTEGRATED

### 문제점

**파일**: `apps/api/app/modules/ops/services/orchestration/tools/direct_query_tool.py`

```python
# ❌ LINE 54-136: execute() 메서드 - 안전 검증 없음
async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
    sql_query = params.get("sql", "")

    # ... source_asset 로드 ...

    # ❌ QuerySafetyValidator.validate_query() 호출 없음
    # ❌ SQL 인젝션 검증 없음
    # ❌ DDL/DCL 차단 없음
    # ❌ Tenant isolation 검증 없음

    try:
        logger.info(f"Executing direct query via source '{source_ref}': {sql_query[:100]}...")
        connection = ConnectionFactory.create(source_asset)
        rows = connection.execute(sql_query, query_params)  # ⚠️ 직접 실행!
        # ...
    except Exception as e:
        # ...
```

### 설계된 검증 (미사용)

**파일**: `apps/api/app/modules/ops/services/orchestration/tools/query_safety.py`

```python
# ✅ 275줄: 완전히 구현됨 (하지만 호출되지 않음)
class QuerySafetyValidator:
    @staticmethod
    def validate_query(query: str, tenant_id: Optional[str] = None) -> ValidationResult:
        """종합 검증"""
        violations = []

        # 1. Read-only 확인
        violations.extend(QuerySafetyValidator.check_read_only(query))

        # 2. DDL 차단
        violations.extend(QuerySafetyValidator.check_ddl_blocked(query))

        # 3. DCL 차단
        violations.extend(QuerySafetyValidator.check_dcl_blocked(query))

        # 4. Tenant isolation
        tenant_check = QuerySafetyValidator.check_tenant_isolation(query, tenant_id)
        if tenant_check:
            violations.append(tenant_check)

        return ValidationResult(valid=(len(violations) == 0), violations=violations)

    # 정의된 위험 키워드들:
    DDL_KEYWORDS = {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"}
    DML_WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}
    DCL_KEYWORDS = {"GRANT", "REVOKE"}
```

### 영향도

- **심각도**: 🔴 **CRITICAL**
- **보안 위험**: SQL Injection, 쓰기 명령 실행, Tenant 경계 침해 가능
- **설계 부채**: 검증 로직은 완벽하지만 호출 경로 누락

### 수정 방안

1. **DirectQueryTool.execute()에 검증 추가**:
```python
async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
    sql_query = params.get("sql", "")

    # 1단계: 안전성 검증 (실행 전)
    from app.modules.ops.services.orchestration.tools.query_safety import QuerySafetyValidator

    validation_result = QuerySafetyValidator.validate_query(
        sql_query,
        tenant_id=context.tenant_id  # Tenant isolation
    )

    if not validation_result.valid:
        return ToolResult(
            success=False,
            error="Query validation failed",
            error_code=ToolErrorCode.SQL_BLOCKED,
            error_details={
                "violations": [v.description for v in validation_result.violations],
                "sql_preview": sql_query[:100],
            }
        )

    # 2단계: 안전한 쿼리만 실행
    try:
        connection = ConnectionFactory.create(source_asset)
        rows = connection.execute(sql_query, query_params)
        # ...
```

---

## 2. HIGH: P1-1 Runner Modularization - NOT COMPLETED

### 문제점

**파일**: `apps/api/app/modules/ops/services/orchestration/orchestrator/runner.py`

```bash
$ wc -l runner.py
6326 apps/api/app/modules/ops/services/orchestration/orchestrator/runner.py
```

**현재 상태**: 여전히 6,326줄의 **monolithic** 파일

### 설계된 모듈화 (미실행)

**파일**: `apps/api/app/modules/ops/services/orchestration/orchestrator/runner_base.py` (테스트만 통과)

```python
# ✅ 120줄: 기본 클래스 생성됨
class RunnerContext:
    """실행 컨텍스트 - 공유 상태"""
    tenant_id: str
    trace_id: str
    request_id: str
    execution_results: Dict[str, Any] = field(default_factory=dict)
    execution_errors: List[str] = field(default_factory=list)
    response_blocks: List[Block] = field(default_factory=list)
    phase_times: Dict[str, float] = field(default_factory=dict)

class BaseRunner:
    """기본 Runner - 로깅 및 컨텍스트 관리"""
    context: RunnerContext
    logger: logging.Logger

    def log_phase_start(self, phase: str) -> None: ...
    def log_phase_end(self, phase: str, elapsed_ms: float) -> None: ...
    def log_error(self, error: str) -> None: ...
    def get_phase_times_summary(self) -> Dict[str, float]: ...
```

**테스트**: ✅ 17/17 통과 (test_runner_modularization.py)

**현실**: ❌ runner.py는 여전히 모놀리식 구조 유지

### 설계된 병렬 실행 (미통합)

**파일**: `apps/api/app/modules/ops/services/orchestration/orchestrator/parallel_executor.py` (테스트만 통과)

```python
# ✅ 324줄: 병렬 실행 엔진 구현됨
class ParallelExecutor:
    """독립적인 작업들을 병렬로 실행"""
    async def execute(self) -> Dict[str, Any]:
        """asyncio.gather로 병렬 실행"""
        tasks = [task.execute() for task in self.tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # ...

class DependencyAwareExecutor(ParallelExecutor):
    """의존성을 고려한 병렬 실행"""
    def compute_execution_order(self) -> None:
        """Topological sort로 실행 순서 결정"""
        # ...

    async def execute_with_dependencies(self) -> Dict[str, Any]:
        """Phase별로 도구 순차 실행"""
        for phase in self.execution_order:
            results = await asyncio.gather(*[task.execute() for task in phase])
```

**테스트**: ✅ 모두 통과 (test_runner_modularization.py의 TestParallelExecutor, TestDependencyAwareExecutor)

**현실**: ❌ runner.py에서 사용하지 않음

### 근본 원인

1. **모듈화 설계 완료** (파일 생성, 테스트)
2. **runner.py에 통합하지 않음** (여전히 직렬 단일 스레드)
3. **테스트만 통과** (모듈 단위 테스트)
4. **통합 테스트 없음** (runner.py가 실제로 사용하는지 검증 안 함)

### 영향도

- **심각도**: 🟠 **HIGH**
- **성능 영향**: 도구 실행이 직렬 → 병렬 실행 기회 상실
- **코드 유지보수**: 6,300줄 파일 → 분해 어려움

---

## 3. MEDIUM: P1-2 Tool Capability Registry - NOT IMPLEMENTED

### 문제점

**설계**: 도구의 기능 정보 기반 자동 선택

```python
# ❌ 미구현: ToolCapability 시스템 없음
@dataclass
class ToolCapability:
    """도구가 제공하는 기능"""
    name: str  # e.g., "database_query", "graph_traversal"
    parameters: List[str]  # e.g., ["sql_query"]
    output_types: List[str]  # e.g., ["table", "chart"]
    cost_ms: int = 100  # 예상 실행 시간
    failure_rate: float = 0.01  # 예상 실패율

class ToolCapabilityRegistry:
    """도구 기능 정보 저장소"""
    def register_capability(self, tool_id: str, capability: ToolCapability) -> None: ...
    def get_tools_for_capability(self, capability_name: str) -> List[str]: ...
    def recommend_tool(self, required_capabilities: List[str]) -> str: ...
```

**현실**: ❌ 존재하지 않음

### 영향도

- **심각도**: 🟡 **MEDIUM**
- **기능 영향**: LLM 도구 선택이 메타정보 없이 이루어짐
- **유연성 부족**: 런타임 도구 업그레이드 시 수동 설정 필요

---

## 4. MEDIUM: P1-3 PartialSuccess Responses - NOT IMPLEMENTED

### 문제점

**설계**: 부분 성공 상태 응답

```python
# ❌ 미구현: PartialSuccess 상태 없음
class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    # ❌ 아래 상태들이 없음:
    PARTIAL_SUCCESS = "partial_success"  # 일부 작업만 성공
    DEGRADED = "degraded"  # 성능 저하 모드
```

**설계된 응답 예**:
```json
{
  "status": "partial_success",
  "main_result": {...},
  "fallback_used": true,
  "fallback_details": {
    "reason": "primary_timeout",
    "tool_attempted": "database_query",
    "tool_used_fallback": "topology_fallback"
  }
}
```

**현실**: ❌ SUCCESS/FAILURE 이진 상태만 존재

### 영향도

- **심각도**: 🟡 **MEDIUM**
- **신뢰도**: 사용자가 도구 실행 상태를 명확히 이해하기 어려움
- **분석 어려움**: 부분 실패 원인 추적 불가능

---

## 5. MEDIUM: P1-4 Chaos/Negative Tests - NOT IMPLEMENTED

### 문제점

**설계**: 실패 시나리오 테스트

```python
# ❌ 미구현: chaos 테스트 없음
# test_orchestrator_chaos.py (존재하지 않음)

# 예상 테스트들:
class TestToolTimeout:
    """도구 타임아웃 처리"""
    async def test_tool_timeout_recovery(self): ...
    async def test_tool_timeout_fallback_activation(self): ...

class TestToolDatabaseError:
    """도구 DB 에러"""
    async def test_database_connection_error(self): ...
    async def test_sql_injection_blocked(self): ...

class TestTenantBoundary:
    """Tenant 경계 검증"""
    async def test_tenant_isolation_violation_blocked(self): ...
    async def test_cross_tenant_query_rejected(self): ...

class TestPartialSuccess:
    """부분 성공 처리"""
    async def test_multiple_tools_partial_failure(self): ...
    async def test_graceful_degradation_mode(self): ...

class TestInvalidSchema:
    """도구 응답 스키마 검증"""
    async def test_malformed_tool_response(self): ...
    async def test_missing_required_fields(self): ...
```

**현실**: ❌ 모두 미작성

### 영향도

- **심각도**: 🟡 **MEDIUM**
- **품질**: 실패 시나리오 미검증
- **프로덕션**: 실제 장애 상황 대응 불확실

---

## 6. Summary: Integration Gap Status

| Item | Module | Tests | Code Integration | Status |
|------|--------|-------|------------------|--------|
| **P0-4** Query Safety | ✅ query_safety.py (275줄) | ✅ 통과 | ❌ **NOT USED** in DirectQueryTool | 🔴 CRITICAL |
| **P0-5** Request Timeout | ✅ request_timeout.py (323줄) | ✅ 통과 | ❓ 부분 통합 | 🟡 VERIFY |
| **P0-2** Tool Policies | ✅ policy.py (320줄) | ✅ 통과 | ❓ 부분 통합 | 🟡 VERIFY |
| **P1-1** Runner Modularization | ✅ runner_base.py, parallel_executor.py | ✅ 통과 | ❌ **NOT USED** in runner.py (6,326줄) | 🔴 HIGH |
| **P1-2** Tool Capability | ❌ 미구현 | ❌ 없음 | ❌ 없음 | 🟡 MEDIUM |
| **P1-3** PartialSuccess | ❌ 미구현 | ❌ 없음 | ❌ 없음 | 🟡 MEDIUM |
| **P1-4** Chaos Tests | ❌ 미구현 | ❌ 없음 | ❌ 없음 | 🟡 MEDIUM |

---

## 7. Recommended Fix Order

### Phase A: CRITICAL (Day 1-2)
1. **Integrate QuerySafetyValidator into DirectQueryTool.execute()** ✅ Security blocker
2. **Verify P0-2, P0-5 actual integration** in production code

### Phase B: HIGH (Day 2-3)
3. **Decompose runner.py** using RunnerContext + BaseRunner + ParallelExecutor
4. **Integrate ParallelExecutor** into runner.py for concurrent tool execution

### Phase C: MEDIUM (Day 3-5)
5. **Implement ToolCapabilityRegistry** for LLM-driven tool selection
6. **Add PartialSuccess response types** (PARTIAL_SUCCESS, DEGRADED)
7. **Create chaos test suite** (timeout, db_error, tenant_boundary, schema_validation)

---

## 8. Verification Strategy

Each fix should follow:
1. **Code integration** (modify production code)
2. **Unit test** (new or updated test)
3. **Integration test** (test that code path is actually used)
4. **E2E test** (full orchestration flow)

**Example** (P0-4 integration):
```python
# test_direct_query_tool_safety.py
class TestDirectQueryToolSafety:
    async def test_sql_injection_blocked(self):
        """DirectQueryTool should reject SQL injection"""
        tool = DirectQueryTool()
        result = await tool.execute(
            context,
            {"sql": "SELECT * FROM users WHERE id=1 OR '1'='1'"}
        )
        assert result.success is False
        assert result.error_code == ToolErrorCode.SQL_BLOCKED

    async def test_ddl_commands_blocked(self):
        """DirectQueryTool should reject DDL"""
        result = await tool.execute(context, {"sql": "DROP TABLE users"})
        assert result.success is False

    async def test_valid_query_succeeds(self):
        """DirectQueryTool should allow safe SELECT"""
        result = await tool.execute(context, {"sql": "SELECT * FROM ci WHERE id=?"})
        assert result.success is True
```

---

## Conclusion

**핵심 문제**: "테스트 주도 개발(TDD)" 착각
- ✅ 모듈 테스트 통과 = 모듈이 정상작동함
- ❌ 모듈 테스트 통과 ≠ 프로덕션 코드에 통합됨

**해결책**: 모듈 단위 테스트 → **통합 테스트** → **생산 코드 변경**

**예상 영향도**:
- **보안**: SQL Injection 미검증 상태 계속 (CRITICAL)
- **성능**: 병렬 실행 기회 상실 (HIGH)
- **운영**: 실패 시나리오 미검증 (MEDIUM)

**다음 단계**: Phase A (Query Safety 통합) 부터 시작 ➜
