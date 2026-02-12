"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

interface RuleStats {
  rule_id: string;
  rule_name: string;
  is_active: boolean;
  execution_count: number;
  error_count: number;
  error_rate: number;
  avg_duration_ms: number;
}

interface RuleStatsCardProps {
  onRuleSelect?: (ruleId: string) => void;
}

export default function RuleStatsCard({ onRuleSelect }: RuleStatsCardProps) {
  const [rules, setRules] = useState<RuleStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRulesPerformance = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch("/cep/rules/performance?limit=10");
        setRules(response.data?.rules || []);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch rules";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchRulesPerformance();
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border p-6 text-sm" style={{ borderColor: "rgba(51, 65, 85, 0.7)", backgroundColor: "rgba(15, 23, 42, 0.6)", color: "var(--muted-foreground)" }}>
        Loading rule statistics...
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
        <h3 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>Rule Performance</h3>
        <span className="text-xs uppercase tracking-[0.2em]" style={{ color: "var(--muted-foreground)" }}>Last 7 days</span>
      </div>

      <div className="space-y-4">
        {rules.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>No rules found</p>
        ) : (
          rules.map((rule) => (
            <button
              key={rule.rule_id}
              onClick={() => onRuleSelect?.(rule.rule_id)}
              className="w-full text-left p-4 rounded-lg border transition"
              style={{ borderColor: "var(--border)", backgroundColor: "rgba(3, 7, 18, 0.4)" }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium truncate" style={{ color: "var(--foreground)" }}>{rule.rule_name}</span>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      rule.is_active
                        ? ""
                        : ""
                    }`}
                    style={rule.is_active ? { backgroundColor: "rgba(16, 185, 129, 0.2)", color: "rgba(52, 211, 153, 1)" } : { backgroundColor: "rgba(30, 41, 59, 0.5)", color: "var(--muted-foreground)" }}
                  >
                    {rule.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  {rule.execution_count} executions
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span style={{ color: "var(--muted-foreground)" }}>Errors:</span>
                  <span className="font-semibold" style={{ color: "var(--foreground)" }}>
                    {rule.error_count}
                    <span className="ml-1" style={{ color: "var(--muted-foreground)" }}>
                      ({(rule.error_rate * 100).toFixed(1)}%)
                    </span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Avg Duration:</span>
                  <span className="text-white font-semibold">
                    {rule.avg_duration_ms.toFixed(2)}ms
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full ${
                        rule.error_rate > 0.1
                          ? "bg-rose-500"
                          : rule.error_rate > 0.05
                          ? "bg-amber-500"
                          : "bg-emerald-500"
                      }`}
                      style={{ width: `${rule.error_rate * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
