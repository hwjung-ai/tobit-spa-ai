/*
  Binding Engine v2 - Template rendering with expression support
  - Supports: {{inputs.x}}, {{state.x}}, {{context.x}}, {{trace_id}}
  - Dot-path binding (v1) + safe expression evaluation (v2)
  - Expression syntax: {{sum(state.items, 'value')}}, {{state.x > 10 ? 'high' : 'low'}}
  - Provides helpers to apply action result, props binding, loading/error state
*/

export type BindingContext = {
  inputs?: Record<string, unknown>;
  state?: Record<string, unknown>;
  context?: Record<string, unknown>;
  trace_id?: string | null;
};

export type BindingState = Record<string, unknown>;

/** Check if an expression contains function calls, operators, or ternary */
function isExpression(inner: string): boolean {
  return /[()!?:+\-*/<>=|&]/.test(inner);
}

/** Safely evaluate an expression string */
let _expressionParser: typeof import("./expression-parser") | null = null;
let _expressionEvaluator: typeof import("./expression-evaluator") | null = null;

function safeEvalExpression(expr: string, ctx: BindingContext): unknown {
  try {
    // Lazy load to keep v1 paths fast
    if (!_expressionParser) _expressionParser = require("./expression-parser"); // eslint-disable-line @typescript-eslint/no-require-imports
    if (!_expressionEvaluator) _expressionEvaluator = require("./expression-evaluator"); // eslint-disable-line @typescript-eslint/no-require-imports
    const ast = _expressionParser!.parseExpression(expr);
    return _expressionEvaluator!.evaluate(ast, ctx);
  } catch {
    // Fallback: return null on parse/eval error (graceful degradation)
    return null;
  }
}

export function renderTemplate(template: unknown, ctx: BindingContext) {
  if (template == null) return template;
  if (typeof template === "string") {
    const exactMatch = template.match(/^{{\s*([^}]+)\s*}}$/);
    if (exactMatch) {
      const inner = exactMatch[1].trim();
      // v2: check for expression syntax
      if (isExpression(inner)) {
        return safeEvalExpression(inner, ctx);
      }
      return resolvePath(inner, ctx);
    }
    return template.replace(/{{\s*([^}]+)\s*}}/g, (_match: string, expr: string): string => {
      const trimmed = expr.trim();
      // v2: expression in inline interpolation
      if (isExpression(trimmed)) {
        const result = safeEvalExpression(trimmed, ctx);
        return result != null ? String(result) : "";
      }
      const parts = trimmed.split(".");
      const root = parts[0];
      const path = parts.slice(1).join(".");
      if (root === "inputs") return String(get(ctx.inputs || {}, path) ?? "");
      if (root === "state") return String(get(ctx.state || {}, path) ?? "");
      if (root === "context") return String(get(ctx.context || {}, path) ?? "");
      if (root === "trace_id") return ctx.trace_id ?? "";
      return "";
    });
  }
  if (Array.isArray(template)) {
    return template.map((t) => renderTemplate(t, ctx));
  }
  if (typeof template === "object") {
    const out: unknown = {};
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

export function applyActionResultToState(state: BindingState, actionId: string, result: unknown) {
  const results = state.results || {};
  results[actionId] = result;
  state.results = results;
  if (result && typeof result === "object") {
    const resultObj = result as { state_patch?: Record<string, unknown> };
    if (resultObj.state_patch) {
      Object.keys(resultObj.state_patch).forEach((key) => {
        set(state, key, resultObj.state_patch![key]);
      });
    }
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

export function get(obj: unknown, path?: string) {
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

export function set(obj: unknown, path: string, value: unknown) {
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
