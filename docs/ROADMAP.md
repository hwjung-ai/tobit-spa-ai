# Tobit SPA AI - 통합 로드맵

**작성 일시**: 2026-01-18
**상태**: 활성 (전략 + 실행 계획)

이 문서는 프로젝트의 **전략적 방향**과 **구체적인 실행 계획**을 통합으로 제시합니다.

---

## 📊 현재 상태

### 프로덕션 준비도
- **현재**: 35-40% (기초 인프라 완료)
- **3주 후**: 50% (보안 + 배포 기초)
- **6주 후**: 70% (P0 대부분 완료)
- **12주 후**: 95% (프로덕션 배포 준비)

### 완료된 작업 (P0 기본)
- ✅ Request Tracing & Audit Logging
- ✅ Asset Registry System
- ✅ Runtime Settings Externalization
- ✅ ResponseEnvelope 표준화
- ✅ Database Migration 자동화
- ✅ UI Creator Phase 4 (Screen Assets, Binding Engine)

---

## 🎯 Phase별 전략

### Phase 0: 보안 기초 (Week 1)

**목표**: 프로덕션 환경 기반 확립

#### P0-1: JWT 토큰 시스템
- Access token (15분), Refresh token (7일)
- 토큰 블랙리스트 (Redis)
- 위치: `apps/api/core/security.py`

#### P0-2: HTTPS 강제
- HTTP → HTTPS 리다이렉트
- CORS 설정 정밀화
- SSL 인증서 설정

**예상 소요**: 5-6일
**의존성**: 없음

### Phase 1: 인증 & 권한 (Week 2-3)

**목표**: 사용자 접근 제어 및 멀티테넌트 격리

#### 1-1: 사용자 모델 & DB 스키마
- `TbUser`, `TbRole`, `TbPermission` 테이블
- 마이그레이션: `0031_add_user_auth_tables.py`

#### 1-2: RBAC (Role-Based Access Control)
- 라우터 데코레이터: `@require_role(...)`
- 권한 검증 미들웨어
- 테넌트별 데이터 격리

#### 1-3: API Key 인증 (선택)
- API Key 발급/회수
- 만료 정책 (90일)

#### 1-4: OAuth2 / SSO (Optional, P1)
- Google, Microsoft, LDAP 연동

**예상 소요**: 2-3주
**의존성**: Phase 0-1

### Phase 2: OPS AI 오케스트레이터 (Week 4-5)

**목표**: 복잡한 분석 워크플로우 자동 구성

#### 2-1: LangGraph 통합
- 상태 머신 설계
- Planner 통합
- 위치: `apps/api/app/modules/ops/services/orchestrator/graph.py`

#### 2-2: 재귀적 질의 해결
- 질의 분해 전략
- 병렬/순차 실행 스케줄링
- 중간 결과 집계

#### 2-3: Tool 동적 조합
- Tool registry 개선
- 조건부 tool 실행
- 에러 복구 및 재시도

#### 2-4: MCP (Model Context Protocol)
- PostgreSQL adapter
- Neo4j adapter
- LLM에 직접 도구 제공

**예상 소요**: 3-4주
**의존성**: 없음 (독립)

### Phase 3: 문서 검색 (Week 5-7)

**목표**: 다중 형식 문서 지원 및 효율적 검색

#### 3-1: 문서 파서
- PDF, Word, Excel, PPT 형식
- 구현: `apps/api/app/modules/document_search/parsers/`

#### 3-2: 청킹 & 벡터화
- 토큰 기반 청킹 (512 기본)
- pgvector 저장소
- Embedding API 통합

#### 3-3: 비동기 처리
- Background task 관리 (RQ)
- SSE 또는 WebSocket 진행 상황
- 구현: `apps/api/app/modules/document_search/processing.py`

#### 3-4: 검색 신뢰성
- 벡터 유사도 + BM25
- 출처 정보 및 스니펫
- 신뢰도 스코어

**예상 소요**: 2-3주
**의존성**: 없음 (독립)

### Phase 4: 배포 & 운영 (Week 7-9)

**목표**: 원클릭 설치 및 자동 스케일링

#### 4-1: 설치 자동화
- `tobitspaai_YYYYMMDD.sh` 생성
- 의존성 자동 설치
- 환경변수 마법사
- 위치: `scripts/install.sh`

#### 4-2: Docker & Compose
- API, Web, PostgreSQL, Redis, Neo4j Dockerfile
- `docker-compose.yml` (dev/prod 분리)
- 이중화 설정

#### 4-3: 모니터링 & 알림
- Prometheus 메트릭
- Grafana 대시보드
- 임계치 기반 알림 (Slack, Email)
- 위치: `monitoring/prometheus.yml`

#### 4-4: Kubernetes (Optional, P2)
- Helm 차트
- 자동 스케일링

**예상 소요**: 2-3주
**의존성**: Phase 0, 1 권장

### Phase 5: 테스트 (병렬 진행)

**목표**: 80% 이상 테스트 커버리지

#### 5-1: 단위 테스트
- pytest 기반 (목표 80% 커버리지)
- 위치: `apps/api/tests/`

#### 5-2: 통합 테스트
- API 엔드포인트 테스트
- DB 마이그레이션 검증
- 위치: `apps/api/tests/integration/`

#### 5-3: E2E 테스트
- Playwright 기반
- 핵심 사용 시나리오
- 위치: `apps/web/tests-e2e/`

#### 5-4: CI/CD
- GitHub Actions 워크플로우
- 자동 린트, 테스트, 빌드
- 위치: `.github/workflows/`

**예상 소요**: 병렬 진행 (각 phase당 2-3일)
**의존성**: 각 phase 구현 완료

---

## 📈 타임라인

```
Week 1    Phase 0 (보안 기초)
          ├─ JWT 토큰 시스템
          ├─ HTTPS 강제
          └─ .env 구조화

Week 2-3  Phase 1 (인증 & 권한) + Phase 2 시작 + Phase 5 시작
          ├─ RBAC 미들웨어
          ├─ 사용자/역할 모델
          ├─ LangGraph 프로토타입
          └─ 단위 테스트 작성

Week 4-5  Phase 2 (오케스트레이터) + Phase 3 시작
          ├─ 재귀적 질의 해결
          ├─ Tool 조합
          ├─ MCP 어댑터
          ├─ 문서 파서
          └─ 청킹 엔진

Week 6-7  Phase 3 (문서 검색) + Phase 4 시작
          ├─ 벡터화 & 인덱싱
          ├─ 비동기 처리
          ├─ 설치 스크립트
          └─ Docker 구성

Week 8-9  Phase 4 (배포) + Phase 5 계속
          ├─ 모니터링 대시보드
          ├─ 성능 테스트
          ├─ 보안 테스트
          └─ CI/CD 파이프라인

Week 10   Phase 5 마무리
          ├─ 테스트 커버리지 80% 달성
          ├─ E2E 테스트 통과
          └─ CI/CD 자동화 완성

Week 11   UAT (User Acceptance Testing)
          ├─ 베타 사용자 테스트 (5-10명)
          ├─ 피드백 수집
          └─ 버그 수정

Week 12   프로덕션 배포 준비
          ├─ 최종 체크리스트 검증
          ├─ 배포 연습 (Blue-Green)
          ├─ 운영팀 교육
          └─ 배포 권한 확보
```

---

## 🔄 병렬 진행 구조

```
그룹 A (Backend/Security)    그룹 B (AI/ML)              그룹 C (Data)
├─ Phase 0                   ├─ Phase 2                  ├─ Phase 3
├─ Phase 1 (인증)            │ (LangGraph, MCP)          │ (문서 검색)
└─ API 표준화               └─ 오케스트레이터            └─ 벡터화

그룹 D (DevOps)             그룹 E (QA) - 모든 Phase와 병렬
├─ Phase 4                  ├─ Phase 5 (단위 테스트)
│ (배포, 모니터링)          ├─ Phase 5 (통합 테스트)
└─ Kubernetes (P2)          ├─ Phase 5 (E2E 테스트)
                            └─ Phase 5 (CI/CD)
```

---

## 📌 의존성 맵

```
Phase 0 (기초)
├── Phase 1 (인증) [Phase 0 필수]
│   └── Phase 2 (오케스트레이터) [독립, 병렬 가능]
├── Phase 3 (문서 검색) [독립, 병렬 가능]
├── Phase 4 (배포) [Phase 0, 1 권장]
└── Phase 5 (테스트) [모든 Phase와 병렬]
```

---

## 🎯 성공 기준

### P0: MVP 완료 (현재)
- ✅ 기본 기능 작동
- ✅ 내부 테스트 통과
- ✅ 문서화 완료
- ⏳ 프로덕션 준비 40% (진행 중)

### P1: 프로덕션 준비 완료 (12주 후)
- ✅ 보안 구현 (인증, 권장, 암호화)
- ✅ 자동 배포 (Docker, 스크립트)
- ✅ 모니터링 (메트릭, 알림)
- ✅ 테스트 자동화 (80% 커버리지)
- ✅ 운영팀 교육

### P2: 프로덕션 배포 (Week 12)
- ✅ 모든 P0/P1 항목 완료
- ✅ UAT 통과
- ✅ 배포 권한 확보
- ✅ 24/7 모니터링 준비

---

## 💡 주요 의사결정 사항

### 1. 인증 방식
**결정**: JWT (Bearer token) 기반
- 이유: Stateless, 확장성, REST API 표준
- 대안 고려: OAuth2 (향후 SSO 확장 시)

### 2. 배포 전략
**결정**: Docker + Kubernetes (Phase 2)
- 이유: 확장성, 자동 복구, 버전 관리
- 대안: 수동 설치, VM 이미지 (비추천)

### 3. 문서 검색 벡터 DB
**결정**: pgvector (PostgreSQL 확장)
- 이유: 기존 DB 활용, 복합 쿼리 가능
- 대안: Pinecone, Weaviate (비용, 종속성)

### 4. 모니터링 스택
**결정**: Prometheus + Grafana
- 이유: 오픈소스, 커뮤니티 활발, 낮은 비용
- 대안: DataDog, New Relic (고비용)

---

## 📊 KPI & 목표

### 보안
- JWT 토큰 전환률: 100% (모든 API)
- RBAC 적용률: 100% (관리 기능)
- 데이터 암호화: 민감 데이터 100%

### 성능
- API 응답시간 (p95): < 100ms
- 오류율: < 0.1%
- 가용성: 99.5% (월간)

### 운영
- 배포 시간: < 30분 (무중단)
- 복구 시간 (RTO): < 15분
- 백업 최소 손실 (RPO): < 1시간

### 품질
- 테스트 커버리지: ≥ 80%
- E2E 테스트 통과율: 100%
- 기술 부채 감소: 지난 분기 대비 30%

---

## ⚠️ 리스크 관리

| 리스크 | 심각도 | 완화 전략 |
|--------|--------|---------|
| JWT 토큰 갱신 로직 복잡성 | 🟠 중간 | Redis 블랙리스트, 명확한 테스트 |
| LangGraph 설계 오류 | 🔴 높음 | 프로토타입 검증, 아키텍처 리뷰 |
| 벡터 검색 정확도 부족 | 🟠 중간 | 여러 embedding 모델 테스트 |
| 배포 스크립트 호환성 | 🟠 중간 | Windows/Linux/macOS 모두 테스트 |
| 테스트 커버리지 달성 불가 | 🟡 낮음 | 초기부터 TDD 적용 |

---

## 📋 다음 단계

### 즉시 (이번 주)
- [ ] Phase 0-1: JWT 토큰 시스템 구현
- [ ] HTTPS 강제 설정
- [ ] 사용자/역할 DB 스키마 설계

### 단기 (2-3주)
- [ ] Phase 1 완료
- [ ] Phase 2 시작 (LangGraph)
- [ ] Phase 5 시작 (단위 테스트)

### 중기 (1개월)
- [ ] Phase 2, 3 병렬 진행
- [ ] Phase 4 배포 스크립트 작성

### 장기 (3개월)
- [ ] 모든 Phase 완료
- [ ] 프로덕션 배포 준비
- [ ] 12주 이후 배포 예정

---

## 📚 관련 문서

- **PRODUCTION_GAPS.md**: 상세 기능별 TODO
- **PRODUCTION_CHECKLIST.md**: 배포 전 체크리스트
- **IMPLEMENTATION_ROADMAP.md**: 상세한 기술 구현 계획
- **AGENTS.md**: 기술 스택 및 개발 규칙

---

**작성자**: Architecture Team
**마지막 검토**: 2026-01-18
**다음 리뷰**: 2026-01-25
