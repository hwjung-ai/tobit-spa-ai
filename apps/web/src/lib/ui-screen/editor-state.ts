import { create } from "zustand";
import { ScreenSchemaV1, Component, ScreenAction, ComponentActionRef } from "./screen.schema";
import { getComponentDescriptor } from "./component-registry";
import { validateBindingPath, validateActionHandler, validateScreenSchema } from "./validation-utils";
import { parseBindingExpression, formatBindingExpression } from "./binding-path-utils";

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
      const response = await fetch(`/asset-registry/assets/${assetId}`);
      if (!response.ok) throw new Error("Failed to load screen");

      const data = await response.json();
      const asset = data.asset || data;
      const schema = asset.schema_json || asset.screen_schema;
      const status = asset.status || "draft";

      set({
        screen: schema,
        draft: schema,
        published: status === "published" ? schema : null,
        status,
        draftModified: false,
        validationErrors: validateScreen(schema),
      });
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
    set((state) => {
      if (!state.screen) return state;

      const newId = generateComponentId(type, state.screen.components);
      const newComponent = createDefaultComponent(type, newId);

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
    set({ selectedComponentId: id });
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
      const state = get();
      if (!state.screen) throw new Error("No screen loaded");

      const errors = state.validationErrors.filter(e => e.severity === "error");
      if (errors.length > 0) {
        throw new Error("Cannot save: Schema validation errors exist");
      }

      set({ isSaving: true });

      const response = await fetch(`/asset-registry/assets/${currentAssetId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema_json: state.screen,
        }),
      });

      if (!response.ok) throw new Error("Failed to save draft");

      set({
        draft: state.screen,
        draftModified: false,
        isSaving: false,
      });
    } catch (error) {
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

      // Then publish
      const response = await fetch(`/asset-registry/assets/${currentAssetId}/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!response.ok) throw new Error("Failed to publish");

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

      const response = await fetch(`/asset-registry/assets/${currentAssetId}/unpublish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!response.ok) throw new Error("Failed to rollback");

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
