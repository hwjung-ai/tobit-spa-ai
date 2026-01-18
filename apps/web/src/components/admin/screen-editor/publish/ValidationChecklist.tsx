"use client";

import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export interface CheckResult {
  name: string;
  status: "pass" | "fail" | "warn";
  errors?: string[];
  warnings?: string[];
}

interface ValidationChecklistProps {
  checks: CheckResult[];
}

export default function ValidationChecklist({ checks }: ValidationChecklistProps) {
  return (
    <div className="space-y-3 py-4">
      {checks.map((check, idx) => {
        const bgColor =
          check.status === "pass"
            ? "bg-green-50"
            : check.status === "fail"
            ? "bg-red-50"
            : "bg-amber-50";

        const borderColor =
          check.status === "pass"
            ? "border-green-200"
            : check.status === "fail"
            ? "border-red-200"
            : "border-amber-200";

        const textColor =
          check.status === "pass"
            ? "text-green-700"
            : check.status === "fail"
            ? "text-red-700"
            : "text-amber-700";

        const errorTextColor =
          check.status === "fail"
            ? "text-red-700"
            : "text-amber-700";

        return (
          <div
            key={idx}
            className={`p-3 rounded border ${bgColor} ${borderColor}`}
          >
            <div className="flex items-center gap-2">
              {check.status === "pass" && (
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
              )}
              {check.status === "fail" && (
                <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              )}
              {check.status === "warn" && (
                <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
              )}
              <span className={`font-medium text-sm ${textColor}`}>
                {check.name}
              </span>
            </div>

            {check.errors && check.errors.length > 0 && (
              <ul className="mt-2 text-xs space-y-1 pl-6 list-disc">
                {check.errors.map((err, i) => (
                  <li key={i} className={errorTextColor}>
                    {err}
                  </li>
                ))}
              </ul>
            )}

            {check.warnings && check.warnings.length > 0 && (
              <ul className="mt-2 text-xs space-y-1 pl-6 list-disc">
                {check.warnings.map((warn, i) => (
                  <li key={i} className={errorTextColor}>
                    {warn}
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
