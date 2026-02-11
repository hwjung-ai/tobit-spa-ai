# Admin System - 사용자 가이드

**Last Updated**: 2026-02-10

## 문서의 성격

이 문서는 Admin System을 처음 사용하는 운영자가 **자산(Assets), 도구(Tools), 카탈로그(Catalogs)**를 관리하고, **Inspector로 디버깅**하며, **Observability로 시스템을 관찰**할 수 있도록 돕는 튜토리얼입니다.

핵심 목표:
1. Asset/Tool/Catalog CRUD를 직접 수행한다.
2. Inspector로 실행 문제를 진단한다.
3. Observability로 시스템 건전성을 모니터링한다.
4. Regression 테스트로 회귀를 감지한다.

---

## 목차

1. [시작 전 준비](#0-시작-전-준비)
2. [Lab 1 - Assets 관리](#1-lab-1---assets-관리)
3. [Lab 2 - Tools 생성 및 테스트](#2-lab-2---tools-생성-및-테스트)
4. [Lab 3 - Catalogs로 DB 스키마 관리](#3-lab-3---catalogs로-db-스키마-관리)
5. [Lab 4 - Inspector로 Trace 분석](#4-lab-4---inspector로-trace-분석)
6. [Lab 5 - Observability 대시보드](#5-lab-5---observability-대시보드)
7. [Lab 6 - Regression 테스트 설정](#6-lab-6---regression-테스트-설정)
8. [Lab 7 - Settings 관리](#7-lab-7---settings-관리)
9. [Lab 8 - Logs로 시스템 활동 추적](#8-lab-8---logs로-시스템-활동-추적)
10. [운영 부록 - 문제 해결 패턴](#9-운영-부록---문제-해결-패턴)

---

## 0. 시작 전 준비

### 0.1 Admin 접근

1. `/admin` 접속
2. 상단 탭에서 원하는 메뉴 선택

### 0.2 Admin 하위 메뉴

| 메뉴 | 경로 | 용도 |
|------|------|------|
| Assets | `/admin/assets` | Prompt, Mapping, Query, Policy, Schema Asset CRUD |
| Tools | `/admin/tools` | Tool 생성, 테스트, 발행 |
| Catalogs | `/admin/catalogs` | DB 스키마 스캔, 카탈로그 관리 |
| Screens | `/admin/screens` | Screen Asset CRUD (별도 가이드: USER_GUIDE_SCREEN_EDITOR.md) |
| Explorer | `/admin/explorer` | Asset/Tool/Schema 브라우저 |
| Settings | `/admin/settings` | 시스템 설정 |
| Inspector | `/admin/inspector` | Trace 분석 |
| Regression | `/admin/regression` | Golden Query 기반 회귀 테스트 |
| Observability | `/admin/observability` | 시스템 메트릭 대시보드 |
| Logs | `/admin/logs` | Query history, execution trace, audit logs |

### 0.3 필수 권한

| 작업 | 필요 권한 |
|------|----------|
| Asset CRUD | admin |
| Tool 생성/발행 | admin |
| Catalog 스캔 | admin |
| Inspector 조회 | operator, admin |
| Observability 조회 | viewer, operator, admin |
| Settings 변경 | admin |

---

## 1. Lab 1 - Assets 관리

목표: Asset CRUD 기본 흐름을 익힌다.

### Step 1. Asset 목록 진입

1. `/admin/assets` 접속
2. Asset Type 필터로 원하는 타입 선택 (prompt, mapping, query, policy, schema)

### Step 2. Query Asset 생성 (예시)

1. **"Create Asset"** 버튼 클릭
2. Create Asset Modal에서 설정:
   - **Asset Type**: `query`
   - **Name**: `get_device_events`
   - **Description**: 장비 이벤트 조회
3. Query Asset Form에서 상세 입력:
   - **query_sql**:
     ```sql
     SELECT
         timestamp, device_id, event_type, severity
     FROM event_log
     WHERE tenant_id = :tenant_id
       AND device_id = :device_id
     ORDER BY timestamp DESC
     LIMIT :limit
     ```
   - **query_params**:
     ```json
     {
       "tenant_id": {"type": "string", "required": true},
       "device_id": {"type": "string", "required": true},
       "limit": {"type": "integer", "default": 100}
     }
     ```
4. **"Save as Draft"** 클릭

검증 포인트:
- Asset 목록에 `get_device_events`가 표시된다.
- 상태가 `draft`로 표시된다.

### Step 3. Asset 편집

1. 목록에서 Asset 클릭
2. Asset Form에서 내용 수정
3. **"Update"** 클릭

### Step 4. Asset 발행

1. 목록에서 Asset 선택
2. **"Publish"** 버튼 클릭
3. 확인 대화상자에서 **"Confirm"** 클릭

검증 포인트:
- 상태가 `published`로 변경된다.
- 버전이 1 증가한다.

### Step 5. Asset 롤백

1. 발행된 Asset 선택
2. **"Rollback"** 버튼 클릭
3. 이전 버전 선택 (또는 직전 버전)
4. **"Confirm"** 클릭

검증 포인트:
- 상태가 `draft`로 변경된다.
- 버전이 감소하지 않는다 (새 draft 생성).

---

## 2. Lab 2 - Tools 생성 및 테스트

목표: Tool을 직접 만들고 테스트한다.

### Step 1. Tool 목록 진입

1. `/admin/tools` 접속
2. Tool Type 필터로 원하는 타입 선택

### Step 2. SQL Tool 생성

1. **"Create Tool"** 버튼 클릭
2. Create Tool Modal에서 설정:
   - **Tool Type**: `sql`
   - **Name**: `fetch_device_events`
   - **Description**: 장비 이벤트 조회 Tool
3. Tool Form에서 상세 입력:
   - **source_ref**: `default_postgres` (catalog 기반 접속)
   - **query_template**:
     ```sql
     SELECT
         timestamp, device_id, event_type, severity
     FROM event_log
     WHERE tenant_id = :tenant_id
       AND device_id = :device_id
     ORDER BY timestamp DESC
     LIMIT :limit
     ```
   - **input_schema**:
     ```json
     {
       "type": "object",
       "properties": {
         "tenant_id": {"type": "string"},
         "device_id": {"type": "string"},
         "limit": {"type": "integer", "default": 100}
       },
       "required": ["tenant_id", "device_id"]
     }
     ```
   - **output_schema**:
     ```json
     {
       "type": "object",
       "properties": {
         "rows": {
           "type": "array",
           "items": {
             "type": "object",
             "properties": {
               "timestamp": {"type": "string"},
               "device_id": {"type": "string"},
               "event_type": {"type": "string"},
               "severity": {"type": "string"}
             }
           }
         }
       }
     }
     ```
4. **"Save as Draft"** 클릭

### Step 3. Tool 테스트

1. 목록에서 Tool 선택
2. **"Test"** 버튼 클릭
3. Test Panel이 우측에 표시됨
4. Test Payload 입력:
   ```json
   {
     "tenant_id": "t1",
     "device_id": "DEV-001",
     "limit": 10
   }
   ```
5. **"Run Test"** 클릭

검증 포인트:
- **Result** 영역에 실행 결과가 표시된다.
- **Duration**에 실행 시간이 표시된다.
- 오류 발생 시 **Error** 메시지가 표시된다.

### Step 4. Tool 발행

1. 테스트 성공 확인
2. **"Publish"** 버튼 클릭
3. 확인 대화상자에서 **"Confirm"** 클릭

검증 포인트:
- 상태가 `published`로 변경된다.
- OPS Orchestrator에서 호출 가능하다.

---

## 3. Lab 3 - Catalogs로 DB 스키마 관리

목표: DB 스키마를 자동 스캔하여 Catalog를 생성한다.

### Step 1. Catalog 목록 진입

1. `/admin/catalogs` 접속
2. Catalog 목록 확인

### Step 2. PostgreSQL Catalog 생성

1. **"Create Catalog"** 버튼 클릭
2. Create Catalog Modal에서 설정:
   - **Source Type**: `postgres`
   - **Name**: `production_postgres`
   - **Description**: 운영 PostgreSQL 카탈로그
   - **Connection String**: `postgresql://user:pass@host:5432/dbname`
3. **"Create"** 클릭

검증 포인트:
- Catalog 목록에 `production_postgres`가 표시된다.
- 상태가 `draft`로 표시된다.

### Step 3. DB 스캔 실행

1. 목록에서 Catalog 선택
2. **"Scan"** 버튼 클릭
3. Scan Panel이 우측에 표시됨
4. **"Start Scan"** 클릭

검증 포인트:
- 상태가 `scanning`으로 변경된다.
- 스캔 완료 후 상태가 `draft`로 변경된다.
- **Tables** 컬럼에 테이블 수가 표시된다.

### Step 4. 스키마 확인

1. 목록에서 Catalog 선택
2. **"View Schema"** 버튼 클릭
3. Catalog Viewer Panel에 스키마 표시

검증 포인트:
- 테이블 목록이 표시된다.
- 각 테이블의 컬럼 정보가 표시된다.
- 관계(relation) 정보가 표시된다.

### Step 5. Catalog 발행

1. 스키마 확인 완료
2. **"Publish"** 버튼 클릭
3. 확인 대화상자에서 **"Confirm"** 클릭

검증 포인트:
- 상태가 `published`로 변경된다.
- OPS ROUTE+PLAN Stage에서 적용된다.
- LLM이 테이블/컬럼을 인식할 수 있다.

---

## 4. Lab 4 - Inspector로 Trace 분석

목표: 실패한 OPS 실행을 Trace로 분석한다.

### Step 1. Inspector 진입

1. `/admin/inspector` 접속
2. Inspector UI 표시

### Step 2. Trace 검색

**방법 1: Trace ID 직접 입력**
1. **Search by Trace ID** 입력창에 Trace ID 입력
2. **"Search"** 클릭

**방법 2: 필터로 검색**
1. **Date Range** 선택 (예: last_24h)
2. **Status** 필터 선택 (예: failed)
3. **"Search"** 클릭

검증 포인트:
- Trace 목록이 표시된다.
- 각 Trace의 기본 정보가 표시된다.

### Step 3. Trace 상세 분석

1. 목록에서 Trace 클릭
2. Trace Detail Panel 표시

**분석할 섹션**:

| 섹션 | 설명 | 확인 포인트 |
|------|------|-----------|
| **Trace Overview** | 기본 정보, 타임스탬프, 상태 | 실행 시간, Stage 수 |
| **Applied Assets** | 적용된 Asset 목록 | Asset 타입, 이름, 버전 |
| **Plan** | LLM 생성 계획 | mode, targets, constraints |
| **Tool Calls** | 실행된 Tool 목록 | input, output, duration |
| **References** | 참조된 데이터 소스 | table, query, catalog |
| **Answer Blocks** | 생성된 답변 블록 | type, content |

검증 포인트:
- 각 섹션이 정상 표시된다.
- Asset 적용 현황을 확인할 수 있다.
- Tool 호출 성공/실패를 확인할 수 있다.

### Step 4. 문제 진단

**증상: "EXECUTE Stage가 0 rows 반환"**

1. **Applied Assets** 섹션에서 Query Asset 확인
2. **Tool Calls** 섹션에서 Tool 실행 결과 확인
3. **References** 섹션에서 참조된 테이블 확인
4. 문제 원인 파악 (예: Query 잘못됨, 테이블 없음)

**증상: "LLM이 테이블을 인식 못함"**

1. **Applied Assets** 섹션에서 Schema Catalog 확인
2. **Plan** 섹션에서 LLM이 참조한 스키마 확인
3. Catalog 발행 여부 확인

검증 포인트:
- 문제 원인을 좁힐 수 있다.
- 수정 방향을 결정할 수 있다.

---

## 5. Lab 5 - Observability 대시보드

목표: 시스템 건전성을 실시간으로 모니터링한다.

### Step 1. Observability 진입

1. `/admin/observability` 접속
2. Observability Dashboard 표시

### Step 2. System Health 확인

**System Health 카드**:

| 메트릭 | 설명 | 정상 범위 |
|--------|------|----------|
| **Overall Status** | 시스템 상태 | Healthy |
| **Uptime** | 가동 시간 | 99.9%+ |
| **Request Rate** | 요청/sec | 안정적 |
| **Error Rate** | 오류율 | < 1% |

검증 포인트:
- 모든 메트릭이 녹색(정상)으로 표시된다.
- 오류 시 빨간색으로 표시된다.

### Step 3. Execution Timeline 확인

1. **Execution Timeline** 차트 확인
2. 시간대별 요청 추이 확인
3. 스파이크(급증) 여부 확인

검증 포인트:
- 요청 추이를 한눈에 파악할 수 있다.
- 이상 시점을 식별할 수 있다.

### Step 4. Recent Errors 확인

1. **Recent Errors** 목록 확인
2. 오류 메시지, trace_id 확인
3. **"View Trace"** 클릭하여 Inspector 이동

검증 포인트:
- 최근 오류를 빠르게 파악할 수 있다.
- Inspector로 바로 이동할 수 있다.

### Step 5. Performance Metrics 확인

**Performance Metrics**:

| 메트릭 | 설명 |
|--------|------|
| **p50 latency** | 50% 요청 지연 시간 |
| **p95 latency** | 95% 요청 지연 시간 |
| **p99 latency** | 99% 요청 지연 시간 |
| **Throughput** | 처리량 (req/sec) |
| **Error Rate** | 오류율 (%) |

검증 포인트:
- 지연 시간이 허용 범위 내인지 확인한다.
- 처리량이 안정적인지 확인한다.

---

## 6. Lab 6 - Regression 테스트 설정

목표: Golden Query로 회귀 테스트를 설정한다.

### Step 1. Regression 진입

1. `/admin/regression` 접속
2. Regression Dashboard 표시

### Step 2. Golden Query 생성

1. **"Create Golden Query"** 버튼 클릭
2. Create Golden Query Modal에서 설정:
   - **Name**: `device_overview_default`
   - **Question**: `MES Server 06 상태 알려줘`
   - **Expected Blocks**: `5` (예상 답변 블록 수)
   - **Tolerance Percent**: `10` (허용 오차 10%)
   - **Enabled**: 체크
   - **Tags**: `{"domain": "ops", "priority": "high"}`
3. **"Create"** 클릭

검증 포인트:
- Golden Query 목록에 추가된다.
- 상태가 `enabled`로 표시된다.

### Step 3. 회귀 테스트 실행

1. **"Run Regression"** 버튼 클릭
2. 실행 결과 확인

검증 포인트:
- 모든 Golden Query가 실행된다.
- 결과가 표에 표시된다.

### Step 4. 결과 분석

**Result Table**:

| Golden Query | Expected | Actual | Diff | Status |
|-------------|----------|--------|------|--------|
| device_overview_default | 5 | 5 | 0% | passed |
| cpu_usage_check | 3 | 1 | 66% | failed |

검증 포인트:
- **passed**: 정상 (허용 오차 내)
- **warning**: 주의 (허용 오차 근접)
- **failed**: 회귀 감지 (허용 오차 초과)

### Step 5. 회귀 대응

**failed 항목 발생 시**:
1. **"View Trace"** 클릭하여 Inspector 이동
2. 문제 원인 분석
3. Asset/Tool 수정
4. 재테스트 실행

검증 포인트:
- 회귀를 조기에 감지할 수 있다.
- 수정 후 재테스트로 회복 확인 가능하다.

---

## 7. Lab 7 - Settings 관리

목표: 시스템 설정을 변경하고 재시작 여부를 확인한다.

### Step 1. Settings 진입

1. `/admin/settings` 접속
2. Settings Panel 표시

### Step 2. 설정 카테고리 확인

| 카테고리 | 설정 예시 | restart_required |
|---------|----------|-----------------|
| **Database** | connection_string, pool_size | Yes |
| **LLM** | api_key, model, temperature | No |
| **Cache** | redis_url, ttl | Yes |
| **Security** | jwt_secret, encryption_key | Yes |
| **Observability** | log_level, metrics_enabled | No |

### Step 3. 설정 변경 (No Restart)

1. **LLM** 카테고리 확장
2. **model** 변경 (예: `gpt-4` → `gpt-4-turbo`)
3. **"Save"** 클릭

검증 포인트:
- **restart_required**: `false`로 표시
- 즉시 적용된다.

### Step 4. 설정 변경 (Restart Required)

1. **Database** 카테고리 확장
2. **pool_size** 변경 (예: `10` → `20`)
3. **"Save"** 클릭

검증 포인트:
- **restart_required**: `true`로 표시
- ⚠️ 아이콘으로 경고 표시
- 변경 사항을 적용하려면 서비스 재시작 필요

---

## 8. Lab 8 - Logs로 시스템 활동 추적

목표: 시스템 활동을 감사하고 디버깅에 활용한다.

### Step 1. Logs 진입

1. `/admin/logs` 접속
2. Logs Dashboard 표시

### Step 2. Log 탭 선택

| 탭 | 설명 |
|----|------|
| **Query History** | OPS 질의 기록 |
| **Execution Trace** | 전체 실행 추적 |
| **Audit Log** | Asset CRUD, 사용자 활동 |
| **File Log** | 애플리케이션 로그 |
| **LLM Call Log** | LLM 호출 기록 |

### Step 3. Query History 확인

1. **Query History** 탭 선택
2. 필터 설정:
   - **Date Range**: last_24h
   - **User**: 선택 (또는 전체)
   - **Status**: success/failed
3. **"Search"** 클릭

검증 포인트:
- 필터 조건에 맞는 기록이 표시된다.
- 질문, 응답 요약, trace_id를 확인할 수 있다.

### Step 4. Audit Log 확인

1. **Audit Log** 탭 선택
2. 필터 설정:
   - **Date Range**: last_7d
   - **Action**: create, update, delete, publish
   - **User**: admin
3. **"Search"** 클릭

검증 포인트:
- Asset 변경 이력이 표시된다.
- 누가 무엇을 언제 변경했는지 확인 가능하다.

### Step 5. LLM Call Log 확인

1. **LLM Call Log** 탭 선택
2. 필터 설정:
   - **Date Range**: last_24h
   - **Model**: gpt-4-turbo
3. **"Search"** 클릭

검증 포인트:
- LLM 호출 기록이 표시된다.
- 토큰 사용량, 비용, 지연 시간을 확인할 수 있다.

---

## 9. 운영 부록 - 문제 해결 패턴

### 9.1 Asset이 적용되지 않음

점검 순서:
1. Asset 상태가 `published`인지 확인
2. Asset 버전이 최신인지 확인
3. Inspector의 Applied Assets 섹션에서 확인

### 9.2 Tool 테스트 실패

점검 순서:
1. input_schema와 입력 매칭 확인
2. source_ref 연결 확인
3. query_template 문법 확인
4. Catalog 발행 여부 확인

### 9.3 Catalog 스캔 실패

점검 순서:
1. Connection String 확인
2. DB 접근 권한 확인
3. 방화벽规则 확인
4. SSL/TLS 설정 확인

### 9.4 Inspector에서 Trace를 찾을 수 없음

점검 순서:
1. Trace ID 형식 확인 (UUID)
2. Trace 보관 기간 확인 (30일)
3. Date Range 필터 확인

### 9.5 Observability 메트릭 누락

점검 숸서:
1. 메트릭 수집 활성화 확인
2. 로그 레벨 확인
3. 데이터 보관 정책 확인

---

## 10. 최종 체크리스트

```text
[ ] Asset을 생성하고 발행했다.
[ ] Tool을 생성하고 테스트했다.
[ ] Catalog를 스캔하고 발행했다.
[ ] Inspector로 Trace를 분석했다.
[ ] Observability로 시스템을 모니터링했다.
[ ] Regression 테스트를 설정했다.
[ ] Settings를 변경하고 재시작 여부를 확인했다.
[ ] Logs로 시스템 활동을 추적했다.
```

---

## 11. 참고 파일

| 경로 | 설명 |
|------|------|
| `apps/api/app/modules/asset_registry/router.py` | Asset Registry API |
| `apps/api/app/modules/asset_registry/tool_router.py` | Tool API |
| `apps/api/app/modules/asset_registry/crud.py` | Asset CRUD |
| `apps/web/src/app/admin/assets/page.tsx` | Assets 페이지 |
| `apps/web/src/app/admin/tools/page.tsx` | Tools 페이지 |
| `apps/web/src/app/admin/catalogs/page.tsx` | Catalogs 페이지 |
| `apps/web/src/app/admin/inspector/page.tsx` | Inspector 페이지 |
| `apps/web/src/app/admin/observability/page.tsx` | Observability 페이지 |
| `apps/web/src/app/admin/regression/page.tsx` | Regression 페이지 |
| `apps/web/src/app/admin/settings/page.tsx` | Settings 페이지 |
| `apps/web/src/app/admin/logs/page.tsx` | Logs 페이지 |
| `apps/web/src/components/admin/AssetTable.tsx` | Asset 테이블 |
| `apps/web/src/components/admin/ToolTable.tsx` | Tool 테이블 |
| `apps/web/src/components/admin/CatalogTable.tsx` | Catalog 테이블 |
| `apps/web/src/components/admin/ObservabilityDashboard.tsx` | 관찰 가능성 대시보드 |

---

**마지막 정리**: 2026-02-10
**전체 완성도**: 100% (상용 완료)
