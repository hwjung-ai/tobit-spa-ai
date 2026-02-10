/*
  Binding Path Utilities for U3-1
  - Extract available paths from state/context/inputs schemas
  - Build hierarchical tree structure for PathPicker UI
  - Validate binding expressions and paths
  - Parse and format binding expressions
*/

import { ScreenSchemaV1, StateSchema, StateSchemaPrimitive } from "./screen.schema";

/**
 * Represents a hierarchical node in the path tree
 * Used by PathPicker UI for dropdown/tree selection
 */
export interface PathTreeNode {
  name: string; // Display name (e.g., "device_id")
  fullPath: string; // Complete path (e.g., "state.device_id")
  children?: PathTreeNode[]; // Nested properties (for objects)
  type?: string; // JSON type hint (string, number, boolean, object, array)
  isLeaf?: boolean; // True if this is a selectable leaf node
}

/**
 * Parse a binding expression like "{{state.device_id}}" into components
 * Returns null if format is invalid
 */
export function parseBindingExpression(
  expr: string
): { source: string; path: string } | null {
  if (!expr) return null;

  // Match {{source.path}} pattern
  const match = expr.match(/^\{\{(\w+)(\.[\w.]+)?\}\}$/);
  if (!match) return null;

  const source = match[1];
  const path = match[2] ? match[2].substring(1) : ""; // Remove leading dot

  return { source, path };
}

/**
 * Format a source and path into a binding expression
 * Example: source="state", path="device_id" → "{{state.device_id}}"
 */
export function formatBindingExpression(
  source: string,
  path: string
): string {
  if (!path) {
    return `{{${source}}}`;
  }
  return `{{${source}.${path}}}`;
}

/**
 * Check if a binding expression is in valid format
 */
export function isValidBindingExpression(expr: string): boolean {
  return parseBindingExpression(expr) !== null;
}

/**
 * Extract all available state paths from a StateSchema
 * Returns flat array of dot-separated paths
 */
export function extractStatePaths(schema?: StateSchema): string[] {
  if (!schema) return [];

  const paths: string[] = [];

  function traverse(obj: StateSchemaPrimitive | Record<string, unknown>, prefix: string = "") {
    if (!obj) return;

    // Handle both StateSchemaPrimitive and Record<string, unknown>
    // StateSchemaPrimitive has { type, properties, items }
    // Record<string, unknown> is raw object from extractSchemaFromInitial
    const schemaPrim = obj as StateSchemaPrimitive;
    const type = schemaPrim.type;
    
    // Only traverse if it's a StateSchemaPrimitive with object or array type
    if (type === "object" && schemaPrim.properties) {
      Object.keys(schemaPrim.properties).forEach((key) => {
        const newPrefix = prefix ? `${prefix}.${key}` : key;
        paths.push(newPrefix);
        traverse(schemaPrim.properties[key] as StateSchemaPrimitive | Record<string, unknown>, newPrefix);
      });
    } else if (type === "array") {
      const newPrefix = prefix ? `${prefix}[]` : "[]";
      paths.push(newPrefix);
      // Don't traverse array items as they're typically data
    } else if (!type) {
      // This is a Record<string, unknown> from extractSchemaFromInitial
      const record = obj as Record<string, unknown>;
      Object.keys(record).forEach((key) => {
        const newPrefix = prefix ? `${prefix}.${key}` : key;
        paths.push(newPrefix);
        traverse(record[key] as StateSchemaPrimitive | Record<string, unknown>, newPrefix);
      });
    }
  }

  // Schema is a Record<string, StateSchemaPrimitive>, traverse it directly
  Object.keys(schema).forEach((key) => {
    paths.push(key);
    traverse(schema[key], key);
  });
  
  return paths;
}

/**
 * Extract all available context paths
 * Usually comes from inputs schema or fixed structure
 */
export function extractContextPaths(contextSchema?: unknown): string[] {
  if (!contextSchema) {
    // Default context paths from runtime
    return ["user_id", "user_email", "tenant_id", "permissions"];
  }

  return extractStatePaths(contextSchema as StateSchema);
}

/**
 * Extract all available inputs paths
 */
export function extractInputsPaths(inputsSchema?: unknown): string[] {
  if (!inputsSchema) return [];
  return extractStatePaths(inputsSchema as StateSchema);
}

/**
 * Build a hierarchical tree structure for state paths
 * Used by PathPicker dropdown UI
 */
export function buildPathTree(paths: string[]): PathTreeNode[] {
  const tree: Map<string, PathTreeNode> = new Map();

  paths.forEach((path) => {
    const parts = path.split(".");
    let currentPrefix = "";

    parts.forEach((part, index) => {
      const isLast = index === parts.length - 1;
      const nodePath = currentPrefix ? `${currentPrefix}.${part}` : part;

      if (!tree.has(nodePath)) {
        tree.set(nodePath, {
          name: part,
          fullPath: nodePath,
          type: isLast ? "leaf" : "object",
          isLeaf: isLast,
          children: [],
        });
      }

      // Link parent to child
      if (currentPrefix) {
        const parent = tree.get(currentPrefix);
        if (parent && !parent.children?.some((c) => c.fullPath === nodePath)) {
          parent.children?.push(tree.get(nodePath)!);
        }
      }

      currentPrefix = nodePath;
    });
  });

  // Return root nodes only (no parent prefix)
  return Array.from(tree.values()).filter((node) => !node.fullPath.includes("."));
}

/**
 * Get available source prefixes based on schema
 * Returns { state, context, inputs, trace_id }
 */
export function getAvailableSources(
  screen?: ScreenSchemaV1
): {
  state: PathTreeNode[];
  context: PathTreeNode[];
  inputs: PathTreeNode[];
} {
  const statePaths = screen?.state?.schema
    ? extractStatePaths(screen.state.schema)
    : [];
  const contextPaths = extractContextPaths();
  const inputsPaths = screen?.state?.schema
    ? extractInputsPaths()
    : [];

  return {
    state: buildPathTree(statePaths),
    context: buildPathTree(contextPaths),
    inputs: buildPathTree(inputsPaths),
  };
}

/**
 * Validate if a path exists in a schema
 * Returns true if path is valid
 */
export function isValidPath(path: string, schema?: StateSchema): boolean {
  if (!schema || !path) return false;

  const parts = path.split(".");
  let current: StateSchemaPrimitive | undefined;

  // First, get the root key
  const rootKey = parts[0];
  if (!rootKey) return false;
  
  current = schema[rootKey];
  if (!current) return false;

  // Navigate through nested parts (if any)
  for (let i = 1; i < parts.length; i++) {
    const part = parts[i];
    
    if (!current) return false;
    
    if (current.type === "object" && current.properties) {
      // For object type, look in properties
      current = current.properties[part] as StateSchemaPrimitive | undefined;
    } else if (current.type === "array" && current.items) {
      // For array type, look in items (if items is an object)
      // Handle case where items is a StateSchema or a direct StateSchemaPrimitive
      if (typeof current.items === "object" && !Array.isArray(current.items)) {
        // items is a StateSchema (nested object)
        const itemsSchema = current.items as Record<string, StateSchemaPrimitive>;
        current = itemsSchema[part] as StateSchemaPrimitive | undefined;
      } else {
        // items is a StateSchemaPrimitive (primitive array)
        return false; // Can't index into primitive array
      }
    } else {
      // Can't navigate further into primitive types
      return false;
    }
  }

  return true;
}

/**
 * Get the type hint for a path
 */
export function getPathType(path: string, schema?: StateSchema): string {
  if (!schema || !path) return "any";

  const parts = path.split(".");
  let current: StateSchemaPrimitive | undefined;

  // Get root key
  const rootKey = parts[0];
  if (!rootKey) return "any";
  
  current = schema[rootKey];
  if (!current) return "unknown";

  // Navigate through nested parts (if any)
  for (let i = 1; i < parts.length; i++) {
    const part = parts[i];
    
    if (!current) return "unknown";
    
    if (current.type === "object" && current.properties) {
      current = current.properties[part] as StateSchemaPrimitive | undefined;
    } else if (current.type === "array" && current.items) {
      if (typeof current.items === "object" && !Array.isArray(current.items)) {
        const itemsSchema = current.items as Record<string, StateSchemaPrimitive>;
        current = itemsSchema[part] as StateSchemaPrimitive | undefined;
      } else {
        return "array";
      }
    } else {
      return current.type || "any";
    }
  }

  return current?.type || "any";
}

/**
 * Extract all binding expressions from an object/map
 * Recursively searches for {{...}} patterns
 */
export function extractBindingsFromObject(obj: unknown): string[] {
  const bindings: Set<string> = new Set();

  function traverse(value: unknown) {
    if (typeof value === "string") {
      const parsed = parseBindingExpression(value);
      if (parsed) {
        bindings.add(value);
      }
    } else if (Array.isArray(value)) {
      value.forEach(traverse);
    } else if (value !== null && typeof value === "object") {
      Object.values(value).forEach(traverse);
    }
  }

  traverse(obj);
  return Array.from(bindings);
}

/**
 * Render a payload template by substituting binding expressions
 * Returns the rendered object with actual values
 * Note: This is for preview/validation only. Runtime binding is done differently.
 */
export function renderPayloadTemplate(
  template: unknown,
  context: {
    state?: unknown;
    inputs?: unknown;
    context?: unknown;
    trace_id?: string;
  }
): unknown {
  if (typeof template === "string") {
    const parsed = parseBindingExpression(template);
    if (parsed) {
      const { source, path } = parsed;

      if (source === "trace_id") {
        return context.trace_id;
      }

      const sourceObj = context[source as keyof typeof context];
      if (!sourceObj || !path) return template;

      const parts = path.split(".");
      let value: unknown = sourceObj;

      for (const part of parts) {
        if (value && typeof value === "object") {
          value = value[part];
        } else {
          return template;
        }
      }

      return value;
    }
    return template;
  } else if (Array.isArray(template)) {
    return template.map((item) =>
      renderPayloadTemplate(item, context)
    );
  } else if (template !== null && typeof template === "object") {
    const result: unknown = {};
    for (const [key, value] of Object.entries(template)) {
      result[key] = renderPayloadTemplate(value, context);
    }
    return result;
  }

  return template;
}

/**
 * Get all referenced paths in a binding
 * Useful for detecting dependencies
 */
export function getReferencedPaths(binding: string): string[] {
  const parsed = parseBindingExpression(binding);
  if (!parsed) return [];

  const { source, path } = parsed;
  if (!path) {
    return [`${source}`];
  }

  // Return all prefixes of the path (for dependency tracking)
  const paths: string[] = [];
  const parts = path.split(".");

  for (let i = 1; i <= parts.length; i++) {
    paths.push(`${source}.${parts.slice(0, i).join(".")}`);
  }

  return paths;
}

/**
 * Check for circular dependencies in bindings
 * Returns array of circular dependency paths if found
 */
export function detectCircularBindings(
  bindings: Record<string, string>
): string[] {
  const graph: Map<string, Set<string>> = new Map();

  // Build dependency graph
  for (const [target, source] of Object.entries(bindings)) {
    if (!graph.has(target)) graph.set(target, new Set());
    if (!graph.has(source)) graph.set(source, new Set());

    graph.get(target)!.add(source);
  }

  // Detect cycles using DFS
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const cycles: string[] = [];

  function hasCycle(node: string, path: string[]): boolean {
    visited.add(node);
    recursionStack.add(node);
    path.push(node);

    const neighbors = graph.get(node) || new Set();
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (hasCycle(neighbor, path)) {
          return true;
        }
      } else if (recursionStack.has(neighbor)) {
        // Found a cycle
        cycles.push(path.join(" → ") + ` → ${neighbor}`);
        return true;
      }
    }

    recursionStack.delete(node);
    return false;
  }

  for (const node of graph.keys()) {
    if (!visited.has(node)) {
      hasCycle(node, []);
    }
  }

  return cycles;
}
