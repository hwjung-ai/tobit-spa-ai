import { getComponentDescriptor } from "./component-registry";

export interface PropsFormField {
  name: string;
  type: "text" | "number" | "boolean" | "select" | "array" | "object" | "textarea";
  label?: string;
  placeholder?: string;
  required?: boolean;
  description?: string;
  options?: { value: string; label: string }[];
  defaultValue?: unknown;
  multiline?: boolean;
  min?: number;
  max?: number;
}

/**
 * Generate form fields from component props schema
 */
export function generatePropsFormFields(componentType: string): PropsFormField[] {
  const descriptor = getComponentDescriptor(componentType);
  if (!descriptor || !descriptor.propsSchema) return [];

  const fields: PropsFormField[] = [];
  const properties = descriptor.propsSchema.properties || {};
  const required = descriptor.propsSchema.required || [];

  Object.entries(properties).forEach(([name, prop]: [string, Record<string, unknown>]) => {
    const field: PropsFormField = {
      name,
      type: mapJsonTypeToFormType(prop),
      label: prop.title || name,
      description: prop.description,
      required: required.includes(name),
      defaultValue: prop.default,
    };

    // Handle enums
    if (prop.enum) {
      field.type = "select";
      field.options = prop.enum.map((v: string) => ({ value: v, label: v }));
    }

    // Handle number constraints
    if (prop.type === "number") {
      field.min = prop.minimum;
      field.max = prop.maximum;
    }

    // Handle string constraints
    if (prop.type === "string") {
      if (prop.minLength || prop.maxLength) {
        field.multiline = true;
      }
    }

    fields.push(field);
  });

  return fields;
}

/**
 * Map JSON Schema type to form input type
 */
function mapJsonTypeToFormType(
  prop: Record<string, unknown>
): PropsFormField["type"] {
  if ((prop as { enum?: unknown }).enum) return "select";
  if (prop.type === "boolean") return "boolean";
  if (prop.type === "number" || prop.type === "integer") return "number";
  if (prop.type === "array") return "array";
  if (prop.type === "object") return "object";
  if (prop.type === "string") {
    if ((prop as { minLength?: unknown }).minLength || (prop as { maxLength?: unknown }).maxLength || (prop as { description?: string }).description?.includes("multiline")) {
      return "textarea";
    }
    return "text";
  }
  return "text";
}

/**
 * Normalize props value based on type
 */
export function normalizePropsValue(type: string, value: unknown): unknown {
  if (value === null || value === undefined) return undefined;

  switch (type) {
    case "number":
      return isNaN(Number(value)) ? undefined : Number(value);
    case "boolean":
      if (typeof value === "boolean") return value;
      return value === "true" || value === true;
    case "array":
      return Array.isArray(value) ? value : [];
    case "object":
      return typeof value === "object" ? value : {};
    case "text":
    case "textarea":
    default:
      return String(value || "");
  }
}

/**
 * Get displayable props for a component (excluding internal fields)
 */
export function getDisplayableProps(props: Record<string, unknown>): Record<string, unknown> {
  const exclude = ["key", "ref", "children"];
  const result: Record<string, unknown> = {};

  Object.entries(props).forEach(([key, value]) => {
    if (!exclude.includes(key) && value !== undefined && value !== null) {
      result[key] = value;
    }
  });

  return result;
}

/**
 * Validate binding expression format
 */
export function isValidBindingExpression(expr: string): boolean {
  if (!expr) return false;
  // Simple validation: {{state.xxx}} or {{context.xxx}} or {{inputs.xxx}}
  return /^\{\{(state|context|inputs)\.[\w.]+\}\}$/.test(expr);
}

/**
 * Extract path from binding expression
 */
export function extractBindingPath(expr: string): string | null {
  const match = expr.match(/^\{\{([\w.]+)\}\}$/);
  return match ? match[1] : null;
}

/**
 * Format binding expression from components
 */
export function formatBindingExpression(source: string, path: string): string {
  return `{{${source}.${path}}}`;
}
