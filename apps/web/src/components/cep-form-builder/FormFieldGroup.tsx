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
      <label className="form-field-label-text">
        {label}
        {required && <span className="text-rose-400">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-rose-400">{error}</p>}
      {help && !error && <p className="form-field-help">{help}</p>}
    </div>
  );
}
