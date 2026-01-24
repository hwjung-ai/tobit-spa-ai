/**
 * Utility functions for computing differences between two execution traces
 * Handles 6 main sections: Applied Assets, Plan, Tool Calls, References, Answer Blocks, UI Render
 * Maintains security/masking policies from existing codebase
 */

export interface DiffItem<T> {
  changeType: "added" | "removed" | "modified" | "unchanged";
  before?: T;
  after?: T;
  changes?: Record<string, { before: unknown; after: unknown }>;
}

export interface AssetInfo {
  asset_id?: string;
  name?: string;
  version?: string;
  source?: string;
  scope?: string;
  engine?: string;
  policy_type?: string;
  mapping_type?: string;
}

export interface AssetsDiff {
  prompt: DiffItem<AssetInfo>;
  policy: DiffItem<AssetInfo>;
  mapping: DiffItem<AssetInfo>;
  queries: DiffItem<AssetInfo[]>;
}

export interface PlanDiff {
  changeType: "same" | "modified";
  raw?: {
    changeType: "same" | "modified";
    changes?: { [key: string]: { before: unknown; after: unknown } };
  };
  validated?: {
    changeType: "same" | "modified";
    changes?: { [key: string]: { before: unknown; after: unknown } };
  };
}

export interface ToolCallsDiff {
  added: Array<{ tool_name: string; summary: string }>;
  removed: Array<{ tool_name: string; summary: string }>;
  modified: Array<{
    tool_name: string;
    changes: { [key: string]: { before: unknown; after: unknown } };
  }>;
  unchanged: number;
}

export interface ReferencesDiff {
  total_before: number;
  total_after: number;
  byType: {
    [type: string]: {
      before: string[];
      after: string[];
      added: string[];
      removed: string[];
    };
  };
}

export interface AnswerBlocksDiff {
  block_count_before: number;
  block_count_after: number;
  blocks: Array<{
    index: number;
    changeType: "added" | "removed" | "modified" | "unchanged";
    before?: { type: string; title?: string };
    after?: { type: string; title?: string };
    changes?: { [key: string]: { before: unknown; after: unknown } };
  }>;
}

export interface UIRenderDiff {
  component_count_before: number;
  component_count_after: number;
  error_count_before: number;
  error_count_after: number;
  changes: Array<{
    index: number;
    changeType: "added" | "removed" | "modified" | "unchanged";
    before?: { block_type: string; component_name: string; ok: boolean };
    after?: { block_type: string; component_name: string; ok: boolean };
    changes?: { [key: string]: { before: unknown; after: unknown } };
  }>;
}

export interface TraceDiff {
  applied_assets: AssetsDiff;
  plan: PlanDiff;
  tool_calls: ToolCallsDiff;
  references: ReferencesDiff;
  answer_blocks: AnswerBlocksDiff;
  ui_render: UIRenderDiff;
  summary: {
    total_changes: number;
    sections_with_changes: string[];
  };
}

/**
 * Compare two asset objects (prompt, policy, mapping, query)
 */
function compareAssets(before: AssetInfo | null | undefined, after: AssetInfo | null | undefined): DiffItem<AssetInfo> {
  if (!before && !after) {
    return { changeType: "unchanged" };
  }

  if (!before) {
    return { changeType: "added", after };
  }

  if (!after) {
    return { changeType: "removed", before };
  }

  // Both exist - check if modified
  const beforeKey = `${before.asset_id || before.name}@${before.version || "?"}`;
  const afterKey = `${after.asset_id || after.name}@${after.version || "?"}`;

  if (beforeKey === afterKey) {
    return { changeType: "unchanged", before };
  }

  // Modified
  const changes: Record<string, { before: unknown; after: unknown }> = {};
  if (before.version !== after.version) {
    changes.version = { before: before.version, after: after.version };
  }
  if (before.name !== after.name) {
    changes.name = { before: before.name, after: after.name };
  }
  if (before.source !== after.source) {
    changes.source = { before: before.source, after: after.source };
  }

  return { changeType: "modified", before, after, changes };
}

/**
 * Diff Applied Assets section
 */
export function diffAppliedAssets(traceA: unknown, traceB: unknown): AssetsDiff {
  const traceObjA = traceA as Record<string, unknown>;
  const traceObjB = traceB as Record<string, unknown>;
  const assetsA = (traceObjA.applied_assets as Record<string, unknown>) || {};
  const assetsB = (traceObjB.applied_assets as Record<string, unknown>) || {};

  return {
    prompt: compareAssets(assetsA.prompt as AssetInfo | null, assetsB.prompt as AssetInfo | null),
    policy: compareAssets(assetsA.policy as AssetInfo | null, assetsB.policy as AssetInfo | null),
    mapping: compareAssets(assetsA.mapping as AssetInfo | null, assetsB.mapping as AssetInfo | null),
    queries: compareQueryArrays((assetsA.queries as AssetInfo[]) || [], (assetsB.queries as AssetInfo[]) || []),
  };
}

/**
 * Compare query arrays with element matching
 */
function compareQueryArrays(
  before: AssetInfo[],
  after: AssetInfo[]
): DiffItem<AssetInfo[]> {
  if (before.length === 0 && after.length === 0) {
    return { changeType: "unchanged" };
  }

  if (before.length === 0) {
    return { changeType: "added", after };
  }

  if (after.length === 0) {
    return { changeType: "removed", before };
  }

  // Simple matching by index + name
  const beforeNames = before.map((q) => q.name || q.asset_id || "?");
  const afterNames = after.map((q) => q.name || q.asset_id || "?");

  if (JSON.stringify(beforeNames) === JSON.stringify(afterNames)) {
    return { changeType: "unchanged", before };
  }

  return { changeType: "modified", before, after };
}

/**
 * Deep compare two objects by keys (simplified)
 */
function deepCompareObjects(before: unknown, after: unknown): Record<string, { before: unknown; after: unknown }> {
  const changes: Record<string, { before: unknown; after: unknown }> = {};

  if (!before || !after) {
    return changes;
  }

  const beforeObj = before as Record<string, unknown>;
  const afterObj = after as Record<string, unknown>;

  // Compare keys in both objects
  const allKeys = new Set([...Object.keys(beforeObj), ...Object.keys(afterObj)]);

  for (const key of allKeys) {
    const valBefore = beforeObj[key];
    const valAfter = afterObj[key];

    if (JSON.stringify(valBefore) !== JSON.stringify(valAfter)) {
      changes[key] = { before: valBefore, after: valAfter };
    }
  }

  return changes;
}

/**
 * Diff Plan section (raw + validated)
 */
export function diffPlan(traceA: unknown, traceB: unknown): PlanDiff {
  const planA = traceA as Record<string, unknown>;
  const planB = traceB as Record<string, unknown>;

  const validatedA = planA.plan_validated;
  const validatedB = planB.plan_validated;

  const validatedChanges = deepCompareObjects(validatedA, validatedB);
  const validatedChangeType = Object.keys(validatedChanges).length > 0 ? "modified" : "same";

  const rawA = planA.plan_raw;
  const rawB = planB.plan_raw;

  const rawChanges = deepCompareObjects(rawA, rawB);
  const rawChangeType = Object.keys(rawChanges).length > 0 ? "modified" : "same";

  return {
    changeType: validatedChangeType === "modified" || rawChangeType === "modified" ? "modified" : "same",
    validated:
      Object.keys(validatedChanges).length > 0
        ? {
            changeType: "modified",
            changes: validatedChanges,
          }
        : { changeType: "same" },
    raw:
      Object.keys(rawChanges).length > 0
        ? {
            changeType: "modified",
            changes: rawChanges,
          }
        : { changeType: "same" },
  };
}

/**
 * Build signature for tool call matching (tool_name + partial params)
 */
function buildToolSignature(toolCall: Record<string, unknown>): string {
  const tool = toolCall.tool_name || toolCall.step_id || "unknown";
  const params = toolCall.request ? JSON.stringify(toolCall.request).substring(0, 50) : "";
  return `${tool}::${params}`;
}

/**
 * Match tool calls between two execution_steps arrays
 */
function matchToolCalls(before: Record<string, unknown>[], after: Record<string, unknown>[]): Map<number, number> {
  const matches = new Map<number, number>();

  // Greedy matching by signature
  for (let i = 0; i < before.length; i++) {
    const sigBefore = buildToolSignature(before[i]);
    for (let j = 0; j < after.length; j++) {
      if (matches.has(j)) continue; // Already matched
      const sigAfter = buildToolSignature(after[j]);
      if (sigBefore === sigAfter) {
        matches.set(i, j);
        break;
      }
    }
  }

  return matches;
}

/**
 * Summarize tool call for diff display (with masking)
 */
function summarizeToolCall(toolCall: Record<string, unknown>): string {
  const tool = toolCall.tool_name || toolCall.step_id || "?";
  const duration = toolCall.duration_ms || 0;
  const status = toolCall.status || "?";

  // Mask sensitive request params
  let requestSummary = "";
  if (toolCall.request) {
    const masked = maskSensitiveParams(toolCall.request);
    requestSummary = ` [${JSON.stringify(masked).substring(0, 50)}...]`;
  }

  return `${tool} (${duration}ms, ${status})${requestSummary}`;
}

/**
 * Mask sensitive parameters in request/response objects
 */
function maskSensitiveParams(obj: unknown): unknown {
  if (!obj || typeof obj !== "object") {
    return obj;
  }

  const masked = { ...obj };
  const sensitiveKeys = ["password", "token", "secret", "api_key", "auth", "credential"];

  for (const key of Object.keys(masked)) {
    if (sensitiveKeys.some((sk) => key.toLowerCase().includes(sk))) {
      masked[key] = "[MASKED]";
    } else if (typeof masked[key] === "object") {
      masked[key] = maskSensitiveParams(masked[key]);
    }
  }

  return masked;
}

/**
 * Diff Tool Calls section (execution_steps)
 */
export function diffToolCalls(traceA: unknown, traceB: unknown): ToolCallsDiff {
  const traceObjA = traceA as Record<string, unknown>;
  const traceObjB = traceB as Record<string, unknown>;
  const stepsA = (traceObjA.execution_steps as Record<string, unknown>[]) || [];
  const stepsB = (traceObjB.execution_steps as Record<string, unknown>[]) || [];

  const matches = matchToolCalls(stepsA, stepsB);

  const added: Array<{ tool_name: string; summary: string }> = [];
  const removed: Array<{ tool_name: string; summary: string }> = [];
  const modified: Array<{ tool_name: string; changes: { [key: string]: { before: unknown; after: unknown } } }> = [];
  let unchanged = 0;

  // Process matched steps
  const matchedAfterIndices = new Set(matches.values());
  for (const [beforeIdx, afterIdx] of matches.entries()) {
    const stepBefore = stepsA[beforeIdx];
    const stepAfter = stepsB[afterIdx];

    const changes = deepCompareObjects(stepBefore, stepAfter);
    if (Object.keys(changes).length === 0) {
      unchanged++;
    } else {
      modified.push({
        tool_name: stepBefore.tool_name || stepBefore.step_id || "?",
        changes,
      });
    }
  }

  // Removed: in A but not matched
  for (let i = 0; i < stepsA.length; i++) {
    if (!matches.has(i)) {
      removed.push({
        tool_name: stepsA[i].tool_name || stepsA[i].step_id || "?",
        summary: summarizeToolCall(stepsA[i]),
      });
    }
  }

  // Added: in B but not matched
  for (let j = 0; j < stepsB.length; j++) {
    if (!matchedAfterIndices.has(j)) {
      added.push({
        tool_name: stepsB[j].tool_name || stepsB[j].step_id || "?",
        summary: summarizeToolCall(stepsB[j]),
      });
    }
  }

  return {
    added,
    removed,
    modified,
    unchanged,
  };
}

/**
 * Diff References section
 */
export function diffReferences(traceA: unknown, traceB: unknown): ReferencesDiff {
  const traceObjA = traceA as Record<string, unknown>;
  const traceObjB = traceB as Record<string, unknown>;
  const refsA = (traceObjA.references as Record<string, unknown>[]) || [];
  const refsB = (traceObjB.references as Record<string, unknown>[]) || [];

  const byType: Record<string, { before: string[]; after: string[]; added: string[]; removed: string[] }> = {};

  // Group references by type
  const typesBefore = new Set(refsA.map((r: Record<string, unknown>) => r.ref_type));
  const typesAfter = new Set(refsB.map((r: Record<string, unknown>) => r.ref_type));
  const allTypes = new Set([...typesBefore, ...typesAfter]);

  for (const type of allTypes) {
    const refsBefore = refsA.filter((r: Record<string, unknown>) => r.ref_type === type).map((r: Record<string, unknown>) => (r.name || r.statement) as string || "?");
    const refsAfter = refsB.filter((r: Record<string, unknown>) => r.ref_type === type).map((r: Record<string, unknown>) => (r.name || r.statement) as string || "?");

    const added = refsAfter.filter((r) => !refsBefore.includes(r));
    const removed = refsBefore.filter((r) => !refsAfter.includes(r));

    byType[type] = {
      before: refsBefore,
      after: refsAfter,
      added,
      removed,
    };
  }

  return {
    total_before: refsA.length,
    total_after: refsB.length,
    byType,
  };
}

/**
 * Match answer blocks by stable keys (type + index)
 */
function matchAnswerBlocks(before: Record<string, unknown>[], after: Record<string, unknown>[]): Map<number, number> {
  const matches = new Map<number, number>();

  for (let i = 0; i < before.length; i++) {
    const blockBefore = before[i];
    for (let j = 0; j < after.length; j++) {
      if (matches.has(j)) continue;
      const blockAfter = after[j];
      // Match by type (primary) + index proximity (secondary)
      if (blockBefore.type === blockAfter.type && Math.abs(i - j) <= 1) {
        matches.set(i, j);
        break;
      }
    }
  }

  return matches;
}

/**
 * Diff Answer Blocks section
 */
export function diffAnswerBlocks(traceA: unknown, traceB: unknown): AnswerBlocksDiff {
  const traceObjA = traceA as Record<string, unknown>;
  const traceObjB = traceB as Record<string, unknown>;
  const answerA = traceObjA.answer as Record<string, unknown> | undefined;
  const answerB = traceObjB.answer as Record<string, unknown> | undefined;
  const blocksA = (answerA?.blocks as Record<string, unknown>[]) || [];
  const blocksB = (answerB?.blocks as Record<string, unknown>[]) || [];

  const matches = matchAnswerBlocks(blocksA, blocksB);

  const blocks: AnswerBlocksDiff["blocks"] = [];
  const matchedAfterIndices = new Set(matches.values());

  // Process matched blocks
  for (const [beforeIdx, afterIdx] of matches.entries()) {
    const blockBefore = blocksA[beforeIdx];
    const blockAfter = blocksB[afterIdx];

    const changes = deepCompareObjects(blockBefore, blockAfter);
    const changeType = Object.keys(changes).length === 0 ? "unchanged" : "modified";

    blocks.push({
      index: beforeIdx,
      changeType,
      before: { type: blockBefore.type as string, title: blockBefore.title as string | undefined },
      after: { type: blockAfter.type as string, title: blockAfter.title as string | undefined },
      changes: Object.keys(changes).length > 0 ? changes : undefined,
    });
  }

  // Removed blocks
  for (let i = 0; i < blocksA.length; i++) {
    if (!matches.has(i)) {
      blocks.push({
        index: i,
        changeType: "removed",
        before: { type: blocksA[i].type as string, title: blocksA[i].title as string | undefined },
      });
    }
  }

  // Added blocks
  for (let j = 0; j < blocksB.length; j++) {
    if (!matchedAfterIndices.has(j)) {
      blocks.push({
        index: j,
        changeType: "added",
        after: { type: blocksB[j].type as string, title: blocksB[j].title as string | undefined },
      });
    }
  }

  // Sort by original index
  blocks.sort((a, b) => a.index - b.index);

  return {
    block_count_before: blocksA.length,
    block_count_after: blocksB.length,
    blocks,
  };
}

/**
 * Diff UI Render section
 */
export function diffUIRender(traceA: unknown, traceB: unknown): UIRenderDiff {
  const traceObjA = traceA as Record<string, unknown>;
  const traceObjB = traceB as Record<string, unknown>;
  const renderA = (traceObjA.ui_render as Record<string, unknown>) || {};
  const renderB = (traceObjB.ui_render as Record<string, unknown>) || {};

  const componentsA = (renderA.rendered_blocks as Record<string, unknown>[]) || [];
  const componentsB = (renderB.rendered_blocks as Record<string, unknown>[]) || [];

  const errorsBefore = componentsA.filter((c: Record<string, unknown>) => !c.ok).length;
  const errorsAfter = componentsB.filter((c: Record<string, unknown>) => !c.ok).length;

  const changes: UIRenderDiff["changes"] = [];

  // Simple comparison by index
  const maxLen = Math.max(componentsA.length, componentsB.length);
  for (let i = 0; i < maxLen; i++) {
    const compBefore = componentsA[i];
    const compAfter = componentsB[i];

    if (!compBefore && compAfter) {
      changes.push({
        index: i,
        changeType: "added",
        after: compAfter as { block_type: string; component_name: string; ok: boolean },
      });
    } else if (compBefore && !compAfter) {
      changes.push({
        index: i,
        changeType: "removed",
        before: compBefore as { block_type: string; component_name: string; ok: boolean },
      });
    } else if (compBefore && compAfter) {
      const diff = deepCompareObjects(compBefore, compAfter);
      const changeType = Object.keys(diff).length === 0 ? "unchanged" : "modified";

      if (changeType === "modified") {
        changes.push({
          index: i,
          changeType: "modified",
          before: compBefore as { block_type: string; component_name: string; ok: boolean },
          after: compAfter as { block_type: string; component_name: string; ok: boolean },
          changes: diff,
        });
      }
    }
  }

  return {
    component_count_before: componentsA.length,
    component_count_after: componentsB.length,
    error_count_before: errorsBefore,
    error_count_after: errorsAfter,
    changes: changes.filter((c) => c.changeType !== "unchanged"),
  };
}

/**
 * Compute complete diff between two traces
 */
export function computeTraceDiff(traceA: unknown, traceB: unknown): TraceDiff {
  const applied_assets = diffAppliedAssets(traceA, traceB);
  const plan = diffPlan(traceA, traceB);
  const tool_calls = diffToolCalls(traceA, traceB);
  const references = diffReferences(traceA, traceB);
  const answer_blocks = diffAnswerBlocks(traceA, traceB);
  const ui_render = diffUIRender(traceA, traceB);

  // Count total changes
  const sections_with_changes: string[] = [];
  let total_changes = 0;

  if (applied_assets.prompt.changeType !== "unchanged") {
    sections_with_changes.push("Applied Assets");
    total_changes++;
  }
  if (applied_assets.policy.changeType !== "unchanged") {
    if (!sections_with_changes.includes("Applied Assets")) {
      sections_with_changes.push("Applied Assets");
    }
    total_changes++;
  }
  if (applied_assets.mapping.changeType !== "unchanged") {
    if (!sections_with_changes.includes("Applied Assets")) {
      sections_with_changes.push("Applied Assets");
    }
    total_changes++;
  }
  if (applied_assets.queries.changeType !== "unchanged") {
    if (!sections_with_changes.includes("Applied Assets")) {
      sections_with_changes.push("Applied Assets");
    }
    total_changes++;
  }

  if (plan.changeType === "modified") {
    sections_with_changes.push("Plan");
    total_changes += Object.keys(plan.validated?.changes || {}).length + Object.keys(plan.raw?.changes || {}).length;
  }

  if (tool_calls.added.length > 0 || tool_calls.removed.length > 0 || tool_calls.modified.length > 0) {
    sections_with_changes.push("Tool Calls");
    total_changes += tool_calls.added.length + tool_calls.removed.length + tool_calls.modified.length;
  }

  if (
    Object.values(references.byType).some(
      (rt) => rt.added.length > 0 || rt.removed.length > 0
    )
  ) {
    sections_with_changes.push("References");
    total_changes += Object.values(references.byType).reduce(
      (sum, rt) => sum + rt.added.length + rt.removed.length,
      0
    );
  }

  if (answer_blocks.blocks.length > 0) {
    sections_with_changes.push("Answer Blocks");
    total_changes += answer_blocks.blocks.length;
  }

  if (ui_render.changes.length > 0 || ui_render.error_count_before !== ui_render.error_count_after) {
    sections_with_changes.push("UI Render");
    total_changes += ui_render.changes.length;
  }

  return {
    applied_assets,
    plan,
    tool_calls,
    references,
    answer_blocks,
    ui_render,
    summary: {
      total_changes,
      sections_with_changes: [...new Set(sections_with_changes)],
    },
  };
}