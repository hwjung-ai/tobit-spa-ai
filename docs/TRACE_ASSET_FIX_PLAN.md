# Trace Inspector Asset Assignment 개선 계획

## Executive Summary

**현상**: trace_id `7a3e39d9-1b32-4e93-be11-cc3ad4a820e1` 조회 시, 모든 stage에서 동일한 5개 asset (policy, prompt, source, mapping, resolver)이 표시됨

**원인**:
1. Asset tracking이 global scope (stage별 reset 없음)
2. Catalog & Tool asset type이 미지원됨

**해결 방안**:
1. Stage-aware asset context 구현
2. Catalog & Tool asset tracking 추가

---

## Part 1: 상세 문제 분석

### Issue #1: Per-Stage Asset Assignment 부재

#### 현재 데이터 구조
```
Database tb_execution_trace 테이블:

trace_id: 7a3e39d9-1b32-4e93-be11-cc3ad4a820e1

├─ applied_assets (TRACE LEVEL - 전체 execution의 누적):
│  ├─ prompt: ci_planner_output_parser
│  ├─ policy: view_depth_policies
│  ├─ mapping: output_type_priorities
│  ├─ source: primary_postgres
│  └─ resolver: default_resolver

└─ stage_inputs (각 stage별 입력 데이터):
   ├─ route_plan:
   │  └─ applied_assets: [동일한 5개]
   ├─ validate:
   │  └─ applied_assets: [동일한 5개]
   ├─ execute:
   │  └─ applied_assets: [동일한 5개]
   ├─ compose:
   │  └─ applied_assets: [동일한 5개]
   └─ present:
      └─ applied_assets: [동일한 5개]
```

#### 문제: 왜 모든 stage에서 같은가?

**코드 플로우:**

1. **Asset Tracking (어디서든)**
```python
# asset_registry/loader.py의 load_prompt_asset() 예시
def load_prompt_asset(...):
    prompt_data = {...}
    track_prompt_asset({
        "asset_id": "...",
        "name": "ci_planner_output_parser",
        ...
    })  # → Global _ASSET_CONTEXT에 저장
```

2. **Stage 실행 중**
```python
# route_plan stage에서
load_prompt_asset(...)  # _ASSET_CONTEXT["prompt"] = {...}
load_policy_asset(...)  # _ASSET_CONTEXT["policy"] = {...}
# ...

# validate stage에서
# _ASSET_CONTEXT는 여전히 route_plan에서 set된 값들을 가지고 있음
# 새로운 asset 로드 시 이전 값을 overwrite하지만,
# 로드되지 않은 asset은 그대로 남아있음
```

3. **Stage 종료 시 applied_assets 저장**
```python
# runner.py의 _resolve_applied_assets()
def _resolve_applied_assets(self) -> Dict[str, str]:
    assets = get_tracked_assets()  # 현재까지 누적된 모든 asset 반환
    applied: Dict[str, str] = {}

    for key in ("prompt", "policy", "mapping", "source", "schema", "resolver"):
        info = assets.get(key)  # ← 이전 stage에서 load된 것도 포함됨
        if not info:
            continue
        applied[key] = format_asset_display(info)

    # stage_inputs에 저장
    stage_input["applied_assets"] = applied
```

**핵심 문제:**
- `get_tracked_assets()`는 "지금까지 누적된 모든 asset"을 반환
- Stage별로 reset이 없어서, 이전 stage의 asset이 다음 stage에도 표시됨
- 각 stage에서 실제로 **LOAD한** asset만 저장하지 않음

#### Expected vs Actual

**Expected Behavior:**
```
route_plan stage:
  - prompt 로드: ci_planner_output_parser ✅
  - policy 로드: view_depth_policies ✅
  → applied_assets: {prompt, policy}

validate stage:
  - prompt 로드: [재사용, 새로 로드하지 않음]
  - policy 로드: [재사용, 새로 로드하지 않음]
  → applied_assets: {} (새로 로드한 것 없음)

execute stage:
  - source 로드: primary_postgres ✅
  → applied_assets: {source}
```

**Actual Behavior:**
```
route_plan stage:
  - prompt, policy, mapping, source, resolver 모두 표시

validate stage:
  - prompt, policy, mapping, source, resolver 모두 표시 (동일)

execute stage:
  - prompt, policy, mapping, source, resolver 모두 표시 (동일)
```

---

### Issue #2: Catalog & Tool Asset Not Supported

#### 현황 (DB 조회 결과)

| Asset Type | 레코드 수 | asset_context 추적? | _build_applied_assets? | ORM 저장? |
|-----------|---------|-------------------|----------------------|---------|
| prompt    | 20      | ✅ Yes            | ✅ Yes               | ✅ Yes  |
| policy    | 11      | ✅ Yes            | ✅ Yes               | ✅ Yes  |
| mapping   | 17      | ✅ Yes            | ✅ Yes               | ✅ Yes  |
| source    | 2       | ✅ Yes            | ✅ Yes               | ✅ Yes  |
| schema    | 3       | ✅ Yes            | ✅ Yes               | ✅ Yes  |
| resolver  | 4       | ✅ Yes            | ✅ Yes               | ✅ Yes  |
| query     | 131     | ✅ Yes            | ✅ Yes (list)        | ✅ Yes  |
| screen    | 12      | ✅ Yes            | ✅ Yes (list)        | ✅ Yes  |
| **catalog** | **0**  | ❌ No             | ❌ No                | ❌ No   |
| **tool**   | **12** | ❌ No             | ❌ No                | ❌ No   |

#### Catalog이 없는 이유
- 아예 생성되지 않음 (0 records)
- Feature not implemented
- 향후 추가 예정

#### Tool이 안 되는 이유

**1. asset_context.py에서 추적 안 함:**
```python
# 현재 _initial_context()
def _initial_context() -> Dict[str, Any]:
    return {
        "prompt": None,
        "policy": None,
        "mapping": None,
        "source": None,
        "schema": None,
        "resolver": None,
        "queries": [],      # ✅
        "screens": [],      # ✅
        # ❌ Missing: "catalog": None,
        # ❌ Missing: "tool": None,
    }

# 존재하지 않는 함수들:
# track_catalog_asset(info)  ← 필요
# track_tool_asset(info)     ← 필요
```

**2. service.py에서 저장 안 함:**
```python
# _build_applied_assets()에서
def _build_applied_assets(state: dict[str, Any]) -> Dict[str, Any]:
    return {
        "prompt": _summarize_asset(state.get("prompt")),
        "policy": _summarize_asset(state.get("policy")),
        # ... 기타
        "queries": [_summarize_asset(entry) for entry in state.get("queries", [])],
        "screens": [entry for entry in state.get("screens", [])],
        # ❌ Missing: "catalog": _summarize_asset(state.get("catalog")),
        # ❌ Missing: "tool": _summarize_asset(state.get("tool")),
    }
```

**3. models.py에서 ORM 필드 비활성화:**
```python
# Line 79-90
# Tool asset fields are commented out until migrations 0030-0041 are applied to database

# ❌ Commented out:
# tool_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
# tool_catalog_ref: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
# tool_config: dict[str, Any] | None = Field(...)
# tool_input_schema: dict[str, Any] | None = Field(...)
# tool_output_schema: dict[str, Any] | None = Field(...)

# Reason: Pending database migration v0030-0041
```

**4. loader.py에서 추적 안 함:**
```python
# load_tool_asset()는 있지만, track_tool_asset()를 호출하지 않음
def load_tool_asset(...):
    tool_data = {...}
    # ❌ Missing: track_tool_asset(tool_data)
    return tool_data
```

---

## Part 2: 개선 방안

### Solution #1: Stage-Aware Asset Context (높은 우선순위)

#### 목표
- 각 stage에서 **실제로 로드한** asset만 stage_inputs에 저장
- 이전 stage의 asset이 다음 stage에 영향을 주지 않도록

#### 설계

**방안 A: Stage Context Reset (권장)**

```python
# asset_context.py에 추가

class StageAssetSnapshot:
    """한 stage 내에서 로드된 asset들의 스냅샷"""
    def __init__(self):
        self.prompt = None
        self.policy = None
        self.mapping = None
        self.source = None
        self.schema = None
        self.resolver = None
        self.queries: List[Dict] = []
        self.screens: List[Dict] = []

_STAGE_ASSET_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar(
    "stage_asset_context", default=None
)

def begin_stage_asset_tracking():
    """Stage 시작 시 호출 - 새로운 context 생성"""
    _STAGE_ASSET_CONTEXT.set(_initial_context())

def end_stage_asset_tracking() -> Dict[str, Any]:
    """Stage 종료 시 호출 - 현재 context 반환 후 초기화"""
    snapshot = _STAGE_ASSET_CONTEXT.get()
    _STAGE_ASSET_CONTEXT.set(None)
    return snapshot or {}

def track_prompt_asset_in_stage(info):
    """현재 stage context에만 기록"""
    ctx = _STAGE_ASSET_CONTEXT.get()
    if ctx:
        ctx["prompt"] = info
```

**Flow:**
```
Stage 시작 (route_plan):
  begin_stage_asset_tracking()        # New context created

  load_prompt_asset(...)
    → track_prompt_asset_in_stage()   # Only in stage context

  load_policy_asset(...)
    → track_policy_asset_in_stage()   # Only in stage context

Stage 종료:
  stage_applied = end_stage_asset_tracking()  # Get {prompt, policy}
  stage_inputs.applied_assets = stage_applied

Stage 시작 (validate):
  begin_stage_asset_tracking()        # Fresh context (no prompt, no policy)

  [validate에서 새 asset을 load하지 않으면]

Stage 종료:
  stage_applied = end_stage_asset_tracking()  # Get {} (empty!)
  stage_inputs.applied_assets = {}
```

#### 변경 파일

**1. `asset_context.py` (core change)**
```python
# 라인 1-30: 새로운 context var 추가
_STAGE_ASSET_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar(
    "stage_asset_context", default=None
)

# 라인 60-80: 새로운 함수들 추가
def begin_stage_asset_tracking() -> None:
    """Stage 시작 시 호출"""
    _STAGE_ASSET_CONTEXT.set(_initial_context())

def end_stage_asset_tracking() -> Dict[str, Any]:
    """Stage 종료 시 호출 - snapshot 반환"""
    snapshot = _STAGE_ASSET_CONTEXT.get()
    _STAGE_ASSET_CONTEXT.set(None)
    return snapshot or {}

def get_stage_assets() -> Dict[str, Any]:
    """현재 stage의 asset만 반환"""
    ctx = _STAGE_ASSET_CONTEXT.get()
    return ctx or {}

# 라인 85-100: 기존 track 함수들을 dual-track으로 변경
def track_prompt_asset(info: Dict[str, Any]) -> None:
    """Prompt asset tracking"""
    # Global context에도 저장 (backward compat)
    global_ctx = _ASSET_CONTEXT.get()
    if global_ctx:
        global_ctx["prompt"] = info

    # Stage context에도 저장 (새로운 방식)
    stage_ctx = _STAGE_ASSET_CONTEXT.get()
    if stage_ctx:
        stage_ctx["prompt"] = info
```

**2. `runner.py` (integration)**

```python
# Line ~420: _resolve_applied_assets() 메서드 수정

def _resolve_applied_assets(self) -> Dict[str, str]:
    """Stage 종료 시 호출"""
    # 이전: assets = get_tracked_assets()  # ← 전체 누적
    # 새로운: 현재 stage의 asset만 가져옴

    from app.modules.inspector.asset_context import get_stage_assets

    assets = get_stage_assets()  # ← Stage-specific만 반환
    applied: Dict[str, str] = {}

    for key in ("prompt", "policy", "mapping", "source", "schema", "resolver"):
        info = assets.get(key)
        if not info:
            continue
        applied[key] = format_asset_display(info)

    # queries, screens 처리
    for entry in assets.get("queries", []):
        if entry:
            applied.setdefault("queries", []).append(format_asset_display(entry))

    return applied
```

```python
# Stage 실행 전후 추가

async def execute_stage(self, stage_name: str):
    """Stage 실행"""
    # Stage 시작
    from app.modules.inspector.asset_context import begin_stage_asset_tracking
    begin_stage_asset_tracking()

    try:
        # 기존 stage 실행 로직
        result = await self._execute_stage_impl(stage_name)

        # Stage 종료
        from app.modules.inspector.asset_context import end_stage_asset_tracking
        applied_assets = end_stage_asset_tracking()

        # stage_inputs에 저장
        stage_input = StageInput(
            stage=stage_name,
            applied_assets=applied_assets,
            ...
        )

        return result
    except Exception as e:
        # 에러 발생해도 context cleanup
        from app.modules.inspector.asset_context import end_stage_asset_tracking
        end_stage_asset_tracking()
        raise
```

**3. `service.py` (no change needed)**
- `_build_applied_assets()`는 현재 그대로 유지 가능
- Input이 stage-specific이면 자동으로 맞음

---

### Solution #2: Add Catalog & Tool Asset Support (중간 우선순위)

#### Catalog 지원

**1. `asset_context.py`**
```python
# Line 16-25: _initial_context() 수정
def _initial_context() -> Dict[str, Any]:
    return {
        "prompt": None,
        "policy": None,
        "mapping": None,
        "source": None,
        "schema": None,
        "resolver": None,
        "catalog": None,  # ← 추가
        "queries": [],
        "screens": [],
    }

# Line 150-160: 추적 함수 추가
def track_catalog_asset(info: Dict[str, Any]) -> None:
    """Track catalog asset"""
    global_ctx = _ASSET_CONTEXT.get()
    if global_ctx:
        global_ctx["catalog"] = info

    stage_ctx = _STAGE_ASSET_CONTEXT.get()
    if stage_ctx:
        stage_ctx["catalog"] = info

# Line 160-170: 조회 함수 추가
def get_catalog_asset() -> Dict[str, Any] | None:
    """Get currently tracked catalog asset"""
    ctx = _ASSET_CONTEXT.get()
    return ctx.get("catalog") if ctx else None
```

**2. `service.py`**
```python
# Line 29-41: _build_applied_assets() 수정
def _build_applied_assets(state: dict[str, Any]) -> Dict[str, Any]:
    return {
        "prompt": _summarize_asset(state.get("prompt")),
        "policy": _summarize_asset(state.get("policy")),
        "mapping": _summarize_asset(state.get("mapping")),
        "source": _summarize_asset(state.get("source")),
        "schema": _summarize_asset(state.get("schema")),
        "resolver": _summarize_asset(state.get("resolver")),
        "catalog": _summarize_asset(state.get("catalog")),  # ← 추가
        "queries": [_summarize_asset(entry) for entry in state.get("queries", []) if entry],
        "screens": [entry for entry in state.get("screens", []) if entry],
    }
```

**3. `loader.py`**
```python
# load_catalog_asset() 함수에서 tracking 호출 추가

def load_catalog_asset(asset_id: str, session: Session) -> Dict[str, Any]:
    """Load and track catalog asset"""
    asset = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_id == asset_id)
        .where(TbAssetRegistry.asset_type == "catalog")
    ).first()

    if not asset:
        return {}

    catalog_data = {
        "asset_id": str(asset.asset_id),
        "name": asset.name,
        "version": asset.version,
        "source": asset.source,
    }

    # ← 추가: tracking
    track_catalog_asset(catalog_data)

    return catalog_data
```

#### Tool 지원

**1. `models.py` - Tool 필드 활성화**
```python
# Line 79-90: Uncomment tool fields

class TbAssetRegistry(Base):
    # ... 기타 필드들 ...

    # Tool asset fields (재활성화)
    tool_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tool_catalog_ref: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tool_config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    tool_input_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    tool_output_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
```

**2. `asset_context.py`**
```python
# Line 16-25: _initial_context() 수정
def _initial_context() -> Dict[str, Any]:
    return {
        "prompt": None,
        "policy": None,
        "mapping": None,
        "source": None,
        "schema": None,
        "resolver": None,
        "catalog": None,
        "tool": None,  # ← 추가
        "queries": [],
        "screens": [],
    }

# Line 180-190: 추적 함수 추가
def track_tool_asset(info: Dict[str, Any]) -> None:
    """Track tool asset"""
    global_ctx = _ASSET_CONTEXT.get()
    if global_ctx:
        global_ctx["tool"] = info

    stage_ctx = _STAGE_ASSET_CONTEXT.get()
    if stage_ctx:
        stage_ctx["tool"] = info

def get_tool_asset() -> Dict[str, Any] | None:
    """Get currently tracked tool asset"""
    ctx = _ASSET_CONTEXT.get()
    return ctx.get("tool") if ctx else None
```

**3. `service.py`**
```python
# Line 29-41: _build_applied_assets() 수정
def _build_applied_assets(state: dict[str, Any]) -> Dict[str, Any]:
    return {
        "prompt": _summarize_asset(state.get("prompt")),
        "policy": _summarize_asset(state.get("policy")),
        "mapping": _summarize_asset(state.get("mapping")),
        "source": _summarize_asset(state.get("source")),
        "schema": _summarize_asset(state.get("schema")),
        "resolver": _summarize_asset(state.get("resolver")),
        "catalog": _summarize_asset(state.get("catalog")),
        "tool": _summarize_asset(state.get("tool")),  # ← 추가
        "queries": [_summarize_asset(entry) for entry in state.get("queries", []) if entry],
        "screens": [entry for entry in state.get("screens", []) if entry],
    }
```

**4. `loader.py`**
```python
# load_tool_asset() 함수에서 tracking 호출 추가

def load_tool_asset(asset_id: str, session: Session) -> Dict[str, Any]:
    """Load and track tool asset"""
    asset = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_id == asset_id)
        .where(TbAssetRegistry.asset_type == "tool")
    ).first()

    if not asset:
        return {}

    tool_data = {
        "asset_id": str(asset.asset_id),
        "name": asset.name,
        "version": asset.version,
        "source": asset.source,
        "tool_type": asset.tool_type,
        "tool_catalog_ref": asset.tool_catalog_ref,
    }

    # ← 추가: tracking
    track_tool_asset(tool_data)

    return tool_data
```

---

## Part 3: 구현 계획 (단계별)

### Phase 1: Stage-Aware Context (필수) - 우선순위 높음

**목표**: 각 stage에서 실제로 로드한 asset만 표시

**Step 1.1: asset_context.py 수정**
- [ ] `_STAGE_ASSET_CONTEXT` ContextVar 추가
- [ ] `begin_stage_asset_tracking()` 함수 추가
- [ ] `end_stage_asset_tracking()` 함수 추가
- [ ] `get_stage_assets()` 함수 추가
- [ ] 기존 `track_*_asset()` 함수들을 dual-track으로 변경
- [ ] 테스트: unit test 추가

**Step 1.2: runner.py 수정**
- [ ] stage 실행 전에 `begin_stage_asset_tracking()` 호출
- [ ] stage 실행 후에 `end_stage_asset_tracking()` 호출
- [ ] `_resolve_applied_assets()`에서 `get_stage_assets()` 사용
- [ ] 테스트: integration test로 각 stage별 asset 확인

**Step 1.3: 통합 테스트**
- [ ] trace_id `7a3e39d9-1b32-4e93-be11-cc3ad4a820e1` 다시 조회
- [ ] 각 stage에서 다른 asset이 표시되는지 확인
- [ ] Inspector UI에서 stage별로 다른 asset이 보이는지 확인

### Phase 2: Catalog & Tool Support (선택) - 우선순위 중간

**목표**: Catalog와 Tool asset도 추적되도록

**Step 2.1: Catalog 지원**
- [ ] asset_context.py에 catalog 추가
- [ ] service.py에 catalog 처리 추가
- [ ] loader.py에서 track_catalog_asset() 호출 추가
- [ ] 테스트: catalog asset이 로드될 때 추적되는지 확인

**Step 2.2: Tool 지원**
- [ ] models.py의 tool 필드 uncomment (migration 필요)
  - Note: DB migration이 필요함 (pending v0030-0041)
  - 임시로: migration 없이 필드만 활성화할지 확인 필요
- [ ] asset_context.py에 tool 추가
- [ ] service.py에 tool 처리 추가
- [ ] loader.py에서 track_tool_asset() 호출 추가
- [ ] 테스트: tool asset이 로드될 때 추적되는지 확인

**Step 2.3: 통합 테스트**
- [ ] Catalog 로드 후 applied_assets에 표시되는지 확인
- [ ] Tool 로드 후 applied_assets에 표시되는지 확인

### Phase 3: Frontend 업데이트 (선택) - 우선순위 낮음

**목표**: Inspector UI에서 catalog와 tool asset 아이콘 추가

**Step 3.1: inspector/page.tsx 업데이트**
- [ ] catalog asset 아이콘 추가 (예: 📚)
- [ ] tool asset 아이콘 추가 (예: 🛠️)
- [ ] 라인 1201-1211 수정

**Step 3.2: 테스트**
- [ ] UI에서 catalog와 tool asset이 표시되는지 확인

---

## Part 4: 구현 세부사항

### File-by-File Changes

#### 1. `apps/api/app/modules/inspector/asset_context.py`

**변경 사항:**
- Line 1-15: import 확인
- Line 16-25: `_STAGE_ASSET_CONTEXT` 추가
- Line 26-35: 새로운 함수들 추가
- Line 60-100: 기존 track 함수들 수정
- Line 110-150: catalog, tool 함수 추가

**코드 예시:**

```python
# Line 16-25: 추가
_STAGE_ASSET_CONTEXT: ContextVar[Dict[str, Any] | None] = ContextVar(
    "inspector_stage_asset_context", default=None
)

# Line 26-70: 새로운 함수들
def begin_stage_asset_tracking() -> None:
    """Begin tracking assets for a specific stage."""
    _STAGE_ASSET_CONTEXT.set(_initial_context())


def end_stage_asset_tracking() -> Dict[str, Any]:
    """End tracking for current stage and return snapshot."""
    snapshot = _STAGE_ASSET_CONTEXT.get()
    _STAGE_ASSET_CONTEXT.set(None)
    return snapshot or _initial_context()


def get_stage_assets() -> Dict[str, Any]:
    """Get assets tracked only in current stage."""
    ctx = _STAGE_ASSET_CONTEXT.get()
    return ctx or {}


# Line 71-90: 기존 track 함수 수정 (예: prompt)
def track_prompt_asset(info: Dict[str, Any]) -> None:
    """Track prompt asset in both global and stage contexts."""
    # Global context
    ctx = _ASSET_CONTEXT.get()
    if ctx:
        ctx["prompt"] = info

    # Stage context
    stage_ctx = _STAGE_ASSET_CONTEXT.get()
    if stage_ctx is not None:
        stage_ctx["prompt"] = info


# 모든 track_* 함수를 동일하게 수정:
# track_policy_asset(), track_mapping_asset(), track_source_asset(),
# track_schema_asset(), track_resolver_asset()


# Line 150-170: catalog 추가
def track_catalog_asset(info: Dict[str, Any]) -> None:
    """Track catalog asset."""
    ctx = _ASSET_CONTEXT.get()
    if ctx:
        ctx["catalog"] = info

    stage_ctx = _STAGE_ASSET_CONTEXT.get()
    if stage_ctx is not None:
        stage_ctx["catalog"] = info


# Line 170-190: tool 추가
def track_tool_asset(info: Dict[str, Any]) -> None:
    """Track tool asset."""
    ctx = _ASSET_CONTEXT.get()
    if ctx:
        ctx["tool"] = info

    stage_ctx = _STAGE_ASSET_CONTEXT.get()
    if stage_ctx is not None:
        stage_ctx["tool"] = info
```

**_initial_context() 수정:**
```python
def _initial_context() -> Dict[str, Any]:
    return {
        "prompt": None,
        "policy": None,
        "mapping": None,
        "source": None,
        "schema": None,
        "resolver": None,
        "catalog": None,      # ← 추가
        "tool": None,          # ← 추가
        "queries": [],
        "screens": [],
    }
```

---

#### 2. `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**변경 사항:**
- Line 1-20: import 확인/추가
- Line ~350-400: stage 실행 래퍼 함수에서 context 호출 추가
- Line ~425: `_resolve_applied_assets()` 메서드 수정
- 각 stage 실행 부분에서 tracking 시작/종료

**코드 예시:**

```python
# Line 1-20: import 추가
from app.modules.inspector.asset_context import (
    begin_stage_asset_tracking,
    end_stage_asset_tracking,
    get_stage_assets,
)

# Line ~350: stage 실행 전 호출
async def execute_stage(self, stage_name: str, ...):
    """Execute a specific stage with asset tracking."""

    # Stage 시작 - asset tracking 초기화
    begin_stage_asset_tracking()

    try:
        # 기존 stage 실행 로직
        result = await self._execute_stage_impl(stage_name)

        # Stage 종료 - asset 스냅샷 저장
        stage_assets = end_stage_asset_tracking()

        # stage_inputs 구성
        stage_input = StageInput(
            stage=stage_name,
            applied_assets=self._resolve_applied_assets(),  # ← 이제 stage assets 포함
            ...
        )

        return result

    except Exception as e:
        # Error 발생해도 context cleanup
        end_stage_asset_tracking()
        raise

# Line ~425: _resolve_applied_assets() 수정
def _resolve_applied_assets(self) -> Dict[str, str]:
    """Resolve applied assets for current stage."""
    # ← 변경: get_tracked_assets() 대신 get_stage_assets()
    assets = get_stage_assets()

    applied: Dict[str, str] = {}

    for key in ("prompt", "policy", "mapping", "source", "schema", "resolver", "catalog", "tool"):
        info = assets.get(key)
        if not info:
            continue
        applied[key] = format_asset_display(info)

    # queries와 screens 처리
    for entry in assets.get("queries", []):
        if entry:
            applied.setdefault("queries", []).append(format_asset_display(entry))

    for entry in assets.get("screens", []):
        if entry:
            applied.setdefault("screens", []).append(entry)

    return applied
```

---

#### 3. `apps/api/app/modules/inspector/service.py`

**변경 사항:**
- Line 29-41: `_build_applied_assets()` 수정 (catalog, tool 추가)

**코드 예시:**

```python
def _build_applied_assets(state: dict[str, Any]) -> Dict[str, Any]:
    return {
        "prompt": _summarize_asset(state.get("prompt")),
        "policy": _summarize_asset(state.get("policy")),
        "mapping": _summarize_asset(state.get("mapping")),
        "source": _summarize_asset(state.get("source")),
        "schema": _summarize_asset(state.get("schema")),
        "resolver": _summarize_asset(state.get("resolver")),
        "catalog": _summarize_asset(state.get("catalog")),  # ← 추가
        "tool": _summarize_asset(state.get("tool")),       # ← 추가
        "queries": [
            _summarize_asset(entry) for entry in state.get("queries", []) if entry
        ],
        "screens": [entry for entry in state.get("screens", []) if entry],
    }
```

---

#### 4. `apps/api/app/modules/asset_registry/loader.py`

**변경 사항:**
- `load_catalog_asset()` 함수에서 track 호출 추가
- `load_tool_asset()` 함수에서 track 호출 추가

**코드 예시:**

```python
# load_catalog_asset() 함수 내
def load_catalog_asset(asset_id: str, session: Session) -> Dict[str, Any]:
    """Load catalog asset by ID."""
    asset = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_id == asset_id)
        .where(TbAssetRegistry.asset_type == "catalog")
        .where(TbAssetRegistry.status == "published")
    ).first()

    if not asset:
        return {}

    catalog_data = {
        "asset_id": str(asset.asset_id),
        "name": asset.name,
        "version": asset.version,
        "source": asset.source,
    }

    # ← 추가: tracking
    from app.modules.inspector.asset_context import track_catalog_asset
    track_catalog_asset(catalog_data)

    return catalog_data


# load_tool_asset() 함수 내
def load_tool_asset(asset_id: str, session: Session) -> Dict[str, Any]:
    """Load tool asset by ID."""
    asset = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_id == asset_id)
        .where(TbAssetRegistry.asset_type == "tool")
        .where(TbAssetRegistry.status == "published")
    ).first()

    if not asset:
        return {}

    tool_data = {
        "asset_id": str(asset.asset_id),
        "name": asset.name,
        "version": asset.version,
        "source": asset.source,
        "tool_type": getattr(asset, "tool_type", None),
        "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
    }

    # ← 추가: tracking
    from app.modules.inspector.asset_context import track_tool_asset
    track_tool_asset(tool_data)

    return tool_data
```

---

#### 5. `apps/api/app/modules/asset_registry/models.py` (조건부)

**변경 사항** (Tool 지원이 필요할 때):
- Line 79-90: tool 필드 uncomment

**주의**: Database migration이 필요할 수 있음

```python
# Line 79-90: Uncomment these fields

class TbAssetRegistry(Base):
    # ... existing fields ...

    tool_type: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Type of tool (function, api, etc.)"
    )
    tool_catalog_ref: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Reference to tool catalog"
    )
    tool_config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Tool configuration"
    )
    tool_input_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Input schema for tool"
    )
    tool_output_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Output schema for tool"
    )
```

---

#### 6. `apps/web/src/app/admin/inspector/page.tsx` (선택)

**변경 사항** (tool & catalog 아이콘):
- Line 1201-1211: 아이콘 설정에 catalog, tool 추가

```typescript
const config = {
  prompt: { icon: "⭐", color: "text-blue-400" },
  policy: { icon: "🛡️", color: "text-emerald-400" },
  mapping: { icon: "🗺️", color: "text-amber-400" },
  source: { icon: "💾", color: "text-slate-300" },
  schema: { icon: "📊", color: "text-fuchsia-300" },
  resolver: { icon: "🔧", color: "text-orange-300" },
  query: { icon: "🔍", color: "text-purple-400" },
  catalog: { icon: "📚", color: "text-indigo-400" },    // ← 추가
  tool: { icon: "🛠️", color: "text-cyan-400" },         // ← 추가
}[type] || { icon: "📄", color: "text-slate-400" };
```

---

## Part 5: 테스트 계획

### Unit Tests

**File**: `apps/api/tests/test_asset_context.py` (신규)

```python
def test_stage_context_isolation():
    """Test that stage contexts are isolated"""
    begin_stage_asset_tracking()

    track_prompt_asset({"name": "prompt_a"})
    assert get_stage_assets()["prompt"]["name"] == "prompt_a"

    assets1 = end_stage_asset_tracking()

    # New stage
    begin_stage_asset_tracking()
    assert get_stage_assets().get("prompt") is None  # Should be empty

    track_prompt_asset({"name": "prompt_b"})
    assets2 = end_stage_asset_tracking()

    assert assets1["prompt"]["name"] == "prompt_a"
    assert assets2["prompt"]["name"] == "prompt_b"


def test_catalog_asset_tracking():
    """Test catalog asset tracking"""
    begin_stage_asset_tracking()

    catalog_info = {"asset_id": "cat1", "name": "my_catalog"}
    track_catalog_asset(catalog_info)

    stage_assets = get_stage_assets()
    assert stage_assets["catalog"]["name"] == "my_catalog"


def test_tool_asset_tracking():
    """Test tool asset tracking"""
    begin_stage_asset_tracking()

    tool_info = {"asset_id": "tool1", "name": "my_tool"}
    track_tool_asset(tool_info)

    stage_assets = get_stage_assets()
    assert stage_assets["tool"]["name"] == "my_tool"
```

### Integration Tests

**File**: `apps/api/tests/test_stage_asset_assignment.py` (신규)

```python
async def test_stage_assets_are_different():
    """Test that stage_inputs.applied_assets differs per stage"""
    # Execute full trace
    trace_id = "test-trace-id"
    trace = await execute_full_trace(trace_id)

    stage_inputs = trace.stage_inputs

    # Collect assets per stage
    route_plan_assets = stage_inputs[0].applied_assets
    validate_assets = stage_inputs[1].applied_assets

    # They should be different (or at least one should have fewer assets)
    assert route_plan_assets != validate_assets


async def test_new_trace_shows_stage_specific_assets():
    """Test that new trace query shows stage-specific assets"""
    # Query trace
    trace = get_trace("7a3e39d9-1b32-4e93-be11-cc3ad4a820e1")

    for stage_input in trace.stage_inputs:
        stage = stage_input.stage
        assets = stage_input.applied_assets

        # At least one stage should have different assets than others
        # (After fix, not all stages will have all 5 assets)
```

### Manual Testing

1. **Inspector UI 확인**
   - trace_id `7a3e39d9-1b32-4e93-be11-cc3ad4a820e1` 조회
   - Stage Pipeline 섹션 확인
   - 각 stage의 "Applied Assets"이 다른지 확인

2. **API 직접 조회**
   ```bash
   curl http://localhost:8000/api/inspector/traces/7a3e39d9-1b32-4e93-be11-cc3ad4a820e1
   ```
   - `stage_inputs[*].applied_assets` 확인
   - 각 stage마다 다른 asset이 저장되었는지 확인

---

## Part 6: 예상 효과

### Before Fix
```
Route Plan Stage:
  ✅ policy: view_depth_policies
  ✅ prompt: ci_planner_output_parser
  ✅ source: primary_postgres
  ✅ mapping: output_type_priorities
  ✅ resolver: default_resolver

Validate Stage:
  ✅ policy: view_depth_policies
  ✅ prompt: ci_planner_output_parser
  ✅ source: primary_postgres
  ✅ mapping: output_type_priorities
  ✅ resolver: default_resolver

Execute Stage:
  ✅ policy: view_depth_policies
  ✅ prompt: ci_planner_output_parser
  ✅ source: primary_postgres
  ✅ mapping: output_type_priorities
  ✅ resolver: default_resolver
```

### After Fix
```
Route Plan Stage:
  ✅ policy: view_depth_policies
  ✅ prompt: ci_planner_output_parser

Validate Stage:
  ✅ policy: view_depth_policies
  (prompt 재사용이므로 표시 안 함)

Execute Stage:
  ✅ source: primary_postgres
  (policy, prompt는 이미 로드되었으므로 표시 안 함)

Compose Stage:
  ✅ mapping: output_type_priorities
  ✅ resolver: default_resolver

Present Stage:
  ❌ (새로운 asset 로드 안 함)
```

---

## Part 7: Migration & Deployment

### Pre-Deployment Checklist

- [ ] Code review 완료
- [ ] Unit tests 모두 pass
- [ ] Integration tests 모두 pass
- [ ] 기존 기능 regression 테스트
- [ ] Performance impact 평가 (거의 없을 것으로 예상)
- [ ] DB migration 필요 여부 확인 (tool fields 활성화 시에만)

### Deployment Strategy

**Phase 1** (필수):
- `asset_context.py` 배포
- `runner.py` 배포
- `service.py` 배포
- Tests pass 확인

**Phase 2** (선택, 나중에):
- `loader.py` 배포 (catalog, tool)
- `models.py` 배포 (tool fields)

### Rollback Plan

문제 발생 시:
- `asset_context.py` 이전 버전으로 복구
- `runner.py` 이전 버전으로 복구
- 데이터는 영향 없음 (단순 추적 로직 변경)

---

## Summary

| 항목 | 현황 | 개선 후 |
|------|------|--------|
| Stage별 asset 표시 | ❌ 모두 동일 | ✅ 각 stage별 다름 |
| Catalog 지원 | ❌ 미지원 | ✅ 지원 |
| Tool 지원 | ❌ 미지원 | ✅ 지원 |
| 파일 변경 수 | - | 4-6개 |
| 예상 구현 시간 | - | ~2-3시간 |
| DB migration | - | 선택 (tool fields용) |

---

**이 계획에 따라 VS Code extension에서 구현하시면 됩니다.**
**각 파일별로 정확한 라인 번호와 코드가 제공되었으므로 직접 수정이 가능합니다.**
