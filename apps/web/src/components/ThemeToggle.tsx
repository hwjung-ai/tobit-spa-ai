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
      className="rounded-md border p-2 transition"
      style={{
        borderColor: "var(--border)",
        backgroundColor: "var(--surface-base)",
        color: "var(--foreground)"
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = "var(--surface-elevated)";
        e.currentTarget.style.borderColor = "var(--border-muted)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "var(--surface-base)";
        e.currentTarget.style.borderColor = "var(--border)";
      }}
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
