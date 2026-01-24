/**
 * Screen Templates for U3-2
 * Provides 3 pre-built templates for rapid screen creation:
 * 1. Read-only Detail - Display device/entity details with labeled text fields
 * 2. List + Filter - Searchable/filterable data grid
 * 3. List + Modal CRUD - Data grid with create/edit modal
 */

import { ScreenSchemaV1 } from "./screen.schema";

export interface ScreenTemplate {
  id: string;
  name: string;
  description: string;
  preview?: string;
  generate: (params: { screen_id: string; name: string }) => ScreenSchemaV1;
}

/**
 * Template 1: Read-only Detail
 * Displays entity details in labeled rows
 */
const readOnlyDetailTemplate: ScreenTemplate = {
  id: "readonly_detail",
  name: "Read-only Detail",
  description: "Display device/entity details with labeled text fields",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_title",
        type: "text",
        label: "Title",
        props: {
          text: name,
          variant: "heading",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_label_id",
        type: "text",
        label: "ID Label",
        props: {
          text: "ID:",
          variant: "label",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_value_id",
        type: "text",
        label: "ID Value",
        props: {
          text: "{{state.device_id}}",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_label_name",
        type: "text",
        label: "Name Label",
        props: {
          text: "Name:",
          variant: "label",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_value_name",
        type: "text",
        label: "Name Value",
        props: {
          text: "{{state.device_name}}",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_label_status",
        type: "text",
        label: "Status Label",
        props: {
          text: "Status:",
          variant: "label",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_value_status",
        type: "text",
        label: "Status Value",
        props: {
          text: "{{state.status}}",
        },
        visibility: { rule: "true" },
        actions: [],
      },
    ],
    state: {
      schema: {
        device_id: { type: "string" },
        device_name: { type: "string" },
        status: { type: "string" },
      },
      initial: {
        device_id: "",
        device_name: "",
        status: "",
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "form",
      direction: "vertical",
      spacing: 16,
    },
  }),
};

/**
 * Template 2: List + Filter
 * Data grid with search/filter inputs
 */
const listFilterTemplate: ScreenTemplate = {
  id: "list_filter",
  name: "List + Filter",
  description: "Searchable/filterable data grid",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_title",
        type: "text",
        label: "Title",
        props: {
          text: name,
          variant: "heading",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_filter_label",
        type: "text",
        label: "Filter Label",
        props: {
          text: "Search:",
          variant: "label",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_search_input",
        type: "input",
        label: "Search Input",
        props: {
          placeholder: "Enter search term",
          value: "{{state.search_term}}",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_datagrid",
        type: "table",
        label: "Data Grid",
        props: {
          data: "{{state.items}}",
          columns: [
            { field: "id", header: "ID" },
            { field: "name", header: "Name" },
            { field: "status", header: "Status" },
          ],
        },
        visibility: { rule: "true" },
        actions: [],
      },
    ],
    state: {
      schema: {
        search_term: { type: "string" },
        items: { type: "array" },
      },
      initial: {
        search_term: "",
        items: [],
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "form",
      direction: "vertical",
      spacing: 16,
    },
  }),
};

/**
 * Template 3: List + Modal CRUD
 * Data grid with create/edit modal
 */
const listModalCrudTemplate: ScreenTemplate = {
  id: "list_modal_crud",
  name: "List + Modal CRUD",
  description: "Data grid with create/edit modal",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_title",
        type: "text",
        label: "Title",
        props: {
          text: name,
          variant: "heading",
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "comp_create_btn",
        type: "button",
        label: "Create Button",
        props: {
          text: "Create New",
        },
        visibility: { rule: "true" },
        actions: [
          {
            id: "action_open_create_modal",
            handler: "set_state",
            payload_template: {
              modal_open: "true",
              is_edit: "false",
            },
          },
        ],
      },
      {
        id: "comp_datagrid",
        type: "table",
        label: "Data Grid",
        props: {
          data: "{{state.items}}",
          columns: [
            { field: "id", header: "ID" },
            { field: "name", header: "Name" },
            { field: "status", header: "Status" },
          ],
        },
        visibility: { rule: "true" },
        actions: [
          {
            id: "action_edit_row",
            handler: "set_state",
            payload_template: {
              modal_open: "true",
              is_edit: "true",
            },
          },
        ],
      },
      {
        id: "comp_modal",
        type: "modal",
        label: "Edit Modal",
        props: {
          open: "{{state.modal_open}}",
          title: "{{state.is_edit ? 'Edit' : 'Create'}} Item",
        },
        visibility: { rule: "{{state.modal_open}}" },
        actions: [],
        children: [
          {
            id: "comp_form_name",
            type: "input",
            label: "Name",
            props: {
              placeholder: "Item name",
              value: "{{state.form_name}}",
            },
            visibility: { rule: "true" },
            actions: [],
          },
          {
            id: "comp_form_status",
            type: "input",
            label: "Status",
            props: {
              placeholder: "Status",
              value: "{{state.form_status}}",
            },
            visibility: { rule: "true" },
            actions: [],
          },
          {
            id: "comp_save_btn",
            type: "button",
            label: "Save",
            props: {
              text: "Save",
            },
            visibility: { rule: "true" },
            actions: [
              {
                id: "action_save_item",
                handler: "http_request",
                payload_template: {
                  method: "POST",
                  endpoint: "/api/items",
                  body: {
                    name: "{{state.form_name}}",
                    status: "{{state.form_status}}",
                  },
                },
              },
            ],
          },
          {
            id: "comp_cancel_btn",
            type: "button",
            label: "Cancel",
            props: {
              text: "Cancel",
            },
            visibility: { rule: "true" },
            actions: [
              {
                id: "action_close_modal",
                handler: "set_state",
                context_required: [],
                payload_template: {
                  modal_open: "false",
                },
              },
            ],
          },
        ],
      },
    ],
    state: {
      schema: {
        items: { type: "array" },
        modal_open: { type: "boolean" },
        is_edit: { type: "boolean" },
        form_name: { type: "string" },
        form_status: { type: "string" },
      },
      initial: {
        items: [],
        modal_open: false,
        is_edit: false,
        form_name: "",
        form_status: "",
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "form",
      direction: "vertical",
      spacing: 16,
    },
  }),
};

/**
 * All available templates
 */
export const SCREEN_TEMPLATES: ScreenTemplate[] = [
  readOnlyDetailTemplate,
  listFilterTemplate,
  listModalCrudTemplate,
];

/**
 * Get template by ID
 */
export function getTemplateById(id: string): ScreenTemplate | undefined {
  return SCREEN_TEMPLATES.find((t) => t.id === id);
}

/**
 * Helper: Create a minimal blank screen
 */
export function createMinimalScreen(
  screen_id: string,
  name?: string
): ScreenSchemaV1 {
  return {
    id: screen_id,
    screen_id,
    name: name || screen_id,
    version: "1.0",
    components: [],
    state: {
      schema: {},
      initial: {},
    },
    actions: [],
    bindings: null,
    layout: {
      type: "form",
      direction: "vertical",
      spacing: 16,
    },
  };
}
