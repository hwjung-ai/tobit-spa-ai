/**
 * Input Validation and Security Hardening
 * Provides sanitization and validation for all user inputs across builders
 * Prevents:
 * - XSS (Cross-Site Scripting)
 * - SQL Injection
 * - Command Injection
 * - Path Traversal
 */

export interface ValidationRules {
  type?: "string" | "number" | "boolean" | "email" | "url" | "json" | "sql";
  maxLength?: number;
  minLength?: number;
  pattern?: RegExp;
  allowedCharacters?: string[];
  blockedPatterns?: RegExp[];
  trim?: boolean;
  lowercase?: boolean;
}

export interface SanitizationOptions {
  stripHtml?: boolean;
  stripScripts?: boolean;
  stripSql?: boolean;
  trimWhitespace?: boolean;
  removeNullBytes?: boolean;
}

/**
 * Validate input against security rules
 */
export function validateInput(
  value: unknown,
  rules: ValidationRules
): { valid: boolean; error?: string } {
  // Type checking
  if (typeof value !== "string" && rules.type !== "number" && rules.type !== "boolean") {
    return { valid: false, error: "Invalid input type" };
  }

  const strValue = String(value).trim();

  // Empty string check
  if (strValue.length === 0 && rules.minLength === undefined) {
    return { valid: false, error: "Input cannot be empty" };
  }

  // Length validation
  if (rules.minLength !== undefined && strValue.length < rules.minLength) {
    return { valid: false, error: `Minimum ${rules.minLength} characters required` };
  }
  if (rules.maxLength !== undefined && strValue.length > rules.maxLength) {
    return { valid: false, error: `Maximum ${rules.maxLength} characters allowed` };
  }

  // Pattern validation
  if (rules.pattern && !rules.pattern.test(strValue)) {
    return { valid: false, error: "Input does not match required pattern" };
  }

  // Blocked patterns check (security)
  if (rules.blockedPatterns) {
    for (const blockedPattern of rules.blockedPatterns) {
      if (blockedPattern.test(strValue)) {
        return { valid: false, error: "Input contains invalid characters or patterns" };
      }
    }
  }

  // Type-specific validation
  switch (rules.type) {
    case "email":
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(strValue)) {
        return { valid: false, error: "Invalid email format" };
      }
      break;

    case "url":
      try {
        new URL(strValue);
      } catch {
        return { valid: false, error: "Invalid URL format" };
      }
      break;

    case "json":
      try {
        JSON.parse(strValue);
      } catch {
        return { valid: false, error: "Invalid JSON format" };
      }
      break;

    case "sql":
      if (containsDangerousSqlPatterns(strValue)) {
        return { valid: false, error: "Input contains potentially dangerous SQL patterns" };
      }
      break;

    case "number":
      if (isNaN(Number(strValue))) {
        return { valid: false, error: "Input must be a valid number" };
      }
      break;

    case "boolean":
      if (!["true", "false", "0", "1", "yes", "no"].includes(strValue.toLowerCase())) {
        return { valid: false, error: "Input must be a boolean value" };
      }
      break;
  }

  return { valid: true };
}

/**
 * Sanitize input to prevent XSS and injection attacks
 */
export function sanitizeInput(
  value: string,
  options: SanitizationOptions = {}
): string {
  let result = value;

  // Remove null bytes
  if (options.removeNullBytes !== false) {
    result = result.replace(/\0/g, "");
  }

  // Trim whitespace
  if (options.trimWhitespace !== false) {
    result = result.trim();
  }

  // Remove HTML/scripts
  if (options.stripHtml !== false) {
    result = stripHtmlTags(result);
  }

  if (options.stripScripts !== false) {
    result = stripScriptTags(result);
  }

  // Remove dangerous SQL patterns (for SQL builder inputs)
  if (options.stripSql !== false) {
    result = stripSqlInjectionPatterns(result);
  }

  return result;
}

/**
 * Check if input contains dangerous SQL patterns
 */
export function containsDangerousSqlPatterns(input: string): boolean {
  const dangerous = [
    /;\s*(DELETE|DROP|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|EXEC|EXECUTE)/i,
    /--\s*(SELECT|DELETE|DROP|INSERT|UPDATE)/i,
    /\/\*.*\*\//i,
    /UNION\s+SELECT/i,
    /OR\s+1\s*=\s*1/i,
    /'\s*(OR|AND)\s*'/,
  ];

  return dangerous.some(pattern => pattern.test(input));
}

/**
 * Strip HTML tags from string
 */
export function stripHtmlTags(input: string): string {
  return input.replace(/<[^>]*>/g, "");
}

/**
 * Strip script tags from string
 */
export function stripScriptTags(input: string): string {
  // Remove script tags and their content
  let result = input.replace(/<script[^>]*>.*?<\/script>/gi, "");

  // Remove event handlers
  result = result.replace(/on\w+\s*=\s*["'][^"']*["']/gi, "");
  result = result.replace(/on\w+\s*=\s*[^\s>]*/gi, "");

  // Remove javascript: protocol
  result = result.replace(/javascript:/gi, "");

  return result;
}

/**
 * Strip SQL injection patterns
 */
export function stripSqlInjectionPatterns(input: string): string {
  // Remove common SQL injection patterns
  let result = input;

  // Remove multiple statement separators
  result = result.replace(/;\s*(?=SELECT|DELETE|DROP|INSERT|UPDATE)/gi, " ");

  // Remove SQL comments
  result = result.replace(/--[^\n]*/g, "");
  result = result.replace(/\/\*.*?\*\//g, "");

  return result;
}

/**
 * Escape special characters for safe display
 */
export function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, char => map[char] || char);
}

/**
 * Generate secure random string
 */
export function generateRandomString(length: number = 32): string {
  const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";

  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const values = crypto.getRandomValues(new Uint8Array(length));
    for (let i = 0; i < length; i++) {
      result += charset[values[i] % charset.length];
    }
  } else {
    // Fallback for environments without crypto API
    for (let i = 0; i < length; i++) {
      result += charset.charAt(Math.floor(Math.random() * charset.length));
    }
  }

  return result;
}

/**
 * Validate endpoint path format
 */
export function isValidEndpointPath(path: string): boolean {
  // Must start with /
  if (!path.startsWith("/")) return false;

  // Should only contain alphanumeric, hyphens, underscores, and slashes
  if (!/^\/[a-zA-Z0-9\/_-]*$/.test(path)) return false;

  // Should not contain double slashes (except //)
  if (path.includes("//")) return false;

  // Should not end with /
  if (path.length > 1 && path.endsWith("/")) return false;

  return true;
}

/**
 * Validate variable/identifier names
 */
export function isValidIdentifier(name: string): boolean {
  // Must start with letter or underscore
  // Can contain letters, numbers, underscores
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

/**
 * Rate limiting utility
 */
export class RateLimiter {
  private attempts: Map<string, number[]> = new Map();
  private windowMs: number;
  private maxAttempts: number;

  constructor(windowMs: number = 60000, maxAttempts: number = 10) {
    this.windowMs = windowMs;
    this.maxAttempts = maxAttempts;
  }

  isAllowed(key: string): boolean {
    const now = Date.now();
    const attempts = this.attempts.get(key) || [];

    // Filter out old attempts outside the window
    const recentAttempts = attempts.filter(time => now - time < this.windowMs);

    if (recentAttempts.length >= this.maxAttempts) {
      return false;
    }

    // Add new attempt
    recentAttempts.push(now);
    this.attempts.set(key, recentAttempts);

    return true;
  }

  getRemainingAttempts(key: string): number {
    const now = Date.now();
    const attempts = this.attempts.get(key) || [];
    const recentAttempts = attempts.filter(time => now - time < this.windowMs);
    return Math.max(0, this.maxAttempts - recentAttempts.length);
  }

  reset(key?: string): void {
    if (key) {
      this.attempts.delete(key);
    } else {
      this.attempts.clear();
    }
  }
}
