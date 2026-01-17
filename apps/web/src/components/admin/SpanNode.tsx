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
  links: Record<string, any>;
  span: any;
}

function SpanNode({ data, isConnecting, selected }: NodeProps<SpanNodeData>) {
  const statusClass =
    data.status === "ok"
      ? "bg-emerald-900/40 border-emerald-700 text-emerald-200"
      : "bg-rose-900/40 border-rose-700 text-rose-200";

  const nodeClass = selected
    ? "border-2 border-blue-500 shadow-lg shadow-blue-500/50"
    : "border border-slate-700";

  return (
    <div
      className={`w-56 bg-slate-900/80 rounded-lg px-3 py-2 transition-all cursor-pointer ${nodeClass} ${statusClass}`}
    >
      <Handle type="target" position={Position.Top} isConnecting={isConnecting} />

      <div className="text-xs font-semibold text-slate-100 truncate">{data.name}</div>

      <div className="mt-1 flex items-center gap-2 justify-between">
        <span className="text-[10px] text-slate-400 uppercase tracking-[0.2em]">{data.kind}</span>
        <span className="text-[10px] font-mono text-slate-300">{data.duration_ms}ms</span>
      </div>

      {data.summary.error_message && (
        <div className="mt-2 text-[10px] text-rose-300 truncate">{data.summary.error_message}</div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export default memo(SpanNode);
