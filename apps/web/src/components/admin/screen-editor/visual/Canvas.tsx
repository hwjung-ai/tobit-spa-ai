"use client";

import React from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import CanvasComponent from "./CanvasComponent";
import { Button } from "@/components/ui/button";

export default function Canvas() {
  const editorState = useEditorState();
  const { screen, selectedComponentId, moveComponent } = editorState;

  if (!screen) return null;

  const hasComponents = screen.components.length > 0;

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
        className="flex-1 overflow-y-auto p-3 space-y-2"
        data-testid="canvas-list"
      >
        {!hasComponents ? (
          <div className="flex items-center justify-center h-full text-center">
            <div className="space-y-2">
              <p className="text-slate-400 text-sm">No components yet</p>
              <p className="text-slate-500 text-xs">
                Add components from the palette
              </p>
            </div>
          </div>
        ) : (
          screen.components.map((component, index) => (
            <div key={component.id} className="space-y-1">
              <CanvasComponent
                component={component}
                isSelected={selectedComponentId === component.id}
                onSelect={() => editorState.selectComponent(component.id)}
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
          ))
        )}
      </div>
    </div>
  );
}
