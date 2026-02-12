# UI Design System Guide

> Project: tobit-spa-ai
> Framework: Next.js 16 + React 19 + Tailwind CSS 4 + Radix UI
> Last Updated: 2026-02-12 (Phase 1-6: Complete UI Consistency Standardization)

---

## 📋 Table of Contents

1. [Consistency Fixes Applied](#consistency-fixes-applied)
2. [Standard Patterns](#standard-patterns)
3. [Color System](#color-system)
4. [Typography](#typography)
5. [Spacing & Layout](#spacing--layout)
6. [Component Patterns](#component-patterns)
7. [Dark Mode](#dark-mode)
8. [Code Style Guidelines](#code-style-guidelines)
9. [Universal Page Standards](#universal-page-standards)
10. [ADMIN Page Standards](#admin-page-standards)
11. [Visual Hierarchy Guidelines](#visual-hierarchy-guidelines) 🆕
12. [Common Anti-Patterns](#common-anti-patterns) 🆕
13. [Migration Checklist](#migration-checklist)

---

## ✅ Consistency Fixes Applied (Phase 1-7)

### Files Modified (2026-02-12)

**Phase 7 (Admin Pages Inline Styles → CSS Classes):**
- ✅ `RegressionWatchPanel.tsx` - Convert all inline styles to CSS classes
- ✅ `admin/layout.tsx` - Navigation tabs use cn() utility
- ✅ `admin/settings/page.tsx` - Alert banners and table use CSS classes
- ✅ `AssetTable.tsx` - Loading/empty states use CSS classes
- ✅ `ui/label.tsx` - Remove inline color style
- ✅ `admin/regression/page.tsx` - Fix Suspense fallback styling

**Phase 3-4 (Border Radius & Background Colors):**
- ✅ `/apps/web/src/app/globals.css` - Added border-radius & background standard classes
  - `.br-badge`, `.br-btn`, `.br-card`, `.br-section`, `.br-panel`
  - `.bg-surface-base`, `.bg-surface-overlay`, `.bg-surface-elevated`
  - `.container-card`, `.container-section`, `.container-panel`
  - `.input-container`, `.code-block`, `.code-block-lg`

**Phase 5 (Apply Consistency Classes):**
- ✅ `/apps/web/src/app/sim/page.tsx` - Applied `.container-section`, `.br-card`
- ✅ `/apps/web/src/app/ops/page.tsx` - Applied `.container-section`, `.br-card`
- ✅ `/apps/web/src/app/page.tsx` - Applied `.container-section`
- ✅ `/apps/web/src/app/documents/page.tsx` - Applied `.container-section`
- ✅ `/apps/web/src/app/login/page.tsx` - Applied `.container-panel`
- ✅ `/apps/web/src/app/cep-events/page.tsx` - Applied `.br-section`
- ✅ `/apps/web/src/app/cep-builder/page.tsx` - Applied `.br-card`

**Phase 6 (Inspector Page Hierarchy):**
- ✅ `/apps/web/src/app/admin/inspector/page.tsx` - Applied inspector-specific classes
  - `.insp-h1`, `.insp-h2`, `.insp-h3` - Heading hierarchy
  - `.insp-body`, `.insp-body-secondary` - Body text hierarchy
  - `.insp-label`, `.insp-label-small` - Label styles
  - `.insp-section` - Section containers
  - `.insp-input` - Input fields
  - `.insp-button` - Primary buttons
  - `.insp-mono` - Monospace text

**Phase 1-2 (Primary Colors & Letter Spacing):**
- ✅ `/apps/web/src/app/globals.css` - Added consistency utility classes (btn-primary, text-label, etc.)
- ✅ `/apps/web/src/app/documents/page.tsx` - Primary colors + letter spacing standardized
- ✅ `/apps/web/src/app/sim/page.tsx` - Primary colors + letter spacing standardized
- ✅ `/apps/web/src/app/ops/page.tsx` - Primary colors + letter spacing standardized
- ✅ `/apps/web/src/app/cep-events/page.tsx` - Letter spacing standardized
- ✅ `/apps/web/src/app/api-manager/page.tsx` - Letter spacing standardized
- ✅ `/apps/web/src/app/admin/settings/page.tsx` - Letter spacing standardized
- ✅ `/apps/web/src/app/layout.tsx` - Header background + letter spacing
- ✅ `/apps/web/src/components/admin/CreateAssetModal.tsx` - Primary color dark mode added
- ✅ `/apps/web/src/components/admin/CreateToolModal.tsx` - Primary color dark mode added
- ✅ `/apps/web/src/components/admin/SourceAssetForm.tsx` - Primary color dark mode added
- ✅ `/apps/web/src/components/admin/AssetForm.tsx` - Primary color dark mode added
- ✅ `/apps/web/src/components/admin/CreateCatalogModal.tsx` - Primary color dark mode added
- ✅ `/apps/web/src/app/admin/inspector/page.tsx` - Inspector page hierarchy + consistency fixed
- ✅ `/apps/web/src/components/admin/screen-editor/ScreenEditorTabs.tsx` - Letter spacing standardized
- ✅ `/apps/web/src/components/api-manager/WorkflowBuilder.tsx` - Primary colors standardized
- ✅ `/apps/web/src/components/api-manager/PythonBuilder.tsx` - Primary colors standardized
- ✅ `/apps/web/src/components/simulation/FunctionBrowser.tsx` - Letter spacing standardized
- ✅ `/apps/web/src/components/answer/UIScreenRenderer.tsx` - Letter spacing standardized

**Phase 0 (Previous - Inline Styles):**
- ✅ `globals.css` - Component-specific CSS variables added
- ✅ `FormSection.tsx` - 100% 클래스 기반
- ✅ `FormFieldGroup.tsx` - 100% 클래스 기반
- ✅ `DraftAssistantPanel.tsx` - 99+ inline styles 제거
- ✅ SQLQueryBuilder, WorkflowBuilder, PythonBuilder - inline styles 제거
- ✅ CEP Form Builder (11개 파일) - inline styles 제거

### Key Changes

**Phase 3-4 (Border Radius & Background Colors):**
1. **Border Radius Standardization**
   - `.br-badge` - `rounded-full` (badges, pills)
   - `.br-btn` - `rounded-lg` (buttons)
   - `.br-card` - `rounded-xl` (cards)
   - `.br-section` - `rounded-2xl` (sections)
   - `.br-panel` - `rounded-3xl` (large panels)

2. **Background Color Standardization**
   - `.bg-surface-base` - Primary surface (white/slate-950)
   - `.bg-surface-overlay` - Overlay surface (slate-50/slate-950/50)
   - `.bg-surface-elevated` - Elevated surface (slate-100/slate-900/40)

3. **Container Classes** (Combined border-radius + background)
   - `.container-card` - Card container (`.br-card` + surface styles)
   - `.container-section` - Section container (`.br-section` + surface styles)
   - `.container-panel` - Panel container (`.br-panel` + surface styles)

4. **Input & Code Block Classes**
   - `.input-container` - Standard input field with consistent styling
   - `.code-block` - Code block with max-height: 12rem
   - `.code-block-lg` - Large code block with max-height: 20rem

**Phase 1-2 (Primary Colors & Letter Spacing):**
1. **Primary Color Standardization**
   - All primary buttons now use `bg-sky-600` (not `bg-sky-500`)
   - Hover states use `hover:bg-sky-500` (not `hover:bg-sky-400`)
   - Dark mode: `dark:bg-sky-700 dark:hover:bg-sky-600`

2. **Letter Spacing Standardization**
   - All uppercase labels now use `tracking-wider` (not `tracking-[0.3em]`, `tracking-[0.2em]`, etc.)
   - Removed hardcoded letter-spacing values
   - Consistent `tracking-wider` for all uppercase labels, badges, buttons

3. **New CSS Utility Classes** (globals.css)
   - `.btn-primary` - Standard primary button
   - `.btn-primary-small` - Small primary button
   - `.btn-secondary` - Standard secondary button
   - `.badge-primary`, `.badge-active` - Badge styles
   - `.text-label`, `.text-label-sm`, `.text-label-normal` - Label text styles
   - `.tab-button`, `.tab-button-active`, `.tab-button-inactive` - Tab styles
   - `.page-section` - Standard page section
   - `.input-standard` - Standard input field
   - `.text-primary`, `.text-muted-standard`, `.text-disabled` - Text colors

4. **Dark Mode Support**
   - All pages now support light/dark mode
   - Pattern: `dark:` prefix for dark variants

---

## 🎨 Standard Patterns

### Utility Function Pattern

**Always use `cn()` for className merging:**

```typescript
import { cn } from "@/lib/utils";

// ✅ Good
const MyComponent = ({ className, ...props }) => (
  <div className={cn("base-styles", className)} {...props} />
);

// ❌ Bad - template literals
const BadComponent = ({ className }) => (
  <div className={`base-styles ${className ?? ''}`} />
);
```

### Dark Mode Pattern

**Always use `dark:` prefix for dark variants:**

```typescript
// ✅ Good - explicit dark mode
className="bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50"

// ❌ Bad - dark mode hardcoded
className="bg-slate-950 text-slate-100"
```

---

## 🎨 Color System

### Primary Colors (Slate Scale)

| Usage | Light Mode | Dark Mode |
|-------|------------|-----------|
| **Background** | `bg-white` | `dark:bg-slate-950` |
| **Background (elevated)** | `bg-slate-50` | `dark:bg-slate-900` |
| **Foreground** | `text-slate-900` | `dark:text-slate-50` |
| **Muted Foreground** | `text-slate-600` | `dark:text-slate-400` |
| **Border** | `border-slate-200` | `dark:border-slate-800` |
| **Border (muted)** | `border-slate-300` | `dark:border-slate-700` |

### Accent Colors

| Purpose | Color | Usage |
|---------|-------|-------|
| **Primary** | `bg-sky-600` | Default buttons, links |
| **Primary Hover** | `hover:bg-sky-500` | Interactive states |
| **Destructive** | `bg-rose-600` | Error badges, delete buttons |
| **Success** | `bg-emerald-600` | Success states |
| **Warning** | `bg-amber-600` | Warning states |

### Focus Ring

```css
focus-visible:outline-none
focus-visible:ring-2
focus-visible:ring-sky-500
dark:focus-visible:ring-sky-400
```

---

## 📝 Typography

### Font Sizes

| Size | Class | Usage |
|------|-------|-------|
| **10px** | `text-[10px]` | Tiny labels, badges |
| **xs** | `text-xs` | Small labels, secondary text |
| **sm** | `text-sm` | Descriptions, secondary text |
| **base** | `text-base` | Body content, inputs |
| **lg** | `text-lg` | Section titles, dialog titles |
| **2xl** | `text-2xl` | Page headings |

### Font Weights

| Weight | Class | Usage |
|--------|-------|-------|
| **Normal** | `font-normal` | Body text (default) |
| **Semibold** | `font-semibold` | Titles, headings |
| **Bold** | `font-bold` | Emphasis |

### Letter Spacing

| Usage | Class |
|-------|-------|
| **Normal** | (default) |
| **Wide/Uppercase** | `tracking-wider` | Labels, uppercase text |

---

## 📐 Spacing & Layout

### Standard Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| **2** | 8px | Tight gaps (`gap-2`) |
| **3** | 12px | Compact gaps (`gap-3`) |
| **4** | 16px | Default gaps (`gap-4`) |
| **5** | 20px | Section padding (`p-5`) |
| **6** | 24px | Large gaps (`gap-6`) |

### Common Patterns

```typescript
// Page section padding
"p-5"           // 20px - page sections

// Button padding (default)
"px-6 py-3"     // 24px 12px - primary buttons
"px-4 py-2"     // 16px 8px - secondary buttons

// Input padding
"px-4 py-3"     // 16px 12px - inputs

// Flex gaps
"gap-2"      // 8px - tight spacing
"gap-3"      // 12px - compact spacing
"gap-4"      // 16px - default spacing
"gap-6"      // 24px - section spacing
```

---

## 🧩 Component Patterns

### Page Section

```typescript
<section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Section Title</h2>
  {/* content */}
</section>
```

**Styles:**
- Container: `rounded-2xl border shadow-sm`
- Padding: `p-5` (20px)
- Light: `bg-white border-slate-200`
- Dark: `dark:bg-slate-900/90 dark:border-slate-800`

### Button

**Variants:**
- Primary: `bg-sky-600 text-white hover:bg-sky-500`
- Secondary: `border border-slate-300 text-slate-700 hover:border-slate-400 dark:border-slate-700 dark:text-slate-300`

**Sizes:**
- Default: `px-6 py-3 text-sm`
- Small: `px-4 py-2 text-sm`

### Input

```typescript
<input
  className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-base outline-none transition focus:border-sky-500 dark:border-slate-700 dark:bg-slate-950/50 dark:text-white dark:focus:border-sky-400"
/>
```

---

## 🌙 Dark Mode

### Implementation Pattern

```typescript
// Always pair light and dark variants
className={cn(
  "bg-white text-slate-900",           // Light mode
  "dark:bg-slate-950 dark:text-slate-50" // Dark mode
)}
```

### Dark Mode Colors

| Element | Light | Dark |
|---------|--------|------|
| Background | `bg-white` | `dark:bg-slate-950` |
| Text | `text-slate-900` | `dark:text-slate-50` |
| Muted Text | `text-slate-600` | `dark:text-slate-400` |
| Border | `border-slate-200` | `dark:border-slate-800` |
| Elevated BG | `bg-slate-50` | `dark:bg-slate-900` |

---

## 📝 Code Style Guidelines

### 1. Always use `cn()` utility

```typescript
// ✅ Good
import { cn } from "@/lib/utils";
className={cn("base-styles", className)}

// ❌ Bad
className={`base-styles ${className}`}
```

### 2. Dark mode first approach

```typescript
// ✅ Good - start with light, add dark variants
className="bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50"

// ❌ Bad - assume dark mode only
className="bg-slate-950 text-slate-100"
```

### 3. Border radius consistency

```typescript
// ✅ Good - consistent sizing
rounded-2xl   // Page sections
rounded-md     // Buttons, inputs
rounded-lg     // Cards

// ❌ Bad - mixed sizes without reason
rounded-3xl | rounded-2xl | rounded-xl | rounded-full (mixed arbitrarily)
```

### 4. Forward refs for composite components

```typescript
// ✅ Good
const Component = React.forwardRef<HTMLDivElement, Props>(
  (props, ref) => <div ref={ref} {...props} />
);
Component.displayName = "Component";
```

---

## ✅ Migration Checklist

Use this checklist when updating components:

- [ ] Use `cn()` for className merging
- [ ] Add `dark:` variants for all colors
- [ ] Use consistent border radius (`rounded-2xl` for sections, `rounded-md` for buttons)
- [ ] Use consistent text colors (`text-slate-900/50` for primary, `text-slate-600/400` for muted)
- [ ] Use consistent borders (`border-slate-200` for light, `border-slate-800` for dark)
- [ ] Add focus states for interactive elements

---

## 🧠 UX Heuristics: Nielsen's 10 Usability Principles

Industry-standard UX guidelines to apply alongside the design system.

### 1. Visibility of System Status

**Keep users informed about what is going on**

```typescript
// ✅ Good - Loading states visible
<button disabled={loading}>
  {loading ? <Spinner /> : "Submit"}
</button>

// ✅ Good - Progress indicator for long operations
<ProgressBar value={progress} max={100} />

// ✅ Good - Toast notifications for async results
<Toast>{status}</Toast>
```

### 2. Match Between System and Real World

**Use familiar concepts and language**

```typescript
// ❌ Bad - Technical jargon
<button>Execute CRUD Operation</button>

// ✅ Good - User's language
<button>Create Item</button>
```

### 3. User Control and Freedom

**Provide undo/redo and easy exit**

```typescript
// ✅ Good - Cancel/confirm for destructive actions
<AlertDialog>
  <AlertDialogTrigger>Delete</AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogTitle>Are you sure?</AlertDialogTitle>
    <AlertDialogAction>Cancel</AlertDialogAction>
    <AlertDialogAction>Delete</AlertDialogAction>
  </AlertDialogContent>
</AlertDialog>

// ✅ Good - Escape to dismiss modals
// ✅ Good - Back button in multi-step forms
```

### 4. Consistency and Standards

**Use design tokens and established patterns**

```typescript
// ✅ Good - Consistent with design system
import { buttonVariants } from "@/components/ui/button";
className={buttonVariants({ variant: "default" })}

// ❌ Bad - Inconsistent styling
className="px-3 py-1.5 bg-blue-500 rounded" // Non-standard
```

### 5. Error Prevention

**Validate before submission, provide constraints**

```typescript
// ✅ Good - Form validation
<input
  type="email"
  required
  pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"
  onInvalid={(e) => e.target.setCustomValidity("Please enter a valid email")}
/>

// ✅ Good - Disabled state while invalid
<SubmitButton disabled={!form.isValid} />

// ✅ Good - Confirmation for destructive actions
```

### 6. Recognition Rather Than Recall

**Make options visible, minimize memory load**

```typescript
// ✅ Good - Visible filters
<FilterGroup>
  <FilterOption label="Active" />
  <FilterOption label="Archived" />
  <FilterOption label="Draft" />
</FilterGroup>

// ✅ Good - Help text and placeholders
<input placeholder="Search by name or email..." />
<p className="text-xs text-muted-foreground">
  Supports wildcards: *.example.com
</p>
```

### 7. Flexibility and Efficiency of Use

**Support power users with shortcuts**

```typescript
// ✅ Good - Keyboard shortcuts
<div onKeyDown={(e) => {
  if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    openCommandPalette();
  }
}} />

// ✅ Good - Sensible defaults
<select defaultValue="last-30-days">
  <option value="last-7-days">Last 7 days</option>
  <option value="last-30-days">Last 30 days</option>
  <option value="custom">Custom range</option>
</select>
```

### 8. Aesthetic and Minimalist Design

**Remove clutter, focus on essentials**

```typescript
// ❌ Bad - Everything visible at once
<div>
  <Button>Edit</Button>
  <Button>Delete</Button>
  <Button>Share</Button>
  <Button>Duplicate</Button>
  <Button>Export</Button>
</div>

// ✅ Good - Primary action, secondary in dropdown
<div className="flex gap-2">
  <Button>Edit</Button>
  <DropdownMenu>
    <DropdownMenuTrigger>More</DropdownMenuTrigger>
    <DropdownMenuContent>
      <DropdownMenuItem>Delete</DropdownMenuItem>
      <DropdownMenuItem>Share</DropdownMenuItem>
      <DropdownMenuItem>Duplicate</DropdownMenuItem>
      <DropdownMenuItem>Export</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</div>
```

### 9. Help Users Recogn Errors

**Clear error messages with solutions**

```typescript
// ❌ Bad - Cryptic error
<ErrorMessage>ERR_CONNECTION_REFUSED</ErrorMessage>

// ✅ Good - Actionable error message
<Alert variant="destructive">
  <AlertTitle>Connection Failed</AlertTitle>
  <AlertDescription>
    Unable to connect to the server. Please check your network connection
    and try again. If the problem persists, contact support.
  </AlertDescription>
</Alert>
```

### 10. Help and Documentation

**Guidance for first-time users**

```typescript
// ✅ Good - Empty state with guidance
{items.length === 0 && (
  <EmptyState
    icon={FileIcon}
    title="No documents yet"
    description="Create your first document to get started"
    action={<Button>Create Document</Button>}
  />
)}

// ✅ Good - Tooltips for icon-only buttons
<Button>
  <Tooltip content="Copy to clipboard">
    <CopyIcon />
  </Tooltip>
</Button>
```

### UX Checklist

Use this checklist when implementing features:

- [ ] **H1**: Loading/spinner states for async operations
- [ ] **H2**: Labels use user's language (not technical terms)
- [ ] **H3**: Cancel/undo/escape available for destructive actions
- [ ] **H4**: Uses design system tokens and patterns
- [ ] **H5**: Form validates before submission
- [ ] **H6**: Options visible with clear labels
- [ ] **H7**: Keyboard shortcuts documented (Esc, Cmd+K, etc.)
- [ ] **H8**: Minimal UI, clear visual hierarchy
- [ ] **H9**: Error messages explain problem + solution
- [ ] **H10**: Empty states guide next action

---

## 📚 References

- [Tailwind CSS 4 Docs](https://tailwindcss.com/docs)
- [Radix UI Primitives](https://www.radix-ui.com/primitives)
- [Class Variance Authority](https://cva.style/docs)
- [Design Tokens](/apps/web/src/lib/design-tokens.ts)
- [Nielsen's 10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) - Industry standard UX principles

## 🏢 ADMIN Page Standards

### Page Layout

All ADMIN pages follow this standard structure:

\`\`\`typescript
<div className="space-y-6">
  {/* Page Header */}
  <div>
    <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Page Title</h1>
    <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
      Page description and context
    </p>
  </div>

  {/* Control Bar (Optional) */}
  <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
    {/* Filters, actions, etc. */}
  </section>

  {/* Content Area */}
  <section className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
    {/* Main content */}
  </section>
</div>
\`\`\`

### Button Group Standards

Tab buttons and filter groups:

\`\`\`typescript
// ✅ Good - Consistent tab group
<div className="inline-flex rounded-xl border border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-950/70 p-1">
  <button
    className={cn(
      "px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.15em] transition rounded-lg",
      activeTab === "all"
        ? "bg-sky-600 text-white"
        : "bg-transparent text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"
    )}
  >
    All
  </button>
  <button>...</button>
  <button>...</button>
</div>
\`\`\`

### Table Standards

Data tables with consistent styling:

\`\`\`typescript
<table className="w-full text-[11px]">
  <thead>
    <tr className="border-b border-slate-300 dark:border-slate-800">
      <th className="px-3 py-2 text-left font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
        Column Name
      </th>
    </tr>
  </thead>
  <tbody>
    <tr className="border-b border-slate-200 dark:border-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800/30">
      <td className="px-3 py-2 text-slate-700 dark:text-slate-400">
        Cell Value
      </td>
    </tr>
  </tbody>
</table>
\`\`\`

### Loading Skeleton Standards

Consistent loading patterns:

\`\`\`typescript
// ✅ Good - Follows page section standard
<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
  <div className="flex gap-6">
    <div className="h-10 w-40 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
    <div className="h-10 w-40 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
  </div>
  <div className="h-10 w-32 animate-pulse rounded-xl bg-sky-600" />
</div>
\`\`\`

### Status Indicators

Consistent status colors:

| Status | Background | Text | Border |
|--------|------------|------|--------|
| Success | \`bg-emerald-600\` | \`text-white\` | - |
| Warning | \`bg-amber-600\` | \`text-white\` | - |
| Error | \`bg-rose-600\` | \`text-white\` | - |
| Info | \`bg-sky-600\` | \`text-white\` | - |
| Neutral | \`bg-slate-200\` | \`text-slate-700\` | \`border-slate-300\` (dark: \`bg-slate-800 dark:text-slate-300\`) |

### ADMIN Page Checklist

Use this checklist for ADMIN pages:

- [ ] Page header with title (\`text-2xl\`) and description (\`text-sm\`)
- [ ] Control bar uses \`rounded-2xl border bg-white p-5 dark:bg-slate-900/90\`
- [ ] Content area uses \`rounded-2xl border bg-white shadow-sm dark:bg-slate-900/90\`
- [ ] Buttons follow standard variants (Primary, Secondary, etc.)
- [ ] Tables use consistent border colors (\`border-slate-200\` / \`dark:border-slate-800\`)
- [ ] Loading skeletons follow page section pattern
- [ ] All text has dark mode variants

## 🌐 Universal Page Standards

### All Page Layout

Applies to ALL pages (Main, OPS, SIM, ADMIN, etc.):

```typescript
<div className="min-h-screen bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50">
  <header className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
    {/* Header content */}
  </header>
  <main className="min-h-[calc(100vh-96px)] w-full px-4 pb-16 pt-4 md:px-6 md:pb-4">
    {/* Page content */}
  </main>
</div>
```

### Universal Card/Section

All content sections use this pattern:

```typescript
// Option 1: Use standardized container class (Phase 3-4)
<section className="container-section">
  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Title</h2>
  {/* Content */}
</section>

// Option 2: Use utility classes directly
<section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Title</h2>
  {/* Content */}
</section>
```

### Universal Input

All form inputs follow this pattern:

```typescript
// Option 1: Use standardized input class (Phase 3-4)
<input className="input-container" />

// Option 2: Use utility classes directly
<input
  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-base outline-none transition focus:border-sky-500 dark:border-slate-700 dark:bg-slate-950/50 dark:text-white dark:focus:border-sky-400"
/>
```

### Universal Button Standards

All buttons follow these variants:

| Variant | Classes |
|---------|----------|
| Primary | `bg-sky-600 text-white hover:bg-sky-500 dark:bg-sky-700` |
| Secondary | `border border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800` |
| Destructive | `bg-rose-600 text-white hover:bg-rose-500 dark:bg-rose-900` |
| Ghost | `hover:bg-slate-100 text-slate-700 dark:hover:bg-slate-800 dark:text-slate-300` |

### Universal Text Standards

All text follows these rules:

| Element | Light | Dark |
|----------|--------|--------|
| Heading (h1) | `text-slate-900` | `dark:text-slate-50` |
| Heading (h2) | `text-slate-900` | `dark:text-white` |
| Heading (h3) | `text-slate-900` | `dark:text-white` |
| Body (p) | `text-slate-900` | `dark:text-slate-50` |
| Muted (secondary) | `text-slate-600` | `dark:text-slate-400` |
| Disabled | `text-slate-400` | `dark:text-slate-600` |

### Universal Form Standards

All forms follow these patterns:

```typescript
// ✅ Good - Consistent form layout
<form className="space-y-4">
  <div className="space-y-2">
    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Field Name</label>
    <input className="w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-base outline-none transition focus:border-sky-500 dark:border-slate-700 dark:bg-slate-950/50 dark:text-white dark:focus:border-sky-400" />
  </div>
</form>
```

### Empty State Standards

All empty states follow this pattern:

```typescript
<div className="flex flex-col items-center justify-center py-20">
  <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4 border border-slate-300 dark:bg-slate-800 dark:border-slate-700">
    {/* Icon */}
  </div>
  <p className="text-slate-700 dark:text-slate-400 text-sm font-medium">No data found</p>
  <p className="text-slate-500 dark:text-slate-500 text-xs">Create your first item to get started</p>
</div>
```

### Loading State Standards

All loading states follow this pattern:

```typescript
<div className="flex flex-col items-center justify-center py-20">
  <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
  <p className="text-slate-600 dark:text-slate-400 text-xs font-bold uppercase tracking-widest">Loading...</p>
</div>
```

---

## 🎨 Visual Hierarchy Guidelines 🆕

### Purpose
Create clear visual hierarchy through consistent sizing, spacing, and contrast. Users should instantly understand:
- What is most important (primary actions)
- What is related (grouped content)
- What is secondary (metadata, timestamps)

### Visual Hierarchy Levels

| Level | Size | Spacing | Usage | Example |
|--------|------|----------|-------|---------|
| **H1 (Page Heading)** | `text-2xl` (24px) | Large | Page titles, hero sections | "Create API Asset" |
| **H2 (Section Title)** | `text-lg` (18px) | Medium-Large | Section headers, card titles | "Basic Information" |
| **H3 (Subsection)** | `text-base` (16px) | Medium | Subsection titles | "Request Parameters" |
| **Body (Primary)** | `text-sm` (14px) | Default | Main content, descriptions | Default paragraph text |
| **Body (Secondary)** | `text-xs` (12px) | Compact | Labels, timestamps, metadata | "Updated 2 hours ago" |
| **Tiny (Labels)** | `text-[10px]` (10px) | Minimal | Status badges, tiny tags | "PROD", "v2.1" |

### Hierarchy Guidelines

1. **Font Size Steps**
   - Always use at least 2 steps between hierarchy levels
   - Never jump from `text-2xl` to `text-xs` directly
   - Example: `text-2xl` → `text-lg` → `text-base` → `text-sm` → `text-xs`

2. **Contrast Requirements**
   - Page headings: `text-slate-900` / `dark:text-slate-50` (strongest)
   - Section titles: `text-slate-900` / `dark:text-white`
   - Body text: `text-slate-700` / `dark:text-slate-300`
   - Secondary text: `text-slate-500` / `dark:text-slate-400`
   - Disabled text: `text-slate-400` / `dark:text-slate-600`

3. **Spacing Hierarchy**
   - Page sections: `p-5` (20px padding)
   - Card content: `p-4` (16px padding)
   - Dense content: `p-3` (12px padding)
   - Tight groups: `space-y-2` (8px gaps)
   - Default: `space-y-4` (16px gaps)

4. **Interactive Element Hierarchy**
   - Primary buttons: `bg-sky-600 hover:bg-sky-500` (most prominent)
   - Secondary actions: `border border-slate-300 hover:bg-slate-100` (less prominent)
   - Ghost buttons: `hover:bg-slate-100 dark:hover:bg-slate-800` (subtle)
   - Links: `text-sky-600 hover:text-sky-500 dark:text-sky-400`

5. **Border Radius Hierarchy** (Phase 3 Standardized)
   - Panels (large containers): `rounded-3xl` (24px) - `.br-panel`
   - Page sections: `rounded-2xl` (16px) - `.br-section`
   - Cards: `rounded-xl` (12px) - `.br-card`
   - Buttons: `rounded-lg` (8px) - `.br-btn`
   - Badges/Tags: `rounded-full` - `.br-badge`

---

## 🚫 Common Anti-Patterns 🆕

### Purpose
Identify and avoid common UI/UX mistakes that reduce clarity and consistency.

### 1. Magic Numbers in Styles

❌ **Bad**:
```typescript
// Arbitrary values without clear purpose
<div style={{ padding: "13px", fontSize: "11.5px" }}>
<button className="px-3.5 py-1.5 rounded-[7px]">
```

✅ **Good**:
```typescript
// Use design tokens or standard Tailwind classes
<div className="p-4">  // 16px standard
<div className="p-5">  // 20px page section
<button className="px-6 py-3">  // 24px 12px standard
<button className="px-4 py-2">  // 16px 8px small
<button className="px-3 py-1.5 text-xs rounded-full">  // tiny button with badge
```

### 2. Inconsistent Hierarchy

❌ **Bad**:
```typescript
// All text same size, no clear hierarchy
<h1 className="text-sm">Title</h1>
<p className="text-sm">Body text</p>
<span className="text-sm">Label</span>
```

✅ **Good**:
```typescript
// Clear visual hierarchy
<h1 className="text-2xl font-semibold">Page Title</h1>
<h2 className="text-lg font-semibold">Section Title</h2>
<h3 className="text-base font-medium">Subsection</h3>
<p className="text-sm">Body content</p>
<span className="text-xs">Secondary label</span>
```

### 3. Border Radius Soup

❌ **Bad**:
```typescript
// Mixed border radius without clear purpose
<div className="rounded-sm rounded-xl rounded-2xl">
<button className="rounded-md rounded-full rounded-lg">
```

✅ **Good**:
```typescript
// Consistent border radius by element type (Phase 3 standardized)
<section className="br-section">     {/* page sections - rounded-2xl */}
<div className="br-card">            {/* cards - rounded-xl */}
<button className="br-btn">          {/* buttons - rounded-lg */}
<input className="br-btn">           {/* inputs - rounded-lg */}
<span className="br-badge">          {/* badges - rounded-full */}
```

Or use utility classes directly:
```typescript
<section className="rounded-2xl">    {/* page sections */}
<div className="rounded-xl">          {/* cards */}
<button className="rounded-lg">       {/* buttons */}
<span className="rounded-full">       {/* badges */}
```

### 4. Color Chaos

❌ **Bad**:
```typescript
// Random colors without semantic meaning
<span style={{ color: "#a83f39" }}>
<button className="bg-blue-500 bg-green-600 bg-purple">
```

✅ **Good**:
```typescript
// Semantic color tokens (Phase 3-4 standardized)
<span className="text-slate-900 dark:text-slate-50">  {/* primary text */}
<span className="text-slate-600 dark:text-slate-400">  {/* muted text */}
<div className="bg-surface-base">  {/* surface - white/slate-950 */}
<div className="bg-surface-overlay">  {/* overlay - slate-50/slate-950/50 */}
<button className="bg-sky-600 hover:bg-sky-500">  {/* primary button */}
<button className="bg-rose-600 hover:bg-rose-500">  {/* destructive */}
<button className="bg-emerald-600">  {/* success */}
```

### 5. Hardcoded Dark Styles

❌ **Bad**:
```typescript
// Dark mode hardcoded, not responsive
<div className="bg-slate-950 text-slate-100">
<span className="text-white">
```

✅ **Good**:
```typescript
// Use dark: prefix for dark variants
<div className="bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-50">
<span className="text-slate-900 dark:text-slate-50">
```

### 6. Template Literal className Soup

❌ **Bad**:
```typescript
// Hard to read, error-prone
<div className={`base-styles ${isActive ? "active" : ""} ${disabled ? "opacity-50" : ""}`}>
```

✅ **Good**:
```typescript
// Use cn() utility for clean className merging
import { cn } from "@/lib/utils";

<div className={cn("base-styles", isActive && "active", disabled && "opacity-50")}>
```

### 7. Accessibility Ignored

❌ **Bad**:
```typescript
// No focus states, no ARIA labels
<button className="bg-sky-600">
<div onClick={handleClick}>
```

✅ **Good**:
```typescript
// Focus visible, keyboard accessible, proper ARIA
<button className="bg-sky-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
<div role="button" tabIndex={0} onClick={handleClick} onKeyDown={handleKeyDown}>
<button aria-label="Close dialog">
```

### 8. Spacing Inconsistency

❌ **Bad**:
```typescript
// Random spacing values
<div className="space-y-2 space-x-5 gap-1.5 p-7">
```

✅ **Good**:
```typescript
// Consistent spacing scale
<div className="space-y-2">  {/* tight */}
<div className="space-y-3">  {/* compact */}
<div className="space-y-4">  {/* default */}
<div className="p-4">  {/* card padding */}
<div className="p-5">  {/* page section */}
```

### Quick Reference Table

| Category | Anti-Pattern | Solution |
|----------|--------------|----------|
| **Font Sizes** | `text-[11px]`, `text-[13px]` | Use `text-xs`, `text-sm` |
| **Border Radius** | Mixed arbitrary values | Use `.br-badge`, `.br-card`, `.br-section`, `.br-panel` or `rounded-full`, `rounded-xl`, `rounded-2xl`, `rounded-3xl` |
| **Colors** | Hex codes, random colors | Use semantic tokens: `text-slate-900`, `bg-sky-600` or `.bg-surface-base`, `.bg-surface-overlay` |
| **Dark Mode** | Hardcoded dark styles | Use `dark:` prefix variants |
| **Spacing** | `px-3.5`, `gap-1.5` | Use `px-3`, `px-4`, `gap-2`, `gap-3` |
| **Letter Spacing** | `tracking-[0.2em]`, `tracking-[0.3em]` | Use `tracking-wider` for uppercase |
| **Containers** | Mixed border+bg styles | Use `.container-card`, `.container-section`, `.container-panel` |

### Common Violations to Avoid

❌ **Bad Hierarchy**:
- Same font size for title and body (`text-sm` everywhere)
- Insufficient contrast between hierarchy levels
- Random font sizes without clear progression
- Inconsistent spacing between related elements

✅ **Good Hierarchy**:
```typescript
// Clear visual progression
<div>
  <h1 className="text-2xl font-semibold">Page Title</h1>
  <section className="p-5">
    <h2 className="text-lg font-semibold">Section Title</h2>
    <div className="space-y-4">
      <h3 className="text-base font-medium">Subsection</h3>
      <p className="text-sm">Body content</p>
      <p className="text-xs">Secondary info</p>
    </div>
  </section>
</div>
```

---

## 🔧 Phase 3-4: Border Radius & Background Utility Classes

### Border Radius Classes

Use these for consistent border radius across components:

| Class | Value | Usage |
|-------|-------|-------|
| `.br-badge` | `rounded-full` | Badges, pills, indicators |
| `.br-btn` | `rounded-lg` | Buttons, inputs |
| `.br-card` | `rounded-xl` | Cards, small boxes |
| `.br-section` | `rounded-2xl` | Page sections, large containers |
| `.br-panel` | `rounded-3xl` | Large panels, main containers |

### Background Color Classes

Use these for consistent background colors with automatic dark mode:

| Class | Light | Dark | Usage |
|-------|-------|------|-------|
| `.bg-surface-base` | `bg-white` | `dark:bg-slate-900/90` | Primary surface |
| `.bg-surface-overlay` | `bg-slate-50` | `dark:bg-slate-950/50` | Overlay surface |
| `.bg-surface-elevated` | `bg-slate-100` | `dark:bg-slate-900/40` | Elevated surface |

### Combined Container Classes

These combine border-radius + background + border + shadow:

| Class | Border | Background | Padding | Usage |
|-------|--------|------------|----------|-------|
| `.container-card` | `rounded-xl` | surface-base | `p-4` | Cards |
| `.container-section` | `rounded-2xl` | surface-base | `p-5` | Page sections |
| `.container-panel` | `rounded-3xl` | surface-base | `p-6` | Large panels |

### Input & Code Block Classes

| Class | Usage |
|-------|-------|
| `.input-container` | Standard input field with focus states |
| `.code-block` | Code block (max-height: 12rem) |
| `.code-block-lg` | Large code block (max-height: 20rem) |

### Usage Examples

```typescript
// Container classes
<section className="container-section">
  <h2>Section Title</h2>
  {/* content */}
</section>

<div className="container-card">
  {/* card content */}
</div>

// Background classes
<div className="bg-surface-base">
  <div className="bg-surface-overlay p-4">
    {/* layered content */}
  </div>
</div>

// Input classes
<input className="input-container" />
<textarea className="input-container" />

// Code blocks
<pre className="code-block">{code}</pre>
<pre className="code-block-lg">{longCode}</pre>

// Border radius classes
<span className="br-badge px-3 py-1">Badge</span>
<button className="br-btn px-6 py-3">Button</button>
<div className="br-card p-4">Card</div>
<section className="br-section p-5">Section</section>
<div className="br-panel p-6">Panel</div>
```

---

## 🎯 Complete Design Checklist

Use this checklist for ANY page/component:

**Layout & Structure:**
- [ ] Page wrapper: `bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50`
- [ ] Sections: `.container-section` or `rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/90`
- [ ] Cards: `.container-card` or `rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900`
- [ ] Panels: `.container-panel` or `rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900`

**Components:**
- [ ] Inputs: `.input-container` or `rounded-lg border border-slate-300 bg-white px-4 py-3` (with dark variants)
- [ ] Code blocks: `.code-block` or `.code-block-lg`
- [ ] Buttons use standard variants (Primary, Secondary, Destructive, Ghost)
- [ ] Badges use `.br-badge` (rounded-full)

**Colors & Typography:**
- [ ] Text has proper dark mode variants
- [ ] Use `.bg-surface-base`, `.bg-surface-overlay`, `.bg-surface-elevated` for backgrounds
- [ ] Use `.br-badge`, `.br-btn`, `.br-card`, `.br-section`, `.br-panel` for border radius

**Forms:**
- [ ] Forms use `space-y-4` for vertical spacing
- [ ] Empty states follow universal pattern
- [ ] Loading states follow universal pattern

