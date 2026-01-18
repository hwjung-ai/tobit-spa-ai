/*
  Validation Utilities for U3-1
  - Validate action handlers, binding paths, component actions
  - Check for circular dependencies
  - Validate visibility expressions
  - Generate user-friendly error messages
*/

import { ScreenSchemaV1, ScreenAction, ComponentActionRef } from "./screen.schema";
import {
  parseBindingExpression,
  isValidPath,
  detectCircularBindings,
  extractBindingsFromObject,
} from "./binding-path-utils";

/**
 * Validation error structure
 */
export interface ValidationError {
  path: string; // Location in schema (e.g., "components[0].props.title")
  message: string; // User-friendly error message
  severity: "error" | "warning"; // error blocks publish, warning is informational
  type?: string; // Category (e.g., "binding-not-found", "circular-dependency")
}

/**
 * Validate an action handler exists or follows naming convention
 * Note: If action_registry is available via API, this would check against it
 * For now, we just check basic naming conventions
 */
export function validateActionHandler(
  handler: string
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!handler || typeof handler !== "string") {
    errors.push({
      path: "handler",
      message: "Action handler is required and must be a string",
      severity: "error",
      type: "invalid-handler",
    });
    return errors;
  }

  if (handler.length === 0) {
    errors.push({
      path: "handler",
      message: "Action handler cannot be empty",
      severity: "error",
      type: "empty-handler",
    });
  }

  // Check naming convention (lowercase with underscores)
  if (!/^[a-z_][a-z0-9_]*$/.test(handler)) {
    errors.push({
      path: "handler",
      message: `Handler "${handler}" must follow naming convention: lowercase letters, numbers, and underscores only`,
      severity: "warning",
      type: "naming-convention",
    });
  }

  return errors;
}

/**
 * Validate a binding path expression
 * Checks format ({{source.path}}) and verifies path exists in schema
 */
export function validateBindingPath(
  pathExpr: string | null | undefined,
  schema?: ScreenSchemaV1
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!pathExpr) return errors; // Optional binding is OK

  if (typeof pathExpr !== "string") {
    errors.push({
      path: pathExpr,
      message: "Binding expression must be a string",
      severity: "error",
      type: "invalid-type",
    });
    return errors;
  }

  // Parse expression
  const parsed = parseBindingExpression(pathExpr);
  if (!parsed) {
    errors.push({
      path: pathExpr,
      message: `Invalid binding expression format. Use {{source.path}}, got: "${pathExpr}"`,
      severity: "error",
      type: "invalid-format",
    });
    return errors;
  }

  const { source, path } = parsed;

  // Validate source
  const validSources = ["state", "context", "inputs", "trace_id"];
  if (!validSources.includes(source)) {
    errors.push({
      path: pathExpr,
      message: `Invalid binding source: "${source}". Must be one of: ${validSources.join(", ")}`,
      severity: "error",
      type: "invalid-source",
    });
    return errors;
  }

  // Validate path exists in schema for state bindings
  if (source === "state") {
    if (!path) {
      errors.push({
        path: pathExpr,
        message: 'Binding source "{{state}}" requires a path (e.g., "{{state.device_id}}")',
        severity: "error",
        type: "missing-path",
      });
      return errors;
    }

    if (schema?.state?.schema) {
      if (!isValidPath(path, schema.state.schema)) {
        errors.push({
          path: pathExpr,
          message: `Path "${path}" not found in state schema. Available paths: ${Object.keys(schema.state.schema).join(", ")}`,
          severity: "warning",
          type: "path-not-found",
        });
      }
    }
  }

  // Validate context paths (basic check)
  if (source === "context" && path) {
    const validContextPaths = ["user_id", "user_email", "tenant_id", "permissions"];
    const pathRoot = path.split(".")[0];
    if (!validContextPaths.includes(pathRoot)) {
      errors.push({
        path: pathExpr,
        message: `Context path "${pathRoot}" is uncommon. Valid contexts: ${validContextPaths.join(", ")}`,
        severity: "warning",
        type: "uncommon-context",
      });
    }
  }

  return errors;
}

/**
 * Validate a component action reference
 */
export function validateComponentActionRef(
  action: ComponentActionRef,
  schema?: ScreenSchemaV1,
  componentId?: string
): ValidationError[] {
  const errors: ValidationError[] = [];
  const pathPrefix = componentId ? `components[*].actions[*]` : "actions[*]";

  // Validate ID
  if (!action.id || typeof action.id !== "string") {
    errors.push({
      path: `${pathPrefix}.id`,
      message: "Action ID is required",
      severity: "error",
    });
  }

  // Validate handler
  errors.push(
    ...validateActionHandler(action.handler).map((e) => ({
      ...e,
      path: `${pathPrefix}.handler`,
    }))
  );

  // Validate payload bindings
  if (action.payload_template) {
    const bindings = extractBindingsFromObject(action.payload_template);
    bindings.forEach((binding) => {
      const bindingErrors = validateBindingPath(binding, schema);
      errors.push(
        ...bindingErrors.map((e) => ({
          ...e,
          path: `${pathPrefix}.payload_template`,
        }))
      );
    });
  }

  return errors;
}

/**
 * Validate a screen-level action
 */
export function validateScreenAction(
  action: ScreenAction,
  schema?: ScreenSchemaV1,
  actionIndex?: number
): ValidationError[] {
  const errors: ValidationError[] = [];
  const pathPrefix = actionIndex !== undefined ? `actions[${actionIndex}]` : "actions[*]";

  // Validate ID
  if (!action.id || typeof action.id !== "string") {
    errors.push({
      path: `${pathPrefix}.id`,
      message: "Action ID is required",
      severity: "error",
    });
  }

  // Validate handler
  errors.push(
    ...validateActionHandler(action.handler).map((e) => ({
      ...e,
      path: `${pathPrefix}.handler`,
    }))
  );

  // Validate payload bindings
  if (action.payload_template) {
    const bindings = extractBindingsFromObject(action.payload_template);
    bindings.forEach((binding) => {
      const bindingErrors = validateBindingPath(binding, schema);
      errors.push(
        ...bindingErrors.map((e) => ({
          ...e,
          path: `${pathPrefix}.payload_template.${binding}`,
        }))
      );
    });
  }

  // Validate context_required
  if (action.context_required && Array.isArray(action.context_required)) {
    action.context_required.forEach((ctx, idx) => {
      if (typeof ctx !== "string" || !ctx) {
        errors.push({
          path: `${pathPrefix}.context_required[${idx}]`,
          message: "Context keys must be non-empty strings",
          severity: "warning",
        });
      }
    });
  }

  return errors;
}

/**
 * Validate visibility rule expression
 */
export function validateVisibilityExpression(
  expr: string | null | undefined,
  schema?: ScreenSchemaV1
): ValidationError[] {
  if (!expr) return []; // No visibility rule is OK

  return validateBindingPath(expr, schema).map((e) => ({
    ...e,
    type: "visibility-rule",
  }));
}

/**
 * Validate all bindings in screen.bindings
 */
export function validateScreenBindings(
  bindings: Record<string, string> | null | undefined,
  schema?: ScreenSchemaV1
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!bindings) return errors;

  // Check for circular dependencies
  const cycles = detectCircularBindings(bindings);
  cycles.forEach((cycle) => {
    errors.push({
      path: "bindings",
      message: `Circular binding dependency detected: ${cycle}`,
      severity: "error",
      type: "circular-dependency",
    });
  });

  // Validate each binding target and source
  Object.entries(bindings).forEach(([target, source]) => {
    // Validate target (should be a valid path)
    if (!target || typeof target !== "string") {
      errors.push({
        path: `bindings.${target}`,
        message: "Binding target must be a non-empty string",
        severity: "error",
      });
    }

    // Validate source (should be a valid binding expression)
    const sourceErrors = validateBindingPath(source, schema);
    errors.push(
      ...sourceErrors.map((e) => ({
        ...e,
        path: `bindings.${target}`,
      }))
    );
  });

  return errors;
}

/**
 * Validate component visibility settings
 */
export function validateComponentVisibility(
  rule: string | null | undefined,
  schema?: ScreenSchemaV1,
  componentId?: string
): ValidationError[] {
  if (!rule) return [];

  const errors = validateVisibilityExpression(rule, schema);
  return errors.map((e) => ({
    ...e,
    path: componentId ? `components[*].visibility` : "visibility",
  }));
}

/**
 * Comprehensive validation of entire screen schema
 * Returns all validation errors found
 */
export function validateScreenSchema(
  screen: ScreenSchemaV1
): ValidationError[] {
  const errors: ValidationError[] = [];

  // Validate screen-level actions
  if (screen.actions && Array.isArray(screen.actions)) {
    screen.actions.forEach((action, idx) => {
      errors.push(...validateScreenAction(action, screen, idx));
    });
  }

  // Validate component actions and visibility
  screen.components.forEach((component, idx) => {
    // Validate component actions
    if (component.actions && Array.isArray(component.actions)) {
      component.actions.forEach((action) => {
        errors.push(
          ...validateComponentActionRef(action, screen, `[${idx}]`)
        );
      });
    }

    // Validate component visibility
    if (component.visibility?.rule) {
      errors.push(
        ...validateComponentVisibility(
          component.visibility.rule,
          screen,
          component.id
        )
      );
    }

    // Validate component prop bindings
    if (component.props) {
      const propBindings = extractBindingsFromObject(component.props);
      propBindings.forEach((binding) => {
        const bindingErrors = validateBindingPath(binding, screen);
        errors.push(
          ...bindingErrors.map((e) => ({
            ...e,
            path: `components[${idx}].props`,
          }))
        );
      });
    }

    // Validate component bind field
    if (component.bind) {
      const bindErrors = validateBindingPath(component.bind, screen);
      errors.push(
        ...bindErrors.map((e) => ({
          ...e,
          path: `components[${idx}].bind`,
        }))
      );
    }
  });

  // Validate top-level bindings
  errors.push(...validateScreenBindings(screen.bindings, screen));

  return errors;
}

/**
 * Get validation error summary
 * Groups errors by severity and type
 */
export function summarizeValidationErrors(errors: ValidationError[]): {
  errorCount: number;
  warningCount: number;
  summary: string;
} {
  const errorCount = errors.filter((e) => e.severity === "error").length;
  const warningCount = errors.filter((e) => e.severity === "warning").length;

  let summary = "";
  if (errorCount > 0) {
    summary += `${errorCount} error${errorCount !== 1 ? "s" : ""}`;
  }
  if (warningCount > 0) {
    if (summary) summary += ", ";
    summary += `${warningCount} warning${warningCount !== 1 ? "s" : ""}`;
  }

  return { errorCount, warningCount, summary };
}

/**
 * Filter validation errors by severity
 */
export function filterValidationErrors(
  errors: ValidationError[],
  severity: "error" | "warning"
): ValidationError[] {
  return errors.filter((e) => e.severity === severity);
}
