# UI Design System Guide

> Project: tobit-spa-ai
> Framework: Next.js 16 + React 19 + Tailwind CSS 4 + Radix UI
> Last Updated: 2026-02-12

---

## 📋 Table of Contents

1. [Consistency Issues Found](#consistency-issues-found)
2. [Standard Patterns](#standard-patterns)
3. [Color System](#color-system)
4. [Typography](#typography)
5. [Spacing & Layout](#spacing--layout)
6. [Component Patterns](#component-patterns)
7. [Dark Mode](#dark-mode)
8. [Code Style Guidelines](#code-style-guidelines)

---

## 🔍 Consistency Issues Found

### 1. CSS Application Method Inconsistency

| Component | Method | Status |
|-----------|--------|--------|
| Button, Card, Input, Label, Switch, Tabs, Drawer | `cn()` utility | ✅ Consistent |
| Badge, Alert, Select | Template literals | ❌ Inconsistent |
| Button | CVA (class-variance-authority) | ✅ Best Practice |

**Issue**: Badge, Alert, and Select use template literals instead of `cn()` utility.

### 2. Color System Inconsistency

| Component | Color System | Status |
|-----------|--------------|--------|
| Button, Card, Input, Dialog, Drawer | Direct Slate colors | ✅ Consistent |
| Tabs, Select | CSS Variables (`bg-muted`, `text-foreground`) | ❌ Inconsistent |
| Label | Mixed (Slate + dark variant) | ⚠️ Partial |

**Issue**: CSS variables are used inconsistently. Recommend standardizing on Slate colors.

### 3. Dark Mode Support Inconsistency

| Component | Dark Mode | Status |
|-----------|-----------|--------|
| Button, Card, Input | Full support | ✅ Consistent |
| Label | Partial (`dark:text-slate-300`) | ⚠️ Partial |
| Dialog, Drawer | Always dark mode | ❌ Inconsistent |
| Badge, Alert | No dark mode | ❌ Missing |

**Issue**: Dialog and Drawer are always dark-themed. Badge and Alert lack dark mode variants.

### 4. Border Radius Inconsistency

| Radius | Components |
|--------|------------|
| `rounded-md` | Button, Input, TabsTrigger, SelectTrigger |
| `rounded-lg` | Card |
| `rounded-2xl` | Dialog |
| `rounded-full` | Badge |
| `rounded-sm` | TabsTrigger (internal) |

**Recommendation**: Standardize on `rounded-md` for interactive elements, `rounded-lg` for containers.

### 5. Padding Inconsistency

| Padding | Components |
|---------|------------|
| `p-6` | Card header/footer, Dialog, Drawer header |
| `p-4` | Alert |
| `px-3 py-2` | Input, SelectTrigger |
| `px-4 py-2` | Button (default) |

**Recommendation**:
- Containers: `p-6`
- Compact components: `px-3 py-2`
- Standard components: `px-4 py-2`

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

### Component Pattern with Radix UI

```typescript
import * as React from "react";
import * as Primitive from "@radix-ui/react-primitive";
import { cn } from "@/lib/utils";

const MyComponent = React.forwardRef<
  React.ElementRef<typeof Primitive.Root>,
  React.ComponentPropsWithoutRef<typeof Primitive.Root>
>(({ className, ...props }, ref) => (
  <Primitive.Root
    ref={ref}
    className={cn("base-styles", className)}
    {...props}
  />
));
MyComponent.displayName = Primitive.Root.displayName;

export { MyComponent };
```

### Variant Pattern with CVA

```typescript
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const componentVariants = cva(
  "base-classes",
  {
    variants: {
      variant: {
        default: "variant-default-classes",
        secondary: "variant-secondary-classes",
      },
      size: {
        default: "size-default-classes",
        sm: "size-sm-classes",
        lg: "size-lg-classes",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface MyComponentProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof componentVariants> {}

const MyComponent = React.forwardRef<HTMLDivElement, MyComponentProps>(
  ({ className, variant, size, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(componentVariants({ variant, size }), className)}
      {...props}
    />
  )
);
```

---

## 🎨 Color System

### Primary Colors (Slate Scale)

| Usage | Light Mode | Dark Mode |
|-------|------------|-----------|
| **Background** | `bg-white` | `dark:bg-slate-950` |
| **Foreground** | `text-slate-950` | `dark:text-slate-50` |
| **Muted Background** | `bg-slate-100` | `dark:bg-slate-800` |
| **Muted Foreground** | `text-slate-500` | `dark:text-slate-400` |
| **Border** | `border-slate-200` | `dark:border-slate-800` |
| **Input Background** | `bg-white` | `dark:bg-slate-950` |
| **Card Background** | `bg-white` | `dark:bg-slate-950` |

### Accent Colors

| Purpose | Color | Usage |
|---------|-------|-------|
| **Primary** | `bg-blue-600` | Default buttons, links |
| **Secondary** | `bg-slate-600` | Secondary badges |
| **Destructive** | `bg-red-600` | Destructive buttons, error badges |
| **Success** | `bg-green-600` | Success states |
| **Warning** | `bg-yellow-600` | Warning states |

### Focus Ring

```css
focus-visible:outline-none
focus-visible:ring-2
focus-visible:ring-slate-950
focus-visible:ring-offset-2
dark:focus-visible:ring-slate-300
dark:ring-offset-slate-950
```

---

## 📝 Typography

### Font Sizes

| Size | Class | Usage |
|------|-------|-------|
| **xs** | `text-xs` | Badges, labels |
| **sm** | `text-sm` | Default text, descriptions, labels |
| **base** | `text-base` | Body content |
| **lg** | `text-lg` | Dialog/Drawer titles |
| **xl** | `text-xl` | Section headers |
| **2xl** | `text-2xl` | Card titles |
| **3xl** | `text-3xl` | Page headings |

### Font Weights

| Weight | Class | Usage |
|--------|-------|-------|
| **Medium** | `font-medium` | Buttons, labels, badges |
| **Semibold** | `font-semibold` | Titles, headings |
| **Normal** | `font-normal` | Body text (default) |

### Letter Spacing

| Usage | Class |
|-------|-------|
| **Headings** | `tracking-tight` |
| **Normal** | (default) |

---

## 📐 Spacing & Layout

### Standard Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| **1** | 0.25rem (4px) | Tight gaps |
| **2** | 0.5rem (8px) | Small gaps |
| **3** | 0.75rem (12px) | Compact padding |
| **4** | 1rem (16px) | Default padding |
| **6** | 1.5rem (24px) | Container padding |
| **8** | 2rem (32px) | Section spacing |

### Common Patterns

```typescript
// Card padding
"p-6"           // Header, footer
"p-6 pt-0"      // Content (no top padding)

// Button padding (default)
"h-10 px-4 py-2" // Standard
"h-9 px-3"       // Small
"h-11 px-8"       // Large

// Input padding
"h-10 px-3 py-2"

// Flex gaps
"space-x-2"      // Horizontal gap
"space-y-1.5"    // Vertical gap
"space-x-2"       // Footer buttons
```

---

## 🧩 Component Patterns

### Card

```typescript
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
  <CardFooter>Footer</CardFooter>
</Card>
```

**Styles:**
- Container: `rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950`
- Header: `flex flex-col space-y-1.5 p-6`
- Title: `text-2xl font-semibold leading-none tracking-tight`
- Description: `text-sm text-slate-500 dark:text-slate-400`

### Button

**Variants:**
- `default`: `bg-slate-900 text-slate-50`
- `destructive`: `bg-red-500 text-slate-50`
- `outline`: `border border-slate-200 bg-white`
- `secondary`: `bg-slate-100 text-slate-900`
- `ghost`: `hover:bg-slate-100`
- `link`: `text-slate-900 underline-offset-4 hover:underline`

**Sizes:**
- `default`: `h-10 px-4 py-2`
- `sm`: `h-9 px-3`
- `lg`: `h-11 px-8`
- `icon`: `h-10 w-10`

### Input

```typescript
<Input
  className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:ring-2 focus-visible:ring-slate-950"
/>
```

### Dialog/Drawer

**Dialog Overlay:** `fixed inset-0 bg-slate-950/80 backdrop-blur-sm`
**Drawer Overlay:** Same as dialog

**Content:**
- Dialog: `bg-slate-950 border border-slate-800 p-6 rounded-2xl`
- Drawer: `bg-slate-950 border-l border-slate-800`

---

## 🌙 Dark Mode

### Implementation Pattern

```typescript
// Always pair light and dark variants
className={cn(
  "bg-white text-slate-950",           // Light mode
  "dark:bg-slate-950 dark:text-slate-50" // Dark mode
)}
```

### Dark Mode Colors

| Element | Light | Dark |
|---------|--------|------|
| Background | `bg-white` | `dark:bg-slate-950` |
| Text | `text-slate-950` | `dark:text-slate-50` |
| Border | `border-slate-200` | `dark:border-slate-800` |
| Muted bg | `bg-slate-100` | `dark:bg-slate-800` |
| Muted text | `text-slate-500` | `dark:text-slate-400` |

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

### 2. Use CVA for variants

```typescript
// ✅ Good - scalable
const variants = cva("base", { variants: { ... } });

// ❌ Bad - hard to maintain
const variantStyles = { default: "...", secondary: "..." };
```

### 3. Forward refs for composite components

```typescript
// ✅ Good
const Component = React.forwardRef<HTMLDivElement, Props>(
  (props, ref) => <div ref={ref} {...props} />
);
Component.displayName = "Component";

// ❌ Bad - no ref forwarding
const Component = (props) => <div {...props} />;
```

### 4. TypeScript best practices

```typescript
// ✅ Good - proper type extension
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

// ❌ Bad - loose typing
interface ButtonProps {
  className?: string;
  variant?: string;
}
```

### 5. displayName for debugging

```typescript
// Always set displayName
Component.displayName = "Component";
```

---

## 📚 Recommended Actions

### High Priority

1. **Standardize CSS application method**
   - Convert Badge, Alert, Select to use `cn()`
   - Convert Badge, Alert to use CVA

2. **Fix Dark Mode inconsistencies**
   - Add dark mode to Badge, Alert
   - Fix Dialog, Drawer to support light mode

3. **Standardize CSS variables**
   - Replace `bg-muted`, `text-foreground` with explicit Slate colors
   - Or define consistent CSS variables in globals.css

### Medium Priority

4. **Standardize border radius**
   - Use `rounded-md` for interactive elements
   - Use `rounded-lg` for containers

5. **Standardize padding**
   - Define token-based system

### Low Priority

6. **Create design tokens**
   - Extract colors to CSS variables
   - Create spacing scale

---

## 📖 References

- [Tailwind CSS 4 Docs](https://tailwindcss.com/docs)
- [Radix UI Primitives](https://www.radix-ui.com/primitives)
- [Class Variance Authority](https://cva.style/docs)
- [shadcn/ui Components](https://ui.shadcn.com/docs/components)
