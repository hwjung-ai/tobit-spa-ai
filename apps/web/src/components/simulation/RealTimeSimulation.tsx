"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { cn } from "@/lib/utils";

type Strategy = "rule" | "stat" | "ml" | "dl";

interface SimulationProgress {
  step: string;
  message: string;
  current?: number;
  total?: number;
  strategy?: string;
}

interface BaselineData {
  kpis: Record<string, number>;
  source: string;
  dataQuality?: {
    metrics_available: boolean;
    using_fallback: boolean;
    note: string;
  };
}

interface KPIResult {
  kpi: string;
  baseline: number;
  simulated: number;
  unit: string;
}

interface CompleteResult {
  simulation: {
    scenario_id: string;
    strategy: Strategy;
    confidence: number;
    kpis: KPIResult[];
    explanation: string;
  };
  summary: string;
  timing?: {
    total_ms: number;
    planning_ms: number;
    baseline_loading_ms: number;
    strategy_execution_ms: number;
  };
  data_source?: string;
}

interface RealTimeSimulationProps {
  question: string;
  scenarioType: string;
  strategy: Strategy;
  horizon: string;
  service: string;
  assumptions: Record<string, number>;
}

export default function RealTimeSimulation({
  question,
  scenarioType,
  strategy,
  horizon,
  service,
  assumptions,
}: RealTimeSimulationProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState<SimulationProgress | null>(null);
  const [baseline, setBaseline] = useState<BaselineData | null>(null);
  const [kpis, setKpis] = useState<KPIResult[]>([]);
  const [result, setResult] = useState<CompleteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    setKpis([]);
    setResult(null);
    setError(null);
    reconnectAttemptsRef.current = 0;

    const closeCurrentSource = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const connect = () => {
      const params = new URLSearchParams({
        question,
        scenario_type: scenarioType,
        strategy,
        horizon,
        service,
        assumptions: JSON.stringify(assumptions),
      });

      const eventSource = new EventSource(`/api/sim/stream/run?${params.toString()}`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.addEventListener("progress", (e: MessageEvent) => {
        try {
          setProgress(JSON.parse(e.data));
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("baseline", (e: MessageEvent) => {
        try {
          setBaseline(JSON.parse(e.data));
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("kpi", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          setKpis((prev) => {
            const next = [...prev, data.kpi];
            const existing = next.findIndex((k) => k.kpi === data.kpi.kpi);
            if (existing >= 0) {
              next[existing] = data.kpi;
            }
            return next;
          });
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("complete", (e: MessageEvent) => {
        try {
          setResult(JSON.parse(e.data));
          setIsConnected(false);
          closeCurrentSource();
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("error", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          if (data?.message) {
            setError(data.message);
          }
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("ping", () => {
        // Heartbeat event; no-op
      });

      eventSource.onerror = () => {
        setIsConnected(false);
        closeCurrentSource();
        if (stoppedRef.current) {
          return;
        }
        if (reconnectAttemptsRef.current >= 5) {
          setError("Connection lost. Reconnect failed after 5 attempts.");
          return;
        }
        reconnectAttemptsRef.current += 1;
        const delayMs = Math.min(5000, reconnectAttemptsRef.current * 1000);
        setError(`Connection lost. Reconnecting (${reconnectAttemptsRef.current}/5)...`);
        clearReconnectTimer();
        reconnectTimerRef.current = window.setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      stoppedRef.current = true;
      clearReconnectTimer();
      closeCurrentSource();
    };
  }, [question, scenarioType, strategy, horizon, service, JSON.stringify(assumptions)]);

  const handleStop = () => {
    stoppedRef.current = true;
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  };

  const handleRestart = () => {
    window.location.reload();
  };

  const chartData =
    kpis.length > 0
      ? kpis.map((kpi) => ({
          kpi: kpi.kpi.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          baseline: kpi.baseline,
          simulated: kpi.simulated,
          changePct: ((kpi.simulated - kpi.baseline) / kpi.baseline) * 100,
        }))
      : [];

  const sectionClass = "rounded-2xl border p-5 shadow-sm";
  const cardClass = "rounded-lg border p-4";

  return (
    <div className="space-y-6">
      <section
        style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
        className={sectionClass}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 style={{ color: "var(--foreground)" }} className="text-2xl font-semibold">
              Real-time Simulation
            </h1>
            <p className="mt-2 text-sm" style={{ color: "var(--muted-foreground)" }}>
              Streaming simulation results as they compute
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                style={{ borderColor: "var(--border)" }}
                className={cn(
                  "h-3 w-3 rounded-full border",
                  isConnected ? "bg-emerald-500" : "bg-slate-400",
                )}
              />
              <span style={{ color: "var(--muted-foreground)" }} className="text-sm">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            {isConnected && (
              <button
                onClick={handleStop}
                style={{
                  borderColor: "var(--error)",
                  backgroundColor: "rgba(var(--error-rgb), 0.1)",
                  color: "var(--error)",
                }}
                className="rounded-md border px-4 py-2 text-sm font-semibold hover:opacity-80"
              >
                Stop
              </button>
            )}
            {!isConnected && result && (
              <button
                onClick={handleRestart}
                style={{
                  borderColor: "var(--success)",
                  backgroundColor: "rgba(var(--success-rgb), 0.1)",
                  color: "var(--success)",
                }}
                className="rounded-md border px-4 py-2 text-sm font-semibold hover:opacity-80"
              >
                Restart
              </button>
            )}
          </div>
        </div>
      </section>

      {progress && (
        <section
          style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
          className={sectionClass}
        >
          <div className="flex items-center justify-between">
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
              Progress
            </h2>
            <span style={{ color: "var(--muted-foreground)" }} className="text-xs">
              {progress.step}
            </span>
          </div>
          <div
            style={{ backgroundColor: "var(--muted-background)" }}
            className="mt-3 h-2 overflow-hidden rounded-full"
          >
            <div
              className="h-full transition-all duration-300 ease-out"
              style={{
                backgroundColor: "var(--primary)",
                width: progress.total
                  ? `${((progress.current || 0) / progress.total) * 100}%`
                  : "50%",
              }}
            />
          </div>
          <p style={{ color: "var(--foreground-secondary)" }} className="mt-2 text-sm">
            {progress.message}
          </p>
        </section>
      )}

      {baseline && (
        <section
          style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
          className={sectionClass}
        >
          <div className="flex items-center justify-between">
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
              Baseline KPIs
            </h2>
            <span
              className={cn(
                "rounded-md px-2 py-1 text-xs font-semibold",
                baseline.dataQuality?.metrics_available ? "text-white" : "",
              )}
              style={
                baseline.dataQuality?.metrics_available
                  ? { backgroundColor: "rgba(var(--success-rgb), 0.4)", color: "var(--success)" }
                  : baseline.dataQuality?.using_fallback
                    ? { backgroundColor: "rgba(var(--warning-rgb), 0.4)", color: "var(--warning)" }
                    : {
                        backgroundColor: "var(--surface-base)",
                        borderColor: "var(--border)",
                        color: "var(--foreground-secondary)",
                      }
              }
            >
              {baseline.dataQuality?.metrics_available
                ? "Real Metrics"
                : baseline.dataQuality?.using_fallback
                  ? "Topology Fallback"
                  : "Unknown Source"}
            </span>
          </div>
          <p style={{ color: "var(--muted-foreground)" }} className="mt-1 text-xs">
            {baseline.dataQuality?.note || `Source: ${baseline.source}`}
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(baseline.kpis).map(([key, value]) => (
              <div
                key={key}
                style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
                className="rounded-lg border p-3"
              >
                <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                  {key}
                </p>
                <p style={{ color: "var(--foreground)" }} className="text-lg font-semibold">
                  {typeof value === "number" ? value.toFixed(2) : value}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {kpis.length > 0 && (
        <section
          style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
          className={sectionClass}
        >
          <h2
            style={{ color: "var(--muted-foreground)" }}
            className="text-sm font-semibold uppercase tracking-wider"
          >
            KPI Results ({kpis.length})
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((kpi) => {
              const changePct = ((kpi.simulated - kpi.baseline) / kpi.baseline) * 100;
              return (
                <div
                  key={kpi.kpi}
                  style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
                  className="rounded-lg border p-3"
                >
                  <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                    {kpi.kpi}
                  </p>
                  <p style={{ color: "var(--foreground-secondary)" }} className="mt-1 text-sm">
                    {kpi.baseline.toFixed(2)} → {kpi.simulated.toFixed(2)} {kpi.unit}
                  </p>
                  <p
                    className={cn("text-sm font-semibold", changePct >= 0 ? "" : "")}
                    style={{ color: changePct >= 0 ? "var(--warning)" : "var(--success)" }}
                  >
                    {changePct >= 0 ? "+" : ""}
                    {changePct.toFixed(2)}%
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {chartData.length > 0 && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
            className={sectionClass}
          >
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
              Comparison Chart
            </h2>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                  <XAxis dataKey="kpi" stroke="var(--border-muted)" />
                  <YAxis stroke="var(--border-muted)" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="baseline" fill="var(--primary)" name="Baseline" />
                  <Bar dataKey="simulated" fill="var(--warning)" name="Simulated" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
            className={sectionClass}
          >
            <h2
              style={{ color: "var(--muted-foreground)" }}
              className="text-sm font-semibold uppercase tracking-wider"
            >
              Change Percentage
            </h2>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                  <XAxis dataKey="kpi" stroke="var(--border-muted)" />
                  <YAxis stroke="var(--border-muted)" />
                  <Tooltip />
                  <Bar dataKey="changePct" fill="var(--success)" name="Change %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      )}

      {result && (
        <section
          style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}
          className={sectionClass}
        >
          <h2
            style={{ color: "var(--muted-foreground)" }}
            className="text-sm font-semibold uppercase tracking-wider"
          >
            Final Result
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
              className={cardClass}
            >
              <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                Strategy
              </p>
              <p style={{ color: "var(--foreground)" }} className="text-lg font-semibold uppercase">
                {result.simulation.strategy}
              </p>
            </div>
            <div
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
              className={cardClass}
            >
              <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                Confidence
              </p>
              <p style={{ color: "var(--success)" }} className="text-lg font-semibold">
                {(result.simulation.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
              className={cardClass}
            >
              <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                Scenario ID
              </p>
              <p style={{ color: "var(--foreground-secondary)" }} className="truncate text-sm">
                {result.simulation.scenario_id}
              </p>
            </div>
          </div>
          <div
            style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
            className={cn(cardClass, "mt-4")}
          >
            <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
              Explanation
            </p>
            <p style={{ color: "var(--foreground-secondary)" }} className="mt-1 text-sm">
              {result.simulation.explanation}
            </p>
          </div>

          {(result.data_source || result.timing) && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {result.data_source && (
                <div
                  style={
                    result.data_source === "metric_timeseries"
                      ? {
                          borderColor: "var(--success)",
                          backgroundColor: "rgba(var(--success-rgb), 0.1)",
                        }
                      : {
                          borderColor: "var(--warning)",
                          backgroundColor: "rgba(var(--warning-rgb), 0.1)",
                        }
                  }
                  className="rounded-lg border p-4"
                >
                  <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                    Data Source
                  </p>
                  <p
                    className={cn(
                      "text-sm font-semibold",
                      result.data_source === "metric_timeseries" ? "" : "",
                    )}
                    style={{
                      color:
                        result.data_source === "metric_timeseries"
                          ? "var(--success)"
                          : "var(--warning)",
                    }}
                  >
                    {result.data_source === "metric_timeseries"
                      ? "Real Metric Data"
                      : result.data_source === "topology_fallback"
                        ? "Topology Fallback (No Real Metrics)"
                        : result.data_source}
                  </p>
                </div>
              )}
              {result.timing && (
                <div
                  style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}
                  className={cardClass}
                >
                  <p style={{ color: "var(--muted-foreground)" }} className="text-xs">
                    Computation Time
                  </p>
                  <p style={{ color: "var(--primary)" }} className="text-sm font-semibold">
                    {result.timing.total_ms.toFixed(0)}ms total
                  </p>
                  <p style={{ color: "var(--muted-foreground)" }} className="mt-1 text-xs">
                    Planning: {result.timing.planning_ms.toFixed(0)}ms | Baseline:{" "}
                    {result.timing.baseline_loading_ms.toFixed(0)}ms | Strategy:{" "}
                    {result.timing.strategy_execution_ms.toFixed(0)}ms
                  </p>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {error && (
        <section
          style={{ borderColor: "var(--error)", backgroundColor: "rgba(var(--error-rgb), 0.1)" }}
          className="rounded-2xl border p-5"
        >
          <p style={{ color: "var(--error)" }}>{error}</p>
        </section>
      )}
    </div>
  );
}
