# 6-Month Roadmap

이 로드맵은 Trace 기반 운영 루프(D1~D4)의 다음 진화를 6개월 단위로 나열합니다. 각 항목은 운영자가 Inspector만으로 판단/대응할 수 있도록 하는 것을 목표로 합니다.

| Month | Focus | Deliverables |
|-------|-------|--------------|
| 1 | Observability release | Admin > Observability 탭: 성공/실패율, latency(p50/p95), regression trend, RCA top causes, no-data ratio. `/ops/observability/kpis` API 검증. |
| 2 | Regression automation | Golden Query onboarding flow, baseline auto-capture from warm traces, scheduled regression runner, PASS/WARN/FAIL notification hooks (Slack/email). |
| 3 | RCA fidelity | RCA Rule v2 roll-out, evidence path improvements, false-positive suppression, RCA checklist enrichment, inspectable `confidence` tags in UI. |
| 4 | Incident playbooks | Playbooks (답 이상, 데이터 없음, tool timeout, 5xx, auth, asset regression, UI error, trace missing) 정식화 + Playbook search in Admin. |
| 5 | Operator toolkit | Trace bookmarks, Evidence snapshot exports, Observability → Regression cross-links, RCA report templates for retrospectives. |
| 6 | Scale & enablement | On-call runbooks, runtime telemetry (tool latency breakdown), training doc + product positioning “Trace-based AI Ops” for new hires. |

**KPI checkpoints**
- Monthly: Regression PASS ≥ 95%, WARN/FAIL ratio trending downward.
- Weekly: Observability tab error rate < 1%, RCA top causes stabilized (Major cause < 3 unique reasons).
- Quarterly: New hire onboarding doc ready with `PRODUCT_OVERVIEW.md`, `DEMO_SCENARIOS.md`, `OPERATIONS_PLAYBOOK.md`.
