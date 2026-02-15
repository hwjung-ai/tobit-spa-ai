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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  return (
    <div className="space-y-6">
      <section className="ui-box">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              Function Comparison
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Compare simulation outputs across different functions side by side.
            </p>
          </div>
          <button
            onClick={() => void runComparison()}
            disabled={loading}
            className="btn-primary px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Running..." : "Re-run"}
          </button>
        </div>
      </section>

      {loading ? (
        <section className="ui-box text-center text-muted-standard">
          Running comparison...
        </section>
      ) : error ? (
        <section className="alert-box alert-error">
          <p>{error}</p>
        </section>
      ) : (
        <>
          <section className="ui-box">
            <h2 className="section-title">
              Confidence Comparison
            </h2>
            <div className="mt-4 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                  <XAxis dataKey="function" stroke="var(--border-muted)" />
                  <YAxis stroke="var(--border-muted)" />
                  <Tooltip />
                  <Bar dataKey="confidence" fill="var(--primary)" name="Confidence %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            {kpiNames.map((kpi) => (
              <section key={kpi} className="ui-box">
                <h2 className="section-title">
                  {kpi.replace(/([A-Z])/g, " $1").trim()} Comparison
                </h2>
                <div className="mt-4 h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                      <XAxis dataKey="function" stroke="var(--border-muted)" />
                      <YAxis stroke="var(--border-muted)" />
                      <Tooltip />
                      <Bar dataKey={kpi} fill="var(--warning)" name={kpi} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            ))}
          </div>

          <section className="ui-box">
            <h2 className="section-title">
              Detailed Results
            </h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-variant">
                    <th className="px-4 py-2 text-left text-muted-foreground">
                      Function
                    </th>
                    <th className="px-4 py-2 text-right text-muted-foreground">
                      Confidence
                    </th>
                    <th className="px-4 py-2 text-right text-muted-foreground">
                      Latency (ms)
                    </th>
                    <th className="px-4 py-2 text-right text-muted-foreground">
                      Error Rate (%)
                    </th>
                    <th className="px-4 py-2 text-right text-muted-foreground">
                      Throughput (rps)
                    </th>
                    <th className="px-4 py-2 text-right text-muted-foreground">
                      Cost (USD/h)
                    </th>
                    <th className="px-4 py-2 text-center text-muted-foreground">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row) => (
                    <tr key={row.key} className="border-b border-variant">
                      <td className="px-4 py-2 text-foreground">
                        {row.function}
                      </td>
                      <td className="px-4 py-2 text-right text-primary">
                        {row.confidence.toFixed(0)}%
                      </td>
                      <td className="px-4 py-2 text-right text-foreground">
                        {row.latency.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right text-foreground">
                        {row.errorRate.toFixed(3)}
                      </td>
                      <td className="px-4 py-2 text-right text-foreground">
                        {row.throughput.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right text-foreground">
                        {row.cost.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span
                          className={cn(
                            "rounded-md px-2 py-1 text-xs font-semibold",
                            row.success ? "bg-success/40 text-success" : "bg-error/40 text-error",
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

          <section className="ui-box">
            <h2 className="section-title">
              Baseline vs Simulated
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="ui-subbox">
                <p className="text-xs text-muted-foreground">
                  Baseline Latency
                </p>
                <p className="text-2xl font-semibold text-foreground">
                  {baseline.latency_ms || 50} ms
                </p>
              </div>
              <div className="ui-subbox">
                <p className="text-xs text-muted-foreground">
                  Assumptions
                </p>
                <p className="text-sm text-muted-foreground">
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
