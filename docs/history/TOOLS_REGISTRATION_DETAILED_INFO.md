# Tools 등록 시 필요한 정보 완벽 가이드

**작성일**: 2026-02-09

---

## 1. 한눈에 보는 Tool 등록 정보

```
┌─────────────────────────────────────────────────────────────┐
│                   Tool Asset 구성요소                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  필수 정보 (LLM이 Tool을 선택하고 사용하는 데 필요)            │
│  ════════════════════════════════════════════════════       │
│                                                             │
│  1️⃣  name                    (문자열)                        │
│      "Get Equipment Status"                                │
│      → LLM이 이 도구를 호출할 때 사용                         │
│                                                             │
│  2️⃣  description            (문자열) ⭐ 중요                 │
│      "Retrieve equipment status from database              │
│       including online/offline/maintenance states"        │
│      → LLM이 도구를 "선택"할지 말지 결정 (이것이 핵심!)     │
│      → 정확할수록 LLM이 올바르게 선택                       │
│                                                             │
│  3️⃣  tool_type             (http_api, database_query 등)  │
│      "http_api"                                           │
│      → 도구의 종류                                         │
│                                                             │
│  4️⃣  tool_config           (JSON)                          │
│      {                                                    │
│        "url": "http://localhost:8000/...",              │
│        "method": "POST",                                │
│        "headers": { "X-Tenant-Id": "{tenant_id}" }      │
│      }                                                   │
│      → 실제로 도구를 호출하는 방법                          │
│                                                             │
│  5️⃣  tool_input_schema     (JSON Schema) ⭐⭐ 중요            │
│      {                                                    │
│        "type": "object",                                │
│        "properties": {                                  │
│          "status": {                                    │
│            "type": "string",                            │
│            "enum": ["online", "offline", "maintenance"],│
│            "description": "Filter by status"            │
│          },                                             │
│          "limit": {                                     │
│            "type": "integer",                           │
│            "minimum": 1,                                │
│            "maximum": 1000,                             │
│            "default": 100,                              │
│            "description": "Max results to return"       │
│          }                                              │
│        },                                               │
│        "required": ["status"]                           │
│      }                                                   │
│      → LLM이 "어떤 입력"을 제공해야 하는지 알 수 있음      │
│                                                             │
│  6️⃣  tool_output_schema    (JSON Schema) ⭐⭐ 중요            │
│      {                                                    │
│        "type": "array",                                 │
│        "items": {                                       │
│          "type": "object",                              │
│          "properties": {                                │
│            "id": { "type": "string" },                 │
│            "name": { "type": "string" },               │
│            "status": {                                 │
│              "type": "string",                         │
│              "enum": ["online", "offline", "maintenance"]│
│            },                                          │
│            "location": { "type": "string" }            │
│          }                                              │
│        }                                                │
│      }                                                   │
│      → LLM이 "어떤 응답"을 받을지 예상할 수 있음            │
│                                                             │
│  선택 정보 (관리/추적용)                                     │
│  ═══════════════════════════════════════                   │
│                                                             │
│  7️⃣  tags                  (JSON 객체)                      │
│      {                                                    │
│        "category": "infrastructure",                    │
│        "source": "api_manager",                         │
│        "performance": "fast"                            │
│      }                                                   │
│      → Tool을 검색/분류하는 데 사용                        │
│                                                             │
│  8️⃣  created_by            (문자열)                         │
│      "admin" 또는 "user123"                              │
│      → 누가 만들었는지 기록                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 각 필드의 상세 설명

### 2.1 name (필수)

```
용도: Tool 식별자 및 LLM 호출 이름
특징:
  • 고유성: 권장하지만 강제하지 않음
  • 길이: 1-255자
  • 형식: 자유로운 문자열
  • 공백 허용

예시:
  ❌ "Tool1"                    (너무 일반적)
  ❌ "Get"                      (불명확)
  ✅ "Get Equipment Status"      (명확)
  ✅ "Search Documents by Query" (동작 명확)
```

### 2.2 description (필수 + 매우 중요 ⭐⭐⭐)

```
용도: LLM이 도구를 선택하는 핵심 정보

LLM이 사용하는 방식:
  질문: "우리 회사의 모든 정상 장비를 보여줄래?"
    ↓
  LLM이 등록된 모든 Tool을 검토
    ↓
  각 Tool의 description을 읽음
    ↓
  "Equipment Status 도구를 써야겠네" 결정
    ↓
  Tool 호출

따라서 description은:
  1️⃣  무엇을 하는지 명확히: "Retrieve equipment status"
  2️⃣  어떤 데이터: "from database"
  3️⃣  입력이 무엇인지: "status filter"
  4️⃣  출력이 무엇인지: "equipment list"
  5️⃣  사용 시기: "When you need to check device status"

좋은 예:
✅ "Retrieve equipment status information from database.
   Accepts status filter (online/offline/maintenance).
   Returns list of equipment with ID, name, location, and status.
   Use when you need to check device availability or status."

나쁜 예:
❌ "Get equipment"         (너무 짧음)
❌ "Equipment tool"        (무엇을 하는지 불명확)
❌ "JSON API endpoint"     (LLM이 이해하기 어려움)

길이: 권장 50-200자 (상세할수록 좋음)
언어: 영어 권장 (LLM 학습 데이터 기준)
```

### 2.3 tool_type (필수)

```
현재 지원하는 타입:
  • http_api          (HTTP REST API)
  • database_query    (SQL 쿼리)
  • graph_query       (Neo4j 같은 그래프 DB)
  • python_script     (Python 코드 실행)
  • builtin           (내장 도구)

예시:
  POST /asset-registry/tools
  {
    "tool_type": "http_api"
  }
```

### 2.4 tool_config (필수)

```
용도: 실제로 Tool을 호출하는 구체적인 설정

Tool Type별 설정:

A️⃣  HTTP API 타입:
    {
      "url": "http://localhost:8000/api/equipment",
      "method": "POST",              # POST 권장 (GET도 가능)
      "headers": {
        "Content-Type": "application/json",
        "X-Tenant-Id": "{tenant_id}", # 동적 변수 지원
        "Authorization": "Bearer {token}"
      },
      "timeout_ms": 30000,           # 선택 사항
      "retry_count": 3,              # 선택 사항
      "body_template": {             # 입력 매핑
        "status": "status",          # LLM 입력 → 요청 본문
        "limit": "limit"
      }
    }

2️⃣  Database Query 타입:
    {
      "source_ref": "source_asset_id",
      "timeout_ms": 5000
    }

3️⃣  Python Script 타입:
    {
      "script_path": "/scripts/tool.py",
      "timeout_ms": 10000
    }

중요:
  • {변수}는 동적 치환됨 (tenant_id, user_id 등)
  • URL은 상대경로 또는 절대경로 모두 가능
```

### 2.5 tool_input_schema (필수 ⭐⭐)

```
용도: LLM이 "어떤 입력"을 제공할지 결정하는 스키마

JSON Schema 형식:

{
  "type": "object",
  "description": "Input parameters for equipment search",

  "properties": {
    "status": {
      "type": "string",
      "description": "Equipment status filter",
      "enum": ["online", "offline", "maintenance"],
      "default": "online"
    },
    "location": {
      "type": "string",
      "description": "Physical location filter (optional)",
      "minLength": 1,
      "maxLength": 100
    },
    "limit": {
      "type": "integer",
      "description": "Maximum number of results",
      "minimum": 1,
      "maximum": 1000,
      "default": 100
    },
    "tags": {
      "type": "array",
      "description": "Filter by equipment tags",
      "items": { "type": "string" },
      "minItems": 1,
      "maxItems": 10
    }
  },

  "required": ["status"],  # status는 필수

  # 선택 사항:
  "additionalProperties": false  # 정해진 속성만 허용
}

스키마 작성 팁:

1️⃣  type 명시:
    ✅ "type": "string"
    ✅ "type": "integer"
    ✅ "type": "object"
    ✅ "type": "array"
    ✅ "type": "boolean"

2️⃣  description 작성 (LLM이 이해하도록):
    ❌ "status"           (무엇인지 모름)
    ✅ "Equipment status (online/offline/maintenance)"

3️⃣  제약 조건 명시:
    - minimum/maximum (숫자)
    - minLength/maxLength (문자열)
    - enum (선택지)
    - pattern (정규식)

4️⃣  기본값 제공:
    "default": "online"  (LLM이 입력 안 했을 때 사용)

5️⃣  필수 필드 지정:
    "required": ["status"]  (status는 반드시 제공)

예시 1: 간단한 입력
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query text"
    }
  },
  "required": ["query"]
}

예시 2: 복잡한 입력
{
  "type": "object",
  "properties": {
    "filters": {
      "type": "object",
      "properties": {
        "status": { "type": "string", "enum": ["A", "B"] },
        "date_from": { "type": "string", "format": "date-time" }
      }
    },
    "page": { "type": "integer", "minimum": 1 }
  },
  "required": ["filters"]
}
```

### 2.6 tool_output_schema (권장 ⭐⭐)

```
용도: LLM이 "어떤 응답"을 받을지 예상하는 스키마

JSON Schema 형식 (input과 유사):

{
  "type": "array",
  "description": "List of equipment with status",
  "items": {
    "type": "object",
    "description": "Equipment record",
    "properties": {
      "id": {
        "type": "string",
        "description": "Unique equipment identifier"
      },
      "name": {
        "type": "string",
        "description": "Equipment name"
      },
      "status": {
        "type": "string",
        "enum": ["online", "offline", "maintenance"],
        "description": "Current status"
      },
      "location": {
        "type": "string",
        "description": "Physical location"
      },
      "last_seen": {
        "type": "string",
        "format": "date-time",
        "description": "Last activity timestamp"
      }
    },
    "required": ["id", "name", "status"]
  }
}

출력 스키마의 역할:
  1️⃣  LLM이 응답을 이해하기 쉽게
  2️⃣  응답 검증 가능
  3️⃣  타입 오류 감지
  4️⃣  문서화

output_schema가 없으면:
  ⚠️  LLM이 응답 형식을 추측해야 함
  ⚠️  오류 해석 어려움
  ⚠️  응답 검증 불가능

따라서 꼭 작성하자!
```

### 2.7 tags (선택)

```
용도: Tool을 분류, 검색, 추적하는 메타데이터

예시:
{
  "category": "infrastructure",
  "domain": "equipment",
  "performance": "fast",
  "reliability": "99.9%",
  "cost": "free",
  "version": "1.0",
  "owner": "ops-team"
}

검색 활용:
  GET /asset-registry/tools?tags=infrastructure,fast
  → "infrastructure" AND "fast" 태그를 가진 도구들

내부 추적:
  tags.source = "api_manager"  (어디서 생성되었나)
  tags.api_id = "uuid"          (원본 API ID)
```

---

## 3. 실제 Tool 등록 예시

### 예시 1: 간단한 HTTP API Tool

```json
{
  "name": "Search Documents",
  "description": "Search company documents by keyword using hybrid vector + BM25 search. Accepts query text and search type. Returns matching documents with relevance scores.",
  "tool_type": "http_api",

  "tool_config": {
    "url": "/api/documents/search",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "X-Tenant-Id": "{tenant_id}"
    },
    "timeout_ms": 30000
  },

  "tool_input_schema": {
    "type": "object",
    "description": "Document search parameters",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query text (required)"
      },
      "search_type": {
        "type": "string",
        "enum": ["text", "vector", "hybrid"],
        "default": "hybrid",
        "description": "Search method: text (BM25), vector (semantic), or hybrid"
      },
      "top_k": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 10,
        "description": "Number of results to return"
      }
    },
    "required": ["query"]
  },

  "tool_output_schema": {
    "type": "object",
    "description": "Search results",
    "properties": {
      "query": { "type": "string" },
      "total_count": { "type": "integer" },
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "document_id": { "type": "string" },
            "document_name": { "type": "string" },
            "chunk_text": { "type": "string" },
            "relevance_score": { "type": "number" }
          }
        }
      }
    }
  },

  "tags": {
    "category": "document",
    "search_types": "hybrid,vector,text"
  }
}
```

### 예시 2: 복잡한 쿼리 Tool

```json
{
  "name": "Get Equipment List with Filters",
  "description": "Retrieve equipment inventory with optional filtering. Supports status, location, and tag filters. Returns equipment details including ID, name, status, location, and metadata. Use when checking device availability or generating inventory reports.",
  "tool_type": "http_api",

  "tool_config": {
    "url": "/runtime/api/equipment",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "X-Tenant-Id": "{tenant_id}"
    },
    "timeout_ms": 30000,
    "retry_count": 3,
    "body_template": {
      "filters": "filters",
      "limit": "limit",
      "offset": "offset"
    }
  },

  "tool_input_schema": {
    "type": "object",
    "description": "Equipment query parameters",
    "properties": {
      "filters": {
        "type": "object",
        "description": "Optional filters",
        "properties": {
          "status": {
            "type": "string",
            "enum": ["online", "offline", "maintenance", "disabled"],
            "description": "Equipment status filter"
          },
          "location": {
            "type": "string",
            "description": "Location filter (building or region)"
          },
          "tags": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Tag filters (any tag match)"
          }
        }
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 1000,
        "default": 100,
        "description": "Max results to return"
      },
      "offset": {
        "type": "integer",
        "minimum": 0,
        "default": 0,
        "description": "Pagination offset"
      }
    }
  },

  "tool_output_schema": {
    "type": "object",
    "properties": {
      "total_count": { "type": "integer" },
      "returned_count": { "type": "integer" },
      "data": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": { "type": "string" },
            "name": { "type": "string" },
            "status": { "type": "string" },
            "location": { "type": "string" },
            "model": { "type": "string" },
            "tags": { "type": "array", "items": { "type": "string" } },
            "last_check": { "type": "string", "format": "date-time" }
          },
          "required": ["id", "name", "status"]
        }
      }
    }
  },

  "tags": {
    "category": "infrastructure",
    "domain": "equipment",
    "filterable": true
  }
}
```

---

## 4. Admin UI에서 Tool 등록하기

### UI에서 입력 가능한 필드 (CreateToolModal.tsx)

```
┌─────────────────────────────────────────┐
│   Admin > Assets > Tools > [+] 新建      │
├─────────────────────────────────────────┤
│                                         │
│  입력 필드:                              │
│  ═════════════════════════════════════  │
│                                         │
│  1️⃣  Tool Name                         │
│     └─ 텍스트 입력                      │
│                                         │
│  2️⃣  Description                       │
│     └─ 긴 텍스트 (⭐ LLM 선택 결정)     │
│                                         │
│  3️⃣  Tool Type                         │
│     └─ 드롭다운:                       │
│        • database_query                │
│        • http_api ← 권장                │
│        • graph_query                   │
│        • python_script                 │
│                                         │
│  4️⃣  Tool Config                       │
│     └─ JSON 에디터                      │
│        {                               │
│          "url": "...",                 │
│          "method": "POST",             │
│          ...                           │
│        }                               │
│                                         │
│  5️⃣  Input Schema                      │
│     └─ JSON 에디터 (⭐ 매우 중요)       │
│        {                               │
│          "type": "object",             │
│          "properties": { ... }         │
│        }                               │
│                                         │
│  6️⃣  Output Schema (선택)               │
│     └─ JSON 에디터 (권장)                │
│        {                               │
│          "type": "array",              │
│          ...                           │
│        }                               │
│                                         │
│  7️⃣  [Save]                            │
│     └─ Tool Asset 생성 (draft 상태)    │
│                                         │
│  8️⃣  [Publish]                         │
│     └─ OPS Ask에서 즉시 사용 가능       │
│                                         │
└─────────────────────────────────────────┘
```

### 검증 규칙

```
UI는 다음을 검증합니다:

✅ 필수 필드:
   • name: 최소 1자
   • description: 최소 1자 (LLM 선택 중요)
   • tool_type: 선택 필수

✅ JSON 검증:
   • tool_config: 유효한 JSON
   • input_schema: 유효한 JSON
   • output_schema: 유효한 JSON (선택)

⚠️  경고 (진행 막지 않음):
   • description이 너무 짧으면: 경고
   • input_schema에 required가 없으면: 경고
   • output_schema가 없으면: 권장
```

---

## 5. LLM이 Tool을 사용하는 흐름

```
사용자 질문
  │
  ▼
LLM 플래너 (planner_llm.py)
  │
  ├─ 1️⃣  OPS에 등록된 모든 Tool 조회
  │   └─ Asset Registry에서 tool_type="http_api" 등 조회
  │
  ├─ 2️⃣  각 Tool의 description 읽음
  │   └─ "이 질문에 어떤 Tool이 도움될까?"
  │       예: "우리 장비의 온라인인 것만"
  │          → "Get Equipment List" Tool 발견!
  │
  ├─ 3️⃣  Tool의 input_schema 확인
  │   └─ "어떤 입력이 필요한가?"
  │       {
  │         "properties": {
  │           "status": "online/offline/maintenance"
  │         }
  │       }
  │
  ├─ 4️⃣  입력값 자동 생성
  │   └─ 질문 분석해서:
  │       { "status": "online", "limit": 100 }
  │
  ├─ 5️⃣  Tool 호출
  │   └─ tool_config.url로 요청 전송
  │       POST /runtime/api/equipment
  │       { "status": "online" }
  │
  ├─ 6️⃣  응답 수신
  │   └─ output_schema 기반 검증
  │       [
  │         { id: "eq1", name: "Device A", status: "online" },
  │         { id: "eq2", name: "Device B", status: "online" }
  │       ]
  │
  └─ 7️⃣  최종 답변 생성
      └─ "온라인 장비 2개: Device A, Device B"
```

---

## 6. 정보 누락 시 문제점

### ❌ description이 없거나 부정확할 때

```
Tool: "Get Data"  ← 뭔지 불명확
Description: "" ← 아무것도 없음

LLM 입장:
  "Get Data...? 이게 장비 정보인가, 로그인가, 문서인가?"
  → Tool을 사용하지 않음 (위험하니까)
  → 잘못된 답변 생성

반드시 작성해야 할 것:
  ✅ "Retrieve equipment status from database including
       device ID, name, current status (online/offline/maintenance),
       location, and last activity time. Use when you need to check
       if a device is available or get device inventory."
```

### ❌ input_schema가 없을 때

```
LLM 입장:
  "입력이 뭐여? 어떤 형식? 필수는?"
  → 추측해서 입력 생성 (오류 가능성 높음)
  → Tool 호출 실패

예시:
  요청: "상태가 온라인인 장비만"

  좋은 input_schema가 있으면:
    { "status": "online" } ← 정확함

  Schema가 없으면:
    { "equipment_status": "online" } ← 필드명 다를 수 있음
    { "status": "on" } ← 값 형식 다를 수 있음
```

### ❌ output_schema가 없을 때

```
LLM이:
  • 응답 형식을 모르면 → 잘못 해석
  • 오류 감지 안 함 → 잘못된 응답도 사용
  • 응답 검증 불가 → 품질 저하

응답이:
  [{ id: "1", name: "A", status: "on" }]  ← 일부만 반환

  Schema가 없으면: 그대로 사용 (incomplete)
  Schema가 있으면: 검증 → required 필드 누락 감지
```

---

## 7. 체크리스트: Tool 등록 전 확인

```
Tool을 등록하기 전에 이것들을 확인하세요:

필수 ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ name              명확하고 이해하기 쉬운가?
□ description      50자 이상인가?
                  무엇을 하는지 명확한가?
                  언제 쓰는지 설명했는가?
□ tool_type        올바른 타입인가? (http_api 권장)
□ tool_config.url  URL이 정확한가?
□ tool_input_schema JSON이 유효한가?
                  각 필드에 description이 있는가?
                  required 필드를 명시했는가?

권장 ⭐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ tool_output_schema JSON이 유효한가?
                    각 필드를 설명했는가?
□ tags            source나 category 태그 있는가?

테스트 🧪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ tool_config.url이 동작하는가?
□ input_schema 샘플로 호출 가능한가?
□ 응답이 output_schema와 일치하는가?
```

---

## 요약

### Tool을 LLM이 효과적으로 사용하려면:

| 필드 | 목적 | 중요도 |
|-----|------|--------|
| **name** | Tool 식별 | ⭐ |
| **description** | LLM 선택 결정 | ⭐⭐⭐ 필수! |
| **tool_type** | Tool 종류 | ⭐ |
| **tool_config** | 실제 호출 방법 | ⭐⭐ |
| **input_schema** | 입력 지정 | ⭐⭐⭐ 필수! |
| **output_schema** | 응답 이해 | ⭐⭐ 권장 |
| **tags** | 메타데이터 | ⭐ |

### 가장 자주 하는 실수:

1. ❌ **description이 너무 짧거나 모호** → LLM이 Tool을 선택 못함
2. ❌ **input_schema 필드명 불정확** → LLM이 잘못된 입력 생성
3. ❌ **output_schema 누락** → 응답 검증 불가
4. ❌ **JSON 포맷 오류** → 파싱 실패
5. ❌ **URL 오타** → Tool 호출 실패

### 필수 3가지:

1. 📝 **좋은 description** (50자 이상, 무엇/언제/왜)
2. 📋 **정확한 input_schema** (모든 필드 설명)
3. 📊 **output_schema** (응답 검증용)

이 3가지를 잘 준비하면 LLM이 Tool을 완벽하게 사용할 수 있습니다! 🚀

