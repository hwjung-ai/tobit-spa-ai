/**
 * Design Token System for Screen Editor Theme
 * Provides light/dark/brand presets with CSS variable integration.
 */

export interface ColorTokens {
  brand: { primary: string; secondary: string; accent: string };
  semantic: { success: string; warning: string; error: string; info: string };
  surface: { background: string; foreground: string; muted: string; card: string; border: string; input: string };
  text: { primary: string; secondary: string; muted: string; inverse: string };
}

export interface DesignTokenSet {
  id: string;
  name: string;
  colors: ColorTokens;
  borderRadius: { sm: string; md: string; lg: string; xl: string };
  shadows: { sm: string; md: string; lg: string };
}

export type ThemePreset = "light" | "dark" | "brand";

export const THEME_PRESETS: Record<ThemePreset, DesignTokenSet> = {
  dark: {
    id: "dark",
    name: "Dark",
    colors: {
      brand: { primary: "#38bdf8", secondary: "#818cf8", accent: "#f472b6" },
      semantic: { success: "#22c55e", warning: "#eab308", error: "#ef4444", info: "#3b82f6" },
      surface: { background: "#0a0a0a", foreground: "#ededed", muted: "#1e293b", card: "#0f172a", border: "#1e293b", input: "#1e293b" },
      text: { primary: "#f1f5f9", secondary: "#94a3b8", muted: "#64748b", inverse: "#0f172a" },
    },
    borderRadius: { sm: "0.25rem", md: "0.375rem", lg: "0.5rem", xl: "0.75rem" },
    shadows: { sm: "0 1px 2px rgba(0,0,0,0.5)", md: "0 4px 6px rgba(0,0,0,0.5)", lg: "0 10px 15px rgba(0,0,0,0.5)" },
  },
  light: {
    id: "light",
    name: "Light",
    colors: {
      brand: { primary: "#0284c7", secondary: "#6366f1", accent: "#db2777" },
      semantic: { success: "#16a34a", warning: "#ca8a04", error: "#dc2626", info: "#2563eb" },
      surface: { background: "#ffffff", foreground: "#0f172a", muted: "#f1f5f9", card: "#ffffff", border: "#e2e8f0", input: "#f8fafc" },
      text: { primary: "#0f172a", secondary: "#475569", muted: "#94a3b8", inverse: "#f8fafc" },
    },
    borderRadius: { sm: "0.25rem", md: "0.375rem", lg: "0.5rem", xl: "0.75rem" },
    shadows: { sm: "0 1px 2px rgba(0,0,0,0.05)", md: "0 4px 6px rgba(0,0,0,0.1)", lg: "0 10px 15px rgba(0,0,0,0.1)" },
  },
  brand: {
    id: "brand",
    name: "Brand",
    colors: {
      brand: { primary: "#8b5cf6", secondary: "#06b6d4", accent: "#f59e0b" },
      semantic: { success: "#10b981", warning: "#f59e0b", error: "#f43f5e", info: "#6366f1" },
      surface: { background: "#0c0a1a", foreground: "#e2e0f0", muted: "#1a1530", card: "#130f2a", border: "#2d2650", input: "#1a1530" },
      text: { primary: "#e2e0f0", secondary: "#a5a0c0", muted: "#706b90", inverse: "#0c0a1a" },
    },
    borderRadius: { sm: "0.375rem", md: "0.5rem", lg: "0.75rem", xl: "1rem" },
    shadows: { sm: "0 1px 3px rgba(139,92,246,0.15)", md: "0 4px 8px rgba(139,92,246,0.2)", lg: "0 10px 20px rgba(139,92,246,0.25)" },
  },
};

/** Convert a DesignTokenSet to CSS variable declarations */
export function tokensToCSSVariables(tokens: DesignTokenSet): Record<string, string> {
  const vars: Record<string, string> = {};
  const { colors, borderRadius, shadows } = tokens;

  // Colors
  vars["--theme-brand-primary"] = colors.brand.primary;
  vars["--theme-brand-secondary"] = colors.brand.secondary;
  vars["--theme-brand-accent"] = colors.brand.accent;
  vars["--theme-success"] = colors.semantic.success;
  vars["--theme-warning"] = colors.semantic.warning;
  vars["--theme-error"] = colors.semantic.error;
  vars["--theme-info"] = colors.semantic.info;
  vars["--theme-bg"] = colors.surface.background;
  vars["--theme-fg"] = colors.surface.foreground;
  vars["--theme-muted"] = colors.surface.muted;
  vars["--theme-card"] = colors.surface.card;
  vars["--theme-border"] = colors.surface.border;
  vars["--theme-input"] = colors.surface.input;
  vars["--theme-text"] = colors.text.primary;
  vars["--theme-text-secondary"] = colors.text.secondary;
  vars["--theme-text-muted"] = colors.text.muted;
  vars["--theme-text-inverse"] = colors.text.inverse;

  // Border radius
  vars["--theme-radius-sm"] = borderRadius.sm;
  vars["--theme-radius-md"] = borderRadius.md;
  vars["--theme-radius-lg"] = borderRadius.lg;
  vars["--theme-radius-xl"] = borderRadius.xl;

  // Shadows
  vars["--theme-shadow-sm"] = shadows.sm;
  vars["--theme-shadow-md"] = shadows.md;
  vars["--theme-shadow-lg"] = shadows.lg;

  return vars;
}

/** Merge base tokens with partial overrides */
export function mergeTokens(base: DesignTokenSet, overrides: Partial<DesignTokenSet>): DesignTokenSet {
  return {
    ...base,
    ...overrides,
    colors: {
      brand: { ...base.colors.brand, ...overrides.colors?.brand },
      semantic: { ...base.colors.semantic, ...overrides.colors?.semantic },
      surface: { ...base.colors.surface, ...overrides.colors?.surface },
      text: { ...base.colors.text, ...overrides.colors?.text },
    },
    borderRadius: { ...base.borderRadius, ...overrides.borderRadius },
    shadows: { ...base.shadows, ...overrides.shadows },
  };
}
