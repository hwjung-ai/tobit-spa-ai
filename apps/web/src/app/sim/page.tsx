"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { authenticatedFetch } from "@/lib/apiClient";
import TopologyMap from "@/components/simulation/TopologyMap";
import Toast from "@/components/admin/Toast";

type Strategy = "rule" | "stat" | "ml" | "dl";
type ScenarioType = "what_if" | "stress_test" | "capacity";

interface SimulationTemplate {
  id: string;
  name: string;
  description: string;
  scenario_type: ScenarioType;
  default_strategy: Strategy;
  assumptions: Record<string, number>;
  question_example: string;
}

interface SimulationPlan {
  scenario_id: string;
  scenario_name: string;
  target_entities: string[];
  target_kpis: string[];
  assumptions: Record<string, number>;
  baseline_window: string;
  horizon: string;
  strategy: Strategy;
  scenario_type: ScenarioType;
  service: string;
  question: string;
}

interface KpiResult {
  kpi: string;
  baseline: number;
  simulated: number;
  unit: string;
  change_pct?: number;
}

interface SimulationResult {
  scenario_id: string;
  strategy: Strategy;
  scenario_type: ScenarioType;
  question: string;
  horizon: string;
  assumptions: Record<string, number>;
  kpis: KpiResult[];
  confidence: number;
  confidence_interval?: [number, number];
  error_bound?: number;
  warnings: string[];
  explanation: string;
  recommended_actions: string[];
  model_info: Record<string, unknown>;
  created_at: string;
}

interface RunResponseData {
  simulation: SimulationResult;
  summary: string;
  plan: SimulationPlan;
  references: Array<{ kind: string; title: string; payload: unknown }>;
}

interface BacktestResponseData {
  backtest: {
    strategy: Strategy;
    service: string;
    horizon: string;
    summary: string;
    metrics: {
      r2: number;
      mape: number;
      rmse: number;
      coverage_90: number;
    };
  };
}

interface Envelope<T> {
  data?: T;
  message?: string;
  detail?: string;
}

const assumptionMeta: Record<
  string,
  {
    label: string;
    unit: string;
    min: number;
    max: number;
    step: number;
  }
> = {
  traffic_change_pct: { label: "트래픽 변화", unit: "%", min: -50, max: 200, step: 1 },
  cpu_change_pct: { label: "CPU 변화", unit: "%", min: -50, max: 200, step: 1 },
  memory_change_pct: { label: "메모리 변화", unit: "%", min: -50, max: 200, step: 1 },
};

const strategyMeta: Record<Strategy, { title: string; desc: string; badge: string }> = {
  rule: {
    title: "Rule",
    desc: "사전 정의 수식(선형/임계)으로 계산합니다.",
    badge: "설명 가능",
  },
  stat: {
    title: "Stat",
    desc: "EMA + 회귀 기반으로 추세를 반영합니다.",
    badge: "균형형",
  },
  ml: {
    title: "ML",
    desc: "비선형 상호작용을 반영하는 surrogate 추론입니다.",
    badge: "고급형",
  },
  dl: {
    title: "DL",
    desc: "시퀀스형 비선형 패턴을 반영하는 딥러닝 surrogate입니다.",
    badge: "심화형",
  },
};

const formatKpiLabel = (value: string) =>
  value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

const getConfidenceLabel = (score: number) => {
  if (score >= 0.8) return "High";
  if (score >= 0.6) return "Medium";
  return "Low";
};

const calculateChangePct = (item: KpiResult): number => {
  if (typeof item.change_pct === "number") {
    return item.change_pct;
  }
  if (!item.baseline) {
    return 0;
  }
  return Number((((item.simulated - item.baseline) / item.baseline) * 100).toFixed(2));
};

export default function SimPage() {
  const [templates, setTemplates] = useState<SimulationTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [services, setServices] = useState<string[]>([]);
  const [servicesLoading, setServicesLoading] = useState(true);
  const [question, setQuestion] = useState("트래픽이 20% 증가하면 서비스 지표가 어떻게 변하나?");
  const [scenarioType, setScenarioType] = useState<ScenarioType>("what_if");
  const [strategy, setStrategy] = useState<Strategy>("rule");
  const [horizon, setHorizon] = useState("7d");
  const [service, setService] = useState("");
  const [assumptions, setAssumptions] = useState<Record<string, number>>({
    traffic_change_pct: 20,
    cpu_change_pct: 10,
    memory_change_pct: 5,
  });
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [plan, setPlan] = useState<SimulationPlan | null>(null);
  const [result, setResult] = useState<RunResponseData | null>(null);
  const [previousResult, setPreviousResult] = useState<RunResponseData | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponseData["backtest"] | null>(null);

  useEffect(() => {
    const loadServices = async () => {
      setServicesLoading(true);
      try {
        const response = await authenticatedFetch<Envelope<{ services: string[] }>>("/api/sim/services");
        const loaded = response.data?.services ?? [];
        setServices(loaded);
        if (loaded.length > 0) {
          setService(loaded[0]);
        }
      } catch (err) {
        console.error("Failed to load simulation services", err);
      } finally {
        setServicesLoading(false);
      }
    };

    const loadTemplates = async () => {
      try {
        const response = await authenticatedFetch<Envelope<{ templates: SimulationTemplate[] }>>("/api/sim/templates");
        setTemplates(response.data?.templates ?? []);
      } catch (err) {
        console.error("Failed to load templates", err);
      }
    };
    void loadServices();
    void loadTemplates();
  }, []);

  const getEffectiveService = () => {
    const trimmed = service.trim();
    if (!trimmed) {
      throw new Error("Service를 입력하거나 선택해 주세요.");
    }
    if (services.length === 0) {
      return trimmed;
    }
    if (!services.includes(trimmed)) {
      const fallback = services[0];
      setService(fallback);
      return fallback;
    }
    return trimmed;
  };

  const applyTemplate = (template: SimulationTemplate) => {
    setSelectedTemplateId(template.id);
    setQuestion(template.question_example);
    setScenarioType(template.scenario_type);
    setStrategy(template.default_strategy);
    setAssumptions(template.assumptions);
  };

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templates]
  );

  const handleRun = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const effectiveService = getEffectiveService();
      const buildPayload = (svc: string) => ({
        question,
        scenario_type: scenarioType,
        strategy,
        assumptions,
        horizon,
        service: svc,
      });
      let targetService = effectiveService;
      let queryPayload = buildPayload(targetService);

      const queryResponse = await authenticatedFetch<Envelope<{ plan: SimulationPlan }>>("/api/sim/query", {
        method: "POST",
        body: JSON.stringify(queryPayload),
      });
      setPlan(queryResponse.data?.plan ?? null);

      let runResponse: Envelope<RunResponseData> | null = null;
      try {
        runResponse = await authenticatedFetch<Envelope<RunResponseData>>("/api/sim/run", {
          method: "POST",
          body: JSON.stringify(queryPayload),
        });
      } catch (runError) {
        const message = runError instanceof Error ? runError.message : "Simulation run failed";
        const fallbackService = services[0];
        const shouldRetry = message.includes("HTTP 404") && Boolean(fallbackService) && fallbackService !== targetService;
        if (!shouldRetry) {
          throw runError;
        }
        targetService = fallbackService;
        setService(fallbackService);
        queryPayload = buildPayload(targetService);
        const fallbackQuery = await authenticatedFetch<Envelope<{ plan: SimulationPlan }>>("/api/sim/query", {
          method: "POST",
          body: JSON.stringify(queryPayload),
        });
        setPlan(fallbackQuery.data?.plan ?? null);
        runResponse = await authenticatedFetch<Envelope<RunResponseData>>("/api/sim/run", {
          method: "POST",
          body: JSON.stringify(queryPayload),
        });
      }

      if (!runResponse.data) {
        throw new Error(runResponse.message || "Simulation response is empty");
      }
      setPreviousResult(result);
      setResult(runResponse.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Simulation run failed";
      if (message.includes("HTTP 404")) {
        setStatusMessage("선택한 서비스의 토폴로지 데이터가 없습니다. Service를 다시 선택해 주세요.");
      } else {
        setStatusMessage(message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBacktest = async () => {
    setStatusMessage(null);
    try {
      const effectiveService = getEffectiveService();
      const response = await authenticatedFetch<Envelope<BacktestResponseData>>("/api/sim/backtest", {
        method: "POST",
        body: JSON.stringify({
          strategy,
          service: effectiveService,
          horizon: "30d",
          assumptions,
        }),
      });
      setBacktest(response.data?.backtest ?? null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Backtest failed";
      if (message.includes("HTTP 404")) {
        setStatusMessage("선택한 서비스의 토폴로지 데이터가 없습니다. Service를 다시 선택해 주세요.");
      } else {
        setStatusMessage(message);
      }
    }
  };

  const handleExportCsv = async () => {
    setStatusMessage(null);
    try {
      const effectiveService = getEffectiveService();
      const csvText = await authenticatedFetch<string>("/api/sim/export", {
        method: "POST",
        body: JSON.stringify({
          question,
          scenario_type: scenarioType,
          strategy,
          assumptions,
          horizon,
          service: effectiveService,
        }),
        headers: {
          Accept: "text/csv",
        },
      });
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sim-${service}-${strategy}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "CSV export failed";
      if (message.includes("HTTP 404")) {
        setStatusMessage("선택한 서비스의 토폴로지 데이터가 없습니다. Service를 다시 선택해 주세요.");
      } else {
        setStatusMessage(message);
      }
    }
  };

  const chartData = useMemo(() => {
    if (!result?.simulation?.kpis) return [];
    return result.simulation.kpis.map((item) => ({
      kpi: formatKpiLabel(item.kpi),
      baseline: Number(item.baseline.toFixed(3)),
      simulated: Number(item.simulated.toFixed(3)),
      changePct: Number(calculateChangePct(item).toFixed(2)),
    }));
  }, [result]);

  const compareData = useMemo(() => {
    if (!result || !previousResult) return [];
    const previousMap = new Map(previousResult.simulation.kpis.map((k) => [k.kpi, k]));
    return result.simulation.kpis.map((kpi) => {
      const prev = previousMap.get(kpi.kpi);
      return {
        kpi: formatKpiLabel(kpi.kpi),
        current: calculateChangePct(kpi),
        previous: prev ? calculateChangePct(prev) : 0,
      };
    });
  }, [previousResult, result]);

  return (
    <div className="space-y-6 py-6">
      <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Simulation</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">SIM Workspace</h1>
        <p className="mt-2 max-w-4xl text-sm text-slate-300">
          질문과 가정값을 기반으로 계획을 검증한 뒤 실행합니다. 결과는 KPI 변화, 비교 차트, 룰/모델 근거를 함께 제공합니다.
        </p>
      </section>

      <section className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <aside className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/60 p-5 min-h-[320px]">
          <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">Scenario Builder</h2>

          <label className="block text-xs uppercase tracking-[0.2em] text-slate-400">
            질문
            <textarea
              data-testid="simulation-question-input"
              className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none focus:border-sky-500"
              rows={4}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                  event.preventDefault();
                  void handleRun();
                }
              }}
            />
          </label>

          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">템플릿</p>
            <div className="mt-2 grid gap-2">
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  data-testid="simulation-template-select"
                  onClick={() => applyTemplate(template)}
                  className="rounded-2xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-left transition hover:border-sky-500"
                >
                  <p className="text-sm font-semibold text-white">{template.name}</p>
                  <p className="text-xs text-slate-400">{template.description}</p>
                </button>
              ))}
            </div>
            {selectedTemplate ? (
              <div className="mt-3 rounded-xl border border-emerald-700/40 bg-emerald-950/20 px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Applied Template</p>
                <p className="mt-1 text-sm text-slate-200">{selectedTemplate.name}</p>
                <p className="text-xs text-slate-400">{selectedTemplate.description}</p>
              </div>
            ) : (
              <p className="mt-2 text-xs text-slate-500">템플릿을 클릭하면 질문/전략/가정값이 자동 적용됩니다.</p>
            )}
          </div>

          <label className="block text-xs uppercase tracking-[0.2em] text-slate-400">
            시나리오 타입
            <select
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              value={scenarioType}
              onChange={(event) => setScenarioType(event.target.value as ScenarioType)}
            >
              <option value="what_if">What-if</option>
              <option value="stress_test">Stress Test</option>
              <option value="capacity">Capacity</option>
            </select>
          </label>

          <label className="block text-xs uppercase tracking-[0.2em] text-slate-400">
            Service
            {services.length > 0 ? (
              <select
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
                value={service}
                onChange={(event) => setService(event.target.value)}
              >
                {services.map((svc) => (
                  <option key={svc} value={svc}>
                    {svc}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
                value={service}
                onChange={(event) => setService(event.target.value)}
                placeholder="예: api-gateway"
              />
            )}
            {services.length === 0 ? (
              <p className="mt-1 text-[11px] text-amber-300">자동 감지된 서비스가 없어 수동 입력 모드입니다.</p>
            ) : null}
          </label>

          <label className="block text-xs uppercase tracking-[0.2em] text-slate-400">
            Horizon
            <input
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              value={horizon}
              onChange={(event) => setHorizon(event.target.value)}
            />
          </label>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">가정값</p>
            {Object.entries(assumptions).map(([key, value]) => {
              const meta = assumptionMeta[key];
              if (!meta) return null;
              return (
                <label key={key} className="block rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs text-slate-300">{meta.label}</span>
                    <span className="text-xs text-slate-400">
                      {value}
                      {meta.unit}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={meta.min}
                    max={meta.max}
                    step={meta.step}
                    value={value}
                    onChange={(event) =>
                      setAssumptions((prev) => ({
                        ...prev,
                        [key]: Number(event.target.value),
                      }))
                    }
                    className="w-full"
                  />
                </label>
              );
            })}
          </div>

          <div className="grid gap-2">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">전략 선택</p>
            {(Object.keys(strategyMeta) as Strategy[]).map((s) => (
              <button
                key={s}
                data-testid="simulation-strategy-select"
                onClick={() => setStrategy(s)}
                className={`rounded-2xl border px-3 py-2 text-left transition ${
                  strategy === s
                    ? "border-sky-500 bg-sky-500/10"
                    : "border-slate-700 bg-slate-950/60 hover:border-slate-500"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">{strategyMeta[s].title}</span>
                  <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{strategyMeta[s].badge}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{strategyMeta[s].desc}</p>
              </button>
            ))}
          </div>

          <button
            data-testid="simulation-run-button"
            className="w-full rounded-2xl bg-emerald-500/90 px-4 py-2 text-sm font-semibold uppercase tracking-[0.25em] text-white transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700"
            onClick={handleRun}
            disabled={loading || servicesLoading || !question.trim() || !service.trim()}
          >
            {loading ? "Running..." : servicesLoading ? "Loading Services..." : "Run Simulation"}
          </button>
          {!question.trim() ? <p className="text-[11px] text-slate-500">질문을 입력하면 실행할 수 있습니다.</p> : null}
          {!service.trim() ? <p className="text-[11px] text-slate-500">Service를 입력 또는 선택하면 실행할 수 있습니다.</p> : null}

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              data-testid="simulation-backtest-button"
              className="rounded-2xl border border-slate-700 bg-slate-950/50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-slate-200 hover:border-sky-500"
              onClick={handleBacktest}
            >
              Run Backtest
            </button>
            <button
              type="button"
              data-testid="simulation-export-button"
              className="rounded-2xl border border-slate-700 bg-slate-950/50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-slate-200 hover:border-emerald-500"
              onClick={handleExportCsv}
            >
              Export CSV
            </button>
          </div>
        </aside>

        <main className="space-y-4">
          <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
            <h2 data-testid="simulation-kpi-summary" className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">
              KPI Summary
            </h2>
            {!result ? (
              <p className="mt-3 text-sm text-slate-400">왼쪽에서 시나리오를 설정하고 실행하세요.</p>
            ) : (
              <>
                <p className="mt-3 text-sm text-slate-300">{result.summary}</p>
                <p className="mt-1 text-xs text-slate-400">
                  Confidence: {result.simulation.confidence.toFixed(2)} ({getConfidenceLabel(result.simulation.confidence)})
                </p>
                {result.simulation.confidence_interval ? (
                  <p className="mt-1 text-xs text-slate-400">
                    CI: {result.simulation.confidence_interval[0].toFixed(2)} ~ {result.simulation.confidence_interval[1].toFixed(2)}
                    {result.simulation.error_bound ? ` / Error Bound: ±${result.simulation.error_bound}` : ""}
                  </p>
                ) : null}
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {result.simulation.kpis.map((kpi) => (
                    <div key={kpi.kpi} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-3">
                      {(() => {
                        const changePct = calculateChangePct(kpi);
                        return (
                          <>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{formatKpiLabel(kpi.kpi)}</p>
                      <p className="mt-1 text-sm text-slate-300">
                        {kpi.baseline} → {kpi.simulated} {kpi.unit}
                      </p>
                      <p className={`text-sm font-semibold ${changePct >= 0 ? "text-amber-300" : "text-emerald-300"}`}>
                        {changePct >= 0 ? "+" : ""}
                        {changePct}%
                      </p>
                          </>
                        );
                      })()}
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5 min-h-[420px]">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">Comparison Charts</h2>
            {!result ? (
              <p className="mt-3 text-sm text-slate-400">실행 후 차트가 표시됩니다.</p>
            ) : (
              <div className="mt-4 grid gap-4">
                <div data-testid="simulation-chart-timeseries" className="h-64 rounded-2xl border border-slate-800 bg-slate-950/50 p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="kpi" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="baseline" stroke="#38bdf8" strokeWidth={2} />
                      <Line type="monotone" dataKey="simulated" stroke="#f59e0b" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div data-testid="simulation-chart-delta" className="h-64 rounded-2xl border border-slate-800 bg-slate-950/50 p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="kpi" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="changePct" fill="#22d3ee" name="Change %" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {compareData.length > 0 ? (
                  <div className="h-56 rounded-2xl border border-slate-800 bg-slate-950/50 p-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={compareData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis dataKey="kpi" stroke="#94a3b8" />
                        <YAxis stroke="#94a3b8" />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="previous" fill="#64748b" name="Previous Run" />
                        <Bar dataKey="current" fill="#14b8a6" name="Current Run" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}
              </div>
            )}
          </section>

          {/* 토폴로지 맵 시각화 */}
          <section>
            <TopologyMap
              service={service}
              scenarioType={scenarioType}
              assumptions={assumptions}
              enabled={Boolean(result)}
            />
          </section>

          <section data-testid="simulation-evidence-panel" className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5 min-h-[220px]">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">Algorithm & Evidence</h2>
            {!result ? (
              <p className="mt-3 text-sm text-slate-400">실행 후 알고리즘 설명과 근거가 표시됩니다.</p>
            ) : (
              <div className="mt-3 space-y-3 text-sm text-slate-300">
                <p>
                  <span className="text-slate-500">Strategy:</span> {result.simulation.strategy.toUpperCase()} /
                  <span className="text-slate-500"> Model:</span> {String(result.simulation.model_info.version ?? "n/a")}
                </p>
                {plan ? (
                  <p className="text-xs text-slate-400">
                    Baseline Window: {plan.baseline_window} / Horizon: {plan.horizon} / Service: {plan.service}
                  </p>
                ) : null}
                <p>{result.simulation.explanation}</p>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Recommended Actions</p>
                  <ul className="mt-1 list-disc pl-5">
                    {result.simulation.recommended_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </div>
                <pre className="overflow-auto rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-300">
                  {JSON.stringify(result.references, null, 2)}
                </pre>
                {result.simulation.warnings.length > 0 ? (
                  <ul data-testid="simulation-warning-list" className="list-disc pl-5 text-amber-300">
                    {result.simulation.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-300">Backtest Report</h2>
            {!backtest ? (
              <p className="mt-3 text-sm text-slate-400">좌측에서 Backtest 버튼을 눌러 전략 성능 지표를 확인하세요.</p>
            ) : (
              <div className="mt-3 grid gap-3 text-sm text-slate-300 md:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-xs text-slate-500">R2</p>
                  <p className="text-lg font-semibold">{backtest.metrics.r2.toFixed(4)}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-xs text-slate-500">MAPE</p>
                  <p className="text-lg font-semibold">{(backtest.metrics.mape * 100).toFixed(2)}%</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-xs text-slate-500">RMSE</p>
                  <p className="text-lg font-semibold">{backtest.metrics.rmse.toFixed(3)}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
                  <p className="text-xs text-slate-500">Coverage@90</p>
                  <p className="text-lg font-semibold">{(backtest.metrics.coverage_90 * 100).toFixed(2)}%</p>
                </div>
              </div>
            )}
          </section>
        </main>
      </section>

      <Toast
        message={statusMessage ?? ""}
        type={
          statusMessage?.includes("토폴로지 데이터가 없습니다")
            ? "warning"
            : statusMessage?.includes("실패")
              ? "error"
              : "info"
        }
        onDismiss={() => setStatusMessage(null)}
      />
    </div>
  );
}
