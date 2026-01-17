# RCA Quality Guide

Step 6 RCA Assist의 운영 단계 품질 강화와 D2 요구사항을 동시에 만족하기 위해 아래 항목을 정리했습니다.

## 1. RCA Evidence Jump 개선 (Inspector integration)

1. **Evidence Path 클릭 → Inspector jump**: `RCAHypothesis.evidence.path`에 있는 DOT path(`execution_steps[2].error.message`)를 클릭하면 Inspector가 해당 trace node로 스크롤되고, 붙박이 단축키 `J`로 해당 step으로 jump합니다. UI에는 `trace.jumpTargets` 메타 데이터가 추가되어 `Inspect -> Evidence`로 순환합니다.
2. **Low-confidence *(confidence="low")* 지정**: `RCAHypothesis.confidence` 값을 “low”로 설정한 규칙은 UI에서 옅은 색(#F9DDA4)으로 표기되고, `confidence_hint` 텍스트(“재현성이 낮음”)이 함께 표시됩니다. 검증 checklists에 “re-run 확인”을 권장합니다.
3. **오탐/중복 규칙 분리**: `No Data Normal`(정상적인 무 결과)과 같이 과거 오탐이 자주 발생한 규칙은 confidence를 “low”로 내리고 evidence display에 “(예: 정상 No-data)” 태그를 추가하여 재확인 유도합니다.

## 2. RCA Rule Set v2 (정제된 12개)

| Rule | Kind | Confidence | Improvements | Notes |
|------|------|------------|--------------|-------|
| Tool Call Errors (A1) | single | high | 기존 `timeout/auth/http5xx` + `tool_call.output.success=false` 추가 | Jump path: `execution_steps[i].error` |
| Tool Duration Spike (A2) | single | medium | `duration_ms > avg * 3`과 `tool_call.retry` 검사 추가 | `Trace -> Trend graph` quick launch 버튼 |
| UI Render Failures (A3) | single | medium | `ui_render.error_count` 증가 시 RCA block에 UI mapper link 제공 | evidence path points to `ui_render.errors[*]` |
| Validator Policy Violation (A4) | single | high | `policy_decisions.policy_violations` 상세 추가 | `checks`: policy owner contact |
| Fallback Asset Usage (A5) | single | medium | fallbacks dict value + `asset_versions` alignment check | `recommended_actions`: re-publish asset |
| Data Reduction Spike (B1) | diff | medium | `len(candidate_refs)` vs `len(baseline_refs)` 20% threshold | diff view `References` toggles |
| Asset Version Drift (B2) | diff | high | strict version match, include `asset_id` list for quick inspect | `check`: `asset_registry` history |
| Plan Intent Shift (B3) | diff | medium | intent + output type change detection + `intent_confidence` track | `inspection`: highlight plan node |
| Tool Path Changes (B4) | diff | medium | tool addition/removal + `tool_call_index` detection | `<Evidence path>` includes step id |
| Tool Error Regression (B5) | diff | high | new metric `error_delta_ratio` + `ToolCall` summary | `recommended_actions`: service health focus |
| Performance Regression (B6) | diff | low | `duration` + `planner.error_rate` spikes | Low confidence note and `re-run` primer |
| No Data Ambiguity (B7) | diff | low | `No data` flagged only when both baseline & candidate > `row_count=0` | Recheck filter, `allowlist` |

모든 규칙은 `ExecutorResult`에 `runners`로 기록되며, `ReferenceItem`이 `trace.references`에 누적됩니다. `confidence`가 “low”인 rule은 RCA 캡션에 “(추적 확인 필요)”로 표시되고, `next_actions`에는 `re-run` 사전 정의 버튼이 추가됩니다.

## 3. False Positive / Low Confidence Controls

- **False positive rule**: `No Data Normal`과 `Data Reduction Spike`는 `trace.meta.sampling == "no_result"`일 때 Auto-suppress되어 overlap로 판단되는 경우 `confidence="low"`로 강제 downgrade.
- **Evidence density hint**: evidence path가 3개 미만이면 “Data 부족(low confidence)” 표시.
- **Auto `candidate_re-run` action**: `Tool duration spike` 이후 `Re-run with time_range=last_5m` action을 inspector context menu에 추가하여 실제 시간 변동을 재확인.

## 4. 실제 실패 trace 2건 RCA 결과

### Trace A: `trace-device-health-20261015-FAIL`
- **Golden Query**: GQ-001 Device Health Overview
- **Judgment**: FAIL (Tool Error Regression + Asset Version Drift)
- **Evidence**:
  1. `execution_steps[3].error.code=HTTP500` (Rule A1)
  2. `asset_versions["device-config"]=v2.1` vs baseline `v2.0` (Rule B2)
- **Inspector Path**: `Execution Steps > DeviceMetricsCall` → Evidence jump inspects `tool_call.output.error.message`
- **Checklist**:
  - [ ] API Token 유효성 확인
  - [ ] Asset Registry v2.1 배포 로그 확인
  - [ ] Tool dependency health 확인 (`tool_call.metrics.{duration}`)
- **Action**: Rollback asset to `v2.0` 또는 patch config, 이후 `Re-run Device Health Overview` manual 실행.

### Trace B: `trace-storage-latency-20261017-WARN`
- **Golden Query**: GQ-003 Storage Alert Latency
- **Judgment**: WARN (Performance Regression + Tool Duration Spike)
- **Evidence**:
  1. `candidate_duration=3120ms` vs baseline `980ms` (`Rule B6`)
  2. `execution_steps[1].duration_ms` tripled, `tool_call.retry=2` (`Rule A2`)
- **Inspector Path**: open `RegressionResultsView` → `View Evidence Path` → `execution_steps[1]` highlight.
- **Checklist**:
  - [ ] Backend API trace log latency per endpoint 확인
  - [ ] DB slow query log (Ops) 확인
  - [ ] regressed tool retry count 증가 여부
- **Action**: Increase cache TTL & monitor `tool_call.retry` or revert to `optimization` asset, tag RCA as WARN so automation queue triggers once `next_run` success.

## 5. Next Steps

1. RCA 결과 `Trace` 탭에서 “Evidence path”들을 inspector jump target으로 추가하고, `Trace` JSON에 `runners`/`tool_calls` summary를 더해 inspectable.
2. `docs/STEP6_RCA_ASSIST.md`에 실패 사례 요약 추가 (`Trace A/B`).
3. 다음 운영 회고(Ops Weekly)에서 RCA Rule v2를 검증하고 `confidence` 값을 조정합니다.
