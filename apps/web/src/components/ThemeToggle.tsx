"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

export default function ThemeToggle() {
  const { currentTheme, setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(currentTheme === "dark" ? "light" : "dark");
  };

  return (
    <button
      onClick={toggleTheme}
      className="rounded-md border border-variant bg-surface-base text-foreground p-2 transition hover:bg-surface-elevated hover:border-border-muted"
      aria-label={currentTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={currentTheme === "dark" ? "Light mode" : "Dark mode"}
    >
      {currentTheme === "dark" ? (
        <Sun className="h-5 w-5" />
      ) : (
        <Moon className="h-5 w-5" />
      )}
    </button>
  );
}
