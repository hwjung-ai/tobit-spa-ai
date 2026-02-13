"use client";

import React, { useState } from "react";
import { ValidationError } from "@/lib/ui-screen/editor-state";

interface ScreenEditorErrorsProps {
  errors: ValidationError[];
}

export default function ScreenEditorErrors({ errors }: ScreenEditorErrorsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const errorCount = errors.filter(e => e.severity === "error").length;
  const warningCount = errors.filter(e => e.severity === "warning").length;

  if (errors.length === 0) return null;

  return (
    <div
      className="border-b border-variant bg-red-950/30 px-6 py-3"
      data-testid="editor-errors"
    >
      <div className="flex items-center justify-between gap-4">
        <div
          className="flex items-center gap-2 cursor-pointer flex-1"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <span className="text-red-400 font-semibold">
            {errorCount} error{errorCount !== 1 ? "s" : ""}{warningCount > 0 && `, ${warningCount} warning${warningCount !== 1 ? "s" : ""}`}
          </span>
          <span className="text-foreground0">
            {isExpanded ? "▼" : "▶"}
          </span>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-3 space-y-2 max-h-32 overflow-y-auto">
          {errors.map((error, idx) => (
            <div
              key={idx}
              className={`flex gap-2 text-xs ${
                error.severity === "error"
                  ? "text-red-400"
                  : "text-yellow-400"
              }`}
              data-testid={`error-${idx}`}
            >
              <span className="font-mono text-foreground0 min-w-[150px]">
                {error.path}:
              </span>
              <span>{error.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
