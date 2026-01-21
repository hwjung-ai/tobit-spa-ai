/**
 * Template substitution utility for UI Actions
 * Supports: {{trace_id}}, {{inputs.<id>}}, {{action_id}}
 */

export function substituteTemplate(
  template: unknown,
  context: {
    trace_id: string;
    action_id: string;
    inputs: Record<string, unknown>;
  }
): unknown {
  if (typeof template === "string") {
    return template
      .replace(/\{\{trace_id\}\}/g, context.trace_id)
      .replace(/\{\{action_id\}\}/g, context.action_id)
      .replace(/\{\{inputs\.(\w+)\}\}/g, (match, inputId) => {
        const value = context.inputs[inputId];
        return value !== undefined && value !== null ? String(value) : "";
      });
  }

  if (Array.isArray(template)) {
    return template.map((item) => substituteTemplate(item, context));
  }

  if (typeof template === "object" && template !== null) {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(template)) {
      result[key] = substituteTemplate(value, context);
    }
    return result;
  }

  return template;
}
