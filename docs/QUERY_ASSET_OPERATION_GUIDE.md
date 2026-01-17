# Query Asset 운영 가이드

## 목적

기존 파일 기반 Query와 신규 DB 기반 Query Asset을 병행 운영하면서 발생할 수 있는 혼란을 방지하고, Prompt Asset 운영 철학을 Query 영역으로 확장한다.

---

## 1️⃣ 개요 (Why)

### 1.1 배경

기존 Query는 `resources/queries/**/*.sql` 파일 기반으로 관리되었으며, Asset Registry UI(Assets) 도입으로 Query Asset(DB)이 추가되어 개발과 운영이 각각 다른 저장소를 참고하는 전환기 상태가 되었다. 이 문서는 두 체계가 공존하는 동안 혼란이 생기지 않도록 정본을 명확히 정의하고, 운영·개선 모두 동일한 기준으로 작업되도록 안내한다.

### 1.2 목표

1. 운영 중 Query의 정본(source of truth)을 Query Asset(DB)으로 고정한다.
2. Query 개선 작업이 기존 흐름을 방해하지 않고 계속 가능하도록 보장한다.
3. 납품(오프라인) 환경에서도 복구 및 이해가 가능하도록 File Query를 Seed·문서·백업용으로 유지한다.

---

## 2️⃣ 용어 정의 (중요)

| 용어 | 정의 |
| --- | --- |
| **File Query** | 현재 저장소의 `resources/queries` 이하에 존재하는 SQL 쿼리 파일 |
| **Query Asset** | Asset Registry(DB)에 저장된 SQL 쿼리 |
| **Seed Query** | 최초 기준이 되는 File Query (YAML 메타데이터 포함) |
| **Published Query** | 운영에 실제 적용 중인 Query Asset |
| **Query Importer** | File Query를 Query Asset으로 이관하는 도구 |
| **Query Fallback** | Query Asset이 없을 때 File Query를 사용하는 동작 |

---

## 3️⃣ Query Asset 특성 및 운영 원칙

### 3.1 Query Asset의 특성

Query Asset은 Prompt Asset과 다음 점에서 차별화된다:

- **SELECT only**: 데이터 조회 목적으로만 사용 (INSERT/UPDATE/DELETE 금지)
- **매개변수 관리**: `query_params`로 입력 스키마와 출력 스키마 정의
- **메타데이터**: `query_metadata`에 데이터베이스, 범주, 태그, 원본 파일 정보 기록
- **자동 로깅**: Inspector에서 Query Asset ID와 버전이 자동으로 추적됨

### 3.2 단일 정본 원칙

운영 시점의 정본은 Query Asset(DB)이며, File Query는 Seed, 백업, 문서로서의 역할만 담당한다.

### 3.3 병행 운영 원칙

개발 단계에서는 File Query와 Query Asset을 병행 유지한다. 운영 변경은 반드시 Query Asset을 통해서만 수행하고, File Query 직접 수정은 제외한다.

### 3.4 Fallback 원칙

Query Asset을 로드할 때 우선순위는:
1. **Published Query Asset** (DB에서 공개된 버전)
2. **Seed File Query** (resources/queries/에서 파일 쿼리)

Fallback은 권장되지 않으므로, 모든 운영 Query는 Asset Registry로 이관되어야 한다.

---

## 4️⃣ Query Asset의 생명주기 (Lifecycle)

```
[File Query (Seed)] + [YAML Metadata]
        |
        |  (1회 Import via query_asset_importer.py)
        v
[Query Asset - Draft]
        |
        |  Publish
        v
[Query Asset - Published]
        |
        |  Rollback
        v
[New Draft (from previous version)]
```

* File Query는 자동으로 Asset으로 변환되지 않으며 최초 1회만 수동 Import한다.
* YAML 메타데이터는 쿼리와 함께 유지되어 의도와 출력 계약을 명확히 한다.

---

## 5️⃣ 파일 구조

### 5.1 File Query 구조

```
resources/queries/
├── postgres/
│   ├── ci/
│   │   ├── ci_get.sql          (SQL 쿼리 파일)
│   │   ├── ci_get.yaml         (메타데이터)
│   │   ├── ci_list.sql
│   │   ├── ci_list.yaml
│   │   ├── ci_search.sql
│   │   └── ci_search.yaml
│   ├── discovery/
│   │   ├── postgres_catalog_columns.sql
│   │   ├── postgres_catalog_columns.yaml
│   │   └── ...
│   ├── metric/
│   │   ├── metric_timeseries.sql
│   │   ├── metric_timeseries.yaml
│   │   └── ...
│   └── history/
│       ├── work_history.sql
│       ├── work_history.yaml
│       └── ...
├── neo4j/
│   ├── discovery/
│   │   ├── labels.cypher
│   │   ├── labels.yaml
│   │   └── ...
│   └── graph/
│       ├── component_composition.cypher
│       ├── component_composition.yaml
│       └── ...
```

### 5.2 YAML 메타데이터 형식

```yaml
# resources/queries/postgres/ci/ci_get.yaml
name: ci_get
description: "Fetch a single CI record with extended attributes"
scope: ci
category: discovery
tags:
  - ci
  - retrieval
parameters:
  - name: field
    type: string
    description: "Field name to filter by"
    required: true
  - name: tenant_id
    type: string
    description: "Tenant ID for multi-tenant isolation"
    required: true
output_schema:
  type: object
  properties:
    ci_id:
      type: string
    ci_name:
      type: string
    # ... 출력 필드 정의
```

---

## 6️⃣ 개발 단계 작업 규칙

### 6.1 Query 신규 추가 시

1. `resources/queries/{db}/{scope}/` 디렉토리에 `query_name.sql` 생성
2. 같은 위치에 `query_name.yaml` 메타데이터 작성
   - 쿼리 설명, 매개변수, 출력 스키마 정의
3. 테스트 후 운영 환경에 따라:
   - **개발**: File Query로 즉시 사용 가능 (Fallback)
   - **운영**: Query Importer로 Asset Registry로 이관 후 Publish

### 6.2 Query 개선 작업 시

1. File Query 또는 Export된 Query Asset 텍스트를 분석 대상으로 제공
2. 개선안 검토 후 필요하다면 File Query를 업데이트 (선택)
3. 운영 적용을 위한 최종 SQL은 Query Asset UI에서 수정 후 Publish

### 6.3 금지 사항

* DB Query Asset 내용을 레포에 없는 상태로 방치하지 않는다.
* 어떤 Query가 운영 중인지 모르는 상태에서 수정하지 않는다.
* File Query와 Query Asset을 동기화되지 않은 채로 혼용하지 않는다.

---

## 7️⃣ 운영 단계 작업 규칙

### 7.1 Query Asset 이관

Query Importer를 사용하여 File Query를 Query Asset으로 이관한다:

```bash
# Dry run (확인 목적)
python scripts/query_asset_importer.py --scope ci

# Draft 생성
python scripts/query_asset_importer.py --scope ci --apply

# Draft 생성 및 즉시 Publish
python scripts/query_asset_importer.py --scope ci --apply --publish

# 기존 Draft 삭제 후 새로 생성
python scripts/query_asset_importer.py --scope ci --apply --publish --cleanup-drafts
```

Importer는 다음을 자동 처리한다:
- YAML 메타데이터와 SQL 파일 결합
- Asset Registry에 Query Asset 생성
- 입력/출력 스키마 등록
- 선택 시 즉시 Publish

### 7.2 운영 중 변경

운영 변경은 반드시 **Assets UI의 Query Asset**에서만 수행한다:

1. Assets 페이지에서 Query Asset 선택
2. Draft 상태 확인 또는 새 Draft 생성
3. SQL, 매개변수, 메타데이터 수정
4. "Save Draft" → "Publish" 순서로 진행

**File Query를 직접 수정하지 않는다.**

### 7.3 장애 대응

1. Inspector로 적용된 Query Asset 버전 확인
   - Tool Call 정보에 `query_asset: "{asset_id}:v{version}"` 기록
2. 필요 시 Rollback 수행
   - Query Asset 상세 페이지 → "Version Rollback..." 버튼
   - 문제가 발생한 버전의 이전 버전으로 복구
3. File Query는 복구 수단으로만 사용

### 7.4 Audit Log 추적

Query Asset 관련 모든 작업은 Audit Log에 기록된다:

- **Action**: create, update, publish, rollback, unpublish, delete
- **Actor**: 변경을 수행한 사용자
- **Changes**: SQL, 매개변수, 메타데이터 변경 사항
- **Trace**: Inspector에서 Query 실행 추적 가능

---

## 8️⃣ Query Asset 검증 (SELECT only)

Query Asset 발행 시 자동으로 다음 검증이 수행된다:

✅ **필수 필드**
- `query_sql`: 비어있지 않은 SELECT 문
- `query_params`: 입력 매개변수 스키마
- `query_metadata`: 쿼리 메타데이터

✅ **SELECT only 검증**
- SELECT로 시작해야 함
- INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, EXECUTE 금지

❌ **발행 실패 시나리오**
```
Query asset must contain only SELECT statements
Query asset cannot contain INSERT statements
```

---

## 9️⃣ Inspector를 통한 Query Asset 추적

### 9.1 Query 실행 추적

Query가 실행될 때마다 Trace에 기록된다:

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_calls": [
    {
      "tool": "postgres",
      "elapsed_ms": 145,
      "query_asset": "12345678-1234-1234-1234-123456789abc:v3",
      "input_params": {"field": "ci_id", "tenant_id": "t1"},
      "output_summary": {"rows_count": 1}
    }
  ]
}
```

### 9.2 Inspector 페이지 활용

1. Trace ID 입력 → 모든 Query 실행 이력 조회
2. Parent Trace ID 확인 → 상위 요청 추적
3. Query Asset 버전 확인 → Audit Log에서 변경 이력 조회
4. Rollback 필요 시 → Query Asset 상세 페이지로 이동

---

## 🔟 FAQ

**Q. File Query를 삭제해도 되나요?**
A. ❌ 안 됩니다. Seed/백업/문서 역할을 하기 때문에 유지해야 합니다. Asset Registry로 완전히 이관된 후에도 참고용으로 유지하세요.

**Q. Asset Registry가 없을 때 File Query로 자동 Fallback되나요?**
A. ✅ 네, 하지만 이는 임시 방편입니다. 모든 운영 Query는 Asset Registry로 이관되어야 합니다.

**Q. Query Asset과 File Query가 다르면 어느 것을 믿어야 하나요?**
A. Query Asset(DB)이 정답입니다. File Query는 Seed일 뿐입니다.

**Q. 운영 중 Query를 빠르게 수정해야 하면?**
A. Assets UI에서 직접 수정 후 Publish하세요. File Query 수정은 금합니다.

**Q. Query 성능 최적화는 어디서 하나요?**
A. Query Asset에서 SQL을 수정 후 Publish. 변경 이력은 자동으로 Audit Log에 기록됩니다.

---

## 🕐 책임과 권한

| 역할 | 책임 |
| --- | --- |
| **개발자** | Seed Query(File) 유지, Importer 도구 관리 |
| **운영자** | Query Asset 관리/Publish/Rollback, 성능 최적화 |
| **데이터 담당** | Query 내용 검증, 출력 스키마 정의 |

---

## ✅ 작업 완료 기준 (DoD)

1. Query Asset 타입 추가 및 검증 로직 구현
2. Seed Query 파일 구조 설정 (YAML + SQL)
3. Query Importer 스크립트 제공
4. Assets UI에서 Query Asset 관리 기능
5. Inspector에서 Query Asset 추적 기능
6. Audit Log에 Query 관련 작업 기록
7. 이 가이드 문서 작성 및 팀 내 공유

---

## 🚀 다음 단계

1. 모든 File Query를 YAML 메타데이터와 함께 정리
2. Query Importer로 Asset Registry로 이관 (--apply --publish)
3. Inspector에서 Query 실행 확인 및 추적
4. 운영 Query는 100% Assets UI에서 관리

---

## 마지막으로 한 문장 요약

Query는 이제 코드가 아니라 운영 자산이다. File은 기준이고, DB는 정본이며, Inspector는 추적자다.
