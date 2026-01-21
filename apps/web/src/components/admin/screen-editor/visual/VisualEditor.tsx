"use client";

import React, { useEffect } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import ComponentPalette from "./ComponentPalette";
import Canvas from "./Canvas";
import ComponentTreeView from "./ComponentTreeView";
import PropertiesPanel from "./PropertiesPanel";

export default function VisualEditor() {
  const editorState = useEditorState();

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Delete key: delete selected component
      if (e.key === "Delete" && editorState.selectedComponentId) {
        editorState.deleteComponent(editorState.selectedComponentId);
      }

      // Arrow keys for reordering (with Ctrl/Cmd)
      if ((e.ctrlKey || e.metaKey) && editorState.selectedComponentId) {
        if (e.key === "ArrowUp") {
          e.preventDefault();
          editorState.moveComponent(editorState.selectedComponentId, "up");
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          editorState.moveComponent(editorState.selectedComponentId, "down");
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editorState]);

  if (editorState.status === "published") {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-slate-400">Published screens are read-only</p>
          <p className="text-slate-500 text-sm">Rollback to draft to edit</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="h-full grid gap-4 relative"
      style={{ gridTemplateColumns: "200px 1fr 220px 300px" }}
      data-testid="visual-editor"
    >
      {editorState.previewEnabled && (
        <div className="absolute inset-x-6 top-6 z-10 rounded-lg border border-sky-500/40 bg-sky-950/60 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-sky-200">
          Preview overlay active
        </div>
      )}
      {/* Left: Component Palette */}
      <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col">
        <ComponentPalette />
      </div>

      {/* Center: Canvas */}
      <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col">
        <Canvas />
      </div>

      {/* Tree: Component hierarchy */}
      <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col">
        <ComponentTreeView />
      </div>

      {/* Right: Properties Panel */}
      <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col">
        <PropertiesPanel />
      </div>
    </div>
  );
}
