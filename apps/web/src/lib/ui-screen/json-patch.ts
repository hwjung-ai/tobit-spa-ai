"use client";

/**
 * Minimal RFC6902 JSON Patch implementation tailored for ScreenSchema patches.
 * Supports: add, replace, remove with object keys and array indices (including '-' append).
 */

export type JsonPatchOperation =
  | { op: "add"; path: string; value: unknown }
  | { op: "replace"; path: string; value: unknown }
  | { op: "remove"; path: string };

type PathSegment = string;

function cloneDeep<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function parsePointer(path: string): PathSegment[] {
  if (!path || path[0] !== "/") {
    throw new Error(`Invalid JSON Pointer "${path}". Must start with "/"`);
  }
  if (path === "/") return [];
  return path
    .slice(1)
    .split("/")
    .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"));
}

function getParent(root: unknown, segments: PathSegment[]): { parent: unknown; key: string | null } {
  if (segments.length === 0) {
    return { parent: null, key: null };
  }

  let node = root as unknown;
  for (let i = 0; i < segments.length - 1; i++) {
    const segment = segments[i];

    if (Array.isArray(node)) {
      const index = segment === "-" ? node.length - 1 : parseInt(segment, 10);
      if (isNaN(index) || index < 0 || index >= node.length) {
        throw new Error(`Invalid array index "${segment}" while walking path`);
      }
      node = node[index];
      continue;
    }

    if (node && typeof node === "object") {
      const obj = node as Record<string, unknown>;
      if (!(segment in obj)) {
        throw new Error(`Path segment "${segment}" does not exist`);
      }
      node = obj[segment];
      continue;
    }

    throw new Error(`Cannot traverse path segment "${segment}"`);
  }

  const lastSegment = segments[segments.length - 1];
  if (node === undefined || node === null) {
    throw new Error("Cannot resolve parent for JSON Pointer");
  }

  return { parent: node, key: lastSegment };
}

function applySingleOp(doc: unknown, op: JsonPatchOperation): unknown {
  const segments = parsePointer(op.path);

  if (segments.length === 0) {
    if (op.op === "remove") {
      throw new Error("Removing entire document is not supported");
    }
    return cloneDeep(op.value);
  }

  const { parent, key } = getParent(doc, segments);
  if (parent === null || key === null) {
    throw new Error("Invalid JSON Patch target");
  }

  if (op.op === "remove") {
    if (Array.isArray(parent)) {
      const index = key === "-" ? parent.length - 1 : parseInt(key, 10);
      if (isNaN(index) || index < 0 || index >= parent.length) {
        throw new Error(`Invalid array index "${key}" for remove`);
      }
      parent.splice(index, 1);
      return doc;
    }

    const obj = parent as Record<string, unknown>;
    delete obj[key];
    return doc;
  }

  if (Array.isArray(parent)) {
    if (key === "-") {
      parent.push(op.value);
      return doc;
    }

    const index = parseInt(key, 10);
    if (isNaN(index) || index < 0 || index > parent.length) {
      throw new Error(`Invalid array index "${key}" for ${op.op}`);
    }

    if (op.op === "replace") {
      if (index >= parent.length) {
        throw new Error(`Array index "${key}" out of bounds for replace`);
      }
      parent[index] = op.value;
      return doc;
    }

    parent.splice(index, 0, op.value);
    return doc;
  }

  const obj = parent as Record<string, unknown>;
  obj[key] = op.value;
  return doc;
}

export function applyJsonPatch(doc: unknown, patch: JsonPatchOperation[]) {
  if (!Array.isArray(patch)) {
    throw new Error("Patch must be an array");
  }

  const worked = cloneDeep(doc);
  patch.forEach((op) => {
    applySingleOp(worked, op);
  });
  return worked;
}
