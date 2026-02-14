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
 * Template 5: Login Form
 * Simple login form with username/password
 */
const loginFormTemplate: ScreenTemplate = {
  id: "login_form",
  name: "로그인 폼",
  description: "아이디/비밀번호 로그인 폼",
  preview: "🔐",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_title",
        type: "text",
        label: "타이틀",
        props: {
          text: "로그인",
          size: "xl",
          weight: "bold",
        },
      },
      {
        id: "comp_subtitle",
        type: "text",
        label: "부제목",
        props: {
          text: "계정에 로그인하세요",
          color: "muted",
        },
      },
      {
        id: "comp_username",
        type: "input",
        label: "아이디",
        props: {
          placeholder: "아이디를 입력하세요",
          value: "{{state.username}}",
        },
      },
      {
        id: "comp_password",
        type: "input",
        label: "비밀번호",
        props: {
          placeholder: "비밀번호를 입력하세요",
          type: "password",
          value: "{{state.password}}",
        },
      },
      {
        id: "comp_remember",
        type: "input",
        label: "로그인 유지",
        props: {
          type: "checkbox",
          checked: "{{state.remember_me}}",
        },
      },
      {
        id: "comp_login_btn",
        type: "button",
        label: "로그인 버튼",
        props: {
          label: "로그인",
          variant: "primary",
          loading: "{{state.is_loading}}",
        },
        actions: [
          {
            id: "action_login",
            handler: "auth.login",
            payload_template: {
              username: "{{state.username}}",
              password: "{{state.password}}",
              remember_me: "{{state.remember_me}}",
            },
            continue_on_error: false,
            stop_on_error: true,
            retry_count: 0,
          },
        ],
      },
      {
        id: "comp_error_msg",
        type: "text",
        label: "에러 메시지",
        props: {
          text: "{{state.error_message}}",
          color: "red",
        },
        visibility: { rule: "{{state.error_message}}" },
      },
    ],
    state: {
      schema: {
        username: { type: "string" },
        password: { type: "string" },
        remember_me: { type: "boolean" },
        is_loading: { type: "boolean" },
        error_message: { type: "string" },
      },
      initial: {
        username: "",
        password: "",
        remember_me: false,
        is_loading: false,
        error_message: "",
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "form",
      direction: "vertical",
      spacing: 16,
      max_width: "400px",
    },
  }),
};

/**
 * Template 6: Customer Detail
 * Customer information display with edit capability
 */
const customerDetailTemplate: ScreenTemplate = {
  id: "customer_detail",
  name: "고객 상세",
  description: "고객 정보 상세 화면 (조회/편집)",
  preview: "👤",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_header",
        type: "row",
        label: "헤더",
        props: {
          gap: 4,
        },
        children: [
          {
            id: "comp_back_btn",
            type: "button",
            label: "뒤로",
            props: {
              label: "← 목록",
              variant: "ghost",
            },
            actions: [
              {
                id: "action_go_back",
                handler: "navigate.back",
                payload_template: {},
              },
            ],
          },
          {
            id: "comp_title",
            type: "text",
            label: "타이틀",
            props: {
              text: "고객 상세 정보",
              size: "xl",
              weight: "bold",
            },
          },
        ],
      },
      {
        id: "comp_status_badge",
        type: "badge",
        label: "상태",
        props: {
          text: "{{state.customer.status}}",
          variant: "{{state.customer.status === 'active' ? 'success' : 'default'}}",
        },
      },
      {
        id: "comp_info_section",
        type: "keyvalue",
        label: "기본 정보",
        props: {
          items: [
            { key: "고객명", value: "{{state.customer.name}}" },
            { key: "이메일", value: "{{state.customer.email}}" },
            { key: "전화번호", value: "{{state.customer.phone}}" },
            { key: "가입일", value: "{{state.customer.created_at}}" },
          ],
          columns: 2,
        },
      },
      {
        id: "comp_address_section",
        type: "keyvalue",
        label: "주소 정보",
        props: {
          items: [
            { key: "주소", value: "{{state.customer.address}}" },
            { key: "상세주소", value: "{{state.customer.address_detail}}" },
          ],
        },
      },
      {
        id: "comp_actions",
        type: "row",
        label: "액션 버튼",
        props: {
          gap: 2,
        },
        children: [
          {
            id: "comp_edit_btn",
            type: "button",
            label: "편집",
            props: {
              label: "편집",
              variant: "outline",
            },
            actions: [
              {
                id: "action_open_edit",
                handler: "state.patch",
                payload_template: { edit_mode: true },
              },
            ],
          },
          {
            id: "comp_delete_btn",
            type: "button",
            label: "삭제",
            props: {
              label: "삭제",
              variant: "destructive",
            },
            actions: [
              {
                id: "action_delete",
                handler: "api_manager.execute",
                payload_template: {
                  api_id: "delete_customer",
                  customer_id: "{{state.customer.id}}",
                },
              },
            ],
          },
        ],
      },
    ],
    state: {
      schema: {
        customer: { type: "object" },
        edit_mode: { type: "boolean" },
      },
      initial: {
        customer: {
          id: "",
          name: "",
          email: "",
          phone: "",
          status: "active",
          address: "",
          address_detail: "",
          created_at: "",
        },
        edit_mode: false,
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
 * Template 7: Settings Form
 * Configuration/settings form with sections
 */
const settingsFormTemplate: ScreenTemplate = {
  id: "settings_form",
  name: "설정 폼",
  description: "사용자 설정/환경설정 폼",
  preview: "⚙️",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_title",
        type: "text",
        label: "타이틀",
        props: {
          text: "환경 설정",
          size: "xl",
          weight: "bold",
        },
      },
      {
        id: "comp_section_notifications",
        type: "text",
        label: "알림 섹션 타이틀",
        props: {
          text: "🔔 알림 설정",
          size: "lg",
          weight: "semibold",
        },
      },
      {
        id: "comp_email_notif",
        type: "input",
        label: "이메일 알림",
        props: {
          type: "checkbox",
          checked: "{{state.settings.email_notifications}}",
          label: "이메일 알림 받기",
        },
      },
      {
        id: "comp_push_notif",
        type: "input",
        label: "푸시 알림",
        props: {
          type: "checkbox",
          checked: "{{state.settings.push_notifications}}",
          label: "푸시 알림 받기",
        },
      },
      {
        id: "comp_section_display",
        type: "text",
        label: "화면 섹션 타이틀",
        props: {
          text: "🖥️ 화면 설정",
          size: "lg",
          weight: "semibold",
        },
      },
      {
        id: "comp_theme",
        type: "input",
        label: "테마",
        props: {
          type: "select",
          value: "{{state.settings.theme}}",
          options: [
            { value: "light", label: "라이트" },
            { value: "dark", label: "다크" },
            { value: "system", label: "시스템" },
          ],
        },
      },
      {
        id: "comp_language",
        type: "input",
        label: "언어",
        props: {
          type: "select",
          value: "{{state.settings.language}}",
          options: [
            { value: "ko", label: "한국어" },
            { value: "en", label: "English" },
          ],
        },
      },
      {
        id: "comp_save_btn",
        type: "button",
        label: "저장 버튼",
        props: {
          label: "설정 저장",
          variant: "primary",
        },
        actions: [
          {
            id: "action_save_settings",
            handler: "api_manager.execute",
            payload_template: {
              api_id: "update_settings",
              settings: "{{state.settings}}",
            },
            continue_on_error: false,
            retry_count: 2,
          },
        ],
      },
    ],
    state: {
      schema: {
        settings: { type: "object" },
      },
      initial: {
        settings: {
          email_notifications: true,
          push_notifications: false,
          theme: "system",
          language: "ko",
        },
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "form",
      direction: "vertical",
      spacing: 16,
      max_width: "500px",
    },
  }),
};

/**
 * Template 8: Notification List
 * Notifications/announcements list with read/unread
 */
const notificationListTemplate: ScreenTemplate = {
  id: "notification_list",
  name: "알림 목록",
  description: "공지사항/알림 목록 (읽음/안읽음)",
  preview: "🔔",
  generate: ({ screen_id, name }) => ({
    id: screen_id,
    screen_id,
    name,
    version: "1.0",
    components: [
      {
        id: "comp_header",
        type: "row",
        label: "헤더",
        props: {
          gap: 4,
          justify: "space-between",
        },
        children: [
          {
            id: "comp_title",
            type: "text",
            label: "타이틀",
            props: {
              text: "알림",
              size: "xl",
              weight: "bold",
            },
          },
          {
            id: "comp_mark_all",
            type: "button",
            label: "전체 읽음",
            props: {
              label: "전체 읽음 처리",
              variant: "ghost",
              size: "sm",
            },
            actions: [
              {
                id: "action_mark_all_read",
                handler: "api_manager.execute",
                payload_template: {
                  api_id: "mark_all_notifications_read",
                },
              },
            ],
          },
        ],
      },
      {
        id: "comp_filter_tabs",
        type: "tabs",
        label: "필터 탭",
        props: {
          value: "{{state.filter}}",
          tabs: [
            { value: "all", label: "전체" },
            { value: "unread", label: "안읽음" },
            { value: "important", label: "중요" },
          ],
        },
        actions: [
          {
            id: "action_change_filter",
            handler: "state.patch",
            payload_template: { filter: "{{context.tab_value}}" },
          },
        ],
      },
      {
        id: "comp_list",
        type: "table",
        label: "알림 목록",
        props: {
          rows: "{{state.notifications}}",
          columns: [
            { field: "title", header: "제목" },
            { field: "message", header: "내용" },
            { field: "created_at", header: "날짜" },
            { field: "is_read", header: "읽음" },
          ],
          row_class: "{{context.row.is_read ? 'opacity-50' : 'font-bold'}}",
        },
        actions: [
          {
            id: "action_mark_read",
            handler: "api_manager.execute",
            payload_template: {
              api_id: "mark_notification_read",
              notification_id: "{{context.row.id}}",
            },
          },
        ],
      },
    ],
    state: {
      schema: {
        notifications: { type: "array" },
        filter: { type: "string" },
      },
      initial: {
        notifications: [],
        filter: "all",
      },
    },
    actions: [],
    bindings: null,
    layout: {
      type: "list",
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
  loginFormTemplate,
  customerDetailTemplate,
  settingsFormTemplate,
  notificationListTemplate,
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
