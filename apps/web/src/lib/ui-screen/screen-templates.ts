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
    name,
    version: 1,
    components: [
      {
        id: "comp_title",
        type: "Text",
        label: "Title",
        props: {
          text: name,
          variant: "heading",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_label_id",
        type: "Text",
        label: "ID Label",
        props: {
          text: "ID:",
          variant: "label",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_value_id",
        type: "Text",
        label: "ID Value",
        props: {
          text: "{{state.device_id}}",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_label_name",
        type: "Text",
        label: "Name Label",
        props: {
          text: "Name:",
          variant: "label",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_value_name",
        type: "Text",
        label: "Name Value",
        props: {
          text: "{{state.device_name}}",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_label_status",
        type: "Text",
        label: "Status Label",
        props: {
          text: "Status:",
          variant: "label",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_value_status",
        type: "Text",
        label: "Status Value",
        props: {
          text: "{{state.status}}",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
    ],
    state: {
      schema: {
        device_id: "string",
        device_name: "string",
        status: "string",
      },
      initial_values: {
        device_id: "",
        device_name: "",
        status: "",
      },
    },
    actions: [],
    layout: {
      type: "vertical",
      spacing: "md",
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
    name,
    version: 1,
    components: [
      {
        id: "comp_title",
        type: "Text",
        label: "Title",
        props: {
          text: name,
          variant: "heading",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_filter_label",
        type: "Text",
        label: "Filter Label",
        props: {
          text: "Search:",
          variant: "label",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_search_input",
        type: "Input",
        label: "Search Input",
        props: {
          placeholder: "Enter search term",
          value: "{{state.search_term}}",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_datagrid",
        type: "DataGrid",
        label: "Data Grid",
        props: {
          data: "{{state.items}}",
          columns: [
            { field: "id", header: "ID" },
            { field: "name", header: "Name" },
            { field: "status", header: "Status" },
          ],
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
    ],
    state: {
      schema: {
        search_term: "string",
        items: "array",
      },
      initial_values: {
        search_term: "",
        items: [],
      },
    },
    actions: [],
    layout: {
      type: "vertical",
      spacing: "md",
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
    name,
    version: 1,
    components: [
      {
        id: "comp_title",
        type: "Text",
        label: "Title",
        props: {
          text: name,
          variant: "heading",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [],
      },
      {
        id: "comp_create_btn",
        type: "Button",
        label: "Create Button",
        props: {
          text: "Create New",
        },
        visibility: { rule: "true", mode: "always" },
        actions: [
          {
            id: "action_open_create_modal",
            handler: "set_state",
            context_required: [],
            payload_template: {
              modal_open: "true",
              is_edit: "false",
            },
          },
        ],
      },
      {
        id: "comp_datagrid",
        type: "DataGrid",
        label: "Data Grid",
        props: {
          data: "{{state.items}}",
          columns: [
            { field: "id", header: "ID" },
            { field: "name", header: "Name" },
            { field: "status", header: "Status" },
          ],
        },
        visibility: { rule: "true", mode: "always" },
        actions: [
          {
            id: "action_edit_row",
            handler: "set_state",
            context_required: [],
            payload_template: {
              modal_open: "true",
              is_edit: "true",
            },
          },
        ],
      },
      {
        id: "comp_modal",
        type: "Modal",
        label: "Edit Modal",
        props: {
          open: "{{state.modal_open}}",
          title: "{{state.is_edit ? 'Edit' : 'Create'}} Item",
        },
        visibility: { rule: "{{state.modal_open}}", mode: "when_true" },
        actions: [],
        children: [
          {
            id: "comp_form_name",
            type: "Input",
            label: "Name",
            props: {
              placeholder: "Item name",
              value: "{{state.form_name}}",
            },
            visibility: { rule: "true", mode: "always" },
            actions: [],
          },
          {
            id: "comp_form_status",
            type: "Input",
            label: "Status",
            props: {
              placeholder: "Status",
              value: "{{state.form_status}}",
            },
            visibility: { rule: "true", mode: "always" },
            actions: [],
          },
          {
            id: "comp_save_btn",
            type: "Button",
            label: "Save",
            props: {
              text: "Save",
            },
            visibility: { rule: "true", mode: "always" },
            actions: [
              {
                id: "action_save_item",
                handler: "http_request",
                context_required: ["device_id"],
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
            type: "Button",
            label: "Cancel",
            props: {
              text: "Cancel",
            },
            visibility: { rule: "true", mode: "always" },
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
        items: "array",
        modal_open: "boolean",
        is_edit: "boolean",
        form_name: "string",
        form_status: "string",
      },
      initial_values: {
        items: [],
        modal_open: false,
        is_edit: false,
        form_name: "",
        form_status: "",
      },
    },
    actions: [],
    layout: {
      type: "vertical",
      spacing: "md",
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
  name: string
): ScreenSchemaV1 {
  return {
    id: screen_id,
    name,
    version: 1,
    components: [],
    state: {
      schema: {},
      initial_values: {},
    },
    actions: [],
    layout: {
      type: "vertical",
      spacing: "md",
    },
  };
}
