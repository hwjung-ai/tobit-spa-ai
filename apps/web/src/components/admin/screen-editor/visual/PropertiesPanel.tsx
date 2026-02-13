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
import { Trash2, Plus, Edit2, ChevronUp, ChevronDown } from "lucide-react";
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

type AutoRefreshEditorValue = {
  enabled?: boolean;
  interval_ms?: number;
  action_index?: number;
  max_failures?: number;
  backoff_ms?: number;
};

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
  const editorManagedProps = new Set<string>();
  if (normalizedType === "table") {
    editorManagedProps.add("columns");
  }
  if (normalizedType === "chart") {
    editorManagedProps.add("series");
  }
  const renderableFields = fields.filter((field) => !editorManagedProps.has(field.name));
  const bindableFields = renderableFields.filter(field => !isTextField(field.name));
  const actionOptions = selectedComponent.actions || [];
  const rawAutoRefresh = formData.auto_refresh;
  const autoRefresh: AutoRefreshEditorValue =
    rawAutoRefresh && typeof rawAutoRefresh === "object"
      ? (rawAutoRefresh as AutoRefreshEditorValue)
      : {};
  const rawTableColumns = formData.columns;
  const tableColumns = !Array.isArray(rawTableColumns)
    ? ([] as Array<{ field: string; header: string; sortable: boolean; format: string }>)
    : rawTableColumns.map((item) => {
        if (typeof item === "string") {
          return { field: item, header: item, sortable: true, format: "" };
        }
        const obj = (item || {}) as Record<string, unknown>;
        const field = String(obj.field || obj.key || "");
        return {
          field,
          header: String(obj.header || obj.label || field),
          sortable: obj.sortable !== false,
          format: String(obj.format || ""),
        };
      });
  const rawChartSeries = formData.series;
  const chartSeries = !Array.isArray(rawChartSeries)
    ? ([] as Array<{ name: string; data_key: string; color: string }>)
    : rawChartSeries.map((item, index) => {
        const obj = (item || {}) as Record<string, unknown>;
        return {
          name: String(obj.name || `Series ${index + 1}`),
          data_key: String(obj.data_key || obj.dataKey || (index === 0 ? "y" : `y${index + 1}`)),
          color: String(obj.color || obj.stroke || "var(--primary-light)"),
        };
      });
  const rawConditionalStyles = formData.conditional_styles;
  const componentConditionalStyles = !Array.isArray(rawConditionalStyles)
    ? ([] as Array<{
        field: string;
        operator: string;
        value: string;
        color: string;
        bg_color: string;
        border_color: string;
        series_name: string;
        target: string;
        variant: string;
      }>)
    : rawConditionalStyles.map((item) => {
        const obj = (item || {}) as Record<string, unknown>;
        return {
          field: String(obj.field || ""),
          operator: String(obj.operator || "eq"),
          value: String(obj.value ?? ""),
          color: String(obj.color || ""),
          bg_color: String(obj.bg_color || ""),
          border_color: String(obj.border_color || ""),
          series_name: String(obj.series_name || ""),
          target: String(obj.target || "auto"),
          variant: String(obj.variant || ""),
        };
      });

  const handlePropChange = (name: string, value: unknown) => {
    const newData = { ...formData, [name]: value };
    setFormData(newData);
    editorState.updateComponentProps(selectedComponent.id, newData);
  };

  const handleAutoRefreshChange = (
    key: keyof AutoRefreshEditorValue,
    value: boolean | number
  ) => {
    const next: AutoRefreshEditorValue = {
      enabled: autoRefresh.enabled ?? false,
      interval_ms: autoRefresh.interval_ms ?? 30000,
      action_index: autoRefresh.action_index ?? 0,
      max_failures: autoRefresh.max_failures ?? 3,
      backoff_ms: autoRefresh.backoff_ms ?? 10000,
      [key]: value,
    };
    handlePropChange("auto_refresh", next as unknown as Record<string, unknown>);
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
        {renderableFields.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-4">
            No properties available
          </div>
        ) : (
          renderableFields.map(field => (
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

        {normalizedType === "table" && (
          <Accordion type="single" collapsible>
            <AccordionItem value="table-columns">
              <AccordionTrigger className="text-sm font-semibold text-slate-300">
                Table Columns
              </AccordionTrigger>
              <AccordionContent className="space-y-2 pt-3">
                {tableColumns.length === 0 ? (
                  <p className="text-xs text-slate-500">No columns configured.</p>
                ) : (
                  tableColumns.map((column, index) => (
                    <div key={`table-col-${index}`} className="rounded border border-slate-700 bg-slate-800/60 p-2 space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <Input
                          value={column.field}
                          onChange={(e) => {
                            const next = [...tableColumns];
                            next[index] = { ...next[index], field: e.target.value };
                            handlePropChange("columns", next);
                          }}
                          placeholder="field"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                          data-testid={`prop-table-column-field-${index}`}
                        />
                        <Input
                          value={column.header}
                          onChange={(e) => {
                            const next = [...tableColumns];
                            next[index] = { ...next[index], header: e.target.value };
                            handlePropChange("columns", next);
                          }}
                          placeholder="header"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                          data-testid={`prop-table-column-header-${index}`}
                        />
                      </div>
                      <div>
                        <Select
                          value={column.format || "none"}
                          onValueChange={(val) => {
                            const next = [...tableColumns];
                            next[index] = {
                              ...next[index],
                              format: val === "none" ? "" : val,
                            };
                            handlePropChange("columns", next);
                          }}
                        >
                          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
                            <SelectValue placeholder="format" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">No format</SelectItem>
                            <SelectItem value="number">Number</SelectItem>
                            <SelectItem value="percent">Percent</SelectItem>
                            <SelectItem value="date">Date</SelectItem>
                            <SelectItem value="datetime">DateTime</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 text-xs text-slate-300">
                          <input
                            type="checkbox"
                            checked={column.sortable}
                            onChange={(e) => {
                              const next = [...tableColumns];
                              next[index] = { ...next[index], sortable: e.target.checked };
                              handlePropChange("columns", next);
                            }}
                          />
                          sortable
                        </label>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs text-rose-300 hover:text-rose-200"
                          onClick={() => {
                            const next = tableColumns.filter((_, i) => i !== index);
                            handlePropChange("columns", next);
                          }}
                        >
                          Remove
                        </Button>
                      </div>
                    </div>
                  ))
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full h-8 text-xs"
                  onClick={() =>
                    handlePropChange("columns", [
                      ...tableColumns,
                      {
                        field: `field_${tableColumns.length + 1}`,
                        header: `Field ${tableColumns.length + 1}`,
                        sortable: true,
                        format: "",
                      },
                    ])
                  }
                >
                  Add Column
                </Button>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {normalizedType === "chart" && (
          <Accordion type="single" collapsible>
            <AccordionItem value="chart-series">
              <AccordionTrigger className="text-sm font-semibold text-slate-300">
                Chart Behavior
              </AccordionTrigger>
              <AccordionContent className="space-y-2 pt-3">
                <div>
                  <label className="text-xs text-slate-400">Chart Type</label>
                  <Select
                    value={String(formData.chart_type || formData.type || "line")}
                    onValueChange={(val) => {
                      handlePropChange("chart_type", val);
                      handlePropChange("type", val);
                    }}
                  >
                    <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="line">Line</SelectItem>
                      <SelectItem value="bar">Bar</SelectItem>
                      <SelectItem value="pie">Pie</SelectItem>
                      <SelectItem value="area">Area</SelectItem>
                      <SelectItem value="scatter">Scatter</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    value={String(formData.x_key || "")}
                    onChange={(e) => handlePropChange("x_key", e.target.value)}
                    placeholder="x_key (e.g. timestamp)"
                    className="h-8 text-xs bg-slate-800 border-slate-700"
                    data-testid="prop-chart-x-key"
                  />
                  <Input
                    type="number"
                    min={200}
                    max={800}
                    step={10}
                    value={String((formData.height as number) ?? 400)}
                    onChange={(e) => handlePropChange("height", Number(e.target.value || 400))}
                    placeholder="height"
                    className="h-8 text-xs bg-slate-800 border-slate-700"
                    data-testid="prop-chart-height"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={formData.show_legend !== false}
                      onChange={(e) => handlePropChange("show_legend", e.target.checked)}
                    />
                    Show Legend
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={formData.show_grid !== false}
                      onChange={(e) => handlePropChange("show_grid", e.target.checked)}
                    />
                    Show Grid
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={formData.responsive !== false}
                      onChange={(e) => handlePropChange("responsive", e.target.checked)}
                    />
                    Responsive
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    value={String((formData.y_min as number) ?? "")}
                    onChange={(e) =>
                      handlePropChange(
                        "y_min",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                    placeholder="y_min"
                    className="h-8 text-xs bg-slate-800 border-slate-700"
                    data-testid="prop-chart-y-min"
                  />
                  <Input
                    type="number"
                    value={String((formData.y_max as number) ?? "")}
                    onChange={(e) =>
                      handlePropChange(
                        "y_max",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                    placeholder="y_max"
                    className="h-8 text-xs bg-slate-800 border-slate-700"
                    data-testid="prop-chart-y-max"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Y-Axis Options (JSON)</label>
                  <Textarea
                    value={JSON.stringify(formData.y_axis || {}, null, 2)}
                    onChange={(e) => {
                      try {
                        handlePropChange("y_axis", JSON.parse(e.target.value));
                      } catch {
                        // keep previous value until valid JSON
                      }
                    }}
                    placeholder='{"min": 0, "max": 100, "title": "Value"}'
                    className="h-20 text-xs bg-slate-800 border-slate-700 font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Legend Options (JSON)</label>
                  <Textarea
                    value={JSON.stringify(formData.legend || {}, null, 2)}
                    onChange={(e) => {
                      try {
                        handlePropChange("legend", JSON.parse(e.target.value));
                      } catch {
                        // keep previous value until valid JSON
                      }
                    }}
                    placeholder='{"show": true, "position": "right"}'
                    className="h-20 text-xs bg-slate-800 border-slate-700 font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Tooltip Options (JSON)</label>
                  <Textarea
                    value={JSON.stringify(formData.tooltip || {}, null, 2)}
                    onChange={(e) => {
                      try {
                        handlePropChange("tooltip", JSON.parse(e.target.value));
                      } catch {
                        // keep previous value until valid JSON
                      }
                    }}
                    placeholder='{"show": true, "trigger": "axis"}'
                    className="h-20 text-xs bg-slate-800 border-slate-700 font-mono"
                  />
                </div>
                {chartSeries.length === 0 ? (
                  <p className="text-xs text-slate-500">No series configured.</p>
                ) : (
                  chartSeries.map((series, index) => (
                    <div key={`chart-series-${index}`} className="rounded border border-slate-700 bg-slate-800/60 p-2 space-y-2">
                      <div className="grid grid-cols-3 gap-2">
                        <Input
                          value={series.name}
                          onChange={(e) => {
                            const next = [...chartSeries];
                            next[index] = { ...next[index], name: e.target.value };
                            handlePropChange("series", next);
                          }}
                          placeholder="name"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                        <Input
                          value={series.data_key}
                          onChange={(e) => {
                            const next = [...chartSeries];
                            next[index] = { ...next[index], data_key: e.target.value };
                            handlePropChange("series", next);
                          }}
                          placeholder="data_key"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                        <Input
                          value={series.color}
                          onChange={(e) => {
                            const next = [...chartSeries];
                            next[index] = { ...next[index], color: e.target.value };
                            handlePropChange("series", next);
                          }}
                          placeholder="var(--primary-light)"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-rose-300 hover:text-rose-200"
                        onClick={() => {
                          const next = chartSeries.filter((_, i) => i !== index);
                          handlePropChange("series", next);
                        }}
                      >
                        Remove
                      </Button>
                    </div>
                  ))
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full h-8 text-xs"
                  onClick={() =>
                    handlePropChange("series", [
                      ...chartSeries,
                      {
                        name: `Series ${chartSeries.length + 1}`,
                        data_key: chartSeries.length === 0 ? "y" : `y${chartSeries.length + 1}`,
                        color: "#38bdf8",
                      },
                    ])
                  }
                >
                  Add Series
                </Button>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {/* Bindings Section */}
        <Accordion type="single" collapsible>
          <AccordionItem value="bindings">
            <AccordionTrigger className="text-sm font-semibold text-slate-300">
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
            <AccordionTrigger className="text-sm font-semibold text-slate-300">
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
            <AccordionTrigger className="text-sm font-semibold text-slate-300">
              Actions ({selectedComponent.actions?.length || 0})
            </AccordionTrigger>
            <AccordionContent className="space-y-2 pt-3">
              {!selectedComponent.actions || selectedComponent.actions.length === 0 ? (
                <p className="text-xs text-slate-500">
                  No actions defined. Click &quot;Add Action&quot; to create one.
                </p>
              ) : (
                <div className="space-y-1">
                  {selectedComponent.actions.map((action, index) => (
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
                          disabled={index === 0}
                          onClick={() => {
                            editorState.moveComponentAction(
                              selectedComponent.id,
                              action.id,
                              "up"
                            );
                          }}
                          className="h-6 px-2 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700 disabled:opacity-30"
                        >
                          <ChevronUp className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={index === (selectedComponent.actions?.length || 1) - 1}
                          onClick={() => {
                            editorState.moveComponentAction(
                              selectedComponent.id,
                              action.id,
                              "down"
                            );
                          }}
                          className="h-6 px-2 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700 disabled:opacity-30"
                        >
                          <ChevronDown className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingAction(action);
                            setActionModalOpen(true);
                          }}
                          className="h-6 px-2 text-xs text-sky-400 hover:text-sky-300 hover:bg-slate-700"
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

        {/* Auto Refresh Section */}
        {actionOptions.length > 0 && (
          <Accordion type="single" collapsible>
            <AccordionItem value="auto-refresh">
              <AccordionTrigger className="text-sm font-semibold text-slate-300">
                Auto Refresh
              </AccordionTrigger>
              <AccordionContent className="space-y-3 pt-3">
                <label className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefresh.enabled ?? false}
                    onChange={(e) =>
                      handleAutoRefreshChange("enabled", e.target.checked)
                    }
                    className="rounded"
                    data-testid="prop-auto-refresh-enabled"
                  />
                  Enabled
                </label>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Action
                  </label>
                  <Select
                    value={String(autoRefresh.action_index ?? 0)}
                    onValueChange={(val) =>
                      handleAutoRefreshChange("action_index", Number(val))
                    }
                  >
                    <SelectTrigger
                      className="h-8 text-xs bg-slate-800 border-slate-700"
                      data-testid="prop-auto-refresh-action-index"
                    >
                      <SelectValue placeholder="Select action" />
                    </SelectTrigger>
                    <SelectContent>
                      {actionOptions.map((action, index) => (
                        <SelectItem key={`${action.id}-${index}`} value={String(index)}>
                          {(action.label || action.id) + " · " + action.handler}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Interval (ms)
                  </label>
                  <Input
                    type="number"
                    min={1000}
                    value={String(autoRefresh.interval_ms ?? 30000)}
                    onChange={(e) =>
                      handleAutoRefreshChange(
                        "interval_ms",
                        Number(e.target.value || 30000)
                      )
                    }
                    className="h-8 text-xs bg-slate-800 border-slate-700"
                    data-testid="prop-auto-refresh-interval-ms"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Max Failures
                    </label>
                    <Input
                      type="number"
                      min={1}
                      value={String(autoRefresh.max_failures ?? 3)}
                      onChange={(e) =>
                        handleAutoRefreshChange(
                          "max_failures",
                          Number(e.target.value || 3)
                        )
                      }
                      className="h-8 text-xs bg-slate-800 border-slate-700"
                      data-testid="prop-auto-refresh-max-failures"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Backoff (ms)
                    </label>
                    <Input
                      type="number"
                      min={0}
                      value={String(autoRefresh.backoff_ms ?? 10000)}
                      onChange={(e) =>
                        handleAutoRefreshChange(
                          "backoff_ms",
                          Number(e.target.value || 0)
                        )
                      }
                      className="h-8 text-xs bg-slate-800 border-slate-700"
                      data-testid="prop-auto-refresh-backoff-ms"
                    />
                  </div>
                </div>
                <p className="text-xs text-slate-500">
                  Runtime executes selected action periodically with backoff and failure stop.
                </p>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {/* Table Behavior Section */}
        {normalizedType === "table" && actionOptions.length > 0 && (
          <Accordion type="single" collapsible>
            <AccordionItem value="table-behavior">
              <AccordionTrigger className="text-sm font-semibold text-slate-300">
                Table Behavior
              </AccordionTrigger>
              <AccordionContent className="space-y-3 pt-3">
                <label className="flex items-center gap-2 text-xs font-medium text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.sortable !== false}
                    onChange={(e) => handlePropChange("sortable", e.target.checked)}
                    className="rounded"
                    data-testid="prop-table-sortable"
                  />
                  Sortable
                </label>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Page Size (0 = off)
                  </label>
                  <Input
                    type="number"
                    min={0}
                    value={String((formData.page_size as number) ?? 0)}
                    onChange={(e) =>
                      handlePropChange("page_size", Number(e.target.value || 0))
                    }
                    className="h-8 text-xs bg-slate-800 border-slate-700"
                    data-testid="prop-table-page-size"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Row Click Action
                  </label>
                  <Select
                    value={String((formData.row_click_action_index as number) ?? -1)}
                    onValueChange={(val) =>
                      handlePropChange("row_click_action_index", Number(val))
                    }
                  >
                    <SelectTrigger
                      className="h-8 text-xs bg-slate-800 border-slate-700"
                      data-testid="prop-table-row-action-index"
                    >
                      <SelectValue placeholder="Select action" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="-1">No Action</SelectItem>
                      {actionOptions.map((action, index) => (
                        <SelectItem key={`${action.id}-${index}`} value={String(index)}>
                          {(action.label || action.id) + " · " + action.handler}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        {(normalizedType === "table" || normalizedType === "chart" || normalizedType === "badge") && (
          <Accordion type="single" collapsible>
            <AccordionItem value="component-conditional-styles">
              <AccordionTrigger className="text-sm font-semibold text-slate-300">
                Conditional Styles
              </AccordionTrigger>
              <AccordionContent className="space-y-2 pt-3">
                {componentConditionalStyles.length === 0 ? (
                  <p className="text-xs text-slate-500">No rules configured.</p>
                ) : (
                  componentConditionalStyles.map((rule, index) => (
                    <div
                      key={`component-style-rule-${index}`}
                      className="rounded border border-slate-700 bg-slate-800/60 p-2 space-y-2"
                    >
                      <div className={normalizedType === "chart" ? "grid grid-cols-3 gap-2" : "grid grid-cols-2 gap-2"}>
                        <Input
                          value={rule.field}
                          onChange={(e) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], field: e.target.value };
                            handlePropChange("conditional_styles", next);
                          }}
                          placeholder="field"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                        <Select
                          value={rule.operator}
                          onValueChange={(val) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], operator: val };
                            handlePropChange("conditional_styles", next);
                          }}
                        >
                          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
                            <SelectValue placeholder="operator" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="eq">eq</SelectItem>
                            <SelectItem value="ne">ne</SelectItem>
                            <SelectItem value="gt">gt</SelectItem>
                            <SelectItem value="gte">gte</SelectItem>
                            <SelectItem value="lt">lt</SelectItem>
                            <SelectItem value="lte">lte</SelectItem>
                            <SelectItem value="contains">contains</SelectItem>
                          </SelectContent>
                        </Select>
                        {normalizedType === "chart" && (
                          <Input
                            value={rule.series_name}
                            onChange={(e) => {
                              const next = [...componentConditionalStyles];
                              next[index] = { ...next[index], series_name: e.target.value };
                              handlePropChange("conditional_styles", next);
                            }}
                            placeholder="series (optional)"
                            className="h-8 text-xs bg-slate-800 border-slate-700"
                          />
                        )}
                      </div>
                      {normalizedType === "chart" && (
                        <div className="grid grid-cols-1 gap-2">
                          <Select
                            value={rule.target || "auto"}
                            onValueChange={(val) => {
                              const next = [...componentConditionalStyles];
                              next[index] = { ...next[index], target: val };
                              handlePropChange("conditional_styles", next);
                            }}
                          >
                            <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
                              <SelectValue placeholder="target" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="auto">target: auto</SelectItem>
                              <SelectItem value="line">target: line</SelectItem>
                              <SelectItem value="area">target: area</SelectItem>
                              <SelectItem value="point">target: point</SelectItem>
                              <SelectItem value="bar">target: bar</SelectItem>
                              <SelectItem value="pie">target: pie</SelectItem>
                              <SelectItem value="scatter">target: scatter</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                      <div className="grid grid-cols-4 gap-2">
                        <Input
                          value={rule.value}
                          onChange={(e) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], value: e.target.value };
                            handlePropChange("conditional_styles", next);
                          }}
                          placeholder="value"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                        <Input
                          value={rule.color}
                          onChange={(e) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], color: e.target.value };
                            handlePropChange("conditional_styles", next);
                          }}
                          placeholder="#fca5a5"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                        <Input
                          value={rule.bg_color}
                          onChange={(e) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], bg_color: e.target.value };
                            handlePropChange("conditional_styles", next);
                          }}
                          placeholder="#7f1d1d"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                        <Input
                          value={rule.border_color}
                          onChange={(e) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], border_color: e.target.value };
                            handlePropChange("conditional_styles", next);
                          }}
                          placeholder="#ef4444"
                          className="h-8 text-xs bg-slate-800 border-slate-700"
                        />
                      </div>
                      {normalizedType === "badge" && (
                        <Select
                          value={rule.variant || "default"}
                          onValueChange={(val) => {
                            const next = [...componentConditionalStyles];
                            next[index] = { ...next[index], variant: val };
                            handlePropChange("conditional_styles", next);
                          }}
                        >
                          <SelectTrigger className="h-8 text-xs bg-slate-800 border-slate-700">
                            <SelectValue placeholder="variant" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="default">variant: default</SelectItem>
                            <SelectItem value="secondary">variant: secondary</SelectItem>
                            <SelectItem value="success">variant: success</SelectItem>
                            <SelectItem value="warning">variant: warning</SelectItem>
                            <SelectItem value="danger">variant: danger</SelectItem>
                            <SelectItem value="outline">variant: outline</SelectItem>
                            <SelectItem value="ghost">variant: ghost</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-rose-300 hover:text-rose-200"
                        onClick={() => {
                          const next = componentConditionalStyles.filter((_, i) => i !== index);
                          handlePropChange("conditional_styles", next);
                        }}
                      >
                        Remove Rule
                      </Button>
                    </div>
                  ))
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full h-8 text-xs"
                  onClick={() =>
                    handlePropChange("conditional_styles", [
                      ...componentConditionalStyles,
                      {
                        field: "",
                        operator: "eq",
                        value: "",
                        color: "#fca5a5",
                        bg_color: "",
                        border_color: "",
                        series_name: "",
                        target: normalizedType === "chart" ? "auto" : "",
                        variant: normalizedType === "badge" ? "default" : "",
                      },
                    ])
                  }
                >
                  Add Rule
                </Button>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
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
  const [jsonText, setJsonText] = React.useState(() => {
    if (field.type === "array" || field.type === "object") {
      try {
        return JSON.stringify(value ?? (field.type === "array" ? [] : {}), null, 2);
      } catch {
        return field.type === "array" ? "[]" : "{}";
      }
    }
    return "";
  });
  const [jsonError, setJsonError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (field.type === "array" || field.type === "object") {
      try {
        setJsonText(JSON.stringify(value ?? (field.type === "array" ? [] : {}), null, 2));
        setJsonError(null);
      } catch {
        setJsonError("Failed to serialize value");
      }
    }
  }, [field.type, value]);

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

  if (field.type === "array" || field.type === "object") {
    return (
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1">
          {field.label || field.name}
        </label>
        <Textarea
          value={jsonText}
          onChange={e => {
            const next = e.target.value;
            setJsonText(next);
            try {
              const parsed = JSON.parse(next);
              if (field.type === "array" && !Array.isArray(parsed)) {
                setJsonError("Value must be a JSON array");
                return;
              }
              if (field.type === "object" && (Array.isArray(parsed) || parsed === null || typeof parsed !== "object")) {
                setJsonError("Value must be a JSON object");
                return;
              }
              setJsonError(null);
              onChange(parsed);
            } catch {
              setJsonError("Invalid JSON");
            }
          }}
          placeholder={field.type === "array" ? "[]" : "{}"}
          className="min-h-24 text-xs font-mono bg-slate-800 border-slate-700 resize-y"
          data-testid={`prop-${field.name}`}
        />
        {jsonError && (
          <p className="text-xs text-rose-300 mt-1">{jsonError}</p>
        )}
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
      value={String(value ?? "")}
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
        <span className="text-tiny uppercase tracking-wider text-slate-400">
          {mode === "binding" ? "Binding" : "Static"}
        </span>
      </div>
      <Tabs value={mode} onValueChange={(val) => setMode(val as "binding" | "static")}>
        <TabsList className="grid grid-cols-2 gap-2 bg-slate-800/50">
          <TabsTrigger
            className="h-8 text-tiny uppercase tracking-wider px-2 data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200"
            value="static"
          >
            Static
          </TabsTrigger>
          <TabsTrigger
            className="h-8 text-tiny uppercase tracking-wider px-2 data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200"
            value="binding"
          >
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
