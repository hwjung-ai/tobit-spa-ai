# Tobit SPA AI - 문서 인덱스

**최종 정리**: 2026-02-20
**전체 완성도**: 95%

## 최근 마일스톤 (2026-02-14 ~ 2026-02-20)

### ✅ P0-4 Query Safety Validation - 완전 통합 (Feb 14)
- DirectQueryTool에 QuerySafetyValidator 통합
- 모든 SQL 쿼리 검증 (read-only, DDL/DCL 차단, tenant isolation)
- 23개 테스트 모두 통과

### ✅ OPS Orchestration 안정화 (Feb 17-18)
- OPS SSE flow 및 Inspector mapping visibility 개선
- Stage assets 정규화 및 legacy compat alias 제거
- LLM 기반 동적 도구 선택 시스템 완성

### ✅ OPS 모드 라우팅 완전 수정 (Feb 17)
- Mode parameter 전체 파이프라인에서 작동
- "all" 모드 선택 시 full orchestration 실행
- Document search 통합 (orchestration의 일부)
- UI Mode 태그 정상 표시

### ✅ Document Search Tool 완성 (Feb 17)
- body_template 추가 및 하이브리드 검색 정상 작동
- BM25 + pgvector 하이브리드 검색
- OPS orchestration에서 문서 검색 호출

### ✅ UI Design System 일관성 (Feb 13)
- 타이포그래피 정규화: 14개 인스턴스
- CSS 변수 bracket 제거: 118개 → 0개
- 하드코딩된 색상 제거: 10개 이상
- Spacing 표준화: 73개+ 인스턴스

**활성 문서**: 17개 (docs/)
**아카이브**: docs/history/ (완료된 Phase 및 설계 문서)

---

## 빠른 시작

### 처음 오신 분
1. **프로젝트 개요**: 루트 `README.md`
2. **AI 에이전트 규칙**: 루트 `AGENTS.md` **필독**

### 아키텍처 이해
1. **OPS 쿼리 설계**: `BLUEPRINT_OPS_QUERY.md`
2. **CEP 엔진 설계**: `BLUEPRINT_CEP_ENGINE.md`
3. **API Engine 설계**: `BLUEPRINT_API_ENGINE.md`
4. **Screen Editor 설계**: `BLUEPRINT_SCREEN_EDITOR.md`
5. **Admin 설계**: `BLUEPRINT_ADMIN.md`
6. **SIM 설계**: `BLUEPRINT_SIM.md`

### 기능 구현
1. **기능 명세서**: `FEATURES.md`
2. **테스트 표준**: `TESTING_STRUCTURE.md` (data-testid 네이밍 규칙 포함)
3. **UI 디자인 시스템 가이드**: `UI_DESIGN_SYSTEM_GUIDE.md`
4. **UI 패턴 레시피**: `UI_PATTERN_RECIPES.md`

### 사용자 가이드
1. **OPS 사용자 가이드**: `USER_GUIDE_OPS.md`
2. **CEP 사용자 가이드**: `USER_GUIDE_CEP.md`
3. **API 사용자 가이드**: `USER_GUIDE_API.md`
4. **Screen Editor 사용자 가이드**: `USER_GUIDE_SCREEN_EDITOR.md`
5. **Admin 사용자 가이드**: `USER_GUIDE_ADMIN.md`
6. **SIM 사용자 가이드**: `USER_GUIDE_SIM.md`

---

## 문서 체계

```
tobit-spa-ai/
│
├── Root (2개)
│   ├── README.md                    # 프로젝트 개요, 빠른 시작
│   └── AGENTS.md                    # AI 에이전트 필독 규칙
│
├── docs/ (17개)
│   ├── INDEX.md                     # 문서 인덱스 (이 파일)
│   │
│   ├── 아키텍처 & Blueprint (6개)
│   │   ├── BLUEPRINT_OPS_QUERY.md   # OPS 쿼리 시스템
│   │   ├── BLUEPRINT_CEP_ENGINE.md  # CEP 엔진
│   │   ├── BLUEPRINT_API_ENGINE.md  # API Engine
│   │   ├── BLUEPRINT_SCREEN_EDITOR.md # Screen Editor
│   │   ├── BLUEPRINT_ADMIN.md       # Admin System
│   │   └── BLUEPRINT_SIM.md         # SIM Workspace
│   │
│   ├── 사용자 가이드 (6개)
│   │   ├── USER_GUIDE_OPS.md        # OPS 운영/학습 사용자 가이드
│   │   ├── USER_GUIDE_CEP.md        # CEP 규칙/이벤트 운영 가이드
│   │   ├── USER_GUIDE_API.md        # API Manager 사용자 가이드
│   │   ├── USER_GUIDE_SCREEN_EDITOR.md # Screen Editor 사용자 가이드
│   │   ├── USER_GUIDE_ADMIN.md      # Admin System 사용자 가이드
│   │   └── USER_GUIDE_SIM.md        # SIM Workspace 사용자 가이드
│   │
│   └── 기능/운영 (5개)
│       ├── FEATURES.md              # 기능 명세서
│       ├── TESTING_STRUCTURE.md     # 테스트 구조 표준
│       ├── UI_DESIGN_SYSTEM_GUIDE.md # UI 디자인 시스템
│       └── UI_PATTERN_RECIPES.md    # UI 패턴 레시피
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
| **Ops Query System** | 88% | ✅ 상용 가능 | 6가지 질의 모드, Document Search, LLM Orchestration |
| **SIM Workspace** | 91% | ✅ 상용 가능 | What-if/Stress/Capacity, Topology, Backtest, CSV Export |
| **Docs** | 100% | ✅ 상용 완료 | BM25 + pgvector 하이브리드, share/export/reindex/versioning |
| **API Manager** | 95% | ✅ 상용 가능 | SQL/HTTP/Python/Workflow Executor, 버전/롤백, 캐싱 |
| **Screens** | 94% | ✅ 상용 가능 | 15종 컴포넌트, Drag & Drop, RBAC |
| **CEP Builder** | 100% | ✅ 상용 완료 | 복합 조건, 7집계, 5채널 알림, CEP→API 트리거 |
| **Admin** | 95% | ✅ 상용 가능 | Assets, Tools, Catalogs, Explorer, Observability, 영속화 |
| **CEP Events** | 85% | ✅ 상용 가능 | 이벤트 목록, 필터링, SSE 스트리밍 |
| **Chat** | 92% | ✅ 상용 가능 | 채팅 UI, SSE 스트리밍, Thread 관리 |
| **전체 평균** | **94%** | ✅ 상용 준비 | |

## 6개 모듈별 문서 매핑

| 모듈 | Blueprint | 상용 준비도 | 완성도 |
|------|-----------|------------|---------|
| **OPS** | `BLUEPRINT_OPS_QUERY.md` | ✅ 상용 가능 | 88% |
| **CEP** | `BLUEPRINT_CEP_ENGINE.md` | ✅ 상용 완료 | 100% |
| **DOCS** | `FEATURES.md` (검색 섹션) | ✅ 상용 완료 | 100% |
| **API Engine** | `BLUEPRINT_API_ENGINE.md` | ✅ 상용 가능 | 95% |
| **ADMIN** | `BLUEPRINT_ADMIN.md` | ✅ 상용 가능 | 95% |
| **Screen Editor** | `BLUEPRINT_SCREEN_EDITOR.md` | ✅ 상용 가능 | 94% |

---

## 문서 유지보수 가이드

1. **변경 시**: 해당 문서 1곳만 수정 (단일 정본)
2. **새 기능**: `FEATURES.md`에 추가
3. **아키텍처 변경**: 해당 모듈 Blueprint 업데이트
4. **중복 제거**: 분석용/임시 문서는 `docs/history/`로 이동

---

## 향후 개선 방안

### 단기 (1~2주)
- 접근성 (a11y) 완전 구현 (WCAG 2.1 AA 준수)

**기대 전체 완성도: 95% → 96%**

### 중기 (1~2개월)
- 다언어 지원 (한국어, 영어)

**기대 전체 완성도: 96% → 97%**

### 장기 (3~6개월)
- AI Copilot 고도화 (Screen Editor, CEP)
- ML 기반 이상 탐지
- 모바일 앱

**기대 전체 완성도: 97% → 98%**

---

**마지막 정리**: 2026-02-20
**활성 문서**: 17개 (docs/)
**전체 완성도**: 95% (상용 준비)
