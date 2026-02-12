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
      brand: { primary: "#0284c7", secondary: "#818cf8", accent: "#f472b6" },
      semantic: { success: "#22c55e", warning: "#ca8a04", error: "#dc2626", info: "#0369a1" },
      surface: { background: "#020617", foreground: "#f8fafc", muted: "#0f172a", card: "#0f172a", border: "#1e293b", input: "#334155" },
      text: { primary: "#f8fafc", secondary: "#94a3b8", muted: "#94a3b8", inverse: "#020617" },
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
      surface: { background: "#ffffff", foreground: "#020617", muted: "#f8fafc", card: "#ffffff", border: "#e2e8f0", input: "#cbd5e1" },
      text: { primary: "#020617", secondary: "#475569", muted: "#64748b", inverse: "#ffffff" },
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

  // Colors - use globals.css variable names for consistency
  vars["--background"] = colors.surface.background;
  vars["--foreground"] = colors.surface.foreground;
  vars["--surface-base"] = colors.surface.background;
  vars["--surface-elevated"] = colors.surface.muted;
  vars["--surface-overlay"] = colors.surface.card;

  vars["--muted-foreground"] = colors.text.secondary;
  vars["--muted-background"] = colors.surface.muted;
  vars["--border"] = colors.surface.border;
  vars["--border-muted"] = colors.surface.input;
  vars["--input-border"] = colors.surface.input;

  // Semantic colors
  vars["--primary"] = colors.brand.primary;
  vars["--primary-foreground"] = colors.surface.foreground;
  vars["--primary-light"] = colors.brand.secondary;
  vars["--primary-dark"] = colors.brand.primary;

  vars["--destructive"] = colors.semantic.error;
  vars["--destructive-foreground"] = "#ffffff";
  vars["--success"] = colors.semantic.success;
  vars["--success-foreground"] = "#ffffff";
  vars["--warning"] = colors.semantic.warning;
  vars["--warning-foreground"] = "#ffffff";

  // Border radius
  vars["--radius-sm"] = borderRadius.sm;
  vars["--radius-md"] = borderRadius.md;
  vars["--radius-lg"] = borderRadius.lg;
  vars["--radius-xl"] = borderRadius.xl;

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
