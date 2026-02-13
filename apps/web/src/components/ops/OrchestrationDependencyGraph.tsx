'use client';

import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { SpanNode } from '@/components/admin/SpanNode';
import type { OrchestrationTrace, ExecutionGroup, Tool } from './OrchestrationVisualization';

interface OrchestrationDependencyGraphProps {
  trace: OrchestrationTrace;
  selectedTool?: string;
  onToolSelect?: (toolId: string) => void;
}

/**
 * Converts orchestration trace to React Flow nodes and edges
 */
function generateOrchestrationNodes(trace: OrchestrationTrace): Node[] {
  const nodes: Node[] = [];
  const nodeId = new Map<string, boolean>();

  trace.execution_groups.forEach((group) => {
    group.tools.forEach((tool) => {
      if (!nodeId.has(tool.tool_id)) {
        nodeId.set(tool.tool_id, true);

        // Calculate position based on group and tool index
        const groupY = group.group_index * 120;
        const groupTools = group.tools;
        const toolIndexInGroup = groupTools.findIndex((t) => t.tool_id === tool.tool_id);
        const toolX = toolIndexInGroup * 180 + (group.parallel_execution ? 0 : 0);

        nodes.push({
          id: tool.tool_id,
          data: {
            label: tool.tool_id,
            kind: tool.tool_type,
            duration: 0, // Will be populated from execution results
            status: 'ok',
            error: null,
          },
          position: { x: toolX, y: groupY },
          type: 'default',
          style: {
            background: getToolColor(trace.strategy, group.parallel_execution),
            border: '1px solid var(--border-muted)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--spacing-xs)',
            color: 'var(--foreground)',
            fontSize: '12px',
            minWidth: '120px',
            textAlign: 'center',
          },
        });
      }
    });
  });

  return nodes;
}

/**
 * Converts orchestration trace to React Flow edges
 */
function generateOrchestrationEdges(trace: OrchestrationTrace): Edge[] {
  const edges: Edge[] = [];
  const edgeSet = new Set<string>();

  trace.execution_groups.forEach((group) => {
    group.tools.forEach((tool) => {
      tool.depends_on.forEach((dependency) => {
        const edgeId = `${dependency}->${tool.tool_id}`;
        if (!edgeSet.has(edgeId)) {
          edgeSet.add(edgeId);

          edges.push({
            id: edgeId,
            source: dependency,
            target: tool.tool_id,
            animated: true,
            style: {
              stroke: 'var(--primary-light)',
              strokeWidth: 2,
            },
          });
        }
      });
    });
  });

  return edges;
}

/**
 * Get tool node color based on strategy
 */
function getToolColor(strategy: string, isParallel: boolean): string {
  switch (strategy) {
    case 'parallel':
      return isParallel ? 'var(--execution-color-parallel)' : 'var(--execution-color-serial)';
    case 'dag':
      return isParallel ? 'var(--execution-color-parallel)' : 'var(--execution-color-dag)';
    case 'serial':
    default:
      return 'var(--execution-color-default)';
  }
}

/**
 * OrchestrationDependencyGraph Component
 *
 * Displays orchestration execution plan as a dependency graph using React Flow
 * - Shows tool nodes with dependency arrows
 * - Color-coded by execution strategy
 * - Interactive node selection
 */
export function OrchestrationDependencyGraph({
  trace,
  selectedTool,
  onToolSelect,
}: OrchestrationDependencyGraphProps) {
  const initialNodes = useMemo(() => generateOrchestrationNodes(trace), [trace]);
  const initialEdges = useMemo(() => generateOrchestrationEdges(trace), [trace]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      onToolSelect?.(node.id);
    },
    [onToolSelect]
  );

  // Update node styling based on selection
  const styledNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        style: {
          ...node.style,
          border:
            selectedTool === node.id
              ? '2px solid var(--primary-light)'
              : '1px solid var(--border-muted)',
          boxShadow:
            selectedTool === node.id
              ? 'var(--node-shadow-selected)'
              : 'none',
        },
      })),
    [nodes, selectedTool]
  );

  return (
    <div className="w-full h-[500px] rounded-lg overflow-hidden  border /50">
      <ReactFlow
        nodes={styledNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
      >
        <Background color="var(--chart-grid-color)" gap={16} size={1} />
        <Controls position="top-right" />
      </ReactFlow>

      {/* Empty state */}
      {trace.execution_groups.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center /80">
          <div className="text-center">
            <p className=" text-sm">No execution groups</p>
            {trace.error && (
              <p className="text-rose-400 text-xs mt-2">{trace.error}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export type { OrchestrationDependencyGraphProps };
