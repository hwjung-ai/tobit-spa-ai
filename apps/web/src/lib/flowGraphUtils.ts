/**
 * Utility functions for Flow Graph View (React Flow)
 * Generates nodes and edges from flow_spans array
 */

import { Node, Edge } from "reactflow";

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

const X_GAP = 260;
const Y_GAP = 90;

/**
 * Calculate depth for each span in the hierarchy
 */
function calculateDepths(spans: FlowSpan[]): Map<string, number> {
  const depthMap = new Map<string, number>();
  const spanMap = new Map<string, FlowSpan>(spans.map((s) => [s.span_id, s]));

  const visited = new Set<string>();
  const visiting = new Set<string>();

  function dfs(spanId: string): number {
    if (visited.has(spanId)) {
      return depthMap.get(spanId) ?? 0;
    }

    if (visiting.has(spanId)) {
      // Cycle detected
      return 0;
    }

    visiting.add(spanId);
    const span = spanMap.get(spanId);

    if (!span) {
      return 0;
    }

    let depth = 0;
    if (span.parent_span_id && spanMap.has(span.parent_span_id)) {
      depth = dfs(span.parent_span_id) + 1;
    }

    depthMap.set(spanId, depth);
    visited.add(spanId);
    visiting.delete(spanId);

    return depth;
  }

  for (const span of spans) {
    if (!visited.has(span.span_id)) {
      dfs(span.span_id);
    }
  }

  return depthMap;
}

/**
 * Calculate Y positions for siblings and stagger
 */
function calculateYPositions(spans: FlowSpan[]): Map<string, number> {
  const yMap = new Map<string, number>();

  // Group spans by parent
  const byParent = new Map<string | null, FlowSpan[]>();
  for (const span of spans) {
    const parentId = span.parent_span_id;
    if (!byParent.has(parentId)) {
      byParent.set(parentId, []);
    }
    byParent.get(parentId)!.push(span);
  }

  // Sort each group by ts_start_ms
  for (const group of byParent.values()) {
    group.sort((a, b) => a.ts_start_ms - b.ts_start_ms);
  }

  // Assign Y positions
  let yCounter = 0;
  for (const group of byParent.values()) {
    for (let i = 0; i < group.length; i++) {
      yMap.set(group[i].span_id, yCounter * Y_GAP);
      yCounter++;
    }
  }

  return yMap;
}

/**
 * Generate React Flow nodes from flow_spans
 * Handles edge cases: missing spans, null values, etc.
 */
export function generateNodes(spans: FlowSpan[] | null | undefined): Node[] {
  if (!spans || spans.length === 0) {
    return [];
  }

  // Sanitize spans
  const validSpans = spans.filter((s) => s && s.span_id && s.name && typeof s.duration_ms === "number");

  if (validSpans.length === 0) {
    return [];
  }

  try {
    const depthMap = calculateDepths(validSpans);
    const yMap = calculateYPositions(validSpans);

    const nodes: Node[] = validSpans.map((span) => {
      const depth = Math.max(0, depthMap.get(span.span_id) ?? 0);
      const x = Math.max(0, depth * X_GAP);
      const y = Math.max(0, yMap.get(span.span_id) ?? 0);

      return {
        id: span.span_id,
        data: {
          label: span.name,
          name: span.name,
          kind: span.kind || "unknown",
          status: span.status || "ok",
          duration_ms: span.duration_ms || 0,
          summary: span.summary || {},
          links: span.links || {},
          span,
        },
        position: { x, y },
        type: "spanNode",
      };
    });

    return nodes;
  } catch (error) {
    console.error("Error generating nodes:", error);
    return [];
  }
}

/**
 * Generate React Flow edges from flow_spans
 * Handles edge cases: orphan spans, cycles, missing parents
 */
export function generateEdges(spans: FlowSpan[] | null | undefined): Edge[] {
  if (!spans || spans.length === 0) {
    return [];
  }

  const validSpans = spans.filter((s) => s && s.span_id);
  if (validSpans.length === 0) {
    return [];
  }

  const spanIds = new Set(validSpans.map((s) => s.span_id));
  const edges: Edge[] = [];
  const visited = new Set<string>();
  const path = new Set<string>();

  // Helper to detect cycles
  const hasCycle = (sourceId: string, targetId: string): boolean => {
    visited.clear();
    path.clear();

    const dfs = (id: string): boolean => {
      if (path.has(id)) return true; // Cycle detected
      if (visited.has(id)) return false;

      visited.add(id);
      path.add(id);

      const span = validSpans.find((s) => s.span_id === id);
      if (span?.parent_span_id && spanIds.has(span.parent_span_id)) {
        if (dfs(span.parent_span_id)) return true;
      }

      path.delete(id);
      return false;
    };

    return dfs(targetId);
  };

  try {
    for (const span of validSpans) {
      if (span.parent_span_id && spanIds.has(span.parent_span_id)) {
        // Avoid cycles
        if (!hasCycle(span.span_id, span.parent_span_id)) {
          edges.push({
            id: `${span.parent_span_id}->${span.span_id}`,
            source: span.parent_span_id,
            target: span.span_id,
            animated: false,
          });
        }
      }
    }
  } catch (error) {
    console.error("Error generating edges:", error);
  }

  return edges;
}

/**
 * Get orphan spans (spans with missing parent)
 */
export function getOrphanSpans(spans: FlowSpan[]): FlowSpan[] {
  if (!spans || spans.length === 0) {
    return [];
  }

  const spanIds = new Set(spans.map((s) => s.span_id));
  return spans.filter((span) => span.parent_span_id && !spanIds.has(span.parent_span_id));
}

/**
 * Filter out tool spans (for toggle feature)
 */
export function filterToolSpans(spans: FlowSpan[]): FlowSpan[] {
  return spans.filter((span) => !span.name.startsWith("tool:"));
}
