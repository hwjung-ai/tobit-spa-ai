# API Manager vs Tools: Architecture Analysis & Integration Strategy

**최종 작성**: 2026-02-09

---

## 1. 현재 두 시스템 비교

### 1.1 API Manager 시스템

#### 기능
```
API Manager
├─> API 정의 (CRUD)
│   ├─ 이름, 메서드, 엔드포인트, 설명
│   ├─ 스코프 (system / custom)
│   └─ 상태 (draft / published)
├─> 실행 (Execute)
│   ├─ SQL: SELECT 쿼리 (안전성 검증)
│   ├─ Python: 코드 실행
│   ├─ Workflow: 다중 단계 오케스트레이션
│   └─ HTTP: 외부 API 호출
├─> 로깅
│   ├─ 실행 시간 (ms)
│   ├─ 요청/응답 데이터
│   ├─ 에러 메시지 및 스택트레이스
│   └─ 행 수 영향
└─> 버전 관리
    ├─ draft/published 상태
    └─ 변경 이력

데이터베이스 테이블:
- ApiDefinition: 정의
- ApiExecutionLog: 실행 로그
```

#### 특징
| 항목 | 내용 |
|-----|------|
| **사용 목적** | 사용자가 "웹 UI"에서 직접 API를 만들고 테스트 |
| **실행 방식** | 직접 HTTP 요청 → 즉시 실행 |
| **데이터 저장** | 정의만 저장 (실행 결과는 로그) |
| **보안** | SQL 검증 (위험한 키워드 필터링) |
| **타겟 사용자** | DevOps, 데이터 분석가 (웹 UI 사용) |

---

### 1.2 Tools 시스템 (Asset Registry)

#### 기능
```
Asset Registry (Tools)
├─> Tool Asset 정의
│   ├─ 이름, 설명, 버전
│   ├─ Tool Type (http_api, builtin 등)
│   ├─ Tool Config (HTTP 설정)
│   ├─ Input/Output Schema (JSON Schema)
│   └─ Tags (메타데이터)
├─> Tool 실행
│   ├─ OPS CI/Ask에서 자동 발견
│   ├─ LLM이 도구로 선택하여 호출
│   └─ 결과를 LLM 컨텍스트에 포함
├─> 상태 관리
│   ├─ draft → published
│   ├─ 버전 이력
│   └─ Rollback 지원
└─> 내장 도구 (Built-in)
    ├─ CI Tool
    ├─ Graph Tool
    ├─ Metric Tool
    └─ Document Search Tool

데이터베이스 테이블:
- TbAssetRegistry: 도구 정의
- TbAssetVersionHistory: 버전 이력
```

#### 특징
| 항목 | 내용 |
|-----|------|
| **사용 목적** | OPS/LLM이 "자동으로 사용"하는 도구 카탈로그 |
| **실행 방식** | LLM이 필요시 선택 → 비동기 호출 |
| **데이터 저장** | 정의 + 스키마 저장 |
| **보안** | 스키마 검증 (input/output) |
| **타겟 사용자** | OPS AI 플래너, LLM 에이전트 |

---

## 2. 핵심 차이점

### 2.1 설계 철학

| 구분 | API Manager | Tools (Asset Registry) |
|-----|-----------|----------------------|
| **인터페이스** | 웹 UI (사람) | 프로그래밍 인터페이스 (AI/자동화) |
| **실행 모델** | 즉시/동기 | 지연/비동기 |
| **메타데이터** | 최소한 (이름, 경로, 메서드) | 풍부함 (스키마, 태그, 버전) |
| **발견성** | 사용자가 수동 조회 | LLM이 자동 발견 |
| **상태 관리** | 시스템 수준 | 자산 수준 (버전별) |

### 2.2 데이터 흐름

#### API Manager 흐름
```
사용자 정의 API
    ↓
[웹 UI 테스트 버튼 클릭]
    ↓
즉시 실행 (SQL/Python/HTTP)
    ↓
결과 표시 + 로그 저장
```

#### Tools 흐름
```
도구 자산 정의 (스키마 포함)
    ↓
[OPS Ask 질문]
    ↓
LLM이 도구 발견 및 선택
    ↓
필요시 호출 (입력 생성)
    ↓
결과 → LLM 컨텍스트에 포함
```

---

## 3. 장단점 분석

### 3.1 API Manager의 장점

✅ **직관적인 웹 UI**
- 개발자가 직접 API를 만들고 테스트할 수 있음
- 즉시 피드백

✅ **상세한 실행 로깅**
- 정확한 타이밍, 입력/출력, 에러 추적
- 디버깅 용이

✅ **SQL 보안 검증**
- SELECT만 허용, 위험한 키워드 필터링
- 데이터 무결성 보호

✅ **다양한 실행 모드**
- SQL, Python, Workflow, HTTP 지원

### 3.2 API Manager의 단점

❌ **LLM/AI 통합 부족**
- 자동 발견 메커니즘 없음
- 스키마 정보 불충분 (input/output 정의 없음)

❌ **상태 관리 미흡**
- draft/published 상태는 있으나, 버전별 롤백 없음
- 자산으로서의 생명주기 부족

❌ **메타데이터 부족**
- 입력/출력 스키마가 없어 AI가 도구 용도 파악 어려움
- 태그, 카테고리 같은 구조적 메타데이터 없음

---

### 3.3 Tools의 장점

✅ **LLM 네이티브 설계**
- JSON Schema 기반 입력/출력 정의
- LLM이 도구를 자동으로 발견하고 선택

✅ **메타데이터 풍부**
- 스키마, 태그, 설명이 명확함
- 도구 용도를 AI가 정확히 파악 가능

✅ **버전 관리 강력**
- 버전별 스냅샷 저장
- 롤백 지원

✅ **유연한 Tool Type**
- http_api, builtin, 향후 확장 가능

### 3.4 Tools의 단점

❌ **웹 UI 부족**
- 도구를 정의하려면 코드/스크립트 필요
- 비개발자가 사용하기 어려움

❌ **실행 로깅 미흡**
- 도구 호출 이력은 있으나, 상세 실행 정보 부족
- 디버깅 추적 어려움

❌ **HTTP API 타입만 외부 연동**
- SQL/Python 도구는 내장만 가능
- 외부 API 기반 도구만 정의 가능

---

## 4. 통합 전략: 3가지 옵션

### 옵션 1️⃣: 완전 분리 (현재 상태)

```
API Manager          Tools (Asset Registry)
├─> 웹 UI용          ├─> LLM/OPS용
├─> 개발자           ├─> 자동화
└─> 즉시 실행        └─> 비동기

서로 독립적, 중복 가능
```

**장점**:
- 각 시스템이 순수한 목적에 집중
- 변경 영향 최소화

**단점**:
- 같은 기능을 두 곳에서 관리
- 일관성 문제 (A라는 API를 둘 다 정의해야 할 수도)

**언제 사용?**
- API Manager: 개발/테스트 용도만
- Tools: OPS/LLM 용도만

---

### 옵션 2️⃣: 단방향 링크 (권장)

```
API Manager (원본)
    ↓
[변환 계층] ← 스키마 생성
    ↓
Tools (파생)
    └─> OPS/LLM이 사용
```

**구현 방식**:
1. API Manager에서 API 정의 (기존 방식)
2. 웹 UI에 "Tool로 등록" 버튼 추가
3. 자동으로:
   - Input Schema 생성 (요청 파라미터 기반)
   - Output Schema 생성 (응답 구조 기반)
   - Tool Asset 생성 (TbAssetRegistry)
   - 자동 발행

**코드 흐름**:
```python
def api_to_tool(api_definition: ApiDefinition) -> TbAssetRegistry:
    """
    Convert API Definition → Tool Asset
    """
    # 1. 파라미터 → input_schema
    input_schema = extract_input_schema(api_definition.logic)

    # 2. 응답 → output_schema
    output_schema = extract_output_schema(api_definition)

    # 3. Tool Asset 생성
    tool_asset = TbAssetRegistry(
        asset_type="tool",
        tool_type="http_api",
        name=api_definition.name,
        description=api_definition.description,
        tool_config={
            "url": f"/api/execute/{api_definition.api_id}",
            "method": api_definition.method,
        },
        tool_input_schema=input_schema,
        tool_output_schema=output_schema,
        tags={"source": "api_manager", "api_id": api_definition.api_id}
    )

    return tool_asset
```

**장점**:
- ✅ API Manager는 현재 그대로 유지
- ✅ 개발자는 API 정의 한 번만
- ✅ OPS/LLM은 자동으로 도구 사용 가능
- ✅ 스키마 자동 생성으로 유지보수 감소

**단점**:
- 스키마 자동 생성이 완벽하지 않을 수 있음
- 복잡한 API는 수동 조정 필요

**언제 사용?**
- **권장**: 시스템 확장 시 최적
- API Manager를 "도구의 원본 저장소"로 취급

---

### 옵션 3️⃣: 양방향 동기화

```
API Manager ←→ Tools
├─> 정의 공유
├─> 메타데이터 병합
└─> 버전 동기화
```

**구현 방식**:
1. API Manager에서 "Tool" 필드 추가
   ```python
   class ApiDefinition:
       ...
       tool_asset_id: UUID | None  # 연결된 Tool
       input_schema: dict  # Tool input schema
       output_schema: dict # Tool output schema
   ```

2. API Manager 수정 시 Tool도 자동 업데이트

3. Tool 발행 시 API도 published 표시

**장점**:
- ✅ 완벽한 일관성 보장
- ✅ 한 곳에서만 관리

**단점**:
- ❌ 복잡도 증가 (코드 많음)
- ❌ 두 시스템의 강한 결합
- ❌ 변경 영향 범위 증가
- ❌ 롤백, 마이그레이션 어려움

**언제 사용?**
- 불권장 (현재는 단방향만으로도 충분)

---

## 5. 최종 권장안: 옵션 2 (단방향 링크)

### 5.1 이유

1. **API Manager 역할 보장**: 웹 UI 기반 개발자 도구로 계속 작동
2. **LLM 도구화**: 자동 변환으로 OPS/AI 통합
3. **유지보수 용이**: API 정의 한 번으로 두 시스템 커버
4. **확장성**: 향후 더 많은 자산 타입 추가 가능

### 5.2 구현 로드맵

#### Phase 1: API Manager 확장 (현재)
```
API Manager UI
├─> [새] Tool로 등록 버튼
├─> [새] 입력/출력 스키마 정의
└─> [새] Tool 메타데이터 편집
```

#### Phase 2: 자동 변환 (다음)
```
API → Tool 변환기
├─> 스키마 생성 (SQL/Python/HTTP 지원)
├─> Tool Asset 자동 생성
└─> Asset Registry에 등록
```

#### Phase 3: OPS 통합 (최종)
```
OPS CI Ask
└─> Tool 목록에서 API Manager API 도구 자동 표시
```

---

## 6. SQL vs Python vs HTTP: 어느 것을 Tool화할까?

### 6.1 SQL API

```
장점:
✅ 안전성 (위험한 키워드 필터링)
✅ 스키마 자동 생성 가능 (SELECT 결과 → output_schema)
✅ 성능 좋음

단점:
❌ 도구로 사용하려면 파라미터 맵핑 필요
```

### 6.2 Python API

```
장점:
✅ 유연성 (모든 로직 가능)

단점:
❌ 입출력 스키마 자동 생성 불가 (코드 분석 어려움)
❌ 보안 위험 (임의 코드 실행)
```

### 6.3 HTTP API

```
장점:
✅ 이미 Tool로 사용 중 (document_search)
✅ 스키마 명확함

단점:
❌ 외부 API만 가능
```

### 결론

**Tool로 권장**:
1. **SQL API** (가장 안전하고 자동화 가능)
2. **HTTP API** (이미 구현됨)

**Tool로 비권장**:
- Python API (스키마 자동 생성 어려움, 보안 위험)

---

## 7. 실제 예시

### 예시: "장비 목록 조회" API

#### API Manager에서 정의
```python
{
    "name": "Get Equipment List",
    "method": "GET",
    "endpoint": "/api/equipment",
    "mode": "sql",
    "logic": """
        SELECT id, name, status, location
        FROM equipment
        WHERE status = $1
        LIMIT 100
    """,
    "description": "조직의 모든 장비 조회"
}
```

#### "Tool로 등록" 버튼 클릭 →

#### Tool Asset 자동 생성
```python
{
    "asset_type": "tool",
    "name": "Get Equipment List",
    "description": "조직의 모든 장비 조회",
    "tool_type": "http_api",
    "tool_config": {
        "url": "/api/execute/api_equipment_list",
        "method": "POST",  # Tool 호출은 항상 POST
        "headers": {"X-Tenant-Id": "{tenant_id}"}
    },
    "tool_input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Equipment status filter"
            }
        },
        "required": ["status"]
    },
    "tool_output_schema": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "status": {"type": "string"},
                "location": {"type": "string"}
            }
        }
    },
    "tags": {
        "source": "api_manager",
        "api_id": "api_equipment_list"
    }
}
```

#### OPS Ask에서 자동 사용
```
사용자: "우리 회사의 모든 정상 장비를 목록으로 보여줄래?"

→ LLM이 자동으로 "Get Equipment List" 도구 발견
→ 입력: { "status": "normal" }
→ Tool 호출
→ 결과를 LLM 컨텍스트에 포함
→ 최종 답변 생성
```

---

## 8. 결론

### API Manager vs Tools 요약

| 기준 | API Manager | Tools |
|-----|-----------|-------|
| **목적** | 개발/테스트 | OPS/LLM 자동화 |
| **사용자** | 개발자 (웹 UI) | AI 플래너 (자동) |
| **실행** | 즉시/동기 | 비동기/조건부 |
| **메타데이터** | 최소 | 풍부 (스키마) |

### 최종 권장 아키텍처

```
┌─────────────────────┐
│  API Manager (웹 UI) │
│ ├─ SQL API          │
│ ├─ Python API       │
│ └─ HTTP API         │
└──────────┬──────────┘
           │
      [변환 계층]
      (API → Tool)
           │
┌──────────▼──────────┐
│ Tools (Asset Registry)│
│ └─ OPS AI 플래너가   │
│   자동으로 발견/사용  │
└─────────────────────┘
```

### 다음 단계

1. ✅ **분석 완료** (현재)
2. ⏳ **API Manager에 Tool 등록 UI 추가** (Phase 1)
3. ⏳ **자동 변환 엔진 구현** (Phase 2)
4. ⏳ **OPS 통합 테스트** (Phase 3)

---

## 참고자료

- API Manager: `/apps/api/services/api_manager.py`
- API Executor: `/apps/api/services/api_manager_executor.py`
- Asset Registry: `/apps/api/app/modules/asset_registry/models.py`
- Tool Router: `/apps/api/app/modules/asset_registry/tool_router.py`
- Document Search Tool: `/apps/api/tools/init_document_search_tool.py`
