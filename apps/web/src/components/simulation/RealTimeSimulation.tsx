"use client";

import { useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

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
  data_transparency?: {
    baseline_from_real_metrics: boolean;
    baseline_from_topology_fallback: boolean;
    strategy_used: string;
    strategy_computation_real: boolean;
  };
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
          const data = JSON.parse(e.data);
          setProgress(data);
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("baseline", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          setBaseline(data);
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("kpi", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          setKpis((prev) => {
            const newKpis = [...prev, data.kpi];
            const existing = newKpis.findIndex((k) => k.kpi === data.kpi.kpi);
            if (existing >= 0) {
              newKpis[existing] = data.kpi;
            }
            return newKpis;
          });
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener("complete", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          setResult(data);
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
    // Force re-mount by toggling a key or similar
    window.location.reload();
  };

  // Chart data
  const chartData = kpis.length > 0 ? kpis.map((kpi) => ({
    kpi: kpi.kpi.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    baseline: kpi.baseline,
    simulated: kpi.simulated,
    changePct: ((kpi.simulated - kpi.baseline) / kpi.baseline) * 100,
  })) : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">Real-time Simulation</h1>
            <p className="mt-2 text-sm text-slate-300">
              Streaming simulation results as they compute
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`} />
              <span className="text-sm text-slate-400">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            {isConnected && (
              <button
                onClick={handleStop}
                className="rounded-2xl border border-rose-700 bg-rose-500/20 px-4 py-2 text-sm font-semibold text-rose-300 hover:bg-rose-500/30"
              >
                Stop
              </button>
            )}
            {!isConnected && result && (
              <button
                onClick={handleRestart}
                className="rounded-2xl border border-emerald-700 bg-emerald-500/20 px-4 py-2 text-sm font-semibold text-emerald-300 hover:bg-emerald-500/30"
              >
                Restart
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Progress */}
      {progress && (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
              Progress
            </h2>
            <span className="text-xs text-slate-400">
              {progress.step}
            </span>
          </div>
          <div className="mt-3">
            <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-sky-500 transition-all duration-300 ease-out"
                style={{
                  width: progress.total
                    ? `${(progress.current || 0) / progress.total * 100}%`
                    : "50%",
                }}
              />
            </div>
          </div>
          <p className="mt-2 text-sm text-slate-300">{progress.message}</p>
        </section>
      )}

      {/* Baseline Info */}
      {baseline && (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
              Baseline KPIs
            </h2>
            <span className={`text-xs px-2 py-1 rounded-full ${
              baseline.dataQuality?.metrics_available
                ? "bg-emerald-500/20 text-emerald-300"
                : baseline.dataQuality?.using_fallback
                ? "bg-amber-500/20 text-amber-300"
                : "bg-slate-500/20 text-slate-300"
            }`}>
              {baseline.dataQuality?.metrics_available
                ? "Real Metrics"
                : baseline.dataQuality?.using_fallback
                ? "Topology Fallback"
                : "Unknown Source"}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {baseline.dataQuality?.note || `Source: ${baseline.source}`}
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(baseline.kpis).map(([key, value]) => (
              <div key={key} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                <p className="text-xs text-slate-500">{key}</p>
                <p className="text-lg font-semibold text-white">{typeof value === "number" ? value.toFixed(2) : value}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Real-time KPI Results */}
      {kpis.length > 0 && (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
            KPI Results ({kpis.length})
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((kpi) => {
              const changePct = ((kpi.simulated - kpi.baseline) / kpi.baseline) * 100;
              return (
                <div key={kpi.kpi} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-xs text-slate-500">{kpi.kpi}</p>
                  <p className="mt-1 text-sm text-slate-300">
                    {kpi.baseline.toFixed(2)} → {kpi.simulated.toFixed(2)} {kpi.unit}
                  </p>
                  <p className={`text-sm font-semibold ${changePct >= 0 ? "text-amber-300" : "text-emerald-300"}`}>
                    {changePct >= 0 ? "+" : ""}
                    {changePct.toFixed(2)}%
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Charts */}
      {chartData.length > 0 && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
              Comparison Chart
            </h2>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="kpi" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="baseline" fill="#38bdf8" name="Baseline" />
                  <Bar dataKey="simulated" fill="#f59e0b" name="Simulated" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
              Change Percentage
            </h2>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="kpi" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="changePct" fill="#22d3ee" name="Change %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      )}

      {/* Final Result */}
      {result && (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
            Final Result
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <p className="text-xs text-slate-500">Strategy</p>
              <p className="text-lg font-semibold text-white uppercase">{result.simulation.strategy}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <p className="text-xs text-slate-500">Confidence</p>
              <p className="text-lg font-semibold text-emerald-400">
                {(result.simulation.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <p className="text-xs text-slate-500">Scenario ID</p>
              <p className="text-sm text-slate-300 truncate">{result.simulation.scenario_id}</p>
            </div>
          </div>
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <p className="text-xs text-slate-500">Explanation</p>
            <p className="mt-1 text-sm text-slate-300">{result.simulation.explanation}</p>
          </div>

          {/* Data Source Transparency */}
          {(result.data_source || result.data_transparency || result.timing) && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {result.data_source && (
                <div className={`rounded-xl border p-4 ${
                  result.data_source === "metric_timeseries"
                    ? "border-emerald-700/40 bg-emerald-950/20"
                    : "border-amber-700/40 bg-amber-950/20"
                }`}>
                  <p className="text-xs text-slate-400">Data Source</p>
                  <p className={`text-sm font-semibold ${
                    result.data_source === "metric_timeseries"
                      ? "text-emerald-300"
                      : "text-amber-300"
                  }`}>
                    {result.data_source === "metric_timeseries"
                      ? "✓ Real Metric Data"
                      : result.data_source === "topology_fallback"
                      ? "⚠ Topology Fallback (No Real Metrics)"
                      : result.data_source}
                  </p>
                </div>
              )}
              {result.timing && (
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                  <p className="text-xs text-slate-400">Computation Time</p>
                  <p className="text-sm font-semibold text-sky-300">
                    {result.timing.total_ms.toFixed(0)}ms total
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Planning: {result.timing.planning_ms.toFixed(0)}ms |
                    Baseline: {result.timing.baseline_loading_ms.toFixed(0)}ms |
                    Strategy: {result.timing.strategy_execution_ms.toFixed(0)}ms
                  </p>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Error */}
      {error && (
        <section className="rounded-3xl border border-rose-800/40 bg-rose-950/20 p-5">
          <p className="text-rose-300">{error}</p>
        </section>
      )}
    </div>
  );
}
