'use client';

import React, { useMemo } from 'react';
import { ChevronDown, ChevronRight, GitBranch, Zap, Lock } from 'lucide-react';

/**
 * Orchestration trace types matching Phase 5 backend
 */
interface Tool {
  tool_id: string;
  tool_type: string;
  depends_on: string[];
  dependency_groups: number[];
  output_mapping: Record<string, string>;
}

interface ExecutionGroup {
  group_index: number;
  tools: Tool[];
  parallel_execution: boolean;
}

interface OrchestrationTrace {
  strategy: 'parallel' | 'serial' | 'dag';
  execution_groups: ExecutionGroup[];
  total_groups: number;
  total_tools: number;
  tool_ids: string[];
  error?: string;
}

interface OrchestrationVisualizationProps {
  trace: OrchestrationTrace;
  expandedGroups?: number[];
  onGroupToggle?: (groupIndex: number) => void;
  selectedTool?: string;
  onToolSelect?: (toolId: string) => void;
}

/**
 * OrchestrationVisualization Component
 *
 * Displays Phase 5 orchestration execution plan with:
 * - Strategy badge (PARALLEL/SERIAL/DAG)
 * - Execution groups organized by dependencies
 * - Tool details with types and data flow
 * - Visual indicators for parallel/sequential execution
 */
export function OrchestrationVisualization({
  trace,
  expandedGroups = [],
  onGroupToggle,
  selectedTool,
  onToolSelect,
}: OrchestrationVisualizationProps) {
  const strategyIcon = useMemo(() => {
    switch (trace.strategy) {
      case 'parallel':
        return <Zap className="w-4 h-4" />;
      case 'dag':
        return <GitBranch className="w-4 h-4" />;
      case 'serial':
      default:
        return <Lock className="w-4 h-4" />;
    }
  }, [trace.strategy]);

  const strategyColor = useMemo(() => {
    switch (trace.strategy) {
      case 'parallel':
        return 'bg-emerald-900/40 text-emerald-200 border-emerald-400/50';
      case 'dag':
        return 'bg-blue-900/40 text-blue-200 border-blue-400/50';
      case 'serial':
      default:
        return 'bg-amber-900/40 text-amber-200 border-amber-400/50';
    }
  }, [trace.strategy]);

  const strategyLabel = useMemo(() => {
    switch (trace.strategy) {
      case 'parallel':
        return 'Parallel';
      case 'dag':
        return 'Complex DAG';
      case 'serial':
      default:
        return 'Sequential';
    }
  }, [trace.strategy]);

  // Check if any group is expanded
  const hasExpandedGroups = expandedGroups.length > 0;

  return (
    <div className="space-y-4">
      {/* Header with strategy badge */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold " style={{ color: "var(--foreground-secondary)" }}>Execution Plan</h3>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-lg border ${strategyColor}`}>
          {strategyIcon}
          {strategyLabel}
        </div>
      </div>

      {/* Error message if trace generation failed */}
      {trace.error && (
        <div className="rounded-lg bg-rose-900/20 border border-rose-400/30 p-3">
          <p className="text-xs text-rose-200">
            <span className="font-semibold">Trace Error:</span> {trace.error}
          </p>
        </div>
      )}

      {/* Execution groups */}
      <div className="space-y-3">
        {trace.execution_groups.map((group, groupIdx) => (
          <div key={groupIdx} className="rounded-lg  border /50 overflow-hidden" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
            {/* Group header */}
            <button
              onClick={() => onGroupToggle?.(groupIdx)}
              className="w-full flex items-center gap-3 px-4 py-3 hover: transition-colors" style={{ backgroundColor: "var(--surface-overlay)" }}
            >
              {/* Expand/collapse icon */}
              <div className="flex-shrink-0">
                {expandedGroups.includes(groupIdx) ? (
                  <ChevronDown className="w-4 h-4 " style={{ color: "var(--muted-foreground)" }} />
                ) : (
                  <ChevronRight className="w-4 h-4 " style={{ color: "var(--muted-foreground)" }} />
                )}
              </div>

              {/* Group info */}
              <div className="flex-1 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono  px-2 py-1 rounded " style={{ color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-elevated)" }}>
                    Group {groupIdx}
                  </span>
                  <span className="text-sm " style={{ color: "var(--foreground-secondary)" }}>
                    {group.tools.length} tool{group.tools.length !== 1 ? 's' : ''}
                  </span>
                  {group.parallel_execution && (
                    <div className="px-2 py-1 rounded text-[10px] bg-emerald-900/30 text-emerald-300">
                      Parallel
                    </div>
                  )}
                </div>

                {/* Dependency info if not first group */}
                {groupIdx > 0 && group.tools[0]?.dependency_groups.length > 0 && (
                  <span className="text-[10px] " style={{ color: "var(--muted-foreground)" }}>
                    Depends on group{group.tools[0].dependency_groups.length !== 1 ? 's' : ''}{' '}
                    {group.tools[0].dependency_groups.map((g) => `${g}`).join(', ')}
                  </span>
                )}
              </div>
            </button>

            {/* Group content - tools */}
            {expandedGroups.includes(groupIdx) && (
              <div className="border-t /50 px-4 py-3 space-y-2 /30" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                {group.tools.map((tool, toolIdx) => (
                  <div
                    key={toolIdx}
                    onClick={() => onToolSelect?.(tool.tool_id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedTool === tool.tool_id
                        ? 'bg-blue-900/30 border-blue-400/50 ring-1 ring-blue-400/30'
                        : ' /30 hover:/50 hover:'
                    }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                  >
                    {/* Tool header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono " style={{ color: "var(--foreground)" }}>{tool.tool_id}</span>
                        <span className="px-2 py-1 rounded text-[10px]   border /50" style={{ borderColor: "var(--border)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-overlay)" }}>
                          {tool.tool_type}
                        </span>
                      </div>
                      <span className="text-[10px] " style={{ color: "var(--muted-foreground)" }}>#{toolIdx + 1}</span>
                    </div>

                    {/* Tool details */}
                    {(tool.depends_on.length > 0 || Object.keys(tool.output_mapping).length > 0) && (
                      <div className="space-y-1 text-xs " style={{ color: "var(--muted-foreground)" }}>
                        {/* Dependencies */}
                        {tool.depends_on.length > 0 && (
                          <div className="flex gap-2">
                            <span className="" style={{ color: "var(--muted-foreground)" }}>Depends on:</span>
                            <span className="" style={{ color: "var(--foreground-secondary)" }}>{tool.depends_on.join(', ')}</span>
                          </div>
                        )}

                        {/* Data flow mappings */}
                        {Object.keys(tool.output_mapping).length > 0 && (
                          <div className="flex gap-2">
                            <span className="" style={{ color: "var(--muted-foreground)" }}>Data flow:</span>
                            <span className="" style={{ color: "var(--foreground-secondary)" }}>{Object.keys(tool.output_mapping).length} mapping(s)</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary footer */}
      <div className="flex items-center justify-between text-xs  border-t /30 pt-3" style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" }}>
        <span>
          {trace.total_groups} group{trace.total_groups !== 1 ? 's' : ''} • {trace.total_tools} tool
          {trace.total_tools !== 1 ? 's' : ''}
        </span>
        {!hasExpandedGroups && (
          <span className="" style={{ color: "var(--muted-foreground)" }}>Click to expand groups</span>
        )}
      </div>
    </div>
  );
}

export type { OrchestrationTrace, ExecutionGroup, Tool, OrchestrationVisualizationProps };
