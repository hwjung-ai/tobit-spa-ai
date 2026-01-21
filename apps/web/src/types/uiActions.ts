/**
 * TypeScript types for UI Actions (Interactive UI Panels)
 */

export interface UIInput {
  id: string;
  label: string;
  kind: "text" | "number" | "select" | "date" | "datetime" | "checkbox";
  required?: boolean;
  placeholder?: string;
  default?: unknown;
  options?: Array<{ label: string; value: unknown }>;
}

export interface UIAction {
  id: string;
  label: string;
  endpoint?: string;
  method?: "POST";
  payload_template: Record<string, unknown>;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
}

export interface UIBindings {
  loading?: string;
  error?: string;
  result_blocks?: string;
}

export interface UIPanelBlock {
  type: "ui_panel";
  title?: string;
  id?: string;
  inputs: UIInput[];
  actions: UIAction[];
  bindings?: UIBindings;
}
