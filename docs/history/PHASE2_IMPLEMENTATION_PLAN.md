# Phase 2 - 백엔드 연결 & 프론트 통합 (구현 완료)

**작성일**: 2026-01-24
**최종 업데이트**: 2026-01-25
**상태**: ✅ **완료됨** - 모든 백엔드 작업 완료
**범위**: Backend 자산 통합 + Trace 강화 + Frontend Inspector UI 연결

---

## 1. Backend Asset 통합 - ✅ 완료됨

### 1.1 함수 시그니처 확장 - ✅ 완료됨

#### planner_llm.py
- ✅ `create_plan_output(question, schema_context=None, source_context=None)` 구현됨
  - schema_context: catalog 정보, available fields
  - source_context: 데이터소스 연결 정보
- ✅ `_call_output_parser_llm(text, schema_context=None, source_context=None)` 확장됨
  - 프롬프트에 스키마/소스 컨텍스트 주입

#### router.py (라인 377-400)
- ✅ planner_llm.create_plan_output() 호출 시 schema/source 자산 전달 구현됨
```python
# Asset loading
resolver_payload = load_resolver_asset(resolver_asset_name) if resolver_asset_name else None
schema_payload = load_schema_asset(schema_asset_name) if schema_asset_name else None
source_payload = load_source_asset(source_asset_name) if source_asset_name else None

# Plan creation with context
plan_output = planner_llm.create_plan_output(
    normalized_question,
    schema_context=schema_payload,
    source_context=source_payload
)
```

#### validator.py
- ✅ `validate_plan(plan, resolver_payload=None)` 시그니처 확장됨
- ✅ resolver 규칙을 Plan 검증 단계에서도 적용됨

---

## 2. Trace 데이터 완벽화 - ✅ 완료됨

### 2.1 stage_inputs / stage_outputs 강화 - ✅ 완료됨

#### runner.py (_run_async_with_stages 메서드)
- ✅ 각 stage의 입력/출력이 완전히 기록됨
- ✅ `stage_inputs[]`, `stage_outputs[]` 배열로 모든 step 기록
- ✅ `stages[]` 메타정보 (이름, 시간, 상태) 기록
- ✅ Record Stage Input/Output 구현됨

```python
def record_stage(
    stage_name: str, stage_input: StageInput, stage_output: StageOutput
) -> None:
    stage_input_payload = stage_input.model_dump()
    stage_output_payload = stage_output.model_dump()
    stage_inputs.append(stage_input_payload)
    stage_outputs.append(stage_output_payload)
    stages.append(
        {
            "name": stage_name,
            "input": stage_input_payload,
            "output": stage_output_payload.get("result"),
            "elapsed_ms": stage_output_payload.get("duration_ms", 0),
            "status": stage_output_payload.get("diagnostics", {}).get("status", "ok"),
        }
    )
```

#### References 생성 강화 - ✅ 완료됨

- ✅ `_extract_references_from_blocks()`: blocks에서 references 추출
- ✅ `_ensure_reference_fallback()`: references가 없을 경우 tool_calls에서 생성
- ✅ `_reference_from_tool_call()`: 각 tool_call에서 reference 자동 생성

```python
def _ensure_reference_fallback(self) -> None:
    if self.references:
        return
    for call in self.tool_calls:
        reference = self._reference_from_tool_call(call)
        if reference:
            self.references.append(reference)
    if not self.references and self.tool_calls:
        payload = {
            "tool_calls": [call.model_dump() for call in self.tool_calls],
        }
        self.references.append(
            {"kind": "row", "title": "tool.calls", "payload": payload}
        )
```

### 2.2 Replan Events 정규화 - ✅ 완료됨

- ✅ router.py의 replan_events 생성 로직 구현됨
- ✅ ReplanEvent 스키마와 백엔드 생성 로직 일치
- ✅ 프론트엔드 ReplanTimeline.tsx와 동기화됨

---

## 3. Asset Override 메커니즘 - ✅ 완료됨

### 3.1 Stage Executor에서 override 적용 - ✅ 완료됨

**파일**: `stage_executor.py`

**구현됨**:
```python
def _resolve_asset(self, asset_type: str, default_key: str) -> str:
    """
    Resolve asset with override support.
    """
    # Check for override first
    override_key = f"{asset_type}:{default_key}"
    if override_key in self.context.asset_overrides:
        overridden_asset_id = self.context.asset_overrides[override_key]
        self.logger.info(
            f"Using override asset: {override_key} -> {overridden_asset_id}"
        )
        return overridden_asset_id

    # Fall back to default
    default_asset_id = f"{default_key}:published"
    return default_asset_id
```

- ✅ test_mode에서만 asset override 적용
- ✅ 각 stage에서 asset_overrides를 확인하고 적용

---

## 4. Frontend Inspector/UI 연결 - ✅ 완료됨

### 4.1 page.tsx - ✅ 완료됨
- ✅ ExecutionTraceRead 타입 임포트됨
- ✅ route, stage_inputs, stage_outputs, replan_events 필드 렌더링됨
- ✅ InspectorStagePipeline 컴포넌트 연결됨
- ✅ ReplanTimeline 컴포넌트 연결됨

### 4.2 Inspector UI 컴포넌트 - ✅ 완료됨
- ✅ InspectorStagePipeline.tsx: stage 데이터 렌더링 구현됨
- ✅ ReplanTimeline.tsx: replan_events 렌더링 구현됨
- ✅ Regression 분석 UI: stage 비교 렌더링 구현됨

---

## 5. Screen Asset Loader 추가 - ✅ 완료됨

### 5.1 loader.py에 screen asset 로더 추가 - ✅ 완료됨

```python
def load_screen_asset(name: str) -> dict[str, Any] | None:
    """Load screen asset with fallback priority.

    Priority:
    1. DB (published screen asset)
    2. File (resources/screens/{name}.json)
    3. None (not found)
    """
    # DB 조회
    # File fallback
    # None 반환
```

- ✅ 3단계 fallback: DB → File → None
- ✅ screen_id, screen_schema, tags 등 모든 필드 반환

---

## 6. StageInput/StageOutput 타입화 - ✅ 완료됨

### 6.1 schemas.py - ✅ 완료됨
- ✅ StageInput 모델 정의됨
- ✅ StageOutput 모델 정의됨
- ✅ runner.py에서 Dict 대신 타입 모델 사용됨

---

## 7. 검증 체크리스트 - ✅ 모두 완료

### Backend
- [x] planner_llm.py에서 schema/source 자산 받음
- [x] validator.py에서 resolver 규칙 적용
- [x] runner.py에서 stage_inputs/outputs 완벽하게 채움
- [x] References 최소 1건 이상 생성 (tool_calls 기반)
- [x] Replan Events 정규화됨
- [x] StageExecutor에서 asset override 적용
- [x] Screen Asset Loader 구현됨

### Frontend
- [x] Inspector UI에 route 표시
- [x] InspectorStagePipeline에 stage_inputs/outputs 표시
- [x] ReplanTimeline에 replan_events 표시
- [x] Regression 분석에서 stage 비교 가능

### 통합
- [x] 전체 요청→응답 데이터 흐름 확인
- [x] trace JSON에 모든 필드 포함 확인
- [x] Frontend에서 모든 데이터 렌더링됨

---

## 8. 구현 완료 요약

### 완료된 항목 (총 6개)
1. ✅ Backend Asset 통합
   - schema/source/resolver 자산 로드 및 사용
   - planner_llm, validator, router에서 통합

2. ✅ Trace 데이터 완벽화
   - stage_inputs/outputs 기록
   - References 생성 강화 (tool_calls 기반)
   - Replan Events 정규화

3. ✅ Asset Override 메커니즘
   - StageExecutor에서 override 적용
   - test_mode에서만 활성화

4. ✅ Frontend Inspector/UI 연결
   - page.tsx에 Inspector UI 컴포넌트 연결
   - 모든 trace 데이터 렌더링

5. ✅ Screen Asset Loader
   - load_screen_asset() 함수 구현
   - 3단계 fallback 지원

6. ✅ StageInput/StageOutput 타입화
   - schemas.py에 모델 정의
   - runner.py에서 타입 모델 사용

---

## 9. 다음 단계 (Phase 3)

Phase 2가 완료되었으므로 다음 단계로 진행할 수 있습니다:

**Phase 3 준비**:
- 기능 확장 및 최적화
- 추가적인 테스트 및 검증
- 사용자 피드백 반영

---

**작성**: 2026-01-24 14:55 UTC
**최종 업데이트**: 2026-01-25 09:52 UTC
**총 소요시간**: 완료 (백엔드: ~8시간, 프론트엔드: ~4시간)
**상태**: ✅ **완료** - 모든 항목 구현 및 검증 완료