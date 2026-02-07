"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { ComponentActionRef, ScreenAction } from "@/lib/ui-screen/screen.schema";
import ActionFlowVisualizer from "./ActionFlowVisualizer";

type ActionKind = "screen" | "component";
type ViewMode = "list" | "flow";

export default function ActionTab() {
  const editorState = useEditorState();
  const [selectedActionId, setSelectedActionId] = useState<string | null>(null);
  const [actionKind, setActionKind] = useState<ActionKind>("screen");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [editingAction, setEditingAction] = useState<ScreenAction | ComponentActionRef | null>(null);

  if (!editorState.screen) {
    return <div className="flex h-full items-center justify-center text-slate-400">No screen loaded</div>;
  }

  const screenActions = editorState.screen.actions || [];
  const componentActions = editorState.selectedComponentId
    ? editorState.getComponentActions(editorState.selectedComponentId)
    : [];

  const actions = actionKind === "screen" ? screenActions : componentActions;

  const selectedAction = actions.find((item) => item.id === selectedActionId) || null;

  const handleAddAction = () => {
    if (actionKind === "screen") {
      const action: ScreenAction = {
        id: `action_${Date.now()}`,
        handler: "",
        payload_template: {},
      };
      editorState.addAction(action);
      setSelectedActionId(action.id);
      setEditingAction(action);
      return;
    }

    if (!editorState.selectedComponentId) {
      return;
    }

    const action: ComponentActionRef = {
      id: `action_${Date.now()}`,
      handler: "",
      payload_template: {},
      continue_on_error: false,
      stop_on_error: true,
      retry_count: 0,
      retry_delay_ms: 500,
      on_error_action_index: -1,
      on_error_action_indexes: [],
    };
    editorState.addComponentAction(editorState.selectedComponentId, action);
    setSelectedActionId(action.id);
    setEditingAction(action);
  };

  const handleDeleteAction = (actionId: string) => {
    if (actionKind === "screen") {
      editorState.deleteAction(actionId);
    } else if (editorState.selectedComponentId) {
      editorState.deleteComponentAction(editorState.selectedComponentId, actionId);
    }
    setSelectedActionId(null);
    setEditingAction(null);
  };

  const handleSaveAction = () => {
    if (!editingAction) return;
    if (actionKind === "screen") {
      editorState.updateAction(editingAction.id, editingAction);
    } else if (editorState.selectedComponentId) {
      editorState.updateComponentAction(
        editorState.selectedComponentId,
        editingAction.id,
        editingAction as Partial<ComponentActionRef>
      );
    }
    setEditingAction(null);
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white">Actions</h3>
          <p className="text-xs text-slate-400">Manage action chains and execution flow</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode("list")}
            className={`rounded px-3 py-1.5 text-xs ${
              viewMode === "list"
                ? "bg-sky-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            List View
          </button>
          <button
            onClick={() => setViewMode("flow")}
            className={`rounded px-3 py-1.5 text-xs ${
              viewMode === "flow"
                ? "bg-sky-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            Flow View
          </button>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setActionKind("screen")}
          className={`flex-1 rounded px-3 py-2 text-xs ${
            actionKind === "screen"
              ? "bg-sky-600 text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700"
          }`}
        >
          Screen Actions ({screenActions.length})
        </button>
        <button
          onClick={() => setActionKind("component")}
          disabled={!editorState.selectedComponentId}
          className={`flex-1 rounded px-3 py-2 text-xs ${
            actionKind === "component"
              ? "bg-sky-600 text-white"
              : editorState.selectedComponentId
              ? "bg-slate-800 text-slate-400 hover:bg-slate-700"
              : "cursor-not-allowed bg-slate-900 text-slate-600"
          }`}
        >
          Component Actions ({componentActions.length})
        </button>
      </div>

      {viewMode === "flow" ? (
        <div className="min-h-0 flex-1">
          <ActionFlowVisualizer actions={actions} />
        </div>
      ) : (
        <>
          {actions.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3">
              <div className="text-center text-slate-400">
                <div className="text-sm">No actions</div>
                <div className="text-xs">Create an action to start chaining workflows</div>
              </div>
              <button
                onClick={handleAddAction}
                className="rounded bg-sky-600 px-4 py-2 text-xs text-white hover:bg-sky-700"
              >
                + New Action
              </button>
            </div>
          ) : (
            <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr] gap-3">
              <div className="overflow-y-auto rounded border border-slate-700 bg-slate-900/40 p-2">
                <div className="mb-2 flex justify-end">
                  <button
                    onClick={handleAddAction}
                    className="rounded bg-slate-700 px-2 py-1 text-[11px] text-white hover:bg-slate-600"
                  >
                    + Add
                  </button>
                </div>
                <div className="space-y-2">
                  {actions.map((action) => (
                    <button
                      type="button"
                      key={action.id}
                      onClick={() => {
                        setSelectedActionId(action.id);
                        setEditingAction(action);
                      }}
                      className={`w-full rounded border p-2 text-left ${
                        selectedActionId === action.id
                          ? "border-sky-500 bg-sky-500/10"
                          : "border-slate-700 bg-slate-800/60 hover:border-slate-600"
                      }`}
                    >
                      <div className="text-xs font-mono text-sky-300">{action.id}</div>
                      <div className="mt-1 text-[11px] text-slate-400">{action.handler || "(unset)"}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded border border-slate-700 bg-slate-900/30 p-3">
                {!editingAction && <div className="text-xs text-slate-400">Select an action to edit.</div>}
                {editingAction && (
                  <div className="space-y-3">
                    <div>
                      <label className="mb-1 block text-xs text-slate-300">Action ID</label>
                      <input
                        type="text"
                        value={editingAction.id}
                        disabled
                        className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-xs text-slate-500"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs text-slate-300">Handler</label>
                      <input
                        type="text"
                        value={editingAction.handler || ""}
                        onChange={(e) =>
                          setEditingAction((prev) =>
                            prev ? { ...prev, handler: e.target.value } : prev
                          )
                        }
                        className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-xs text-white"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        onClick={handleSaveAction}
                        className="rounded bg-sky-600 px-3 py-2 text-xs text-white hover:bg-sky-700"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => handleDeleteAction(editingAction.id)}
                        className="rounded bg-rose-900/60 px-3 py-2 text-xs text-rose-200 hover:bg-rose-900"
                      >
                        Delete
                      </button>
                      <button
                        onClick={() => {
                          setEditingAction(selectedAction);
                        }}
                        className="rounded bg-slate-700 px-3 py-2 text-xs text-white hover:bg-slate-600"
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
