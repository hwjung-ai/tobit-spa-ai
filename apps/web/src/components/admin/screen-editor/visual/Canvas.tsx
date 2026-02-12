"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import CanvasComponent from "./CanvasComponent";
import GridCanvas from "./GridCanvas";
import { Button } from "@/components/ui/button";
import { PALETTE_DRAG_TYPE } from "./ComponentPalette";
import { ComponentType } from "@/lib/ui-screen/screen.schema";

export default function Canvas() {
  const editorState = useEditorState();
  const { screen, selectedComponentId, selectedComponentIds, moveComponent, reorderComponentAtIndex } = editorState;
  const [isDragOver, setIsDragOver] = useState(false);

  if (!screen) return null;

  if (screen.layout.type === "dashboard" || screen.layout.type === "grid") {
    return <GridCanvas />;
  }

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
    const typeData = e.dataTransfer.getData(PALETTE_DRAG_TYPE);
    const componentType = typeData ? (typeData as ComponentType) : null;
    if (componentType) {
      editorState.addComponent(componentType);
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "rgba(15, 23, 42, 0.5)" }}>
      {/* Header */}
      <div className="border-b p-3" style={{ borderColor: "var(--border)" }}>
        <h3 className="text-sm font-semibold" style={{ color: "var(--foreground-secondary)" }}>
          Canvas ({screen.components.length})
        </h3>
      </div>

      {/* Component List */}
      <div
        className={`flex-1 overflow-y-auto p-3 space-y-2 transition-colors ${isDragOver ? "ring-2 ring-inset ring-sky-400/50" : ""
          }`}
        style={isDragOver ? { backgroundColor: "rgba(12, 74, 110, 0.3)" } : undefined}
        data-testid="canvas-list"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!hasComponents ? (
          <div className={`flex items-center justify-center h-full text-center border-2 border-dashed rounded-lg`}
            style={isDragOver ? { borderColor: "rgba(14, 165, 233, 1)", backgroundColor: "rgba(12, 74, 110, 0.2)" } : { borderColor: "var(--border-muted)" }}>
            <div className="space-y-2 p-6">
              <p className="text-sm" style={isDragOver ? { color: "#bae6fd" } : { color: "var(--muted-foreground)" }}>
                {isDragOver ? "Drop here to add" : "No components yet"}
              </p>
              <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
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
                  isSelected={selectedComponentIds.includes(component.id)}
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
