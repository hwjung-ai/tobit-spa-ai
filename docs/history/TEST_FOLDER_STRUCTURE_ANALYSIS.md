# 테스트 폴더 구조 분석 보고서

**분석 일시**: 2026-01-24
**분석 범위**: 프로젝트 전체 테스트 폴더 구조

---

## 1. 테스트 폴더 현황

### 1.1 발견된 테스트 폴더

| 경로 | 용도 | 파일 수 | 상태 |
|------|------|----------|------|
| `/tests` | Backend 통합/E2E 테스트 | 존재 | ✓ 활성 |
| `/test-results` | 테스트 결과 저장 | .last-run.json | ✓ 활성 |
| `/apps/api/tests` | Backend 유닛 테스트 | 29개 파일 | ✓ 활성 |
| `/apps/web/tests` | Frontend 테스트 (비어있음) | 0개 파일 | ⚠️ 비어있음 |
| `/apps/web/tests-e2e` | Frontend E2E 테스트 | 22개 파일 | ✓ 활성 |

### 1.2 폴더 구조 시각화

```
tobit-spa-ai/
├── tests/                              # 루트 테스트 폴더
│   ├── test_asset_importers.py
│   ├── ops_ci_api/                     # CI Orchestrator API 통합 테스트
│   └── ops_e2e/                       # OPS 기능 E2E 테스트
│
├── test-results/                       # 테스트 결과 폴더
│   └── .last-run.json
│
├── apps/api/
│   └── tests/                         # Backend 유닛 테스트
│       ├── test_api_keys.py
│       ├── test_asset_models.py
│       ├── test_audit_log.py
│       ├── test_chat_stream.py
│       ├── test_ci_ask_pipeline.py
│       ├── test_ci_exact_candidate.py
│       ├── test_ci_list_llm_output.py
│       ├── test_ci_management.py
│       ├── test_ci_runner_tool_contracts.py
│       ├── test_control_loop.py
│       ├── test_documents.py
│       ├── test_encryption.py
│       ├── test_health.py
│       ├── test_hello.py
│       ├── test_langgraph_advanced.py
│       ├── test_migration_final.py
│       ├── test_openai.py
│       ├── test_operation_settings.py
│       ├── test_ops_executor_tool_contracts.py
│       ├── test_ops_resolvers.py
│       ├── test_ops_service.py
│       ├── test_permissions.py
│       ├── test_plan_multistep.py
│       ├── test_screen_editor_auth.py
│       ├── test_security_headers.py
│       ├── test_stage_executor.py
│       ├── test_trace_id.py
│       ├── test_ui_actions_with_traces.py
│       ├── test_ui_contract.py
│       ├── integration/
│       └── unit/
│
└── apps/web/
    ├── tests/                         # Frontend 테스트 (비어있음)
    │   └── (빈 폴더)
    │
    └── tests-e2e/                     # Frontend E2E 테스트
        ├── explore-ui.spec.ts
        ├── inspector_e2e.spec.ts
        ├── integration_test.spec.ts
        ├── ops_e2e.spec.ts
        ├── rca_comprehensive_test.spec.ts
        ├── rca_real_trace_test.spec.ts
        ├── rca_simple_test.spec.ts
        ├── reproduce-exact-error.spec.ts
        ├── save-draft.spec.ts
        ├── screen-editor.spec.ts
        ├── simple-test.spec.ts
        ├── smoke.spec.ts
        ├── test-login-simple.ts
        ├── test-u3-simple.ts
        ├── test-utils.ts
        ├── u3_2_diff_compare.spec.ts
        ├── u3_2_publish_gate.spec.ts
        ├── u3_2_template_creation.spec.ts
        ├── u3_editor_publish_preview_v2.spec.ts
        ├── u3_editor_publish_preview.spec.ts
        ├── u3_editor_visual_json_roundtrip.spec.ts
        ├── u3_entry_layout_rendering.spec.ts
        ├── u3_entry_screen_lifecycle.spec.ts
        └── ui_screen_with_actions_e2e.spec.ts
```

---

## 2. 폴더별 용도 분석

### 2.1 루트 tests/

**위치**: `/tests`

**용도**: Backend 통합/E2E 테스트

**하위 폴더**:
- `ops_ci_api/`: CI Orchestrator API 통합 테스트
- `ops_e2e/`: OPS 기능 E2E 테스트

**파일**:
- `test_asset_importers.py`: Asset Importer 테스트

**특징**:
- 백엔드 API 전체 흐름을 테스트
- 실제 DB와 연동하여 통합 테스트 수행
- `apps/api/tests/`와 별도로 존재

### 2.2 루트 test-results/

**위치**: `/test-results`

**용도**: 테스트 결과 저장

**파일**:
- `.last-run.json`: 마지막 테스트 실행 결과 메타데이터

**특징**:
- 테스트 실행 시 자동으로 생성
- Playwright E2E 테스트의 기본 결과 폴더
- `.gitignore`에 포함되어야 함 (자동 생성 파일)

### 2.3 apps/api/tests/

**위치**: `/apps/api/tests`

**용도**: Backend 유닛 테스트

**파일 수**: 29개

**주요 테스트**:
- 보안: `test_security_headers.py`, `test_encryption.py`, `test_permissions.py`, `test_api_keys.py`
- CI Orchestrator: `test_ci_ask_pipeline.py`, `test_ci_management.py`, `test_plan_multistep.py`
- OPS: `test_ops_service.py`, `test_ops_resolvers.py`, `test_ops_executor_tool_contracts.py`
- UI Contract: `test_ui_contract.py`, `test_ui_actions_with_traces.py`
- Asset: `test_asset_models.py`, `test_screen_editor_auth.py`
- 기타: `test_health.py`, `test_hello.py`, `test_chat_stream.py`

**특징**:
- 개별 모듈 단위 테스트
- Mock 사용하여 빠른 테스트 실행
- `pytest`로 실행

### 2.4 apps/web/tests/

**위치**: `/apps/web/tests`

**용도**: Frontend 테스트 (현재 비어있음)

**파일 수**: 0개

**특징**:
- 현재 사용되지 않음
- Frontend E2E 테스트는 `tests-e2e/` 폴더 사용
- **권장사항**: 빈 폴더 삭제 또는 유닛 테스트 작성 시 사용

### 2.5 apps/web/tests-e2e/

**위치**: `/apps/web/tests-e2e`

**용도**: Frontend E2E 테스트

**파일 수**: 22개

**주요 테스트**:
- Inspector: `inspector_e2e.spec.ts`, `rca_comprehensive_test.spec.ts`, `rca_simple_test.spec.ts`
- Screen Editor: `screen-editor.spec.ts`, `u3_2_diff_compare.spec.ts`, `u3_2_publish_gate.spec.ts`
- UI Screen: `ui_screen_with_actions_e2e.spec.ts`, `u3_entry_layout_rendering.spec.ts`
- 일반: `smoke.spec.ts`, `simple-test.spec.ts`, `test-login-simple.ts`

**특징**:
- Playwright로 브라우저 자동화 테스트
- 실제 사용자 흐름 시뮬레이션
- `npm run test:e2e`로 실행

---

## 3. AGENTS.md 반영 상태

### 3.1 현재 AGENTS.md 기술

```markdown
- **Test Coverage**: 
    - Backend 유닛 테스트: `apps/api/tests/`
    - Backend 통합/E2E 테스트: `tests/ops_ci_api/`, `tests/ops_e2e/`
    - Frontend E2E 테스트: `apps/web/tests-e2e/`
```

### 3.2 검증 결과

| 항목 | AGENTS.md | 실제 | 상태 |
|------|----------|------|------|
| **Backend 유닛 테스트** | `apps/api/tests/` | `apps/api/tests/` | ✓ 일치 |
| **Backend 통합/E2E 테스트** | `tests/ops_ci_api/`, `tests/ops_e2e/` | `tests/ops_ci_api/`, `tests/ops_e2e/` | ✓ 일치 |
| **Frontend E2E 테스트** | `apps/web/tests-e2e/` | `apps/web/tests-e2e/` | ✓ 일치 |
| **Frontend 테스트** | 언급 안됨 | `apps/web/tests/` (비어있음) | ⚠️ 언급 안됨 |

**결론**: AGENTS.md는 정확히 반영됨 (빈 폴더인 `apps/web/tests/`는 언급하지 않음)

---

## 4. 권장 사항

### 4.1 폴더 구조 유지

**현재 구조 유지**:
- 루트 `tests/` - Backend 통합/E2E 테스트 (유지)
- 루트 `test-results/` - 테스트 결과 저장 (유지)
- `apps/api/tests/` - Backend 유닛 테스트 (유지)
- `apps/web/tests-e2e/` - Frontend E2E 테스트 (유지)

### 4.2 apps/web/tests/ 폴더 처리

**옵션 1: 빈 폴더 삭제**
- 현재 사용되지 않음
- `tests-e2e/`가 존재하므로 중복
- `rm -rf apps/web/tests/`

**옵션 2: 유닛 테스트 작성용으로 유지**
- Frontend 유닛 테스트 (Jest, React Testing Library) 작성 시 사용
- 현재는 비어있으므로 `.gitkeep` 파일 추가하여 폴더 유지
- `touch apps/web/tests/.gitkeep`

**권장사항**: 옵션 1 (빈 폴더 삭제)

### 4.3 AGENTS.md 추가 사항

현재 상태로 충분히 정확하며 추가 언급 불필요

---

## 5. 정리

### 5.1 활성 테스트 폴더 (4개)

1. `/tests` - Backend 통합/E2E 테스트
2. `/test-results` - 테스트 결과 저장
3. `/apps/api/tests` - Backend 유닛 테스트 (29개 파일)
4. `/apps/web/tests-e2e` - Frontend E2E 테스트 (22개 파일)

### 5.2 비활성 테스트 폴더 (1개)

1. `/apps/web/tests` - 비어있음 (삭제 권장)

### 5.3 결론

현재 테스트 폴더 구조는 다음과 같이 구성되는 것이 **올바른 것**으로 확인됨:

1. **Backend 유닛 테스트**: `apps/api/tests/`
2. **Backend 통합/E2E 테스트**: 루트 `tests/`
3. **Frontend E2E 테스트**: `apps/web/tests-e2e/`
4. **테스트 결과**: 루트 `test-results/`

AGENTS.md의 Test Coverage 기술은 **정확함** (빈 폴더인 `apps/web/tests/`는 언급하지 않음)

---

**분석 담당**: Claude AI
**검토자**: [대기]
**승인자**: [대기]
**마지막 수정**: 2026-01-24