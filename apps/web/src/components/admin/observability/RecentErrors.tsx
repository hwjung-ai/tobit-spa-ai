"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

interface Error {
  exec_id: string;
  rule_id: string;
  rule_name: string;
  triggered_at: string;
  error_message: string | null;
  duration_ms: number;
}

interface ErrorsData {
  timeline: Array<{ timestamp: string; error_count: number }>;
  error_distribution: Record<string, number>;
  recent_errors: Error[];
  period: string;
  total_errors: number;
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

  const getSeverityColor = (message: string | null): string => {
    if (!message) return "color: var(--muted-foreground)";
    if (message.toLowerCase().includes("timeout")) return "color: rgba(251, 146, 60, 1)";
    if (message.toLowerCase().includes("connection")) return "color: rgba(251, 146, 60, 1)";
    if (message.toLowerCase().includes("validation")) return "color: rgba(250, 204, 21, 1)";
    return "color: var(--muted-foreground)";
  };

  const getSeverityBgColor = (message: string | null): string => {
    if (!message) return "background-color: rgba(30, 41, 59, 0.3)";
    if (message.toLowerCase().includes("timeout")) return "background-color: rgba(127, 29, 29, 0.2); border-color: rgba(127, 29, 29, 0.5)";
    if (message.toLowerCase().includes("connection")) return "background-color: rgba(124, 45, 18, 0.2); border-color: rgba(124, 45, 18, 0.5)";
    if (message.toLowerCase().includes("validation")) return "background-color: rgba(250, 204, 21, 0.2); border-color: rgba(250, 204, 21, 0.5)";
    return "background-color: rgba(30, 41, 59, 0.3)";
  };

  if (loading) {
    return (
      <div className="rounded-2xl border p-6 text-sm" style={{ borderColor: "rgba(51, 65, 85, 0.7)", backgroundColor: "rgba(15, 23, 42, 0.6)", color: "var(--muted-foreground)" }}>
        Loading recent errors...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border p-6 text-sm" style={{ borderColor: "rgba(159, 18, 57, 0.7)", backgroundColor: "rgba(120, 53, 15, 0.6)", color: "rgba(251, 146, 60, 1)" }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border p-6" style={{ borderColor: "rgba(51, 65, 85, 0.7)", backgroundColor: "rgba(15, 23, 42, 0.6)" }}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>Recent Errors</h3>
        <span className="text-xs uppercase tracking-[0.2em]" style={{ color: "var(--muted-foreground)" }}>
          {errors.length} errors
        </span>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {errors.length === 0 ? (
          <div className="p-6 text-center rounded-lg border" style={{ borderColor: "var(--border)", backgroundColor: "rgba(3, 7, 18, 0.4)" }}>
            <div className="inline-block p-3 rounded-full mb-3" style={{ backgroundColor: "rgba(16, 185, 129, 0.1)" }}>
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
            <p className="text-sm " style={{ color: "var(--muted-foreground)" }}>No errors in the last 24 hours</p>
          </div>
        ) : (
          errors.map((err) => (
            <div
              key={err.exec_id}
              className={`p-4 rounded-lg border cursor-pointer transition ${getSeverityBgColor(
                err.error_message
              )}`}
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
                    <div
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${getSeverityColor(
                        err.error_message
                      ).replace("text-", "bg-")}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-semibold truncate">{err.rule_name}</p>
                      <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>
                        {new Date(err.triggered_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                    <span className="text-xs " style={{ color: "var(--muted-foreground)" }}>{err.duration_ms}ms</span>
                    <svg
                      className={`w-4 h-4 text-[var(--muted-foreground)] transition ${
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
                  <p className={`text-xs ${getSeverityColor(err.error_message)} truncate`}>
                    {err.error_message}
                  </p>
                )}
              </button>

              {/* Expanded Details */}
              {expandedId === err.exec_id && (
                <div className="mt-4 pt-4 border-t /50 space-y-3" style={{ borderColor: "var(--border)" }}>
                  <div>
                    <p className="text-xs  mb-1" style={{ color: "var(--muted-foreground)" }}>Execution ID</p>
                    <p className="text-xs font-mono  break-all" style={{ color: "var(--foreground-secondary)" }}>
                      {err.exec_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs  mb-1" style={{ color: "var(--muted-foreground)" }}>Rule ID</p>
                    <p className="text-xs font-mono  break-all" style={{ color: "var(--foreground-secondary)" }}>
                      {err.rule_id}
                    </p>
                  </div>
                  {err.error_message && (
                    <div>
                      <p className="text-xs  mb-1" style={{ color: "var(--muted-foreground)" }}>Error Message</p>
                      <p className={`text-xs font-mono ${getSeverityColor(err.error_message)} break-words`}>
                        {err.error_message}
                      </p>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className=" mb-1" style={{ color: "var(--muted-foreground)" }}>Duration</p>
                      <p className="text-white font-semibold">{err.duration_ms}ms</p>
                    </div>
                    <div>
                      <p className=" mb-1" style={{ color: "var(--muted-foreground)" }}>Timestamp</p>
                      <p className="text-white font-semibold">
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
