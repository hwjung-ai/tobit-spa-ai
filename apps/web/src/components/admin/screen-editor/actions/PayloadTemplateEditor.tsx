"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BindingEditor, type PathTreeNode } from "@/components/admin/screen-editor/visual/BindingEditor";
import { Trash2, Plus } from "lucide-react";

interface PayloadField {
  key: string;
  value: string;
  isBinding: boolean;
}

interface PayloadTemplateEditorProps {
  template?: Record<string, unknown>;
  onChange: (template: Record<string, unknown>) => void;
  stateTree?: PathTreeNode[];
  contextTree?: PathTreeNode[];
  inputsTree?: PathTreeNode[];
  placeholder?: string;
  className?: string;
}

/**
 * PayloadTemplateEditor Component
 *
 * Provides UI for editing action payload templates as key-value pairs.
 * Each value can be either:
 * - A static literal value (string, number, boolean, etc.)
 * - A binding expression ({{state.x}}, {{context.y}}, etc.)
 *
 * Used by: ActionEditorModal (for action payload_template field)
 *
 * @param template - Current payload template object
 * @param onChange - Callback when template changes
 * @param stateTree - Hierarchical state paths for binding editor
 * @param contextTree - Hierarchical context paths
 * @param inputsTree - Hierarchical inputs paths
 * @param placeholder - Placeholder text
 * @param className - Additional CSS classes
 */
export const PayloadTemplateEditor = React.forwardRef<
  HTMLDivElement,
  PayloadTemplateEditorProps
>(
    (
    {
      template = {},
      onChange,
      stateTree = [],
      contextTree = [],
      inputsTree = [],
      className = "",
    },
    ref
  ) => {
    // Initialize fields from template
    const [fields, setFields] = useState<PayloadField[]>(() => {
      return Object.entries(template).map(([key, value]) => ({
        key,
        value: typeof value === "string" ? value : JSON.stringify(value),
        isBinding: typeof value === "string" && value.startsWith("{{"),
      }));
    });

    // Update template whenever fields change
    const updateTemplate = (newFields: PayloadField[]) => {
      setFields(newFields);
      const newTemplate: Record<string, unknown> = {};
      newFields.forEach((field) => {
        if (field.key) {
          newTemplate[field.key] = field.value;
        }
      });
      onChange(newTemplate);
    };

    const handleKeyChange = (index: number, newKey: string) => {
      const newFields = [...fields];
      newFields[index].key = newKey;
      updateTemplate(newFields);
    };

    const handleValueChange = (index: number, newValue: string) => {
      const newFields = [...fields];
      newFields[index].value = newValue;
      newFields[index].isBinding = newValue.startsWith("{{");
      updateTemplate(newFields);
    };

    const handleAddField = () => {
      const newFields = [
        ...fields,
        { key: "", value: "", isBinding: false },
      ];
      updateTemplate(newFields);
    };

    const handleDeleteField = (index: number) => {
      const newFields = fields.filter((_, i) => i !== index);
      updateTemplate(newFields);
    };

    return (
      <div ref={ref} className={`space-y-3 ${className}`}>
        {/* Instructions */}
        <p className="text-xs">
          Define key-value pairs for the action payload. Values can be static or bound to state/context/inputs.
        </p>

        {/* Fields */}
        <div className="space-y-2 max-h-60 overflow-y-auto border rounded p-3">
          {fields.length === 0 ? (
            <p className="text-xs text-center py-4">
              No fields. Click &quot;Add Field&quot; to get started.
            </p>
          ) : (
            fields.map((field, index) => (
              <div key={index} className="space-y-1 p-2 border rounded">
                {/* Key input */}
                <div>
                  <label className="block text-xs font-medium mb-1">
                    Key
                  </label>
                  <Input
                    value={field.key}
                    onChange={(e) => handleKeyChange(index, e.target.value)}
                    placeholder="e.g., user_id"
                    className="h-7 text-xs"
                  />
                </div>

                {/* Value input/binding editor */}
                <div>
                  <label className="block text-xs font-medium mb-1">
                    Value
                  </label>
                  {field.isBinding || (field.value.startsWith("{{") && field.value.endsWith("}}")) ? (
                    // Binding mode
                    <BindingEditor
                      value={field.value}
                      onChange={(val) => handleValueChange(index, val)}
                      stateTree={stateTree}
                      contextTree={contextTree}
                      inputsTree={inputsTree}
                      placeholder="Select or enter binding..."
                      className="text-xs"
                      showModeToggle={true}
                    />
                  ) : (
                    // Static mode
                    <Input
                      value={field.value}
                      onChange={(e) => handleValueChange(index, e.target.value)}
                      placeholder="e.g., John Doe or {{state.name}}"
                      className="h-7 text-xs"
                    />
                  )}
                </div>

                {/* Delete button */}
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteField(index)}
                    className="h-6 px-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    Delete
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Add field button */}
        <Button
          onClick={handleAddField}
          variant="outline"
          size="sm"
          className="w-full h-8 text-xs"
        >
          <Plus className="w-3 h-3 mr-1" />
          Add Field
        </Button>

        {/* JSON preview */}
        <details className="text-xs">
          <summary className="cursor-pointer font-medium">
            View as JSON
          </summary>
          <pre className="mt-2 p-2 rounded text-xs overflow-x-auto">
            {JSON.stringify(
              fields.reduce((acc, field) => {
                if (field.key) {
                  acc[field.key] = field.value;
                }
                return acc;
              }, {} as Record<string, unknown>),
              null,
              2
            )}
          </pre>
        </details>
      </div>
    );
  }
);

PayloadTemplateEditor.displayName = "PayloadTemplateEditor";
