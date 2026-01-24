# PRODUCT OVERVIEW

## Trace 기반 AI 운영 플랫폼이 필요한 이유
Trace는 AI가 결정한 모든 흐름, 도구 호출, 계획, 참조, UI 렌더 상태를 그대로 기록합니다. `Execution Trace`를 중심으로 운영이 설계되었기 때문에, 운영자는 “무엇이 변경되었는지”를 사람의 머리로 추론하지 않고도 정확히 파악할 수 있습니다. Regression Watch와 RCA Assist는 이 트레이스를 기준선과 비교하고, evidence path 중심의 RCA를 실행함으로써 “왜 FAIL인지”와 “다음 행동”을 즉시 안내합니다.

## 핵심 가치
- **Audit-friendly**: Trace / plan / tool call / reference를 모두 `tb_execution_trace`에 정량적으로 저장해 검색 가능하게 만들었고, 유지보수가 쉬운 JSON schema로 evidence path를 제공.
- **Deterministic 판단**: Golden Query + Baseline Trace + Regression Run → PASS/WARN/FAIL 판정의 이유를 `verdict_reason` 텍스트로 명시.
- **Actionable RCA**: RCA 루프는 오탐을 걷어내고 low confidence를 갱신하며, Evidence click → Inspector jump → checklist → Next action 흐름을 명확히 제공합니다.
- **Visibility-first**: Admin > Observability 탭에서 success/failure, tool latency(p50/p95), regression trend, RCA top causes, no-data ratio를 한번에 확인하여 “관리자가 즉시 판단/대응”할 수 있도록 합니다.

## 운영 흐름
1. **Flow 실행**: Inspector 또는 OPS/CI 질문을 통해 trace가 생성되고, Regression Watch Panel에서 trace history를 본다.
2. **Diff/Regression**: Regression run은 baseline과 비교해 PASS/WARN/FAIL을 판정하고, diff summary card를 통해 변화량을 시각화합니다.
3. **RCA**: Fail/Warn 발견 시 RCA Assist가 root cause candidate를 rank/ evidence로 정리하고, Evidence path click으로 Inspector deep dive.
4. **Action**: Checklist + Next action 버튼(예: rerun, rollback, policy review)으로 운영자가 즉시 후속 조치를 취함.

## 운영 결과
- 신규 인력도 문서만으로 `Golden Query`, `Baseline trace`, `Regression run`, `RCA evidence`를 따라가면서 문제를 판단할 수 있습니다.
- Regression/RCA가 일상화되어 watchdog 역할을 수행하고, Observability 탭이 KPI 모니터링을 담당합니다.
- Trace-based evidence를 중심으로 “Why FAIL인지”, “무엇을 고쳐야 하는지”, “다음 어떻게 실행할지”까지 설명 가능한 제품 상태를 유지합니다.
