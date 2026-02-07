# Tobit SPA AI - 문서 인덱스

**최종 정리**: 2026-02-08
**활성 문서**: 10개 (docs/) + 3개 (root) = 13개
**아카이브**: docs/history/ (완료된 Phase 및 설계 문서)

---

## 빠른 시작

### 처음 오신 분
1. **프로젝트 개요**: 루트 `README.md`
2. **개발 환경 설정**: 루트 `DEV_ENV.md`
3. **AI 에이전트 규칙**: 루트 `AGENTS.md` **필독**

### 아키텍처 이해
1. **시스템 전체 개요**: `SYSTEM_ARCHITECTURE_REPORT.md` (v1.6)
2. **OPS 쿼리 설계**: `OPS_QUERY_BLUEPRINT.md`
3. **CEP 엔진 설계**: `CEP_ENGINE_BLUEPRINT.md`
4. **API Engine 설계**: `API_ENGINE_BLUEPRINT.md`
5. **Screen Editor 설계**: `SCREEN_EDITOR_BLUEPRINT.md`

### 기능 구현
1. **기능 명세서**: `FEATURES.md`
2. **테스트 표준**: `TESTIDS.md`

---

## 문서 체계

```
tobit-spa-ai/
│
├── Root (3개)
│   ├── README.md                    # 프로젝트 개요, 빠른 시작
│   ├── AGENTS.md                    # AI 에이전트 필독 규칙
│   └── DEV_ENV.md                   # 개발 환경 설정
│
├── docs/ (10개)
│   ├── INDEX.md                     # 문서 인덱스 (이 파일)
│   │
│   ├── 아키텍처 Blueprint (5개)
│   │   ├── SYSTEM_ARCHITECTURE_REPORT.md  # 시스템 전체 아키텍처 (v1.6)
│   │   ├── OPS_QUERY_BLUEPRINT.md         # OPS 쿼리 시스템
│   │   ├── CEP_ENGINE_BLUEPRINT.md        # CEP 엔진
│   │   ├── API_ENGINE_BLUEPRINT.md        # API Engine
│   │   └── SCREEN_EDITOR_BLUEPRINT.md     # Screen Editor
│   │
│   ├── 기능/운영 (2개)
│   │   ├── FEATURES.md                    # 기능 명세서
│   │   └── TESTIDS.md                     # E2E 테스트 표준
│   │
│   ├── 검증 (1개)
│   │   └── README.md                      # 시스템 완성도 검증 결과
│   │
│   └── 참고 (1개)
│       └── PRODUCT_OVERVIEW.md            # 제품 전략 개요
│
└── docs/history/ (아카이브)
    ├── Phase 완료 문서
    ├── 이전 설계 문서
    └── 통합 전 개별 문서들
```

---

## 6개 모듈별 문서 매핑

| 모듈 | Blueprint | 상용 준비도 | codepen 감사 |
|------|-----------|------------|-------------|
| **OPS** | `OPS_QUERY_BLUEPRINT.md` | 90% | 85% (엔드포인트 오류 정정) |
| **CEP** | `CEP_ENGINE_BLUEPRINT.md` | 90% | 90% (Catalogs 100%, Explorer 95%) |
| **DOCS** | (SYSTEM_ARCHITECTURE_REPORT 내) | 85% | - |
| **API Engine** | `API_ENGINE_BLUEPRINT.md` | 80% | 80% (codepen 70% -> 상향 정정) |
| **ADMIN** | (SYSTEM_ARCHITECTURE_REPORT 내) | 85% | - |
| **Screen Editor** | `SCREEN_EDITOR_BLUEPRINT.md` | 95% | 95% |

---

## 문서 유지보수 가이드

1. **변경 시**: 해당 문서 1곳만 수정 (단일 정본)
2. **새 기능**: `FEATURES.md`에 추가
3. **아키텍처 변경**: 해당 모듈 Blueprint 업데이트 + `SYSTEM_ARCHITECTURE_REPORT.md` 반영
4. **중복 제거**: 분석용/임시 문서는 `docs/history/`로 이동

---

**마지막 정리**: 2026-02-08
**활성 문서**: 10개 (docs/) + 3개 (root)
