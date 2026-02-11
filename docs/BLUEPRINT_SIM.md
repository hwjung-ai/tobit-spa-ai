# Simulation System Blueprint

**Last Updated**: 2026-02-11
**Version**: 1.0
**Status**: Production In Progress

---

## 1. 개요

Simulation System은 Tobit SPA AI의 메인 메뉴 `SIM`에서 제공되는 독립 시뮬레이션 모듈이다.
목표는 운영자가 질문과 가정값을 입력하면 KPI 변화, 신뢰도, 근거를 즉시 확인할 수 있게 하는 것이다.

핵심 원칙:

1. 실제 데이터 우선: mock 데이터 경로를 사용하지 않는다.
2. 멀티테넌트 격리: 사용자 tenant와 요청 tenant가 다르면 즉시 차단한다.
3. 표준 계약 준수: `ResponseEnvelope`, `ToolCall`, `ReferenceItem` 구조를 따른다.
4. 확장 가능 전략: Rule/Stat/ML/DL 전략 인터페이스를 공통화한다.

---

## 2. 범위

### 2.1 현재 구현 범위

1. SIM 전용 메인 라우트 `/sim` (Frontend)
2. SIM 전용 API `/sim/*` (Backend)
3. 전략 4종 실행
- `rule`
- `stat`
- `ml`
- `dl`
4. 토폴로지 시각화
- Neo4j 기반 노드/링크 조회
- 가정값 적용 후 상태 계산
5. 결과 패널
- KPI summary
- comparison charts
- algorithm & evidence
- backtest report
- CSV export

### 2.2 비범위(현재)

1. 학습 파이프라인 자동화(MLOps full stack)
2. 모델 재학습 스케줄러
3. CEP 자동 정책 반영

---

## 3. 아키텍처

### 3.1 전체 구조

```text
Frontend (/sim)
  -> SIM API Router (/sim/*)
    -> Planner + Validator
    -> Strategy Executor (rule/stat/ml/dl)
    -> Baseline Loader (Neo4j topology -> KPI derivation)
    -> Presenter (blocks/references)
    -> ResponseEnvelope
```

### 3.2 모듈별 파일

Backend:

1. Router
- `apps/api/app/modules/simulation/api/router.py`

2. Request/Response DTO
- `apps/api/app/modules/simulation/schemas.py`

3. 실행기
- `apps/api/app/modules/simulation/services/simulation/simulation_executor.py`

4. 베이스라인 로더
- `apps/api/app/modules/simulation/services/simulation/baseline_loader.py`

5. 전략 구현
- `apps/api/app/modules/simulation/services/simulation/strategies/rule_strategy.py`
- `apps/api/app/modules/simulation/services/simulation/strategies/stat_strategy.py`
- `apps/api/app/modules/simulation/services/simulation/strategies/ml_strategy.py`
- `apps/api/app/modules/simulation/services/simulation/strategies/dl_strategy.py`

6. 토폴로지 서비스
- `apps/api/app/modules/simulation/services/topology_service.py`

Frontend:

1. SIM 페이지
- `apps/web/src/app/sim/page.tsx`

2. 토폴로지 시각화
- `apps/web/src/components/simulation/TopologyMap.tsx`

3. 네비게이션
- `apps/web/src/components/NavTabs.tsx`
- `apps/web/src/components/MobileBottomNav.tsx`

---

## 4. 데이터 흐름

### 4.1 시뮬레이션 실행 흐름

1. 사용자 입력 수집
- question, scenario_type, strategy, assumptions, horizon, service

2. `/sim/query`
- planner가 `SimulationPlan` 생성

3. `/sim/run`
- baseline_loader가 Neo4j 토폴로지 기반 KPI baseline/scenario 계산
- 전략 실행기로 confidence/model_info 계산
- 결과를 실제 scenario KPI로 정렬
- tool_calls/references/blocks 생성

4. 프론트 렌더링
- KPI 카드, 차트, evidence, warnings, backtest 출력

### 4.2 토폴로지 흐름

1. `/sim/topology` 호출
2. 서비스 기준 그래프 로드
3. assumptions 적용 후 노드/링크 변화 계산
4. 상태 등급 계산
- `healthy`: < 70
- `warning`: >= 70
- `critical`: >= 90

---

## 5. API 계약

모든 JSON 응답은 `ResponseEnvelope` 구조를 따른다.

```json
{
  "time": "...",
  "code": 0,
  "message": "OK",
  "data": {}
}
```

### 5.1 Endpoints

1. `GET /sim/services`
- 설명: 서비스 목록
- 실패: 데이터 없으면 `404`

2. `GET /sim/templates`
- 설명: 시나리오 템플릿 목록

3. `POST /sim/query`
- 설명: 실행 계획 생성

4. `POST /sim/run`
- 설명: 전략 기반 시뮬레이션 실행
- 주요 반환:
- `simulation`
- `plan`
- `blocks`
- `references`
- `tool_calls`

5. `GET /sim/topology`
- query:
- `service` (required)
- `scenario_type` (optional)
- `traffic_change_pct`, `cpu_change_pct`, `memory_change_pct` (optional)

6. `POST /sim/backtest`
- 설명: 전략별 지표 반환
- 반환: `r2`, `mape`, `rmse`, `coverage_90`

7. `POST /sim/export`
- 설명: 실행 결과 CSV 반환
- content-type: `text/csv`

---

## 6. 보안 및 테넌시

1. 모든 엔드포인트는 `get_current_user`를 사용한다.
2. `current_user.tenant_id`와 `get_current_tenant`가 다르면 `403` 반환한다.
3. 데이터 조회는 tenant 기준으로 제한한다.
4. 인증 실패 시 프론트에서 오류 배너로 노출한다.

---

## 7. 알고리즘 계층

### 7.1 Strategy 계층 역할

1. `Rule`: 선형/임계 기반
2. `Stat`: EMA+회귀 계열 surrogate
3. `ML`: 비선형 surrogate
4. `DL`: 시퀀스형 surrogate

공통 출력:

1. KPI 리스트
2. confidence
3. model_info

### 7.2 Baseline/Scenario 정합성

최종 simulated KPI는 전략 출력값이 아니라 실제 topology 기반 scenario KPI로 정렬한다.

의미:

1. 해석 계층(전략 confidence)과 데이터 계층(실측 기반 파생 KPI)을 분리
2. mock 없이 실데이터 기반 결과 일관성 보장

---

## 8. UI 설계

### 8.1 레이아웃

1. 좌측 패널: 설정/실행 중심
2. 우측 패널: 결과/해석 중심

### 8.2 시각화

1. KPI 카드
2. Recharts 기반 비교 차트
3. SVG 기반 토폴로지 맵
4. Evidence JSON 패널

### 8.3 사용자 상호작용

1. 템플릿 선택
2. 가정값 슬라이더 조정
3. 전략 전환 재실행
4. 이전 실행 대비 비교
5. 백테스트/CSV 출력

---

## 9. 테스트 전략

### 9.1 Backend

1. `apps/api/tests/test_simulation_router.py`
2. `apps/api/tests/test_simulation_executor.py`
3. `apps/api/tests/test_simulation_rule_strategy.py`
4. `apps/api/tests/test_simulation_tenant_isolation.py`
5. `apps/api/tests/test_simulation_dl_strategy.py`

### 9.2 Frontend

1. `apps/web/tests-e2e/simulation.spec.ts`
2. `apps/web/src/app/sim/page.tsx` 대상 타입 검사

### 9.3 실행 명령

```bash
cd apps/api
pytest tests/test_simulation_router.py tests/test_simulation_executor.py tests/test_simulation_rule_strategy.py tests/test_simulation_tenant_isolation.py tests/test_simulation_dl_strategy.py -q
```

```bash
cd apps/web
npm run type-check
npx playwright test tests-e2e/simulation.spec.ts
```

---

## 10. 운영 리스크와 대응

1. Neo4j 데이터 공백
- 증상: `/sim/services` 404
- 대응: topology ingest 점검

2. 과도한 가정값 입력
- 증상: 경고 증가, 오차 확대
- 대응: warning 기반 가드레일 UI 안내

3. 전략 신뢰도 과신
- 증상: 고신뢰 전략에만 편향
- 대응: backtest 지표 병행 확인 강제 운영 가이드 적용

---

## 11. 향후 확장

1. 시나리오 저장/버전 관리
2. 멀티 시나리오 배치 비교
3. CEP 정책 추천 연동
4. 모델 레지스트리와 학습 이력 추적
5. Screen Asset 기반 맞춤 시뮬레이션 대시보드

---

## 12. 관련 문서

1. `docs/USER_GUIDE_SIM.md`
2. `docs/SIMULATION_IMPLEMENTATION_GUIDE.md`
3. `docs/FEATURES.md`
4. `docs/SIMULATION_BENCHMARK_ANALYSIS.md`
