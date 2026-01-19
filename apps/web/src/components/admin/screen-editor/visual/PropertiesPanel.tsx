"use client";

import React, { useState, useMemo } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { generatePropsFormFields } from "@/lib/ui-screen/props-schema-utils";
import { BindingEditor } from "@/components/admin/screen-editor/visual/BindingEditor";
import { ActionEditorModal } from "@/components/admin/screen-editor/actions/ActionEditorModal";
import { extractStatePaths, buildPathTree } from "@/lib/ui-screen/binding-path-utils";
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
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { ComponentActionRef } from "@/lib/ui-screen/screen.schema";
import { Trash2, Plus, Edit2 } from "lucide-react";

export default function PropertiesPanel() {
  const editorState = useEditorState();
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [editingAction, setEditingAction] = useState<ComponentActionRef | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  // Get selected component by finding it in the components array
  const selectedComponent = React.useMemo(() => {
    if (!editorState.screen || !editorState.selectedComponentId) return null;
    return editorState.screen.components.find(c => c.id === editorState.selectedComponentId) || null;
  }, [editorState.screen, editorState.selectedComponentId]);

  // Update form data when component changes
  React.useEffect(() => {
    if (selectedComponent) {
      console.log("[PROPERTIES] Selected component updated:", selectedComponent.id, selectedComponent);
      setFormData(selectedComponent.props || {});
    }
  }, [selectedComponent]);

  // Build path trees for binding editor
  const pathTrees = useMemo(() => {
    if (!editorState.screen?.state) {
      return { stateTree: [], contextTree: [], inputsTree: [] };
    }

    const statePaths = extractStatePaths(editorState.screen.state.schema || {});
    const stateTree = buildPathTree(statePaths);

    return {
      stateTree,
      contextTree: [], // Context paths would be extracted similarly if provided
      inputsTree: [], // Inputs paths would be extracted similarly if provided
    };
  }, [editorState.screen?.state]);

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

        {/* Bindings Section */}
        <Accordion type="single" collapsible>
          <AccordionItem value="bindings">
            <AccordionTrigger className="text-xs font-semibold text-slate-300">
              Bindings
            </AccordionTrigger>
            <AccordionContent className="space-y-3 pt-3">
              {fields.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No bindable properties
                </p>
              ) : (
                fields.map(field => (
                  <div key={`binding-${field.name}`}>
                    <label className="block text-xs font-medium text-slate-300 mb-2">
                      {field.label || field.name}
                    </label>
                    <BindingEditor
                      value={formData[field.name] || ""}
                      onChange={(value) => handlePropChange(field.name, value)}
                      stateTree={pathTrees.stateTree}
                      contextTree={pathTrees.contextTree}
                      inputsTree={pathTrees.inputsTree}
                      placeholder={`Bind ${field.name}...`}
                      className="text-xs"
                      showModeToggle={true}
                    />
                  </div>
                ))
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Visibility Section */}
        <Accordion type="single" collapsible>
          <AccordionItem value="visibility">
            <AccordionTrigger className="text-xs font-semibold text-slate-300">
              Visibility
            </AccordionTrigger>
            <AccordionContent className="space-y-2 pt-3">
              <label className="block text-xs font-medium text-slate-300 mb-2">
                Show when (optional)
              </label>
              <BindingEditor
                value={selectedComponent.visibility?.rule || ""}
                onChange={(value) => editorState.updateComponentVisibility(selectedComponent.id, value || null)}
                stateTree={pathTrees.stateTree}
                contextTree={pathTrees.contextTree}
                inputsTree={pathTrees.inputsTree}
                placeholder="Select visibility condition..."
                className="text-xs"
                showModeToggle={false}
              />
              <p className="text-xs text-slate-500">
                Component will be hidden if condition is empty or false
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        {/* Actions Section */}
        <Accordion type="single" collapsible>
          <AccordionItem value="actions">
            <AccordionTrigger className="text-xs font-semibold text-slate-300">
              Actions ({selectedComponent.actions?.length || 0})
            </AccordionTrigger>
            <AccordionContent className="space-y-2 pt-3">
              {!selectedComponent.actions || selectedComponent.actions.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No actions defined. Click "Add Action" to create one.
                </p>
              ) : (
                <div className="space-y-1">
                  {selectedComponent.actions.map((action) => (
                    <div
                      key={action.id}
                      className="flex items-center justify-between p-2 rounded bg-slate-800 border border-slate-700"
                    >
                      <div className="flex-1">
                        <p className="text-xs font-medium text-slate-200">
                          {action.label || action.id}
                        </p>
                        <p className="text-xs text-slate-400">
                          {action.handler}
                        </p>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingAction(action);
                            setActionModalOpen(true);
                          }}
                          className="h-6 px-2 text-xs text-blue-400 hover:text-blue-300 hover:bg-slate-700"
                        >
                          <Edit2 className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            editorState.deleteComponentAction(selectedComponent.id, action.id);
                          }}
                          className="h-6 px-2 text-xs text-red-400 hover:text-red-300 hover:bg-slate-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <Button
                onClick={() => {
                  setEditingAction(null);
                  setActionModalOpen(true);
                }}
                variant="outline"
                size="sm"
                className="w-full h-8 text-xs mt-2"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add Action
              </Button>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      {/* Component-level Actions */}
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
          onClick={() => setConfirmDeleteOpen(true)}
          variant="destructive"
          size="sm"
          className="w-full text-xs"
          data-testid="btn-delete"
        >
          Delete
        </Button>
        <ConfirmDialog
          open={confirmDeleteOpen}
          onOpenChange={setConfirmDeleteOpen}
          title="Delete component"
          description={`Delete ${selectedComponent.label || selectedComponent.id}? This action cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={() => {
            editorState.deleteComponent(selectedComponent.id);
            editorState.selectComponent(null);
          }}
        />
      </div>

      {/* Action Editor Modal */}
      <ActionEditorModal
        open={actionModalOpen}
        onOpenChange={setActionModalOpen}
        action={editingAction}
        actionType="component"
        onSave={(action) => {
          if (editingAction) {
            editorState.updateComponentAction(selectedComponent.id, editingAction.id, action as any);
          } else {
            editorState.addComponentAction(selectedComponent.id, action as ComponentActionRef);
          }
          setEditingAction(null);
        }}
        stateTree={pathTrees.stateTree}
        contextTree={pathTrees.contextTree}
        inputsTree={pathTrees.inputsTree}
      />
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
