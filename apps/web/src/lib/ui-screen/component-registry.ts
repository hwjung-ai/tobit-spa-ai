/*
  Component Registry v1 - frontend side
  - Lists supported components (10) with props schema, supported bindings, and events.
  - This registry is the source-of-truth used by UIScreenRenderer to map component.type
    to actual React components and to validate props/bindings.
*/

export type BindingKind = "state" | "result";

type JsonSchema = {
  type: string | string[];
  title?: string;
  description?: string;
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
    fontSize: {
      type: "string",
      title: "Font Size",
      description: "Text size (xs, sm, base, lg, xl, 2xl, 3xl, 4xl)"
    },
    fontWeight: {
      type: "string",
      title: "Font Weight",
      description: "Font weight (normal, medium, semibold, bold)"
    },
  },
};

const BUTTON_PROPS: JsonSchema = {
  type: "object",
  properties: {
    label: { type: "string" },
    variant: { type: "string" },
    disabled: { type: "boolean" },
    fontSize: {
      type: "string",
      title: "Font Size",
      description: "Button text size (xs, sm, base, lg)"
    },
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

const FORM_PROPS: JsonSchema = {
  type: "object",
  properties: {
    title: { type: "string" },
    submit_label: { type: "string" },
    components: { type: "array" },
  },
};

const TABLE_PROPS: JsonSchema = {
  type: "object",
  properties: {
    columns: { type: "array" },
    rows: { type: "array" },
    selectable: { type: "boolean" },
    sortable: { type: "boolean" },
    page_size: { type: "integer" },
    row_click_action_index: { type: "integer" },
    auto_refresh: { type: "object" },
    conditional_styles: { type: "array" },
  },
};

const CHART_PROPS: JsonSchema = {
  type: "object",
  properties: {
    chart_type: { type: "string" },
    type: { type: "string" },
    data: { type: "array" },
    x_key: { type: "string" },
    show_legend: { type: "boolean" },
    show_grid: { type: "boolean" },
    y_min: { type: "number" },
    y_max: { type: "number" },
    series: { type: "array" },
    y_axis: { type: "object" },
    legend: { type: "object" },
    tooltip: { type: "object" },
    height: { type: "number" },
    responsive: { type: "boolean" },
    options: { type: "object" },
    conditional_styles: { type: "array" },
  },
};

const BADGE_PROPS: JsonSchema = {
  type: "object",
  properties: {
    label: { type: "string" },
    variant: { type: "string" },
    color: { type: "string" },
    conditional_styles: { type: "array" },
  },
};

const TABS_PROPS: JsonSchema = {
  type: "object",
  properties: {
    tabs: { type: "array" },
    activeIndex: { type: "number" },
  },
};

const ACCORDION_PROPS: JsonSchema = {
  type: "object",
  properties: {
    items: { type: "array" },
    allow_multiple: { type: "boolean" },
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
    fontSize: {
      type: "string",
      title: "Font Size",
      description: "Text size (xs, sm, base, lg, xl)"
    },
  },
};

const DIVIDER_PROPS: JsonSchema = {
  type: "object",
  properties: {
    orientation: { type: "string" },
  },
};

const ROW_PROPS: JsonSchema = {
  type: "object",
  properties: {
    gap: { type: "number" },
    align: { type: "string" }, // "start" | "center" | "end" | "stretch"
    justify: { type: "string" }, // "start" | "center" | "end" | "between" | "around"
    components: { type: "array" },
  },
};

const COLUMN_PROPS: JsonSchema = {
  type: "object",
  properties: {
    gap: { type: "number" },
    align: { type: "string" }, // "start" | "center" | "end" | "stretch"
    components: { type: "array" },
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
    type: "form",
    label: "Form",
    propsSchema: FORM_PROPS,
    supportedBindings: ["state"],
    events: ["onSubmit"],
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
    type: "accordion",
    label: "Accordion",
    propsSchema: ACCORDION_PROPS,
    supportedBindings: ["state"],
    events: ["onToggle"],
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
  {
    type: "row",
    label: "Row (horizontal)",
    propsSchema: ROW_PROPS,
    supportedBindings: [],
    events: [],
  },
  {
    type: "column",
    label: "Column (vertical)",
    propsSchema: COLUMN_PROPS,
    supportedBindings: [],
    events: [],
  },
];

export function getComponentDescriptor(type: string): ComponentDescriptor | undefined {
  return COMPONENT_REGISTRY.find((c) => c.type === type);
}
