# UI Design System Guide

> Project: tobit-spa-ai
> Framework: Next.js 16 + React 19 + Tailwind CSS 4 + Radix UI
> Last Updated: 2026-02-12 (Phase 1: Consistency Fixes Applied)

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
9. [ADMIN Page Standards](#admin-page-standards)
10. [Migration Checklist](#migration-checklist)

---

## ✅ Consistency Fixes Applied (Phase 1)

### Files Modified (2026-02-12)
- ✅ `/apps/web/src/app/globals.css` - CSS variables defined
- ✅ `/apps/web/src/lib/design-tokens.ts` - Design token system created
- ✅ `/apps/web/src/components/builder/BuilderShell.tsx` - Dark mode support added
- ✅ `/apps/web/src/app/page.tsx` - Full consistency pass
- ✅ `/apps/web/src/app/admin/screens/page.tsx` - Dark mode support added

### Key Changes

1. **Dark Mode Support**
   - All pages now support light/dark mode
   - Pattern: `dark:` prefix for dark variants

2. **Border Radius Standardized**
   - `rounded-2xl` - Page sections, large containers
   - `rounded-md` - Buttons, inputs, interactive elements
   - `rounded-lg` - Cards

3. **Color System**
   - Text: `text-slate-900` (light) / `text-slate-50` (dark)
   - Muted: `text-slate-600` (light) / `text-slate-400` (dark)
   - Background: `bg-white` (light) / `bg-slate-950` (dark)
   - Border: `border-slate-200` (light) / `border-slate-800` (dark)

4. **Spacing**
   - Page sections: `p-5` (20px)
   - Buttons: `px-4 py-2` or `px-6 py-3`
   - Gaps: `gap-2` to `gap-6`

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
