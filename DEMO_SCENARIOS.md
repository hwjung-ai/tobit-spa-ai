# Demo Scenarios

각 시나리오는 Trace Flow → Trace Diff → Regression 실행 → RCA Assist 흐름을 통해 운영자가 “어떻게 문제를 찾아내고 왜 FAIL인지 설명하며 그 다음 조치를 정하는지”를 보여줍니다.

## 1. CI 시스템 의존 관계가 엉킴
- **Flow**: Ops 질문 “sys-erp 의존 관계” → `/ops/ci/ask` 응답으로 Graph + Table block → Trace에 plan/graph recorded.
- **Diff**: Regression Watch에서 이전 baseline 그래프(GQ-002)와 비교하여 edge 수가 줄었음을 확인.
- **Regression**: GQ-002를 rerun → FAIL (tool path change) → verdict_reason “cluster graph edge removed”.
- **RCA**: `Tool Path Changes` rule + evidence path jump → Inspector에서 `graph_path` block → Attackers check list: Neo4j 관계 매핑, policy allowlist.

## 2. Storage latency 급증
- **Flow**: 질문 “storage latency last 1h trend” → metric/graph block + timeline.
- **Diff**: Recorded trace vs previous baseline (GQ-003) → duration delta, references unchanged.
- **Regression**: Run regression → WARN (performance regression) → diff summary shows candidate_duration = 3120ms.
- **RCA**: `Tool Duration Spike` / `Performance Regression` rule highlight `execution_steps[1]`, checklist includes DB slow query log and cache TTL.

## 3. 데이터 없음 vs 정상
- **Flow**: 질문 “show RCA entries for storage” → history block with “No data” message.
- **Diff**: TraceDiffView compares candidate vs baseline baseline where history had rows; candidate references list empty.
- **Regression**: Run regression (GQ-004) → WARN (data reduction) with references variance 75%.
- **RCA**: `No Data Ambiguity` rule runs low confidence, `evidence.path` points to `references[*].row_count` = 0 → checklist ensures filters/time-range correct before re-run.

## 4. 인증이 만료된 API
- **Flow**: 질문 “list protected asset versions” → tool call to HTTP API returning 401.
- **Diff**: Trace diff identifies new `verdict_reason` and `execution_steps[i].error`.
- **Regression**: Running regression on GQ-005 after asset change → FAIL because `verdict_reason` changed and tool error increased.
- **RCA**: `HTTP Auth Errors` rule surfaces evidence path + recommended action “refresh token, verify asset policy”.

## 5. UI 렌더 블록 깨짐
- **Flow**: 질문 “show RCA summary” → answer block includes UI renderer block referencing `UIScreen`.
- **Diff**: baseline block set vs candidate block set compared; new block under `answer.blocks` flagged as `block_schema` mismatch.
- **Regression**: Running regression on GQ-009 (“Ops Trace Consistency”) and inspect `ui_render.error_count` change → FAIL.
- **RCA**: `UI Render Failures` rule points to `ui_render.errors[0]`, checklist checks UIScreen schema, binding engine config.

각 데모는 Inspector > Regression > RCA Assist로 이어지며, 운영자가 Inspector만으로 평가/개선/회귀 감시를 수행할 수 있음을 강조합니다.
