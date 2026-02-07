/**
 * Safe Functions Library for Expression Evaluation
 * All functions are statically whitelisted - no eval() or Function() used.
 * Array operations capped at 10,000 elements for DoS prevention.
 */

const MAX_ARRAY_SIZE = 10000;

function toNum(v: unknown): number {
  const n = Number(v);
  return isNaN(n) ? 0 : n;
}

function toStr(v: unknown): string {
  if (v == null) return "";
  return String(v);
}

function toArr(v: unknown): unknown[] {
  if (Array.isArray(v)) return v.slice(0, MAX_ARRAY_SIZE);
  return [];
}

function pluck(arr: unknown[], field: string): unknown[] {
  return arr.map(item => {
    if (item && typeof item === "object") return (item as Record<string, unknown>)[field];
    return undefined;
  });
}

// String functions
function uppercase(s: unknown): string { return toStr(s).toUpperCase(); }
function lowercase(s: unknown): string { return toStr(s).toLowerCase(); }
function trim(s: unknown): string { return toStr(s).trim(); }
function substring(s: unknown, start: unknown, end?: unknown): string {
  return end != null ? toStr(s).substring(toNum(start), toNum(end)) : toStr(s).substring(toNum(start));
}
function includes(s: unknown, search: unknown): boolean { return toStr(s).includes(toStr(search)); }
function startsWith(s: unknown, prefix: unknown): boolean { return toStr(s).startsWith(toStr(prefix)); }
function endsWith(s: unknown, suffix: unknown): boolean { return toStr(s).endsWith(toStr(suffix)); }
function replace(s: unknown, search: unknown, replacement: unknown): string {
  return toStr(s).replace(toStr(search), toStr(replacement));
}
function split(s: unknown, sep: unknown): string[] { return toStr(s).split(toStr(sep)); }
function join(arr: unknown, sep: unknown): string { return toArr(arr).map(toStr).join(toStr(sep)); }
function length(v: unknown): number {
  if (Array.isArray(v)) return v.length;
  return toStr(v).length;
}

// Number functions
function round(n: unknown, decimals?: unknown): number {
  const d = decimals != null ? toNum(decimals) : 0;
  const factor = Math.pow(10, d);
  return Math.round(toNum(n) * factor) / factor;
}
function ceil(n: unknown): number { return Math.ceil(toNum(n)); }
function floor(n: unknown): number { return Math.floor(toNum(n)); }
function abs(n: unknown): number { return Math.abs(toNum(n)); }

// Date functions
function now(): string { return new Date().toISOString(); }
function formatDate(date: unknown, format: unknown): string {
  const d = date instanceof Date ? date : new Date(toStr(date));
  if (isNaN(d.getTime())) return toStr(date);
  const fmt = toStr(format);
  const pad = (n: number) => n.toString().padStart(2, "0");
  return fmt
    .replace("YYYY", d.getFullYear().toString())
    .replace("MM", pad(d.getMonth() + 1))
    .replace("DD", pad(d.getDate()))
    .replace("HH", pad(d.getHours()))
    .replace("mm", pad(d.getMinutes()))
    .replace("ss", pad(d.getSeconds()));
}

// Collection / aggregation functions
function sum(arr: unknown, field?: unknown): number {
  const a = toArr(arr);
  const vals = field != null ? pluck(a, toStr(field)) : a;
  return vals.reduce<number>((acc, v) => acc + toNum(v), 0);
}
function avg(arr: unknown, field?: unknown): number {
  const a = toArr(arr);
  if (a.length === 0) return 0;
  return sum(arr, field) / a.length;
}
function min(arr: unknown, field?: unknown): number {
  const a = toArr(arr);
  const vals = field != null ? pluck(a, toStr(field)).map(toNum) : a.map(toNum);
  return vals.length === 0 ? 0 : Math.min(...vals);
}
function max(arr: unknown, field?: unknown): number {
  const a = toArr(arr);
  const vals = field != null ? pluck(a, toStr(field)).map(toNum) : a.map(toNum);
  return vals.length === 0 ? 0 : Math.max(...vals);
}
function count(arr: unknown): number { return toArr(arr).length; }
function first(arr: unknown): unknown { const a = toArr(arr); return a.length > 0 ? a[0] : null; }
function last(arr: unknown): unknown { const a = toArr(arr); return a.length > 0 ? a[a.length - 1] : null; }
function unique(arr: unknown, field?: unknown): unknown[] {
  const a = toArr(arr);
  if (field != null) {
    const seen = new Set<string>();
    return a.filter(item => {
      const key = toStr((item as Record<string, unknown>)[toStr(field)]);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  return [...new Set(a.map(toStr))];
}
function filter(arr: unknown, field: unknown, op: unknown, value: unknown): unknown[] {
  const a = toArr(arr);
  const f = toStr(field);
  const operator = toStr(op);
  return a.filter(item => {
    const v = (item && typeof item === "object") ? (item as Record<string, unknown>)[f] : item;
    switch (operator) {
      case "eq": case "==": return v == value;
      case "ne": case "!=": return v != value;
      case "gt": case ">": return toNum(v) > toNum(value);
      case "gte": case ">=": return toNum(v) >= toNum(value);
      case "lt": case "<": return toNum(v) < toNum(value);
      case "lte": case "<=": return toNum(v) <= toNum(value);
      case "contains": return toStr(v).includes(toStr(value));
      default: return false;
    }
  });
}
function map(arr: unknown, field: unknown): unknown[] {
  return pluck(toArr(arr), toStr(field));
}

// Utility functions
function coalesce(...args: unknown[]): unknown {
  for (const a of args) {
    if (a != null && a !== "") return a;
  }
  return null;
}
function ifElse(condition: unknown, trueVal: unknown, falseVal: unknown): unknown {
  return condition ? trueVal : falseVal;
}
function toString(v: unknown): string { return toStr(v); }
function toNumber(v: unknown): number { return toNum(v); }
function formatNumber(n: unknown, decimals?: unknown): string {
  const d = decimals != null ? toNum(decimals) : 0;
  return toNum(n).toFixed(d);
}

export const SAFE_FUNCTIONS: Record<string, (...args: unknown[]) => unknown> = {
  // String
  uppercase, lowercase, trim, substring, includes, startsWith, endsWith,
  replace, split, join, length,
  // Number
  round, ceil, floor, abs,
  // Date
  now, formatDate,
  // Collection
  sum, avg, min, max, count, first, last, unique, filter, map,
  // Utility
  coalesce, ifElse, toString, toNumber, formatNumber,
};

export const FUNCTION_SIGNATURES: Record<string, { params: string[]; returnType: string; description: string }> = {
  uppercase: { params: ["string"], returnType: "string", description: "Convert to uppercase" },
  lowercase: { params: ["string"], returnType: "string", description: "Convert to lowercase" },
  trim: { params: ["string"], returnType: "string", description: "Trim whitespace" },
  substring: { params: ["string", "start", "end?"], returnType: "string", description: "Extract substring" },
  includes: { params: ["string", "search"], returnType: "boolean", description: "Check if string includes" },
  startsWith: { params: ["string", "prefix"], returnType: "boolean", description: "Check prefix" },
  endsWith: { params: ["string", "suffix"], returnType: "boolean", description: "Check suffix" },
  replace: { params: ["string", "search", "replacement"], returnType: "string", description: "Replace first occurrence" },
  split: { params: ["string", "separator"], returnType: "string[]", description: "Split string" },
  join: { params: ["array", "separator"], returnType: "string", description: "Join array to string" },
  length: { params: ["value"], returnType: "number", description: "Length of string or array" },
  round: { params: ["number", "decimals?"], returnType: "number", description: "Round number" },
  ceil: { params: ["number"], returnType: "number", description: "Round up" },
  floor: { params: ["number"], returnType: "number", description: "Round down" },
  abs: { params: ["number"], returnType: "number", description: "Absolute value" },
  now: { params: [], returnType: "string", description: "Current ISO timestamp" },
  formatDate: { params: ["date", "format"], returnType: "string", description: "Format date (YYYY-MM-DD HH:mm:ss)" },
  sum: { params: ["array", "field?"], returnType: "number", description: "Sum of array values" },
  avg: { params: ["array", "field?"], returnType: "number", description: "Average of array values" },
  min: { params: ["array", "field?"], returnType: "number", description: "Minimum value" },
  max: { params: ["array", "field?"], returnType: "number", description: "Maximum value" },
  count: { params: ["array"], returnType: "number", description: "Count of array elements" },
  first: { params: ["array"], returnType: "unknown", description: "First element" },
  last: { params: ["array"], returnType: "unknown", description: "Last element" },
  unique: { params: ["array", "field?"], returnType: "array", description: "Unique elements" },
  filter: { params: ["array", "field", "operator", "value"], returnType: "array", description: "Filter array (eq,ne,gt,gte,lt,lte,contains)" },
  map: { params: ["array", "field"], returnType: "array", description: "Extract field from array objects" },
  coalesce: { params: ["...values"], returnType: "unknown", description: "First non-null value" },
  ifElse: { params: ["condition", "trueValue", "falseValue"], returnType: "unknown", description: "Conditional value" },
  toString: { params: ["value"], returnType: "string", description: "Convert to string" },
  toNumber: { params: ["value"], returnType: "number", description: "Convert to number" },
  formatNumber: { params: ["number", "decimals?"], returnType: "string", description: "Format number with decimals" },
};
