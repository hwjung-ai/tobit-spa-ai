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

function getInitialTheme(): ThemePreset {
  if (typeof window === "undefined") return "dark";
  const saved = localStorage.getItem(STORAGE_KEY) as ThemePreset | null;
  return saved && THEME_PRESETS[saved] ? saved : "dark";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [currentTheme, setCurrentTheme] = useState<ThemePreset>(getInitialTheme);
  const [tokens, setTokens] = useState<DesignTokenSet>(() => THEME_PRESETS[getInitialTheme()]);

  // Apply CSS variables whenever tokens change
  useEffect(() => {
    const vars = tokensToCSSVariables(tokens);
    const root = document.documentElement;
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
    root.setAttribute("data-theme", currentTheme);
  }, [tokens, currentTheme]);

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
