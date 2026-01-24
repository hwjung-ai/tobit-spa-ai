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
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { PathTreeNode } from "@/components/admin/screen-editor/visual/BindingEditor";

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

// Available handlers from the backend
const AVAILABLE_HANDLERS = [
  { value: "http_request", label: "HTTP Request" },
  { value: "run_workflow", label: "Run Workflow" },
  { value: "update_state", label: "Update State" },
  { value: "navigate", label: "Navigate" },
  { value: "open_modal", label: "Open Modal" },
  { value: "close_modal", label: "Close Modal" },
  { value: "refresh_data", label: "Refresh Data" },
  { value: "custom", label: "Custom Handler" },
];

/**
 * ActionEditorModal Component
 *
 * Dialog for creating/editing actions (both screen-level and component-level).
 * Allows selection of:
 * - Action handler/type (HTTP, Workflow, State Update, etc.)
 * - Payload template with bindings
 * - Context requirements
 *
 * Used by: PropertiesPanel Actions section
 *
 * @param open - Whether the modal is open
 * @param onOpenChange - Callback when open state changes
 * @param action - Action to edit (null for new)
 * @param actionType - Whether this is a screen or component action
 * @param onSave - Callback when action is saved
 * @param stateTree - Hierarchical state paths
 * @param contextTree - Hierarchical context paths
 * @param inputsTree - Hierarchical inputs paths
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
    ref
  ) => {
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
        } as ComponentActionRef;
      }
    });

    const [isTestingAction, setIsTestingAction] = useState(false);
    const [testResult, setTestResult] = useState<ActionTestResult | null>(null);
    const [testError, setTestError] = useState<string | null>(null);

    // Generate action ID if new
    useEffect(() => {
      if (!action && !formData.id) {
        const timestamp = Date.now();
        const newId = `action_${timestamp}`;
        setFormData((prev) => ({ ...prev, id: newId }));
      }
    }, [action, formData.id]);

    const handleSave = () => {
      if (!formData.id || !formData.handler) {
        alert("Action ID and Handler are required");
        return;
      }

      onSave(formData);
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

        // Prepare test request
        const testPayload = {
          handler: formData.handler,
          payload: formData.payload_template || {},
          context: {},
          trace_id: `test-${Date.now()}`,
        };

        // Call /ops/ui-actions endpoint
        const response = await fetch("/ops/ui-actions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(testPayload),
        });

        if (!response.ok) {
          throw new Error(`Failed: ${response.statusText}`);
        }

        const result = await response.json();
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

          <div className="space-y-4 max-h-96 overflow-y-auto">
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
              <p className="text-xs text-gray-500">
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
                  <SelectValue placeholder="Select a handler..." />
                </SelectTrigger>
                <SelectContent>
                  {AVAILABLE_HANDLERS.map((handler) => (
                    <SelectItem key={handler.value} value={handler.value}>
                      {handler.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Payload Template */}
            <div className="space-y-2">
              <Label className="text-xs font-medium">
                Payload Template (optional)
              </Label>
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
                <p className="text-xs text-gray-500">
                  Comma-separated list of context variables required by this action
                </p>
              </div>
            )}

            {/* Test Result Display */}
            {testError && (
              <div className="p-2 rounded bg-red-50 border border-red-200">
                <p className="text-xs font-medium text-red-700">Test Error</p>
                <p className="text-xs text-red-600 mt-1">{testError}</p>
              </div>
            )}

            {testResult && (
              <div className="p-2 rounded bg-green-50 border border-green-200">
                <p className="text-xs font-medium text-green-700">Test Successful</p>
                {testResult.trace_id && (
                  <p className="text-xs text-green-600 mt-1">
                    Trace ID: <code className="bg-green-100 px-1 rounded">{testResult.trace_id}</code>
                  </p>
                )}
                {testResult.state_patch && (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer text-green-600 font-medium">
                      State changes
                    </summary>
                    <pre className="text-xs bg-green-100 p-1 rounded mt-1 overflow-x-auto">
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
                disabled={isTestingAction || !formData.handler}
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
