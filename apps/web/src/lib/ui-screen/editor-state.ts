import { create } from "zustand";
import { ScreenSchemaV1, Component, ComponentType, ScreenAction, ComponentActionRef } from "./screen.schema";
import { getComponentDescriptor } from "./component-registry";
import { validateScreenSchema } from "./validation-utils";
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
  previewEnabled: boolean;
  previewError: string | null;
  proposedPatch: string | null;

  // Computed
  selectedComponent: Component | null;
  isDirty: boolean;
  canPublish: boolean;
  canRollback: boolean;

  // Actions
  setAssetId: (assetId: string) => void;
  loadScreen: (assetId: string) => Promise<void>;
  initializeScreen: (screen: ScreenSchemaV1, status: "draft" | "published") => void;
  addComponent: (type: ComponentType, index?: number) => void;
  addComponentToParent: (type: ComponentType, parentId: string) => void;
  deleteComponent: (id: string) => void;
  selectComponent: (id: string | null) => void;
  updateComponentProps: (id: string, props: Record<string, unknown>) => void;
  updateComponentLabel: (id: string, label: string) => void;
  moveComponent: (id: string, direction: "up" | "down") => void;
  moveComponentToParent: (componentId: string, targetParentId: string) => void;
  reorderComponentAtIndex: (componentId: string, targetIndex: number, targetParentId?: string | null) => void;
  updateLayout: (layout: unknown) => void;
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
  testAction: (actionId: string, payload?: Record<string, unknown>) => Promise<unknown>;
  applyStatePatch: (patch: Record<string, unknown>) => void;

  // Preview/Patch management (Phase 4 - Copilot)
  setProposedPatch: (patch: string | null) => void;
  disablePreview: () => void;
  previewPatch: () => void;
  applyProposedPatch: () => void;
  discardProposal: () => void;

  // Draft/Publish/Rollback
  saveDraft: () => Promise<void>;
  publish: () => Promise<void>;
  rollback: () => Promise<void>;

  // Validation
  validateScreen: () => ValidationError[];

  // Reset
  reset: () => void;
}


// Helper to create default component
function createDefaultComponent(type: ComponentType, id: string): Component {
  const descriptor = getComponentDescriptor(type);
  const component: Component = {
    id,
    type,
    label: descriptor?.label || type,
    props: {},
  };
  // Initialize empty components array for container types
  if (type === "row" || type === "column") {
    component.props = { components: [] };
  }
  return component;
}

// Helper to collect all component IDs (including nested)
function collectAllComponentIds(components: Component[]): string[] {
  const ids: string[] = [];
  for (const c of components) {
    ids.push(c.id);
    const nested = c.props?.components as Component[] | undefined;
    if (nested && Array.isArray(nested)) {
      ids.push(...collectAllComponentIds(nested));
    }
  }
  return ids;
}

// Helper to generate unique ID across all components (including nested)
function generateUniqueComponentId(type: string, allComponents: Component[]): string {
  const allIds = new Set(collectAllComponentIds(allComponents));
  let counter = 1;
  let id = `${type}_${counter}`;
  while (allIds.has(id)) {
    counter++;
    id = `${type}_${counter}`;
  }
  return id;
}

// Helper to check if component is a container type
function isContainerComponent(type: string): boolean {
  return type === "row" || type === "column" || type === "modal";
}

// Helper to add component to a parent container (returns new components array)
function addToParent(
  components: Component[],
  parentId: string,
  newComponent: Component
): Component[] {
  return components.map(c => {
    if (c.id === parentId && isContainerComponent(c.type)) {
      const children = (c.props?.components as Component[]) || [];
      return {
        ...c,
        props: {
          ...c.props,
          components: [...children, newComponent],
        },
      };
    }
    // Recurse into nested components
    const nested = c.props?.components as Component[] | undefined;
    if (nested && Array.isArray(nested)) {
      return {
        ...c,
        props: {
          ...c.props,
          components: addToParent(nested, parentId, newComponent),
        },
      };
    }
    return c;
  });
}

// Helper to delete component by ID (including from nested)
function deleteComponentById(components: Component[], id: string): Component[] {
  return components
    .filter(c => c.id !== id)
    .map(c => {
      const nested = c.props?.components as Component[] | undefined;
      if (nested && Array.isArray(nested)) {
        return {
          ...c,
          props: {
            ...c.props,
            components: deleteComponentById(nested, id),
          },
        };
      }
      return c;
    });
}

// Helper to find a component by ID (including nested)
function findComponentById(components: Component[], id: string): Component | null {
  for (const c of components) {
    if (c.id === id) return c;
    const nested = c.props?.components as Component[] | undefined;
    if (nested && Array.isArray(nested)) {
      const found = findComponentById(nested, id);
      if (found) return found;
    }
  }
  return null;
}

// Helper to update a component by ID (including nested) with a transformer function
function updateComponentById(
  components: Component[],
  id: string,
  updater: (c: Component) => Component
): Component[] {
  return components.map(c => {
    if (c.id === id) {
      return updater(c);
    }
    // Recurse into nested components
    const nested = c.props?.components as Component[] | undefined;
    if (nested && Array.isArray(nested)) {
      return {
        ...c,
        props: {
          ...c.props,
          components: updateComponentById(nested, id, updater),
        },
      };
    }
    return c;
  });
}

// Helper to insert component at a specific index in a parent (or root)
function insertComponentAtIndex(
  components: Component[],
  component: Component,
  targetIndex: number,
  targetParentId: string | null
): Component[] {
  // If target parent is null, insert at root level
  if (targetParentId === null) {
    const newComponents = [...components];
    const safeIndex = Math.min(Math.max(0, targetIndex), newComponents.length);
    newComponents.splice(safeIndex, 0, component);
    return newComponents;
  }

  // Otherwise, insert into the target parent's children
  return components.map(c => {
    if (c.id === targetParentId && isContainerComponent(c.type)) {
      const children = (c.props?.components as Component[]) || [];
      const newChildren = [...children];
      const safeIndex = Math.min(Math.max(0, targetIndex), newChildren.length);
      newChildren.splice(safeIndex, 0, component);
      return {
        ...c,
        props: {
          ...c.props,
          components: newChildren,
        },
      };
    }
    // Recurse into nested components
    const nested = c.props?.components as Component[] | undefined;
    if (nested && Array.isArray(nested)) {
      return {
        ...c,
        props: {
          ...c.props,
          components: insertComponentAtIndex(nested, component, targetIndex, targetParentId),
        },
      };
    }
    return c;
  });
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
  previewEnabled: false,
  previewError: null,
  proposedPatch: null,

  // Computed
  get selectedComponent() {
    const state = get();
    if (!state.screen || !state.selectedComponentId) return null;
    // Use findComponentById to find nested components too
    return findComponentById(state.screen.components, state.selectedComponentId);
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

      // Load from asset-registry endpoint (source of truth)
      console.log("[EDITOR] Attempting to load screen from /asset-registry:", assetId);
      const response = await fetchApi(`/asset-registry/assets/${assetId}`);
      const responseData = response.data as unknown;
      const asset = (responseData as { asset?: { asset_id?: string; schema_json?: Record<string, unknown>; screen_schema?: Record<string, unknown>; status?: string } } | null)?.asset as { asset_id?: string; schema_json?: Record<string, unknown>; screen_schema?: Record<string, unknown>; status?: string } | null;
      const rawSchema = (asset?.schema_json || asset?.screen_schema) as Record<string, unknown>;
      const status = (asset?.status || "draft") as "draft" | "published";

      const baseSchema: ScreenSchemaV1 = {
        screen_id: rawSchema?.screen_id || asset?.screen_id || asset?.asset_id || assetId,
        name: rawSchema?.name,
        description: rawSchema?.description,
        version: rawSchema?.version,
        layout: rawSchema?.layout || { type: "form", direction: "vertical" },
        components: (rawSchema?.components as any) || [],
        actions: (rawSchema?.actions as any) || null,
        state: rawSchema?.state || null,
        bindings: rawSchema?.bindings || null,
        metadata: rawSchema?.metadata,
        ...rawSchema,
      };

      const schema: ScreenSchemaV1 = {
        ...baseSchema,
        screen_id: baseSchema.screen_id || rawSchema?.screen_id || asset?.screen_id || asset?.asset_id || assetId,
      };

      // IMPORTANT: Update currentAssetId to be canonical UUID from backend
      // This ensures subsequent PUT requests use UUID, not a slug/screen_id
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

  addComponent: (type: ComponentType, index?: number) => {
    console.log("[EDITOR] Adding component:", type);
    set((state) => {
      if (!state.screen) {
        console.log("[EDITOR] No screen loaded");
        return state;
      }

      const newId = generateUniqueComponentId(type, state.screen.components);
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

  addComponentToParent: (type: ComponentType, parentId: string) => {
    console.log("[EDITOR] Adding component to parent:", type, parentId);
    set((state) => {
      if (!state.screen) {
        console.log("[EDITOR] No screen loaded");
        return state;
      }

      const newId = generateUniqueComponentId(type, state.screen.components);
      const newComponent = createDefaultComponent(type, newId);
      console.log("[EDITOR] Created component:", newId, newComponent);

      const newComponents = addToParent(state.screen.components, parentId, newComponent);

      const newScreen = {
        ...state.screen,
        components: newComponents,
      };

      console.log("[EDITOR] Added component to parent:", parentId);

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

      // Use recursive delete to handle nested components
      const newComponents = deleteComponentById(state.screen.components, id);
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

  updateComponentProps: (id: string, props: Record<string, unknown>) => {
    set((state) => {
      if (!state.screen) return state;

      // Use updateComponentById to handle nested components
      const newComponents = updateComponentById(
        state.screen.components,
        id,
        (c) => ({ ...c, props: { ...c.props, ...props } })
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

      // Use updateComponentById to handle nested components
      const newComponents = updateComponentById(
        state.screen.components,
        id,
        (c) => ({ ...c, label })
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

  moveComponentToParent: (componentId: string, targetParentId: string) => {
    console.log("[EDITOR] moveComponentToParent:", componentId, "->", targetParentId);
    set((state) => {
      if (!state.screen) return state;

      // Find the component to move
      const componentToMove = findComponentById(state.screen.components, componentId);
      if (!componentToMove) {
        console.log("[EDITOR] Component not found:", componentId);
        return state;
      }

      // Can't move into itself or its children
      if (componentId === targetParentId) {
        console.log("[EDITOR] Cannot move component into itself");
        return state;
      }

      // Remove from current location
      let newComponents = deleteComponentById(state.screen.components, componentId);

      // Add to new parent
      newComponents = addToParent(newComponents, targetParentId, componentToMove);

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

  reorderComponentAtIndex: (componentId: string, targetIndex: number, targetParentId?: string | null) => {
    console.log("[EDITOR] reorderComponentAtIndex:", componentId, "-> index", targetIndex, "parent:", targetParentId);
    set((state) => {
      if (!state.screen) return state;

      // Find the component to move
      const componentToMove = findComponentById(state.screen.components, componentId);
      if (!componentToMove) {
        console.log("[EDITOR] Component not found:", componentId);
        return state;
      }

      // Remove from current location
      let newComponents = deleteComponentById(state.screen.components, componentId);

      // Insert at new position
      newComponents = insertComponentAtIndex(
        newComponents,
        componentToMove,
        targetIndex,
        targetParentId ?? null
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

  updateLayout: (layout: unknown) => {
    set((state) => {
      if (!state.screen) return state;

      const newScreen = {
        ...state.screen,
        layout: { ...state.screen.layout, ...(layout as Record<string, unknown>) },
      } as ScreenSchemaV1;

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
      };
    });
  },

  updateScreenFromJson: (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString) as ScreenSchemaV1;
      set(() => {
        return {
          screen: parsed,
          draftModified: true,
          validationErrors: validateScreen(parsed),
          selectedComponentId: null,
        };
      });
    } catch (error) {
      console.error("Invalid JSON:", error);
      set(() => ({
        validationErrors: [
          { path: "json", message: `Invalid JSON: ${error instanceof Error ? error.message : "Unknown error"}`, severity: "error" },
        ],
      }));
    }
  },

  // Screen-level action CRUD
  addAction: (action: ScreenAction) => {
    set(() => {
      const currentScreen = get().screen;
      if (!currentScreen) return {};

      const newActions = [...(currentScreen.actions || []), action];
      const newScreen: ScreenSchemaV1 = {
        ...currentScreen,
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
    set(() => {
      const currentScreen = get().screen;
      if (!currentScreen || !currentScreen.actions) return {};

      const newActions = currentScreen.actions.map(a =>
        a.id === actionId ? { ...a, ...updates } : a
      );

      const newScreen: ScreenSchemaV1 = {
        ...currentScreen,
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
    set(() => {
      const currentScreen = get().screen;
      if (!currentScreen || !currentScreen.actions) return {};

      const newActions = currentScreen.actions.filter(a => a.id !== actionId);
      const newScreen: ScreenSchemaV1 = {
        ...currentScreen,
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

      // Use updateComponentById to handle nested components
      const newComponents = updateComponentById(
        state.screen.components,
        componentId,
        (c) => ({
          ...c,
          actions: [...(c.actions || []), action],
        })
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

  updateComponentAction: (componentId: string, actionId: string, updates: Partial<ComponentActionRef>) => {
    set((state) => {
      if (!state.screen) return state;

      // Use updateComponentById to handle nested components
      const newComponents = updateComponentById(
        state.screen.components,
        componentId,
        (c) => ({
          ...c,
          actions: c.actions
            ? c.actions.map(a => a.id === actionId ? { ...a, ...updates } : a)
            : [],
        })
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

  deleteComponentAction: (componentId: string, actionId: string) => {
    set((state) => {
      if (!state.screen) return state;

      // Use updateComponentById to handle nested components
      const newComponents = updateComponentById(
        state.screen.components,
        componentId,
        (c) => {
          const newActions = c.actions?.filter(a => a.id !== actionId) || [];
          return {
            ...c,
            actions: newActions.length > 0 ? newActions : undefined,
          };
        }
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

  getComponentActions: (componentId: string) => {
    const state = get();
    if (!state.screen) return [];
    // Use findComponentById to handle nested components
    const component = findComponentById(state.screen.components, componentId);
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

      // Use updateComponentById to handle nested components
      const newComponents = updateComponentById(
        state.screen.components,
        componentId,
        (c) => ({
          ...c,
          visibility: visibleIf ? { rule: visibleIf } : undefined,
        })
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

  // Test action by calling /ops/ui-actions endpoint
  testAction: async (actionId: string, payload?: Record<string, unknown>) => {
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
  applyStatePatch: (patch: Record<string, unknown>) => {
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
          schema_json: state.screen as unknown as Record<string, unknown>,
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
      } catch (putError: unknown) {
        // If asset doesn't exist (404), create it with POST
        // Check for 404 status code or "not found" in error message
        const errStr = String(putError).toLowerCase();
        const errMsg = ((putError as Error)?.message || "").toLowerCase();
        const statusCode = (putError as { statusCode?: number })?.statusCode;

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
            console.log("[EDITOR] POST body size:", JSON.stringify(postBody).length);

            const postResponse = await fetchApi(`/asset-registry/assets`, {
              method: "POST",
              body: JSON.stringify(postBody),
            });
            console.log("[EDITOR] POST response received");
            console.log("[EDITOR] POST response data:", postResponse);
            console.log("[EDITOR] Created new asset successfully");
          } catch (postError: unknown) {
            console.error("[EDITOR] POST error:", postError);
            console.error("[EDITOR] POST error details:", {
              message: (postError as Error)?.message,
              statusCode: (postError as { statusCode?: number })?.statusCode,
              errorType: typeof postError,
            });
            throw new Error(`Failed to create screen: ${postError}`);
          }
        } else {
          console.error("[EDITOR] PUT error:", putError);
          console.error("[EDITOR] Could not determine if error was 404 or other error");
          console.error("[EDITOR] Error string:", String(putError));
          console.error("[EDITOR] Error details:", {
            statusCode,
            errorStr: errStr,
            errorMsg: errMsg,
            errorType: typeof putError,
            errorKeys: Object.keys(putError || {}),
          });
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

      set({
        status: "draft",
        isRollbacking: false,
      });

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

  // Preview/Patch management (Phase 4 - Copilot)
  setProposedPatch: (patch: string | null) => {
    set({ proposedPatch: patch as string | null });
  },

  disablePreview: () => {
    set({ previewEnabled: false, previewError: null });
  },

  previewPatch: () => {
    set({ previewEnabled: true, previewError: null });
  },

  applyProposedPatch: () => {
    set((state) => ({
      previewEnabled: false,
      previewError: null,
      // Apply patch to screen (implementation would go here)
    }));
  },

  discardProposal: () => {
    set({ previewEnabled: false, previewError: null });
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
      previewEnabled: false,
      previewError: null,
    });
  },
}));
