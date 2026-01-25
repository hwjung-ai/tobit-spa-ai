"use client";

import type React from "react";
import { useEffect, useMemo, useState } from "react";
import BuilderShell from "../../../components/builder/BuilderShell";
import Neo4jGraphFlow, {
  type Neo4jFlowEdge,
  type Neo4jFlowNode,
} from "../../../components/admin/Neo4jGraphFlow";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, RowClickedEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

ModuleRegistry.registerModules([AllCommunityModule]);

type GridRow = Record<string, unknown>;

type PostgresTable = { schema: string; table: string };

type RedisKeyResult = {
  key: string;
  type: string;
  ttl: number | null;
  value: unknown;
};

const MAX_ROWS = 200;
const MAX_GRAPH_NODES = 50;
const MAX_GRAPH_EDGES = 80;
const NEO4J_ROW_INDEX_KEY = "__neo4j_row_index";

type RowGraphRef = {
  nodeIds: string[];
  edgeIds: string[];
};

type NormalizedResult = {
  graphNodes: Neo4jFlowNode[];
  graphEdges: Neo4jFlowEdge[];
  rowGraphRefs: RowGraphRef[];
  rows: GridRow[];
  scalar?: string | number | boolean;
  warnings: string[];
  truncated: { nodes: boolean; edges: boolean };
};

type Neo4jSerializedNode = {
  __neo4j_type: "node";
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
};

type Neo4jSerializedRelationship = {
  __neo4j_type: "relationship";
  id: string;
  type: string;
  start: string;
  end: string;
  properties: Record<string, unknown>;
};

const isNeo4jNode = (value: unknown): value is Neo4jSerializedNode =>
  Boolean(
    value &&
    typeof value === "object" &&
    "__neo4j_type" in value &&
    (value as Record<string, unknown>).__neo4j_type === "node"
  );

const isNeo4jRelationship = (value: unknown): value is Neo4jSerializedRelationship =>
  Boolean(
    value &&
    typeof value === "object" &&
    "__neo4j_type" in value &&
    (value as Record<string, unknown>).__neo4j_type === "relationship"
  );

const getNodeDisplayName = (node: Neo4jSerializedNode): string =>
  String(node.properties?.ci_code ??
    node.properties?.ci_name ??
    node.properties?.name ??
    node.labels[0] ??
    `Node:${node.id}`);

const formatGridCellValue = (value: unknown): string | number | boolean => {
  if (value === null || value === undefined) {
    return "";
  }
  if (isNeo4jNode(value)) {
    return getNodeDisplayName(value) as string;
  }
  if (isNeo4jRelationship(value)) {
    return `${value.type}:${value.start}->${value.end}`;
  }
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return Object.prototype.toString.call(value);
    }
  }
  return value as string | number | boolean;
};

const normalizeResult = (rows: GridRow[]): NormalizedResult => {
  const nodeMap = new Map<string, { label: string; displayName: string; properties: Record<string, unknown> }>();
  const edgeMap = new Map<string, Neo4jSerializedRelationship>();
  const rowGraphRefs: RowGraphRef[] = [];

  const collectNode = (node: Neo4jSerializedNode) => {
    const existing = nodeMap.get(node.id);
    const label = node.labels.concat(existing?.label ? [] : []).filter(Boolean);
    nodeMap.set(node.id, {
      label: label[0] ?? node.labels[0] ?? "Node",
      displayName: getNodeDisplayName(node),
      properties: node.properties,
    });
  };

  const collectRelationship = (rel: Neo4jSerializedRelationship) => {
    edgeMap.set(rel.id, rel);
    collectNode({
      __neo4j_type: "node",
      id: rel.start,
      labels: [],
      properties: {},
    });
    collectNode({
      __neo4j_type: "node",
      id: rel.end,
      labels: [],
      properties: {},
    });
  };

  rows.forEach((row) => {
    const graphRef: RowGraphRef = { nodeIds: [], edgeIds: [] };
    Object.values(row).forEach((value) => {
      if (isNeo4jNode(value)) {
        collectNode(value);
        graphRef.nodeIds.push(value.id);
      }
      if (isNeo4jRelationship(value)) {
        collectRelationship(value);
        graphRef.edgeIds.push(value.id);
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (isNeo4jNode(item)) {
            collectNode(item);
            graphRef.nodeIds.push(item.id);
          }
          if (isNeo4jRelationship(item)) {
            collectRelationship(item);
            graphRef.edgeIds.push(item.id);
          }
        });
      }
    });
    rowGraphRefs.push({
      nodeIds: Array.from(new Set(graphRef.nodeIds)),
      edgeIds: Array.from(new Set(graphRef.edgeIds)),
    });
  });

  const scalar =
    rows.length === 1 && Object.keys(rows[0]).length === 1
      ? (Object.values(rows[0])[0] as string | number | boolean)
      : undefined;

  const graphNodesArray = Array.from(nodeMap.entries()).map(([id, data], index) => ({
    id,
    data: {
      label: data.displayName,
      properties: data.properties,
      originalLabel: data.label,
    },
    position: {
      x: Math.cos((index / Math.max(1, nodeMap.size)) * 2 * Math.PI) * 200,
      y: Math.sin((index / Math.max(1, nodeMap.size)) * 2 * Math.PI) * 200,
    },
  })) as Neo4jFlowNode[];

  const graphEdgesArray = Array.from(edgeMap.values()).map((rel) => ({
    id: rel.id,
    source: rel.start,
    target: rel.end,
    label: rel.type,
  })) as Neo4jFlowEdge[];

  const truncated = {
    nodes: graphNodesArray.length > MAX_GRAPH_NODES,
    edges: graphEdgesArray.length > MAX_GRAPH_EDGES,
  };

  const truncatedNodes = truncated.nodes
    ? graphNodesArray.slice(0, MAX_GRAPH_NODES)
    : graphNodesArray;
  const truncatedEdges = truncated.edges
    ? graphEdgesArray.slice(0, MAX_GRAPH_EDGES)
    : graphEdgesArray;

  const warnings = [];
  if (truncated.nodes) {
    warnings.push(`Node count clipped to ${MAX_GRAPH_NODES}`);
  }
  if (truncated.edges) {
    warnings.push(`Edge count clipped to ${MAX_GRAPH_EDGES}`);
  }

  const normalizedRows = rows.map((row, index) => ({
    ...Object.fromEntries(
      Object.entries(row).map(([column, value]) => [column, formatGridCellValue(value)])
    ),
    [NEO4J_ROW_INDEX_KEY]: index,
  }));

  return {
    graphNodes: truncatedNodes,
    graphEdges: truncatedEdges,
    rowGraphRefs,
    rows: normalizedRows,
    scalar: typeof scalar === "object" ? undefined : scalar,
    warnings,
    truncated,
  };
};
const normalizeBaseUrl = (value?: string) => {
  if (!value) {
    return "";
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

const formatError = (err: unknown) => {
  if (err instanceof Error) {
    return err.message;
  }
  if (typeof err === "string") {
    return err;
  }
  try {
    return JSON.stringify(err);
  } catch {
    return "Unknown error";
  }
};

const TabsButton = ({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.25em] transition ${active
      ? "border-sky-400 text-white"
      : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"
      }`}
  >
    {children}
  </button>
);

export default function ExplorerPage() {
  const apiBaseUrl = normalizeBaseUrl(
    process.env.NEXT_PUBLIC_API_BASE_URL
  );
  const enableDataExplorer =
    process.env.NEXT_PUBLIC_ENABLE_DATA_EXPLORER === "true";

  const [sourceTab, setSourceTab] = useState<"postgres" | "neo4j" | "redis">(
    "postgres"
  );
  const [modeTab, setModeTab] = useState<"browse" | "query">("browse");
  const [selectedTable, setSelectedTable] = useState<PostgresTable | null>(
    null
  );
  const [tableSearch, setTableSearch] = useState("");
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [redisPrefix, setRedisPrefix] = useState("cep:");
  const [redisPattern, setRedisPattern] = useState("");
  const [redisCursor, setRedisCursor] = useState(0);
  const [queryText, setQueryText] = useState("");
  const [gridColumns, setGridColumns] = useState<string[]>([]);
  const [gridRows, setGridRows] = useState<GridRow[]>([]);
  const [normalizedNeo4jResult, setNormalizedNeo4jResult] =
    useState<NormalizedResult | null>(null);
  const [neo4jRowRefs, setNeo4jRowRefs] = useState<RowGraphRef[]>([]);
  const [neo4jViewMode, setNeo4jViewMode] =
    useState<"graph" | "table" | "value">("table");
  const [neo4jScalar, setNeo4jScalar] = useState<string | number | boolean | null>(
    null
  );
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(
    new Set()
  );
  const [highlightedEdgeIds, setHighlightedEdgeIds] = useState<Set<string>>(
    new Set()
  );
  const [selectedGraphNode, setSelectedGraphNode] = useState<Neo4jFlowNode | null>(
    null
  );
  const [selectedRow, setSelectedRow] = useState<GridRow | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  const defaultQuery = useMemo(() => {
    switch (sourceTab) {
      case "neo4j":
        return "MATCH (n) RETURN n LIMIT 10";
      case "redis":
        return "GET cep:";
      case "postgres":
      default:
        return "SELECT * FROM tb_cep_notification_log LIMIT 10";
    }
  }, [sourceTab]);

  useEffect(() => {
    setQueryText(defaultQuery);
  }, [defaultQuery]);

  useEffect(() => {
    // Clear all results when switching tabs
    setGridRows([]);
    setGridColumns([]);
    setStatusMessage(null);
    setQueryError(null);
    setSelectedRow(null);

    setNormalizedNeo4jResult(null);
    setNeo4jRowRefs([]);
    setNeo4jScalar(null);
    setNeo4jViewMode("table");
    setHighlightedNodeIds(new Set());
    setHighlightedEdgeIds(new Set());
    setSelectedGraphNode(null);
  }, [sourceTab]);

  const tablesQuery = useQuery({
    queryKey: ["data", "postgres", "tables"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/data/postgres/tables`);
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to load tables");
      }
      return body.data?.tables as PostgresTable[];
    },
    enabled: enableDataExplorer && sourceTab === "postgres",
  });

  const labelsQuery = useQuery({
    queryKey: ["data", "neo4j", "labels"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/data/neo4j/labels`);
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to load labels");
      }
      return body.data?.labels as string[];
    },
    enabled: enableDataExplorer && sourceTab === "neo4j",
  });

  const redisScanQuery = useQuery({
    queryKey: ["data", "redis", "scan", redisPrefix, redisPattern, redisCursor],
    queryFn: async () => {
      const params = new URLSearchParams({
        prefix: redisPrefix,
        pattern: redisPattern,
        cursor: String(redisCursor),
        count: "50",
      });
      const response = await fetch(
        `${apiBaseUrl}/data/redis/scan?${params}`
      );
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to scan keys");
      }
      return body.data as { cursor: number; keys: string[] };
    },
    enabled: enableDataExplorer && sourceTab === "redis" && modeTab === "browse",
  });

  const previewTableMutation = useMutation({
    mutationFn: async (tableName: string) => {
      const params = new URLSearchParams({
        table: tableName,
        limit: String(MAX_ROWS),
      });
      const response = await fetch(
        `${apiBaseUrl}/data/postgres/preview?${params.toString()}`
      );
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Preview failed");
      }
      return body.data as { columns: string[]; rows: GridRow[] };
    },
    onSuccess: (data) => {
      setGridColumns(data.columns);
      setGridRows(data.rows);
      setSelectedRow(null);
      setStatusMessage("Preview loaded");
    },
    onError: (err) => {
      setStatusMessage(formatError(err));
    },
  });

  const runQueryMutation = useMutation({
    mutationFn: async (statement: string) => {
      if (sourceTab === "postgres") {
        const response = await fetch(`${apiBaseUrl}/data/postgres/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sql: statement }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            body.message ?? body.detail ?? "Query failed. See server logs for details."
          );
        }
        return body.data as { columns: string[]; rows: GridRow[] };
      }
      if (sourceTab === "neo4j") {
        const response = await fetch(`${apiBaseUrl}/data/neo4j/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cypher: statement }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            body.message ?? body.detail ?? "Query failed. See server logs for details."
          );
        }
        return body.data as { columns: string[]; rows: GridRow[] };
      }
      const response = await fetch(`${apiBaseUrl}/data/redis/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: statement }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          body.message ?? body.detail ?? "Command failed. See server logs for details."
        );
      }
      return { columns: ["result"], rows: [{ result: body.data?.result }] };
    },
    onSuccess: (data) => {
      setGridColumns(data.columns);
      if (sourceTab === "neo4j") {
        const normalized = normalizeResult(data.rows);
        setGridRows(normalized.rows);
        setNormalizedNeo4jResult(normalized);
        setNeo4jRowRefs(normalized.rowGraphRefs);
        setNeo4jScalar(normalized.scalar ?? null);
        setNeo4jViewMode(
          normalized.graphNodes.length > 0
            ? "graph"
            : normalized.scalar !== undefined
              ? "value"
              : "table"
        );
        setHighlightedNodeIds(new Set());
        setHighlightedEdgeIds(new Set());
        setSelectedGraphNode(null);
      } else {
        setGridRows(data.rows);
        setNormalizedNeo4jResult(null);
        setNeo4jRowRefs([]);
        setNeo4jScalar(null);
        setNeo4jViewMode("table");
        setHighlightedNodeIds(new Set());
        setHighlightedEdgeIds(new Set());
      }
      setSelectedRow(null);
      setStatusMessage("Query executed");
      setQueryError(null);
    },
    onError: (err) => {
      setStatusMessage(formatError(err));
      setQueryError(formatError(err));
      setNormalizedNeo4jResult(null);
      setNeo4jRowRefs([]);
      setNeo4jScalar(null);
      setNeo4jViewMode("table");
      setHighlightedNodeIds(new Set());
      setHighlightedEdgeIds(new Set());
      setSelectedGraphNode(null);
    },
  });

  const redisKeyMutation = useMutation({
    mutationFn: async (key: string) => {
      const params = new URLSearchParams({ key });
      const response = await fetch(`${apiBaseUrl}/data/redis/key?${params}`);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          body.message ?? body.detail ?? "Failed to fetch key. See server logs for details."
        );
      }
      return body.data as RedisKeyResult;
    },
    onSuccess: (data) => {
      setGridColumns(["value"]);
      setGridRows([{ value: data.value }]);
      setSelectedRow(data as unknown as GridRow);
      setStatusMessage(`Key loaded (${data.type})`);
    },
    onError: (err) => {
      setStatusMessage(formatError(err));
    },
  });

  const gridColDefs = useMemo<ColDef[]>(
    () => gridColumns.map((col) => ({ field: col, sortable: true, filter: true, resizable: true })),
    [gridColumns]
  );

  const neo4jGraphPreview = useMemo(() => {
    if (!normalizedNeo4jResult) {
      return {
        nodes: [] as Neo4jFlowNode[],
        edges: [] as Neo4jFlowEdge[],
        warnings: [] as string[],
        truncated: { nodes: false, edges: false },
      };
    }
    return {
      nodes: normalizedNeo4jResult.graphNodes,
      edges: normalizedNeo4jResult.graphEdges,
      warnings: normalizedNeo4jResult.warnings,
      truncated: normalizedNeo4jResult.truncated,
    };
  }, [normalizedNeo4jResult]);

  const getRowGraphRefs = (row: GridRow): RowGraphRef => {
    const rowIndex =
      typeof row[NEO4J_ROW_INDEX_KEY] === "number"
        ? (row[NEO4J_ROW_INDEX_KEY] as number)
        : undefined;
    if (rowIndex !== undefined && neo4jRowRefs[rowIndex]) {
      return neo4jRowRefs[rowIndex];
    }
    return { nodeIds: [], edgeIds: [] };
  };

  const handleTableRowClick = (event: RowClickedEvent) => {
    const row = event.data as GridRow;
    setSelectedRow(row);
    setSelectedGraphNode(null);
    const refs = getRowGraphRefs(row);
    setHighlightedNodeIds(new Set(refs.nodeIds));
    setHighlightedEdgeIds(new Set(refs.edgeIds));
  };

  const handleGraphNodeClick = (node: Neo4jFlowNode) => {
    setSelectedGraphNode(node);
    setSelectedRow(null);
    setHighlightedNodeIds(new Set([node.id]));
    const connectedEdges = neo4jGraphPreview.edges
      .filter((edge: Neo4jFlowEdge) => edge.source === node.id || edge.target === node.id)
      .map((edge: Neo4jFlowEdge) => edge.id);
    setHighlightedEdgeIds(new Set(connectedEdges));
  };

  const graphAvailable =
    neo4jGraphPreview.nodes.length > 0 || neo4jGraphPreview.edges.length > 0;
  const valueAvailable = neo4jScalar !== null;
  const inspectorContent =
    selectedGraphNode !== null
      ? {
        label: selectedGraphNode.data.label,
        originalLabel: (selectedGraphNode.data as Record<string, unknown>).originalLabel as string | undefined,
        properties: selectedGraphNode.data.properties,
      }
      : selectedRow;

  if (!enableDataExplorer) {
    return (
      <div className="min-h-screen bg-[#05070f] px-10 py-10 text-slate-200">
        <h1 className="text-2xl font-semibold">Data Explorer</h1>
        <p className="mt-4 text-sm text-slate-400">
          Data Explorer is disabled. Enable{" "}
          <code className="rounded bg-slate-800 px-2 py-1 text-xs">
            NEXT_PUBLIC_ENABLE_DATA_EXPLORER
          </code>{" "}
          to continue.
        </p>
      </div>
    );
  }

  const renderExplorer = () => {
    if (sourceTab === "postgres") {
      return (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Tables
          </div>
          <input
            value={tableSearch}
            onChange={(event) => setTableSearch(event.target.value)}
            placeholder="Search tables"
            className="w-full rounded-full border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
          />
          <div className="custom-scrollbar max-h-[420px] space-y-2 overflow-auto pr-1">

            {tablesQuery.isError && (
              <div className="text-xs text-rose-300">
                {formatError(tablesQuery.error)}
              </div>
            )}
            {(tablesQuery.data ?? [])
              .filter((item) =>
                `${item.schema}.${item.table}`
                  .toLowerCase()
                  .includes(tableSearch.toLowerCase())
              )
              .map((item) => {
                const fullName = `${item.schema}.${item.table}`;
                const active =
                  selectedTable?.schema === item.schema &&
                  selectedTable?.table === item.table;
                return (
                  <button
                    key={fullName}
                    type="button"
                    onClick={() => {
                      setSelectedTable(item);
                      previewTableMutation.mutate(fullName);
                    }}
                    className={`w-full rounded-xl border px-3 py-2 text-left text-sm ${active
                      ? "border-sky-500 text-white"
                      : "border-slate-800 text-slate-300 hover:border-slate-600"
                      }`}
                  >
                    {fullName}
                  </button>
                );
              })}
          </div>
        </div>
      );
    }
    if (sourceTab === "neo4j") {
      return (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Labels
          </div>
          <div className="custom-scrollbar max-h-[420px] space-y-2 overflow-auto pr-1">

            {labelsQuery.isError && (
              <div className="text-xs text-rose-300">
                {formatError(labelsQuery.error)}
              </div>
            )}
            {(labelsQuery.data ?? []).map((label) => {
              const active = selectedLabel === label;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => {
                    setSelectedLabel(label);
                    const statement = `MATCH (n:${label}) RETURN n LIMIT ${MAX_ROWS}`;
                    setQueryText(statement);
                    runQueryMutation.mutate(statement);
                  }}
                  className={`w-full rounded-xl border px-3 py-2 text-left text-sm ${active
                    ? "border-sky-500 text-white"
                    : "border-slate-800 text-slate-300 hover:border-slate-600"
                    }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      );
    }
    return (
      <div className="space-y-3">
        <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
          Keys
        </div>
        <input
          value={redisPrefix}
          onChange={(event) => setRedisPrefix(event.target.value)}
          placeholder="Prefix (allowlist)"
          className="w-full rounded-full border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
        />
        <input
          value={redisPattern}
          onChange={(event) => setRedisPattern(event.target.value)}
          placeholder="Pattern (optional)"
          className="w-full rounded-full border border-slate-700 bg-transparent px-4 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
        />
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <button
            type="button"
            onClick={() => setRedisCursor(0)}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs uppercase tracking-[0.2em] text-slate-300"
          >
            Scan
          </button>
          <span>cursor: {redisScanQuery.data?.cursor ?? 0}</span>
        </div>
        <div className="custom-scrollbar max-h-[320px] space-y-2 overflow-auto pr-1">

          {redisScanQuery.isError && (
            <div className="text-xs text-rose-300">
              {formatError(redisScanQuery.error)}
            </div>
          )}
          {(redisScanQuery.data?.keys ?? []).map((key) => {
            const active = selectedKey === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setSelectedKey(key);
                  redisKeyMutation.mutate(key);
                }}
                className={`w-full rounded-xl border px-3 py-2 text-left text-sm ${active
                  ? "border-sky-500 text-white"
                  : "border-slate-800 text-slate-300 hover:border-slate-600"
                  }`}
              >
                {key}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="py-6 tracking-tight builder-shell builder-text">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Data Explorer</h1>
        <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Admin only
        </div>
      </div>
      <p className="mb-4 text-sm text-slate-400">
        Read-only data access. Max {MAX_ROWS} rows.
      </p>

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] items-center uppercase tracking-[0.2em] text-slate-500">Source:</span>
          <TabsButton active={sourceTab === "postgres"} onClick={() => setSourceTab("postgres")}>
            Postgres
          </TabsButton>
          <TabsButton active={sourceTab === "neo4j"} onClick={() => setSourceTab("neo4j")}>
            Neo4j
          </TabsButton>
          <TabsButton active={sourceTab === "redis"} onClick={() => setSourceTab("redis")}>
            Redis
          </TabsButton>
        </div >
        <div className="h-4 w-px bg-slate-800 mx-2" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] items-center uppercase tracking-[0.2em] text-slate-500">Mode:</span>
          <TabsButton active={modeTab === "browse"} onClick={() => setModeTab("browse")}>
            Browse
          </TabsButton>
          <TabsButton active={modeTab === "query"} onClick={() => setModeTab("query")}>
            {sourceTab === "redis" ? "Command" : "Query"}
          </TabsButton>
        </div>
      </div >

      <BuilderShell
        leftPane={renderExplorer()}
        centerTop={
          <div className="space-y-4">
            {modeTab === "query" && (
              <div className="space-y-3">
                <textarea
                  value={queryText}
                  onChange={(event) => setQueryText(event.target.value)}
                  rows={4}
                  className="w-full resize-none rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-200 focus:border-sky-500 focus:outline-none custom-scrollbar"
                  placeholder={
                    sourceTab === "redis"
                      ? "GET cep:example"
                      : sourceTab === "neo4j"
                        ? "MATCH (n) RETURN n"
                        : "SELECT * FROM tb_cep_notification_log"
                  }
                />
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Max {MAX_ROWS} rows</span>
                  <button
                    type="button"
                    onClick={() => runQueryMutation.mutate(queryText)}
                    className="rounded-full border border-slate-700 px-4 py-2 text-xs uppercase tracking-[0.25em] text-slate-200 hover:border-sky-500"
                  >
                    Run
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-3">
              <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
                Results
              </div>
              <div className="ag-theme-cep h-[520px] w-full rounded-2xl border border-slate-800 bg-slate-950/70 overflow-hidden">
                <AgGridReact
                  theme="legacy"
                  columnDefs={gridColDefs}
                  rowData={gridRows}
                  rowSelection="single"
                  defaultColDef={{ resizable: true, sortable: true, filter: true } satisfies ColDef}
                  onRowClicked={handleTableRowClick}
                />
              </div>
              {statusMessage && (
                <div className="mt-3 text-xs text-slate-400">{statusMessage}</div>
              )}
              {queryError && (
                <div className="mt-2 rounded-2xl border border-rose-500/70 bg-rose-500/5 px-3 py-2 text-xs text-rose-200">
                  {queryError}
                </div>
              )}
            </div>
            {sourceTab === "neo4j" && (
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Graph preview</p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] ${neo4jViewMode === "graph"
                        ? "border-sky-400 text-white"
                        : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"
                        }`}
                      onClick={() => setNeo4jViewMode("graph")}
                      disabled={!graphAvailable}
                    >
                      Graph
                    </button>
                    <button
                      type="button"
                      className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] ${neo4jViewMode === "table"
                        ? "border-sky-400 text-white"
                        : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"
                        }`}
                      onClick={() => {
                        setNeo4jViewMode("table");
                        setHighlightedNodeIds(new Set());
                        setHighlightedEdgeIds(new Set());
                        setSelectedGraphNode(null);
                      }}
                    >
                      Table
                    </button>
                    <button
                      type="button"
                      className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.2em] ${neo4jViewMode === "value"
                        ? "border-sky-400 text-white"
                        : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white"
                        }`}
                      onClick={() => setNeo4jViewMode("value")}
                      disabled={!valueAvailable}
                    >
                      Value
                    </button>
                  </div>
                </div>
                <div className="text-[10px] text-slate-500">
                  Nodes: {neo4jGraphPreview.nodes.length} · Relations: {neo4jGraphPreview.edges.length}
                </div>
                {neo4jGraphPreview.warnings.length > 0 && (
                  <div className="space-y-1 text-[10px] text-slate-400">
                    {neo4jGraphPreview.warnings.map((warning, index) => (
                      <p key={`warning-${index}`}>{warning}</p>
                    ))}
                  </div>
                )}
                {neo4jViewMode === "graph" && (
                  <div className="h-[360px] w-full rounded-2xl border border-slate-800 bg-slate-950/70 shadow-inner">
                    {graphAvailable ? (
                      <Neo4jGraphFlow
                        nodes={neo4jGraphPreview.nodes}
                        edges={neo4jGraphPreview.edges}
                        highlightNodeIds={highlightedNodeIds}
                        highlightEdgeIds={highlightedEdgeIds}
                        onNodeClick={handleGraphNodeClick}
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-sm text-slate-400">
                        Run a Neo4j query returning nodes & relationships to visualize the graph.
                      </div>
                    )}
                  </div>
                )}
                {neo4jViewMode === "value" && valueAvailable && (
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-100">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Scalar result</p>
                    <p className="mt-2 text-lg font-semibold">{String(neo4jScalar)}</p>
                  </div>
                )}
              </section>
            )}
          </div>
        }
        rightPane={
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
              Inspector
            </div>
            <div className="custom-scrollbar mt-3 max-h-[620px] overflow-auto rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-200">
              <pre className="whitespace-pre-wrap">
                {inspectorContent ? JSON.stringify(inspectorContent, null, 2) : "No selection"}
              </pre>
            </div>
          </div>
        }
      />
    </div >
  );
}
