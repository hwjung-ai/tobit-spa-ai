# Step 0: UI Creator ↔ 운영 루프 계약 (Contract V1)

**문서 버전**: v1.0
**상태**: FINAL (확정본, 구현 진행 가능)
**최종 수정**: 2026-01-17
**범위**: UI Creator와 Inspector/Regression/RCA 병렬 개발을 위한 3대 계약 고정

---

## 0. 핵심 원칙

### 설계 철학
- **운영 자산 대우**: Prompt/Policy처럼 UI Screen도 draft → published → rollback의 생명주기를 가진 "운영 자산"
- **Deterministic Execution**: 모든 UI 액션은 deterministic executor가 담당하며 trace_id로 증명 가능
- **분리된 책임**:
  - **Block ↔ Screen 분리**: Answer block은 "대화/응답 단위", Screen Schema는 "UI 정의 단위"
  - **단일 Action 엔드포인트**: 모든 UI 액션 실행은 `/ops/ui-actions` 하나로 통일
- **Trace 연동**: 실행의 모든 근거(applied_assets, asset_versions, execution steps)는 trace에 기록

---

## C0-1: Block ↔ Screen 경계 계약

### 1.1 `ui_screen` Block 타입 명세

새로운 answer block type을 도입: **`ui_screen`**

#### 1.1.1 Block 구조 (최종)

```python
# /apps/api/schemas/answer_blocks.py

class UIScreenBlock(BaseModel):
    """Screen 렌더링 트리거 블록"""
    type: Literal["ui_screen"]
    screen_id: str                          # Required: Published Screen Asset의 ID
    params: dict[str, Any] | None = None    # Optional: 화면에 전달할 파라미터
    bindings: dict[str, str] | None = None  # Optional: state 초기화 바인딩
    id: str | None = None                   # Block instance ID (optional)
    title: str | None = None                # Optional: UI 렌더러가 무시 가능

# AnswerBlock Union에 추가
AnswerBlock = Annotated[
    Union[
        ...,
        UIScreenBlock,  # ← 신규
    ],
    Field(discriminator="type"),
]
```

#### 1.1.2 필드 명세

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `type` | Literal["ui_screen"] | ✓ | Block 타입 고정값 |
| `screen_id` | str | ✓ | Published Screen Asset의 stable key |
| `params` | dict | ✗ | 화면 렌더링 시 초기 파라미터 (예: device_id, filter) |
| `bindings` | dict[str, str] | ✗ | state 바인딩 규칙 (key=화면 내부 경로, value=바인딩 표현식) |
| `id` | str | ✗ | Block 인스턴스 ID (trace에서 참조용) |
| `title` | str | ✗ | 선택적 제목 (UI 렌더러가 무시 가능) |

#### 1.1.3 예시 1: Read-Only 화면 (Device Detail)

```json
{
  "type": "ui_screen",
  "screen_id": "device_detail_v1",
  "params": {
    "device_id": "GT-1",
    "show_metrics": true
  },
  "bindings": {
    "params.device_id": "state.selected_device_id"
  },
  "id": "block_001"
}
```

**설명**:
- Screen asset `device_detail_v1` (published)를 로드
- 초기 파라미터로 device_id="GT-1" 전달
- 화면 내 params.device_id는 state.selected_device_id에서 실시간 바인딩

#### 1.1.4 예시 2: CRUD 화면 (Maintenance Modal)

```json
{
  "type": "ui_screen",
  "screen_id": "maintenance_crud_v2",
  "params": {
    "list_mode": true,
    "allow_create": true
  },
  "bindings": {
    "params.device_list": "state.devices",
    "params.selected_id": "state.selected_maintenance_id"
  },
  "id": "block_maint_001"
}
```

**설명**:
- 목록 + 모달 CRUD 패턴
- state.devices 변경 → params.device_list 자동 동기화

### 1.2 Screen Schema vs Answer Block 분리 원칙

#### 1.2.1 책임 분리 (법칙)

| 차원 | Answer Block | Screen Schema |
|------|-------------|--------------|
| **소유자** | LLM/Executor (어떤 화면을 보여줄지) | UI Creator (화면 내부 구조) |
| **생성 시점** | 질문 → 계획 → 실행 → block 생성 | 미리 설계 → publish |
| **변경 빈도** | 매 답변마다 | UI 업데이트 시 (별도 버저닝) |
| **렌더러** | Answer block renderer (web) | Screen renderer (web) |
| **저장소** | Execution trace | Asset registry (Screen Asset) |

#### 1.2.2 렌더링 흐름 (상세)

```
┌─────────────────────────────────────────────────────────────┐
│ Executor 실행 결과 (AnswerEnvelope)                         │
│ └─ blocks: [MarkdownBlock, UIScreenBlock, ...]              │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────┐
        │ Answer Block Renderer (Web)             │
        │ - Type discriminator 확인: "ui_screen"  │
        └─────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────────────────┐
    │ 1. screen_id에서 Published Screen Asset 로드        │
    │    GET /asset-registry/assets/device_detail_v1      │
    │    Response: {asset_id, screen_id, schema_json, ... │
    │    version: 3, status: "published"}                 │
    └──────────────────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────────────────┐
    │ 2. Screen Schema (JSON) 파싱 & 렌더러 선택          │
    │    - schema_json.layout (grid/form/modal/...)        │
    │    - schema_json.components (각 컴포넌트 정의)      │
    └──────────────────────────────────────────────────────┘
                          ↓
    ┌──────────────────────────────────────────────────────┐
    │ 3. 초기화 & 바인딩 적용                             │
    │    - params → state 초기화                          │
    │    - bindings 규칙으로 state 동기화                 │
    │    - action handlers 설정                           │
    └──────────────────────────────────────────────────────┘
                          ↓
            ┌────────────────────────┐
            │ UI 렌더 (React, etc)   │
            │ - 컴포넌트 트리 구성    │
            │ - Event handlers 바인딩│
            └────────────────────────┘
```

### 1.3 Trace 기록 규칙

#### 1.3.1 Applied Assets에 Screen 포함

Answer block이 ui_screen을 포함할 경우:

```python
# /apps/api/app/modules/inspector/service.py
# persist_execution_trace() 호출 시

applied_assets: Dict[str, Any] = {
    "prompts": [...],
    "policies": [...],
    "screens": [                          # ← 신규
        {
            "screen_id": "device_detail_v1",
            "version": 3,
            "status": "published",
            "applied_at": "2026-01-17T10:30:00Z",
            "block_id": "block_001"        # ui_screen block의 id
        }
    ]
}
```

#### 1.3.2 Inspector 표시

Inspector UI → Applied Assets 섹션:

```
┌──────────────────────────────────────┐
│ Applied Assets                       │
├──────────────────────────────────────┤
│ Prompts:                             │
│ └─ prompt_ci_analyze_v2 (v4)        │
│ Screens:                             │
│ └─ device_detail_v1 (v3) [published] │
│ Policies:                            │
│ └─ rate_limit_standard (v1)         │
└──────────────────────────────────────┘
```

### 1.4 구현 체크리스트

- [ ] `UIScreenBlock` 클래스 추가 (answer_blocks.py)
- [ ] AnswerBlock Union에 포함
- [ ] BlockRenderer에서 ui_screen 렌더링 로직 추가
- [ ] applied_assets.screens 구조 정의
- [ ] Inspector 화면에 Screens 섹션 추가

---

## C0-2: Screen Asset 운영 모델 계약

### 2.1 Screen Asset 메타데이터 스키마 (확정)

Screen Asset은 Prompt Asset과 동일한 운영 모델을 따름:

#### 2.1.1 DB 모델 (SQLModel)

```python
# /apps/api/app/modules/asset_registry/models.py

class TbAssetRegistry(SQLModel, table=True):
    # ... existing fields ...
    asset_type: str  # "prompt" | "mapping" | "policy" | "query" | "screen" ← 신규

# asset_type="screen" 전용 필드 (기존 선택 필드들)
# - screen_schema: dict[str, Any] (main content)
```

#### 2.1.2 Screen Asset 스키마 (Pydantic)

```python
# /apps/api/app/modules/asset_registry/schemas.py

class ScreenAssetCreate(BaseModel):
    """Screen asset 생성"""
    asset_type: Literal["screen"]  # 고정
    screen_id: str                 # stable key (예: "device_detail_v1")
    name: str                       # 화면 이름 (예: "Device Detail")
    description: str | None = None  # 용도 설명
    schema_json: dict[str, Any]     # Screen Schema (구조 정의)
    tags: dict[str, Any] | None = None
    created_by: str | None = None

class ScreenAssetRead(BaseModel):
    """Screen asset 조회"""
    asset_id: str                   # UUID
    asset_type: Literal["screen"]
    screen_id: str                  # stable key
    name: str
    description: str | None
    version: int
    status: Literal["draft", "published"]
    schema_json: dict[str, Any]
    tags: dict[str, Any] | None
    created_by: str | None
    published_by: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

class ScreenAssetUpdate(BaseModel):
    """Screen asset 업데이트 (draft만 가능)"""
    name: str | None = None
    description: str | None = None
    schema_json: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
```

### 2.2 Screen Schema 구조 명세

Screen asset 내부의 `schema_json` 필드 구조:

```python
# MVP 구조 (확장 가능)

ScreenSchema: TypedDict = {
    "version": "1.0",
    "layout": {
        "type": Literal["grid", "form", "modal", "list", "dashboard"],
        "direction": Literal["horizontal", "vertical"] = "vertical",
        "spacing": int = 8,
        "max_width": str = "100%"
    },
    "components": [
        {
            "id": str,                              # 컴포넌트 ID
            "type": Literal[                        # 컴포넌트 타입
                "text", "input", "select", "button",
                "table", "chart", "grid", "modal"
            ],
            "label": str | None = None,
            "bind": str | None = None,              # 바인딩 경로 (state.*)
            "props": dict[str, Any],                # 타입별 props
            "visibility": {
                "rule": str | None = None           # 표현식 (향후)
            },
            "actions": [                            # 컴포넌트 액션 (버튼 등)
                {
                    "id": str,
                    "label": str,
                    "handler": str                  # action_id (ui-actions 대상)
                }
            ]
        }
    ],
    "state_schema": {
        # 화면이 사용하는 state 필드 정의
        "device_id": {"type": "string"},
        "devices": {"type": "array", "items": {"type": "object"}},
        "__loading": {"type": "object"},
        "__error": {"type": "object"}
    },
    "metadata": {
        "author": str | None = None,
        "created_at": str | None = None,
        "notes": str | None = None
    }
}
```

#### 예시: Device Detail Screen Schema

```json
{
  "version": "1.0",
  "layout": {
    "type": "grid",
    "direction": "vertical",
    "spacing": 12
  },
  "components": [
    {
      "id": "device_header",
      "type": "text",
      "label": "Device Information",
      "bind": "state.device_name",
      "props": {
        "variant": "h2"
      }
    },
    {
      "id": "device_status",
      "type": "text",
      "bind": "state.device.status",
      "props": {
        "variant": "body2",
        "color": "secondary"
      }
    },
    {
      "id": "device_table",
      "type": "table",
      "bind": "state.device_details",
      "props": {
        "columns": ["key", "value"],
        "striped": true
      }
    },
    {
      "id": "refresh_btn",
      "type": "button",
      "label": "Refresh",
      "props": {
        "variant": "primary"
      },
      "actions": [
        {
          "id": "refresh_device",
          "label": "Refresh",
          "handler": "fetch_device_detail"
        }
      ]
    }
  ],
  "state_schema": {
    "device_id": {"type": "string"},
    "device_name": {"type": "string"},
    "device": {"type": "object"},
    "device_details": {"type": "array"},
    "__loading": {"type": "object"},
    "__error": {"type": "object"}
  },
  "metadata": {
    "author": "DevOps Team",
    "notes": "Read-only device details view"
  }
}
```

### 2.3 API 계약 (확정)

Asset Registry 기존 엔드포인트를 그대로 사용 (asset_type="screen"):

#### 2.3.1 화면 자산 목록 조회

```
GET /asset-registry/assets?asset_type=screen

Response 200:
{
  "success": true,
  "data": {
    "items": [
      {
        "asset_id": "uuid-1",
        "screen_id": "device_detail_v1",
        "asset_type": "screen",
        "name": "Device Detail",
        "version": 3,
        "status": "published",
        "published_at": "2026-01-10T15:30:00Z"
      }
    ],
    "total": 42
  }
}
```

#### 2.3.2 특정 화면 자산 조회

```
GET /asset-registry/assets/{asset_id}

Response 200:
{
  "success": true,
  "data": {
    "asset_id": "uuid-1",
    "screen_id": "device_detail_v1",
    "asset_type": "screen",
    "name": "Device Detail",
    "version": 3,
    "status": "published",
    "schema_json": { ... },
    "created_by": "alice@example.com",
    "published_by": "bob@example.com",
    "published_at": "2026-01-10T15:30:00Z",
    "created_at": "2026-01-08T10:00:00Z",
    "updated_at": "2026-01-10T15:25:00Z"
  }
}

# 버전별 조회 (선택)
GET /asset-registry/assets/{asset_id}?version=2

Response: 버전 2의 스냅샷
```

#### 2.3.3 Draft 화면 자산 생성

```
POST /asset-registry/assets

Request:
{
  "asset_type": "screen",
  "screen_id": "new_screen_v1",
  "name": "New Screen",
  "description": "...",
  "schema_json": { ... },
  "tags": {"category": "admin"},
  "created_by": "alice@example.com"
}

Response 201:
{
  "success": true,
  "data": {
    "asset_id": "uuid-new",
    "asset_type": "screen",
    "screen_id": "new_screen_v1",
    "version": 1,
    "status": "draft",
    "created_at": "2026-01-17T10:30:00Z"
  }
}
```

#### 2.3.4 Draft 화면 자산 업데이트

```
PUT /asset-registry/assets/{asset_id}

Request (draft만 가능):
{
  "name": "Updated Name",
  "schema_json": { ... }
}

Response 200:
{
  "success": true,
  "data": { updated asset }
}
```

#### 2.3.5 화면 자산 발행 (publish)

```
POST /asset-registry/assets/{asset_id}/publish

Request:
{
  "published_by": "bob@example.com"
}

Response 200:
{
  "success": true,
  "data": {
    "asset_id": "uuid-1",
    "version": 3,
    "status": "published",
    "published_at": "2026-01-17T10:35:00Z",
    "published_by": "bob@example.com"
  }
}

# Trace 기록:
# - asset_id, screen_id, version, published_by → audit_log
```

#### 2.3.6 화면 자산 이전 버전 복구 (rollback)

```
POST /asset-registry/assets/{asset_id}/rollback

Request:
{
  "target_version": 2,
  "published_by": "bob@example.com"
}

Response 200:
{
  "success": true,
  "data": {
    "asset_id": "uuid-1",
    "version": 4,  # 새 버전 (v2 스냅샷의 복사본)
    "status": "published",
    "rollback_from_version": 3,
    "published_at": "2026-01-17T10:40:00Z"
  }
}

# Trace 기록:
# - rollback_from_version=3 → audit_log
```

#### 2.3.7 Draft 화면 자산 삭제

```
DELETE /asset-registry/assets/{asset_id}

Precondition: status == "draft"

Response 204 (No Content)
```

### 2.4 Trace 연동 규칙 (Screen Asset)

#### 2.4.1 Screen Asset 로드 시

UI block renderer가 asset을 로드할 때:

```python
# Pseudo-code (web 렌더러)
async function renderUIScreen(block: UIScreenBlock) {
    // 1. Asset 로드 (캐시 또는 DB)
    const asset = await getPublishedScreenAsset(block.screen_id);

    // 2. Trace에 기록할 정보 수집
    const appliedScreen = {
        screen_id: block.screen_id,
        asset_id: asset.asset_id,
        version: asset.version,
        status: asset.status,
        published_at: asset.published_at,
        applied_at: new Date().toISOString()
    };

    // 3. Parent trace에 applied_assets.screens 추가
    // (API 응답 시점에 이미 포함되어야 함)
}
```

#### 2.4.2 Execution Trace 기록 (API 측)

```python
# /apps/api/app/modules/inspector/service.py

def persist_execution_trace(
    ...,
    applied_assets: Dict[str, Any] | None = None,
    ...
):
    """
    Answer block에 ui_screen이 포함되면:
    """
    if any(block.type == "ui_screen" for block in blocks):
        screens_to_apply = []
        for block in blocks:
            if block.type == "ui_screen":
                # Asset 로드
                asset = get_published_screen_asset(block.screen_id)
                screens_to_apply.append({
                    "screen_id": block.screen_id,
                    "asset_id": str(asset.asset_id),
                    "version": asset.version,
                    "status": asset.status,
                    "published_at": asset.published_at.isoformat(),
                    "block_id": block.id
                })

        if applied_assets is None:
            applied_assets = {}
        applied_assets["screens"] = screens_to_apply

    # DB에 저장
    trace_record = TbExecutionTrace(
        ...
        applied_assets=applied_assets,
        asset_versions=[...],  # screen versions 포함
        ...
    )
    session.add(trace_record)
    session.commit()
```

#### 2.4.3 Audit Log

Screen asset 생성/발행/롤백 시:

```python
def log_screen_asset_change(
    event: Literal["create", "publish", "rollback"],
    asset_id: str,
    screen_id: str,
    version: int,
    actor: str,
    details: Dict[str, Any] | None = None
):
    """
    Audit trail for compliance
    """
    log_record = {
        "event": event,
        "asset_id": asset_id,
        "screen_id": screen_id,
        "version": version,
        "actor": actor,
        "timestamp": datetime.now(),
        "details": details or {}
    }
    # → audit_logs table
```

### 2.5 구현 체크리스트

- [ ] asset_type 리스트에 "screen" 추가
- [ ] TbAssetRegistry: screen 필드 추가 (또는 기존 필드 재사용)
- [ ] Screen asset 스키마 클래스 추가
- [ ] API 라우터: screen asset 필터링 로직
- [ ] Trace 기록 로직: applied_assets.screens 구조
- [ ] Audit log: Screen asset 변경 이벤트
- [ ] Inspector UI: Screens 섹션 렌더링

---

## C0-3: Runtime Action 단일화 + Binding 규칙 계약

### 3.1 Action Schema (확정)

모든 UI 액션은 **공통 Schema**를 따르며, `/ops/ui-actions` 단일 엔드포인트로 실행됨:

#### 3.1.1 Action 정의 (Screen Schema 내)

```python
# Screen schema 내 component.actions[]

class ScreenAction(BaseModel):
    """Screen 컴포넌트 액션 정의"""
    id: str                         # 액션 ID (고유)
    label: str                      # UI 표시 텍스트
    handler: str                    # action_id (executor에서 매칭)
    endpoint: str = "/ops/ui-actions"  # 항상 고정
    method: Literal["POST"] = "POST"   # 항상 고정
    payload_template: dict[str, Any]   # 바인딩 템플릿
    context_required: list[str] | None = None  # 선택: 필요한 context 필드
```

#### 3.1.2 Action 실행 요청 (UIActionRequest)

```python
# /apps/api/app/modules/ops/schemas.py

class UIActionRequest(BaseModel):
    """UI 액션 실행 요청"""
    trace_id: str | None = None          # Parent trace (옵션, 권장)
    action_id: str                       # Handler ID
    inputs: dict[str, Any]               # 사용자 입력 ({{inputs.field}})
    context: dict[str, Any] = {}         # 실행 context (mode, tenant_id, ...)
    screen_id: str | None = None         # 현재 화면 ID (옵션)
```

#### 3.1.3 Action 실행 응답 (UIActionResponse)

```python
# /apps/api/app/modules/ops/schemas.py

class UIActionResponse(BaseModel):
    """UI 액션 실행 결과"""
    trace_id: str                        # 새로 생성된 trace
    parent_trace_id: str | None = None   # 부모 trace (있으면)
    status: Literal["ok", "error"]
    blocks: list[dict[str, Any]]         # AnswerBlock들 (JSON)
    error: str | None = None             # 에러 메시지 (status="error")
    duration_ms: int
```

### 3.2 Payload Template 규칙 (확정)

모든 action payload는 **템플릿 문자열** (`{{...}}`)로 표현되며, 실행 시 바인딩 엔진이 치환:

#### 3.2.1 사용 가능한 바인딩 변수

| 변수 유형 | 표현식 | 예시 | 설명 |
|---------|--------|-----|------|
| **inputs** | `{{inputs.field_id}}` | `{{inputs.device_id}}` | 폼/테이블 입력값 |
| **state** | `{{state.path}}` | `{{state.device.name}}` | 화면 상태 |
| **trace** | `{{trace_id}}` | `{{trace_id}}` | 현재 trace ID |
| **context** | `{{context.key}}` | `{{context.mode}}` | 실행 context |
| **literals** | `"string"`, `123`, `true` | `"raw_value"` | 정적 값 |

#### 3.2.2 Dot-path 전용 (표현식 금지)

- ✅ 허용: `{{state.device.id}}`
- ✅ 허용: `{{inputs.filter}}`
- ❌ 금지: `{{state.device.id + 1}}` (계산 금지)
- ❌ 금지: `{{Math.random()}}` (함수 호출 금지)
- ❌ 금지: `{{state[inputs.key]}}` (동적 접근 금지)

### 3.3 Binding Engine 규칙 (MVP)

#### 3.3.1 3가지 바인딩 유형

##### A) State ← Component Props (읽기)

화면 렌더링 시, component props는 state에서 동기화:

```json
{
  "components": [
    {
      "id": "device_table",
      "type": "table",
      "bind": "state.devices",
      "props": {
        "rows": "{{state.devices}}",
        "loading": "{{state.__loading['fetch_devices']}}"
      }
    }
  ]
}
```

**바인딩 규칙**:
- `bind` 필드의 값이 state 경로
- `props` 내 `{{...}}` 표현식은 실시간 구독(reactive)

##### B) Action Payload ← Inputs (쓰기)

액션 실행 시, payload는 사용자 입력 + state에서 조성:

```json
{
  "id": "save_device",
  "label": "Save",
  "handler": "save_device_action",
  "payload_template": {
    "device_id": "{{inputs.device_id}}",
    "name": "{{inputs.name}}",
    "location": "{{inputs.location}}",
    "created_by": "{{context.user_id}}",
    "trace_id": "{{trace_id}}"
  }
}
```

**바인딩 규칙**:
- `{{inputs.*}}`: 폼 필드 또는 테이블 선택 항목
- `{{state.*}}`: 기존 상태 값
- `{{context.*}}`, `{{trace_id}}`: 메타데이터

##### C) State ← Action Result (업데이트)

액션 실행 후, 결과를 state에 저장:

```python
# 개념적 (web 렌더러 구현)
class UIScreenState:
    async def executeAction(action, inputs):
        # 1. payload 렌더링
        payload = renderTemplate(action.payload_template, {
            inputs: inputs,
            state: this.state,
            context: this.context,
            trace_id: this.trace_id
        })

        # 2. API 호출
        response = await POST("/ops/ui-actions", {
            trace_id: this.trace_id,
            action_id: action.handler,
            inputs: inputs,
            context: this.context
        })

        # 3. State 업데이트 (result binding)
        if (action.result_binding) {
            // e.g. state.device ← response.blocks[0].data
            this.state[action.result_binding.target] =
                getValue(response, action.result_binding.source)
        }

        // 4. Loading/Error state 자동 처리
        this.state.__loading[action.handler] = false
        if (response.status === "error") {
            this.state.__error[action.handler] = response.error
        }
```

#### 3.3.2 Loading & Error State (자동 관리)

모든 액션 실행은 다음 state를 자동 관리:

```typescript
// State structure
{
  __loading: {
    "fetch_devices": false,      // 액션별 로딩 상태
    "save_device": false
  },
  __error: {
    "fetch_devices": null,       // 액션별 에러 메시지
    "save_device": "Validation failed"
  }
}
```

**규칙**:
1. 액션 시작 시 `state.__loading[action_id] = true`
2. 액션 완료 시 `state.__loading[action_id] = false`
3. 에러 발생 시 `state.__error[action_id] = error_message`
4. 성공 시 `state.__error[action_id] = null`

### 3.4 UI Actions 구현 규칙

#### 3.4.1 Executor 라우팅

```python
# /apps/api/app/modules/ops/services/ui_actions.py

async def execute_action_deterministic(
    action_id: str,
    inputs: dict[str, Any],
    context: dict[str, Any],
    session: Session
) -> dict[str, Any]:
    """
    Deterministic action executor

    Flow:
    1. action_id에 맞는 executor 선택
    2. OPS executors 활용 (config, history, metric, graph, etc.)
    3. AnswerBlock[] 생성
    4. ExecutorResult 반환
    """

    # Action registry에서 handler 조회
    handler = ACTION_REGISTRY.get(action_id)
    if not handler:
        raise ValueError(f"Unknown action_id: {action_id}")

    # 각 handler는 deterministic executor
    # 예: "fetch_device_detail" → config executor
    #     "list_maintenance" → history executor
    #     "create_maintenance" → api_manager executor

    result = await handler(
        inputs=inputs,
        context=context,
        session=session
    )

    return {
        "blocks": result.blocks,
        "tool_calls": result.tool_calls,
        "references": result.references,
        "summary": result.summary
    }
```

#### 3.4.2 Mask Sensitive Inputs

Trace에 기록하기 전에 민감정보 마스킹:

```python
def mask_sensitive_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    민감 필드 마스킹 (비밀번호, API 키, 등)
    """
    masked = inputs.copy()

    sensitive_patterns = ["password", "secret", "token", "api_key", "credit_card"]

    for key in masked:
        if any(pattern in key.lower() for pattern in sensitive_patterns):
            if isinstance(masked[key], str):
                masked[key] = "***MASKED***"
            else:
                masked[key] = "***MASKED***"

    return masked
```

### 3.5 Trace 연동 규칙 (UI Actions)

#### 3.5.1 Trace 생성

```python
# /apps/api/app/modules/ops/router.py
# execute_ui_action() 함수

def execute_ui_action(payload: UIActionRequest, ...):
    trace_id = str(uuid.uuid4())                    # 신규 trace
    parent_trace_id = payload.trace_id or None      # 부모 연결

    # Span tracking
    clear_spans()
    action_span = start_span(
        name=f"ui_action:{payload.action_id}",
        kind="ui_action"
    )

    try:
        # Execute
        executor_result = await execute_action_deterministic(...)

        # End span
        end_span(action_span, status="ok")

        # Persist trace
        persist_execution_trace(
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            feature="ui_action",
            endpoint="/ops/ui-actions",
            question=f"UI Action: {payload.action_id}",
            status="success",
            request_payload={
                "trace_id": payload.trace_id,
                "action_id": payload.action_id,
                "inputs": mask_sensitive_inputs(payload.inputs),
                "context": payload.context,
                "screen_id": payload.screen_id
            },
            answer_envelope={
                "meta": {...},
                "blocks": executor_result["blocks"]
            },
            flow_spans=get_all_spans()
        )

        return UIActionResponse(
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            status="ok",
            blocks=executor_result["blocks"],
            duration_ms=...
        )
```

#### 3.5.2 Trace 구조 (Inspector에서 가시성)

```json
{
  "trace_id": "uuid-action-trace",
  "parent_trace_id": "uuid-parent-question-trace",
  "feature": "ui_action",
  "endpoint": "/ops/ui-actions",
  "method": "POST",
  "question": "UI Action: save_device_action",
  "status": "success",
  "duration_ms": 245,
  "request_payload": {
    "trace_id": "uuid-parent",
    "action_id": "save_device_action",
    "inputs": {
      "device_id": "GT-1",
      "name": "Server-01",
      "location": "DC-A"
    },
    "context": {"mode": "real", "user_id": "alice@example.com"},
    "screen_id": "device_detail_v1"
  },
  "answer": {
    "meta": {
      "route": "save_device_action",
      "route_reason": "UI action execution",
      "timing_ms": 245,
      "trace_id": "uuid-action-trace",
      "parent_trace_id": "uuid-parent"
    },
    "blocks": [
      {
        "type": "markdown",
        "content": "Device saved successfully"
      },
      {
        "type": "ui_screen",
        "screen_id": "device_detail_v1",
        "params": {"device_id": "GT-1"}
      }
    ]
  },
  "flow_spans": [
    {
      "span_id": "span_001",
      "name": "ui_action:save_device_action",
      "kind": "ui_action",
      "status": "ok",
      "ts_start_ms": 1000,
      "ts_end_ms": 1245,
      "duration_ms": 245
    },
    {
      "span_id": "span_002",
      "parent_span_id": "span_001",
      "name": "api_manager:save_device",
      "kind": "executor",
      "status": "ok",
      "ts_start_ms": 1010,
      "ts_end_ms": 1240,
      "duration_ms": 230,
      "summary": {
        "endpoint": "PUT /api/devices/GT-1",
        "status_code": 200
      }
    }
  ]
}
```

#### 3.5.3 Inspector 표시

UI Action trace는 Inspector에서:

```
┌──────────────────────────────────────────────────┐
│ Trace: uuid-action-trace                         │
├──────────────────────────────────────────────────┤
│ Parent: uuid-parent (Device Detail 화면)        │
│ Feature: ui_action                              │
│ Status: success (245 ms)                         │
├──────────────────────────────────────────────────┤
│ Action: save_device_action                       │
│ Inputs: device_id=GT-1, name=Server-01, ...     │
├──────────────────────────────────────────────────┤
│ Execution Timeline:                              │
│ └─ 0-245ms: ui_action:save_device_action        │
│    └─ 10-240ms: api_manager:save_device         │
│       └─ PUT /api/devices/GT-1 → 200            │
├──────────────────────────────────────────────────┤
│ Result Blocks:                                   │
│ - Markdown: "Device saved successfully"         │
│ - UI Screen: device_detail_v1 (v3, published)   │
└──────────────────────────────────────────────────┘
```

### 3.6 Payload 예시 (구체적)

#### 3.6.1 단순 조회 액션

```json
{
  "id": "fetch_device",
  "label": "Refresh Device",
  "handler": "fetch_device_detail",
  "payload_template": {
    "device_id": "{{inputs.device_id}}",
    "include_metrics": true,
    "trace_id": "{{trace_id}}"
  }
}
```

**실행 시**:
```python
inputs = {"device_id": "GT-1"}
context = {"user_id": "alice", "mode": "real"}
trace_id = "uuid-xyz"

# Binding engine 처리
payload = {
    "device_id": "GT-1",           # inputs.device_id 치환
    "include_metrics": true,        # 정적 값
    "trace_id": "uuid-xyz"          # trace_id 치환
}

# Executor 호출 (config mode로 device 조회)
result = await config_executor(payload)
```

#### 3.6.2 생성 액션 (CRUD)

```json
{
  "id": "create_maintenance",
  "label": "Create",
  "handler": "create_maintenance_ticket",
  "payload_template": {
    "op": "create",
    "device_id": "{{inputs.device_id}}",
    "maintenance_type": "{{inputs.maint_type}}",
    "description": "{{inputs.description}}",
    "scheduled_date": "{{inputs.scheduled_date}}",
    "priority": "{{inputs.priority}}",
    "assigned_to": "{{context.user_id}}",
    "trace_id": "{{trace_id}}"
  }
}
```

**실행 시**:
```python
inputs = {
    "device_id": "GT-1",
    "maint_type": "preventive",
    "description": "Routine maintenance",
    "scheduled_date": "2026-02-01",
    "priority": "normal"
}
context = {"user_id": "bob@example.com", "mode": "real"}
trace_id = "uuid-abc"

# Binding engine 처리
payload = {
    "op": "create",
    "device_id": "GT-1",
    "maintenance_type": "preventive",
    "description": "Routine maintenance",
    "scheduled_date": "2026-02-01",
    "priority": "normal",
    "assigned_to": "bob@example.com",
    "trace_id": "uuid-abc"
}

# Executor 호출 (api_manager로 POST)
result = await api_manager_executor(
    endpoint="POST /api/maintenance",
    payload=payload
)
```

#### 3.6.3 목록 조회 + 필터 (Stateful)

```json
{
  "id": "list_devices",
  "label": "Apply Filter",
  "handler": "list_devices_filtered",
  "payload_template": {
    "device_type": "{{inputs.device_type}}",
    "location": "{{inputs.location}}",
    "status": "{{state.filter_status}}",
    "offset": "{{state.pagination.offset}}",
    "limit": 20,
    "trace_id": "{{trace_id}}"
  }
}
```

**실행 시**:
```python
inputs = {
    "device_type": "server",
    "location": "DC-A"
}
state = {
    "filter_status": "active",
    "pagination": {"offset": 0}
}
trace_id = "uuid-def"

# Binding engine 처리
payload = {
    "device_type": "server",
    "location": "DC-A",
    "status": "active",            # state.filter_status
    "offset": 0,                   # state.pagination.offset
    "limit": 20,
    "trace_id": "uuid-def"
}
```

### 3.7 구현 체크리스트

- [ ] UIActionRequest, UIActionResponse 스키마 확정
- [ ] Action handler registry 구현
- [ ] execute_action_deterministic() 함수 구현
- [ ] Binding engine (template 치환) 구현
- [ ] mask_sensitive_inputs() 함수 구현
- [ ] Trace 생성 및 parent_trace_id 연결
- [ ] Flow span tracking (ui_action kind)
- [ ] Inspector UI: UI Action trace 표시

---

## E2E 예시 (End-to-End)

### Example A: Device Detail 화면 (Read-Only)

#### A-1. Screen Asset 정의

```python
# Step: UI Creator가 화면 설계
POST /asset-registry/assets
{
  "asset_type": "screen",
  "screen_id": "device_detail_v1",
  "name": "Device Detail",
  "description": "Device information view (read-only)",
  "schema_json": {
    "version": "1.0",
    "layout": {
      "type": "grid",
      "direction": "vertical",
      "spacing": 12
    },
    "components": [
      {
        "id": "device_header",
        "type": "text",
        "label": "Device",
        "bind": "state.device.name",
        "props": {"variant": "h2"}
      },
      {
        "id": "status_badge",
        "type": "text",
        "bind": "state.device.status",
        "props": {"variant": "body2", "color": "success"}
      },
      {
        "id": "device_grid",
        "type": "table",
        "bind": "state.device_details",
        "props": {
          "columns": ["Field", "Value"],
          "striped": true
        }
      },
      {
        "id": "refresh_btn",
        "type": "button",
        "label": "Refresh",
        "props": {"variant": "primary"},
        "actions": [
          {
            "id": "btn_refresh",
            "label": "Refresh",
            "handler": "fetch_device_detail",
            "payload_template": {
              "device_id": "{{inputs.device_id}}",
              "include_metrics": true,
              "trace_id": "{{trace_id}}"
            }
          }
        ]
      }
    ],
    "state_schema": {
      "device_id": {"type": "string"},
      "device": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "status": {"type": "string"}
        }
      },
      "device_details": {"type": "array"},
      "__loading": {"type": "object"},
      "__error": {"type": "object"}
    },
    "metadata": {
      "author": "DevOps Team",
      "notes": "Read-only device details"
    }
  },
  "created_by": "ui-creator@example.com"
}

# Response 201
{
  "asset_id": "uuid-1",
  "screen_id": "device_detail_v1",
  "version": 1,
  "status": "draft"
}
```

#### A-2. Screen Asset 발행

```python
POST /asset-registry/assets/uuid-1/publish
{
  "published_by": "ui-reviewer@example.com"
}

# Response 200
{
  "asset_id": "uuid-1",
  "version": 1,
  "status": "published",
  "published_at": "2026-01-17T10:30:00Z"
}
```

#### A-3. LLM/Executor가 화면 참조

```python
# Executor가 답변에 화면 포함
answer_envelope = {
  "meta": {
    "route": "config",
    "route_reason": "Device detail query",
    "timing_ms": 150,
    "trace_id": "trace-parent"
  },
  "blocks": [
    {
      "type": "markdown",
      "content": "Here's the device details for GT-1:"
    },
    {
      "type": "ui_screen",
      "screen_id": "device_detail_v1",
      "params": {
        "device_id": "GT-1"
      },
      "bindings": {
        "params.device_id": "state.selected_device_id"
      },
      "id": "block_device_001"
    }
  ]
}
```

#### A-4. Trace 기록

```python
# persist_execution_trace() 호출
applied_assets: Dict = {
  "prompts": [
    {"prompt_id": "prompt_analyze_device", "version": 2, "status": "published"}
  ],
  "screens": [
    {
      "screen_id": "device_detail_v1",
      "asset_id": "uuid-1",
      "version": 1,
      "status": "published",
      "published_at": "2026-01-17T10:30:00Z",
      "block_id": "block_device_001"
    }
  ]
}
```

#### A-5. Web 렌더링 및 사용자 상호작용

```typescript
// Answer block 렌더러
function renderUIScreen(block: UIScreenBlock) {
  // 1. Screen asset 로드
  const asset = await fetch(`/asset-registry/assets?screen_id=${block.screen_id}`)
  const screenSchema = asset.schema_json

  // 2. 초기 state 구성
  const state = {
    device_id: block.params.device_id,  // "GT-1"
    device: null,
    device_details: [],
    __loading: {},
    __error: {}
  }

  // 3. Screen 렌더 (React component)
  return (
    <ScreenRenderer
      schema={screenSchema}
      state={state}
      onAction={handleAction}
    />
  )
}

// 사용자가 Refresh 버튼 클릭
async function handleAction(action, inputs) {
  // Render payload template
  const payload = {
    device_id: inputs.device_id || "GT-1",
    include_metrics: true,
    trace_id: "trace-parent"
  }

  // Call UI action API
  const response = await POST("/ops/ui-actions", {
    trace_id: "trace-parent",
    action_id: "fetch_device_detail",
    inputs: {device_id: "GT-1"},
    context: {mode: "real", user_id: "alice"}
  })

  // Response: new trace (uuid-action) with blocks
  // Update state with new blocks
  state.device = response.blocks[0].data
  state.__loading['fetch_device_detail'] = false
}
```

#### A-6. Inspector 조회

```python
# Inspector에서 parent trace 조회
GET /inspector/traces/trace-parent

Response:
{
  "trace_id": "trace-parent",
  "feature": "config",
  "endpoint": "/ops/query",
  "question": "Show device detail for GT-1",
  "status": "success",
  "applied_assets": {
    "screens": [
      {
        "screen_id": "device_detail_v1",
        "version": 1,
        "status": "published"
      }
    ]
  },
  "answer": {
    "blocks": [
      {"type": "markdown", "content": "..."},
      {"type": "ui_screen", "screen_id": "device_detail_v1", ...}
    ]
  }
}

# 사용자가 Refresh 버튼 실행 → action trace 생성
GET /inspector/traces/uuid-action

Response:
{
  "trace_id": "uuid-action",
  "parent_trace_id": "trace-parent",
  "feature": "ui_action",
  "endpoint": "/ops/ui-actions",
  "question": "UI Action: fetch_device_detail",
  "status": "success",
  "request_payload": {
    "action_id": "fetch_device_detail",
    "inputs": {"device_id": "GT-1"}
  },
  "flow_spans": [
    {
      "span_id": "span_1",
      "name": "ui_action:fetch_device_detail",
      "duration_ms": 120
    },
    {
      "span_id": "span_2",
      "parent_span_id": "span_1",
      "name": "config_executor:device",
      "duration_ms": 115
    }
  ]
}
```

---

### Example B: Maintenance CRUD 화면

#### B-1. Screen Asset (다중 모드: 목록 + 생성 모달)

```json
{
  "asset_type": "screen",
  "screen_id": "maintenance_crud_v1",
  "name": "Maintenance Management",
  "description": "Create/read/update maintenance tickets",
  "schema_json": {
    "version": "1.0",
    "layout": {
      "type": "grid",
      "direction": "vertical",
      "spacing": 12
    },
    "components": [
      {
        "id": "list_header",
        "type": "text",
        "label": "Maintenance List",
        "props": {"variant": "h2"}
      },
      {
        "id": "filter_device",
        "type": "select",
        "label": "Filter by Device",
        "bind": "state.filter_device_id",
        "props": {
          "options": [
            {"label": "All", "value": ""},
            {"label": "GT-1", "value": "GT-1"},
            {"label": "GT-2", "value": "GT-2"}
          ]
        },
        "actions": [
          {
            "id": "apply_filter",
            "label": "Apply",
            "handler": "list_maintenance_filtered",
            "payload_template": {
              "device_id": "{{inputs.filter_device_id}}",
              "offset": "{{state.pagination.offset}}",
              "limit": 20,
              "trace_id": "{{trace_id}}"
            }
          }
        ]
      },
      {
        "id": "maintenance_table",
        "type": "table",
        "label": "Tickets",
        "bind": "state.maintenance_items",
        "props": {
          "columns": ["ID", "Device", "Type", "Status", "Action"],
          "selectable": true,
          "rows": "{{state.maintenance_items}}"
        }
      },
      {
        "id": "create_btn",
        "type": "button",
        "label": "Create Maintenance",
        "props": {"variant": "primary"},
        "actions": [
          {
            "id": "show_create_modal",
            "label": "Create",
            "handler": "open_maintenance_modal",
            "payload_template": {
              "mode": "create",
              "trace_id": "{{trace_id}}"
            }
          }
        ]
      },
      {
        "id": "create_modal",
        "type": "modal",
        "label": "Create Maintenance",
        "visibility": {
          "rule": "{{state.modal.open && state.modal.mode === 'create'}}"
        },
        "components": [
          {
            "id": "device_input",
            "type": "select",
            "label": "Device",
            "bind": "state.modal.device_id",
            "props": {
              "options": "{{state.available_devices}}"
            }
          },
          {
            "id": "type_input",
            "type": "select",
            "label": "Type",
            "bind": "state.modal.maintenance_type",
            "props": {
              "options": [
                {"label": "Preventive", "value": "preventive"},
                {"label": "Corrective", "value": "corrective"}
              ]
            }
          },
          {
            "id": "date_input",
            "type": "date",
            "label": "Scheduled Date",
            "bind": "state.modal.scheduled_date",
            "props": {}
          },
          {
            "id": "submit_btn",
            "type": "button",
            "label": "Create",
            "props": {"variant": "primary"},
            "actions": [
              {
                "id": "submit_create",
                "label": "Create",
                "handler": "create_maintenance_ticket",
                "payload_template": {
                  "op": "create",
                  "device_id": "{{state.modal.device_id}}",
                  "maintenance_type": "{{state.modal.maintenance_type}}",
                  "scheduled_date": "{{state.modal.scheduled_date}}",
                  "assigned_to": "{{context.user_id}}",
                  "trace_id": "{{trace_id}}"
                }
              }
            ]
          },
          {
            "id": "cancel_btn",
            "type": "button",
            "label": "Cancel",
            "props": {"variant": "outline"},
            "actions": [
              {
                "id": "close_modal",
                "label": "Cancel",
                "handler": "close_maintenance_modal",
                "payload_template": {
                  "trace_id": "{{trace_id}}"
                }
              }
            ]
          }
        ]
      }
    ],
    "state_schema": {
      "filter_device_id": {"type": "string"},
      "pagination": {
        "type": "object",
        "properties": {
          "offset": {"type": "integer"},
          "limit": {"type": "integer"}
        }
      },
      "maintenance_items": {"type": "array"},
      "available_devices": {"type": "array"},
      "modal": {
        "type": "object",
        "properties": {
          "open": {"type": "boolean"},
          "mode": {"type": "string"},
          "device_id": {"type": "string"},
          "maintenance_type": {"type": "string"},
          "scheduled_date": {"type": "string"}
        }
      },
      "__loading": {"type": "object"},
      "__error": {"type": "object"}
    }
  }
}
```

#### B-2. Action Handlers

##### 액션 1: 목록 필터

```python
@action_handler("list_maintenance_filtered")
async def list_maintenance(inputs, context, session):
    """
    Deterministic executor로 maintenance 목록 조회
    history executor 활용
    """
    payload = inputs  # device_id, offset, limit, trace_id

    result = await history_executor(
        query="SELECT * FROM maintenance WHERE device_id=?",
        params={"device_id": payload["device_id"]},
        offset=payload["offset"],
        limit=payload["limit"],
        session=session
    )

    return ExecutorResult(
        blocks=[
            TableBlock(
                type="table",
                columns=["ID", "Device", "Type", "Status"],
                rows=result.rows
            )
        ],
        tool_calls=[],
        references=[],
        summary={"total": result.total}
    )
```

##### 액션 2: 생성 모달 열기

```python
@action_handler("open_maintenance_modal")
async def open_modal(inputs, context, session):
    """UI 상태 변경 (로컬 state, no executor)"""

    return ExecutorResult(
        blocks=[
            MarkdownBlock(
                type="markdown",
                content="Create new maintenance ticket"
            )
        ],
        tool_calls=[],
        references=[],
        summary={"action": "modal_opened"}
    )
```

##### 액션 3: 티켓 생성

```python
@action_handler("create_maintenance_ticket")
async def create_ticket(inputs, context, session):
    """API manager executor로 create"""

    payload = inputs  # op, device_id, maintenance_type, scheduled_date, assigned_to

    result = await api_manager_executor(
        endpoint="POST /api/maintenance",
        payload=payload,
        session=session,
        context=context
    )

    return ExecutorResult(
        blocks=[
            MarkdownBlock(
                type="markdown",
                content=f"Maintenance ticket #{result.ticket_id} created successfully"
            )
        ],
        tool_calls=[],
        references=[],
        summary={"ticket_id": result.ticket_id}
    )
```

#### B-3. 사용자 흐름

```
1. 화면 로드 (ui_screen block)
   → state 초기화 (filter_device_id="", maintenance_items=[], modal={open: false})
   → list_maintenance_filtered 자동 호출 (초기 목록 로드)

2. 사용자가 디바이스 필터 선택 & Apply 클릭
   → inputs = {filter_device_id: "GT-1"}
   → payload_template 렌더링:
      {device_id: "GT-1", offset: 0, limit: 20}
   → list_maintenance_filtered 액션 실행
   → state.maintenance_items 업데이트

3. 사용자가 "Create Maintenance" 클릭
   → open_maintenance_modal 액션 실행
   → state.modal.open = true
   → 모달 표시 (state 바인딩)

4. 사용자가 모달에서 정보 입력 & Create 클릭
   → state.modal.device_id = "GT-1"
   → state.modal.maintenance_type = "preventive"
   → state.modal.scheduled_date = "2026-02-01"
   → create_maintenance_ticket 액션 실행
   → payload={op: "create", device_id: "GT-1", ...}
   → API 호출 → ticket 생성
   → state.modal.open = false (모달 닫기)
   → state.maintenance_items 갱신 (목록 재로드)

4. Inspector에서 모든 액션의 trace 확인
   → parent_trace_id로 체인 연결
   → flow_spans로 타임라인 표시
```

---

## 3. 구현 로드맵 (시간 추정 없음)

### Phase 0 (현재): 계약 고정 ✓

- [x] 3대 계약 문서화
- [x] 스키마 & 인터페이스 확정
- [x] E2E 예시 작성

### Phase 1: API & 스키마 구현

**UI Creator 팀**:
- [ ] UIScreenBlock 추가 (answer_blocks.py)
- [ ] Screen Asset 스키마 추가 (asset_registry/schemas.py)
- [ ] Screen Asset DB 마이그레이션
- [ ] Screen Asset CRUD API
- [ ] ScreenSchema 검증 로직

**Runtime 팀**:
- [ ] Binding engine 구현 (template 치환)
- [ ] execute_action_deterministic() 구현
- [ ] Action handler registry
- [ ] mask_sensitive_inputs() 함수
- [ ] UIActionRequest/Response 통합

**Inspector 팀**:
- [ ] applied_assets.screens 구조 지원
- [ ] UI Action trace 기록
- [ ] Parent trace 연결 (parent_trace_id)
- [ ] Flow span tracking (ui_action kind)

### Phase 2: Web 렌더링 & UI

**Web 팀**:
- [ ] UIScreenBlock 렌더러 추가
- [ ] Screen asset 로드 & 캐싱
- [ ] Screen schema 파싱
- [ ] Component 렌더링 엔진
- [ ] Binding engine (state ← component props)
- [ ] Action 실행 & state 업데이트
- [ ] Loading/Error state 관리

**Inspector Web**:
- [ ] UI Action trace 타임라인 표시
- [ ] Applied Screens 섹션 렌더링
- [ ] Parent trace 네비게이션

### Phase 3: 통합 & 테스트

- [ ] E2E 테스트 (Playwright 또는 Cypress)
- [ ] Inspector regression test
- [ ] Performance 테스트
- [ ] Security audit (민감정보 마스킹)

---

## 4. 호환성 & 마이그레이션

### 기존 코드와의 호환성

- **UIPanelBlock vs UIScreenBlock**:
  - UIPanelBlock: 기존 답변 내 인라인 UI (inputs/actions 정의)
  - UIScreenBlock: 새로운 Screen asset 참조 (screen_id 지정)
  - **공존 가능**: 같은 AnswerBlock Union에 모두 포함

- **기존 ui_panel 사용 코드**:
  - 변경 불필요
  - 점진적으로 ui_screen으로 마이그레이션 (권장)

### 마이그레이션 전략

1. **UI Creator 기존 화면 → Screen Asset으로 변환**
   - 기존 UIPanelBlock 정의 → Screen schema로 추출
   - Screen asset으로 등록 & publish

2. **기존 executor → action handler로 등록**
   - 기존 로직 재사용 (복사/이식 아님)
   - action handler wrapper로 감싸기

3. **점진적 전환**
   - Phase 1 끝나면 새 화면은 Screen Asset 사용
   - 기존 화면은 UIPanelBlock 유지 가능

---

## 5. 확장 포인트 (향후 고려)

### 5.1 바인딩 엔진 확장

현재 (MVP):
- Dot-path 만 허용

향후:
- 조건부 표시 (visibility rules): `state.mode === 'edit'`
- 계산된 props: `state.total * 1.1`
- 함수 호출: `formatDate(state.date)`

### 5.2 Component 타입 확장

현재:
- text, input, select, button, table, chart, grid, modal

향후:
- file upload
- date range picker
- tree view
- custom component (plugin)

### 5.3 Action 결과 바인딩

현재:
- 상태 업데이트는 action handler의 executor_result로 제한

향후:
- 명시적 result binding: `action.result_binding = {target: "state.device", source: "blocks[0].data"}`
- 변환 함수: `transform: "json.parse"`

### 5.4 multi-tenant 고려

- action_id, screen_id에 tenant 스코핑 (선택)
- API 응답에 tenant_id 포함 (선택)

---

## 6. FAQ & 주의사항

### Q1: UIPanelBlock과 UIScreenBlock의 차이는?

**UIPanelBlock** (기존):
- Answer block 내에 inputs/actions 정의
- 매 답변마다 새로 생성
- Asset 버전 관리 X

**UIScreenBlock** (신규):
- Published Screen Asset 참조만 (screen_id)
- 재사용 가능한 UI 정의
- Asset 버전 관리 O
- 여러 답변에서 같은 화면 참조 가능

### Q2: Action 실행 시 state는 어디서 관리되나?

**Web 렌더러 (클라이언트)**:
- 현재 screen의 state 관리
- action 실행 시 inputs + state 수집

**Backend (API)**:
- action 실행 로직만 (deterministic executor)
- state 업데이트는 web에서 응답 기반으로 처리

### Q3: Binding expression에서 계산이 필요하면?

현재: 불가능 (dot-path만)

해결책:
1. **Backend executor에서 미리 계산**: payload template에서 `{{state.total}}` 사용, backend에서 필요한 계산 추가
2. **Web에서 computed state**: state 정의 시 getter/derived 값 사용

### Q4: Screen asset 버전 관리는 어떻게 되나?

- 모든 변경 사항이 **새 version으로 기록** (atomic)
- Published 상태만 ui_screen block에서 사용 가능
- 이전 버전으로 rollback 가능 (new published version 생성)
- Trace에 applied_assets.screens[].version 기록

### Q5: Trace에서 Screen asset이 변경되면 어떻게 추적하나?

예: trace-1에서 device_detail_v1 (v1) 적용 → trace-2에서 v2 적용

```
Inspector 조회:
GET /inspector/traces?screen_id=device_detail_v1

Response:
[
  {trace_id: "trace-1", applied_assets.screens[0].version: 1},
  {trace_id: "trace-2", applied_assets.screens[0].version: 2}
]

Regression 감지:
baseline (v1) vs candidate (v2) 비교
```

### Q6: 민감정보 마스킹은 어떤 수준인가?

현재 (MVP):
- Payload template의 `{{inputs.password}}` → "***MASKED***"
- Pattern matching: password, secret, token, api_key, credit_card

향후:
- PII detection (이름, 전화, 이메일)
- Field-level policy

---

## 7. 참고: 기존 코드 기반

- **Answer blocks**: `/apps/api/schemas/answer_blocks.py`
- **Asset registry**: `/apps/api/app/modules/asset_registry/`
- **OPS executor**: `/apps/api/app/modules/ops/`
- **Inspector/Trace**: `/apps/api/app/modules/inspector/`
- **Web renderer**: `/apps/web/src/components/answer/`

---

## 결론

**Step 0 Contract V1**은 다음 3개의 계약을 **명문화 + 확정**했습니다:

1. **C0-1** (Block ↔ Screen 경계): ui_screen block으로 화면 참조, Screen Schema는 별도 자산
2. **C0-2** (Screen Asset 운영): Prompt와 동일한 draft/published/rollback 생명주기
3. **C0-3** (Action 단일화): /ops/ui-actions 하나의 엔드포인트, binding engine으로 deterministic 실행

이 계약서를 기반으로 **UI Creator(화면 제작)** 팀과 **운영 루프(Inspector/Regression/RCA)** 팀이 **병렬 개발**할 수 있습니다.

다음 단계: Phase 1 구현 (API, 스키마, 렌더러)

---

**Document Version**: v1.0 | **Status**: FINAL | **Date**: 2026-01-17
