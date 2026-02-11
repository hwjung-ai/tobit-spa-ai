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
      // Skip shortcuts when focus is in an input element
      const tag = (e.target as HTMLElement)?.tagName;
      const isEditable = tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable;
      if (isEditable) return;

      const isMod = e.ctrlKey || e.metaKey;

      // Undo: Ctrl+Z
      if (isMod && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        editorState.undo();
        return;
      }
      // Redo: Ctrl+Shift+Z
      if (isMod && e.key === "z" && e.shiftKey) {
        e.preventDefault();
        editorState.redo();
        return;
      }
      // Select All: Ctrl+A
      if (isMod && e.key === "a") {
        e.preventDefault();
        editorState.selectAll();
        return;
      }
      // Copy: Ctrl+C
      if (isMod && e.key === "c") {
        e.preventDefault();
        editorState.copySelectedComponents();
        return;
      }
      // Cut: Ctrl+X
      if (isMod && e.key === "x") {
        e.preventDefault();
        editorState.cutSelectedComponents();
        return;
      }
      // Paste: Ctrl+V
      if (isMod && e.key === "v") {
        e.preventDefault();
        editorState.pasteComponents();
        return;
      }
      // Duplicate: Ctrl+D
      if (isMod && e.key === "d") {
        e.preventDefault();
        editorState.duplicateSelectedComponents();
        return;
      }
      // Escape: Deselect
      if (e.key === "Escape") {
        editorState.deselectAll();
        return;
      }
      // Delete: Delete selected components
      if (e.key === "Delete" && editorState.selectedComponentIds.length > 0) {
        editorState.deleteSelectedComponents();
        return;
      }
      // Arrow keys for reordering (with Ctrl/Cmd)
      if (isMod && editorState.selectedComponentId && editorState.screen) {
        const isGrid = editorState.screen.layout.type === "dashboard" || editorState.screen.layout.type === "grid";

        if (isGrid) {
          const comp = editorState.screen.components.find(c => c.id === editorState.selectedComponentId);
          if (comp) {
            const layout = (comp.props?.layout as { x: number, y: number, w: number, h: number }) || { x: 0, y: 0, w: 4, h: 2 };
            const newLayout = { ...layout };

            // Movement (Ctrl+Arrow)
            if (!e.shiftKey) {
              if (e.key === "ArrowUp") newLayout.y = Math.max(0, layout.y - 1);
              if (e.key === "ArrowDown") newLayout.y = layout.y + 1;
              if (e.key === "ArrowLeft") newLayout.x = Math.max(0, layout.x - 1);
              if (e.key === "ArrowRight") newLayout.x = Math.min(11, layout.x + 1);
            }

            // Resize (Ctrl+Shift+Arrow)
            if (e.shiftKey) {
              if (e.key === "ArrowRight") newLayout.w = Math.min(12 - layout.x, layout.w + 1);
              if (e.key === "ArrowLeft") newLayout.w = Math.max(1, layout.w - 1);
              if (e.key === "ArrowDown") newLayout.h = layout.h + 1;
              if (e.key === "ArrowUp") newLayout.h = Math.max(1, layout.h - 1);
            }

            if (JSON.stringify(newLayout) !== JSON.stringify(layout)) {
              e.preventDefault();
              editorState.updateComponentProps(comp.id, { layout: newLayout });
            }
            return;
          }
        }

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
