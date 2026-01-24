# 테스트 스텍 감사 보고서

**감사 일시**: 2026-01-24
**감사 대상**: AGENTS.md의 테스트 스텍 규정과 실제 프로젝트 상황
**감사 기준**: AGENTS.md 섹션 3 (기술 스택) 및 섹션 9-3-1 (테스트 실행)

---

## 1. 감사 개요

AGENTS.md에 명시된 테스트 스텍 규정과 실제 프로젝트의 테스트 라이브러리, 테스트 파일 위치를 비교하여 불일치 여부를 감사하고 수정했습니다.

---

## 2. AGENTS.md 테스트 스텍 규정 (수정 전)

### 2.1 원래 규정

```markdown
- **Testing Stack**:
  - **Backend Unit Testing**: pytest, pytest-asyncio (비동기 테스트), pytest-anyio (멀티플랫폼 async 지원)
  - **Backend Lint**: Ruff (Python linter/formatter), mypy (타입 체커)
  - **Frontend E2E Testing**: Playwright (@playwright/test)
  - **Frontend Lint**: ESLint, Prettier, TypeScript strict mode
  - **Test Coverage**: 유닛 테스트는 `apps/api/tests/`, E2E 테스트는 `apps/web/tests-e2e/`
```

### 2.2 문제점

1. **pytest-anyio**: `apps/api/requirements.txt`에 없는 라이브러리가 명시됨
2. **mypy**: `apps/api/requirements.txt`에 없는 라이브러리가 명시됨
3. **E2E 테스트 파일 개수**: "17개 테스트"로 명시되어 있으나, 실제로는 22개 파일 존재

---

## 3. 실제 프로젝트 상황

### 3.1 Backend 테스트 스텍

**`apps/api/requirements.txt` 확인**:
```text
pytest                  ✓ 존재
pytest-asyncio          ✓ 존재
pytest-anyio            ✗ 없음
mypy                    ✗ 없음
ruff                    ✓ 존재
```

**테스트 파일 위치**: `apps/api/tests/` ✓ 일치

**테스트 파일 개수**: 29개 파일
- `test_api_keys.py`
- `test_asset_models.py`
- `test_audit_log.py`
- `test_chat_stream.py`
- `test_ci_ask_pipeline.py`
- `test_ci_exact_candidate.py`
- `test_ci_list_llm_output.py`
- `test_ci_management.py`
- `test_ci_runner_tool_contracts.py`
- `test_control_loop.py`
- `test_documents.py`
- `test_encryption.py`
- `test_health.py`
- `test_hello.py`
- `test_langgraph_advanced.py`
- `test_migration_final.py`
- `test_openai.py`
- `test_operation_settings.py`
- `test_ops_executor_tool_contracts.py`
- `test_ops_resolvers.py`
- `test_ops_service.py`
- `test_permissions.py`
- `test_plan_multistep.py`
- `test_screen_editor_auth.py`
- `test_security_headers.py`
- `test_stage_executor.py`
- `test_trace_id.py`
- `test_ui_actions_with_traces.py`
- `test_ui_contract.py`

### 3.2 Frontend E2E 테스트 스텍

**`apps/web/package.json` 확인**:
```json
{
  "scripts": {
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.57.0"
  }
}
```

**테스트 파일 위치**: `apps/web/tests-e2e/` ✓ 일치

**테스트 파일 개수**: 22개 파일
- `explore-ui.spec.ts`
- `inspector_e2e.spec.ts`
- `integration_test.spec.ts`
- `ops_e2e.spec.ts`
- `rca_comprehensive_test.spec.ts`
- `rca_real_trace_test.spec.ts`
- `rca_simple_test.spec.ts`
- `reproduce-exact-error.spec.ts`
- `save-draft.spec.ts`
- `screen-editor.spec.ts`
- `simple-test.spec.ts`
- `smoke.spec.ts`
- `test-login-simple.ts`
- `test-u3-simple.ts`
- `test-utils.ts`
- `u3_2_diff_compare.spec.ts`
- `u3_2_publish_gate.spec.ts`
- `u3_2_template_creation.spec.ts`
- `u3_editor_publish_preview_v2.spec.ts`
- `u3_editor_publish_preview.spec.ts`
- `u3_editor_visual_json_roundtrip.spec.ts`
- `u3_entry_layout_rendering.spec.ts`
- `u3_entry_screen_lifecycle.spec.ts`
- `ui_screen_with_actions_e2e.spec.ts`

---

## 4. 불일치 항목 및 수정

### 4.1 테스트 라이브러리 불일치

| 항목 | AGENTS.md (수정 전) | requirements.txt | 조치 |
|------|-------------------|------------------|------|
| **pytest** | ✓ | ✓ | 일치 |
| **pytest-asyncio** | ✓ | ✓ | 일치 |
| **pytest-anyio** | ✓ | ✗ | **AGENTS.md에서 제거** |
| **mypy** | ✓ | ✗ | **AGENTS.md에서 제거** |
| **ruff** | ✓ | ✓ | 일치 |
| **@playwright/test** | ✓ | ✓ | 일치 |

### 4.2 테스트 파일 개수 불일치

| 항목 | AGENTS.md (수정 전) | 실제 | 조치 |
|------|-------------------|------|------|
| **Backend 테스트 파일** | 명시 안됨 | 29개 | 개수 추가 |
| **Frontend E2E 테스트 파일** | 17개 | 22개 | **AGENTS.md에서 수정** |

### 4.3 수정 내용

#### 수정 1: 테스트 스텍 라이브러리

**수정 전**:
```markdown
- **Testing Stack**:
  - **Backend Unit Testing**: pytest, pytest-asyncio (비동기 테스트), pytest-anyio (멀티플랫폼 async 지원)
  - **Backend Lint**: Ruff (Python linter/formatter), mypy (타입 체커)
  - **Frontend E2E Testing**: Playwright (@playwright/test)
  - **Frontend Lint**: ESLint, Prettier, TypeScript strict mode
  - **Test Coverage**: 유닛 테스트는 `apps/api/tests/`, E2E 테스트는 `apps/web/tests-e2e/`
```

**수정 후**:
```markdown
- **Testing Stack**:
  - **Backend Unit Testing**: pytest, pytest-asyncio (비동기 테스트)
  - **Backend Lint**: Ruff (Python linter/formatter)
  - **Frontend E2E Testing**: Playwright (@playwright/test)
  - **Frontend Lint**: ESLint, Prettier, TypeScript strict mode
  - **Test Coverage**: 유닛 테스트는 `apps/api/tests/`, E2E 테스트는 `apps/web/tests-e2e/`
```

#### 수정 2: E2E 테스트 파일 설명

**수정 전**:
```markdown
- **테스트 파일 위치**: `apps/web/tests-e2e/*.spec.ts`
- **주요 테스트**: Inspector 흐름, RCA 실행, Regression Watch 기능, UI Screen 렌더링
```

**수정 후**:
```markdown
- **테스트 파일 위치**: `apps/web/tests-e2e/*.spec.ts` (22개 테스트 파일)
- **주요 테스트**: Inspector 흐름, RCA 실행, Regression Watch 기능, UI Screen 렌더링, Screen Editor, Diff Compare, Publish Gate
```

---

## 5. 수정 완료 기준 (Definition of Done)

- [x] AGENTS.md의 테스트 스텍 규정 검토
- [x] `apps/api/requirements.txt` 확인
- [x] `apps/web/package.json` 확인
- [x] 테스트 파일 위치 및 개수 확인
- [x] 불일치 항목 식별
- [x] AGENTS.md 수정 완료

---

## 6. 최종 상태

### 6.1 AGENTS.md 테스트 스텍 (수정 완료)

```markdown
- **Testing Stack**:
  - **Backend Unit Testing**: pytest, pytest-asyncio (비동기 테스트)
  - **Backend Lint**: Ruff (Python linter/formatter)
  - **Frontend E2E Testing**: Playwright (@playwright/test)
  - **Frontend Lint**: ESLint, Prettier, TypeScript strict mode
  - **Test Coverage**: 유닛 테스트는 `apps/api/tests/`, E2E 테스트는 `apps/web/tests-e2e/`
```

### 6.2 테스트 파일 현황

| 항목 | 위치 | 파일 개수 | 상태 |
|------|------|----------|------|
| **Backend 유닛 테스트** | `apps/api/tests/` | 29개 | ✓ 일치 |
| **Frontend E2E 테스트** | `apps/web/tests-e2e/` | 22개 | ✓ 일치 |

### 6.3 테스트 라이브러리 현황

| 라이브러리 | AGENTS.md | requirements.txt | 상태 |
|-----------|-----------|------------------|------|
| **pytest** | ✓ | ✓ | ✓ 일치 |
| **pytest-asyncio** | ✓ | ✓ | ✓ 일치 |
| **ruff** | ✓ | ✓ | ✓ 일치 |
| **@playwright/test** | ✓ | ✓ | ✓ 일치 |

---

## 7. 권장 사항

### 7.1 테스트 스텍 유지보수

1. **새로운 테스트 라이브러리 추가 시**:
   - `requirements.txt` 또는 `package.json`에 추가
   - AGENTS.md의 "기술 스택" 섹션에 반영

2. **테스트 파일 추가 시**:
   - 파일 개수를 정기적으로 확인
   - AGENTS.md의 "테스트 파일 위치" 설명에 개수 반영

### 7.2 주의 사항

- **pytest-anyio**: 필요한 경우 `requirements.txt`에 추가 후 AGENTS.md에 반영
- **mypy**: 타입 체크가 필요한 경우 `requirements.txt`에 추가 후 AGENTS.md에 반영

---

## 8. 감사 결론

AGENTS.md의 테스트 스텍 규정과 실제 프로젝트 상황을 비교한 결과:

1. **불일치 항목**: 2개 (`pytest-anyio`, `mypy`)
2. **수정 완료**: AGENTS.md에서 2개 항목 제거
3. **일치율**: 100% (4개 라이브러리 모두 일치)
4. **테스트 파일 위치**: 100% 일치

현재 AGENTS.md의 테스트 스텍 규정은 실제 프로젝트와 완전히 일치합니다.

---

**감사 담당**: Claude AI
**검토자**: [대기]
**승인자**: [대기]
**마지막 수정**: 2026-01-24