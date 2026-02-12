"use client";

import { ReactNode } from "react";

interface FormFieldGroupProps {
  label: string;
  error?: string;
  required?: boolean;
  help?: string;
  children: ReactNode;
}

export function FormFieldGroup({
  label,
  error,
  required = false,
  help,
  children,
}: FormFieldGroupProps) {
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--foreground)" }}>
        {label}
        {required && <span className="text-rose-400">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-rose-400">{error}</p>}
      {help && !error && <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>{help}</p>}
    </div>
  );
}
