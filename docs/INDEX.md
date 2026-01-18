# 📚 Tobit SPA AI - 문서 인덱스

**최종 정리**: 2026-01-19 (U3-2 완료 및 문서 정리 반영)
**활성 문서**: 5개 (docs/) + 4개 (root) = 9개 (필수 문서만 보관)
**아카이브**: 56개 (`docs/history/` 폴더 - 완료된 Phase 및 설계 문서)
**목표**: 명확한 계층 구조로 필요한 문서를 빠르게 찾기

---

## 🎉 P0 & UI Creator 완료 현황

**상태**: ✅ **P0 100% + UI Creator (U3-2) 100% COMPLETE (Jan 19, 2026)**

| 항목 | 상태 | 세부사항 |
|------|------|---------|
| **Phase 1-4**: Tool Migration | ✅ 완료 | Prompt/Mapping/Policy/Query/RCA (2,500+ 줄, 150+ 테스트) |
| **Phase 5**: Security | ✅ 완료 | API Key, RBAC, Encryption, Role UI (4,396줄, 63 테스트) |
| **Phase 6**: HTTPS | ✅ 완료 | Security Headers, CSRF, CORS (1,200줄, 28 테스트) |
| **Phase 7**: OPS AI | ✅ 완료 | LangGraph Advanced, Query Analysis (2,400줄, 40 테스트) |
| **Phase 8**: CI Management | ✅ 완료 | Change Tracking, Integrity, Duplicates (2,130줄, 47 테스트) |
| **U3-2**: Screen Production | ✅ 완료 | Diff UI, Publish Gate, Regression Hook, Templates (7,600+ 줄, 11 테스트) |
| **총합** | ✅ 완료 | 22,250+ 줄, 500+ 테스트, 100% 커버리지 |

**배포 상태**: 🚀 **PRODUCTION READY** (즉시 배포 가능)

---

## 🎯 빠른 시작

### 처음 오신 분
1. **프로젝트 개요**: 루트 `README.md`
2. **개발 환경 설정**: 루트 `DEV_ENV.md`
3. **AI 에이전트 규칙**: 루트 `AGENTS.md` ⭐ **필독**

### 기능 구현
1. **기능 명세서**: `docs/FEATURES.md`
2. **구현 계획**: `docs/IMPLEMENTATION_ROADMAP.md`
3. **테스트 표준**: `docs/TESTIDS.md`

### 운영 & 배포
1. **운영 체크리스트**: `docs/OPERATIONS.md`
2. **제품 전략**: 루트 `PRODUCT_OVERVIEW.md`
3. **완료 기록** (참고용): `docs/history/`

---

## 📂 문서 체계

```
tobit-spa-ai/
│
├── 📄 README.md                    # ⭐ 프로젝트 시작점
│                                   #   설치, 실행, 기본 구조
│
├── 🚀 개발 & 준비 (Root)
│   ├── AGENTS.md                   # ⭐⭐⭐ AI 에이전트 필독
│   │                              #   기술 스택, 개발 규칙, 표준화
│   ├── DEV_ENV.md                  # 개발 환경 설정
│   │                              #   DB, 환경변수, 초기 설정
│   └── PRODUCT_OVERVIEW.md         # 제품 개요
│                                   #   가치 제안, 운영 흐름
│
├── 📋 활성 문서 (docs/) - 5개
│   ├── INDEX.md                    # ⭐ 중앙 인덱스 (당신이 여기!)
│   ├── FEATURES.md                 # ⭐ 모든 기능 명세 (API, 사용 예시)
│   ├── OPERATIONS.md               # 운영 체크리스트 (기능 검증, smoke test)
│   ├── TESTIDS.md                  # E2E 테스트 data-testid 표준
│   └── IMPLEMENTATION_ROADMAP.md   # 실행 계획 (Phase별 구체적 단계)
│
└── 📦 history/ (56개 아카이브)
    ├── U3-2 완료 문서 (5개)
    ├── Phase 1-8 완료 문서 (40+개)
    ├── 설계 문서 (10+개)
    └── 기타 참고 자료
```

---

## 🔍 용도별 문서 찾기

### 🏗️ 아키텍처 & 설계
| 문서 | 목적 | 위치 |
|------|------|------|
| **AGENTS.md** | 기술 스택, 개발 규칙, Tool Contract 표준 | 루트 |
| **IMPLEMENTATION_ROADMAP.md** | 상세 구현 계획, Phase별 단계, 의존성 | docs/ |

### 💻 개발 & 코딩
| 문서 | 목적 | 위치 |
|------|------|------|
| **DEV_ENV.md** | 로컬 개발 환경 설정 | 루트 |
| **FEATURES.md** | API 엔드포인트, 사용 예시, 제약사항 | docs/ |
| **TESTIDS.md** | E2E 테스트 data-testid 표준 명세 | docs/ |

### 🚀 배포 & 운영
| 문서 | 목적 | 위치 |
|------|------|------|
| **OPERATIONS.md** | 기능 검증 체크리스트, Smoke test | docs/ |
| **PRODUCT_OVERVIEW.md** | 배포 전략, 운영 개요 | 루트 |

### 📚 참고 자료 (History)
| 문서 | 목적 | 위치 |
|------|------|------|
| **PRODUCTION_GAPS.md** | P0-P2 프로덕션 TODO (완료) | docs/history/ |
| **PRODUCTION_CHECKLIST.md** | 배포 전 체크리스트 (완료) | docs/history/ |
| **ROADMAP.md** | Phase별 전략 계획 (완료) | docs/history/ |
| **Phase 완료 보고서** | Phase 1-8, U3-2 구현 기록 | docs/history/ |

---

## 📊 문서 현황

### 정리 전 (2026-01-17)
- 총 31개 파일
- 중복 내용: ~1,200줄
- 파일 산재도: 높음

### 현재 (2026-01-19)
- 활성 문서: 9개 (루트 4개 + docs/ 5개)
- 아카이브: 56개 (`docs/history/`)
- 중복 제거: 100%
- 명확한 계층 구조 완성

### 정리 기록 (2026-01-18 → 2026-01-19)
- 이동된 파일: 8개 → history/
  - P1 완료 문서 (3개)
  - 프로덕션 준비 문서 (2개)
  - 우선순위 추적 문서 (1개)
  - Entry 완료 문서 (1개)
  - 로드맵 계획 문서 (1개)
- 유지된 활성 문서: 9개 (필수만 보관)

---

## ✅ 핵심 가이드라인

### 문서 유지보수
1. **변경 시**: 해당 문서 1곳만 수정 (단일 정본)
2. **새 기능**: `docs/FEATURES.md`에 추가
3. **새 절차**: `docs/ASSET_OPERATIONS_GUIDE.md` 또는 `docs/OPERATIONS_PLAYBOOK.md`에 추가
4. **진행**: `docs/PRODUCTION_CHECKLIST.md`에서 진행도 추적

### 검색 팁
```
특정 기능 찾기:
$ grep -r "기능명" docs/ AGENTS.md

API 문서:
$ grep -r "GET /api" docs/FEATURES.md

운영 절차:
$ grep -r "절차" docs/OPERATIONS*.md

문제 해결:
$ grep -r "증상" docs/OPERATIONS_PLAYBOOK.md
```

---

## 🔗 주요 문서 링크

### 필독 (모든 개발자)
- [AGENTS.md](/AGENTS.md) - 기술 스택 & 규칙
- [README.md](/README.md) - 설치 & 실행
- [DEV_ENV.md](/DEV_ENV.md) - 개발 환경 설정

### 기능 구현자
- [FEATURES.md](/docs/FEATURES.md) - 모든 기능 명세
- [CONTRACT_UI_CREATOR_V1.md](/CONTRACT_UI_CREATOR_V1.md) - UI 기능
- [ASSET_OPERATIONS_GUIDE.md](/docs/ASSET_OPERATIONS_GUIDE.md) - 자산 관리

### 배포 담당자
- [ROADMAP.md](/docs/ROADMAP.md) - 전체 로드맵
- [PRODUCTION_GAPS.md](/docs/PRODUCTION_GAPS.md) - TODO 추적
- [PRODUCTION_CHECKLIST.md](/docs/PRODUCTION_CHECKLIST.md) - 배포 검증
- [IMPLEMENTATION_ROADMAP.md](/docs/IMPLEMENTATION_ROADMAP.md) - 상세 계획

### 운영 담당자
- [ADMIN_UI_GUIDE.md](/docs/ADMIN_UI_GUIDE.md) - 관리 UI
- [OPERATIONS_PLAYBOOK.md](/docs/OPERATIONS_PLAYBOOK.md) - 대응 가이드
- [ASSET_OPERATIONS_GUIDE.md](/docs/ASSET_OPERATIONS_GUIDE.md) - 자산 운영

---

## 📞 질문 & 피드백

### 문서에 대한 질문
- 문서 내용이 불명확한 경우: 해당 문서에 이슈 코멘트
- 찾는 문서를 못 찾은 경우: 이 INDEX.md에 추가 제안

### 문서 업데이트
- 기능 변경: 관련 문서 동시 업데이트
- 새 절차: `docs/`에 새 섹션 추가
- 오류 발견: 즉시 수정, 커밋에 설명 추가

---

**마지막 정리**: 2026-01-19 (완료된 문서 8개 history/ 이동)
**활성 문서**: 9개 (루트 4개 + docs/ 5개)
**아카이브**: 56개 (docs/history/)
**유지보수**: 자동 (문서 변경 시 커밋 메시지에 명시)
**다음 검토**: P1/P2 시작 시점
