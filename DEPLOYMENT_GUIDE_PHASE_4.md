# Phase 4 배포 & 실행 가이드

**버전**: v1.0
**상태**: 배포 준비 완료
**마지막 업데이트**: 2026-01-17

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [DB 마이그레이션](#db-마이그레이션)
3. [API 통합 검증](#api-통합-검증)
4. [테스트 실행](#테스트-실행)
5. [배포 체크리스트](#배포-체크리스트)
6. [트러블슈팅](#트러블슈팅)

---

## 사전 요구사항

### 환경

- Python 3.9+
- Node.js 18+
- PostgreSQL 13+
- pip, npm, poetry (설치되어 있어야 함)

### 설정 파일

```bash
# API 환경 변수 확인
cat /home/spa/tobit-spa-ai/apps/api/.env

# Web 환경 변수 확인
cat /home/spa/tobit-spa-ai/apps/web/.env.local
```

**필요한 환경 변수**:
```
# API
DATABASE_URL=postgresql://user:password@localhost/tobit_spa_db
OPS_MODE=real
LOG_LEVEL=INFO

# Web
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## DB 마이그레이션

### 1단계: 마이그레이션 파일 생성 확인

```bash
# 마이그레이션 파일 확인
ls -lah /home/spa/tobit-spa-ai/apps/api/alembic/versions/0029_*.py
```

**파일**:
```
0029_add_screen_asset_fields.py  (54줄)
```

**포함 내용**:
- `screen_id` 컬럼 추가 (nullable, Text)
- `schema_json` 컬럼 추가 (nullable, JSONB)
- `tags` 컬럼 추가 (nullable, JSONB)
- `screen_id` 인덱스 생성 (asset_type='screen' only)

### 2단계: 마이그레이션 실행

```bash
# 작업 디렉토리 이동
cd /home/spa/tobit-spa-ai/apps/api

# Alembic 마이그레이션 확인 (실행 예정 마이그레이션 확인)
alembic current
alembic upgrade --sql head | tail -50

# 마이그레이션 실행
alembic upgrade head
```

**예상 출력**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl with target database...
INFO  [alembic.runtime.migration] Will assume transactional DDL is supported
INFO  [alembic.runtime.migration] Upgrading database from revision 0028_add_flow_spans_column to 0029_add_screen_asset_fields
INFO  [alembic.runtime.migration] Running upgrade 0029_add_screen_asset_fields
```

### 3단계: 마이그레이션 검증

```bash
# PostgreSQL 연결
psql -U postgres -d tobit_spa_db

# 스키마 확인
\d tb_asset_registry

# 인덱스 확인
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'tb_asset_registry';

# 데이터 확인 (기존 데이터 있는 경우)
SELECT asset_id, asset_type, screen_id, schema_json, tags FROM tb_asset_registry LIMIT 5;
```

**예상 결과**:
- `screen_id` 컬럼 (text, nullable) ✅
- `schema_json` 컬럼 (jsonb, nullable) ✅
- `tags` 컬럼 (jsonb, nullable) ✅
- `ix_asset_registry_screen_id` 인덱스 ✅

---

## API 통합 검증

### 1단계: API 서버 시작

```bash
# API 디렉토리
cd /home/spa/tobit-spa-ai/apps/api

# 의존성 확인
pip list | grep fastapi

# 서버 시작
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**서버 시작 로그**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 2단계: Screen Asset 생성 테스트

```bash
# Terminal 1: 서버 실행 중

# Terminal 2: API 테스트
curl -X POST http://localhost:8000/asset-registry/assets \
  -H "Content-Type: application/json" \
  -d '{
    "asset_type": "screen",
    "screen_id": "device_detail_v1",
    "name": "Device Detail",
    "description": "Device information screen",
    "schema_json": {
      "version": "1.0",
      "layout": {"type": "grid"},
      "components": [
        {
          "id": "title",
          "type": "text",
          "label": "Device Title",
          "bind": "state.device.name"
        }
      ],
      "state_schema": {
        "device": {
          "type": "object",
          "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"}
          }
        }
      }
    },
    "tags": {"category": "device", "access": "public"},
    "created_by": "test@example.com"
  }'
```

**예상 응답**:
```json
{
  "success": true,
  "data": {
    "asset": {
      "asset_id": "uuid-...",
      "asset_type": "screen",
      "screen_id": "device_detail_v1",
      "name": "Device Detail",
      "version": 1,
      "status": "draft",
      "schema_json": { ... },
      "tags": { ... },
      "created_at": "2026-01-17T...",
      "updated_at": "2026-01-17T..."
    }
  }
}
```

### 3단계: Screen Asset 조회 테스트

```bash
# 모든 screen assets 조회
curl http://localhost:8000/asset-registry/assets?asset_type=screen

# 특정 screen 조회
curl http://localhost:8000/asset-registry/assets?asset_type=screen&screen_id=device_detail_v1

# Asset ID로 직접 조회
curl http://localhost:8000/asset-registry/assets/{asset_id}
```

**예상 응답**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "asset_id": "...",
        "asset_type": "screen",
        "screen_id": "device_detail_v1",
        ...
      }
    ],
    "total": 1
  }
}
```

### 4단계: Screen Asset 발행 테스트

```bash
# Asset 발행
curl -X POST http://localhost:8000/asset-registry/assets/{asset_id}/publish \
  -H "Content-Type: application/json" \
  -d '{
    "published_by": "reviewer@example.com"
  }'
```

**예상 응답**:
```json
{
  "success": true,
  "data": {
    "asset": {
      "asset_id": "...",
      "status": "published",
      "version": 1,
      "published_at": "2026-01-17T...",
      "published_by": "reviewer@example.com",
      ...
    }
  }
}
```

### 5단계: Binding Engine 테스트

```bash
# UI Action 호출 (binding 포함)
curl -X POST http://localhost:8000/ops/ui-actions \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "trace-parent-123",
    "action_id": "fetch_device_detail",
    "inputs": {
      "device_id": "GT-1"
    },
    "context": {
      "mode": "real",
      "user_id": "alice@example.com"
    }
  }'
```

**예상 응답**:
```json
{
  "success": true,
  "data": {
    "trace_id": "...",
    "status": "ok",
    "blocks": [
      {
        "type": "markdown",
        "content": "Device detail for GT-1..."
      }
    ]
  }
}
```

---

## 테스트 실행

### Python API 테스트

```bash
# API 테스트 디렉토리
cd /home/spa/tobit-spa-ai/apps/api

# pytest 설치 확인
pip list | grep pytest

# 테스트 실행
pytest tests/test_ui_contract.py -v

# 특정 테스트만 실행
pytest tests/test_ui_contract.py::TestUIScreenBlock -v
pytest tests/test_ui_contract.py::TestBindingEngine -v
pytest tests/test_ui_contract.py::TestScreenAsset -v
```

**테스트 카운트**:
- UIScreenBlock: 3 tests ✅
- ScreenAsset: 3 tests ✅
- BindingEngine: 10 tests ✅
- ActionRegistry: 2 tests ✅
- Integration: 2 tests ✅
- **총 20 tests**

**예상 결과**:
```
tests/test_ui_contract.py::TestUIScreenBlock::test_ui_screen_block_structure PASSED
tests/test_ui_contract.py::TestUIScreenBlock::test_ui_screen_block_in_answer_block_union PASSED
...
========================= 20 passed in 2.34s =========================
```

### Web E2E 테스트

```bash
# Web 디렉토리
cd /home/spa/tobit-spa-ai/apps/web

# Playwright 설치 확인
npx playwright --version

# 브라우저 설치 (초첫 실행 시)
npx playwright install

# E2E 테스트 실행
npm run test:e2e

# 또는 headful mode (브라우저 보이기)
npx playwright test e2e/ui-screen.spec.ts --headed

# 특정 테스트만 실행
npx playwright test e2e/ui-screen.spec.ts -g "should render ui_screen"
```

**테스트 그룹**:
- C0-1 Block ↔ Screen: 3 tests
- C0-2 Screen Asset: 5 tests
- C0-3 UI Action: 4 tests
- Integration: 2 tests
- Error Handling: 3 tests
- **총 17 tests**

**예상 결과**:
```
Running 17 tests using 1 worker
✓ [chromium] › ui-screen.spec.ts › C0-1: Block ↔ Screen boundary contract › should render ui_screen...
✓ [chromium] › ui-screen.spec.ts › C0-1: Block ↔ Screen boundary contract › should load published...
...
17 passed (45.2s)
```

---

## 배포 체크리스트

### Pre-Deployment

- [ ] 모든 코드 변경 commit 완료
- [ ] git status 확인 (clean)
- [ ] 환경 변수 설정 확인 (.env 파일)

### Database

- [ ] PostgreSQL 실행 중 확인
- [ ] DATABASE_URL 유효성 확인
- [ ] Alembic 마이그레이션 실행
- [ ] 마이그레이션 롤백 테스트 완료

### API

- [ ] 모든 Python 패키지 설치 (pip install -r requirements.txt)
- [ ] API 서버 시작 가능 확인
- [ ] Asset Registry 엔드포인트 응답 확인
- [ ] pytest 모든 테스트 pass

### Web

- [ ] 모든 npm 패키지 설치 (npm install)
- [ ] TypeScript 컴파일 오류 없음
- [ ] Playwright E2E 테스트 모두 pass
- [ ] 브라우저 개발자 도구 콘솔 에러 없음

### Integration

- [ ] API ↔ Web 통신 확인
- [ ] UIScreenBlock 렌더링 테스트
- [ ] Action 실행 흐름 테스트
- [ ] Trace 기록 검증

### Documentation

- [ ] CONTRACT_UI_CREATOR_V1.md 최신화
- [ ] PHASE_1_2_3_SUMMARY.md 최신화
- [ ] DEPLOYMENT_GUIDE_PHASE_4.md 완료
- [ ] README 업데이트

---

## 트러블슈팅

### 1. 마이그레이션 실패

**증상**: `alembic upgrade head` 실패

```bash
# 원인: 마이그레이션 파일 누락
ls -lah apps/api/alembic/versions/0029*.py

# 해결
alembic current  # 현재 버전 확인
alembic upgrade --sql head | tail -100  # 실행될 SQL 확인
```

### 2. API 서버 시작 실패

**증상**: `ModuleNotFoundError: No module named 'binding_engine'`

```bash
# 원인: 새 모듈 import 경로 오류
# 해결: Python path 확인
cd apps/api
PYTHONPATH=. python -c "from app.modules.ops.services.binding_engine import BindingEngine"
```

### 3. 테스트 실패

**증상**: `pytest tests/test_ui_contract.py` 실패

```bash
# 원인: 데이터베이스 연결 실패
# 해결: 환경 변수 확인
echo $DATABASE_URL
psql $DATABASE_URL -c "SELECT 1"

# 또는 테스트용 임시 DB 사용
export DATABASE_URL="sqlite:///test.db"
pytest tests/test_ui_contract.py
```

### 4. E2E 테스트 타임아웃

**증상**: `Playwright timeout`

```bash
# 원인: API 서버 미실행
# 해결: API 서버 시작 (터미널 1)
cd apps/api && uvicorn main:app --port 8000

# E2E 테스트 재실행 (터미널 2)
cd apps/web && npx playwright test e2e/ui-screen.spec.ts
```

### 5. Asset 조회 실패

**증상**: `GET /asset-registry/assets?screen_id=...` 빈 응답

```bash
# 원인: published asset이 아님
# 해결: asset 상태 확인
curl http://localhost:8000/asset-registry/assets | jq '.data.items[] | {screen_id, status}'

# draft asset 발행
curl -X POST http://localhost:8000/asset-registry/assets/{asset_id}/publish \
  -H "Content-Type: application/json" \
  -d '{"published_by": "admin"}'
```

---

## 성능 최적화 (선택사항)

### 인덱스 추가

```sql
-- screen_id 조회 성능 향상
CREATE INDEX idx_asset_screen_id ON tb_asset_registry(screen_id)
WHERE asset_type = 'screen';

-- status 필터 성능 향상
CREATE INDEX idx_asset_status ON tb_asset_registry(status)
WHERE asset_type = 'screen';
```

### 캐싱 설정

```python
# Redis 캐시 (선택사항)
# apps/api/.env
REDIS_URL=redis://localhost:6379/0

# Web 렌더러: Screen Asset 캐시
# apps/web/src/components/answer/UIScreenRenderer.tsx
// 같은 screen_id는 5분 동안 캐시
const SCREEN_CACHE_TTL_MS = 5 * 60 * 1000;
```

---

## 모니터링 & 로깅

### 로그 레벨 설정

```bash
# API
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Web
export NEXT_PUBLIC_LOG_LEVEL=info
```

### 주요 로그 포인트

```
[API]
- Asset Registry: "created screen asset {screen_id}"
- Binding Engine: "render_action_payload: {template_keys}"
- Action Execution: "execute_action_deterministic: {action_id}"

[Web]
- UIScreenRenderer: "Loading screen {screen_id}"
- Action Handler: "Executing action {handler}"
- State Update: "State updated: {key}"
```

### 메트릭 (선택사항)

```python
# Prometheus 메트릭 추가
from prometheus_client import Counter, Histogram

action_execution_count = Counter(
    'ui_action_executions_total',
    'Total UI action executions',
    ['action_id', 'status']
)

action_duration = Histogram(
    'ui_action_duration_seconds',
    'UI action execution duration',
    ['action_id']
)
```

---

## 배포 후 검증

### 1단계: 기본 기능 확인

```bash
# 1. Screen Asset 생성 ✅
# 2. Screen Asset 발행 ✅
# 3. UI Action 실행 ✅
# 4. Trace 기록 확인 ✅
```

### 2단계: 전체 워크플로우 테스트

```bash
# Device Detail 화면 워크플로우
# 1. LLM이 ui_screen block 생성
# 2. Web이 screen asset 로드
# 3. 사용자가 Refresh 버튼 클릭
# 4. Action 실행
# 5. State 업데이트
# 6. Trace 기록
```

### 3단계: 성능 테스트

```bash
# 부하 테스트 (선택사항)
ab -n 100 -c 10 http://localhost:8000/asset-registry/assets?asset_type=screen

# 메모리 사용량 모니터링
top -p $(pgrep -f uvicorn)
```

---

## 롤백 절차

### DB 마이그레이션 롤백

```bash
# 현재 버전 확인
alembic current

# 마이그레이션 롤백
alembic downgrade -1  # 한 버전 뒤로
alembic downgrade 0028_add_flow_spans_column  # 특정 버전으로

# 검증
alembic current
psql -d tobit_spa_db -c "\d tb_asset_registry"
```

### 코드 롤백

```bash
# git 롤백
git status
git reset --hard HEAD~1  # 최신 commit 취소
git reset --hard HEAD~5  # 5개 commit 취소

# 또는 특정 파일만 롤백
git checkout HEAD -- apps/api/schemas/answer_blocks.py
```

---

## 다음 단계

Phase 4 배포 후:

1. **모니터링 수립**
   - Log aggregation (ELK, Datadog 등)
   - APM (Application Performance Monitoring)
   - Error tracking (Sentry 등)

2. **문서화**
   - API 문서 (Swagger/OpenAPI)
   - Screen Asset 작성 가이드
   - Action 작성 가이드

3. **확장**
   - Component 타입 확장
   - Binding 표현식 확장
   - 성능 최적화

---

## 도움말

### 자주하는 질문 (FAQ)

**Q1: Screen Asset과 Prompt Asset의 차이는?**
- Screen: UI 정의 (layout, components)
- Prompt: LLM 지시문 (template, output_contract)

**Q2: Binding expression에서 계산이 필요하면?**
- Backend executor에서 미리 계산
- 또는 Web에서 computed state 사용

**Q3: 기존 UI Panel과의 호환성은?**
- 완전 호환: UIPanelBlock은 그대로 유지
- UIScreenBlock은 새로운 선택사항

---

## 지원

문제 발생 시:

1. 로그 확인: `tail -f logs/api.log`
2. 테스트 실행: `pytest tests/test_ui_contract.py -v`
3. Issue 생성: https://github.com/anthropics/claude-code/issues
4. Slack: #engineering-phase-4

---

**준비 완료? 배포를 시작하세요! 🚀**

