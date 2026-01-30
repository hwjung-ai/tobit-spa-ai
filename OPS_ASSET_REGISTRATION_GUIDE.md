# OPS Asset Registry 생성 및 발행 가이드

## 개요
이 문서는 OPS 쿼리 실행을 위한 모든 필요한 Asset들을 Asset Registry에 등록하고 발행하는 과정을 설명합니다.

## 생성된 Asset 목록

### 1. Query Assets (query_asset 타입)
OPS 쿼리 실행에 필요한 4개의 쿼리 asset이 생성되었습니다.

#### 1.1 ci_search
- **경로**: `/apps/api/resources/queries/postgres/ops/ci_search.yaml` & `.sql`
- **설명**: CI를 키워드로 검색하는 쿼리
- **매개변수**: `where_clause` (문자열, 필수)
- **출력**: CI 객체 배열 (ci_id, ci_code, ci_name, ci_type, ci_category 등)

#### 1.2 metric_aggregate
- **경로**: `/apps/api/resources/queries/postgres/ops/metric_aggregate.yaml` & `.sql`
- **설명**: 메트릭을 그룹별로 집계하는 쿼리
- **매개변수**: `where_clause` (문자열, 필수)
- **출력**: 메트릭 집계 정보 (metric_name, count, avg_value, min_value, max_value)

#### 1.3 event_history
- **경로**: `/apps/api/resources/queries/postgres/ops/event_history.yaml` & `.sql`
- **설명**: 이벤트 로그 조회
- **매개변수**: `where_clause` (문자열, 필수)
- **출력**: 이벤트 로그 데이터 (event_id, event_type, event_timestamp, severity)

#### 1.4 graph_expand
- **경로**: `/apps/api/resources/queries/postgres/ops/graph_expand.yaml` & `.sql`
- **설명**: 그래프 관계 확장
- **매개변수**: `source_ci_id`, `initial_depth`, `max_depth`
- **출력**: 그래프 경로 데이터 (source_ci_id, target_ci_id, relation_type, depth)

### 2. Policy Assets (policy 타입)
OPS 플랜 실행을 위한 2개의 정책 asset이 생성되었습니다.

#### 2.1 plan_budget_ops
- **경로**: `/apps/api/resources/policies/plan_budget_ops.yaml`
- **정책 타입**: plan_budget
- **설정**:
  - max_steps: 15
  - timeout_ms: 180000 (3분)
  - max_depth: 8
  - max_branches: 5
  - max_iterations: 200

#### 2.2 view_depth_ops
- **경로**: `/apps/api/resources/policies/view_depth_ops.yaml`
- **정책 타입**: view_depth
- **설정**: 각 뷰 타입별 깊이 제약
  - SUMMARY: 기본 깊이 2, 최대 2
  - COMPOSITION: 기본 깊이 3, 최대 4
  - DEPENDENCY: 기본 깊이 3, 최대 4
  - IMPACT: 기본 깊이 2, 최대 3
  - PATH: 기본 깊이 4, 최대 8
  - NEIGHBORS: 기본 깊이 2, 최대 3

### 3. Prompt Assets (prompt 타입)
OPS 실행을 위한 2개의 프롬프트 asset이 생성되었습니다.

#### 3.1 ops_planner
- **경로**: `/apps/api/resources/prompts/ops/ops_planner.yaml`
- **엔진**: langgraph
- **역할**: OPS 질문을 분석하고 실행 계획을 생성
- **입력**: question, plan 관련 정보
- **출력**: 구조화된 쿼리 계획 (JSON)

#### 3.2 ops_composer
- **경로**: `/apps/api/resources/prompts/ops/ops_composer.yaml`
- **엔진**: langgraph
- **역할**: 여러 쿼리 결과를 종합하여 운영 통찰을 생성
- **입력**: question, ci_data, metrics_data, event_data, graph_data
- **출력**: 마크다운 형식의 운영 분석 보고서

### 4. Source Assets (source 타입)
OPS 쿼리 실행을 위한 데이터베이스 연결 정보

#### 4.1 primary_postgres_ops
- **경로**: `/apps/api/resources/sources/primary_postgres_ops.yaml`
- **소스 타입**: postgresql
- **설정**: 환경 변수 기반 (PG_HOST, PG_PORT, PG_USER, PG_DB, PG_PASSWORD)
- **스코프**: ops

### 5. Mapping Assets (mapping 타입)
OPS 그래프 뷰를 위한 관계 매핑

#### 5.1 graph_relation_ops
- **경로**: `/apps/api/resources/mappings/graph_relation_ops.yaml`
- **매핑 타입**: graph_relation
- **내용**:
  - 각 뷰 타입별 관계 타입 정의
  - MANAGES, MONITORED_BY 등 운영 관련 관계 타입 포함
  - IMPACT, DEPENDENCY, PATH 등 뷰별 관계 매핑

### 6. Schema Catalog Asset (catalog 타입)
데이터베이스 테이블/컬럼 정보는 기존 `primary_postgres_catalog.yaml`을 사용합니다.

## Asset Registry 등록 절차

### 단계 1: Query Assets 등록
```bash
# API 서버가 실행 중이어야 합니다
python scripts/query_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

### 단계 2: Policy Assets 등록
```bash
python scripts/policy_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

### 단계 3: Prompt Assets 등록
```bash
python scripts/prompt_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

### 단계 4: Source Assets 등록 (수동)
Source Asset은 현재 dedicated importer가 없으므로,
API 엔드포인트를 직접 호출하여 등록합니다:

```bash
curl -X POST http://localhost:8000/asset-registry/assets \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "source",
    "name": "primary_postgres_ops",
    "description": "Primary PostgreSQL source for OPS queries",
    "scope": "ops",
    "source_type": "postgresql",
    "connection": {
      "host": "${PG_HOST}",
      "port": "${PG_PORT}",
      "username": "${PG_USER}",
      "database": "${PG_DB}",
      "secret_key_ref": "env:PG_PASSWORD",
      "timeout": 30,
      "ssl_mode": "verify-full",
      "connection_params": {}
    }
  }'
```

### 단계 5: Mapping Assets 등록 (수동)
Mapping Asset도 dedicated importer를 사용합니다:

```bash
python scripts/mapping_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

### 단계 6: Schema Catalog 등록 (수동)
```bash
curl -X POST http://localhost:8000/asset-registry/assets \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "catalog",
    "name": "primary_postgres_catalog",
    "description": "PostgreSQL catalog for OPS queries",
    "scope": "ops",
    "source_ref": "primary_postgres_ops",
    "catalog": {
      "name": "primary_postgres_catalog",
      "source_ref": "primary_postgres_ops",
      "tables": [],
      "scan_status": "pending"
    }
  }'
```

## Asset 확인 절차

### 1. Asset Registry 조회
```bash
# 모든 OPS scope assets 조회
curl http://localhost:8000/asset-registry/assets?scope=ops

# 특정 타입의 assets 조회
curl http://localhost:8000/asset-registry/assets?asset_type=query&scope=ops
curl http://localhost:8000/asset-registry/assets?asset_type=policy&scope=ops
curl http://localhost:8000/asset-registry/assets?asset_type=prompt&scope=ops
```

### 2. 개별 Asset 확인
```bash
# Asset ID로 조회 (등록 후 반환되는 asset_id 사용)
curl http://localhost:8000/asset-registry/assets/{asset_id}

# 버전별 확인
curl http://localhost:8000/asset-registry/assets/{asset_id}?version=1
```

### 3. Published Assets 확인
```bash
# Published 상태의 모든 OPS assets 확인
curl "http://localhost:8000/asset-registry/assets?scope=ops&status=published"
```

## 등록 순서의 중요성

1. **Source Assets 먼저**: Schema Catalog가 Source를 참조하므로 먼저 등록
2. **Query Assets**: Schema가 필요하지 않은 독립적인 쿼리
3. **Policy Assets**: 다른 asset에 의존하지 않음
4. **Mapping Assets**: Graph 관계 정의에만 사용
5. **Prompt Assets**: 마지막에 등록 (다른 assets에 의존할 수 있음)

## 상태 확인

모든 asset이 'published' 상태로 설정되어야 OPS 실행에 사용 가능합니다:

```bash
# Published 상태 확인
curl http://localhost:8000/asset-registry/assets \
  -H "Accept: application/json" | jq '.data.assets[] | select(.scope=="ops") | {name, status, asset_type}'
```

예상 출력:
```json
{
  "name": "ci_search",
  "status": "published",
  "asset_type": "query"
}
{
  "name": "metric_aggregate",
  "status": "published",
  "asset_type": "query"
}
{
  "name": "event_history",
  "status": "published",
  "asset_type": "query"
}
{
  "name": "graph_expand",
  "status": "published",
  "asset_type": "query"
}
{
  "name": "plan_budget_ops",
  "status": "published",
  "asset_type": "policy"
}
{
  "name": "view_depth_ops",
  "status": "published",
  "asset_type": "policy"
}
{
  "name": "ops_planner",
  "status": "published",
  "asset_type": "prompt"
}
{
  "name": "ops_composer",
  "status": "published",
  "asset_type": "prompt"
}
{
  "name": "primary_postgres_ops",
  "status": "published",
  "asset_type": "source"
}
{
  "name": "graph_relation_ops",
  "status": "published",
  "asset_type": "mapping"
}
```

## 문제 해결

### 등록 실패 시
1. API 서버가 실행 중인지 확인
2. 파일 경로가 올바른지 확인
3. YAML 문법이 올바른지 확인
4. 필수 필드가 모두 포함되었는지 확인

### Asset이 Draft 상태일 때
Draft 상태의 asset을 삭제하고 다시 등록:
```bash
python scripts/query_asset_importer.py \
  --scope ops \
  --apply \
  --cleanup-drafts \
  --publish
```

### 데이터베이스 연결 테스트
```bash
# Primary PostgreSQL 소스 연결 테스트
curl -X POST http://localhost:8000/asset-registry/assets/{source_asset_id}/test-connection
```

## 다음 단계

Assets가 모두 'published' 상태가 되면:
1. OPS Planner에서 이들 assets를 참조할 수 있습니다
2. Query 실행 엔진이 쿼리를 처리할 수 있습니다
3. Policy에 따라 실행 계획의 리소스를 관리합니다
4. Prompt를 통해 결과를 종합하여 운영 통찰을 생성합니다

## 참고 사항

- 모든 OPS scope assets는 'ops' 스코프로 등록됩니다
- Source Asset의 연결 정보는 환경 변수로 주입됩니다
- Policy Assets의 limits는 실행 시간 및 리소스 제약을 정의합니다
- Prompt Assets는 LangGraph 엔진을 사용하여 복잡한 오케스트레이션을 지원합니다
