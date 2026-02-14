# Production Hardening 구현 계획서

**작성일**: 2026-02-14
**근거**: MODULES_PRODUCTION_READINESS_AUDIT.md (v2)
**목표**: 준비도 72/100 → 85/100 달성

---

## Phase 0: 즉시 실행 (Day 1-2)

> console.log 제거, requirements 고정, fail-closed 전환
> 코드 변경 최소, 리스크 최저, 효과 즉각적

### Task 0-1. Frontend console.log 제거 (59건)

**대상 파일 (주요)**:
| 파일 | 건수 |
|------|------|
| `apps/web/src/lib/ui-screen/editor-state.ts` | 21 |
| `apps/web/src/lib/adminUtils.ts` | 8 |
| `apps/web/src/components/answer/ChatExperience.tsx` | 5 |
| `apps/web/src/components/answer/BlockRenderer.tsx` | 4 |
| 기타 10+파일 | 21 |

**작업**:
1. 모든 `console.log` → 삭제 (디버그 목적)
2. 의미 있는 로그가 필요한 경우 → `if (process.env.NODE_ENV === 'development')` 가드 추가
3. 검증: `grep -r "console.log" apps/web/src/ | wc -l` → 0

**예상 변경**: ~59줄 삭제, 0줄 추가

---

### Task 0-2. requirements.txt 버전 고정

**현재 문제**: 34개 패키지 중 26개 버전 미지정

**작업**:
1. 현재 설치된 버전 확인: `pip freeze`
2. 각 패키지에 `~=` (compatible release) 제약 추가
3. dev 의존성 분리: `requirements-dev.txt` 생성

**변경 예시**:
```
# requirements.txt (production)
fastapi~=0.115.0
uvicorn[standard]~=0.34.0
pydantic>=2.0,<3.0
sqlmodel~=0.0.22
openai>=1.0.0,<2.0
redis~=5.2.0
neo4j~=5.27.0
psycopg[binary]>=3.1,<4.0
alembic~=1.14.0
httpx~=0.28.0
jinja2~=3.1.0
python-dotenv>=1.2.0
cryptography~=44.0.0
```

```
# requirements-dev.txt
-r requirements.txt
pytest~=8.3.0
ruff~=0.9.0
mypy~=1.14.0
```

---

### Task 0-3. main.py 마이그레이션 fail-closed

**현재 (위험)**:
```python
try:
    command.upgrade(alembic_cfg, "head")
except Exception as upgrade_error:
    logger.warning("Migration upgrade failed (non-fatal)")
    logger.info("Proceeding with current database schema")
```

**변경**:
```python
try:
    command.upgrade(alembic_cfg, "head")
except Exception as upgrade_error:
    if settings.app_env == "prod":
        logger.critical(f"Migration failed in production: {upgrade_error}")
        raise SystemExit(1)
    else:
        logger.warning(f"Migration failed (non-prod, continuing): {upgrade_error}")
```

**예상 변경**: ~5줄

---

## Phase 1: 예외 체계 + Circuit Breaker (Day 3-5)

### Task 1-1. 공통 예외 클래스 도입

**새 파일**: `apps/api/core/exceptions.py`

```python
"""공통 예외 클래스 - 모든 모듈에서 사용"""

class AppBaseError(Exception):
    """애플리케이션 기본 에러"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class ConnectionError(AppBaseError):
    """DB/Redis/외부 서비스 연결 실패 (재시도 가능)"""
    def __init__(self, service: str, message: str):
        super().__init__(f"{service} connection failed: {message}", "CONNECTION_ERROR")
        self.service = service

class TimeoutError(AppBaseError):
    """작업 타임아웃 (에스컬레이션 필요)"""
    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(f"{operation} timed out after {timeout_seconds}s", "TIMEOUT")

class ValidationError(AppBaseError):
    """입력 검증 실패 (400 응답)"""
    def __init__(self, field: str, message: str):
        super().__init__(f"Validation failed for {field}: {message}", "VALIDATION_ERROR")

class TenantIsolationError(AppBaseError):
    """테넌트 격리 위반 (403 응답, 감사 로그 필수)"""
    def __init__(self, tenant_id: str):
        super().__init__(f"Tenant isolation violation: {tenant_id}", "TENANT_VIOLATION")

class ToolExecutionError(AppBaseError):
    """Tool 실행 실패"""
    def __init__(self, tool_name: str, message: str):
        super().__init__(f"Tool '{tool_name}' failed: {message}", "TOOL_ERROR")
        self.tool_name = tool_name

class PlanningError(AppBaseError):
    """LLM Plan 생성 실패"""
    pass

class CircuitOpenError(AppBaseError):
    """Circuit breaker가 열린 상태"""
    def __init__(self, service: str):
        super().__init__(f"Circuit breaker open for {service}", "CIRCUIT_OPEN")
        self.service = service
```

**새 파일**: `apps/api/core/exception_handlers.py`

FastAPI 글로벌 예외 핸들러 등록:
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from core.exceptions import *

async def app_error_handler(request: Request, exc: AppBaseError):
    status_map = {
        "VALIDATION_ERROR": 400,
        "TENANT_VIOLATION": 403,
        "CONNECTION_ERROR": 503,
        "TIMEOUT": 504,
        "CIRCUIT_OPEN": 503,
    }
    status = status_map.get(exc.code, 500)
    return JSONResponse(status_code=status, content={"error": exc.code, "message": exc.message})
```

`main.py`에 등록:
```python
app.add_exception_handler(AppBaseError, app_error_handler)
```

---

### Task 1-2. LLM Circuit Breaker 구현

**새 파일**: `apps/api/app/llm/circuit_breaker.py`

```python
import time
from dataclasses import dataclass, field

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5       # 연속 5회 실패 시 open
    recovery_timeout: float = 60.0   # 60초 후 half-open
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: str = field(default="closed", init=False)  # closed, open, half-open

    def is_open(self) -> bool:
        if self._state == "open":
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = "half-open"
                return False
            return True
        return False

    def record_success(self):
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    @property
    def state(self) -> str:
        # refresh state check
        self.is_open()
        return self._state
```

**client.py 통합**:
```python
from app.llm.circuit_breaker import CircuitBreaker

class LlmClient:
    def __init__(self, ...):
        ...
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    async def acreate_response(self, input, model=None, tools=None, **kwargs):
        if self._circuit_breaker.is_open():
            raise CircuitOpenError("llm")

        try:
            response = await self.async_client.responses.create(...)
            self._circuit_breaker.record_success()
            return response
        except Exception as e:
            self._circuit_breaker.record_failure()
            # 기존 fallback 로직 유지
            if self.enable_fallback and self.fallback_model:
                return await self._try_fallback(...)
            raise
```

---

### Task 1-3. Asset Registry silent failure 제거 (3건)

**대상**: `apps/api/app/modules/asset_registry/router.py`

`except Exception: pass` → 적절한 로깅 + 에러 전파:
```python
# Before
except Exception:
    pass

# After
except Exception as e:
    logger.warning(f"Non-critical operation failed: {e}")
    # 또는 re-raise if critical
```

---

## Phase 2: OPS runner.py 분해 (Week 2)

> 가장 큰 기술 부채. 6,326줄 → ~6개 파일로 분리.

### Task 2-1. runner.py Phase 분석 및 분해

**현재 구조 분석** (6,326줄 내부):
1. Plan 생성/검증 로직
2. Tool 선택/매핑 로직
3. Tool 실행 로직 (직렬)
4. 결과 집계/LLM 요약
5. 응답 포매팅
6. 캐싱/로깅

**목표 구조**:
```
orchestrator/
├── runner.py              # 메인 오케스트레이터 (~500줄)
│                          # - run() 진입점
│                          # - Phase 순서 관리
│                          # - 에러 복구 흐름
│
├── phases/
│   ├── __init__.py
│   ├── planning.py        # Phase 1: Plan 생성 (~800줄)
│   │                      # - LLM plan 호출
│   │                      # - Plan 검증/수정
│   │
│   ├── tool_resolution.py # Phase 2: Tool 선택 (~600줄)
│   │                      # - Tool registry 조회
│   │                      # - Tool capability 매칭
│   │
│   ├── execution.py       # Phase 3: Tool 실행 (~1,000줄)
│   │                      # - ParallelExecutor 통합
│   │                      # - 개별 Tool 실행
│   │                      # - 타임아웃/재시도
│   │
│   ├── aggregation.py     # Phase 4: 결과 집계 (~800줄)
│   │                      # - LLM 요약 호출
│   │                      # - 부분 성공 처리
│   │
│   └── response.py        # Phase 5: 응답 빌드 (~500줄)
│                          # - Block 포매팅
│                          # - 캐시 저장
│
├── runner_context.py      # 실행 컨텍스트 (기존 runner_base.py 리네임)
└── parallel_executor.py   # 병렬 실행 (기존 파일 통합)
```

**작업 순서**:
1. runner.py의 메서드/함수 목록 추출 및 분류
2. Phase별 파일 생성 (import만 정리, 로직 이동)
3. runner.py를 Phase 호출자로 리팩터링
4. 기존 테스트 통과 확인
5. Dead code (runner_base.py 미사용 부분) 정리

**핵심 원칙**:
- **동작 변경 없음**: 순수 구조 리팩터링
- **Phase 단위 커밋**: 각 Phase 분리마다 커밋
- **테스트 우선**: 기존 통합 테스트 먼저 확인

---

### Task 2-2. OPS router.py 분해 (3,119줄)

**현재**: 모든 OPS 엔드포인트가 하나의 `router.py`에 집중

**목표**: 기존 `routes/` 하위 파일들로 책임 이전하고, `router.py`는 라우터 결합만 담당

```python
# router.py (~50줄) - 라우터 결합만
from fastapi import APIRouter
from .routes import orchestration, threads, actions, regression, rca, ui_actions

router = APIRouter(prefix="/ops", tags=["ops"])
router.include_router(orchestration.router)
router.include_router(threads.router)
router.include_router(actions.router)
router.include_router(regression.router)
router.include_router(rca.router)
router.include_router(ui_actions.router)
```

---

## Phase 3: API Manager + CEP 분해 (Week 3)

### Task 3-1. API Manager router.py 분해 (1,522줄 → 6개 파일)

기존 감사 보고서의 권장안 그대로 실행:
```
api_manager/router/ → discovery.py, crud.py, versioning.py, execution.py, export.py, logs.py
```

### Task 3-2. CEP router.py 분해 (1,578줄 → 6개 파일)

```
cep_builder/router/ → rules.py, notifications.py, simulation.py, events.py, scheduler.py, performance.py
```

### Task 3-3. CEP executor.py 분해 (1,170줄 → 4개 파일)

```
cep_builder/executor/ → rule_executor.py, metric_executor.py, notification_executor.py, baseline_executor.py
```

---

## Phase 4: 품질 강화 (Week 4)

### Task 4-1. except Exception 단계적 개선

**전략**: 한 번에 350+건을 모두 바꾸지 않고, 파일별로 점진적 개선

**우선순위**:
1. `except Exception: pass` (silent failure) → **즉시 제거** (Asset Registry 3건, baseline_loader 5건)
2. `router.py` 파일들의 except Exception → 구체적 예외 분류
3. `runner.py` 분해 시 함께 개선

### Task 4-2. Frontend 테스트 기반 구축

**작업**:
1. Vitest 설정 추가 (`vitest.config.ts`)
2. 핵심 유틸리티 테스트 우선 작성:
   - `editor-state.ts` (1,530줄 - 상태 관리 핵심)
   - `orchestrationTraceUtils.ts` (유틸리티)
   - `adminUtils.ts` (유틸리티)
3. 주요 컴포넌트 스냅샷 테스트

---

## 실행 일정 요약

```
Day 1-2  [Phase 0] console.log 제거 + requirements 고정 + fail-closed
Day 3-5  [Phase 1] 예외 체계 + Circuit Breaker + silent failure 제거
Week 2   [Phase 2] OPS runner.py + router.py 분해
Week 3   [Phase 3] API Manager + CEP 분해
Week 4   [Phase 4] except Exception 개선 + Frontend 테스트
```

**Phase 0 완료 시**: 72 → 78/100
**Phase 1 완료 시**: 78 → 82/100
**Phase 2 완료 시**: 82 → 85/100
**Phase 3-4 완료 시**: 85 → 90/100

---

## 착수 순서 (바로 개발 시작)

Phase 0의 Task 0-1 (console.log 제거)부터 시작합니다.
가장 안전하고, 즉각적 효과가 있으며, 다른 작업에 영향 없습니다.
