# OPS Asset Registration Checklist

## Asset 생성 완료 체크리스트

### 1. Query Assets (4개) ✓
- [x] ci_search.yaml & .sql
  - 설명: CI를 키워드로 검색하는 쿼리
  - 경로: `/apps/api/resources/queries/postgres/ops/`
  
- [x] metric_aggregate.yaml & .sql
  - 설명: 메트릭을 그룹별로 집계하는 쿼리
  - 경로: `/apps/api/resources/queries/postgres/ops/`
  
- [x] event_history.yaml & .sql
  - 설명: 이벤트 로그를 조회하는 쿼리
  - 경로: `/apps/api/resources/queries/postgres/ops/`
  
- [x] graph_expand.yaml & .sql
  - 설명: 그래프 관계를 확장하는 쿼리
  - 경로: `/apps/api/resources/queries/postgres/ops/`

### 2. Policy Assets (2개) ✓
- [x] plan_budget_ops.yaml
  - 정책 타입: plan_budget
  - max_steps: 15, timeout: 180000ms
  - 경로: `/apps/api/resources/policies/`
  
- [x] view_depth_ops.yaml
  - 정책 타입: view_depth
  - 각 뷰별 깊이 제약 정의
  - 경로: `/apps/api/resources/policies/`

### 3. Prompt Assets (2개) ✓
- [x] ops_planner.yaml
  - 엔진: langgraph
  - 역할: OPS 질문 분석 및 실행 계획 생성
  - 경로: `/apps/api/resources/prompts/ops/`
  
- [x] ops_composer.yaml
  - 엔진: langgraph
  - 역할: 쿼리 결과 종합 및 운영 통찰 생성
  - 경로: `/apps/api/resources/prompts/ops/`

### 4. Source Assets (1개) ✓
- [x] primary_postgres_ops.yaml
  - 소스 타입: postgresql
  - 환경 변수 기반 연결 설정
  - 경로: `/apps/api/resources/sources/`

### 5. Mapping Assets (1개) ✓
- [x] graph_relation_ops.yaml
  - 매핑 타입: graph_relation
  - 그래프 관계 타입 정의
  - 경로: `/apps/api/resources/mappings/`

### 6. Schema Catalog (1개) ✓
- [x] primary_postgres_catalog (기존 사용)
  - 위치: `/apps/api/resources/catalogs/primary_postgres_catalog.yaml`

**총 11개 Assets 생성 완료**

---

## Asset Registry 등록 절차 (아래 순서대로 진행)

### Step 1: 환경 준비
```bash
# 1.1 프로젝트 디렉토리 이동
cd /home/spa/tobit-spa-ai

# 1.2 API 서버 실행 (별도 터미널)
# API 서버 시작 스크립트 실행
```

### Step 2: Query Assets 등록
```bash
# 상태 확인: [ ] 진행 [ ] 완료

python scripts/query_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000 \
  --cleanup-drafts

# 확인 명령어:
curl http://localhost:8000/asset-registry/assets?asset_type=query&scope=ops
```

### Step 3: Policy Assets 등록
```bash
# 상태 확인: [ ] 진행 [ ] 완료

python scripts/policy_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000 \
  --cleanup-drafts

# 확인 명령어:
curl http://localhost:8000/asset-registry/assets?asset_type=policy&scope=ops
```

### Step 4: Mapping Assets 등록
```bash
# 상태 확인: [ ] 진행 [ ] 완료

python scripts/mapping_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000 \
  --cleanup-drafts

# 확인 명령어:
curl http://localhost:8000/asset-registry/assets?asset_type=mapping&scope=ops
```

### Step 5: Prompt Assets 등록
```bash
# 상태 확인: [ ] 진행 [ ] 완료

python scripts/prompt_asset_importer.py \
  --scope ops \
  --apply \
  --publish \
  --base-url http://localhost:8000 \
  --cleanup-drafts

# 확인 명령어:
curl http://localhost:8000/asset-registry/assets?asset_type=prompt&scope=ops
```

### Step 6: Source Asset 등록 (자동 스크립트 포함)
```bash
# 상태 확인: [ ] 진행 [ ] 완료

# 자동 등록을 위해 생성된 스크립트 실행:
# register_ops_assets.py는 이를 포함합니다
```

---

## 통합 등록 스크립트 사용 (권장)

```bash
# 모든 Assets를 한 번에 등록하고 발행
python scripts/register_ops_assets.py \
  --base-url http://localhost:8000 \
  --publish \
  --cleanup

# 상태 확인: [ ] 진행 [ ] 완료
```

**결과 확인:**
```bash
curl http://localhost:8000/asset-registry/assets?scope=ops | jq '.data.assets[] | {name, asset_type, status}'
```

---

## 최종 검증 (모든 Assets Published 확인)

### 1. 전체 Assets 조회
```bash
curl http://localhost:8000/asset-registry/assets?scope=ops
```

### 2. 예상 결과 (11개 Assets 모두 published)
- [x] ci_search (query, published)
- [x] metric_aggregate (query, published)
- [x] event_history (query, published)
- [x] graph_expand (query, published)
- [x] plan_budget_ops (policy, published)
- [x] view_depth_ops (policy, published)
- [x] ops_planner (prompt, published)
- [x] ops_composer (prompt, published)
- [x] primary_postgres_ops (source, published)
- [x] graph_relation_ops (mapping, published)
- [x] primary_postgres_catalog (catalog, published)

### 3. 각 타입별 확인
```bash
# Query Assets (4개)
curl "http://localhost:8000/asset-registry/assets?asset_type=query&scope=ops" | jq '.data.assets | length'

# Policy Assets (2개)
curl "http://localhost:8000/asset-registry/assets?asset_type=policy&scope=ops" | jq '.data.assets | length'

# Prompt Assets (2개)
curl "http://localhost:8000/asset-registry/assets?asset_type=prompt&scope=ops" | jq '.data.assets | length'

# Source Assets (1개)
curl "http://localhost:8000/asset-registry/assets?asset_type=source&scope=ops" | jq '.data.assets | length'

# Mapping Assets (1개)
curl "http://localhost:8000/asset-registry/assets?asset_type=mapping&scope=ops" | jq '.data.assets | length'

# Catalog Assets (1개)
curl "http://localhost:8000/asset-registry/assets?asset_type=catalog&scope=ops" | jq '.data.assets | length'
```

---

## 문제 해결

### Issue: Assets가 draft 상태로 남음
**해결책:**
```bash
# Cleanup 플래그로 다시 등록
python scripts/register_ops_assets.py --cleanup
```

### Issue: API 서버 연결 실패
**해결책:**
```bash
# API 서버 상태 확인
curl http://localhost:8000/health

# API 서버 시작 필요
```

### Issue: YAML 파일 오류
**해결책:**
```bash
# YAML 문법 검증
pip install yamllint
yamllint apps/api/resources/queries/postgres/ops/*.yaml
yamllint apps/api/resources/policies/*ops*.yaml
yamllint apps/api/resources/prompts/ops/*ops*.yaml
```

### Issue: SQL 쿼리 오류
**해결책:**
```bash
# SQL 파일이 유효한지 데이터베이스에서 테스트
# 각 SQL 파일의 문법이 올바른지 확인
```

---

## 문서 참조

생성된 상세 문서:
1. `/home/spa/tobit-spa-ai/OPS_ASSET_REGISTRATION_GUIDE.md` - 상세 가이드
2. `/home/spa/tobit-spa-ai/OPS_ASSET_CREATION_SUMMARY.md` - 생성 요약
3. `/home/spa/tobit-spa-ai/scripts/register_ops_assets.py` - 자동 등록 스크립트

---

## 작업 일정

| 단계 | 작업 | 예상 시간 | 상태 |
|------|------|---------|------|
| 1 | 환경 준비 | 5분 | [ ] |
| 2 | Query Assets 등록 | 1분 | [ ] |
| 3 | Policy Assets 등록 | 1분 | [ ] |
| 4 | Mapping Assets 등록 | 1분 | [ ] |
| 5 | Prompt Assets 등록 | 1분 | [ ] |
| 6 | Source/Catalog Assets 등록 | 2분 | [ ] |
| 7 | 최종 검증 | 2분 | [ ] |
| **합계** | **전체 등록** | **13분** | [ ] |

---

## Notes

- 모든 Assets는 'ops' 스코프로 등록됩니다
- Source Asset의 PostgreSQL 연결 정보는 환경 변수로 주입됩니다
- Policy Assets의 limits는 실행 시간 및 리소스 제약을 정의합니다
- Prompt Assets는 LangGraph 엔진을 사용합니다
- 모든 Assets는 'published' 상태로 설정됩니다

---

## 등록 완료 확인 방법

```bash
# 1. 모든 OPS Assets 조회
curl "http://localhost:8000/asset-registry/assets?scope=ops" | jq '.data.assets | length'

# 결과: 11개여야 함

# 2. Published 상태 확인
curl "http://localhost:8000/asset-registry/assets?scope=ops&status=published" | jq '.data.assets | length'

# 결과: 11개여야 함

# 3. 개별 Asset 확인
curl "http://localhost:8000/asset-registry/assets?scope=ops" | jq '.data.assets[] | select(.name=="ci_search") | {name, status, version}'
```

**등록 완료 시 모든 검증이 통과해야 합니다.**
