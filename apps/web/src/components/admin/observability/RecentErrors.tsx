"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";
import { cn } from "@/lib/utils";

interface Error {
  exec_id: string;
  rule_id: string;
  rule_name: string;
  triggered_at: string;
  error_message: string | null;
  duration_ms: number;
}

export default function RecentErrors() {
  const [errors, setErrors] = useState<Error[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchErrors = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch("/cep/errors/timeline?period=24h");
        setErrors(response.data?.recent_errors || []);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch errors";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchErrors();
    // Refresh every 60 seconds
    const interval = setInterval(fetchErrors, 60000);
    return () => clearInterval(interval);
  }, []);

  // Get severity text color class based on error message
  const getSeverityColorClass = (message: string | null): string => {
    if (!message) return "text-muted-foreground";
    if (message.toLowerCase().includes("timeout")) return "text-orange-400";
    if (message.toLowerCase().includes("connection")) return "text-orange-400";
    if (message.toLowerCase().includes("validation")) return "text-yellow-400";
    return "text-muted-foreground";
  };

  // Get severity background/border color class based on error message
  const getSeverityBgClass = (message: string | null): string => {
    if (!message) return "bg-surface-elevated0/30 border-slate-500/30";
    if (message.toLowerCase().includes("timeout")) return "bg-red-900/20 border-red-900/50";
    if (message.toLowerCase().includes("connection")) return "bg-orange-900/20 border-orange-900/50";
    if (message.toLowerCase().includes("validation")) return "bg-yellow-500/20 border-yellow-500/50";
    return "bg-surface-elevated0/30 border-slate-500/30";
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-variant bg-surface-base/60 p-6 text-sm text-muted-foreground">
        Loading recent errors...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-500/50 bg-amber-900/40 p-6 text-sm text-amber-300">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-variant bg-surface-base/60 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground">Recent Errors</h3>
        <span className="text-sm uppercase tracking-wider text-muted-foreground">
          {errors.length} errors
        </span>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {errors.length === 0 ? (
          <div className="p-6 text-center rounded-lg border border-variant bg-surface-base/40">
            <div className="inline-block p-3 rounded-full mb-3 bg-emerald-500/10">
              <svg
                className="w-6 h-6 text-emerald-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-sm text-muted-foreground">No errors in the last 24 hours</p>
          </div>
        ) : (
          errors.map((err) => (
            <div
              key={err.exec_id}
              className={cn(
                "p-4 rounded-lg border cursor-pointer transition",
                getSeverityBgClass(err.error_message)
              )}
            >
              {/* Header */}
              <button
                onClick={() =>
                  setExpandedId(expandedId === err.exec_id ? null : err.exec_id)
                }
                className="w-full text-left"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3 flex-1">
                    <div className={cn("w-2 h-2 rounded-full flex-shrink-0", getSeverityColorClass(err.error_message).replace("text-", "bg-"))} />
                    <div className="flex-1 min-w-0">
                      <p className="text-foreground dark:text-foreground font-semibold truncate">{err.rule_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(err.triggered_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                    <span className="text-xs text-muted-foreground">{err.duration_ms}ms</span>
                    <svg
                      className={`w-4 h-4 text-muted-foreground transition ${
                        expandedId === err.exec_id ? "rotate-180" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 14l-7 7m0 0l-7-7m7 7V3"
                      />
                    </svg>
                  </div>
                </div>

                {/* Error Message Preview */}
                {err.error_message && (
                  <p className={cn("text-xs truncate", getSeverityColorClass(err.error_message))}>
                    {err.error_message}
                  </p>
                )}
              </button>

              {/* Expanded Details */}
              {expandedId === err.exec_id && (
                <div className="mt-4 pt-4 border-t border-variant space-y-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Execution ID</p>
                    <p className="text-xs font-mono text-foreground break-all">
                      {err.exec_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Rule ID</p>
                    <p className="text-xs font-mono text-foreground break-all">
                      {err.rule_id}
                    </p>
                  </div>
                  {err.error_message && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Error Message</p>
                      <p className={cn("text-xs font-mono break-words", getSeverityColorClass(err.error_message))}>
                        {err.error_message}
                      </p>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className="text-muted-foreground mb-1">Duration</p>
                      <p className="text-foreground dark:text-foreground font-semibold">{err.duration_ms}ms</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground mb-1">Timestamp</p>
                      <p className="text-foreground dark:text-foreground font-semibold">
                        {new Date(err.triggered_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
