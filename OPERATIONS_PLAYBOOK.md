# Operations Playbook

이 파일은 D3 “운영 플레이북 정식화” 요구사항에 따라, Inspector 기반으로 문제를 진단하고 Diff/Regression/RCA를 조합하여 대응하는 8가지 시나리오를 정리합니다. 각 시나리오는 작업자가 Inspector 클릭 경로와 사용해야 할 도구(또는 regression flow)를 명시합니다.

## 1. 답이 이상함
- **증상**: 응답 내 주요 항목(값, 개수, 설명)이 문맥과 맞지 않거나, 기대한 도메인(예: CI 토폴로지)과 무관하게 빌드됨.
- **Inspector 클릭 경로**: Trace → `answer.blocks` → 해당 block(`table`, `graph`) → `tool_calls` → `plan_validated.steps`.
- **사용 도구**: Diff + RCA.
  1. Diff 모듈(`TraceDiffView`)에서 이 trace와 Baseline(동일 Golden Query) 비교.
  2. Regression 결과에서 PASS/WARN/FAIL 판정과 `verdict_reason` 확인.
  3. RCA에서 “Plan Intent Shift” 또는 “Tool Path Changes” 규칙 검토.
- **대응**:
  1. Plan intent mismatch → planner prompt 수정 또는 new asset.
  2. Tool path에 불필요한 tool 발견 → executor config roll back.
  3. 재실행 후 diff를 통해 block 변화를 검증하고 PASS 기록 유지.

## 2. 데이터 없음 (정상/비정상 구분)
- **증상**: `No data` 메시지, 로우 개수 0건, 혹은 row_count 감소가 반복.
- **Inspector 클릭 경로**: Trace → `references` (SQL/Cypher/metric) → `row_count` → `trace.meta.filters`.
- **사용 도구**: RCA → Regression (if baseline exist).
  1. RCA의 `No Data Ambiguity` (low confidence) rule로 정상 무 결과인지 확인; false positive이면 `confidence=low`로 표기.
  2. Regression Baseline 대비 reference row_count 80% 이하 reduction이 WARN/FAIL인지 점검.
- **대응**:
  1. 필터/시간 범위 change 확인 후 diff view로 `references[*].query_text` 검토.
  2. Production data 부족이면 `Ops checklist`에 “데이터 수집 확인” 추가.
  3. WARN이 나온 경우, baseline trace 다시 capture 후 PASS 여부 확인.

## 3. Tool timeout
- **증상**: 도구 실행 시간이 기준을 초과하고, `tool_call.error`에 `timeout` 문구.
- **Inspector 클릭 경로**: Trace → `execution_steps` → `duration_ms` → `error`.
- **사용 도구**: RCA + Regression.
  1. RCA에서 `Tool Duration Spike` rule을 보고 evidence path jump.
  2. Regression에서 `timed out` tool이 baseline에서 absent or success 인지 검증.
- **대응**:
  1. `ToolCall` config의 timeout 값/리트라이 수 확인 (`apps/api/app/modules/ops/services/_tool_config`).
  2. Timeout tool이 외부 호출이면 `External API 5xx` 항목(다음 시나리오)과 연결하면서 API health 체크.
  3. 변경사항 적용 후 `GQ`를 rerun 하여 PASS status 유지.

## 4. 외부 API 5xx
- **증상**: `tool_call.error.status=5xx`, External HTTP 도구, `trace.references`에 `kind: "http"`.
- **Inspector 클릭 경로**: Trace → `tool_calls` → `step_id` → `error.request`.
- **사용 도구**: RCA + Diff.
  1. RCA rule `HTTP 5xx` evidence path jump → `requests` silica.
  2. Diff view로 baseline vs candidate response payload + references row count 비교.
- **대응**:
  1. 스텝 내 `requests` URL/headers 확인, 필요한 API key/token 유효성 점검.
  2. HTTP status 5xx 지속시 `next_actions`에 “retry after 5m” or “switch fallback asset”.
  3. Regression run에서 FAIL이면 asset rollback + `RCA Rule B5` 도구 error regression rule confirm.

## 5. 권한/401/403
- **증상**: `HTTP 401` 또는 `403` error. Inspector에서 `token`/`role` mismatch confirm.
- **Inspector 클릭 경로**: Trace → `execution_steps[i].error.response.status` → `meta.claims`.
- **사용 도구**: RCA (Tool Call Errors) + Regression (Baseline).
  1. RCA evidence path jumps to `error.message` + `response.headers` to highlight missing scope.
  2. Regression diff to check if caller identity or asset version changed.
- **대응**:
  1. Credentials rotation 여부, `asset_registry` policy update log 확인.
  2. `RCA checklist`: token refresh, policy allowlist.
  3. After fix, re-run regression with same Golden Query to ensure PASS + `verdict_reason` now “Credentials refreshed”.

## 6. 자산 변경 후 회귀
- **증상**: Regression run FAIL/WARN 직후, `asset_versions` mismatch, `Answer` structure change.
- **Inspector 클릭 경로**: Trace → `asset_versions` → `applied_assets`.
- **사용 도구**: Regression + RCA.
  1. Regression diff shows assets_changed flag, `verdict_reason` references changed asset.
  2. RCA rule `Asset Version Drift` attaches evidence path and recommended rollback.
- **대응**:
  1. Rollback or re-apply asset version, log in `asset_registry`.
  2. When new asset expected, update baseline trace to capture new version, then rerun regression to PASS.
  3. Document change in `docs/versions/asset-changes.md` with `trace_id`.

## 7. UI 렌더 오류
- **증상**: `ui_render.error_count > 0`, Antwort block not rendering in Inspector.
- **Inspector 클릭 경로**: Trace → `ui_render.errors[0]` → `block_index` → `schema`.
- **사용 도구**: RCA + Diff (UI diff).
  1. RCA rule `UI Render Failures` identifies `component mismatch`.
  2. Diff view to compare `answer.blocks` structure with baseline.
- **대응**:
  1. 애셋의 block schema mismatch인지 확인 후 UI map config patch.
  2. Regression run after rebuild ensures PASS.
  3. Add entry to `UI Creator` or `components/answer` watchers if new block needs support.

## 8. Trace 누락/저장 실패
- **증상**: Regression run 또는 Inspector에서 `trace` field 없음, `trace_id` not persisted.
- **Inspector 클릭 경로**: OPS Dashboard → `Ops Logs` → `Trace Blackbox` → `trace_id`.
- **사용 도구**: RCA + Regression (observability).
  1. RCA rule `Trace Persistence` (정책 violation) - evidence path: `trace.meta.persistence`.
  2. Regression diff ensures no baseline entry created.
- **대응**:
  1. Backend logs (`apps/api/logs/api.log`) / DB (`tb_execution_trace`) check for missing writes.
  2. If persistence fails, rerun question and confirm `trace_id` recorded; consider enabling `ops_trace.retry`.
  3. Document event in `docs/trace-ops/trace-missing.md` for future auditing.

각 플레이북은 Inspector에서 evidence path를 따라가며 Diff/Regression/RCA를 적절히 조합해 신속하게 원인을 좁혀줍니다. 필요한 경우 `next_actions`의 `re-run` 버튼, `Asset Registry` 롤백, `RCA checklist` 등도 함께 활용하세요.
