# OPS Mode Filtering Guide

**Date**: 2026-02-13
**Status**: ✅ **IMPLEMENTED**

---

## 개요

OPS UI에서 사용자가 모드를 선택하면 (구성/수치/이력/연결/문서/전체), 해당 모드와 관련된 tools만 선택되도록 필터링하는 시스템입니다.

---

## 아키텍처

### 1. UI 모드 선택
```
사용자가 UI에서 선택:
- 구성 (config)
- 수치 (metric)
- 이력 (history/hist)
- 연결 (graph)
- 문서 (document)
- 전체 (all)
```

### 2. 데이터 흐름
```
UI Mode Selection
    ↓
POST /ops/query?mode=config
    ↓
execute_universal(question, mode="config", tenant_id)
    ↓
_create_simple_plan(mode="config", question)
    ↓
Plan.mode_hint = "config"  ← NEW!
    ↓
OpsOrchestratorRunner(plan, ...)
    ↓
SmartToolSelector.select_tools(context)
    ↓
_get_candidate_tools(intent, mode_hint="config")
    ↓
Mode Keywords Filtering  ← NEW!
    ↓
Only config-related tools selected
```

---

## 구현 상세

### 1. Plan Schema 수정 (`plan_schema.py`)

**추가된 필드**:
```python
class Plan(BaseModel):
    # ... existing fields
    mode_hint: str | None = Field(
        default=None,
        description="Mode hint to guide tool selection (config, metric, graph, history, document, all)"
    )
```

### 2. Plan 생성 시 mode_hint 설정 (`services/__init__.py`)

**_create_simple_plan()**:
```python
def _create_simple_plan(mode: str, question: str = "") -> Any:
    # ... existing code
    mode_hint = mode  # Store mode for tool selection filtering

    # ... mode-specific configuration

    return Plan(
        intent=intent,
        view=view,
        mode=plan_mode,
        # ... other specs
        mode_hint=mode_hint,  # Pass mode hint for tool selection
    )
```

**_create_all_plan()**:
```python
def _create_all_plan(question: str) -> Any:
    # ... existing code

    return Plan(
        intent=intent,
        view=view,
        mode=plan_mode,
        # ... other specs
        mode_hint="all",  # ALL mode: no filtering
    )
```

### 3. ToolSelectionContext 수정 (`tool_selector.py`)

**추가된 필드**:
```python
@dataclass
class ToolSelectionContext:
    intent: Intent
    user_pref: SelectionStrategy
    current_load: Dict[str, float]
    cache_status: Dict[str, bool]
    estimated_time: Dict[str, float]
    mode_hint: str | None = None  # NEW: Mode hint for tool filtering
```

### 4. OpsOrchestratorRunner 수정 (`runner.py`)

**mode_hint 전달**:
```python
async def _select_best_tools(self) -> List[str]:
    context = ToolSelectionContext(
        intent=self.plan.intent,
        user_pref=self._selection_strategy(),
        current_load=await self._get_system_load(),
        cache_status={},
        estimated_time=self._estimate_tool_times(),
        mode_hint=getattr(self.plan, "mode_hint", None),  # Pass mode hint
    )
    ranked = await self._tool_selector.select_tools(context)
    return [tool for tool, _ in ranked]
```

### 5. SmartToolSelector - Mode Filtering (`tool_selector.py`)

**새로운 메서드**:
```python
def _get_mode_keywords(self, mode: str) -> List[str]:
    """Get keyword filters for each mode."""
    mode_keywords = {
        "config": ["ci", "config", "lookup", "search", "detail"],
        "metric": ["metric", "cpu", "memory", "disk", "network", "performance"],
        "graph": ["graph", "topology", "relation", "dependency", "neighbor"],
        "history": ["history", "event", "log", "maintenance", "work"],
        "hist": ["history", "event", "log", "maintenance", "work"],
        "document": ["document", "doc", "search", "file"],
    }
    return mode_keywords.get(mode, [])
```

**수정된 _get_candidate_tools()**:
```python
def _get_candidate_tools(self, intent: Intent, mode_hint: str | None = None) -> List[str]:
    """Get candidate tools from registry based on intent and mode_hint."""
    registry = get_tool_registry()
    tools_info = registry.get_all_tools_info()

    candidates = []

    for tool_info in tools_info:
        tool_name = tool_info.get("name")
        tool_type = tool_info.get("type", "")

        # Mode-based filtering (highest priority)
        if mode_hint and mode_hint != "all":
            # Filter by mode keywords
            mode_keywords = self._get_mode_keywords(mode_hint)
            if not any(keyword in tool_name.lower() for keyword in mode_keywords):
                continue  # Skip tools that don't match mode

        # Intent-based filtering (secondary)
        # ... (existing intent logic)

        candidates.append(tool_name)

    # Fallback logic
    if not candidates:
        # Return mode-filtered or all tools
        ...

    return candidates
```

---

## Mode별 Tool 필터링 규칙

### config 모드
**Keywords**: `["ci", "config", "lookup", "search", "detail"]`

**허용되는 Tool 예시**:
- `ci_detail_lookup` ✅ (contains "ci")
- `ci_summary_aggregate` ✅ (contains "ci")
- `config_get_settings` ✅ (contains "config")

**차단되는 Tool 예시**:
- `mcp_add` ❌ (no matching keyword)
- `metric_cpu_usage` ❌ (no matching keyword)
- `graph_topology` ❌ (no matching keyword)

### metric 모드
**Keywords**: `["metric", "cpu", "memory", "disk", "network", "performance"]`

**허용되는 Tool 예시**:
- `sim_metric_timeseries_query` ✅ (contains "metric")
- `metric_cpu_aggregate` ✅ (contains "metric" + "cpu")
- `performance_monitor` ✅ (contains "performance")

**차단되는 Tool 예시**:
- `ci_detail_lookup` ❌
- `graph_topology` ❌
- `document_search` ❌

### graph 모드
**Keywords**: `["graph", "topology", "relation", "dependency", "neighbor"]`

**허용되는 Tool 예시**:
- `ci_graph_expand` ✅ (contains "graph")
- `topology_viewer` ✅ (contains "topology")
- `dependency_analyzer` ✅ (contains "dependency")

### history 모드
**Keywords**: `["history", "event", "log", "maintenance", "work"]`

**허용되는 Tool 예시**:
- `maintenance_history_list` ✅ (contains "history" + "maintenance")
- `event_log_query` ✅ (contains "event" + "log")
- `work_order_search` ✅ (contains "work")

### document 모드
**Keywords**: `["document", "doc", "search", "file"]`

**허용되는 Tool 예시**:
- `document_search` ✅ (contains "document")
- `doc_retrieval` ✅ (contains "doc")
- `file_lookup` ✅ (contains "file")

### all 모드
**Keywords**: None (no filtering)

**동작**: 모든 Tool Registry의 tools 사용 가능

---

## 사용 예시

### 예시 1: config 모드 선택

**사용자 행동**:
1. UI에서 "구성(config)" 모드 선택
2. 질의: "서버 06 상태는?"

**시스템 동작**:
```
1. POST /ops/query?mode=config
2. execute_universal(question="서버 06 상태는?", mode="config", ...)
3. _create_simple_plan(mode="config", ...) → Plan(mode_hint="config")
4. SmartToolSelector.select_tools(context(mode_hint="config"))
5. _get_candidate_tools(intent=LOOKUP, mode_hint="config")
6. Filter tools: only tools with ["ci", "config", "lookup", "search", "detail"]
7. Result: ["ci_detail_lookup", "ci_summary_aggregate", ...]
8. Execute selected tools
```

**선택되는 Tools**:
- ✅ `ci_detail_lookup` (contains "ci")
- ✅ `ci_summary_aggregate` (contains "ci")
- ❌ `metric_cpu_usage` (filtered out)
- ❌ `graph_topology` (filtered out)

### 예시 2: all 모드 선택

**사용자 행동**:
1. UI에서 "전체(all)" 모드 선택
2. 질의: "서버 06의 CPU 사용률과 의존성 구조는?"

**시스템 동작**:
```
1. POST /ops/ask (all 모드는 /ops/ask 사용)
2. _run_all_orchestration(question, ...)
3. _create_all_plan(...) → Plan(mode_hint="all")
4. SmartToolSelector.select_tools(context(mode_hint="all"))
5. _get_candidate_tools(intent=AGGREGATE, mode_hint="all")
6. NO FILTERING - all tools available
7. Result: ["ci_detail_lookup", "metric_cpu_usage", "graph_topology", ...]
8. Execute multiple tools (serial/parallel based on Plan)
```

**선택되는 Tools**:
- ✅ `ci_detail_lookup` (CI 정보)
- ✅ `metric_cpu_usage` (CPU 메트릭)
- ✅ `graph_topology` (의존성 그래프)
- ✅ All other tools available

---

## Tool 이름 규칙 (Best Practices)

Tool Asset를 등록할 때 **mode 키워드를 포함**하면 자동으로 필터링됩니다:

### Good Examples ✅
```
ci_detail_lookup          → config 모드에서 선택됨
ci_graph_expand           → graph 모드에서 선택됨
metric_cpu_aggregate      → metric 모드에서 선택됨
maintenance_history_list  → history 모드에서 선택됨
document_search           → document 모드에서 선택됨
```

### Bad Examples ❌
```
get_server_info      → 어느 모드에도 매칭 안 됨 (키워드 없음)
query_data           → 너무 일반적 (키워드 없음)
mcp_add              → 어느 모드에도 매칭 안 됨
```

**권장사항**: Tool 이름에 **도메인 키워드**를 포함하세요:
- `ci_*` for config mode
- `metric_*` for metric mode
- `graph_*` or `topology_*` for graph mode
- `history_*` or `event_*` for history mode
- `document_*` or `doc_*` for document mode

---

## 테스트 시나리오

### Test 1: config 모드 필터링
```bash
curl -X POST http://localhost:8000/ops/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서버 06 상태는?",
    "mode": "config"
  }'
```

**기대 결과**:
- Only CI-related tools selected
- No metric/graph/history tools

### Test 2: metric 모드 필터링
```bash
curl -X POST http://localhost:8000/ops/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서버 06 CPU 사용률은?",
    "mode": "metric"
  }'
```

**기대 결과**:
- Only metric tools selected
- No CI/graph/history tools

### Test 3: all 모드 (no filtering)
```bash
curl -X POST http://localhost:8000/ops/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서버 06의 전체 상태를 알려줘",
    "mode": "all"
  }'
```

**기대 결과**:
- All tools available
- Multiple tools selected (CI + metric + graph + ...)

---

## 디버깅

### 로그 확인
```python
logger.info(
    "tool_selector.ranked",
    extra={
        "intent": context.intent.value,
        "mode_hint": context.mode_hint,
        "top_3": [(name, round(score, 3)) for name, score in ranked[:3]]
    }
)
```

### 필터링 검증
```python
logger.warning(
    "tool_selector.no_intent_match",
    extra={
        "intent": intent.value,
        "mode_hint": mode_hint,
        "fallback_count": len(candidates)
    }
)
```

---

## 향후 개선 사항

1. **Tool Metadata에 tags 추가**:
   ```python
   tool_asset = {
       "name": "ci_detail_lookup",
       "tool_type": "database_query",
       "tags": ["config", "ci", "lookup"],  # NEW
       "capabilities": ["read", "search"],  # NEW
   }
   ```

2. **LLM 기반 tool 선택** (future):
   - Mode hint를 LLM prompt에 포함
   - LLM이 직접 tool 선택

3. **Dynamic keyword learning**:
   - 실제 사용 패턴 학습
   - Mode별 tool 성공률 트래킹

---

**Implementation Date**: 2026-02-13
**Status**: ✅ COMPLETE
**Next**: Testing with actual mode selections
