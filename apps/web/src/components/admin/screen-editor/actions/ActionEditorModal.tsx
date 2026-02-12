"use client";

import React, { useState, useEffect } from "react";
import { ScreenAction, ComponentActionRef } from "@/lib/ui-screen/screen.schema";
import { PayloadTemplateEditor } from "@/components/admin/screen-editor/actions/PayloadTemplateEditor";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { PathTreeNode } from "@/components/admin/screen-editor/visual/BindingEditor";
import { useActionCatalog, CatalogItem } from "./useActionCatalog";

export type ActionType = "screen" | "component";

interface ActionTestResult {
  trace_id?: string;
  state_patch?: Record<string, unknown>;
  [key: string]: unknown;
}

interface ActionEditorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  action?: ScreenAction | ComponentActionRef | null;
  actionType?: ActionType;
  onSave: (action: ScreenAction | ComponentActionRef) => void;
  stateTree?: PathTreeNode[];
  contextTree?: PathTreeNode[];
  inputsTree?: PathTreeNode[];
}

const CHAIN_POLICY_PRESETS = [
  {
    id: "strict_stop",
    label: "Strict Stop",
    values: {
      continue_on_error: false,
      stop_on_error: true,
      retry_count: 0,
      retry_delay_ms: 500,
    },
  },
  {
    id: "best_effort",
    label: "Best Effort",
    values: {
      continue_on_error: true,
      stop_on_error: false,
      retry_count: 0,
      retry_delay_ms: 500,
    },
  },
  {
    id: "retry_then_fallback",
    label: "Retry Then Fallback",
    values: {
      continue_on_error: false,
      stop_on_error: true,
      retry_count: 2,
      retry_delay_ms: 1000,
    },
  },
];

function buildTemplateFromSchema(schema?: CatalogItem["input_schema"]): Record<string, unknown> {
  if (!schema || schema.type !== "object" || !schema.properties) {
    return {};
  }

  const template: Record<string, unknown> = {};
  for (const [key, prop] of Object.entries(schema.properties)) {
    if (prop.default !== undefined) {
      template[key] = prop.default;
      continue;
    }
    switch (prop.type) {
      case "boolean":
        template[key] = false;
        break;
      case "integer":
      case "number":
        template[key] = 0;
        break;
      case "array":
        template[key] = [];
        break;
      case "object":
        template[key] = {};
        break;
      default:
        template[key] = "";
    }
  }
  return template;
}

function getMissingRequiredFields(
  schema: CatalogItem["input_schema"] | undefined,
  template: Record<string, unknown> | undefined
): string[] {
  const required = schema?.required || [];
  if (!required.length) return [];

  const payload = template || {};
  return required.filter((field) => {
    const value = payload[field];
    if (value === undefined || value === null) return true;
    if (typeof value === "string" && value.trim() === "") return true;
    return false;
  });
}

/**
 * ActionEditorModal Component
 *
 * Dialog for creating/editing actions (both screen-level and component-level).
 * Uses shared useActionCatalog hook for handler discovery with API Manager integration.
 */
export const ActionEditorModal = React.forwardRef<HTMLDivElement, ActionEditorModalProps>(
  (
    {
      open,
      onOpenChange,
      action = null,
      actionType = "screen",
      onSave,
      stateTree = [],
      contextTree = [],
      inputsTree = [],
    },
    _ref
  ) => {
    void _ref;
    const [formData, setFormData] = useState<ScreenAction | ComponentActionRef>(() => {
      if (action) {
        return { ...action };
      }
      if (actionType === "screen") {
        return {
          id: "",
          handler: "",
          label: "",
          payload_template: {},
          context_required: [],
        } as ScreenAction;
      } else {
        return {
          id: "",
          handler: "",
          label: "",
          payload_template: {},
          continue_on_error: false,
          stop_on_error: true,
          retry_count: 0,
          retry_delay_ms: 500,
          run_if: "",
          on_error_action_index: -1,
          on_error_action_indexes: [],
        } as ComponentActionRef;
      }
    });

    const [isTestingAction, setIsTestingAction] = useState(false);
    const [testResult, setTestResult] = useState<ActionTestResult | null>(null);
    const [testError, setTestError] = useState<string | null>(null);

    // Shared catalog hook
    const {
      builtinOptions,
      apiManagerOptions,
      isLoading: isCatalogLoading,
      error: catalogError,
      findItem,
    } = useActionCatalog(open);

    // Generate action ID if new
    useEffect(() => {
      if (!action && !formData.id) {
        const timestamp = Date.now();
        const newId = `action_${timestamp}`;
        setFormData((prev) => ({ ...prev, id: newId }));
      }
    }, [action, formData.id]);

    const selectedActionMeta = findItem(formData.handler || "");
    const missingRequiredFields = getMissingRequiredFields(
      selectedActionMeta?.input_schema,
      (formData.payload_template || {}) as Record<string, unknown>
    );

    const applySchemaTemplate = () => {
      if (!selectedActionMeta?.input_schema) {
        return;
      }
      const generated = buildTemplateFromSchema(selectedActionMeta.input_schema);
      setFormData((prev) => ({ ...prev, payload_template: generated }));
    };

    const handleSave = () => {
      if (!formData.id || !formData.handler) {
        alert("Action ID and Handler are required");
        return;
      }
      if (missingRequiredFields.length > 0) {
        alert(`Required fields missing in payload template: ${missingRequiredFields.join(", ")}`);
        return;
      }

      // For API Manager items, set handler to "api_manager.execute"
      // and ensure api_id is in payload
      const apiMeta = selectedActionMeta?.api_manager_meta;
      if (apiMeta) {
        const finalAction = {
          ...formData,
          handler: "api_manager.execute",
          payload_template: {
            ...(formData.payload_template as Record<string, unknown>),
            api_id: apiMeta.api_id,
          },
        };
        onSave(finalAction);
      } else {
        onSave(formData);
      }
      onOpenChange(false);
    };

    const handleCancel = () => {
      onOpenChange(false);
    };

    const handleTestAction = async () => {
      try {
        setIsTestingAction(true);
        setTestError(null);
        setTestResult(null);

        if (!formData.handler) {
          setTestError("Handler is required");
          return;
        }

        // Determine the actual handler for testing
        const apiMeta = selectedActionMeta?.api_manager_meta;
        const testHandler = apiMeta ? "api_manager.execute" : formData.handler;
        const testInputs = apiMeta
          ? { api_id: apiMeta.api_id, params: formData.payload_template || {} }
          : formData.payload_template || {};

        const testPayload = {
          action_id: testHandler,
          inputs: testInputs,
          context: { mode: "real", origin: "screen_editor_modal_test" },
          trace_id: `test-${Date.now()}`,
        };

        const response = await fetch("/ops/ui-actions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testPayload),
        });

        if (!response.ok) {
          throw new Error(`Failed: ${response.statusText}`);
        }

        const envelope = await response.json();
        const result = envelope?.data ?? envelope;
        setTestResult(result);
      } catch (error) {
        setTestError(error instanceof Error ? error.message : "Unknown error");
      } finally {
        setIsTestingAction(false);
      }
    };

     return (
       <Dialog open={open} onOpenChange={onOpenChange}>
         <DialogContent className="max-w-2xl">
           <DialogHeader>
            <DialogTitle>
              {action ? "Edit Action" : "Create Action"}
            </DialogTitle>
            <DialogDescription>
              {actionType === "screen"
                ? "Define a reusable action that can be called from components"
                : "Define an action for this component"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 max-h-[28rem] overflow-y-auto">
            {/* Action ID */}
            <div className="space-y-2">
              <Label htmlFor="action-id" className="text-xs font-medium">
                Action ID
              </Label>
              <Input
                id="action-id"
                value={formData.id || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, id: e.target.value }))
                }
                placeholder="e.g., action_submit_form"
                className="h-8 text-xs"
                disabled={!!action}
              />
              <p className="text-xs text-slate-500">
                {!action ? "Auto-generated if empty" : "Cannot change after creation"}
              </p>
            </div>

            {/* Label */}
            <div className="space-y-2">
              <Label htmlFor="action-label" className="text-xs font-medium">
                Label (optional)
              </Label>
              <Input
                id="action-label"
                value={formData.label || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, label: e.target.value }))
                }
                placeholder="e.g., Submit Form"
                className="h-8 text-xs"
              />
            </div>

            {/* Handler */}
            <div className="space-y-2">
              <Label htmlFor="action-handler" className="text-xs font-medium">
                Handler <span className="text-red-600">*</span>
              </Label>
              <Select
                value={formData.handler || ""}
                onValueChange={(value) =>
                  setFormData((prev) => ({ ...prev, handler: value }))
                }
              >
                <SelectTrigger id="action-handler" className="h-8 text-xs">
                  <SelectValue
                    placeholder={isCatalogLoading ? "Loading handlers..." : "Select a handler..."}
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel className="text-[10px] text-slate-400">Built-in Handlers</SelectLabel>
                    {builtinOptions.map((handler) => (
                      <SelectItem key={handler.value} value={handler.value}>
                        {handler.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                  {apiManagerOptions.length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-[10px] text-slate-400">API Manager</SelectLabel>
                      {apiManagerOptions.map((handler) => (
                        <SelectItem key={handler.value} value={handler.value}>
                          {handler.label}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  )}
                </SelectContent>
              </Select>

              {/* Catalog error warning */}
              {catalogError && (
                <p className="text-xs text-amber-500">
                  Catalog unavailable ({catalogError}) - showing fallback handlers
                </p>
              )}

              {/* Handler metadata display */}
              {selectedActionMeta?.description && (
                <p className="text-xs text-slate-500">{selectedActionMeta.description}</p>
              )}
              {selectedActionMeta?.output?.state_patch_keys &&
                selectedActionMeta.output.state_patch_keys.length > 0 && (
                  <p className="text-xs text-slate-500">
                    state_patch: {selectedActionMeta.output.state_patch_keys.join(", ")}
                  </p>
                )}
              {selectedActionMeta?.required_context &&
                selectedActionMeta.required_context.length > 0 && (
                  <p className="text-xs text-slate-500">
                    required context: {selectedActionMeta.required_context.join(", ")}
                  </p>
                )}
              {selectedActionMeta?.input_schema?.required &&
                selectedActionMeta.input_schema.required.length > 0 && (
                  <p className="text-xs text-slate-500">
                    Required: {selectedActionMeta.input_schema.required.join(", ")}
                  </p>
                )}

              {/* Input schema parameters */}
              {selectedActionMeta?.input_schema?.properties &&
                Object.keys(selectedActionMeta.input_schema.properties).length > 0 && (
                  <details className="mt-1">
                    <summary className="text-xs cursor-pointer hover:text-slate-300 font-medium" style={{ color: "var(--muted-foreground)" }}>
                      Input Parameters
                    </summary>
                    <div className="mt-1 rounded p-2 space-y-1" style={{ backgroundColor: "rgba(30, 41, 59, 0.5)" }}>
                      {Object.entries(selectedActionMeta.input_schema.properties).map(
                        ([key, prop]) => (
                          <div key={key} className="flex items-center gap-2 text-[11px]">
                            <code
                              className={`font-mono ${
                                selectedActionMeta.input_schema?.required?.includes(key)
                                  ? "text-rose-400"
                                  : "text-slate-300"
                              }`}
                            >
                              {key}
                              {selectedActionMeta.input_schema?.required?.includes(key) && "*"}
                            </code>
                            <span className="text-slate-500">({prop.type})</span>
                            {prop.title && (
                              <span className="text-slate-400">- {prop.title}</span>
                            )}
                            {prop.default !== undefined && (
                              <span className="text-slate-500">
                                = {JSON.stringify(prop.default)}
                              </span>
                            )}
                          </div>
                        )
                      )}
                    </div>
                  </details>
                )}

              {/* Sample output preview */}
              {selectedActionMeta?.sample_output && (
                <details className="mt-1">
                  <summary className="text-xs cursor-pointer text-emerald-400 hover:text-emerald-300 font-medium">
                    Sample Output Preview
                  </summary>
                  <pre className="mt-1 p-2 rounded bg-slate-800 text-[11px] text-slate-300 overflow-x-auto max-h-32">
                    {JSON.stringify(selectedActionMeta.sample_output, null, 2)}
                  </pre>
                </details>
              )}

              {/* API Manager meta */}
              {selectedActionMeta?.api_manager_meta && (
                <p className="text-xs text-sky-400">
                  API: {selectedActionMeta.api_manager_meta.method} {selectedActionMeta.api_manager_meta.path} ({selectedActionMeta.api_manager_meta.mode})
                </p>
              )}
            </div>

            {/* Payload Template */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Payload Template (optional)</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[11px]"
                  onClick={applySchemaTemplate}
                  disabled={!selectedActionMeta?.input_schema}
                >
                  Apply Input Template
                </Button>
              </div>
              <PayloadTemplateEditor
                template={formData.payload_template || {}}
                onChange={(template) =>
                  setFormData((prev) => ({
                    ...prev,
                    payload_template: template,
                  }))
                }
                stateTree={stateTree}
                contextTree={contextTree}
                inputsTree={inputsTree}
                className="text-xs"
              />
              {missingRequiredFields.length > 0 && (
                <p className="text-xs text-amber-600">
                  Missing required fields: {missingRequiredFields.join(", ")}
                </p>
              )}
            </div>

            {/* Context Required (screen-level only) */}
            {actionType === "screen" && "context_required" in formData && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">
                  Context Required (optional)
                </Label>
                <Input
                  value={(formData as ScreenAction).context_required?.join(", ") || ""}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      context_required: e.target.value
                        ? e.target.value.split(",").map((s) => s.trim())
                        : [],
                    }))
                  }
                  placeholder="e.g., user_id, session"
                  className="h-8 text-xs"
                />
                <p className="text-xs text-slate-500">
                  Comma-separated list of context variables required by this action
                </p>
              </div>
            )}

            {/* Chain Policy (component-level) */}
            {actionType === "component" && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">Chain Policy</Label>
                <label className="flex items-center gap-2 text-xs text-slate-300">
                  <Checkbox
                    checked={!!(formData as ComponentActionRef).continue_on_error}
                    onCheckedChange={(checked) =>
                      setFormData((prev) => ({
                        ...prev,
                        continue_on_error: !!checked,
                      }))
                    }
                  />
                  Continue on error
                </label>
                <p className="text-xs text-slate-500">
                  If enabled, next actions run even when this action fails.
                </p>
                <label className="flex items-center gap-2 text-xs text-slate-300">
                  <Checkbox
                    checked={(formData as ComponentActionRef).stop_on_error !== false}
                    onCheckedChange={(checked) =>
                      setFormData((prev) => ({
                        ...prev,
                        stop_on_error: !!checked,
                      }))
                    }
                  />
                  Stop on error
                </label>
                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div className="space-y-1 col-span-2">
                    <Label className="text-[11px] text-slate-400">Policy Preset</Label>
                    <Select
                      value=""
                      onValueChange={(value) => {
                        const preset = CHAIN_POLICY_PRESETS.find((item) => item.id === value);
                        if (!preset) return;
                        setFormData((prev) => ({
                          ...prev,
                          ...preset.values,
                        }));
                      }}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Apply preset..." />
                      </SelectTrigger>
                      <SelectContent>
                        {CHAIN_POLICY_PRESETS.map((preset) => (
                          <SelectItem key={preset.id} value={preset.id}>
                            {preset.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px] text-slate-400">Retry Count</Label>
                    <Input
                      type="number"
                      min={0}
                      max={5}
                      value={String((formData as ComponentActionRef).retry_count ?? 0)}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          retry_count: Math.max(0, Math.min(5, Number(e.target.value || 0))),
                        }))
                      }
                      className="h-8 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[11px] text-slate-400">Retry Delay (ms)</Label>
                    <Input
                      type="number"
                      min={0}
                      step={100}
                      value={String((formData as ComponentActionRef).retry_delay_ms ?? 500)}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          retry_delay_ms: Math.max(0, Number(e.target.value || 0)),
                        }))
                      }
                      className="h-8 text-xs"
                    />
                  </div>
                </div>
                <div className="space-y-1 pt-2">
                  <Label className="text-[11px] text-slate-400">
                    Run If (binding expression)
                  </Label>
                  <Input
                    value={String((formData as ComponentActionRef).run_if || "")}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        run_if: e.target.value,
                      }))
                    }
                    placeholder="{{state.flags.can_submit}}"
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1 pt-2">
                  <Label className="text-[11px] text-slate-400">
                    On Error Action Index
                  </Label>
                  <Input
                    type="number"
                    min={-1}
                    value={String((formData as ComponentActionRef).on_error_action_index ?? -1)}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        on_error_action_index: Number(e.target.value || -1),
                      }))
                    }
                    placeholder="-1"
                    className="h-8 text-xs"
                  />
                  <p className="text-[11px] text-slate-500">
                    -1 disables fallback. Otherwise run selected index when this action fails.
                  </p>
                </div>
                <div className="space-y-1 pt-2">
                  <Label className="text-[11px] text-slate-400">
                    On Error Action Indexes (comma separated)
                  </Label>
                  <Input
                    value={((formData as ComponentActionRef).on_error_action_indexes || []).join(", ")}
                    onChange={(e) =>
                      setFormData((prev) => {
                        const parsed = e.target.value
                          .split(",")
                          .map((v) => v.trim())
                          .filter((v) => v.length > 0)
                          .map((v) => Number(v))
                          .filter((v) => Number.isFinite(v) && v >= 0);
                        return {
                          ...prev,
                          on_error_action_indexes: parsed,
                        };
                      })
                    }
                    placeholder="2, 3, 4"
                    className="h-8 text-xs"
                  />
                  <p className="text-[11px] text-slate-500">
                    Optional. Runs fallback actions in order until one succeeds.
                  </p>
                </div>
              </div>
            )}

            {/* Test Result Display */}
            {testError && (
              <div className="p-2 rounded bg-red-950/50 border border-red-800">
                <p className="text-xs font-medium text-red-400">Test Error</p>
                <p className="text-xs text-red-300 mt-1">{testError}</p>
              </div>
            )}

            {testResult && (
              <div className="p-2 rounded bg-emerald-950/50 border border-emerald-800">
                <p className="text-xs font-medium text-emerald-400">Test Successful</p>
                {testResult.trace_id && (
                  <p className="text-xs text-emerald-300 mt-1">
                    Trace ID: <code className="bg-emerald-900/50 px-1 rounded">{testResult.trace_id}</code>
                  </p>
                )}
                {testResult.state_patch && (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer text-emerald-300 font-medium">
                      State changes
                    </summary>
                    <pre className="text-[11px] bg-emerald-900/30 p-1 rounded mt-1 overflow-x-auto max-h-32 text-slate-300">
                      {JSON.stringify(testResult.state_patch, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </div>

          <DialogFooter className="flex gap-2 justify-between">
            <div className="flex gap-2">
              <Button
                onClick={handleCancel}
                variant="outline"
                size="sm"
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                onClick={handleTestAction}
                variant="secondary"
                size="sm"
                className="text-xs"
                disabled={isTestingAction || !formData.handler || missingRequiredFields.length > 0}
              >
                {isTestingAction ? "Testing..." : "Test Action"}
              </Button>
            </div>
            <Button
              onClick={handleSave}
              size="sm"
              className="text-xs"
            >
              {action ? "Update" : "Create"} Action
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }
);

ActionEditorModal.displayName = "ActionEditorModal";
