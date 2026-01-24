# Phase 2 - 백엔드 연결 & 프론트 통합 (구현 계획서)

**작성일**: 2026-01-24
**상태**: Phase 2 시작
**범위**: Backend 자산 통합 + Trace 강화 + Frontend Inspector UI 연결

---

## 1. Backend Asset 통합 (필수 변경사항)

### 1.1 함수 시그니처 확장

#### planner_llm.py
- `create_plan_output(question, schema_context=None, source_context=None)` 추가
  - schema_context: catalog 정보, available fields
  - source_context: 데이터소스 연결 정보
- `_call_output_parser_llm(text, schema_context=None, source_context=None)` 확장
  - 프롬프트에 스키마/소스 컨텍스트 주입

#### router.py (라인 381-400)
- planner_llm.create_plan_output() 호출 시 schema/source 자산 전달
```python
plan_output = planner_llm.create_plan_output(
    normalized_question,
    schema_context=schema_payload,
    source_context=source_payload
)
```

#### validator.py
- `validate_plan(plan, resolver_payload=None)` 시그니처 확장
- resolver 규칙을 Plan 검증 단계에서도 적용

---

## 2. Trace 데이터 완벽화

### 2.1 stage_inputs / stage_outputs 강화

#### runner.py (라인 509-596)
현재: `stage_inputs[]`, `stage_outputs[]` 배열로 기록

확인 필요사항:
- [ ] 각 stage의 입력/출력이 완전히 기록되는지
- [ ] `stage_inputs[i]` = `{stage: name, applied_assets: {}, params: {}, prev_output: ...}`
- [ ] `stage_outputs[i]` = `{stage: name, status: ok|warning|error, result: {}, diagnostics: {}}`

#### References 생성 강화

**현재 문제**: References가 tool_calls 기반으로 최소 1건 이상 생성되지 않을 수 있음

**해결방안**:
- stage_executor.py에서 실행된 도구 호출 기록 강화
- 각 tool_call → reference 자동 생성 로직 추가

```python
# stage_executor.py 수정
def execute_stage(self, stage_input: StageInput) -> StageOutput:
    # ... 기존 로직
    references = []
    for tool_call in tool_calls:
        ref = {
            "type": "tool_call",
            "tool_name": tool_call.get("tool"),
            "params": tool_call.get("params"),
            "result_summary": tool_call_result_summary
        }
        references.append(ref)
    # references 반환
```

### 2.2 Replan Events 정규화

**현재**:
- router.py의 replan_events 생성 로직 (라인 395-422, 685-772)

**필요한 확인**:
- [ ] ReplanEvent 스키마와 백엔드 생성 로직 일치 확인
- [ ] 프론트엔드 ReplanTimeline.tsx와 동기화

---

## 3. Asset Override 메커니즘 구현

### 3.1 Stage Executor에서 override 적용

**파일**: `stage_executor.py` (라인 55-75)

**현재**: `asset_overrides` 파라미터만 받음 (실제 적용 로직 미흡)

**구현**:
```python
class StageExecutor:
    def __init__(self, ..., asset_overrides: dict[str, str] | None = None):
        self.asset_overrides = asset_overrides or {}

    def execute_stage(self, stage_input: StageInput) -> StageOutput:
        # applied_assets에 override 적용
        for asset_type, override_name in self.asset_overrides.items():
            if asset_type in ["source", "schema", "resolver"]:
                # 해당 자산을 override_name으로 교체
                stage_input.applied_assets[asset_type] = override_name
```

---

## 4. Frontend Inspector/UI 연결

### 4.1 page.tsx 수정

**파일**: `apps/web/src/app/ops/page.tsx` (추정)

필요 작업:
- [ ] ExecutionTraceRead 타입 임포트
- [ ] route, stage_inputs, stage_outputs, replan_events 필드 렌더링
- [ ] InspectorStagePipeline 컴포넌트 연결
- [ ] ReplanTimeline 컴포넌트 연결

### 4.2 Inspector UI 컴포넌트 검증

- [ ] InspectorStagePipeline.tsx: stage 데이터 렌더링 확인
- [ ] ReplanTimeline.tsx: replan_events 렌더링 확인
- [ ] Regression 분석 UI: stage 비교 렌더링 확인

---

## 5. Screen Asset Loader 추가

### 5.1 loader.py에 screen asset 로더 추가

```python
def load_screen_asset(name: str) -> dict[str, Any] | None:
    """Load screen asset with fallback priority"""
    # Priority 1: DB (published)
    # Priority 2: File resources/screens/{name}.json
    # Priority 3: None
```

---

## 6. StageInput/StageOutput 타입화

### 6.1 schemas.py 확인

**파일**: `app/modules/ops/schemas.py`

필요사항:
- [ ] StageInput 모델 정의 확인 (라인 173-199)
- [ ] StageOutput 모델 정의 확인
- [ ] runner.py에서 Dict 대신 타입 모델 사용

---

## 7. 테스트 계획

### 7.1 Backend 테스트

```bash
# pytest
cd apps/api
pytest app/modules/ops/services/ci/planner/test_planner_llm.py
pytest app/modules/ops/services/ci/planner/test_validator.py
pytest app/modules/ops/services/ci/orchestrator/test_runner.py
```

### 7.2 API 테스트

```bash
# /ops/ci/ask 엔드포인트 확인
curl -X POST http://localhost:8000/ops/ci/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "test query"}'

# 응답에서 trace 데이터 확인:
# - route: "orch" | "direct" | "reject"
# - stage_inputs: [] (stage별 입력)
# - stage_outputs: [] (stage별 출력)
# - replan_events: [] (재계획 이벤트)
```

### 7.3 Frontend 테스트

```bash
# Playwright Inspector spec
cd apps/web
npm run test:e2e -- tests-e2e/inspector_spec.ts
```

---

## 8. 구현 순서 (추천)

1. **Backend Asset 통합** (2-3시간)
   - router.py 수정 (schema/source 전달)
   - planner_llm.py 확장 (함수 시그니처)
   - validator.py 확장 (resolver 규칙 적용)

2. **Trace 강화** (1-2시간)
   - stage_inputs/outputs 검증
   - References 생성 로직 강화
   - Replan Events 정규화

3. **Asset Override** (30분-1시간)
   - stage_executor.py에 override 로직 추가

4. **Screen Asset Loader** (30분)
   - loader.py에 load_screen_asset() 추가

5. **StageInput/StageOutput 타입화** (1시간)
   - schemas.py 확인
   - runner.py 수정 (Dict → 타입 모델)

6. **Frontend 연결** (1-2시간)
   - page.tsx에 Inspector UI 컴포넌트 연결
   - trace 데이터 렌더링 테스트

7. **전체 테스트** (1-2시간)
   - Backend pytest
   - API curl 테스트
   - Frontend E2E 테스트

---

## 9. 검증 체크리스트

### Backend
- [ ] planner_llm.py에서 schema/source 자산 받음
- [ ] validator.py에서 resolver 규칙 적용
- [ ] runner.py에서 stage_inputs/outputs 완벽하게 채움
- [ ] References 최소 1건 이상 생성
- [ ] Replan Events 정규화됨

### Frontend
- [ ] Inspector UI에 route 표시
- [ ] InspectorStagePipeline에 stage_inputs/outputs 표시
- [ ] ReplanTimeline에 replan_events 표시
- [ ] Regression 분석에서 stage 비교 가능

### 통합
- [ ] 전체 요청→응답 데이터 흐름 확인
- [ ] trace JSON에 모든 필드 포함 확인
- [ ] Frontend에서 모든 데이터 렌더링됨

---

## 10. 다음 액션

1. 이 계획서를 검토하고 승인
2. 1번 항목 (Backend Asset 통합)부터 시작
3. 각 항목 완료 후 테스트 확인
4. 최종 통합 테스트

---

**작성**: 2026-01-24 14:55 UTC
**예상 총 소요시간**: 6-10시간 (병렬화 가능)
