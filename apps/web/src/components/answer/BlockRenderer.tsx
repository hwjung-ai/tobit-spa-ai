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

export type AnswerBlock =
  | MarkdownBlock
  | TableBlock
  | TimeSeriesBlock
  | GraphBlock
  | ReferencesBlock;

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
}

const lineColors = ["#38bdf8", "#34d399", "#f97316", "#a855f7", "#f472b6"];

export default function BlockRenderer({ blocks }: BlockRendererProps) {
  const [fullscreenGraph, setFullscreenGraph] = useState<GraphBlock | null>(null);

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

          case "table":
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
                      </tr>
                    </thead>
                    <tbody>
                      {block.rows.map((row, rowIndex) => (
                        <tr
                          key={`${rowIndex}-${row.join("-")}`}
                          className={rowIndex % 2 === 0 ? "bg-slate-950/40" : "bg-slate-900/40"}
                        >
                          {row.map((cell, cellIndex) => (
                            <td key={`${rowIndex}-${cellIndex}`} className="px-3 py-2">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            );

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

function GraphFlowRenderer({ block }: { block: GraphBlock }) {
  const uniqueNodes = useMemo(() => {
    const seen = new Set<string>();
    return block.nodes.filter((node, idx) => {
      const idKey = node.id ?? `node-${idx}`;
      if (seen.has(idKey)) {
        return false;
      }
      seen.add(idKey);
      return true;
    });
  }, [block.nodes]);
  const edges = useMemo(
    () =>
      block.edges.map((edge, idx) => ({
        ...edge,
        id: edge.id ?? `edge-${idx}`,
      })),
    [block.edges]
  );

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={uniqueNodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        attributionPosition="bottom-left"
      >
        <Background gap={12} size={1} color="#0f172a" />
        <Controls showInteractive={false} />
      </ReactFlow>
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
