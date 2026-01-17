"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";

type RegressionTrendRow = {
  date: string;
  PASS: number;
  WARN: number;
  FAIL: number;
};

type ObservabilityPayload = {
  success_rate: number;
  failure_rate: number;
  total_recent_requests: number;
  latency: {
    p50: number | null;
    p95: number | null;
  };
  regression_trend: RegressionTrendRow[];
  regression_totals: Record<"PASS" | "WARN" | "FAIL", number>;
  top_causes: { reason: string; count: number }[];
  no_data_ratio: number;
};

type ObservabilityResponse = {
  time: string;
  code: number;
  message: string;
  data?: {
    kpis: ObservabilityPayload;
  };
};

export default function ObservabilityDashboard() {
  const [payload, setPayload] = useState<ObservabilityPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadKpis = async () => {
      try {
        const res = await fetch("/ops/observability/kpis");
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const json: ObservabilityResponse = await res.json();

        if (cancelled) return;

        if (json.code !== 0) {
          setError(json.message || "Failed to load observability metrics");
          return;
        }

        if (json.data?.kpis) {
          // Validate KPI payload structure
          const kpis = json.data.kpis;
          if (typeof kpis.success_rate !== 'number' ||
              typeof kpis.failure_rate !== 'number' ||
              !kpis.latency ||
              !Array.isArray(kpis.regression_trend) ||
              !kpis.regression_totals ||
              !Array.isArray(kpis.top_causes)) {
            throw new Error("Invalid KPI payload structure");
          }
          setPayload(kpis);
          setError(null);
        } else {
          setError("No KPI payload returned from server");
        }
      } catch (err) {
        if (cancelled) return;
        const errorMsg = err instanceof Error ? err.message : "Observability request failed";
        console.error("ObservabilityDashboard error:", errorMsg);
        setError(errorMsg);
      }
    };

    loadKpis();
    return () => {
      cancelled = true;
    };
  }, []);

  const summaryLabels = useMemo(() => {
    if (!payload) return [];
    return [
      { label: "Success Rate", value: `${(payload.success_rate * 100).toFixed(1)}%` },
      { label: "Failure Rate", value: `${(payload.failure_rate * 100).toFixed(1)}%` },
      { label: "No-data Ratio", value: `${(payload.no_data_ratio * 100).toFixed(1)}%` },
      { label: "Requests (24h)", value: payload.total_recent_requests.toLocaleString() },
    ];
  }, [payload]);

  if (error) {
    return (
      <div className="rounded-3xl border border-rose-500/50 bg-rose-500/5 p-6 text-sm text-rose-200">
        Observability dashboard failed: {error}
      </div>
    );
  }

  if (!payload) {
    return (
      <div className="rounded-3xl border border-slate-700 bg-slate-900/60 p-6 text-sm text-slate-300">
        Loading observability KPIs...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Observability</h1>
          <p className="text-sm text-slate-400">Trace & Regression 핵심 KPI를 한 화면에서 파악합니다.</p>
        </div>
        <span className="text-xs uppercase tracking-[0.3em] text-sky-400">realtime</span>
      </div>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {summaryLabels.map((item, idx) => (
          <article
            key={item.label}
            className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-5 text-white shadow-[0_10px_40px_rgba(15,23,42,0.5)]"
          >
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{item.label}</p>
            <p className="mt-3 text-3xl font-semibold">{item.value}</p>
            {idx === 0 && <p className="text-xs text-slate-400">Goal ≥ 96%</p>}
          </article>
        ))}
      </section>

      <section className="rounded-3xl border border-slate-800/80 bg-slate-900/60 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Latency & Tool Health</h2>
          <span className="text-xs text-slate-400">last 24h</span>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4">
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">p50 Latency</p>
            <p className="mt-2 text-3xl font-semibold text-white">
              {payload.latency.p50 ? `${payload.latency.p50} ms` : "—"}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4">
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">p95 Latency</p>
            <p className="mt-2 text-3xl font-semibold text-white">
              {payload.latency.p95 ? `${payload.latency.p95} ms` : "—"}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Regression trend</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-400">last 7 days</span>
          </div>
          {payload.regression_trend.length === 0 ? (
            <div className="mt-4 text-sm text-slate-400">No regression runs in the last 7 days.</div>
          ) : (
            <div className="mt-4 h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={payload.regression_trend} margin={{ top: 20, right: 10, left: 0, bottom: 20 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                    cursor={{ fill: "rgba(148, 163, 184, 0.1)" }}
                  />
                  <Legend wrapperStyle={{ paddingTop: "20px" }} />
                  <Bar dataKey="PASS" fill="#34d399" />
                  <Bar dataKey="WARN" fill="#fbbf24" />
                  <Bar dataKey="FAIL" fill="#f87171" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="mt-5 flex flex-wrap gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
            <span className="rounded-full border border-slate-700 px-3 py-1">Regression FAIL/WARN focus</span>
            <span className="rounded-full border border-slate-700 px-3 py-1">Trend & RCA</span>
          </div>
        </article>

        <article className="rounded-3xl border border-slate-800/70 bg-slate-900/60 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Regression breakdown</h2>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-400">kpi</span>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3 text-xs uppercase tracking-[0.2em] text-slate-400">
            {(["PASS", "WARN", "FAIL"] as const).map((key) => (
              <div key={key} className="rounded-2xl border border-slate-800/60 bg-slate-950/40 p-4 text-center">
                <p className="text-[10px] text-slate-400">{key}</p>
                <p
                  className={
                    "mt-2 text-3xl font-semibold " +
                    (key === "FAIL" ? "text-rose-300" : key === "WARN" ? "text-amber-300" : "text-emerald-300")
                  }
                >
                  {payload.regression_totals[key].toLocaleString()}
                </p>
              </div>
            ))}
          </div>

          {payload.regression_totals.PASS + payload.regression_totals.WARN + payload.regression_totals.FAIL > 0 && (
            <div className="mt-6 h-40 w-full flex justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: "PASS", value: payload.regression_totals.PASS },
                      { name: "WARN", value: payload.regression_totals.WARN },
                      { name: "FAIL", value: payload.regression_totals.FAIL },
                    ]}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name} ${value}`}
                    outerRadius={60}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    <Cell fill="#34d399" />
                    <Cell fill="#fbbf24" />
                    <Cell fill="#f87171" />
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="mt-4 text-sm text-slate-300">
            RCA Top Causes
            <ul className="mt-2 space-y-2 text-xs text-slate-400">
              {payload.top_causes.length === 0 && <li>No causes collected yet.</li>}
              {payload.top_causes.map((cause) => (
                <li key={cause.reason} className="flex justify-between">
                  <span className="truncate pr-2">{cause.reason}</span>
                  <span className="text-emerald-300">{cause.count}</span>
                </li>
              ))}
            </ul>
          </div>
        </article>
      </section>
    </div>
  );
}
