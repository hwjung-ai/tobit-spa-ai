/**
 * Fixed error banner for displaying form validation errors
 * Displays at the top of the form and can be dismissed
 */

import { useEffect, useState } from "react";

interface ErrorBannerProps {
  title?: string;
  errors: string[];
  warnings?: string[];
  onDismiss?: () => void;
  autoDismissMs?: number;
}

export default function ErrorBanner({
  title = "Validation Error",
  errors,
  warnings = [],
  onDismiss,
  autoDismissMs = 0,
}: ErrorBannerProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (errors.length === 0 && warnings.length === 0) {
      setIsVisible(false);
      return;
    }

    setIsVisible(true);

    if (autoDismissMs > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
      }, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [errors, warnings, autoDismissMs]);

  if (!isVisible || (errors.length === 0 && warnings.length === 0)) {
    return null;
  }

  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0;

  return (
    <div
      className={`sticky top-0 z-40 rounded-xl border p-4 ${
        hasErrors
          ? "border-rose-800/50 bg-rose-950/40"
          : "border-yellow-800/50 bg-yellow-950/40"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3
            className={`text-sm font-semibold ${
              hasErrors ? "text-rose-300" : "text-yellow-300"
            }`}
          >
            {title}
          </h3>

          {errors.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-rose-200">
              {errors.map((error, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="text-rose-400">✕</span>
                  <span>{error}</span>
                </li>
              ))}
            </ul>
          )}

          {warnings.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-yellow-200">
              {warnings.map((warning, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="text-yellow-400">!</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {onDismiss && (
          <button
            onClick={() => {
              setIsVisible(false);
              onDismiss();
            }}
            className="error-banner-dismiss-button"
            title="Dismiss"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
