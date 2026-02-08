import type { UIPanelBlock } from "@/types/uiActions";

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
  payload_summary?: string | null;
  references?: ReferenceEntry[];
  items?: ReferenceLink[];
  id?: BlockId;
}

export interface ReferenceEntry {
  ref_type: string;
  name: string;
  engine?: string | null;
  statement?: string | null;
  params?: Record<string, unknown> | null;
  row_count?: number | null;
  latency_ms?: number | null;
  source_id?: string | null;
}

export interface UIScreenBlock {
  type: "ui_screen";
  screen_id: string;
  params?: Record<string, unknown>;
  bindings?: Record<string, string>;
  id?: BlockId;
  title?: string;
}

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
  | PathBlock
  | UIPanelBlock
  | UIScreenBlock
  & { [key: string]: unknown }
  & { references?: ReferenceEntry[]; payload_summary?: string | null };

export interface AnswerEnvelope {
  meta: AnswerMeta;
  blocks: AnswerBlock[];
}

export interface AnswerMeta {
  route: string;
  route_reason: string;
  timing_ms: number;
  summary?: string;
  used_tools?: string[];
  fallback?: boolean;
  error?: string;
  trace_id?: string;
}
