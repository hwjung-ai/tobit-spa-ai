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

  const sectionClass = "rounded-2xl border p-5 shadow-sm";
  const cardClass = "rounded-lg border p-4";

  return (
    <div className="space-y-6">
      <section
        style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
        className={sectionClass}
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 style={{ color: "var(--foreground)" }} className="text-2xl font-semibold">
              Function Comparison
            </h1>
            <p className="mt-2 text-sm" style={{ color: "var(--muted-foreground)" }}>
              Compare simulation outputs across different functions side by side.
            </p>
          </div>
          <button
            onClick={() => void runComparison()}
            disabled={loading}
            style={{ backgroundColor: "var(--primary)" }}
            className="rounded-md px-4 py-2 text-sm font-semibold uppercase tracking-wider text-white transition disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Running..." : "Re-run"}
          </button>
        </div>
      </section>

      {loading ? (
        <section
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--surface-overlay)",
            color: "var(--muted-foreground)",
          }}
          className={cn(sectionClass, "text-center")}
        >
          Running comparison...
        </section>
      ) : error ? (
        <section
          style={{ borderColor: "var(--error)", backgroundColor: "rgba(var(--error-rgb), 0.1)" }}
          className="rounded-2xl border p-5"
        >
          <p style={{ color: "var(--error)" }}>{error}</p>
        </section>
      ) : (
        <>
          <section
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
            className={sectionClass}
          >
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
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
              <section
                key={kpi}
                style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
                className={sectionClass}
              >
                <h2
                  style={{ color: "var(--muted-foreground)" }}
                  className="text-sm font-semibold uppercase tracking-wider"
                >
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

          <section
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
            className={sectionClass}
          >
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
              Detailed Results
            </h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderColor: "var(--border)" }} className="border-b">
                    <th
                      className="px-4 py-2 text-left"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Function
                    </th>
                    <th
                      className="px-4 py-2 text-right"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Confidence
                    </th>
                    <th
                      className="px-4 py-2 text-right"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Latency (ms)
                    </th>
                    <th
                      className="px-4 py-2 text-right"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Error Rate (%)
                    </th>
                    <th
                      className="px-4 py-2 text-right"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Throughput (rps)
                    </th>
                    <th
                      className="px-4 py-2 text-right"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Cost (USD/h)
                    </th>
                    <th
                      className="px-4 py-2 text-center"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row) => (
                    <tr key={row.key} style={{ borderColor: "var(--border)" }} className="border-b">
                      <td className="px-4 py-2" style={{ color: "var(--foreground)" }}>
                        {row.function}
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: "var(--primary)" }}>
                        {row.confidence.toFixed(0)}%
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: "var(--foreground)" }}>
                        {row.latency.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: "var(--foreground)" }}>
                        {row.errorRate.toFixed(3)}
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: "var(--foreground)" }}>
                        {row.throughput.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right" style={{ color: "var(--foreground)" }}>
                        {row.cost.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span
                          className={cn(
                            "rounded-md px-2 py-1 text-xs font-semibold",
                            row.success ? "text-white" : "",
                          )}
                          style={
                            row.success
                              ? {
                                  backgroundColor: "rgba(var(--success-rgb), 0.4)",
                                  color: "var(--success)",
                                }
                              : {
                                  backgroundColor: "rgba(var(--error-rgb), 0.4)",
                                  color: "var(--error)",
                                }
                          }
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

          <section
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
            className={sectionClass}
          >
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
              Baseline vs Simulated
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div
                style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
                className={cardClass}
              >
                <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                  Baseline Latency
                </p>
                <p style={{ color: "var(--foreground)" }} className="text-2xl font-semibold">
                  {baseline.latency_ms || 50} ms
                </p>
              </div>
              <div
                style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
                className={cardClass}
              >
                <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                  Assumptions
                </p>
                <p style={{ color: "var(--foreground-secondary)" }} className="text-sm">
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
