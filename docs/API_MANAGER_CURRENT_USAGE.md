# API Manager 현재 사용 현황 분석

**작성일**: 2026-02-09

---

## 1. API Manager에서 정의한 API를 사용할 수 있는 곳

### 1.1 3가지 현재 사용처

```
┌─────────────────────────────────────────────────────┐
│         API Manager에서 정의한 API                   │
└────────────┬──────────────────────────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
[1]      [2]      [3]
/runtime  Screen  OPS
API       Editor  UI-Actions
```

---

## 2. 상세 분석

### **[1] Runtime API**: `/runtime/{path}`

#### 📍 위치
- **엔드포인트**: `/runtime/{path:path}` (GET/POST)
- **파일**: `/apps/api/app/modules/api_manager/runtime_router.py:59-134`
- **라우터 등록**: 메인 FastAPI 앱에 자동 등록

#### 🔧 기능
```
API Manager에서 정의한 API가 자동으로 /runtime 경로로 노출됨
```

#### 📊 사용 방식
```python
# API Manager에서 정의:
{
  "name": "Get Equipment List",
  "method": "GET",
  "path": "/api/equipment",  # 이것이 key
  "mode": "sql",
  "logic": "SELECT id, name FROM equipment LIMIT 100"
}

# 외부에서 호출:
GET /runtime/api/equipment?param1=value1
```

#### 🎯 사용 사례
- ✅ **모바일 앱** (REST API 호출)
- ✅ **외부 시스템** (데이터 조회)
- ✅ **Power BI/대시보드** (데이터 소스)
- ✅ **Postman/cURL** (API 테스트)

#### 🔐 보안
- 레이트 리미팅: 120 requests/min per IP
- SQL 검증: SELECT만 허용, 위험한 키워드 필터링
- 실행 로깅: 모든 호출 기록

#### 📝 예시
```bash
# 1. API Manager에서 정의
POST /api-manager/apis
{
  "name": "Get Device Status",
  "method": "GET",
  "path": "/devices/status",
  "mode": "sql",
  "logic": "SELECT * FROM devices WHERE status = $1"
}

# 2. 자동으로 Runtime API 노출됨
GET /runtime/devices/status?status=online

# 3. 응답
{
  "meta": {
    "route": "/devices/status",
    "timing_ms": 45
  },
  "data": {
    "api": {...},
    "result": {
      "columns": ["id", "name", "status"],
      "rows": [["dev1", "Device A", "online"], ...]
    }
  }
}
```

---

### **[2] Screen Editor Actions**: 화면 디자인에서 사용

#### 📍 위치
- **UI 파일**: `/apps/web/src/app/admin/screens`
- **Catalog 엔드포인트**: `/ops/ui-actions/catalog?include_api_manager=true`
- **실행 엔드포인트**: `/ops/ui-actions` (POST)

#### 🔧 기능
```
Screen Editor에서 화면의 버튼/이벤트에 API Manager API를 바인딩
```

#### 📊 구조

```
화면 정의 (Screen Schema)
├─ Components (Button, Table 등)
│  └─ onClicks/onSubmits 이벤트
│     └─ 액션 정의
│        └─ handler: "api_manager:api_id" ← API Manager API
│           └─ inputs: {...} (실행 파라미터)
└─ State 바인딩
   └─ result: 실행 결과
```

#### 🎯 사용 흐름

```
1️⃣  Admin > Screens > 새로운 화면 만들기
2️⃣  Button 컴포넌트 추가
3️⃣  Button onClickAction 설정
4️⃣  Action Type 선택 → "API Manager API"
5️⃣  Handler 목록에서 API 선택
    (예: "[API] Get Equipment List")
6️⃣  Input 파라미터 설정
    (예: { "status": "online" })
7️⃣  버튼 클릭 시 자동 실행
```

#### 📋 코드 구조

**Frontend - Action Catalog 로드** (`/apps/web/src/components/admin/screen-editor/actions/useActionCatalog.ts`):
```typescript
// Screen Editor에서 화면 정의 시 사용 가능한 액션 목록 로드
const loadCatalog = async () => {
  const response = await fetch(
    "/ops/ui-actions/catalog?include_api_manager=true"
  );
  const envelope = await response.json();
  const actions = envelope?.data?.actions ?? [];
  // [
  //   { action_id: "fetch_device_detail", ... }, // 내장 액션
  //   { action_id: "api_manager:uuid-123", ... }, // API Manager API
  // ]
};
```

**Backend - Catalog 생성** (`/apps/api/app/modules/ops/router.py:1298-1378`):
```python
@router.get("/ops/ui-actions/catalog")
def list_ui_actions_catalog(include_api_manager: bool = Query(False)):
    actions = list_registered_actions()  # 내장 액션들

    if include_api_manager:
        # API Manager 활성화 API 목록 조회
        apis = session.exec(
            select(ApiDefinition).where(
                ApiDefinition.deleted_at.is_(None),
                ApiDefinition.is_enabled == True,
            )
        ).all()

        for api in apis:
            # 각 API를 action_id로 변환
            action_item = {
                "action_id": f"api_manager:{api.id}",
                "label": f"[API] {api.name}",
                "source": "api_manager",
                "input_schema": { /* 자동 생성 */ },
                "api_manager_meta": {
                    "api_id": str(api.id),
                    "method": api.method,
                    "path": api.path,
                }
            }
```

**Frontend - Action 실행** (`/apps/web/src/components/admin/screen-editor/actions/ActionEditorModal.tsx`):
```typescript
// 버튼 클릭 시 액션 실행
const executeAction = async (action: ScreenAction) => {
  if (action.handler.startsWith("api_manager:")) {
    // API Manager API 실행
    const apiId = action.handler.substring("api_manager:".length);

    fetch("/ops/ui-actions", {
      method: "POST",
      body: JSON.stringify({
        action_id: action.handler,
        inputs: action.inputs, // 사용자가 정의한 파라미터
        context: { ... }
      })
    });
  }
};
```

#### 📝 예시 화면 정의

```json
{
  "screen_id": "device_management",
  "name": "Device Management",
  "components": [
    {
      "id": "btn_refresh",
      "type": "button",
      "label": "새로고침",
      "actions": [
        {
          "event": "onClick",
          "handler": "api_manager:8f2a3e1c-b4d9-4a2f-8c6d-2e4f5a9c7b1d",
          "inputs": {
            "api_id": "8f2a3e1c-b4d9-4a2f-8c6d-2e4f5a9c7b1d",
            "params": {
              "status": "active"
            }
          }
        }
      ]
    },
    {
      "id": "tbl_devices",
      "type": "table",
      "bind": "state.devices",
      "columns": ["id", "name", "status"]
    }
  ]
}
```

#### 🔄 실행 흐름

```
1. 사용자가 Screen Editor에서 API 선택
   ↓
2. /ops/ui-actions/catalog에서 API 메타데이터 로드
   ↓
3. 화면에 구성요소 배치
   ↓
4. 버튼/폼 이벤트에 액션 바인딩
   ↓
5. 런타임에 사용자가 버튼 클릭
   ↓
6. POST /ops/ui-actions (action_id, inputs)
   ↓
7. Backend: ActionRegistry에서 handler 실행
   ↓
8. API Manager API 호출 (/runtime/...)
   ↓
9. 결과를 화면 state에 업데이트 (state_patch)
```

---

### **[3] OPS UI-Actions**: 모니터링 화면의 액션

#### 📍 위치
- **엔드포인트**: `POST /ops/ui-actions`
- **파일**: `/apps/api/app/modules/ops/routes/ui_actions.py:35-230`
- **카탈로그**: `/ops/ui-actions/catalog?include_api_manager=true`

#### 🔧 기능
```
OPS 모니터링 화면에서 API Manager API를 액션으로 사용
```

#### 🎯 사용 사례
- ✅ **모니터링 대시보드**: 상태 조회 버튼
- ✅ **문제 진단**: 로그 조회 API
- ✅ **관리자 작업**: 데이터 수정/확인

#### 📋 요청/응답 구조

**요청**:
```json
POST /ops/ui-actions
{
  "action_id": "api_manager:8f2a3e1c-b4d9-4a2f-8c6d-2e4f5a9c7b1d",
  "inputs": {
    "api_id": "8f2a3e1c-b4d9-4a2f-8c6d-2e4f5a9c7b1d",
    "params": { "status": "online" }
  },
  "context": { ... },
  "trace_id": "parent-trace-uuid"
}
```

**응답**:
```json
{
  "status": "ok",
  "data": {
    "trace_id": "new-trace-uuid",
    "blocks": [
      {
        "type": "table",
        "columns": ["id", "name"],
        "rows": [["dev1", "Device A"]]
      }
    ],
    "state_patch": {
      "device_list": [...]
    },
    "references": [...]
  }
}
```

#### 🔐 보안 & 감사
- 모든 호출 trace 저장
- 실행 시간, 입력/출력 기록
- 에러 추적 및 롤백 지원

---

## 3. 비교 표

| 기준 | Runtime API | Screen Editor | OPS UI-Actions |
|-----|-----------|--------------|-----------------|
| **사용 목적** | 외부 시스템 연동 | 화면 UI 액션 | 모니터링 화면 |
| **호출자** | REST 클라이언트 | 화면 컴포넌트 | 사용자 (UI) |
| **경로** | `/runtime/{path}` | `/ops/ui-actions` | `/ops/ui-actions` |
| **인증** | 선택 (헤더 기반) | OAuth/토큰 | OAuth/토큰 |
| **동기/비동기** | 동기 | 비동기 가능 | 동기 |
| **로깅** | ApiExecutionLog | ExecutionTrace | ExecutionTrace |
| **State 업데이트** | ❌ | ✅ (state_patch) | ✅ (state_patch) |
| **응답 형식** | 테이블/JSON | Blocks | Blocks |

---

## 4. 현재 구조 다이어그램

```
┌─────────────────────────────────────┐
│     API Manager (웹 UI)              │
│                                      │
│  API 정의 (SQL/Python/HTTP/Workflow)│
│  - 이름, 경로, 메서드               │
│  - 실행 로직                        │
│  - 활성화 상태                      │
└─────────────┬───────────────────────┘
              │
              │ (API가 활성화되면)
              │
    ┌─────────┼──────────┐
    │         │          │
    ▼         ▼          ▼
┌────────┐ ┌───────┐ ┌──────────┐
│Runtime │ │Screen │ │OPS       │
│  API   │ │Editor │ │UI-Actions│
└────────┘ └───────┘ └──────────┘
    ▲         ▲          ▲
    │         │          │
  외부    화면 컴포넌트  모니터링
  시스템   이벤트       대시보드
```

---

## 5. 현재 API 검색 방식

### 5.1 API 목록 조회
```python
# Backend
GET /api-manager/apis
→ 모든 API 정의 반환 (custom + system)
→ scope별 필터링 가능

# Frontend
GET /api-manager/apis?search=...&scope=custom
→ API 목록 표시
```

### 5.2 Catalog (OPS/Screen에서)
```python
# Backend
GET /ops/ui-actions/catalog?include_api_manager=true
→ 내장 액션 + API Manager API를 통합 반환

# Frontend (useActionCatalog.ts)
const { items, handlerOptions, apiManagerOptions } = useActionCatalog(enabled);
→ API Manager API만 필터링 가능
```

---

## 6. 현재 한계점

### ❌ 문제 1: 스키마 자동화 부족
- API Manager의 input/output schema가 없음
- Screen Editor에서 파라미터 검증 불가
- API 목록에서 "params" 일괄 정의만 가능

### ❌ 문제 2: Tools와 중복
- API Manager API와 Asset Registry Tools가 분리
- OPS Ask에서는 Tools만 사용 가능
- API Manager API는 OPS Ask에서 자동 발견 안 됨

### ❌ 문제 3: 메타데이터 부족
- API의 input schema 정보 없음
- output schema 정보 없음
- LLM이 API를 자동 선택할 수 없음

### ❌ 문제 4: 외부 시스템 연동 복잡
- Runtime API는 알려야만 사용 가능
- API 목록 문서화 필요
- OpenAPI spec 자동 생성 안 됨

---

## 7. 개선 로드맵

### Phase 1: Schema 추가 (2주)
```python
# API Manager에 input/output schema 필드 추가
class ApiDefinition:
    ...
    input_schema: dict  # JSON Schema
    output_schema: dict # JSON Schema
```

### Phase 2: API → Tool 변환 (2주)
```
API Manager UI
└─ [새] "Tool로 등록" 버튼
   └─ 자동으로 Asset Registry에 Tool 생성
   └─ OPS Ask에서도 자동 발견 가능
```

### Phase 3: OpenAPI 지원 (1주)
```
GET /api-manager/openapi.json
→ Swagger/Postman과 호환되는 스펙 자동 생성
```

### Phase 4: API 목록 UI (1주)
```
/api-manager/published
→ 공개 API 목록 (외부 개발자용)
→ 문서화 + 코드 샘플
```

---

## 요약

### 현재 사용처 3가지

| # | 사용처 | 엔드포인트 | 대상 |
|---|-------|----------|-----|
| 1 | Runtime API | `/runtime/{path}` | 외부 시스템 |
| 2 | Screen Editor | `/ops/ui-actions` | 화면 컴포넌트 |
| 3 | OPS UI-Actions | `/ops/ui-actions` | 모니터링 |

### 다음 개선 방향
1. **Schema 추가**: input/output 자동 검증
2. **Tools 통합**: API Manager → Tools 변환
3. **LLM 연동**: OPS Ask에서 자동 발견
4. **OpenAPI**: 외부 도구 통합 (Postman, Swagger)

