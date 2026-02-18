"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface ExamplePrompt {
  label: string;
  prompt: string;
  icon?: string;
}

export interface ExamplePromptsProps {
  prompts: ExamplePrompt[];
  onSelect: (prompt: string) => void;
  disabled?: boolean;
  title?: string;
}

export function ExamplePrompts({
  prompts,
  onSelect,
  disabled = false,
  title = "Try these examples:",
}: ExamplePromptsProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {prompts.map((example, index) => (
          <button
            key={index}
            type="button"
            onClick={() => onSelect(example.prompt)}
            disabled={disabled}
            className={cn(
              "px-2 py-1 text-xs rounded-full border transition-colors",
              "border-border hover:border-primary hover:bg-primary/10",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {example.icon && <span className="mr-1">{example.icon}</span>}
            {example.label}
          </button>
        ))}
      </div>
    </div>
  );
}
