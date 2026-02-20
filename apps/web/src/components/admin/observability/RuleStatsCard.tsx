"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";
import { cn } from "@/lib/utils";

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
        const response = await authenticatedFetch<{ data?: { rules?: RuleStats[] } }>(
          "/cep/rules/performance?limit=10"
        );
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
      <div className="rounded-2xl border border-variant bg-surface-base/60 p-6 text-sm text-muted-foreground">
        Loading rule statistics...
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
        <h3 className="text-lg font-semibold text-foreground">Rule Performance</h3>
        <span className="text-sm uppercase tracking-wider text-muted-foreground">Last 7 days</span>
      </div>

      <div className="space-y-4">
        {rules.length === 0 ? (
          <p className="text-sm text-muted-foreground">No rules found</p>
        ) : (
          rules.map((rule) => (
            <button
              key={rule.rule_id}
              onClick={() => onRuleSelect?.(rule.rule_id)}
              className="w-full text-left p-4 rounded-lg border border-variant bg-surface-base/40 transition"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium truncate text-foreground">{rule.rule_name}</span>
                  <span
                    className={cn(
                      "text-xs px-2 py-1 rounded",
                      rule.is_active
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-surface-elevated0/50 text-muted-foreground"
                    )}
                  >
                    {rule.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {rule.execution_count} executions
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Errors:</span>
                  <span className="font-semibold text-foreground">
                    {rule.error_count}
                    <span className="ml-1 text-muted-foreground">
                      ({(rule.error_rate * 100).toFixed(1)}%)
                    </span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Avg Duration:</span>
                  <span className="text-foreground dark:text-foreground font-semibold">
                    {rule.avg_duration_ms.toFixed(2)}ms
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-surface-elevated overflow-hidden">
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
