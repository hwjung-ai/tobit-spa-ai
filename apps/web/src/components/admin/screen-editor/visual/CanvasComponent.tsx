"use client";

import React, { useState } from "react";
import { Component, ComponentType } from "@/lib/ui-screen/screen.schema";
import { Button } from "@/components/ui/button";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { PALETTE_DRAG_TYPE } from "./ComponentPalette";
import { GripVertical } from "lucide-react";

// Container types that can have children
const CONTAINER_TYPES = new Set(["row", "column", "modal", "form"]);

// Drag type for reordering existing components
export const COMPONENT_DRAG_TYPE = "application/x-component-id";

interface CanvasComponentProps {
  component: Component;
  isSelected: boolean;
  onSelect: () => void;
  depth?: number;
  index?: number;
  parentId?: string | null;
  onReorder?: (dragId: string, dropIndex: number) => void;
  isGridItem?: boolean;
}

export default function CanvasComponent({
  component,
  isSelected,
  onSelect,
  depth = 0,
  index = 0,
  parentId = null,
  onReorder,
  isGridItem = false,
}: CanvasComponentProps) {
  const editorState = useEditorState();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dropPosition, setDropPosition] = useState<"before" | "after" | "inside" | null>(null);

  const isContainer = CONTAINER_TYPES.has(component.type);
  const children = (component.props?.components as Component[]) || [];

  // Determine direction for display
  const isRow = component.type === "row";

  // Handle drag start for reordering
  const handleDragStart = (e: React.DragEvent) => {
    e.stopPropagation();
    e.dataTransfer.setData(COMPONENT_DRAG_TYPE, JSON.stringify({
      id: component.id,
      parentId,
      index,
    }));
    e.dataTransfer.effectAllowed = "move";
    setIsDragging(true);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Check for palette drag (new component)
    if (e.dataTransfer.types.includes(PALETTE_DRAG_TYPE)) {
      if (isContainer) {
        e.dataTransfer.dropEffect = "copy";
        setIsDragOver(true);
        setDropPosition("inside");
      }
      return;
    }

    // Check for component reorder drag
    if (e.dataTransfer.types.includes(COMPONENT_DRAG_TYPE)) {
      e.dataTransfer.dropEffect = "move";

      // Calculate drop position based on mouse position
      const rect = e.currentTarget.getBoundingClientRect();
      const y = e.clientY - rect.top;
      const threshold = rect.height / 3;

      if (isContainer && y > threshold && y < rect.height - threshold) {
        setDropPosition("inside");
      } else if (y < rect.height / 2) {
        setDropPosition("before");
      } else {
        setDropPosition("after");
      }
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.stopPropagation();
    setIsDragOver(false);
    setDropPosition(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    setDropPosition(null);

    // Handle palette drag (new component)
    if (e.dataTransfer.types.includes(PALETTE_DRAG_TYPE)) {
      const componentType = e.dataTransfer.getData(PALETTE_DRAG_TYPE) as ComponentType;
      if (componentType && isContainer) {
        editorState.addComponentToParent(componentType, component.id);
      }
      return;
    }

    // Handle component reorder
    if (e.dataTransfer.types.includes(COMPONENT_DRAG_TYPE)) {
      const dragData = JSON.parse(e.dataTransfer.getData(COMPONENT_DRAG_TYPE));
      if (dragData.id === component.id) return; // Can't drop on self

      const rect = e.currentTarget.getBoundingClientRect();
      const y = e.clientY - rect.top;
      const threshold = rect.height / 3;

      if (isContainer && y > threshold && y < rect.height - threshold) {
        // Drop inside container
        editorState.moveComponentToParent(dragData.id, component.id);
      } else if (onReorder) {
        // Drop before or after
        const dropIdx = y < rect.height / 2 ? index : index + 1;
        onReorder(dragData.id, dropIdx);
      }
    }
  };

  // Get border/background class based on drag state
  const getDragClass = () => {
    if (isGridItem) return "h-full w-full"; // Minimal styling for grid items as container handles it

    if (isDragging) {
      return "opacity-50";
    }
    if (isDragOver) {
      if (dropPosition === "inside") {
        return "border-sky-400 bg-sky-950/50 ring-2 ring-sky-500/30";
      }
      return "border-sky-400";
    }
    if (isSelected) {
      return "border-sky-500 bg-sky-950/30";
    }
    if (isContainer) {
      return "";
    }
    return "";
  };

  return (
    <div className={`relative ${isGridItem ? "h-full w-full" : ""}`}>
      {/* Drop indicator - before */}
      {!isGridItem && isDragOver && dropPosition === "before" && (
        <div className="absolute -top-1 left-0 right-0 h-1 bg-sky-500 rounded-full z-10" />
      )}

      <div
        draggable={!isGridItem}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onClick={(e) => {
          e.stopPropagation();
          if (e.ctrlKey || e.metaKey) {
            editorState.selectComponentToggle(component.id);
          } else if (e.shiftKey) {
            editorState.selectComponentRange(component.id);
          } else {
            onSelect();
          }
        }}
        onDragOver={isGridItem ? undefined : handleDragOver}
        onDragLeave={isGridItem ? undefined : handleDragLeave}
        onDrop={isGridItem ? undefined : handleDrop}
        className={`${isGridItem ? "" : "p-3 rounded-lg border-2 cursor-pointer transition-colors"} ${getDragClass()}`}

        onMouseEnter={(e) => {
          if (isContainer && !isDragging && !isDragOver && !isSelected) {
            e.currentTarget.style.backgroundColor = "var(--surface-base)";
          }
        }}
        onMouseLeave={(e) => {
          if (isContainer && !isDragging && !isDragOver && !isSelected) {
            e.currentTarget.style.backgroundColor = "var(--surface-elevated)";
          }
        }}
        data-testid={`canvas-component-${component.id}`}
      >
        <div className="flex items-start justify-between gap-2">
          {/* Drag handle */}
          {!isGridItem && (
            <div className="flex-shrink-0 cursor-grab active:cursor-grabbing 0 hover: pt-0.5">
              <GripVertical className="w-4 h-4" />
            </div>
          )}

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              {isContainer && (
                <span className="text-[10px] uppercase tracking-wider text-sky-400 bg-sky-950 px-1.5 py-0.5 rounded">
                  {component.type}
                </span>
              )}
              <div className="text-sm font-semibold truncate">
                {component.label || component.id}
              </div>
            </div>
            {!isContainer && (
              <div className="text-xs font-mono">
                {component.type}
              </div>
            )}
            <div className="text-xs 0 mt-1">
              ID: {component.id}
              {isContainer && children.length > 0 && (
                <span className="ml-2">
                  ({children.length} children)
                </span>
              )}
            </div>
          </div>

          {isSelected && (
            <>
              <Button
                size="sm"
                variant="destructive"
                onClick={e => {
                  e.stopPropagation();
                  setConfirmOpen(true);
                }}
                className="h-7 px-2"
                data-testid={`btn-delete-${component.id}`}
              >
                ✕
              </Button>
              <ConfirmDialog
                open={confirmOpen}
                onOpenChange={setConfirmOpen}
                title="Delete component"
                description={`Are you sure you want to delete ${component.label || component.id}?`}
                confirmLabel="Delete"
                onConfirm={() => {
                  editorState.deleteComponent(component.id);
                }}
              />
            </>
          )}
        </div>

        {/* Render children for container components */}
        {isContainer && children.length > 0 && (
          <div
            className={`mt-3 pt-3 border-t  ${isRow ? "flex flex-row gap-2 flex-wrap" : "flex flex-col gap-2"
              }`}
          >
            {children.map((child, childIndex) => (
              <div key={child.id} className={isRow ? "flex-1 min-w-[120px]" : ""}>
                <CanvasComponent
                  component={child}
                  isSelected={editorState.selectedComponentId === child.id}
                  onSelect={() => editorState.selectComponent(child.id)}
                  depth={depth + 1}
                  index={childIndex}
                  parentId={component.id}
                  onReorder={(dragId, dropIndex) =>
                    editorState.reorderComponentAtIndex(dragId, dropIndex, component.id)
                  }
                />
              </div>
            ))}
          </div>
        )}

        {/* Empty container placeholder */}
        {isContainer && children.length === 0 && (
          <div className="mt-3 pt-3 border-t">
            <div className={`text-center py-4 border-2 border-dashed rounded-lg transition-colors ${isDragOver ? "border-sky-500 bg-sky-950/30" : ""
              }`}>
              <p className={`text-xs ${isDragOver ? "text-sky-300" : "0"}`}>
                {isDragOver ? "Drop here to add" : `Drag or click to add components`}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Drop indicator - after */}
      {!isGridItem && isDragOver && dropPosition === "after" && (
        <div className="absolute -bottom-1 left-0 right-0 h-1 bg-sky-500 rounded-full z-10" />
      )}
    </div>
  );
}
