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

export interface DraftConflictInfo {
  hasConflict: boolean;
  message: string | null;
  expectedUpdatedAt: string | null;
  serverUpdatedAt: string | null;
  serverScreen: ScreenSchemaV1 | null;
  autoMergedScreen: ScreenSchemaV1 | null;
}

export interface EditorState {
  // State
  screen: ScreenSchemaV1 | null;
  draft: ScreenSchemaV1 | null;
  published: ScreenSchemaV1 | null;
  selectedComponentId: string | null;
  selectedComponentIds: string[];
  draftModified: boolean;
  status: "draft" | "published";
  validationErrors: ValidationError[];
  isSaving: boolean;
  isPublishing: boolean;
  isRollbacking: boolean;
  previewEnabled: boolean;
  previewError: string | null;
  proposedPatch: string | null;
  serverUpdatedAt: string | null;
  lastSyncedScreen: ScreenSchemaV1 | null;
  draftConflict: DraftConflictInfo;

  // History (Undo/Redo)
  historyStack: ScreenSchemaV1[];
  historyIndex: number;
  canUndo: boolean;
  canRedo: boolean;

  // Clipboard
  clipboard: Component[] | null;
  clipboardOperation: "copy" | "cut" | null;

  // Computed
  selectedComponent: Component | null;
  isDirty: boolean;
  canPublish: boolean;
  canRollback: boolean;

  // Actions
  setAssetId: (assetId: string) => void;
  loadScreen: (assetId: string) => Promise<void>;
  initializeScreen: (screen: ScreenSchemaV1, status: "draft" | "published") => void;
  applyRemoteScreen: (screen: ScreenSchemaV1, updatedAt?: string | null) => void;
  addComponent: (type: ComponentType, index?: number) => void;
  addComponentToParent: (type: ComponentType, parentId: string) => void;
  deleteComponent: (id: string) => void;
  selectComponent: (id: string | null) => void;
  selectComponentToggle: (id: string) => void;
  selectComponentRange: (id: string) => void;
  selectAll: () => void;
  deselectAll: () => void;
  deleteSelectedComponents: () => void;
  updateComponentProps: (id: string, props: Record<string, unknown>) => void;
  updateComponentLabel: (id: string, label: string) => void;
  moveComponent: (id: string, direction: "up" | "down") => void;
  moveComponentToParent: (componentId: string, targetParentId: string) => void;
  reorderComponentAtIndex: (componentId: string, targetIndex: number, targetParentId?: string | null) => void;
  updateLayout: (layout: unknown) => void;
  updateScreenFromJson: (json: string) => void;

  // Undo/Redo
  undo: () => void;
  redo: () => void;

  // Clipboard
  copySelectedComponents: () => void;
  cutSelectedComponents: () => void;
  pasteComponents: () => void;
  duplicateSelectedComponents: () => void;

  // Action CRUD (screen-level)
  addAction: (action: ScreenAction) => void;
  updateAction: (actionId: string, updates: Partial<ScreenAction>) => void;
  deleteAction: (actionId: string) => void;
  getAction: (actionId: string) => ScreenAction | null;

  // Component Action CRUD
  addComponentAction: (componentId: string, action: ComponentActionRef) => void;
  updateComponentAction: (componentId: string, actionId: string, updates: Partial<ComponentActionRef>) => void;
  deleteComponentAction: (componentId: string, actionId: string) => void;
  moveComponentAction: (componentId: string, actionId: string, direction: "up" | "down") => void;
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
  saveDraft: (opts?: { force?: boolean }) => Promise<void>;
  clearDraftConflict: () => void;
  applyAutoMergedConflict: () => void;
  reloadFromServer: () => Promise<void>;
  forceSaveDraft: () => Promise<void>;
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
  if (type === "row" || type === "column" || type === "form") {
    component.props = { components: [] };
  } else if (type === "accordion") {
    component.props = {
      items: [
        { id: "section_1", title: "Section 1", components: [] },
      ],
      allow_multiple: false,
    };
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
  return type === "row" || type === "column" || type === "modal" || type === "form";
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

const MERGE_KEYS: Array<keyof ScreenSchemaV1> = [
  "name",
  "layout",
  "components",
  "actions",
  "state",
  "bindings",
  "metadata",
];

function changedScreenKeys(
  before: ScreenSchemaV1 | null,
  after: ScreenSchemaV1 | null
): Set<keyof ScreenSchemaV1> {
  const out = new Set<keyof ScreenSchemaV1>();
  if (!before || !after) return out;
  for (const key of MERGE_KEYS) {
    const a = before[key];
    const b = after[key];
    if (JSON.stringify(a) !== JSON.stringify(b)) {
      out.add(key);
    }
  }
  return out;
}

function buildAutoMergedScreen(
  baseRemote: ScreenSchemaV1,
  localScreen: ScreenSchemaV1,
  localChanged: Set<keyof ScreenSchemaV1>
): ScreenSchemaV1 {
  const merged = { ...baseRemote } as ScreenSchemaV1;
  for (const key of localChanged) {
    (merged as unknown as Record<string, unknown>)[key] = (
      localScreen as unknown as Record<string, unknown>
    )[key];
  }
  return merged;
}

const MAX_HISTORY_SIZE = 50;

// Deep clone a component with a new unique ID (including nested children)
function deepCloneComponent(component: Component, existingComponents: Component[]): Component {
  const newId = generateUniqueComponentId(component.type, existingComponents);
  const cloned: Component = {
    ...component,
    id: newId,
    label: component.label ? `${component.label} (copy)` : undefined,
    props: component.props ? { ...component.props } : undefined,
  };
  if (cloned.props?.components && Array.isArray(cloned.props.components)) {
    const clonedChildren = (cloned.props.components as Component[]).map(child =>
      deepCloneComponent(child, [...existingComponents, cloned])
    );
    cloned.props = { ...cloned.props, components: clonedChildren };
  }
  if (cloned.actions) {
    cloned.actions = cloned.actions.map(a => ({
      ...a,
      id: `${a.id}_${Date.now().toString(36).slice(-4)}`,
    }));
  }
  return cloned;
}

let currentAssetId = "";

const EMPTY_DRAFT_CONFLICT: DraftConflictInfo = {
  hasConflict: false,
  message: null,
  expectedUpdatedAt: null,
  serverUpdatedAt: null,
  serverScreen: null,
  autoMergedScreen: null,
};

export const useEditorState = create<EditorState>((set, get) => ({
  // State
  screen: null,
  draft: null,
  published: null,
  selectedComponentId: null,
  selectedComponentIds: [],
  draftModified: false,
  status: "draft",
  validationErrors: [],
  isSaving: false,
  isPublishing: false,
  isRollbacking: false,
  previewEnabled: false,
  previewError: null,
  proposedPatch: null,
  serverUpdatedAt: null,
  lastSyncedScreen: null,
  draftConflict: { ...EMPTY_DRAFT_CONFLICT },

  // History
  historyStack: [],
  historyIndex: -1,
  clipboard: null,
  clipboardOperation: null,

  // Computed
  get canUndo() {
    return get().historyIndex >= 0;
  },
  get canRedo() {
    const state = get();
    return state.historyIndex < state.historyStack.length - 1;
  },
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
      // fetchApi returns ResponseEnvelope, so access response.data.asset
      const asset = (response as {
        data?: {
          asset?: {
            asset_id?: string;
            screen_id?: string;
            schema_json?: Record<string, unknown>;
            screen_schema?: Record<string, unknown>;
            status?: string;
            updated_at?: string;
          };
        };
      } | null)?.data?.asset as {
        asset_id?: string;
        screen_id?: string;
        schema_json?: Record<string, unknown>;
        screen_schema?: Record<string, unknown>;
        status?: string;
        updated_at?: string;
      } | null;
      const rawSchema = ((asset?.schema_json || asset?.screen_schema || {}) as Record<
        string,
        unknown
      >);
      const raw = rawSchema as Record<string, unknown>;
      const status = (asset?.status || "draft") as "draft" | "published";

      const baseSchema: ScreenSchemaV1 = {
        screen_id:
          String(raw.screen_id || asset?.screen_id || asset?.asset_id || assetId),
        name: (raw.name as string | undefined) || undefined,
        version: (raw.version as string | undefined) || undefined,
        layout:
          (raw.layout as ScreenSchemaV1["layout"] | undefined) || {
            type: "form",
            direction: "vertical",
          },
        components: (raw.components as ScreenSchemaV1["components"]) || [],
        actions: (raw.actions as ScreenSchemaV1["actions"]) || null,
        state: (raw.state as ScreenSchemaV1["state"]) || null,
        bindings: (raw.bindings as ScreenSchemaV1["bindings"]) || null,
        metadata: (raw.metadata as ScreenSchemaV1["metadata"]) || undefined,
        ...rawSchema,
      };

      const schema: ScreenSchemaV1 = {
        ...baseSchema,
        screen_id:
          baseSchema.screen_id ||
          String(raw.screen_id || asset?.screen_id || asset?.asset_id || assetId),
      };

      // IMPORTANT: Update currentAssetId to be canonical UUID from backend
      // This ensures subsequent PUT requests use UUID, not a slug/screen_id
      if (asset?.asset_id) {
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
        serverUpdatedAt: asset?.updated_at || null,
        lastSyncedScreen: schema,
        draftConflict: { ...EMPTY_DRAFT_CONFLICT },
        historyStack: [],
        historyIndex: -1,
        selectedComponentId: null,
        selectedComponentIds: [],
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
      serverUpdatedAt: null,
      lastSyncedScreen: screen,
      draftConflict: { ...EMPTY_DRAFT_CONFLICT },
      historyStack: [],
      historyIndex: -1,
      selectedComponentId: null,
      selectedComponentIds: [],
    });
  },

  applyRemoteScreen: (screen: ScreenSchemaV1, updatedAt?: string | null) => {
    set((state) => {
      if (state.draftModified && state.screen) {
        const localJson = JSON.stringify(state.screen);
        const remoteJson = JSON.stringify(screen);
        if (localJson !== remoteJson) {
          const localChanged = changedScreenKeys(
            state.lastSyncedScreen,
            state.screen as ScreenSchemaV1
          );
          const remoteChanged = changedScreenKeys(state.lastSyncedScreen, screen);
          const hasOverlap = [...localChanged].some((key) => remoteChanged.has(key));
          const autoMergedScreen =
            !hasOverlap && localChanged.size > 0
              ? buildAutoMergedScreen(screen, state.screen as ScreenSchemaV1, localChanged)
              : null;
          return {
            draftConflict: {
              hasConflict: true,
              message: autoMergedScreen
                ? "Remote changes merged candidate is ready. Review and apply auto-merge."
                : "Remote editor updated this screen while you have local draft changes.",
              expectedUpdatedAt: state.serverUpdatedAt,
              serverUpdatedAt: updatedAt || state.serverUpdatedAt,
              serverScreen: screen,
              autoMergedScreen,
            },
          };
        }
      }

      return {
        screen,
        draft: screen,
        lastSyncedScreen: screen,
        serverUpdatedAt: updatedAt || state.serverUpdatedAt,
        validationErrors: validateScreen(screen),
        draftModified: false,
        draftConflict: { ...EMPTY_DRAFT_CONFLICT },
      };
    });
  },

  addComponent: (type: ComponentType, index?: number) => {
    set((state) => {
      if (!state.screen) return state;

      // Push history
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);

      const newId = generateUniqueComponentId(type, state.screen.components);
      const newComponent = createDefaultComponent(type, newId);

      const newComponents = [...state.screen.components];
      if (index !== undefined) {
        newComponents.splice(index, 0, newComponent);
      } else {
        newComponents.push(newComponent);
      }

      const newScreen = { ...state.screen, components: newComponents };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: newId,
        selectedComponentIds: [newId],
        historyStack: newStack,
        historyIndex: newStack.length - 1,
      };
    });
  },

  addComponentToParent: (type: ComponentType, parentId: string) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);

      const newId = generateUniqueComponentId(type, state.screen.components);
      const newComponent = createDefaultComponent(type, newId);
      const newComponents = addToParent(state.screen.components, parentId, newComponent);
      const newScreen = { ...state.screen, components: newComponents };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: newId,
        selectedComponentIds: [newId],
        historyStack: newStack,
        historyIndex: newStack.length - 1,
      };
    });
  },

  deleteComponent: (id: string) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);

      const newComponents = deleteComponentById(state.screen.components, id);
      const newScreen = { ...state.screen, components: newComponents };
      const newSelectedIds = state.selectedComponentIds.filter(sid => sid !== id);

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: state.selectedComponentId === id ? (newSelectedIds[newSelectedIds.length - 1] || null) : state.selectedComponentId,
        selectedComponentIds: newSelectedIds,
        historyStack: newStack,
        historyIndex: newStack.length - 1,
      };
    });
  },

  selectComponent: (id: string | null) => {
    set(() => ({
      selectedComponentId: id,
      selectedComponentIds: id ? [id] : [],
    }));
  },

  selectComponentToggle: (id: string) => {
    set((state) => {
      const ids = [...state.selectedComponentIds];
      const idx = ids.indexOf(id);
      if (idx >= 0) {
        ids.splice(idx, 1);
      } else {
        ids.push(id);
      }
      return {
        selectedComponentId: ids[ids.length - 1] || null,
        selectedComponentIds: ids,
      };
    });
  },

  selectComponentRange: (id: string) => {
    set((state) => {
      if (!state.screen) return state;
      const allIds = collectAllComponentIds(state.screen.components);
      const lastSelected = state.selectedComponentId;
      if (!lastSelected) return { selectedComponentId: id, selectedComponentIds: [id] };

      const startIdx = allIds.indexOf(lastSelected);
      const endIdx = allIds.indexOf(id);
      if (startIdx === -1 || endIdx === -1) return { selectedComponentId: id, selectedComponentIds: [id] };

      const min = Math.min(startIdx, endIdx);
      const max = Math.max(startIdx, endIdx);
      const rangeIds = allIds.slice(min, max + 1);

      return {
        selectedComponentId: id,
        selectedComponentIds: rangeIds,
      };
    });
  },

  selectAll: () => {
    set((state) => {
      if (!state.screen) return state;
      const allIds = collectAllComponentIds(state.screen.components);
      return {
        selectedComponentId: allIds[allIds.length - 1] || null,
        selectedComponentIds: allIds,
      };
    });
  },

  deselectAll: () => {
    set(() => ({
      selectedComponentId: null,
      selectedComponentIds: [],
    }));
  },

  deleteSelectedComponents: () => {
    set((state) => {
      if (!state.screen || state.selectedComponentIds.length === 0) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);

      let newComponents = state.screen.components;
      for (const id of state.selectedComponentIds) {
        newComponents = deleteComponentById(newComponents, id);
      }
      const newScreen = { ...state.screen, components: newComponents };

      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: null,
        selectedComponentIds: [],
        historyStack: newStack,
        historyIndex: newStack.length - 1,
      };
    });
  },

  updateComponentProps: (id: string, props: Record<string, unknown>) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, id, (c) => ({ ...c, props: { ...c.props, ...props } }));
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  updateComponentLabel: (id: string, label: string) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, id, (c) => ({ ...c, label }));
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  moveComponent: (id: string, direction: "up" | "down") => {
    set((state) => {
      if (!state.screen) return state;
      const idx = state.screen.components.findIndex(c => c.id === id);
      if (idx === -1) return state;
      const newIndex = direction === "up" ? idx - 1 : idx + 1;
      if (newIndex < 0 || newIndex >= state.screen.components.length) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = [...state.screen.components];
      [newComponents[idx], newComponents[newIndex]] = [newComponents[newIndex], newComponents[idx]];
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  moveComponentToParent: (componentId: string, targetParentId: string) => {
    set((state) => {
      if (!state.screen) return state;
      const componentToMove = findComponentById(state.screen.components, componentId);
      if (!componentToMove || componentId === targetParentId) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      let newComponents = deleteComponentById(state.screen.components, componentId);
      newComponents = addToParent(newComponents, targetParentId, componentToMove);
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  reorderComponentAtIndex: (componentId: string, targetIndex: number, targetParentId?: string | null) => {
    set((state) => {
      if (!state.screen) return state;
      const componentToMove = findComponentById(state.screen.components, componentId);
      if (!componentToMove) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      let newComponents = deleteComponentById(state.screen.components, componentId);
      newComponents = insertComponentAtIndex(newComponents, componentToMove, targetIndex, targetParentId ?? null);
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  updateLayout: (layout: unknown) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newScreen = { ...state.screen, layout: { ...state.screen.layout, ...(layout as Record<string, unknown>) } } as ScreenSchemaV1;
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  updateScreenFromJson: (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString) as ScreenSchemaV1;
      set((state) => {
        const newStack = state.screen
          ? [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE)
          : state.historyStack;
        return {
          screen: parsed,
          draftModified: true,
          validationErrors: validateScreen(parsed),
          selectedComponentId: null,
          selectedComponentIds: [],
          historyStack: newStack,
          historyIndex: newStack.length - 1,
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
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newActions = [...(state.screen.actions || []), action];
      const newScreen: ScreenSchemaV1 = { ...state.screen, actions: newActions };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  updateAction: (actionId: string, updates: Partial<ScreenAction>) => {
    set((state) => {
      if (!state.screen?.actions) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newActions = state.screen.actions.map(a => a.id === actionId ? { ...a, ...updates } : a);
      const newScreen: ScreenSchemaV1 = { ...state.screen, actions: newActions };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  deleteAction: (actionId: string) => {
    set((state) => {
      if (!state.screen?.actions) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newActions = state.screen.actions.filter(a => a.id !== actionId);
      const newScreen: ScreenSchemaV1 = { ...state.screen, actions: newActions.length > 0 ? newActions : null };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
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
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, componentId, (c) => ({ ...c, actions: [...(c.actions || []), action] }));
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  updateComponentAction: (componentId: string, actionId: string, updates: Partial<ComponentActionRef>) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, componentId, (c) => ({
        ...c, actions: c.actions ? c.actions.map(a => a.id === actionId ? { ...a, ...updates } : a) : [],
      }));
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  deleteComponentAction: (componentId: string, actionId: string) => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, componentId, (c) => {
        const newActions = c.actions?.filter(a => a.id !== actionId) || [];
        return { ...c, actions: newActions.length > 0 ? newActions : undefined };
      });
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  moveComponentAction: (componentId: string, actionId: string, direction: "up" | "down") => {
    set((state) => {
      if (!state.screen) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, componentId, (c) => {
        const actions = c.actions || [];
        const index = actions.findIndex((a) => a.id === actionId);
        if (index < 0) return c;
        const targetIndex = direction === "up" ? index - 1 : index + 1;
        if (targetIndex < 0 || targetIndex >= actions.length) return c;
        const reordered = [...actions];
        [reordered[index], reordered[targetIndex]] = [reordered[targetIndex], reordered[index]];
        return { ...c, actions: reordered };
      });
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
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
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newBindings = { ...(state.screen.bindings || {}), [targetPath]: sourcePath };
      const newScreen = { ...state.screen, bindings: newBindings };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  deleteBinding: (targetPath: string) => {
    set((state) => {
      if (!state.screen?.bindings) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newBindings = { ...state.screen.bindings };
      delete newBindings[targetPath];
      const newScreen = { ...state.screen, bindings: Object.keys(newBindings).length > 0 ? newBindings : null };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
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
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);
      const newComponents = updateComponentById(state.screen.components, componentId, (c) => ({
        ...c, visibility: visibleIf ? { rule: visibleIf } : undefined,
      }));
      const newScreen = { ...state.screen, components: newComponents };
      return { screen: newScreen, draftModified: true, validationErrors: validateScreen(newScreen), historyStack: newStack, historyIndex: newStack.length - 1 };
    });
  },

  // Undo/Redo
  undo: () => {
    set((state) => {
      if (state.historyIndex < 0 || !state.screen) return state;
      // Save current screen as redo point if we're at the top
      let stack = state.historyStack;
      if (state.historyIndex === stack.length - 1) {
        stack = [...stack, JSON.parse(JSON.stringify(state.screen))];
      }
      const previousScreen = stack[state.historyIndex] as ScreenSchemaV1;
      return {
        screen: previousScreen,
        historyStack: stack,
        historyIndex: state.historyIndex - 1,
        draftModified: true,
        validationErrors: validateScreen(previousScreen),
        selectedComponentId: null,
        selectedComponentIds: [],
      };
    });
  },

  redo: () => {
    set((state) => {
      if (state.historyIndex >= state.historyStack.length - 1) return state;
      const nextIndex = state.historyIndex + 2;
      if (nextIndex >= state.historyStack.length) return state;
      const nextScreen = state.historyStack[nextIndex] as ScreenSchemaV1;
      return {
        screen: nextScreen,
        historyIndex: state.historyIndex + 1,
        draftModified: true,
        validationErrors: validateScreen(nextScreen),
        selectedComponentId: null,
        selectedComponentIds: [],
      };
    });
  },

  // Clipboard
  copySelectedComponents: () => {
    const state = get();
    if (!state.screen || state.selectedComponentIds.length === 0) return;
    const components = state.selectedComponentIds
      .map(id => findComponentById(state.screen!.components, id))
      .filter(Boolean) as Component[];
    set({ clipboard: JSON.parse(JSON.stringify(components)), clipboardOperation: "copy" });
  },

  cutSelectedComponents: () => {
    const state = get();
    if (!state.screen || state.selectedComponentIds.length === 0) return;
    const components = state.selectedComponentIds
      .map(id => findComponentById(state.screen!.components, id))
      .filter(Boolean) as Component[];
    set({ clipboard: JSON.parse(JSON.stringify(components)), clipboardOperation: "cut" });
    // Delete the originals
    get().deleteSelectedComponents();
  },

  pasteComponents: () => {
    set((state) => {
      if (!state.screen || !state.clipboard || state.clipboard.length === 0) return state;
      const newStack = [...state.historyStack.slice(0, state.historyIndex + 1), JSON.parse(JSON.stringify(state.screen))].slice(-MAX_HISTORY_SIZE);

      const newIds: string[] = [];
      let newComponents = [...state.screen.components];
      for (const original of state.clipboard) {
        const cloned = deepCloneComponent(original, newComponents);
        newIds.push(cloned.id);
        newComponents.push(cloned);
      }

      const newScreen = { ...state.screen, components: newComponents };
      return {
        screen: newScreen,
        draftModified: true,
        validationErrors: validateScreen(newScreen),
        selectedComponentId: newIds[newIds.length - 1] || null,
        selectedComponentIds: newIds,
        historyStack: newStack,
        historyIndex: newStack.length - 1,
        clipboardOperation: state.clipboardOperation === "cut" ? null : state.clipboardOperation,
        clipboard: state.clipboardOperation === "cut" ? null : state.clipboard,
      };
    });
  },

  duplicateSelectedComponents: () => {
    const state = get();
    if (!state.screen || state.selectedComponentIds.length === 0) return;
    // Copy then immediately paste
    get().copySelectedComponents();
    get().pasteComponents();
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
        action_id: action.handler,
        inputs: payload || action.payload_template || {},
        context: { mode: "real", origin: "screen_editor_test" },
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

      const envelope = await response.json();
      const result = envelope?.data ?? envelope;

      // Apply state patch if provided
      if (result?.state_patch) {
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

  saveDraft: async (opts?: { force?: boolean }) => {
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
          expected_updated_at: state.serverUpdatedAt || undefined,
          force: !!opts?.force,
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
        const nextUpdatedAt =
          ((putResponse as { data?: { asset?: { updated_at?: string } } })?.data?.asset
            ?.updated_at as string | undefined) || state.serverUpdatedAt || null;
        set({
          serverUpdatedAt: nextUpdatedAt,
          draftConflict: { ...EMPTY_DRAFT_CONFLICT },
        });
      } catch (putError: unknown) {
        // If asset doesn't exist (404), create it with POST
        // Check for 404 status code or "not found" in error message
        const errStr = String(putError).toLowerCase();
        const errMsg = ((putError as Error)?.message || "").toLowerCase();
        const statusCode = (putError as { statusCode?: number })?.statusCode;

        console.log("[EDITOR] PUT failed:", putError);
        console.log("[EDITOR] Status code:", statusCode);
        console.log("[EDITOR] Checking error for 404/not found matches...");

        if (statusCode === 409) {
          try {
            const latest = await fetchApi(`/asset-registry/assets/${currentAssetId}`);
            const latestAsset = (latest as {
              data?: {
                asset?: {
                  schema_json?: Record<string, unknown>;
                  screen_schema?: Record<string, unknown>;
                  updated_at?: string;
                };
              };
            })?.data?.asset;
            const latestRaw = (latestAsset?.schema_json ||
              latestAsset?.screen_schema ||
              {}) as Record<string, unknown>;
            const latestSchema: ScreenSchemaV1 = {
              ...(state.screen as ScreenSchemaV1),
              ...latestRaw,
            };
            const localChanged = changedScreenKeys(
              state.lastSyncedScreen,
              state.screen as ScreenSchemaV1
            );
            const serverChanged = changedScreenKeys(state.lastSyncedScreen, latestSchema);
            let autoMergedScreen: ScreenSchemaV1 | null = null;
            const hasOverlap = [...localChanged].some((key) => serverChanged.has(key));
            if (!hasOverlap && localChanged.size > 0) {
              autoMergedScreen = buildAutoMergedScreen(
                latestSchema,
                state.screen as ScreenSchemaV1,
                localChanged
              );
            }
            set({
              draftConflict: {
                hasConflict: true,
                message: "Another editor saved newer changes. Choose reload or force save.",
                expectedUpdatedAt: state.serverUpdatedAt,
                serverUpdatedAt: latestAsset?.updated_at || null,
                serverScreen: latestSchema,
                autoMergedScreen,
              },
            });
          } catch {
            set({
              draftConflict: {
                hasConflict: true,
                message:
                  "Another editor saved newer changes. Reload latest version before saving.",
                expectedUpdatedAt: state.serverUpdatedAt,
                serverUpdatedAt: null,
                serverScreen: null,
                autoMergedScreen: null,
              },
            });
          }
          throw new Error("Draft conflict detected");
        } else if (
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
            const postUpdatedAt =
              ((postResponse as { data?: { asset?: { updated_at?: string } } })?.data?.asset
                ?.updated_at as string | undefined) || state.serverUpdatedAt || null;
            set({
              serverUpdatedAt: postUpdatedAt,
              draftConflict: { ...EMPTY_DRAFT_CONFLICT },
            });
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
        lastSyncedScreen: state.screen,
      });
      console.log("[EDITOR] saveDraft completed successfully");
    } catch (error) {
      console.error("[EDITOR] saveDraft error:", error);
      set({ isSaving: false });
      throw error;
    }
  },

  clearDraftConflict: () => {
    set({ draftConflict: { ...EMPTY_DRAFT_CONFLICT } });
  },

  applyAutoMergedConflict: () => {
    const state = get();
    const merged = state.draftConflict.autoMergedScreen;
    if (!merged) return;
    set({
      screen: merged,
      draftModified: true,
      validationErrors: validateScreen(merged),
      draftConflict: {
        ...state.draftConflict,
        message: "Auto-merged draft prepared. Review and save.",
      },
    });
  },

  reloadFromServer: async () => {
    if (!currentAssetId) return;
    await get().loadScreen(currentAssetId);
  },

  forceSaveDraft: async () => {
    await get().saveDraft({ force: true });
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
    set(() => ({
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
      selectedComponentIds: [],
      draftModified: false,
      status: "draft",
      validationErrors: [],
      isSaving: false,
      isPublishing: false,
      isRollbacking: false,
      previewEnabled: false,
      previewError: null,
      serverUpdatedAt: null,
      lastSyncedScreen: null,
      draftConflict: { ...EMPTY_DRAFT_CONFLICT },
      historyStack: [],
      historyIndex: -1,
      clipboard: null,
      clipboardOperation: null,
    });
  },
}));
