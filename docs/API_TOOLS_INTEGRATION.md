# API Manager ↔ Tools Integration Guide

## 개요

API Manager에서 생성한 API를 Tools(Asset Registry)로 내보내기(Eport) 기능을 제공합니다. 이 기능은 사용자가 API Manager에서 정의한 API를 Tool로 재사용할 수 있게 합니다.

## 아키텍처

### 설계 원칙

1. **독립성 유지**: API Manager와 Tools는 독립적인 시스템으로 유지됩니다.
2. **유연한 가져오기**: 필요할 때만 Tools로 가져오기를 수행합니다.
3. **양방향 연결 추적**: 플래그 기반으로 연결 상태를 명확히 추적합니다.

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────┐
│ 1. API Manager에서 내보내기 준비                   │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
POST /api-manager/apis/{api_id}/export-to-tools
  ├─ ApiDefinition.linked_to_tool_name 설정
  ├─ ApiDefinition.linked_at 설정
  └─ linked_to_tool_id는 Tools 가져오기 시 설정
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Tools에서 가져오기 (추후 구현)                   │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
POST /asset-registry/tools/import-from-api-manager/{api_id}
  ├─ Tool Asset 생성
  ├─ input_schema 자동 생성
  └─ 양방향 연결 완성
```

## 데이터베이스 스키마

### ApiDefinition 모델 확장

```python
class ApiDefinition(SQLModel, table=True):
    # ... 기존 필드 ...
    
    # Tools export linkage
    linked_to_tool_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="asset_registry.asset_id",
        description="연결된 Tool Asset ID"
    )
    linked_to_tool_name: str | None = Field(
        default=None,
        description="연결된 Tool 이름"
    )
    linked_at: datetime | None = Field(
        default=None,
        description="Tool로 연결된 시간"
    )
```

### 연결 상태

| 상태 | linked_to_tool_id | linked_to_tool_name | linked_at | 의미 |
|-----|------------------|-------------------|-----------|-----|
| 미연결 | NULL | NULL | NULL | 내보내기/가져오기 전 |
| 내보내기 준비 | NULL | "Imported from API: ..." | timestamp | Tools로 가져오기 대기 |
| 연결됨 | UUID | Tool 이름 | timestamp | Tools에서 가져오기 완료 |

## API 엔드포인트

### 1. 내보내기 옵션 확인

```http
GET /api-manager/apis/{api_id}/export-options
Authorization: Bearer {token}
```

**응답 예시**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "api_id": "123e4567-e89b-12d3-a456-426614174000",
    "api_name": "Get Equipment Status",
    "can_export_to_tools": true,
    "linked_tool": null,
    "available_export_targets": ["tools"],
    "export_url": "/asset-registry/tools/import-from-api-manager/123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### 2. Tools로 내보내기

```http
POST /api-manager/apis/{api_id}/export-to-tools
Authorization: Bearer {token}
Content-Type: application/json

{
  "export": true
}
```

**요청 파라미터**:
- `export` (boolean, 필수): `true`로 설정하면 내보내기 준비, `false`로 설정하면 취소

**응답 예시 (준비 완료)**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "api_id": "123e4567-e89b-12d3-a456-426614174000",
    "api_name": "Get Equipment Status",
    "export_status": "ready",
    "message": "API ready for export. Complete import in Tools section.",
    "import_url": "/asset-registry/tools/import-from-api-manager/123e4567-e89b-12d3-a456-426614174000"
  }
}
```

**응답 예시 (이미 가져옴)**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "api_id": "123e4567-e89b-12d3-a456-426614174000",
    "api_name": "Get Equipment Status",
    "export_status": "already_imported",
    "message": "API already imported as tool: Tool: Get Equipment Status",
    "linked_tool": {
      "tool_id": "987e6543-e89b-12d3-a456-426614174999",
      "tool_name": "Tool: Get Equipment Status",
      "linked_at": "2026-02-10T14:00:00Z"
    }
  }
}
```

### 3. 연결 해제

```http
POST /api-manager/apis/{api_id}/unlink-from-tool
Authorization: Bearer {token}
```

**응답 예시**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "api_id": "123e4567-e89b-12d3-a456-426614174000",
    "api_name": "Get Equipment Status",
    "message": "Unlinked from tool: Tool: Get Equipment Status",
    "previous_link": {
      "tool_name": "Tool: Get Equipment Status",
      "linked_at": "2026-02-10T14:00:00Z"
    }
  }
}
```

## 프론트엔드 사용 예시

### API Manager 페이지

```tsx
function ApiCard({ api }: { api: ApiDefinition }) {
  const [isExporting, setIsExporting] = useState(false);
  
  const handleExportToTools = async () => {
    setIsExporting(true);
    try {
      const response = await fetch(
        `/api-manager/apis/${api.id}/export-to-tools`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ export: true })
        }
      );
      const result = await response.json();
      
      toast({
        title: "Export Ready",
        description: result.data.message,
        action: (
          <Button
            onClick={() => router.push("/admin/assets/tools?import-from-api=true")}
          >
            Go to Tools
          </Button>
        )
      });
    } catch (error) {
      toast({
        title: "Export Failed",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsExporting(false);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle>{api.name}</CardTitle>
            <CardDescription>{api.description}</CardDescription>
          </div>
          
          {api.linked_to_tool_id ? (
            <Badge variant="secondary">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              Linked to {api.linked_to_tool_name}
            </Badge>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportToTools}
              disabled={isExporting}
            >
              <Share2 className="w-4 h-4 mr-2" />
              Export to Tools
            </Button>
          )}
        </div>
      </CardHeader>
    </Card>
  );
}
```

## Tools 측 구현 (완료)

### 1. 내보내기 준비된 API 목록 조회

```http
GET /asset-registry/tools/available-api-exports
Authorization: Bearer {token}
```

**응답 예시**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "exports": [
      {
        "api_id": "123e4567-e89b-12d3-a456-426614174000",
        "api_name": "Get Equipment Status",
        "api_description": "Fetch equipment status from database",
        "api_mode": "sql",
        "api_method": "POST",
        "api_path": "/equipment/status",
        "linked_at": "2026-02-10T15:00:00Z",
        "is_imported": false
      }
    ],
    "total": 1
  }
}
```

### 2. API에서 Tool로 가져오기

```http
POST /asset-registry/tools/import-from-api-manager/{api_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Tool: Get Equipment Status",
  "description": "Custom description...",
  "infer_output_schema": true
}
```

**요청 파라미터**:
- `name` (string, 선택): Tool 이름 (기본값: "Tool from API: {api_name}")
- `description` (string, 선택): Tool 설명
- `infer_output_schema` (boolean, 선택): output_schema 자동 추론 여부 (기본값: false)

**응답 예시**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "tool_id": "987e6543-e89b-12d3-a456-426614174999",
    "tool_name": "Tool: Get Equipment Status",
    "api_id": "123e4567-e89b-12d3-a456-426614174000",
    "api_name": "Get Equipment Status",
    "status": "imported",
    "message": "Tool created successfully from API Manager",
    "asset": {
      "asset_id": "987e6543-e89b-12d3-a456-426614174999",
      "asset_type": "tool",
      "name": "Tool: Get Equipment Status",
      "description": "Tool imported from API Manager API 'Get Equipment Status'. Mode: sql. Use when: Fetch equipment status from database",
      "version": 1,
      "status": "draft",
      "tool_type": "http_api",
      "tool_config": {
        "url": "/api-manager/apis/123e4567-e89b-12d3-a456-426614174000/execute",
        "method": "POST",
        "headers": {
          "Content-Type": "application/json",
          "Authorization": "Bearer {token}",
          "X-Tenant-Id": "{tenant_id}"
        }
      },
      "tool_input_schema": {
        "type": "object",
        "properties": {},
        "required": []
      },
      "linked_from_api": {
        "api_id": "123e4567-e89b-12d3-a456-426614174000",
        "api_name": "Get Equipment Status",
        "linked_at": "2026-02-10T15:30:00Z",
        "import_mode": "api_to_tool",
        "last_synced_at": "2026-02-10T15:30:00Z",
        "is_internal_api": true
      },
      "created_at": "2026-02-10T15:30:00Z",
      "updated_at": "2026-02-10T15:30:00Z"
    }
  }
}
```

### 3. Tool과 API 동기화

```http
POST /asset-registry/tools/{tool_id}/sync-from-api
Authorization: Bearer {token}
```

**응답 예시**:
```json
{
  "time": "2026-02-10T15:30:00Z",
  "code": 0,
  "message": "OK",
  "data": {
    "tool_id": "987e6543-e89b-12d3-a456-426614174999",
    "tool_name": "Tool: Get Equipment Status",
    "synced_at": "2026-02-10T16:00:00Z",
    "api_version": "2026-02-10T15:45:00Z",
    "message": "Tool synced successfully from API Manager",
    "asset": {
      "asset_id": "987e6543-e89b-12d3-a456-426614174999",
      "asset_type": "tool",
      "name": "Tool: Get Equipment Status",
      "description": "Tool imported from API Manager API 'Get Equipment Status'. Mode: sql. Use when: Fetch equipment status from database",
      "version": 1,
      "status": "draft",
      "tool_type": "http_api",
      "tool_input_schema": {
        "type": "object",
        "properties": {
          "equipment_id": {"type": "string", "description": "Equipment ID"}
        },
        "required": ["equipment_id"]
      },
      "linked_from_api": {
        "api_id": "123e4567-e89b-12d3-a456-426614174000",
        "api_name": "Get Equipment Status",
        "linked_at": "2026-02-10T15:30:00Z",
        "import_mode": "api_to_tool",
        "last_synced_at": "2026-02-10T16:00:00Z",
        "is_internal_api": true
      },
      "created_at": "2026-02-10T15:30:00Z",
      "updated_at": "2026-02-10T16:00:00Z"
    }
  }
}
```

## 마이그레이션

### 마이그레이션 파일

마이그레이션 파일: `apps/api/alembic/versions/0050_add_tools_linkage_to_api_definitions.py`

### 마이그레이션 실행

```bash
cd apps/api
alembic upgrade head
```

또는:

```bash
make api-migrate
```

## 사용자 시나리오

### 시나리오 1: API Manager → Tools로 내보내기

1. 사용자가 API Manager에서 "Get Equipment Status" API 생성
2. 사용자가 "Export to Tools" 버튼 클릭
3. API가 내보내기 준비 상태로 변경
4. 사용자가 Tools 페이지로 이동
5. 사용자가 "Import from API Manager" 선택
6. 준비된 API 목록에서 "Get Equipment Status" 선택
7. Tool 생성 완료
8. API와 Tool 양방향 연결 완료

### 시나리오 2: API 변경 후 Tool 동기화

1. 사용자가 API Manager에서 API 수정 (예: 쿼리 변경)
2. 사용자가 Tools 페이지에서 해당 Tool 접근
3. "Sync from API" 버튼 클릭
4. Tool의 input_schema 등 업데이트
5. Tool의 last_synced_at 갱신

### 시나리오 3: 연결 해제

1. 사용자가 API Manager 또는 Tools에서 연결 해제 선택
2. 양방향 연결 플래그 초기화
3. API와 Tool 독립 상태로 변경

## 보안 고려사항

1. **인증**: 모든 엔드포인트에 인증(`get_current_user`) 필요
2. **권한**: API 소유자만 내보내기/가져오기 가능
3. **테넌트 격리**: tenant_id 기반 데이터 격리 유지

## 테스트

### 백엔드 테스트

```python
# tests/test_api_manager_export.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_export_api_to_tools():
    """API를 Tools로 내보내기 테스트"""
    response = client.post(
        "/api-manager/apis/{api_id}/export-to-tools",
        json={"export": true},
        headers={"Authorization": "Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["export_status"] == "ready"

def test_get_export_options():
    """내보내기 옵션 확인 테스트"""
    response = client.get(
        "/api-manager/apis/{api_id}/export-options",
        headers={"Authorization": "Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["can_export_to_tools"] == True

def test_unlink_api_from_tool():
    """연결 해제 테스트"""
    response = client.post(
        "/api-manager/apis/{api_id}/unlink-from-tool",
        headers={"Authorization": "Bearer {token}"}
    )
    assert response.status_code == 200
    assert "message" in response.json()["data"]
```

## 문서화

### 업데이트 필요한 문서

- [x] `docs/API_TOOLS_INTEGRATION.md` (본 문서)
- [ ] `docs/FEATURES.md` (기능 설명 추가)
- [ ] `docs/API_MANAGER_VS_TOOLS_ARCHITECTURE.md` (아키텍처 업데이트)

## 향후 작업

### Tools 측 구현 (추후 작업)

1. [ ] `GET /asset-registry/tools/available-api-exports` 엔드포인트
2. [ ] `POST /asset-registry/tools/import-from-api-manager/{api_id}` 엔드포인트
3. [ ] `POST /asset-registry/tools/{tool_id}/sync-from-api` 엔드포인트
4. [ ] TbAssetRegistry 모델 연결 필드 추가
5. [ ] Tools 페이지 UI 구현

### 프론트엔드 구현

1. [ ] API Manager 페이지: "Export to Tools" 버튼
2. [ ] Tools 페이지: "Import from API Manager" 다이얼로그
3. [ ] Tool 상세 페이지: 연결 정보 및 동기화 기능

## 참조

- API Manager Blueprint: `docs/BLUEPRINT_API_ENGINE.md`
- Asset Registry: `apps/api/app/modules/asset_registry/`
- API Manager Router: `apps/api/app/modules/api_manager/router.py`
- API Definition Model: `apps/api/models/api_definition.py`