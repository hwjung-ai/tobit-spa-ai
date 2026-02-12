"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

interface SystemStats {
  total_rules: number;
  active_rules: number;
  inactive_rules: number;
  today_execution_count: number;
  today_error_count: number;
  today_error_rate: number;
  today_avg_duration_ms: number;
  last_24h_execution_count: number;
  timestamp: string;
}

export default function SystemHealthChart() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch("/cep/stats/summary");

        if (!response?.data?.stats) {
          throw new Error("Invalid response format");
        }

        setStats(response.data.stats);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch stats";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const getHealthColor = (value: number, isRate: boolean = false) => {
    if (isRate) {
      if (value < 0.05) return "bg-emerald-500";
      if (value < 0.1) return "bg-amber-500";
      return "bg-rose-500";
    }
    return "bg-sky-500";
  };

  const getHealthTextColor = (value: number, isRate: boolean = false) => {
    if (isRate) {
      if (value < 0.05) return "text-emerald-400";
      if (value < 0.1) return "text-amber-400";
      return "text-rose-400";
    }
    return "text-sky-400";
  };

  if (loading) {
    return (
      <div className="rounded-2xl border /70  p-6  text-sm" style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-overlay)" }}>
        Loading system health...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-800/70 bg-rose-900/60 p-6 text-rose-400 text-sm">
        Error: {error}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border /70  p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
          <p className="text-xs uppercase tracking-[0.2em]  mb-2" style={{ color: "var(--muted-foreground)" }}>Total Rules</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-semibold text-white">{stats.total_rules}</p>
            <span className="text-xs " style={{ color: "var(--muted-foreground)" }}>
              {stats.active_rules} active
            </span>
          </div>
          <div className="mt-3 h-2 rounded-full  overflow-hidden" style={{ backgroundColor: "var(--surface-elevated)" }}>
            <div
              className="h-full bg-sky-500"
              style={{
                width: `${stats.total_rules > 0 ? (stats.active_rules / stats.total_rules) * 100 : 0}%`,
              }}
            />
          </div>
        </div>

        <div className="rounded-2xl border /70  p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
          <p className="text-xs uppercase tracking-[0.2em]  mb-2" style={{ color: "var(--muted-foreground)" }}>Today Executions</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-semibold text-white">
              {stats.today_execution_count.toLocaleString()}
            </p>
            <span className={`text-xs ${getHealthTextColor(stats.today_error_rate, true)}`}>
              {(stats.today_error_rate * 100).toFixed(1)}% error
            </span>
          </div>
          <div className="mt-3 h-2 rounded-full  overflow-hidden" style={{ backgroundColor: "var(--surface-elevated)" }}>
            <div
              className={getHealthColor(stats.today_error_rate, true)}
              style={{
                width: `${Math.min(stats.today_error_rate * 100, 100)}%`,
              }}
            />
          </div>
        </div>

        <div className="rounded-2xl border /70  p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
          <p className="text-xs uppercase tracking-[0.2em]  mb-2" style={{ color: "var(--muted-foreground)" }}>Error Count</p>
          <div className="flex items-baseline gap-2">
            <p className={`text-3xl font-semibold ${
              stats.today_error_count > 0 ? "text-rose-400" : "text-emerald-400"
            }`}>
              {stats.today_error_count}
            </p>
            <span className="text-xs " style={{ color: "var(--muted-foreground)" }}>errors today</span>
          </div>
          <div className="mt-3 h-2 rounded-full  overflow-hidden" style={{ backgroundColor: "var(--surface-elevated)" }}>
            <div
              className={stats.today_error_count > 0 ? "bg-rose-500" : "bg-emerald-500"}
              style={{
                width: `${stats.today_error_count > 0 ? 100 : 0}%`,
              }}
            />
          </div>
        </div>

        <div className="rounded-2xl border /70  p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
          <p className="text-xs uppercase tracking-[0.2em]  mb-2" style={{ color: "var(--muted-foreground)" }}>Avg Duration</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-semibold text-white">
              {stats.today_avg_duration_ms.toFixed(0)}
            </p>
            <span className="text-xs " style={{ color: "var(--muted-foreground)" }}>ms</span>
          </div>
          <div className="mt-3 h-2 rounded-full  overflow-hidden" style={{ backgroundColor: "var(--surface-elevated)" }}>
            <div
              className="bg-purple-500"
              style={{
                width: `${Math.min((stats.today_avg_duration_ms / 1000) * 100, 100)}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Health Status */}
      <div className="rounded-2xl border /70  p-6" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
        <h3 className="text-lg font-semibold text-white mb-4">System Health Status</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm " style={{ color: "var(--muted-foreground)" }}>Rule Activation Rate</span>
            <div className="flex items-center gap-2">
              <div className="w-24 h-2 rounded-full  overflow-hidden" style={{ backgroundColor: "var(--surface-elevated)" }}>
                <div
                  className="h-full bg-sky-500"
                  style={{
                    width: `${stats.total_rules > 0 ? (stats.active_rules / stats.total_rules) * 100 : 0}%`,
                  }}
                />
              </div>
              <span className="text-sm text-white font-semibold">
                {stats.total_rules > 0
                  ? ((stats.active_rules / stats.total_rules) * 100).toFixed(0)
                  : 0}%
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm " style={{ color: "var(--muted-foreground)" }}>Error Rate</span>
            <div className="flex items-center gap-2">
              <div className="w-24 h-2 rounded-full  overflow-hidden" style={{ backgroundColor: "var(--surface-elevated)" }}>
                <div
                  className={getHealthColor(stats.today_error_rate, true)}
                  style={{
                    width: `${Math.min(stats.today_error_rate * 100, 100)}%`,
                  }}
                />
              </div>
              <span className={`text-sm font-semibold ${getHealthTextColor(stats.today_error_rate, true)}`}>
                {(stats.today_error_rate * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm " style={{ color: "var(--muted-foreground)" }}>System Status</span>
            <div className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  stats.today_error_rate < 0.05 ? "bg-emerald-500" : "bg-amber-500"
                }`}
              />
              <span className="text-sm text-white font-semibold">
                {stats.today_error_rate < 0.05 ? "Healthy" : "Monitoring"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
