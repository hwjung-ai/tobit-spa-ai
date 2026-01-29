'use client';

import React, { useState } from 'react';
import { OrchestrationVisualization, type OrchestrationTrace } from './OrchestrationVisualization';
import { OrchestrationDependencyGraph } from './OrchestrationDependencyGraph';
import { extractOrchestrationTrace, isValidOrchestrationTrace } from '@/lib/orchestrationTraceUtils';

interface OrchestrationSectionProps {
  stageOutput: any;
}

/**
 * OrchestrationSection Component
 *
 * Displays orchestration visualization in Inspector detail drawer
 * Supports both timeline (hierarchical list) and graph (dependency graph) views
 */
export function OrchestrationSection({ stageOutput }: OrchestrationSectionProps) {
  const [viewMode, setViewMode] = useState<'timeline' | 'graph'>('timeline');
  const [selectedTool, setSelectedTool] = useState<string | undefined>();
  const [expandedGroups, setExpandedGroups] = useState<number[]>([]);

  // Extract orchestration trace from stage output
  const orchestrationTrace = extractOrchestrationTrace(stageOutput);

  if (!orchestrationTrace || !isValidOrchestrationTrace(orchestrationTrace)) {
    return null;
  }

  const handleGroupToggle = (groupIndex: number) => {
    setExpandedGroups((prev) =>
      prev.includes(groupIndex) ? prev.filter((g) => g !== groupIndex) : [...prev, groupIndex]
    );
  };

  return (
    <section className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Orchestration</p>
          {orchestrationTrace && (
            <span className="text-[10px] text-slate-400">
              {orchestrationTrace.total_groups} group{orchestrationTrace.total_groups !== 1 ? 's' : ''} •{' '}
              {orchestrationTrace.total_tools} tool{orchestrationTrace.total_tools !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* View mode toggle */}
        {orchestrationTrace && (
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex gap-1 bg-slate-950 rounded-lg p-1">
              <button
                onClick={() => {
                  setViewMode('timeline');
                  setSelectedTool(undefined);
                }}
                className={`px-3 py-1 rounded text-[10px] uppercase tracking-[0.2em] transition-colors ${
                  viewMode === 'timeline'
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                Timeline
              </button>
              <button
                onClick={() => {
                  setViewMode('graph');
                  setSelectedTool(undefined);
                }}
                className={`px-3 py-1 rounded text-[10px] uppercase tracking-[0.2em] transition-colors ${
                  viewMode === 'graph'
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                Graph
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      {orchestrationTrace && (
        <div className="space-y-4">
          {viewMode === 'timeline' ? (
            /* Timeline View */
            <OrchestrationVisualization
              trace={orchestrationTrace}
              expandedGroups={expandedGroups}
              onGroupToggle={handleGroupToggle}
              selectedTool={selectedTool}
              onToolSelect={setSelectedTool}
            />
          ) : (
            /* Graph View */
            <OrchestrationDependencyGraph
              trace={orchestrationTrace}
              selectedTool={selectedTool}
              onToolSelect={setSelectedTool}
            />
          )}

          {/* Tool Details Panel */}
          {selectedTool && (
            <div className="bg-slate-950/40 border border-slate-700/50 rounded-lg p-4 space-y-3">
              <div className="text-sm font-semibold text-slate-200">Tool: {selectedTool}</div>

              {orchestrationTrace.execution_groups.map((group) => {
                const tool = group.tools.find((t) => t.tool_id === selectedTool);
                if (!tool) return null;

                return (
                  <div key={selectedTool} className="space-y-3 text-xs text-slate-400">
                    <div>
                      <p className="text-slate-500 font-semibold mb-1">Type</p>
                      <p className="text-slate-300">{tool.tool_type}</p>
                    </div>

                    {tool.depends_on.length > 0 && (
                      <div>
                        <p className="text-slate-500 font-semibold mb-1">Dependencies</p>
                        <div className="flex flex-wrap gap-2">
                          {tool.depends_on.map((dep) => (
                            <span
                              key={dep}
                              className="px-2 py-1 rounded bg-blue-900/30 text-blue-300 border border-blue-400/30"
                            >
                              {dep}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {Object.keys(tool.output_mapping).length > 0 && (
                      <div>
                        <p className="text-slate-500 font-semibold mb-1">Data Flow Mappings</p>
                        <div className="space-y-1">
                          {Object.entries(tool.output_mapping).map(([key, value]) => (
                            <div key={key} className="flex items-start gap-2">
                              <span className="text-slate-500 font-mono">{key}:</span>
                              <code className="text-emerald-400 font-mono break-all">{value as string}</code>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div>
                      <p className="text-slate-500 font-semibold mb-1">Execution Group</p>
                      <p className="text-slate-300">Group {group.group_index}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export type { OrchestrationSectionProps };
