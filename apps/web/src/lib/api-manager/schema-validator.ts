/**
 * Enhanced JSON Schema Validator
 * Provides comprehensive validation for API Manager and all builders
 * Supports:
 * - Type checking
 * - Required field validation
 * - Format validation (email, URL, etc.)
 * - Nested object/array validation
 * - Circular reference detection
 * - Helpful error messages with suggestions
 */

export interface JsonSchema {
  type?: string | string[];
  required?: string[];
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  format?: string;
  pattern?: string;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  enum?: unknown[];
  [key: string]: unknown;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  path: string;
  message: string;
  code: string;
  suggestion?: string;
}

export interface ValidationWarning {
  path: string;
  message: string;
  code: string;
}

const COMMON_PATTERNS = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  url: /^https?:\/\/.+/,
  uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
  slug: /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
  phone: /^\+?[1-9]\d{1,14}$/,
};

export class JsonSchemaValidator {
  /**
   * Validate a value against a JSON schema
   */
  static validate(value: unknown, schema: JsonSchema, path = ""): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];
    const visited = new Set<unknown>();

    this._validate(value, schema, path, errors, warnings, visited);

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  private static _validate(
    value: unknown,
    schema: JsonSchema,
    path: string,
    errors: ValidationError[],
    warnings: ValidationWarning[],
    visited: Set<unknown>
  ): void {
    // Circular reference check
    if (typeof value === "object" && value !== null) {
      if (visited.has(value)) {
        errors.push({
          path,
          message: "Circular reference detected",
          code: "CIRCULAR_REFERENCE",
          suggestion: "Check for objects that reference themselves",
        });
        return;
      }
      visited.add(value);
    }

    // Type validation
    if (schema.type) {
      const types = Array.isArray(schema.type) ? schema.type : [schema.type];
      if (!this._isValidType(value, types)) {
        const actualType = Array.isArray(value) ? "array" : typeof value;
        errors.push({
          path,
          message: `Expected type(s) [${types.join(", ")}], got ${actualType}`,
          code: "TYPE_MISMATCH",
          suggestion: `Change the value to match one of: ${types.join(", ")}`,
        });
        return;
      }
    }

    // Format validation
    if (schema.format && typeof value === "string") {
      if (!this._isValidFormat(value, schema.format)) {
        errors.push({
          path,
          message: `Invalid ${schema.format} format`,
          code: `INVALID_${schema.format.toUpperCase()}`,
          suggestion: this._getFormatSuggestion(schema.format),
        });
      }
    }

    // Pattern validation
    if (schema.pattern && typeof value === "string") {
      try {
        const pattern = new RegExp(schema.pattern);
        if (!pattern.test(value)) {
          errors.push({
            path,
            message: `String does not match pattern: ${schema.pattern}`,
            code: "PATTERN_MISMATCH",
          });
        }
      } catch {
        warnings.push({
          path,
          message: `Invalid regex pattern: ${schema.pattern}`,
          code: "INVALID_REGEX",
        });
      }
    }

    // String length validation
    if (typeof value === "string") {
      if (schema.minLength !== undefined && value.length < schema.minLength) {
        errors.push({
          path,
          message: `String is too short (minimum ${schema.minLength} characters)`,
          code: "STRING_TOO_SHORT",
          suggestion: `Add at least ${schema.minLength - value.length} more character(s)`,
        });
      }
      if (schema.maxLength !== undefined && value.length > schema.maxLength) {
        errors.push({
          path,
          message: `String is too long (maximum ${schema.maxLength} characters)`,
          code: "STRING_TOO_LONG",
          suggestion: `Remove at least ${value.length - schema.maxLength} character(s)`,
        });
      }
    }

    // Number range validation
    if (typeof value === "number") {
      if (schema.minimum !== undefined && value < schema.minimum) {
        errors.push({
          path,
          message: `Number is below minimum (${schema.minimum})`,
          code: "NUMBER_TOO_SMALL",
        });
      }
      if (schema.maximum !== undefined && value > schema.maximum) {
        errors.push({
          path,
          message: `Number exceeds maximum (${schema.maximum})`,
          code: "NUMBER_TOO_LARGE",
        });
      }
    }

    // Enum validation
    if (schema.enum && !schema.enum.includes(value)) {
      errors.push({
        path,
        message: `Value not in allowed list: [${schema.enum.map(v => JSON.stringify(v)).join(", ")}]`,
        code: "ENUM_MISMATCH",
        suggestion: `Use one of: ${schema.enum.map(v => JSON.stringify(v)).join(", ")}`,
      });
    }

    // Object validation
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      const obj = value as Record<string, unknown>;

      // Check required properties
      if (schema.required) {
        for (const prop of schema.required) {
          if (!(prop in obj)) {
            errors.push({
              path: path ? `${path}.${prop}` : prop,
              message: `Required property missing`,
              code: "REQUIRED_PROPERTY_MISSING",
              suggestion: `Add the "${prop}" property`,
            });
          }
        }
      }

      // Validate properties
      if (schema.properties) {
        for (const [key, propSchema] of Object.entries(schema.properties)) {
          if (key in obj) {
            const propPath = path ? `${path}.${key}` : key;
            this._validate(obj[key], propSchema, propPath, errors, warnings, visited);
          }
        }
      }

      // Warn about unknown properties
      if (schema.properties) {
        for (const key of Object.keys(obj)) {
          if (!(key in schema.properties)) {
            const propPath = path ? `${path}.${key}` : key;
            warnings.push({
              path: propPath,
              message: `Unknown property not in schema`,
              code: "UNKNOWN_PROPERTY",
            });
          }
        }
      }
    }

    // Array validation
    if (Array.isArray(value) && schema.items) {
      for (let i = 0; i < value.length; i++) {
        const itemPath = path ? `${path}[${i}]` : `[${i}]`;
        this._validate(value[i], schema.items, itemPath, errors, warnings, visited);
      }
    }
  }

  private static _isValidType(value: unknown, types: string[]): boolean {
    const actualType = Array.isArray(value) ? "array" : typeof value;

    if (types.includes(actualType)) return true;
    if (types.includes("null") && value === null) return true;
    if (types.includes("number") && typeof value === "number") return true;
    if (types.includes("integer") && Number.isInteger(value)) return true;

    return false;
  }

  private static _isValidFormat(value: string, format: string): boolean {
    const patterns: Record<string, RegExp> = COMMON_PATTERNS;

    if (format in patterns) {
      return patterns[format].test(value);
    }

    // Custom format checks
    switch (format) {
      case "date":
        return !isNaN(Date.parse(value));
      case "time":
        return /^\d{2}:\d{2}:\d{2}/.test(value);
      case "datetime":
        return !isNaN(Date.parse(value));
      case "hostname":
        return /^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)*[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(value);
      case "ipv4":
        return /^(\d{1,3}\.){3}\d{1,3}$/.test(value) &&
               value.split(".").every(n => parseInt(n) <= 255);
      default:
        return true;
    }
  }

  private static _getFormatSuggestion(format: string): string {
    const suggestions: Record<string, string> = {
      email: "Use format: user@example.com",
      url: "Use format: https://example.com",
      uuid: "Use format: 550e8400-e29b-41d4-a716-446655440000",
      slug: "Use lowercase letters, numbers, and hyphens (e.g., my-api-name)",
      phone: "Use format: +1234567890",
      date: "Use format: YYYY-MM-DD",
      time: "Use format: HH:MM:SS",
      datetime: "Use ISO 8601 format: 2024-02-14T10:30:00Z",
      hostname: "Use valid hostname format",
      ipv4: "Use format: 192.168.1.1",
    };

    return suggestions[format] || `Use valid ${format} format`;
  }
}

/**
 * Validate API draft schema
 */
export function validateApiSchema(draft: Record<string, unknown>): ValidationResult {
  const schema: JsonSchema = {
    type: "object",
    required: ["api_name", "endpoint", "method", "logic_type"],
    properties: {
      api_name: {
        type: "string",
        minLength: 1,
        maxLength: 255,
      },
      endpoint: {
        type: "string",
        pattern: "^/",
        minLength: 1,
        maxLength: 255,
      },
      method: {
        type: "string",
        enum: ["GET", "POST", "PUT", "DELETE"],
      },
      logic_type: {
        type: "string",
        enum: ["sql", "http", "python", "workflow"],
      },
      logic_body: {
        type: "string",
      },
      description: {
        type: "string",
        maxLength: 1000,
      },
      tags: {
        type: "array",
        items: {
          type: "string",
        },
      },
      param_schema: {
        type: "object",
      },
      runtime_policy: {
        type: "object",
      },
    },
  };

  return JsonSchemaValidator.validate(draft, schema);
}

/**
 * Validate CEP draft schema
 */
export function validateCepSchema(draft: Record<string, unknown>): ValidationResult {
  const schema: JsonSchema = {
    type: "object",
    required: ["rule_name", "trigger_type", "trigger_spec", "actions"],
    properties: {
      rule_name: {
        type: "string",
        minLength: 1,
        maxLength: 255,
      },
      description: {
        type: "string",
        maxLength: 1000,
      },
      is_active: {
        type: "boolean",
      },
      trigger_type: {
        type: "string",
        enum: ["metric", "event", "schedule", "anomaly"],
      },
      trigger_spec: {
        type: "object",
      },
      conditions: {
        type: "array",
      },
      condition_logic: {
        type: "string",
        enum: ["AND", "OR", "NOT"],
      },
      actions: {
        type: "array",
      },
    },
  };

  return JsonSchemaValidator.validate(draft, schema);
}
