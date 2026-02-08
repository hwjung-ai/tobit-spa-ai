# Tobit SPA AI - 문서 인덱스

**최종 정리**: 2026-02-08
**전체 완성도**: 94%
**활성 문서**: 15개 (docs/) + 3개 (root)
**아카이브**: docs/history/ (완료된 Phase 및 설계 문서)

---

## 빠른 시작

### 처음 오신 분
1. **프로젝트 개요**: 루트 `README.md`
2. **AI 에이전트 규칙**: 루트 `AGENTS.md` **필독**

### 아키텍처 이해
1. **시스템 전체 개요**: `SYSTEM_ARCHITECTURE_REPORT.md` (v1.8)
2. **OPS 쿼리 설계**: `BLUEPRINT_OPS_QUERY.md`
3. **CEP 엔진 설계**: `BLUEPRINT_CEP_ENGINE.md`
4. **API Engine 설계**: `BLUEPRINT_API_ENGINE.md`
5. **Screen Editor 설계**: `BLUEPRINT_SCREEN_EDITOR.md`
6. **개발 환경 설정**: 루트 `DEV_ENV.md`

### 기능 구현
1. **기능 명세서**: `FEATURES.md`
2. **테스트 표준**: `TESTIDS.md`, TESTING_STRUCTURE.md

### 사용자 가이드
1. **OPS 사용자 가이드**: `OPS_USER_GUIDE.md`
2. **CEP 사용자 가이드**: `CEP_USER_GUIDE.md`
3. **API 사용자 가이드**: `API_USER_GUIDE.md`
4. **Screen Editor 사용자 가이드**: `SCREEN_EDITOR_USER_GUIDE.md`

---

## 문서 체계

```
tobit-spa-ai/
│
├── Root (3개)
│   ├── README.md                    # 프로젝트 개요, 빠른 시작
│   ├── AGENTS.md                    # AI 에이전트 필독 규칙
│
├── docs/ (15개)
│   ├── INDEX.md                     # 문서 인덱스 (이 파일)
│   ├── DEV_ENV.md                   # 개발 환경 설정
│   │
│   ├── 아키텍처 & Blueprint (7개)
│   │   ├── SYSTEM_ARCHITECTURE_REPORT.md      # 시스템 전체 아키텍처 (v1.8)
│   │   ├── BLUEPRINT_PRODUCT_COMPLETENESS.md  # 제품 완성도 평가 (v1.6)
│   │   ├── BLUEPRINT_OPS_QUERY.md             # OPS 쿼리 시스템
│   │   ├── BLUEPRINT_CEP_ENGINE.md            # CEP 엔진
│   │   ├── BLUEPRINT_API_ENGINE.md            # API Engine
│   │   └── BLUEPRINT_SCREEN_EDITOR.md         # Screen Editor
│   │
│   ├── 사용자 가이드 (4개)
│   │   ├── OPS_USER_GUIDE.md                 # OPS 운영/학습 사용자 가이드
│   │   ├── CEP_USER_GUIDE.md                 # CEP 규칙/이벤트 운영 가이드
│   │   ├── API_USER_GUIDE.md                 # API Manager 사용자 가이드
│   │   └── SCREEN_EDITOR_USER_GUIDE.md       # Screen Editor 사용자 가이드
│   │
│   ├── 기능/운영 (2개)
│   │   ├── FEATURES.md                    # 기능 명세서
│   │   └── TESTIDS.md                     # E2E 테스트 표준
│
└── docs/history/ (아카이브)
    ├── Phase 완료 문서
    ├── 이전 설계 문서
    └── 통합 전 개별 문서들
```

---

## 전체 메뉴 완성도 요약

| 메뉴 | 완성도 | 상태 | 상세 |
|------|--------|------|------|
| **Ops Query System** | 88% | ✅ 상용 가능 | 6가지 질의 모드, Document Search, LangGraph |
| **Docs** | 100% | ✅ 상용 완료 | BM25 + pgvector 하이브리드, share/export/reindex/versioning |
| **API Manager** | 95% | ✅ 상용 가능 | SQL/HTTP/Python/Workflow Executor, 버전/롤백, 캐싱 |
| **Screens** | 94% | ✅ 상용 가능 | 15종 컴포넌트, Drag & Drop, RBAC |
| **CEP Builder** | 100% | ✅ 상용 완료 | 복합 조건, 7집계, 5채널 알림, CEP→API 트리거 |
| **Admin** | 100% | ✅ 상용 완료 | Assets, Catalogs, Explorer, Observability, 영속화 |
| **CEP Events** | 85% | ✅ 상용 가능 | 이벤트 목록, 필터링, SSE 스트리밍 |
| **Chat** | 92% | ✅ 상용 가능 | 채팅 UI, SSE 스트리밍, Thread 관리 |
| **전체 평균** | **94%** | ✅ 상용 준비 | 상세: `BLUEPRINT_PRODUCT_COMPLETENESS.md` |

## 6개 모듈별 문서 매핑

| 모듈 | Blueprint | 상용 준비도 | 완성도 |
|------|-----------|------------|---------|
| **OPS** | `BLUEPRINT_OPS_QUERY.md` | ✅ 상용 가능 | 88% |
| **CEP** | `BLUEPRINT_CEP_ENGINE.md` | ✅ 상용 완료 | 100% |
| **DOCS** | (SYSTEM_ARCHITECTURE_REPORT 내) | ✅ 상용 완료 | 100% |
| **API Engine** | `BLUEPRINT_API_ENGINE.md` | ✅ 상용 가능 | 95% |
| **ADMIN** | (SYSTEM_ARCHITECTURE_REPORT 내) | ✅ 상용 완료 | 100% |
| **Screen Editor** | `BLUEPRINT_SCREEN_EDITOR.md` | ✅ 상용 가능 | 94% |

---

## 문서 유지보수 가이드

1. **변경 시**: 해당 문서 1곳만 수정 (단일 정본)
2. **새 기능**: `FEATURES.md`에 추가
3. **아키텍처 변경**: 해당 모듈 Blueprint 업데이트 + `SYSTEM_ARCHITECTURE_REPORT.md` 반영
4. **중복 제거**: 분석용/임시 문서는 `docs/history/`로 이동

---

## 향후 개선 방안

### 단기 (1~2주)
- 접근성 (a11y) 완전 구현 (WCAG 2.1 AA 준수)

**기대 전체 완성도: 94% → 95%**

### 중기 (1~2개월)
- 다언어 지원 (한국어, 영어)

**기대 전체 완성도: 95% → 96%**

### 장기 (3~6개월)
- AI Copilot 고도화 (Screen Editor, CEP)
- ML 기반 이상 탐지
- 모바일 앱

**기대 전체 완성도: 96% → 98%**

---

**마지막 정리**: 2026-02-08
**활성 문서**: 15개 (docs/) + 3개 (root)
**전체 완성도**: 94% (상용 준비)
