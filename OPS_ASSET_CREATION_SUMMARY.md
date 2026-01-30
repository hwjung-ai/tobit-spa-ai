# OPS Asset 생성 및 등록 완료 보고서

## 작업 완료 현황

### 1. 생성된 Asset 파일

#### 1.1 Query Assets (4개)
모든 파일은 `/home/spa/tobit-spa-ai/apps/api/resources/queries/postgres/ops/` 디렉토리에 위치

| Asset | 파일 | 설명 |
|-------|------|------|
| ci_search | ci_search.yaml, ci_search.sql | CI를 키워드로 검색 |
| metric_aggregate | metric_aggregate.yaml, metric_aggregate.sql | 메트릭을 그룹별로 집계 |
| event_history | event_history.yaml, event_history.sql | 이벤트 로그 조회 |
| graph_expand | graph_expand.yaml, graph_expand.sql | 그래프 관계 확장 |

#### 1.2 Policy Assets (2개)
모든 파일은 `/home/spa/tobit-spa-ai/apps/api/resources/policies/` 디렉토리에 위치

| Asset | 파일 | 정책 타입 |
|-------|------|---------|
| plan_budget_ops | plan_budget_ops.yaml | plan_budget |
| view_depth_ops | view_depth_ops.yaml | view_depth |

#### 1.3 Prompt Assets (2개)
모든 파일은 `/home/spa/tobit-spa-ai/apps/api/resources/prompts/ops/` 디렉토리에 위치

| Asset | 파일 | 엔진 |
|-------|------|-----|
| ops_planner | ops_planner.yaml | langgraph |
| ops_composer | ops_composer.yaml | langgraph |

#### 1.4 Source Assets (1개)
위치: `/home/spa/tobit-spa-ai/apps/api/resources/sources/`

| Asset | 파일 |
|-------|------|
| primary_postgres_ops | primary_postgres_ops.yaml |

#### 1.5 Mapping Assets (1개)
위치: `/home/spa/tobit-spa-ai/apps/api/resources/mappings/`

| Asset | 파일 |
|-------|------|
| graph_relation_ops | graph_relation_ops.yaml |

### 2. 생성된 설정 파일 상세

#### Query Asset 상세

**ci_search.yaml / ci_search.sql**
```yaml
- 이름: ci_search
- 범위: ops
- 설명: CI를 키워드로 검색하는 쿼리
- 매개변수: where_clause (SQL WHERE 절)
- 출력: CI 객체 배열
```

**metric_aggregate.yaml / metric_aggregate.sql**
```yaml
- 이름: metric_aggregate
- 범위: ops
- 설명: 메트릭을 그룹별로 집계
- 매개변수: where_clause
- 출력: 메트릭 집계 정보 (count, avg, min, max)
```

**event_history.yaml / event_history.sql**
```yaml
- 이름: event_history
- 범위: ops
- 설명: 이벤트 로그 조회
- 매개변수: where_clause
- 출력: 이벤트 로그 (event_id, type, timestamp, severity)
```

**graph_expand.yaml / graph_expand.sql**
```yaml
- 이름: graph_expand
- 범위: ops
- 설명: 그래프 관계를 재귀적으로 확장
- 매개변수: source_ci_id, initial_depth, max_depth
- 출력: 그래프 경로 (source, target, relation_type, depth)
```

#### Policy Asset 상세

**plan_budget_ops.yaml**
```yaml
정책 타입: plan_budget
범위: ops
제약 조건:
  - max_steps: 15 (최대 실행 단계)
  - timeout_ms: 180000 (3분 타임아웃)
  - max_depth: 8 (최대 깊이)
  - max_branches: 5 (최대 분기)
  - max_iterations: 200 (최대 반복)
```

**view_depth_ops.yaml**
```yaml
정책 타입: view_depth
범위: ops
뷰별 깊이 제약:
  - SUMMARY: 기본 2, 최대 2
  - COMPOSITION: 기본 3, 최대 4
  - DEPENDENCY: 기본 3, 최대 4
  - IMPACT: 기본 2, 최대 3
  - PATH: 기본 4, 최대 8
  - NEIGHBORS: 기본 2, 최대 3
```

#### Prompt Asset 상세

**ops_planner.yaml**
```
역할: OPS 질문을 분석하고 실행 계획 생성
템플릿:
  - plan_system: 플래너 시스템 프롬프트
  - plan_user: 사용자 질문 처리 지시
  - summary_system: 요약 시스템 프롬프트
  - summary_user: 요약 생성 지시

입력:
  - question: 운영 질문
  - plan: 실행 계획 정보
  - results: 쿼리 실행 결과

출력: JSON 형식 실행 계획
  {
    "queries": [쿼리 목록],
    "aggregation_strategy": "sequential|parallel",
    "estimated_duration_ms": 예상 시간,
    "confidence": 신뢰도
  }
```

**ops_composer.yaml**
```
역할: 여러 쿼리 결과를 종합하여 운영 통찰 생성
템플릿:
  - composition_system: 작성자 시스템 프롬프트
  - composition_instruction: 작성 지시
  - composition_format: 출력 형식

입력:
  - question: 운영 질문
  - ci_data: CI 검색 결과
  - metrics_data: 메트릭 집계 결과
  - event_data: 이벤트 로그
  - graph_data: 그래프 확장 결과

출력: 마크다운 형식 운영 분석 보고서
  # 제목
  ## 현재 상태
  ## 주요 메트릭
  ## 최근 이벤트
  ## 관계 및 의존성
  ## 위험 평가
  ## 권장 조치
```

### 3. Asset Registry 등록 방법

#### 3.1 자동 등록 스크립트 (권장)

```bash
# 생성된 스크립트 실행
python scripts/register_ops_assets.py \
  --base-url http://localhost:8000 \
  --publish

# 또는 기존 드래프트를 정리하고 등록
python scripts/register_ops_assets.py \
  --base-url http://localhost:8000 \
  --publish \
  --cleanup
```

#### 3.2 개별 등록 명령어

**Query Assets 등록**
```bash
python scripts/query_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

**Policy Assets 등록**
```bash
python scripts/policy_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

**Mapping Assets 등록**
```bash
python scripts/mapping_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

**Prompt Assets 등록**
```bash
python scripts/prompt_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000
```

### 4. Asset 확인 명령어

```bash
# 모든 OPS scope assets 조회
curl http://localhost:8000/asset-registry/assets?scope=ops

# 특정 타입의 assets만 조회
curl http://localhost:8000/asset-registry/assets?asset_type=query&scope=ops
curl http://localhost:8000/asset-registry/assets?asset_type=policy&scope=ops
curl http://localhost:8000/asset-registry/assets?asset_type=prompt&scope=ops
curl http://localhost:8000/asset-registry/assets?asset_type=source&scope=ops
curl http://localhost:8000/asset-registry/assets?asset_type=mapping&scope=ops

# Published 상태만 확인
curl "http://localhost:8000/asset-registry/assets?scope=ops&status=published"
```

### 5. 등록될 Asset 목록

| 이름 | 타입 | 범위 | 설명 |
|------|------|------|------|
| ci_search | query | ops | CI 키워드 검색 |
| metric_aggregate | query | ops | 메트릭 집계 |
| event_history | query | ops | 이벤트 로그 조회 |
| graph_expand | query | ops | 그래프 확장 |
| plan_budget_ops | policy | ops | 실행 계획 예산 |
| view_depth_ops | policy | ops | 그래프 뷰 깊이 |
| ops_planner | prompt | ops | OPS 플래너 |
| ops_composer | prompt | ops | 결과 조합 |
| primary_postgres_ops | source | ops | PostgreSQL 연결 |
| graph_relation_ops | mapping | ops | 그래프 관계 매핑 |
| primary_postgres_catalog | catalog | ops | PostgreSQL 스키마 |

**총 11개 Asset 생성**

### 6. 주요 기능

#### Query Assets로 가능한 작업
- **ci_search**: 특정 조건의 CI를 빠르게 검색
- **metric_aggregate**: 시간별, 그룹별 메트릭 분석
- **event_history**: 운영 이벤트 추적 및 분석
- **graph_expand**: CI 간 의존성 및 관계 분석

#### Policy Assets로 제어되는 항목
- **plan_budget_ops**: 너무 오래 걸리거나 과도한 리소스를 사용하는 쿼리 방지
- **view_depth_ops**: 그래프 탐색 깊이 제한으로 성능 최적화

#### Prompt Assets로 제공되는 기능
- **ops_planner**: 자동으로 필요한 쿼리 결정 및 실행 계획 생성
- **ops_composer**: 분산된 데이터를 통합하여 운영 인사이트 제공

### 7. 데이터 흐름

```
사용자 질문
    ↓
ops_planner (프롬프트)
    ↓
쿼리 실행 계획 생성
    ↓
Policy 검증 (plan_budget_ops)
    ↓
Query 실행 (ci_search, metric_aggregate, event_history, graph_expand)
    ↓
결과 수집
    ↓
ops_composer (프롬프트)
    ↓
운영 통찰 문서 생성
    ↓
사용자에게 반환
```

### 8. 파일 위치 요약

```
/home/spa/tobit-spa-ai/
├── apps/api/resources/
│   ├── queries/postgres/ops/
│   │   ├── ci_search.yaml / .sql
│   │   ├── metric_aggregate.yaml / .sql
│   │   ├── event_history.yaml / .sql
│   │   └── graph_expand.yaml / .sql
│   ├── policies/
│   │   ├── plan_budget_ops.yaml
│   │   └── view_depth_ops.yaml
│   ├── prompts/ops/
│   │   ├── ops_planner.yaml
│   │   └── ops_composer.yaml
│   ├── sources/
│   │   └── primary_postgres_ops.yaml
│   └── mappings/
│       └── graph_relation_ops.yaml
├── scripts/
│   └── register_ops_assets.py (새로 생성)
├── OPS_ASSET_REGISTRATION_GUIDE.md (상세 가이드)
└── OPS_ASSET_CREATION_SUMMARY.md (이 파일)
```

### 9. 다음 단계

1. **등록 실행**
   ```bash
   cd /home/spa/tobit-spa-ai
   python scripts/register_ops_assets.py --base-url http://localhost:8000 --publish
   ```

2. **등록 확인**
   ```bash
   curl http://localhost:8000/asset-registry/assets?scope=ops
   ```

3. **OPS 쿼리 실행 테스트**
   - OPS 플래너가 쿼리를 자동으로 선택하고 실행
   - 결과를 ops_composer로 종합하여 운영 통찰 제공

4. **모니터링**
   - Asset Registry에서 모든 assets가 'published' 상태인지 확인
   - Query 실행 성능 모니터링
   - Policy limits이 올바르게 적용되는지 확인

### 10. 트러블슈팅

#### API 서버 연결 실패
```bash
# API 서버 상태 확인
curl http://localhost:8000/health

# 또는 API 서버 시작
# (프로젝트의 API 서버 시작 스크립트 참조)
```

#### Asset 등록 실패
- YAML 문법 오류 확인: `yamllint` 사용
- SQL 문법 오류 확인: SQL 파일을 데이터베이스에서 테스트
- API 응답 메시지 확인: `-v` 플래그로 상세 로그 확인

#### Draft 상태 Asset 정리
```bash
python scripts/register_ops_assets.py --cleanup
```

## 결론

OPS 쿼리 실행을 위한 모든 필수 Asset이 생성되었습니다:

✓ **4개 Query Assets**: 다양한 운영 데이터 수집
✓ **2개 Policy Assets**: 실행 제약 및 리소스 관리
✓ **2개 Prompt Assets**: 자동 계획 및 결과 종합
✓ **1개 Source Asset**: PostgreSQL 데이터베이스 연결
✓ **1개 Mapping Asset**: 그래프 관계 정의
✓ **총 11개 Assets** (Catalog 포함)

이제 API 서버를 실행하고 `register_ops_assets.py` 스크립트를 실행하면 모든 assets가 자동으로 등록되고 published 상태로 설정됩니다.
