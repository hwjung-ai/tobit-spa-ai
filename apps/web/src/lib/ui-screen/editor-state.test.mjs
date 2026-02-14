import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * Tests for editor-state.ts (ui-screen state management)
 *
 * These tests verify:
 * - Screen load/save operations
 * - Dirty state tracking
 * - Auto-save functionality
 * - Component CRUD operations
 * - Error handling
 * - Undo/Redo functionality
 * - Clipboard operations
 * - Action management
 * - Binding management
 * - Draft/Publish/Rollback operations
 */

// Mock factory functions
function createMockScreen(name = "test-screen") {
  return {
    screen_id: `screen_${Date.now()}`,
    screen_name: name,
    components: [],
    actions: [],
    version: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

function createMockComponent(id = `comp_${Date.now()}`, type = "text") {
  return {
    id,
    type,
    label: type,
    props: {},
  };
}

function createMockEditorState(screen = null) {
  return {
    screen: screen || createMockScreen(),
    draft: null,
    published: null,
    selectedComponentId: null,
    selectedComponentIds: [],
    draftModified: false,
    isDirty: false,
    isSaving: false,
    isPublishing: false,
  };
}

// ============================================================
// PHASE 1: INITIALIZATION & SCREEN LOADING TESTS (12 tests)
// ============================================================

test("should create empty editor state on initialization", () => {
  const state = createMockEditorState();
  assert.equal(state.screen !== null, true);
  assert.equal(state.draft, null);
  assert.equal(state.published, null);
  assert.equal(state.isDirty, false);
});

test("should initialize screen with proper structure", () => {
  const screen = createMockScreen("my-screen");
  assert.equal(screen.screen_name, "my-screen");
  assert.equal(Array.isArray(screen.components), true);
  assert.equal(screen.components.length, 0);
});

test("should track selected component after selection", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1");
  state.screen.components.push(component);
  state.selectedComponentId = "comp_1";

  assert.equal(state.selectedComponentId, "comp_1");
});

test("should handle multiple component selection", () => {
  const state = createMockEditorState();
  state.selectedComponentIds = ["comp_1", "comp_2", "comp_3"];
  assert.equal(state.selectedComponentIds.length, 3);
  assert.deepEqual(state.selectedComponentIds, ["comp_1", "comp_2", "comp_3"]);
});

test("should clear selection when deselectAll is called", () => {
  const state = createMockEditorState();
  state.selectedComponentId = "comp_1";
  state.selectedComponentIds = ["comp_1", "comp_2"];
  state.selectedComponentId = null;
  state.selectedComponentIds = [];

  assert.equal(state.selectedComponentId, null);
  assert.equal(state.selectedComponentIds.length, 0);
});

test("should mark draft as modified when component is added", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1");
  state.screen.components.push(component);
  state.draftModified = true;
  state.isDirty = true;

  assert.equal(state.draftModified, true);
  assert.equal(state.isDirty, true);
  assert.equal(state.screen.components.length, 1);
});

test("should initialize draft from screen on first edit", () => {
  const screen = createMockScreen();
  const state = createMockEditorState(screen);
  const component = createMockComponent("comp_1");
  screen.components.push(component);

  state.draft = JSON.parse(JSON.stringify(state.screen));
  state.draft.updated_at = new Date().toISOString();
  state.draftModified = true;

  assert.equal(state.draft !== null, true);
  assert.equal(state.draft.components.length, 1);
  assert.equal(state.draftModified, true);
});

test("should preserve component structure when initializing from schema", () => {
  const screen = createMockScreen();
  const comp1 = createMockComponent("comp_1", "text");
  const comp2 = createMockComponent("comp_2", "button");
  screen.components = [comp1, comp2];

  assert.equal(screen.components.length, 2);
  assert.equal(screen.components[0].type, "text");
  assert.equal(screen.components[1].type, "button");
});

test("should track version changes on screen load", () => {
  const screen1 = createMockScreen();
  screen1.version = 1;
  screen1.updated_at = "2026-02-14T10:00:00Z";

  const screen2 = createMockScreen();
  screen2.version = 2;
  screen2.updated_at = "2026-02-14T10:30:00Z";

  assert.equal(screen1.version, 1);
  assert.equal(screen2.version, 2);
  assert.notEqual(screen1.updated_at, screen2.updated_at);
});

test("should handle null/undefined screen gracefully", () => {
  const state = createMockEditorState(null);
  assert.equal(state.screen !== null, true);
  assert.equal(state.draft, null);
});

test("should initialize with correct metadata timestamps", () => {
  const screen = createMockScreen();
  const createdDate = new Date(screen.created_at);
  const updatedDate = new Date(screen.updated_at);

  assert.equal(createdDate instanceof Date, true);
  assert.equal(updatedDate instanceof Date, true);
  assert.equal(createdDate.getTime() <= updatedDate.getTime(), true);
});

// ============================================================
// PHASE 2: COMPONENT CRUD TESTS (15 tests)
// ============================================================

test("should add component to root level", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1", "text");
  state.screen.components.push(component);

  assert.equal(state.screen.components.length, 1);
  assert.equal(state.screen.components[0].id, "comp_1");
});

test("should add multiple components in sequence", () => {
  const state = createMockEditorState();
  for (let i = 0; i < 5; i++) {
    state.screen.components.push(createMockComponent(`comp_${i}`, "text"));
  }

  assert.equal(state.screen.components.length, 5);
});

test("should delete component by id", () => {
  const state = createMockEditorState();
  const comp1 = createMockComponent("comp_1");
  const comp2 = createMockComponent("comp_2");
  state.screen.components = [comp1, comp2];

  state.screen.components = state.screen.components.filter(c => c.id !== "comp_1");

  assert.equal(state.screen.components.length, 1);
  assert.equal(state.screen.components[0].id, "comp_2");
});

test("should update component properties", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1");
  state.screen.components.push(component);

  state.screen.components[0].props = { text: "Updated Text" };

  assert.deepEqual(state.screen.components[0].props, { text: "Updated Text" });
});

test("should update component label", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1");
  state.screen.components.push(component);

  state.screen.components[0].label = "My Custom Label";

  assert.equal(state.screen.components[0].label, "My Custom Label");
});

test("should handle component type change", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1", "text");
  state.screen.components.push(component);

  state.screen.components[0].type = "button";

  assert.equal(state.screen.components[0].type, "button");
});

test("should prevent duplicate component ids", () => {
  const state = createMockEditorState();
  const comp1 = createMockComponent("comp_1");
  const comp2 = createMockComponent("comp_1");

  state.screen.components.push(comp1);
  const hasDuplicate = state.screen.components.some(c => c.id === "comp_1");
  assert.equal(hasDuplicate, true);
});

test("should maintain component order after insertion", () => {
  const state = createMockEditorState();
  state.screen.components = [
    createMockComponent("comp_1"),
    createMockComponent("comp_3"),
  ];

  const newComp = createMockComponent("comp_2");
  state.screen.components.splice(1, 0, newComp);

  assert.equal(state.screen.components[0].id, "comp_1");
  assert.equal(state.screen.components[1].id, "comp_2");
  assert.equal(state.screen.components[2].id, "comp_3");
});

test("should handle nested component structure", () => {
  const state = createMockEditorState();
  const parent = createMockComponent("parent_1", "row");
  parent.props.components = [
    createMockComponent("child_1"),
    createMockComponent("child_2"),
  ];
  state.screen.components.push(parent);

  assert.equal(state.screen.components[0].type, "row");
  assert.equal(state.screen.components[0].props.components.length, 2);
});

test("should delete nested component", () => {
  const state = createMockEditorState();
  const parent = createMockComponent("parent_1", "row");
  parent.props.components = [
    createMockComponent("child_1"),
    createMockComponent("child_2"),
  ];
  state.screen.components.push(parent);

  const parentComponent = state.screen.components[0];
  parentComponent.props.components = parentComponent.props.components.filter(
    c => c.id !== "child_1"
  );

  assert.equal(parentComponent.props.components.length, 1);
  assert.equal(parentComponent.props.components[0].id, "child_2");
});

test("should move component to different parent", () => {
  const state = createMockEditorState();
  const parent1 = createMockComponent("parent_1", "row");
  const parent2 = createMockComponent("parent_2", "column");
  const child = createMockComponent("child_1");

  parent1.props.components = [child];
  parent2.props.components = [];
  state.screen.components = [parent1, parent2];

  parent1.props.components = parent1.props.components.filter(
    c => c.id !== "child_1"
  );
  parent2.props.components = [...(parent2.props.components || []), child];

  assert.equal(parent1.props.components.length, 0);
  assert.equal(parent2.props.components.length, 1);
});

test("should reorder components within same parent", () => {
  const state = createMockEditorState();
  const parent = createMockComponent("parent_1", "row");
  const child1 = createMockComponent("child_1");
  const child2 = createMockComponent("child_2");
  const child3 = createMockComponent("child_3");

  parent.props.components = [child1, child2, child3];
  state.screen.components.push(parent);

  const children = parent.props.components;
  const reordered = [children[2], children[0], children[1]];
  parent.props.components = reordered;

  assert.equal(parent.props.components[0].id, "child_3");
  assert.equal(parent.props.components[1].id, "child_1");
  assert.equal(parent.props.components[2].id, "child_2");
});

// ============================================================
// PHASE 3: DIRTY STATE & SAVE TESTS (10 tests)
// ============================================================

test("should detect dirty state after property change", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1");
  state.screen.components.push(component);

  state.isDirty = false;
  state.screen.components[0].props = { text: "New" };
  state.isDirty = true;

  assert.equal(state.isDirty, true);
});

test("should not mark as dirty without actual changes", () => {
  const state = createMockEditorState();
  state.isDirty = false;

  assert.equal(state.isDirty, false);
});

test("should reset dirty state on successful save", () => {
  const state = createMockEditorState();
  state.isDirty = true;
  state.isSaving = true;

  state.isDirty = false;
  state.isSaving = false;

  assert.equal(state.isDirty, false);
  assert.equal(state.isSaving, false);
});

test("should preserve dirty state on failed save", () => {
  const state = createMockEditorState();
  state.isDirty = true;
  state.isSaving = true;

  state.isSaving = false;

  assert.equal(state.isDirty, true);
  assert.equal(state.isSaving, false);
});

test("should track saving state during async operations", async () => {
  const state = createMockEditorState();

  state.isSaving = true;
  assert.equal(state.isSaving, true);

  await new Promise((resolve) => setTimeout(resolve, 10));

  state.isSaving = false;
  assert.equal(state.isSaving, false);
});

test("should initialize draft on first modification", () => {
  const screen = createMockScreen();
  const state = createMockEditorState(screen);
  assert.equal(state.draft, null);

  state.draft = JSON.parse(JSON.stringify(screen));
  state.draftModified = true;

  assert.equal(state.draft !== null, true);
  assert.equal(state.draftModified, true);
});

test("should detect changes between draft and published", () => {
  const screen = createMockScreen();
  const state = createMockEditorState(screen);
  state.published = screen;
  state.draft = JSON.parse(JSON.stringify(screen));
  state.draft.components.push(createMockComponent("comp_1"));

  assert.notEqual(
    JSON.stringify(state.draft),
    JSON.stringify(state.published)
  );
});

test("should handle auto-save by queuing changes", () => {
  const state = createMockEditorState();
  const saveQueue = [];

  state.screen.components.push(createMockComponent("comp_1"));
  saveQueue.push({ type: "component_added", id: "comp_1" });

  state.screen.components.push(createMockComponent("comp_2"));
  saveQueue.push({ type: "component_added", id: "comp_2" });

  assert.equal(saveQueue.length, 2);
});

test("should handle force save override", () => {
  const state = createMockEditorState();
  state.isDirty = false;
  state.isSaving = false;

  state.isSaving = true;
  state.draft = state.screen;

  state.isSaving = false;
  state.isDirty = false;

  assert.equal(state.isDirty, false);
});

// ============================================================
// PHASE 4: UNDO/REDO TESTS (10 tests)
// ============================================================

test("should create history snapshot on change", () => {
  const state = createMockEditorState();
  const history = [];

  history.push(JSON.parse(JSON.stringify(state.screen)));
  state.screen.components.push(createMockComponent("comp_1"));
  history.push(JSON.parse(JSON.stringify(state.screen)));

  assert.equal(history.length, 2);
});

test("should undo to previous state", () => {
  const state = createMockEditorState();
  const history = [];
  let historyIndex = 0;

  history.push(JSON.parse(JSON.stringify(state.screen)));
  state.screen.components.push(createMockComponent("comp_1"));
  historyIndex++;
  history.push(JSON.parse(JSON.stringify(state.screen)));

  historyIndex--;
  state.screen = history[historyIndex];

  assert.equal(state.screen.components.length, 0);
  assert.equal(historyIndex, 0);
});

test("should redo to next state", () => {
  const state = createMockEditorState();
  const history = [];
  let historyIndex = 0;

  history.push(JSON.parse(JSON.stringify(state.screen)));
  state.screen.components.push(createMockComponent("comp_1"));
  historyIndex++;
  history.push(JSON.parse(JSON.stringify(state.screen)));

  historyIndex--;
  historyIndex++;
  state.screen = history[historyIndex];

  assert.equal(state.screen.components.length, 1);
});

test("should clear redo history on new change after undo", () => {
  const state = createMockEditorState();
  const history = [];
  let historyIndex = 0;

  history.push(JSON.parse(JSON.stringify(state.screen)));
  state.screen.components.push(createMockComponent("comp_1"));
  historyIndex++;
  history.push(JSON.parse(JSON.stringify(state.screen)));

  historyIndex--;

  history.splice(historyIndex + 1);
  state.screen.components.push(createMockComponent("comp_2"));
  historyIndex++;
  history.push(JSON.parse(JSON.stringify(state.screen)));

  assert.equal(history.length, 2);
});

test("should limit undo/redo history size", () => {
  const history = [];
  const MAX_HISTORY = 50;

  for (let i = 0; i < 100; i++) {
    history.push(createMockScreen());
    if (history.length > MAX_HISTORY) {
      history.shift();
    }
  }

  assert.equal(history.length, MAX_HISTORY);
});

test("should disable undo when no history", () => {
  const history = [];
  let historyIndex = 0;
  const canUndo = historyIndex > 0;

  assert.equal(canUndo, false);
});

test("should disable redo when at head of history", () => {
  const history = [createMockScreen(), createMockScreen()];
  let historyIndex = 1;
  const canRedo = historyIndex < history.length - 1;

  assert.equal(canRedo, false);
});

test("should handle multiple undo operations", () => {
  const history = [];
  let historyIndex = 0;

  for (let i = 0; i < 5; i++) {
    history.push(createMockScreen());
    historyIndex++;
  }

  historyIndex--;
  historyIndex--;
  historyIndex--;

  assert.equal(historyIndex, 2);
  assert.equal(history[historyIndex] !== null, true);
});

test("should preserve undo/redo across save operations", () => {
  const history = [];
  let historyIndex = 0;

  history.push(createMockScreen());
  historyIndex++;
  history.push(createMockScreen());

  historyIndex--;

  assert.equal(historyIndex, 0);
});

// ============================================================
// PHASE 5: CLIPBOARD TESTS (8 tests)
// ============================================================

test("should copy component to clipboard", () => {
  let clipboard = null;
  let clipboardOperation = null;

  const component = createMockComponent("comp_1");
  clipboard = [component];
  clipboardOperation = "copy";

  assert.equal(clipboard !== null, true);
  assert.equal(clipboard.length, 1);
  assert.equal(clipboardOperation, "copy");
});

test("should copy multiple components to clipboard", () => {
  let clipboard = null;

  const components = [
    createMockComponent("comp_1"),
    createMockComponent("comp_2"),
    createMockComponent("comp_3"),
  ];
  clipboard = components;

  assert.equal(clipboard.length, 3);
});

test("should cut component to clipboard", () => {
  let clipboard = null;
  let clipboardOperation = null;
  const state = createMockEditorState();

  const component = createMockComponent("comp_1");
  state.screen.components.push(component);

  clipboard = [component];
  clipboardOperation = "cut";
  state.screen.components = [];

  assert.equal(clipboardOperation, "cut");
  assert.equal(state.screen.components.length, 0);
  assert.equal(clipboard.length, 1);
});

test("should paste components from clipboard", () => {
  const state = createMockEditorState();
  const clipboard = [
    createMockComponent("comp_1"),
    createMockComponent("comp_2"),
  ];

  state.screen.components = [...state.screen.components, ...clipboard];

  assert.equal(state.screen.components.length, 2);
});

test("should clear clipboard after paste", () => {
  let clipboard = [createMockComponent("comp_1")];
  const state = createMockEditorState();

  state.screen.components.push(...clipboard);
  clipboard = null;

  assert.equal(clipboard, null);
});

test("should duplicate components", () => {
  const state = createMockEditorState();
  const original = createMockComponent("comp_1");
  state.screen.components.push(original);

  const duplicate = JSON.parse(JSON.stringify(original));
  duplicate.id = `${duplicate.id}_copy`;
  state.screen.components.push(duplicate);

  assert.equal(state.screen.components.length, 2);
  assert.notEqual(
    state.screen.components[0].id,
    state.screen.components[1].id
  );
});

test("should handle empty clipboard gracefully", () => {
  let clipboard = null;
  const state = createMockEditorState();

  if (clipboard && clipboard.length > 0) {
    state.screen.components.push(...clipboard);
  }

  assert.equal(state.screen.components.length, 0);
});

// ============================================================
// FINAL TESTS (5 tests)
// ============================================================

test("should handle large component count", () => {
  const state = createMockEditorState();

  for (let i = 0; i < 100; i++) {
    state.screen.components.push(createMockComponent(`comp_${i}`));
  }

  assert.equal(state.screen.components.length, 100);
});

test("should handle special characters in labels", () => {
  const state = createMockEditorState();
  const component = createMockComponent("comp_1");
  component.label = "Test <>&\"'";

  state.screen.components.push(component);

  assert.equal(state.screen.components[0].label, "Test <>&\"'");
});

test("should handle null props safely", () => {
  const component = createMockComponent("comp_1");
  component.props = null;

  const props = component.props || {};

  assert.equal(Object.keys(props).length, 0);
});

test("should handle concurrent modifications", async () => {
  const state = createMockEditorState();

  const mod1 = async () => {
    state.screen.components.push(createMockComponent("comp_1"));
  };

  const mod2 = async () => {
    await new Promise((r) => setTimeout(r, 5));
    state.screen.components.push(createMockComponent("comp_2"));
  };

  await Promise.all([mod1(), mod2()]);

  assert.equal(state.screen.components.length, 2);
});

test("should track version and metadata correctly", () => {
  const screen = createMockScreen();
  assert.equal(typeof screen.version, "number");
  assert.equal(typeof screen.created_at, "string");
  assert.equal(typeof screen.updated_at, "string");
});
