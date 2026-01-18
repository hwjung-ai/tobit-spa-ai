# Tobit SPA AI - 프로덕션 로드맵 (MVP → Production)

## 1. 문서 개요

이 문서는 현재 MVP(Minimum Viable Product) 상태인 Tobit SPA AI를 안정적인 프로덕션(운영) 환경에 적용하기 위해 **반드시 보완되어야 할 기능 및 기술 부채 TODO 리스트**입니다.

> **AGENTS.md 참조**: 프로젝트 운영과 테스트는 `AGENTS.md`의 지침을 따라야 합니다. `AGENTS.md`에서는 `pytest apps/api/tests/` 및 `npm run test:e2e`(또는 `make web-test-e2e`)로 백엔드/프론트 테스트를 실행하고, `.venv` 환경을 활성화한 상태에서 모든 명령을 수행하라고 명시되어 있으니 테스트 관련 내용을 확인할 때마다 해당 문서를 먼저 열어주세요.

> **참고**: 이 문서는 운영 안정성 관점의 필수 보완 사항을 추적하기 위한 것이며, 일반적인 기능 요구사항과는 별도로 관리됩니다. 작업 진행 시 이 문서의 항목을 체크하고 내용을 업데이트하세요.

---

## 2. 완료된 P0 항목 (✅ Completed)

### P0-1: Request Tracing & Audit Logging System ✅
- **설명**: 요청별 trace_id/parent_trace_id를 통한 분산 추적 및 모든 중요 변경사항의 감사 로그 기록
- **구현 상태**: 완료
- **주요 기능**:
  - 미들웨어에서 trace_id 자동 생성 및 전파
  - 로깅에 trace_id/parent_trace_id 포함
  - TbAuditLog 테이블: 리소스별 변경 이력 추적
  - 자산 레지스트리(publish/rollback) 감사 로그 통합
- **소스**:
  - 미들웨어: `apps/api/core/middleware.py`
  - 로깅: `apps/api/core/logging.py`
  - 감사 모델: `apps/api/app/modules/audit_log/models.py`
  - 감사 CRUD: `apps/api/app/modules/audit_log/crud.py`
  - 마이그레이션: `apps/api/alembic/versions/0023_add_audit_log.py`

### P0-2: Asset Registry System ✅
- **설명**: 자산(Asset) 버전 관리, 발행/롤백 기능을 통한 자산 수명주기 관리
- **구현 상태**: 완료
- **주요 기능**:
  - Asset 정의 및 버전 관리
  - Publish/Rollback을 통한 버전 제어
  - 자산 변경 이력 추적
  - P0-1 감사 로그 통합
- **소스**:
  - 모델/CRUD: `apps/api/app/modules/asset_registry/`
  - 마이그레이션: `apps/api/alembic/versions/0022_add_asset_registry.py`

### P0-3: Runtime Settings Externalization ✅
- **설명**: OPS_MODE, ops_enable_langgraph 등 런타임 플래그를 설정 관리 시스템으로 외부화
- **구현 상태**: 완료
- **주요 기능**:
  - 설정 우선순위: published > env > default
  - GET /settings/operations: 모든 설정 조회
  - PUT /settings/operations/{key}: 설정 변경
  - 설정 변경 이력 감사 로그 기록
  - 변경 적용 시 restart_required 플래그 제공
- **설정 항목**:
  - ops_mode (mock/real)
  - ops_enable_langgraph (bool)
  - enable_system_apis (bool)
  - enable_data_explorer (bool)
  - cep_enable_metric_polling (bool)
  - cep_metric_poll_global_interval_seconds (int)
  - cep_metric_poll_concurrency (int)
  - cep_enable_notifications (bool)
  - ops_enable_cep_scheduler (bool)
- **소스**:
  - 모델: `apps/api/app/modules/operation_settings/models.py`
  - CRUD: `apps/api/app/modules/operation_settings/crud.py`
  - 서비스: `apps/api/app/modules/operation_settings/services.py`
  - 라우터: `apps/api/app/modules/operation_settings/router.py`
  - 마이그레이션: `apps/api/alembic/versions/0024_add_operation_settings.py`
  - 테스트: `apps/api/tests/test_operation_settings.py` (9/9 passing)

---

## 3. Common Features (공통 기능)

모든 모듈에 걸쳐 필요한 최우선 공통 과제입니다.

### 🔴 P0: 즉시 필요
1.  **인증 및 권한 관리**:
    - 사용자 인증 (JWT/OAuth2)
    - 역할 기반 접근 제어 (RBAC: Role-Based Access Control)
    - 리소스(API, UI, CI) 및 데이터별 접근 권한
    - 테넌트 격리 강화
2.  **보안 처리 상세**:
    - 로그인/로그아웃 (비밀번호 암호화) 및 SSO 연동 기반 마련
    - 요청/응답 암호화 및 HTTPS 강제
    - API Key 기반의 REST API 보안
    - URL 공유 기능 (인증 없는 접근, 권한 위임, 공유 이력)
3.  **감사 로그 (Audit Log)**:
    - 모든 중요 변경(C/U/D) 이력 및 사용자 활동 추적
    - 데이터 접근 로그 기록 및 보관 정책
4.  **로그 처리 표준화**:
    - 표준 로그 포맷 정의 (JSON 형식 권장)
    - 콘솔 및 파일 동시 출력, 로그 레벨 관리
    - 로그 로테이션 및 보관 정책
5.  **테스트 관리**:
    - 단위/통합/E2E 테스트 커버리지 관리
    - 기능 개발 시 테스트 케이스 동시 작성 문화
    - REST API 및 UI 렌더링 테스트 자동화

### 🟠 P1: 단기 필요
6.  **관리자 화면**:
    - 사용자/테넌트별 토큰 사용량 및 시스템 리소스 모니터링
    - 시스템 로그 조회 및 다운로드
    - 프롬프트/쿼리/Query Asset 관리 UI (draft/publish/rollback, SQL read-only bible view)
    - Query asset 변경/Publish/rollback은 Inspector trace와 Audit Log에 기록되어야 하며, docs/QUERY_ASSET_OPERATION_GUIDE.md를 참조하여 SQL 자산을 운영합니다.
7.  **백업 및 복구**:
    - 정기 자동 백업 및 검증
    - 데이터 복구 프로세스 수립
8.  **배포 및 설치**:
    - 원격 설치 및 자동 실행 스크립트 (`tobitspaai_YYYYMMDD.sh`)
    - Cython 빌드를 통한 소스 코드 보호
    - 이중화 구성을 위한 Docker 기반 패키징 검토
9.  **문서화**:
    - 최종 사용자 가이드, 운영 매뉴얼, 트러블슈팅 가이드

---

## 3. API Manager (API 매니저)

### 🔴 P0: 즉시 필요
1.  **버전 관리 및 변경 이력**: API 정의에 대한 버전 관리, 변경 이력(who, when, what), 변경 사유 기록 및 Diff 표시 기능이 필요합니다.
2.  **롤백 기능**: 이전 버전으로 API 정의를 되돌리는 기능이 필요합니다.
3.  **API 검증 및 테스트**: API 저장 전 SQL 문법, 스키마 유효성 등을 자동으로 검증하는 기능이 필요합니다.
4.  **권한 관리**: API별 실행 및 수정 권한, API 타입(system/custom)별 권한을 관리해야 합니다.

### 🟠 P1: 단기 필요
5.  **성능 모니터링**: API별 평균 실행 시간, 실패율, 슬로우 쿼리 등 성능 메트릭을 수집하고 시각화해야 합니다.
6.  **에러 처리 강화**: 사용자 친화적 에러 메시지, 재시도 정책, 실패 알림 기능이 필요합니다.
7.  **의존성 관리**: 워크플로우 내 API 간 의존성을 추적하고, API 변경/삭제 시 영향도를 분석해야 합니다.

### 🟡 P2: 중기 필요
8.  **캐싱**: API 응답 및 쿼리 결과 캐싱 전략을 도입하여 성능을 최적화합니다.
9.  **배치 및 스케줄링**: API를 배치 또는 스케줄 기반으로 자동 실행하는 기능이 필요합니다.

---

## 4. UI Creator (UI 크리에이터)

### 🔴 P0: 즉시 필요
1.  **UI 정의 버전 관리**: UI 스키마의 변경 이력을 추적하고, 이전 버전으로 롤백하는 기능이 필요합니다.
2.  **UI 검증 및 테스트**: 스키마 유효성, 데이터 소스 엔드포인트 연결성을 저장 전에 검증해야 합니다.
3.  **권한 관리**: UI별 접근, 수정, 공유 권한을 관리하고 테넌트별로 격리해야 합니다.

#### UI Creator U1 → U2 증거
- 위 P0 항목은 2026-01-18 기준 **U2 레벨 실현**을 목표로 한 작업이며, 상세 구현 내용과 증거는 `docs/history/U1_TO_U2_CERTIFICATION_REPORT.md`의 ‘state_patch 계약’, ‘CRUD 액션 실동작’, ‘Inspector trace’ 3개 PR 항목과 연계되어 있습니다.
- Demo trace/결과는 `docs/history/trace_evidence.json`에 정리되어 있으며, read-only(Trace ID `b3ddfb8a…`)와 CRUD create-action (parent_trace `a553…`, child_trace `f0b4…`) 두 건의 trace_id를 포함합니다.
- Playwright/E2E 시험 및 CI 레포트는 `docs/history/test_results.log`에서 확인 가능하며, 현재는 `pytest` 모듈이 없다는 메시지가 남아 있으므로(즉, 단순 실행 로그만 확보)를 참고합니다.
- 테스트 안정성을 위해 `tests/test_asset_importers.py`도 마련되어 있고, 자산 데이터를 받아오는 프로세스가 준비되어 있으나, 실 테스트는 `pytest`가 설치된 환경에서 재실행이 필요합니다.

### 🟠 P1: 단기 필요
4.  **에러 처리 및 폴백**: 데이터 소스 실패 또는 타임아웃 발생 시, UI가 깨지지 않고 사용자에게 명확한 메시지를 보여줘야 합니다.
5.  **성능 최적화**: 데이터 로딩 성능 모니터링, 캐싱, 지연 로딩(lazy loading) 등을 도입해야 합니다.
6.  **UI 템플릿 및 라이브러리**: 자주 사용하는 UI 패턴을 템플릿으로 제공하여 재사용성을 높여야 합니다.

### 🟡 P2: 중기 필요
7.  **고급 차트 및 대시보드**: 라인 차트 외에 다양한 차트(bar, pie 등)를 지원하고, 위젯을 드래그앤드롭으로 배치하는 등 대시보드 기능을 고도화합니다.

---

## 5. CEP Engine (CEP 엔진)

### 🔴 P0: 즉시 필요
1.  **Rule 버전 관리**: Rule의 변경 이력을 추적하고 이전 버전으로 롤백하는 기능이 필요합니다.
2.  **Rule 테스트 및 검증**: Rule 저장 전 유효성을 검사하고, 시뮬레이션 결과를 검증하는 체계가 필요합니다.
3.  **다양한 알림 채널**: 현재 Webhook만 지원하나, 이메일, SMS, Slack 등 다양한 채널 연동이 필요합니다.

### 🟠 P1: 단기 필요
4.  **Bytewax 통합 및 고도화**: Windows에 설치된 Bytewax 엔진과 연동하여 실시간 이벤트 처리, 대시보드 UI, 처리 액션 관리 기능을 구현합니다.
5.  **Rule 성능 모니터링**: Rule별 실행 통계, 트리거 빈도, 실패 원인을 분석하여 성능을 관리합니다.
6.  **Rule 스케줄링 고도화**: `interval` 외에 Cron 표현식을 지원하고, 시간대 설정을 지원해야 합니다.
7.  **Rule 디버깅 도구**: Rule 실행 과정을 실시간으로 추적하고 상세 로그를 확인할 수 있는 디버깅 모드가 필요합니다.

### 🟡 P2: 중기 필요
8.  **Rule 템플릿 및 라이브러리**: 자주 사용하는 규칙을 템플릿으로 제공하거나, 공유 가능한 라이브러리 형태로 관리합니다.

---

## 6. OPS AI (AIOps Assistant)

### 🔴 P0: 즉시 필요
1.  **오케스트레이터 고도화 (핵심)**:
    - 현재의 단일 질의-응답 구조를 넘어, 최종 답변을 위해 필요한 정보를 **재귀적으로 탐색하고 조합**하는 기능이 필요합니다.
    - LangGraph, LlamaIndex 등 외부 라이브러리 통합을 적극 검토하고 적용하여 복잡한 추론을 수행해야 합니다.
    - 조건부 분기, 병렬/순차 실행 최적화 등 고급 워크플로우를 지원해야 합니다.
2.  **CI 변경 관리**: CI 데이터의 변경 이력을 추적하고, 필요한 경우 변경 승인 워크플로우를 도입해야 합니다.
3.  **CI 데이터 정합성**: 중복 CI를 감지하고, 정기적으로 데이터 무결성을 검증하는 프로세스가 필요합니다.

### 🟠 P1: 단기 필요
4.  **질의 성능 최적화**: 복잡한 그래프 순회나 집계 질의에 대한 타임아웃을 관리하고, 결과를 캐싱하여 성능을 개선해야 합니다.
5.  **실시간 데이터 연계**: TIM+ 등 외부 시스템과 연계하여 실시간 이벤트 및 메트릭 데이터를 수집하고 분석에 활용해야 합니다.
6.  **CI 자동화 및 통합**: 외부 시스템과 CI 정보를 동기화하고, CI 라이프사이클(생성-사용-폐기)을 관리해야 합니다.

### 🟡 P2: 중기 필요
7.  **분석 기능 고도화**: 그래프 DB 기반의 최적 경로, 근본 원인 분석(RCA) 등 고급 분석 기능을 템플릿화하여 제공합니다.
8.  **이상징후 검출**: ML 기반 알고리즘 또는 동적 임계치를 활용하여 시스템의 이상 징후를 자동으로 검출합니다.
9.  **AI 질의 시스템 고도화**: 사용자의 이전 질의를 학습하여 질문을 추천하거나 자동 완성하는 기능이 필요합니다.

---

## 7. Document Search (문서 검색)

### 🔴 P0: 즉시 필요
1.  **문서 처리 고도화**:
    - PDF 외에 PPT, DOC, XLS 등 다양한 문서 형식을 지원해야 합니다.
    - 대용량 파일은 비동기 백그라운드 방식으로 처리하고, UI에서 처리 상태(업로드 → 파싱 → 완료)를 표시해야 합니다.
    - 검색 결과의 출처(페이지, 문단 등)를 명확히 표시하여 신뢰도를 높여야 합니다.
2.  **문서 관리 및 접근 제어**:
    - 문서 업로드/삭제 이력을 DB에 기록하고, 파일 시스템과 동기화해야 합니다.
    - 테넌트, 사용자별로 문서를 격리하고 접근 권한을 관리해야 합니다.

---

## 8. Chat & History (대화 및 이력)

### 🔴 P0: 즉시 필요
1.  **이력 관리 고도화**:
    - 각 대화 쓰레드에 대해 자동으로 요약 제목을 생성해야 합니다.
    - 각 질의응답마다 소요 시간 및 토큰 사용량을 표시해야 합니다.
    - 답변에 포함된 차트, 테이블 등의 결과물을 이력에 함께 저장해야 합니다.
2.  **이력 검색 및 관리**: 이력 목록을 검색하거나, 소프트 삭제(soft delete)하는 기능이 필요합니다.

---

## 9. Data Explorer (데이터 탐색기)

### 🔴 P0: 즉시 필요 (프로덕션 활성화 시)
1.  **프로덕션 활성화 여부 결정**: 현재 개발 전용인 이 기능을 프로덕션 환경에서 사용할지 정책 결정이 필요합니다.
2.  **권한 관리 및 감사**: 활성화 시, 데이터베이스 및 테이블별 접근 권한을 제어하고, 모든 쿼리 실행 기록을 감사 로그로 남겨야 합니다.

---

## 10. OPS AI - 고급 기능 (Enhancement Details)

### 🔴 P0: 즉시 필요 (확장 상세)

#### 1. 오케스트레이터/코디네이터 패턴 (핵심 재귀 구조)
- **구현 목표**: LangGraph, LangChain, LlamaIndex를 활용한 재귀적 질의 해결
- **핵심 기능**:
  - **질의 분해**: 복잡한 질문을 트리 구조로 분해하고 병렬/순차 실행
  - **분기 처리**: 조건부 분기(IF/THEN/ELSE), 루프, 재귀 호출 지원
  - **Tool 조합**: 여러 도구를 동적으로 조합하여 복잡한 분석 수행
  - **상태 관리**: 중간 결과, 컨텍스트, 에러를 안전하게 전파
- **구현 위치**:
  - Planner: `apps/api/app/modules/ops/services/ci/planner/`
  - Runner: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`
  - LangGraph 통합: 워크플로우 상태 머신 구현
- **우선순위**: P0 - 오케스트레이터가 없으면 복잡한 분석 불가능

#### 2. Model Context Protocol (MCP) 설정
- **목적**: PostgreSQL, Neo4j에 LLM의 직접 접근 권한 부여
- **구현 전략**:
  - **PostgreSQL Adapter**:
    - 쿼리 결과를 LLM이 읽을 수 있는 형식으로 변환
    - 테이블 스키마 정보 제공
    - 권한 검증 (read-only 쿼리만 허용)
  - **Neo4j Adapter**:
    - Cypher 쿼리 결과 직렬화
    - 그래프 탐색 기능 (BFS, 최단 경로 등)
  - **구현 위치**: `apps/api/app/modules/ops/services/mcp/`
- **보안 고려사항**:
  - 민감 데이터 마스킹 (password, API key, 개인정보)
  - 쿼리 허용목록 (allowlist) 기반 검증
  - 실행 권한별 차등 접근

#### 3. CI 변경 관리 및 정합성
- **변경 이력 추적**:
  - 모든 CI 데이터 변경(추가, 수정, 삭제)을 `TbChangeHistory` 테이블에 기록
  - 변경 사유, 변경자, 변경 전후 내용 저장
- **변경 승인 워크플로우** (선택):
  - 중요 CI 변경에 대해 승인 프로세스 적용
  - 변경 승인 대기/완료 상태 관리
- **데이터 정합성 검증**:
  - 정기적 (예: 일일) 중복 CI 감지 및 병합
  - 고아 데이터(참조되지 않는 CI) 정리 프로세스
  - 데이터 무결성 검증 리포트

### 🟠 P1: 단기 필요

#### 4. 질의 성능 최적화
- **Query 캐싱**: 동일한 질의에 대해 TTL 기반 캐시 적용 (Redis)
- **타임아웃 관리**: 복잡한 그래프 순회 및 집계 쿼리의 타임아웃 설정
- **결과 페이지네이션**: 대용량 결과에 대해 페이지 단위 반환

#### 5. 실시간 데이터 연계 (TIM+ Integration)
- **외부 시스템 동기화**: TIM+ 등 모니터링/메트릭 시스템과의 연계
- **실시간 이벤트 수집**: 메트릭, 알림, 로그 등을 비동기로 수집
- **캐시 무효화**: 새로운 데이터 도입 시 관련 캐시 초기화

#### 6. CI 자동화 및 생명주기 관리
- **자동 동기화**: 외부 시스템(CMDB, 모니터링 도구)과 CI 정보 자동 동기화
- **생명주기 관리**: 생성 → 활성 → 폐지 단계별 상태 추적

### 🟡 P2: 중기 필요

#### 7. 분석 기능 고도화
- **RCA 템플릿 시스템**: 근본 원인 분석을 위한 재사용 가능한 템플릿
- **그래프 최적 경로**: 의존성 그래프에서 성능 병목 경로 자동 추출
- **시각화**: 분석 결과를 차트/다이어그램으로 자동 생성

#### 8. 이상징후 검출 (Anomaly Detection)
- **ML 기반 알고리즘**: 시계열 데이터에서 이상 패턴 감지
- **동적 임계치**: 시간대, 요일 등에 따른 적응형 임계치 적용
- **알림 통합**: 감지된 이상 징후를 알림 시스템으로 연동

#### 9. AI 질의 시스템 고도화
- **질의 추천**: 사용자의 이전 질의 히스토리 분석하여 관련 질문 추천
- **자동 완성**: 입력 중인 질의에 대해 예상 완성 제안
- **학습 기반 재정렬**: 사용자 피드백을 통해 추천 순서 학습

---

## 11. Document Search - 상세 구현 전략

### 🔴 P0: 즉시 필요

#### 1. 다중 형식 문서 지원
- **지원 형식**:
  - PDF: PDFMiner, PyPDF 활용
  - Word (.docx): python-docx
  - Excel (.xlsx): openpyxl
  - PowerPoint (.pptx): python-pptx
  - 이미지 (OCR): Tesseract, EasyOCR
- **비동기 처리 전략**:
  - 대용량 파일은 background task로 처리
  - 업로드 → 파싱 중 → 인덱싱 중 → 완료 단계별 상태 업데이트
  - WebSocket 또는 SSE로 처리 진행 상황 실시간 전송
- **청킹 전략**:
  - 문단 기반 청킹 (default 512 토큰/청크)
  - 슬라이딩 윈도우 방식으로 문맥 연속성 유지
  - 헤더/제목 정보 보존
- **벡터화**:
  - Embedding 모델: OpenAI, Hugging Face 등
  - 각 청크별 벡터 저장 (pgvector)
  - 청크의 원본 문서 참조 정보 기록

#### 2. 검색 결과 신뢰성 강화
- **출처 명시**:
  - 결과의 출처 문서명, 페이지 번호, 단락 번호 표시
  - 원문 스니펫(snippet) 제공
- **신뢰도 스코어**:
  - 벡터 유사도 및 BM25 점수 조합
  - 문서 최신성, 접근 권한 반영
- **인용 기능**:
  - 검색 결과를 답변에 자동으로 인용 처리
  - 참고 문헌 자동 생성

#### 3. 문서 관리 및 접근 제어
- **문서 생명주기**:
  - 업로드 → 인덱싱 → 활성 → 보관/삭제
- **접근 권한**:
  - 테넌트, 사용자, 그룹별로 문서 격리
  - 문서별 공유 권한 관리 (공개/비공개/제한)
- **감사 로그**:
  - 문서 업로드/다운로드/삭제 이력
  - 검색 쿼리 및 결과 접근 로그

---

## 12. Chat & History - 상세 기능

### 🔴 P0: 즉시 필요

#### 1. 자동 제목 생성 및 이력 관리
- **제목 자동 생성**:
  - 첫 몇 개 메시지를 바탕으로 LLM이 제목 생성
  - 사용자가 수동으로 변경 가능
- **토큰 추적**:
  - 각 질문-응답마다 input/output 토큰 기록
  - 누적 토큰 사용량 표시
  - 토큰 예상 비용 계산
- **결과물 보존**:
  - 차트, 테이블, 스크린샷 등을 이력에 함께 저장
  - 결과물을 별도 형식(PNG, CSV 등)으로 다운로드 가능

#### 2. 이력 검색 및 관리
- **이력 검색**: 날짜, 키워드, 태그 기반 검색
- **소프트 삭제**: 삭제된 이력도 추후 복구 가능
- **이력 정리**: 오래된 이력 자동 보관 또는 삭제 정책

---

## 13. API Manager - 상세 구현

### 🔴 P0: 즉시 필요

#### 1. 버전 관리 및 변경 이력 (확장)
- **버전 관리**:
  - Semantic versioning (1.0.0, 1.0.1 등)
  - 각 버전에 대한 변경 로그
  - 호환성 정보 (breaking changes 명시)
- **변경 이력**:
  - 변경자, 변경 시간, 변경 내용 (Diff 표시)
  - 변경 사유 필드 (textarea)
  - 변경 승인 워크플로우 (선택)

#### 2. API 검증 강화
- **구문 검증**: SQL 문법 검증 (parser 활용)
- **스키마 검증**: 데이터베이스 스키마와의 맞춤 검증
- **성능 검증**: 쿼리 실행 계획 분석으로 문제 쿼리 사전 감지
- **테스트 케이스**: 샘플 데이터로 API 실행 결과 미리 확인

---

## 14. Admin Dashboard & System Architecture

### 🟠 P1: 단기 필요

#### Admin Dashboard 상세 구성
- **사용자/테넌트 모니터링**:
  - API 호출 통계 (일/월별 사용량)
  - 토큰 사용량 추적 (비용 계산)
  - 시스템 리소스 모니터링 (CPU, 메모리, DB 연결)
- **시스템 로그 관리**:
  - 구조화된 로그 조회 (JSON 형식)
  - 로그 레벨별 필터링
  - 로그 다운로드 및 장기 보관 정책
- **자산 관리**:
  - Query Asset, Prompt, Policy 관리 UI
  - Draft/Publish/Rollback 상태 관리
  - 변경 이력 및 감사 로그 연동

---

## 15. 보안 구현 로드맵

### 🔴 P0: 인증 및 권한 관리

#### 1. 인증 시스템
- **JWT 기반 인증**:
  - Access token (단기), Refresh token (장기) 분리
  - 토큰 갱신 로직
  - 토큰 블랙리스트 (로그아웃 처리)
- **OAuth2 / SSO 연동** (선택):
  - Google, Microsoft, LDAP 등과 연동
  - SSO 세션 관리
- **MFA (Multi-Factor Authentication)**:
  - TOTP (Time-based OTP) 지원
  - SMS 또는 이메일 기반 2FA

#### 2. 역할 기반 접근 제어 (RBAC)
- **역할 정의**:
  - Admin: 모든 권한
  - Manager: 자산 발행, 로그 조회, 사용자 관리
  - Developer: 자산 개발, API 테스트
  - Viewer: 읽기 전용
- **리소스 권한**:
  - API 실행/수정 권한
  - 문서 접근 권한
  - 자산 발행 권한

#### 3. 데이터 암호화
- **전송 중 암호화**: HTTPS 강제
- **저장 시 암호화**: 민감 데이터 (password, API key, 개인정보) 암호화
- **API Key 보안**: 사용자별 고유 API Key 발급, 만료 정책

#### 4. URL 공유 기능
- **임시 공개 링크**: TTL 기반 공유 링크 생성
- **권한 위임**: 공유 대상의 접근 권한 지정
- **공유 이력**: 공유 및 접근 로그 기록

---

## 16. 배포 및 설치 자동화

### 🟠 P1: 단기 필요

#### 1. 자동 설치 스크립트
- **배포 패키지 생성**:
  - `tobitspaai_YYYYMMDD.sh` 형식의 설치 스크립트
  - 의존성 자동 설치 (Python, Node.js, PostgreSQL 등)
  - 환경변수 자동 설정 마법사
- **Cython 컴파일**:
  - 소스 코드 보호를 위해 핵심 로직을 Cython으로 컴파일
  - `.pyc` 또는 `.pyd` 형식으로 배포

#### 2. Docker 기반 패키징
- **컨테이너 이미지**:
  - API 서버 (FastAPI)
  - Web 서버 (Next.js)
  - 의존 서비스 (PostgreSQL, Redis, Neo4j)
- **Docker Compose**:
  - 개발/프로덕션 설정 분리
  - 이중화 설정 (API 레플리카, 로드 밸런싱)
- **Kubernetes 준비** (선택):
  - Helm 차트 제공
  - 자동 스케일링 설정

---

## 17. 테스트 관리 프레임워크

### 🟠 P1: 단기 필요

#### 1. 테스트 계층화
- **단위 테스트 (Unit Test)**:
  - 비즈니스 로직, 유틸리티 함수 (pytest)
  - 목표: 80% 이상 커버리지
- **통합 테스트 (Integration Test)**:
  - API 엔드포인트, DB 상호작용
  - 목표: 모든 주요 기능 커버
- **E2E 테스트 (End-to-End)**:
  - UI 사용자 흐름 (Playwright)
  - 목표: 핵심 사용 시나리오 검증

#### 2. 테스트 자동화
- **CI/CD 통합**:
  - Git push 시 자동 테스트 실행
  - 테스트 실패 시 병합 차단
- **테스트 리포트**:
  - 커버리지 리포트
  - 성능 테스트 결과
  - 보안 스캔 결과

#### 3. 테스트 데이터 관리
- **Mockup 데이터**:
  - 프로덕션과 유사한 테스트 데이터셋
  - 데이터 마이그레이션 스크립트
  - 데이터 정기 리프레시 프로세스
- **Test Fixtures**:
  - 각 테스트에 필요한 초기 데이터 셋업
  - 테스트 후 정리 (teardown) 로직

---

## 18. 시스템 아키텍처 및 설계 원칙

### 🟠 P1: 단기 필요

#### 1. 마이크로서비스 기반 아키텍처
- **모듈별 독립성**:
  - 각 모듈 (OPS AI, UI Creator, CEP 등)은 자체 DB/캐시 보유 가능
  - REST API 또는 메시지 큐로 통신
  - 장애 격리 (한 모듈의 장애가 다른 모듈에 영향 최소화)

#### 2. 이벤트 주도 아키텍처
- **이벤트 스트림**:
  - 중요한 상태 변화 (자산 발행, 규칙 실행 등)를 이벤트로 발행
  - Redis Pub/Sub 또는 Kafka 활용
- **비동기 처리**:
  - 무거운 작업 (문서 인덱싱, 대용량 분석)은 큐에 저장하여 비동기 처리
  - RQ (Redis Queue) 활용

#### 3. 대시보드 및 모니터링
- **실시간 모니터링**:
  - 시스템 상태 (가용성, 성능)
  - 사용 통계 (API 호출, 토큰 사용량)
  - 알림 시스템 (임계치 초과 시 알림)
- **로깅 및 추적**:
  - 구조화된 로깅 (JSON 형식)
  - 분산 추적 (Distributed Tracing) - 요청 흐름 추적
  - 장기 로그 저장 및 분석

---

## 19. UI Creator Phase 4 완료 항목 (✅ Completed - 2026-01-18)

### 📊 UI Screen & Asset Registry 최종 통합
- **UI Screen Component** ✅
  - JSON 기반 UI 정의 및 동적 렌더링 (UIScreenRenderer)
  - 컴포넌트 지원: button, input, text, card, grid, chart 등
  - State management 및 reactive binding
  - Error Boundary를 통한 런타임 오류 처리

- **Screen Asset Model & Migration** ✅
  - TbAssetRegistry에 screen_id, schema_json, tags 칼럼 추가
  - 마이그레이션: `0029_add_screen_asset_fields.py` (0028 → 0030 체인)
  - 자산 생명주기: draft → published → rollback

- **Binding Engine** ✅
  - 템플릿 표현식: `{{inputs.x}}`, `{{state.x}}`, `{{context.x}}`
  - Array index 지원: `{{state.items[0].name}}`
  - 정규식 기반 검증

- **RCA Integration & Inspector** ✅
  - RCAPanel: Root Cause Analysis 가설 표시
  - Inspector 점프 링크 (seamless navigation)
  - RegressionWatchPanel 통합

- **Admin Dashboard** ✅
  - Asset Registry UI (목록, 필터, 생성)
  - Observability Dashboard (KPI, 차트)
  - Regression Watch Panel (결과 분석)

### 🔧 API Response Format Standardization (2026-01-18)
- **ResponseEnvelope 표준화** ✅
  - 모든 API 응답을 `{time, code, message, data}` 형식으로 통일
  - 예외: SSE 스트리밍은 제외
  - Asset Registry, Observability KPI 모두 준수

- **마이그레이션 자동화** ✅
  - Alembic 병렬 마이그레이션 해결 (merge 파일 제거)
  - 0029 down_revision 수정: 0022 → 0028
  - 수동 마이그레이션 완료: tags 칼럼, 인덱스 생성
  - startup 시 자동 마이그레이션 실행

- **프론트엔드-백엔드 통합** ✅
  - fetchApi 호환성: `response.data.assets` 구조 확립
  - ObservabilityDashboard 절대 URL 적용
  - CORS 설정 및 API 라우팅 정상화

---

## 20. 우선순위 요약 (업데이트 - 2026-01-18)

### P0: 즉시 시작 (부분 완료)

**완료된 항목** (✅):
- **공통**: 감사 로그 (Audit Log) ✅, Request Tracing ✅
- **운영 설정**: 런타임 플래그 외부화 ✅
- **UI Creator**: Phase 4 완료 (Screen Asset, Binding Engine, RCA Integration) ✅
- **API 표준**: ResponseEnvelope 표준화 ✅

**즉시 필요한 항목** (우선순위 순):

| 순위 | 항목 | 영향도 | 복잡도 | 예상 기간 |
|------|------|--------|--------|----------|
| 1 | **인증 & 권한 관리 (JWT, RBAC)** | 🔴 높음 | 🔴 높음 | 2-3주 |
| 2 | **OPS AI 오케스트레이터** (LangGraph 통합) | 🔴 높음 | 🔴 높음 | 3-4주 |
| 3 | **MCP 설정** (PostgreSQL, Neo4j) | 🔴 높음 | 🟠 중간 | 2주 |
| 4 | **문서 검색 고도화** (다중 형식, 청킹) | 🟠 중간 | 🟠 중간 | 2-3주 |
| 5 | **API 검증 강화** (SQL 문법, 성능 검증) | 🟠 중간 | 🟠 중간 | 1-2주 |
| 6 | **Chat History 강화** (토큰 추적, 제목) | 🟠 중간 | 🟡 낮음 | 1주 |
| 7 | **데이터 암호화** (저장 시, 전송 시) | 🔴 높음 | 🟠 중간 | 2주 |

**여전히 필요한 항목**:
- **공통**: 인증/권한 (JWT, RBAC, OAuth2) ✋, 보안 구현 로드맵 ✋, 데이터 암호화 ✋
- **OPS AI**: 오케스트레이터 고도화 (재귀/분기 처리) ✋, MCP 설정 ✋, CI 변경 관리
- **API/UI/CEP**: 버전 관리 및 롤백 기능 (Asset Registry는 기본 완료)
- **문서 검색/대화**: 다중 형식 지원 ✋, 청킹 전략 ✋, 이력 관리 강화 ✋

### P1: 단기 (1-3개월)

**주요 항목**:
- **공통**: 관리자 화면, 백업/복구, 배포 자동화 (설치 스크립트, Docker)
- **OPS AI**: 질의 성능 최적화, 실시간 데이터 연계 (TIM+), CI 자동화
- **CEP 엔진**: Bytewax 통합, 알림 채널 확장, 성능 모니터링
- **API/UI 매니저**: 성능 모니터링, 에러 처리 강화
- **시스템 아키텍처**: 마이크로서비스 설계, 이벤트 주도 아키텍처
- **테스트 관리**: 테스트 자동화 (CI/CD), 커버리지 관리

### P2: 중기 (3-6개월)

**고급 기능**:
- **전체**: 고급 분석 기능, 템플릿/라이브러리, 캐싱 등 성능 고도화
- **OPS AI**: 이상징후 검출 (Anomaly Detection), AI 질의 추천/자동 완성, RCA 템플릿
- **CEP 엔진**: Rule 디버깅 도구, 스케줄링 고도화 (Cron 표현식)
