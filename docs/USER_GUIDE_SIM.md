# SIM Workspace 사용자 가이드

> 최종 업데이트: 2026-02-11
> 대상: 운영자, SRE, 서비스 담당자

## 1. 문서 목적

이 문서는 `/sim` 메뉴에서 제공하는 시뮬레이션 기능을 실제 운영에 사용하는 방법을 안내한다.
핵심은 다음 세 가지다.

1. 질문과 가정값(What-if)을 기반으로 KPI 변화를 예측한다.
2. 결과를 차트/토폴로지/근거로 함께 해석한다.
3. 전략(Rule/Stat/ML/DL)을 비교하고 백테스트로 신뢰도를 확인한다.

---

## 2. 시작 전 체크

1. 로그인 상태여야 한다.
2. 요청 헤더의 `x-tenant-id`와 로그인 사용자 `tenant_id`가 일치해야 한다.
3. Neo4j에 서비스 토폴로지 데이터가 있어야 한다.
4. 서비스 목록은 `/api/sim/services`에서 조회되며, 데이터가 없으면 SIM 실행이 불가능하다.

---

## 3. 화면 구성

SIM 페이지는 좌측 빌더 + 우측 결과 영역으로 구성된다.

### 좌측: Scenario Builder

1. `질문` 입력
2. `템플릿` 선택 (초기값 빠른 적용)
3. `시나리오 타입` 선택 (`what_if`, `stress_test`, `capacity`)
4. `Service` 선택 (토폴로지 기반)
5. `Horizon` 입력 (`7d`, `30d` 등)
6. `가정값` 슬라이더 조정
   - `traffic_change_pct`
   - `cpu_change_pct`
   - `memory_change_pct`
7. `전략` 선택
   - `rule`: 수식 기반
   - `stat`: 통계 기반
   - `ml`: ML surrogate
   - `dl`: DL surrogate
8. 실행 버튼
   - `Run Simulation`
   - `Run Backtest`
   - `Export CSV`

### 우측: 결과/해석

1. `KPI Summary`
   - baseline vs simulated
   - change %
   - confidence, confidence interval, error bound
2. `Comparison Charts`
   - baseline vs simulated 라인 차트
   - change% 바 차트
   - 이전 실행 대비 비교 차트
3. `System Topology Map`
   - 노드 상태(healthy/warning/critical)
   - 링크 변화(traffic/dependency)
   - 노드 클릭 시 상세 정보
4. `Algorithm & Evidence`
   - 전략 설명
   - 모델 정보
   - 추천 액션
   - references(JSON)
5. `Backtest Report`
   - R2, MAPE, RMSE, Coverage@90

---

## 4. 기본 사용 절차

1. `/sim`으로 이동한다.
2. 템플릿 하나를 선택해 기본 질문/가정값을 채운다.
3. 대상 `Service`와 `전략`을 선택한다.
4. `Run Simulation`을 실행한다.
5. 우측에서 KPI, 차트, 토폴로지, 근거를 확인한다.
6. 필요 시 가정값 또는 전략을 바꿔 재실행한다.
7. `Run Backtest`로 전략 성능 지표를 확인한다.
8. `Export CSV`로 결과를 저장/공유한다.

권장 패턴:
- 같은 질문으로 `rule -> stat -> ml` 순서로 비교하면 해석성과 정확도 균형을 잡기 쉽다.

---

## 5. 전략 선택 가이드

1. `rule`
- 정책 설명 가능성이 가장 중요할 때 사용
- 초기 운영 규칙 검증에 적합

2. `stat`
- 노이즈가 있는 시계열을 안정적으로 보고 싶을 때 사용
- rule 대비 과도한 민감도를 줄일 수 있다

3. `ml`
- 상호작용이 복잡한 KPI에서 사용
- 성능 중심 시나리오 비교에 유리

4. `dl`
- 시퀀스 패턴 영향이 큰 경우 사용
- 계산/해석 비용이 크므로 후보 전략 좁힌 뒤 적용 권장

---

## 6. 주요 API

모든 SIM API는 인증과 tenant 검증을 거친다.

1. `GET /api/sim/services`
- 실행 가능한 서비스 목록 조회

2. `GET /api/sim/templates`
- 시나리오 템플릿 조회

3. `POST /api/sim/query`
- 질문 기반 실행 계획(Plan) 생성

4. `POST /api/sim/run`
- 시뮬레이션 실행
- 결과: `simulation`, `plan`, `blocks`, `references`, `tool_calls`

5. `GET /api/sim/topology?service=...&scenario_type=...`
- 토폴로지 기반 노드/링크 시뮬레이션 데이터

6. `POST /api/sim/backtest`
- 전략별 성능 지표 반환

7. `POST /api/sim/export`
- CSV 반환 (`text/csv`)

---

## 7. 오류 대응

1. `403 Tenant mismatch`
- 원인: 로그인 사용자 테넌트와 요청 테넌트 불일치
- 조치: 프론트 헤더 `x-tenant-id`와 사용자 세션 테넌트 정합 확인

2. `404 No simulation services found in topology data`
- 원인: Neo4j에 서비스 노드가 없거나 tenant 데이터 미존재
- 조치: 토폴로지 적재 상태 확인

3. `404 No topology data found for service=...`
- 원인: 선택한 서비스의 그래프 데이터 없음
- 조치: 서비스 선택 변경 또는 데이터 적재

4. `400 Invalid numeric assumption`
- 원인: assumption 파라미터 형식 오류
- 조치: 숫자형 입력만 전달

---

## 8. 운영 체크리스트

- [ ] `/api/sim/services` 호출 성공
- [ ] 기본 서비스로 첫 실행 성공
- [ ] KPI Summary/차트/Topology/Evidence 표시 확인
- [ ] `Run Backtest` 지표 확인
- [ ] `Export CSV` 파일 다운로드 확인
- [ ] tenant mismatch 시 403 반환 확인

---

## 9. 테스트 가이드

Backend:

```bash
cd apps/api
pytest tests/test_simulation_router.py tests/test_simulation_executor.py tests/test_simulation_rule_strategy.py tests/test_simulation_tenant_isolation.py tests/test_simulation_dl_strategy.py -q
```

Frontend Type Check:

```bash
cd apps/web
npm run type-check
```

Frontend E2E:

```bash
cd apps/web
npx playwright test tests-e2e/simulation.spec.ts
```

---

## 10. 관련 문서

1. `docs/BLUEPRINT_SIM.md`
2. `docs/history/SIMULATION_IMPLEMENTATION_GUIDE.md`
3. `docs/FEATURES.md`

---

## 11. 운영 시나리오 예시

### 11.1 용량 계획 (Capacity Planning)

권장 입력:
1. 시나리오 타입: `capacity`
2. 서비스: 핵심 트랜잭션 서비스 (예: `order-service`)
3. 가정값: `traffic +80%`, `cpu +50%`, `memory +30%`
4. 전략: `ml`

확인 포인트:
1. `Topology Map`에서 `critical` 노드 발생 여부
2. `KPI Summary`에서 임계치 초과 가능성
3. `Algorithm & Evidence`의 권장 액션

### 11.2 장애 대응 (Stress Test)

권장 입력:
1. 시나리오 타입: `stress_test`
2. 서비스: 진입점 서비스 (예: `api-gateway`)
3. 가정값: `traffic +150%`, `cpu +100%`, `memory +80%`
4. 전략: `rule`

확인 포인트:
1. 연쇄 영향 경로(업스트림/다운스트림) 확인
2. 경고 메시지와 위험 노드 우선순위 확인
3. 즉시 대응 항목(스케일아웃/스로틀링) 도출

### 11.3 최적화 효과 검증 (What-if)

권장 입력:
1. 시나리오 타입: `what_if`
2. 서비스: 최적화 대상 서비스
3. 가정값: `cpu -30%`, `memory -20%`
4. 전략: `stat`

확인 포인트:
1. 이전 실행 대비 개선 폭(`Previous vs Current`)
2. `confidence` 상승 여부
3. 백테스트 지표(`MAPE`, `RMSE`) 개선 여부

---

## 12. 개발자 확장 포인트

1. 템플릿 확장: `apps/api/app/modules/simulation/services/simulation/scenario_templates.py`
2. 전략 확장: `apps/api/app/modules/simulation/services/simulation/strategies/`
3. 결과 렌더링 확장: `apps/api/app/modules/simulation/services/simulation/presenter.py`
4. 화면 확장: `apps/web/src/app/sim/page.tsx`
