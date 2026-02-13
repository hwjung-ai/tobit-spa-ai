"use client";

import React, { useState, useMemo } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { COMPONENT_REGISTRY } from "@/lib/ui-screen/component-registry";
import { Input } from "@/components/ui/input";
import { Component, ComponentType } from "@/lib/ui-screen/screen.schema";
import { GripVertical } from "lucide-react";

// Container types that can have children
const CONTAINER_TYPES = new Set(["row", "column", "modal", "form"]);

// Drag data type identifier
export const PALETTE_DRAG_TYPE = "application/x-component-type";

// Helper to find component by ID (including nested)
function findComponentById(components: Component[], id: string): Component | null {
  for (const c of components) {
    if (c.id === id) return c;
    const nested = c.props?.components as Component[] | undefined;
    if (nested && Array.isArray(nested)) {
      const found = findComponentById(nested, id);
      if (found) return found;
    }
  }
  return null;
}

export default function ComponentPalette() {
  const editorState = useEditorState();
  const [searchTerm, setSearchTerm] = useState("");
  const [draggingType, setDraggingType] = useState<string | null>(null);

  const filteredComponents = COMPONENT_REGISTRY.filter((desc) => {
    if (!searchTerm) return true;
    return desc.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      desc.label.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // Check if selected component is a container
  const selectedContainer = useMemo(() => {
    if (!editorState.screen || !editorState.selectedComponentId) return null;
    const component = findComponentById(editorState.screen.components, editorState.selectedComponentId);
    if (component && CONTAINER_TYPES.has(component.type)) {
      return component;
    }
    return null;
  }, [editorState.screen, editorState.selectedComponentId]);

  const handleAddComponent = (type: ComponentType) => {
    if (selectedContainer) {
      // Add to selected container
      editorState.addComponentToParent(type, selectedContainer.id);
    } else {
      // Add to root
      editorState.addComponent(type);
    }
  };

  const handleDragStart = (e: React.DragEvent, type: ComponentType) => {
    e.dataTransfer.setData(PALETTE_DRAG_TYPE, type);
    e.dataTransfer.effectAllowed = "copy";
    setDraggingType(type);
  };

  const handleDragEnd = () => {
    setDraggingType(null);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-3">
        <h3 className="text-sm font-semibold mb-2">Components</h3>
        <Input
          placeholder="Search..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="h-8 text-xs"

          data-testid="palette-search"
        />
      </div>

      {/* Target indicator */}
      {selectedContainer && (
        <div className="border-b px-3 py-2">
          <p className="text-xs">
            Adding to: <span className="font-semibold">{selectedContainer.label || selectedContainer.id}</span>
          </p>
        </div>
      )}

      {/* Component List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredComponents.length === 0 ? (
          <div className="text-xs text-center py-4">
            No components found
          </div>
        ) : (
          filteredComponents.map((desc) => (
            <div
              key={desc.type}
              draggable
              onDragStart={(e) => handleDragStart(e, desc.type as ComponentType)}
              onDragEnd={handleDragEnd}
              onClick={() => handleAddComponent(desc.type as ComponentType)}
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors text-xs font-medium border cursor-grab active:cursor-grabbing flex items-center gap-2 ${
                draggingType === desc.type ? "opacity-50" : ""
              }`}
              style={Object.assign(
                {},
                draggingType === desc.type ? { borderColor: "rgba(14, 165, 233, 1)" } : { backgroundColor: "var(--surface-elevated)", borderColor: "var(--border)", color: "var(--foreground-secondary)" }
              )}
              data-testid={`palette-component-${desc.type}`}
            >
              <GripVertical className="w-3 h-3 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-semibold">{desc.label}</div>
                <div className="text-xs mt-1">{desc.type}</div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Info */}
      <div className="border-t p-3">
        <p className="text-xs">
          {selectedContainer
            ? `Click or drag to add inside ${selectedContainer.type}`
            : "Click or drag to add component"
          }
        </p>
      </div>
    </div>
  );
}
