/**
 * Utility functions for computing differences between two ScreenSchemaV1 objects
 * Adapted from traceDiffUtils.ts patterns for Screen-specific comparison
 * Handles: Components, Actions, Bindings, State Schema
 */

import { ScreenSchemaV1, Component } from "./screen.schema";

export interface DiffItem {
  changeType: "added" | "removed" | "modified" | "unchanged";
  path: string;
  before?: unknown;
  after?: unknown;
  changes?: Record<string, { before: unknown; after: unknown }>;
}

export interface ComponentDiffItem extends DiffItem {
  componentId?: string;
  componentType?: string;
}

export interface ActionDiffItem extends DiffItem {
  actionId?: string;
  handler?: string;
}

export interface BindingDiffItem extends DiffItem {
  componentId?: string;
  propertyPath?: string;
}

export interface StateSchemaDiffItem extends DiffItem {
  fieldName?: string;
  fieldType?: string;
}

export interface ScreenDiff {
  summary: {
    added: number;
    removed: number;
    modified: number;
    unchanged: number;
  };
  components: ComponentDiffItem[];
  actions: ActionDiffItem[];
  bindings: BindingDiffItem[];
  state: StateSchemaDiffItem[];
}

/**
 * Deep equality check for any two values
 */
function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a == null || b == null) return a === b;
  if (typeof a !== "object" || typeof b !== "object") return false;

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);

  if (keysA.length !== keysB.length) return false;

  for (const key of keysA) {
    if (!keysB.includes(key) || !deepEqual(a[key], b[key])) {
      return false;
    }
  }

  return true;
}

/**
 * Detect changes between two objects (shallow property level)
 * Returns object mapping changed properties to { before, after }
 */
function detectPropertyChanges(
  before: unknown,
  after: unknown
): Record<string, { before: unknown; after: unknown }> | undefined {
  if (!before || !after) return undefined;

  const changes: Record<string, { before: unknown; after: unknown }> = {};
  const allKeys = new Set([
    ...Object.keys(before as object || {}),
    ...Object.keys(after as object || {}),
  ]);

  for (const key of allKeys) {
    if (!deepEqual((before as Record<string, unknown>)?.[key], (after as Record<string, unknown>)?.[key])) {
      changes[key] = {
        before: (before as Record<string, unknown>)?.[key],
        after: (after as Record<string, unknown>)?.[key],
      };
    }
  }

  return Object.keys(changes).length > 0 ? changes : undefined;
}

/**
 * Compare components between two screens
 * Maps components by ID to detect add/remove/modify
 */
function compareComponents(
  before: ScreenSchemaV1 | null,
  after: ScreenSchemaV1
): ComponentDiffItem[] {
  const beforeMap = new Map(
    (before?.components || []).map((c) => [c.id, c])
  );
  const afterMap = new Map(after.components.map((c) => [c.id, c]));
  const allIds = new Set([...beforeMap.keys(), ...afterMap.keys()]);

  const items: ComponentDiffItem[] = [];

  for (const id of allIds) {
    const beforeComp = beforeMap.get(id);
    const afterComp = afterMap.get(id);

    if (!beforeComp) {
      items.push({
        changeType: "added",
        path: `components[${id}]`,
        componentId: id,
        componentType: afterComp?.type,
        after: afterComp,
      });
    } else if (!afterComp) {
      items.push({
        changeType: "removed",
        path: `components[${id}]`,
        componentId: id,
        componentType: beforeComp?.type,
        before: beforeComp,
      });
    } else {
      const changes = detectPropertyChanges(beforeComp, afterComp);
      if (changes) {
        items.push({
          changeType: "modified",
          path: `components[${id}]`,
          componentId: id,
          componentType: afterComp?.type,
          before: beforeComp,
          after: afterComp,
          changes,
        });
      } else {
        items.push({
          changeType: "unchanged",
          path: `components[${id}]`,
          componentId: id,
          componentType: afterComp?.type,
        });
      }
    }
  }

  return items;
}

/**
 * Compare screen-level actions
 */
function compareActions(
  before: ScreenSchemaV1 | null,
  after: ScreenSchemaV1
): ActionDiffItem[] {
  const beforeMap = new Map(
    (before?.actions || []).map((a) => [a.id, a])
  );
  const afterMap = new Map(
    (after?.actions || []).map((a) => [a.id, a])
  );
  const allIds = new Set([...beforeMap.keys(), ...afterMap.keys()]);

  const items: ActionDiffItem[] = [];

  for (const id of allIds) {
    const beforeAction = beforeMap.get(id);
    const afterAction = afterMap.get(id);

    if (!beforeAction) {
      items.push({
        changeType: "added",
        path: `actions[${id}]`,
        actionId: id,
        handler: afterAction?.handler,
        after: afterAction,
      });
    } else if (!afterAction) {
      items.push({
        changeType: "removed",
        path: `actions[${id}]`,
        actionId: id,
        handler: beforeAction?.handler,
        before: beforeAction,
      });
    } else {
      const changes = detectPropertyChanges(beforeAction, afterAction);
      if (changes) {
        items.push({
          changeType: "modified",
          path: `actions[${id}]`,
          actionId: id,
          handler: afterAction?.handler,
          before: beforeAction,
          after: afterAction,
          changes,
        });
      } else {
        items.push({
          changeType: "unchanged",
          path: `actions[${id}]`,
          actionId: id,
          handler: afterAction?.handler,
        });
      }
    }
  }

  return items;
}

/**
 * Extract all bindings from a component (props, visibility, etc.)
 */
function extractBindingsFromComponent(comp: Component): Array<{
  propertyPath: string;
  binding: string;
}> {
  const bindings: Array<{ propertyPath: string; binding: string }> = [];

  // Check props for bindings
  if (comp.props) {
    for (const [key, value] of Object.entries(comp.props)) {
      if (typeof value === "string" && value.includes("{{")) {
        bindings.push({ propertyPath: `props.${key}`, binding: value });
      }
    }
  }

  // Check visibility rule
  if (comp.visibility?.rule && typeof comp.visibility.rule === "string") {
    bindings.push({ propertyPath: "visibility.rule", binding: comp.visibility.rule });
  }

  // Check component actions for payload bindings
  if (comp.actions) {
    for (const action of comp.actions) {
      if (action.payload_template) {
        for (const [key, value] of Object.entries(action.payload_template)) {
          if (typeof value === "string" && value.includes("{{")) {
            bindings.push({
              propertyPath: `actions[${action.id}].payload.${key}`,
              binding: value,
            });
          }
        }
      }
    }
  }

  return bindings;
}

/**
 * Compare all bindings between screens
 */
function compareBindings(
  before: ScreenSchemaV1 | null,
  after: ScreenSchemaV1
): BindingDiffItem[] {
  const beforeBindings = new Map<string, string>();
  const afterBindings = new Map<string, string>();

  // Collect before bindings
  (before?.components || []).forEach((comp) => {
    extractBindingsFromComponent(comp).forEach(({ propertyPath, binding }) => {
      const key = `${comp.id}:${propertyPath}`;
      beforeBindings.set(key, binding);
    });
  });

  // Collect after bindings
  after.components.forEach((comp) => {
    extractBindingsFromComponent(comp).forEach(({ propertyPath, binding }) => {
      const key = `${comp.id}:${propertyPath}`;
      afterBindings.set(key, binding);
    });
  });

  const allKeys = new Set([...beforeBindings.keys(), ...afterBindings.keys()]);
  const items: BindingDiffItem[] = [];

  for (const key of allKeys) {
    const [componentId, propertyPath] = key.split(":");
    const beforeBinding = beforeBindings.get(key);
    const afterBinding = afterBindings.get(key);

    if (!beforeBinding) {
      items.push({
        changeType: "added",
        path: `${componentId}:${propertyPath}`,
        componentId,
        propertyPath,
        after: afterBinding,
      });
    } else if (!afterBinding) {
      items.push({
        changeType: "removed",
        path: `${componentId}:${propertyPath}`,
        componentId,
        propertyPath,
        before: beforeBinding,
      });
    } else if (beforeBinding !== afterBinding) {
      items.push({
        changeType: "modified",
        path: `${componentId}:${propertyPath}`,
        componentId,
        propertyPath,
        before: beforeBinding,
        after: afterBinding,
      });
    } else {
      items.push({
        changeType: "unchanged",
        path: `${componentId}:${propertyPath}`,
        componentId,
        propertyPath,
      });
    }
  }

  return items;
}

/**
 * Compare state schemas
 */
function compareState(
  before: ScreenSchemaV1 | null,
  after: ScreenSchemaV1
): StateSchemaDiffItem[] {
  const beforeSchema = before?.state?.schema || {};
  const afterSchema = after.state?.schema || {};
  const allFields = new Set([
    ...Object.keys(beforeSchema),
    ...Object.keys(afterSchema),
  ]);

  const items: StateSchemaDiffItem[] = [];

  for (const fieldName of allFields) {
    const beforeType = beforeSchema[fieldName];
    const afterType = afterSchema[fieldName];

    if (!beforeType) {
      items.push({
        changeType: "added",
        path: `state.schema[${fieldName}]`,
        fieldName,
        fieldType: afterType,
        after: afterType,
      });
    } else if (!afterType) {
      items.push({
        changeType: "removed",
        path: `state.schema[${fieldName}]`,
        fieldName,
        fieldType: beforeType,
        before: beforeType,
      });
    } else if (beforeType !== afterType) {
      items.push({
        changeType: "modified",
        path: `state.schema[${fieldName}]`,
        fieldName,
        before: beforeType,
        after: afterType,
      });
    } else {
      items.push({
        changeType: "unchanged",
        path: `state.schema[${fieldName}]`,
        fieldName,
        fieldType: afterType,
      });
    }
  }

  return items;
}

/**
 * Main comparison function
 * Compares before and after screens, returns structured diff
 */
export function compareScreens(
  before: ScreenSchemaV1 | null,
  after: ScreenSchemaV1
): ScreenDiff {
  const components = compareComponents(before, after);
  const actions = compareActions(before, after);
  const bindings = compareBindings(before, after);
  const state = compareState(before, after);

  const allItems = [...components, ...actions, ...bindings, ...state];
  const summary = {
    added: allItems.filter((i) => i.changeType === "added").length,
    removed: allItems.filter((i) => i.changeType === "removed").length,
    modified: allItems.filter((i) => i.changeType === "modified").length,
    unchanged: allItems.filter((i) => i.changeType === "unchanged").length,
  };

  return {
    summary,
    components,
    actions,
    bindings,
    state,
  };
}

/**
 * Helper: Get human-readable summary text
 */
export function getDiffSummaryText(diff: ScreenDiff): string {
  const { added, removed, modified } = diff.summary;
  const parts = [];

  if (added > 0) parts.push(`+${added} added`);
  if (removed > 0) parts.push(`-${removed} removed`);
  if (modified > 0) parts.push(`~${modified} modified`);

  return parts.join(", ") || "No changes";
}

/**
 * Helper: Check if there are any actual changes (ignoring unchanged items)
 */
export function hasChanges(diff: ScreenDiff): boolean {
  return diff.summary.added > 0 || diff.summary.removed > 0 || diff.summary.modified > 0;
}
