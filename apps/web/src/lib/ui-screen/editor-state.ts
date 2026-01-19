import { create } from "zustand";
import { ScreenSchemaV1, Component, ScreenAction, ComponentActionRef } from "./screen.schema";
import { getComponentDescriptor } from "./component-registry";
import { validateBindingPath, validateActionHandler, validateScreenSchema } from "./validation-utils";
import { parseBindingExpression, formatBindingExpression } from "./binding-path-utils";
import { fetchApi } from "../adminUtils";

export interface ValidationError {
  path: string;
  message: string;
  severity: "error" | "warning";
}

export interface EditorState {
  // State
  screen: ScreenSchemaV1 | null;
  draft: ScreenSchemaV1 | null;
  published: ScreenSchemaV1 | null;
  selectedComponentId: string | null;
  draftModified: boolean;
  status: "draft" | "published";
  validationErrors: ValidationError[];
  isSaving: boolean;
  isPublishing: boolean;
  isRollbacking: boolean;

  // Computed
  selectedComponent: Component | null;
  isDirty: boolean;
  canPublish: boolean;
  canRollback: boolean;

  // Actions
  loadScreen: (assetId: string) => Promise<void>;
  initializeScreen: (screen: ScreenSchemaV1, status: "draft" | "published") => void;
  addComponent: (type: string, index?: number) => void;
  deleteComponent: (id: string) => void;
  selectComponent: (id: string | null) => void;
  updateComponentProps: (id: string, props: Record<string, any>) => void;
  updateComponentLabel: (id: string, label: string) => void;
  moveComponent: (id: string, direction: "up" | "down") => void;
  updateLayout: (layout: any) => void;
  updateScreenFromJson: (json: string) => void;

  // Action CRUD (screen-level)
  addAction: (action: ScreenAction) => void;
  updateAction: (actionId: string, updates: Partial<ScreenAction>) => void;
  deleteAction: (actionId: string) => void;
  getAction: (actionId: string) => ScreenAction | null;

  // Component Action CRUD
  addComponentAction: (componentId: string, action: ComponentActionRef) => void;
  updateComponentAction: (componentId: string, actionId: string, updates: Partial<ComponentActionRef>) => void;
  deleteComponentAction: (componentId: string, actionId: string) => void;
  getComponentActions: (componentId: string) => ComponentActionRef[];

  // Binding management
  updateBinding: (targetPath: string, sourcePath: string) => void;
  deleteBinding: (targetPath: string) => void;
  getAllBindings: () => Record<string, string>;

  // Component visibility
  updateComponentVisibility: (componentId: string, visibleIf: string | null) => void;

  // Action testing (Phase 4)
  testAction: (actionId: string, payload?: Record<string, any>) => Promise<any>;
  applyStatePatch: (patch: Record<string, any>) => void;

  saveDraft: () => Promise<void>;
  publish: () => Promise<void>;
  rollback: () => Promise<void>;
  validateScreen: () => ValidationError[];
  reset: () => void;
  setAssetId: (assetId: string) => void;
}

// Helper to generate unique component ID
function generateComponentId(type: string, existingComponents: Component[]): string {
  let counter = 1;
  let id = `${type}_${counter}`;
  while (existingComponents.some(c => c.id === id)) {
    counter++;
    id = `${type}_${counter}`;
  }
  return id;
}

// Helper to generate unique action ID
function generateActionId(existingActions: ScreenAction[]): string {
  let counter = 1;
  let id = `action_${counter}`;
  while (existingActions.some(a => a.id === id)) {
    counter++;
    id = `action_${counter}`;
  }
  return id;
}

// Helper to create default component
function createDefaultComponent(type: string, id: string): Component {
  const descriptor = getComponentDescriptor(type);
  return {
    id,
    type,
    label: descriptor?.label || type,
    props: {},
  };
}

// Validation function - uses comprehensive validation from validation-utils
function validateScreen(screen: ScreenSchemaV1): ValidationError[] {
  try {
    // Use the comprehensive validation from validation-utils
    return validateScreenSchema(screen);
  } catch (error) {
    // Fallback basic validation if comprehensive validation fails
    console.warn("Comprehensive validation failed, using fallback:", error);
    const errors: ValidationError[] = [];

    if (!screen.screen_id) {
      errors.push({ path: "screen_id", message: "screen_id is required", severity: "error" });
    }

    if (!screen.layout) {
      errors.push({ path: "layout", message: "layout is required", severity: "error" });
    } else if (!screen.layout.type) {
      errors.push({ path: "layout.type", message: "layout.type is required", severity: "error" });
    } else if (!["grid", "form", "modal", "list", "dashboard", "stack"].includes(screen.layout.type)) {
      errors.push({
        path: "layout.type",
        message: `layout.type must be one of: grid, form, modal, list, dashboard, stack`,
        severity: "error",
      });
    }

    if (!Array.isArray(screen.components)) {
      errors.push({ path: "components", message: "components must be an array", severity: "error" });
    }

    if (!screen.state) {
      errors.push({ path: "state", message: "state is required", severity: "error" });
    }

    return errors;
  }
}

let currentAssetId = "";

export const useEditorState = create<EditorState>((set, get) => ({
  // State
  screen: null,
  draft: null,
  published: null,
  selectedComponentId: null,
  draftModified: false,
  status: "draft",
  validationErrors: [],
  isSaving: false,
  isPublishing: false,
  isRollbacking: false,

  // Computed
  get selectedComponent() {
    const state = get();
    if (!state.screen || !state.selectedComponentId) return null;
    return state.screen.components.find(c => c.id === state.selectedComponentId) || null;
  },

  get isDirty() {
    return get().draftModified;
  },

  get canPublish() {
    const state = get();
    return state.status === "draft" && state.validationErrors.filter(e => e.severity === "error").length === 0;
  },

  get canRollback() {
    return get().status === "published";
  },

  // Actions
  setAssetId: (assetId: string) => {
    currentAssetId = assetId;
  },

  loadScreen: async (assetId: string) => {
    try {
      currentAssetId = assetId;

      // Try to load from /ui-defs first (new system)
      try {
        console.log("[EDITOR] Attempting to load screen from /ui-defs:", assetId);
        const response = await fetchApi(`/ui-defs/${assetId}`);
        console.log("[EDITOR] Loaded UI definition:", response);
        const uiDef = response.data?.ui || response.ui || response;
        console.log("[EDITOR] Extracted uiDef:", uiDef);

        // Convert UI definition schema to screen schema format
        let schema: ScreenSchemaV1;

        if (uiDef.schema) {
          console.log("[EDITOR] Has schema, converting...");
          // Determine layout type from ui_type or schema structure
          let layoutType = uiDef.ui_type || "dashboard";
          if (layoutType === "grid") layoutType = "grid";
          else if (layoutType === "chart") layoutType = "dashboard";
          else if (layoutType === "dashboard") layoutType = "dashboard";

          // If schema already has screen_id, components, state - use it as-is
          if (uiDef.schema.screen_id && uiDef.schema.components) {
            schema = uiDef.schema;
            console.log("[EDITOR] Using schema as-is");
          } else {
            // Otherwise convert grid/chart schema to screen schema
            schema = {
              screen_id: uiDef.ui_id,
              id: uiDef.ui_id,
              name: uiDef.ui_name,
              version: "1.0",
              layout: {
                type: layoutType as any,
                ...uiDef.schema,
              },
              components: [],
              state: { initial: {} },
            };
            console.log("[EDITOR] Converted to ScreenSchemaV1:", schema);
          }
        } else {
          // Fallback: create minimal screen schema
          console.log("[EDITOR] No schema in uiDef, creating minimal");
          schema = {
            screen_id: uiDef.ui_id,
            id: uiDef.ui_id,
            name: uiDef.ui_name,
            version: "1.0",
            layout: { type: "dashboard" },
            components: [],
            state: { initial: {} },
          };
        }

        const status = uiDef.is_active ? "published" : "draft";

        set({
          screen: schema,
          draft: schema,
          published: status === "published" ? schema : null,
          status,
          draftModified: false,
          validationErrors: validateScreen(schema),
        });
        console.log("[EDITOR] Screen loaded successfully from /ui-defs");
        return;
      } catch (uiDefsError) {
        console.warn("[EDITOR] Failed to load from /ui-defs:", uiDefsError);
      }

      // Fallback to asset-registry endpoint
      console.log("[EDITOR] Attempting to load screen from /asset-registry:", assetId);
      const response = await fetchApi(`/asset-registry/assets/${assetId}`);
      const data = response.data || response;
      const asset = data.asset || data;
      const schema = asset.schema_json || asset.screen_schema;
      const status = asset.status || "draft";

      // IMPORTANT: Update currentAssetId to the canonical UUID from the backend
      // This ensures subsequent PUT requests use the UUID, not a slug/screen_id
      if (asset.asset_id) {
        console.log("[EDITOR] Updating currentAssetId to canonical UUID:", asset.asset_id);
        currentAssetId = asset.asset_id;
      }

      set({
        screen: schema,
        draft: schema,
        published: status === "published" ? schema : null,
        status,
        draftModified: false,
        validationErrors: validateScreen(schema),
      });
      console.log("[EDITOR] Screen loaded successfully from /asset-registry");
    } catch (error) {
      console.error("Failed to load screen:", error);
      throw error;
    }
  },

  initializeScreen: (screen: ScreenSchemaV1, status: "draft" | "published") => {
    set({
      screen,
      draft: screen,
      published: status === "published" ? screen : null,
      status,
      draftModified: false,
      validationErrors: validateScreen(screen),
    });
  },

  addComponent: (type: string, index?: number) => {
    console.log("[EDITOR] Adding component:", type);
    set((state) => {
      if (!state.screen) {
        console.log("[EDITOR] No screen loaded");
        return state;
      }

      const newId = generateComponentId(type, state.screen.components);
      const newComponent = createDefaultComponent(type, newId);
      console.log("[EDITOR] Created component:", newId, newComponent);

      const newComponents = [...state.screen.components];
      if (index !== undefined) {
        newComponents.splice(index, 0, newComponent);
      } else {
        newComponents.push(newComponent);
      }

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      console.log("[EDITOR] Updated screen with", newComponents.length, "components");
      console.log("[EDITOR] Setting selectedComponentId to:", newId);

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: newId,
      };
    });
  },

  deleteComponent: (id: string) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.filter(c => c.id !== id);
      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: state.selectedComponentId === id ? null : state.selectedComponentId,
      };
    });
  },

  selectComponent: (id: string | null) => {
    console.log("[EDITOR] selectComponent called with:", id);
    set((state) => {
      console.log("[EDITOR] Current selectedComponentId:", state.selectedComponentId);
      console.log("[EDITOR] Screen components:", state.screen?.components.map(c => c.id));
      return { selectedComponentId: id };
    });
  },

  updateComponentProps: (id: string, props: Record<string, any>) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.map(c =>
        c.id === id
          ? { ...c, props: { ...c.props, ...props } }
          : c
      );

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  updateComponentLabel: (id: string, label: string) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.map(c =>
        c.id === id
          ? { ...c, label }
          : c
      );

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  moveComponent: (id: string, direction: "up" | "down") => {
    set((state) => {
      if (!state.screen) return state;

      const idx = state.screen.components.findIndex(c => c.id === id);
      if (idx === -1) return state;

      const newIndex = direction === "up" ? idx - 1 : idx + 1;
      if (newIndex < 0 || newIndex >= state.screen.components.length) return state;

      const newComponents = [...state.screen.components];
      [newComponents[idx], newComponents[newIndex]] = [newComponents[newIndex], newComponents[idx]];

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  updateLayout: (layout: any) => {
    set((state) => {
      if (!state.screen) return state;

      const newScreen = {
        ...state.screen,
        layout: { ...state.screen.layout, ...layout },
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  updateScreenFromJson: (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString);
      set((state) => {
        return {
          screen: parsed,
          draftModified: true,
          validationErrors: validateScreen(parsed),
          selectedComponentId: null,
        };
      });
    } catch (error) {
      console.error("Invalid JSON:", error);
      set((state) => ({
        validationErrors: [
          { path: "json", message: `Invalid JSON: ${error instanceof Error ? error.message : "Unknown error"}`, severity: "error" },
        ],
      }));
    }
  },

  // Screen-level action CRUD
  addAction: (action: ScreenAction) => {
    set((state) => {
      if (!state.screen) return state;

      const newActions = [...(state.screen.actions || []), action];
      const newScreen = {
        ...state.screen,
        actions: newActions,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  updateAction: (actionId: string, updates: Partial<ScreenAction>) => {
    set((state) => {
      if (!state.screen || !state.screen.actions) return state;

      const newActions = state.screen.actions.map(a =>
        a.id === actionId ? { ...a, ...updates } : a
      );

      const newScreen = {
        ...state.screen,
        actions: newActions,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  deleteAction: (actionId: string) => {
    set((state) => {
      if (!state.screen || !state.screen.actions) return state;

      const newActions = state.screen.actions.filter(a => a.id !== actionId);
      const newScreen = {
        ...state.screen,
        actions: newActions.length > 0 ? newActions : null,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  getAction: (actionId: string) => {
    const state = get();
    if (!state.screen || !state.screen.actions) return null;
    return state.screen.actions.find(a => a.id === actionId) || null;
  },

  // Component-level action CRUD
  addComponentAction: (componentId: string, action: ComponentActionRef) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.map(c => {
        if (c.id === componentId) {
          return {
            ...c,
            actions: [...(c.actions || []), action],
          };
        }
        return c;
      });

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  updateComponentAction: (componentId: string, actionId: string, updates: Partial<ComponentActionRef>) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.map(c => {
        if (c.id === componentId && c.actions) {
          return {
            ...c,
            actions: c.actions.map(a =>
              a.id === actionId ? { ...a, ...updates } : a
            ),
          };
        }
        return c;
      });

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  deleteComponentAction: (componentId: string, actionId: string) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.map(c => {
        if (c.id === componentId && c.actions) {
          const newActions = c.actions.filter(a => a.id !== actionId);
          return {
            ...c,
            actions: newActions.length > 0 ? newActions : null,
          };
        }
        return c;
      });

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  getComponentActions: (componentId: string) => {
    const state = get();
    if (!state.screen) return [];
    const component = state.screen.components.find(c => c.id === componentId);
    return component?.actions || [];
  },

  // Binding management
  updateBinding: (targetPath: string, sourcePath: string) => {
    set((state) => {
      if (!state.screen) return state;

      const newBindings = {
        ...(state.screen.bindings || {}),
        [targetPath]: sourcePath,
      };

      const newScreen = {
        ...state.screen,
        bindings: newBindings,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  deleteBinding: (targetPath: string) => {
    set((state) => {
      if (!state.screen || !state.screen.bindings) return state;

      const newBindings = { ...state.screen.bindings };
      delete newBindings[targetPath];

      const newScreen = {
        ...state.screen,
        bindings: Object.keys(newBindings).length > 0 ? newBindings : null,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  getAllBindings: () => {
    const state = get();
    if (!state.screen) return {};
    return state.screen.bindings || {};
  },

  // Component visibility
  updateComponentVisibility: (componentId: string, visibleIf: string | null) => {
    set((state) => {
      if (!state.screen) return state;

      const newComponents = state.screen.components.map(c => {
        if (c.id === componentId) {
          return {
            ...c,
            visibility: visibleIf ? { rule: visibleIf } : null,
          };
        }
        return c;
      });

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  // Test action by calling /ops/ui-actions endpoint
  testAction: async (actionId: string, payload?: Record<string, any>) => {
    try {
      const state = get();
      if (!state.screen) throw new Error("No screen loaded");

      // Find the action
      const action = state.screen.actions?.find(a => a.id === actionId);
      if (!action) throw new Error(`Action ${actionId} not found`);

      // Prepare request body
      const requestBody = {
        handler: action.handler,
        payload: payload || action.payload_template || {},
        context: {},
        trace_id: `test-${Date.now()}`,
      };

      // Call /ops/ui-actions endpoint
      const response = await fetch("/ops/ui-actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Action execution failed: ${response.statusText}`);
      }

      const result = await response.json();

      // Apply state patch if provided
      if (result.state_patch) {
        get().applyStatePatch(result.state_patch);
      }

      return result;
    } catch (error) {
      console.error("testAction error:", error);
      throw error;
    }
  },

  // Apply state patch to current screen
  applyStatePatch: (patch: Record<string, any>) => {
    set((state) => {
      if (!state.screen?.state) return state;

      const newInitial = {
        ...state.screen.state.initial,
        ...patch,
      };

      const newScreen = {
        ...state.screen,
        state: {
          ...state.screen.state,
          initial: newInitial,
        },
      };

      return {
        screen: newScreen,
        draftModified: true,
      };
    });
  },

  saveDraft: async () => {
    try {
      console.log("[EDITOR] saveDraft called");
      const state = get();
      console.log("[EDITOR] Current state:", { isDirty: state.draftModified, isSaving: state.isSaving });

      if (!state.screen) throw new Error("No screen loaded");

      const errors = state.validationErrors.filter(e => e.severity === "error");
      if (errors.length > 0) {
        throw new Error("Cannot save: Schema validation errors exist");
      }

      set({ isSaving: true });

      console.log("[EDITOR] Attempting to save screen:", currentAssetId);

      // Save to asset-registry using fetchApi (with correct base URL)
      try {
        // Try PUT (update existing)
        const putPayload = {
          schema_json: state.screen,
        };
        console.log("[EDITOR] Attempting PUT to /asset-registry/assets");
        console.log("[EDITOR] PUT payload:", putPayload);
        console.log("[EDITOR] Screen data:", state.screen);
        const putResponse = await fetchApi(`/asset-registry/assets/${currentAssetId}`, {
          method: "PUT",
          body: JSON.stringify(putPayload),
        });
        console.log("[EDITOR] PUT response:", putResponse);
        console.log("[EDITOR] Saved to asset-registry successfully");
      } catch (putError: any) {
        // If asset doesn't exist (404), create it with POST
        // Check for 404 status code or "not found" in error message
        const errStr = String(putError).toLowerCase();
        const errMsg = (putError?.message || "").toLowerCase();
        const statusCode = (putError as any)?.statusCode;

        console.log("[EDITOR] PUT failed:", putError);
        console.log("[EDITOR] Status code:", statusCode);
        console.log("[EDITOR] Checking error for 404/not found matches...");

        if (
          statusCode === 404 ||
          errStr.includes("404") ||
          errStr.includes("not found") ||
          errMsg.includes("404") ||
          errMsg.includes("not found")
        ) {
          console.log("[EDITOR] Asset not found, creating new asset with POST");
          try {
            const postBody = {
              asset_type: "screen",
              screen_id: currentAssetId,
              name: state.screen.name || `Screen ${currentAssetId}`,
              description: "Visual Editor Screen",
              schema_json: state.screen,
            };
            console.log("[EDITOR] POST body:", postBody);

            const postResponse = await fetchApi(`/asset-registry/assets`, {
              method: "POST",
              body: JSON.stringify(postBody),
            });
            console.log("[EDITOR] Created new asset successfully");
          } catch (postError) {
            console.error("[EDITOR] POST error:", postError);
            throw new Error(`Failed to create screen: ${postError}`);
          }
        } else {
          console.error("[EDITOR] PUT error:", putError);
          console.error("[EDITOR] Could not determine if error was 404 or other error");
          console.error("[EDITOR] Error string:", String(putError));
          throw new Error(`Failed to save draft: ${putError}`);
        }
      }


      set({
        draft: state.screen,
        draftModified: false,
        isSaving: false,
      });
      console.log("[EDITOR] saveDraft completed successfully");
    } catch (error) {
      console.error("[EDITOR] saveDraft error:", error);
      set({ isSaving: false });
      throw error;
    }
  },

  publish: async () => {
    try {
      const state = get();
      if (!state.screen) throw new Error("No screen loaded");

      const errors = state.validationErrors.filter(e => e.severity === "error");
      if (errors.length > 0) {
        throw new Error("Cannot publish: Schema validation errors exist");
      }

      set({ isPublishing: true });

      // First save draft
      await get().saveDraft();

      // Then publish via asset-registry using fetchApi with token
      await fetchApi(`/asset-registry/assets/${currentAssetId}/publish`, {
        method: "POST",
        body: JSON.stringify({}),
      });

      set({
        published: state.screen,
        status: "published",
        isPublishing: false,
      });
    } catch (error) {
      set({ isPublishing: false });
      throw error;
    }
  },

  rollback: async () => {
    try {
      set({ isRollbacking: true });

      // Rollback via asset-registry using fetchApi with token
      await fetchApi(`/asset-registry/assets/${currentAssetId}/unpublish`, {
        method: "POST",
        body: JSON.stringify({}),
      });

      set((state) => ({
        status: "draft",
        isRollbacking: false,
      }));

      // Reload screen to sync state
      await get().loadScreen(currentAssetId);
    } catch (error) {
      set({ isRollbacking: false });
      throw error;
    }
  },

  validateScreen: () => {
    const state = get();
    if (!state.screen) return [];
    return validateScreen(state.screen);
  },

  reset: () => {
    set({
      screen: null,
      draft: null,
      published: null,
      selectedComponentId: null,
      draftModified: false,
      status: "draft",
      validationErrors: [],
      isSaving: false,
      isPublishing: false,
      isRollbacking: false,
    });
  },
}));
