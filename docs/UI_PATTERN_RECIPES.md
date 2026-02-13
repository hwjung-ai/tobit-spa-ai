# UI Pattern Recipes

> Project: tobit-spa-ai
> Scope: `apps/web` 실전 UI 구현 예시 모음
> Source of Truth: `docs/UI_DESIGN_SYSTEM_GUIDE.md`
> Last Updated: 2026-02-13

---

## 1. 문서 목적

이 문서는 디자인 시스템을 실제 화면에 적용할 때 바로 참고할 수 있는 **패턴/스니펫 레시피 모음**입니다.

원칙:
- 규칙/정책: `docs/UI_DESIGN_SYSTEM_GUIDE.md`
- 실전 예시/코드 조합: `docs/UI_PATTERN_RECIPES.md` (이 문서)

---

## 2. 빠른 인덱스

- 기본 페이지 골격
- Page Header
- 섹션/카드/패널 컨테이너
- 버튼/입력/배지
- 테이블 패턴
- 상태 배지/피드백
- Empty/Loading/Skeleton
- Splitter(Resizable Handle)
- ADMIN 레이아웃
- 폼 패턴
- UX 휴리스틱 체크
- 안티패턴

---

## 3. 기본 페이지 골격

```tsx
<div className="min-h-screen bg-surface-base text-foreground">
  <header className="border-b border-variant px-6 py-4">
    {/* header */}
  </header>
  <main className="min-h-[calc(100vh-96px)] w-full px-4 pb-16 pt-4 md:px-6 md:pb-4">
    {/* content */}
  </main>
</div>
```

---

## 4. Page Header 패턴

### 4.1 기본형

```tsx
<div className="space-y-2">
  <h1 className="text-2xl font-semibold text-foreground">Page Title</h1>
  <p className="text-sm text-muted-foreground">설명 텍스트</p>
</div>
```

**JSON Snippet:**
```json
{
  "id": "header_group",
  "type": "column",
  "props": {
    "gap": 1,
    "components": [
      { "id": "title", "type": "text", "props": { "content": "Page Title", "fontSize": "2xl", "fontWeight": "semibold" } },
      { "id": "desc", "type": "text", "props": { "content": "설명 텍스트", "fontSize": "sm", "variant": "muted" } }
    ]
  }
}
```

### 4.2 액션 포함형

```tsx
<div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
  <div className="space-y-2">
    <h1 className="text-2xl font-semibold text-foreground">Page Title</h1>
    <p className="text-sm text-muted-foreground">Page description</p>
  </div>
  <div className="flex flex-wrap items-center gap-2">
    <button className="btn-primary">Primary Action</button>
    <button className="br-btn border border-variant px-4 py-2 text-sm text-foreground hover:bg-surface-elevated">
      Secondary
    </button>
  </div>
</div>
```

---

## 5. 컨테이너 레시피

### 5.1 Section

```tsx
<section className="container-section">
  <h2 className="text-lg font-semibold text-foreground">Section Title</h2>
  <div className="mt-4 space-y-4">...</div>
</section>
```

**JSON Snippet:**
```json
{
  "id": "main_section",
  "type": "column",
  "label": "Section Title",
  "props": {
    "gap": 4,
    "components": [
      {
        "id": "section_title",
        "type": "text",
        "props": { "content": "Section Title", "fontSize": "lg", "fontWeight": "semibold" }
      }
    ]
  }
}
```

### 5.2 Card

```tsx
<div className="container-card">
  <h3 className="text-base font-semibold text-foreground">Card Title</h3>
  <p className="mt-2 text-sm text-muted-foreground">Card description</p>
</div>
```

### 5.3 Panel

```tsx
<div className="container-panel">
  <div className="space-y-4">...</div>
</div>
```

---

## 6. 버튼/입력/배지 레시피

### 6.1 버튼 변형

```tsx
// Primary
<button className="btn-primary">Save</button>

// Small Primary
<button className="btn-primary-small">Run</button>

// Secondary
<button className="br-btn border border-variant px-4 py-2 text-sm text-foreground hover:bg-surface-elevated">
  Cancel
</button>

// Destructive
<button className="br-btn bg-rose-600 px-4 py-2 text-sm text-white hover:bg-rose-500">
  Delete
</button>
```

**JSON Snippet:**
```json
[
  { "id": "save_btn", "type": "button", "props": { "label": "Save", "variant": "primary" } },
  { "id": "cancel_btn", "type": "button", "props": { "label": "Cancel", "variant": "outline" } }
]
```

### 6.2 입력

```tsx
<input className="input-container" placeholder="Type here..." />
<textarea className="input-container min-h-32" placeholder="Details..." />
<select className="input-container">
  <option>Option A</option>
</select>
```

### 6.3 배지

```tsx
<span className="br-badge bg-surface-elevated px-3 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
  Draft
</span>

<span className="br-badge bg-emerald-600 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white">
  Active
</span>
```

**JSON Snippet:**
```json
{ "id": "status_badge", "type": "badge", "props": { "label": "Active", "variant": "success" } }
```

---

## 7. 테이블 레시피

```tsx
<div className="container-card overflow-hidden">
  <table className="w-full text-xs">
    <thead>
      <tr className="border-b border-variant bg-surface-elevated">
        <th className="px-3 py-2 text-left font-semibold uppercase tracking-wider text-muted-foreground">
          Name
        </th>
        <th className="px-3 py-2 text-left font-semibold uppercase tracking-wider text-muted-foreground">
          Status
        </th>
      </tr>
    </thead>
    <tbody>
      <tr className="border-b border-variant hover:bg-surface-elevated">
        <td className="px-3 py-2 text-foreground">Asset A</td>
        <td className="px-3 py-2 text-muted-foreground">Published</td>
      </tr>
    </tbody>
  </table>
</div>
```

**JSON Snippet:**
```json
{
  "id": "asset_table",
  "type": "table",
  "props": {
    "rows": "{{state.assets}}",
    "columns": [
      { "field": "name", "header": "Name" },
      { "field": "status", "header": "Status" }
    ],
    "page_size": 10
  }
}
```

---

## 8. 상태 표시 레시피

### 8.1 상태 배지

| 상태 | 클래스 |
|---|---|
| Success | `bg-emerald-600 text-white` 또는 `bg-green-600 text-white` |
| Warning | `bg-amber-600 text-white` 또는 `bg-yellow-600 text-white` |
| Error | `bg-rose-600 text-white` 또는 `bg-red-600 text-white` |
| Info | `bg-sky-600 text-white` |
| Neutral | `bg-surface-elevated text-foreground border border-variant` |

### 8.2 인라인 메시지

```tsx
<div className="br-card border border-variant bg-surface-elevated px-4 py-3 text-sm text-muted-foreground">
  최근 배포가 완료되었습니다.
</div>

<div className="br-card border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
  연결에 실패했습니다. 네트워크 상태를 확인한 뒤 다시 시도하세요.
</div>
```

---

## 9. Empty / Loading / Skeleton 레시피

### 9.1 Empty

```tsx
<div className="flex flex-col items-center justify-center py-20 text-center">
  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-variant bg-surface-elevated" />
  <p className="text-sm font-medium text-foreground">No data found</p>
  <p className="mt-1 text-xs text-muted-foreground">Create your first item to get started</p>
  <button className="btn-primary mt-4">Create</button>
</div>
```

### 9.2 Loading

```tsx
<div className="flex flex-col items-center justify-center py-20">
  <div className="h-10 w-10 animate-spin rounded-full border-2 border-sky-500/20 border-t-sky-500" />
  <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Loading...</p>
</div>
```

### 9.3 Skeleton

```tsx
<div className="container-section">
  <div className="flex gap-4">
    <div className="h-10 w-40 animate-pulse rounded-lg bg-surface-elevated" />
    <div className="h-10 w-32 animate-pulse rounded-lg bg-surface-elevated" />
  </div>
  <div className="mt-4 h-44 animate-pulse rounded-xl bg-surface-elevated" />
</div>
```

---

## 10. Splitter 레시피

```tsx
<div
  className={cn("resize-handle-col", isResizing && "is-active")}
  role="separator"
  aria-orientation="vertical"
  aria-label="Resize panel"
>
  <div className="resize-handle-grip" />
</div>
```

규칙:
- 고정 폭 `w-2` 기준
- per-page 커스텀 hover 애니메이션 금지
- `.resize-handle-col` + `.resize-handle-grip` 조합 유지

---

## 11. 탭/선택 레시피

### 11.1 상위 내비게이션 탭 (Admin assets/tools/catalogs/screens)

```tsx
<button className={cn("nav-tab", isActive ? "nav-tab-active" : "nav-tab-inactive")}>
  Assets
</button>
```

### 11.2 인패널 탭 (Definition/Logic/Test 등)

```tsx
<button className={cn("panel-tab", active ? "panel-tab-active" : "panel-tab-inactive")}>
  Definition
</button>
```

### 11.3 선택 칩 (metric/event/schedule/anomaly)

```tsx
<button className={cn("choice-chip", selected ? "choice-chip-active" : "choice-chip-inactive")}>
  metric
</button>
```

---

## 12. ADMIN 페이지 레시피

```tsx
<div className="space-y-6">
  <div className="space-y-2">
    <h1 className="text-2xl font-semibold text-foreground">Admin Page</h1>
    <p className="text-sm text-muted-foreground">운영 설정과 리소스를 관리합니다.</p>
  </div>

  <section className="container-section">
    {/* filter/action controls */}
  </section>

  <section className="container-section">
    {/* table/form/content */}
  </section>
</div>
```

탭 그룹 예시:

```tsx
<div className="inline-flex rounded-xl border border-variant bg-surface-elevated p-1">
  <button className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white">
    All
  </button>
  <button className="rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:bg-surface-base">
    Draft
  </button>
</div>
```

---

## 13. 폼 레시피

```tsx
<form className="space-y-4">
  <div className="space-y-2">
    <label className="text-sm font-medium text-foreground">Name</label>
    <input className="input-container" />
    <p className="text-xs text-muted-foreground">최대 100자</p>
  </div>

  <div className="space-y-2">
    <label className="text-sm font-medium text-foreground">Description</label>
    <textarea className="input-container min-h-32" />
  </div>

  <div className="flex gap-2">
    <button type="submit" className="btn-primary">Save</button>
    <button type="button" className="br-btn border border-variant px-4 py-2 text-sm text-foreground hover:bg-surface-elevated">
      Cancel
    </button>
  </div>
</form>
```

---

## 14. UX 휴리스틱 체크(실무 버전)

- [ ] 로딩/처리 중 상태가 보이는가
- [ ] 사용자 용어(비전문 용어)로 라벨링되어 있는가
- [ ] 파괴적 액션에 취소/확인 플로우가 있는가
- [ ] 디자인 토큰/표준 패턴을 따르는가
- [ ] 제출 전 검증이 있는가
- [ ] 옵션/필터가 눈에 보이고 이해 가능한가
- [ ] 키보드 단축/포커스 동작이 일관적인가
- [ ] 화면이 과밀하지 않고 우선순위가 명확한가
- [ ] 에러 메시지에 원인과 다음 행동이 있는가
- [ ] 빈 상태에서 다음 행동 CTA를 제공하는가

---

## 15. 안티패턴 모음

### 14.1 className 템플릿 리터럴 남용

```tsx
// Bad
<div className={`base ${active ? "on" : ""} ${disabled ? "opacity-50" : ""}`} />

// Good
<div className={cn("base", active && "on", disabled && "opacity-50")} />
```

### 14.2 임의값 남용

```tsx
// Bad
<div className="text-[11px] rounded-[7px] tracking-[0.23em]" />

// Good
<div className="text-xs rounded-lg tracking-wider" />
```

### 14.3 다크 모드 하드코딩

```tsx
// Bad
<div className="bg-slate-950 text-slate-100" />

// Good
<div className="bg-surface-base text-foreground" />
```

### 14.4 계층 없는 타이포

```tsx
// Bad
<h1 className="text-sm">Title</h1>
<p className="text-sm">Body</p>

// Good
<h1 className="text-2xl font-semibold">Title</h1>
<p className="text-sm">Body</p>
```

---

## 16. 클래스 빠른 참조

| 목적 | 우선 클래스 |
|---|---|
| 섹션 컨테이너 | `container-section` |
| 카드 컨테이너 | `container-card` |
| 대형 패널 | `container-panel` |
| 기본 입력 | `input-container` |
| 코드 블록 | `code-block`, `code-block-lg` |
| 버튼(주요) | `btn-primary`, `btn-primary-small` |
| 경계선 | `border-variant` |
| 기본 배경 | `bg-surface-base` |
| 상승 배경 | `bg-surface-elevated` |
| 오버레이 배경 | `bg-surface-overlay` |
| 기본 텍스트 | `text-foreground` |
| 보조 텍스트 | `text-muted-foreground` |
| tiny 라벨 | `text-tiny` |
| 대문자 간격 | `tracking-wider` |
| 상위 탭 | `nav-tab`, `nav-tab-active`, `nav-tab-inactive` |
| 인패널 탭 | `panel-tab`, `panel-tab-active`, `panel-tab-inactive` |
| 선택 칩 | `choice-chip`, `choice-chip-active`, `choice-chip-inactive` |

---

## 17. 관련 문서

- 정책 정본: `docs/UI_DESIGN_SYSTEM_GUIDE.md`
- 구현 토큰: `apps/web/src/app/globals.css`
- TS 토큰: `apps/web/src/lib/design-tokens.ts`
- 테스트 구조: `docs/TESTING_STRUCTURE.md`
