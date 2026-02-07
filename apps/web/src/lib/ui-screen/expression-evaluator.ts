/**
 * Safe Expression Evaluator
 * Evaluates AST nodes produced by expression-parser.ts against a binding context.
 * Uses SAFE_FUNCTIONS whitelist - no eval() or Function() used.
 */

import { ASTNode } from "./expression-parser";
import { SAFE_FUNCTIONS } from "./safe-functions";
import type { BindingContext } from "./binding-engine";
import { get } from "./binding-engine";

const MAX_DEPTH = 10;

export interface EvalOptions {
  maxDepth?: number;
  functions?: Record<string, (...args: unknown[]) => unknown>;
}

export function evaluate(node: ASTNode, ctx: BindingContext, opts?: EvalOptions): unknown {
  const maxDepth = opts?.maxDepth ?? MAX_DEPTH;
  const fns = opts?.functions ?? SAFE_FUNCTIONS;
  let depth = 0;

  function evalNode(n: ASTNode): unknown {
    if (++depth > maxDepth) throw new Error("Expression evaluation depth exceeded");
    try {
      switch (n.type) {
        case "literal":
          return n.value;

        case "path":
          return resolvePath(n.segments, ctx);

        case "call": {
          const fn = fns[n.name];
          if (!fn) throw new Error(`Unknown function: ${n.name}`);
          const args = n.args.map(evalNode);
          return fn(...args);
        }

        case "binary":
          return evalBinary(n.op, evalNode(n.left), evalNode(n.right));

        case "unary":
          return evalUnary(n.op, evalNode(n.operand));

        case "ternary": {
          const cond = evalNode(n.condition);
          return cond ? evalNode(n.consequent) : evalNode(n.alternate);
        }

        case "array":
          return n.elements.map(evalNode);

        default:
          return null;
      }
    } finally {
      depth--;
    }
  }

  return evalNode(node);
}

function resolvePath(segments: string[], ctx: BindingContext): unknown {
  if (segments.length === 0) return undefined;
  const root = segments[0];
  const rest = segments.slice(1).join(".");

  if (root === "state") return get(ctx.state || {}, rest);
  if (root === "inputs") return get(ctx.inputs || {}, rest);
  if (root === "context") return get(ctx.context || {}, rest);
  if (root === "trace_id") return ctx.trace_id ?? null;

  // Fallback: try resolving from state
  return get(ctx.state || {}, segments.join("."));
}

function evalBinary(op: string, left: unknown, right: unknown): unknown {
  switch (op) {
    case "+": {
      if (typeof left === "string" || typeof right === "string") return String(left ?? "") + String(right ?? "");
      return toNum(left) + toNum(right);
    }
    case "-": return toNum(left) - toNum(right);
    case "*": return toNum(left) * toNum(right);
    case "/": { const r = toNum(right); return r === 0 ? 0 : toNum(left) / r; }
    case "%": { const r = toNum(right); return r === 0 ? 0 : toNum(left) % r; }
    case ">": return toNum(left) > toNum(right);
    case ">=": return toNum(left) >= toNum(right);
    case "<": return toNum(left) < toNum(right);
    case "<=": return toNum(left) <= toNum(right);
    case "==": return left == right;
    case "!=": return left != right;
    case "===": return left === right;
    case "!==": return left !== right;
    case "&&": return (left as boolean) && (right as boolean);
    case "||": return (left as boolean) || (right as boolean);
    default: return null;
  }
}

function evalUnary(op: string, operand: unknown): unknown {
  switch (op) {
    case "!": return !operand;
    case "-": return -toNum(operand);
    default: return null;
  }
}

function toNum(v: unknown): number {
  const n = Number(v);
  return isNaN(n) ? 0 : n;
}

/**
 * Convenience: parse + evaluate an expression string in one step.
 * Import parseExpression from expression-parser to use.
 */
export function evaluateExpression(
  expr: string,
  ctx: BindingContext,
  opts?: EvalOptions
): unknown {
  // Lazy import to avoid circular dependency
  const { parseExpression } = require("./expression-parser"); // eslint-disable-line @typescript-eslint/no-require-imports
  const ast = parseExpression(expr);
  return evaluate(ast, ctx, opts);
}
