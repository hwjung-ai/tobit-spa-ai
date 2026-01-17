# UI Screen Asset CRUD (C3)

이 문서는 Screen Asset의 저장/불러오기/버전관리 CRUD 흐름을 설명합니다. CONTRACT_UI_CREATOR_V1.md의 규칙을 그대로 따릅니다.

## 1. DB Schema

`tb_asset_registry`는 Screen Asset을 포함하는 통합 테이블입니다.

- `asset_type = "screen"`
- `screen_id`: stable key (e.g. `maintenance_crud_v1`)
- `schema_json`: Screen Schema JSON (DB 컬럼명 그대로 유지)
- 버전/상태: `version`, `status` (draft/published)

관련 마이그레이션:
- `apps/api/alembic/versions/0029_add_screen_asset_fields.py`

## 2. API Router

모든 Screen Asset CRUD는 `/asset-registry` 아래에서 수행됩니다.

- `POST /asset-registry/assets`  
  - draft 생성 (asset_type=screen)
- `GET /asset-registry/assets?asset_type=screen`  
  - 목록 조회
- `GET /asset-registry/assets/{asset_id}`  
  - asset_id 또는 screen_id로 조회 가능 (published 기준)
- `PUT /asset-registry/assets/{asset_id}`  
  - draft 업데이트
- `POST /asset-registry/assets/{asset_id}/publish`  
  - publish + version 증가 + history 기록
- `POST /asset-registry/assets/{asset_id}/rollback`  
  - 특정 버전으로 rollback

구현: `apps/api/app/modules/asset_registry/router.py`

## 3. CRUD Flow (draft → publish → rollback)

1) draft 생성  
2) UI Schema 수정 후 draft 업데이트  
3) publish 실행 → 버전 증가, status=published  
4) 문제 발생 시 rollback 실행 → 이전 버전 복구

History 기록: `tb_asset_version_history`

## 4. Inspector 적용 자산 기록

`persist_execution_trace()` 단계에서 Answer blocks 중 `ui_screen`을 탐지해 screen asset 정보를 조회합니다.

Trace에 기록되는 형식:
```
applied_assets.screens: [
  { screen_id, version, status, applied_at, block_id, asset_id }
]
```

관련 코드:
- `apps/api/app/modules/inspector/service.py`
- `apps/api/app/modules/inspector/asset_context.py`
