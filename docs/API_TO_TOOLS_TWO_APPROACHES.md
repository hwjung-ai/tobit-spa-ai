# API Manager → Tools 등록: 2가지 방식 비교

**작성일**: 2026-02-09

---

## 1. 두 가지 방식 개요

### ✅ 방식 A: API Manager에서 먼저 정의 → "Tool로 등록" 버튼
```
API Manager (웹 UI)
└─ API 정의 (SQL/Python/HTTP)
   └─ [새] "Tool로 등록" 버튼
      └─ 자동으로 Tool Asset 생성
```

### ✅ 방식 B: Admin Tools에서 직접 HTTP API Tool 정의
```
Admin > Assets > Tools
└─ 수동으로 HTTP API Tool 생성
   ├─ name, description
   ├─ URL (HTTP endpoint)
   ├─ input_schema (JSON Schema)
   └─ output_schema (JSON Schema)
```

---

## 2. 상세 비교

### 방식 A: API Manager 경로

#### 📍 단계별 프로세스

```
1️⃣  Admin > API Manager
     └─ API 정의
        ├─ 이름: "Get Equipment List"
        ├─ 경로: /api/equipment
        ├─ 모드: SQL
        └─ 로직: SELECT id, name FROM equipment

2️⃣  테스트 버튼으로 즉시 확인
     ├─ Runtime: GET /runtime/api/equipment
     ├─ 응답: { columns: [...], rows: [...] }
     └─ 검증 완료 ✅

3️⃣  [새] "Tool로 등록" 버튼 클릭
     └─ 자동 변환 (이게 핵심!)
        ├─ API 메타데이터 추출
        ├─ Input Schema 자동 생성
        ├─ Output Schema 자동 생성
        └─ Tool Asset 생성

4️⃣  자동으로 OPS Ask에서도 사용 가능
     ├─ LLM이 Tool 발견
     ├─ 사용자 질문에 자동 호출
     └─ 결과 포함된 답변 생성
```

#### 💡 자동 변환 로직

```python
# API Manager API 정의
{
  "name": "Get Equipment List",
  "path": "/api/equipment",
  "method": "GET",
  "mode": "sql",
  "logic": "SELECT id, name, status FROM equipment WHERE status = $1 LIMIT 100"
}

        ↓ [자동 변환]

# Tool Asset으로 변환됨
{
  "asset_type": "tool",
  "name": "Get Equipment List",
  "description": "API from API Manager",
  "tool_type": "http_api",

  # 자동 생성된 Input Schema
  "tool_input_schema": {
    "type": "object",
    "required": ["status"],
    "properties": {
      "status": {
        "type": "string",
        "description": "Filter by equipment status"
      }
    }
  },

  # 자동 생성된 Output Schema
  "tool_output_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "id": { "type": "string" },
        "name": { "type": "string" },
        "status": { "type": "string" }
      }
    }
  },

  # Tool 호출 설정
  "tool_config": {
    "url": "/api/execute/api-uuid",
    "method": "POST",  # API 호출은 항상 POST
    "headers": {
      "X-Tenant-Id": "{tenant_id}"
    }
  },

  # 원본 추적
  "tags": {
    "source": "api_manager",
    "api_id": "original-uuid"
  }
}
```

#### 장점 ✅
1. **개발자 중심**: 웹 UI에서 API 작성 후 한 버튼으로 Tool화
2. **검증됨**: Runtime API로 이미 테스트한 API를 Tool로 등록
3. **자동화**: Input/Output Schema 자동 생성 (스키마 중복 작성 안 함)
4. **추적 가능**: API와 Tool의 연결 관계 유지 (tags.source)
5. **이중 사용**: 동시에 Runtime API + Tool로 사용 가능
6. **유지보수 쉬움**: API 수정하면 Tool도 자동 동기화 가능

#### 단점 ❌
1. **구현 필요**: "Tool로 등록" 버튼 개발 필요
2. **자동화 한계**: 복잡한 API는 스키마 수정 필요할 수 있음
3. **의존성**: API Manager가 변경되면 Tool도 영향

---

### 방식 B: Admin Tools 직접 등록

#### 📍 단계별 프로세스

```
1️⃣  Admin > Assets > Tools
     └─ [새로운 Tool 생성] 버튼

2️⃣  Tool 세부사항 입력
     ├─ 이름: "Get Equipment List"
     ├─ 설명: "Retrieve equipment from system"
     ├─ Tool Type: http_api
     ├─ URL: http://localhost:8000/runtime/api/equipment
     ├─ 메서드: POST
     └─ Headers: { X-Tenant-Id }

3️⃣  Input Schema 수동 작성
     ├─ 타입: object
     ├─ 속성:
     │  └─ "status": { type: string, required: true }
     └─ 자동 검증

4️⃣  Output Schema 수동 작성
     ├─ 타입: array
     └─ Items:
        └─ "id", "name", "status": string

5️⃣  Tool 발행
     ├─ 상태: draft → published
     ├─ 버전: 1
     └─ OPS Ask에서 즉시 사용 가능
```

#### 장점 ✅
1. **완전한 자유도**: 원하는 대로 URL, 스키마 정의
2. **외부 API 지원**: 어떤 HTTP 엔드포인트든 Tool화 가능
   - 자사 API Manager API
   - 타사 API (AWS, Slack 등)
   - 레거시 시스템
3. **독립적**: API Manager와 무관하게 작동
4. **즉시 사용**: 등록하면 바로 OPS Ask에서 사용 가능
5. **명시적**: 모든 설정을 직접 제어

#### 단점 ❌
1. **수동 작업**: Input/Output Schema를 직접 정의
2. **검증 부재**: Tool을 테스트하기 어려움 (네트워크 필요)
3. **중복 관리**: API Manager API와 Tool을 따로 관리
4. **스키마 오류**: 입력 실수로 Tool 작동 안 될 수 있음
5. **동기화 문제**: API 변경 시 Tool도 수동으로 수정
6. **문서화 필요**: Tool의 용도와 입출력 명확히 해야 함

---

## 3. 실제 비교

### 시나리오: "장비 상태 조회" Tool 만들기

#### 🔵 방식 A: API Manager → Tool

**Step 1: API Manager에서 정의 (5분)**
```
API Manager UI
├─ 이름: Get Equipment Status
├─ 경로: /api/equipment
├─ 모드: SQL
└─ 로직: SELECT id, name, status FROM equipment
```

**Step 2: 테스트 (2분)**
```
[테스트] 버튼
→ GET /runtime/api/equipment
→ 결과 확인 ✅
```

**Step 3: Tool로 등록 (클릭 1초!)**
```
[Tool로 등록] 버튼
→ ✅ Tool Asset 생성됨
→ Input/Output Schema 자동 생성됨
```

**Step 4: OPS Ask에서 사용 (1분 후)**
```
사용자: "우리 장비 중 온라인인 것만 보여줄래?"
↓
LLM: "Get Equipment Status" Tool 발견
↓
입력 자동 생성: { "status": "online" }
↓
Tool 호출
↓
결과 표시 ✅
```

**총 시간: ~8분** ⏱️

---

#### 🟠 방식 B: Admin Tools 직접 등록

**Step 1: Tools 생성 화면 열기 (30초)**
```
Admin > Assets > Tools > [+] 새로운 Tool
```

**Step 2: 메타데이터 입력 (3분)**
```
이름: Get Equipment Status
설명: Retrieve equipment from system
Tool Type: http_api
URL: http://localhost:8000/runtime/api/equipment
메서드: POST
```

**Step 3: Input Schema 작성 (5분)**
```
{
  "type": "object",
  "required": ["status"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["online", "offline", "maintenance"],
      "description": "Equipment status filter"
    }
  }
}
```

**Step 4: Output Schema 작성 (5분)**
```
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "id": { "type": "string" },
      "name": { "type": "string" },
      "status": { "type": "string" }
    },
    "required": ["id", "name", "status"]
  }
}
```

**Step 5: Tool 발행 (1분)**
```
[Save] → [Publish]
```

**Step 6: OPS Ask에서 사용 (1분 후)**
```
(방식 A와 동일)
```

**총 시간: ~15분** ⏱️

---

## 4. 기술적 차이

### 데이터 흐름

#### 방식 A
```
API Manager
├─ ApiDefinition (DB)
│  ├─ id: uuid
│  ├─ name: string
│  ├─ path: string
│  ├─ logic: SQL/Python/HTTP
│  └─ mode: "sql" | "python" | "http" | "workflow"
│
├─ [변환 로직] ← 새 코드
│  ├─ path → tool_config.url (/api/execute/{id})
│  ├─ logic의 파라미터 → input_schema
│  └─ 예상 결과 구조 → output_schema
│
└─ Tool Asset (TbAssetRegistry)
   ├─ asset_type: "tool"
   ├─ tool_type: "http_api"
   ├─ tool_config: { url, method, headers }
   ├─ tool_input_schema: { ... }
   ├─ tool_output_schema: { ... }
   └─ tags: { source: "api_manager", api_id: "..." }
```

#### 방식 B
```
Admin UI (직접 입력)
│
├─ tool_type: "http_api"
├─ URL: (사용자가 직접 입력)
├─ input_schema: (사용자가 직접 작성)
└─ output_schema: (사용자가 직접 작성)
    │
    └─ Tool Asset (TbAssetRegistry)
       ├─ asset_type: "tool"
       ├─ tool_type: "http_api"
       ├─ tool_config: { url, method, headers }
       ├─ tool_input_schema: { ... }
       ├─ tool_output_schema: { ... }
       └─ tags: {} (기존 Tool)
```

### 최종 Tool Asset 형태

**두 방식 모두 같음**:
```
TbAssetRegistry
├─ asset_id: UUID
├─ asset_type: "tool"
├─ name: string
├─ description: string
├─ tool_type: "http_api"
├─ tool_config: { url, method, headers }
├─ tool_input_schema: JSON Schema
├─ tool_output_schema: JSON Schema
├─ status: "draft" | "published"
├─ version: int
└─ tags: { source: "..." }
```

---

## 5. 선택 기준

### 방식 A를 선택해야 할 때 ✅

1. **자사 API**: API Manager에서 정의한 API를 Tool화
2. **개발자**: 웹 UI로 API를 먼저 작성하고 검증
3. **빠른 개발**: 자동 스키마 생성으로 시간 절감
4. **이중 사용**: Runtime API + Tool 동시 활용
5. **통제**: 한 곳에서 정의하면 자동 동기화

### 방식 B를 선택해야 할 때 ✅

1. **타사 API**: 외부 HTTP 서비스를 Tool화
   - AWS API
   - Slack API
   - GitHub API
   - 기타 REST API
2. **레거시**: 기존 API를 Tool로 래핑
3. **유연성**: 복잡한 설정이 필요한 경우
4. **독립성**: API Manager와 무관하게 작동
5. **명시성**: 모든 설정을 명확히 제어

---

## 6. 추천 전략: 하이브리드

### 일반적인 사용 패턴

```
┌─────────────────────────────────────┐
│         Tool 필요 여부               │
└──────┬──────────────────────────────┘
       │
   ┌───┴────┬───────────────────┐
   │        │                   │
   ▼        ▼                   ▼

자사 API  외부 API         기존 API
(신규)    (SaaS)         (레거시)
   │        │                   │
   │        │                   │
방식 A    방식 B              방식 B
   │        │                   │
   └────────┴───────────────────┘
            │
            ▼
   Tool Asset (최종)
            │
            ▼
   OPS Ask / AI 플래너
```

### 구현 로드맵

**Phase 1: 방식 B (현재 상태)**
```
Admin > Assets > Tools에서 HTTP API Tool 직접 등록
(이미 가능: init_document_search_tool.py 참고)
```

**Phase 2: 방식 A (권장)**
```
API Manager에서 "Tool로 등록" 버튼 추가
├─ API 정의 시 input/output schema 필드 추가
├─ 자동 변환 엔진 구현
└─ Tool Asset 자동 생성
```

**Phase 3: 관리**
```
Admin > Assets > Tools
├─ API Manager 소스 Tool (방식 A)
├─ 수동 등록 Tool (방식 B)
└─ 통합 관리 UI
```

---

## 7. 코드 예시

### 방식 A: API Manager에 추가할 코드

```python
# /apps/api/app/modules/api_manager/routes.py에 추가

@router.post("/apis/{api_id}/register-as-tool")
async def register_api_as_tool(
    api_id: str,
    session: Session = Depends(get_session),
):
    """
    Convert API Definition to Tool Asset.
    This creates a new Tool in Asset Registry that wraps this API.
    """
    # 1. API 조회
    api = get_api_definition(session, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")

    # 2. Input Schema 자동 생성
    input_schema = extract_input_schema(api.logic)

    # 3. Output Schema 자동 생성 (테스트 실행)
    output_schema = extract_output_schema(api)

    # 4. Tool Config 생성
    tool_config = {
        "url": f"/api/execute/{api_id}",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "X-Tenant-Id": "{tenant_id}"
        }
    }

    # 5. Tool Asset 생성
    from app.modules.asset_registry.crud import create_tool_asset

    tool_asset = create_tool_asset(
        session=session,
        name=api.name,
        description=api.description or f"Tool from API {api.name}",
        tool_type="http_api",
        tool_config=tool_config,
        tool_input_schema=input_schema,
        tool_output_schema=output_schema,
        tags={
            "source": "api_manager",
            "api_id": str(api_id),
            "mode": api.mode
        },
        created_by="system"
    )

    # 6. 발행
    publish_asset(session, tool_asset, "system")

    return {
        "status": "ok",
        "tool_id": str(tool_asset.asset_id),
        "api_id": str(api_id)
    }
```

### 방식 B: Admin UI에서 (이미 가능)

```python
# 현재 구현 참고
# /apps/api/app/modules/asset_registry/router.py

@router.post("/asset-registry/tools")
def create_tool(
    payload: dict,
    session: Session = Depends(get_session),
):
    """
    Create a new Tool Asset manually.
    User provides all details including URL and schemas.
    """
    tool_asset = create_tool_asset(
        session=session,
        name=payload["name"],
        description=payload["description"],
        tool_type=payload["tool_type"],  # "http_api"
        tool_config=payload["tool_config"],  # url, method, headers
        tool_input_schema=payload["tool_input_schema"],
        tool_output_schema=payload["tool_output_schema"],
        tags=payload.get("tags", {}),
        created_by=current_user.id
    )

    return { "asset_id": str(tool_asset.asset_id) }
```

---

## 8. 최종 정리

| 항목 | 방식 A | 방식 B |
|-----|--------|--------|
| **경로** | API Manager → Tool | Admin Tools 직접 |
| **개발 시간** | 짧음 (5-8분) | 중간 (10-15분) |
| **스키마** | 자동 생성 | 수동 작성 |
| **검증** | Runtime에서 테스트 | 네트워크 필요 |
| **외부 API** | ❌ | ✅ |
| **자동화 정도** | 높음 | 낮음 |
| **의존성** | API Manager에 종속 | 독립적 |
| **유지보수** | 쉬움 | 중간 |
| **권장 대상** | 자사 API | 타사 API, 외부 서비스 |

---

## 결론

### 최적 전략
1. **자사 API** → **방식 A** 사용 (API Manager에서 "Tool로 등록")
2. **타사 API** → **방식 B** 사용 (Admin Tools 직접 등록)
3. **관리**: 두 방식 모두 통합 Tool 관리 화면에서

### 다음 단계
- Phase 1: 방식 B로 실제 사용 경험 쌓기 (이미 가능)
- Phase 2: 방식 A 구현 (API Manager 확장)
- Phase 3: 통합 관리 UI 구축

