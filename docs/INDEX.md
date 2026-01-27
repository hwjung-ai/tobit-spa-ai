# 📚 Tobit SPA AI - 문서 인덱스

**최종 정리**: 2026-01-27
**활성 문서**: 9개 (docs/) + 4개 (root) = 13개
**아카이브**: 56개 (`docs/history/` 폴더 - 완료된 Phase 및 설계 문서)

---

## 🎯 빠른 시작

### 처음 오신 분
1. **프로젝트 개요**: 루트 `README.md`
2. **개발 환경 설정**: 루트 `DEV_ENV.md`
3. **AI 에이전트 규칙**: 루트 `AGENTS.md` ⭐ **필독**

### 기능 구현
1. **기능 명세서**: `docs/FEATURES.md`
2. **테스트 표준**: `docs/TESTIDS.md`

### 제품/운영
1. **운영 체크리스트**: `docs/OPERATIONS.md`
2. **제품 전략**: 루트 `PRODUCT_OVERVIEW.md`

---

## 📂 문서 체계

```
tobit-spa-ai/
│
├── 🚀 개발 & 준비 (Root) - 4개
│   ├── README.md
│   ├── AGENTS.md                   # ⭐⭐⭐ AI 에이전트 필독
│   ├── DEV_ENV.md                  # 개발 환경 설정
│   └── PRODUCT_OVERVIEW.md         # 제품 개요
│
├── 📋 활성 문서 (docs/) - 7개
│   ├── INDEX.md                                   # ⭐ 중앙 인덱스 (당신이 여기!)
│   ├── FEATURES.md                                # ⭐ 모든 기능 명세
│   ├── OPERATIONS.md                             # 운영 체크리스트
│   ├── TESTIDS.md                                # E2E 테스트 표준
│   ├── ORCHESTRATION_USER_GUIDE.md               # ⭐ OPS 사용자 가이드
│   ├── PIPELINE_AND_ASSETS.md                     # ⭐ 기술 아키텍처 가이드
│   └── TESTING_STRUCTURE.md                      # 테스트 구조
│
└── 📦 history/ (56개 아카이브)
    ├── U3-2 완료 문서
    ├── Phase 1-8 완료 문서
    ├── 설계 문서
    └── 기타 참고 자료
```

---

## 🔍 용도별 문서 찾기

### 🏗️ 오케스트레이션 (완료 ✅)
| 문서 | 목적 | 테스트 결과 |
|------|------|------------|
| **ORCHESTRATION_USER_GUIDE.md** | ⭐ OPS 사용자 학습 가이드 | 99/99 (100%) |
| **PIPELINE_AND_ASSETS.md** | ⭐ Stage Pipeline & Assets 기술 아키텍처 | - |

### 🚀 배포 & 운영
| 문서 | 목적 | 위치 |
|------|------|------|
| **OPERATIONS.md** | 운영 체크리스트, Smoke Test, UI 표준 검증 | docs/ |
| **PRODUCT_OVERVIEW.md** | 배포 전략, 운영 개요 | 루트 |

### 💻 개발
| 문서 | 목적 | 위치 |
|------|------|------|
| **DEV_ENV.md** | 개발 환경 설정 | 루트 |
| **FEATURES.md** | API 명세, 기능 목록 | docs/ |
| **TESTING_STRUCTURE.md** | 테스트 구조 | docs/ |

### 📚 참고 (History)
| 문서 | 목적 | 위치 |
|------|------|------|
| **PRODUCTION_GAPS.md** | P0-P2 프로덕션 TODO | docs/history/ |
| **PRODUCTION_CHECKLIST.md** | 배포 전 체크리스트 | docs/history/ |
| **ROADMAP.md** | Phase별 전략 계획 | docs/history/ |
| **Phase 완료 보고서** | Phase 1-8, U3-2 구현 기록 | docs/history/ |

---

## ✅ 완료된 작업

### 범용 오케스트레이션 (2026-01-27 완료)
| 항목 | 결과 |
|------|------|
| 테스트 정확도 | **99/99 (100%)** |
| CI 카테고리 | 25/25 (100%) |
| Graph 카테고리 | 24/24 (100%) |
| Metric 카테고리 | 25/25 (100%) |
| History 카테고리 | 25/25 (100%) |

---

## ✅ 핵심 가이드라인

### 문서 유지보수
1. **변경 시**: 해당 문서 1곳만 수정 (단일 정본)
2. **새 기능**: `docs/FEATURES.md`에 추가
3. **새 절차**: 새로운 계획 문서를 docs/에 생성
4. **중복 제거**: 분석용/임시 문서는 history/로 이동 또는 삭제

### 문서 정리 기록
**2026-01-27**: 문서 재구성
- `OPS_ORCHESTRATION_USER_GUIDE_v2.md` → `ORCHESTRATION_USER_GUIDE.md` (이름 변경, 테스트 결과 추가)
- `PIPELINE_AND_ASSETS_COMPLETE_GUIDE.md` → `PIPELINE_AND_ASSETS.md` (이름 변경, 제목 간소화)
- `UNIVERSAL_ORCHESTRATION_COMPLETE.md` 삭제 (내용은 ORCHESTRATION_USER_GUIDE에 통합)
- `USER_GUIDE.md` 삭제 (내용은 ORCHESTRATION_USER_GUIDE에 포함)

---

**마지막 정리**: 2026-01-27
**활성 문서**: 9개 (docs/) + 4개 (root)
**아카이브**: 56개 (docs/history/)
