/**
 * Safe Expression Parser - Recursive Descent Parser
 * Produces an AST from binding expressions like:
 *   sum(state.items, 'value')
 *   formatDate(state.created_at, 'YYYY-MM-DD')
 *   state.count > 10 ? 'high' : 'low'
 *   uppercase(state.name)
 *
 * Security: No eval(), no Function(), no dynamic code execution.
 * All function calls are resolved against a whitelist at evaluation time.
 */

export type ASTNode =
  | { type: "literal"; value: string | number | boolean | null }
  | { type: "path"; segments: string[] }
  | { type: "call"; name: string; args: ASTNode[] }
  | { type: "binary"; op: string; left: ASTNode; right: ASTNode }
  | { type: "unary"; op: string; operand: ASTNode }
  | { type: "ternary"; condition: ASTNode; consequent: ASTNode; alternate: ASTNode }
  | { type: "array"; elements: ASTNode[] };

// Token types
type TokenType =
  | "number" | "string" | "identifier" | "boolean" | "null"
  | "(" | ")" | "[" | "]" | "," | "." | "?"  | ":"
  | "+" | "-" | "*" | "/" | "%"
  | ">" | ">=" | "<" | "<=" | "==" | "!=" | "===" | "!=="
  | "&&" | "||" | "!" | "EOF";

interface Token {
  type: TokenType;
  value: string | number | boolean | null;
  pos: number;
}

const MAX_TOKENS = 500;

export function tokenize(input: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;

  while (i < input.length) {
    if (tokens.length > MAX_TOKENS) throw new Error(`Expression too complex (>${MAX_TOKENS} tokens)`);

    const ch = input[i];

    // Whitespace
    if (/\s/.test(ch)) { i++; continue; }

    // Numbers
    if (/\d/.test(ch) || (ch === "." && i + 1 < input.length && /\d/.test(input[i + 1]))) {
      let num = "";
      while (i < input.length && (/\d/.test(input[i]) || input[i] === ".")) { num += input[i++]; }
      tokens.push({ type: "number", value: parseFloat(num), pos: i });
      continue;
    }

    // Strings
    if (ch === "'" || ch === '"') {
      const quote = ch;
      let str = "";
      i++; // skip opening quote
      while (i < input.length && input[i] !== quote) {
        if (input[i] === "\\" && i + 1 < input.length) { str += input[++i]; }
        else { str += input[i]; }
        i++;
      }
      if (i < input.length) i++; // skip closing quote
      tokens.push({ type: "string", value: str, pos: i });
      continue;
    }

    // Identifiers / keywords
    if (/[a-zA-Z_$]/.test(ch)) {
      let ident = "";
      while (i < input.length && /[a-zA-Z0-9_$]/.test(input[i])) { ident += input[i++]; }
      if (ident === "true") tokens.push({ type: "boolean", value: true, pos: i });
      else if (ident === "false") tokens.push({ type: "boolean", value: false, pos: i });
      else if (ident === "null") tokens.push({ type: "null", value: null, pos: i });
      else tokens.push({ type: "identifier", value: ident, pos: i });
      continue;
    }

    // Multi-char operators
    const two = input.slice(i, i + 3);
    if (two === "===" || two === "!==") { tokens.push({ type: two as TokenType, value: two, pos: i }); i += 3; continue; }
    const pair = input.slice(i, i + 2);
    if (pair === "==" || pair === "!=" || pair === ">=" || pair === "<=" || pair === "&&" || pair === "||") {
      tokens.push({ type: pair as TokenType, value: pair, pos: i }); i += 2; continue;
    }

    // Single-char tokens
    const singles: Record<string, TokenType> = {
      "(": "(", ")": ")", "[": "[", "]": "]", ",": ",", ".": ".",
      "?": "?", ":": ":", "+": "+", "-": "-", "*": "*", "/": "/", "%": "%",
      ">": ">", "<": "<", "!": "!",
    };
    if (singles[ch]) { tokens.push({ type: singles[ch], value: ch, pos: i }); i++; continue; }

    throw new Error(`Unexpected character '${ch}' at position ${i}`);
  }

  tokens.push({ type: "EOF", value: null, pos: i });
  return tokens;
}

const MAX_DEPTH = 10;

export function parse(tokens: Token[]): ASTNode {
  let pos = 0;
  let depth = 0;

  function peek(): Token { return tokens[pos] || { type: "EOF", value: null, pos: -1 }; }
  function advance(): Token { return tokens[pos++]; }
  function expect(type: TokenType): Token {
    const t = advance();
    if (t.type !== type) throw new Error(`Expected '${type}' but got '${t.type}' at position ${t.pos}`);
    return t;
  }

  function parseExpression(): ASTNode {
    if (++depth > MAX_DEPTH) throw new Error("Expression nesting too deep");
    try { return parseTernary(); } finally { depth--; }
  }

  function parseTernary(): ASTNode {
    let node = parseOr();
    if (peek().type === "?") {
      advance(); // skip ?
      const consequent = parseExpression();
      expect(":");
      const alternate = parseExpression();
      node = { type: "ternary", condition: node, consequent, alternate };
    }
    return node;
  }

  function parseOr(): ASTNode {
    let left = parseAnd();
    while (peek().type === "||") { advance(); left = { type: "binary", op: "||", left, right: parseAnd() }; }
    return left;
  }

  function parseAnd(): ASTNode {
    let left = parseComparison();
    while (peek().type === "&&") { advance(); left = { type: "binary", op: "&&", left, right: parseComparison() }; }
    return left;
  }

  function parseComparison(): ASTNode {
    let left = parseAddition();
    const ops = ["==", "!=", "===", "!==", ">", ">=", "<", "<="];
    while (ops.includes(peek().type)) {
      const op = advance().type;
      left = { type: "binary", op, left, right: parseAddition() };
    }
    return left;
  }

  function parseAddition(): ASTNode {
    let left = parseMultiplication();
    while (peek().type === "+" || peek().type === "-") {
      const op = advance().type;
      left = { type: "binary", op, left, right: parseMultiplication() };
    }
    return left;
  }

  function parseMultiplication(): ASTNode {
    let left = parseUnary();
    while (peek().type === "*" || peek().type === "/" || peek().type === "%") {
      const op = advance().type;
      left = { type: "binary", op, left, right: parseUnary() };
    }
    return left;
  }

  function parseUnary(): ASTNode {
    if (peek().type === "!") { advance(); return { type: "unary", op: "!", operand: parseUnary() }; }
    if (peek().type === "-") { advance(); return { type: "unary", op: "-", operand: parseUnary() }; }
    return parseCallOrAccess();
  }

  function parseCallOrAccess(): ASTNode {
    let node = parsePrimary();

    while (true) {
      if (peek().type === "(") {
        // Function call
        if (node.type !== "path" && node.type !== "literal") break;
        const name = node.type === "path" ? node.segments.join(".") : String(node.value);
        advance(); // skip (
        const args: ASTNode[] = [];
        if (peek().type !== ")") {
          args.push(parseExpression());
          while (peek().type === ",") { advance(); args.push(parseExpression()); }
        }
        expect(")");
        node = { type: "call", name, args };
      } else if (peek().type === ".") {
        // Property access
        advance(); // skip .
        const prop = expect("identifier");
        if (node.type === "path") {
          node = { type: "path", segments: [...node.segments, String(prop.value)] };
        } else {
          node = { type: "path", segments: [String((node as { value: unknown }).value || ""), String(prop.value)] };
        }
      } else if (peek().type === "[") {
        // Index access
        advance(); // skip [
        const indexNode = parseExpression();
        expect("]");
        if (node.type === "path" && indexNode.type === "literal") {
          node = { type: "path", segments: [...node.segments, String(indexNode.value)] };
        }
      } else {
        break;
      }
    }
    return node;
  }

  function parsePrimary(): ASTNode {
    const t = peek();

    if (t.type === "number") { advance(); return { type: "literal", value: t.value as number }; }
    if (t.type === "string") { advance(); return { type: "literal", value: t.value as string }; }
    if (t.type === "boolean") { advance(); return { type: "literal", value: t.value as boolean }; }
    if (t.type === "null") { advance(); return { type: "literal", value: null }; }

    if (t.type === "identifier") {
      advance();
      return { type: "path", segments: [String(t.value)] };
    }

    if (t.type === "(") {
      advance();
      const node = parseExpression();
      expect(")");
      return node;
    }

    if (t.type === "[") {
      advance();
      const elements: ASTNode[] = [];
      if (peek().type !== "]") {
        elements.push(parseExpression());
        while (peek().type === ",") { advance(); elements.push(parseExpression()); }
      }
      expect("]");
      return { type: "array", elements };
    }

    throw new Error(`Unexpected token '${t.type}' at position ${t.pos}`);
  }

  const result = parseExpression();
  if (peek().type !== "EOF") {
    throw new Error(`Unexpected token '${peek().type}' after expression at position ${peek().pos}`);
  }
  return result;
}

export function parseExpression(input: string): ASTNode {
  const tokens = tokenize(input);
  return parse(tokens);
}

/** Collect all path references in an AST (for validation) */
export function collectPaths(node: ASTNode): string[] {
  const paths: string[] = [];
  function visit(n: ASTNode) {
    if (n.type === "path") paths.push(n.segments.join("."));
    if (n.type === "call") n.args.forEach(visit);
    if (n.type === "binary") { visit(n.left); visit(n.right); }
    if (n.type === "unary") visit(n.operand);
    if (n.type === "ternary") { visit(n.condition); visit(n.consequent); visit(n.alternate); }
    if (n.type === "array") n.elements.forEach(visit);
  }
  visit(node);
  return paths;
}

/** Collect all function names in an AST (for whitelist validation) */
export function collectFunctions(node: ASTNode): string[] {
  const fns: string[] = [];
  function visit(n: ASTNode) {
    if (n.type === "call") { fns.push(n.name); n.args.forEach(visit); }
    if (n.type === "binary") { visit(n.left); visit(n.right); }
    if (n.type === "unary") visit(n.operand);
    if (n.type === "ternary") { visit(n.condition); visit(n.consequent); visit(n.alternate); }
    if (n.type === "array") n.elements.forEach(visit);
  }
  visit(node);
  return fns;
}
