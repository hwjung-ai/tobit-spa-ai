# 모듈별 상용화 준비도 감사 보고서 (v2 - 보완)

**작성일**: 2026-02-14
**보완일**: 2026-02-14
**범위**: 전체 7개 Backend 모듈 + Frontend + 인프라
**목적**: Production 전환 전 비판적 검토
**보완 사유**: 초판에서 OPS Orchestration, Asset Registry, Document Processor, Frontend 누락

---

## 📊 Executive Summary

| 모듈 | 코드량 | 준비도 | 주요 리스크 | 권장 조치 |
|------|--------|--------|------------|----------|
| **OPS Orchestration** | 39,023줄 | 🔴 미흡 | runner.py 6,326줄 monolith, except 200+건 | **P0 분해 필수** |
| **Asset Registry** | 7,350줄 | 🟡 중간 | router.py 1,896줄, silent failure 3건 | P1 리팩터링 |
| **API Manager** | 4,061줄 | 🟡 중간 | router.py 1,522줄, except 60건 | P1 리팩터링 |
| **CEP Builder** | 9,355줄 | 🟡 중간 | router/executor 비대화, except 85건 | P1 리팩터링 |
| **Document Processor** | 2,147줄 | 🟢 양호 | router.py 1,328줄 | 유지 |
| **Admin** | ~400줄 | 🟢 양호 | 파일 크기 적절, except 5건 | 유지 |
| **Simulation** | ~7,000줄 | 🟢 양호 | 모듈화 잘 됨, except 20건 | 유지 |
| **Frontend** | 65,690줄 | 🔴 미흡 | 테스트 3개, console.log 59개 | **P0 정리 필수** |

**보정된 프로덕션 준비도: 72/100**

---

## 0️⃣ OPS Orchestration 상용화 검토 (신규 - Critical)

> 초판에서 **완전히 누락**된 가장 큰 모듈. 전체 코드의 56%를 차지.

### 📁 파일 구조 분석

| 파일 | 라인 수 | except Exception | 상태 |
|------|---------|-----------------|------|
| `orchestrator/runner.py` | **6,326** | 29 | 🔴 Critical |
| `router.py` (모듈 root) | **3,119** | 41 | 🔴 Critical |
| `orchestrator/stage_executor.py` | 2,086 | 16 | 🔴 |
| `planner/planner_llm.py` | 1,676 | 7 | 🟡 |
| `services/__init__.py` | **1,614** | 14 | 🔴 |
| `services/action_registry.py` | 1,555 | 9 | 🟡 |
| `tools/dynamic_tool.py` | 1,081 | 8 | 🟡 |
| `services/rca_engine.py` | 992 | - | 🟡 |
| `orchestrator/tool_orchestration.py` | 854 | - | 🟡 |
| `planner/validator.py` | 736 | - | 🟡 |
| `routes/ci_ask.py` | 682 | 11 | 🟡 |
| `services/query_decomposition_runner.py` | 614 | - | ✅ |
| `services/report_service.py` | 559 | 3 | ✅ |
| `orchestrator/chain_executor.py` | 518 | - | ✅ |
| `security.py` | 500 | - | ✅ |
| `tools/runtime_tool_discovery.py` | 499 | 9 | ✅ |
| 기타 60+파일 | ~16,612 | ~53 | - |
| **Total** | **39,023** | **200+** | |

### 🔴 R1. runner.py Monolith (6,326줄) - 최우선 리팩터링

**문제점**:
- 단일 파일에 planning, execution, caching, error handling, response building 혼재
- 29개 `except Exception` 핸들러 (에러 원인 분류 불가)
- `parallel_executor.py` (324줄), `runner_base.py` (120줄) 생성했지만 **미사용 (Dead Code)**
- 직렬 실행 유지 중 (병렬 실행 모듈 미통합)

**권장 분리**:
```
orchestrator/
├── runner.py              # 메인 진입점 (~300줄)
├── phases/
│   ├── planning.py        # Plan 생성/검증
│   ├── tool_resolution.py # Tool 선택/매핑
│   ├── execution.py       # Tool 실행 (ParallelExecutor 통합)
│   ├── aggregation.py     # 결과 집계/LLM 요약
│   └── response.py        # 응답 포매팅
├── runner_context.py      # 실행 컨텍스트 (기존 runner_base.py 활용)
└── parallel_executor.py   # 기존 파일 (통합 필요)
```

### 🔴 R2. router.py (3,119줄) + services/__init__.py (1,614줄)

**문제점**:
- `router.py`에 41건의 `except Exception` (프로젝트 전체 최다)
- `services/__init__.py`에 비즈니스 로직 + 라우팅 혼재 (1,614줄)

**권장 분리 (router.py)**:
```
routes/
├── __init__.py        # 라우터 결합
├── orchestration.py   # /ops/ask, /ops/query (핵심)
├── threads.py         # 스레드 관리 (기존)
├── actions.py         # 액션 실행 (기존)
├── regression.py      # 회귀 분석 (기존)
├── rca.py             # 근본 원인 분석 (기존)
└── ui_actions.py      # UI 액션 (기존)
```

### 🔴 R3. except Exception 200+건

**Top offenders**:

| 파일 | 건수 | 심각도 |
|------|------|--------|
| `router.py` | 41 | 🔴 |
| `runner.py` | 29 | 🔴 |
| `stage_executor.py` | 16 | 🔴 |
| `services/__init__.py` | 14 | 🔴 |
| `ci_ask.py` | 11 | 🟡 |
| `runtime_tool_discovery.py` | 9 | 🟡 |
| `action_registry.py` | 9 | 🟡 |
| `dynamic_tool.py` | 8 | 🟡 |
| 기타 12개 파일 | ~63 | 🟡 |

**권장 예외 체계**:
```python
# core/exceptions.py (공통 예외 모듈 신설)
class OpsBaseError(Exception): pass
class ToolExecutionError(OpsBaseError): pass      # Tool 실행 실패
class PlanningError(OpsBaseError): pass            # Plan 생성 실패
class ConnectionError(OpsBaseError): pass          # DB/외부 연결 실패
class TenantIsolationError(OpsBaseError): pass     # 테넌트 격리 위반
class TimeoutError(OpsBaseError): pass             # 타임아웃
class ValidationError(OpsBaseError): pass          # 입력 검증 실패
```

### 🟡 R4. Dead Code

| 파일 | 줄 수 | 상태 |
|------|-------|------|
| `runner_base.py` | 120 | 미사용 |
| `parallel_executor.py` | 324 | 미사용 |

runner.py 리팩터링 시 통합하거나, 사용하지 않을 경우 삭제 필요.

---

## 1️⃣ API Manager 상용화 검토

### 📁 파일 구조 분석

| 파일 | 라인 수 | 상태 |
|------|---------|------|
| `router.py` | **1,522** | 🔴 비대화 |
| `workflow_executor.py` | 375 | 🟡 |
| `executor.py` | 334 | 🟡 |
| `script_executor_runner.py` | 329 | 🟡 |
| `runtime_router.py` | 318 | 🟡 |
| `schemas.py` | 221 | ✅ |
| `crud.py` | 184 | ✅ |
| `cache_service.py` | 139 | ✅ |
| `models.py` | 135 | ✅ |
| `script_executor.py` | 122 | ✅ |
| **Total** | **4,061** | |

### 🔴 R1. Router 비대화 (Critical)

**문제점**:
- `router.py`가 1,522줄로 단일 파일에 과도한 로직 집중
- 19개 엔드포인트가 하나의 파일에 혼재
- 변경 충돌 가능성 높음

**권장 분리**:
```
router/
├── __init__.py          # 메인 라우터 결합
├── discovery.py         # /discover, /register-discovered
├── crud.py              # /, /{api_id}, /create, /update
├── versioning.py        # /{api_id}/versions, /{api_id}/rollback
├── execution.py         # /{api_id}/execute, /{api_id}/test
├── export.py            # /{api_id}/export, /{api_id}/unlink-tool
└── logs.py              # /{api_id}/logs
```

### 🔴 R2. 광범위 예외처리 패턴 (60건)

**검출된 패턴**:
```python
# router.py - 22건
except Exception as e:
    logger.error(f"List APIs failed: {str(e)}")
    return ResponseEnvelope.error(...)

# executor.py - 6건
except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc))

# cache_service.py - 3건
except Exception as exc:
    self._redis = None
    return None  # Silent failure
```

### 🟡 R3. 인증/테넌트 격리

- 일부 엔드포인트에만 `get_current_user` 적용
- `tenant_id` 필터링 일부 누락
- `runtime_router.py`는 인증 없음

### 🟡 R4. 테스트 커버리지

| 테스트 파일 | 상태 |
|------------|------|
| `test_api_manager_executor.py` | ✅ |
| `test_api_manager_script_executor.py` | ✅ |
| `test_api_manager_workflow_executor.py` | ✅ |
| `test_api_manager_auth_policy.py` | ✅ |
| `test_api_cache_service.py` | ✅ |
| **카오스 테스트** | ❌ 없음 |

---

## 2️⃣ CEP Builder 상용화 검토

### 📁 파일 구조 분석

| 파일 | 라인 수 | 상태 |
|------|---------|------|
| `router.py` | **1,578** | 🔴 비대화 |
| `executor.py` | **1,170** | 🔴 비대화 |
| `redis_state_manager.py` | 666 | 🟡 |
| `scheduler.py` | 548 | 🟡 |
| `notification_channels.py` | 488 | ✅ |
| `cep_routes.py` | 462 | ✅ |
| `bytewax_engine.py` | 409 | ✅ |
| `notification_retry.py` | 415 | ✅ |
| `cache_manager.py` | 382 | ✅ |
| `notification_templates.py` | 366 | ✅ |
| `notification_engine.py` | 325 | ✅ |
| `crud.py` | 323 | ✅ |
| `schemas.py` | 327 | ✅ |
| 기타 7개 파일 | ~1,778 | ✅ |
| **Total** | **9,355** | |

### 🔴 R1. Router/Executor 비대화 (Critical)

**권장 분리 (router.py)**:
```
router/
├── __init__.py
├── rules.py             # Rule CRUD
├── notifications.py     # Notification CRUD
├── simulation.py        # Simulation endpoints
├── events.py            # SSE streaming
├── scheduler.py         # Scheduler status
└── performance.py       # Stats/metrics
```

**권장 분리 (executor.py)**:
```
executor/
├── __init__.py
├── rule_executor.py     # Rule evaluation
├── metric_executor.py   # Metric polling
├── notification_executor.py  # Notification dispatch
└── baseline_executor.py # Baseline calculation
```

### 🔴 R2. 광범위 예외처리 패턴 (85건)

| 파일 | 예외처리 수 | 비고 |
|------|------------|------|
| `redis_state_manager.py` | 22건 | silent failure 다수 |
| `router.py` | 15건 | |
| `cep_routes.py` | 14건 | |
| `notification_channels.py` | 8건 | |
| `scheduler.py` | 7건 | |

### 🟡 R3. 테넌트 격리

- `cep_routes.py`: 전체 적용 ✅
- `router.py`: 부분 적용 (인증 없는 엔드포인트 존재)

### 🟡 R4. Redis 의존성

- 22개 함수가 Redis 직접 사용
- 장애 시 silent failure → circuit breaker 필요

---

## 3️⃣ Asset Registry 상용화 검토 (신규)

> 초판에서 **완전히 누락**된 모듈.

### 📁 파일 구조 분석

| 파일 | 라인 수 | except Exception | 상태 |
|------|---------|-----------------|------|
| `router.py` | **1,896** | 9 | 🔴 비대화 |
| `crud.py` | 1,377 | 3 | 🟡 |
| `tool_router.py` | 1,187 | 6 | 🟡 |
| `loader.py` | 870 | 2 | 🟡 |
| `validators.py` | 377 | 1 | ✅ |
| `schema_models.py` | 308 | - | ✅ |
| `tool_validator.py` | 274 | 1 | ✅ |
| `resolver_models.py` | 225 | - | ✅ |
| `credential_manager.py` | 206 | - | ✅ |
| `schemas.py` | 193 | - | ✅ |
| `source_models.py` | 187 | - | ✅ |
| `models.py` | 178 | - | ✅ |
| `query_models.py` | 58 | - | ✅ |
| **Total** | **7,350** | **22** | |

### 🔴 R1. Silent Failure (except Exception: pass)

```python
# router.py - 3곳에서 except Exception: pass 발견
except Exception:
    pass  # 에러 완전 무시 - 원인 추적 불가
```

이 패턴은 프로덕션에서 **가장 위험**합니다. 에러가 발생해도 로그조차 남지 않아 장애 원인 파악이 불가합니다.

### 🟡 R2. router.py 비대화 (1,896줄)

API Manager, CEP와 동일한 패턴. 기능별 분리 권장.

### 🟡 R3. credential_manager.py 보안

- `source_models.py`에 `password` 필드가 plain text 허용
- `secret_key_ref` 대안 존재하지만, plain text 경로 제거 필요

---

## 4️⃣ Document Processor 상용화 검토 (신규)

> 초판에서 **누락**된 모듈.

### 📁 파일 구조 분석

| 파일 | 라인 수 | 상태 |
|------|---------|------|
| `router.py` | 1,328 | 🟡 |
| `crud.py` | 476 | ✅ |
| `search_crud.py` | 327 | ✅ |
| `__init__.py` | 16 | ✅ |
| **Total** | **2,147** | |

### ✅ 양호한 점

1. 모듈 크기 적절
2. 검색 기능 분리 (search_crud.py)
3. pgvector + BM25 하이브리드 검색 구현

### 🟡 개선 권장

- `router.py` 1,328줄 → 기능별 분리 고려 (document CRUD vs search)

---

## 5️⃣ Admin>Tools 상용화 검토

### 📁 파일 구조 분석

| 파일 | 라인 수 | 상태 |
|------|---------|------|
| `crud.py` | 375 | ✅ 적절 |
| `routes/logs.py` | - | ✅ |
| `__init__.py` | 2 | ✅ |

### ✅ 양호한 점

1. **파일 크기 적절**: 최대 375줄
2. **예외처리 5건**: 매우 적음
3. **명확한 로깅**: `logger.warning` 사용

---

## 6️⃣ Simulation 상용화 검토

### 📁 파일 구조 분석

| 파일 | 라인 수 | 상태 |
|------|---------|------|
| `ml_functions.py` | 991 | 🟡 |
| `domain_functions.py` | 880 | 🟡 |
| `router.py` | 759 | 🟡 |
| `stat_functions.py` | 700 | 🟡 |
| `rule_functions.py` | 680 | 🟡 |
| `sse_handler.py` | 464 | ✅ |
| `user_functions.py` | 362 | ✅ |
| `baseline_loader.py` | 310 | ✅ |
| 기타 | ~1,854 | ✅ |

### ✅ 양호한 점

1. **모듈화 잘 됨**: Strategy 패턴 적용
2. **테넌트 격리 검증됨**: `test_simulation_tenant_isolation.py` 존재
3. **테스트 풍부**: 4개 테스트 파일

### 🟡 예외처리 (20건)

- `baseline_loader.py`: 5건 silent (`except Exception: pass`)
- `sse_handler.py`: 4건 (적절한 SSE 에러 이벤트)

---

## 7️⃣ AI Copilot (LLM Client) 품질 검토

### 📁 LLM 클라이언트 구조 분석

**위치**: `app/llm/client.py`

#### ✅ 잘 되어 있는 점

| 기준 | 상태 | 설명 |
|------|------|------|
| **Provider 추상화** | ✅ | OpenAI, Internal 지원 |
| **Fallback Model** | ✅ | 설정 가능 |
| **Timeout/Retry** | ✅ | DB 기반 설정 (120s, 2회) |
| **Call Logging** | ✅ | LlmCallLogger + DB 저장 |
| **Streaming** | ✅ | SSE 호환 async generator |

#### 🟡/🔴 개선 필요

| 기준 | 상태 | 설명 |
|------|------|------|
| **Token Budget** | 🟡 | max_tokens가 kwargs에 묻혀 있음 |
| **Context Window** | 🟡 | 자동 truncation 없음 |
| **Circuit Breaker** | 🔴 | 완전 장애 시 대응 없음 |
| **Prompt Versioning** | 🟡 | A/B 테스트 미지원 |

---

## 8️⃣ Frontend 품질 검토 (신규 - Critical)

> 초판에서 **완전히 누락**. 65,690줄 TypeScript/React 코드.

### 📁 대형 파일 (1,000줄 초과) - 10개

| 파일 | 라인 수 | 상태 |
|------|---------|------|
| `api-manager/page.tsx` | **2,590** | 🔴 Critical |
| `admin/inspector/page.tsx` | **2,212** | 🔴 Critical |
| `UIScreenRenderer.tsx` | **2,009** | 🔴 |
| `PropertiesPanel.tsx` | **1,587** | 🔴 |
| `cep-builder/page.tsx` | **1,564** | 🔴 |
| `editor-state.ts` | **1,530** | 🔴 |
| `documents/page.tsx` | **1,386** | 🟡 |
| `sim/page.tsx` | **1,257** | 🟡 |
| `ops/page.tsx` | **1,165** | 🟡 |
| `BlockRenderer.tsx` | **1,121** | 🟡 |

추가로 500-1,000줄 파일이 **14개** 더 존재.

### 🔴 R1. 프론트엔드 테스트 부재 (Critical)

| 메트릭 | 값 | 판정 |
|--------|-----|------|
| 총 TS/TSX 코드 | 65,690줄 | - |
| 테스트 파일 수 | **3개** | 🔴 Critical |
| 테스트 커버리지 | **~0.05%** | 🔴 Critical |

존재하는 테스트:
- `apiManagerSave.test.js` (1개)
- `RuleStatsCard.test.tsx` (1개)
- `SystemHealthChart.test.tsx` (1개)

65,690줄 코드에 테스트 3개는 사실상 **테스트 없음**과 동일.

### 🔴 R2. console.log 59개 (프로덕션 노출)

| 파일 | 건수 | 위험도 |
|------|------|--------|
| `editor-state.ts` | **21** | 🔴 payload 데이터 노출 |
| `adminUtils.ts` | 8 | 🟡 |
| `ChatExperience.tsx` | 5 | 🟡 |
| `BlockRenderer.tsx` | 4 | 🟡 |
| 기타 10+파일 | 21 | 🟡 |

**특히 위험한 패턴**:
```typescript
// editor-state.ts - 사용자 데이터가 브라우저 콘솔에 노출
console.log("[EDITOR] PUT payload:", putPayload);
console.log("[EDITOR] Screen data:", state.screen);
```

### 🟡 R3. TypeScript `any` 사용 (19건)

19건은 65K 코드 대비 적은 편이나, 프로덕션 전 제거 권장.

---

## 9️⃣ 인프라 및 의존성 검토 (신규)

### 🔴 R1. 의존성 버전 미고정

`requirements.txt`에서 34개 패키지 중 **26개가 버전 미지정**:

```
# 위험 - 버전 없음
fastapi          # Breaking change 가능
uvicorn          # Breaking change 가능
sqlmodel         # Breaking change 가능
redis            # Breaking change 가능
neo4j            # Breaking change 가능

# 양호 - 최소 버전 있음
pydantic>=2.0
openai>=1.0.0
psycopg[binary]>=3.1
```

**위험**: `pip install -r requirements.txt` 실행 시점에 따라 다른 버전 설치 가능.

### 🟡 R2. Dev/Prod 의존성 미분리

`pytest`, `ruff`, `mypy` 등 개발 도구가 프로덕션 의존성과 혼재.

### 🟡 R3. 마이그레이션 실패 무시

```python
# main.py - 마이그레이션 실패해도 서버 시작
try:
    command.upgrade(alembic_cfg, "head")
except Exception as upgrade_error:
    logger.warning("Migration upgrade failed (non-fatal)")
    logger.info("Proceeding with current database schema")  # 불완전 스키마로 운영
```

프로덕션에서는 마이그레이션 실패 시 **fail-closed** 해야 합니다.

### ✅ R4. 보안 (양호)

- 하드코딩된 API 키/비밀번호: **0건** (환경변수 + encryption manager 사용)
- CORS: 프로덕션 환경 별도 제한 ✅
- Alembic 마이그레이션: 57개, 파괴적 작업(DROP/DELETE) **0건** ✅

---

## 📋 보정된 종합 개선 로드맵

### P0 (즉시, 1주) - 프로덕션 차단 이슈

| # | 모듈 | 작업 | 영향도 |
|---|------|------|--------|
| 1 | **Frontend** | console.log 59건 제거 | 데이터 노출 차단 |
| 2 | **인프라** | requirements.txt 버전 고정 | 빌드 안정성 |
| 3 | **OPS** | 공통 예외 체계 도입 (`core/exceptions.py`) | 장애 분류 가능 |
| 4 | **AI Copilot** | LLM Circuit Breaker 구현 | 완전 장애 대응 |
| 5 | **인프라** | main.py 마이그레이션 실패 시 fail-closed | 스키마 무결성 |

### P1 (2주) - 아키텍처 부채

| # | 모듈 | 작업 | 영향도 |
|---|------|------|--------|
| 6 | **OPS** | runner.py 분해 (6,326줄 → 5개 phase 파일) | 유지보수성 |
| 7 | **OPS** | router.py 분해 (3,119줄 → 6개 라우트 파일) | 변경 격리 |
| 8 | **API Manager** | router.py 분해 (1,522줄 → 6개 파일) | 변경 격리 |
| 9 | **CEP** | router.py + executor.py 분해 | 변경 격리 |
| 10 | **Asset Registry** | `except Exception: pass` 3건 제거 | 장애 추적 |
| 11 | **API Manager** | 모든 엔드포인트 인증 적용 | 보안 |
| 12 | **CEP** | 모든 엔드포인트 tenant_id 필터링 | 보안 |

### P2 (4주) - 품질 강화

| # | 모듈 | 작업 | 영향도 |
|---|------|------|--------|
| 13 | **Frontend** | 주요 컴포넌트 테스트 추가 (최소 30개) | 회귀 방지 |
| 14 | **OPS** | runner.py 카오스 테스트 | 신뢰성 |
| 15 | **인프라** | SLO/메트릭 대시보드 | 가시성 |
| 16 | **CEP** | Redis circuit breaker | 장애 격리 |

---

## 🎯 보정된 모듈별 준비도 평가

| 기준 | OPS | Asset Registry | API Manager | CEP | Doc Proc | Admin | Simulation | Frontend |
|------|-----|----------------|-------------|-----|----------|-------|------------|----------|
| 파일 크기 | 🔴 | 🟡 | 🔴 | 🔴 | 🟡 | ✅ | 🟡 | 🔴 |
| 예외 처리 | 🔴 | 🟡 | 🔴 | 🔴 | 🟡 | ✅ | 🟡 | - |
| 테넌트 격리 | 🟡 | 🟡 | 🟡 | 🟡 | ✅ | ✅ | ✅ | - |
| 인증 적용 | 🟡 | 🟡 | 🟡 | 🟡 | ✅ | ✅ | ✅ | - |
| 테스트 | ✅ | 🟡 | ✅ | ✅ | ✅ | ✅ | ✅ | 🔴 |
| **종합** | **🔴** | **🟡** | **🟡** | **🟡** | **🟢** | **🟢** | **🟢** | **🔴** |

---

## 🎯 운영 적용 최종 판정 (보정)

### ✅ 즉시 운영 가능

| 모듈 | 판정 근거 |
|------|----------|
| **Admin** | 파일 크기 적절, 예외처리 양호 |
| **Document Processor** | 모듈 크기 적절, 검색 기능 안정 |

### 🟡 조건부 운영 가능 (P0 완료 후)

| 모듈 | 차단 이유 | 필요 조치 |
|------|----------|----------|
| **Simulation** | baseline_loader silent failure | 예외 처리 개선 |
| **API Manager** | Router 비대화, 인증 미적용 일부 | 모니터링 강화 |
| **CEP Builder** | Router/Executor 비대화 | 모니터링 강화 |
| **Asset Registry** | Silent failure 3건 | `except: pass` 제거 |

### 🔴 보완 필수 (운영 전 해결)

| 모듈 | 차단 이유 | 예상 소요 |
|------|----------|----------|
| **OPS Orchestration** | 6,326줄 monolith, except 200+건 | 1주 |
| **Frontend** | console.log 59건, 테스트 0건 | 3일 |
| **AI Copilot** | Circuit Breaker 부재 | 2일 |
| **인프라** | requirements.txt 미고정, 마이그레이션 fail-open | 1일 |

---

## 📋 운영 적용 체크리스트 (보정)

### Pre-Launch (반드시 완료)

- [ ] console.log 59건 제거 (Frontend)
- [ ] requirements.txt 전체 버전 고정
- [ ] main.py 마이그레이션 fail-closed 전환
- [ ] LLM Circuit Breaker 구현
- [ ] Asset Registry `except: pass` 3건 → 적절한 에러 처리
- [ ] 공통 예외 클래스 도입 (`core/exceptions.py`)

### Week 1 (운영 첫 주)

- [ ] OPS runner.py Phase 분해 착수
- [ ] OPS router.py 분해 착수
- [ ] API Manager 엔드포인트 인증 적용
- [ ] CEP tenant_id 필터링 검증

### Week 2-4 (안정화)

- [ ] API Manager Router 분해
- [ ] CEP Router/Executor 분해
- [ ] Frontend 주요 컴포넌트 테스트 추가
- [ ] Token Budget 관리 구현
- [ ] SLO/메트릭 대시보드

---

## 💡 최종 결론 (보정)

### 운영 적용 가능 여부: **🔴 조건부 보류 → P0 완료 후 승인**

초판의 "🟡 조건부 승인"은 **3개 핵심 모듈(OPS, Asset Registry, Frontend)을 누락**한 상태에서의 판정이었습니다.

실제 코드베이스 검증 결과:
- **전체 except Exception: 350+건** (초판 145건 → 2.4배)
- **가장 큰 파일**: runner.py 6,326줄 (초판에서 누락)
- **프론트엔드 테스트**: 사실상 0% (초판에서 누락)
- **console.log**: 59건 데이터 노출 위험 (초판에서 누락)

**보정된 준비도: 72/100** (P0 항목 완료 시 85/100 달성 가능)

### 권장 실행 순서

1. **Day 1-2**: P0 즉시 항목 (console.log 제거, requirements 고정, fail-closed)
2. **Day 3-5**: Circuit Breaker + 예외 체계 도입
3. **Week 2**: OPS runner.py/router.py 분해
4. **Week 3-4**: API Manager + CEP 분해 + 프론트엔드 테스트

---

**감사 완료**: 7개 Backend 모듈 + Frontend + 인프라 + AI Copilot
**최종 판정**: P0 완료 전까지 운영 보류
**필수 사항**: console.log 제거 + requirements 고정 + Circuit Breaker + 예외 체계
