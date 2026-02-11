# Admin System Blueprint

**Last Updated**: 2026-02-11
**Version**: 1.0
**Status**: Production (Core Complete)

---

## 1. 개요

Admin System은 Tobit SPA AI의 **모든 자산(Assets), 도구(Tools), 카탈로그(Catalogs)**를 관리하고, **시스템을 관찰(Observability)하고 디버깅(Inspector)**하며, **회귀 테스트(Regression)**를 수행하는 중앙 관리 시스템입니다.

### 1.1 Admin System의 핵심 목표

1. **자산 관리**: Prompt, Mapping, Query, Policy, Schema, Screen, Tool 등 모든 Asset의 CRUD
2. **카탈로그 관리**: DB 스키마 자동 스캔 및 카탈그 생성
3. **도구 관리**: Tool 등록, 테스트, 발행 (OPS 실행 단위)
4. **검사 및 디버깅**: Trace 분석, Asset 적용 확인, 문제 진단
5. **관찰 가능성**: 시스템 메트릭, 오류율, 실행 통계 모니터링
6. **회귀 테스트**: Golden Query 기반 자동 회귀 테스트

### 1.2 Admin 하위 메뉴 구조

```
Admin Dashboard
├── Assets        - Prompt, Mapping, Query, Policy, Schema Asset CRUD
├── Tools         - Tool Asset 생성, 테스트, 발행
├── Catalogs      - DB 스키마 스캔, 카탈로그 관리
├── Screens       - Screen Asset CRUD, Visual Editor
├── Explorer      - Asset/Tool/Schema 브라우저
├── Settings      - 시스템 설정 (restart_required 표시)
├── Inspector     - Trace ID 기반 실행 분석
├── Regression    - Golden Query 기반 회귀 테스트
├── Observability - 처리량, 지연, 오류율 대시보드
└── Logs          - Query history, execution trace, audit logs
```

---

## 2. 아키텍처

### 2.1 레이어 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                      │
├─────────────────────────────────────────────────────────────────┤
│  /admin/assets  │  /admin/tools  │  /admin/catalogs            │
│  AssetTable      │  ToolTable      │  CatalogTable               │
│  AssetForm       │  ToolTestPanel  │  CatalogScanPanel           │
├─────────────────────────────────────────────────────────────────┤
│                        Backend (FastAPI)                       │
├─────────────────────────────────────────────────────────────────┤
│  asset_registry/router.py  │  tool_router.py                  │
│  Asset CRUD (CRUD)          │  Tool CRUD, Test, Execute        │
│  Catalog CRUD, Scan         │  Publish, Rollback              │
├─────────────────────────────────────────────────────────────────┤
│                        Database (PostgreSQL)                   │
├─────────────────────────────────────────────────────────────────┤
│  tb_asset_registry           │  tb_asset_version               │
│  tb_schema_catalog          │  tb_query_execution_log         │
│  tb_llm_call_log            │  tb_trace                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 핵심 컴포넌트

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| **AssetRegistry** | `apps/api/app/modules/asset_registry/` | Asset CRUD API |
| **ToolRouter** | `apps/api/app/modules/asset_registry/tool_router.py` | Tool 전용 API |
| **AdminDashboard** | `apps/web/src/components/admin/AdminDashboard.tsx` | Admin 대시보드 컴포넌트 |
| **AssetTable** | `apps/web/src/components/admin/AssetTable.tsx` | Asset 목록 테이블 |
| **ToolTable** | `apps/web/src/components/admin/ToolTable.tsx` | Tool 목록 테이블 |
| **CatalogTable** | `apps/web/src/components/admin/CatalogTable.tsx` | Catalog 목록 테이블 |
| **ObservabilityDashboard** | `apps/web/src/components/admin/ObservabilityDashboard.tsx` | 관찰 가능성 대시보드 |

---

## 3. Asset Registry

### 3.1 Asset 정의

**Asset**은 시스템 동작을 코드 수정 없이 변경할 수 있는 **유일한 수단**입니다. 모든 Asset은 `tb_asset_registry` 테이블에 저장됩니다.

### 3.2 Asset 타입별 스펙

| Asset Type | 설명 | 주요 필드 | Stage 바인딩 |
|------------|------|----------|-------------|
| **prompt** | LLM 프롬프트 템플릿 | scope, engine, template, input_schema, output_contract | ROUTE+PLAN, COMPOSE |
| **mapping** | 데이터 매핑 규칙 | mapping_type, content | COMPOSE |
| **query** | DB 쿼리 (SQL/Cypher/HTTP) | query_sql, query_cypher, query_http, query_params | EXECUTE |
| **source** | 데이터 소스 연결 정보 | source_type, connection_string, credentials | EXECUTE |
| **policy** | 실행 정책/보안 규칙 | policy_type, limits | ROUTE+PLAN, VALIDATE |
| **schema** | DB 스키마 정의 (Catalog) | schema_json, tables, columns | ROUTE+PLAN |
| **screen** | UI 화면 정의 | screen_id, schema_json | PRESENT |
| **tool** | 실행 가능한 도구 | tool_type, tool_config, input_schema, output_schema | EXECUTE |

### 3.3 Asset 라이프사이클

```
[draft] → [publish] → [published] → [rollback] → [draft]
         → [delete] → (deleted)
```

- **draft**: 편집 가능 상태
- **published**: 읽기 전용 상태 (OPS에서 적용 가능)
- **rollback**: published → draft로 되돌림
- **delete**: 영구 삭제 (thread-safe)

### 3.4 Asset 버전 관리

- **자동 증가**: `version` 필드는 publish 시 자동 증가
- **버전 스냅샷**: `tb_asset_version` 테이블에 모든 변경 저장
- **롤백 지원**: 이전 버전으로 즉시 복원 가능

---

## 4. Tools System

### 4.1 Tool 정의

**Tool**은 OPS Orchestrator가 호출할 수 있는 **실행 가능한 단위**입니다.

### 4.2 Tool 타입

| Tool Type | 설명 | 실행 방식 |
|-----------|------|----------|
| **sql** | SQL 쿼리 실행 | DirectTool (SQL 바인딩) |
| **http** | HTTP API 호출 | DirectTool (httpx) |
| **python** | Python 스크립트 실행 | DirectTool (exec) |
| **dynamic_tool** | 동적 Asset 참조 | Asset resolve 후 실행 |
| **workflow** | 다중 Tool 연결 | WorkflowExecutor |

### 4.3 Tool 등록 프로세스

```
1. Tool 생성 (/admin/tools)
   ├─ tool_type 선택
   ├─ input_schema 정의 (JSON Schema)
   ├─ output_schema 정의
   └─ tool_config 설정 (연결 정보)

2. Tool 테스트 (Test Panel)
   ├─ 샘플 입력으로 실행
   ├─ 응답 검증
   └─ 디버깅

3. Tool 발행 (publish)
   ├─ status: draft → published
   ├─ version 자동 증가
   └─ OPS에서 호출 가능
```

### 4.4 Tool Catalog

- **내장 Tool**: 시스템 기본 제공 (fetch_device_detail, list_maintenance_filtered 등)
- **사용자 Tool**: 사용자 생성 등록
- **API Manager 연동**: API Definition → Tool로 import

---

## 5. Catalogs System

### 5.1 Catalog 정의

**Catalog**는 DB 스키마 자동 스캔 결과를 저장하여 **LLM이 테이블/컬럼을 인식**할 수 있게 합니다.

### 5.2 Catalog 소스

| 소스 | 설명 | 스캔 방식 |
|-----|------|----------|
| **postgres** | PostgreSQL 테이블 | information_schema 조회 |
| **mysql** | MySQL 테이블 | information_schema 조회 |
| **oracle** | Oracle 테이블 | ALL_TAB_COLUMNS 조회 |
| **neo4j** | Neo4j 노드/관계 | Cypher 조회 |

### 5.3 Catalog 스캔 프로세스

```
1. Catalog 생성 (/admin/catalogs)
   ├─ source_type 선택 (postgres/mysql/oracle/neo4j)
   ├─ connection_string 입력
   └─ name/description 입력

2. 스캔 실행 (Scan 버튼)
   ├─ DB 메타데이터 조회
   ├─ 테이블/컬럼 추출
   └─ tb_schema_catalog에 저장

3. Catalog 발행
   ├─ status: draft → published
   └─ ROUTE+PLAN Stage에서 적용
```

### 5.4 Catalog 스키마

```python
class TbSchemaCatalog(SQLModel, table=True):
    catalog_id: UUID
    source_type: str        # postgres, mysql, oracle, neo4j
    name: str
    connection_string: str
    tables: dict[str, Any]  # {table_name: {columns: [...], relations: [...]}}
    status: str             # draft, published, scanning, failed
    last_scanned_at: datetime
```

---

## 6. Inspector System

### 6.1 Inspector 정의

**Inspector**는 **단일 Trace ID**를 기준으로 실행의 **모든 단계(Stage)**와 **Asset 적용 현황**을 분석하는 디버깅 도구입니다.

### 6.2 Trace 구조

```
Trace
├── trace_id (UUID)
├── plan_validated (PlanOutput)
├── policy_decisions (Policy[])
├── tool_calls (ToolCall[])
├── references (Reference[])
├── applied_assets (AssetRef[])
└── answer_blocks (AnswerBlock[])
```

### 6.3 Inspector UI 구성

| 섹션 | 설명 | 데이터 소스 |
|------|------|-----------|
| **Trace Overview** | 기본 정보, 타임스탬프, 상태 | tb_trace |
| **Applied Assets** | 적용된 Asset 목록 (type, name, version) | tb_asset_applied |
| **Plan** | LLM 생성 계획 (mode, targets, constraints) | trace.plan_validated |
| **Tool Calls** | 실행된 Tool 목록 (input, output, duration) | trace.tool_calls |
| **References** | 참조된 데이터 소스 (table, query, catalog) | trace.references |
| **Answer Blocks** | 생성된 답변 블록 (type, content) | trace.answer_blocks |

### 6.4 Inspector 검색 패턴

| 검색 타입 | 패턴 | 사용 사례 |
|----------|------|----------|
| **trace_id** | 정확한 UUID | 단일 실행 분석 |
| **parent_trace** | 부모 Trace ID | Replan/Rerun 추적 |
| **asset_id** | Asset 식별자 | Asset 영향도 분석 |
| **date_range** | 시간 범위 | 기간별 실행 분석 |

---

## 7. Regression System

### 7.1 Regression 정의

**Regression**은 **Golden Query**라고 불리는 중요 질의 모음을 주기적으로 실행하여 **시스템 변경으로 인한 회귀**를 감지합니다.

### 7.2 Golden Query 구조

```python
class GoldenQuery(SQLModel, table=True):
    query_id: UUID
    name: str
    question: str           # 테스트 질문
    expected_blocks: int    # 예상 답변 블록 수
    tolerance_percent: float  # 허용 오차 (기본 10%)
    enabled: bool           # 활성화 여부
    tags: dict[str, Any]    # 카테고리, 우선순위
```

### 7.3 Regression 실행 프로세스

```
1. Golden Query 생성 (/admin/regression)
   ├─ 질문 입력
   ├─ 예상 결과 정의
   └─ 스케줄 설정

2. 주기적 실행 (Scheduler)
   ├─ 모든 활성화된 Golden Query 조회
   ├─ OPS Orchestrator 실행
   └─ 결과 분석

3. 회귀 감지
   ├─ 결과 블록 수 비교
   ├─ 허용 오차 초과 시 경고
   └── 이슈 생성 (선택)
```

### 7.4 Regression 결과

```python
class RegressionResult(SQLModel, table=True):
    result_id: UUID
    query_id: UUID
    executed_at: datetime
    actual_blocks: int
    expected_blocks: int
    diff_percent: float
    status: str          # passed, failed, warning
    trace_id: UUID       # 디버깅용 참조
```

---

## 8. Observability System

### 8.1 Observability 정의

**Observability**는 시스템의 **처리량, 지연 시간, 오류율**을 실시간으로 모니터링하는 대시보드입니다.

### 8.2 메트릭 카테고리

| 카테고리 | 메트릭 | 데이터 소스 |
|---------|--------|-----------|
| **Throughput** | 요청/sec, 실행/sec | tb_trace |
| **Latency** | p50, p95, p99 지연 | tb_trace |
| **Error Rate** | 실패율, 타임아웃율 | tb_trace |
| **Stage Metrics** | Stage별 소요 시간 | tb_stage_execution |
| **Tool Metrics** | Tool별 호출/실패 | tb_tool_call |
| **Asset Impact** | Asset 적용 빈도 | tb_asset_applied |

### 8.3 Observability Dashboard 구성

```
┌─────────────────────────────────────────────────────────────────┐
│  System Health                                                   │
│  ├─ Overall Status (Healthy/Degraded/Down)                     │
│  └─ Uptime, Request Rate, Error Rate                           │
├─────────────────────────────────────────────────────────────────┤
│  Execution Timeline                                              │
│  ├─ 요청 추이 (시간별)                                          │
│  └─ Stage별 소요 시간                                          │
├─────────────────────────────────────────────────────────────────┤
│  Recent Errors                                                   │
│  ├─ 최근 오류 목록 (trace_id, message)                         │
│  └─ Inspector 링크                                             │
├─────────────────────────────────────────────────────────────────┤
│  Performance Metrics                                             │
│  ├─ p50/p95/p99 지연                                           │
│  └─ 처리량, 오류율                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4 데이터 수집

- **자동 수집**: 모든 OPS 실행이 자동으로 메트릭 기록
- **집계**: 1분, 5분, 15분, 1시간 단위 집계
- **보관**: 30일 (raw), 90일 (aggregated)

---

## 9. Logs System

### 9.1 Logs 정의

**Logs**는 모든 시스템 활동을 **영구적으로 기록**하여 **감사(audit)**, **디버깅**, **분석**에 활용합니다.

### 9.2 로그 타입

| 로그 타입 | 설명 | 테이블 |
|----------|------|-------|
| **Query History** | OPS 질의 기록 | tb_query_execution_log |
| **Execution Trace** | 전체 실행 추적 | tb_trace |
| **Audit Log** | Asset CRUD, 사용자 활동 | tb_audit_log |
| **File Log** | 애플리케이션 로그 | 파일 시스템 |
| **LLM Call Log** | LLM 호출 기록 | tb_llm_call_log |

### 9.3 로그 검색 패턴

| 필터 | 설명 | 예시 |
|-----|------|------|
| **date_range** | 시간 범위 | last_24h, last_7d |
| **user** | 사용자 | user_id = "admin" |
| **asset_id** | Asset 식별자 | asset_id = "uuid" |
| **action_type** | 작업 타입 | create, update, delete, publish |
| **status** | 상태 | success, failed |

---

## 10. Settings System

### 10.1 Settings 정의

**Settings**는 시스템 전역 설정을 관리하며, **변경 시 재시작 여부**를 명확히 표시합니다.

### 10.2 설정 카테고리

| 카테고리 | 설정 예시 | restart_required |
|---------|----------|-----------------|
| **Database** | connection_string, pool_size | Yes |
| **LLM** | provider, base_url, default/fallback_model, timeout/retry, routing_policy | Mixed |
| **Cache** | redis_url, ttl | Yes |
| **Security** | jwt_secret, encryption_key | Yes |
| **Observability** | log_level, metrics_enabled | No |

### 10.3 Settings UI

```typescript
interface Setting {
  key: string;
  value: string | number | boolean;
  type: "string" | "number" | "boolean" | "json";
  category: string;
  description: string;
  restart_required: boolean;  // ⚠️ 표시
}
```

### 10.4 LLM Runtime 적용 우선순위

LLM 관련 설정은 아래 우선순위로 해석됩니다.

1. `tb_operation_settings`의 published 값
2. `apps/api/.env` 또는 `.env.example` 기본값

핵심 키:
- `llm_provider` (`openai` | `internal`)
- `llm_base_url` (internal/OpenAI-compatible endpoint)
- `llm_default_model`, `llm_fallback_model`
- `llm_timeout_seconds`, `llm_max_retries`, `llm_enable_fallback`, `llm_routing_policy`

적용 지점:
- `app/llm/client.py`에서 런타임 로드 및 provider별 클라이언트 초기화
- OPS ALL / Query Decomposition 러너는 provider 가용성 검사 시 `is_llm_available(settings)`를 사용

---

## 11. Security & Permissions

### 11.1 RBAC (Role-Based Access Control)

| 역할 | 권한 |
|-----|------|
| **admin** | 모든 Asset/Tool/Catalog CRUD, Settings 변경, Logs 조회 |
| **operator** | Asset 조회, Tool 테스트, Inspector, Observability 조회 |
| **viewer** | 읽기 전용 (Assets, Tools, Catalogs, Observability) |

### 11.2 Asset 권한

- **draft**: 작성자만 편집 가능
- **published**: admin만 수정 가능 (rollback 허용)
- **delete**: admin 또는 작성자

### 11.3 Audit Trail

모든 Asset 변경은 `tb_audit_log`에 기록됩니다.

```python
class AuditLog(SQLModel, table=True):
    log_id: UUID
    user_id: str
    action: str           # create, update, delete, publish, rollback
    asset_type: str
    asset_id: UUID
    old_value: dict       # 이전 값 (JSON)
    new_value: dict       # 새 값 (JSON)
    created_at: datetime
```

---

## 12. API 엔드포인트

### 12.1 Asset Registry API

| 엔드포인트 | 메서드 | 설명 |
|----------|--------|------|
| `/asset-registry/assets` | GET | Asset 목록 조회 (필터 지원) |
| `/asset-registry/assets` | POST | Asset 생성 |
| `/asset-registry/assets/{asset_id}` | GET | Asset 상세 조회 |
| `/asset-registry/assets/{asset_id}` | PUT | Asset 업데이트 |
| `/asset-registry/assets/{asset_id}` | DELETE | Asset 삭제 |
| `/asset-registry/assets/{asset_id}/publish` | POST | Asset 발행 |
| `/asset-registry/assets/{asset_id}/rollback` | POST | Asset 롤백 |
| `/asset-registry/assets/{asset_id}/versions` | GET | Asset 버전 목록 |

### 12.2 Tools API

| 엔드포인트 | 메서드 | 설명 |
|----------|--------|------|
| `/asset-registry/tools` | GET | Tool 목록 조회 |
| `/asset-registry/tools` | POST | Tool 생성 |
| `/asset-registry/tools/{tool_id}/test` | POST | Tool 테스트 |
| `/asset-registry/tools/{tool_id}/publish` | POST | Tool 발행 |
| `/asset-registry/tools/{tool_id}/execute` | POST | Tool 실행 |

### 12.3 Catalogs API

| 엔드포인트 | 메서드 | 설명 |
|----------|--------|------|
| `/asset-registry/catalogs` | GET | Catalog 목록 조회 |
| `/asset-registry/catalogs` | POST | Catalog 생성 |
| `/asset-registry/catalogs/{catalog_id}/scan` | POST | DB 스캔 실행 |
| `/asset-registry/catalogs/{catalog_id}/publish` | POST | Catalog 발행 |

### 12.4 Inspector API

| 엔드포인트 | 메서드 | 설명 |
|----------|--------|------|
| `/admin/inspector/traces/{trace_id}` | GET | Trace 상세 조회 |
| `/admin/inspector/traces` | GET | Trace 목록 (필터 지원) |
| `/admin/inspector/assets/{asset_id}/traces` | GET | Asset별 Trace 목록 |
| `/admin/inspector/stage/{stage_name}/metrics` | GET | Stage별 메트릭 |

### 12.5 Regression API

| 엔드포인트 | 메서드 | 설명 |
|----------|--------|------|
| `/admin/regression/golden-queries` | GET | Golden Query 목록 |
| `/admin/regression/golden-queries` | POST | Golden Query 생성 |
| `/admin/regression/run` | POST | 회귀 테스트 실행 |
| `/admin/regression/results` | GET | 회귀 테스트 결과 |

---

## 13. 데이터 모델

### 13.1 핵심 테이블

| 테이블 | 설명 | 주요 필드 |
|-------|------|----------|
| `tb_asset_registry` | Asset 마스터 | asset_id, asset_type, name, status, version |
| `tb_asset_version` | Asset 버전 스냅샷 | version_id, asset_id, content, created_at |
| `tb_schema_catalog` | DB 스키마 카탈로그 | catalog_id, source_type, tables, status |
| `tb_trace` | OPS 실행 추적 | trace_id, plan, tool_calls, answer_blocks |
| `tb_llm_call_log` | LLM 호출 로그 | call_id, model, tokens, duration |
| `tb_golden_query` | 회귀 테스트 질의 | query_id, question, expected_blocks |
| `tb_regression_result` | 회귀 테스트 결과 | result_id, query_id, status, diff_percent |
| `tb_audit_log` | 감사 로그 | log_id, user_id, action, asset_id |

### 13.2 인덱스 전략

- **asset_type + status**: Asset 목록 조회 최적화
- **trace_id**: Trace 조회 (Primary Key)
- **created_at**: 시간 범위 기반 조회
- **user_id + action_type**: 감사 로그 조회

---

## 14. Frontend Components

### 14.1 Asset 관리

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `AssetTable` | `components/admin/AssetTable.tsx` | Asset 목록 테이블 |
| `AssetForm` | `components/admin/AssetForm.tsx` | Asset 생성/편집 폼 |
| `CreateAssetModal` | `components/admin/CreateAssetModal.tsx` | Asset 생성 모달 |
| `AssetImpactAnalyzer` | `components/admin/AssetImpactAnalyzer.tsx` | Asset 영향도 분석 |

### 14.2 Tool 관리

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `ToolTable` | `components/admin/ToolTable.tsx` | Tool 목록 테이블 |
| `ToolTestPanel` | `components/admin/ToolTestPanel.tsx` | Tool 테스트 패널 |
| `CreateToolModal` | `components/admin/CreateToolModal.tsx` | Tool 생성 모달 |

### 14.3 Catalog 관리

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `CatalogTable` | `components/admin/CatalogTable.tsx` | Catalog 목록 테이블 |
| `CatalogScanPanel` | `components/admin/CatalogScanPanel.tsx` | DB 스캔 패널 |
| `CatalogViewerPanel` | `components/admin/CatalogViewerPanel.tsx` | 스키마 뷰어 |
| `CreateCatalogModal` | `components/admin/CreateCatalogModal.tsx` | Catalog 생성 모달 |

### 14.4 Inspector

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `InspectorPanel` | `components/admin/inspector/InspectorPanel.tsx` | Inspector 메인 패널 |
| `TraceDiffView` | `components/admin/TraceDiffView.tsx` | Trace 비교 뷰 |
| `StageDiffView` | `components/admin/StageDiffView.tsx` | Stage별 비교 |

### 14.5 Observability

| 컴포넌트 | 경로 | 역할 |
|---------|------|------|
| `ObservabilityDashboard` | `components/admin/ObservabilityDashboard.tsx` | 관찰 가능성 대시보드 |
| `SystemHealthChart` | `components/admin/observability/SystemHealthChart.tsx` | 시스템 건전도 차트 |
| `ExecutionTimeline` | `components/admin/observability/ExecutionTimeline.tsx` | 실행 타임라인 |
| `RecentErrors` | `components/admin/observability/RecentErrors.tsx` | 최근 오류 목록 |
| `PerformanceMetrics` | `components/admin/observability/PerformanceMetrics.tsx` | 성능 메트릭 |

---

## 15. 확장 포인트

### 15.1 새 Asset 타입 추가

1. `models.py`에 새 필드 추가
2. `schemas.py`에 Pydantic 모델 추가
3. `crud.py`에 CRUD 함수 추가
4. Frontend Form 생성

### 15.2 새 Tool 타입 추가

1. `tool_router.py`에 새 실행기 추가
2. Frontend Test Panel 업데이트
3. Input/Output Schema 정의

### 15.3 새 Catalog 소스 추가

1. `catalog_factory.py`에 새 스캐너 추가
2. Connection String 포맷 정의
3. Schema 변환 로직 구현

---

## 16. 향후 작업 (미완료)

### 16.1 인증/접근 제어 고도화

- [ ] `Admin > Settings`에서 JWT 전용 / API Key 전용 / Hybrid 모드 전환 지원
- [ ] API Key 스코프를 엔드포인트 그룹(예: `/ops/*`, `/sim/*`) 단위로 정책화
- [ ] `tb_api_key` 사용 현황(마지막 사용 시각, 호출량, 실패율) 대시보드 제공

### 16.2 멀티 테넌트/사용자 운영

- [ ] Tenant/User/Role 관리 UI 통합 (`Admin > Settings` 또는 `Admin > IAM`)
- [ ] tenant/user 정합성 검사 배치 및 경고 알림 추가
- [ ] 메뉴 가시성(프론트)과 API 권한(백엔드) 매핑 테이블 단일화

### 16.3 운영 자동화/품질

- [ ] Regression 실패 시 자동 재현 실행 및 원인 분류(데이터/정책/코드)
- [ ] Audit 로그 이상 징후 탐지(권한 상승, 비정상 다량 변경) 룰 엔진 추가
- [ ] Settings 변경 이력에 승인 워크플로(2인 승인) 선택 적용

---

**마지막 정리**: 2026-02-11
**상태**: 상용 운영 가능 (핵심 완료, 고도화 과제 진행)
