/*
  Component Registry v1 - frontend side
  - Lists supported components (10) with props schema, supported bindings, and events.
  - This registry is the source-of-truth used by UIScreenRenderer to map component.type
    to actual React components and to validate props/bindings.
*/

export type BindingKind = "state" | "result";

type JsonSchema = {
  type: string | string[];
  properties?: Record<string, JsonSchema>;
  required?: string[];
  items?: JsonSchema;
};

export interface ComponentDescriptor {
  type: string;
  label: string;
  propsSchema: JsonSchema | null;
  supportedBindings: BindingKind[];
  events: string[];
}

const TEXT_PROPS: JsonSchema = {
  type: "object",
  properties: {
    content: { type: "string" },
    variant: { type: "string" },
    color: { type: "string" },
  },
};

const BUTTON_PROPS: JsonSchema = {
  type: "object",
  properties: {
    label: { type: "string" },
    variant: { type: "string" },
    disabled: { type: "boolean" },
  },
};

const INPUT_PROPS: JsonSchema = {
  type: "object",
  properties: {
    placeholder: { type: "string" },
    inputType: { type: "string" },
    name: { type: "string" },
  },
};

const TABLE_PROPS: JsonSchema = {
  type: "object",
  properties: {
    columns: { type: "array" },
    rows: { type: "array" },
    selectable: { type: "boolean" },
  },
};

const CHART_PROPS: JsonSchema = {
  type: "object",
  properties: {
    type: { type: "string" },
    series: { type: "array" },
    options: { type: "object" },
  },
};

const BADGE_PROPS: JsonSchema = {
  type: "object",
  properties: {
    label: { type: "string" },
    variant: { type: "string" },
    color: { type: "string" },
  },
};

const TABS_PROPS: JsonSchema = {
  type: "object",
  properties: {
    tabs: { type: "array" },
    activeIndex: { type: "number" },
  },
};

const MODAL_PROPS: JsonSchema = {
  type: "object",
  properties: {
    title: { type: "string" },
    size: { type: "string" },
    open: { type: "boolean" },
    components: { type: "array" },
  },
};

const KEYVALUE_PROPS: JsonSchema = {
  type: "object",
  properties: {
    items: { type: "array" },
  },
};

const DIVIDER_PROPS: JsonSchema = {
  type: "object",
  properties: {
    orientation: { type: "string" },
  },
};

export const COMPONENT_REGISTRY: ComponentDescriptor[] = [
  {
    type: "text",
    label: "Text",
    propsSchema: TEXT_PROPS,
    supportedBindings: ["state"],
    events: [],
  },
  {
    type: "markdown",
    label: "Markdown",
    propsSchema: TEXT_PROPS,
    supportedBindings: ["state"],
    events: [],
  },
  {
    type: "button",
    label: "Button",
    propsSchema: BUTTON_PROPS,
    supportedBindings: ["state"],
    events: ["onClick"],
  },
  {
    type: "input",
    label: "Input (form)",
    propsSchema: INPUT_PROPS,
    supportedBindings: ["state"],
    events: ["onChange", "onSubmit"],
  },
  {
    type: "table",
    label: "DataTable",
    propsSchema: TABLE_PROPS,
    supportedBindings: ["state", "result"],
    events: ["onRowSelect", "onRowClick"],
  },
  {
    type: "chart",
    label: "Chart",
    propsSchema: CHART_PROPS,
    supportedBindings: ["state", "result"],
    events: ["onHover", "onClick"],
  },
  {
    type: "badge",
    label: "Badge",
    propsSchema: BADGE_PROPS,
    supportedBindings: ["state"],
    events: [],
  },
  {
    type: "tabs",
    label: "Tabs",
    propsSchema: TABS_PROPS,
    supportedBindings: ["state"],
    events: ["onTabChange"],
  },
  {
    type: "modal",
    label: "Modal",
    propsSchema: MODAL_PROPS,
    supportedBindings: ["state"],
    events: ["onOpen", "onClose"],
  },
  {
    type: "keyvalue",
    label: "KeyValue",
    propsSchema: KEYVALUE_PROPS,
    supportedBindings: ["state"],
    events: [],
  },
  {
    type: "divider",
    label: "Divider",
    propsSchema: DIVIDER_PROPS,
    supportedBindings: [],
    events: [],
  },
];

export function getComponentDescriptor(type: string): ComponentDescriptor | undefined {
  return COMPONENT_REGISTRY.find((c) => c.type === type);
}
