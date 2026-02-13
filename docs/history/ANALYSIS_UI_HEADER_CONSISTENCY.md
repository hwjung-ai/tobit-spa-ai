# UI Header 일관성 분석 보고서

> 분석 일자: 2026-02-12
> 분석 대상: 메인 메뉴 페이지 상단 헤더 섹션 일관성

---

## 1. 분석 대상 페이지

### 메인 메뉴
1. **Home** (`/app/page.tsx`) - Streaming Assistant
2. **OPS** (`/app/ops/page.tsx`) - OPS Workspace
3. **SIM** (`/app/sim/page.tsx`) - SIM Workspace
4. **Documents** (`/app/documents/page.tsx`) - Document Index
5. **CEP Events** (`/app/cep-events/page.tsx`) - CEP Event Browser
6. **CEP Builder** (`/app/cep-builder/page.tsx`) - CEP Builder

### Admin 메뉴
7. **Settings** (`/app/admin/settings/page.tsx`)
8. **Assets** (`/app/admin/assets/page.tsx`)
9. **Inspector** (`/app/admin/inspector/page.tsx`)
10. **API Manager** (`/app/api-manager/page.tsx`)

---

## 2. 현재 헤더 패턴 분석

### 패턴 A: 가장 표준적인 헤더 (Home, OPS, SIM, Documents)
```tsx
<div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
  <div>
    <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
      {pageTitle}
    </h1>
    <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
      {pageDescription}
    </p>
  </div>
  <div className="flex gap-2">
    {/* Action buttons */}
  </div>
</div>
```

**특징**:
- 헤딩 없음 (기본 배경에서 표시)
- `<h1>`: `text-2xl font-semibold`
- 설명: `mt-2 text-sm`
- 버튼 그룹: `flex gap-2`

---

### 패턴 B: 내부 섹션 스타일 (CEP Events)
```tsx
<header className="flex flex-wrap items-end justify-between gap-4">
  <div>
    <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
      CEP Event Browser
    </h1>
    <p className="text-sm text-slate-600 dark:text-slate-400">
      알림 발화 이력과 ACK 상태를 확인합니다. (SSE 갱신)
    </p>
  </div>
  <div className="flex flex-wrap gap-3 br-section ...">
    {/* Summary stats */}
  </div>
</header>
```

**특징**:
- 별도의 `<header>` 태그 사용
- 버튼/상태 카드를 동일 라인에 배치
- `flex-wrap`으로 모바일 브레이크 대응

---

### 패턴 C: 라이트 그레이 배경 헤더 (CEP Builder)
```tsx
<header className="border-b border-slate-200 px-6 py-4 dark:border-slate-800 bg-white dark:bg-slate-900">
  <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
    CEP Builder
  </h1>
  <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
    Define, simulate, and trigger complex CEP rules...
  </p>
</header>
```

**특징**:
- 명시적 `border-b`로 하단 구분선
- `px-6 py-4` 패딩 (메인 컨텐츠와 다름)
- 흰색 배경 (light mode)

---

### 패턴 D: SIM Workspace (복합형)
```tsx
<header className="border-b px-6 py-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
  <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
    SIM Workspace
  </h1>
  <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
    질문과 가정값을 기반으로 계획을 검증한 뒤 실행합니다...
  </p>
</header>
```

---

### 패턴 E: Admin Settings
```tsx
<div className="space-y-6">
  {/* Banner */}
  <div className="alert-box alert-warning">...</div>

  {/* No h1 - Uses inline section instead */}
  <div className="insp-section">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="inline-flex rounded-xl border p-1 ...">
        {/* Tab buttons */}
      </div>
      <div className="flex flex-wrap items-center gap-2 ...">
        {/* Status badges */}
      </div>
    </div>
    <p className="mt-3 text-xs text-muted-standard">...</p>
  </div>
</div>
```

**특징**:
- `<h1>` 없음
- 배너/탭을 헤더로 사용
- 전체 `space-y-6`로 래핑

---

## 3. 식별된 일관성 문제

### 3.1 헤더 하단 구분선 불일치
- **Home/OPS/SIM/Documents**: 하단 구분선 없음
- **CEP Builder/SIM**: `border-b`로 명시적 하단 구분선
- **CEP Events**: 하단 구분선 없음

### 3.2 헤더 배경색 불일치
- **대부분**: 기본 배경 (`bg-slate-50` 또는 `bg-white`)
- **일부**: 흰색 배경 명시 사용 (`bg-white`)

### 3.3 패딩 불일치
| 페이지 | 상단 패딩 |
|-------|-----------|
| Home/OPS/SIM/Documents | 없음 (기본 배경에 직접 배치) |
| CEP Builder/SIM | `px-6 py-4` |
| CEP Events | 없음 |

### 3.4 타이틀-설명 간격 불일치
| 페이지 | H1-설명 간격 |
|-------|----------------|
| Home, OPS, SIM, CEP Builder, CEP Events, Documents | 있음 |
| Admin Settings | 없음 (탭만 있음) |

### 3.5 버튼 영역 배치 불일치
| 페이지 | 버튼 배치 |
|-------|-----------|
| Home, OPS, SIM, Documents | 우측 (정렬) |
| CEP Events | 하단 라인 (정렬X) |

---

## 4. 하드코딩된 스타일 부분

### 4.1 고정 픽셀/값 사용
```tsx
// SIM Page
className="px-6 py-4"  // 하드코딩됨
className="border-b px-6 py-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
className="text-2xl font-semibold"  // 반복
className="mt-2 text-sm"
```

### 4.2 CSS 변수 직접 사용 (일부)
```tsx
// Settings Page
style={{ backgroundColor: "var(--surface-base)" }}  // OK
style={{ borderColor: "var(--border)" }}  // OK
```

---

## 5. 제안하는 일관성 표준

### 5.1 표준 페이지 헤더 컴포넌트

```tsx
// Standard Page Header (with border)
<header className="page-header">
  <div className="page-header-content">
    <div className="page-header-title-group">
      <h1 className="page-title">{title}</h1>
      <p className="page-description">{description}</p>
    </div>
    <div className="page-header-actions">
      {actions}
    </div>
  </div>
</header>
```

```css
/* globals.css */
.page-header {
  @apply border-b border-slate-200 bg-white px-6 py-4;
  .dark\:border-slate-800 .dark\:bg-slate-900;
}

.page-header-content {
  @apply flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between;
}

.page-header-title-group {
  @apply flex-1;
}

.page-title {
  @apply text-2xl font-semibold text-slate-900 dark:text-slate-50;
}

.page-description {
  @apply mt-2 text-sm text-slate-600 dark:text-slate-400;
}

.page-header-actions {
  @apply flex flex-wrap gap-2;
}

.page-header-actions > * {
  @apply flex-shrink-0;
}
```

### 5.2 박스 없는 페이지 헤더 (홈페이지 스타일)

```tsx
// Simple Page Header (no border)
<div className="page-section-header">
  <div className="page-header-content">
    <div className="page-header-title-group">
      <h1 className="page-title">{title}</h1>
      <p className="page-description">{description}</p>
    </div>
    <div className="page-header-actions">
      {actions}
    </div>
  </div>
</div>
```

```css
.page-section-header {
  @apply flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between px-6 py-6;
}

.page-section-header .page-title {
  @apply text-2xl font-semibold text-slate-900 dark:text-slate-50;
}

.page-section-header .page-description {
  @apply mt-2 text-sm text-slate-600 dark:text-slate-400;
}
```

### 5.3 Admin 페이지 헤더 (배너/탭 포함)

```tsx
// Admin Page Header (with tabs/banner)
<div className="admin-page-header">
  {/* Optional Banner */}
  {banner && <div className="admin-banner">{banner}</div>}

  <div className="admin-header-tabs">
    {tabs}
  </div>

  <div className="admin-header-info">
    {statusBadges}
  </div>
</div>
```

---

## 6. 일관성 작업 우선순위

### Phase 1: 헤더 컴포넌트 표준화 (높은 우선순위)
1. **표준 헤더 CSS 클래스 추가** (`globals.css`)
   - `.page-header`, `.page-title`, `.page-description`, `.page-header-actions`
   - `.page-section-header` (박스 없는 버전)
   - `.admin-page-header`, `.admin-banner`, `.admin-header-tabs`

2. **메인 페이지 헤더 통일**
   - Home, OPS, SIM, Documents, CEP Events → 표준 패턴 적용
   - CEP Builder, API Manager → 하단 구분선 추가

3. **Admin 페이지 헤더 통일**
   - Settings, Assets, Inspector, Tools 등 → 표준 Admin 패턴 적용

### Phase 2: 폰트/스타일 일관성
1. **헤더 하단 구분선 표준화**
   - 모든 페이지: `border-b` 추가 또는 통일된 없음
2. **패딩 표준화**
   - 메인: `px-6 py-4` 또는 `py-6` (container-section 기준)
   - Admin: 내부 섹션에 따름

### Phase 3: 설명 텍스트 가이드라인
1. **모든 설명에 `page-description` 클래스 적용**
2. **일관된 간격: `text-sm text-slate-600 dark:text-slate-400`

### Phase 4: 버튼 영역 표준화
1. **`page-header-actions` 클래스 사용**
2. **`flex gap-2` 간격 유지**

---

## 7. CSS 클래스 명명 규칙 제안

### 7.1 네이밍 규칙
```css
/* Layout */
.page-header {}
.page-header-content {}
.page-header-title-group {}
.page-header-actions {}

/* Typography */
.page-title {}
.page-description {}

/* Variants */
.page-header--with-border {} /* border-b가 있는 버전 */
.page-header--simple {}    /* border가 없는 간단한 버전 */
```

### 7.2 Admin 전용
```css
.admin-page-header {}
.admin-banner {}
.admin-header-tabs {}
.admin-header-status {}
```

---

## 8. 적용 대상 파일별 변경 사항

| 파일 | 현재 패턴 | 제안 변경 |
|------|----------|----------|
| `/app/page.tsx` | 패턴 A (기본) | 표준 `.page-section-header` 클래스 |
| `/app/ops/page.tsx` | 패턴 A | 표준 `.page-section-header` 클래스 |
| `/app/sim/page.tsx` | 패턴 D (border 있음) | border 제거하고 표준 패턴으로 |
| `/app/documents/page.tsx` | 패턴 A | 표준 `.page-section-header` 클래스 |
| `/app/cep-events/page.tsx` | 패턴 B (flex-wrap) | 표준 `.page-header` 클래스 |
| `/app/cep-builder/page.tsx` | 패턴 C (border + 배경) | 표준 `.page-header` 클래스로 |
| `/app/api-manager/page.tsx` | 분석 필요 | 표준 Admin 패턴 |
| `/app/admin/settings/page.tsx` | 패턴 E (탭 기반) | 표준 Admin 패턴 |
| `/app/admin/assets/page.tsx` | 로딩만 있음 | 표준 Admin 패턴 |
| `/app/admin/inspector/page.tsx` | 분석 필요 | 표준 Admin 패턴 |

---

## 9. 검토가 필요한 추가 항목

### 9.1 헤더 외 컴포넌트
- **서브 섹션 제목** (`h2`, `h3`) 일관성
- **버튼 그룹** (Primary, Secondary) 스타일 일관성
- **탭/필터** 스타일 일관성
- **테이블** 스타일 일관성

### 9.2 반응형 레이아웃
- **모바일** (320px 이하)에서 헤더 버튼 정렬 변경
- **태블릿** (768px 이하)에서 2단계 레이아웃

### 9.3 다크 모드
- 모든 헤더 스타일이 dark mode에서 자동으로 작동해야 함

---

## 10. 구현 로드맵

### Step 1: CSS 클래스 정의 (`globals.css`)
- `.page-header`, `.page-title`, `.page-description`
- `.page-header-actions`, `.page-header-content`
- `.page-section-header`, `.admin-page-header`

### Step 2: 메인 페이지 헤더 수정
- Home, OPS, SIM, Documents, CEP Events, CEP Builder
- 표준 클래스 적용, 하드코딩 제거

### Step 3: Admin 페이지 헤더 수정
- Settings, Assets, Inspector, API Manager, Tools
- Admin 전용 표준 적용

### Step 4: 검증 및 수정
- 각 페이지에서 레이아웃/다크모드 테스트
- 필요한 경우 미디어 쿼리 추가

---

## 11. 예시 코드

### Before (현재 SIM 페이지)
```tsx
<header className="border-b px-6 py-4 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
  <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
    SIM Workspace
  </h1>
  <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
    ...
  </p>
</header>
```

### After (제안)
```tsx
<header className="page-header">
  <div className="page-header-content">
    <div className="page-header-title-group">
      <h1 className="page-title">SIM Workspace</h1>
      <p className="page-description">
        질문과 가정값을 기반으로 계획을 검증한 뒤 실행합니다. 결과는 KPI 변화, 비교 차트, 피드백/모델 근거를 함께 제공합니다.
      </p>
    </div>
  </div>
</header>
```

---

## 12. 요약

### 주요 일관성 문제
1. **헤더 구조 불일치**: 5가지 다른 패턴 사용
2. **하드코딩된 스타일**: `px-6 py-4`, `text-2xl font-semibold` 반복
3. **하단 구분선 불일치**: 일부 페이지만 border-b 있음
4. **CSS 클래스 활용 부족**: 대부분이 인라인 Tailwind 클래스 사용

### 제안 해결책
1. **표준 헤더 CSS 클래스 정의**
2. **모든 페이지에 동일한 패턴 적용**
3. **다크모드 자동 지원** (CSS 변수 활용)
4. **Admin 페이지 전용 헤더 패턴**

### 기대 효과
- **일관된 사용자 경험**: 모든 페이지가 동일한 헤더 구조
- **유지보수 용이**: CSS 클래스로 중앙 관리
- **반응형 디자인**: 모바일/태블릿에서 자동 레이아웃

---

## 13. 다음 단계

1. **팀 리뷰**: 제안 방향에 동의하는지 확인
2. **Phase 1 구현**: CSS 클래스 정의 및 주요 페이지 적용
3. **Phase 2 구현**: Admin 페이지 표준화
4. **검증**: 각 브레이크포인트/디바이스에서 테스트
