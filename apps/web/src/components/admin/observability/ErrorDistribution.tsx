"use client";

import { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { authenticatedFetch } from "@/lib/apiClient";

interface ErrorDistribution {
  [key: string]: number;
}

interface ErrorData {
  timeline: Array<{ timestamp: string; error_count: number }>;
  error_distribution: ErrorDistribution;
  recent_errors: Array<{
    exec_id: string;
    rule_id: string;
    rule_name: string;
    triggered_at: string;
    error_message: string | null;
    duration_ms: number;
  }>;
  period: string;
  total_errors: number;
}

const colors: Record<string, string> = {
  timeout: "#f87171",
  connection: "#fb923c",
  validation: "#facc15",
  authentication: "#a78bfa",
  other: "#94a3b8",
};

const colorList = ["#f87171", "#fb923c", "#facc15", "#a78bfa", "#94a3b8"];

export default function ErrorDistribution() {
  const [data, setData] = useState<ErrorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch("/cep/errors/timeline?period=24h");
        setData(response.data || null);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch error data";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border /70  p-6  text-sm" style={{borderColor: "var(--border)", color: "var(--muted-foreground)", backgroundColor: "var(--surface-overlay)"}}>
        Loading error distribution...
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

  if (!data) return null;

  const pieData = Object.entries(data.error_distribution).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <div className="rounded-2xl border /70  p-6" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Error Distribution</h3>
        <span className="text-sm uppercase tracking-[0.2em] " style={{color: "var(--muted-foreground)"}}>Last 24h</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="flex justify-center">
          {pieData.length === 0 ? (
            <div className="h-64 flex items-center justify-center  text-sm" style={{color: "var(--muted-foreground)"}}>
              No errors
            </div>
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name} (${value})`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={colors[entry.name] || colorList[index % colorList.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                    formatter={(value) => value}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Error Type Details */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-white mb-4">Error Types</h4>
          {Object.entries(data.error_distribution).length === 0 ? (
            <p className="text-sm " style={{color: "var(--muted-foreground)"}}>No errors recorded</p>
          ) : (
            Object.entries(data.error_distribution).map(([type, count]) => {
              const total = data.total_errors || 1;
              const percentage = (count / total) * 100;

              return (
                <div key={type} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{backgroundColor: colors[type] || "#94a3b8"}}
                      />
                      <span className="text-sm text-white capitalize font-medium">
                        {type}
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-white font-semibold">{count}</span>
                      <span className=" ml-2" style={{color: "var(--muted-foreground)"}}>({percentage.toFixed(1)}%)</span>
                    </div>
                  </div>

                  <div className="h-2 rounded-full  overflow-hidden" style={{backgroundColor: "var(--surface-elevated)"}}>
                    <div
                      className="h-full"
                      style={{backgroundColor: colors[type] || "#94a3b8", width: `${percentage}%`}}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="mt-6 p-4 rounded-lg /40 border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
        <p className="text-xs  mb-2" style={{color: "var(--muted-foreground)"}}>Total Errors</p>
        <p className="text-3xl font-semibold text-white">{data.total_errors}</p>
        <p className="text-xs  mt-2" style={{color: "var(--muted-foreground)"}}>
          in {data.period}
        </p>
      </div>
    </div>
  );
}
