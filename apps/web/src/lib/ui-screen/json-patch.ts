"use client";

/**
 * Minimal RFC6902 JSON Patch implementation tailored for ScreenSchema patches.
 * Supports: add, replace, remove with object keys and array indices (including '-' append).
 *
 * Path syntax: "/components/0/props/content"
 */

export type JsonPatchOperation =
  | { op: "add"; path: string; value: any }
  | { op: "replace"; path: string; value: any }
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

function getParent(root: any, segments: PathSegment[]): { parent: any; key: string | number | null } {
  if (segments.length === 0) {
    return { parent: null, key: null };
  }

  let node = root;
  for (let i = 0; i < segments.length - 1; i++) {
    const segment = segments[i];
    if (Array.isArray(node)) {
      const index = segment === "-" ? node.length - 1 : parseInt(segment, 10);
      if (isNaN(index) || index < 0 || index >= node.length) {
        throw new Error(`Invalid array index "${segment}" while walking path`);
      }
      node = node[index];
    } else if (node && typeof node === "object") {
      if (!(segment in node)) {
        throw new Error(`Path segment "${segment}" does not exist`);
      }
      node = node[segment];
    } else {
      throw new Error(`Cannot traverse path segment "${segment}"`);
    }
  }

  const lastSegment = segments[segments.length - 1];
  if (node === undefined || node === null) {
    throw new Error("Cannot resolve parent for JSON Pointer");
  }

  return { parent: node, key: lastSegment };
}

function applySingleOp(doc: any, op: JsonPatchOperation) {
  const segments = parsePointer(op.path);
  if (segments.length === 0) {
    if (op.op === "remove") {
      throw new Error("Removing the entire document is not supported");
    }
    if (op.op === "replace" || op.op === "add") {
      return cloneDeep(op.value);
    }
  }

  const { parent, key } = getParent(doc, segments);
  if (parent === null || key === null) {
    throw new Error("Invalid JSON Patch target");
  }

  if (op.op === "remove") {
    if (Array.isArray(parent)) {
      const index = key === "-" ? parent.length - 1 : parseInt(String(key), 10);
      if (isNaN(index) || index < 0 || index >= parent.length) {
        throw new Error(`Invalid array index "${key}" for remove`);
      }
      parent.splice(index, 1);
      return;
    }
    delete parent[key];
    return;
  }

  if (Array.isArray(parent)) {
    const indexStr = String(key);
    if (indexStr === "-") {
      parent.push(op.value);
      return;
    }
    const index = parseInt(indexStr, 10);
    if (isNaN(index) || index < 0 || index > parent.length) {
      throw new Error(`Invalid array index "${indexStr}" for ${op.op}`);
    }
    if (op.op === "replace") {
      if (index >= parent.length) {
        throw new Error(`Array index "${index}" out of bounds for replace`);
      }
      parent[index] = op.value;
      return;
    }
    parent.splice(index, 0, op.value);
    return;
  }

  if (op.op === "add" || op.op === "replace") {
    parent[key] = op.value;
    return;
  }

  throw new Error(`Unsupported operation "${op.op}"`);
}

export function applyJsonPatch(doc: any, patch: JsonPatchOperation[]) {
  if (!Array.isArray(patch)) {
    throw new Error("Patch must be an array");
  }

  let worked = cloneDeep(doc);
  patch.forEach((op) => {
    applySingleOp(worked, op);
  });
  return worked;
}
