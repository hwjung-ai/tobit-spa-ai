"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  ThemePreset,
  DesignTokenSet,
  THEME_PRESETS,
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
  const [currentTheme, setCurrentTheme] = useState<ThemePreset>("dark");
  const [tokens, setTokens] = useState<DesignTokenSet>(THEME_PRESETS.dark);

  const applyTheme = useCallback((theme: ThemePreset) => {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, []);

  useEffect(() => {
    const savedTheme = getInitialTheme();
    setCurrentTheme(savedTheme);
    setTokens(THEME_PRESETS[savedTheme]);
    applyTheme(savedTheme);
  }, [applyTheme]);

  useEffect(() => {
    applyTheme(currentTheme);
  }, [applyTheme, currentTheme]);

  const setTheme = useCallback((preset: ThemePreset) => {
    setCurrentTheme(preset);
    setTokens(THEME_PRESETS[preset]);
    localStorage.setItem(STORAGE_KEY, preset);
  }, []);

  const customizeTokens = useCallback((overrides: Partial<DesignTokenSet>) => {
    setTokens((prev) => mergeTokens(prev, overrides));
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
