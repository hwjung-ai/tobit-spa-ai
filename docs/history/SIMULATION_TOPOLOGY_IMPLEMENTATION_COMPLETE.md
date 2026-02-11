# 시뮬레이션 토폴로지 맵 - 구현 완료 보고서

**작성일**: 2026-02-10  
**버전**: v1.0

---

## 1. 개요

시뮬레이션(SIM) 페이지에 토폴로지 맵 기능을 구현하여 사용자가 시스템 의존성을 시각적으로 확인하고, What-If 시뮬레이션을 통해 트래픽/부하 변화의 영향을 미리 파악할 수 있습니다.

### 1.1 구현 범위

| 기능 | 구현 여부 | 설명 |
|------|----------|------|
| 토폴로지 맵 시각화 | ✅ | SVG 기반 대화형 토폴로지 맵 |
| 노드 색상 표시 | ✅ | 상태별 색상 (healthy: 파랑, warning: 노랑, critical: 빨강) |
| 링크 트래픽 표시 | ✅ | 링크 라벨로 기본/시뮬레이션 트래픽 표시 |
| 토폴로지 노출/숨기기 | ✅ | 버튼으로 토폴로지 맵 토글 |
| What-If 시나리오 | ✅ | 트래픽/CPU/메모리 변화 가정 및 시뮬레이션 |
| Neo4j 실제 데이터 조회 | ✅ | SIM_MODE 환경변수로 Mock/Real 모드 지원 |
| 시드 데이터 스크립트 | ✅ | Neo4j 토폴로지 데이터 생성 스크립트 |

---

## 2. 벤치마크 분석 결과

### 2.1 대상 시스템

| 시스템 | 주요 특징 | 벤치마킹 포인트 |
|--------|-----------|----------------|
| Renobit (국내) | L3/2/1 스위치, 포트, 업링크 표시 | 물리적 네트워크 토폴로지 표현 |
| Dynatrace | 자동 토폴로지 맵, Smartscape | 서비스 의존성 자동 생성 |
| New Relic | 분산 추적, 서비스 맵 | 마이크로서비스 간 호출 관계 |
| Splunk | ITSI, 네트워크 토폴로지 | 통합 모니터링 대시보드 |

### 2.2 주요 차별점

- **Renobit**: 하드웨어 중심, 포트 단위 토폴로지
- **Tobit SPA AI**: 소프트웨어 서비스 중심, 의존성 기반 시뮬레이션

---

## 3. 구현 내용

### 3.1 백엔드

#### 3.1.1 API 엔드포인트

```python
# apps/api/app/modules/simulation/router.py
@router.get("/sim/topology")
async def get_topology(
    service: str,
    scenario_type: str = "what_if",
    traffic_change_pct: float = 0,
    cpu_change_pct: float = 0,
    memory_change_pct: float = 0
)
```

**응답 형식**:
```json
{
  "nodes": [
    {
      "id": "api-gateway",
      "name": "API Gateway",
      "type": "service",
      "status": "warning",
      "baseline_load": 45.0,
      "simulated_load": 54.0,
      "load_change_pct": 20.0
    }
  ],
  "links": [
    {
      "source": "loadbalancer",
      "target": "api-gateway",
      "type": "traffic",
      "baseline_traffic": 1000.0,
      "simulated_traffic": 1200.0,
      "traffic_change_pct": 20.0
    }
  ]
}
```

#### 3.1.2 토폴로지 서비스

**파일**: `apps/api/app/modules/simulation/services/topology_service.py`

**주요 기능**:
- `_fetch_neo4j_topology()`: Neo4j에서 토폴로지 조회
  - `SIM_MODE=mock`: 가상 데이터 반환
  - `SIM_MODE=real`: Neo4j 실제 데이터 조회
- `_apply_simulation()`: What-If 시뮬레이션 적용
  - 노드 타입별 영향도 계산
  - 상태 판단 (healthy/warning/critical)
  - 변화율 계산

**Neo4j 쿼리**:
```cypher
MATCH path = (s {name: $service, tenant_id: $tenant_id})<-[:DEPENDS_ON*0..5|HOSTS*0..5|TRAFFIC*0..5]-(n)
WITH s, n, path
WITH s, collect(DISTINCT n) AS all_nodes
UNWIND all_nodes AS n1
UNWIND all_nodes AS n2
WITH n1, n2
WHERE n1 <> n2
MATCH (n1)-[r:DEPENDS_ON|HOSTS|TRAFFIC]->(n2)
RETURN collect(DISTINCT {id, name, type, baseline_load}) AS nodes,
       collect(DISTINCT {source, target, type, baseline_traffic}) AS links
```

#### 3.1.3 시드 데이터 스크립트

**파일**: `apps/api/scripts/seed_topology_data.py`

**사용법**:
```bash
cd apps/api
python scripts/seed_topology_data.py --tenant-id t1
```

**데이터 구조**:
- 노드: 7개 (Load Balancer, API Gateway, Web Server, App Service, Redis, PostgreSQL, NFS)
- 관계: 8개 (DEPENDS_ON, HOSTS, TRAFFIC)

---

### 3.2 프론트엔드

#### 3.2.1 토폴로지 맵 컴포넌트

**파일**: `apps/web/src/components/simulation/TopologyMap.tsx`

**주요 기능**:
- SVG 기반 대화형 토폴로지 맵
- 노드 상태별 색상 표시
- 링크 트래픽 라벨
- 자동 레이아웃 (계층형)
- 확대/축소 지준비

**노드 타입별 아이콘**:
- `service`: 📦 (큐브)
- `server`: 🖥️ (서버)
- `db`: 🗄️ (데이터베이스)
- `network`: 🌐 (네트워크)
- `storage`: 💾 (스토리지)

#### 3.2.2 SIM 페이지 통합

**파일**: `apps/web/src/app/sim/page.tsx`

**추가된 기능**:
- 토폴로지 맵 노출/숨기기 버튼
- What-If 시나리오 설정
- 시뮬레이션 결과 테이블

---

## 4. Neo4j 데이터 구조

### 4.1 노드 속성

| 속성 | 타입 | 필수 | 설명 |
|-------|-------|--------|------|
| `name` | String | ✅ | 컴포넌트 이름 |
| `type` | String | ✅ | service/server/db/network/storage |
| `baseline_load` | Float | ✅ | 기본 부하율 (0.0 ~ 100.0) |
| `tenant_id` | String | ✅ | 테넌트 ID |

### 4.2 관계 타입

| 관계 | 방향 | 속성 | 설명 |
|------|--------|------|------|
| `DEPENDS_ON` | A → B | `baseline_traffic` | A가 B에 의존 |
| `HOSTS` | A → B | `baseline_traffic` | A가 B를 호스팅 |
| `TRAFFIC` | A → B | `baseline_traffic` | A에서 B로 트래픽 흐름 |

### 4.3 데이터 생성 예시

```cypher
// 노드 생성
CREATE (lb:Network {name: "loadbalancer", type: "network", baseline_load: 50.0, tenant_id: "t1"})
CREATE (gw:Service {name: "api-gateway", type: "service", baseline_load: 45.0, tenant_id: "t1"})

// 관계 생성
MATCH (lb:Network {name: "loadbalancer", tenant_id: "t1"})
MATCH (gw:Service {name: "api-gateway", tenant_id: "t1"})
MERGE (lb)-[:TRAFFIC {baseline_traffic: 1000.0}]->(gw)
```

---

## 5. 환경 설정

### 5.1 .env 설정

```bash
# 시뮬레이션 모드 설정
SIM_MODE=mock  # mock: 가상 데이터, real: Neo4j 실제 데이터

# Neo4j 연결 (SIM_MODE=real인 경우 필수)
NEO4J_URI=neo4j://YOUR_NEO4J_HOST:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secret
```

### 5.2 시드 데이터 실행

```bash
cd apps/api
python scripts/seed_topology_data.py --tenant-id t1
```

---

## 6. 사용 방법

### 6.1 Mock 모드 (개발/테스트)

1. `.env` 설정: `SIM_MODE=mock`
2. SIM 페이지 접속: `http://localhost:3000/sim`
3. 토폴로지 맵 노출 버튼 클릭
4. 시나리오 설정 (트래픽/CPU/메모리 변화)
5. 시뮬레이션 실행 및 결과 확인

### 6.2 Real 모드 (운영)

1. `.env` 설정: `SIM_MODE=real`
2. Neo4j 연결 설정 (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
3. 시드 데이터 실행: `python scripts/seed_topology_data.py --tenant-id t1`
4. SIM 페이지 접속 및 Mock 모드와 동일하게 사용

---

## 7. 테스트

### 7.1 백엔드 테스트

```bash
# Mock 모드 테스트
curl "http://localhost:8000/api/sim/topology?service=api-gateway&traffic_change_pct=20&cpu_change_pct=10"

# Real 모드 테스트 (Neo4j 데이터 필요)
# .env 설정: SIM_MODE=real
curl "http://localhost:8000/api/sim/topology?service=api-gateway&traffic_change_pct=20&cpu_change_pct=10"
```

### 7.2 프론트엔드 테스트

```bash
cd apps/web
npm run dev
# 브라우저에서 http://localhost:3000/sim 접속
# 토폴로지 맵 노출/숨기기 기능 확인
# 시나리오 설정 및 시뮬레이션 확인
```

---

## 8. 향후 개선 사항

### 8.1 단기 개선

- [ ] Neo4j 데이터 실시간 동기화 (TIM+ 연동)
- [ ] 토폴로지 맵 필터링 기능 (상태별, 타입별)
- [ ] 링크 애니메이션 (트래픽 흐름 표현)
- [ ] 드래그 앤 드롭으로 노드 위치 조정
- [ ] 노드 상세 정보 팝업

### 8.2 중기 개선

- [ ] 토폴로지 맵 다운로드 (PNG/SVG)
- [ ] 공유 링크 생성
- [ ] 복수 시나리오 비교
- [ ] 경로 탐색 기능 (최단 경로, 장애 영향 분석)

### 8.3 장기 개선

- [ ] AI 기반 토폴로지 추천
- [ ] 예측 시뮬레이션 (ML 모델 기반)
- [ ] 물리적 토폴로지 매핑 (Renobit 스타일)
- [ ] 포트 단위 상세 토폴로지

---

## 9. 관련 문서

- [시뮬레이션 토폴로지 - Neo4j 데이터 구조 가이드](./SIMULATION_TOPOLOGY_NEO4J_SCHEMA.md)
- [벤치마킹 분석 보고서](./BENCHMARK_ANALYSIS.md)
- [TIM+ 연동 가이드](./USER_GUIDE_CEP.md)

---

## 10. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0 | 2026-02-10 | 초기 구현 완료 | AI Agent |