"use client";

import React, { Suspense } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Toast from "../../../components/admin/Toast";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Asset,
  AuditLog,
  fetchApi,
  formatRelativeTime,
  formatTimestamp,
} from "../../../lib/adminUtils";
import AuditLogTable, { AuditLogDetailsModal } from "../../../components/admin/AuditLogTable";
import ValidationAlert from "../../../components/admin/ValidationAlert";
import SpanNode from "../../../components/admin/SpanNode";
import TraceDiffView from "../../../components/admin/TraceDiffView";
import StageDiffView from "../../../components/admin/StageDiffView";
import InspectorStagePipeline, {
  type StageStatus,
} from "../../../components/ops/InspectorStagePipeline";
import ReplanTimeline from "../../../components/ops/ReplanTimeline";
import AssetOverrideModal from "../../../components/ops/AssetOverrideModal";
import { OrchestrationSection } from "../../../components/ops/OrchestrationSection";
import { generateNodes, generateEdges, filterToolSpans } from "../../../lib/flowGraphUtils";
import { cn } from "@/lib/utils";
import {
  AnswerBlock,
  AssetSummary,
  AssetOverride,
  AssetVersion,
  FlowSpan,
  StageInput,
  StageOutput,
  StageSnapshot,
  ExecutionTraceDetail,
  TraceSummaryRow,
  TraceListResponse,
  ExecutionStep,
  ReferenceEntry,
  UIRenderedBlock,
} from "../../../lib/apiClient/index";
import type { FilterState, TraceDetailResponse } from "../../../lib/inspector/types";
import {
  PER_PAGE,
  STAGE_ORDER,
  STAGE_LABELS,
  initialFilters,
  createPlaceholderTraceDetail,
} from "../../../lib/inspector/types";
import {
  getStatusBadgeClass,
  formatDuration,
  formatAppliedAssetSummary,
  summarizeStepPayload,
  summarizeBlockPayload,
  normalizeStageStatus,
} from "../../../lib/inspector/utils";

function InspectorContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTraceId = searchParams.get("trace_id");

  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [lookupTraceId, setLookupTraceId] = useState("");
  const [traces, setTraces] = useState<TraceSummaryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [traceDetail, setTraceDetail] = useState<ExecutionTraceDetail | null>(
    initialTraceId ? createPlaceholderTraceDetail(initialTraceId) : null,
  );
  const [traceAuditLogs, setTraceAuditLogs] = useState<AuditLog[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [planView, setPlanView] = useState<"raw" | "validated">("validated");
  const [traceCopyStatus, setTraceCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [linkCopyStatus, setLinkCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
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
  const [showStageDiffView, setShowStageDiffView] = useState(false);
  const [baselineStageTraceId, setBaselineStageTraceId] = useState("");
  const [showAssetOverrideModal, setShowAssetOverrideModal] = useState(false);
  const [availableAssets, setAvailableAssets] = useState<Record<string, AssetVersion[]>>({});
  const [assetOverrideLoading, setAssetOverrideLoading] = useState(false);
  const [assetOverrideError, setAssetOverrideError] = useState<string | null>(null);
  const [singleRcaLoading, setSingleRcaLoading] = useState(false);
  const [singleRcaError, setSingleRcaError] = useState<string | null>(null);

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
        if (filters.assetName) params.set("asset_name", filters.assetName);
        const response = await fetchApi<TraceListResponse>(
          `/inspector/traces?${params.toString()}`,
        );
        setTraces((prev) =>
          nextOffset === 0 ? response.data.traces : [...prev, ...response.data.traces],
        );
        setTotal(response.data.total);
        setOffset(nextOffset + response.data.traces.length);
      } catch (err: unknown) {
        const errorObj = err as Error | { message: string; details?: unknown };
        setError(errorObj.message || "업무 추적 데이터를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    },
    [filters],
  );

  const fetchTraceDetail = useCallback(async (traceId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    setStatusMessage(null);

    const token = localStorage.getItem("access_token");
    const url = `/inspector/traces/${encodeURIComponent(traceId)}`;

    try {
      const response = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });

      if (response.status === 404) {
        // trace_id not found - show toast only, don't open drawer
        const errorMessage = `"${traceId}" trace_id를 찾을 수 없습니다.`;
        setStatusMessage(errorMessage);
        setDetailLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = (await response.json()) as TraceDetailResponse;

      if (!data.data?.trace) {
        if (process.env.NODE_ENV === 'development') {
          console.warn("[Inspector] No trace in response data");
        }
        setStatusMessage(`"${traceId}" trace_id를 찾을 수 없습니다.`);
        setDetailLoading(false);
        return;
      }

      setTraceDetail(data.data.trace);
      setTraceAuditLogs(data.data.audit_logs || []);
      setSelectedTraceId(data.data.trace.trace_id);
      setStatusMessage(null); // Clear any error message
    } catch (err: unknown) {
      console.error("[Inspector] Error fetching trace detail:", err);
      const errorMessage = err instanceof Error ? err.message : "실행 증거를 불러오지 못했습니다.";
      setStatusMessage(errorMessage);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    // Skip initial search if trace_id is in URL params
    const traceIdParam = searchParams.get("trace_id");
    if (!traceIdParam) {
      handleSearch(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const traceIdParam = searchParams.get("trace_id");
    if (traceIdParam) {
      setLookupTraceId(traceIdParam);
      setDetailError(null);
      setTraceDetail(createPlaceholderTraceDetail(traceIdParam));
      setTraceAuditLogs([]);
      setSelectedTraceId(traceIdParam);
      fetchTraceDetail(traceIdParam);
    }
  }, [searchParams, fetchTraceDetail]);

  // Load asset names when trace detail is loaded (for InspectorStagePipeline)
  useEffect(() => {
    const loadAssetNames = async () => {
      if (Object.keys(availableAssets).length === 0) {
        try {
          const response = await fetchApi<{ assets: Asset[] }>("/asset-registry/assets");
          const grouped: Record<string, AssetVersion[]> = {};
          response.data.assets.forEach((asset) => {
            if (!asset.asset_type) return;
            const status = asset.status === "published" ? "published" : "draft";
            const assetVersion: AssetVersion = {
              id: asset.asset_id,
              asset_id: asset.asset_id,
              asset_type: asset.asset_type,
              version: String(asset.version ?? "1"),
              name: asset.name,
              description: asset.description ?? undefined,
              created_at: asset.updated_at ?? asset.published_at ?? new Date().toISOString(),
              status,
              author: "system",
              size: 0,
              metadata: {},
            };
            if (!grouped[asset.asset_type]) {
              grouped[asset.asset_type] = [];
            }
            grouped[asset.asset_type].push(assetVersion);
          });
          setAvailableAssets(grouped);
        } catch {
          // Ignore errors for asset loading
        }
      }
    };
    loadAssetNames();
  }, [availableAssets]);

  useEffect(() => {
    setTraceCopyStatus("idle");
    setLinkCopyStatus("idle");
  }, [traceDetail?.trace_id]);

  // Generate graph nodes and edges when traceDetail or hideToolSpans changes
  useEffect(() => {
    if (traceDetail?.flow_spans && traceDetail.flow_spans.length > 0) {
      const spansToUse = hideToolSpans
        ? filterToolSpans(traceDetail.flow_spans)
        : traceDetail.flow_spans;
      const generatedNodes = generateNodes(spansToUse);
      const generatedEdges = generateEdges(spansToUse);

      setNodes(
        generatedNodes.map((node) => ({
          ...node,
          selected: node.id === selectedNodeId,
        })),
      );
      setEdges(generatedEdges);
    }
  }, [traceDetail?.flow_spans, hideToolSpans, selectedNodeId, setNodes, setEdges]);

  const handleLookup = () => {
    if (!lookupTraceId.trim()) {
      const msg = "Trace ID를 입력하세요.";
      setDetailError(msg);
      setStatusMessage(msg);
      return;
    }

    // No format validation - let server check if trace_id exists
    const traceId = lookupTraceId.trim();
    fetchTraceDetail(traceId);
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

  const handleStageCompareClick = () => {
    if (!selectedTraceId) {
      alert("Please select a trace first");
      return;
    }
    setShowStageDiffView(true);
    setBaselineStageTraceId(selectedTraceId);
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
        `/inspector/traces/${encodeURIComponent(compareTraceId.trim())}`,
      );
      setCompareTraceDetail(response.data.trace);
      setShowDiffView(true);
      setShowCompareModal(false);
    } catch (err: unknown) {
      setCompareError((err as Error).message || "비교 trace를 불러오는데 실패했습니다.");
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

      const resolvedTraceId =
        response.data?.trace_id ?? (response as { trace_id?: string }).trace_id;
      if (!resolvedTraceId) {
        setSingleRcaError("Invalid RCA response: missing trace_id");
        return;
      }

      setShowDiffView(false);
      setCompareTraceDetail(null);
      setTraceDetail(null);
      setTraceAuditLogs([]);
      setSelectedTraceId(null);
      setDetailError(null);
      router.push(`/admin/inspector?trace_id=${encodeURIComponent(resolvedTraceId)}`);
    } catch (err: unknown) {
      setSingleRcaError((err as Error).message || "Failed to run RCA analysis.");
    } finally {
      setSingleRcaLoading(false);
    }
  }, [traceDetail, router]);

  const renderAppliedAsset = (asset: AssetSummary | null | undefined) => {
    if (!asset) {
      return (
        <span className="text-xs text-muted-foreground">
          미적용
        </span>
      );
    }
    return (
      <div className="space-y-1 text-xs text-muted-foreground">
        {asset.name && <p>{asset.name}</p>}
        <p className="font-mono text-sm text-foreground">
          {asset.asset_id || `${asset.name || "asset"}@${asset.source || "fallback"}`}
          {asset.version ? ` · v${asset.version}` : ""}
        </p>
        {asset.source && (
          <p className="uppercase text-xs tracking-wider text-muted-foreground">
            {asset.source}
          </p>
        )}
      </div>
    );
  };

  const highlightFallbacks = (fallbacks: Record<string, boolean> | null | undefined) => {
    if (!fallbacks) return null;
    const entries = Object.entries(fallbacks).filter(([key]) => {
      // Prefer catalog label when both keys exist.
      if (key === "schema" && Object.prototype.hasOwnProperty.call(fallbacks, "catalog")) {
        return false;
      }
      return true;
    });
    return (
      <div className="flex gap-2 flex-wrap text-sm">
        {entries.map(([key, value]) => (
          <span
            key={key}
            className={cn(
              "px-2 py-1 rounded-full border font-semibold uppercase tracking-wider text-xs",
              value
                ? "border-amber-500/50 bg-amber-500/15 text-amber-700 dark:text-amber-300"
                : "border-emerald-500/50 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
            )}
          >
            {key === "schema" ? "catalog" : key}: {value ? "fallback" : "asset"}
          </span>
        ))}
      </div>
    );
  };

  const renderJsonDetails = (label: string, payload: unknown): React.ReactNode | null => {
    if (!payload) {
      return null;
    }
    return (
      <details className="border border-border bg-surface-base rounded-xl p-3">
        <summary className="text-xs font-semibold cursor-pointer text-muted-standard">
          {label}
        </summary>
        <pre className="mt-2 text-sm overflow-x-auto max-h-48 text-muted-standard">
          {JSON.stringify(payload, null, 2)}
        </pre>
      </details>
    );
  };

  const stageSnapshots: StageSnapshot[] = useMemo(() => {
    const inputs = traceDetail?.stage_inputs ?? [];
    const outputs = traceDetail?.stage_outputs ?? [];
    return STAGE_ORDER.map((stage) => {
      const stageInput = inputs.find((entry: StageInput) => entry.stage === stage);
      const stageOutput = outputs.find((entry: StageOutput) => entry.stage === stage);
      return {
        name: stage,
        label: STAGE_LABELS[stage] ?? stage.toUpperCase(),
        status: normalizeStageStatus(stageOutput) as StageStatus,
        duration_ms: stageOutput?.duration_ms,
        input: stageInput ?? null,
        output: stageOutput ?? null,
        diagnostics: stageOutput?.diagnostics ?? null,
      } as StageSnapshot;
    });
  }, [traceDetail?.stage_inputs, traceDetail?.stage_outputs]);

  // availableAssets를 assetNames 형식으로 변환
  const assetNames = useMemo(() => {
    const names: Record<string, { name: string; version?: string }> = {};
    Object.entries(availableAssets).forEach(([_, assetList]) => {
      assetList.forEach((asset) => {
        names[asset.asset_id] = {
          name: asset.name,
          version: asset.version,
        };
      });
    });
    return names;
  }, [availableAssets]);

  const resolveAssetDisplayName = useCallback(
    (value: string): string => {
      if (!value) {
        return value;
      }
      const raw = value.trim();
      const versionMatch = raw.match(/:v(\d+)$/);
      const normalizedId = versionMatch ? raw.slice(0, versionMatch.index) : raw;
      const found = assetNames[normalizedId];
      if (found?.name) {
        if (versionMatch?.[1]) {
          return `${found.name} (v${versionMatch[1]})`;
        }
        if (found.version) {
          return `${found.name} (v${found.version})`;
        }
        return found.name;
      }
      return raw;
    },
    [assetNames],
  );

  const loadOverrideAssets = useCallback(async () => {
    setAssetOverrideLoading(true);
    setAssetOverrideError(null);
    try {
      const response = await fetchApi<{ assets: Asset[] }>("/asset-registry/assets");
      const grouped: Record<string, AssetVersion[]> = {};
      response.data.assets.forEach((asset) => {
        if (!asset.asset_type) return;
        const status = asset.status === "published" ? "published" : "draft";
        const assetVersion: AssetVersion = {
          id: asset.asset_id,
          asset_id: asset.asset_id,
          asset_type: asset.asset_type,
          version: String(asset.version ?? "1"),
          name: asset.name,
          description: asset.description ?? undefined,
          created_at: asset.updated_at ?? asset.published_at ?? new Date().toISOString(),
          status,
          author: "system",
          size: 0,
          metadata: {},
        };
        if (!grouped[asset.asset_type]) {
          grouped[asset.asset_type] = [];
        }
        grouped[asset.asset_type].push(assetVersion);
      });
      setAvailableAssets(grouped);
    } catch (err: unknown) {
      const message = (err as Error).message || "자산 목록을 불러오지 못했습니다.";
      setAssetOverrideError(message);
      setStatusMessage(message);
    } finally {
      setAssetOverrideLoading(false);
    }
  }, []);

  useEffect(() => {
    if (showAssetOverrideModal) {
      loadOverrideAssets();
    }
  }, [showAssetOverrideModal, loadOverrideAssets]);

  const handleAssetOverrideRun = useCallback(
    async (overrides: AssetOverride[]) => {
      if (!traceDetail) {
        setStatusMessage("Trace가 선택되지 않았습니다.");
        return;
      }
      const overrideMap: Record<string, string> = {};
      overrides.forEach((override) => {
        overrideMap[override.asset_type] = override.asset_name;
      });
      const baselineTraceId = traceDetail.trace_id;
      setStatusMessage("Asset override 실행 중...");
      try {
        const response = await fetchApi<{
          answer: string;
          trace: Record<string, unknown>;
          meta?: Record<string, unknown>;
        }>("/ops/ask", {
          method: "POST",
          body: JSON.stringify({
            question: traceDetail.question,
            asset_overrides: overrideMap,
            source_asset: overrideMap.source,
            schema_asset: overrideMap.schema,
            resolver_asset: overrideMap.resolver,
          }),
        });
        const newTraceId =
          (response.data.meta?.trace_id as string | undefined) ||
          (response.data.trace?.trace_id as string | undefined);
        if (newTraceId) {
          await fetchTraceDetail(newTraceId);
          setBaselineStageTraceId(baselineTraceId);
          setShowStageDiffView(true);
          setStatusMessage(`Override 실행 완료: ${newTraceId}`);
        } else {
          setStatusMessage("Override 실행 완료: 새 trace_id를 찾지 못했습니다.");
        }
      } catch (err: unknown) {
        setStatusMessage((err as Error).message || "Override 실행 실패");
      } finally {
        setShowAssetOverrideModal(false);
      }
    },
    [traceDetail, fetchTraceDetail],
  );

  return (
    <div className="space-y-6">
      <div className="px-6 pb-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="insp-section lg:col-span-4">
          <div className="flex gap-3">
            <label htmlFor="trace-id-lookup" className="form-field-label whitespace-nowrap self-center">
              Trace_id
            </label>
            <input
              id="trace-id-lookup"
              type="text"
              value={lookupTraceId}
              onChange={(event) => setLookupTraceId(event.target.value)}
              placeholder="Trace ID를 입력하세요"
              className="input-container flex-1"
            />
            <button
              onClick={handleLookup}
              className="rounded-md bg-sky-600 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:bg-sky-500"
            >
              {detailLoading ? "로딩..." : "조회"}
            </button>
          </div>
        </div>

        <div className="insp-section lg:col-span-8">
          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <input
                type="text"
                value={filters.q}
                onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
                placeholder="질의 또는 키워드(q)"
                className="input-container"
              />
              <input
                type="text"
                value={filters.feature}
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, feature: event.target.value }))
                }
                placeholder="Feature (예: ci)"
                className="input-container"
              />
              <input
                type="text"
                value={filters.assetName}
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, assetName: event.target.value }))
                }
                placeholder="Asset name 기준"
                className="input-container"
              />
              <div className="flex items-center justify-end">
                <button
                  onClick={handleResetFilters}
                  className="rounded-md border border-border px-4 py-2 text-xs uppercase tracking-wider text-foreground transition hover:bg-surface-elevated dark:border-border dark:text-foreground dark:hover:bg-surface-elevated"
                >
                  Reset
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <select
                value={filters.status}
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, status: event.target.value }))
                }
                className="input-container"
              >
                <option value="">응답 상태 (전체)</option>
                <option value="success">success</option>
                <option value="error">error</option>
              </select>
              <input
                type="date"
                value={filters.from}
                onChange={(event) =>
                  setFilters((prev) => ({ ...prev, from: event.target.value }))
                }
                className="input-container [color-scheme:light] dark:[color-scheme:dark]"
              />
              <input
                type="date"
                value={filters.to}
                onChange={(event) => setFilters((prev) => ({ ...prev, to: event.target.value }))}
                className="input-container [color-scheme:light] dark:[color-scheme:dark]"
              />
              <div className="flex items-center justify-end">
                <button
                  onClick={() => handleSearch(0)}
                  disabled={loading}
                  className="rounded-md bg-emerald-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white transition hover:bg-emerald-500 disabled:opacity-50"
                >
                  {loading ? "Searching..." : "Trace Search"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && <ValidationAlert errors={[error]} onClose={() => setError(null)} />}

      <div
        className="border rounded-2xl overflow-hidden shadow-2xl border-border bg-surface-elevated"
      >
        <div
          className="px-5 py-3 border-b flex items-center justify-between border-border"
        >
          <p className="text-sm font-semibold text-white">
            Trace Results · {traces.length} 건 중 {total}개
          </p>
        </div>
        {loading && traces.length === 0 ? (
          <div className="py-12 flex flex-col items-center gap-3">
            <div
              className="w-10 h-10 rounded-full border-2 border-t-emerald-400 animate-spin"
            />
            <p
              className="text-sm uppercase tracking-widest"
            >
              Loading traces...
            </p>
          </div>
        ) : traces.length === 0 ? (
          <div className="py-12 text-center text-xs  text-muted-standard">
            필터를 조정하여 실행 기록을 검색하세요.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr
                  className="text-left text-xs uppercase tracking-wider border-b border-border text-muted-standard"
                >
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Feature</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Route</th>
                  <th className="px-4 py-3">Replans</th>
                  <th className="px-4 py-3">Question</th>
                  <th className="px-4 py-3">Assets</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((trace) => (
                  <tr
                    key={trace.trace_id}
                    onClick={() => handleRowClick(trace.trace_id)}
                    className="border-b transition-colors cursor-pointer bg-surface-base border-border"
                  >
                    <td className="px-4 py-3">
                      <p
                        className="font-mono text-xs "
                      >
                        {trace.trace_id.slice(0, 8)}
                      </p>
                      <p className="text-sm  text-muted-standard">
                        {formatRelativeTime(trace.created_at)}
                    </p>
                    <p className="text-xs text-muted-standard">
                      </p>
                      <p className="text-xs  text-muted-standard">
                        {formatTimestamp(trace.created_at)}
                      </p>
                    </td>
                    <td className="px-4 py-3  text-muted-standard">
                      {trace.feature}
                    </td>
                    <td className="px-4 py-3  text-foreground">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${getStatusBadgeClass(trace.status)}`}
                      >
                        {trace.status}
                      </span>
                    </td>
                    <td className="px-4 py-3  text-muted-standard">
                      {formatDuration(trace.duration_ms)}
                    </td>
                    <td className="px-4 py-3">
                      {trace.route ? (
                        <span className="px-2 py-1 rounded-full text-xs font-mono bg-sky-500/10 text-sky-400">
                          {trace.route}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {trace.replan_count !== undefined && trace.replan_count >= 0 ? (
                        trace.replan_count > 0 ? (
                          <span className="px-2 py-1 rounded-full text-xs bg-amber-500/10 text-amber-400">
                            {trace.replan_count}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">0</span>
                        )
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs  text-muted-standard">
                      {trace.question_snippet}
                    </td>
                    <td
                      className="px-4 py-3 text-xs "
                    >
                      {formatAppliedAssetSummary(trace, resolveAssetDisplayName)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {offset < total && traces.length > 0 && (
          <div
            className="p-4 flex justify-center border-t "
          >
            <button
              onClick={() => handleSearch(offset)}
              disabled={loading}
              className="px-6 py-2 rounded-full text-xs uppercase tracking-wider opacity-50 bg-surface-elevated dark:bg-surface-elevated"
            >
              {loading ? "불러오는 중..." : "Load More"}
            </button>
          </div>
        )}
      </div>

      {traceDetail && (
        <div
          data-testid="inspector-drawer"
          className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/70 p-4"
        >
          <div
            className="border border-border max-w-6xl w-full max-h-[90vh] rounded-3xl overflow-hidden shadow-2xl flex flex-col bg-surface-elevated"
          >
            <header
              className="px-6 py-4 border-b border-border flex flex-col gap-4 md:flex-row md:items-center md:justify-between"
            >
              <div className="space-y-3">
                <p
                  className="text-xs uppercase tracking-wider text-muted-foreground"
                >
                  Trace Overview
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-sm font-semibold text-foreground tracking-tight">
                    {traceDetail.question}
                  </h2>
                  <span
                    className={`px-3 py-1 rounded-full text-xs uppercase tracking-wider ${getStatusBadgeClass(
                      traceDetail.status,
                    )}`}
                  >
                    {traceDetail.status}
                  </span>
                </div>
                <div
                  className="flex flex-wrap gap-3 text-xs text-muted-foreground"
                >
                  <span>Feature: {traceDetail.feature}</span>
                  <span>Mode: {traceDetail.ops_mode}</span>
                  <span>Endpoint: {traceDetail.endpoint}</span>
                  <span>Method: {traceDetail.method}</span>
                </div>
                <div
                  className="flex flex-wrap items-center gap-2 text-sm"
                >
                  <span className="font-mono text-foreground">{traceDetail.trace_id}</span>
                  <button
                    onClick={handleCopyTraceId}
                    className="px-3 py-1 rounded-lg border border-border text-xs uppercase tracking-wider transition text-foreground hover:bg-surface-overlay"
                  >
                    {traceCopyStatus === "copied"
                      ? "복사됨"
                      : traceCopyStatus === "failed"
                        ? "재시도"
                        : "Copy trace_id"}
                  </button>
                  <button
                    onClick={handleCopyLink}
                    className="px-3 py-1 rounded-lg border border-border text-xs uppercase tracking-wider transition text-foreground hover:bg-surface-overlay"
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
                      className="px-3 py-1 rounded-lg border border-border text-xs uppercase tracking-wider transition text-foreground hover:bg-surface-overlay"
                    >
                      View parent
                    </button>
                  )}
                </div>
                <div
                  className="flex flex-wrap gap-4 text-sm text-muted-foreground"
                >
                  <span>Duration: {formatDuration(traceDetail.duration_ms)}</span>
                  <span>{formatTimestamp(traceDetail.created_at)}</span>
                  <span>{formatRelativeTime(traceDetail.created_at)}</span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={handleRunSingleRca}
                  disabled={singleRcaLoading}
                  className={cn(
                    "px-3 py-2 rounded-xl border text-xs uppercase tracking-wider transition",
                    singleRcaLoading
                      ? "border-border text-muted-foreground opacity-50 cursor-not-allowed"
                      : "border-sky-600 bg-sky-600 text-white hover:bg-sky-500 dark:border-sky-700 dark:bg-sky-700 dark:hover:bg-sky-600"
                  )}
                  data-testid="drawer-run-rca"
                >
                  {singleRcaLoading ? "Analyzing..." : "Run RCA"}
                </button>
                <button
                  onClick={handleCompareClick}
                  className="px-3 py-2 rounded-xl border border-emerald-600 bg-emerald-600 text-xs uppercase tracking-wider text-white transition hover:bg-emerald-500 dark:border-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-600"
                >
                  Compare
                </button>
                <button
                  onClick={handleStageCompareClick}
                  className="px-3 py-2 rounded-xl border border-amber-600 bg-amber-600 text-xs uppercase tracking-wider text-white transition hover:bg-amber-500 dark:border-amber-700 dark:bg-amber-700 dark:hover:bg-amber-600"
                >
                  Stage Compare
                </button>
                <button
                  onClick={() => {
                    setTraceDetail(null);
                    setTraceAuditLogs([]);
                    setSelectedTraceId(null);
                    setDetailError(null);
                    setShowDiffView(false);
                  }}
                  className="px-3 py-2 rounded-xl border border-border text-foreground text-xs uppercase tracking-wider transition hover:bg-surface-overlay"
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
                  <div
                    className="w-10 h-10 rounded-full border-2 border-t-emerald-400 animate-spin"
                  />
                  <p
                    className="text-xs uppercase tracking-wider"
                  >
                    Loading detail...
                  </p>
                </div>
              ) : (
                <>
                  <section
                    data-testid="flow-section"
                    className="border border-border rounded-2xl p-5 space-y-3 bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider text-muted-foreground"
                      >
                        Overview
                      </p>
                      <span className="text-xs text-muted-foreground">
                        Request & Context
                      </span>
                    </div>
                    <p className="text-sm text-foreground">{traceDetail.question}</p>
                    <div
                      className="flex flex-wrap gap-2 text-sm"
                    >
                      <span
                        className="px-2 py-1 rounded-full bg-surface-elevated text-foreground"
                      >
                        Mode: {traceDetail.ops_mode}
                      </span>
                      <span
                        className="px-2 py-1 rounded-full bg-surface-elevated text-foreground"
                      >
                        Endpoint: {traceDetail.endpoint}
                      </span>
                      <span
                        className="px-2 py-1 rounded-full bg-surface-elevated text-foreground"
                      >
                        Method: {traceDetail.method}
                      </span>
                      <span
                        className="px-2 py-1 rounded-full bg-surface-elevated text-foreground"
                      >
                        Route: {traceDetail.route ?? "orch"}
                      </span>
                    </div>
                    <div
                      className="flex flex-wrap gap-3 text-sm text-muted-foreground"
                    >
                      <span>Duration: {formatDuration(traceDetail.duration_ms)}</span>
                      <span>{formatTimestamp(traceDetail.created_at)}</span>
                      <span>{formatRelativeTime(traceDetail.created_at)}</span>
                    </div>
                    {renderJsonDetails("Request payload", traceDetail.request_payload)}
                  </section>

                  <section
                    className="border border-border rounded-2xl p-5 space-y-3 bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider text-muted-foreground"
                      >
                        Applied Assets
                      </p>
                      {highlightFallbacks(traceDetail.fallbacks)}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div
                        className="rounded-xl border border-border px-4 py-3 bg-surface-elevated"
                      >
                        <p
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Prompt
                        </p>
                        {renderAppliedAsset(traceDetail.applied_assets?.prompt ?? null)}
                      </div>
                      <div
                        className="rounded-xl border border-border px-4 py-3 bg-surface-elevated"
                      >
                        <p
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Policy
                        </p>
                        {renderAppliedAsset(traceDetail.applied_assets?.policy ?? null)}
                      </div>
                      <div
                        className="rounded-xl border border-border px-4 py-3 bg-surface-elevated"
                      >
                        <p
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Mapping
                        </p>
                        {renderAppliedAsset(traceDetail.applied_assets?.mapping ?? null)}
                      </div>
                      <div className="md:col-span-2 space-y-2">
                        <p
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Queries
                        </p>
                        {traceDetail.applied_assets?.queries?.length ? (
                          <ul className="space-y-2">
                            {traceDetail.applied_assets.queries.map(
                              (query: {
                                asset_id: string | null;
                                name: string | null;
                                source: string | null;
                              }) => (
                                <li
                                  key={query.asset_id || `${query.name}-${query.source}`}
                                  className="border border-border rounded-xl px-3 py-2 text-sm text-foreground bg-surface-elevated"
                                >
                                  {query.name || "query"} · {query.source} ·{" "}
                                  {query.asset_id ?? "seed"}
                                </li>
                              ),
                            )}
                          </ul>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Query asset 없음
                          </p>
                        )}
                      </div>
                      <div className="md:col-span-2 space-y-2">
                        <p
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Screens
                        </p>
                        {traceDetail.applied_assets?.screens?.length ? (
                          <ul className="space-y-2">
                            {traceDetail.applied_assets.screens.map((screen) => (
                              <li
                                key={screen.asset_id || `${screen.screen_id}-${screen.status}`}
                                className="border border-border rounded-xl px-3 py-2 text-sm text-foreground bg-surface-elevated"
                              >
                                {screen.screen_id || "screen"} · {screen.status ?? "unknown"} ·{" "}
                                {screen.version ?? "?"}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Screen asset 없음
                          </p>
                        )}
                      </div>
                    </div>
                  </section>

                  <section
                    data-testid="regression-panel"
                    className="border border-border rounded-2xl p-5 space-y-4 bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider text-muted-foreground"
                      >
                        Plan
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPlanView("raw")}
                          className={cn(
                            "px-3 py-1 rounded-full text-xs uppercase tracking-wider transition",
                            planView === "raw"
                              ? "bg-surface-elevated border border-border text-foreground"
                              : "border border-border text-muted-foreground hover:text-foreground hover:bg-surface-overlay"
                          )}
                        >
                          Raw
                        </button>
                        <button
                          onClick={() => setPlanView("validated")}
                          className={cn(
                            "px-3 py-1 rounded-full text-xs uppercase tracking-wider transition",
                            planView === "validated"
                              ? "bg-surface-elevated border border-border text-foreground"
                              : "border border-border text-muted-foreground hover:text-foreground hover:bg-surface-overlay"
                          )}
                        >
                          Validated
                        </button>
                      </div>
                    </div>
                    {renderJsonDetails(
                      planView === "raw" ? "Raw plan snapshot" : "Validated plan snapshot",
                      planView === "raw" ? traceDetail.plan_raw : traceDetail.plan_validated,
                    )}
                    <div>
                      <p
                        className="text-xs uppercase tracking-wider text-muted-foreground"
                      >
                        Plan steps
                      </p>
                      <div className="mt-2 overflow-x-auto">
                        {traceDetail.execution_steps && traceDetail.execution_steps.length ? (
                          <table
                            className="min-w-full text-xs"
                          >
                            <thead>
                              <tr
                                className="text-left text-xs uppercase tracking-wider border-b border-border text-muted-foreground"
                              >
                                <th className="px-2 py-2">Step</th>
                                <th className="px-2 py-2">Tool</th>
                                <th className="px-2 py-2">Status</th>
                                <th className="px-2 py-2">Duration</th>
                                <th className="px-2 py-2">Summary</th>
                              </tr>
                            </thead>
                            <tbody>
                              {traceDetail.execution_steps.map((step: ExecutionStep) => (
                                <tr
                                  key={`${step.step_id}-${step.tool_name}-${step.duration_ms}`}
                                  className="border-b border-border"
                                >
                                  <td className="px-2 py-2 text-foreground">{step.step_id || "step"}</td>
                                  <td className="px-2 py-2 text-foreground">{step.tool_name || "tool"}</td>
                                  <td className="px-2 py-2">
                                    <span
                                      className={`px-2 py-1 rounded-full text-xs ${
                                        step.status === "success"
                                          ? "bg-emerald-900/40 text-emerald-200"
                                          : "bg-rose-900/40 text-rose-200"
                                      }`}
                                    >
                                      {step.status}
                                    </span>
                                  </td>
                                  <td className="px-2 py-2 text-foreground">{formatDuration(step.duration_ms)}</td>
                                  <td className="px-2 py-2 text-muted-foreground">
                                    {summarizeStepPayload(step.request || step.response)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Plan step 정보가 없습니다.
                          </p>
                        )}
                      </div>
                    </div>
                  </section>

                  <section
                    className="border border-border rounded-2xl p-5 space-y-4 bg-surface-base"
                  >
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div className="flex items-center gap-3">
                        <p
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Stage Pipeline
                        </p>
                        <span className="text-xs text-muted-foreground">
                          Route: {traceDetail.route ?? "orch"}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {traceDetail.stage_outputs?.length ?? 0} stages
                        </span>
                      </div>
                      <button
                        onClick={() => setShowAssetOverrideModal(true)}
                        className="px-3 py-2 rounded-xl border border-border text-foreground text-xs uppercase tracking-wider transition hover:bg-surface-overlay"
                      >
                        Asset Override Test
                      </button>
                      {assetOverrideLoading && (
                        <span
                          className="text-xs uppercase tracking-wider text-muted-foreground"
                        >
                          Loading assets...
                        </span>
                      )}
                      {assetOverrideError && !assetOverrideLoading && (
                        <span className="text-xs text-rose-300 uppercase tracking-wider">
                          Asset load failed
                        </span>
                      )}
                    </div>
                    {traceDetail.stage_outputs?.length ? (
                      <InspectorStagePipeline
                        traceId={traceDetail.trace_id}
                        stages={stageSnapshots}
                        showAssets={true}
                        assetNames={assetNames}
                      />
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Stage trace가 아직 없습니다.
                      </p>
                    )}
                    <div className="grid gap-4 md:grid-cols-2">
                      {STAGE_ORDER.map((stage) => {
                        const stageInput = traceDetail.stage_inputs?.find(
                          (entry: StageInput) => entry.stage === stage,
                        );
                        const stageOutput = traceDetail.stage_outputs?.find(
                          (entry: StageOutput) => entry.stage === stage,
                        );
                        const status = normalizeStageStatus(stageOutput);
                        const warnings = stageOutput?.diagnostics?.warnings ?? [];
                        const errors = stageOutput?.diagnostics?.errors ?? [];
                        const appliedAssets = stageInput?.applied_assets;

                        return (
                          <article
                            key={stage}
                            className="border border-border rounded-xl p-4 space-y-3 bg-surface-elevated"
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p
                                  className="text-xs uppercase tracking-wider text-muted-foreground"
                                >
                                  {STAGE_LABELS[stage] ?? stage.toUpperCase()}
                                </p>
                                <p
                                  className="text-sm font-mono text-foreground"
                                >
                                  {stage}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span
                                  className="text-xs uppercase tracking-wider text-muted-foreground"
                                >
                                  {stageOutput?.duration_ms ? `${stageOutput.duration_ms}ms` : "-"}
                                </span>
                                <span
                                  className="px-2 py-1 rounded-full text-xs uppercase tracking-wider text-foreground bg-surface-base border border-border"
                                >
                                  {status}
                                </span>
                              </div>
                            </div>

                            {/* Applied Assets Cards */}
                            {appliedAssets && Object.keys(appliedAssets).length > 0 && (
                              <div
                                className="rounded-lg p-3 border border-border bg-surface-base"
                              >
                                <p
                                  className="text-xs uppercase tracking-wider mb-2 text-muted-foreground"
                                >
                                  Applied Assets
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  {Object.entries(appliedAssets)
                                    .filter(([type]) => {
                                      // Prefer catalog label when both keys exist.
                                      if (
                                        type === "schema" &&
                                        Object.prototype.hasOwnProperty.call(appliedAssets, "catalog")
                                      ) {
                                        return false;
                                      }
                                      return true;
                                    })
                                    .map(([type, value]) => {
                                    if (!value) return null;
                                    const config = {
                                      prompt: {
                                        icon: "⭐",
                                        color: "text-sky-700 dark:text-sky-300",
                                      },
                                      policy: {
                                        icon: "🛡️",
                                        color: "text-emerald-700 dark:text-emerald-300",
                                      },
                                      mapping: {
                                        icon: "🗺️",
                                        color: "text-amber-700 dark:text-amber-300",
                                      },
                                      source: {
                                        icon: "💾",
                                        color: "text-muted-foreground",
                                      },
                                      catalog: {
                                        icon: "📊",
                                        color: "text-fuchsia-700 dark:text-fuchsia-300",
                                      },
                                      schema: {
                                        icon: "📊",
                                        color: "text-fuchsia-700 dark:text-fuchsia-300",
                                      },
                                      resolver: {
                                        icon: "🔧",
                                        color: "text-orange-700 dark:text-orange-300",
                                      },
                                      query: {
                                        icon: "🔍",
                                        color: "text-violet-700 dark:text-violet-300",
                                      },
                                    }[type] || {
                                      icon: "📄",
                                      color: "text-muted-foreground",
                                    };

                                    const displayValue = String(value)
                                      .replace(/:v\d+$/, "")
                                      .replace(/@[^:]+$/, "");

                                    return (
                                      <div
                                        key={type}
                                        className={cn(
                                          "flex items-center gap-2 px-2 py-1 rounded-md",
                                          "bg-surface-base/60 border border-border/50 text-xs",
                                        )}
                                        title={`${type}: ${value}`}
                                      >
                                        <span>{config.icon}</span>
                                        <span
                                          className=" capitalize"
                                        >
                                          {type === "schema" ? "catalog" : type}:
                                        </span>
                                        <span className={cn("font-mono", config.color)}>
                                          {displayValue}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {renderJsonDetails("Stage input", stageInput)}
                            {renderJsonDetails("Stage output", stageOutput)}
                            {(warnings.length > 0 || errors.length > 0) && (
                              <div className="grid gap-3 md:grid-cols-2 text-xs">
                                {warnings.length > 0 && (
                                  <div className="bg-amber-500/5 border border-amber-400/30 rounded-xl p-3 text-amber-200">
                                    <p className="text-xs uppercase tracking-wider text-amber-300">
                                      Warnings
                                    </p>
                                    <ul className="mt-2 space-y-1">
                                      {warnings.map((warning: string, index: number) => (
                                        <li key={`${stage}-warn-${index}`}>{warning}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {errors.length > 0 && (
                                  <div className="bg-rose-500/5 border border-rose-400/30 rounded-xl p-3 text-rose-200">
                                    <p className="text-xs uppercase tracking-wider text-rose-300">
                                      Errors
                                    </p>
                                    <ul className="mt-2 space-y-1">
                                      {errors.map((error: string, index: number) => (
                                        <li key={`${stage}-err-${index}`}>{error}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  </section>

                  <section
                    className="border border-border rounded-2xl p-5 space-y-4 bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider text-muted-foreground"
                      >
                        Execution
                      </p>
                      <span className="text-xs text-muted-foreground">
                        {traceDetail.execution_steps?.length ?? 0} steps
                      </span>
                    </div>
                    {traceDetail.execution_steps && traceDetail.execution_steps.length ? (
                      <div className="space-y-3">
                        {traceDetail.execution_steps.map((step: ExecutionStep, index: number) => (
                          <article
                            key={`${step.step_id ?? index}-${step.tool_name ?? "tool"}`}
                            className="border border-border rounded-xl p-4 space-y-3 bg-surface-elevated"
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm text-foreground font-semibold">
                                  {step.step_id || `step-${index + 1}`}
                                </p>
                                <p
                                  className="text-sm text-muted-foreground"
                                >
                                  {step.tool_name || "tool"}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span
                                  className={`px-2 py-1 rounded-full text-xs uppercase tracking-wider ${
                                    step.status === "success"
                                      ? "bg-emerald-900/40 text-emerald-200"
                                      : "bg-rose-900/40 text-rose-200"
                                  }`}
                                >
                                  {step.status}
                                </span>
                                <span
                                  className="text-sm text-muted-foreground"
                                >
                                  {formatDuration(step.duration_ms)}
                                </span>
                              </div>
                            </div>
                            {renderJsonDetails("Request summary", step.request)}
                            {renderJsonDetails("Response summary", step.response)}
                            {step.error && (
                              <details className="bg-rose-950/40 border border-rose-800 rounded-xl p-2 text-sm text-rose-200">
                                <summary className="cursor-pointer uppercase tracking-wider text-xs">
                                  Error details
                                </summary>
                                <p className="mt-2 text-sm text-rose-100">
                                  {step.error?.message ?? "Unknown error"}
                                </p>
                                {step.error?.stack && (
                                  <pre className="mt-2 max-h-40 overflow-auto text-xs text-rose-100">
                                    {step.error.stack}
                                  </pre>
                                )}
                              </details>
                            )}
                            {step.references && step.references.length ? (
                              <p className="text-sm text-muted-foreground">
                                References:{" "}
                                {step.references
                                  .map((ref: { name: string }) => ref.name)
                                  .join(", ")}
                              </p>
                            ) : null}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Tool execution trace가 없습니다.
                      </p>
                    )}
                  </section>

                  <section
                    className="border border-border rounded-2xl p-5 space-y-4 bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider text-muted-foreground"
                      >
                        Control Loop
                      </p>
                      <span className="text-xs text-muted-foreground">
                        {traceDetail.replan_events?.length ?? 0} events
                      </span>
                    </div>
                    {traceDetail.replan_events && traceDetail.replan_events.length ? (
                      <ReplanTimeline
                        traceId={traceDetail.trace_id ?? ""}
                        events={traceDetail.replan_events}
                      />
                    ) : (
                      <p className="text-xs text-muted-standard">
                        Replan 이벤트가 없습니다.
                      </p>
                    )}
                  </section>

                  <section
                    className="border rounded-2xl p-5 space-y-3 border-border bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider"
                      >
                        References
                      </p>
                      <span className="text-xs text-muted-standard">
                        {traceDetail.references?.length ?? 0} items
                      </span>
                    </div>
                    {traceDetail.references && traceDetail.references.length ? (
                      <div className="overflow-x-auto">
                        <table
                          className="min-w-full text-xs"
                        >
                          <thead>
                            <tr
                              className="text-left uppercase tracking-wider border-b text-xs border-border text-foreground"
                            >
                              <th className="px-2 py-2">Type</th>
                              <th className="px-2 py-2">Name</th>
                              <th className="px-2 py-2">Engine</th>
                              <th className="px-2 py-2">Rows</th>
                              <th className="px-2 py-2">Latency</th>
                              <th className="px-2 py-2">Detail</th>
                            </tr>
                          </thead>
                          <tbody>
                            {traceDetail.references.map((ref: ReferenceEntry, index: number) => (
                              <tr
                                key={`${ref.name}-${index}`}
                                className="border-b "
                              >
                                <td
                                  className="px-2 py-2 text-sm "
                                >
                                  {ref.ref_type}
                                </td>
                                <td className="px-2 py-2  text-foreground">
                                  {ref.name}
                                </td>
                                <td
                                  className="px-2 py-2 "
                                >
                                  {ref.engine || "unknown"}
                                </td>
                                <td
                                  className="px-2 py-2 "
                                >
                                  {ref.row_count ?? "-"}
                                </td>
                                <td
                                  className="px-2 py-2 "
                                >
                                  {ref.latency_ms ?? "-"} ms
                                </td>
                                <td className="px-2 py-2 space-y-1">
                                  {ref.statement && (
                                    <details
                                      className="border rounded-xl p-2 border-border bg-surface-base"
                                    >
                                      <summary
                                        className="text-xs uppercase tracking-wider cursor-pointer"
                                      >
                                        Statement
                                      </summary>
                                      <pre
                                        className="mt-2 text-sm overflow-x-auto"
                                      >
                                        {ref.statement}
                                      </pre>
                                    </details>
                                  )}
                                  {ref.params && (
                                    <details
                                      className="border rounded-xl p-2 border-border bg-surface-base"
                                    >
                                      <summary
                                        className="text-xs uppercase tracking-wider cursor-pointer"
                                      >
                                        Params
                                      </summary>
                                      <pre
                                        className="mt-2 text-sm overflow-x-auto"
                                      >
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
                      <p className="text-xs  text-muted-standard">
                        근거 레코드가 없습니다.
                      </p>
                    )}
                  </section>

                  <section
                    className="border rounded-2xl p-5 space-y-3 border-border bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider"
                      >
                        Answer Blocks
                      </p>
                      <span className="text-xs text-muted-standard">
                        {traceDetail.answer?.blocks?.length ?? 0} blocks
                      </span>
                    </div>
                    {traceDetail.answer?.blocks && traceDetail.answer.blocks.length > 0 ? (
                      <div className="grid gap-3 md:grid-cols-2">
                        {traceDetail.answer.blocks.map((block: AnswerBlock, index: number) => (
                          <article
                            key={`${block.type}-${index}`}
                            className="border rounded-xl p-4 space-y-2 border-border bg-surface-elevated"
                          >
                            <div
                              className="flex items-center justify-between text-sm uppercase tracking-wider"
                            >
                              <span>{block.type}</span>
                              <span>
                                {block.references?.length
                                  ? `${block.references.length} references`
                                  : "No refs"}
                              </span>
                            </div>
                            <div>
                              {block.title ? (
                                <p className="text-sm text-white font-semibold">{block.title}</p>
                              ) : (
                                <p className="text-sm  text-foreground">
                                  Untitled block
                                </p>
                              )}
                              <p
                                className="text-sm mt-1"
                              >
                                {summarizeBlockPayload(block)}
                              </p>
                            </div>
                            <details
                              className="border rounded-xl p-2 border-border bg-surface-base"
                            >
                              <summary
                                className="text-xs uppercase tracking-wider cursor-pointer"
                              >
                                View payload
                              </summary>
                              <pre
                                className="mt-2 text-xs overflow-x-auto max-h-48"
                              >
                                {JSON.stringify(block, null, 2)}
                              </pre>
                            </details>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-standard">
                        Blocks가 없습니다.
                      </p>
                    )}
                  </section>

                  <section
                    className="border rounded-2xl p-5 space-y-3 border-border bg-surface-base"
                  >
                    <p
                      className="text-xs uppercase tracking-wider"
                    >
                      UI Render Trace
                    </p>
                    {traceDetail.ui_render ? (
                      <div className="space-y-3">
                        <div
                          className="text-xs uppercase tracking-wider"
                        >
                          Rendered Blocks
                        </div>
                        <div className="grid gap-2">
                          {traceDetail.ui_render.rendered_blocks.map(
                            (block: UIRenderedBlock, index: number) => (
                              <div
                                key={`${block.block_type}-${index}`}
                                className="border rounded-xl px-3 py-2 text-sm border-border bg-surface-elevated"
                              >
                                <div className="flex items-center justify-between">
                                  <span>{block.block_type}</span>
                                  <span>{block.ok ? "ok" : "error"}</span>
                                </div>
                                <p
                                  className="text-sm "
                                >
                                  {block.component_name}
                                </p>
                                {block.error && (
                                  <p className="text-rose-300 text-sm mt-1">{block.error}</p>
                                )}
                              </div>
                            ),
                          )}
                        </div>
                        {traceDetail.ui_render.warnings.length > 0 && (
                          <ul
                            className="list-disc list-inside text-sm "
                          >
                            {traceDetail.ui_render.warnings.map((warning: string, idx: number) => (
                              <li key={idx}>{warning}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-standard">
                        UI 렌더 이벤트가 아직 없습니다.
                      </p>
                    )}
                  </section>

                  <section
                    className="border rounded-2xl p-5 space-y-3 border-border bg-surface-base"
                  >
                    <div className="flex items-center justify-between gap-4 flex-wrap">
                      <div className="flex items-center gap-2">
                        <p
                          className="text-xs uppercase tracking-wider"
                        >
                          Flow
                        </p>
                        {traceDetail.flow_spans && traceDetail.flow_spans.length > 0 && (
                          <span className="text-xs text-muted-standard">
                            {traceDetail.flow_spans.length} spans
                          </span>
                        )}
                      </div>
                      {traceDetail.flow_spans && traceDetail.flow_spans.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <div
                            className="flex gap-1 rounded-lg p-1"
                          >
                            <button
                              data-testid="flow-toggle-timeline"
                              onClick={() => {
                                setFlowViewMode("timeline");
                                setSelectedSpan(null);
                              }}
                              className={`px-3 py-1 rounded text-xs uppercase tracking-wider transition-colors ${
                                flowViewMode === "timeline" ? " text-white" : ""
                              } bg-surface-elevated text-foreground`}
                            >
                              Timeline
                            </button>
                            <button
                              data-testid="flow-toggle-graph"
                              onClick={() => {
                                setFlowViewMode("graph");
                                setSelectedSpan(null);
                              }}
                              className={`px-3 py-1 rounded text-xs uppercase tracking-wider transition-colors ${
                                flowViewMode === "graph" ? " text-white" : ""
                              } bg-surface-elevated text-foreground`}
                            >
                              Graph
                            </button>
                          </div>
                          {flowViewMode === "graph" && (
                            <label
                              className="flex items-center gap-2 px-3 py-1 text-xs rounded-lg cursor-pointer text-foreground bg-surface-elevated"
                            >
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
                              .sort((a: FlowSpan, b: FlowSpan) => a.ts_start_ms - b.ts_start_ms)
                              .map((span: FlowSpan) => {
                                const statusClass =
                                  span.status === "ok"
                                    ? "bg-emerald-900/40 text-emerald-200"
                                    : "bg-rose-900/40 text-rose-200";
                                return (
                                  <div
                                    key={span.span_id}
                                    onClick={() => setSelectedSpan(span)}
                                    className="border rounded-xl px-4 py-3 cursor-pointer transition-colors border-border bg-surface-base"
                                  >
                                    <div className="flex items-center justify-between gap-3">
                                      <div className="flex items-center gap-3 flex-1 min-w-0">
                                        <span
                                          className="text-xs font-mono truncate"
                                        >
                                          {span.name}
                                        </span>
                                        <span
                                          className={`px-2 py-1 rounded-full text-xs uppercase whitespace-nowrap ${statusClass}`}
                                        >
                                          {span.status}
                                        </span>
                                        <span
                                          className="text-sm whitespace-nowrap"
                                        >
                                          {span.kind}
                                        </span>
                                      </div>
                                      <span
                                        className="text-sm whitespace-nowrap"
                                      >
                                        {span.duration_ms}ms
                                      </span>
                                    </div>
                                    {span.summary.note && (
                                      <p
                                        className="mt-2 text-sm "
                                      >
                                        {span.summary.note}
                                      </p>
                                    )}
                                    {span.summary.error_message && (
                                      <p className="mt-2 text-sm text-rose-300">
                                        {span.summary.error_message}
                                      </p>
                                    )}
                                  </div>
                                );
                              })}
                          </div>
                        ) : (
                          <div
                            className="h-[400px] rounded-lg border border-variant bg-surface-elevated"
                          >
                            <ReactFlow
                              nodes={nodes}
                              edges={edges}
                              onNodesChange={onNodesChange}
                              onEdgesChange={onEdgesChange}
                              onNodeClick={(event, node) => {
                                setSelectedNodeId(node.id);
                                const span = traceDetail.flow_spans?.find(
                                  (s: FlowSpan) => s.span_id === node.id,
                                );
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
                      <p
                        data-testid="flow-empty-state"
                        className="text-xs "
                      >
                        Flow 데이터 없음 (구버전 trace)
                      </p>
                    )}
                  </section>

                  {selectedSpan && (
                    <section
                      className="border rounded-2xl p-5 space-y-3 border-border bg-surface-base"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p
                            className="text-xs uppercase tracking-wider"
                          >
                            Span Details
                          </p>
                          <p className="text-sm font-semibold text-white mt-1">
                            {selectedSpan.name}
                          </p>
                        </div>
                        <button
                          onClick={() => setSelectedSpan(null)}
                          className=" text-white text-sm"
                        >
                          ✕
                        </button>
                      </div>

                      <div
                        className="grid grid-cols-2 gap-3 text-xs "
                      >
                        <div>
                          <p
                            className=" uppercase tracking-wider text-xs"
                          >
                            Kind
                          </p>
                          <p className="mt-1">{selectedSpan.kind}</p>
                        </div>
                        <div>
                          <p
                            className=" uppercase tracking-wider text-xs"
                          >
                            Status
                          </p>
                          <p className="mt-1">{selectedSpan.status}</p>
                        </div>
                        <div>
                          <p
                            className=" uppercase tracking-wider text-xs"
                          >
                            Duration
                          </p>
                          <p className="mt-1">{selectedSpan.duration_ms}ms</p>
                        </div>
                        <div>
                          <p
                            className=" uppercase tracking-wider text-xs"
                          >
                            Span ID
                          </p>
                          <p className="mt-1 font-mono text-xs">{selectedSpan.span_id}</p>
                        </div>
                      </div>

                      {selectedSpan.links.plan_path && (
                        <div
                          className="border rounded-xl p-3 space-y-2 border-border bg-surface-elevated"
                        >
                          <p
                            className="text-xs uppercase tracking-wider "
                          >
                            Related Plan
                          </p>
                          {renderJsonDetails(
                            selectedSpan.links.plan_path === "plan.raw"
                              ? "Raw Plan"
                              : "Validated Plan",
                            selectedSpan.links.plan_path === "plan.raw"
                              ? traceDetail.plan_raw
                              : traceDetail.plan_validated,
                          )}
                        </div>
                      )}

                      {selectedSpan.links.tool_call_id && traceDetail.execution_steps && (
                        <div
                          className="border rounded-xl p-3 space-y-2 border-border bg-surface-elevated"
                        >
                          <p
                            className="text-xs uppercase tracking-wider "
                          >
                            Related Tool Call
                          </p>
                          {(() => {
                            const step = traceDetail.execution_steps?.find(
                              (s: ExecutionStep) => s.tool_name === selectedSpan.links.tool_call_id,
                            );
                            return step ? (
                              <div className="space-y-2">
                                {renderJsonDetails("Request", step.request)}
                                {renderJsonDetails("Response", step.response)}
                              </div>
                            ) : (
                              <p className="text-sm text-muted-standard">
                                Tool call not found
                              </p>
                            );
                          })()}
                        </div>
                      )}
                    </section>
                  )}

                  {/* Orchestration Section */}
                  {traceDetail && <OrchestrationSection stageOutput={traceDetail} />}

                  <section
                    className="border rounded-2xl p-5 space-y-3 border-border bg-surface-base"
                  >
                    <div className="flex items-center justify-between">
                      <p
                        className="text-xs uppercase tracking-wider"
                      >
                        Audit Logs
                      </p>
                      <span className="text-xs text-muted-standard">
                        {traceAuditLogs.length} events
                      </span>
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
          <div
            className="border rounded-2xl p-6 w-96 space-y-4 border-border bg-surface-base"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Compare with Trace</h3>
              <button
                onClick={() => setShowCompareModal(false)}
                className=" text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label
                  className="block text-xs font-semibold uppercase tracking-wider mb-2"
                >
                  Trace ID to Compare
                </label>
                <input
                  type="text"
                  value={compareTraceId}
                  onChange={(e) => setCompareTraceId(e.target.value)}
                  placeholder="Paste trace_id..."
                  className="w-full px-3 py-2 border rounded-lg text-sm text-white placeholder-slate-500 outline-none border-border bg-surface-base"
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
                  className="px-3 py-2 rounded-lg border text-xs uppercase tracking-wider "
                >
                  Cancel
                </button>
                <button
                  onClick={handleFetchCompareTrace}
                  disabled={compareFetching}
                  className="px-4 py-2 rounded-lg bg-emerald-600 bg-emerald-700 text-xs uppercase tracking-wider text-white opacity-50 cursor-not-allowed transition"
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

      {/* Stage Diff View */}
      {showStageDiffView && traceDetail && baselineStageTraceId && (
        <StageDiffView
          baselineTraceId={baselineStageTraceId}
          currentTraceId={traceDetail.trace_id}
          onClose={() => {
            setShowStageDiffView(false);
            setBaselineStageTraceId("");
          }}
        />
      )}

      {showAssetOverrideModal && traceDetail && (
        <AssetOverrideModal
          isOpen={showAssetOverrideModal}
          onClose={() => setShowAssetOverrideModal(false)}
          traceId={traceDetail.trace_id}
          baselineTraceId={traceDetail.trace_id}
          availableAssets={availableAssets}
          onTestRun={handleAssetOverrideRun}
        />
      )}

      <Toast
        message={statusMessage ?? ""}
        type={detailError ? "error" : "info"}
        onDismiss={() => setStatusMessage(null)}
        duration={0}
      />
    </div>
    </div>
  );
}

export default function InspectorPage() {
  return (
    <ReactFlowProvider>
      <Suspense
        fallback={
          <div className="p-4  text-muted-standard">
            Loading...
          </div>
        }
      >
        <InspectorContent />
      </Suspense>
    </ReactFlowProvider>
  );
}
