"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis, ResponsiveContainer } from "recharts";

type FunctionCategory = "rule" | "statistical" | "ml" | "domain";

interface FunctionMetadata {
  id: string;
  name: string;
  category: FunctionCategory;
  confidence: number;
  tags: string[];
}

interface FunctionOutput {
  simulated_value?: number;
  prediction?: number;
  forecast?: number;
  latency_ms?: number;
  error_rate_pct?: number;
  throughput_rps?: number;
  cost_usd_hour?: number;
  [key: string]: number | undefined;
}

interface FunctionExecutionResult {
  function_id: string;
  outputs: FunctionOutput;
  confidence: number;
  debug_info: Record<string, unknown>;
  success: boolean;
}

interface Envelope<T> {
  data?: T;
  message?: string;
  detail?: string;
}

interface FunctionComparisonProps {
  functionIds: string[];
  baseline: Record<string, number>;
  assumptions: Record<string, number>;
}

export default function FunctionComparison({ functionIds, baseline, assumptions }: FunctionComparisonProps) {
  const [results, setResults] = useState<Record<string, FunctionExecutionResult>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    runComparison();
  }, [functionIds, baseline, assumptions]);

  const runComparison = async () => {
    setLoading(true);
    setError(null);

    const newResults: Record<string, FunctionExecutionResult> = {};

    for (const functionId of functionIds) {
      try {
        const response = await authenticatedFetch<Envelope<FunctionExecutionResult>>(
          `/api/sim/functions/${functionId}/execute`,
          {
            method: "POST",
            body: JSON.stringify({ baseline, assumptions }),
          }
        );

        if (response.data) {
          newResults[functionId] = response.data;
        }
      } catch (err) {
        console.error(`Failed to execute function ${functionId}`, err);
        newResults[functionId] = {
          function_id: functionId,
          outputs: {},
          confidence: 0,
          debug_info: { error: "Execution failed" },
          success: false,
        };
      }
    }

    setResults(newResults);
    setLoading(false);
  };

  // Prepare comparison chart data
  const comparisonData = Object.entries(results).map(([functionId, result]) => {
    const output = result.outputs || {};
    return {
      function: functionId.split("_").slice(-1)[0].replace(/^\w/, (c: string) => c.toUpperCase()),
      confidence: result.confidence * 100,
      latency: output.latency_ms || output.simulated_value || output.prediction || output.forecast || 0,
      errorRate: output.error_rate_pct || 0,
      throughput: output.throughput_rps || 0,
      cost: output.cost_usd_hour || 0,
    };
  });

  // Get KPI names for chart
  const kpiNames: (keyof typeof comparisonData[0])[] = ["latency", "errorRate", "throughput", "cost"];

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border  /70 p-6" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">Function Comparison</h1>
            <p className="mt-2 text-sm " style={{ color: "var(--foreground-secondary)" }}>
              Compare simulation outputs across different functions side by side.
            </p>
          </div>
          <button
            onClick={runComparison}
            disabled={loading}
            className="rounded-2xl bg-sky-500/90 px-4 py-2 text-sm font-semibold uppercase tracking-[0.25em] text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:" style={{ backgroundColor: "var(--surface-elevated)" }}
          >
            {loading ? "Running..." : "Re-run"}
          </button>
        </div>
      </section>

      {loading ? (
        <section className="rounded-3xl border   p-12 text-center " style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-overlay)" }}>
          Running comparison...
        </section>
      ) : error ? (
        <section className="rounded-3xl border border-rose-800/40 bg-rose-950/20 p-6">
          <p className="text-rose-300">{error}</p>
        </section>
      ) : (
        <>
          {/* Confidence Comparison */}
          <section className="rounded-3xl border   p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{ color: "var(--foreground-secondary)" }}>Confidence Comparison</h2>
            <div className="mt-4 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="function" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="confidence" fill="#22d3ee" name="Confidence %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* KPI Comparison Charts */}
          <div className="grid gap-4 lg:grid-cols-2">
            {kpiNames.map((kpi) => (
              <section key={kpi} className="rounded-3xl border   p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
                <h2 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{ color: "var(--foreground-secondary)" }}>
                  {kpi.replace(/([A-Z])/g, " $1").trim()} Comparison
                </h2>
                <div className="mt-4 h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="function" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip />
                      <Bar dataKey={kpi} fill="#f59e0b" name={kpi} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            ))}
          </div>

          {/* Detailed Results Table */}
          <section className="rounded-3xl border   p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{ color: "var(--foreground-secondary)" }}>Detailed Results</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b " style={{ borderColor: "var(--border)" }}>
                    <th className="px-4 py-2 text-left " style={{ color: "var(--muted-foreground)" }}>Function</th>
                    <th className="px-4 py-2 text-right " style={{ color: "var(--muted-foreground)" }}>Confidence</th>
                    <th className="px-4 py-2 text-right " style={{ color: "var(--muted-foreground)" }}>Latency (ms)</th>
                    <th className="px-4 py-2 text-right " style={{ color: "var(--muted-foreground)" }}>Error Rate (%)</th>
                    <th className="px-4 py-2 text-right " style={{ color: "var(--muted-foreground)" }}>Throughput (rps)</th>
                    <th className="px-4 py-2 text-right " style={{ color: "var(--muted-foreground)" }}>Cost (USD/h)</th>
                    <th className="px-4 py-2 text-center " style={{ color: "var(--muted-foreground)" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row) => (
                    <tr key={row.function} className="border-b /50" style={{ borderColor: "var(--border)" }}>
                      <td className="px-4 py-2 text-white">{row.function}</td>
                      <td className="px-4 py-2 text-right text-sky-400">{row.confidence.toFixed(0)}%</td>
                      <td className="px-4 py-2 text-right text-white">{row.latency.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right text-white">{row.errorRate.toFixed(3)}</td>
                      <td className="px-4 py-2 text-right text-white">{row.throughput.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right text-white">{row.cost.toFixed(2)}</td>
                      <td className="px-4 py-2 text-center">
                        <span className={`text-xs px-2 py-1 rounded ${
                          results[Object.keys(results).find(k => k.endsWith(row.function) || k.includes(row.function.toLowerCase()))]?.success
                            ? "bg-emerald-500/20 text-emerald-300"
                            : "bg-rose-500/20 text-rose-300"
                        }`}>
                          {results[Object.keys(results).find(k => k.endsWith(row.function) || k.includes(row.function.toLowerCase()))]?.success ? "Success" : "Failed"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Baseline vs Simulated */}
          <section className="rounded-3xl border   p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{ color: "var(--foreground-secondary)" }}>Baseline vs Simulated</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border  /50 p-4" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>Baseline Latency</p>
                <p className="text-2xl font-semibold text-white">{baseline.latency_ms || 50} ms</p>
              </div>
              <div className="rounded-xl border  /50 p-4" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>Assumptions</p>
                <p className="text-sm " style={{ color: "var(--foreground-secondary)" }}>
                  Traffic: {assumptions.traffic_change_pct || 0}% |
                  CPU: {assumptions.cpu_change_pct || 0}% |
                  Memory: {assumptions.memory_change_pct || 0}%
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
