"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { PdfViewerModal } from "@/components/pdf/PdfViewerModal";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import "reactflow/dist/style.css";
import Link from "next/link";
import { type NextAction } from "../../app/ops/nextActions";
import UIPanelRenderer from "./UIPanelRenderer";
import UIScreenRenderer from "./UIScreenRenderer";
import type { UIPanelBlock } from "@/types/uiActions";
import type {
  AnswerBlock,
  ChartPoint,
  GraphBlock,
  NetworkEdge,
  NetworkBlock,
  NetworkNode,
  PathBlock,
  ReferencesBlock,
  ReferenceEntry,
  TableBlock,
  TimeSeriesSeries,
  TimeSeriesBlock,
  UIScreenBlock,
} from "./block-types";
export type {
  AnswerBlock,
  AnswerEnvelope,
  AnswerMeta,
  ChartBlock,
  ChartPoint,
  ChartSeries,
  GraphBlock,
  GraphEdge,
  GraphNode,
  MarkdownBlock,
  NetworkBlock,
  NetworkEdge,
  NetworkNode,
  NumberBlock,
  PathBlock,
  ReferenceEntry,
  ReferenceLink,
  ReferencesBlock,
  TableBlock,
  TextBlock,
  TimeSeriesBlock,
  TimeSeriesPoint,
  TimeSeriesSeries,
  UIScreenBlock,
} from "./block-types";

// ── Table download helpers ──

function downloadTableAsCSV(
  columns: string[],
  rows: Array<Array<string | number | boolean | null>>,
  title?: string
) {
  const escapeCsv = (val: string) => {
    if (val.includes(",") || val.includes('"') || val.includes("\n")) {
      return `"${val.replace(/"/g, '""')}"`;
    }
    return val;
  };
  const header = columns.map(escapeCsv).join(",");
  const body = rows.map((row) => row.map((cell) => escapeCsv(String(cell ?? ""))).join(",")).join("\n");
  const csv = `${header}\n${body}`;
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  triggerDownload(blob, `${title || "table"}.csv`);
}

function downloadTableAsJSON(
  columns: string[],
  rows: Array<Array<string | number | boolean | null>>,
  title?: string
) {
  const data = rows.map((row) => {
    const obj: Record<string, string> = {};
    columns.forEach((col, i) => {
      obj[col] = String(row[i] ?? "");
    });
    return obj;
  });
  const json = JSON.stringify({ title: title || "table", columns, data }, null, 2);
  const blob = new Blob([json], { type: "application/json;charset=utf-8;" });
  triggerDownload(blob, `${title || "table"}.json`);
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.replace(/[^a-zA-Z0-9가-힣_.-]/g, "_");
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

interface BlockRendererProps {
  blocks: AnswerBlock[];
  nextActions?: NextAction[];
  onAction?: (action: NextAction) => void;
  traceId?: string;
}

const lineColors = ["var(--chart-primary-color)", "var(--chart-success-color)", "#f97316", "#a855f7", "#f472b6"];

interface RenderedBlockTelemetry {
  block_type: string;
  component_name: string;
  ok: boolean;
  error?: string;
}

const BLOCK_COMPONENT_NAMES: Record<string, string> = {
  markdown: "MarkdownBlock",
  table: "TableBlock",
  text: "TextBlock",
  number: "NumberBlock",
  timeseries: "TimeSeriesBlock",
  chart: "ChartBlock",
  graph: "GraphFlowRenderer",
  network: "NetworkBlock",
  path: "PathBlock",
  references: "ReferencesBlock",
  ui_panel: "UIPanelRenderer",
  ui_screen: "UIScreenRenderer",
};

const normalizeApiBaseUrl = (value?: string) => value?.replace(/\/+$/, "") ?? "";

export default function BlockRenderer({ blocks, nextActions, onAction, traceId }: BlockRendererProps) {
  const router = useRouter();
  const [fullscreenGraph, setFullscreenGraph] = useState<GraphBlock | null>(null);

  // PDF viewer modal state (for references)
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("document.pdf");
  const [pdfHighlightSnippet, setPdfHighlightSnippet] = useState<string | undefined>(undefined);
  const [pdfInitialPage, setPdfInitialPage] = useState<number>(1);

  const candidateActionMap = useMemo(() => {
    const map = new Map<string, NextAction>();
    nextActions?.forEach((action) => {
      if (action.type !== "rerun" || !action.payload) {
        return;
      }
      if (action.payload.selected_ci_id) {
        map.set(action.payload.selected_ci_id, action);
      }
      if (action.payload.selected_secondary_ci_id) {
        map.set(action.payload.selected_secondary_ci_id, action);
      }
    });
    return map;
  }, [nextActions]);
  const generalActions = useMemo(() => {
    return (
      nextActions?.filter((action) => {
        if (action.type === "rerun") {
          return !action.payload?.selected_ci_id && !action.payload?.selected_secondary_ci_id;
        }
        return true;
      }) ?? []
    );
  }, [nextActions]);

  const telemetryEntriesRef = useRef<RenderedBlockTelemetry[]>([]);
  const lastPayloadKeyRef = useRef<string>("");

  telemetryEntriesRef.current = [];
  useEffect(() => {
    if (!traceId) {
      lastPayloadKeyRef.current = "";
      return;
    }
    if (!blocks || blocks.length === 0) {
      lastPayloadKeyRef.current = "";
      return;
    }
    const payload = {
      rendered_blocks: telemetryEntriesRef.current,
      warnings: [],
    };
    const payloadKey = JSON.stringify(payload);
    if (lastPayloadKeyRef.current === payloadKey) {
      return;
    }
    lastPayloadKeyRef.current = payloadKey;

    const baseUrl = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
    const endpoint = baseUrl
      ? `${baseUrl}/inspector/traces/${encodeURIComponent(traceId)}/ui-render`
      : `/inspector/traces/${encodeURIComponent(traceId)}/ui-render`;

    void (async () => {
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          console.warn("UI render telemetry failed", response.status, response.statusText);
        }
      } catch (fetchError) {
        console.warn("UI render telemetry request failed", fetchError);
      }
    })();
  }, [traceId, blocks]);
  if (!blocks || blocks.length === 0) {
    return (
      <div className="answer-block">
        <p className="text-sm text-muted-foreground">No blocks to display yet.</p>
      </div>
    );
  }

  // Separate reference blocks from answer blocks
  const referenceBlocks = blocks.filter(block => block.type === "references");
  const answerBlocks = blocks.filter(block => block.type !== "references") as AnswerBlock[];

  return (
    <>
    <div className="space-y-6">
      {/* Render reference blocks first (at the top) */}
      {referenceBlocks.map((block, index) => {
        const title = block.title ? (
          <p className="mb-3 text-label">
            {block.title}
          </p>
        ) : null;

        return (
          <section
            key={`reference-${index}`}
            className="answer-section"
          >
            {title}
            <div className="mt-4 space-y-3">
              {block.items.map((reference, refIndex) => {
                const cardClass = `block rounded-2xl border border-variant bg-surface-overlay p-4 text-sm text-muted-foreground transition ${
                  reference.url
                    ? "cursor-pointer hover:border-sky-500 hover:text-foreground"
                    : "hover:border-variant"
                }`;
                const cardContent = (
                  <>
                    <div className="flex items-center justify-between">
                      <p className="font-semibold">{reference.title}</p>
                      <span className="text-label-sm">
                        {reference.kind ?? "reference"}
                      </span>
                    </div>
                    {reference.snippet ? (
                      <p className="mt-1 text-xs text-muted-foreground">{reference.snippet}</p>
                    ) : null}
                    {reference.url && reference.kind === "document" ? (
                      <p className="mt-1 text-tiny uppercase tracking-wider text-sky-400 flex items-center gap-1">
                        📄 View document
                      </p>
                    ) : reference.url ? (
                      <p className="mt-1 text-tiny uppercase tracking-wider text-sky-400 flex items-center gap-1">
                        🔗 View source
                      </p>
                    ) : null}
                    {renderReferencePayload(reference.payload) ? (
                      <pre className="answer-code">
                        {renderReferencePayload(reference.payload)}
                      </pre>
                    ) : null}
                  </>
                );

                // Handle document URLs - use button with authenticated fetch (same as docs page)
                if (reference.url && reference.kind === "document") {
                  const handleDocumentClick = async () => {
                    try {
                      // Use fetchWithAuth to get the PDF with auth headers
                      const { fetchWithAuth } = await import("@/lib/apiClient");
                      const response = await fetchWithAuth(reference.url);

                      // Get PDF blob
                      const blob = await response.blob();

                      // Debug: Log snippet value
                      console.log('[OPS Reference] snippet:', reference.snippet);
                      console.log('[OPS Reference] full reference:', reference);

                      // Open PDF in modal (same as docs page)
                      setPdfBlob(blob);
                      setPdfFilename(reference.title || "document.pdf");
                      setPdfInitialPage(1);
                      setPdfHighlightSnippet(reference.snippet || undefined);
                      setPdfViewerOpen(true);
                    } catch (error) {
                      console.error("Error opening document:", error);
                    }
                  };

                  return (
                    <button
                      key={`${reference.title}-${refIndex}`}
                      type="button"
                      onClick={handleDocumentClick}
                      className={`${cardClass} text-left w-full pointer-events-auto !cursor-pointer`}
                      data-testid="reference-item"
                    >
                      {cardContent}
                    </button>
                  );
                }

                // Use <a> for external URLs
                if (reference.url) {
                  return (
                    <a
                      key={`${reference.title}-${refIndex}`}
                      href={reference.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cardClass}
                    >
                      {cardContent}
                    </a>
                  );
                }

                // No URL - static card
                return (
                  <div
                    key={`${reference.title}-${refIndex}`}
                    className={cardClass}
                  >
                    {cardContent}
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}

      {/* Render answer blocks after references */}
      {answerBlocks.map((block, index) => {
        const title = block.title ? (
          <p className="mb-3 text-label">
            {block.title}
          </p>
        ) : null;

        const baseKey = `${block.type}-${block.id ?? index}`;
        const componentName = BLOCK_COMPONENT_NAMES[block.type] ?? "BlockRenderer";
        const renderBlockContent = () => {
          switch (block.type) {
          case "markdown":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <div className="prose max-w-none prose-invert answer-prose">
                  <ReactMarkdown>{block.content}</ReactMarkdown>
                </div>
              </section>
            );

          case "text":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <p className="text-sm text-foreground">{block.text}</p>
              </section>
            );

          case "number":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <div className="mt-2 flex items-baseline gap-3">
                  <p className="text-label">
                    {block.label}
                  </p>
                  <p className="text-3xl font-semibold text-foreground">{block.value}</p>
                </div>
              </section>
            );

          case "table": {
            const tableBlock = block as TableBlock & { content?: { headers?: string[]; rows?: (string | number | boolean | null)[][] } };
            const columns = tableBlock.columns ?? tableBlock.content?.headers ?? [];
            const rows = tableBlock.rows ?? tableBlock.content?.rows ?? [];
            const isCandidateTable = (block.id ?? "").startsWith("ci-candidates");
            const ciIdIndex = columns.findIndex((column) => column === "ci_id");
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                <div className="flex items-center justify-between">
                  {title}
                  {rows.length > 0 && (
                    <div className="flex gap-1">
                      <button
                        type="button"
                        aria-label="Download as CSV"
                        className="answer-button"
                        onClick={() => downloadTableAsCSV(columns, rows, block.title)}
                      >
                        CSV
                      </button>
                      <button
                        type="button"
                        aria-label="Download as JSON"
                        className="answer-button"
                        onClick={() => downloadTableAsJSON(columns, rows, block.title)}
                      >
                        JSON
                      </button>
                    </div>
                  )}
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="answer-table">
                    <thead>
                      <tr>
                        {columns.map((column) => (
                          <th
                            key={column}
                            scope="col"
                            className="answer-table-header"
                          >
                            {column}
                          </th>
                        ))}
                        {isCandidateTable ? (
                          <th scope="col" className="answer-table-header">
                            Action
                          </th>
                        ) : null}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, rowIndex) => {
                        const candidateId = ciIdIndex >= 0 ? row[ciIdIndex] : undefined;
                        const candidateKey = candidateId != null ? String(candidateId) : undefined;
                        const candidateAction =
                          candidateKey && candidateActionMap.has(candidateKey)
                            ? candidateActionMap.get(candidateKey)
                            : undefined;
                        return (
                          <tr
                            key={`${rowIndex}-${row.join("-")}`}
                            className="answer-table-row"
                          >
                            {row.map((cell, cellIndex) => (
                              <td key={`${rowIndex}-${cellIndex}`} className="px-3 py-2">
                                {cell}
                              </td>
                            ))}
                            {isCandidateTable ? (
                              <td className="px-3 py-2">
                                {candidateAction ? (
                                  <button
                                    type="button"
                                    className="answer-button"
                                    disabled={!onAction}
                                    onClick={() => onAction?.(candidateAction)}
                                  >
                                    {candidateAction.label}
                                  </button>
                                ) : (
                                  <span className="text-label-sm">
                                    선택
                                  </span>
                                )}
                              </td>
                            ) : null}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            );
          }

          case "chart": {
            const [series] = block.series ?? [];
            const points = series?.points ?? [];
            let chartContent: React.ReactNode;
            try {
              const normalizedPoints: ChartPoint[] = points
                .map(([timestamp, value]) => ({
                  timestamp: String(timestamp),
                  value: Number(value),
                }))
                .filter((point) => point.timestamp && !Number.isNaN(point.value));
              if (normalizedPoints.length <= 1) {
                throw new Error("Not enough points for chart");
              }
              normalizedPoints.sort(
                (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
              );
              const width = 600;
              const height = 220;
              const padding = 30;
              const values = normalizedPoints.map((point) => point.value);
              const minValue = Math.min(...values);
              const maxValue = Math.max(...values);
              const minTime = new Date(normalizedPoints[0].timestamp).getTime();
              const maxTime = new Date(normalizedPoints[normalizedPoints.length - 1].timestamp).getTime();
              const deltaTime = Math.max(maxTime - minTime, 1);
              const deltaValue = Math.max(maxValue - minValue, 1);
              const polylinePoints = normalizedPoints
                .map((point) => {
                  const x =
                    padding +
                    ((new Date(point.timestamp).getTime() - minTime) / deltaTime) *
                    (width - padding * 2);
                  const y =
                    height -
                    padding -
                    ((point.value - minValue) / deltaValue) * (height - padding * 2);
                  return `${x},${y}`;
                })
                .join(" ");
              chartContent = (
                <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label={block.title || "Chart"}>
                  <polyline
                    fill="none"
                    stroke="var(--chart-primary-color)"
                    strokeWidth="3"
                    points={polylinePoints}
                    strokeLinecap="round"
                  />
                  <line
                    x1={padding}
                    y1={height - padding}
                    x2={width - padding}
                    y2={height - padding}
                    stroke="var(--chart-tooltip-bg)"
                  />
                  <line
                    x1={padding}
                    y1={padding}
                    x2={padding}
                    y2={height - padding}
                    stroke="var(--chart-tooltip-bg)"
                  />
                  {normalizedPoints.map((point, idx) => {
                    const x =
                      padding +
                      ((new Date(point.timestamp).getTime() - minTime) / deltaTime) *
                      (width - padding * 2);
                    const y =
                      height -
                      padding -
                      ((point.value - minValue) / deltaValue) * (height - padding * 2);
                    return (
                      <circle
                        key={`${point.timestamp}-${idx}`}
                        cx={x}
                        cy={y}
                        r={3}
                        fill="var(--chart-primary-color)"
                      />
                    );
                  })}
                </svg>
              );
            } catch {
              chartContent = (
                <div className="answer-empty">
                  Chart rendering not enabled yet; see the table block below.
                </div>
              );
            }
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                {chartContent}
              </section>
            );
          }

          case "timeseries": {
            const chartData = prepareChartData(block.series);
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <div className="mt-4 h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid stroke="var(--chart-grid-color)" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="timestamp"
                        tick={{ fill: "var(--chart-text-color)", fontSize: 12 }}
                        tickFormatter={(value) => formatTimestampLabel(value)}
                      />
                      <YAxis
                        tick={{ fill: "var(--chart-text-color)", fontSize: 12 }}
                        stroke="var(--chart-tooltip-bg)"
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: "var(--chart-tooltip-bg)", borderColor: "var(--chart-tooltip-border)" }}
                        labelFormatter={(value) => `Time: ${value}`}
                      />
                      {block.series.map((series, seriesIndex) => (
                        <Line
                          key={series.name ?? `series-${seriesIndex}`}
                          type="monotone"
                          dataKey={seriesKey(series, seriesIndex)}
                          stroke={lineColors[seriesIndex % lineColors.length]}
                          strokeWidth={3}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>
            );
          }

          case "graph":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">Dependency graph (up to 3 levels)</p>
                  <button
                    type="button"
                    className="answer-button"
                    onClick={() => setFullscreenGraph(block)}
                  >
                    전체 보기
                  </button>
                </div>
                <div className="mt-3 h-64 answer-code">
                  <GraphFlowRenderer block={block} />
                </div>
                {fullscreenGraph ? (
                  <GraphFullscreenOverlay
                    block={fullscreenGraph}
                    onClose={() => setFullscreenGraph(null)}
                  />
                ) : null}
              </section>
            );

          case "network":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <div className="mt-2 text-sm text-muted-foreground">
                  Nodes: {block.nodes.length} · Edges: {block.edges.length}
                  {block.meta?.truncated ? " · truncated" : ""}
                </div>
                {block.nodes.length > 0 ? renderNodeTable(block.nodes) : null}
              </section>
            );

          case "path":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
              >
                {title}
                <p className="mt-2 text-sm text-muted-foreground">Hops: {block.hop_count}</p>
                {block.nodes.length > 0 ? renderNodeTable(block.nodes, "Path nodes") : null}
                {block.edges.length > 0 ? renderEdgeTable(block.edges) : null}
              </section>
            );

          case "references":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="answer-section"
                data-testid="references-block"
              >
                {title}
                <div className="mt-4 space-y-3">
                  {block.items.map((reference, refIndex) => {
                    const cardClass = `rounded-2xl border border-variant bg-surface-overlay p-4 text-sm text-muted-foreground transition ${
                      reference.url
                        ? "cursor-pointer hover:border-sky-500 hover:text-foreground"
                        : "hover:border-variant"
                    }`;

                    console.log('[BlockRenderer] Rendering reference:', reference.title, 'URL:', reference.url);
                    const cardContent = (
                      <>
                        <div className="flex items-center justify-between">
                          <p className="font-semibold">{reference.title}</p>
                          <span className="text-label-sm">
                            {reference.kind ?? "reference"}
                          </span>
                        </div>
                        {reference.snippet ? (
                          <p className="mt-1 text-xs text-muted-foreground">{reference.snippet}</p>
                        ) : null}
                        {reference.url && reference.kind === "document" ? (
                          <p className="mt-1 text-tiny uppercase tracking-wider text-sky-400 flex items-center gap-1">
                            📄 View document
                          </p>
                        ) : reference.url ? (
                          <p className="mt-1 text-tiny uppercase tracking-wider text-sky-400 flex items-center gap-1">
                            🔗 View source
                          </p>
                        ) : null}
                        {renderReferencePayload(reference.payload) ? (
                          <pre className="answer-code">
                            {renderReferencePayload(reference.payload)}
                          </pre>
                        ) : null}
                      </>
                    );

                    // Handle document URLs - use button with authenticated fetch
                    if (reference.url && reference.kind === "document") {
                      console.log('[Reference] Document URL:', reference.url);

                      const handleDocumentClick = async () => {
                        try {
                          // Use fetchWithAuth to get the PDF with auth headers
                          const { fetchWithAuth } = await import("@/lib/apiClient");
                          const response = await fetchWithAuth(reference.url);

                          // Get PDF blob
                          const blob = await response.blob();

                          // Open PDF in modal (same as docs page)
                          setPdfBlob(blob);
                          setPdfFilename(reference.title || "document.pdf");
                          setPdfInitialPage(1);
                          setPdfHighlightSnippet(reference.snippet || undefined);
                          setPdfViewerOpen(true);
                        } catch (error) {
                          console.error('Error opening document:', error);
                        }
                      };

                      return (
                        <button
                          key={`${reference.title}-${refIndex}`}
                          type="button"
                          onClick={handleDocumentClick}
                          className={`${cardClass} text-left w-full pointer-events-auto !cursor-pointer`}
                          data-testid="reference-item"
                        >
                          {cardContent}
                        </button>
                      );
                    }

                    // Use <a> for external URLs
                    if (reference.url) {
                      return (
                        <a
                          key={`${reference.title}-${refIndex}`}
                          href={reference.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={cardClass}
                        >
                          {cardContent}
                        </a>
                      );
                    }

                    // No URL - static card
                    return (
                      <div
                        key={`${reference.title}-${refIndex}`}
                        className={cardClass}
                      >
                        {cardContent}
                      </div>
                    );
                  })}
                </div>
              </section>
            );

          case "ui_panel":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl"
              >
                <UIPanelRenderer
                  block={block as UIPanelBlock}
                  traceId={traceId}
                  onResult={() => {
                    // Optional: handle result blocks
                    // Could append to current view or replace
                  }}
                />
              </section>
            );

          case "ui_screen": {
            const screenBlock = block as UIScreenBlock;
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl"
              >
                <UIScreenRenderer
                  block={screenBlock}
                  traceId={traceId}
                  onResult={() => {
                    // Optional: handle result blocks from screen actions
                  }}
                />
              </section>
            );
          }

          default:
            const _exhaustiveCheck: never = block as never;
            return _exhaustiveCheck;
          }
        };
        let blockElement: ReactNode;
        let ok = true;
        let errorMessage: string | undefined;
        try {
          blockElement = renderBlockContent();
        } catch (error) {
          ok = false;
          errorMessage =
            error instanceof Error ? error.message : String(error ?? "unknown error");
          blockElement = (
            <section
              key={baseKey}
              className="answer-section"
            >
              {title}
              <p className="text-sm text-rose-300">렌더링 오류: {errorMessage}</p>
            </section>
          );
        }
        telemetryEntriesRef.current.push({
          block_type: block.type,
          component_name: componentName,
          ok,
          ...(errorMessage ? { error: errorMessage } : {}),
        });
        return blockElement;
      })}
      {generalActions.length ? (
        <section className="answer-section">
          <p className="text-label">Next actions</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {generalActions.map((action, index) => (
              <button
                key={`${action.type}-${action.label}-${index}`}
                type="button"
                className="answer-button"
                disabled={!onAction}
                onClick={() => onAction?.(action)}
              >
                {action.label}
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </div>

    {/* PDF Viewer Modal for references */}
    <PdfViewerModal
      isOpen={pdfViewerOpen}
      onClose={() => {
        setPdfViewerOpen(false);
        setPdfBlob(null);
        setPdfHighlightSnippet(undefined);
      }}
      pdfBlob={pdfBlob}
      filename={pdfFilename}
      initialPage={pdfInitialPage}
      highlightSnippet={pdfHighlightSnippet}
    />
    </>
  );
}

function seriesKey(series: TimeSeriesSeries, index: number) {
  return series.name ? `series-${series.name}` : `series-${index}`;
}

function formatTimestampLabel(value: string) {
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return `${date.getHours().toString().padStart(2, "0")}:${date
      .getMinutes()
      .toString()
      .padStart(2, "0")}`;
  } catch {
    return value;
  }
}

function prepareChartData(series: TimeSeriesSeries[]) {
  const dataMap = new Map<string, Record<string, number | string>>();

  series.forEach((currentSeries, currentIndex) => {
    const key = seriesKey(currentSeries, currentIndex);
    currentSeries.data.forEach((point) => {
      const entry =
        dataMap.get(point.timestamp) ?? { timestamp: point.timestamp };
      entry[key] = point.value;
      dataMap.set(point.timestamp, entry);
    });
  });

  return Array.from(dataMap.values()).sort((a, b) => {
    const left = new Date(a.timestamp).getTime();
    const right = new Date(b.timestamp).getTime();
    if (Number.isNaN(left) || Number.isNaN(right)) {
      const leftStr = String(a.timestamp);
      const rightStr = String(b.timestamp);
      return leftStr.localeCompare(rightStr);
    }
    return left - right;
  });
}

import Neo4jGraphFlow, {
  type Neo4jFlowEdge,
  type Neo4jFlowNode,
} from "../admin/Neo4jGraphFlow";

function GraphFlowRenderer({ block }: { block: GraphBlock }) {
  const [highlightNodeIds, setHighlightNodeIds] = useState<Set<string>>(new Set());
  const [highlightEdgeIds, setHighlightEdgeIds] = useState<Set<string>>(new Set());

  const nodes: Neo4jFlowNode[] = useMemo(
    () =>
      block.nodes.map((node) => ({
        id: node.id,
        position: node.position,
        data: { label: node.data.label },
        type: node.type,
      })),
    [block.nodes]
  );

  const edges: Neo4jFlowEdge[] = useMemo(
    () =>
      block.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
      })),
    [block.edges]
  );

  const handleNodeClick = (node: Neo4jFlowNode) => {
    setHighlightNodeIds(new Set([node.id]));
    const connectedEdges = edges
      .filter((edge) => edge.source === node.id || edge.target === node.id)
      .map((edge) => edge.id);
    setHighlightEdgeIds(new Set(connectedEdges));
  };

  return (
    <div className="h-full w-full">
      <Neo4jGraphFlow
        nodes={nodes}
        edges={edges}
        highlightNodeIds={highlightNodeIds}
        highlightEdgeIds={highlightEdgeIds}
        onNodeClick={handleNodeClick}
      />
    </div>
  );
}

function GraphFullscreenOverlay({ block, onClose }: { block: GraphBlock; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-6">
      <div className="flex h-full w-full flex-col overflow-hidden answer-block shadow-2xl">
        <div className="flex items-center justify-between border-b px-5 py-3 answer-divider">
          <div>
            <p className="text-label">
              Graph overview
            </p>
            <p className="text-sm text-muted-foreground">
              {block.nodes.length} nodes · {block.edges.length} relations
            </p>
          </div>
          <button
            type="button"
            className="answer-button"
            onClick={onClose}
          >
            닫기
          </button>
        </div>
        <div className="flex-1">
          <GraphFlowRenderer block={block} />
        </div>
      </div>
    </div>
  );
}

function renderNodeTable(nodes: NetworkNode[], heading = "Nodes") {
  const unique = Array.from(
    new Map(nodes.map((node) => [node.id, node])).values()
  );
  return (
    <div className="mt-3 overflow-x-auto answer-code">
      <p className="text-label">{heading}</p>
      <table className="answer-table">
        <thead>
          <tr>
            <th scope="col" className="px-2 py-1 text-muted-foreground">ID</th>
            <th scope="col" className="px-2 py-1 text-muted-foreground">Type</th>
            <th scope="col" className="px-2 py-1 text-muted-foreground">Subtype</th>
          </tr>
        </thead>
        <tbody>
          {unique.map((node) => (
            <tr key={node.id} className="answer-divider">
              <td className="px-2 py-1">{node.label ?? node.id}</td>
              <td className="px-2 py-1">{node.ci_type ?? "-"}</td>
              <td className="px-2 py-1">{node.ci_subtype ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderEdgeTable(edges: NetworkEdge[]) {
  return (
    <div className="mt-3 overflow-x-auto answer-code">
      <p className="text-label">Edges</p>
      <table className="answer-table">
        <thead>
          <tr>
            <th scope="col" className="px-2 py-1 text-muted-foreground">Source</th>
            <th scope="col" className="px-2 py-1 text-muted-foreground">Target</th>
            <th scope="col" className="px-2 py-1 text-muted-foreground">Type</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((edge, index) => (
            <tr key={`${edge.source}-${edge.target}-${index}`} className="answer-divider">
              <td className="px-2 py-1">{edge.source ?? "-"}</td>
              <td className="px-2 py-1">{edge.target ?? "-"}</td>
              <td className="px-2 py-1">{edge.type ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderReferencePayload(payload: unknown) {
  if (!payload) {
    return null;
  }

  if (typeof payload === "string") {
    return payload;
  }

  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}
