# 테스트 결과 폴더 구조 명확화 보고서

**작성 일시**: 2026-01-24
**목적**: 테스트 결과가 저장되는 폴더 구조 명확화

---

## 1. 테스트 결과 폴더 분류

### 1.1 Playwright E2E 테스트 결과

**기본 동작** (Playwright 표준):
- `playwright-report/`: HTML 리포트 (UI로 테스트 결과 확인)
- `test-results/`: 테스트 실행 결과 (trace, screenshot, video 등)

**실제 설정** (`apps/web/playwright.config.ts`):
```typescript
testDir: './tests-e2e',  // 테스트 파일 위치
reporter: 'html',          // HTML 리포트 생성
```

**실제 저장 위치**:
- `apps/web/playwright-report/`: HTML 리포트
- `apps/web/test-results/`: 테스트 실행 결과

### 1.2 pytest Backend 테스트 결과

**기본 동작** (pytest 표준):
- `test-results/`: JUnit XML 형식의 테스트 결과
- `.pytest_cache/`: pytest 캐시

**실제 저장 위치**:
- 루트 `artifacts/junit.xml`: JUnit 형식 테스트 결과
- 루트 `test-results/.last-run.json`: 마지막 테스트 실행 메타데이터

### 1.3 CI/CD 파이프라인 결과

**용도**: CI/CD 파이프라인에서 테스트 결과 요약 및 보고

**실제 저장 위치**:
- 루트 `artifacts/ops_ci_api_summary.json`: CI Orchestrator API 테스트 요약
- 루트 `artifacts/ops_e2e_summary.json`: OPS E2E 테스트 요약
- 루트 `artifacts/e2e_raw/`: E2E 테스트 원본 데이터
- 루트 `artifacts/ops_ci_api_raw/`: CI Orchestrator API 테스트 원본 데이터

---

## 2. 테스트 결과 폴더 구조 (정확한 버전)

### 2.1 Playwright E2E 테스트 결과 (Frontend)

```
apps/web/
├── playwright-report/          # Playwright HTML 리포트 (UI)
│   └── index.html            # 테스트 결과 HTML
│
└── test-results/             # Playwright 테스트 실행 결과
    ├── [test-name]-*.trace.zip  # 실패한 테스트의 trace
    ├── [test-name]-*.png       # 스크린샷
    └── [test-name]-*.webm      # 비디오 (설정 시)
```

**생성 명령**:
```bash
cd apps/web
npm run test:e2e
```

**설정 파일**: `apps/web/playwright.config.ts`

### 2.2 pytest Backend 테스트 결과

```
artifacts/
├── junit.xml                # JUnit 형식 테스트 결과 (CI용)
│
test-results/
└── .last-run.json         # 마지막 테스트 실행 메타데이터

.pytest_cache/               # pytest 캐시 (자동 생성)
```

**생성 명령**:
```bash
cd apps/api
pytest tests/              # 또는 make api-test
```

### 2.3 CI/CD 파이프라인 결과

```
artifacts/
├── junit.xml                           # JUnit 형식 테스트 결과
├── ops_ci_api_summary.json            # CI Orchestrator API 테스트 요약
├── ops_e2e_summary.json              # OPS E2E 테스트 요약
│
├── e2e_raw/                          # E2E 테스트 원본 데이터
│   ├── [test-name].json
│   └── ...
│
└── ops_ci_api_raw/                    # CI Orchestrator API 테스트 원본 데이터
    ├── lookup_server_status.json
    ├── metric_cpu_usage.json
    └── ...
```

**용도**:
- CI/CD 파이프라인에서 테스트 결과를 보고하고 분석
- `junit.xml`: Jenkins, GitHub Actions 등 CI 시스템에서 테스트 결과 표시
- `*_summary.json`: 테스트 실행 결과 요약 (테스트 이름, 통과/실패, 응답 코드 등)
- `*_raw/`: 테스트 실행 시 생성된 원본 응답 데이터 (디버깅 및 분석용)

---

## 3. 정리

### 3.1 Playwright E2E 테스트 결과 (Frontend)
- **리포트**: `apps/web/playwright-report/` (HTML)
- **결과**: `apps/web/test-results/` (trace, screenshot, video)

### 3.2 pytest Backend 테스트 결과
- **결과**: `artifacts/junit.xml` (JUnit 형식)
- **메타데이터**: `test-results/.last-run.json`

### 3.3 CI/CD 파이프라인 결과
- **요약**: `artifacts/*_summary.json`
- **원본 데이터**: `artifacts/*_raw/`

### 3.4 중요한 점
1. **Playwright 기본 결과 폴더**: `apps/web/playwright-report/`, `apps/web/test-results/`
2. **pytest 결과**: `artifacts/junit.xml`, `test-results/.last-run.json`
3. **루트 `test-results/`**: Playwright가 아닌 pytest의 메타데이터 저장용
4. **루트 `artifacts/`**: CI/CD 파이프라인에서 생성하는 커스텀 결과

---

## 4. .gitignore 권장 사항

다음 폴더들은 자동 생성 파일이므로 `.gitignore`에 포함되어야 합니다:

```
# Playwright
apps/web/playwright-report/
apps/web/test-results/

# pytest
.pytest_cache/

# CI/CD
test-results/
artifacts/
```

---

## 5. 수정된 FINAL_AUDIT_SUMMARY.md

`docs/FINAL_AUDIT_SUMMARY.md`의 섹션 6.2 "test-results/ 폴더" 설명을 다음과 같이 수정해야 합니다:

### 6.2 수정 전 (오류)
```
**용도**:
- 테스트 실행 결과를 저장하는 폴더
- Playwright E2E 테스트의 기본 결과 폴더
- `.last-run.json`: 마지막 테스트 실행 결과 메타데이터
```

### 6.3 수정 후 (정확)
```
**용도**:
- pytest 백엔드 테스트의 메타데이터 저장 폴더
- `.last-run.json`: 마지막 테스트 실행 메타데이터
- **주의**: Playwright E2E 테스트 결과는 `apps/web/playwright-report/`와 `apps/web/test-results/`에 저장됨
```

---

**작성 담당**: Claude AI
**검토자**: [대기]
**승인자**: [대기]
**마지막 수정**: 2026-01-24