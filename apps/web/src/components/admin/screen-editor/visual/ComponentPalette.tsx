"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { COMPONENT_REGISTRY } from "@/lib/ui-screen/component-registry";
import { Input } from "@/components/ui/input";

export default function ComponentPalette() {
  const editorState = useEditorState();
  const [searchTerm, setSearchTerm] = useState("");

  const filteredComponents = COMPONENT_REGISTRY.filter((desc) => {
    if (!searchTerm) return true;
    return desc.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      desc.label.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const handleAddComponent = (type: string) => {
    editorState.addComponent(type);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* Header */}
      <div className="border-b border-slate-800 p-3">
        <h3 className="text-sm font-semibold text-slate-200 mb-2">Components</h3>
        <Input
          placeholder="Search..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="h-8 text-xs bg-slate-800 border-slate-700"
          data-testid="palette-search"
        />
      </div>

      {/* Component List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredComponents.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-4">
            No components found
          </div>
        ) : (
          filteredComponents.map((desc) => (
            <button
              key={desc.type}
              onClick={() => handleAddComponent(desc.type)}
              className="w-full text-left px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors text-xs font-medium text-slate-200 border border-slate-700 hover:border-slate-600"
              data-testid={`palette-component-${desc.type}`}
            >
              <div className="font-semibold">{desc.label}</div>
              <div className="text-slate-400 text-[10px] mt-1">{desc.type}</div>
            </button>
          ))
        )}
      </div>

      {/* Info */}
      <div className="border-t border-slate-800 p-3">
        <p className="text-[10px] text-slate-500">
          Click to add component
        </p>
      </div>
    </div>
  );
}
