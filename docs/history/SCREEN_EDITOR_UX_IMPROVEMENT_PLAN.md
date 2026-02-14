# Screen Editor UX 개선 작업계획서

**작성일**: 2026-02-14
**목표**: 제품 수준 UX 완성도 달성
**예상 소요**: 1~2일

---

## 📋 개선 항목

### P0: 사용자 온보딩 (필수)
- [ ] 온보딩 튜토리얼 컴포넌트
- [ ] 첫 방문 시 가이드 표시
- [ ] 컴포넌트별 도움말 툴팁

### P1: 템플릿 확장
- [ ] 실용적인 예제 템플릿 5개 추가
- [ ] 템플릿 갤러리 UI 개선

### P2: UI 다듬기
- [ ] 빈 상태 안내 메시지
- [ ] 키보드 단축키 안내
- [ ] 에러 메시지 친근하게

### P3: AI Copilot 개선
- [ ] 프롬프트 예시 제공
- [ ] 빠른 액션 버튼

---

## 1️⃣ 진행 상황

### Phase 1: 온보딩 시스템 ✅
- [x] OnboardingTour 컴포넌트 생성 (`common/OnboardingTour.tsx`)
- [x] 7단계 가이드 작성 (환영, 컴포넌트, 속성, 액션, 바인딩, Copilot, 미리보기)
- [x] localStorage로 완료 상태 저장
- [x] useOnboardingStatus 훅

### Phase 2: 템플릿 ✅
- [x] 기존 4개 템플릿 (Read-only Detail, List+Filter, List+Modal CRUD, Dashboard)
- [x] 로그인 폼 템플릿 추가
- [x] 고객 상세 템플릿 추가
- [x] 설정 폼 템플릿 추가
- [x] 알림 목록 템플릿 추가
- **총 8개 템플릿**

### Phase 3: UI Polish ✅
- [x] EmptyState 컴포넌트 (`common/EmptyState.tsx`)
- [x] EmptyComponentsState
- [x] EmptyActionsState
- [x] WelcomeState (새 화면 만들기)
- [x] Copilot 빠른 액션 버튼 (6개)

---

## 2️⃣ 생성된 파일

```
apps/web/src/components/admin/screen-editor/common/
├── OnboardingTour.tsx    # 온보딩 튜토리얼
└── EmptyState.tsx        # 빈 상태 컴포넌트들

apps/web/src/lib/ui-screen/
└── screen-templates.ts   # 8개 템플릿 (4개 추가)

apps/web/src/components/admin/screen-editor/
└── CopilotPanel.tsx      # 빠른 액션 추가
```

---

## 3️⃣ 기능 요약

### 온보딩 튜토리얼
- 첫 방문 시 자동 표시
- 7단계 가이드 (다음/이전/건너뛰기)
- 진행 상태 표시
- localStorage로 완료 상태 유지

### 빈 상태 안내
- 컴포넌트 없을 때 안내
- 액션 없을 때 안내
- 새 화면 만들기 (템플릿 vs 빈 화면)

### 빠른 액션 (Copilot)
- 🔵 버튼 추가
- 📝 입력 필드
- 📊 테이블
- 🎨 색상 변경
- 📐 레이아웃
- ❌ 삭제

### 템플릿 (8개)
1. Read-only Detail
2. List + Filter
3. List + Modal CRUD
4. Observability Dashboard
5. 로그인 폼
6. 고객 상세
7. 설정 폼
8. 알림 목록

---

**완료일**: 2026-02-14
**상태**: UX 개선 완료 ✅
