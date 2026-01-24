"use client";

import React, { useState, useMemo } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { generatePropsFormFields, type PropsFormField as PropsFormFieldSchema } from "@/lib/ui-screen/props-schema-utils";
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
import { ComponentActionRef, ScreenSchemaV1 } from "@/lib/ui-screen/screen.schema";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PathPicker, type PathTreeNode } from "@/components/admin/screen-editor/common/PathPicker";
import { validateBindingPath } from "@/lib/ui-screen/validation-utils";
import { Trash2, Plus, Edit2 } from "lucide-react";
import { Component } from "@/lib/ui-screen/screen.schema";

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

export default function PropertiesPanel() {
  const editorState = useEditorState();
  const displayScreen = editorState.screen;
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [editingAction, setEditingAction] = useState<ComponentActionRef | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  // Get selected component by finding it in the components array (including nested)
  const selectedComponent = React.useMemo(() => {
    if (!displayScreen || !editorState.selectedComponentId) return null;
    return findComponentById(displayScreen.components, editorState.selectedComponentId);
  }, [displayScreen, editorState.selectedComponentId]);

  // Update form data when component changes
  React.useEffect(() => {
    if (selectedComponent) {
      console.log("[PROPERTIES] Selected component updated:", selectedComponent.id, selectedComponent);
      setFormData(selectedComponent.props || {});
    }
  }, [selectedComponent]);

  // Build path trees for binding editor
  const pathTrees = useMemo(() => {
    if (!displayScreen?.state) {
      return { stateTree: [], contextTree: [], inputsTree: [] };
    }

    const statePaths = extractStatePaths(displayScreen.state.schema || {});
    const stateTree = buildPathTree(statePaths);

    return {
      stateTree,
      contextTree: [], // Context paths would be extracted similarly if provided
      inputsTree: [], // Inputs paths would be extracted similarly if provided
    };
  }, [displayScreen]);

  if (!selectedComponent) {
    return (
      <div className="flex flex-col h-full bg-slate-900/50 items-center justify-center">
        <p className="text-slate-400 text-sm">Select a component to edit</p>
      </div>
    );
  }

  const fields = generatePropsFormFields(selectedComponent.type);
  const normalizedType = (selectedComponent.type || "").toLowerCase();
  const isTextComponent = TEXT_COMPONENT_TYPES.has(normalizedType);
  const isTextField = (name: string) => isTextComponent && TEXT_PROPERTY_FIELDS.has(name);
  const bindableFields = fields.filter(field => !isTextField(field.name));

  const handlePropChange = (name: string, value: unknown) => {
    const newData = { ...formData, [name]: value };
    setFormData(newData);
    editorState.updateComponentProps(selectedComponent.id, newData);
  };

  const handleLabelChange = (value: string) => {
    editorState.updateComponentLabel(selectedComponent.id, value);
  };

  const handleDuplicate = () => {
    const idx = displayScreen?.components.findIndex(c => c.id === selectedComponent.id) ?? -1;
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
            isTextField(field.name) ? (
              <TextPropertyField
                key={field.name}
                field={field}
                value={formData[field.name]}
                onChange={(value) => handlePropChange(field.name, value)}
                bindingTrees={pathTrees}
                screenSchema={displayScreen}
              />
            ) : (
              <PropsFormField
                key={field.name}
                field={field}
                value={formData[field.name]}
                onChange={(value) => handlePropChange(field.name, value)}
              />
            )
          ))
        )}

        {/* Bindings Section */}
        <Accordion type="single" collapsible>
          <AccordionItem value="bindings">
            <AccordionTrigger className="text-xs font-semibold text-slate-300">
              Bindings
            </AccordionTrigger>
            <AccordionContent className="space-y-3 pt-3">
              {bindableFields.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No bindable properties
                </p>
              ) : (
                bindableFields.map(field => (
                  <div key={`binding-${field.name}`}>
                    <label className="block text-xs font-medium text-slate-300 mb-2">
                      {field.label || field.name}
                    </label>
                     <BindingEditor
                       value={(formData[field.name] as string | undefined) ?? ""}
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
                  No actions defined. Click &quot;Add Action&quot; to create one.
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
            editorState.updateComponentAction(selectedComponent.id, editingAction.id, action as ComponentActionRef);
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
  field: PropsFormFieldSchema;
  value: unknown;
  onChange: (value: unknown) => void;
}

function PropsFormField({ field, value, onChange }: PropsFormFieldProps) {
  if (field.type === "boolean") {
    return (
      <div>
        <label className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={(value as boolean) || false}
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
        <Select value={typeof value === "string" ? value : ""} onValueChange={(val) => onChange(val)}>
          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700" data-testid={`prop-${field.name}`}>
            <SelectValue placeholder="Select..." />
          </SelectTrigger>
          <SelectContent>
            {field.options.map((opt) => (
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
          value={(value as string) || ""}
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
          value={(value as string | number) || ""}
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
        value={(value as string) || ""}
        onChange={e => onChange(e.target.value)}
        placeholder={field.placeholder || ""}
        className="h-8 text-xs bg-slate-800 border-slate-700"
        data-testid={`prop-${field.name}`}
      />
    </div>
  );
}

interface BindingTrees {
  stateTree: PathTreeNode[];
  contextTree: PathTreeNode[];
  inputsTree: PathTreeNode[];
}

function TextPropertyField({
  field,
  value,
  onChange,
  bindingTrees,
  screenSchema,
}: {
  field: PropsFormFieldSchema;
  value: unknown;
  onChange: (value: string) => void;
  bindingTrees: BindingTrees;
  screenSchema: ScreenSchemaV1 | null;
}) {
  const description =
    field.description ||
    (field.name === "variant"
      ? "Variant is a design token (heading, label, body, caption)."
      : field.name === "color"
        ? "Color is a design token (default, primary, muted, danger)."
        : undefined);

  const renderStatic = (staticValue: string, handleStaticChange: (val: string) => void) => {
    if (field.name === "content") {
      return (
        <Textarea
          value={staticValue}
          onChange={(e) => handleStaticChange(e.target.value)}
          placeholder={field.placeholder || "Enter text..."}
          className="min-h-16 text-xs bg-slate-800 border-slate-700 resize-none"
        />
      );
    }

    if (field.name === "variant") {
      return (
        <Select value={staticValue || ""} onValueChange={(val) => handleStaticChange(val)}>
          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
            <SelectValue placeholder="Select variant" />
          </SelectTrigger>
          <SelectContent>
            {TEXT_VARIANT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }

    if (field.name === "color") {
      return (
        <Select value={staticValue || ""} onValueChange={(val) => handleStaticChange(val)}>
          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
            <SelectValue placeholder="Select color" />
          </SelectTrigger>
          <SelectContent>
            {TEXT_COLOR_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }

    return (
      <Input
        value={staticValue}
        onChange={(e) => handleStaticChange(e.target.value)}
        placeholder={field.placeholder || ""}
        className="h-8 text-xs bg-slate-800 border-slate-700"
      />
    );
  };

  return (
    <FieldBindingControl
      label={field.label || field.name}
      description={description}
      value={value}
      onChange={onChange}
      bindingTrees={bindingTrees}
      screenSchema={screenSchema}
      renderStaticInput={renderStatic}
    />
  );
}

const TEXT_COMPONENT_TYPES = new Set(["text", "markdown"]);
const TEXT_PROPERTY_FIELDS = new Set(["content", "variant", "color"]);
const TEXT_VARIANT_OPTIONS = [
  { value: "heading", label: "Heading" },
  { value: "label", label: "Label" },
  { value: "body", label: "Body" },
  { value: "caption", label: "Caption" },
];
const TEXT_COLOR_OPTIONS = [
  { value: "default", label: "Default" },
  { value: "primary", label: "Primary" },
  { value: "muted", label: "Muted" },
  { value: "danger", label: "Danger" },
];

function FieldBindingControl({
  label,
  description,
  value,
  onChange,
  bindingTrees,
  screenSchema,
  renderStaticInput,
}: {
  label: string;
  description?: string;
  value?: string;
  onChange: (value: string) => void;
  bindingTrees: BindingTrees;
  screenSchema: ScreenSchemaV1 | null;
  renderStaticInput: (value: string, onChange: (val: string) => void) => React.ReactNode;
}) {
  const normalizedValue = typeof value === "string" ? value : String(value || "");
  const [mode, setMode] = useState<"binding" | "static">(isBindingExpression(normalizedValue) ? "binding" : "static");
  const [staticValue, setStaticValue] = useState<string>(isBindingExpression(normalizedValue) ? "" : normalizedValue);
  const [bindingValue, setBindingValue] = useState<string>(normalizedValue);

  React.useEffect(() => {
    setBindingValue(normalizedValue);
    if (isBindingExpression(normalizedValue)) {
      setMode("binding");
    } else {
      setMode("static");
      setStaticValue(normalizedValue);
    }
  }, [normalizedValue]);

  const handleStaticChange = (next: string) => {
    setStaticValue(next);
    setMode("static");
    onChange(next);
  };

  const handleBindingChange = (next: string) => {
    setBindingValue(next);
    setMode("binding");
    onChange(next);
  };

  const bindingError = React.useMemo(() => {
    if (mode !== "binding" || !bindingValue) return "";
    const errors = validateBindingPath(bindingValue, screenSchema);
    return errors.length ? errors[0].message : "";
  }, [bindingValue, mode, screenSchema]);

  const prefixOptions = [
    { label: "state", value: "state" },
    { label: "inputs", value: "inputs" },
    { label: "context", value: "context" },
    { label: "trace_id", value: "trace_id" },
  ];

  const handlePrefixInsert = (source: string) => {
    const payload = source === "trace_id" ? "{{trace_id}}" : `{{${source}}}`;
    handleBindingChange(payload);
  };

  return (
    <div className="space-y-2 rounded border border-slate-800 bg-slate-900/60 p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-300">{label}</p>
          {description && (
            <p className="text-[10px] text-slate-500">
              {description}
            </p>
          )}
        </div>
        <span className="text-[10px] uppercase tracking-[0.4em] text-slate-400">
          {mode === "binding" ? "Binding" : "Static"}
        </span>
      </div>
      <Tabs value={mode} onValueChange={(val) => setMode(val as "binding" | "static")}>
        <TabsList className="grid grid-cols-2 gap-2">
          <TabsTrigger className="h-8 text-[10px] uppercase tracking-[0.1em] px-2" value="static">
            Static
          </TabsTrigger>
          <TabsTrigger className="h-8 text-[10px] uppercase tracking-[0.1em] px-2" value="binding">
            Binding
          </TabsTrigger>
        </TabsList>
        <TabsContent value="static" className="space-y-2">
          {renderStaticInput(staticValue, handleStaticChange)}
        </TabsContent>
        <TabsContent value="binding" className="space-y-2">
          <div className="flex flex-wrap gap-2">
            {prefixOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className="rounded-full border border-slate-700 px-2 py-1 text-[10px] text-slate-200 hover:border-slate-500"
                onClick={() => handlePrefixInsert(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <PathPicker
            value={bindingValue}
            onChange={(val) => handleBindingChange(val)}
            stateTree={bindingTrees.stateTree}
            contextTree={bindingTrees.contextTree}
            inputsTree={bindingTrees.inputsTree}
            placeholder={`Bind ${label.toLowerCase()}...`}
            error={bindingError}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function isBindingExpression(value: string) {
  return value.startsWith("{{") && value.endsWith("}}");
}
