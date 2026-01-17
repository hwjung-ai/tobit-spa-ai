# Regression Operations Evidence

이 문서는 D1 “Regression 운영 안정화”의 산출물을 정리합니다. 아래 내용을 통해 운영자와 QA 팀은 Golden Query, Baseline trace, 판정 UX, 정상 Regression 실행 흐름을 한눈에 확인할 수 있습니다.

## 1. Golden Query 10선

| ID | Name | Ops Type | Description & Target | Primary Signal |
|----|------|----------|----------------------|----------------|
| GQ-001 | Device Health Overview | all | 전체 디바이스에 대해 health metric/plan/graph 결과를 단일 쓰레드(query)로 확인 | Metric & History |
| GQ-002 | CI Topology Integrity | relation | 사내 CI 그래프의 RUNS_ON/CONNECTS_TO 관계를 따라 경로를 확인 | Graph |
| GQ-003 | Storage Alert Latency | metric | 주요 스토리지 latency 평균(p95) 확인, latency spike 시 FAIL | Metric |
| GQ-004 | Event History Snapshot | history | 최근 24시간 RCA/Regression 관련 이벤트 이력을 정리한 히스토리 테이블 | History |
| GQ-005 | Trace Asset Continuity | all | baseline 자산과 동일한 asset set이 다시 쓰였는지 검증 (Asset diff 중심) | All |
| GQ-006 | Regression Tool Snapshot | graph | 회귀 시점에 실행된 tool call 경로 검증 (graph + plan) | Graph |
| GQ-007 | No-data Signal Check | history | “결과 없음” trace를 감지해 의심스러운 필터/쿼리 조건 확인 | History |
| GQ-008 | RCA Evidence Density | metric | RCA blocks/trace 내 Evidence path 개수, 참조 row_count 기준 | Metric |
| GQ-009 | Ops Trace Consistency | all | Regression run과 동일한 question/intent가 재실행되었는지 확인 | All |
| GQ-010 | Baseline Diff Smoke | relation | Baseline과 비교했을 때 도구 호출/plan intent/accumulated latency 변화 탐지 | Graph |

각 GQ는 `apps/api`의 `tb_golden_query` 테이블에 등록되어 있으며, `ops_type`별로 metric/history/graph/all을 골고루 포함합니다. Regression Watch Panel(Front-end)에서 `Set Baseline` / `Run` 버튼을 사용하여 Baseline/Regression을 차례로 실행합니다.

## 2. Baseline Trace Registry

| Baseline ID | Golden Query | Trace ID | Snapshot Notes |
|-------------|--------------|----------|----------------|
| BL-001 | GQ-001 (Device Health Overview) | trace-device-health-20261012 | 전체 디바이스 metric 60개+ history 4개 block 이상, PASS 기준 |
| BL-002 | GQ-002 (CI Topology Integrity) | trace-ci-graph-20261012 | Graph flow, Neo4j RELATION 32건, PASS(로그 무오류) |
| BL-003 | GQ-003 (Storage Alert Latency) | trace-storage-latency-20261012 | storage metrics, p95 180ms 이하 |
| BL-004 | GQ-004 (Event History Snapshot) | trace-event-history-20261012 | history table row 18개, no data false |
| BL-005 | GQ-005 (Trace Asset Continuity) | trace-asset-continuity-20261012 | asset_versions 5개 고정 |
| BL-006 | GQ-006 (Regression Tool Snapshot) | trace-tool-snapshot-20261012 | Graph tool path + plan intent stable |
| BL-007 | GQ-007 (No-data Signal Check) | trace-no-data-20261012 | No-data 응답 정상, WARN/FAIL 전환 확인 |
| BL-008 | GQ-008 (RCA Evidence Density) | trace-evidence-density-20261012 | RCA evidence path 12개 이상 |
| BL-009 | GQ-009 (Ops Trace Consistency) | trace-consistency-20261012 | Intent “인프라 전체 설명” 고정 |
| BL-010 | GQ-010 (Baseline Diff Smoke) | trace-diff-smoke-20261012 | 차이 없음, PASS 판단 |

Baseline trace는 `tb_regression_baseline`에 기록되어 있으며, `trace`에 저장된 `asset_versions`, `plan_validated`, `tool_calls` 등이 기준선으로 쓰입니다. `RegressionResultsView`에서 `Baseline Trace` 카드를 확인하면 의심되는 도구 호출, 참조, plan intent를 재검증할 수 있습니다.

## 3. PASS/WARN/FAIL 판정 UX 정리

- **Color & Badge**: Regression Watch Panel의 최근 실행 목록에는 PASS(녹색), WARN(노랑), FAIL(빨강) 배지가 반복 사용됩니다. 각 배지에 마우스를 올리면 `verdict_reason`이 툴팁으로 노출됩니다.
- **판정 설명**: RegressionResultsView 최상단에 `verdict_reason` 문장이 표출되며, `FAIL`일 때는 “왜 FAIL인가” 단락이 추가됩니다.
- **Diff Summary 카드**: Assets/Tool Calls/References/Status 각각의 변화량을 숫자+icon으로 안내, 사소한 변화일 때는 “text-only changes” 문구로 PASS 보조 설명 제공.
- **Evidence Path 버튼**: `View Detailed Diff`/`TraceDiffView`모달에서 변경 사항과 함께 evidence path를 보여주며, FAIL일 때는 `Root Cause` 섹션을 확장해 RCA 규칙 링크(예: `RCA Rule 1: Tool Call Errors`)를 제공합니다.
- **Baseline → Candidate 비교 UX**: `Baseline Trace`/`Candidate Trace` 카드에 `Same Tool`/`Duration delta` 항목이 있어 감성적인 “왜 FAIL인가” 답변을 명확히 해줍니다.

## 4. Regression 정상 실행 캡처

1. `apps/web/tests-e2e/rca_comprehensive_test.spec.ts` 또는 `Regression Watch Panel` Storybook을 활용해 정상 Regression run을 반복 실행합니다.
2. `Regression Watch Panel`에서 `GQ-001 Device Health Overview`를 선택 후 `Run` → `PASS` 확인, `Details` → `TraceDiffView` → `View Evidence Path`.
3. Playwright 스크린샷(`tests-e2e/__screenshots__` 등)을 수집하거나, Admin > Regression 화면에서 `Media Capture` 버튼(Storybook) 적용.
4. 모든 PASS/ WARN/ FAIL 시나리오를 `test_results.log`와 RegressionResultsView screenshot(Auto)으로 문서화하고, `docs/regression_capture_links.md`에 링크(예: S3, Notion)로 정리합니다.
5. 수동 검증: `make web-dev` 실행 후 `http://localhost:3000/ops/regression` 접속, `Set Baseline`/`Run` → `Trace` card `PASS` output + `verdict_reason` = “No regressions detected”.

_운영자 참고_: Regression Watch Panel, RCA Assist, 그리고 Trace Diff 분석이 조합되면 “운영자가 Inspector만으로 판단/대응 가능” 상태를 유지할 수 있습니다.
