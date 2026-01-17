# Tobit SPA AI - 프로덕션 준비 구현 로드맵

**작성 일시**: 2026-01-18
**상태**: 활성 로드맵
**마지막 업데이트**: 문서 확장 및 우선순위 재조정

---

## 1. 개요

이 문서는 SPA AI 시스템을 프로덕션 환경에 배포하기 위한 **구체적인 구현 순서**, **의존성 분석**, **팀 할당 전략**을 정의합니다.

사용자 제공 28-item 메모와 PRODUCTION_GAPS.md의 P0-P2 항목을 기반으로 작성했으며, 각 항목의 **기술적 복잡도**, **비즈니스 임팩트**, **예상 소요 기간**을 고려했습니다.

---

## 2. Phase별 구현 전략

### Phase 0: 기초 준비 (1주)
**목표**: 프로덕션 환경 기반 확립

#### 0-1. 보안 기반 구축
- **JWT 토큰 시스템 구현**
  - Access token (15분 만료), Refresh token (7일 만료)
  - 토큰 블랙리스트 관리 (Redis)
  - 구현 위치: `apps/api/core/security.py`
  - 테스트: `apps/api/tests/test_jwt_auth.py`

- **HTTPS 강제 설정**
  - FastAPI 미들웨어 (HTTPS 리다이렉트)
  - CORS 설정 정밀화
  - 구현 위치: `apps/api/main.py`

**의존성**: 없음
**예상 소요**: 5-6일

#### 0-2. 환경 설정 표준화
- `.env.example` 보안 관련 변수 추가
- 설정 우선순위 재검토 (env > settings > default)
- 구현 위치: `core/config.py`

**의존성**: 없음
**예상 소요**: 1일

**마일스톤**: 기본 보안 인프라 완성 ✓

---

### Phase 1: 인증 & 권한 관리 (2-3주)
**목표**: 사용자 접근 제어 및 멀티테넌트 격리

#### 1-1. 사용자 모델 및 DB 스키마
- `TbUser` 테이블: username, email, password_hash, role, tenant_id
- `TbRole` 테이블: admin, manager, developer, viewer
- `TbPermission` 테이블: resource_type, action (read/write/delete)
- 마이그레이션: `0031_add_user_auth_tables.py`

**의존성**: Phase 0-1
**예상 소요**: 3-4일

#### 1-2. RBAC (Role-Based Access Control)
- 라우터 데코레이터: `@require_role("admin", "manager")`
- 권한 검증 미들웨어: `RBACMiddleware`
- 테넌트 격리 로직: 모든 쿼리에 `tenant_id` 필터링
- 구현 위치: `apps/api/core/security.py`, 각 라우터

**의존성**: 1-1
**예상 소요**: 5-7일

#### 1-3. API Key 기반 인증 (선택)
- API Key 발급/회수 엔드포인트
- 만료 정책 (예: 90일)
- 구현 위치: `apps/api/app/modules/api_keys/`

**의존성**: 1-1
**예상 소요**: 2-3일

#### 1-4. OAuth2 / SSO 연동 (Optional - P1)
- Google, Microsoft, LDAP 통합
- 구현 위치: `apps/api/core/oauth.py`

**의존성**: 1-1
**예상 소요**: 2주 (별도)

**마일스톤**: 프로덕션 인증 시스템 완성 ✓

---

### Phase 2: OPS AI 오케스트레이터 강화 (3-4주)
**목표**: 복잡한 분석 워크플로우 자동 구성 및 실행

#### 2-1. LangGraph 통합
- 상태 머신 설계 (상태 정의, 노드, 엣지)
- Planner 통합: 질의를 그래프로 변환
- 구현 위치: `apps/api/app/modules/ops/services/orchestrator/graph.py`

**의존성**: 없음
**예상 소요**: 1주

#### 2-2. 재귀적 질의 해결
- 분해(Decompose) 전략
- 병렬/순차 실행 스케줄링
- 중간 결과 집계 로직
- 구현 위치: `apps/api/app/modules/ops/services/orchestrator/runner.py`

**의존성**: 2-1
**예상 소요**: 1주

#### 2-3. Tool 동적 조합
- Tool registry 개선
- 조건부 tool 실행 (IF/THEN/ELSE)
- 에러 복구 및 재시도 로직
- 구현 위치: `apps/api/app/modules/ops/services/executors/`

**의존성**: 2-2
**예상 소요**: 5-6일

#### 2-4. MCP (Model Context Protocol) 적용
- PostgreSQL adapter 구현
- Neo4j adapter 구현
- LLM에 직접 도구 제공
- 구현 위치: `apps/api/app/modules/ops/services/mcp/`

**의존성**: 2-3
**예상 소요**: 1주

**마일스톤**: 고급 질의 엔진 완성 ✓

---

### Phase 3: 문서 검색 고도화 (2-3주)
**목표**: 다중 형식 문서 지원 및 효율적 검색

#### 3-1. 문서 파서 구현
- PDF, Word, Excel, PPT 형식 지원
- 구현 위치: `apps/api/app/modules/document_search/parsers/`
- 테스트: `apps/api/tests/test_document_parsers.py`

**의존성**: 없음
**예상 소요**: 5-7일

#### 3-2. 청킹 & 벡터화 전략
- 청킹 엔진 (토큰 기반, 슬라이딩 윈도우)
- pgvector 저장소 활용
- Embedding API 통합 (OpenAI, Hugging Face)
- 구현 위치: `apps/api/app/modules/document_search/chunker.py`

**의존성**: 3-1
**예상 소요**: 5-6일

#### 3-3. 비동기 처리 & 진행 상황 표시
- Background task 관리 (RQ)
- 업로드 → 파싱 → 인덱싱 단계별 상태 추적
- SSE 또는 WebSocket 진행 상황 실시간 전송
- 구현 위치: `apps/api/app/modules/document_search/processing.py`

**의존성**: 3-2
**예상 소요**: 3-4일

#### 3-4. 검색 신뢰성 강화
- 벡터 유사도 + BM25 스코링
- 출처 정보 및 스니펫 제공
- 신뢰도 스코어 계산
- 구현 위치: `apps/api/app/modules/document_search/search.py`

**의존성**: 3-3
**예상 소요**: 3-4일

**마일스톤**: 엔터프라이즈급 문서 검색 완성 ✓

---

### Phase 4: 배포 & 운영 자동화 (2-3주)
**목표**: 원클릭 설치 및 자동 스케일링

#### 4-1. 설치 자동화 스크립트
- `tobitspaai_YYYYMMDD.sh` 생성
- 의존성 자동 설치 (Python, Node, PostgreSQL, Redis, Neo4j)
- 환경변수 설정 마법사
- 초기 데이터 로드
- 구현 위치: `scripts/install.sh`, `scripts/setup-env.sh`

**의존성**: Phase 0
**예상 소요**: 4-5일

#### 4-2. Docker & Docker Compose
- API, Web, PostgreSQL, Redis, Neo4j Dockerfile 작성
- `docker-compose.yml` (dev/prod 분리)
- 이중화 설정 (API 레플리카 x2)
- 구현 위치: `docker/`, `docker-compose.yml`, `docker-compose.prod.yml`

**의존성**: 4-1
**예상 소요**: 4-5일

#### 4-3. 모니터링 & 알림
- Prometheus 메트릭 수집 (API 응답 시간, 오류율, 토큰 사용량)
- Grafana 대시보드
- 임계치 기반 알림 (Slack, Email)
- 구현 위치: `monitoring/prometheus.yml`, `monitoring/grafana-dashboards/`

**의존성**: 4-2
**예상 소요**: 3-4일

#### 4-4. Kubernetes 준비 (Optional - P2)
- Helm 차트 작성
- 자동 스케일링 규칙 정의
- 구현 위치: `k8s/helm/`

**의존성**: 4-2
**예상 소요**: 2주 (별도)

**마일스톤**: 프로덕션 배포 준비 완료 ✓

---

### Phase 5: 테스트 & 품질 관리 (병렬 진행)
**목표**: 80% 이상 테스트 커버리지 달성

#### 5-1. 단위 테스트 작성
- Backend: pytest 기반 (목표 80%)
- 주요 대상: 비즈니스 로직, CRUD, 유틸리티
- 구현 위치: `apps/api/tests/`

**의존성**: 각 Phase의 기능 구현 완료 시
**예상 소요**: 병렬 진행 (각 feature당 2-3일)

#### 5-2. 통합 테스트
- API 엔드포인트 테스트 (FastAPI TestClient)
- DB 마이그레이션 검증
- 구현 위치: `apps/api/tests/integration/`

**의존성**: 5-1
**예상 소요**: 병렬 진행

#### 5-3. E2E 테스트 (Playwright)
- Frontend 사용자 흐름 검증
- 주요 시나리오: 로그인, 질의, 자산 발행, 보고서 생성
- 구현 위치: `apps/web/tests-e2e/`

**의존성**: 5-2
**예상 소요**: 병렬 진행

#### 5-4. CI/CD 파이프라인 구축
- GitHub Actions 워크플로우
- 자동 린트, 테스트, 빌드
- 구현 위치: `.github/workflows/`

**의존성**: 5-1, 5-2, 5-3
**예상 소요**: 2-3일

**마일스톤**: 완전 자동화된 테스트 스위트 ✓

---

## 3. 병렬 진행 가능 작업

다음 작업들은 **독립적으로** 진행 가능합니다:

### 그룹 A (보안 기반)
- Phase 0-1, 0-2 → Phase 1 (인증 & 권한)
- 팀: Backend Lead

### 그룹 B (AI 오케스트레이션)
- Phase 2 (LangGraph, MCP)
- 팀: AI/ML Engineer

### 그룹 C (문서 검색)
- Phase 3 (파서, 청킹, 벡터화)
- 팀: Data Engineer

### 그룹 D (배포 & 운영)
- Phase 4 (Docker, 스크립트, 모니터링)
- 팀: DevOps Engineer

### 그룹 E (테스트, 병렬)
- Phase 5 (모든 Phase와 병렬로 진행)
- 팀: QA Engineer

---

## 4. 타임라인 (권장)

```
Week 1:    Phase 0 (기초 준비)
           ↓
Week 2-3:  Phase 1 (인증) + Phase 2 병렬 시작 + Phase 5 시작
           ↓
Week 4-5:  Phase 2 (오케스트레이터) + Phase 3 병렬 시작
           ↓
Week 6-7:  Phase 3 (문서 검색) + Phase 4 병렬 시작
           ↓
Week 8-9:  Phase 4 (배포) + Phase 5 계속
           ↓
Week 10:   Phase 5 마무리 (테스트 커버리지 확인)
           ↓
Week 11:   UAT (User Acceptance Testing) & 버그 수정
           ↓
Week 12:   프로덕션 배포 준비

총 예상 기간: 12주 (3개월)
```

---

## 5. 우선순위 판단 기준

### P0 (즉시 필요)
- ✅ 완료: Request Tracing, Audit Logging, Asset Registry, Runtime Settings
- ⏳ 진행 중: JWT 인증, API ResponseEnvelope, UI Creator Phase 4
- 🔴 **필수**: 인증/권한, 보안, OPS AI 오케스트레이터, 문서 검색, API 검증

### P1 (단기, 1-3개월)
- 🟠 **중요**: 배포 자동화, 모니터링, 테스트 자동화, 성능 최적화
- 관리자 대시보드, 백업/복구, 실시간 데이터 연계

### P2 (중기, 3-6개월)
- 🟡 **선택**: 이상징후 검출, AI 질의 추천, 고급 분석 기능
- 템플릿/라이브러리, Kubernetes, MLOps

---

## 6. 의존성 맵

```
Phase 0 (기초)
├── Phase 1 (인증) [Phase 0 완료 필수]
│   └── Phase 2 (오케스트레이터) [독립]
├── Phase 3 (문서 검색) [독립]
├── Phase 4 (배포) [Phase 0, 1 권장]
└── Phase 5 (테스트) [모든 Phase와 병렬]
```

---

## 7. 성공 기준

### 각 Phase 완료 기준

| Phase | 성공 기준 |
|-------|---------|
| 0 | JWT 토큰 발급/갱신/검증 작동, HTTPS 강제 적용 |
| 1 | 모든 엔드포인트에 RBAC 적용, 테넌트 격리 검증 |
| 2 | LangGraph 상태 머신 실행, 재귀 질의 처리, MCP 도구 접근 |
| 3 | 5+ 형식 문서 파싱, pgvector 인덱싱, 검색 정확도 >85% |
| 4 | 설치 스크립트 자동화, Docker 이중화, 모니터링 대시보드 |
| 5 | 단위 테스트 80%, E2E 테스트 100%, CI/CD 자동화 |

### 프로덕션 배포 최종 기준

- ✅ 보안: JWT, RBAC, HTTPS, 데이터 암호화 완료
- ✅ 안정성: 99.5% 가용성, <100ms 응답 시간 (P95)
- ✅ 관찰성: 모든 요청 추적 가능, 구조화된 로그
- ✅ 성능: API 병렬 처리, 캐싱 전략 적용
- ✅ 테스트: 모든 주요 기능 E2E 테스트 통과

---

## 8. 리스크 및 완화 전략

### 리스크 1: JWT 토큰 갱신 로직 복잡성
**완화**: Redis를 활용한 토큰 블랙리스트, 명확한 검증 테스트

### 리스크 2: LangGraph 상태 머신 설계 오류
**완화**: 프로토타입 단계에서 충분한 검증, 상태 다이어그램 리뷰

### 리스크 3: 벡터 검색 정확도 부족
**완화**: 여러 embedding 모델 테스트, BM25와 벡터 유사도 조합

### 리스크 4: 배포 스크립트 플랫폼 호환성
**완화**: Windows/Linux/macOS 모두 테스트, Docker 우선 사용

### 리스크 5: 테스트 커버리지 달성 불가
**완화**: 초기 Phase부터 TDD (Test-Driven Development) 적용

---

## 9. 다음 단계

### 즉시 (이번 주)
- [ ] Phase 0-1: JWT 토큰 시스템 구현 시작
- [ ] HTTPS 강제 설정
- [ ] 사용자/역할 DB 스키마 설계

### 단기 (2-3주)
- [ ] Phase 1 완료: RBAC 미들웨어 적용
- [ ] Phase 2 시작: LangGraph 프로토타입
- [ ] Phase 5 시작: 단위 테스트 작성

### 중기 (1개월)
- [ ] Phase 2, 3 병렬 진행
- [ ] Phase 4 배포 스크립트 작성
- [ ] 모니터링 대시보드 구축

---

## 10. 참고 자료

- **PRODUCTION_GAPS.md**: 상세 기능별 TODO
- **AGENTS.md**: 기술 스택 및 개발 워크플로우
- **CONTRACT_UI_CREATOR_V1.md**: UI Screen 기능 명세
- **DEV_ENV.md**: 개발 환경 설정

---

**작성자**: Claude AI
**승인자**: [대기]
**마지막 검토**: 2026-01-18
