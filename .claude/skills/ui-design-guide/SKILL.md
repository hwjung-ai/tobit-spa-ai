# UI Design Guide & Consistency Checker

This skill helps maintain UI consistency across the tobit-spa-ai project by:

1. **Analyzing existing UI components** for consistency issues
2. **Providing design system guidance** based on project standards
3. **Reviewing code** against design system guidelines

---

## ✅ Phase 1 Complete (2026-02-12)

### Consistency Fixes Applied

**Files Modified:**
- `/apps/web/src/app/globals.css` - CSS variables defined
- `/apps/web/src/lib/design-tokens.ts` - Design token system created
- `/apps/web/src/components/builder/BuilderShell.tsx` - Dark mode support
- `/apps/web/src/app/page.tsx` - Full consistency pass
- `/apps/web/src/app/admin/screens/page.tsx` - Dark mode support
- `/apps/web/src/app/admin/assets/page.tsx` - Dark mode support
- `/apps/web/src/app/admin/tools/page.tsx` - Dark mode support
- `/apps/web/src/app/admin/catalogs/page.tsx` - Gray to Slate colors + dark mode
- `/apps/web/src/app/admin/observability/page.tsx` - Dark mode support
- `/apps/web/src/app/admin/logs/page.tsx` - Dark mode support
- `/apps/web/src/app/admin/regression/page.tsx` - Dark mode support
- `/apps/web/src/app/admin/explorer/page.tsx` - Dark mode support
- `/apps/web/src/app/ops/page.tsx` - Dark mode support
- `/apps/web/src/app/sim/page.tsx` - Dark mode support

**Key Changes:**
- ✅ Dark mode support added to all pages
- ✅ Border radius standardized (`rounded-2xl` for sections, `rounded-md` for buttons)
- ✅ Color system defined (Slate scale with dark variants)
- ✅ Spacing standardized (`p-5` for sections, `gap-2` to `gap-6`)

---

## 📚 Design System Reference

### Color System

| Usage | Light Mode | Dark Mode |
|-------|------------|-----------|
| Background | `bg-white` | `dark:bg-slate-950` |
| Elevated BG | `bg-slate-50` | `dark:bg-slate-900` |
| Foreground | `text-slate-900` | `dark:text-slate-50` |
| Muted Text | `text-slate-600` | `dark:text-slate-400` |
| Border | `border-slate-200` | `dark:border-slate-800` |
| Muted Border | `border-slate-300` | `dark:border-slate-700` |

### Typography

| Usage | Class |
|-------|-------|
| Tiny labels | `text-[10px]` |
| Small text | `text-xs` |
| Body text | `text-sm` / `text-base` |
| Section titles | `text-lg` |
| Page headings | `text-2xl` |

### Border Radius

| Usage | Class |
|-------|-------|
| Page sections | `rounded-2xl` |
| Buttons, inputs | `rounded-md` |
| Cards | `rounded-lg` |

### Spacing

| Usage | Class |
|-------|-------|
| Section padding | `p-5` |
| Button padding | `px-6 py-3` (large) / `px-4 py-2` (small) |
| Gaps | `gap-2` (8px) to `gap-6` (24px) |

---

## 🔍 Code Review Checklist

When reviewing UI code, check for:

- [ ] Uses `cn()` utility (not template literals)
- [ ] Has `dark:` variants for all colors
- [ ] Uses consistent border radius
- [ ] Uses consistent text colors from system
- [ ] Uses consistent borders from system
- [ ] Has proper focus states

---

## 📋 Key Patterns

### Dark Mode Pattern

```typescript
// ✅ Good - always include dark mode
className="bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50"

// ❌ Bad - assumes dark mode only
className="bg-slate-950 text-slate-100"
```

### Component Pattern

```typescript
import { cn } from "@/lib/utils";

const MyComponent = ({ className, ...props }) => (
  <section className={cn(
    "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm",
    "dark:border-slate-800 dark:bg-slate-900/90",
    className
  )} {...props}>
    {/* content */}
  </section>
);
```

---

## Files

- `DESIGN_SYSTEM_GUIDE.md` - Complete design system documentation
- `COMPONENT_PATTERNS.md` - Component implementation patterns (coming soon)

---

## 🧠 Nielsen's 10 Usability Heuristics

This skill enforces Nielsen's standard UX principles:

| # | Heuristic | Implementation |
|---|-----------|----------------|
| 1 | **Visibility of system status** | Loading states, progress indicators, toast notifications |
| 2 | **Match between system and real world** | Familiar language, real-world metaphors, logical information flow |
| 3 | **User control and freedom** | Cancel buttons, undo/redo, clear "back" navigation, escape to dismiss |
| 4 | **Consistency and standards** | Use design tokens, consistent spacing/colors (see Design System Reference) |
| 5 | **Error prevention** | Form validation before submit, disabled states, confirmation dialogs |
| 6 | **Recognition rather than recall** | Visible options, clear labels, contextual hints, help text |
| 7 | **Flexibility and efficiency** | Keyboard shortcuts, power user features, sensible defaults |
| 8 | **Aesthetic and minimalist design** | Remove clutter, focus on essential content, whitespace |
| 9 | **Help users recognize errors** | Clear error messages, inline validation, suggested fixes |
| 10 | **Help and documentation** | Tooltips, empty states with guidance, contextual help |

### Heuristic Application Checklist

When implementing UI features, verify:

- [ ] **H1**: Loading states for async operations (spinners, skeletons)
- [ ] **H2**: Labels match user's mental model (not technical terms)
- [ ] **H3**: Cancel/undo available for destructive actions
- [ ] **H4**: Consistent with existing design system patterns
- [ ] **H5**: Form validates before submission
- [ ] **H6**: Options visible, no hidden menus without clear affordance
- [ ] **H7**: Keyboard shortcuts documented (Esc, Cmd+Enter, etc.)
- [ ] **H8**: No unnecessary elements, clear visual hierarchy
- [ ] **H9**: Error messages explain what went wrong + how to fix
- [ ] **H10**: Empty states guide users to next action

---

## Notes

- This skill is project-specific to tobit-spa-ai
- Design system based on shadcn/ui patterns
- Phase 1 (consistency fixes) complete
- Phase 2 (component library) pending
- UX heuristics: Nielsen's 10 Usability Heuristics (industry standard)
