"use client";

import React from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { BindingEditor, type PathTreeNode } from "@/components/admin/screen-editor/visual/BindingEditor";

/**
 * BindingTab Component
 *
 * Tab for managing screen-level and component-level data bindings.
 * Allows users to create and modify bindings between UI components and data sources.
 */
export default function BindingTab() {
  const editorState = useEditorState();
  const [selectedBinding, setSelectedBinding] = React.useState<string | null>(null);

  if (!editorState.screen) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-400">No screen loaded</div>
      </div>
    );
  }

  const bindings = editorState.getAllBindings();
  const bindingEntries = Object.entries(bindings);

  // Build state tree from screen state
  const stateTree: PathTreeNode[] = [
    {
      path: "state",
      label: "State",
      children: Object.keys(editorState.screen.state?.initial || {}).map((key) => ({
        path: `state.${key}`,
        label: key,
      })),
    },
  ];

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <div>
        <h3 className="text-sm font-semibold text-white mb-3">Data Bindings</h3>
        <p className="text-xs text-slate-400 mb-4">
          Map component properties to state or context data
        </p>
      </div>

      {bindingEntries.length === 0 ? (
        <div className="flex items-center justify-center flex-1">
          <div className="text-center text-slate-400">
            <p className="text-sm mb-2">No bindings created yet</p>
            <p className="text-xs">Bindings will appear here</p>
          </div>
        </div>
      ) : (
        <div className="space-y-2 flex-1 overflow-y-auto">
          {bindingEntries.map(([targetPath, sourcePath]) => (
            <div
              key={targetPath}
              onClick={() => setSelectedBinding(targetPath)}
              className={`p-3 rounded border cursor-pointer transition ${
                selectedBinding === targetPath
                  ? "border-sky-400 bg-sky-400/10"
                  : "border-slate-700 bg-slate-800/50 hover:border-slate-600"
              }`}
            >
              <div className="text-xs font-mono text-sky-300">{targetPath}</div>
              <div className="text-xs text-slate-400 mt-1">→ {sourcePath}</div>
            </div>
          ))}
        </div>
      )}

      {selectedBinding && (
        <div className="border-t border-slate-700 pt-4">
          <h4 className="text-xs font-semibold text-white mb-3">Edit Binding</h4>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-300 block mb-1">Target Path</label>
              <div className="text-xs font-mono text-slate-400 p-2 bg-slate-900 rounded">
                {selectedBinding}
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-300 block mb-2">Source Path</label>
              <input
                type="text"
                value={bindings[selectedBinding] || ""}
                onChange={(e) => {
                  editorState.updateBinding(selectedBinding, e.target.value);
                }}
                placeholder="state.propertyName or context.key"
                className="w-full text-xs p-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  editorState.deleteBinding(selectedBinding);
                  setSelectedBinding(null);
                }}
                className="flex-1 px-3 py-2 text-xs bg-red-900/50 hover:bg-red-900 text-red-300 rounded transition"
              >
                Delete
              </button>
              <button
                onClick={() => setSelectedBinding(null)}
                className="flex-1 px-3 py-2 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-slate-700 pt-4 text-xs text-slate-400">
        <p className="mb-2">
          <strong>Binding Format:</strong>
        </p>
        <ul className="space-y-1 text-slate-500 list-disc list-inside">
          <li>Static values: <code className="text-slate-400">hello</code>, <code className="text-slate-400">123</code></li>
          <li>State: <code className="text-slate-400">state.userName</code></li>
          <li>Context: <code className="text-slate-400">context.userId</code></li>
          <li>Inputs: <code className="text-slate-400">inputs.formData</code></li>
        </ul>
      </div>
    </div>
  );
}
