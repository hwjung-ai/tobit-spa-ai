# 🔧 프로젝트 Assets 설정 분석 보고서

**작성일**: 2026-02-16
**총 Assets**: 42개 (Published: 36, Draft: 6)
**분석 범위**: Asset Registry Tools 및 설정

---

## 📊 Executive Summary

### 현황
- **총 등록 Tools**: 42개
- **활성(Published)**: 36개 ✅
- **개발중(Draft)**: 6개 📝
- **주요 도구 타입**: Database Query (35), Graph Query (1), HTTP API (3), MCP (3)
- **데이터 소스**: PostgreSQL (2개), Neo4j (1개)

### 주요 발견사항
1. ✅ **Database Query 도구가 대부분** - 83% (35/42)
2. ⚠️ **중복 도구 발견** - "maintenance_history", "bom_lookup", "production_status" 등 여러 버전
3. 🟡 **MCP Tools는 Draft 상태** - 프로덕션 통합 미완료
4. ✅ **일관된 재시도 정책** - Factory PostgreSQL 도구들은 max_retries: 3
5. ⚠️ **이름 없는 Draft 도구 2개** - 명명 규칙 미적용

---

## 📋 Tool 분류 및 구성

### 1️⃣ **Database Query Tools (35개)**

#### A. Default PostgreSQL (23개 도구) - Operations/ITSM

**카테고리: CI Management**
- `ci_detail_lookup` - CI 상세정보 조회
- `ci_summary_aggregate` - CI 분포 통계
- `ci_list_paginated` - CI 목록 (페이징)
- `ci_aggregation` - CI 집계 통계
- `ci_graph_query` - CI 관계/의존성
- `ci_search` - CI 키워드 검색

**카테고리: Work History & Maintenance**
- `maintenance_history_list` - 유지보수 기록
- `maintenance_ticket_create` - 유지보수 티켓 생성 (INSERT)
- `work_history_query` - 작업 이력
- `history_combined_union` - 통합 이력 (work + maintenance)
- `work_history` - 작업 이력 조회

**카테고리: Metrics**
- `metric_list` - 메트릭 정의 목록
- `metric_query` - CI별 메트릭 조회
- `metric` - 메트릭 값 (집계)
- `metric_series` - 시계열 메트릭
- `metric_aggregate_by_ci` - CI별 메트릭 집계

**카테고리: Events & Logs**
- `event_log` - 이벤트 로그 조회
- `event_aggregate` - 이벤트 집계
- `history` - 이벤트+유지보수 이력

**설정 특징**:
- ✅ 매개변수화 쿼리 (SQL injection 방지)
- ✅ 다양한 필터링 옵션
- ✅ 테넌트 격리 (tenant_id 필수)
- 🟡 Timeout 미설정 (일부만 설정)

**입력 스키마 예시**:
```json
// metric_query
{
  "tenant_id": "string (required)",
  "ci_code": "string (required)",
  "metric_name": "string (required)",
  "start_time": "datetime (required)",
  "end_time": "datetime (required)",
  "limit": "integer (required)"
}
```

---

#### B. Factory PostgreSQL (12개 도구) - Manufacturing/Operations

**카테고리: Equipment**
- `equipment_search` - 장비 검색 (keyword ILIKE)
- `maintenance_history` (2x) - 장비별 유지보수 이력

**카테고리: Production**
- `production_status` (2x) - 생산 현황 조회
- `bom_lookup` (2x) - 제품 BOM(부품구성)

**카테고리: Operations**
- `worker_schedule` (2x) - 근무자 일정
- `energy_consumption` (2x) - 에너지 소비량

**설정 특징**:
- ✅ 일관된 재시도 정책: `max_retries: 3`
- ✅ 일관된 타임아웃: `timeout_ms: 30000` (30초)
- ✅ 모두 Published 상태
- ✅ Input/Output 스키마 정의

**설정 예시**:
```json
{
  "source_ref": "factory_postgres",
  "timeout_ms": 30000,
  "max_retries": 3,
  "query_template": "SELECT * FROM equipment WHERE name ILIKE '%{keyword}%' LIMIT {limit}"
}
```

---

### 2️⃣ **Graph Query Tools (1개)**

**`ci_graph`** - CI 관계도 쿼리
- **Source**: default_neo4j
- **타입**: MATCH path = (source)-[*1..{depth}]->(target)
- **지원 Views**: dependency, composition, impact, path
- **입력**: source_ids, depth, view
- **Status**: Published ✅

```json
{
  "source_ref": "default_neo4j",
  "query_template": "MATCH path = (source)-[*1..{depth}]->(target) WHERE source.ci_id IN {source_ids}..."
}
```

---

### 3️⃣ **HTTP API Tools (3개)**

**`document_search`** - 문서 검색 (하이브리드)

| 버전 | Status | 설정 |
|------|--------|------|
| v1 | Published | endpoint: POST /api/documents/search |
| v2 | Draft | bearer_token 인증 |
| v3 | Draft | bearer_token 인증 |

**Request Body Template**:
```json
{
  "query": "검색어",
  "top_k": 10,
  "search_type": "hybrid",  // "text", "vector", "hybrid"
  "min_relevance": 0.0
}
```

**설정 특징**:
- ✅ Vector + BM25 하이브리드 검색
- ✅ pgvector 임베딩 사용
- 🟡 Draft 버전들에 bearer_token 인증 추가 (개발 중)

---

### 4️⃣ **MCP Tools (3개)** - 🟡 Draft 상태

**Server**: http://localhost:3100 (streamable_http)

| Tool | Status | 입력 | 설명 |
|------|--------|------|------|
| `mcp_get_time` | Draft | format (optional) | 현재 서버 시간 |
| `mcp_echo` | Draft | message (required) | 메시지 반향 |
| `mcp_add` | Draft | a, b (required) | 두 수 더하기 |

**설정**:
```json
{
  "tool_name": "get_time",
  "transport": "streamable_http",
  "server_url": "http://localhost:3100",
  "timeout_ms": 30000
}
```

**현황**:
- ✅ 테스트 서버 실행 중
- ⏳ 프로덕션 환경으로 이관 예정
- 🔧 사용자 정의 MCP 서버 추가 가능

---

## 🔴 문제점 및 개선사항

### 1. **중복 도구 (Duplicate Tools)**

```
❌ Problem: 같은 도구가 여러 버전으로 등록됨
```

| 도구명 | 버전 1 ID | 버전 2 ID | 원인 |
|--------|-----------|-----------|------|
| maintenance_history | bf9c5a4b | e1264ede | 중복 seed |
| bom_lookup | 1f236e98 | 626401fa | 중복 seed |
| production_status | c9c6f222 | 50eb7fc8 | 중복 seed |
| worker_schedule | fa6bcadf | 7a875ccc | 중복 seed |
| energy_consumption | 3d2359a5 | e8a0123c | 중복 seed |
| equipment_search | 79bd417d | 632b62d6 | 중복 seed |

**권장사항**:
- 중복 도구 제거
- Seed script 검증
- Tool Asset 통합 (factory_postgres tools 정리)

---

### 2. **MCP Tools - Draft 상태**

```
🟡 Status: 테스트만 완료, 프로덕션 미통합
```

**현황**:
- ✅ MCP 서버 연결 (localhost:3100)
- ✅ 도구 등록 (draft)
- ⏳ 네비게이션에서 선택 불가

**필요한 작업**:
1. ✅ Production MCP 서버 배포
2. ✅ 도구 상태를 "published"로 변경
3. ✅ OPS 오케스트레이터에 통합

---

### 3. **이름 없는 Draft 도구**

```
⚠️ Problem: 명명 규칙 미적용
```

- **ID**: f44e71f1-92e3-4963-b729-b770620ea3df
- **Description**: Query work history (maintenance/change records) for CIs
- **Source**: default_postgres

**원인**: 수동 생성 시 이름 필드 누락

**권장사항**:
- `work_history_detail` 또는 `ci_work_history_detailed`로 명명
- Draft 도구 검토 체계 수립

---

### 4. **Timeout & Retry Policy 불일치**

| Source | Timeout | Max Retries | 설정 수준 |
|--------|---------|------------|----------|
| default_postgres | ❌ 미설정 | ❌ 미설정 | 낮음 |
| factory_postgres | ✅ 30초 | ✅ 3회 | 높음 |
| default_neo4j | ❌ 미설정 | ❌ 미설정 | 낮음 |

**문제점**:
- default_postgres 도구들이 실패해도 재시도 없음
- 네트워크 오류 시 사용자 영향 증가

**권장사항**:
```json
// default_postgres 도구에 추가
{
  "timeout_ms": 30000,
  "max_retries": 3,
  "retry_backoff_ms": 500
}
```

---

### 5. **Input Schema 정의 불일치**

**현황**:
- ✅ 대부분의 도구: 명확한 입력 스키마
- 🟡 일부 도구: 선택적 필드만 있거나 미정의

**예시 - 개선이 필요한 도구**:

```json
// ci_lookup - 모든 필드가 선택적
{
  "type": "object",
  "properties": {
    "keywords": {"type": "array"},
    "filters": {"type": "array"},
    "limit": {"type": "integer", "default": 10}
  }
  // ❌ "required": [] - 필수 필드 없음
}
```

**권장사항**:
```json
{
  "type": "object",
  "required": ["source_ids"],
  "properties": {
    "source_ids": {"type": "array", "minItems": 1},
    "keywords": {"type": "array"},
    "filters": {"type": "array"},
    "limit": {"type": "integer", "default": 10}
  }
}
```

---

## 🔗 데이터 소스 구성

### **default_postgres** (23개 도구)

**특징**:
- ITSM/Operations 데이터
- 테넌트 격리 필수
- 일관된 쿼리 패턴

**연결 설정** (예상):
```
Host: localhost or POSTGRES_HOST
Port: 5432
Database: spa
User: spa
```

**테스트**:
```bash
curl -X POST http://localhost:8000/asset-registry/tools/test \
  -H "Content-Type: application/json" \
  -H "X-Debug-User-Id: test-user" \
  -d '{
    "asset_id": "70f6b0ed-49b7-403e-b368-01fb36f4c9f4",
    "test_params": {"tenant_id": "test-tenant", "limit": 10}
  }'
```

---

### **factory_postgres** (12개 도구)

**특징**:
- 제조/운영 데이터
- 재시도 정책 적용
- 타임아웃 설정됨

**연결 설정** (예상):
```
Host: factory-db.internal or FACTORY_POSTGRES_HOST
Port: 5432
Database: factory
User: spa_user
```

**설정 확인**:
```python
# Asset Registry에서 확인 가능
tool = get_tool("equipment_search")
config = tool.tool_config
print(config["source_ref"])  # "factory_postgres"
print(config["timeout_ms"])  # 30000
```

---

### **default_neo4j** (1개 도구)

**특징**:
- CI 관계도 데이터
- Cypher 쿼리
- 변수 깊이 지원

**연결 설정** (예상):
```
URI: neo4j://localhost:7687 or NEO4J_URI
Auth: neo4j/password
```

---

## 💾 Tool Asset 레지스트리 데이터 모델

### Table: `tb_asset_registry`

```sql
CREATE TABLE tb_asset_registry (
  -- 기본
  asset_id UUID PRIMARY KEY,
  asset_type VARCHAR(50),          -- "tool", "prompt", "query", "schema", ...
  name VARCHAR(255),
  description TEXT,
  version INTEGER,
  status VARCHAR(50),              -- "draft", "published"

  -- Tool 관련 필드
  tool_type VARCHAR(50),           -- "database_query", "http_api", "graph_query", "mcp"
  tool_config JSONB,               -- source_ref, query_template, timeout_ms, ...
  tool_input_schema JSONB,         -- JSON Schema for inputs
  tool_output_schema JSONB,        -- JSON Schema for outputs

  -- 메타데이터
  created_by VARCHAR(255),
  published_by VARCHAR(255),
  published_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Audit
  tenant_id UUID,
  tags JSONB
);
```

### Tool Config 구조

#### Database Query Tools
```json
{
  "source_ref": "default_postgres|factory_postgres|default_neo4j",
  "query_template": "SELECT ... WHERE {param1} AND {param2}",
  "timeout_ms": 30000,
  "max_retries": 3
}
```

#### HTTP API Tools
```json
{
  "endpoint": "https://api.example.com/search",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer {token}",
    "Content-Type": "application/json"
  },
  "body_template": {
    "query": "{query}",
    "top_k": "{top_k}"
  },
  "auth_type": "bearer_token|api_key|basic"
}
```

#### MCP Tools
```json
{
  "tool_name": "get_time",
  "server_url": "http://localhost:3100",
  "transport": "streamable_http|sse",
  "timeout_ms": 30000
}
```

---

## 📊 사용량 통계

### By Status
- **Published**: 36개 (85.7%)
- **Draft**: 6개 (14.3%)

### By Type
- **Database Query**: 35개 (83.3%)
- **HTTP API**: 3개 (7.1%)
- **MCP**: 3개 (7.1%)
- **Graph Query**: 1개 (2.4%)

### By Source
- **default_postgres**: 23개 (54.8%)
- **factory_postgres**: 12개 (28.6%)
- **HTTP**: 3개 (7.1%)
- **default_neo4j**: 1개 (2.4%)
- **MCP**: 3개 (7.1%)

### Configuration Coverage
- **Input Schema 정의**: 41/42 (97.6%) ✅
- **Output Schema 정의**: 일부
- **Timeout 설정**: 15/42 (35.7%) 🟡
- **Retry Policy**: 12/42 (28.6%) 🟡

---

## 🎯 권장사항 (우선순위)

### P0 - 즉시 처리
1. ✅ **중복 도구 제거**
   - maintenance_history, bom_lookup 등 중복 제거
   - Seed script 정리

2. ✅ **MCP Tools 프로덕션 이관**
   - localhost:3100 → 프로덕션 서버
   - Draft → Published 상태 변경

### P1 - 이번 주
3. ✅ **Timeout/Retry Policy 표준화**
   - default_postgres: timeout_ms 30000, max_retries 3 추가
   - default_neo4j: 유사하게 설정

4. ✅ **Input Schema 검증**
   - 필수 필드 명확히
   - Optional 필드에는 default 값 제공

### P2 - 이번 달
5. ✅ **Tool 명명 규칙 수립**
   - Naming convention 문서화
   - Draft 도구 검토 프로세스

6. ✅ **Output Schema 완성**
   - 모든 도구에 output_schema 정의
   - API 클라이언트 코드 생성 (OpenAPI)

---

## 📖 참고 자료

### API Endpoints

#### Tool 관리
- `GET /asset-registry/tools` - Tool 목록 조회
- `GET /asset-registry/tools/{asset_id}` - Tool 상세조회
- `POST /asset-registry/tools` - Tool 생성
- `PUT /asset-registry/tools/{asset_id}` - Tool 수정
- `DELETE /asset-registry/tools/{asset_id}` - Tool 삭제
- `POST /asset-registry/tools/{asset_id}/publish` - 발행
- `POST /asset-registry/tools/{asset_id}/test` - 도구 테스트

#### Source 관리
- `GET /asset-registry/sources` - Data source 목록
- `POST /asset-registry/sources/test` - Source 연결 테스트

### 주요 파일

```
apps/api/
  ├─ app/modules/
  │  ├─ asset_registry/
  │  │  ├─ models.py           # TbAssetRegistry
  │  │  ├─ tool_router.py      # Tool API endpoints
  │  │  ├─ schemas.py          # Pydantic schemas
  │  │  └─ crud.py             # CRUD operations
  │  ├─ ops/
  │  │  └─ services/
  │  │     └─ orchestration/
  │  │        └─ tools/        # Tool runtime
  │  │           ├─ registry_init.py
  │  │           ├─ dynamic_tool.py
  │  │           └─ direct_query_tool.py
```

---

## 🔐 보안 고려사항

### ✅ 현재 적용된 보안 정책

1. **SQL Injection 방지**
   - 모든 쿼리가 매개변수화됨
   - `{param}` 플레이스홀더 사용

2. **테넌트 격리**
   - 쿼리에서 `tenant_id` 필터링 필수
   - default_postgres 도구 대부분 적용

3. **쿼리 검증**
   - DDL/DCL 차단 (CREATE, ALTER, DROP, GRANT, REVOKE)
   - 읽기 전용 정책 (INSERT/UPDATE/DELETE 차단, maintenance_ticket_create 제외)

### 🟡 개선이 필요한 부분

1. **사용자 권한 검증**
   - 도구별 접근 제어 (RBAC) 미구현
   - 누구나 모든 도구 실행 가능

2. **속도 제한 (Rate Limiting)**
   - Tool 별 호출 제한 없음
   - DOS 공격 위험

3. **감사 로깅**
   - Tool 실행 이력 추적 필요
   - 누가, 언제, 어떤 도구를 실행했는지 기록

---

## 🚀 다음 단계

1. **이번 주**: 중복 도구 제거 + MCP 프로덕션 이관
2. **다음 주**: 재시도 정책 표준화 + Input Schema 검증
3. **3주 후**: 명명 규칙 수립 + Output Schema 완성
4. **1개월 후**: 접근 제어 + 감사 로깅 구현

---

**문서 끝**
