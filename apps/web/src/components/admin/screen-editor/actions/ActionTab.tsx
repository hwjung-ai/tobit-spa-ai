"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { ScreenAction, ComponentActionRef } from "@/lib/ui-screen/screen.schema";
import { Button } from "@/components/ui/button";

/**
 * ActionTab Component
 *
 * Tab for managing screen-level actions and component-level actions.
 * Actions can be:
 * - Screen actions: Global actions triggered by UI events
 * - Component actions: Actions tied to specific components
 */
export default function ActionTab() {
  const editorState = useEditorState();
  const [selectedActionId, setSelectedActionId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<"screen" | "component">("screen");
  const [editingAction, setEditingAction] = useState<ScreenAction | null>(null);

  if (!editorState.screen) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-400">No screen loaded</div>
      </div>
    );
  }

  const screenActions = editorState.screen.actions || [];
  const componentActions = editorState.selectedComponentId
    ? editorState.getComponentActions(editorState.selectedComponentId)
    : [];

  const actions = actionType === "screen" ? screenActions : componentActions;

  const handleAddAction = () => {
    const newAction: ScreenAction = {
      id: `action_${Date.now()}`,
      handler: "",
      payload_template: {},
    };
    editorState.addAction(newAction);
    setSelectedActionId(newAction.id);
  };

  const handleSaveAction = (action: ScreenAction) => {
    editorState.updateAction(action.id, action);
    setEditingAction(null);
  };

  const handleDeleteAction = (actionId: string) => {
    editorState.deleteAction(actionId);
    setSelectedActionId(null);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <div>
        <h3 className="text-sm font-semibold text-white mb-2">Screen Actions</h3>
        <p className="text-xs text-slate-400 mb-4">
          Define actions that respond to user interactions and events
        </p>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActionType("screen")}
          className={`flex-1 px-3 py-2 text-xs rounded transition ${
            actionType === "screen"
              ? "bg-sky-600 text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700"
          }`}
        >
          Screen Actions ({screenActions.length})
        </button>
        <button
          onClick={() => setActionType("component")}
          disabled={!editorState.selectedComponentId}
          className={`flex-1 px-3 py-2 text-xs rounded transition ${
            actionType === "component"
              ? "bg-sky-600 text-white"
              : editorState.selectedComponentId
                ? "bg-slate-800 text-slate-400 hover:bg-slate-700"
                : "bg-slate-900 text-slate-600 cursor-not-allowed"
          }`}
        >
          Component Actions ({componentActions.length})
        </button>
      </div>

      {actions.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <div className="text-center text-slate-400">
            <p className="text-sm mb-2">No {actionType} actions</p>
            <p className="text-xs">Create your first action to get started</p>
          </div>
          <button
            onClick={handleAddAction}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs rounded transition"
          >
            + New Action
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-2 flex-1 overflow-y-auto">
            {actions.map((action) => (
              <div
                key={action.id}
                onClick={() => {
                  setSelectedActionId(action.id);
                  setEditingAction(action);
                }}
                className={`p-3 rounded border cursor-pointer transition ${
                  selectedActionId === action.id
                    ? "border-sky-400 bg-sky-400/10"
                    : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
                }`}
              >
                <div className="text-xs font-mono text-sky-300">{action.id}</div>
                <div className="text-xs text-slate-400 mt-1">Handler: {action.handler || "-"}</div>
              </div>
            ))}
          </div>

          <button
            onClick={handleAddAction}
            className="w-full px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded transition"
          >
            + Add Action
          </button>
        </>
      )}

      {editingAction && (
        <div className="border-t border-slate-700 pt-4 space-y-3">
          <h4 className="text-xs font-semibold text-white">Edit Action</h4>

          <div>
            <label className="text-xs text-slate-300 block mb-1">Action ID</label>
            <input
              type="text"
              value={editingAction.id}
              disabled
              className="w-full text-xs p-2 bg-slate-900 border border-slate-700 rounded text-slate-500 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="text-xs text-slate-300 block mb-1">Handler</label>
            <input
              type="text"
              value={editingAction.handler}
              onChange={(e) =>
                setEditingAction({ ...editingAction, handler: e.target.value })
              }
              placeholder="e.g., api.fetchUserData, workflow.submitForm"
              className="w-full text-xs p-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => handleSaveAction(editingAction)}
              className="flex-1 px-3 py-2 text-xs bg-sky-600 hover:bg-sky-700 text-white rounded transition"
            >
              Save
            </button>
            <button
              onClick={() => {
                handleDeleteAction(editingAction.id);
              }}
              className="flex-1 px-3 py-2 text-xs bg-red-900/50 hover:bg-red-900 text-red-300 rounded transition"
            >
              Delete
            </button>
            <button
              onClick={() => setEditingAction(null)}
              className="flex-1 px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded transition"
            >
              Close
            </button>
          </div>
        </div>
      )}

      <div className="border-t border-slate-700 pt-4 text-xs text-slate-400">
        <p className="mb-2">
          <strong>Action Types:</strong>
        </p>
        <ul className="space-y-1 text-slate-500 list-disc list-inside">
          <li>API calls: <code className="text-slate-400">api.endpoint</code></li>
          <li>Workflows: <code className="text-slate-400">workflow.name</code></li>
          <li>State updates: <code className="text-slate-400">state.set</code></li>
          <li>Navigation: <code className="text-slate-400">nav.goTo</code></li>
        </ul>
      </div>
    </div>
  );
}
