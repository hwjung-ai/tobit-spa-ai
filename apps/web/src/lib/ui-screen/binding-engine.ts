/**
 * Binding Engine v1 - Template rendering and dot-path binding
 *
 * This module provides a lightweight data binding system that supports template
 * rendering with dot-path notation and state management utilities. It enables
 * dynamic data binding between UI components and various data sources.
 *
 * Supported binding sources:
 * - `{{inputs.x}}` - Component input parameters
 * - `{{state.x}}` - Local component state
 * - `{{context.x}}` - Global context data
 * - `{{trace_id}}` - Current trace identifier
 *
 * Features:
 * - Template string interpolation with mustache-style syntax
 * - Dot-path notation with array index support (e.g., `items[0].name`)
 * - Recursive rendering for nested objects and arrays
 * - State management helpers for actions, loading, and error states
 * - No expression evaluation (pure path-based binding for security)
 *
 * @module binding-engine
 * @version 1.0
 */

/**
 * Context object containing all available binding sources.
 *
 * The binding context aggregates data from multiple sources that can be
 * referenced in templates using the mustache syntax `{{source.path}}`.
 *
 * @example
 * ```typescript
 * const context: BindingContext = {
 *   inputs: { userId: "123", name: "Alice" },
 *   state: { isLoggedIn: true, cart: [{ id: 1, qty: 2 }] },
 *   context: { theme: "dark", lang: "en" },
 *   trace_id: "trace-abc-123"
 * };
 * ```
 */
export type BindingContext = {
  /** Component input parameters passed from parent */
  inputs?: Record<string, any>;
  /** Local component state data */
  state?: Record<string, any>;
  /** Global application context shared across components */
  context?: Record<string, any>;
  /** Current trace identifier for debugging/logging */
  trace_id?: string | null;
};

/**
 * State object used by components to store local data.
 *
 * The binding state is a flexible key-value store that supports nested
 * objects and arrays. Special reserved keys include:
 * - `results` - Stores action execution results keyed by action ID
 * - `__loading` - Internal map tracking loading states by action ID
 * - `__error` - Internal map tracking error messages by action ID
 *
 * @example
 * ```typescript
 * const state: BindingState = {
 *   user: { name: "Alice", age: 30 },
 *   items: [{ id: 1, name: "Product A" }],
 *   results: { action1: { success: true } },
 *   __loading: { action1: false },
 *   __error: { action1: null }
 * };
 * ```
 */
export type BindingState = Record<string, any>;

/**
 * Renders a template by replacing binding expressions with values from the context.
 *
 * This function processes templates recursively, supporting:
 * - String interpolation with `{{path}}` syntax
 * - Exact value replacement for strings containing only a binding expression
 * - Recursive processing of nested objects and arrays
 * - Multiple bindings in a single string
 *
 * Binding resolution priority:
 * 1. `{{inputs.path}}` - Resolves from context.inputs
 * 2. `{{state.path}}` - Resolves from context.state
 * 3. `{{context.path}}` - Resolves from context.context
 * 4. `{{trace_id}}` - Resolves to context.trace_id
 *
 * @param template - The template to render. Can be a string, object, array, or primitive.
 * @param ctx - The binding context containing data sources.
 * @returns The rendered template with all bindings resolved.
 *
 * @example
 * ```typescript
 * // String interpolation
 * renderTemplate("Hello {{inputs.name}}!", { inputs: { name: "Alice" } });
 * // Returns: "Hello Alice!"
 *
 * // Exact value replacement (returns the actual value, not a string)
 * renderTemplate("{{state.user}}", { state: { user: { id: 1, name: "Bob" } } });
 * // Returns: { id: 1, name: "Bob" }
 *
 * // Array with dot-path and indices
 * renderTemplate("Item: {{state.items[0].name}}", { state: { items: [{ name: "Product A" }] } });
 * // Returns: "Item: Product A"
 *
 * // Object recursion
 * renderTemplate(
 *   { title: "{{inputs.title}}", count: "{{state.count}}" },
 *   { inputs: { title: "Dashboard" }, state: { count: 5 } }
 * );
 * // Returns: { title: "Dashboard", count: 5 }
 *
 * // Multiple bindings in one string
 * renderTemplate(
 *   "User {{inputs.name}} has {{state.points}} points",
 *   { inputs: { name: "Alice" }, state: { points: 100 } }
 * );
 * // Returns: "User Alice has 100 points"
 * ```
 */
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

/**
 * Applies a set of bindings to update state from context sources.
 *
 * This function maps values from the binding context to state properties using
 * a declarative binding configuration. Each binding maps a target path in state
 * to a source path in the context.
 *
 * The state object is mutated in place, with values resolved from the context
 * and set at the specified target paths using dot notation with array index support.
 *
 * @param state - The state object to update (mutated in place).
 * @param bindings - Map of target paths to source paths. If null/undefined, no action is taken.
 * @param ctx - The binding context containing source data.
 *
 * @example
 * ```typescript
 * const state: BindingState = {};
 * const bindings = {
 *   "currentUser": "inputs.user",
 *   "settings.theme": "context.theme",
 *   "items": "state.products"
 * };
 * const ctx: BindingContext = {
 *   inputs: { user: { id: 1, name: "Alice" } },
 *   context: { theme: "dark" },
 *   state: { products: [{ id: 101, name: "Product A" }] }
 * };
 *
 * applyBindings(state, bindings, ctx);
 *
 * // state is now:
 * // {
 * //   currentUser: { id: 1, name: "Alice" },
 * //   settings: { theme: "dark" },
 * //   items: [{ id: 101, name: "Product A" }]
 * // }
 * ```
 *
 * @example
 * ```typescript
 * // Array index binding
 * const state: BindingState = {};
 * const bindings = { "selectedItem": "state.items[0]" };
 * const ctx = { state: { items: [{ id: 1, name: "First" }] } };
 *
 * applyBindings(state, bindings, ctx);
 * // state.selectedItem = { id: 1, name: "First" }
 * ```
 */
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

/**
 * Applies an action result to the state, storing the result and applying any state patches.
 *
 * This function handles the side effects of action execution by:
 * 1. Storing the full action result in `state.results[actionId]`
 * 2. Applying any `state_patch` from the result to update state properties
 *
 * The `state_patch` is a flat or nested object where keys are dot-paths and values
 * are the new values to set. This allows actions to update multiple state properties
 * atomically.
 *
 * @param state - The state object to update (mutated in place).
 * @param actionId - Unique identifier for the action.
 * @param result - The action execution result, optionally containing a `state_patch` property.
 *
 * @example
 * ```typescript
 * const state: BindingState = { user: { name: "Alice" } };
 * const result = {
 *   success: true,
 *   data: { id: 123 },
 *   state_patch: {
 *     "user.id": 123,
 *     "lastUpdate": "2026-01-20T10:00:00Z"
 *   }
 * };
 *
 * applyActionResultToState(state, "fetchUser", result);
 *
 * // state is now:
 * // {
 * //   user: { name: "Alice", id: 123 },
 * //   lastUpdate: "2026-01-20T10:00:00Z",
 * //   results: {
 * //     fetchUser: {
 * //       success: true,
 * //       data: { id: 123 },
 * //       state_patch: { "user.id": 123, "lastUpdate": "2026-01-20T10:00:00Z" }
 * //     }
 * //   }
 * // }
 * ```
 *
 * @example
 * ```typescript
 * // Result without state_patch
 * const state: BindingState = {};
 * applyActionResultToState(state, "simpleAction", { value: 42 });
 *
 * // state.results.simpleAction = { value: 42 }
 * // No other state properties are modified
 * ```
 */
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

/**
 * Sets the loading state for a specific action.
 *
 * This function updates the internal `__loading` map in the state to track
 * which actions are currently executing. UI components can bind to these
 * loading states to show spinners or disable buttons.
 *
 * @param state - The state object to update (mutated in place).
 * @param actionId - Unique identifier for the action.
 * @param loading - Whether the action is currently loading.
 *
 * @example
 * ```typescript
 * const state: BindingState = {};
 *
 * // Start loading
 * setLoading(state, "fetchData", true);
 * // state.__loading = { fetchData: true }
 *
 * // Stop loading
 * setLoading(state, "fetchData", false);
 * // state.__loading = { fetchData: false }
 * ```
 *
 * @example
 * ```typescript
 * // Multiple concurrent actions
 * const state: BindingState = {};
 * setLoading(state, "action1", true);
 * setLoading(state, "action2", true);
 * // state.__loading = { action1: true, action2: true }
 *
 * setLoading(state, "action1", false);
 * // state.__loading = { action1: false, action2: true }
 * ```
 */
export function setLoading(state: BindingState, actionId: string, loading: boolean) {
  const loadingMap = state.__loading || {};
  loadingMap[actionId] = loading;
  state.__loading = loadingMap;
}

/**
 * Sets the error state for a specific action.
 *
 * This function updates the internal `__error` map in the state to track
 * error messages from failed actions. UI components can bind to these
 * error states to display error messages to users.
 *
 * @param state - The state object to update (mutated in place).
 * @param actionId - Unique identifier for the action.
 * @param error - Error message string, or null to clear the error.
 *
 * @example
 * ```typescript
 * const state: BindingState = {};
 *
 * // Set error
 * setError(state, "fetchData", "Network request failed");
 * // state.__error = { fetchData: "Network request failed" }
 *
 * // Clear error
 * setError(state, "fetchData", null);
 * // state.__error = { fetchData: null }
 * ```
 *
 * @example
 * ```typescript
 * // Typical action lifecycle with loading and error states
 * const state: BindingState = {};
 *
 * // Before action
 * setLoading(state, "saveUser", true);
 * setError(state, "saveUser", null);
 *
 * try {
 *   const result = await saveUserAPI();
 *   applyActionResultToState(state, "saveUser", result);
 *   setLoading(state, "saveUser", false);
 * } catch (err) {
 *   setError(state, "saveUser", err.message);
 *   setLoading(state, "saveUser", false);
 * }
 * ```
 */
export function setError(state: BindingState, actionId: string, error: string | null) {
  const errorMap = state.__error || {};
  errorMap[actionId] = error;
  state.__error = errorMap;
}

/**
 * Resolves a binding path to its value from the binding context.
 *
 * Internal helper that determines which context source to use based on the path prefix.
 * Falls back to `ctx.state` if no prefix matches.
 *
 * @internal
 * @param path - Binding path (e.g., "state.user.name", "inputs.id", "trace_id")
 * @param ctx - Binding context
 * @returns The resolved value or null/undefined if not found
 */
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

/**
 * Gets a value from an object using dot-path notation with array index support.
 *
 * This function safely traverses nested objects and arrays using a path string.
 * It supports:
 * - Dot notation: `"user.profile.name"`
 * - Array indices: `"items[0]"` or `"items[0].id"`
 * - Mixed notation: `"users[0].addresses[1].city"`
 * - Array properties: `"items.length"`
 *
 * Returns `undefined` if any part of the path is null/undefined.
 *
 * @param obj - The object to traverse.
 * @param path - Dot-path string with optional array indices. If undefined, returns undefined.
 * @returns The value at the path, or undefined if not found.
 *
 * @example
 * ```typescript
 * const data = {
 *   user: { name: "Alice", age: 30 },
 *   items: [
 *     { id: 1, name: "Item A" },
 *     { id: 2, name: "Item B" }
 *   ]
 * };
 *
 * get(data, "user.name");           // "Alice"
 * get(data, "user.age");            // 30
 * get(data, "items[0].name");       // "Item A"
 * get(data, "items[1].id");         // 2
 * get(data, "items.length");        // 2
 * get(data, "user.email");          // undefined
 * get(data, "items[5]");            // undefined
 * get(data, "items[0].tags[0]");    // undefined
 * ```
 *
 * @example
 * ```typescript
 * // Nested arrays
 * const data = {
 *   matrix: [
 *     [1, 2, 3],
 *     [4, 5, 6]
 *   ]
 * };
 *
 * get(data, "matrix[0][1]");  // 2
 * get(data, "matrix[1][2]");  // 6
 * ```
 */
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

/**
 * Sets a value on an object using dot-path notation with array index support.
 *
 * This function mutates the object in place, creating intermediate objects or
 * arrays as needed. It supports:
 * - Dot notation: `"user.profile.name"`
 * - Array indices: `"items[0]"` or `"items[0].id"`
 * - Mixed notation: `"users[0].addresses[1].city"`
 * - Auto-creates intermediate objects/arrays if they don't exist
 *
 * Array creation behavior:
 * - Numeric indices create arrays: `items[0]` creates an array
 * - Non-numeric keys create objects: `user.name` creates an object
 *
 * @param obj - The object to mutate.
 * @param path - Dot-path string with optional array indices.
 * @param value - The value to set at the path.
 *
 * @example
 * ```typescript
 * const data = {};
 *
 * // Simple property
 * set(data, "name", "Alice");
 * // data = { name: "Alice" }
 *
 * // Nested property (creates intermediate objects)
 * set(data, "user.profile.age", 30);
 * // data = { name: "Alice", user: { profile: { age: 30 } } }
 *
 * // Array index (creates array)
 * set(data, "items[0]", { id: 1, name: "Item A" });
 * // data.items = [{ id: 1, name: "Item A" }]
 *
 * // Nested array property
 * set(data, "items[0].qty", 5);
 * // data.items[0] = { id: 1, name: "Item A", qty: 5 }
 * ```
 *
 * @example
 * ```typescript
 * // Complex nested structure
 * const data = {};
 * set(data, "users[0].addresses[0].city", "New York");
 *
 * // data = {
 * //   users: [
 * //     {
 * //       addresses: [
 * //         { city: "New York" }
 * //       ]
 * //     }
 * //   ]
 * // }
 * ```
 *
 * @example
 * ```typescript
 * // Updating existing values
 * const data = { count: 5, items: [{ id: 1 }] };
 * set(data, "count", 10);          // Updates existing
 * set(data, "items[0].id", 99);    // Updates nested
 * // data = { count: 10, items: [{ id: 99 }] }
 * ```
 */
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
