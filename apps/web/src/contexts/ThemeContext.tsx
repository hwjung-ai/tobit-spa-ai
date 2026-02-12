"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  ThemePreset,
  DesignTokenSet,
  THEME_PRESETS,
  tokensToCSSVariables,
  mergeTokens,
} from "@/lib/ui-screen/design-tokens";

interface ThemeContextType {
  currentTheme: ThemePreset;
  tokens: DesignTokenSet;
  setTheme: (preset: ThemePreset) => void;
  customizeTokens: (overrides: Partial<DesignTokenSet>) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  currentTheme: "dark",
  tokens: THEME_PRESETS.dark,
  setTheme: () => {},
  customizeTokens: () => {},
});

const STORAGE_KEY = "tobit-theme-preset";

// Read from localStorage only on client side, with "dark" fallback for SSR
function getInitialTheme(): ThemePreset {
  if (typeof window === "undefined") return "dark";
  try {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemePreset | null;
    return saved && THEME_PRESETS[saved] ? saved : "dark";
  } catch {
    return "dark";
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [currentTheme, setCurrentTheme] = useState<ThemePreset>("dark"); // SSR-safe default
  const [tokens, setTokens] = useState<DesignTokenSet>(THEME_PRESETS.dark); // SSR-safe default
  const [mounted, setMounted] = useState(false);

  // Mount effect: read localStorage and apply saved theme
  useEffect(() => {
    setMounted(true);
    const savedTheme = getInitialTheme();
    // Log for debugging
    console.log('[ThemeContext] Initial theme:', savedTheme, 'localStorage:', localStorage.getItem(STORAGE_KEY));
    setCurrentTheme(savedTheme);
    setTokens(THEME_PRESETS[savedTheme]);
  }, []);

  // Apply CSS variables whenever tokens change
  useEffect(() => {
    if (!mounted) return; // Skip on first render (before mount)
    const vars = tokensToCSSVariables(tokens);
    const root = document.documentElement;
    console.log('[ThemeContext] Applying theme:', currentTheme, 'surface-overlay:', vars['--surface-overlay']);
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
    root.setAttribute("data-theme", currentTheme);

    // Apply "dark" class for Tailwind dark: classes
    if (currentTheme === "dark") {
      root.classList.add("dark");
      console.log('[ThemeContext] Added dark class');
    } else {
      root.classList.remove("dark");
      console.log('[ThemeContext] Removed dark class');
    }
  }, [tokens, currentTheme, mounted]);

  const setTheme = useCallback((preset: ThemePreset) => {
    setCurrentTheme(preset);
    setTokens(THEME_PRESETS[preset]);
    localStorage.setItem(STORAGE_KEY, preset);
  }, []);

  const customizeTokens = useCallback((overrides: Partial<DesignTokenSet>) => {
    setTokens(prev => mergeTokens(prev, overrides));
  }, []);

  return (
    <ThemeContext.Provider value={{ currentTheme, tokens, setTheme, customizeTokens }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

export default ThemeContext;
