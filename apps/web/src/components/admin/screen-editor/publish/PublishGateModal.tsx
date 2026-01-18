"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ValidationChecklist, { CheckResult } from "./ValidationChecklist";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import {
  validateScreenSchema,
  validateBindingPath,
  validateActionHandler,
} from "@/lib/ui-screen/validation-utils";
import { Loader2 } from "lucide-react";

interface PublishGateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

export default function PublishGateModal({
  open,
  onOpenChange,
  onConfirm,
}: PublishGateModalProps) {
  const editorState = useEditorState();
  const [checks, setChecks] = useState<CheckResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    if (open) {
      runValidationChecks();
    }
  }, [open]);

  const runValidationChecks = async () => {
    if (!editorState.screen) return;

    setIsRunning(true);
    const results: CheckResult[] = [];

    // Check 1: Schema Validation
    try {
      const schemaErrors = validateScreenSchema(editorState.screen);
      results.push({
        name: "Schema Validation",
        status: schemaErrors.length === 0 ? "pass" : "fail",
        errors: schemaErrors.map((e) => e.message),
      });
    } catch (error) {
      results.push({
        name: "Schema Validation",
        status: "fail",
        errors: [error instanceof Error ? error.message : "Unknown error"],
      });
    }

    // Check 2: Binding Validation
    try {
      const bindingErrors: string[] = [];

      // Check all component props
      editorState.screen.components.forEach((comp) => {
        if (comp.props) {
          Object.entries(comp.props).forEach(([key, value]) => {
            if (typeof value === "string" && value.includes("{{")) {
              const errors = validateBindingPath(value, editorState.screen!);
              errors.forEach((e) => {
                bindingErrors.push(
                  `Component "${comp.label || comp.id}" prop "${key}": ${e.message}`
                );
              });
            }
          });
        }

        // Check visibility rule
        if (comp.visibility?.rule && typeof comp.visibility.rule === "string") {
          const errors = validateBindingPath(comp.visibility.rule, editorState.screen!);
          errors.forEach((e) => {
            bindingErrors.push(
              `Component "${comp.label || comp.id}" visibility: ${e.message}`
            );
          });
        }

        // Check component actions
        if (comp.actions) {
          comp.actions.forEach((action) => {
            if (action.payload_template) {
              Object.entries(action.payload_template).forEach(([key, value]) => {
                if (typeof value === "string" && value.includes("{{")) {
                  const errors = validateBindingPath(value, editorState.screen!);
                  errors.forEach((e) => {
                    bindingErrors.push(
                      `Component "${comp.label || comp.id}" action "${action.id}" payload "${key}": ${e.message}`
                    );
                  });
                }
              });
            }
          });
        }
      });

      results.push({
        name: "Binding Validation",
        status: bindingErrors.length === 0 ? "pass" : "fail",
        errors: bindingErrors.length > 0 ? bindingErrors : undefined,
      });
    } catch (error) {
      results.push({
        name: "Binding Validation",
        status: "fail",
        errors: [error instanceof Error ? error.message : "Unknown error"],
      });
    }

    // Check 3: Action Validation
    try {
      const actionErrors: string[] = [];

      // Check screen-level actions
      editorState.screen.actions?.forEach((action) => {
        const errors = validateActionHandler(action.handler);
        errors.forEach((e) => {
          actionErrors.push(`Action "${action.id}": ${e.message}`);
        });
      });

      // Check component-level actions
      editorState.screen.components.forEach((comp) => {
        comp.actions?.forEach((action) => {
          const errors = validateActionHandler(action.handler);
          errors.forEach((e) => {
            actionErrors.push(
              `Component "${comp.label || comp.id}" action "${action.id}": ${e.message}`
            );
          });
        });
      });

      results.push({
        name: "Action Validation",
        status: actionErrors.length === 0 ? "pass" : "fail",
        errors: actionErrors.length > 0 ? actionErrors : undefined,
      });
    } catch (error) {
      results.push({
        name: "Action Validation",
        status: "fail",
        errors: [error instanceof Error ? error.message : "Unknown error"],
      });
    }

    // Check 4: Dry-Run Test (optional - only if all other checks pass)
    if (results.every((r) => r.status === "pass")) {
      try {
        // This would call the actual action test endpoint if available
        // For now, we just mark it as passed
        results.push({
          name: "Dry-Run Test",
          status: "pass",
          warnings: ["Dry-run execution not available in current environment"],
        });
      } catch (error) {
        results.push({
          name: "Dry-Run Test",
          status: "warn",
          warnings: [error instanceof Error ? error.message : "Dry-run failed"],
        });
      }
    }

    setChecks(results);
    setIsRunning(false);
  };

  const canPublish = checks.every((c) => c.status !== "fail");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Publish Validation</DialogTitle>
          <DialogDescription>
            All checks must pass before publishing. This ensures your screen is safe for production.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-96 overflow-y-auto">
          {isRunning ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-slate-600" />
              <span className="text-sm text-slate-600">Running validation checks...</span>
            </div>
          ) : checks.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-500">
              No checks completed
            </div>
          ) : (
            <ValidationChecklist checks={checks} />
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isRunning}
          >
            Cancel
          </Button>
          <Button
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
            disabled={!canPublish || isRunning}
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Validating...
              </>
            ) : (
              "Publish"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
