# API Manager - 시스템에 등록된 API 조회

## 개요

API Manager는 시스템에 등록된 API를 조회하는 REST API 엔드포인트를 제공합니다. 이 기능은 인증 없이 접근 가능한 public endpoint입니다.

## API 목록 조회 엔드포인트

### GET /api-manager/apis

시스템에 등록된 모든 API 목록을 조회합니다.

**엔드포인트:** `GET /api-manager/apis`

**인증:** 불필요 (public endpoint)

**쿼리 파라미터:**
- `scope` (선택사항): API 범위 필터 (`system`, `custom`)

**응답 형식:**
```json
{
  "status": "ok",
  "data": {
    "apis": [
      {
        "id": "uuid",
        "scope": "system|custom",
        "name": "API 이름",
        "method": "GET|POST|PUT|DELETE",
        "path": "/runtime/path",
        "description": "API 설명",
        "tags": ["tag1", "tag2"],
        "mode": "sql|python|workflow|script|http",
        "logic": "API 로직",
        "is_enabled": true,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
```

**사용 예:**

1. **모든 API 조회:**
```bash
curl http://localhost:8000/api-manager/apis
```

2. **시스템 API만 조회:**
```bash
curl "http://localhost:8000/api-manager/apis?scope=system"
```

3. **사용자 정의 API만 조회:**
```bash
curl "http://localhost:8000/api-manager/apis?scope=custom"
```

## API 범위 (Scope)

API는 다음 범위로 분류됩니다:

- **system**: 시스템 기본 API (예: `/api-manager/metrics-summary`)
  - 초기 마이그레이션에서 등록됨
  - 수정은 가능하지만 삭제는 권장하지 않음
  
- **custom**: 사용자가 생성한 API
  - 사용자가 직접 등록한 API
  - 자유롭게 생성/수정/삭제 가능

## API 모드 (Mode)

API는 다음 모드로 실행될 수 있습니다:

- **sql**: PostgreSQL 쿼리 실행
- **python**: Python 스크립트 실행
- **workflow**: 여러 API를 순차적으로 실행하는 워크플로
- **script**: Python 스크립트 실행 (sql과 동일한 의미)
- **http**: 외부 HTTP 요청 실행

## 필터링 및 정렬

### Scope 필터링

```bash
# 시스템 API만
curl "http://localhost:8000/api-manager/apis?scope=system"

# 사용자 정의 API만
curl "http://localhost:8000/api-manager/apis?scope=custom"
```

### 삭제된 API 제외

삭제된 API (`deleted_at`이 NULL이 아닌 API)는 목록에 포함되지 않습니다.

## 소스 코드

**라우터:** `apps/api/app/modules/api_manager/router.py`

**구현:**
```python
@router.get("/apis", response_model=dict)
async def list_apis(
    scope: Optional[str] = Query(None), 
    session: Session = Depends(get_session)
):
    """List all available APIs (public endpoint - no authentication required)"""
    
    try:
        # Build query
        statement = select(ApiDefinition).where(ApiDefinition.deleted_at.is_(None))

        # Filter by scope if provided
        if scope:
            try:
                scope_enum = ApiScope(scope)
                statement = statement.where(ApiDefinition.scope == scope_enum)
            except ValueError:
                # Invalid scope, just return empty
                pass

        # Execute query
        apis = session.exec(statement).all()

        # Convert to dict format
        api_list = [
            {
                "id": str(api.id),
                "scope": api.scope.value,
                "name": api.name,
                "method": api.method,
                "path": api.path,
                "description": api.description,
                "tags": api.tags or [],
                "mode": api.mode.value if api.mode else None,
                "logic": api.logic,
                "is_enabled": api.is_enabled,
                "created_at": api.created_at.isoformat() if api.created_at else None,
                "updated_at": api.updated_at.isoformat() if api.updated_at else None,
            }
            for api in apis
        ]

        return {"status": "ok", "data": {"apis": api_list}}

    except Exception as e:
        logger.error(f"List APIs failed: {str(e)}")
        raise HTTPException(500, str(e))
```

## 관련 엔드포인트

### API 상세 조회
- `GET /api-manager/apis/{api_id}`: 특정 API 상세 조회

### API 실행 로그 조회
- `GET /api-manager/apis/{api_id}/execution-logs`: API 실행 이력 조회

### API 생성/수정
- `POST /api-manager/apis`: 새 API 생성
- `PUT /api-manager/apis/{api_id}`: 기존 API 수정

### API 실행
- `POST /api-manager/apis/{api_id}/execute`: API 실행

## 사용 예시

### 1. 시스템 API 목록 확인

```bash
curl -s http://localhost:8000/api-manager/apis?scope=system | jq
```

응답 예시:
```json
{
  "status": "ok",
  "data": {
    "apis": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "scope": "system",
        "name": "Metrics Summary",
        "method": "GET",
        "path": "/runtime/metrics-summary",
        "description": "시스템 메트릭 요약",
        "tags": ["metrics", "system"],
        "mode": "sql",
        "logic": "SELECT ...",
        "is_enabled": true,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
```

### 2. 사용자 정의 API 목록 확인

```bash
curl -s http://localhost:8000/api-manager/apis?scope=custom | jq '.data.apis[] | {name, path, mode}'
```

### 3. 특정 API 실행 로그 조회

```bash
API_ID="123e4567-e89b-12d3-a456-426614174000"
curl -s "http://localhost:8000/api-manager/apis/${API_ID}/execution-logs?limit=10" | jq
```

## 주의사항

1. **인증 불필요**: 이 엔드포인트는 public이므로 인증 토큰이 필요 없습니다.
2. **삭제된 API 제외**: soft delete된 API는 목록에 포함되지 않습니다.
3. **쿼리 파라미터 유효성**: 잘못된 scope 값이 전달되면 빈 목록이 반환됩니다.
4. **로직 보안**: `logic` 필드에 API 실행 로직이 포함될 수 있으므로 민감 정보는 제외해야 합니다.

## 향후 개발 사항

1. **페이지네이션**: API 목록이 많을 경우 페이징 지원 추가
2. **검색 기능**: 이름/태그/설명으로 검색 기능 추가
3. **정렬 기능**: 생성일/수정일/이름 순 정렬 추가
4. **카테고리 필터**: 태그 기반 카테고리 필터 추가
5. **상태 필터**: `is_enabled` 상태로 필터링 추가

## 참고

- **모델**: `apps/api/models/api_definition.py` (ApiDefinition)
- **라우터**: `apps/api/app/modules/api_manager/router.py`
- **CRUD**: `apps/api/app/modules/api_manager/crud.py`
- **실행기**: `apps/api/services/api_manager_executor.py`