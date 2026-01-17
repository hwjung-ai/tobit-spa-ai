# Observability Dashboard

Admin > Observability 탭은 D4 요구를 충족하는 대시보드 UI 및 KPI 정의를 하나의 문서로 설명합니다. 이 탭은 기존 `tb_execution_trace`/`tb_regression_run` 테이블만 사용하며 새로운 핵심 테이블을 만들지 않습니다.

## 1. UI 구성 (`apps/web/src/components/admin/ObservabilityDashboard.tsx`)

1. **헤더 카드**: `Observability` 타이틀과 “realtime” 뱃지를 배치하여 운영자가 현재 모니터링 중임을 인지.
2. **상단 요약 그리드**: Success Rate, Failure Rate, No-data Ratio, 24h Request Count 4개의 카드로 운영 KPI를 한눈에 보여줌.
3. **Latency & Tool Health**: 최근 24시간 trace duration을 기준으로 p50/p95 latency를 별도 카드로 정리하여 tool latency(P50/P95) 요구사항 충족.
4. **Regression trend**: 최근 7일 동안 PASS/WARN/FAIL 추이를 날짜별로 나열, FAIL/WARN focus 태그로 우선 순위 강조.
5. **Regression breakdown + RCA Top Causes**: PASS/WARN/FAIL 누적 수치와 함께 `verdict_reason` 기반 상위 원인 5개를 리스트로 제공.

탭은 `apps/web/src/app/admin/layout.tsx`의 네비게이션에 “Observability” 항목으로 추가되며, `apps/web/src/app/admin/observability/page.tsx`에서 위 컴포넌트를 렌더링합니다.

## 2. KPI 정의

| KPI | 정의 | 소스 |
|-----|------|------|
| Success Rate | 최근 24시간(trace.created_at >= now() - 24h) `status == "success"` 비율 | `tb_execution_trace` |
| Failure Rate | Success Rate의 보완(1 - Success Rate) | `tb_execution_trace` |
| Requests (24h) | 최근 24시간 전체 trace 카운트 | `tb_execution_trace` |
| Latency (p50/p95) | 최근 24시간 trace duration_ms의 50th/95th percentile | `tb_execution_trace.duration_ms` |
| Regression Trend | 최근 7일 `tb_regression_run`의 PASS/WARN/FAIL 수치 (날짜별) | `tb_regression_run.judgment`, `created_at` |
| Regression Breakdown | 최근 7일 누적 PASS/WARN/FAIL | same |
| RCA Top Causes | 최신 Regression runs에서 `verdict_reason`을 집계한 상위 5개 | `tb_regression_run.verdict_reason` |
| Data 없음 비율 | 최신 500개 trace의 `answer.meta.summary`에 “no data” 포함 비율 | `tb_execution_trace.answer` |

모든 KPI는 `apps/api/app/modules/ops/services/observability_service.py`에서 집계되며, `/ops/observability/kpis` 엔드포인트(ResponseEnvelope)로 프론트엔드에 전달됩니다.

## 3. KPI 소비 방식

- Observability 탭은 **Dashboard 레벨** UX로서, Regression Watch Panel과 RCA Assist에 앞서 상위 상태를 빠르게 파악합니다.
- **FAIL/WARN 트렌드**: 빠른 의사결정을 돕기 위해 trend 리스트에서 즉시 `PASS`와 `FAIL` 항목을 비교하고, `Regression breakdown` 카드에서 RCA Top Causes를 기반으로 더 깊은 분석(RCA Assist)을 연결합니다.
- **Latency 포커스**: 실시간 latency spike는 `p50/p95` 수치 변화로 포착되며, Regression FAIL/WARN이 동시에 증가하면 `Observability` → `Regression` 탭으로 이동하여 diff + trace 분석을 수행합니다.

## 4. 검증 체크리스트

1. `/ops/observability/kpis`를 호출하고 `code == 0`, `data.kpis`가 존재하는지 확인.
2. Admin > Observability UI 접근 → 값이 로딩되는지 확인(로딩 스피너 대신 텍스트).
3. Regression trend/ breakdown 데이터가 `tb_regression_run`과 일치하는지 DB 조회로 검산.
4. No-data ratio 계산은 최근 500개 trace에서 “no data” summary를 가진 항목을 수기로 확인하여 ±2% 내로 일치하는지 검증.

## 5. 다음 개선 포인트

1. 향후 `trace.references`나 `execution_steps`에 대한 더 정교한 latency 분석(도구별 p50/p95)을 추가할 수 있습니다.
2. RCA Top Causes를 `Confidence`/`Rule ID`와 함께 제공하면 Observability → RCA Assist 흐름이 더 명확해집니다.
