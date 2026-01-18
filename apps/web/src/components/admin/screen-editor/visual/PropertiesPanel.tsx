"use client";

import React, { useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { generatePropsFormFields } from "@/lib/ui-screen/props-schema-utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function PropertiesPanel() {
  const editorState = useEditorState();
  const { selectedComponent } = editorState;
  const [formData, setFormData] = useState<Record<string, any>>({});

  // Update form data when component changes
  React.useEffect(() => {
    if (selectedComponent) {
      setFormData(selectedComponent.props || {});
    }
  }, [selectedComponent]);

  if (!selectedComponent) {
    return (
      <div className="flex flex-col h-full bg-slate-900/50 items-center justify-center">
        <p className="text-slate-400 text-sm">Select a component to edit</p>
      </div>
    );
  }

  const fields = generatePropsFormFields(selectedComponent.type);

  const handlePropChange = (name: string, value: any) => {
    const newData = { ...formData, [name]: value };
    setFormData(newData);
    editorState.updateComponentProps(selectedComponent.id, newData);
  };

  const handleLabelChange = (value: string) => {
    editorState.updateComponentLabel(selectedComponent.id, value);
  };

  const handleDuplicate = () => {
    const idx = editorState.screen?.components.findIndex(c => c.id === selectedComponent.id) ?? -1;
    if (idx >= 0) {
      editorState.addComponent(selectedComponent.type, idx + 1);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50">
      {/* Header */}
      <div className="border-b border-slate-800 p-3">
        <h3 className="text-sm font-semibold text-slate-200 truncate">
          Properties
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          {selectedComponent.type}
        </p>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Component Label */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Label
          </label>
          <Input
            value={selectedComponent.label || ""}
            onChange={e => handleLabelChange(e.target.value)}
            placeholder="Component label"
            className="h-8 text-xs bg-slate-800 border-slate-700"
            data-testid="prop-label"
          />
        </div>

        {/* Component ID (Read-only) */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Component ID
          </label>
          <div className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-400 font-mono">
            {selectedComponent.id}
          </div>
        </div>

        {/* Props */}
        {fields.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-4">
            No properties available
          </div>
        ) : (
          fields.map(field => (
            <PropsFormField
              key={field.name}
              field={field}
              value={formData[field.name]}
              onChange={(value) => handlePropChange(field.name, value)}
            />
          ))
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-slate-800 p-3 space-y-2">
        <Button
          onClick={handleDuplicate}
          variant="outline"
          size="sm"
          className="w-full text-xs"
          data-testid="btn-duplicate"
        >
          Duplicate
        </Button>

        <Button
          onClick={() => {
            if (confirm("Delete this component?")) {
              editorState.deleteComponent(selectedComponent.id);
              editorState.selectComponent(null);
            }
          }}
          variant="destructive"
          size="sm"
          className="w-full text-xs"
          data-testid="btn-delete"
        >
          Delete
        </Button>
      </div>
    </div>
  );
}

interface PropsFormFieldProps {
  field: any;
  value: any;
  onChange: (value: any) => void;
}

function PropsFormField({ field, value, onChange }: PropsFormFieldProps) {
  if (field.type === "boolean") {
    return (
      <div>
        <label className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={value || false}
            onChange={e => onChange(e.target.checked)}
            className="rounded"
            data-testid={`prop-${field.name}`}
          />
          {field.label || field.name}
        </label>
      </div>
    );
  }

  if (field.type === "select" && field.options) {
    return (
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1">
          {field.label || field.name}
        </label>
        <Select value={value || ""} onValueChange={onChange}>
          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700" data-testid={`prop-${field.name}`}>
            <SelectValue placeholder="Select..." />
          </SelectTrigger>
          <SelectContent>
            {field.options.map((opt: any) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (field.type === "textarea") {
    return (
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1">
          {field.label || field.name}
        </label>
        <Textarea
          value={value || ""}
          onChange={e => onChange(e.target.value)}
          placeholder={field.placeholder || ""}
          className="min-h-16 text-xs bg-slate-800 border-slate-700 resize-none"
          data-testid={`prop-${field.name}`}
        />
      </div>
    );
  }

  if (field.type === "number") {
    return (
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1">
          {field.label || field.name}
        </label>
        <Input
          type="number"
          value={value || ""}
          onChange={e => onChange(e.target.value ? Number(e.target.value) : "")}
          placeholder={field.placeholder || ""}
          className="h-8 text-xs bg-slate-800 border-slate-700"
          min={field.min}
          max={field.max}
          data-testid={`prop-${field.name}`}
        />
      </div>
    );
  }

  // Default: text input
  return (
    <div>
      <label className="block text-xs font-medium text-slate-300 mb-1">
        {field.label || field.name}
      </label>
      <Input
        value={value || ""}
        onChange={e => onChange(e.target.value)}
        placeholder={field.placeholder || ""}
        className="h-8 text-xs bg-slate-800 border-slate-700"
        data-testid={`prop-${field.name}`}
      />
    </div>
  );
}
