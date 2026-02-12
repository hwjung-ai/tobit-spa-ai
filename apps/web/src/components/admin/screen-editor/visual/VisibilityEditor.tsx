"use client";

import React from "react";
import { BindingEditor, type PathTreeNode } from "@/components/admin/screen-editor/visual/BindingEditor";

interface VisibilityEditorProps {
  value?: string | null;
  onChange: (value: string | null) => void;
  stateTree?: PathTreeNode[];
  contextTree?: PathTreeNode[];
  inputsTree?: PathTreeNode[];
  className?: string;
}

/**
 * VisibilityEditor Component
 *
 * Specialized binding editor for component visibility rules.
 * Allows selection of a binding expression that evaluates to a boolean.
 *
 * The component will be:
 * - Visible if the binding evaluates to true
 * - Hidden if the binding evaluates to false or if the value is empty
 *
 * Used by: PropertiesPanel (Visibility section)
 *
 * @param value - Current visibility rule (binding expression or null)
 * @param onChange - Callback when rule changes
 * @param stateTree - Hierarchical state paths
 * @param contextTree - Hierarchical context paths
 * @param inputsTree - Hierarchical inputs paths
 * @param className - Additional CSS classes
 */
export const VisibilityEditor = React.forwardRef<HTMLDivElement, VisibilityEditorProps>(
  (
    {
      value = null,
      onChange,
      stateTree = [],
      contextTree = [],
      inputsTree = [],
      className = "",
    },
    ref
  ) => {
    return (
      <div ref={ref} className={`space-y-2 ${className}`}>
        <BindingEditor
          value={value || ""}
          onChange={(val) => onChange(val || null)}
          stateTree={stateTree}
          contextTree={contextTree}
          inputsTree={inputsTree}
          placeholder="Select binding or leave empty to always show..."
          className="text-xs"
          showModeToggle={false}
        />
        <div className="text-xs text-slate-500 space-y-1">
          <p>• Component is <strong>visible</strong> when binding is true</p>
          <p>• Component is <strong>hidden</strong> when binding is false or empty</p>
          <p>• Example: {`{{state.show_modal}}`} shows component only if state.show_modal is true</p>
        </div>
      </div>
    );
  }
);

VisibilityEditor.displayName = "VisibilityEditor";
