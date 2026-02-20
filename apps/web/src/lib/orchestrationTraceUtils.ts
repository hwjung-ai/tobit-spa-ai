/**
 * Orchestration Trace Utilities
 *
 * Utilities for working with Phase 5 orchestration traces in the Inspector UI
 */

import type { OrchestrationTrace, ExecutionGroup, Tool } from '@/components/ops/OrchestrationVisualization';

/**
 * Extract orchestration_trace from stage output
 */
export function extractOrchestrationTrace(stageOutput: Record<string, unknown>): OrchestrationTrace | null {
  if (!stageOutput) return null;

  // Check for orchestration_trace field
  if (stageOutput.orchestration_trace) {
    return stageOutput.orchestration_trace as OrchestrationTrace;
  }

  // Fallback: check if trace is nested in execution results
  if (stageOutput.execution_results && Array.isArray(stageOutput.execution_results)) {
    // Try to extract from first result that has orchestration metadata
    for (const result of stageOutput.execution_results) {
      if (result.orchestration) {
        // Construct trace from individual step metadata
        return constructTraceFromStepMetadata(stageOutput.execution_results);
      }
    }
  }

  // Legacy fallback: nested base_result.execution_results
  if (
    stageOutput.base_result &&
    typeof stageOutput.base_result === "object" &&
    (stageOutput.base_result as Record<string, unknown>).execution_results &&
    Array.isArray((stageOutput.base_result as Record<string, unknown>).execution_results)
  ) {
    const executionResults = (stageOutput.base_result as Record<string, unknown>)
      .execution_results as Record<string, unknown>[];
    for (const result of executionResults) {
      if (result.orchestration) {
        return constructTraceFromStepMetadata(executionResults);
      }
    }
  }

  return null;
}

/**
 * Construct orchestration trace from step-level metadata
 */
function constructTraceFromStepMetadata(results: Record<string, unknown>[]): OrchestrationTrace {
  const groups: Map<number, Tool[]> = new Map();
  let strategy: OrchestrationTrace["strategy"] = "serial";
  const tools = new Set<string>();

  for (const result of results) {
    if (result.orchestration && typeof result.orchestration === "object") {
      const orchestration = result.orchestration as Record<string, unknown>;
      const groupIndex =
        typeof orchestration.group_index === "number" ? orchestration.group_index : 0;
      const toolId =
        typeof orchestration.tool_id === "string" ? orchestration.tool_id : null;
      const toolType =
        typeof orchestration.tool_type === "string" ? orchestration.tool_type : "unknown";
      const dependsOn = Array.isArray(orchestration.depends_on)
        ? orchestration.depends_on.filter((v): v is string => typeof v === "string")
        : [];
      const rawOutputMapping =
        orchestration.output_mapping && typeof orchestration.output_mapping === "object"
          ? (orchestration.output_mapping as Record<string, unknown>)
          : {};
      const outputMapping: Record<string, string> = {};
      for (const [key, value] of Object.entries(rawOutputMapping)) {
        if (typeof value === "string") {
          outputMapping[key] = value;
        }
      }

      if (!toolId) continue;

      tools.add(toolId);

      if (!groups.has(groupIndex)) {
        groups.set(groupIndex, []);
      }

      groups.get(groupIndex)!.push({
        tool_id: toolId,
        tool_type: toolType,
        depends_on: dependsOn,
        dependency_groups: [],
        output_mapping: outputMapping,
      });
    }
  }

  // Build execution groups from map
  const executionGroups: ExecutionGroup[] = [];
  const sortedGroupIndices = Array.from(groups.keys()).sort((a, b) => a - b);

  for (const groupIndex of sortedGroupIndices) {
    const groupTools = groups.get(groupIndex)!;

    // Recalculate dependency_groups for each tool
    for (const tool of groupTools) {
      tool.dependency_groups = calculateDependencyGroups(
        tool.tool_id,
        tool.depends_on,
        groups,
        groupIndex
      );
    }

    executionGroups.push({
      group_index: groupIndex,
      tools: groupTools,
      parallel_execution: groupTools.length > 1,
    });

    // Infer strategy from group structure
    if (groupTools.length > 1) {
      strategy = 'dag';
    }
  }

  return {
    strategy,
    execution_groups: executionGroups,
    total_groups: executionGroups.length,
    total_tools: tools.size,
    tool_ids: Array.from(tools),
  };
}

/**
 * Calculate which groups a tool's dependencies are in
 */
function calculateDependencyGroups(
  toolId: string,
  depends_on: string[],
  groups: Map<number, Tool[]>,
  currentGroupIndex: number
): number[] {
  const depGroups = new Set<number>();

  for (const dependency of depends_on) {
    for (const [groupIndex, groupTools] of groups.entries()) {
      if (groupIndex < currentGroupIndex && groupTools.some((t) => t.tool_id === dependency)) {
        depGroups.add(groupIndex);
        break;
      }
    }
  }

  return Array.from(depGroups).sort((a, b) => a - b);
}

/**
 * Validate orchestration trace structure
 */
export function isValidOrchestrationTrace(obj: unknown): obj is OrchestrationTrace {
  if (!obj || typeof obj !== "object") return false;
  const candidate = obj as Record<string, unknown>;

  return (
    typeof candidate.strategy === 'string' &&
    ['parallel', 'serial', 'dag'].includes(candidate.strategy) &&
    Array.isArray(candidate.execution_groups) &&
    typeof candidate.total_groups === 'number' &&
    typeof candidate.total_tools === 'number' &&
    Array.isArray(candidate.tool_ids)
  );
}

/**
 * Get execution strategy description
 */
export function getStrategyDescription(strategy: string): string {
  switch (strategy) {
    case 'parallel':
      return 'All tools execute simultaneously with no dependencies';
    case 'serial':
      return 'Tools execute sequentially with automatic data flow between them';
    case 'dag':
      return 'Complex execution with multiple independent branches and convergence points';
    default:
      return 'Unknown execution strategy';
  }
}

/**
 * Get execution strategy emoji badge
 */
export function getStrategyBadge(strategy: string): {
  emoji: string;
  label: string;
  color: string;
} {
  switch (strategy) {
    case 'parallel':
      return {
        emoji: '⚡',
        label: 'Parallel',
        color: 'bg-emerald-900/40 text-emerald-200 border-emerald-400/50',
      };
    case 'dag':
      return {
        emoji: '🔀',
        label: 'Complex DAG',
        color: 'bg-blue-900/40 text-blue-200 border-blue-400/50',
      };
    case 'serial':
    default:
      return {
        emoji: '🔗',
        label: 'Sequential',
        color: 'bg-amber-900/40 text-amber-200 border-amber-400/50',
      };
  }
}

/**
 * Calculate total duration for execution group (sum of all tool durations)
 */
export function calculateGroupDuration(
  group: ExecutionGroup,
  toolDurations: Map<string, number>
): number {
  if (group.parallel_execution) {
    // For parallel execution, duration is max of all tools
    let maxDuration = 0;
    for (const tool of group.tools) {
      maxDuration = Math.max(maxDuration, toolDurations.get(tool.tool_id) || 0);
    }
    return maxDuration;
  } else {
    // For sequential execution, duration is sum of all tools
    let totalDuration = 0;
    for (const tool of group.tools) {
      totalDuration += toolDurations.get(tool.tool_id) || 0;
    }
    return totalDuration;
  }
}

/**
 * Format duration in milliseconds to readable string
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  } else if (ms < 60000) {
    return `${(ms / 1000).toFixed(2)}s`;
  } else {
    return `${(ms / 60000).toFixed(2)}m`;
  }
}

/**
 * Get tool color based on type
 */
export function getToolTypeColor(toolType: string): {
  bg: string;
  border: string;
  text: string;
} {
  switch (toolType) {
    case 'ci_lookup':
      return {
        bg: 'bg-blue-900/20',
        border: 'border-blue-400/50',
        text: 'text-blue-300',
      };
    case 'ci_aggregate':
      return {
        bg: 'bg-emerald-900/20',
        border: 'border-emerald-400/50',
        text: 'text-emerald-300',
      };
    case 'graph_analysis':
      return {
        bg: 'bg-purple-900/20',
        border: 'border-purple-400/50',
        text: 'text-purple-300',
      };
    case 'metric':
      return {
        bg: 'bg-amber-900/20',
        border: 'border-amber-400/50',
        text: 'text-amber-300',
      };
    case 'mcp':
      return {
        bg: 'bg-cyan-900/20',
        border: 'border-cyan-400/50',
        text: 'text-cyan-300',
      };
    default:
      return {
        bg: 'bg-surface-overlay',
        border: 'border-border',
        text: 'text-foreground-secondary',
      };
  }
}

/**
 * Generate a human-readable report of orchestration execution
 */
export function generateOrchestrationReport(trace: OrchestrationTrace): string {
  const lines: string[] = [];

  lines.push(`Execution Strategy: ${trace.strategy.toUpperCase()}`);
  lines.push(`Description: ${getStrategyDescription(trace.strategy)}`);
  lines.push('');
  lines.push(`Execution Plan:`);
  lines.push(`  Total Groups: ${trace.total_groups}`);
  lines.push(`  Total Tools: ${trace.total_tools}`);
  lines.push('');

  for (const group of trace.execution_groups) {
    lines.push(`Group ${group.group_index}${group.parallel_execution ? ' (Parallel)' : ''}:`);
    for (const tool of group.tools) {
      lines.push(`  - ${tool.tool_id} (${tool.tool_type})`);
      if (tool.depends_on.length > 0) {
        lines.push(`    Depends on: ${tool.depends_on.join(', ')}`);
      }
      if (Object.keys(tool.output_mapping).length > 0) {
        lines.push(`    Data flow: ${Object.keys(tool.output_mapping).length} mapping(s)`);
      }
    }
  }

  return lines.join('\n');
}
