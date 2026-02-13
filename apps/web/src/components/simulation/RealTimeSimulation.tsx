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

  const sectionClass = "container-section";
  const cardClass = "container-card";

  return (
    <div className="space-y-6">
      <section className={sectionClass}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              Real-time Simulation
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Streaming simulation results as they compute
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "h-3 w-3 rounded-full border border-variant",
                  isConnected ? "bg-emerald-500" : "bg-slate-400",
                )}
              />
              <span className="text-sm text-muted-foreground">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            {isConnected && (
              <button
                onClick={handleStop}
                className="btn-error"
              >
                Stop
              </button>
            )}
            {!isConnected && result && (
              <button
                onClick={handleRestart}
                className="btn-success"
              >
                Restart
              </button>
            )}
          </div>
        </div>
      </section>

      {progress && (
        <section className="container-section">
          <div className="flex items-center justify-between">
            <h2 className="text-label">
              Progress
            </h2>
            <span className="text-xs text-muted-foreground">
              {progress.step}
            </span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted-background">
            <div
              className="h-full transition-all duration-300 ease-out bg-sky-600"
              style={{
                width: progress.total
                  ? `${((progress.current || 0) / progress.total) * 100}%`
                  : "50%",
              }}
            />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {progress.message}
          </p>
        </section>
      )}

      {baseline && (
        <section className="container-section">
          <div className="flex items-center justify-between">
            <h2 className="text-label">
              Baseline KPIs
            </h2>
            <span
              className={cn(
                "rounded-md px-2 py-1 text-xs font-semibold",
                baseline.dataQuality?.metrics_available
                  ? "bg-emerald-500/40 text-emerald-600 dark:text-emerald-400"
                  : baseline.dataQuality?.using_fallback
                    ? "bg-amber-500/40 text-amber-600 dark:text-amber-400"
                    : "border border-variant bg-surface-base text-muted-foreground dark:border-variant dark:bg-surface-base dark:text-muted-foreground"
              )}
            >
              {baseline.dataQuality?.metrics_available
                ? "Real Metrics"
                : baseline.dataQuality?.using_fallback
                  ? "Topology Fallback"
                  : "Unknown Source"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {baseline.dataQuality?.note || `Source: ${baseline.source}`}
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(baseline.kpis).map(([key, value]) => (
              <div key={key} className="container-card">
                <p className="text-xs text-muted-foreground">
                  {key}
                </p>
                <p className="text-lg font-semibold text-foreground">
                  {typeof value === "number" ? value.toFixed(2) : value}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {kpis.length > 0 && (
        <section className="container-section">
          <h2 className="text-label">
            KPI Results ({kpis.length})
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((kpi) => {
              const changePct = ((kpi.simulated - kpi.baseline) / kpi.baseline) * 100;
              return (
                <div key={kpi.kpi} className="container-card">
                  <p className="text-xs text-muted-foreground">
                    {kpi.kpi}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {kpi.baseline.toFixed(2)} → {kpi.simulated.toFixed(2)} {kpi.unit}
                  </p>
                  <p
                    className={cn("text-sm font-semibold", changePct >= 0 ? "text-warning" : "text-success")}
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
          <div className="container-section">
            <h2 className="text-label">
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

          <div className="container-section">
            <h2 className="text-label">
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
        <section className="container-section">
          <h2 className="text-label">
            Final Result
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div className="container-card">
              <p className="text-xs text-muted-foreground">
                Strategy
              </p>
              <p className="text-lg font-semibold uppercase text-foreground">
                {result.simulation.strategy}
              </p>
            </div>
            <div className="container-card">
              <p className="text-xs text-muted-foreground">
                Confidence
              </p>
              <p className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                {(result.simulation.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div className="container-card">
              <p className="text-xs text-muted-foreground">
                Scenario ID
              </p>
              <p className="truncate text-sm text-muted-foreground">
                {result.simulation.scenario_id}
              </p>
            </div>
          </div>
          <div className={cn(cardClass, "mt-4")}>
            <p className="text-xs text-muted-foreground">
              Explanation
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {result.simulation.explanation}
            </p>
          </div>

          {(result.data_source || result.timing) && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {result.data_source && (
                <div
                  className={cn(
                    "rounded-lg border p-4",
                    result.data_source === "metric_timeseries"
                      ? "border-emerald-500 bg-emerald-500/10"
                      : "border-amber-500 bg-amber-500/10"
                  )}
                >
                  <p className="text-xs text-muted-foreground">
                    Data Source
                  </p>
                  <p
                    className={cn(
                      "text-sm font-semibold",
                      result.data_source === "metric_timeseries"
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-amber-600 dark:text-amber-400"
                    )}
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
                <div className="container-card">
                  <p className="text-xs text-muted-foreground">
                    Computation Time
                  </p>
                  <p className="text-sm font-semibold text-sky-600 dark:text-sky-400">
                    {result.timing.total_ms.toFixed(0)}ms total
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
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
        <section className="container-section border-error bg-error/10">
          <p className="text-rose-600 dark:text-rose-400">{error}</p>
        </section>
      )}
    </div>
  );
}
