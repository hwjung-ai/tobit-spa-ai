# UI Design Guide & Consistency Checker

This skill helps maintain UI consistency across the tobit-spa-ai project by:

1. **Analyzing existing UI components** for consistency issues
2. **Providing design system guidance** based on project standards
3. **Generating consistent UI components** following established patterns
4. **Reviewing code** against design system guidelines

## Features

### 📊 Consistency Analysis

Analyze UI components for:
- CSS application method (cn() vs template literals)
- Color system usage (Slate vs CSS variables)
- Dark mode support
- Border radius consistency
- Padding/spacing patterns
- TypeScript typing patterns

### 📚 Design System Reference

Access the complete design system guide including:
- Color system (Slate scale, accent colors)
- Typography scale and weights
- Spacing and layout tokens
- Component patterns (Button, Card, Input, Dialog, etc.)
- Dark mode implementation patterns

### ✨ Component Generation

Generate new UI components that follow project standards:
- Uses `cn()` utility for className merging
- Implements CVA for variants
- Proper TypeScript typing
- Radix UI integration pattern
- Dark mode support

### 🔍 Code Review

Review UI code for:
- Consistency with design system
- Best practice adherence
- Potential improvements

## Usage

### Check component consistency

```
/ui check apps/web/src/components/ui/badge.tsx
```

### Get design system reference

```
/ui guide colors
/ui guide typography
/ui guide spacing
/ui guide components
```

### Generate a new component

```
/ui generate tooltip
/ui generate progress
/ui generate skeleton
```

### Review code for consistency

```
/ui review apps/web/src/components/my-new-component.tsx
```

## Design System Standards

This project uses:

- **Framework**: Next.js 16 + React 19
- **Styling**: Tailwind CSS 4
- **Components**: Radix UI primitives
- **Utilities**: `cn()` function + CVA (class-variance-authority)
- **Colors**: Slate scale (slate-50 to slate-950)

### Key Patterns

**Always use `cn()` for className merging:**
```typescript
import { cn } from "@/lib/utils";
className={cn("base-styles", className)}
```

**Use CVA for variants:**
```typescript
const variants = cva("base", {
  variants: { variant: { default: "...", secondary: "..." } }
});
```

**Standard colors:**
- Background: `bg-white dark:bg-slate-950`
- Foreground: `text-slate-950 dark:text-slate-50`
- Border: `border-slate-200 dark:border-slate-800`
- Muted: `text-slate-500 dark:text-slate-400`

## Files

- `DESIGN_SYSTEM_GUIDE.md` - Complete design system documentation
- `COMPONENT_PATTERNS.md` - Component implementation patterns (coming soon)

## Notes

- This skill is project-specific to tobit-spa-ai
- Design system based on shadcn/ui patterns
- Full dark mode support is a goal (not yet fully implemented)
