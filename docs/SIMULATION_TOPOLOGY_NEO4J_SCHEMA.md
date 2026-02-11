# 시뮬레이션 토폴로지 - Neo4j 데이터 구조 가이드

**작성일**: 2026-02-10  
**버전**: v1.0

---

## 1. 개요

이 문서는 시뮬레이션 토폴로지 맵 기능에 필요한 Neo4j 데이터 구조를 정의합니다.

### 1.1 환경 설정

`.env` 파일에서 시뮬레이션 모드를 설정하세요:

```bash
# Mock 모드: 가상 데이터 사용 (개발/테스트용)
SIM_MODE=mock

# Real 모드: Neo4j 실제 데이터 조회 (운영용)
SIM_MODE=real
```

---

## 2. Neo4j 노드 구조

### 2.1 노드 속성

| 속성 | 타입 | 필수 | 설명 |
|-------|-------|--------|------|
| `name` | String | ✅ | 컴포넌트 이름 (예: "api-gateway", "web-server") |
| `type` | String | ✅ | 컴포넌트 타입 (service, server, db, network, storage) |
| `baseline_load` | Float | ✅ | 기본 부하율 (0.0 ~ 100.0) |
| `tenant_id` | String | ✅ | 테넌트 ID (다중 테넌트 지원) |

### 2.2 노드 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| `service` | 마이크로서비스, API 서비스 | API Gateway, App Service |
| `server` | 물리/가상 서버 | Web Server, App Server |
| `db` | 데이터베이스 | Redis Cache, PostgreSQL DB |
| `network` | 네트워크 컴포넌트 | Load Balancer, Router |
| `storage` | 스토리지 | NFS Storage, S3 Bucket |

---

## 3. Neo4j 관계 구조

### 3.1 관계 타입

| 관계 | 방향 | 설명 | 속성 |
|------|--------|------|------|
| `DEPENDS_ON` | A → B | A가 B에 의존 | `baseline_traffic` |
| `HOSTS` | A → B | A가 B를 호스팅 | `baseline_traffic` |
| `TRAFFIC` | A → B | A에서 B로 트래픽 흐름 | `baseline_traffic` |

### 3.2 관계 속성

| 속성 | 타입 | 필수 | 설명 |
|-------|-------|--------|------|
| `baseline_traffic` | Float | ✅ | 기본 트래픽 (단위: req/s) |

---

## 4. Neo4j 데이터 생성 예시

### 4.1 Cypher 쿼리 (시드 데이터)

```cypher
// 테넌트 설정
WITH "t1" AS tenant_id

// 노드 생성
CREATE (lb:Network {name: "loadbalancer", type: "network", baseline_load: 50.0, tenant_id: tenant_id})
CREATE (gw:Service {name: "api-gateway", type: "service", baseline_load: 45.0, tenant_id: tenant_id})
CREATE (ws:Server {name: "web-server", type: "server", baseline_load: 60.0, tenant_id: tenant_id})
CREATE (asv:Service {name: "app-service", type: "service", baseline_load: 55.0, tenant_id: tenant_id})
CREATE (redis:Db {name: "cache-redis", type: "db", baseline_load: 30.0, tenant_id: tenant_id})
CREATE (pg:Db {name: "db-postgres", type: "db", baseline_load: 65.0, tenant_id: tenant_id})
CREATE (nfs:Storage {name: "storage-nfs", type: "storage", baseline_load: 40.0, tenant_id: tenant_id})

// 관계 생성
MATCH (lb:Network {name: "loadbalancer", tenant_id: tenant_id})
MATCH (gw:Service {name: "api-gateway", tenant_id: tenant_id})
MATCH (ws:Server {name: "web-server", tenant_id: tenant_id})
MATCH (asv:Service {name: "app-service", tenant_id: tenant_id})
MATCH (redis:Db {name: "cache-redis", tenant_id: tenant_id})
MATCH (pg:Db {name: "db-postgres", tenant_id: tenant_id})
MATCH (nfs:Storage {name: "storage-nfs", tenant_id: tenant_id})

// Load Balancer → API Gateway (Traffic)
CREATE (lb)-[:TRAFFIC {baseline_traffic: 1000.0}]->(gw)

// API Gateway → Web Server, Redis (Traffic, Dependency)
CREATE (gw)-[:TRAFFIC {baseline_traffic: 800.0}]->(ws)
CREATE (gw)-[:DEPENDS_ON {baseline_traffic: 400.0}]->(redis)

// Web Server → App Service, PostgreSQL (Traffic, Dependency)
CREATE (ws)-[:TRAFFIC {baseline_traffic: 600.0}]->(asv)
CREATE (ws)-[:DEPENDS_ON {baseline_traffic: 500.0}]->(pg)

// App Service → Redis, PostgreSQL (Dependency)
CREATE (asv)-[:DEPENDS_ON {baseline_traffic: 350.0}]->(redis)
CREATE (asv)-[:DEPENDS_ON {baseline_traffic: 450.0}]->(pg)

// PostgreSQL → NFS Storage (Dependency)
CREATE (pg)-[:DEPENDS_ON {baseline_traffic: 300.0}]->(nfs)
```

### 4.2 Python 스크립트 (Neo4j Driver)

```python
from neo4j import GraphDatabase

class Neo4jTopologySeeder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def seed_topology(self, tenant_id="t1"):
        with self.driver.session() as session:
            # 노드 생성
            session.run("""
                UNWIND $nodes AS node
                CREATE (n)
                SET n = node
                SET n.tenant_id = $tenant_id
            """, {
                "nodes": [
                    {"name": "loadbalancer", "type": "network", "baseline_load": 50.0},
                    {"name": "api-gateway", "type": "service", "baseline_load": 45.0},
                    {"name": "web-server", "type": "server", "baseline_load": 60.0},
                    {"name": "app-service", "type": "service", "baseline_load": 55.0},
                    {"name": "cache-redis", "type": "db", "baseline_load": 30.0},
                    {"name": "db-postgres", "type": "db", "baseline_load": 65.0},
                    {"name": "storage-nfs", "type": "storage", "baseline_load": 40.0},
                ],
                "tenant_id": tenant_id
            })
            
            # 관계 생성
            session.run("""
                MATCH (lb:Network {name: "loadbalancer", tenant_id: $tenant_id})
                MATCH (gw:Service {name: "api-gateway", tenant_id: $tenant_id})
                MATCH (ws:Server {name: "web-server", tenant_id: $tenant_id})
                MATCH (asv:Service {name: "app-service", tenant_id: $tenant_id})
                MATCH (redis:Db {name: "cache-redis", tenant_id: $tenant_id})
                MATCH (pg:Db {name: "db-postgres", tenant_id: $tenant_id})
                MATCH (nfs:Storage {name: "storage-nfs", tenant_id: $tenant_id})
                
                MERGE (lb)-[:TRAFFIC {baseline_traffic: 1000.0}]->(gw)
                MERGE (gw)-[:TRAFFIC {baseline_traffic: 800.0}]->(ws)
                MERGE (gw)-[:DEPENDS_ON {baseline_traffic: 400.0}]->(redis)
                MERGE (ws)-[:TRAFFIC {baseline_traffic: 600.0}]->(asv)
                MERGE (ws)-[:DEPENDS_ON {baseline_traffic: 500.0}]->(pg)
                MERGE (asv)-[:DEPENDS_ON {baseline_traffic: 350.0}]->(redis)
                MERGE (asv)-[:DEPENDS_ON {baseline_traffic: 450.0}]->(pg)
                MERGE (pg)-[:DEPENDS_ON {baseline_traffic: 300.0}]->(nfs)
            """, {"tenant_id": tenant_id})
    
    def close(self):
        self.driver.close()

# 사용 예시
if __name__ == "__main__":
    seeder = Neo4jTopologySeeder(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="secret"
    )
    seeder.seed_topology(tenant_id="t1")
    seeder.close()
```

---

## 5. 데이터 가져오기 (TIM+ 연동)

### 5.1 TIM+에서 토폴로지 데이터 추출

TIM+ 시스템에서 다음 데이터를 추출하여 Neo4j에 적재하세요:

1. **서비스**: 마이크로서비스, API 서비스 목록
2. **서버**: 호스트 목록, CPU/메모리 사용률
3. **데이터베이스**: Redis, PostgreSQL 등 DB 목록
4. **네트워크**: 로드밸런서, 라우터 등 네트워크 장비
5. **스토리지**: NFS, S3 등 스토리지 목록
6. **의존성**: 서비스 간 호출 관계, 호스팅 관계
7. **트래픽**: 서비스 간 트래픽 흐름 (req/s)

### 5.2 추천 파이프라인

```python
# TIM+ → Neo4j ETL 파이프라인
1. TIM+ API에서 토폴로지 데이터 수집
2. 데이터 정제 및 변환 (Neo4j 스키마 매핑)
3. Neo4j에 노드/관계 생성/업데이트
4. 주기적 동기화 (예: 10분마다)
```

---

## 6. 쿼리 가이드

### 6.1 전체 토폴로지 조회

```cypher
MATCH (n:Component {tenant_id: "t1"})
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 200
```

### 6.2 특정 서비스 관련 컴포넌트 조회

```cypher
MATCH path = (s:Service {name: "api-gateway", tenant_id: "t1"})<-[:DEPENDS_ON*0..5|HOSTS*0..5|TRAFFIC*0..5]-(n)
RETURN s, n, path
```

### 6.3 부하 임계값 초과 노드 조회

```cypher
MATCH (n:Component {tenant_id: "t1"})
WHERE n.baseline_load >= 70.0
RETURN n.name, n.type, n.baseline_load
ORDER BY n.baseline_load DESC
```

---

## 7. 테스트 및 검증

### 7.1 데이터 검증 쿼리

```bash
# Neo4j Browser에서 실행
# 1. 노드 수 확인
MATCH (n:Component {tenant_id: "t1"}) 
RETURN count(n) AS node_count

# 2. 관계 수 확인
MATCH ()-[r]->() 
RETURN count(r) AS rel_count

# 3. 고립 노드 확인 (관계가 없는 노드)
MATCH (n:Component {tenant_id: "t1"})
WHERE NOT (n)-[]-()
RETURN n.name AS isolated_nodes
```

### 7.2 시뮬레이션 API 테스트

```bash
# Mock 모드 테스트
curl "http://localhost:8000/api/sim/topology?service=api-gateway&scenario_type=what_if&traffic_change_pct=20&cpu_change_pct=10"

# Real 모드 테스트 (Neo4j 데이터 필요)
# .env 설정: SIM_MODE=real
curl "http://localhost:8000/api/sim/topology?service=api-gateway&scenario_type=what_if&traffic_change_pct=20&cpu_change_pct=10"
```

---

## 8. 주의사항

1. **테넌트 분리**: 모든 노드/관계에 `tenant_id` 속성 필수
2. **기본값 설정**: `baseline_load`와 `baseline_traffic`에 합리적인 기본값 설정
3. **관계 방향**: 의존성 방향을 올바르게 설정 (의존하는 쪽 → 의존받는 쪽)
4. **데이터 동기화**: 실시간 부하 데이터 주기적 업데이트 필요
5. **쿼리 제한**: 대용량 데이터일 경우 LIMIT 사용

---

## 9. 참고 자료

- [Neo4j 공식 문서](https://neo4j.com/docs/)
- [Cypher 쿼리 언어](https://neo4j.com/docs/cypher-manual/)
- [TIM+ 연동 가이드](../USER_GUIDE_CEP.md)