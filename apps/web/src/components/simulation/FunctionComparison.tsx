"use client";

import { useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { authenticatedFetch } from "@/lib/apiClient";
import { cn } from "@/lib/utils";

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
}

interface FunctionComparisonProps {
  functionIds: string[];
  baseline: Record<string, number>;
  assumptions: Record<string, number>;
}

export default function FunctionComparison({
  functionIds,
  baseline,
  assumptions,
}: FunctionComparisonProps) {
  const [results, setResults] = useState<Record<string, FunctionExecutionResult>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const runComparison = useCallback(async () => {
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
          },
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
  }, [assumptions, baseline, functionIds]);

  useEffect(() => {
    void runComparison();
  }, [runComparison]);

  const comparisonData = Object.entries(results).map(([functionId, result]) => {
    const output = result.outputs || {};
    return {
      key: functionId,
      function: functionId
        .split("_")
        .slice(-1)[0]
        .replace(/^\w/, (c: string) => c.toUpperCase()),
      confidence: result.confidence * 100,
      latency:
        output.latency_ms || output.simulated_value || output.prediction || output.forecast || 0,
      errorRate: output.error_rate_pct || 0,
      throughput: output.throughput_rps || 0,
      cost: output.cost_usd_hour || 0,
      success: result.success,
    };
  });

  const kpiNames: Array<"latency" | "errorRate" | "throughput" | "cost"> = [
    "latency",
    "errorRate",
    "throughput",
    "cost",
  ];

  const sectionClass =
    "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900/90";
  const cardClass =
    "rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40";

  return (
    <div className="space-y-6">
      <section className={sectionClass}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
              Function Comparison
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Compare simulation outputs across different functions side by side.
            </p>
          </div>
          <button
            onClick={() => void runComparison()}
            disabled={loading}
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Running..." : "Re-run"}
          </button>
        </div>
      </section>

      {loading ? (
        <section className={cn(sectionClass, "text-center text-slate-600 dark:text-slate-400")}>
          Running comparison...
        </section>
      ) : error ? (
        <section className="rounded-2xl border border-rose-300 bg-rose-50 p-5 dark:border-rose-800 dark:bg-rose-950/20">
          <p className="text-rose-700 dark:text-rose-300">{error}</p>
        </section>
      ) : (
        <>
          <section className={sectionClass}>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Confidence Comparison
            </h2>
            <div className="mt-4 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
                  <XAxis dataKey="function" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="confidence" fill="#0ea5e9" name="Confidence %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            {kpiNames.map((kpi) => (
              <section key={kpi} className={sectionClass}>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  {kpi.replace(/([A-Z])/g, " $1").trim()} Comparison
                </h2>
                <div className="mt-4 h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#64748b" />
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

          <section className={sectionClass}>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Detailed Results
            </h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800">
                    <th className="px-4 py-2 text-left text-slate-600 dark:text-slate-400">
                      Function
                    </th>
                    <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-400">
                      Confidence
                    </th>
                    <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-400">
                      Latency (ms)
                    </th>
                    <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-400">
                      Error Rate (%)
                    </th>
                    <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-400">
                      Throughput (rps)
                    </th>
                    <th className="px-4 py-2 text-right text-slate-600 dark:text-slate-400">
                      Cost (USD/h)
                    </th>
                    <th className="px-4 py-2 text-center text-slate-600 dark:text-slate-400">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row) => (
                    <tr
                      key={row.key}
                      className="border-b border-slate-200/70 dark:border-slate-800/70"
                    >
                      <td className="px-4 py-2 text-slate-900 dark:text-slate-100">
                        {row.function}
                      </td>
                      <td className="px-4 py-2 text-right text-sky-500 dark:text-sky-400">
                        {row.confidence.toFixed(0)}%
                      </td>
                      <td className="px-4 py-2 text-right text-slate-900 dark:text-slate-100">
                        {row.latency.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-900 dark:text-slate-100">
                        {row.errorRate.toFixed(3)}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-900 dark:text-slate-100">
                        {row.throughput.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-900 dark:text-slate-100">
                        {row.cost.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span
                          className={cn(
                            "rounded-md px-2 py-1 text-xs font-semibold",
                            row.success
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                              : "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
                          )}
                        >
                          {row.success ? "Success" : "Failed"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={sectionClass}>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Baseline vs Simulated
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className={cardClass}>
                <p className="text-xs text-slate-600 dark:text-slate-400">Baseline Latency</p>
                <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                  {baseline.latency_ms || 50} ms
                </p>
              </div>
              <div className={cardClass}>
                <p className="text-xs text-slate-600 dark:text-slate-400">Assumptions</p>
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  Traffic: {assumptions.traffic_change_pct || 0}% | CPU:{" "}
                  {assumptions.cpu_change_pct || 0}% | Memory: {assumptions.memory_change_pct || 0}%
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
