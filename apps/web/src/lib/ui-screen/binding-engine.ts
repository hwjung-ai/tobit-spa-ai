/*
  Binding Engine v1 - Template rendering and dot-path binding
  - Supports: {{inputs.x}}, {{state.x}}, {{context.x}}, {{trace_id}}
  - Dot-path only, no expression evaluation
  - Provides helpers to apply action result, props binding, loading/error state
*/

export type BindingContext = {
  inputs?: Record<string, any>;
  state?: Record<string, any>;
  context?: Record<string, any>;
  trace_id?: string | null;
};

export type BindingState = Record<string, any>;

export function renderTemplate(template: any, ctx: BindingContext) {
  if (template == null) return template;
  if (typeof template === "string") {
    const exactMatch = template.match(/^{{\s*([^}]+)\s*}}$/);
    if (exactMatch) {
      return resolvePath(exactMatch[1].trim(), ctx);
    }
    return template.replace(/{{\s*([^}]+)\s*}}/g, (_, expr) => {
      const parts = expr.split(".");
      const root = parts[0];
      const path = parts.slice(1).join(".");
      if (root === "inputs") return get(ctx.inputs || {}, path) ?? "";
      if (root === "state") return get(ctx.state || {}, path) ?? "";
      if (root === "context") return get(ctx.context || {}, path) ?? "";
      if (root === "trace_id") return ctx.trace_id ?? "";
      return "";
    });
  }
  if (Array.isArray(template)) {
    return template.map((t) => renderTemplate(t, ctx));
  }
  if (typeof template === "object") {
    const out: any = {};
    for (const k of Object.keys(template)) {
      out[k] = renderTemplate(template[k], ctx);
    }
    return out;
  }
  return template;
}

export function applyBindings(
  state: BindingState,
  bindings: Record<string, string> | null | undefined,
  ctx: BindingContext
) {
  if (!bindings) return;
  for (const targetPath of Object.keys(bindings)) {
    const sourcePath = bindings[targetPath];
    const value = resolvePath(sourcePath, ctx);
    set(state, targetPath, value);
  }
}

export function applyActionResultToState(state: BindingState, actionId: string, result: any) {
  const results = state.results || {};
  results[actionId] = result;
  state.results = results;
  if (result && typeof result === "object" && result.state_patch) {
    Object.keys(result.state_patch).forEach((key) => {
      set(state, key, result.state_patch[key]);
    });
  }
}

export function setLoading(state: BindingState, actionId: string, loading: boolean) {
  const loadingMap = state.__loading || {};
  loadingMap[actionId] = loading;
  state.__loading = loadingMap;
}

export function setError(state: BindingState, actionId: string, error: string | null) {
  const errorMap = state.__error || {};
  errorMap[actionId] = error;
  state.__error = errorMap;
}

function resolvePath(path: string, ctx: BindingContext) {
  if (path.startsWith("state.")) return get(ctx.state || {}, path.replace("state.", ""));
  if (path.startsWith("inputs.")) return get(ctx.inputs || {}, path.replace("inputs.", ""));
  if (path.startsWith("context.")) return get(ctx.context || {}, path.replace("context.", ""));
  if (path === "trace_id") return ctx.trace_id ?? null;
  return get(ctx.state || {}, path);
}

/**
 * Parse dot-path notation with array index support
 * Examples:
 *   "state.device"          → ["state", "device"]
 *   "state.items[0].name"   → ["state", "items", "0", "name"]
 *   "state.nested[2].id"    → ["state", "nested", "2", "id"]
 *   "state.length"          → ["state", "length"] (array.length property)
 */
function parsePathWithIndices(path: string): string[] {
  if (!path) return [];

  const parts: string[] = [];
  let current = "";
  let i = 0;

  while (i < path.length) {
    const char = path[i];

    if (char === ".") {
      if (current) {
        parts.push(current);
        current = "";
      }
      i++;
    } else if (char === "[") {
      if (current) {
        parts.push(current);
        current = "";
      }
      // Extract index: [0], [1], etc.
      i++;
      let index = "";
      while (i < path.length && path[i] !== "]") {
        index += path[i];
        i++;
      }
      if (path[i] === "]") {
        parts.push(index);
        i++;
      }
      // Skip the "." after "]" if present
      if (path[i] === ".") {
        i++;
      }
    } else {
      current += char;
      i++;
    }
  }

  if (current) {
    parts.push(current);
  }

  return parts;
}

export function get(obj: any, path?: string) {
  if (!path) return undefined;
  const parts = parsePathWithIndices(path);
  let cur = obj;
  for (const p of parts) {
    if (cur == null) return undefined;
    // Try to parse as array index (numeric string)
    const idx = parseInt(p, 10);
    if (!isNaN(idx) && Array.isArray(cur)) {
      cur = cur[idx];
    } else {
      cur = cur[p];
    }
  }
  return cur;
}

export function set(obj: any, path: string, value: any) {
  const parts = parsePathWithIndices(path);
  if (parts.length === 0) return;

  let cur = obj;
  for (const p of parts.slice(0, -1)) {
    const idx = parseInt(p, 10);
    if (!isNaN(idx)) {
      // Array index
      if (!Array.isArray(cur)) {
        cur = [];
      }
      if (cur[idx] == null) {
        cur[idx] = {};
      }
      cur = cur[idx];
    } else {
      // Object property
      if (cur[p] == null || typeof cur[p] !== "object") {
        cur[p] = {};
      }
      cur = cur[p];
    }
  }

  const lastPart = parts[parts.length - 1];
  const lastIdx = parseInt(lastPart, 10);
  if (!isNaN(lastIdx) && Array.isArray(cur)) {
    cur[lastIdx] = value;
  } else {
    cur[lastPart] = value;
  }
}
