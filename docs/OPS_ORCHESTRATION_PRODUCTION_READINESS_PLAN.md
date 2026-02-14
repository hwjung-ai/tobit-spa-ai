# OPS 오케스트레이션 상용화 준비 계획

> 작성일: 2026-02-14
> 상태: 검토완료 → 적용계획 수립
> 기반: OPS 오케스트레이션 상용화 비판 리뷰 (2026-02-13)
> 보완: 코드 심층 분석 결과 반영 (4개 영역 병렬 분석, 2026-02-14)

---

## 1. 현황 분석 (코드 기반 심층 검증)

### 1.1 코드 구조 확인 결과

| 항목 | 위치 | 현황 | 리스크 |
|------|------|------|--------|
| Runner 단일 파일 | `orchestrator/runner.py` | **6,326 라인** (전체 orchestrator 모듈 10,164) | 높음 - 변경 충돌, 회귀 위험 |
| Stage Executor | `orchestrator/stage_executor.py` | **2,086 라인** | 중간 - 예외 처리 16개소 |
| Tool Orchestration | `orchestrator/tool_orchestration.py` | **854 라인** | 중간 - 병렬 감지만 있고 실행 없음 |
| Chain Executor | `orchestrator/chain_executor.py` | **518 라인** - `asyncio.gather` 존재 | 낮음 - 구조 양호 |
| Tool Selector | `orchestrator/tool_selector.py` | **261 라인** | 중간 - 키워드 매칭 의존 |
| Direct Query Tool | `tools/direct_query_tool.py` | **보안 가드 없음** | **CRITICAL** - DDL 실행 가능 |
| Registry Init | `tools/registry_init.py` | Asset Registry 기반 동적 로딩 | 낮음 - 구조 양호 |
| Inspector Backend | `inspector/models.py` | 90+ 필드 trace 모델 | 중간 - tool_call_id 누락 |
| Inspector Frontend | `admin/inspector/page.tsx` | 104KB, 스테이지 파이프라인 | 중간 - 병렬 표시 미흡 |
| Regression System | `routes/regression.py` | 9개 판정 지표, RCA 연동 | 높음 - 자동화 0% |
| Asset Registry | `asset_registry/router.py` | CRUD 완비 | **CRITICAL** - Tool 권한 체크 없음 |

### 1.2 잘 되어 있는 점 (유지 강점)

1. **Tool Contract 표준화** - `ToolCall`, `ToolResult` 스키마로 실행 흔적 통일
2. **동적 Tool Registry** - Asset Registry 기반 도구 로딩으로 코드 배포 없이 운영 튜닝 가능
3. **실행 Trace/Span 연동** - Inspector/Span 추적 설계 존재 (`span_tracker.py`)
4. **단계별 파이프라인** - route_plan → validate → execute → compose → present 구조 명확
5. **SQL Injection 방어** - `dynamic_tool.py`에서 parameterized query 사용 (Phase 1에서 수정됨)
6. **Regression 판정 엔진** - 9개 메트릭 기반 PASS/WARN/FAIL 결정적 판정 로직 있음
7. **RCA 엔진** - 단일 trace 및 회귀 분석 모두 지원, Inspector 점프 링크 제공
8. **Asset 버전 히스토리** - `TbAssetVersionHistory`로 변경 이력 추적

### 1.3 리뷰 핵심 리스크 vs 실제 코드

| 리뷰 항목 | 리뷰 내용 | 실제 코드 확인 | 심각도 |
|-----------|----------|---------------|--------|
| R1. Runner 비대화 | 6,000+ 라인 | 6,326 라인 (리뷰 수치 정확) | **높음** |
| R2. 광범위 catch | except Exception 패턴 다수 | **50개+** (`runner` 29, `stage_executor` 16, 기타 5) / 92% 가 제너릭 | **CRITICAL** |
| R3. Tool 거버넌스 | SQL/HTTP 제어 느슨 | DirectQueryTool: DDL 차단 ❌, tenant 필터 ❌, row limit ❌ | **CRITICAL** |
| R4. 비동기/동기 경계 | 불명확 | `executor.py:109`에서 `asyncio.run()` 사용 = **동기 블로킹** | **높음** |
| R5. 테스트 편향 | 정상 플로우 중심 | 카오스/음성 시나리오: 거의 없음 | 중간 |
| **R6. Inspector 미완성** | (리뷰 미언급) | tool_call_id 추적 ❌, 병렬 실행 그룹 ❌, 리플레이 ❌ | **높음** |
| **R7. Asset 보안 미비** | (리뷰 미언급) | Tool CRUD에 권한 체크 없음, Credential 평문 저장 | **CRITICAL** |
| **R8. Regression 자동화 0%** | (리뷰 미언급) | 스케줄링 ❌, CI/CD 연동 ❌, 트렌드 분석 ❌ | **높음** |

---

## 2. 영역별 상세 비판 분석

### 2.1 Orchestrator 심층 분석

#### A. 예외 처리 - CRITICAL

**발견**: 전체 시스템에서 **50개 이상의 `except Exception`** 패턴 확인. 92%가 제너릭.

| 파일 | 제너릭 catch 수 | 대표 위치 | 위험 |
|------|:---:|------|------|
| `runner.py` | 29 | L258, L595, L868, L1101, L1852, **L5817** | 원인 추적 불가 |
| `stage_executor.py` | 16 | L158, L230, L501, **L598** (silent fallback) | 데이터 손실 |
| `tool_orchestration.py` | 3 | - | 중간 |
| `chain_executor.py` | 1 | L361 (제너릭, timeout만 specific) | 낮음 |
| `registry_init.py` | 2 | - | 낮음 |

**가장 위험한 패턴**:
- **`runner.py:5817`** - 오케스트레이션 실패 → legacy로 silent fallback (원인 기록 없이!)
- **`stage_executor.py:598`** - 실패 이유 없이 대체 실행
- **`stage_executor.py:230`** - Asset 로딩 실패해도 실행 계속 (불완전 설정)

#### B. 직렬/병렬 실행 - 허상

**발견**: 병렬 실행이 "설계"되어 있지만 **실제로 직렬 실행됨**.

```
tool_orchestration.py:  병렬 감지 ✅ (DependencyAnalyzer)
                        실행 전략 ✅ (PARALLEL/SERIAL/DAG)
chain_executor.py:      asyncio.gather() ✅ (L188)
executor.py:109:        asyncio.run() ← ❌ 여기서 블로킹!
```

**executor.py:109의 문제**:
```python
# 모든 도구를 동기적으로 실행 (블로킹)
result = asyncio.run(tool.safe_execute(context, params))
```
- `asyncio.run()`은 새 이벤트 루프를 생성하여 **직렬 실행**
- `chain_executor.py`의 `asyncio.gather()`는 죽은 코드 (도달 불가능하거나 nested loop 충돌)
- Inspector UI의 "Parallel" 배지는 **허상**: 설계만 병렬, 실행은 직렬

**영향**: 5개 독립 도구 각 500ms = 직렬 2,500ms (병렬이면 500ms)

#### C. Timeout/Retry/Circuit Breaker

| 기능 | 상태 | 위치 | 문제 |
|------|------|------|------|
| **Timeout** | 부분 구현 | `chain_executor.py:329` | 30초 고정, 도구별 설정 ❌ |
| **Retry** | 스키마만 존재 | `ToolChainStep.retry_count` | **사용 안 됨** (Dead code) |
| **Circuit Breaker** | ❌ 미구현 | - | 연속 실패해도 계속 시도 |
| **Rate Limit** | ❌ 미구현 | - | 도구 무한 호출 가능 |

#### D. 보안 취약점 목록

| ID | 위치 | 취약점 | 심각도 |
|----|------|--------|--------|
| **SEC-1** | `direct_query_tool.py` | DDL/DCL 명령어 미차단 (`DROP TABLE` 가능) | **CRITICAL** |
| **SEC-2** | `direct_query_tool.py` | Tenant 필터 미적용 (다른 테넌트 데이터 접근 가능) | **CRITICAL** |
| **SEC-3** | `direct_query_tool.py` | Row limit 없음 (전체 테이블 스캔 가능) | **HIGH** |
| **SEC-4** | `direct_query_tool.py` | 에러 메시지에 스키마/테이블명 노출 | MEDIUM |
| **SEC-5** | `dynamic_tool.py:172` | operator 검증 미비 (임의 SQL 주입 경로) | **HIGH** |
| **SEC-6** | `ci_ask.py` | 요청 전체 timeout 없음 (무한 hang 가능) | **HIGH** |
| **SEC-7** | `asset_registry/router.py:1602-1776` | Tool CRUD에 권한 체크 없음 | **CRITICAL** |
| **SEC-8** | `tool_router.py:701-708` | Credential이 tool_config에 평문 저장 | **CRITICAL** |
| **SEC-9** | `tool_router.py:836-956` | MCP 서버 URL SSRF 취약 | **HIGH** |
| **SEC-10** | `connections/factory.py:122-126` | Plaintext password fallback 허용 | **HIGH** |

---

### 2.2 Inspector 심층 분석

#### A. 현재 Inspector가 잡을 수 있는 것

| 기능 | 상태 | 상세 |
|------|:---:|------|
| Trace 목록/필터링 | ✅ | question, status, feature, date range |
| 스테이지 파이프라인 | ✅ | route_plan → validate → execute → compose → present |
| Flow Span 타임라인 | ✅ | span_id, parent, name, kind, status, duration_ms |
| Replan 이벤트 추적 | ✅ | LLM이 계획을 수정한 이벤트 |
| Applied Assets 목록 | ✅ | prompt/policy/mapping/source/schema/resolver |
| Asset 버전 기록 | ✅ | asset_versions에 실행 시점 ID |
| Trace 비교 (Diff) | ✅ | TraceDiffView 컴포넌트 존재 |
| Regression 분석 | ✅ | Stage-level 회귀 점수 (0-100) |
| RCA 엔진 | ✅ | 가설 + 증거 + Inspector 점프 링크 |
| ReactFlow 그래프 | ✅ | Span 관계 시각화 |

#### B. Inspector가 잡을 수 **없는** 것 (CRITICAL GAPS)

| 누락 항목 | 영향 | 심각도 |
|-----------|------|--------|
| **tool_call_id 추적** | 어떤 도구가 실패했는지 링크 불가 | **CRITICAL** |
| **병렬 실행 그룹** | "Tool A와 B가 동시에 실행됐는지" 판별 불가 | **HIGH** |
| **도구별 실행 시간** | 어떤 도구가 느린지 식별 불가 | **HIGH** |
| **도구 타입/Asset ID** | 어떤 종류의 도구가 사용됐는지 추적 불가 | HIGH |
| **Retry 시도 횟수** | 재시도가 있었는지 알 수 없음 | MEDIUM |
| **Timeout 발생 여부** | SLO 위반 추적 불가 | **HIGH** |
| **에러 심각도 분류** | 모든 에러가 동일 수준으로 표시 | HIGH |
| **Tenant ID** | 다중 테넌트 감사 추적 불가 | HIGH |
| **Trace 리플레이** | 실패한 질의를 동일 조건으로 재실행 불가 | **HIGH** |
| **에러 집계 대시보드** | 에러 패턴/트렌드 분석 불가 | HIGH |
| **도구 원인-결과** | Tool A 실패 → Tool B 스킵 인과 추적 불가 | MEDIUM |

#### C. Inspector UI에서 직렬/병렬/리플레이 표현

**현재 상태**:
```
OrchestrationVisualization.tsx:
  ✅ 전략 배지: "Parallel" / "Sequential" / "Complex DAG"
  ✅ 실행 그룹 표시 (도구 수 포함)
  ❌ 실제 실행 시간 표시 없음
  ❌ 도구 성공/실패 상태 표시 없음
  ❌ 워터폴 타임라인 없음
  ❌ 리플레이 버튼 없음

InspectorStagePipeline.tsx:
  ✅ 5단계 파이프라인 (route_plan→validate→execute→compose→present)
  ✅ 단계별 상태 색상 (ok/error/warning/skipped)
  ✅ Applied Assets 카드
  ❌ 도구별 에러 목록 없음
  ❌ 병렬 실행 인디케이터 없음
  ❌ Timeout 경고 없음

SpanNode.tsx (ReactFlow):
  ✅ span name, kind, status, duration_ms
  ❌ tool_call_id 표시 없음
  ❌ retry 카운터 없음
  ❌ 병렬 마커 없음
```

**필요한 Inspector UI 개선**:
1. **워터폴 타임라인**: 도구별 시작/종료 시간을 가로 바 차트로
2. **병렬 그룹 표시**: 동시 실행 도구를 수직으로 묶어 표시
3. **도구 상태 배지**: success/error/timeout/skipped 각 색상
4. **리플레이 버튼**: "이 trace를 동일 조건으로 재실행"
5. **에러 드릴다운**: 에러 클릭 → 도구 상세 + 에러 메시지 + 재시도 이력

---

### 2.3 Tools/Assets/Catalog 심층 분석

#### A. Asset Registry 보안 - CRITICAL

**발견**: Screen Asset에는 권한 체크가 있지만, **Tool Asset에는 없음**.

```python
# router.py:1602-1607 - Tool 목록 조회
@router.get("/tools", response_model=ResponseEnvelope)
def list_tools(..., current_user: TbUser = Depends(get_current_user)):
    # ⚠️ current_user 주입되지만 권한 체크 없음!
    # 누구든 인증만 되면 모든 도구에 접근 가능
```

**Tool 엔드포인트에 권한 체크가 없는 곳**:
- `GET /tools` (목록)
- `POST /tools` (생성) - **누구나 도구 생성 가능**
- `PUT /tools/{id}` (수정)
- `DELETE /tools/{id}` (삭제)
- `POST /tools/{id}/test` (테스트 실행) - **임의 쿼리 실행 가능**
- `POST /tools/discover-mcp-tools` (MCP 탐색) - **SSRF 경로**
- `POST /tools/import-from-mcp` (MCP 가져오기)

#### B. Credential 평문 저장 - CRITICAL

```python
# tool_router.py:701-708 - API Manager에서 도구 생성 시
"headers": {
    "Authorization": "Bearer {token}",  # ← 평문으로 저장!
    "X-Tenant-Id": "{tenant_id}"
}
```

**위험**: 백업/로그/감사에서 Credential 노출

**connections/factory.py:122-126**:
```python
password = conn_config.get("password")
if password:
    logger.warning("Using direct password (not recommended)")
    return password  # ← 경고만 하고 허용!
```

#### C. Tool Asset 검증 부재

```python
# crud.py:35 - validate_asset()
# 검증하는 자산 유형: prompt, mapping, policy, query, source, resolver, screen
# ❌ tool 자산은 검증하지 않음!
```

- Tool 생성 시 `tool_config`의 JSON 스키마 검증 없음
- `tool_input_schema`의 유효성 검증 없음
- 위험한 SQL 패턴이 담긴 도구를 published 상태로 게시 가능

#### D. Soft Delete 미구현

- `TbAssetRegistry`에 `deleted_at` 필드 없음
- Hard delete → 감사 추적 불가, 복구 불가
- 의존 관계 확인 없이 삭제 가능 (orphan 위험)

---

### 2.4 Regression 심층 분석

#### A. 존재하는 것 (양호)

| 기능 | 구현 상태 | 위치 |
|------|:---:|------|
| Golden Query CRUD | ✅ | `routes/regression.py:38-192` |
| Baseline 설정 | ✅ | `routes/regression.py:195-252` |
| 회귀 테스트 실행 | ✅ | `routes/regression.py:255-390` |
| 9개 판정 메트릭 | ✅ | `regression_executor.py:40-217` |
| RCA 통합 | ✅ | `routes/rca.py` |
| Trace Diff UI | ✅ | `TraceDiffView.tsx` |
| Regression Watch Panel | ✅ | `RegressionWatchPanel.tsx` |

#### B. 존재하지 않는 것 (CRITICAL GAPS)

| 누락 항목 | 상태 | 영향 |
|-----------|:---:|------|
| **자동 회귀 스케줄링** | ❌ 0% | 수동 실행만 가능, 야간 배치 불가 |
| **CI/CD 연동** | ❌ 0% | Asset 변경 시 자동 회귀 미실행 |
| **Rule Config CRUD** | ❌ (DB 테이블은 있음) | `TbRegressionRuleConfig` 미사용, 하드코딩된 임계값 |
| **Baseline 버전 관리** | ❌ | 최신 1개만 보관, 히스토리 없음 |
| **파라미터 격리** | ❌ | 시간 의존 쿼리 → 플레이키 테스트 |
| **Trend 분석** | ❌ 0% | 일별/주별 FAIL 추이 없음 |
| **에러 알림** | ❌ 0% | FAIL 발생해도 알림 없음 |
| **Inspector Span 캡처** | ❌ | 회귀 실행 시 span 정보 버려짐 |
| **Asset 영향 추적** | ❌ | "이 asset이 어떤 golden query에 영향?" 불가 |
| **TraceDiffView 연동** | ⚠️ 미연결 | 존재하지만 regression detail에 연결 안 됨 |

#### C. Frontend 미사용 코드

```tsx
// RegressionWatchPanel.tsx:59-62 - 컨텍스트 state 선언만 있고 사용 안 됨
const [contextScreenId, setContextScreenId] = useState<string | null>(null);
const [contextAssetId, setContextAssetId] = useState<string | null>(null);
const [contextVersion, setContextVersion] = useState<string | null>(null);
// ↑ 선언만 있고 create/baseline 다이얼로그에서 사용 ❌
```

---

## 3. 개선 적용 계획 (보완 완료)

### 3.0 BLOCKER (P0 전에 즉시)

> 보안 취약점은 기능 개선 전에 반드시 수정해야 함

#### BLOCKER-1. Tool 엔드포인트 권한 체크

**목표**: Tool CRUD에 RBAC 적용 (Screen Asset과 동일 수준)

**수정 위치**: `apps/api/app/modules/asset_registry/router.py:1602-1776`

**작업**:
```python
# 모든 tool 엔드포인트에 권한 체크 추가
@router.post("/tools", response_model=ResponseEnvelope)
def create_tool(
    ...,
    current_user: TbUser = Depends(get_current_user),
):
    # 추가: 관리자 역할 확인
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(403, "Tool 생성 권한이 없습니다")
```

**완료 기준**:
- [ ] 모든 Tool CRUD에 역할 기반 권한 체크
- [ ] Tool test 실행에도 권한 제한
- [ ] MCP 탐색/가져오기에 admin 전용 권한

#### BLOCKER-2. Credential 평문 저장 제거

**목표**: tool_config 내 credential을 secret_key_ref로 대체

**수정 위치**: `apps/api/app/modules/asset_registry/tool_router.py:701-708`

**작업**:
- `tool_config.headers.Authorization` → `secret_key_ref` 참조로 변경
- `connections/factory.py:122-126`에서 plaintext password fallback **차단** (warning → error)
- 기존 평문 credential 마이그레이션 스크립트

**완료 기준**:
- [ ] tool_config에 credential 직접 저장 금지
- [ ] plaintext password fallback 차단 (production 모드)
- [ ] 기존 데이터 마이그레이션

#### BLOCKER-3. Tool Asset 검증 추가

**목표**: Tool 생성/게시 시 필수 검증

**수정 위치**: `apps/api/app/modules/asset_registry/crud.py:35`

**작업**:
```python
def validate_tool_asset(asset: TbAssetRegistry) -> list[str]:
    errors = []
    config = asset.tool_config or {}

    # 1. tool_type 필수
    if not asset.tool_type:
        errors.append("tool_type is required")

    # 2. database_query 타입: SQL 안전성 검증
    if asset.tool_type == "database_query":
        sql = config.get("query_template", "")
        if any(kw in sql.upper() for kw in ["DROP", "DELETE", "TRUNCATE", "ALTER"]):
            errors.append(f"Dangerous SQL keyword in query_template")

    # 3. input_schema 유효성
    if asset.tool_input_schema:
        try:
            jsonschema.validate(schema=asset.tool_input_schema, instance={})
        except jsonschema.exceptions.SchemaError as e:
            errors.append(f"Invalid input schema: {e.message}")

    return errors
```

**완료 기준**:
- [ ] `validate_tool_asset()` 함수 구현
- [ ] `validate_asset()`에 tool 타입 추가
- [ ] 위험 SQL 패턴 감지
- [ ] 게시 전 검증 강제

---

### 3.1 P0 (즉시 적용) - 1주차

#### P0-1. 오케스트레이션 SLO 정의 및 강제 계측

**목표**: 모든 요청에 필수 태깅 및 SLO 지표 수집

**구현 위치**:
- `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
- `apps/api/app/modules/inspector/span_tracker.py`

**작업 내용**:
```python
# 새 파일: apps/api/app/modules/ops/services/ci/metrics.py
class OrchestrationMetrics:
    """Orchestration SLO metrics collector."""

    METRICS = {
        "latency_p50": "histogram",
        "latency_p95": "histogram",
        "latency_p99": "histogram",
        "tool_fail_rate": "counter",
        "fallback_rate": "counter",
        "replan_rate": "counter",
        "timeout_rate": "counter",
    }

    REQUIRED_TAGS = ["trace_id", "tenant_id", "plan_id", "tool_call_id"]
```

**완료 기준**:
- [ ] 모든 orchestration 요청에 필수 태그 포함
- [ ] p50/p95/p99 latency 수집
- [ ] tool fail rate, fallback rate 메트릭 노출

---

#### P0-2. Tool 실행 정책 가드레일 추가

**목표**: tool별 timeout, max_retries, rate_limit 정책 적용

**구현 위치**:
- `apps/api/app/modules/ops/services/ci/tools/base.py`
- `apps/api/app/modules/ops/services/ci/tools/executor.py`

**작업 내용**:
```python
# 새 파일: apps/api/app/modules/ops/services/ci/tools/policy.py
@dataclass
class ToolExecutionPolicy:
    """Tool execution policy for fail-closed behavior."""
    timeout_ms: int = 30000  # 30초
    max_retries: int = 2
    breaker_threshold: int = 5  # 5회 실패 시 circuit breaker 오픈
    rate_limit_per_minute: int = 100

    # SQL 특화 정책
    enforce_readonly: bool = True
    block_ddl: bool = True
    block_dcl: bool = True
    max_rows: int = 10000

DEFAULT_POLICY = ToolExecutionPolicy()
SQL_TOOL_POLICY = ToolExecutionPolicy(
    enforce_readonly=True,
    block_ddl=True,
    max_rows=5000,
)
```

**완료 기준**:
- [ ] 모든 tool 실행에 policy 적용
- [ ] timeout 초과 시 ToolResult 실패 반환
- [ ] 정책 없는 SQL/HTTP tool 실행 차단 (fail-closed)

---

#### P0-3. 실패 분류 체계 도입

**목표**: 표준화된 에러 코드로 실패 원인 분류

**구현 위치**: `apps/api/schemas/tool_contracts.py`

**작업 내용**:
```python
class ToolErrorCode(str, Enum):
    """표준화된 Tool 실행 에러 코드"""
    POLICY_DENY = "POLICY_DENY"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_BAD_REQUEST = "TOOL_BAD_REQUEST"
    TOOL_RATE_LIMITED = "TOOL_RATE_LIMITED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    PLAN_INVALID = "PLAN_INVALID"
    TENANT_MISMATCH = "TENANT_MISMATCH"
    SQL_BLOCKED = "SQL_BLOCKED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

**예외 처리 리팩터링 대상** (최우선 5개):
1. `runner.py:5817` - silent fallback → 에러 코드 + 로깅
2. `stage_executor.py:598` - silent fallback → 에러 코드 + 로깅
3. `runner.py:1852` - main execution → 리소스 정리 + 에러 코드
4. `runner.py:868` - CI search → 구체적 에러 분류
5. `stage_executor.py:230` - Asset load → ASSET_LOAD_FAILED 코드

**완료 기준**:
- [ ] 모든 ToolResult에 error_code 필드 추가
- [ ] 최우선 5개 except 블록 리팩터링
- [ ] trace에 error_code 기록

---

#### P0-4. Direct Query 안전장치 강화

**목표**: read-only 강제, 위험 키워드/DDL 차단, tenant 필터 검증

**구현 위치**: `apps/api/app/modules/ops/services/ci/tools/direct_query_tool.py`

**추가 발견 사항 (P0-4 보완)**:
- `dynamic_tool.py:172`의 operator 검증도 함께 수정 필요
  ```python
  # 현재: where_conditions.append(f"{field} {operator} %s")
  # ← operator가 임의 SQL일 수 있음!
  # 수정: ALLOWED_OPERATORS = ["=", "!=", "<", ">", "<=", ">=", "LIKE", "ILIKE", "IN"]
  ```

**완료 기준**:
- [ ] DDL/DCL 키워드 차단
- [ ] tenant_id 필터 누락 시 실행 거부
- [ ] row limit 하드캡 (10,000건)
- [ ] `dynamic_tool.py` operator whitelist 적용
- [ ] 에러 메시지에서 스키마/테이블명 제거
- [ ] 보안 회귀 테스트 추가

#### P0-5. 요청 전체 Timeout 추가 (신규)

**목표**: `/ops/ask` 엔드포인트에 전체 timeout 추가

**구현 위치**: `apps/api/app/modules/ops/routes/ci_ask.py`

**작업**:
```python
# ci_ask.py 수정
@router.post("/ops/ask")
async def ask_ops(...):
    try:
        result = await asyncio.wait_for(
            orchestrator.run(question, context),
            timeout=60.0  # 60초 hard limit
        )
    except asyncio.TimeoutError:
        return ResponseEnvelope.error(
            code=504,
            message="요청 처리 시간이 60초를 초과했습니다"
        )
```

**완료 기준**:
- [ ] `/ops/ask`에 60초 timeout 적용
- [ ] timeout 발생 시 적절한 에러 응답
- [ ] 리소스 정리 (DB 커넥션 등)

---

### 3.2 P1 (2~4주) - 2~4주차

#### P1-1. Runner 기능별 모듈화

(기존 계획 유지)

**분리 구조**:
```
apps/api/app/modules/ops/services/ci/orchestrator/
├── __init__.py
├── runner.py              # 진입점 (200라인 이하)
├── planning.py            # 계획 관련 로직
├── tool_execution.py      # Tool 실행 로직
├── composition.py         # 결과 합성 로직
├── fallback.py            # 폴백/복구 로직
├── post_processing.py     # 후처리/응답 빌딩
└── stage_executor.py      # 기존 유지
```

**완료 기준**:
- [ ] runner.py 500라인 이하
- [ ] 각 분리 모듈 500라인 이하
- [ ] 기존 테스트 모두 통과

---

#### P1-2. 병렬 실행 실제 구현 (신규 - 리뷰 미언급 추가)

**목표**: `executor.py:109`의 `asyncio.run()` 제거, 실제 병렬 실행

**구현 위치**: `apps/api/app/modules/ops/services/ci/tools/executor.py`

**작업**:
```python
# BEFORE (직렬 - 블로킹)
result = asyncio.run(tool.safe_execute(context, params))

# AFTER (비동기 - 논블로킹)
async def execute_async(self, tool_type, context, params):
    tool = self.registry.get_tool(tool_type)
    return await asyncio.wait_for(
        tool.safe_execute(context, params),
        timeout=policy.timeout_ms / 1000
    )

# 병렬 실행 (chain_executor.py에서)
results = await asyncio.gather(
    *[self.execute_async(t.type, ctx, t.params) for t in parallel_tools],
    return_exceptions=True
)
```

**완료 기준**:
- [ ] `asyncio.run()` 제거
- [ ] 독립 도구는 `asyncio.gather()`로 병렬 실행
- [ ] 의존 도구는 순차 실행 유지
- [ ] 성능 테스트: 5개 독립 도구 2,500ms → 500ms

---

#### P1-3. Inspector 도구 추적 강화 (신규)

**목표**: Inspector에서 도구별 실행 상태, 병렬/직렬, 타임아웃 추적

**구현 위치**:
- Backend: `apps/api/app/modules/inspector/models.py`
- Frontend: `apps/web/src/components/ops/OrchestrationVisualization.tsx`

**DB 스키마 변경**:
```sql
-- TbExecutionTrace에 컬럼 추가
ALTER TABLE tb_execution_trace ADD COLUMN tool_calls JSONB;
-- 구조: [{tool_call_id, tool_type, tool_asset_id, tool_name,
--          start_ms, end_ms, duration_ms, status, error_code,
--          error_message, retry_count, execution_group_index,
--          timeout_exceeded, parallel}]

ALTER TABLE tb_execution_trace ADD COLUMN execution_groups JSONB;
-- 구조: [{group_index, parallel, tools: [...], start_ms, end_ms}]

ALTER TABLE tb_execution_trace ADD COLUMN tenant_id VARCHAR(64);
```

**Frontend 개선**:
```tsx
// OrchestrationVisualization.tsx에 추가
// 1. 워터폴 타임라인
<WaterfallTimeline toolCalls={trace.tool_calls} />

// 2. 도구 상태 배지
<ToolStatusBadge status={tool.status} error={tool.error_code} />

// 3. 병렬 그룹 시각화
<ParallelGroupView groups={trace.execution_groups} />
```

**완료 기준**:
- [ ] `tool_calls` JSONB 컬럼 추가 (Alembic)
- [ ] `execution_groups` JSONB 컬럼 추가
- [ ] `tenant_id` 컬럼 추가
- [ ] Runner에서 tool_call 정보 수집 및 저장
- [ ] 워터폴 타임라인 UI 구현
- [ ] 도구 상태 배지 (success/error/timeout) 표시
- [ ] 병렬 그룹 시각화

---

#### P1-4. Inspector 리플레이 기능 (신규)

**목표**: 실패한 trace를 동일/수정된 조건으로 재실행

**구현 위치**:
- Backend: `apps/api/app/modules/inspector/router.py`
- Frontend: `apps/web/src/app/admin/inspector/page.tsx`

**API**:
```python
# inspector/router.py에 추가
@router.post("/inspector/traces/{trace_id}/replay")
async def replay_trace(
    trace_id: str,
    body: ReplayRequest,  # asset_overrides, parameters 선택적
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """기존 trace를 재실행하고 새 trace 생성"""
    original = get_execution_trace(session, trace_id)
    # 원본 질의 + asset override 적용
    new_trace_id = await orchestrator.run(
        question=original.question,
        asset_overrides=body.asset_overrides,
        parent_trace_id=trace_id,  # 계보 추적
    )
    return ResponseEnvelope.success(data={"new_trace_id": new_trace_id})
```

**Frontend**:
```tsx
// Inspector 상세 화면에 추가
<Button onClick={() => replayTrace(traceId)}>
  리플레이
</Button>
<Button onClick={() => openAssetOverrideModal(traceId)}>
  Asset 변경 후 리플레이
</Button>
```

**완료 기준**:
- [ ] `POST /inspector/traces/{trace_id}/replay` 엔드포인트
- [ ] parent_trace_id로 계보 추적
- [ ] Asset Override 적용 리플레이
- [ ] Frontend 리플레이 버튼

---

#### P1-5. 부분 성공 응답 계약

(기존 계획 유지)

```python
class OrchestrationStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    DEGRADED = "degraded"
    FAILED = "failed"
```

**완료 기준**:
- [ ] 1개 tool 실패 시 partial_success 반환
- [ ] 실패한 tool 목록 포함
- [ ] 사용자 친화 fallback 문구

---

#### P1-6. Tool Capability Registry 확장

(기존 계획 유지)

---

#### P1-7. 테스트 보강 (회귀 + 카오스)

(기존 계획 유지 + 추가)

**추가 테스트 시나리오**:

| 시나리오 | 테스트 파일 | 우선순위 |
|----------|------------|----------|
| tool timeout | `test_tool_timeout.py` | P0 |
| 5xx 응답 | `test_upstream_failure.py` | P0 |
| tenant mismatch | `test_tenant_boundary.py` | P0 |
| DDL 차단 | `test_sql_security.py` | P0 |
| operator injection | `test_operator_whitelist.py` | P0 |
| invalid schema | `test_invalid_schema.py` | P1 |
| 부분 실패 | `test_partial_success.py` | P1 |
| SSRF (MCP) | `test_mcp_ssrf.py` | P0 |
| credential 노출 | `test_credential_exposure.py` | P0 |
| 권한 없는 tool 접근 | `test_tool_authorization.py` | P0 |

---

### 3.3 P2 (5~8주) - 중기

#### P2-1. Regression 자동화 (신규)

**목표**: Golden Query를 자동으로 실행하고 회귀를 감지

**작업**:
1. `TbGoldenQuery`에 `schedule` 필드 추가 (cron 표현식)
2. 백그라운드 스케줄러 구현 (croniter 기반)
3. Asset 변경 시 자동 트리거
4. 결과 알림 (Slack/Email)

**완료 기준**:
- [ ] 야간 배치 회귀 실행
- [ ] Asset 변경 트리거
- [ ] FAIL 시 알림

#### P2-2. Regression Rule Config CRUD (신규)

**목표**: `TbRegressionRuleConfig` 테이블을 실제로 활용

**작업**:
1. CRUD 엔드포인트 추가
2. `determine_judgment()`가 config 참조하도록 수정
3. UI에서 golden query별 임계값 설정

#### P2-3. Inspector 에러 대시보드 (신규)

**목표**: 에러 패턴/트렌드 분석 대시보드

**작업**:
```
GET /inspector/errors?from={date}&to={date}&category={tool|timeout|orchestrator}
Returns: {total_errors, by_category, by_tool, by_error_code, trend}
```

#### P2-4. 비용/성능 최적화 루프

(기존 계획 유지)

#### P2-5. 운영 콘솔 정책 시뮬레이터

(기존 계획 유지)

#### P2-6. Soft Delete 구현 (신규)

**목표**: Asset 삭제를 soft delete로 변경

**작업**:
- `TbAssetRegistry`에 `deleted_at` 컬럼 추가
- 삭제 API에서 `deleted_at = now()` 설정
- 목록 조회에서 `deleted_at IS NULL` 필터
- 관리자 전용 복구 API

---

## 4. 실행 로드맵

```
BLOCKER (Day 0, P0 전):
├── Tool 엔드포인트 권한 체크 (BLOCKER-1)
├── Credential 평문 저장 제거 (BLOCKER-2)
└── Tool Asset 검증 추가 (BLOCKER-3)

Week 1 (P0):
├── Day 1-2: SLO/에러코드 스키마 확정 (P0-1, P0-3)
├── Day 3-4: Tool 실행 정책 가드레일 추가 (P0-2)
├── Day 4: Direct Query 안전장치 강화 (P0-4)
└── Day 5: 요청 timeout + 보안 회귀 테스트 (P0-5)

Week 2 (P1 시작):
├── Day 1-2: Runner 1차 분해 (P1-1)
├── Day 3-4: 병렬 실행 실제 구현 (P1-2)
└── Day 5: partial_success 계약 반영 (P1-5)

Week 3 (P1 계속):
├── Day 1-2: Inspector 도구 추적 강화 - DB (P1-3)
├── Day 3-4: Inspector 도구 추적 강화 - UI (P1-3)
└── Day 5: Inspector 리플레이 기능 (P1-4)

Week 4 (P1 완료):
├── Day 1-2: Tool Capability Registry (P1-6)
├── Day 3-4: 카오스/보안 테스트 (P1-7)
└── Day 5: 통합 테스트 + 문서

Week 5-8 (P2):
├── Regression 자동화 (P2-1)
├── Rule Config CRUD (P2-2)
├── 에러 대시보드 (P2-3)
├── 비용/성능 최적화 (P2-4)
├── 정책 시뮬레이터 (P2-5)
└── Soft Delete (P2-6)
```

---

## 5. 목표 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        OPS Orchestration v2                      │
├─────────────┬─────────────┬──────────────┬─────────────────────┤
│   Planner   │   Policy    │    Tool      │      Composer       │
│  (intent +  │   Engine    │   Runtime    │  (partial success   │
│ capability) │ (가드레일)  │ (timeout/    │   + reference 일관) │
│             │             │ retry/limit) │                     │
│             │             │ **asyncio.   │                     │
│             │             │  gather()**  │                     │
├─────────────┴─────────────┴──────────────┴─────────────────────┤
│                         Observer                                │
│  trace/metric/log 표준 스키마 + SLO 대시보드 + tool_call 추적   │
│  워터폴 타임라인 + 병렬 그룹 + 리플레이 + 에러 대시보드          │
├─────────────────────────────────────────────────────────────────┤
│                    Security Layer                                │
│  RBAC + Credential Vault + SQL Guard + Tenant Isolation          │
├─────────────────────────────────────────────────────────────────┤
│                    Regression Gate                                │
│  자동 회귀 + Rule Config + Trend + Alert + CI/CD                 │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 원칙**: "잘 되는 데모" → **"실패해도 안전하게 동작하고 원인 추적이 빠른 시스템"**

---

## 6. 영역별 Production Readiness Score

| 영역 | 현재 | BLOCKER+P0 후 | P1 후 | P2 후 |
|------|:---:|:---:|:---:|:---:|
| **Orchestrator 실행** | 55% | 75% | 90% | 95% |
| **보안 거버넌스** | 30% | 70% | 85% | 95% |
| **Inspector 가시성** | 45% | 55% | 85% | 95% |
| **Regression 자동화** | 35% | 35% | 40% | 80% |
| **Asset 관리** | 60% | 80% | 85% | 95% |
| **전체 평균** | **45%** | **63%** | **77%** | **92%** |

---

## 7. 의존성 및 위험

### 7.1 의존성
- `ops_ci_api` 테스트 스위트 정상 동작 필요
- Asset Registry DB 마이그레이션 완료 필요
- Redis 캐시 인프라 안정적 운영 필요
- Alembic 마이그레이션 (Inspector 스키마 변경)

### 7.2 위험 요소
| 위험 | 완화 방안 |
|------|----------|
| Runner 분해 시 회귀 | 분해 전/후 동일 테스트 스위트 실행 |
| 보안 정책 과도한 차단 | allowlist와 denylist 병행, 로그 확인 |
| 성능 저하 | baseline 측정 후 10% 이상 저하 시 원인 분석 |
| Inspector 스키마 변경 | backward-compatible 마이그레이션 (nullable 필드) |
| 병렬 실행 전환 | Feature flag로 점진 활성화 |

---

## 8. 승인 및 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-02-14 | AI Agent | 초기 계획 수립 (리뷰 기반) |
| 2.0 | 2026-02-14 | AI Agent | 코드 심층 분석 반영: BLOCKER 3건 추가, Inspector/Regression 개선안 추가, 보안 취약점 10건 식별, 병렬 실행 허상 발견 |

---

## 다음 단계

1. **BLOCKER 즉시 수정** - 보안 취약점 3건 (권한/credential/검증)
2. **P0-1 착수** - SLO/에러코드 스키마 확정부터 시작
3. **주간 진행 회의** - 매주 진행 상황 리뷰
