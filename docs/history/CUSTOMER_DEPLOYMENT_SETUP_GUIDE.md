# 고객사 배포 설정 가이드

## 개요

이 문서는 tobit-spa-ai 제품을 고객사에 설치한 후, 고객의 데이터와 환경에 맞게 설정하는 방법을 단계별로 설명합니다.

---

## 목차

1. [설정 개요](#1-설정-개요)
2. [Phase 1: 시스템 설정](#2-phase-1-시스템-설정)
3. [Phase 2: 데이터베이스 초기화](#3-phase-2-데이터베이스-초기화)
4. [Phase 3: Asset Registry 설정](#4-phase-3-asset-registry-설정)
5. [Phase 4: 고객 데이터 설정](#5-phase-4-고객-데이터-설정)
6. [Phase 5: 검증 및 테스트](#6-phase-5-검증-및-테스트)
7. [설정 체크리스트](#7-설정-체크리스트)

---

## 1. 설정 개요

### 1.1 Asset 유형별 설정 필요 여부

| Asset Type | 필수 설정 | 고객별 커스터마이징 | 기본값 사용 가능 |
|------------|----------|-------------------|-----------------|
| **Source** | ✅ 필수 | 연결 정보 변경 | ❌ |
| **Catalog** | ✅ 필수 | 스캔 실행 | ❌ |
| **Tool** | ✅ 필수 | 고객 쿼리에 맞게 수정 | ⚠️ 부분 |
| **Query** | ✅ 필수 | 고객 스키마에 맞게 수정 | ❌ |
| **Prompt** | ⚠️ 권장 | 고객 용어에 맞게 수정 | ✅ |
| **Policy** | ⚠️ 권장 | 성능 요구사항에 맞게 조정 | ✅ |
| **Mapping** | ⚠️ 권장 | 데이터 매핑 조정 | ✅ |
| **Screen** | 선택 | UI 커스터마이징 | ✅ |
| **Document** | ✅ 필수 | 고객 문서 추가 | ❌ |

### 1.2 설정 순서 (의존성 기반)

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: 시스템 설정 (.env, 외부 서비스)                      │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: DB 초기화 (마이그레이션)                             │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: 기본 Asset 등록 (Source → Catalog)                  │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: 고객 데이터 설정 (Query, Tool, Document, 등)         │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: 검증 및 테스트                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: 시스템 설정

### 2.1 필수 외부 서비스 설치

```bash
# PostgreSQL (필수)
docker run -d --name postgres \
  -e POSTGRES_USER=tobit_user \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=tobit \
  -p 5432:5432 \
  postgres:15

# Redis (필수 - 캐싱, CEP)
docker run -d --name redis \
  -p 6379:6379 \
  redis:7

# Neo4j (선택 - Graph 기능 사용 시)
docker run -d --name neo4j \
  -e NEO4J_AUTH=neo4j/secret \
  -p 7474:7474 \
  -p 7687:7687 \
  neo4j:5
```

### 2.2 환경 변수 설정 (.env)

`apps/api/.env` 파일을 생성하고 다음 값을 설정합니다:

```env
# === 필수 설정 ===

# 애플리케이션 환경
APP_ENV=prod
API_PORT=8000
OPS_MODE=real
SIM_MODE=real

# PostgreSQL (필수)
PG_HOST=<고객 PostgreSQL 호스트>
PG_PORT=5432
PG_DB=tobit
PG_USER=<DB 사용자>
PG_PASSWORD=<DB 비밀번호>

# Redis (필수)
REDIS_URL=redis://<Redis 호스트>:6379/0

# === 선택 설정 ===

# Neo4j (Graph 기능 사용 시)
NEO4J_URI=neo4j://<Neo4j 호스트>:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<Neo4j 비밀번호>

# LLM 설정 (내부 LLM 사용 시)
LLM_PROVIDER=openai  # 또는 azure, anthropic, custom
LLM_BASE_URL=<내부 LLM URL>  # 내부 LLM인 경우 설정
OPENAI_API_KEY=<API 키>  # OpenAI 사용 시
CHAT_MODEL=<모델명>
EMBED_MODEL=<임베딩 모델명>

# 보안 설정
API_AUTH_DEFAULT_MODE=jwt_only
ENABLE_PERMISSION_CHECK=true
DEFAULT_TENANT_ID=<고객 테넌트 ID>

# CORS (프론트엔드 도메인)
CORS_ORIGINS=https://<고객 도메인>
```

### 2.3 LLM 엔진 설정

#### 옵션 A: OpenAI 사용
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
CHAT_MODEL=gpt-4
EMBED_MODEL=text-embedding-3-small
```

#### 옵션 B: 내부 LLM (Azure OpenAI)
```env
LLM_PROVIDER=azure
LLM_BASE_URL=https://<your-resource>.openai.azure.com
OPENAI_API_KEY=<Azure API 키>
CHAT_MODEL=gpt-4-deployment
EMBED_MODEL=text-embedding-ada-002
```

#### 옵션 C: 내부 LLM (vLLM/Ollama)
```env
LLM_PROVIDER=openai  # OpenAI 호환 API
LLM_BASE_URL=http://<내부 LLM 서버>:8000/v1
OPENAI_API_KEY=dummy  # 필요 시
CHAT_MODEL=<모델명>
EMBED_MODEL=<임베딩 모델명>
```

---

## 3. Phase 2: 데이터베이스 초기화

### 3.1 마이그레이션 실행

```bash
cd apps/api

# 모든 마이그레이션 적용
alembic upgrade head
```

### 3.2 주요 마이그레이션 내역

| 마이그레이션 | 생성 테이블 | 설명 |
|-------------|------------|------|
| 0045 | document search indexes | 문서 검색 인덱스 (BM25 + pgvector) |
| 0048 | tb_metric_timeseries | 메트릭 시계열 데이터 |
| 0049 | api_definitions, ml_models | API 관리, ML 모델 |
| 0050 | tenant_id to assets | 멀티테넌시 지원 |
| 0061 | document category/tags | 문서 분류 |
| 0062 | tool_catalog_ref | Tool-Catalog 연결 |

### 3.3 초기 관리자 계정 생성

```sql
-- 필수: 관리자 사용자 생성
INSERT INTO users (user_id, username, email, role, tenant_id)
VALUES (
  gen_random_uuid(),
  'admin',
  'admin@customer.com',
  'admin',
  '<DEFAULT_TENANT_ID>'
);
```

---

## 4. Phase 3: Asset Registry 설정

### 4.1 기본 Asset 등록 스크립트 실행

```bash
# API 서버가 실행 중인 상태에서 실행
python scripts/register_ops_assets.py \
  --base-url http://localhost:8000 \
  --publish
```

### 4.2 등록되는 기본 Assets

| Asset | Type | 설명 |
|-------|------|------|
| primary_postgres_ops | source | PostgreSQL 연결 정보 |
| primary_postgres_catalog | catalog | 스키마 메타데이터 |
| ci_search | query | CI 검색 쿼리 |
| ci_detail_lookup | query | CI 상세 조회 |
| metric_aggregate | query | 메트릭 집계 |
| event_history | query | 이벤트 이력 |
| graph_expand | query | 그래프 확장 |
| plan_budget_ops | policy | 실행 예산 제약 |
| view_depth_ops | policy | 그래프 깊이 제약 |
| ops_planner | prompt | 계획 생성 프롬프트 |
| ops_composer | prompt | 응답 작성 프롬프트 |
| graph_relation_ops | mapping | 그래프 관계 매핑 |

### 4.3 Source Asset 설정 (고객별 필수)

기본 등록 후, 고객의 실제 DB 연결 정보로 수정:

```python
# Admin UI > Asset Registry > Sources > primary_postgres_ops 편집
{
  "connection": {
    "host": "<고객 DB 호스트>",
    "port": 5432,
    "username": "<고객 DB 사용자>",
    "database": "<고객 DB명>",
    "secret_key_ref": "env:PG_PASSWORD"
  }
}
```

### 4.4 Catalog 스캔 실행

```bash
# Catalog 스캔 API 호출
curl -X POST http://localhost:8000/asset-registry/catalogs/primary_postgres_catalog/scan \
  -H "Authorization: Bearer <token>"
```

또는 Admin UI에서:
1. Asset Registry > Catalogs > primary_postgres_catalog 선택
2. "Scan Schema" 버튼 클릭

---

## 5. Phase 4: 고객 데이터 설정

### 5.1 Query Assets 수정

고객의 실제 테이블/컬럼에 맞게 쿼리를 수정해야 합니다.

#### CI Search Query 예시
```sql
-- 원본 (기본)
SELECT ci_id, name, class_name
FROM ci
WHERE name ILIKE :keyword
LIMIT :limit

-- 수정 (고객 스키마에 맞게)
SELECT asset_id as ci_id,
       asset_name as name,
       asset_type as class_name
FROM customer_assets  -- 고객 테이블명
WHERE asset_name ILIKE :keyword
  AND status = 'ACTIVE'  -- 고객별 조건
LIMIT :limit
```

#### Metric Aggregate Query 예시
```sql
-- 원본
SELECT AVG(value) as avg_value
FROM tb_metric_timeseries
WHERE metric_name = :metric_name
  AND ts >= :start_time

-- 수정
SELECT AVG(metric_value) as avg_value
FROM customer_metrics  -- 고객 테이블
WHERE metric_type = :metric_name
  AND collected_at >= :start_time
```

### 5.2 Tool Assets 설정

#### Tool Type별 필수 설정

| Tool Type | 필수 구성 | 설명 |
|-----------|----------|------|
| ci_lookup | source_ref, query | CI 조회 |
| ci_search | source_ref, query | CI 검색 |
| metric_query | source_ref, query | 메트릭 조회 |
| history_search | source_ref, query | 이력 검색 |
| document_search | body_template | 문서 검색 |
| http_api | url_template, method | HTTP API 호출 |

#### Tool Capabilities 설정

각 Tool은 `tags.capabilities`에 자신의 기능을 명시해야 합니다:

```json
{
  "tags": {
    "capabilities": ["ci_lookup", "ci_search"],
    "supported_modes": ["config", "all"]
  }
}
```

### 5.3 Documents 추가

#### 방법 1: API를 통한 업로드

```bash
# 단일 문서 업로드
curl -X POST http://localhost:8000/api/documents \
  -H "Authorization: Bearer <token>" \
  -F "file=@manual.pdf" \
  -F "category=operations" \
  -F "tags=[\"linux\", \"network\"]"
```

#### 방법 2: Admin UI 사용

1. Admin > Documents > Upload
2. 파일 선택 및 메타데이터 입력
3. Category 및 Tags 지정
4. 업로드 후 자동 인덱싱

#### 문서 인덱싱 확인

```sql
-- 인덱싱된 문서 확인
SELECT id, filename, category,
       array_length(tags, 1) as tag_count,
       embedding IS NOT NULL as has_embedding
FROM documents
WHERE tenant_id = '<고객 테넌트>';
```

### 5.4 Prompt Assets 커스터마이징

고객별 용어와 컨텍스트에 맞게 프롬프트 조정:

```python
# ops_planner 프롬프트 수정 예시
template = """
당신은 <고객사명>의 IT 운영 어시스턴트입니다.

사용 가능한 데이터 소스:
- CMDB: <고객 CMDB명> (Asset, Server, Network 등)
- 모니터링: <고객 모니터링 시스템명>
- 이벤트 로그: <고객 로그 시스템명>

고객 특화 용어:
- "서버" = Physical/Virtual Server assets
- "장애" = Incidents with severity > 2
- "SLA" = Response time target < 고객 SLA 시간 >

질의: {question}
"""
```

---

## 6. Phase 5: 검증 및 테스트

### 6.1 Asset 등록 확인

```bash
# 등록된 Assets 확인
python scripts/register_ops_assets.py \
  --base-url http://localhost:8000 \
  --verify
```

### 6.2 연결 테스트

```bash
# Source 연결 테스트
curl -X POST http://localhost:8000/asset-registry/sources/primary_postgres_ops/test \
  -H "Authorization: Bearer <token>"

# 예상 응답: {"status": "ok", "message": "Connection successful"}
```

### 6.3 OPS 기능 테스트

#### Config Mode 테스트
```bash
curl -X POST http://localhost:8000/ops/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "서버 목록을 보여줘",
    "mode": "config"
  }'
```

#### Document Mode 테스트
```bash
curl -X POST http://localhost:8000/ops/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "네트워크 설정 매뉴얼을 찾아줘",
    "mode": "document"
  }'
```

#### All Mode 테스트
```bash
curl -X POST http://localhost:8000/ops/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "MES 서버 06의 상태와 관련 문서를 알려줘",
    "mode": "all"
  }'
```

### 6.4 LLM 연결 테스트

```bash
curl -X POST http://localhost:8000/api/llm/test \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, can you hear me?",
    "model": "gpt-4"
  }'
```

---

## 7. 설정 체크리스트

### 7.1 시스템 설정 ✅

- [ ] PostgreSQL 설치 및 연결 확인
- [ ] Redis 설치 및 연결 확인
- [ ] Neo4j 설치 (Graph 기능 사용 시)
- [ ] .env 파일 구성
- [ ] LLM API 연결 확인

### 7.2 데이터베이스 ✅

- [ ] `alembic upgrade head` 실행
- [ ] 관리자 계정 생성
- [ ] 테넌트 설정

### 7.3 Asset Registry ✅

- [ ] `register_ops_assets.py` 실행
- [ ] Source Asset 연결 정보 수정
- [ ] Catalog 스캔 실행

### 7.4 고객 데이터 ✅

- [ ] Query Assets 고객 스키마에 맞게 수정
- [ ] Tool Assets capabilities 설정
- [ ] Documents 업로드 및 인덱싱
- [ ] Prompts 고객 용어에 맞게 조정

### 7.5 검증 ✅

- [ ] Asset 등록 확인
- [ ] Source 연결 테스트
- [ ] OPS 각 모드 테스트 (config, metric, hist, graph, document, all)
- [ ] LLM 응답 테스트
- [ ] 문서 검색 테스트

---

## 부록 A: 빠른 설정 명령어 모음

```bash
# 1. 환경 설정
cp apps/api/.env.example apps/api/.env
vi apps/api/.env

# 2. DB 마이그레이션
cd apps/api && alembic upgrade head

# 3. 서버 시작
make dev

# 4. Asset 등록
python scripts/register_ops_assets.py --base-url http://localhost:8000 --publish

# 5. Catalog 스캔
curl -X POST http://localhost:8000/asset-registry/catalogs/primary_postgres_catalog/scan

# 6. 검증
python scripts/register_ops_assets.py --base-url http://localhost:8000 --verify
```

---

## 부록 B: 문제 해결

### B.1 Source 연결 실패

**증상**: `Connection refused` 또는 `Authentication failed`

**해결**:
1. .env의 DB 정보 확인
2. 방화벽 설정 확인
3. Source Asset의 connection 정보 재확인

### B.2 문서 검색 결과 없음

**증상**: 문서 업로드했지만 검색 결과가 없음

**해결**:
1. 문서 인덱싱 상태 확인: `SELECT * FROM documents WHERE embedding IS NULL`
2. pgvector 확장 확인: `SELECT * FROM pg_extension WHERE extname = 'vector'`
3. 문서 검색 인덱스 확인: 마이그레이션 0045 실행 여부

### B.3 LLM 응답 없음

**증상**: OPS 쿼리 시 LLM 응답 없음

**해결**:
1. LLM API 키 확인
2. LLM_BASE_URL 확인 (내부 LLM인 경우)
3. LLM_CALL_LOG 테이블에서 에러 확인

### B.4 Tool 실행 실패

**증상**: `Tool not found` 또는 `Tool execution failed`

**해결**:
1. Tool Asset이 published 상태인지 확인
2. Tool의 capabilities가 올바른지 확인
3. Tool의 source_ref가 유효한지 확인

---

## 부록 C: 고객별 커스터마이징 예시

### C.1 제조업 고객

```yaml
# customer_config.yaml
customer:
  name: "제조사 A"
  industry: manufacturing

terminology:
  server: "설비 서버"
  incident: "장애"
  sla: "4시간"

data_sources:
  cmdb_table: "equipment_assets"
  metric_table: "equipment_metrics"
  event_table: "equipment_events"

queries:
  ci_search: |
    SELECT equipment_id, equipment_name, equipment_type
    FROM equipment_assets
    WHERE equipment_name ILIKE :keyword
```

### C.2 금융권 고객

```yaml
customer:
  name: "은행 B"
  industry: finance

terminology:
  server: "시스템"
  incident: "인시던트"
  sla: "1시간"

data_sources:
  cmdb_table: "it_assets"
  metric_table: "system_metrics"
  event_table: "audit_logs"

compliance:
  data_masking: true
  audit_logging: true
  encryption: "AES-256"
```
