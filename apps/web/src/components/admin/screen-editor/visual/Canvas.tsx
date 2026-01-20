"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import CanvasComponent from "./CanvasComponent";
import { Button } from "@/components/ui/button";
import { PALETTE_DRAG_TYPE } from "./ComponentPalette";

export default function Canvas() {
  const editorState = useEditorState();
  const { screen, selectedComponentId, moveComponent, reorderComponentAtIndex } = editorState;
  const [isDragOver, setIsDragOver] = useState(false);

  if (!screen) return null;

  const hasComponents = screen.components.length > 0;

  const handleDragOver = (e: React.DragEvent) => {
    if (e.dataTransfer.types.includes(PALETTE_DRAG_TYPE)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    // Only set false if leaving the container itself
    if (e.currentTarget === e.target) {
      setIsDragOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const componentType = e.dataTransfer.getData(PALETTE_DRAG_TYPE);
    if (componentType) {
      editorState.addComponent(componentType);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* Header */}
      <div className="border-b border-slate-800 p-3">
        <h3 className="text-sm font-semibold text-slate-200">
          Canvas ({screen.components.length})
        </h3>
      </div>

      {/* Component List */}
      <div
        className={`flex-1 overflow-y-auto p-3 space-y-2 transition-colors ${
          isDragOver ? "bg-sky-950/30 ring-2 ring-inset ring-sky-500/50" : ""
        }`}
        data-testid="canvas-list"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!hasComponents ? (
          <div className={`flex items-center justify-center h-full text-center border-2 border-dashed rounded-lg ${
            isDragOver ? "border-sky-500 bg-sky-950/20" : "border-slate-700"
          }`}>
            <div className="space-y-2 p-6">
              <p className={`text-sm ${isDragOver ? "text-sky-300" : "text-slate-400"}`}>
                {isDragOver ? "Drop here to add" : "No components yet"}
              </p>
              <p className="text-slate-500 text-xs">
                {isDragOver ? "" : "Drag components from the palette or click to add"}
              </p>
            </div>
          </div>
        ) : (
          <>
            {screen.components.map((component, index) => (
              <div key={component.id} className="space-y-1">
                <CanvasComponent
                  component={component}
                  isSelected={selectedComponentId === component.id}
                  onSelect={() => editorState.selectComponent(component.id)}
                  index={index}
                  parentId={null}
                  onReorder={(dragId, dropIndex) => reorderComponentAtIndex(dragId, dropIndex, null)}
                />

                {/* Move buttons (only show if selected) */}
                {selectedComponentId === component.id && (
                  <div className="flex gap-1 px-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1 h-7 text-xs"
                      onClick={() => moveComponent(component.id, "up")}
                      disabled={index === 0}
                      data-testid={`btn-move-up-${component.id}`}
                    >
                      ▲ Up
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1 h-7 text-xs"
                      onClick={() => moveComponent(component.id, "down")}
                      disabled={index === screen.components.length - 1}
                      data-testid={`btn-move-down-${component.id}`}
                    >
                      ▼ Down
                    </Button>
                  </div>
                )}
              </div>
            ))}
            {/* Drop zone at the end */}
            {isDragOver && (
              <div className="h-16 border-2 border-dashed border-sky-500 rounded-lg bg-sky-950/20 flex items-center justify-center">
                <p className="text-xs text-sky-300">Drop here</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
