"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface CopilotResponseDisplayProps {
  explanation?: string;
  confidence?: number;
  suggestions?: string[];
  warnings?: string[];
  errors?: string[];
  className?: string;
}

export function CopilotResponseDisplay({
  explanation,
  confidence,
  suggestions = [],
  warnings = [],
  errors = [],
  className = "",
}: CopilotResponseDisplayProps) {
  if (
    !explanation &&
    confidence === undefined &&
    suggestions.length === 0 &&
    warnings.length === 0 &&
    errors.length === 0
  ) {
    return null;
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Explanation */}
      {explanation && (
        <div className="rounded-lg bg-emerald-950/30 border border-emerald-800/60 p-3 dark:bg-emerald-950/20">
          <p className="text-xs font-medium text-emerald-400 uppercase tracking-wider">
            AI Explanation
          </p>
          <p className="text-sm text-emerald-300 mt-1 dark:text-emerald-400">
            {explanation}
          </p>
        </div>
      )}

      {/* Confidence Bar */}
      {confidence !== undefined && confidence > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Confidence:</span>
          <div className="flex-1 h-2 bg-gray-700 dark:bg-gray-800 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full transition-all duration-300",
                confidence >= 0.8
                  ? "bg-emerald-500"
                  : confidence >= 0.5
                    ? "bg-amber-500"
                    : "bg-red-500"
              )}
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
          <span className="text-xs text-foreground font-medium">
            {Math.round(confidence * 100)}%
          </span>
        </div>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <div className="rounded-lg bg-red-950/30 border border-red-800/60 p-3 dark:bg-red-950/20">
          <p className="text-xs font-medium text-red-400 uppercase tracking-wider">
            Errors
          </p>
          <ul className="list-disc list-inside text-xs text-red-300 mt-1 space-y-1 dark:text-red-400">
            {errors.map((error, i) => (
              <li key={i}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="rounded-lg bg-amber-950/30 border border-amber-800/60 p-3 dark:bg-amber-950/20">
          <p className="text-xs font-medium text-amber-400 uppercase tracking-wider">
            Warnings
          </p>
          <ul className="list-disc list-inside text-xs text-amber-300 mt-1 space-y-1 dark:text-amber-400">
            {warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="rounded-lg bg-sky-950/30 border border-sky-800/60 p-3 dark:bg-sky-950/20">
          <p className="text-xs font-medium text-sky-400 uppercase tracking-wider">
            Suggestions
          </p>
          <ul className="list-disc list-inside text-xs text-sky-300 mt-1 space-y-1 dark:text-sky-400">
            {suggestions.map((suggestion, i) => (
              <li key={i}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
