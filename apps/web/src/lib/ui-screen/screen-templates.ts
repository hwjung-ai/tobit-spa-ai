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
        actions: [
          {
            id: "action_search_maintenance",
            handler: "list_maintenance_filtered",
            payload_template: {
              device_id: "{{state.search_term}}",
              offset: 0,
              limit: 20,
            },
          },
        ],
      },
      {
        id: "comp_datagrid",
        type: "table",
        label: "Data Grid",
        props: {
          rows: "{{state.maintenance_list}}",
          columns: [
            "id",
            "device_id",
            "type",
            "status",
            "date",
          ],
          auto_refresh: {
            enabled: true,
            interval_ms: 30000,
            action_index: 0,
            max_failures: 3,
            backoff_ms: 10000,
          },
          sortable: true,
          page_size: 10,
        },
        visibility: { rule: "true" },
        actions: [
          {
            id: "action_refresh_maintenance_list",
            handler: "list_maintenance_filtered",
            payload_template: {
              device_id: "{{state.search_term}}",
              offset: "{{state.pagination.offset}}",
              limit: "{{state.pagination.limit}}",
            },
          },
        ],
      },
    ],
    state: {
      schema: {
        search_term: { type: "string" },
        items: { type: "array" },
        maintenance_list: { type: "array" },
        pagination: { type: "object" },
      },
      initial: {
        search_term: "",
        items: [],
        maintenance_list: [],
        pagination: {
          offset: 0,
          limit: 20,
          total: 0,
        },
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
            handler: "state.merge",
            payload_template: {
              patch: {
                modal_open: true,
                is_edit: false,
                modal_title: "Create Item",
              },
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
          sortable: true,
          page_size: 10,
          row_click_action_index: 0,
        },
        visibility: { rule: "true" },
        actions: [
          {
            id: "action_edit_row",
            handler: "state.merge",
            payload_template: {
              patch: {
                modal_open: true,
                is_edit: true,
                modal_title: "Edit Item",
              },
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
          title: "{{state.modal_title}}",
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
                handler: "create_maintenance_ticket",
                payload_template: {
                  device_id: "{{state.form_name}}",
                  maintenance_type: "{{state.form_status}}",
                  scheduled_date: "{{state.form_date}}",
                  assigned_to: "{{context.user_id}}",
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
                handler: "state.merge",
                context_required: [],
                payload_template: {
                  patch: {
                    modal_open: false,
                  },
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
        form_date: { type: "string" },
        modal_title: { type: "string" },
      },
      initial: {
        items: [],
        modal_open: false,
        is_edit: false,
        modal_title: "Create Item",
        form_name: "",
        form_status: "",
        form_date: "",
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
 * Template 4: Observability Dashboard
 * KPI + trend chart + incidents table with auto-refresh actions
 */
const observabilityDashboardTemplate: ScreenTemplate = {
  id: "observability_dashboard",
  name: "Observability Dashboard",
  description: "Operational dashboard with metrics trend and incident list",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "obs_header",
        type: "row",
        label: "Header Row",
        props: {
          gap: 4,
          components: [
            {
              id: "obs_title",
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
              id: "obs_refresh_button",
              type: "button",
              label: "Refresh",
              props: {
                text: "Refresh",
              },
              visibility: { rule: "true" },
              actions: [
                {
                  id: "obs_action_refresh_list",
                  handler: "list_maintenance_filtered",
                  payload_template: {
                    device_id: "{{state.selected_device}}",
                    offset: 0,
                    limit: 20,
                  },
                },
              ],
            },
          ],
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "obs_kpi_row",
        type: "row",
        label: "KPI Row",
        props: {
          gap: 3,
          components: [
            {
              id: "obs_kpi_total",
              type: "keyvalue",
              label: "Total Incidents",
              props: {
                items: [
                  { key: "total", value: "{{state.kpi_total}}" },
                  { key: "critical", value: "{{state.kpi_critical}}" },
                ],
              },
              visibility: { rule: "true" },
              actions: [],
            },
            {
              id: "obs_kpi_last",
              type: "keyvalue",
              label: "Last Refresh",
              props: {
                items: [{ key: "updated_at", value: "{{state.last_refresh}}" }],
              },
              visibility: { rule: "true" },
              actions: [],
            },
          ],
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "obs_chart",
        type: "chart",
        label: "Incident Trend",
        props: {
          data: "{{state.metric_points}}",
          x_key: "ts",
          series: [
            { data_key: "count", color: "#38bdf8", name: "Incidents" },
            { data_key: "error", color: "#f87171", name: "Errors" },
          ],
        },
        visibility: { rule: "true" },
        actions: [],
      },
      {
        id: "obs_table",
        type: "table",
        label: "Incident Table",
        props: {
          rows: "{{state.maintenance_list}}",
          columns: [
            { field: "id", header: "ID", sortable: true },
            { field: "device_id", header: "Device", sortable: true },
            { field: "type", header: "Type", sortable: true },
            { field: "status", header: "Status", sortable: true },
            { field: "date", header: "Date", sortable: true },
          ],
          sortable: true,
          page_size: 10,
          row_click_action_index: 1,
          auto_refresh: {
            enabled: true,
            interval_ms: 30000,
            action_index: 0,
            max_failures: 3,
            backoff_ms: 10000,
          },
        },
        visibility: { rule: "true" },
        actions: [
          {
            id: "obs_action_auto_refresh",
            handler: "list_maintenance_filtered",
            payload_template: {
              device_id: "{{state.selected_device}}",
              offset: "{{state.pagination.offset}}",
              limit: "{{state.pagination.limit}}",
            },
          },
          {
            id: "obs_action_select_row",
            handler: "state.merge",
            payload_template: {
              patch: {
                selected_row: "{{context.row}}",
                selected_device: "{{context.row.device_id}}",
              },
            },
          },
        ],
      },
    ],
    state: {
      schema: {
        selected_device: { type: "string" },
        selected_row: { type: "object" },
        maintenance_list: { type: "array" },
        pagination: { type: "object" },
        metric_points: { type: "array" },
        kpi_total: { type: "number" },
        kpi_critical: { type: "number" },
        last_refresh: { type: "string" },
      },
      initial: {
        selected_device: "",
        selected_row: {},
        maintenance_list: [],
        pagination: { offset: 0, limit: 20, total: 0 },
        metric_points: [],
        kpi_total: 0,
        kpi_critical: 0,
        last_refresh: "",
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "dashboard",
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
  observabilityDashboardTemplate,
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
