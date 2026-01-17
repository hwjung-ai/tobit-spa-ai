# 📚 Tobit SPA AI - 문서 인덱스

**최종 정리**: 2026-01-18
**문서 개수**: 18개 (통합 후 최소화)
**목표**: 명확한 계층 구조로 필요한 문서를 빠르게 찾기

---

## 🎯 빠른 시작

### 처음 오신 분
1. **프로젝트 개요**: 루트 `README.md`
2. **개발 환경 설정**: 루트 `DEV_ENV.md`
3. **AI 에이전트 규칙**: 루트 `AGENTS.md` ⭐ **필독**

### 기능 구현
1. **기능 명세서**: `docs/FEATURES.md`
2. **UI Creator 계약**: 루트 `CONTRACT_UI_CREATOR_V1.md`
3. **자산 운영 가이드**: `docs/ASSET_OPERATIONS_GUIDE.md`

### 운영 & 배포
1. **운영 체크리스트**: `docs/OPERATIONS.md`
2. **운영 대응 가이드**: `docs/OPERATIONS_PLAYBOOK.md`
3. **프로덕션 준비**: `docs/PRODUCTION_GAPS.md`
4. **배포 전 검증**: `docs/PRODUCTION_CHECKLIST.md`

---

## 📂 문서 체계

```
tobit-spa-ai/
│
├── 📄 README.md                    # ⭐ 프로젝트 시작점
│                                   #   설치, 실행, 기본 구조
│
├── 🚀 개발 & 준비
│   ├── AGENTS.md                   # ⭐⭐⭐ AI 에이전트 필독
│   │                              #   기술 스택, 개발 규칙, 표준화
│   ├── DEV_ENV.md                  # 개발 환경 설정
│   │                              #   DB, 환경변수, 초기 설정
│   ├── PRODUCT_OVERVIEW.md         # 제품 개요
│   │                              #   가치 제안, 운영 흐름
│   └── CONTRACT_UI_CREATOR_V1.md   # UI Creator 기능 명세
│                                   #   3개 계약, API 정의
│
├── 📋 모든 문서 (docs/)
│   ├── INDEX.md                    # ⭐ 중앙 인덱스 (당신이 여기!)
│   │
│   ├── 기능 & 운영
│   ├── FEATURES.md                 # ⭐ 모든 기능 명세
│   │                              #   API, 사용 예시, 제약사항
│   ├── ADMIN_UI_GUIDE.md           # 관리자 UI 운영
│   │                              #   Assets, Observability, Settings
│   ├── ASSET_OPERATIONS_GUIDE.md   # 자산 운영
│   │                              #   Query, Prompt, Mapping, Policy
│   ├── OPERATIONS.md               # 운영 체크리스트
│   │                              #   기능 검증, smoke test
│   ├── OPERATIONS_PLAYBOOK.md      # 대응 가이드
│   │                              #   8가지 문제 시나리오, 진단법
│   │
│   ├── 프로덕션 준비
│   ├── ROADMAP.md                  # 통합 로드맵
│   │                              #   전략 + 타임라인 + 의존성
│   ├── PRODUCTION_GAPS.md          # P0-P2 프로덕션 TODO
│   │                              #   상세 기능별, 우선순위
│   ├── PRODUCTION_CHECKLIST.md     # 배포 전 체크리스트
│   │                              #   200+ 항목, 진행 추적
│   ├── IMPLEMENTATION_ROADMAP.md   # 구현 상세 계획
│   │                              #   Phase별 구체적 단계, 의존성
│   │
│   └── 📦 history/                 # 아카이브 (참고용)
│       ├── README.md               # 아카이브 설명
│       ├── FINAL_STATUS.md         # 완료도 추이
│       ├── PHASE_SUMMARIES.md      # Phase 1-4 요약
│       └── P0_P1_P2_IMPROVEMENTS.md # 개선 추적
```

---

## 🔍 용도별 문서 찾기

### 🏗️ 아키텍처 & 설계
| 문서 | 목적 |
|------|------|
| **AGENTS.md** | 기술 스택, 개발 규칙, Tool Contract 표준 |
| **CONTRACT_UI_CREATOR_V1.md** | UI/Action 계약, API 정의 |
| **ROADMAP.md** | 전체 시스템 전략, Phase별 목표 |
| **IMPLEMENTATION_ROADMAP.md** | 상세 구현 계획, 의존성 분석 |

### 💻 개발 & 코딩
| 문서 | 목적 |
|------|------|
| **DEV_ENV.md** | 로컬 개발 환경 설정 |
| **FEATURES.md** | API 엔드포인트, 사용 예시 |
| **ASSET_OPERATIONS_GUIDE.md** | 자산 생성/수정/발행 절차 |
| **PRODUCTION_CHECKLIST.md** | 코드 완료 기준 (200+ 항목) |

### 🚀 배포 & 운영
| 문서 | 목적 |
|------|------|
| **ROADMAP.md** | 배포 타임라인 (12주) |
| **OPERATIONS.md** | 기능 검증, Smoke test |
| **OPERATIONS_PLAYBOOK.md** | 문제 대응 가이드 (8가지 시나리오) |
| **PRODUCTION_GAPS.md** | 프로덕션 준비 TODO |
| **PRODUCTION_CHECKLIST.md** | 배포 전 체크리스트 |

### 👨‍💼 관리 & 운영
| 문서 | 목적 |
|------|------|
| **ADMIN_UI_GUIDE.md** | 관리자 UI 사용법 |
| **ASSET_OPERATIONS_GUIDE.md** | 자산 발행, 롤백 절차 |
| **OPERATIONS_PLAYBOOK.md** | 장애 진단 & 대응 |
| **PRODUCTION_CHECKLIST.md** | 배포 준비 체크리스트 |

---

## 📊 문서 현황

### 정리 전 (2026-01-17)
- 총 31개 파일
- 중복 내용: ~1,200줄
- 파일 산재도: 높음

### 정리 후 (2026-01-18)
- 총 18개 활성 파일 + 5개 아카이브
- 중복 제거: 100%
- 명확한 계층 구조 확립

### 삭제된 파일
- 아카이브 8개: FINAL_*, PHASE_*, C_D_TRACK_* 등
- 중복/불필요 10개: ADMIN_UI_* (3), ASSET_*_GUIDE.md (2), OBSERVABILITY_*, RCA_*, REGRESSION_* 등
- 기존 로드맵: ROADMAP_6M.md

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

**마지막 정리**: 2026-01-18
**유지보수**: 자동 (문서 변경 시 커밋 메시지에 명시)
**다음 검토**: 2026-02-18
