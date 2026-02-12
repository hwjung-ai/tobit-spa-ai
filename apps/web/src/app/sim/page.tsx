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
import BuilderCopilotPanel from "@/components/chat/BuilderCopilotPanel";
import { recordCopilotMetric } from "@/lib/copilot/metrics";
import {
  extractJsonCandidates,
  stripCodeFences,
  tryParseJson,
} from "@/lib/copilot/json-utils";
import { cn } from "@/lib/utils";

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

interface SimDraftPayload {
  question: string;
  scenario_type: ScenarioType;
  strategy: Strategy;
  horizon: string;
  service: string;
  assumptions: Record<string, number>;
}

interface SimDraftEnvelope {
  type: "sim_draft";
  draft: Partial<SimDraftPayload>;
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
    badge: "규칙형",
  },
  ml: {
    title: "ML",
    desc: "비선형 상호작용을 반영하는 surrogate 추론입니다.",
    badge: "고급형",
  },
  dl: {
    title: "DL",
    desc: "신경망 기반 비선형 패턴을 반영하는 딥러닝 surrogate입니다.",
    badge: "심화형",
  },
};

const SIM_COPILOT_INSTRUCTION = [
  "You are Tobit SIM Workspace AI Copilot.",
  "Output must be a single JSON object: {\"type\":\"sim_draft\",\"draft\":{...}}.",
  "draft may include: question, scenario_type, strategy, horizon, service, assumptions.",
  "scenario_type must be one of: what_if, stress_test, capacity.",
  "strategy must be one of: rule, stat, ml, dl.",
  "assumptions may include traffic_change_pct, cpu_change_pct, memory_change_pct.",
  "No markdown or code fences in final response.",
].join(" ");

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

const isScenarioType = (value: unknown): value is ScenarioType =>
  value === "what_if" || value === "stress_test" || value === "capacity";

const isStrategy = (value: unknown): value is Strategy =>
  value === "rule" || value === "stat" || value === "ml" || value === "dl";

const parseSimDraft = (text: string): { ok: boolean; draft?: Partial<SimDraftPayload>; error?: string } => {
  const candidates = [stripCodeFences(text), text];

  for (const candidate of candidates) {
    const parsedItems: unknown[] = [];
    const direct = tryParseJson(candidate);
    if (direct !== null) parsedItems.push(direct);
    for (const extracted of extractJsonCandidates(candidate)) {
      const value = tryParseJson(extracted);
      if (value !== null) parsedItems.push(value);
    }

    for (const parsed of parsedItems) {
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) continue;
      const typed = parsed as Partial<SimDraftEnvelope>;
      if (typed.type !== "sim_draft") continue;
      if (!typed.draft || typeof typed.draft !== "object" || Array.isArray(typed.draft)) {
        return { ok: false, error: "sim_draft의 draft 객체가 필요합니다." };
      }
      return { ok: true, draft: typed.draft as Partial<SimDraftPayload> };
    }
  }

  return { ok: false, error: "type=sim_draft 객체를 찾지 못했습니다." };
};

export default function SimPage() {
  const [templates, setTemplates] = useState<SimulationTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [services, setServices] = useState<string[]>([]);
  const [servicesLoading, setServicesLoading] = useState(true);
  const [question, setQuestion] = useState("트래픽이 20% 증가하면 서비스 지표가 어떻게 변화나?");
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
  const [simDraft, setSimDraft] = useState<Partial<SimDraftPayload> | null>(null);
  const [draftStatus, setDraftStatus] = useState<"idle" | "draft_ready" | "error">("idle");
  const [draftNotes, setDraftNotes] = useState<string | null>(null);
  const [lastParseStatus, setLastParseStatus] = useState<"idle" | "success" | "fail">("idle");
  const [lastParseError, setLastParseError] = useState<string | null>(null);
  const [lastAssistantRaw, setLastAssistantRaw] = useState<string>("");

  useEffect(() => {
    const loadServices = async () => {
      setServicesLoading(true);
      try {
        const response = await authenticatedFetch<Envelope<{ services: string[] }>>("/api/sim/services");
        const loaded = response.data?.services ?? [];
        if (loaded.length > 0) {
          setServices(loaded);
          setService(loaded[0]);
        } else {
          setServices([]);
          setService("");
          setStatusMessage("사용 가능한 SIM 서비스가 없습니다. 토폴로지 동기화 또는 SIM_MODE 설정을 확인해 주세요.");
        }
      } catch (err) {
        console.error("Failed to load simulation services", err);
        setServices([]);
        setService("");
        setStatusMessage("서비스 목록을 불러오지 못했습니다.");
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
    if (!services.includes(trimmed)) {
      throw new Error("선택한 Service가 서비스 목록에 없습니다.");
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

  const applySimDraftToForm = (draft: Partial<SimDraftPayload>) => {
    if (typeof draft.question === "string" && draft.question.trim()) {
      setQuestion(draft.question);
    }
    if (isScenarioType(draft.scenario_type)) {
      setScenarioType(draft.scenario_type);
    }
    if (isStrategy(draft.strategy)) {
      setStrategy(draft.strategy);
    }
    if (typeof draft.horizon === "string" && draft.horizon.trim()) {
      setHorizon(draft.horizon);
    }
    if (typeof draft.service === "string" && draft.service.trim()) {
      setService(draft.service.trim());
    }
    if (
      draft.assumptions &&
      typeof draft.assumptions === "object" &&
      !Array.isArray(draft.assumptions)
    ) {
      setAssumptions((prev) => {
        const merged: Record<string, number> = { ...prev };
        for (const [key, value] of Object.entries(draft.assumptions ?? {})) {
          if (typeof value === "number" && Number.isFinite(value) && key in assumptionMeta) {
            merged[key] = value;
          }
        }
        return merged;
      });
    }
  };

  const processAssistantDraft = (messageText: string, isComplete: boolean) => {
    setLastAssistantRaw(messageText);
    const result = parseSimDraft(messageText);
    setLastParseStatus(result.ok ? "success" : "fail");
    setLastParseError(result.error ?? null);

    if (result.ok && result.draft) {
      if (isComplete) {
        recordCopilotMetric("sim-workspace", "parse_success");
      }
      setSimDraft(result.draft);
      setDraftStatus("draft_ready");
      setDraftNotes("SIM 드래프트가 준비되었습니다. Apply로 좌측 입력에 반영하세요.");
      return;
    }

    if (isComplete) {
      recordCopilotMetric("sim-workspace", "parse_failure", result.error ?? null);
      setSimDraft(null);
      setDraftStatus("error");
      setDraftNotes("SIM 드래프트를 해석할 수 없습니다.");
      return;
    }

    if (draftStatus !== "draft_ready") {
      setDraftStatus("idle");
      setDraftNotes("AI가 답변을 생성 중입니다...");
    }
  };

  const copilotBuilderContext = useMemo(
    () => ({
      sim_mode: "workspace",
      question,
      scenario_type: scenarioType,
      strategy,
      horizon,
      service,
      assumptions,
      selected_template: selectedTemplate
        ? {
            id: selectedTemplate.id,
            name: selectedTemplate.name,
            scenario_type: selectedTemplate.scenario_type,
            default_strategy: selectedTemplate.default_strategy,
          }
        : null,
      latest_summary: result?.summary ?? null,
      latest_kpis: result?.simulation.kpis ?? [],
      draft_status: draftStatus,
    }),
    [assumptions, draftStatus, horizon, question, result, scenarioType, selectedTemplate, service, strategy]
  );

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--background)", color: "var(--foreground)" }}>
      <header className="border-b px-6 py-4" style={{ borderColor: "var(--border)" }}>
        <h1 className="text-2xl font-semibold" style={{ color: "var(--foreground)" }}>SIM Workspace</h1>
        <p className="mt-2 text-sm" style={{ color: "var(--muted-foreground)" }}>
          질문과 가정값을 기반으로 계획을 검증한 뒤 실행합니다. 결과는 KPI 변화, 비교 차트, 피드백/모델 근거를 함께 제공합니다.
        </p>
      </header>
      <main className="min-h-[calc(100vh-96px)] px-6 py-6">
        {/* Main Content Grid */}
        <section className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)_320px]">
        {/* Left Panel - Scenario Builder */}
        <aside className="space-y-4 rounded-3xl border p-5 min-h-[320px]" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
          <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Scenario Builder</h2>

          <label className="block text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
            질문
            <textarea
              data-testid="simulation-question-input"
              className="mt-2 w-full rounded-3xl px-3 py-2 text-sm outline-none transition"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
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
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>템플릿</p>
            <div className="mt-2 grid gap-2">
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  data-testid="simulation-template-select"
                  onClick={() => applyTemplate(template)}
                  className="rounded-3xl border px-3 py-2 text-left transition"
                  style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                >
                  <p className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{template.name}</p>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>{template.description}</p>
                </button>
              ))}
            </div>
            {selectedTemplate ? (
              <div className="mt-3 rounded-3xl border px-3 py-2" style={{ borderColor: "var(--success)", backgroundColor: "rgba(var(--success-rgb), 0.15)" }}>
                <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--success)" }}>Applied Template</p>
                <p className="mt-1 text-sm" style={{ color: "var(--foreground)" }}>{selectedTemplate.name}</p>
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>{selectedTemplate.description}</p>
              </div>
            ) : (
              <p className="mt-2 text-xs" style={{ color: "var(--muted-foreground)" }}>템플릿을 클릭하면 질문/전략/가정값이 자동 적용됩니다.</p>
            )}
          </div>

          <label className="block text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
            시나리오 유형
            <select
              className="mt-2 w-full rounded-3xl px-3 py-2 text-sm outline-none transition"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
              value={scenarioType}
              onChange={(event) => setScenarioType(event.target.value as ScenarioType)}
            >
              <option value="what_if">What-if</option>
              <option value="stress_test">Stress Test</option>
              <option value="capacity">Capacity</option>
            </select>
          </label>

          <label className="block text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
            Service
            <select
              className="mt-2 w-full rounded-3xl px-3 py-2 text-sm outline-none transition"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
              value={service}
              onChange={(event) => setService(event.target.value)}
            >
              {services.length === 0 ? (
                <option value="">No services available</option>
              ) : null}
              {services.map((svc) => (
                <option key={svc} value={svc}>
                  {svc}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
            Horizon
            <input
              className="mt-2 w-full rounded-3xl px-3 py-2 text-sm outline-none transition"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
              value={horizon}
              onChange={(event) => setHorizon(event.target.value)}
            />
          </label>

          <div>
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>가정값</p>
            {Object.entries(assumptions).map(([key, value]) => {
              const meta = assumptionMeta[key];
              if (!meta) return null;
              return (
                <label key={key} className="block rounded-3xl border px-3 py-2" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs" style={{ color: "var(--foreground)" }}>{meta.label}</span>
                    <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
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
                    style={{ accentColor: "var(--primary)" }}
                  />
                </label>
              );
            })}
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>전략 선택</p>
            {(Object.keys(strategyMeta) as Strategy[]).map((s) => (
              <button
                key={s}
                data-testid="simulation-strategy-select"
                onClick={() => setStrategy(s)}
                className={cn(
                  "rounded-3xl border px-3 py-2 text-left transition",
                  strategy === s
                    ? "text-white"
                    : ""
                )}
                style={strategy === s
                  ? { borderColor: "var(--primary)", backgroundColor: "var(--primary)" }
                  : { borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }
                }
                onMouseEnter={(e) => { if (strategy !== s) e.currentTarget.style.borderColor = "var(--primary)"; }}
                onMouseLeave={(e) => { if (strategy !== s) e.currentTarget.style.borderColor = "var(--border)"; }}
              >
                <div className="flex items-center justify-between">
                  <span className={cn("text-sm font-semibold", strategy === s ? "text-white" : "")}>{strategyMeta[s].title}</span>
                  <span className={cn("text-[10px] uppercase tracking-wider", strategy === s ? "text-white" : "")} style={{ color: strategy === s ? undefined : "var(--muted-foreground)" }}>{strategyMeta[s].badge}</span>
                </div>
                <p className={cn("mt-1 text-xs", strategy === s ? "text-white" : "")} style={{ color: strategy === s ? undefined : "var(--muted-foreground)" }}>{strategyMeta[s].desc}</p>
              </button>
            ))}
          </div>

          <button
            data-testid="simulation-run-button"
            className={cn(
              "w-full rounded-3xl px-4 py-2 text-sm font-semibold uppercase tracking-wider text-white transition disabled:cursor-not-allowed",
              loading || servicesLoading || !question.trim() || !service.trim()
                ? ""
                : ""
            )}
            style={{
              backgroundColor: (loading || servicesLoading || !question.trim() || !service.trim()) ? "var(--muted-background)" : "var(--primary)",
              opacity: (loading || servicesLoading || !question.trim() || !service.trim()) ? 0.6 : 1
            }}
            onMouseEnter={(e) => { if (!(loading || servicesLoading || !question.trim() || !service.trim())) e.currentTarget.style.opacity = "0.9"; }}
            onMouseLeave={(e) => { if (!(loading || servicesLoading || !question.trim() || !service.trim())) e.currentTarget.style.opacity = "1"; }}
            onClick={handleRun}
            disabled={loading || servicesLoading || !question.trim() || !service.trim()}
          >
            {loading ? "Running..." : servicesLoading ? "Loading Services..." : "Run Simulation"}
          </button>
          {!question.trim() ? <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>질문을 입력하면 실행할 수 있습니다.</p> : null}
          {!service.trim() ? <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>Service를 입력하거나 선택하면 실행할 수 있습니다.</p> : null}

          <div className="flex gap-2">
            <button
              type="button"
              data-testid="simulation-backtest-button"
              className="rounded-3xl border px-3 py-2 text-xs font-semibold uppercase tracking-wider transition"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
              onClick={handleBacktest}
              disabled={servicesLoading || !service.trim()}
            >
              Run Backtest
            </button>
            <button
              type="button"
              data-testid="simulation-export-button"
              className="rounded-3xl border px-3 py-2 text-xs font-semibold uppercase tracking-wider transition"
              style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--success)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
              onClick={handleExportCsv}
              disabled={servicesLoading || !service.trim()}
            >
              Export CSV
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="space-y-4">
          {/* KPI Summary Section */}
          <section className="rounded-3xl border p-5" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
            <h2 data-testid="simulation-kpi-summary" className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
              KPI Summary
            </h2>
            {!result ? (
              <p className="mt-3 text-sm" style={{ color: "var(--muted-foreground)" }}>왼쪽에서 시나리오를 설정하고 실행하세요.</p>
            ) : (
              <>
                <p className="mt-3 text-sm" style={{ color: "var(--foreground)" }}>{result.summary}</p>
                <p className="mt-1 text-xs" style={{ color: "var(--muted-foreground)" }}>
                  Confidence: {result.simulation.confidence.toFixed(2)} ({getConfidenceLabel(result.simulation.confidence)})
                </p>
                {result.simulation.confidence_interval ? (
                  <p className="mt-1 text-xs" style={{ color: "var(--muted-foreground)" }}>
                    CI: {result.simulation.confidence_interval[0].toFixed(2)} ~ {result.simulation.confidence_interval[1].toFixed(2)}
                    {result.simulation.error_bound ? ` / Error Bound: ±${result.simulation.error_bound}` : ""}
                  </p>
                ) : null}
                <div className="mt-3 grid gap-3">
                  {result.simulation.kpis.map((kpi) => {
                    const changePct = calculateChangePct(kpi);
                    return (
                      <div key={kpi.kpi} className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                        <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>{formatKpiLabel(kpi.kpi)}</p>
                        <p className="mt-1 text-sm" style={{ color: "var(--foreground)" }}>
                          {kpi.baseline} → {kpi.simulated} {kpi.unit}
                        </p>
                        <p className={cn("text-sm font-semibold", changePct >= 0 ? "text-amber-600" : "text-emerald-600")} style={{ color: changePct >= 0 ? "var(--warning)" : "var(--success)" }}>
                          {changePct >= 0 ? "+" : ""}
                          {changePct}%
                        </p>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </section>

          {/* Comparison Charts Section */}
          <section className="rounded-3xl border p-5" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Comparison Charts</h2>
            {!result ? (
              <p className="mt-3 text-sm" style={{ color: "var(--muted-foreground)" }}>실행 후 차트가 표시됩니다.</p>
            ) : (
              <div className="mt-4 grid gap-4">
                <div className="h-64 rounded-3xl border p-2" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                      <XAxis dataKey="kpi" stroke="var(--border-muted)" />
                      <YAxis stroke="var(--border-muted)" />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="baseline" stroke="var(--primary)" strokeWidth={2} />
                      <Line type="monotone" dataKey="simulated" stroke="var(--warning)" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="h-64 rounded-3xl border p-2" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                      <XAxis dataKey="kpi" stroke="var(--border-muted)" />
                      <YAxis stroke="var(--border-muted)" />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="changePct" fill="var(--success)" name="Change %" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {compareData.length > 0 ? (
                  <div className="h-56 rounded-3xl border p-2" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={compareData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                        <XAxis dataKey="kpi" stroke="var(--border-muted)" />
                        <YAxis stroke="var(--border-muted)" />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="previous" fill="var(--muted-foreground)" name="Previous Run" />
                        <Bar dataKey="current" fill="var(--primary)" name="Current Run" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}
              </div>
            )}
          </section>

          {/* Topology Map Section */}
          <section>
            <TopologyMap
              service={service}
              scenarioType={scenarioType}
              assumptions={assumptions}
              enabled={Boolean(result)}
            />
          </section>

          {/* Evidence Panel */}
          <section className="rounded-3xl border p-5 min-h-[220px]" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Algorithm & Evidence</h2>
            {!result ? (
              <p className="mt-3 text-sm" style={{ color: "var(--muted-foreground)" }}>실행 후 알고리즘 설명과 근거가 표시됩니다.</p>
            ) : (
              <div className="mt-3 space-y-3 text-sm" style={{ color: "var(--foreground)" }}>
                <p>
                  <span style={{ color: "var(--muted-foreground)" }}>Strategy:</span> {result.simulation.strategy.toUpperCase()} /
                  <span style={{ color: "var(--muted-foreground)" }}> Model:</span> {String(result.simulation.model_info.version ?? "n/a")}
                </p>
                {plan ? (
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    Baseline Window: {plan.baseline_window} / Horizon: {plan.horizon} / Service: {plan.service}
                  </p>
                ) : null}
                <p>{result.simulation.explanation}</p>
                <div>
                  <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Recommended Actions</p>
                  <ul className="mt-1 list-disc pl-5">
                    {result.simulation.recommended_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </div>
                <pre className="overflow-auto rounded-3xl border p-3 text-xs font-mono" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}>
                  {JSON.stringify(result.references, null, 2)}
                </pre>
                {result.simulation.warnings.length > 0 ? (
                  <ul className="list-disc pl-5" style={{ color: "var(--warning)" }}>
                    {result.simulation.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            )}
          </section>

          {/* Backtest Report Section */}
          <section className="rounded-3xl border p-5" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Backtest Report</h2>
            {!backtest ? (
              <p className="mt-3 text-sm" style={{ color: "var(--muted-foreground)" }}>왼쪽에서 Backtest 버튼을 눌러 전략 성능 지표를 확인하세요.</p>
            ) : (
              <div className="mt-3 grid gap-3 text-sm" style={{ color: "var(--foreground)" }}>
                <div className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>R2</p>
                  <p className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{backtest.metrics.r2.toFixed(4)}</p>
                </div>
                <div className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>MAPE</p>
                  <p className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{(backtest.metrics.mape * 100).toFixed(2)}%</p>
                </div>
                <div className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>RMSE</p>
                  <p className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{backtest.metrics.rmse.toFixed(3)}</p>
                </div>
                <div className="rounded-3xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Coverage@90%</p>
                  <p className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{(backtest.metrics.coverage_90 * 100).toFixed(2)}%</p>
                </div>
              </div>
            )}
          </section>
        </main>

        {/* Right Panel - AI Copilot */}
        <aside className="min-h-[320px] rounded-3xl border p-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:overflow-y-auto" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
          <div className="space-y-4">
            <BuilderCopilotPanel
              builderSlug="sim-workspace"
              instructionPrompt={SIM_COPILOT_INSTRUCTION}
              expectedContract="sim_draft"
              builderContext={copilotBuilderContext}
              onAssistantMessage={(messageText) => processAssistantDraft(messageText, false)}
              onAssistantMessageComplete={(messageText) => processAssistantDraft(messageText, true)}
              onUserMessage={() => {
                setSimDraft(null);
                setDraftStatus("idle");
                setDraftNotes(null);
                setLastParseStatus("idle");
                setLastParseError(null);
                setLastAssistantRaw("");
              }}
              inputPlaceholder="Ask AI Copilot to generate a SIM draft..."
            />
            <div className="space-y-3 rounded-3xl border p-4 text-sm" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}>
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Draft status</span>
                <span className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                  {draftStatus === "draft_ready"
                    ? "Ready"
                    : draftStatus === "error"
                      ? "Error"
                      : "Idle"}
                </span>
              </div>
              {draftNotes ? <p className="text-sm" style={{ color: "var(--foreground)" }}>{draftNotes}</p> : null}
              <div className="grid gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (!simDraft) return;
                    applySimDraftToForm(simDraft);
                    setStatusMessage("AI 드래프트가 좌측 Scenario Builder에 반영되었습니다.");
                  }}
                  disabled={!simDraft}
                  className="rounded-3xl px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-white transition disabled:opacity-40"
                  style={{ backgroundColor: "var(--primary)" }}
                  onMouseEnter={(e) => { if (simDraft) e.currentTarget.style.opacity = "0.9"; }}
                  onMouseLeave={(e) => { if (simDraft) e.currentTarget.style.opacity = "1"; }}
                >
                  Apply
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSimDraft(null);
                    setDraftStatus("idle");
                    setDraftNotes(null);
                    setLastParseStatus("idle");
                    setLastParseError(null);
                    setLastAssistantRaw("");
                  }}
                  className="rounded-3xl border px-3 py-2 text-[11px] font-semibold uppercase tracking-wider transition"
                  style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                >
                  Discard
                </button>
              </div>
              {simDraft ? (
                <div className="space-y-2 rounded-3xl border p-3" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Draft JSON</p>
                  <pre className="max-h-44 overflow-auto rounded-3xl border p-2 text-[11px] font-mono" style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }}>
                    {JSON.stringify(simDraft, null, 2)}
                  </pre>
                </div>
              ) : (
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>No SIM draft yet. Ask Copilot to generate one.</p>
              )}
              <details className="rounded-3xl border p-3 text-[11px]" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}>
                <summary className="cursor-pointer text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                  Debug
                </summary>
                <div className="mt-2 space-y-1">
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                    Parse status: {lastParseStatus}
                  </p>
                  {lastParseError ? <p className="text-[11px]" style={{ color: "var(--error)" }}>Error: {lastParseError}</p> : null}
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Last assistant raw</p>
                  <pre className="max-h-24 overflow-auto rounded-3xl border p-2 text-[11px] font-mono" style={{ borderColor: "var(--border)", backgroundColor: "var(--background)", color: "var(--foreground)" }}>
                    {lastAssistantRaw || "없음"}
                  </pre>
                </div>
              </details>
            </div>
          </div>
        </aside>
        </section>
      </main>

      {/* Toast Notification */}
      <Toast
        message={statusMessage ?? ""}
        type={
          statusMessage?.includes("토폴로지 데이터가 없습니다")
            ? "warning"
            : statusMessage?.includes("찾을 수 없습니다")
              ? "error"
              : statusMessage?.includes("실패")
                ? "error"
                : "info"
        }
        onDismiss={() => setStatusMessage(null)}
        duration={3000}
      />
    </div>
  );
}
