"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import BuilderShell from "../../components/builder/BuilderShell";
import BuilderCopilotPanel from "../../components/chat/BuilderCopilotPanel";
import { saveUiWithFallback } from "../../lib/uiCreatorSave";
import Editor from "@monaco-editor/react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

const DEFAULT_SCHEMA = {
  data_source: {
    endpoint: "/runtime/config-inventory",
    method: "GET",
    default_params: {
      tenant_id: "t1",
      limit: 10,
    },
  },
  layout: {
    type: "grid",
    columns: ["tenant_id", "ci_count"],
    title: "Configuration inventory",
  },
};

const METRIC_POLLING_DASHBOARD_TEMPLATE = {
  version: 1,
  ui_type: "dashboard",
  widgets: [
    {
      id: "metric-status",
      title: "Metric polling status",
      layout: { x: 0, y: 0, w: 6, h: 6 },
      data_source: { endpoint: "/cep/scheduler/status", method: "GET" },
      render: { type: "json", path: "data.status" },
    },
    {
      id: "metric-instances",
      title: "Scheduler instances",
      layout: { x: 6, y: 0, w: 6, h: 6 },
      data_source: { endpoint: "/cep/scheduler/instances", method: "GET" },
      render: {
        type: "grid",
        rowsPath: "data.instances",
        columns: ["instance_id", "is_leader", "last_heartbeat_at", "leader_stale"],
      },
    },
    {
      id: "metric-matches",
      title: "Recent metric matches",
      layout: { x: 0, y: 6, w: 12, h: 5 },
      data_source: { endpoint: "/cep/scheduler/metric-polling", method: "GET" },
      render: {
        type: "grid",
        rowsPath: "data.telemetry.recent_matches",
        columns: ["rule_name", "actual_value", "threshold", "op", "matched_at"],
      },
    },
    {
      id: "metric-logs",
      title: "Metric rule exec logs",
      layout: { x: 0, y: 11, w: 12, h: 6 },
      data_source: {
        endpoint: "/cep/rules/<METRIC_RULE_ID>/exec-logs",
        method: "GET",
      },
      render: {
        type: "grid",
        rowsPath: "data.logs",
        columns: ["status", "duration_ms", "triggered_at", "error_message"],
      },
    },
  ],
};

/* Dashboard widget example with chart_line:
{
  "version": 1,
  "ui_type": "dashboard",
  "widgets": [
    {
      "id": "metric-trend",
      "title": "CPU Trend",
      "layout": { "x": 0, "y": 0, "w": 12, "h": 4 },
      "data_source": { "endpoint": "/runtime/metrics-summary", "method": "GET" },
      "render": {
        "type": "chart_line",
        "rowsPath": "data.result.rows",
        "xKey": "metric_name",
        "yKey": "peak"
      }
    }
  ]
}
*/

type UiType = "grid" | "chart" | "dashboard";

interface UiDefinitionSummary {
  ui_id: string;
  ui_name: string;
  ui_type: UiType;
  is_active: boolean;
  updated_at: string;
}

interface UiDefinitionDetail extends UiDefinitionSummary {
  schema: Record<string, unknown>;
  description: string | null;
  tags: Record<string, unknown>;
  created_by: string | null;
  created_at: string;
}

interface PreviewResult {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  duration_ms: number;
}

interface UiDraft {
  ui_name: string;
  description?: string;
  layout: Record<string, unknown>;
  data_bindings?: Record<string, unknown>;
  actions?: Record<string, unknown>[];
}

type DraftStatus = "idle" | "draft_ready" | "previewing" | "testing" | "applied" | "saved" | "outdated" | "error";
type PreviewMode = "layout" | "runtime";

const DEFAULT_PARAMS_TEXT = JSON.stringify(DEFAULT_SCHEMA.data_source.default_params, null, 2);
const DEFAULT_MOCK_COLUMNS = ["col1", "col2", "col3"];

const buildMockRows = (columns: string[], count = 8) => {
  return Array.from({ length: count }, (_, idx) => {
    const row: Record<string, unknown> = {};
    columns.forEach((column, colIndex) => {
      row[column] = colIndex === 0 ? `row-${idx + 1}` : idx * 10 + colIndex;
    });
    return row;
  });
};

const buildMockChartRows = (xKey: string, yKey: string, count = 12) => {
  return Array.from({ length: count }, (_, idx) => ({
    [xKey]: `T${idx + 1}`,
    [yKey]: (idx + 1) * 5,
  }));
};
const DRAFT_STORAGE_PREFIX = "ui-creator:draft:";
const FINAL_STORAGE_PREFIX = "ui-creator:ui:";

const draftStatusLabels: Record<DraftStatus, string> = {
  idle: "대기 중",
  draft_ready: "드래프트 준비됨",
  previewing: "미리보기",
  testing: "테스트 중",
  applied: "폼 적용됨",
  saved: "저장됨",
  outdated: "드래프트 오래됨",
  error: "오류 발생",
};

const tryParseJson = (value: string) => {
  try {
    return JSON.parse(value);
  } catch (error) {
    return null;
  }
};

const stripCodeFences = (value: string) => {
  const match = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (match && match[1]) {
    return match[1].trim();
  }
  return value.trim();
};

const extractFirstJsonObject = (text: string) => {
  const startIdx = text.indexOf("{");
  if (startIdx === -1) {
    throw new Error("JSON 객체가 포함되어 있지 않습니다.");
  }
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = startIdx; i < text.length; i += 1) {
    const char = text[i];
    if (escape) {
      escape = false;
      continue;
    }
    if (char === "\\") {
      escape = true;
      continue;
    }
    if (char === '"') {
      inString = !inString;
      continue;
    }
    if (inString) {
      continue;
    }
    if (char === "{") {
      depth += 1;
    }
    if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        return text.slice(startIdx, i + 1);
      }
    }
  }
  if (depth > 0 && !inString) {
    return text.slice(startIdx) + "}".repeat(depth);
  }
  throw new Error("JSON 객체를 추출하지 못했습니다.");
};

const validateUiDraftShape = (draft: UiDraft) => {
  if (!draft.ui_name?.trim()) {
    return "draft.ui_name 값이 필요합니다.";
  }
  if (!draft.layout || typeof draft.layout !== "object") {
    return "draft.layout은 JSON 객체여야 합니다.";
  }
  return null;
};

const parseUiDraft = (text: string) => {
  const candidates = [stripCodeFences(text), text];
  for (const candidate of candidates) {
    if (!candidate.trim()) {
      continue;
    }
    const direct = tryParseJson(candidate);
    const parsed = direct ?? (() => {
      const extracted = extractFirstJsonObject(candidate);
      return JSON.parse(extracted);
    })();
    if (typeof parsed !== "object" || parsed === null) {
      continue;
    }
    const obj = parsed as Record<string, unknown>;
    if (obj.type !== "ui_draft") {
      return { ok: false, error: "type=ui_draft인 객체가 아닙니다." };
    }
    if (!obj.draft || typeof obj.draft !== "object") {
      return { ok: false, error: "draft 필드가 없습니다." };
    }
    const draft = obj.draft as UiDraft;
    const shapeError = validateUiDraftShape(draft);
    if (shapeError) {
      return { ok: false, error: shapeError };
    }
    return { ok: true, draft, notes: (obj.notes as string) ?? null };
  }
  return { ok: false, error: "JSON 객체를 추출할 수 없습니다." };
};

const parseJsonObject = (value: string, label: string) => {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed);
  if (typeof parsed !== "object" || Array.isArray(parsed) || parsed === null) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed;
};

const GridPreview = ({ columns, rows }: PreviewResult) => {
  const displayColumns = columns.length
    ? columns
    : rows.length
    ? Object.keys(rows[0])
    : [];
  const displayRows = rows.slice(0, 12);
  if (!displayColumns.length) {
    return <p className="text-xs text-slate-400">No columns to render.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs text-slate-200">
        <thead>
          <tr>
            {displayColumns.map((column) => (
              <th
                key={column}
                className="border-b border-slate-800 px-2 py-1 text-left uppercase tracking-normal text-slate-500"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, rowIndex) => (
            <tr
              key={`row-${rowIndex}`}
              className={rowIndex % 2 === 0 ? "bg-slate-950/40" : "bg-slate-900/40"}
            >
              {displayColumns.map((column) => (
                <td key={`${rowIndex}-${column}`} className="px-2 py-1 align-top">
                  <pre className="m-0 text-[12px] text-slate-100">{String(row[column] ?? "")}</pre>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ChartPreview = ({ rows, columns, layout }: PreviewResult & { layout: Record<string, unknown> }) => {
  if (!rows.length) {
    return <p className="text-xs text-slate-400">No data yet for chart.</p>;
  }
  const xKey = (layout.xKey as string) ?? (layout.x_key as string) ?? columns[0];
  const numericColumn = columns.find((column) => rows.some((row) => typeof row[column] === "number"));
  const yKey = (layout.yKey as string) ?? (layout.y_key as string) ?? numericColumn ?? columns[1] ?? columns[0];
  if (!xKey || !yKey) {
    return <p className="text-xs text-slate-400">Chart requires xKey and yKey.</p>;
  }
  const chartData = rows.map((row, index) => ({
    __x: String(row[xKey] ?? index),
    __y: typeof row[yKey] === "number" ? (row[yKey] as number) : Number(row[yKey]) || 0,
  }));
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis dataKey="__x" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" />
          <Tooltip wrapperStyle={{ backgroundColor: "#0f172a" }} />
          <Line type="monotone" dataKey="__y" stroke="#38bdf8" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const getPathValue = (target: any, path?: string) => {
  if (!path || typeof path !== "string") {
    return null;
  }
  return path.split(".").reduce((acc, key) => (acc && key in acc ? acc[key] : null), target);
};

const useWidgetData = ({
  endpoint,
  method = "GET",
  params = {},
  reloadTrigger = 0,
}: {
  endpoint: string;
  method?: "GET" | "POST";
  params?: Record<string, unknown>;
  reloadTrigger?: number;
}) => {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [reloadIndex, setReloadIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const fetchWidget = async () => {
      setLoading(true);
      setError(null);
      try {
        const baseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
        const normalized = (() => {
          if (endpoint.startsWith("http")) {
            return endpoint;
          }
          const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
          if (path.startsWith("/runtime/")) {
            return `${baseUrl}${path}`;
          }
          if (path.startsWith("/api-manager/")) {
            return `${baseUrl}/runtime${path.replace("/api-manager", "")}`;
          }
          return `${baseUrl}/runtime${path}`;
        })();
        const url = new URL(normalized);
        let options: RequestInit | undefined;
        if (method === "GET") {
          Object.entries(params ?? {}).forEach(([key, value]) => {
            url.searchParams.set(key, value == null ? "" : String(value));
          });
        } else {
          options = {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ params }),
          };
        }
        const response = await fetch(url.toString(), options);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.message ?? payload.detail ?? "Widget fetch failed");
        }
        if (!cancelled) {
          setData(payload);
          setLastFetched(new Date());
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Widget fetch failed");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    fetchWidget();
    return () => {
      cancelled = true;
    };
  }, [endpoint, method, JSON.stringify(params), reloadIndex, reloadTrigger]);

  const refetch = useCallback(() => {
    setReloadIndex((prev) => prev + 1);
  }, []);

  return { data, error, loading, lastFetched, refetch };
};

const ChartWidgetContent = ({
  rows,
  layout,
}: {
  rows: Record<string, unknown>[];
  layout: Record<string, unknown>;
}) => {
  if (!rows.length) {
    return <p className="text-[11px] text-slate-400">No chart rows.</p>;
  }
  const xKey = (layout.xKey as string | undefined) ?? (layout.x_key as string | undefined);
  const yKey = (layout.yKey as string | undefined) ?? (layout.y_key as string | undefined);
  if (!xKey || !yKey) {
    return <p className="text-[11px] text-slate-400">Chart requires xKey and yKey.</p>;
  }
  const chartData = rows
    .map((row, index) => {
      const xValue = row[xKey] ?? index;
      const yValue = row[yKey];
      if (yValue == null || Number.isNaN(Number(yValue))) {
        return null;
      }
      return {
        __x: String(xValue),
        __y: Number(yValue),
      };
    })
    .filter((entry): entry is { __x: string; __y: number } => entry !== null);
  if (!chartData.length) {
    return <p className="text-[11px] text-slate-400">No chart data.</p>;
  }
  return (
    <div className="h-40 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis dataKey="__x" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" />
          <Tooltip wrapperStyle={{ backgroundColor: "#0f172a" }} />
          <Line type="monotone" dataKey="__y" stroke="#38bdf8" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const DashboardLayoutSkeleton = ({
  widgets,
  globalReloadTrigger,
}: {
  widgets: Record<string, unknown>[];
  globalReloadTrigger?: number;
}) => {
  if (!widgets.length) {
    return <p className="text-xs text-slate-400">No widgets defined yet.</p>;
  }
  return (
    <div className="grid grid-cols-12 gap-4">
      {widgets.map((widget) => {
        const layout = widget.layout as Record<string, number> | undefined;
        const title = (widget.title as string) ?? (widget.id as string) ?? "Widget";
        const x = Math.max(0, layout?.x ?? 0);
        const y = Math.max(0, layout?.y ?? 0);
        const w = Math.min(Math.max(layout?.w ?? 4, 1), 12);
        const h = Math.max(layout?.h ?? 2, 1);
        const dataSource = widget.data_source as Record<string, unknown> | undefined;
        const endpoint = (dataSource?.endpoint as string | undefined) ?? "";
        const method = ((dataSource?.method as string) ?? "GET").toUpperCase() as "GET" | "POST";
        const params = (dataSource?.params ?? {}) as Record<string, unknown>;
        const render = (widget.render as Record<string, unknown> | undefined) ?? {};
        const { data, error, loading, refetch, lastFetched } = useWidgetData({
          endpoint,
          method,
          params,
          reloadTrigger: globalReloadTrigger,
        });
        let content: React.ReactNode = null;
        const lastUpdatedLabel = lastFetched
          ? `Updated: ${new Date(lastFetched).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}`
          : "Awaiting data";
        if (loading) {
          content = <p className="text-[11px] text-slate-500">Loading...</p>;
        } else if (error) {
          content = <p className="text-[11px] text-rose-400">Error: {error}</p>;
        } else if (data) {
          const renderType = render.type as string | undefined;
          if (renderType === "grid") {
            const rows = getPathValue(data, render.rowsPath as string) as Record<string, unknown>[] | null;
            if (Array.isArray(rows)) {
              content = (
                <GridPreview columns={rows.length ? Object.keys(rows[0]) : []} rows={rows} row_count={rows.length} duration_ms={0} />
              );
            } else {
              content = <p className="text-[11px] text-slate-500">rowsPath did not resolve to an array.</p>;
            }
          } else if (renderType === "json") {
            const payload = getPathValue(data, render.path as string);
            content = (
              <pre className="max-h-40 overflow-auto rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-[11px] text-slate-100">
                {JSON.stringify(payload ?? data, null, 2)}
              </pre>
            );
          } else if (renderType === "chart_line") {
            const rows = getPathValue(data, render.rowsPath as string) as Record<string, unknown>[] | null;
            if (!Array.isArray(rows)) {
              content = <p className="text-[11px] text-slate-500">rowsPath must point to an array.</p>;
            } else {
              content = <ChartWidgetContent rows={rows} layout={render} />;
            }
          } else {
            content = <p className="text-[11px] text-slate-500">Render type not supported yet.</p>;
          }
        } else {
          content = <p className="text-[11px] text-slate-500">Awaiting data...</p>;
        }
        return (
          <div
            key={widget.id as string}
            className="col-span-12 rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-400 shadow-inner shadow-black/40"
            style={{
              gridColumn: `${x + 1} / span ${w}`,
              gridRow: `${y + 1} / span ${h}`,
            }}
          >
            <div className="mb-3 flex items-center justify-between gap-2 text-[10px] uppercase tracking-normal text-slate-500">
              <span>{lastUpdatedLabel}</span>
              <button
                onClick={refetch}
                disabled={loading}
                className="rounded-full border border-slate-700 bg-slate-900/40 px-2 py-1 text-[10px] font-semibold uppercase tracking-normal text-slate-300 transition hover:border-slate-500 hover:bg-slate-900/80 disabled:cursor-not-allowed disabled:opacity-50"
              >
                REFRESH
              </button>
            </div>
            <p className="text-[12px] font-semibold text-white">{title}</p>
            {content}
          </div>
        );
      })}
    </div>
  );
};

const DashboardLayoutMock = ({ widgets }: { widgets: Record<string, unknown>[] }) => {
  if (!widgets.length) {
    return <p className="text-xs text-slate-400">No widgets defined yet.</p>;
  }
  return (
    <div className="grid grid-cols-12 gap-4">
      {widgets.map((widget) => {
        const layout = widget.layout as Record<string, number> | undefined;
        const title = (widget.title as string) ?? (widget.id as string) ?? "Widget";
        const x = Math.max(0, layout?.x ?? 0);
        const y = Math.max(0, layout?.y ?? 0);
        const w = Math.min(Math.max(layout?.w ?? 4, 1), 12);
        const h = Math.max(layout?.h ?? 2, 1);
        const render = (widget.render as Record<string, unknown> | undefined) ?? {};
        const renderType = render.type as string | undefined;
        let content: React.ReactNode = null;
        if (renderType === "grid") {
          const columns = (render.columns as string[]) ?? DEFAULT_MOCK_COLUMNS;
          const rows = buildMockRows(columns, 6);
          content = <GridPreview columns={columns} rows={rows} row_count={rows.length} duration_ms={0} />;
        } else if (renderType === "chart_line") {
          const xKey = (render.xKey as string | undefined) ?? "time";
          const yKey = (render.yKey as string | undefined) ?? "value";
          const rows = buildMockChartRows(xKey, yKey, 10);
          content = <ChartWidgetContent rows={rows} layout={{ xKey, yKey }} />;
        } else if (renderType === "stat") {
          content = (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
              <p className="text-[11px] text-slate-400">{render.label ?? "Metric"}</p>
              <p className="text-2xl font-semibold text-white">42</p>
            </div>
          );
        } else if (renderType === "json") {
          content = (
            <pre className="max-h-40 overflow-auto rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-[11px] text-slate-100">
              {JSON.stringify({ sample: true, widget: title }, null, 2)}
            </pre>
          );
        } else {
          content = <p className="text-[11px] text-slate-400">Layout preview (mock).</p>;
        }
        return (
          <div
            key={title}
            className="rounded-3xl border border-slate-800 bg-slate-900/40 p-4"
            style={{
              gridColumn: `${x + 1} / span ${w}`,
              gridRow: `${y + 1} / span ${h}`,
            }}
          >
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs uppercase text-slate-500">{title}</p>
            </div>
            {content}
          </div>
        );
      })}
    </div>
  );
};

export default function UiCreatorPage() {
  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [uiDefs, setUiDefs] = useState<UiDefinitionSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedUi, setSelectedUi] = useState<UiDefinitionDetail | null>(null);
  const [uiName, setUiName] = useState("");
  const [uiType, setUiType] = useState<UiType>("grid");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [tagsText, setTagsText] = useState("{}");
  const [schemaText, setSchemaText] = useState(JSON.stringify(DEFAULT_SCHEMA, null, 2));
  const [paramsText, setParamsText] = useState(DEFAULT_PARAMS_TEXT);
  const [statusMessage, setStatusMessage] = useState<string | null>("Select or create a UI definition.");
  const [isSaving, setIsSaving] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewMeta, setPreviewMeta] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<PreviewMode>("layout");
  const [globalWidgetReload, setGlobalWidgetReload] = useState(0);
  const [draftApi, setDraftApi] = useState<UiDraft | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("idle");
  const [draftNotes, setDraftNotes] = useState<string | null>(null);
  const [draftErrors, setDraftErrors] = useState<string[]>([]);
  const [draftWarnings, setDraftWarnings] = useState<string[]>([]);
  const [draftTestOk, setDraftTestOk] = useState<boolean | null>(null);
  const [draftDiff, setDraftDiff] = useState<string[] | null>(null);
  const [draftPreviewJson, setDraftPreviewJson] = useState<string | null>(null);
  const [draftPreviewSummary, setDraftPreviewSummary] = useState<string | null>(null);
  const [lastAssistantRaw, setLastAssistantRaw] = useState("");
  const [lastParseStatus, setLastParseStatus] = useState<"idle" | "success" | "fail">("idle");
  const [lastParseError, setLastParseError] = useState<string | null>(null);
  const [saveTarget, setSaveTarget] = useState<"server" | "local" | null>(null);
  const [lastSaveError, setLastSaveError] = useState<string | null>(null);
  const [formDirty, setFormDirty] = useState(false);
  const [formBaselineSnapshot, setFormBaselineSnapshot] = useState<string | null>(null);
  const [appliedDraftSnapshot, setAppliedDraftSnapshot] = useState<string | null>(null);

  const draftStorageId = selectedId ?? "new";
  const finalStorageId = selectedId ?? (uiName.trim() || "new");

  const loadDefinitions = useCallback(
    async (preferredId?: string) => {
      try {
        const response = await fetch(`${apiBaseUrl}/ui-defs`);
        const payload = await response.json();
        const items: UiDefinitionSummary[] = payload.data?.ui_defs ?? [];
        setUiDefs(items);
        setSelectedId((prev) => {
          if (preferredId) {
            return preferredId;
          }
          if (prev && items.some((item) => item.ui_id === prev)) {
            return prev;
          }
          return items[0]?.ui_id ?? null;
        });
      } catch (error) {
        console.error("Unable to load UI definitions", error);
        setUiDefs([]);
        setSelectedId(null);
      }
    },
    [apiBaseUrl]
  );

  const loadDefinitionDetail = useCallback(
    async (uiId: string) => {
      try {
        const response = await fetch(`${apiBaseUrl}/ui-defs/${uiId}`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.message ?? payload.detail ?? "Failed to load definition");
        }
        const detail: UiDefinitionDetail | undefined = payload.data?.ui;
        if (!detail) {
          throw new Error("Definition not returned");
        }
        setSelectedUi(detail);
        setUiName(detail.ui_name);
        setUiType(detail.ui_type);
        setDescription(detail.description ?? "");
        setIsActive(detail.is_active);
        setTagsText(JSON.stringify(detail.tags ?? {}, null, 2));
        setSchemaText(JSON.stringify(detail.schema ?? DEFAULT_SCHEMA, null, 2));
        const defaultParams = (detail.schema as Record<string, unknown>)?.data_source?.default_params ?? {};
        setParamsText(JSON.stringify(defaultParams, null, 2));
        setStatusMessage(`Loaded ${detail.ui_name}`);
        setPreviewResult(null);
        setPreviewError(null);
        setPreviewMeta(null);
        setFormBaselineSnapshot(null);
        setFormDirty(false);
        setAppliedDraftSnapshot(null);
      } catch (error) {
        console.error("Failed to fetch UI detail", error);
        setStatusMessage(error instanceof Error ? error.message : "Unable to load UI");
      }
    },
    [apiBaseUrl]
  );

  const buildUiPayloadFromForm = useCallback(() => {
    let schemaPayload: Record<string, unknown>;
    let tagsPayload: Record<string, unknown>;
    try {
      schemaPayload = JSON.parse(schemaText);
    } catch {
      setStatusMessage("Schema must be valid JSON.");
      return null;
    }
    try {
      tagsPayload = parseJsonObject(tagsText, "tags");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Tags must be JSON object.");
      return null;
    }
    return {
      ui_name: uiName.trim() || "Untitled UI",
      ui_type: uiType,
      schema: schemaPayload,
      description: description.trim() || null,
      tags: tagsPayload,
      is_active: isActive,
    };
  }, [schemaText, tagsText, uiName, uiType, description, isActive]);

  const buildFormSnapshot = useCallback(() => {
    return JSON.stringify({
      ui_name: uiName,
      ui_type: uiType,
      description,
      tags: tagsText,
      schema: schemaText,
      is_active: isActive,
    });
  }, [uiName, uiType, description, tagsText, schemaText, isActive]);

  const saveUiToServer = useCallback(
    async (payload: Record<string, unknown>) => {
      const target = selectedId ? `${apiBaseUrl}/ui-defs/${selectedId}` : `${apiBaseUrl}/ui-defs`;
      const method = selectedId ? "PUT" : "POST";
      try {
        const response = await fetch(target, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          return { ok: false, error: result?.message ?? "Unable to save UI", details: result };
        }
        return { ok: true, data: result?.data?.ui ?? null };
      } catch (error) {
        return { ok: false, error: error instanceof Error ? error.message : "Network error", details: error };
      }
    },
    [apiBaseUrl, selectedId]
  );

  useEffect(() => {
    loadDefinitions();
  }, [loadDefinitions]);

  useEffect(() => {
    const key = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      setDraftApi(null);
      setDraftStatus("idle");
      setDraftNotes(null);
      setDraftTestOk(null);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as UiDraft;
      setDraftApi(parsed);
      setDraftStatus("draft_ready");
      setDraftNotes("미적용 드래프트가 있습니다.");
      setDraftTestOk(null);
    } catch {
      window.localStorage.removeItem(key);
      setDraftApi(null);
      setDraftStatus("idle");
    }
  }, [draftStorageId]);

  useEffect(() => {
    const key = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
    if (!draftApi) {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, JSON.stringify(draftApi));
  }, [draftApi, draftStorageId]);


  useEffect(() => {
    if (selectedId) {
      loadDefinitionDetail(selectedId);
    } else {
      setSelectedUi(null);
    }
  }, [selectedId, loadDefinitionDetail]);

  useEffect(() => {
    const currentSnapshot = buildFormSnapshot();
    if (formBaselineSnapshot === null) {
      setFormBaselineSnapshot(currentSnapshot);
      return;
    }
    setFormDirty(currentSnapshot !== formBaselineSnapshot);
    if (draftApi && appliedDraftSnapshot && currentSnapshot !== appliedDraftSnapshot) {
      setDraftStatus("outdated");
      setDraftNotes("폼이 변경되어 드래프트가 오래되었습니다.");
    }
  }, [buildFormSnapshot, formBaselineSnapshot, draftApi, appliedDraftSnapshot]);

  const handleNew = () => {
    setSelectedId(null);
    setSelectedUi(null);
    setUiName("");
    setUiType("grid");
    setDescription("");
    setIsActive(true);
    setTagsText("{}");
    setSchemaText(JSON.stringify(DEFAULT_SCHEMA, null, 2));
    setParamsText(DEFAULT_PARAMS_TEXT);
    setStatusMessage("Define a new UI.");
    setPreviewResult(null);
    setPreviewError(null);
    setPreviewMeta(null);
    setFormDirty(false);
    setFormBaselineSnapshot(buildFormSnapshot());
    setAppliedDraftSnapshot(null);
  };

  const handleInsertMetricPollingTemplate = () => {
    setSchemaText(JSON.stringify(METRIC_POLLING_DASHBOARD_TEMPLATE, null, 2));
    setStatusMessage("Metric polling dashboard template inserted. Update <METRIC_RULE_ID> before saving.");
  };

  const handleSave = async () => {
    let schemaPayload: Record<string, unknown>;
    let tagsPayload: Record<string, unknown>;
    try {
      schemaPayload = JSON.parse(schemaText);
    } catch (error) {
      setStatusMessage("Schema must be valid JSON.");
      return;
    }
    try {
      tagsPayload = parseJsonObject(tagsText, "tags");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Tags must be JSON object.");
      return;
    }
    const payload = {
      ui_name: uiName.trim() || "Untitled UI",
      ui_type: uiType,
      schema: schemaPayload,
      description: description.trim() || null,
      tags: tagsPayload,
      is_active: isActive,
    };
    setIsSaving(true);
    try {
      const target = selectedId ? `${apiBaseUrl}/ui-defs/${selectedId}` : `${apiBaseUrl}/ui-defs`;
      const response = await fetch(target, {
        method: selectedId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      if (!response.ok) {
        const errorDetail =
          typeof result.message === "string"
            ? result.message
            : JSON.stringify(result.message ?? result.detail ?? result ?? "Unable to save UI");
        throw new Error(errorDetail);
      }
      const savedId = result.data?.ui?.ui_id;
      setStatusMessage(selectedId ? "UI updated" : "UI created");
      await loadDefinitions(savedId);
    } catch (error) {
      console.error("Save failed", error);
      setStatusMessage(error instanceof Error ? error.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  const applyUiDraftToForm = (draft: UiDraft) => {
    setUiName(draft.ui_name);
    setDescription(draft.description ?? "");
    const currentSchema = tryParseJson(schemaText) ?? {};
    const draftLayout = draft.layout ?? {};
    const draftType = (draftLayout as { type?: UiType }).type;
    if (draftType) {
      setUiType(draftType);
    }
    const schemaPayload = {
      data_source:
        (draftLayout as { data_source?: Record<string, unknown> }).data_source ??
        (draft as { data_source?: Record<string, unknown> }).data_source ??
        (currentSchema as { data_source?: Record<string, unknown> }).data_source ??
        DEFAULT_SCHEMA.data_source,
      layout: draftLayout,
      ...(draft.data_bindings ? { data_bindings: draft.data_bindings } : {}),
      ...(draft.actions ? { actions: draft.actions } : {}),
    };
    setSchemaText(JSON.stringify(schemaPayload, null, 2));
    setDraftStatus("applied");
    setDraftNotes("드래프트가 폼에 적용되었습니다. 저장 전입니다.");
    setStatusMessage("Draft applied to editor (not saved).");
    setFormDirty(true);
    setAppliedDraftSnapshot(JSON.stringify(draft));
  };

  useEffect(() => {
    const key = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw) as UiDraft;
      applyUiDraftToForm(parsed);
      setFormDirty(false);
      setFormBaselineSnapshot(buildFormSnapshot());
      setAppliedDraftSnapshot(null);
      setStatusMessage("로컬 저장된 UI 정의를 불러왔습니다.");
    } catch {
      window.localStorage.removeItem(key);
    }
  }, [finalStorageId, buildFormSnapshot]);

  const handlePreviewDraft = () => {
    if (!draftApi) {
      setDraftErrors(["UI 드래프트가 없습니다."]);
      return;
    }
    setDraftStatus("previewing");
    setDraftPreviewJson(JSON.stringify(draftApi, null, 2));
    setDraftPreviewSummary(`${draftApi.ui_name}`);
    setDraftNotes("드래프트를 미리보기로 렌더링합니다.");
  };

  const handleTestDraft = () => {
    if (!draftApi) {
      setDraftErrors(["UI 드래프트가 없습니다."]);
      return;
    }
    setDraftStatus("testing");
    const errors: string[] = [];
    if (!draftApi.ui_name.trim()) {
      errors.push("ui_name은 필수입니다.");
    }
    if (!draftApi.layout || typeof draftApi.layout !== "object") {
      errors.push("layout은 JSON 객체여야 합니다.");
    }
    setDraftErrors(errors);
    setDraftWarnings([]);
    setDraftTestOk(errors.length === 0);
    setDraftNotes(errors.length === 0 ? "테스트 통과" : "테스트 실패");
    setDraftStatus(errors.length === 0 ? "draft_ready" : "error");
  };

  const handleApplyDraft = () => {
    if (!draftApi) {
      setDraftErrors(["UI 드래프트가 없습니다."]);
      return;
    }
    if (draftTestOk !== true) {
      setDraftErrors(["테스트를 통과한 뒤 적용할 수 있습니다."]);
      return;
    }
    applyUiDraftToForm(draftApi);
    setDraftErrors([]);
    setDraftWarnings([]);
  };

  const handleSaveDraft = () => {
    if (!draftApi) {
      setDraftErrors(["UI 드래프트가 없습니다."]);
      return;
    }
    if (draftTestOk !== true) {
      setDraftErrors(["테스트를 통과한 뒤 저장할 수 있습니다."]);
      return;
    }
    const payload = buildUiPayloadFromForm();
    if (!payload) {
      return;
    }
    const storageKey = `${FINAL_STORAGE_PREFIX}${finalStorageId}`;
    setIsSaving(true);
    setSaveTarget(null);
    setLastSaveError(null);
    saveUiWithFallback({
      payload,
      saveUiToServer,
      storage: window.localStorage,
      storageKey,
    })
      .then(async (result) => {
        setSaveTarget(result.target);
        if (result.target === "server") {
          setStatusMessage("Saved to server.");
          setDraftNotes("서버에 저장되었습니다.");
          const savedId = (result.data as UiDefinitionDetail | null)?.ui_id;
          await loadDefinitions(savedId ?? selectedId ?? undefined);
          window.localStorage.removeItem(storageKey);
        } else {
          setStatusMessage("Saved locally (server unavailable).");
          setDraftNotes("서버 저장 실패로 로컬에 저장했습니다.");
        }
        setDraftApi(null);
        setDraftStatus("saved");
        setDraftTestOk(null);
        setFormDirty(false);
        setFormBaselineSnapshot(buildFormSnapshot());
        setAppliedDraftSnapshot(null);
        const draftKey = `${DRAFT_STORAGE_PREFIX}${draftStorageId}`;
        window.localStorage.removeItem(draftKey);
      })
      .catch((error) => {
        const message = error instanceof Error ? error.message : "Save failed";
        setLastSaveError(message);
        setStatusMessage(message);
      })
      .finally(() => {
        setIsSaving(false);
      });
  };

  const handlePreview = async () => {
    const schema = tryParseJson(schemaText);
    if (!schema) {
      setPreviewError("Schema must be valid JSON before previewing.");
      return;
    }
    const dataSource = schema.data_source as Record<string, unknown> | undefined;
    if (!dataSource || typeof dataSource.endpoint !== "string" || typeof dataSource.method !== "string") {
      setPreviewError("schema.data_source.endpoint and method are required.");
      return;
    }
    const endpoint = dataSource.endpoint.startsWith("/") ? dataSource.endpoint : `/${dataSource.endpoint}`;
    const runtimeEndpoint = endpoint.startsWith("/runtime/") ? endpoint : `/runtime${endpoint}`;
    const alternateRuntimeEndpoint = endpoint.startsWith("/api-manager/")
      ? `/runtime${endpoint.replace("/api-manager", "")}`
      : null;
    const method = dataSource.method.toUpperCase();
    const defaultParams = (dataSource.default_params ?? {}) as Record<string, unknown>;
    let parsedParams: Record<string, unknown> = {};
    try {
      parsedParams = parseJsonObject(paramsText, "params");
    } catch (error) {
      setPreviewError(error instanceof Error ? error.message : "Params must be JSON");
      return;
    }
    const runtimeParams = { ...defaultParams, ...parsedParams };
    const baseEndpoint = `${apiBaseUrl}${runtimeEndpoint}`;
    setIsPreviewLoading(true);
    setPreviewError(null);
    try {
      const runExecute = async (apiId: string) => {
        const response = await fetch(`${apiBaseUrl}/api-manager/apis/${apiId}/execute`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Executed-By": "ui-creator",
          },
          body: JSON.stringify({ params: runtimeParams, limit: 200 }),
        });
        const payload = await response.json().catch(() => ({}));
        return { response, payload };
      };

      const runFetch = async (target: string) => {
        if (method === "GET") {
          const url = new URL(target);
          Object.entries(runtimeParams).forEach(([key, value]) => {
            url.searchParams.set(key, value == null ? "" : String(value));
          });
          const response = await fetch(url.toString(), {
            method: "GET",
            headers: { "X-Executed-By": "ui-creator" },
          });
          const payload = await response.json().catch(() => ({}));
          return { response, payload };
        }
        const response = await fetch(target, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Executed-By": "ui-creator",
          },
          body: JSON.stringify({ params: runtimeParams }),
        });
        const payload = await response.json().catch(() => ({}));
        return { response, payload };
      };

      let { response, payload } = await runFetch(baseEndpoint);
      if (!response.ok && response.status === 404 && alternateRuntimeEndpoint) {
        const alternateEndpoint = `${apiBaseUrl}${alternateRuntimeEndpoint}`;
        ({ response, payload } = await runFetch(alternateEndpoint));
      }
      if (!response.ok && response.status === 404) {
        const listResponse = await fetch(`${apiBaseUrl}/api-manager/apis`);
        if (listResponse.ok) {
          const listPayload = await listResponse.json().catch(() => ({}));
          const items = (listPayload.data?.apis ?? []) as Array<{ api_id: string; endpoint: string }>;
          const candidates = new Set([endpoint, runtimeEndpoint, alternateRuntimeEndpoint].filter(Boolean) as string[]);
          const match = items.find((item) => candidates.has(item.endpoint));
          if (match?.api_id) {
            ({ response, payload } = await runExecute(match.api_id));
          }
        }
      }
      if (!response.ok) {
        throw new Error(payload.message ?? payload.detail ?? "Preview failed");
      }
      const result = payload.data?.result;
      if (!result) {
        throw new Error("No preview data returned");
      }
      const columns = Array.isArray(result.columns) ? result.columns : [];
      const rows = Array.isArray(result.rows) ? result.rows : [];
      const computedColumns = columns.length
        ? columns
        : rows.length
        ? Object.keys(rows[0])
        : [];
      setPreviewResult({
        columns: computedColumns,
        rows,
        row_count: typeof result.row_count === "number" ? result.row_count : rows.length,
        duration_ms: typeof result.duration_ms === "number" ? result.duration_ms : 0,
      });
      setPreviewMeta(`Duration ${result.duration_ms ?? 0} ms · Rows ${result.row_count ?? rows.length}`);
    } catch (error) {
      console.error("Preview failed", error);
      setPreviewResult(null);
      setPreviewMeta(null);
      setPreviewError(error instanceof Error ? error.message : "Preview failed");
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleLayoutPreview = () => {
    const schema = tryParseJson(schemaText);
    if (!schema) {
      setPreviewError("Schema must be valid JSON before previewing.");
      return;
    }
    setPreviewMode("layout");
    setPreviewError(null);
    setPreviewMeta("Layout preview (mock data)");
    if (layoutType === "dashboard") {
      setPreviewResult(null);
      return;
    }
    const columns = DEFAULT_MOCK_COLUMNS;
    const rows = buildMockRows(columns, 6);
    setPreviewResult({
      columns,
      rows,
      row_count: rows.length,
      duration_ms: 0,
    });
  };

  const handleRuntimePreview = () => {
    setPreviewMode("runtime");
    handlePreview();
  };

  const parsedSchema = useMemo(() => tryParseJson(schemaText), [schemaText]);
  const runtimeInfo = parsedSchema && parsedSchema.data_source ? `${parsedSchema.data_source.method ?? "GET"} ${parsedSchema.data_source.endpoint ?? ""}` : "Schema missing runtime target";
  const layoutType = (parsedSchema?.layout?.type as UiType) ?? "grid";

  const centerTop = (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Definition</h3>
          <p className="text-[11px] text-slate-400">Save JSON-based UI specs that hit runtime APIs.</p>
          {selectedUi ? (
            <p className="text-[11px] text-slate-500">
              Created by {selectedUi.created_by ?? "ops-builder"} ·{' '}
              {new Date(selectedUi.created_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}
            </p>
          ) : null}
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="rounded-2xl border border-slate-800 bg-emerald-500/80 px-4 py-2 text-[12px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
        >
          {isSaving ? "Saving…" : selectedId ? "Update UI" : "Create UI"}
        </button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs uppercase tracking-normal text-slate-500">
          UI Name
          <input
            value={uiName}
            onChange={(event) => setUiName(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          />
        </label>
        <label className="text-xs uppercase tracking-normal text-slate-500">
          UI Type
          <select
            value={uiType}
            onChange={(event) => setUiType(event.target.value as UiType)}
            className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          >
            {["grid", "chart", "dashboard"].map((type) => (
              <option key={type} value={type}>
                {type.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="text-xs uppercase tracking-normal text-slate-500">
        Description
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="mt-2 h-20 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </label>
      <label className="flex items-center gap-2 text-xs uppercase tracking-normal text-slate-500">
        <input
          type="checkbox"
          checked={isActive}
          onChange={(event) => setIsActive(event.target.checked)}
          className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-sky-400"
        />
        Active
      </label>
      <label className="text-xs uppercase tracking-normal text-slate-500">
        Tags (JSON)
        <textarea
          value={tagsText}
          onChange={(event) => setTagsText(event.target.value)}
          className="mt-2 h-24 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </label>
      <div className="flex items-center justify-between text-[11px] uppercase tracking-normal text-slate-500">
        <span>Schema</span>
        <button
          onClick={handleInsertMetricPollingTemplate}
          className="rounded-2xl border border-slate-800 bg-emerald-600/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-500"
        >
          Insert Metric Polling Template
        </button>
      </div>
      <div className="h-64 rounded-2xl border border-slate-800 bg-slate-950/60">
        <Editor
          height="100%"
          defaultLanguage="json"
          value={schemaText}
          onChange={(value) => setSchemaText(value ?? "")}
          theme="vs-dark"
          options={{ minimap: { enabled: false }, fontSize: 13 }}
        />
      </div>
      <p className="text-[11px] uppercase tracking-normal text-slate-500">{statusMessage ?? "Status"}</p>
    </div>
  );

  const centerBottom = (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-normal text-slate-500">Preview</p>
          <p className="text-[11px] text-slate-400">Runtime: {runtimeInfo}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2 rounded-full border border-slate-800 bg-slate-950/60 p-1 text-[10px] uppercase tracking-normal text-slate-400">
            {(["layout", "runtime"] as PreviewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setPreviewMode(mode)}
                className={`rounded-full px-3 py-1 transition ${
                  previewMode === mode
                    ? "bg-sky-500/80 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
          <button
            onClick={handleLayoutPreview}
            disabled={isPreviewLoading}
            className="rounded-2xl border border-slate-800 bg-sky-500/90 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-sky-400 disabled:bg-slate-700"
          >
            {isPreviewLoading ? "Loading…" : "Layout Preview"}
          </button>
          <button
            onClick={() => {
              setPreviewMode("runtime");
              setGlobalWidgetReload((prev) => prev + 1);
            }}
            disabled={isPreviewLoading}
            className="rounded-2xl border border-slate-800 bg-slate-900 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-slate-600 hover:bg-slate-800 disabled:opacity-40"
          >
            Runtime Preview (All Widgets)
          </button>
          <button
            onClick={handleRuntimePreview}
            disabled={isPreviewLoading}
            className="rounded-2xl border border-slate-800 bg-emerald-500/80 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
          >
            Runtime Preview
          </button>
        </div>
      </div>
      <label className="text-xs uppercase tracking-normal text-slate-500">
        Params override (JSON)
        <textarea
          value={paramsText}
          onChange={(event) => setParamsText(event.target.value)}
          className="mt-2 h-28 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
        />
      </label>
      <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <p className="text-[11px] uppercase tracking-normal text-slate-500">Preview result</p>
        {previewMeta ? <p className="text-xs text-slate-400">{previewMeta}</p> : null}
        {previewError ? <p className="text-xs text-rose-400">{previewError}</p> : null}
        {previewMode === "layout" ? (
          layoutType === "dashboard" ? (
            <DashboardLayoutMock widgets={(parsedSchema?.widgets as Record<string, unknown>[]) ?? []} />
          ) : previewResult ? (
            layoutType === "chart" ? (
              <ChartPreview {...previewResult} layout={parsedSchema?.layout ?? {}} />
            ) : (
              <GridPreview {...previewResult} />
            )
          ) : (
            <p className="text-xs text-slate-400">Run the layout preview to render mock data.</p>
          )
        ) : layoutType === "dashboard" ? (
          <DashboardLayoutSkeleton
            widgets={(parsedSchema?.widgets as Record<string, unknown>[]) ?? []}
            globalReloadTrigger={globalWidgetReload}
          />
        ) : previewResult ? (
          layoutType === "chart" ? (
            <ChartPreview {...previewResult} layout={parsedSchema?.layout ?? {}} />
          ) : (
            <GridPreview {...previewResult} />
          )
        ) : (
          <p className="text-xs text-slate-400">Run the runtime preview to render data.</p>
        )}
      </div>
    </div>
  );

  const leftPane = (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-normal text-slate-500">UI definitions</p>
        <button
          onClick={handleNew}
          className="text-[10px] uppercase tracking-normal text-slate-400 underline"
        >
          New
        </button>
      </div>
      <div className="space-y-2 max-h-[420px] overflow-y-auto">
        {uiDefs.length === 0 ? (
          <p className="text-xs text-slate-500">No UIs yet.</p>
        ) : (
          uiDefs.map((ui) => (
            <button
              key={ui.ui_id}
              onClick={() => setSelectedId(ui.ui_id)}
              className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                selectedId === ui.ui_id
                  ? "border-sky-400 bg-sky-500/10 text-white"
                  : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center justify-between text-[10px] text-slate-400">
                <span>{ui.ui_type.toUpperCase()}</span>
                <span>{new Date(ui.updated_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}</span>
              </div>
              <p className="font-semibold">{ui.ui_name}</p>
              <p className="text-[11px] text-slate-500">{ui.is_active ? "active" : "inactive"}</p>
            </button>
          ))
        )}
      </div>
    </div>
  );

  const COPILOT_INSTRUCTION =
    "Return ONLY one JSON object. type=ui_draft. No markdown. Example: {\"type\":\"ui_draft\",\"draft\":{\"ui_name\":\"...\",\"description\":\"...\",\"layout\":{\"ui_type\":\"dashboard\",\"widgets\":[]},\"data_bindings\":{},\"actions\":[]}}";

  const processAssistantDraft = useCallback(
    (messageText: string) => {
      setLastAssistantRaw(messageText);
      const result = parseUiDraft(messageText);
      setLastParseStatus(result.ok ? "success" : "fail");
      setLastParseError(result.error ?? null);
      if (result.ok && result.draft) {
        setDraftApi(result.draft);
        setDraftStatus("draft_ready");
        setDraftNotes((prev) => prev ?? "UI 드래프트가 준비되었습니다.");
        setDraftErrors([]);
        setDraftWarnings([]);
        setDraftTestOk(null);
        setDraftPreviewJson(JSON.stringify(result.draft, null, 2));
        setDraftPreviewSummary(result.draft.ui_name);
      } else {
        setDraftApi(null);
        setDraftPreviewJson(null);
        setDraftPreviewSummary(null);
        setDraftStatus("error");
        setDraftNotes(result.error ?? "UI 드래프트를 해석할 수 없습니다.");
        setDraftTestOk(false);
      }
    },
    []
  );

  const handleAssistantMessage = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText);
    },
    [processAssistantDraft]
  );

  const handleAssistantMessageComplete = useCallback(
    (messageText: string) => {
      processAssistantDraft(messageText);
    },
    [processAssistantDraft]
  );

  const showDebug = process.env.NODE_ENV !== "production";

  const rightPane = (
    <div className="space-y-4">
      <BuilderCopilotPanel
        builderSlug="ui-creator"
        instructionPrompt={COPILOT_INSTRUCTION}
        onAssistantMessage={handleAssistantMessage}
        onAssistantMessageComplete={handleAssistantMessageComplete}
        inputPlaceholder="UI 드래프트를 설명해 주세요..."
      />
      <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-normal text-slate-500">Draft status</span>
          <span className="text-sm font-semibold text-white">
            {draftStatusLabels[draftStatus] ?? draftStatus}
          </span>
        </div>
        {draftNotes ? <p className="text-sm text-slate-300">{draftNotes}</p> : null}
        {draftStatus === "outdated" ? (
          <div className="rounded-2xl border border-amber-500/60 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-200">
            Draft is outdated. Apply again or regenerate.
          </div>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            onClick={handlePreviewDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-sky-500"
          >
            Preview
          </button>
          <button
            onClick={handleTestDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-emerald-400"
          >
            Test
          </button>
          <button
            onClick={handleApplyDraft}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:border-indigo-400"
            disabled={!draftApi || draftTestOk !== true}
          >
            Apply
          </button>
          <button
            onClick={handleSaveDraft}
            className="rounded-2xl border border-slate-800 bg-emerald-500/70 px-3 py-2 text-[11px] font-semibold uppercase tracking-normal text-white transition hover:bg-emerald-400"
            disabled={!draftApi || draftTestOk !== true}
          >
            Save
          </button>
        </div>
        {!draftApi && (
          <p className="text-xs text-slate-400">
            No draft yet. Ask the copilot to generate one.
            {lastParseError ? ` Parse error: ${lastParseError}` : ""}
          </p>
        )}
        {draftErrors.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-rose-500/60 bg-rose-500/5 px-3 py-2 text-[11px] text-rose-200">
            {draftErrors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}
        {draftWarnings.length > 0 && (
          <div className="space-y-1 rounded-2xl border border-amber-500/60 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200">
            {draftWarnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        )}
        {draftPreviewSummary && draftPreviewJson ? (
          <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-200">
            <p className="text-xs uppercase tracking-normal text-slate-500">Preview</p>
            <p className="text-sm text-white">{draftPreviewSummary}</p>
            <pre className="max-h-48 overflow-auto rounded-xl bg-slate-900/50 p-2 text-[11px] text-slate-300">
              {draftPreviewJson}
            </pre>
          </div>
        ) : null}
        {showDebug ? (
          <details className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[11px] text-slate-300">
            <summary className="cursor-pointer text-xs uppercase tracking-normal text-slate-400">
              Debug
            </summary>
            <div className="mt-2 space-y-1">
              <p className="text-[10px] uppercase tracking-normal text-slate-500">
                Save target: {saveTarget ?? "none"}
              </p>
              {lastSaveError ? <p className="text-[11px] text-rose-300">Save error: {lastSaveError}</p> : null}
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Selected UI</p>
              <p className="text-[11px] text-slate-200">
                {selectedUi ? `${selectedUi.ui_name} (${selectedUi.ui_id})` : "새 UI"}
              </p>
              <p className="text-[10px] uppercase tracking-normal text-slate-500">
                Parse status: {lastParseStatus}
              </p>
              {lastParseError ? <p className="text-[11px] text-rose-300">Error: {lastParseError}</p> : null}
              <p className="text-[10px] uppercase tracking-normal text-slate-500">Last assistant raw</p>
              <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
                {lastAssistantRaw || "없음"}
              </pre>
              {draftApi ? (
                <>
                  <p className="text-[10px] uppercase tracking-normal text-slate-500">Draft JSON</p>
                  <pre className="max-h-32 overflow-auto rounded-xl bg-slate-900/60 p-2 text-[10px] text-slate-200">
                    {JSON.stringify(draftApi, null, 2)}
                  </pre>
                </>
              ) : null}
            </div>
          </details>
        ) : null}
      </div>
    </div>
  );

  return (
    <div className="py-6">
      <h1 className="text-2xl font-semibold text-white">UI Creator</h1>
      <p className="mb-6 text-sm text-slate-400">
        Define runtime-backed dashboards and tables with JSON specs and preview the results immediately.
      </p>
      <BuilderShell leftPane={leftPane} centerTop={centerTop} centerBottom={centerBottom} rightPane={rightPane} />
    </div>
  );
}
