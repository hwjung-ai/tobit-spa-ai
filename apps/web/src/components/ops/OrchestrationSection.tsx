'use client';

import React, { useState } from 'react';
import { OrchestrationVisualization } from './OrchestrationVisualization';
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
    <section className="rounded-2xl border p-5 space-y-3 border-variant bg-surface-overlay">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <p className="text-tiny uppercase tracking-wider text-muted-foreground">Orchestration</p>
          {orchestrationTrace && (
            <span className="text-tiny text-muted-foreground">
              {orchestrationTrace.total_groups} group{orchestrationTrace.total_groups !== 1 ? 's' : ''} •{' '}
              {orchestrationTrace.total_tools} tool{orchestrationTrace.total_tools !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* View mode toggle */}
        {orchestrationTrace && (
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex gap-1 rounded-lg p-1 bg-surface-base">
              <button
                onClick={() => {
                  setViewMode('timeline');
                  setSelectedTool(undefined);
                }}
                className={`px-3 py-1 rounded text-tiny uppercase tracking-wider transition-colors ${
                  viewMode === 'timeline'
                    ? 'bg-sky-600 text-white'
                    : 'bg-surface-elevated text-muted-foreground hover:bg-surface-overlay'
                }`}
              >
                Timeline
              </button>
              <button
                onClick={() => {
                  setViewMode('graph');
                  setSelectedTool(undefined);
                }}
                className={`px-3 py-1 rounded text-tiny uppercase tracking-wider transition-colors ${
                  viewMode === 'graph'
                    ? 'bg-sky-600 text-white'
                    : 'bg-surface-elevated text-muted-foreground hover:bg-surface-overlay'
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
            <div className="rounded-lg p-4 space-y-3 border-variant bg-surface-base">
              <div className="text-sm font-semibold text-foreground">Tool: {selectedTool}</div>

              {orchestrationTrace.execution_groups.map((group) => {
                const tool = group.tools.find((t) => t.tool_id === selectedTool);
                if (!tool) return null;

                return (
                  <div key={selectedTool} className="space-y-3 text-xs text-muted-foreground">
                    <div>
                      <p className="font-semibold mb-1 text-muted-foreground">Type</p>
                      <p className="text-foreground">{tool.tool_type}</p>
                    </div>

                    {tool.depends_on.length > 0 && (
                      <div>
                        <p className="font-semibold mb-1 text-muted-foreground">Dependencies</p>
                        <div className="flex flex-wrap gap-2">
                          {tool.depends_on.map((dep) => (
                            <span
                              key={dep}
                              className="px-2 py-1 rounded bg-sky-900/30 text-sky-300 border border-sky-400/30"
                            >
                              {dep}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {Object.keys(tool.output_mapping).length > 0 && (
                      <div>
                        <p className="font-semibold mb-1 text-muted-foreground">Data Flow Mappings</p>
                        <div className="space-y-1">
                          {Object.entries(tool.output_mapping).map(([key, value]) => (
                            <div key={key} className="flex items-start gap-2">
                              <span className="font-mono text-muted-foreground">{key}:</span>
                              <code className="text-emerald-400 font-mono break-all">{value as string}</code>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div>
                      <p className="font-semibold mb-1 text-muted-foreground">Execution Group</p>
                      <p className="text-foreground">Group {group.group_index}</p>
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
