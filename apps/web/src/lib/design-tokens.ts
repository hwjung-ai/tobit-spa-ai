/**
 * Design Tokens for tobit-spa-ai
 *
 * Central design system constants for consistent UI across all pages.
 * Use these tokens instead of hardcoded values.
 */

// ============================================================================
// COLOR TOKENS
// ============================================================================

export const colors = {
  // Base colors (with dark mode variants) - Using CSS variables
  background: {
    light: "bg-white",
    dark: "dark:bg-[var(--surface-base)]",
  },
  foreground: {
    light: "text-[var(--foreground)]",
    dark: "dark:text-[var(--foreground)]",
  },
  border: {
    light: "border-[var(--border)]",
    dark: "dark:border-[var(--border)]",
  },

  // Surface colors (containers, cards, panels)
  surface: {
    base: {
      light: "bg-white",
      dark: "dark:bg-[var(--surface-base)]",
    },
    elevated: {
      light: "bg-[var(--surface-elevated)]",
      dark: "dark:bg-[var(--surface-elevated)]",
    },
    overlay: {
      light: "bg-white/95",
      dark: "dark:bg-[var(--surface-overlay)]",
    },
  },

  // Muted colors (secondary text, backgrounds)
  muted: {
    foreground: {
      light: "text-[var(--muted-foreground)]",
      dark: "dark:text-[var(--muted-foreground)]",
    },
    background: {
      light: "bg-[var(--muted-background)]",
      dark: "dark:bg-[var(--muted-background)]",
    },
  },

  // Accent colors
  primary: {
    DEFAULT: "bg-sky-600",
    foreground: "text-white",
    light: "bg-sky-500",
    dark: "bg-sky-700",
  },
  destructive: {
    DEFAULT: "bg-red-600",
    foreground: "text-white",
    light: "bg-red-500",
    dark: "bg-red-700",
  },
  success: {
    DEFAULT: "bg-green-600",
    foreground: "text-white",
  },
  warning: {
    DEFAULT: "bg-yellow-600",
    foreground: "text-white",
  },

  // Border colors for surfaces
  surfaceBorder: {
    light: "border-[var(--border)]",
    dark: "dark:border-[var(--border)]",
  },
  inputBorder: {
    light: "border-[var(--border)]",
    dark: "dark:border-[var(--border)]",
  },
} as const;

// ============================================================================
// TYPOGRAPHY TOKENS
// ============================================================================

export const typography = {
  // Font sizes
  fontSize: {
    xs: "text-xs",        // 12px - badges, labels
    sm: "text-sm",        // 14px - descriptions, secondary text
    base: "text-base",     // 16px - body content
    lg: "text-lg",        // 18px - dialog/drawer titles
    xl: "text-xl",        // 20px - section headers
    "2xl": "text-2xl",    // 24px - card titles
    "3xl": "text-3xl",     // 30px - page headings
  },

  // Font weights
  fontWeight: {
    normal: "font-normal",
    medium: "font-medium",
    semibold: "font-semibold",
    bold: "font-bold",
  },

  // Letter spacing
  letterSpacing: {
    normal: "",           // default
    tight: "tracking-tight",  // headings
    wide: "tracking-wider",  // labels, uppercase text
  },

  // Line height
  lineHeight: {
    normal: "leading-normal",
    relaxed: "leading-relaxed",
    tight: "leading-tight",
  },
} as const;

// ============================================================================
// SPACING TOKENS
// ============================================================================

export const spacing = {
  // Padding
  padding: {
    xs: "p-2",      // 8px  - tight spacing
    sm: "p-3",      // 12px - compact
    md: "p-4",      // 16px - default
    lg: "p-6",      // 24px - containers
    xl: "p-8",      // 32px - sections
  },

  // Gap (flex/grid gap)
  gap: {
    xs: "gap-1",     // 4px
    sm: "gap-2",     // 8px
    md: "gap-3",     // 12px
    lg: "gap-4",     // 16px
    xl: "gap-6",     // 24px
  },

  // Section spacing
  section: "space-y-6",
} as const;

// ============================================================================
// BORDER RADIUS TOKENS
// ============================================================================

export const borderRadius = {
  sm: "rounded-sm",     // 2px - tabs
  md: "rounded-md",     // 6px - buttons, inputs
  lg: "rounded-lg",     // 8px - cards
  xl: "rounded-xl",     // 12px - panels
  "2xl": "rounded-2xl",   // 16px - large containers
  "3xl": "rounded-3xl",   // 24px - hero sections
  full: "rounded-full",  // pill badges
} as const;

// ============================================================================
// SHADOW TOKENS
// ============================================================================

export const shadow = {
  sm: "shadow-sm",
  md: "shadow-md",
  lg: "shadow-lg",
  xl: "shadow-xl",
  inner: "shadow-inner",
  none: "shadow-none",
} as const;

// ============================================================================
// FOCUS RING TOKENS
// ============================================================================

export const focusRing = {
  base: [
    "focus-visible:outline-none",
    "focus-visible:ring-2",
    "focus-visible:ring-sky-500",
    "focus-visible:ring-offset-2",
    "dark:focus-visible:ring-offset-[var(--surface-base)]",
  ].join(" "),
} as const;

// ============================================================================
// TRANSITION TOKENS
// ============================================================================

export const transition = {
  fast: "transition-all duration-150",
  normal: "transition-all duration-200",
  slow: "transition-all duration-300",
} as const;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get color class with dark mode variant
 */
export function withDarkMode(lightClass: string, darkClass: string): string {
  return `${lightClass} dark:${darkClass}`;
}

/**
 * Get background color class with dark mode
 */
export function bgSurface(variant: keyof typeof colors.surface = "base"): string {
  return withDarkMode(colors.surface[variant].light, colors.surface[variant].dark);
}

/**
 * Get text color class with dark mode
 */
export function textForeground(muted = false): string {
  return muted
    ? withDarkMode(colors.muted.foreground.light, colors.muted.foreground.dark)
    : withDarkMode(colors.foreground.light, colors.foreground.dark);
}

/**
 * Get border color class with dark mode
 */
export function borderSurface(variant: keyof typeof colors.surfaceBorder = "light"): string {
  return withDarkMode(colors.surfaceBorder.light, colors.surfaceBorder.dark);
}

// ============================================================================
// COMMON COMPONENT PATTERNS
// ============================================================================

/**
 * Standard page container styles
 */
export const pageContainer = [
  "min-h-screen",
  bgSurface("base"),
  textForeground(),
].join(" ");

/**
 * Standard card styles
 */
export const cardStyles = [
  borderRadius.lg,
  borderSurface(),
  bgSurface("base"),
  spacing.padding.lg,
].join(" ");

/**
 * Standard input styles
 */
export const inputStyles = [
  "h-10",
  "w-full",
  borderRadius.md,
  "border",
  borderSurface(),
  bgSurface("base"),
  "px-3",
  "py-2",
  typography.fontSize.sm,
  focusRing,
].join(" ");

/**
 * Standard button styles (base, before variant application)
 */
export const buttonBaseStyles = [
  "inline-flex",
  "items-center",
  "justify-center",
  borderRadius.md,
  typography.fontSize.sm,
  typography.fontWeight.medium,
  "ring-offset-white",
  "transition-colors",
  "focus-visible:outline-none",
  "focus-visible:ring-2",
  "focus-visible:ring-sky-500",
  "focus-visible:ring-offset-2",
  "disabled:pointer-events-none",
  "disabled:opacity-50",
  "dark:ring-offset-[var(--surface-base)]",
  "dark:focus-visible:ring-[var(--border-muted)]",
].join(" ");
