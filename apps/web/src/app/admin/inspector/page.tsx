"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { AuditLog, fetchApi, formatRelativeTime, formatTimestamp } from "../../../lib/adminUtils";
import AuditLogTable, { AuditLogDetailsModal } from "../../../components/admin/AuditLogTable";
import ValidationAlert from "../../../components/admin/ValidationAlert";
import SpanNode from "../../../components/admin/SpanNode";
import TraceDiffView from "../../../components/admin/TraceDiffView";
import { generateNodes, generateEdges, filterToolSpans } from "../../../lib/flowGraphUtils";

const PER_PAGE = 20;

interface FilterState {
  q: string;
  feature: string;
  status: string;
  from: string;
  to: string;
  assetId: string;
}

interface TraceSummaryRow {
  trace_id: string;
  created_at: string;
  feature: string;
  status: string;
  duration_ms: number;
  question_snippet: string;
  applied_asset_versions: string[];
}

interface TraceListResponse {
  traces: TraceSummaryRow[];
  total: number;
  limit: number;
  offset: number;
}

interface AssetSummary {
  asset_id: string | null;
  name: string | null;
  version: number | null;
  source: string | null;
  scope?: string | null;
  engine?: string | null;
  policy_type?: string | null;
  mapping_type?: string | null;
  screen_id?: string | null;
  status?: string | null;
}

interface ExecutionStep {
  step_id: string | null;
  tool_name: string | null;
  status: string;
  duration_ms: number;
  request: Record<string, any> | null;
  response: Record<string, any> | null;
  error: Record<string, any> | null;
  references?: ReferenceEntry[];
}

interface FlowSpan {
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: string;
  status: string;
  ts_start_ms: number;
  ts_end_ms: number;
  duration_ms: number;
  summary: {
    note?: string;
    error_type?: string;
    error_message?: string;
  };
  links: {
    plan_path?: string;
    tool_call_id?: string;
    block_id?: string;
  };
}

interface ReferenceEntry {
  ref_type: string;
  name: string;
  engine?: string | null;
  statement?: string | null;
  params?: Record<string, any> | null;
  row_count?: number | null;
  latency_ms?: number | null;
  source_id?: string | null;
}

interface AnswerBlock {
  type: string;
  title?: string | null;
  payload_summary?: string | null;
  references?: ReferenceEntry[];
  [key: string]: any;
}

interface UIRenderedBlock {
  block_type: string;
  component_name: string;
  ok: boolean;
  error?: string;
}

interface ExecutionTraceDetail {
  trace_id: string;
  parent_trace_id: string | null;
  created_at: string;
  feature: string;
  endpoint: string;
  method: string;
  ops_mode: string;
  question: string;
  status: string;
  duration_ms: number;
  request_payload: Record<string, any> | null;
  applied_assets: {
    prompt?: AssetSummary | null;
    policy?: AssetSummary | null;
    mapping?: AssetSummary | null;
    queries?: AssetSummary[] | null;
    screens?: AssetSummary[] | null;
  } | null;
  asset_versions: string[] | null;
  fallbacks: Record<string, boolean> | null;
  plan_raw: Record<string, any> | null;
  plan_validated: Record<string, any> | null;
  execution_steps: ExecutionStep[] | null;
  references: ReferenceEntry[] | null;
  answer: { envelope_meta: Record<string, any> | null; blocks: AnswerBlock[] } | null;
  ui_render: { rendered_blocks: UIRenderedBlock[]; warnings: string[] } | null;
  audit_links: Record<string, any> | null;
  flow_spans: FlowSpan[] | null;
}

interface TraceDetailResponse {
  trace: ExecutionTraceDetail;
  audit_logs: AuditLog[];
}

const initialFilters: FilterState = {
  q: "",
  feature: "",
  status: "",
  from: "",
  to: "",
  assetId: "",
};

function InspectorContent() {
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [lookupTraceId, setLookupTraceId] = useState("");
  const [traces, setTraces] = useState<TraceSummaryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [traceDetail, setTraceDetail] = useState<ExecutionTraceDetail | null>(null);
  const [traceAuditLogs, setTraceAuditLogs] = useState<AuditLog[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [planView, setPlanView] = useState<"raw" | "validated">("validated");
  const [traceCopyStatus, setTraceCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [linkCopyStatus, setLinkCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [selectedSpan, setSelectedSpan] = useState<FlowSpan | null>(null);
  const [flowViewMode, setFlowViewMode] = useState<"timeline" | "graph">("timeline");
  const [hideToolSpans, setHideToolSpans] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [compareTraceId, setCompareTraceId] = useState("");
  const [compareTraceDetail, setCompareTraceDetail] = useState<ExecutionTraceDetail | null>(null);
  const [compareFetching, setCompareFetching] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [showDiffView, setShowDiffView] = useState(false);
  const [singleRcaLoading, setSingleRcaLoading] = useState(false);
  const [singleRcaError, setSingleRcaError] = useState<string | null>(null);
  const reactFlowInstance = useReactFlow();
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleSearch = useCallback(
    async (nextOffset = 0) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set("limit", String(PER_PAGE));
        params.set("offset", String(nextOffset));
        if (filters.q) params.set("q", filters.q);
        if (filters.feature) params.set("feature", filters.feature);
        if (filters.status) params.set("status", filters.status);
        if (filters.from) params.set("from", filters.from);
        if (filters.to) params.set("to", filters.to);
        if (filters.assetId) params.set("asset_id", filters.assetId);
        const response = await fetchApi<TraceListResponse>(`/inspector/traces?${params.toString()}`);
        setTraces((prev) =>
          nextOffset === 0 ? response.data.traces : [...prev, ...response.data.traces]
        );
        setTotal(response.data.total);
        setOffset(nextOffset + response.data.traces.length);
      } catch (err: any) {
        setError(err.message || "업무 추적 데이터를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  const fetchTraceDetail = useCallback(async (traceId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const response = await fetchApi<TraceDetailResponse>(`/inspector/traces/${encodeURIComponent(traceId)}`);
      if (!response.data.trace) {
        setDetailError("Trace not found or invalid response");
        setTraceDetail(null);
        setTraceAuditLogs([]);
        return;
      }
      setTraceDetail(response.data.trace);
      setTraceAuditLogs(response.data.audit_logs || []);
      setSelectedTraceId(response.data.trace.trace_id);
    } catch (err: any) {
      setDetailError(err.message || "실행 증거를 불러오지 못했습니다.");
      setTraceDetail(null);
      setTraceAuditLogs([]);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    handleSearch(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const traceIdParam = searchParams.get("trace_id");
    if (traceIdParam) {
      fetchTraceDetail(traceIdParam);
    }
  }, [searchParams, fetchTraceDetail]);

  useEffect(() => {
    setTraceCopyStatus("idle");
    setLinkCopyStatus("idle");
  }, [traceDetail?.trace_id]);

  // Generate graph nodes and edges when traceDetail or hideToolSpans changes
  useEffect(() => {
    if (traceDetail?.flow_spans && traceDetail.flow_spans.length > 0) {
      const spansToUse = hideToolSpans ? filterToolSpans(traceDetail.flow_spans) : traceDetail.flow_spans;
      const generatedNodes = generateNodes(spansToUse);
      const generatedEdges = generateEdges(spansToUse);

      setNodes(
        generatedNodes.map((node) => ({
          ...node,
          selected: node.id === selectedNodeId,
        }))
      );
      setEdges(generatedEdges);
    }
  }, [traceDetail?.flow_spans, hideToolSpans, selectedNodeId, setNodes, setEdges]);

  const handleLookup = () => {
    if (!lookupTraceId.trim()) {
      setDetailError("Trace ID를 입력하세요.");
      return;
    }
    fetchTraceDetail(lookupTraceId.trim());
  };

  const handleCopyTraceId = useCallback(() => {
    if (!traceDetail) {
      return;
    }
    const copyValue = traceDetail.trace_id;
    if (!navigator?.clipboard) {
      window.prompt("Copy trace_id", copyValue);
      return;
    }
    navigator.clipboard
      .writeText(copyValue)
      .then(() => setTraceCopyStatus("copied"))
      .catch(() => setTraceCopyStatus("failed"));
  }, [traceDetail]);

  const handleCopyLink = useCallback(() => {
    if (!traceDetail) {
      return;
    }
    const link = `${window.location.origin}/admin/inspector?trace_id=${encodeURIComponent(traceDetail.trace_id)}`;
    if (!navigator?.clipboard) {
      window.prompt("Copy trace link", link);
      return;
    }
    navigator.clipboard
      .writeText(link)
      .then(() => setLinkCopyStatus("copied"))
      .catch(() => setLinkCopyStatus("failed"));
  }, [traceDetail]);

  const handleResetFilters = () => {
    setFilters(initialFilters);
  };

  const handleCompareClick = () => {
    setShowCompareModal(true);
    setCompareTraceId("");
    setCompareError(null);
  };

  const handleFetchCompareTrace = async () => {
    if (!compareTraceId.trim()) {
      setCompareError("Trace ID를 입력하세요.");
      return;
    }

    setCompareFetching(true);
    setCompareError(null);
    try {
      const response = await fetchApi<TraceDetailResponse>(
        `/inspector/traces/${encodeURIComponent(compareTraceId.trim())}`
      );
      setCompareTraceDetail(response.data.trace);
      setShowDiffView(true);
      setShowCompareModal(false);
    } catch (err: any) {
      setCompareError(err.message || "비교 trace를 불러오는데 실패했습니다.");
    } finally {
      setCompareFetching(false);
    }
  };

  const handleRowClick = (traceId: string) => {
    fetchTraceDetail(traceId);
  };

  const handleRunSingleRca = useCallback(async () => {
    if (!traceDetail) return;
    setSingleRcaLoading(true);
    setSingleRcaError(null);
    try {
      const response = await fetchApi<{ trace_id: string; status: string }>("/ops/rca", {
        method: "POST",
        body: JSON.stringify({
          mode: "single",
          trace_id: traceDetail.trace_id,
          options: { max_hypotheses: 5, include_snippets: true },
        }),
      });

      if (!response.data || !response.data.trace_id) {
        setSingleRcaError("Invalid RCA response: missing trace_id");
        return;
      }

      setShowDiffView(false);
      setCompareTraceDetail(null);
      setTraceDetail(null);
      setTraceAuditLogs([]);
      setSelectedTraceId(null);
      setDetailError(null);
      router.push(`/admin/inspector?trace_id=${encodeURIComponent(response.data.trace_id)}`);
    } catch (err: any) {
      setSingleRcaError(err.message || "Failed to run RCA analysis.");
    } finally {
      setSingleRcaLoading(false);
    }
  }, [traceDetail, router]);

  const renderAppliedAsset = (asset: AssetSummary | null | undefined) => {
    if (!asset) {
      return <span className="text-xs text-slate-500">미적용</span>;
    }
    return (
      <div className="text-xs text-slate-200 space-y-1">
        {asset.name && <p>{asset.name}</p>}
        <p className="font-mono text-[11px]">
          {asset.asset_id || `${asset.name || "asset"}@${asset.source || "fallback"}`}
          {asset.version ? ` · v${asset.version}` : ""}
        </p>
        {asset.source && <p className="uppercase text-[10px] tracking-[0.3em] text-slate-500">{asset.source}</p>}
      </div>
    );
  };

  const formatAppliedAssetSummary = (trace: TraceSummaryRow) => {
    if (!trace.applied_asset_versions.length) {
      return "Assets: none";
    }
    const preview = trace.applied_asset_versions.slice(0, 3).join(" / ");
    const extra = trace.applied_asset_versions.length - 3;
    return extra > 0 ? `${preview} / +${extra} more` : preview;
  };

  const getStatusBadgeClass = (status: string) =>
    status === "success" ? "bg-emerald-900/60 text-emerald-200" : "bg-rose-900/60 text-rose-200";

  const formatDuration = (ms: number) => `${ms}ms`;

  const highlightFallbacks = (fallbacks: Record<string, boolean> | null | undefined) => {
    if (!fallbacks) return null;
    return (
      <div className="flex gap-2 flex-wrap text-[11px]">
        {Object.entries(fallbacks).map(([key, value]) => (
          <span
            key={key}
            className={`px-2 py-1 rounded-full font-semibold uppercase tracking-[0.3em] text-[10px] ${value ? "bg-yellow-900/60 text-yellow-200" : "bg-green-900/30 text-emerald-300"}`}
          >
            {key}: {value ? "fallback" : "asset"}
          </span>
        ))}
      </div>
    );
  };

  const renderJsonDetails = (label: string, payload: unknown) => {
    if (!payload) {
      return null;
    }
    return (
      <details className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
        <summary className="text-xs font-semibold text-slate-200 cursor-pointer">{label}</summary>
        <pre className="mt-2 text-[11px] text-slate-200 overflow-x-auto max-h-48">{JSON.stringify(payload, null, 2)}</pre>
      </details>
    );
  };

  const summarizeStepPayload = (payload: Record<string, any> | null) => {
    if (!payload) {
      return "";
    }
    try {
      const text = JSON.stringify(payload, null, 2);
      return text.length > 120 ? `${text.slice(0, 120)}…` : text;
    } catch {
      return String(payload);
    }
  };

  const summarizeBlockPayload = (block: AnswerBlock) => {
    const candidate = block.payload_summary ?? block.title ?? block.type;
    if (typeof candidate === "string") {
      return candidate.length > 120 ? `${candidate.slice(0, 120)}…` : candidate;
    }
    try {
      const text = JSON.stringify(candidate);
      return text.length > 120 ? `${text.slice(0, 120)}…` : text;
    } catch {
      return String(candidate);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 text-sm text-slate-200 space-y-2 shadow-inner">
        <p>
          Inspector는 운영자가 실행 기록을 trace_id 기준으로 분석하고 적용된 자산/쿼리/렌더를 확인하는 전용 도구입니다.
        </p>
        <p className="text-xs text-slate-400">
          Assets/Settings 변경 후에는 반드시 Inspector에서 trace_id로 검증하고, 다시 실행한 trace를 사용해 상태를 확인하세요.
        </p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-2xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Trace Lookup</p>
              <h3 className="text-lg font-semibold text-white">Trace ID로 바로 열람</h3>
            </div>
            <span className="text-[11px] text-slate-500">Exact</span>
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              value={lookupTraceId}
              onChange={(event) => setLookupTraceId(event.target.value)}
              placeholder="Trace ID를 입력하세요"
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm font-mono focus:border-sky-500/50 focus:outline-none"
            />
            <button
              onClick={handleLookup}
              className="px-6 py-3 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs tracking-[0.2em] font-bold uppercase"
            >
              {detailLoading ? "로딩..." : "조회"}
            </button>
          </div>
          <p className="text-[11px] text-slate-500">
            Trace ID가 있으면 단일 실행 상세를 즉시 확인합니다.
          </p>
        </div>

        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-2xl">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Trace Search</p>
            <h3 className="text-lg font-semibold text-white">운용/분석 필터</h3>
          </div>
          <div className="space-y-3">
            <input
              type="text"
              value={filters.q}
              onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
              placeholder="질의 또는 키워드(q)"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-sky-500/50 focus:outline-none"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="text"
                value={filters.feature}
                onChange={(event) => setFilters((prev) => ({ ...prev, feature: event.target.value }))}
                placeholder="Feature (예: ci)"
                className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-sky-500/50 focus:outline-none"
              />
              <input
                type="text"
                value={filters.assetId}
                onChange={(event) => setFilters((prev) => ({ ...prev, assetId: event.target.value }))}
                placeholder="Asset ID 기준"
                className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:border-sky-500/50 focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={filters.status}
                onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-3 text-sm focus:border-sky-500/50 focus:outline-none"
              >
                <option value="">응답 상태 (전체)</option>
                <option value="success">success</option>
                <option value="error">error</option>
              </select>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={filters.from}
                  onChange={(event) => setFilters((prev) => ({ ...prev, from: event.target.value }))}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-3 text-sm focus:border-sky-500/50 focus:outline-none"
                />
                <input
                  type="date"
                  value={filters.to}
                  onChange={(event) => setFilters((prev) => ({ ...prev, to: event.target.value }))}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-3 text-sm focus:border-sky-500/50 focus:outline-none"
                />
              </div>
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 border border-slate-700 rounded-xl text-[10px] uppercase tracking-[0.2em] text-slate-400 hover:border-slate-500"
            >
              Reset
            </button>
            <button
              onClick={() => handleSearch(0)}
              disabled={loading}
              className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-[10px] uppercase tracking-[0.2em] font-bold"
            >
              {loading ? "Searching..." : "Trace Search"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <ValidationAlert errors={[error]} onClose={() => setError(null)} />
      )}

      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Trace Results</p>
            <h3 className="text-white text-sm font-semibold">
              {traces.length} 건 중 {total}개
            </h3>
          </div>
          <p className="text-[11px] text-slate-400">
            Showing {offset === 0 ? traces.length : offset} / {total}
          </p>
        </div>
        {loading && traces.length === 0 ? (
          <div className="py-12 flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full border-2 border-slate-800 border-t-emerald-400 animate-spin" />
            <p className="text-[11px] text-slate-500 uppercase tracking-[0.25em]">Loading traces...</p>
          </div>
        ) : traces.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            필터를 조정하여 실행 기록을 검색하세요.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-[0.3em] text-slate-400 border-b border-slate-800">
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Feature</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Question</th>
                  <th className="px-4 py-3">Assets</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((trace) => (
                  <tr
                    key={trace.trace_id}
                    onClick={() => handleRowClick(trace.trace_id)}
                    className={`border-b border-slate-800 hover:bg-slate-900/60 transition-colors cursor-pointer ${selectedTraceId === trace.trace_id ? "bg-slate-900/70" : ""}`}
                  >
                    <td className="px-4 py-3">
                      <p className="font-mono text-xs text-slate-200">{trace.trace_id.slice(0, 8)}</p>
                      <p className="text-[11px] text-slate-400">{formatRelativeTime(trace.created_at)}</p>
                      <p className="text-[10px] text-slate-500">{formatTimestamp(trace.created_at)}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-200">{trace.feature}</td>
                    <td className="px-4 py-3 text-slate-100">
                      <span className={`px-2 py-1 rounded-full text-[11px] ${getStatusBadgeClass(trace.status)}`}>
                        {trace.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-200">{formatDuration(trace.duration_ms)}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{trace.question_snippet}</td>
                    <td className="px-4 py-3 text-xs text-slate-300">{formatAppliedAssetSummary(trace)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {offset < total && traces.length > 0 && (
          <div className="p-4 flex justify-center border-t border-slate-800">
            <button
              onClick={() => handleSearch(offset)}
              disabled={loading}
              className="px-6 py-2 rounded-full bg-slate-800 text-xs uppercase tracking-[0.3em] hover:bg-slate-700 disabled:opacity-50"
            >
              {loading ? "불러오는 중..." : "Load More"}
            </button>
          </div>
        )}
      </div>

      {traceDetail && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/70 p-4">
          <div className="bg-slate-950 border border-slate-800 max-w-6xl w-full max-h-[90vh] rounded-3xl overflow-hidden shadow-2xl flex flex-col">
            <header className="px-6 py-4 border-b border-slate-800 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="space-y-3">
                <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Trace Overview</p>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-lg font-semibold text-white tracking-tight">{traceDetail.question}</h2>
                  <span
                    className={`px-3 py-1 rounded-full text-xs uppercase tracking-[0.3em] ${getStatusBadgeClass(
                      traceDetail.status
                    )}`}
                  >
                    {traceDetail.status}
                  </span>
                </div>
                <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                  <span>Feature: {traceDetail.feature}</span>
                  <span>Mode: {traceDetail.ops_mode}</span>
                  <span>Endpoint: {traceDetail.endpoint}</span>
                  <span>Method: {traceDetail.method}</span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                  <span className="font-mono">{traceDetail.trace_id}</span>
                  <button
                    onClick={handleCopyTraceId}
                    className="px-3 py-1 rounded-lg border border-slate-700 text-[10px] uppercase tracking-[0.2em] transition hover:border-slate-500"
                  >
                    {traceCopyStatus === "copied"
                      ? "복사됨"
                      : traceCopyStatus === "failed"
                        ? "재시도"
                        : "Copy trace_id"}
                  </button>
                  <button
                    onClick={handleCopyLink}
                    className="px-3 py-1 rounded-lg border border-slate-700 text-[10px] uppercase tracking-[0.2em] transition hover:border-slate-500"
                  >
                    {linkCopyStatus === "copied"
                      ? "Link copied"
                      : linkCopyStatus === "failed"
                        ? "Retry link"
                        : "Copy link"}
                  </button>
                  {traceDetail.parent_trace_id && (
                    <button
                      onClick={() => fetchTraceDetail(traceDetail.parent_trace_id!)}
                      className="px-3 py-1 rounded-lg border border-slate-700 text-[10px] uppercase tracking-[0.2em] transition hover:border-slate-500"
                    >
                      View parent
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-4 text-[11px] text-slate-400">
                  <span>Duration: {formatDuration(traceDetail.duration_ms)}</span>
                  <span>{formatTimestamp(traceDetail.created_at)}</span>
                  <span>{formatRelativeTime(traceDetail.created_at)}</span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={handleRunSingleRca}
                  disabled={singleRcaLoading}
                  className="px-3 py-2 rounded-xl border border-fuchsia-600 bg-fuchsia-900/20 text-xs uppercase tracking-[0.2em] text-fuchsia-200 hover:bg-fuchsia-900/40 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {singleRcaLoading ? "Analyzing..." : "Run RCA"}
                </button>
                <button
                  onClick={handleCompareClick}
                  className="px-3 py-2 rounded-xl border border-emerald-700 bg-emerald-900/20 text-xs uppercase tracking-[0.2em] text-emerald-200 hover:bg-emerald-900/40 transition"
                >
                  Compare
                </button>
                <button
                  onClick={() => {
                    setTraceDetail(null);
                    setTraceAuditLogs([]);
                    setSelectedTraceId(null);
                    setDetailError(null);
                    setShowDiffView(false);
                  }}
                  className="px-3 py-2 rounded-xl border border-slate-700 text-xs uppercase tracking-[0.2em] hover:border-slate-500"
                >
                  Close
                </button>
              </div>
              {singleRcaError && (
                <div className="mt-2">
                  <ValidationAlert
                    errors={[singleRcaError]}
                    onClose={() => setSingleRcaError(null)}
                  />
                </div>
              )}
            </header>
            <div className="p-6 overflow-y-auto custom-scrollbar space-y-6">
              {detailError && (
                <ValidationAlert errors={[detailError]} onClose={() => setDetailError(null)} />
              )}
              {detailLoading ? (
                <div className="py-8 flex flex-col items-center gap-3">
                  <div className="w-10 h-10 rounded-full border-2 border-slate-800 border-t-emerald-400 animate-spin" />
                  <p className="text-xs text-slate-400 uppercase tracking-[0.3em]">Loading detail...</p>
                </div>
              ) : (
                <>
                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Overview</p>
                      <span className="text-[10px] text-slate-400">Request & Context</span>
                    </div>
                    <p className="text-sm text-white">{traceDetail.question}</p>
                    <div className="flex flex-wrap gap-2 text-[11px] text-slate-400">
                      <span className="px-2 py-1 rounded-full bg-slate-800">Mode: {traceDetail.ops_mode}</span>
                      <span className="px-2 py-1 rounded-full bg-slate-800">Endpoint: {traceDetail.endpoint}</span>
                      <span className="px-2 py-1 rounded-full bg-slate-800">Method: {traceDetail.method}</span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-[11px] text-slate-400">
                      <span>Duration: {formatDuration(traceDetail.duration_ms)}</span>
                      <span>{formatTimestamp(traceDetail.created_at)}</span>
                      <span>{formatRelativeTime(traceDetail.created_at)}</span>
                    </div>
                    {renderJsonDetails("Request payload", traceDetail.request_payload)}
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Applied Assets</p>
                      {highlightFallbacks(traceDetail.fallbacks)}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-slate-950/50 rounded-xl border border-slate-800 px-4 py-3">
                        <p className="text-[9px] uppercase tracking-[0.3em] text-slate-500">Prompt</p>
                        {renderAppliedAsset(traceDetail.applied_assets?.prompt ?? null)}
                      </div>
                      <div className="bg-slate-950/50 rounded-xl border border-slate-800 px-4 py-3">
                        <p className="text-[9px] uppercase tracking-[0.3em] text-slate-500">Policy</p>
                        {renderAppliedAsset(traceDetail.applied_assets?.policy ?? null)}
                      </div>
                      <div className="bg-slate-950/50 rounded-xl border border-slate-800 px-4 py-3">
                        <p className="text-[9px] uppercase tracking-[0.3em] text-slate-500">Mapping</p>
                        {renderAppliedAsset(traceDetail.applied_assets?.mapping ?? null)}
                      </div>
                      <div className="md:col-span-2 space-y-2">
                        <p className="text-[9px] uppercase tracking-[0.3em] text-slate-500">Queries</p>
                        {traceDetail.applied_assets?.queries?.length ? (
                          <ul className="space-y-2">
                            {traceDetail.applied_assets.queries.map((query) => (
                              <li key={query.asset_id || `${query.name}-${query.source}`} className="bg-slate-950/50 border border-slate-800 rounded-xl px-3 py-2 text-[11px] text-slate-300">
                                {query.name || "query"} · {query.source} · {query.asset_id ?? "seed"}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-slate-500">Query asset 없음</p>
                        )}
                      </div>
                      <div className="md:col-span-2 space-y-2">
                        <p className="text-[9px] uppercase tracking-[0.3em] text-slate-500">Screens</p>
                        {traceDetail.applied_assets?.screens?.length ? (
                          <ul className="space-y-2">
                            {traceDetail.applied_assets.screens.map((screen) => (
                              <li key={screen.asset_id || `${screen.screen_id}-${screen.status}`} className="bg-slate-950/50 border border-slate-800 rounded-xl px-3 py-2 text-[11px] text-slate-300">
                                {screen.screen_id || "screen"} · {screen.status ?? "unknown"} · {screen.version ?? "?"}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-slate-500">Screen asset 없음</p>
                        )}
                      </div>
                    </div>
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Plan</p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPlanView("raw")}
                          className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-[0.3em] ${planView === "raw"
                            ? "bg-slate-700 text-white"
                            : "bg-slate-950 text-slate-400 border border-slate-800"}`}
                        >
                          Raw
                        </button>
                        <button
                          onClick={() => setPlanView("validated")}
                          className={`px-3 py-1 rounded-full text-[10px] uppercase tracking-[0.3em] ${planView === "validated"
                            ? "bg-slate-700 text-white"
                            : "bg-slate-950 text-slate-400 border border-slate-800"}`}
                        >
                          Validated
                        </button>
                      </div>
                    </div>
                    {renderJsonDetails(
                      planView === "raw" ? "Raw plan snapshot" : "Validated plan snapshot",
                      planView === "raw" ? traceDetail.plan_raw : traceDetail.plan_validated
                    )}
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Plan steps</p>
                      <div className="mt-2 overflow-x-auto">
                        {traceDetail.execution_steps && traceDetail.execution_steps.length ? (
                          <table className="min-w-full text-xs text-slate-300">
                            <thead>
                              <tr className="text-left text-[10px] uppercase tracking-[0.2em] text-slate-500 border-b border-slate-800">
                                <th className="px-2 py-2">Step</th>
                                <th className="px-2 py-2">Tool</th>
                                <th className="px-2 py-2">Status</th>
                                <th className="px-2 py-2">Duration</th>
                                <th className="px-2 py-2">Summary</th>
                              </tr>
                            </thead>
                            <tbody>
                              {traceDetail.execution_steps.map((step) => (
                                <tr
                                  key={`${step.step_id}-${step.tool_name}-${step.duration_ms}`}
                                  className="border-b border-slate-800"
                                >
                                  <td className="px-2 py-2">{step.step_id || "step"}</td>
                                  <td className="px-2 py-2">{step.tool_name || "tool"}</td>
                                  <td className="px-2 py-2">
                                    <span className={`px-2 py-1 rounded-full ${step.status === "success"
                                      ? "bg-emerald-900/40 text-emerald-200"
                                      : "bg-rose-900/40 text-rose-200"}`}>
                                      {step.status}
                                    </span>
                                  </td>
                                  <td className="px-2 py-2">{formatDuration(step.duration_ms)}</td>
                                  <td className="px-2 py-2">
                                    {summarizeStepPayload(step.request || step.response)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p className="text-xs text-slate-500">Plan step 정보가 없습니다.</p>
                        )}
                      </div>
                    </div>
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Execution</p>
                      <span className="text-[10px] text-slate-400">{traceDetail.execution_steps?.length ?? 0} steps</span>
                    </div>
                    {traceDetail.execution_steps && traceDetail.execution_steps.length ? (
                      <div className="space-y-3">
                        {traceDetail.execution_steps.map((step, index) => (
                          <article
                            key={`${step.step_id ?? index}-${step.tool_name ?? "tool"}`}
                            className="bg-slate-950/50 border border-slate-800 rounded-xl p-4 space-y-3"
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm text-white font-semibold">{step.step_id || `step-${index + 1}`}</p>
                                <p className="text-[11px] text-slate-400">{step.tool_name || "tool"}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded-full text-[10px] uppercase tracking-[0.2em] ${step.status === "success"
                                  ? "bg-emerald-900/40 text-emerald-200"
                                  : "bg-rose-900/40 text-rose-200"}`}>
                                  {step.status}
                                </span>
                                <span className="text-[11px] text-slate-400">{formatDuration(step.duration_ms)}</span>
                              </div>
                            </div>
                            {renderJsonDetails("Request summary", step.request)}
                            {renderJsonDetails("Response summary", step.response)}
                            {step.error && (
                              <details className="bg-rose-950/40 border border-rose-800 rounded-xl p-2 text-[11px] text-rose-200">
                                <summary className="cursor-pointer uppercase tracking-[0.3em] text-[10px]">Error details</summary>
                                <p className="mt-2 text-[11px] text-rose-100">
                                  {step.error?.message ?? "Unknown error"}
                                </p>
                                {step.error?.stack && (
                                  <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-rose-100">
                                    {step.error.stack}
                                  </pre>
                                )}
                              </details>
                            )}
                            {step.references && step.references.length ? (
                              <p className="text-[11px] text-slate-400">
                                References: {step.references.map((ref) => ref.name).join(", ")}
                              </p>
                            ) : null}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">Tool execution trace가 없습니다.</p>
                    )}
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">References</p>
                      <span className="text-[10px] text-slate-400">{traceDetail.references?.length ?? 0} items</span>
                    </div>
                    {traceDetail.references && traceDetail.references.length ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-xs text-slate-300">
                          <thead>
                            <tr className="text-left uppercase tracking-[0.3em] text-slate-500 border-b border-slate-800 text-[10px]">
                              <th className="px-2 py-2">Type</th>
                              <th className="px-2 py-2">Name</th>
                              <th className="px-2 py-2">Engine</th>
                              <th className="px-2 py-2">Rows</th>
                              <th className="px-2 py-2">Latency</th>
                              <th className="px-2 py-2">Detail</th>
                            </tr>
                          </thead>
                          <tbody>
                            {traceDetail.references.map((ref, index) => (
                              <tr key={`${ref.name}-${index}`} className="border-b border-slate-800">
                                <td className="px-2 py-2 text-[11px] text-slate-400">{ref.ref_type}</td>
                                <td className="px-2 py-2 text-slate-100">{ref.name}</td>
                                <td className="px-2 py-2 text-slate-400">{ref.engine || "unknown"}</td>
                                <td className="px-2 py-2 text-slate-400">{ref.row_count ?? "-"}</td>
                                <td className="px-2 py-2 text-slate-400">{ref.latency_ms ?? "-"} ms</td>
                                <td className="px-2 py-2 space-y-1">
                                  {ref.statement && (
                                    <details className="bg-slate-950/60 border border-slate-800 rounded-xl p-2">
                                      <summary className="text-[10px] uppercase tracking-[0.2em] text-slate-400 cursor-pointer">
                                        Statement
                                      </summary>
                                      <pre className="mt-2 text-[11px] text-slate-200 overflow-x-auto">{ref.statement}</pre>
                                    </details>
                                  )}
                                  {ref.params && (
                                    <details className="bg-slate-950/60 border border-slate-800 rounded-xl p-2">
                                      <summary className="text-[10px] uppercase tracking-[0.2em] text-slate-400 cursor-pointer">
                                        Params
                                      </summary>
                                      <pre className="mt-2 text-[11px] text-slate-200 overflow-x-auto">
                                        {JSON.stringify(ref.params, null, 2)}
                                      </pre>
                                    </details>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">근거 레코드가 없습니다.</p>
                    )}
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Answer Blocks</p>
                      <span className="text-[10px] text-slate-400">{traceDetail.answer?.blocks.length ?? 0} blocks</span>
                    </div>
                    {traceDetail.answer?.blocks?.length ? (
                      <div className="grid gap-3 md:grid-cols-2">
                        {traceDetail.answer.blocks.map((block, index) => (
                          <article
                            key={`${block.type}-${index}`}
                            className="bg-slate-950/40 border border-slate-800 rounded-xl p-4 space-y-2"
                          >
                            <div className="flex items-center justify-between text-[11px] text-slate-400 uppercase tracking-[0.3em]">
                              <span>{block.type}</span>
                              <span>{block.references?.length ? `${block.references.length} references` : "No refs"}</span>
                            </div>
                            <div>
                              {block.title ? (
                                <p className="text-sm text-white font-semibold">{block.title}</p>
                              ) : (
                                <p className="text-sm text-slate-100">Untitled block</p>
                              )}
                              <p className="text-[11px] text-slate-400 mt-1">
                                {summarizeBlockPayload(block)}
                              </p>
                            </div>
                            <details className="bg-slate-950/60 border border-slate-800 rounded-xl p-2">
                              <summary className="text-[10px] uppercase tracking-[0.2em] text-slate-400 cursor-pointer">
                                View payload
                              </summary>
                              <pre className="mt-2 text-[10px] text-slate-200 overflow-x-auto max-h-48">
                                {JSON.stringify(block, null, 2)}
                              </pre>
                            </details>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">Blocks가 없습니다.</p>
                    )}
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">UI Render Trace</p>
                    {traceDetail.ui_render ? (
                      <div className="space-y-3">
                        <div className="text-xs text-slate-400 uppercase tracking-[0.3em]">Rendered Blocks</div>
                        <div className="grid gap-2">
                          {traceDetail.ui_render.rendered_blocks.map((block, index) => (
                            <div key={`${block.block_type}-${index}`} className="bg-slate-950/50 border border-slate-800 rounded-xl px-3 py-2 text-[11px]">
                              <div className="flex items-center justify-between">
                                <span>{block.block_type}</span>
                                <span>{block.ok ? "ok" : "error"}</span>
                              </div>
                              <p className="text-[11px] text-slate-400">{block.component_name}</p>
                              {block.error && <p className="text-rose-300 text-[11px] mt-1">{block.error}</p>}
                            </div>
                          ))}
                        </div>
                        {traceDetail.ui_render.warnings.length > 0 && (
                          <ul className="list-disc list-inside text-[11px] text-slate-400">
                            {traceDetail.ui_render.warnings.map((warning, idx) => (
                              <li key={idx}>{warning}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">UI 렌더 이벤트가 아직 없습니다.</p>
                    )}
                  </section>

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between gap-4 flex-wrap">
                      <div className="flex items-center gap-2">
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Flow</p>
                        {traceDetail.flow_spans && traceDetail.flow_spans.length > 0 && (
                          <span className="text-[10px] text-slate-400">{traceDetail.flow_spans.length} spans</span>
                        )}
                      </div>
                      {traceDetail.flow_spans && traceDetail.flow_spans.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <div className="flex gap-1 bg-slate-950 rounded-lg p-1">
                            <button
                              onClick={() => {
                                setFlowViewMode("timeline");
                                setSelectedSpan(null);
                              }}
                              className={`px-3 py-1 rounded text-[10px] uppercase tracking-[0.2em] transition-colors ${flowViewMode === "timeline"
                                ? "bg-slate-700 text-white"
                                : "text-slate-400 hover:text-slate-300"
                                }`}
                            >
                              Timeline
                            </button>
                            <button
                              onClick={() => {
                                setFlowViewMode("graph");
                                setSelectedSpan(null);
                              }}
                              className={`px-3 py-1 rounded text-[10px] uppercase tracking-[0.2em] transition-colors ${flowViewMode === "graph"
                                ? "bg-slate-700 text-white"
                                : "text-slate-400 hover:text-slate-300"
                                }`}
                            >
                              Graph
                            </button>
                          </div>
                          {flowViewMode === "graph" && (
                            <label className="flex items-center gap-2 px-3 py-1 text-[10px] text-slate-400 bg-slate-950 rounded-lg cursor-pointer hover:text-slate-300">
                              <input
                                type="checkbox"
                                checked={hideToolSpans}
                                onChange={(e) => setHideToolSpans(e.target.checked)}
                                className="w-3 h-3"
                              />
                              <span>Hide tool spans</span>
                            </label>
                          )}
                        </div>
                      )}
                    </div>

                    {traceDetail.flow_spans && traceDetail.flow_spans.length > 0 ? (
                      <>
                        {flowViewMode === "timeline" ? (
                          <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
                            {traceDetail.flow_spans
                              .sort((a, b) => a.ts_start_ms - b.ts_start_ms)
                              .map((span) => {
                                const statusClass =
                                  span.status === "ok"
                                    ? "bg-emerald-900/40 text-emerald-200"
                                    : "bg-rose-900/40 text-rose-200";
                                return (
                                  <div
                                    key={span.span_id}
                                    onClick={() => setSelectedSpan(span)}
                                    className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 cursor-pointer hover:bg-slate-900/60 transition-colors"
                                  >
                                    <div className="flex items-center justify-between gap-3">
                                      <div className="flex items-center gap-3 flex-1 min-w-0">
                                        <span className="text-xs font-mono text-slate-300 truncate">{span.name}</span>
                                        <span className={`px-2 py-1 rounded-full text-[10px] uppercase whitespace-nowrap ${statusClass}`}>
                                          {span.status}
                                        </span>
                                        <span className="text-[11px] text-slate-400 whitespace-nowrap">{span.kind}</span>
                                      </div>
                                      <span className="text-[11px] text-slate-400 whitespace-nowrap">{span.duration_ms}ms</span>
                                    </div>
                                    {span.summary.note && (
                                      <p className="mt-2 text-[11px] text-slate-400">{span.summary.note}</p>
                                    )}
                                    {span.summary.error_message && (
                                      <p className="mt-2 text-[11px] text-rose-300">{span.summary.error_message}</p>
                                    )}
                                  </div>
                                );
                              })}
                          </div>
                        ) : (
                          <div style={{ height: "400px", background: "#1e293b", borderRadius: "0.75rem", border: "1px solid #475569" }}>
                            <ReactFlow
                              nodes={nodes}
                              edges={edges}
                              onNodesChange={onNodesChange}
                              onEdgesChange={onEdgesChange}
                              onNodeClick={(event, node) => {
                                setSelectedNodeId(node.id);
                                const span = traceDetail.flow_spans?.find((s) => s.span_id === node.id);
                                if (span) {
                                  setSelectedSpan(span);
                                }
                              }}
                              nodeTypes={{ spanNode: SpanNode }}
                              fitView
                            >
                              <Background />
                              <Controls />
                            </ReactFlow>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-xs text-slate-500">Flow 데이터 없음 (구버전 trace)</p>
                    )}
                  </section>

                  {selectedSpan && (
                    <section className="bg-slate-900/60 border border-slate-700 rounded-2xl p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[10px] uppercase tracking-[0.3em] text-slate-400">Span Details</p>
                          <p className="text-sm font-semibold text-white mt-1">{selectedSpan.name}</p>
                        </div>
                        <button
                          onClick={() => setSelectedSpan(null)}
                          className="text-slate-400 hover:text-white text-lg"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-xs text-slate-300">
                        <div>
                          <p className="text-slate-500 uppercase tracking-[0.2em] text-[9px]">Kind</p>
                          <p className="mt-1">{selectedSpan.kind}</p>
                        </div>
                        <div>
                          <p className="text-slate-500 uppercase tracking-[0.2em] text-[9px]">Status</p>
                          <p className="mt-1">{selectedSpan.status}</p>
                        </div>
                        <div>
                          <p className="text-slate-500 uppercase tracking-[0.2em] text-[9px]">Duration</p>
                          <p className="mt-1">{selectedSpan.duration_ms}ms</p>
                        </div>
                        <div>
                          <p className="text-slate-500 uppercase tracking-[0.2em] text-[9px]">Span ID</p>
                          <p className="mt-1 font-mono text-[10px]">{selectedSpan.span_id}</p>
                        </div>
                      </div>

                      {selectedSpan.links.plan_path && (
                        <div className="bg-slate-950/50 border border-slate-800 rounded-xl p-3 space-y-2">
                          <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Related Plan</p>
                          {renderJsonDetails(
                            selectedSpan.links.plan_path === "plan.raw" ? "Raw Plan" : "Validated Plan",
                            selectedSpan.links.plan_path === "plan.raw" ? traceDetail.plan_raw : traceDetail.plan_validated
                          )}
                        </div>
                      )}

                      {selectedSpan.links.tool_call_id && traceDetail.execution_steps && (
                        <div className="bg-slate-950/50 border border-slate-800 rounded-xl p-3 space-y-2">
                          <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Related Tool Call</p>
                          {(() => {
                            const step = traceDetail.execution_steps.find((s) => s.tool_name === selectedSpan.links.tool_call_id);
                            return step ? (
                              <div className="space-y-2">
                                {renderJsonDetails("Request", step.request)}
                                {renderJsonDetails("Response", step.response)}
                              </div>
                            ) : (
                              <p className="text-[11px] text-slate-400">Tool call not found</p>
                            );
                          })()}
                        </div>
                      )}
                    </section>
                  )}

                  <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Audit Logs</p>
                      <span className="text-[10px] text-slate-400">{traceAuditLogs.length} events</span>
                    </div>
                    <AuditLogTable logs={traceAuditLogs} onViewDetails={setSelectedLog} />
                  </section>
                </>
              )}
            </div>
          </div>
          {selectedLog && (
            <AuditLogDetailsModal log={selectedLog} onClose={() => setSelectedLog(null)} />
          )}
        </div>
      )}

      {/* Compare Modal */}
      {showCompareModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 w-96 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Compare with Trace</h3>
              <button
                onClick={() => setShowCompareModal(false)}
                className="text-slate-400 hover:text-white text-xl"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 mb-2">
                  Trace ID to Compare
                </label>
                <input
                  type="text"
                  value={compareTraceId}
                  onChange={(e) => setCompareTraceId(e.target.value)}
                  placeholder="Paste trace_id..."
                  className="w-full px-3 py-2 bg-slate-900/40 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleFetchCompareTrace();
                    }
                  }}
                />
              </div>

              {compareError && (
                <div className="px-3 py-2 rounded-lg bg-rose-900/20 border border-rose-800 text-rose-300 text-xs">
                  {compareError}
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowCompareModal(false)}
                  className="px-3 py-2 rounded-lg border border-slate-700 text-xs uppercase tracking-[0.2em] hover:border-slate-500"
                >
                  Cancel
                </button>
                <button
                  onClick={handleFetchCompareTrace}
                  disabled={compareFetching}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs uppercase tracking-[0.2em] text-white disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {compareFetching ? "Fetching..." : "Compare"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Diff View */}
      {showDiffView && traceDetail && compareTraceDetail && (
        <TraceDiffView
          traceA={traceDetail}
          traceB={compareTraceDetail}
          onClose={() => {
            setShowDiffView(false);
            setCompareTraceDetail(null);
          }}
        />
      )}
    </div>
  );
}

export default function InspectorPage() {
  return (
    <ReactFlowProvider>
      <InspectorContent />
    </ReactFlowProvider>
  );
}
