/*
  Screen Schema v1 - TypeScript types
  Location: apps/web/src/lib/ui-screen/screen.schema.ts

  NOTE: This file contains the TypeScript representation of the Screen Schema v1
  as agreed in CONTRACT_UI_CREATOR_V1.md. This is the canonical TypeScript type
  surface used by the frontend runtime. JSON Schema for runtime validation is
  provided in screen.schema.json (same folder).

  Implementation constraints:
  - Dot-path-only binding semantics are documented in the contract.
  - Expansion points (computed expressions, plugins, custom components) are
    intentionally left as comments/documentation only and NOT implemented.
*/

export type LayoutType = "grid" | "form" | "modal" | "list" | "dashboard";
export type LayoutDirection = "horizontal" | "vertical";

export interface LayoutWidthAuto {
  type: "auto";
}

export interface LayoutWidthPercent {
  type: "percent";
  value: number;
}

export interface LayoutWidthRatio {
  type: "ratio";
  value: [number, number];
}

export type LayoutWidth = LayoutWidthAuto | LayoutWidthPercent | LayoutWidthRatio;

export interface LayoutChild {
  component_id?: string;
  direction?: LayoutDirection;
  width?: LayoutWidth;
  children?: LayoutChild[];
}

export interface Layout {
  type: LayoutType;
  direction?: LayoutDirection; // default: vertical
  spacing?: number; // pixels
  max_width?: string; // css width
  children?: LayoutChild[];
}

// Minimal primitive prop types used in MVP
export type Primitive = string | number | boolean | null;
export type PropsMap = Record<string, unknown>;

export type ComponentType =
  | "text"
  | "markdown"
  | "button"
  | "input"
  | "table"
  | "chart"
  | "badge"
  | "tabs"
  | "modal"
  | "keyvalue"
  | "divider"
  | "row"
  | "column";

export interface ScreenAction {
  id: string; // unique within the screen
  label?: string;
  handler: string; // executor action_id (routed to /ops/ui-actions)
  endpoint?: string; // default: /ops/ui-actions (allowed but ignored by runtime)
  method?: "POST"; // fixed to POST in contract
  payload_template?: Record<string, unknown>;
  context_required?: string[];
}

export interface ComponentActionRef {
  id: string;
  label?: string;
  handler: string;
  payload_template?: Record<string, unknown>;
}

export interface ComponentBase {
  id: string;
  type: ComponentType;
  label?: string;
  bind?: string | null; // dot-path into state, e.g. state.items
  props?: PropsMap; // component-specific props
  visibility?: { rule?: string | null } | null; // rule syntax reserved (not implemented)
  actions?: ComponentActionRef[] | null; // local actions
  // Note: nested components (e.g. modal.components) can be typed as `components?: Component[]`
}

export interface TableComponent extends ComponentBase {
  type: "table";
  props?: PropsMap & {
    columns?: string[];
    rows?: unknown[]; // typically bound like "{{state.items}}"
    selectable?: boolean;
  };
}

export type Component = ComponentBase | TableComponent;

export type StateSchemaPrimitive =
  | { type: "string" }
  | { type: "number" }
  | { type: "boolean" }
  | { type: "object"; properties?: Record<string, unknown> }
  | { type: "array"; items?: unknown }
  | { type: "any" };

export interface StateSchema {
  // initial values (actual runtime state) and their JSON Schema-like types
  // Example:
  // {
  //   "device_id": { type: "string" },
  //   "items": { type: "array" }
  // }
  [key: string]: StateSchemaPrimitive;
}

export interface ScreenSchemaV1 {
  // REQUIRED: stable id of the screen (contract requested)
  screen_id: string;

  // Schema version
  version?: string; // default: "1.0"

  // Layout description
  layout: Layout;

  // Component tree (flat array for MVP). Components may reference nested components
  // using `props.components` for modal or tabs; runtime will render recursively.
  components: Component[];

  // Top-level actions (reusable handlers across components)
  actions: ScreenAction[] | null;

  // Initial state schema / shape. Runtime will initialize state according to this.
  state: { initial: { [k: string]: unknown }; schema?: StateSchema } | null;

  // Optional top-level bindings map for quick state initialization
  // key: target path in screen (e.g. params.device_id), value: source e.g. "state.selected_device_id"
  bindings: { [targetPath: string]: string } | null;

  // Metadata
  metadata?: {
    author?: string | null;
    created_at?: string | null;
    notes?: string | null;
    tags?: Record<string, string> | null;
  } | null;
}

// MVP-subset type helper: only fields/components required for minimal rendering
export type ScreenSchemaMVPSlim = Pick<
  ScreenSchemaV1,
  "screen_id" | "version" | "layout" | "components" | "state" | "actions" | "bindings"
>;

// Export a runtime helper type guard
export function isScreenSchemaV1(obj: unknown): obj is ScreenSchemaV1 {
  return !!(obj && typeof obj === "object" && "screen_id" in obj && typeof (obj as ScreenSchemaV1).screen_id === "string" && Array.isArray((obj as ScreenSchemaV1).components) && (obj as ScreenSchemaV1).layout);
}
