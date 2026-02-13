/**
 * Custom React Flow node for displaying execution span
 */

import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";

interface SpanNodeData {
  name: string;
  kind: string;
  status: string;
  duration_ms: number;
  summary: {
    note?: string;
    error_type?: string;
    error_message?: string;
  };
  links: Record<string, unknown>;
  span: unknown;
}

function SpanNode({ data, selected }: NodeProps<SpanNodeData>) {
  const statusClass =
    data.status === "ok"
      ? "bg-emerald-900/40 border-emerald-700 text-emerald-200"
      : "bg-rose-900/40 border-rose-700 text-rose-200";

  const nodeClass = selected
    ? "border-2 border-sky-500 shadow-lg shadow-sky-500/50"
    : "border";

  return (
    <div
      className={`w-56 rounded-lg px-3 py-2 transition-all cursor-pointer bg-surface-base/80 ${nodeClass} ${statusClass}`}
    >
      <Handle type="target" position={Position.Top} />

      <div className="text-sm font-semibold truncate text-foreground">{data.name}</div>

      <div className="mt-1 flex items-center gap-2 justify-between">
        <span className="text-tiny uppercase tracking-wider text-muted-foreground">{data.kind}</span>
        <span className="text-tiny font-mono text-muted-foreground">{data.duration_ms}ms</span>
      </div>

      {data.summary.error_message && (
        <div className="mt-2 text-tiny text-rose-300 truncate">{data.summary.error_message}</div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export { SpanNode };
export default memo(SpanNode);
