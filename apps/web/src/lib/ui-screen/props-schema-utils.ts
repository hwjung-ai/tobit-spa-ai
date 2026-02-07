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
  if (componentType === "chart") {
    return [
      {
        name: "chart_type",
        type: "select",
        label: "Chart Type",
        description: "Type of chart visualization",
        options: [
          { value: "line", label: "Line" },
          { value: "bar", label: "Bar" },
          { value: "pie", label: "Pie" },
          { value: "area", label: "Area" },
          { value: "scatter", label: "Scatter" },
        ],
      },
      {
        name: "x_key",
        type: "text",
        label: "X-Axis Field",
        description: "Field name for X-axis values",
        placeholder: "e.g., timestamp",
      },
      {
        name: "series",
        type: "textarea",
        label: "Series Configuration",
        description: "Array of series with data_key, label, color. JSON format.",
        placeholder: '[{"data_key":"value","label":"Value","color":"#38bdf8"}]',
      },
      {
        name: "y_axis",
        type: "textarea",
        label: "Y-Axis Options",
        description: "Y-axis configuration (min, max, title). JSON format.",
        placeholder: '{"min":0,"max":100,"title":"Value"}',
      },
      {
        name: "legend",
        type: "textarea",
        label: "Legend Options",
        description: "Legend configuration (show, position). JSON format.",
        placeholder: '{"show":true,"position":"right"}',
      },
      {
        name: "tooltip",
        type: "textarea",
        label: "Tooltip Options",
        description: "Tooltip configuration. JSON format.",
        placeholder: '{"show":true,"trigger":"axis"}',
      },
      {
        name: "height",
        type: "number",
        label: "Chart Height",
        description: "Height in pixels",
        min: 200,
        max: 800,
      },
      {
        name: "responsive",
        type: "boolean",
        label: "Responsive",
        description: "Enable responsive resizing",
      },
    ];
  }

  const descriptor = getComponentDescriptor(componentType);
  if (!descriptor || !descriptor.propsSchema) return [];

  const fields: PropsFormField[] = [];
  const properties = descriptor.propsSchema.properties || {};
  const required = descriptor.propsSchema.required || [];

  Object.entries(properties).forEach(([name, prop]: [string, Record<string, unknown>]) => {
    const field: PropsFormField = {
      name,
      type: mapJsonTypeToFormType(prop),
      label: (prop.title as string) || name,
      description: prop.description as string | undefined,
      required: required.includes(name),
      defaultValue: prop.default,
    };

    // Handle enums
    if (prop.enum) {
      field.type = "select";
      field.options = (prop.enum as string[]).map((v: string) => ({ value: v, label: v }));
    }

    // Handle number constraints
    if (prop.type === "number") {
      field.min = prop.minimum as number | undefined;
      field.max = prop.maximum as number | undefined;
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
