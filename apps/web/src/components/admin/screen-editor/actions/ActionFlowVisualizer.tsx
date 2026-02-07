"use client";

import React, { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Handle,
  MarkerType,
  MiniMap,
  Node,
  NodeProps,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import type { ComponentActionRef, ScreenAction } from "@/lib/ui-screen/screen.schema";

type FlowAction = ScreenAction | ComponentActionRef;

interface ActionFlowVisualizerProps {
  actions: FlowAction[];
}

interface ActionNodeData {
  label: string;
  handler: string;
  policyText: string[];
}

function ActionNode({ data }: NodeProps<ActionNodeData>) {
  return (
    <div className="min-w-[220px] rounded-lg border border-sky-500/60 bg-slate-900 px-3 py-2 shadow-md">
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-sky-500" />
      <div className="text-xs font-semibold text-sky-300">{data.label}</div>
      <div className="mt-1 text-[11px] text-slate-400">{data.handler}</div>
      {data.policyText.length > 0 && (
        <div className="mt-2 space-y-1">
          {data.policyText.map((line) => (
            <div key={`${data.handler}-${line}`} className="text-[10px] text-slate-300">
              {line}
            </div>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-sky-500" />
    </div>
  );
}

export default function ActionFlowVisualizer({ actions }: ActionFlowVisualizerProps) {
  const { nodes, edges } = useMemo(() => {
    const mappedNodes: Node<ActionNodeData>[] = actions.map((action, index) => {
      const componentAction = action as ComponentActionRef;
      const policyText: string[] = [];
      if (componentAction.continue_on_error) policyText.push("continue_on_error");
      if (componentAction.stop_on_error === false) policyText.push("stop_on_error=false");
      if ((componentAction.retry_count || 0) > 0) policyText.push(`retry=${componentAction.retry_count}`);
      if (componentAction.run_if) policyText.push(`if ${componentAction.run_if}`);
      if ((componentAction.on_error_action_indexes || []).length > 0) {
        policyText.push(`fallbacks: ${(componentAction.on_error_action_indexes || []).join(",")}`);
      } else if ((componentAction.on_error_action_index ?? -1) >= 0) {
        policyText.push(`fallback: ${componentAction.on_error_action_index}`);
      }

      return {
        id: action.id,
        type: "actionNode",
        position: { x: 100, y: index * 120 + 40 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          label: action.label || action.id,
          handler: action.handler || "(unset handler)",
          policyText,
        },
      };
    });

    const mappedEdges: Edge[] = [];
    actions.forEach((action, index) => {
      if (index < actions.length - 1) {
        mappedEdges.push({
          id: `${action.id}-success-${actions[index + 1].id}`,
          source: action.id,
          target: actions[index + 1].id,
          label: "success",
          labelStyle: { fill: "#4ade80", fontSize: 10 },
          style: { stroke: "#4ade80", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#4ade80" },
          animated: true,
        });
      }

      const componentAction = action as ComponentActionRef;
      const fallbackCandidates = [
        ...(componentAction.on_error_action_indexes || []),
        ...(componentAction.on_error_action_index !== undefined
          ? [componentAction.on_error_action_index]
          : []),
      ]
        .map((idx) => Number(idx))
        .filter((idx) => Number.isFinite(idx) && idx >= 0 && idx < actions.length && idx !== index);

      [...new Set(fallbackCandidates)].forEach((fallbackIdx) => {
        const target = actions[fallbackIdx];
        mappedEdges.push({
          id: `${action.id}-error-${target.id}`,
          source: action.id,
          target: target.id,
          label: "error",
          labelStyle: { fill: "#f87171", fontSize: 10 },
          style: { stroke: "#f87171", strokeWidth: 2, strokeDasharray: "5 4" },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#f87171" },
          type: "smoothstep",
        });
      });
    });

    return { nodes: mappedNodes, edges: mappedEdges };
  }, [actions]);

  if (actions.length === 0) {
    return <div className="flex h-full items-center justify-center text-sm text-slate-500">No actions to visualize</div>;
  }

  return (
    <div className="h-full w-full rounded border border-slate-700 bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={{ actionNode: ActionNode }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
      >
        <Background color="#334155" gap={16} />
        <MiniMap
          nodeColor={() => "#0ea5e9"}
          maskColor="rgba(2, 6, 23, 0.6)"
          pannable
          zoomable
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}
