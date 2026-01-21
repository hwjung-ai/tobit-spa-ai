"use client";

import { useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";

export type Neo4jFlowNode = Node<{ label: string; properties?: Record<string, unknown> }>;
export interface Neo4jFlowEdge extends Edge {
  label?: string;
}

export interface Neo4jGraphFlowProps {
  nodes: Neo4jFlowNode[];
  edges: Neo4jFlowEdge[];
  highlightNodeIds?: Set<string>;
  highlightEdgeIds?: Set<string>;
  onNodeClick?: (node: Neo4jFlowNode) => void;
}

export default function Neo4jGraphFlow({
  nodes,
  edges,
  highlightNodeIds,
  highlightEdgeIds,
  onNodeClick,
}: Neo4jGraphFlowProps) {
  const [nodeState, setNodeState, onNodesChange] = useNodesState(nodes);
  const [edgeState, setEdgeState, onEdgesChange] = useEdgesState(edges);

  useEffect(() => {
    setNodeState(nodes);
  }, [nodes, setNodeState]);

  useEffect(() => {
    setEdgeState(edges);
  }, [edges, setEdgeState]);

  const uniqueNodes = useMemo(() => {
    const seen = new Set<string>();
    return nodeState.filter((node) => {
      if (seen.has(node.id)) {
        return false;
      }
      seen.add(node.id);
      return true;
    });
  }, [nodeState]);

  const uniqueEdges = useMemo(() => {
    const seen = new Set<string>();
    return edgeState.filter((edge) => {
      const key = `${edge.id}-${edge.source}-${edge.target}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [edgeState]);

  const formattedEdges = useMemo(
    () =>
      uniqueEdges.map((edge, index) => ({
        ...edge,
        id: edge.id ?? `edge-${index}-${edge.source}-${edge.target}`,
      })),
    [uniqueEdges]
  );

  const decoratedNodes = uniqueNodes.map((node) => ({
    ...node,
    style: highlightNodeIds?.has(node.id ?? "")
          ? {
              border: "2px solid #38bdf8",
              background: "#0f172a",
              boxShadow: "0 0 10px rgba(56, 189, 248, 0.6)",
              color: "#e0f2fe",
              fontWeight: 600,
            }
      : node.style,
  }));

  const decoratedEdges = formattedEdges.map((edge) => ({
    ...edge,
    style: highlightEdgeIds?.has(edge.id ?? "")
      ? { stroke: "#f97316", strokeWidth: 3 }
      : edge.style,
  }));

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={decoratedNodes}
        edges={decoratedEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        attributionPosition="bottom-left"
        nodesDraggable
        panOnDrag
        selectionOnDrag={false}
        onNodeClick={(event, node) => {
          event.preventDefault();
          onNodeClick?.(node);
        }}
      >
        <Background gap={12} size={1} color="#0f172a" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
