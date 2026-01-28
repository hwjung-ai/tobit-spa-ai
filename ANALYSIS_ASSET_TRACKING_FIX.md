# Stage별 에셋 추적 문제 분석 및 해결책

## 1. 현재 상황 분석

### 1.1 문제 증상
- **Stage별 applied_assets**: 모두 0개 (비어있음)
- **Global applied_assets**: 정상 저장됨
- 원인: `begin_stage_asset_tracking()` 호출 후에도 실제 assets이 stage context에 저장되지 않음

### 1.2 코드 흐름 분석

#### 파일: `/home/spa/tobit-spa-ai/apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**현재 구현 (문제 있음):**
```
Line 5009-5023: route_plan stage
├─ begin_stage_asset_tracking() 호출  [라인 5009]
├─ route_input = _build_stage_input("route_plan", ...)  [라인 5011]
│  └─ _build_stage_input에서 get_stage_assets() 호출 [라인 5323]
│     └─ 하지만 이 시점에서 stage context는 EMPTY (아직 실행되지 않음)
└─ route_output 생성 및 record_stage 호출  [라인 5023]

Line 5218-5227: compose stage
├─ begin_stage_asset_tracking() 호출  [라인 5218]
├─ await self._stage_executor.execute_stage(compose_input)  [라인 5226]
│  └─ 이 함수 내에서 assets을 사용하지만,
│     이미 _build_stage_input에서 호출되었으므로 너무 늦음
└─ record_stage 호출  [라인 5227]
```

**핵심 문제:**
1. `begin_stage_asset_tracking()` 호출 시점: Stage 시작 전
2. `_build_stage_input()` 호출 시점: Stage 시작 직후 (하지만 아직 실행 전)
3. Stage 실행: `_stage_executor.execute_stage()` 호출 (라인 5226, 5239 등)
4. `_resolve_applied_assets()` 호출 시점: `_build_stage_input()` 내부 (라인 5323)

**결과:** `_resolve_applied_assets()` 호출 시점에 stage context가 아직 비어있음!

### 1.3 Asset Context 구조 분석

#### 파일: `/home/spa/tobit-spa-ai/apps/api/app/modules/inspector/asset_context.py`

```python
# 두 가지 Context 존재:
_ASSET_CONTEXT  # 전역 에셋 추적
_STAGE_ASSET_CONTEXT  # Stage별 에셋 추적

# 관계:
- begin_stage_asset_tracking()  [라인 110]
  └─ _STAGE_ASSET_CONTEXT을 초기화

- get_stage_assets()  [라인 145]
  └─ _STAGE_ASSET_CONTEXT에서 현재 값 반환 (비어있을 수 있음)

- track_*_asset_to_stage()  [라인 164-253]
  └─ 실제 stage context에 에셋 저장
  └─ 동시에 전역 context에도 저장

- end_stage_asset_tracking()  [라인 119]
  └─ Stage context 반환 및 리셋
  └─ 하지만 runner.py에서 호출되지 않음!
```

## 2. 근본 원인

### 2.1 Architecture 문제

```
Current Flow (BROKEN):
begin_stage_asset_tracking()  [Stage 시작]
    ↓
_build_stage_input()  [Stage input 구성 - 아직 비어있음]
    ├─ _resolve_applied_assets()  [get_stage_assets() 호출]
    │  └─ 이 시점: stage context = EMPTY {}
    └─ StageInput 생성 (applied_assets 비어있음)
    ↓
await _stage_executor.execute_stage(stage_input)  [Stage 실행]
    ├─ 이 함수 내에서 track_*_asset_to_stage() 호출
    │  └─ stage context에 에셋 저장
    └─ Stage 완료

record_stage()  [Stage 기록 - 하지만 이미 stage input은 생성됨]
```

**문제:** Stage 실행 전에 이미 stage input이 생성되었으므로, stage 실행 중에 저장된 에셋을 반영할 수 없음!

### 2.2 해결책

#### 옵션 1: 올바른 순서로 _build_stage_input 호출 (권장)

```
begin_stage_asset_tracking()  [Stage 시작]
    ↓
await _stage_executor.execute_stage(stage_input_partial)  [Stage 실행]
    ├─ 이 함수 내에서 track_*_asset_to_stage() 호출
    │  └─ stage context에 에셋 저장
    └─ 반환값 포함
    ↓
_build_stage_input()  [Stage 끝난 후에 input 구성]
    ├─ 이 시점: stage context에 실제 에셋이 저장됨
    ├─ _resolve_applied_assets()  [get_stage_assets() 호출]
    │  └─ 정상적으로 stage 에셋 포함
    └─ StageInput 생성 (applied_assets 포함됨)
    ↓
record_stage()  [정상적인 에셋과 함께 기록]
```

**장점:**
- 실제 stage 실행 후에 stage input 생성
- Stage 내에서 사용된 모든 에셋이 정확히 반영됨
- 논리적으로 일관성 있음

**단점:**
- Stage input이 나중에 생성되므로, 이전 stage의 output을 참조하는 로직 수정 필요
- 약간의 코드 재구성 필요

#### 옵션 2: 차이 계산 방식 (대안)

```
before_assets = get_tracked_assets()  [Stage 시작 전 전역 에셋]

await _stage_executor.execute_stage(...)  [Stage 실행]

after_assets = get_tracked_assets()  [Stage 종료 후 전역 에셋]

stage_assets = 계산(after_assets - before_assets)  [차이만 추출]
```

**장점:**
- 기존 코드 구조 최소 변경

**단점:**
- 복잡한 diff 계산 필요
- 여러 에셋이 추가될 경우 오류 가능성

#### 옵션 3: Stage 완료 후 에셋 수집 (현실적)

```
begin_stage_asset_tracking()  [Stage 시작]
    ↓
# 현재: _build_stage_input() 호출
# 수정: 생략하고 진행

await _stage_executor.execute_stage(stage_output)  [Stage 실행]
    └─ Stage context에 에셋 저장됨
    ↓
stage_assets = end_stage_asset_tracking()  [Stage 에셋 수집]
    ↓
_build_stage_input(applied_assets=stage_assets)  [Stage input 구성]
    └─ Stage 에셋 직접 전달
    ↓
record_stage()  [기록]
```

**장점:**
- 명확한 의도
- Stage 에셋이 정확히 캡처됨
- `end_stage_asset_tracking()` 함수 사용 (이미 구현됨)

**단점:**
- `_build_stage_input` 메소드 시그니처 수정 필요

## 3. 권장 해결책 (옵션 3)

### 3.1 수정할 함수들

#### A. `_build_stage_input()` 메소드 수정
**파일:** `/home/spa/tobit-spa-ai/apps/api/app/modules/ops/services/ci/orchestrator/runner.py` 라인 5312

**현재:**
```python
def _build_stage_input(
    self,
    stage: str,
    plan_output: PlanOutput,
    prev_output: Optional[Dict[str, Any]] = None,
) -> StageInput:
    """Build StageInput from plan output and previous output."""
    context = get_request_context()
    trace_id = context.get("trace_id") or context.get("request_id")
    return StageInput(
        stage=stage,
        applied_assets=self._resolve_applied_assets(),  # ← 이 부분이 문제
        params={"plan_output": plan_output.model_dump()},
        prev_output=prev_output,
        trace_id=trace_id,
    )
```

**수정:**
```python
def _build_stage_input(
    self,
    stage: str,
    plan_output: PlanOutput,
    prev_output: Optional[Dict[str, Any]] = None,
    stage_assets: Optional[Dict[str, Any]] = None,  # ← 새 파라미터
) -> StageInput:
    """Build StageInput from plan output and previous output."""
    context = get_request_context()
    trace_id = context.get("trace_id") or context.get("request_id")

    # stage_assets가 제공되면 사용, 아니면 현재 stage context 사용
    if stage_assets is not None:
        applied_assets = self._resolve_applied_assets_from_assets(stage_assets)
    else:
        applied_assets = self._resolve_applied_assets()

    return StageInput(
        stage=stage,
        applied_assets=applied_assets,
        params={"plan_output": plan_output.model_dump()},
        prev_output=prev_output,
        trace_id=trace_id,
    )
```

#### B. `_resolve_applied_assets_from_assets()` 헬퍼 메소드 추가

```python
def _resolve_applied_assets_from_assets(self, assets: Dict[str, Any]) -> Dict[str, str]:
    """Resolve applied assets from pre-computed assets dictionary.

    This is similar to _resolve_applied_assets() but takes assets as input
    instead of reading from stage context.
    """
    applied: Dict[str, str] = {}

    def format_asset_display(info: Dict[str, Any]) -> str:
        """Format asset info for user-friendly display."""
        name = info.get("name") or info.get("screen_id") or "unknown"
        version = info.get("version")
        source = info.get("source", "asset_registry")

        if source != "asset_registry":
            return f"{name} (fallback)"

        if version is not None:
            return f"{name} (v{version})"
        return name

    for key in ("prompt", "policy", "mapping", "source", "schema", "resolver"):
        info = assets.get(key)
        if not info:
            continue
        applied[key] = format_asset_display(info)
        override_key = f"{key}:{info.get('name')}"
        override = self.asset_overrides.get(override_key)
        if override:
            applied[key] = str(override)

    for entry in assets.get("queries", []) or []:
        if not entry:
            continue
        name = entry.get("name") or entry.get("asset_id") or "query"
        version = entry.get("version")
        if version is not None:
            display_name = f"{name} (v{version})"
        else:
            display_name = name
        applied[f"query:{name}"] = display_name
        override_key = f"query:{name}"
        override = self.asset_overrides.get(override_key)
        if override:
            applied[f"query:{name}"] = str(override)

    for entry in assets.get("screens", []) or []:
        if not entry:
            continue
        screen_id = entry.get("screen_id") or entry.get("asset_id") or "screen"
        name = entry.get("screen_id") or entry.get("name") or screen_id
        version = entry.get("version")
        if version is not None:
            display_name = f"{name} (v{version})"
        else:
            display_name = name
        applied[f"screen:{screen_id}"] = display_name
        override_key = f"screen:{screen_id}"
        override = self.asset_overrides.get(override_key)
        if override:
            applied[f"screen:{screen_id}"] = str(override)

    return applied
```

#### C. Stage 실행 로직 수정

**예시 (route_plan stage):**

현재:
```python
# route_plan stage
begin_stage_asset_tracking()
route_start = perf_counter()
route_input = self._build_stage_input("route_plan", plan_output)
route_result = {...}
route_output = StageOutput(...)
record_stage("route_plan", route_input, route_output)
```

수정:
```python
# route_plan stage
begin_stage_asset_tracking()
route_start = perf_counter()

# Route stage는 자체 실행 없음, plan_output에서 직접 결과
route_assets = end_stage_asset_tracking()  # 빈 dict 반환 (this stage uses no assets)

route_input = self._build_stage_input(
    "route_plan",
    plan_output,
    stage_assets=route_assets
)
route_result = {...}
route_output = StageOutput(...)
record_stage("route_plan", route_input, route_output)
```

**예시 (execute stage - PLAN path):**

현재:
```python
# execute stage (PLAN path)
begin_stage_asset_tracking()
execute_start = perf_counter()
execute_input = self._build_stage_input(
    "execute", plan_output, validate_output.model_dump()
)
base_result = await self._run_async()  # ← 이 함수에서 에셋 사용됨
blocks = base_result.get("blocks", [])
answer = base_result.get("answer", answer)
execute_output = StageOutput(...)
execute_input = self._build_stage_input(...)  # ← 다시 호출? (이미 위에서 호출됨)
record_stage("execute", execute_input, execute_output)
```

수정:
```python
# execute stage (PLAN path)
begin_stage_asset_tracking()
execute_start = perf_counter()

base_result = await self._run_async()  # ← 이 함수에서 에셋이 stage context에 저장됨
blocks = base_result.get("blocks", [])
answer = base_result.get("answer", answer)

execute_assets = end_stage_asset_tracking()  # ← Execute stage에서 사용한 에셋 수집

execute_input = self._build_stage_input(
    "execute",
    plan_output,
    validate_output.model_dump(),
    stage_assets=execute_assets  # ← 수집한 에셋 전달
)
execute_output = StageOutput(...)
record_stage("execute", execute_input, execute_output)
```

**예시 (compose stage - StageExecutor 사용):**

현재:
```python
# compose stage (PLAN path)
begin_stage_asset_tracking()
compose_start = perf_counter()
compose_input = self._build_stage_input(
    "compose", plan_output, execute_output.model_dump()
)
compose_input.params["question"] = self.question
compose_output = await self._stage_executor.execute_stage(compose_input)  # ← 실행
record_stage("compose", compose_input, compose_output)
```

수정:
```python
# compose stage (PLAN path)
begin_stage_asset_tracking()
compose_start = perf_counter()

compose_output = await self._stage_executor.execute_stage(
    # 임시 input 전달 (assets는 stage executor에서 채워질 것)
    StageInput(
        stage="compose",
        applied_assets={},  # ← 임시 (아직 실행 전)
        params={
            "plan_output": plan_output.model_dump(),
            "question": self.question
        },
        prev_output=execute_output.model_dump(),
        trace_id=get_request_context().get("trace_id") or get_request_context().get("request_id"),
    )
)

compose_assets = end_stage_asset_tracking()  # ← Compose stage에서 사용한 에셋 수집

compose_input = self._build_stage_input(
    "compose",
    plan_output,
    execute_output.model_dump(),
    stage_assets=compose_assets  # ← 실제 에셋 반영
)
record_stage("compose", compose_input, compose_output)
```

## 4. 구현 체크리스트

### 4.1 Phase 1: 기초 구현
- [ ] `_resolve_applied_assets_from_assets()` 메소드 추가
- [ ] `_build_stage_input()` 시그니처 수정 (stage_assets 파라미터 추가)
- [ ] `end_stage_asset_tracking()` import 확인

### 4.2 Phase 2: Stage 실행 로직 수정
- [ ] route_plan stage 수정
- [ ] DIRECT path stages (validate, execute, compose, present) 수정
- [ ] REJECT path stages (validate, execute, compose, present) 수정
- [ ] PLAN path stages (validate, execute, compose, present) 수정

### 4.3 Phase 3: 검증
- [ ] 각 stage의 applied_assets 수집 확인
- [ ] Trace 저장 시 stage_inputs에 assets 포함 확인
- [ ] 테스트 쿼리 20개 실행 및 결과 검증

## 5. 예상 결과

### 현재 상태:
```json
{
  "stage_inputs": [
    {
      "stage": "route_plan",
      "applied_assets": {},  // ← EMPTY
      "params": {...}
    },
    {
      "stage": "validate",
      "applied_assets": {},  // ← EMPTY
      "params": {...}
    },
    {
      "stage": "execute",
      "applied_assets": {},  // ← EMPTY
      "params": {...}
    },
    ...
  ]
}
```

### 수정 후 예상:
```json
{
  "stage_inputs": [
    {
      "stage": "route_plan",
      "applied_assets": {},  // ← OK (이 stage는 assets 사용 안 함)
      "params": {...}
    },
    {
      "stage": "validate",
      "applied_assets": {"policy": "policy_v1 (v1)"}, // ← OK
      "params": {...}
    },
    {
      "stage": "execute",
      "applied_assets": {
        "queries": ["query1 (v2)", "query2 (v1)"],
        "schema": "db_schema (v3)"
      }, // ← OK
      "params": {...}
    },
    {
      "stage": "compose",
      "applied_assets": {"prompt": "compose_prompt (v2)"}, // ← OK
      "params": {...}
    },
    {
      "stage": "present",
      "applied_assets": {"prompt": "present_prompt (v1)"}, // ← OK
      "params": {...}
    }
  ]
}
```

## 6. 추가 고려사항

### 6.1 `_run_async()` 함수
- 이 함수에서 실제 query 실행과 에셋 추적이 일어남
- `begin_stage_asset_tracking()` 호출 후 `_run_async()`가 실행되어야 함
- 현재 코드에서 이미 그렇게 되어 있음 (문제 없음)

### 6.2 `_stage_executor.execute_stage()` 함수
- 이 함수도 내부에서 track_*_asset_to_stage() 호출
- 현재 구조: 불명확한 시점에 호출됨
- 수정 후: Stage 전체 실행 후에 호출됨

### 6.3 Logger 추가
```python
self.logger.info(
    "ci.stage.assets_captured",
    extra={
        "stage": stage_name,
        "asset_count": len(stage_assets.get("queries", [])),
        "applied_assets": list(applied_assets.keys())
    }
)
```

## 7. 테스트 전략

### 7.1 단위 테스트
- `_resolve_applied_assets_from_assets()` 메소드 단위 테스트
- 각 asset type별로 정상 포맷팅 확인

### 7.2 통합 테스트
- 20개 테스트 쿼리 실행
- Trace의 stage_inputs 검증
- 각 stage별 applied_assets 확인

### 7.3 검증 기준
- Stage별 applied_assets 개수 > 0 (stage가 assets 사용할 경우)
- applied_assets의 key 포맷 정확성
- applied_assets의 value 포맷 정확성 (e.g., "name (vX)")

---

**상태:** 분석 완료 → 구현 대기
**우선순위:** Phase 1 (기초) → Phase 2 (stage 수정) → Phase 3 (검증)
