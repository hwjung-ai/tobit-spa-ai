"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { type NextAction } from "../../app/ops/nextActions";

export type AnswerBlock =
  | MarkdownBlock
  | TableBlock
  | TimeSeriesBlock
  | ChartBlock
  | GraphBlock
  | ReferencesBlock
  | TextBlock
  | NumberBlock
  | NetworkBlock
  | PathBlock;

export interface AnswerEnvelope {
  meta: AnswerMeta;
  blocks: AnswerBlock[];
}

export interface AnswerMeta {
  route: string;
  route_reason: string;
  timing_ms: number;
  summary?: string;
}

type BlockId = string;

export interface MarkdownBlock {
  type: "markdown";
  content: string;
  title?: string;
  id?: BlockId;
}

export interface TableBlock {
  type: "table";
  title?: string;
  columns: string[];
  rows: string[][];
  id?: BlockId;
}

export interface TextBlock {
  type: "text";
  title?: string;
  text: string;
  id?: BlockId;
}

export interface NumberBlock {
  type: "number";
  title?: string;
  label: string;
  value: number;
  id?: BlockId;
}

export interface NetworkNode {
  id: string;
  label?: string;
  ci_type?: string;
  ci_subtype?: string;
}

export interface NetworkEdge {
  source?: string;
  target?: string;
  type?: string;
}

export interface NetworkBlock {
  type: "network";
  title?: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  meta: { truncated?: boolean };
  id?: BlockId;
}

export interface PathBlock {
  type: "path";
  title?: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  hop_count: number;
  meta: { truncated?: boolean };
  id?: BlockId;
}
export interface TimeSeriesSeries {
  name?: string;
  data: TimeSeriesPoint[];
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface TimeSeriesBlock {
  type: "timeseries";
  title?: string;
  series: TimeSeriesSeries[];
  id?: BlockId;
}

export interface ChartPoint {
  timestamp: string;
  value: number;
}

export interface ChartSeries {
  name?: string;
  points: [string, number][];
}

export interface ChartBlock {
  type: "chart";
  title?: string;
  chart_type: "line";
  x: string;
  series: ChartSeries[];
  meta: {
    ci_id?: string;
    metric_name: string;
    time_range: string;
  };
  id?: BlockId;
}

export interface GraphNode {
  id: string;
  data: { label: string };
  position: { x: number; y: number };
  type?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface GraphBlock {
  type: "graph";
  title?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  id?: BlockId;
}

export interface ReferenceLink {
  title: string;
  url?: string;
  snippet?: string;
  payload?: unknown;
  kind?: string;
}

export interface ReferencesBlock {
  type: "references";
  title?: string;
  items: ReferenceLink[];
  id?: BlockId;
}

interface BlockRendererProps {
  blocks: AnswerBlock[];
  nextActions?: NextAction[];
  onAction?: (action: NextAction) => void;
}

const lineColors = ["#38bdf8", "#34d399", "#f97316", "#a855f7", "#f472b6"];

export default function BlockRenderer({ blocks, nextActions, onAction }: BlockRendererProps) {
  const [fullscreenGraph, setFullscreenGraph] = useState<GraphBlock | null>(null);
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

  if (!blocks || blocks.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <p className="text-sm text-slate-400">No blocks to display yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {blocks.map((block, index) => {
        const title = block.title ? (
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
            {block.title}
          </p>
        ) : null;

        switch (block.type) {
          case "markdown":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="prose max-w-none prose-invert text-slate-100">
                  <ReactMarkdown>{block.content}</ReactMarkdown>
                </div>
              </section>
            );

          case "text":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <p className="text-sm text-slate-100">{block.text}</p>
              </section>
            );

          case "number":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="mt-2 flex items-baseline gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                    {block.label}
                  </p>
                  <p className="text-3xl font-semibold text-white">{block.value}</p>
                </div>
              </section>
            );

          case "table": {
            const isCandidateTable = (block.id ?? "").startsWith("ci-candidates");
            const ciIdIndex = block.columns.findIndex((column) => column === "ci_id");
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-sm text-slate-200">
                    <thead>
                      <tr>
                        {block.columns.map((column) => (
                          <th
                            key={column}
                            className="border-b border-slate-800 px-3 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400"
                          >
                            {column}
                          </th>
                        ))}
                        {isCandidateTable ? (
                          <th className="border-b border-slate-800 px-3 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                            Action
                          </th>
                        ) : null}
                      </tr>
                    </thead>
                    <tbody>
                      {block.rows.map((row, rowIndex) => {
                        const candidateId = ciIdIndex >= 0 ? row[ciIdIndex] : undefined;
                        const candidateAction =
                          candidateId && candidateActionMap.has(candidateId)
                            ? candidateActionMap.get(candidateId)
                            : undefined;
                        return (
                          <tr
                            key={`${rowIndex}-${row.join("-")}`}
                            className={rowIndex % 2 === 0 ? "bg-slate-950/40" : "bg-slate-900/40"}
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
                                    className="rounded-full border border-slate-700 px-2 py-1 text-[10px] uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-40"
                                    disabled={!onAction}
                                    onClick={() => onAction?.(candidateAction)}
                                  >
                                    {candidateAction.label}
                                  </button>
                                ) : (
                                  <span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
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
                <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
                  <polyline
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="3"
                    points={polylinePoints}
                    strokeLinecap="round"
                  />
                  <line
                    x1={padding}
                    y1={height - padding}
                    x2={width - padding}
                    y2={height - padding}
                    stroke="#0f172a"
                  />
                  <line
                    x1={padding}
                    y1={padding}
                    x2={padding}
                    y2={height - padding}
                    stroke="#0f172a"
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
                        fill="#38bdf8"
                      />
                    );
                  })}
                </svg>
              );
            } catch (error) {
              chartContent = (
                <div className="mt-4 rounded-2xl border border-dashed border-slate-700/80 bg-slate-950/40 p-4 text-sm text-slate-400">
                  Chart rendering not enabled yet; see the table block below.
                </div>
              );
            }
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
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
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="mt-4 h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="timestamp"
                        tick={{ fill: "#94a3b8", fontSize: 12 }}
                        tickFormatter={(value) => formatTimestampLabel(value)}
                      />
                      <YAxis
                        tick={{ fill: "#94a3b8", fontSize: 12 }}
                        stroke="#0f172a"
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }}
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
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="flex items-center justify-between">
                  <p className="text-sm text-slate-400">Dependency graph (up to 3 levels)</p>
                  <button
                    type="button"
                    className="rounded-full border border-slate-700 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-400 transition hover:border-slate-500 hover:text-white"
                    onClick={() => setFullscreenGraph(block)}
                  >
                    전체 보기
                  </button>
                </div>
                <div className="mt-3 h-64 rounded-2xl border border-slate-800 bg-slate-950 shadow-inner">
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
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="mt-2 text-sm text-slate-300">
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
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <p className="mt-2 text-sm text-slate-400">Hops: {block.hop_count}</p>
                {block.nodes.length > 0 ? renderNodeTable(block.nodes, "Path nodes") : null}
                {block.edges.length > 0 ? renderEdgeTable(block.edges) : null}
              </section>
            );

          case "references":
            return (
              <section
                key={`${block.type}-${block.id ?? index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                {title}
                <div className="mt-4 space-y-3">
                  {block.items.map((reference, refIndex) => (
                    <div
                      key={`${reference.title}-${refIndex}`}
                      className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-200 transition hover:border-sky-500 hover:text-white"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-semibold">{reference.title}</p>
                        <span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                          {reference.kind ?? "reference"}
                        </span>
                      </div>
                      {reference.snippet ? (
                        <p className="mt-1 text-xs text-slate-400">{reference.snippet}</p>
                      ) : null}
                      {reference.url ? (
                        <p className="mt-1 text-[10px] uppercase tracking-[0.3em] text-slate-500">
                          {reference.url}
                        </p>
                      ) : null}
                      {renderReferencePayload(reference.payload) ? (
                        <pre className="mt-3 max-h-40 overflow-auto rounded-xl bg-slate-950/80 px-3 py-2 text-[11px] text-slate-100">
                          {renderReferencePayload(reference.payload)}
                        </pre>
                      ) : null}
                    </div>
                  ))}
                </div>
              </section>
            );

          default:
            return (
              <section
                key={`unknown-${index}`}
                className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5"
              >
                <p className="text-sm text-slate-400">Unsupported block type.</p>
              </section>
            );
        }
      })}
      {generalActions.length ? (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 px-5 py-4">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Next actions</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {generalActions.map((action, index) => (
              <button
                key={`${action.type}-${action.label}-${index}`}
                type="button"
                className="rounded-full border border-slate-700 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-40"
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
      return a.timestamp.localeCompare(b.timestamp);
    }
    return left - right;
  });
}

import Neo4jGraphFlow, {
  type Neo4jFlowEdge,
  type Neo4jFlowNode,
} from "../data/Neo4jGraphFlow";

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
      <div className="flex h-full w-full flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
              Graph overview
            </p>
            <p className="text-sm text-slate-200">
              {block.nodes.length} nodes · {block.edges.length} relations
            </p>
          </div>
          <button
            type="button"
            className="rounded-full border border-slate-700 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-400 transition hover:border-slate-500 hover:text-white"
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
    <div className="mt-3 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/30 p-3">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{heading}</p>
      <table className="min-w-full text-left text-[11px] text-slate-200">
        <thead>
          <tr>
            <th className="px-2 py-1 text-slate-500">ID</th>
            <th className="px-2 py-1 text-slate-500">Type</th>
            <th className="px-2 py-1 text-slate-500">Subtype</th>
          </tr>
        </thead>
        <tbody>
          {unique.map((node) => (
            <tr key={node.id} className="border-t border-slate-900">
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
    <div className="mt-3 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/30 p-3">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Edges</p>
      <table className="min-w-full text-left text-[11px] text-slate-200">
        <thead>
          <tr>
            <th className="px-2 py-1 text-slate-500">Source</th>
            <th className="px-2 py-1 text-slate-500">Target</th>
            <th className="px-2 py-1 text-slate-500">Type</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((edge, index) => (
            <tr key={`${edge.source}-${edge.target}-${index}`} className="border-t border-slate-900">
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
